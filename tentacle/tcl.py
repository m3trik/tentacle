# !/usr/bin/python
# coding=utf-8
"""The host-agnostic entry point — one launcher snippet for every DCC.

A startup script should not have to know which class its DCC needs, nor how that DCC wants
startup deferred (Maya: ``executeDeferred``; Blender: a one-shot ``bpy.app.timers``; 3ds Max:
immediately). :meth:`Tcl.launch` detects the host and does the right thing, so the documented
snippet is the same two lines everywhere::

    from tentacle import Tcl
    Tcl.launch(key_show="Z")

``key_show`` names this install's DEFAULT activation key. A key the user sets in the
shortcut editor (or a DCC-side rebind) persists and outranks it, so the snippet can keep
naming its default without overwriting the user's choice (see :meth:`Tcl.resolve_key`).

This module is also the single source for the **activation-key contract** the three ``tcl_<dcc>``
entry classes share: the ``Key_``-prefix normalization and the default chord→menu table
(:meth:`Tcl.chord_bindings`), which were three near-verbatim copies differing only in the
both-button target. Import-safe everywhere — stdlib only, and every DCC module it dispatches to is
imported lazily inside the launch path (so ``import tentacle`` in a ``userSetup.py`` stays cheap
and the heavy DCC imports happen on the deferred tick, as they did when each snippet imported its
own class).

The **DCC engine** (``mayatk`` / ``blendertk``) is an *extra*, not a hard dependency: the two
hosts install into separate interpreters and each imports exactly one engine. Every extra in
``pyproject.toml`` is named after its :attr:`_TclInternal.HOSTS` key, so :meth:`Tcl.host` doubles
as the extra resolver and no second table can drift — :meth:`Tcl.declared_dists` reads the pins
straight back out of the installed metadata, and :meth:`Tcl.engine_install_hint` turns a missing
engine into the exact pip line that fixes it.
"""

import os
import re
import sys
import importlib


class _TclInternal:
    """Host detection data + the per-DCC startup mechanics behind :class:`Tcl`."""

    # Default activation key. Bare (no ``Key_`` prefix) — normalized by ``qt_key_name``.
    DEFAULT_KEY = "Z"

    #: Startup banner issued by ``Tcl.banner()`` on the launch path (see ``banner``).
    BANNER = "Good {hr}! You are using {modver} with {pyver}."

    #: Once-per-process latch for :meth:`Tcl.banner`. Written on the base class so the
    #: latch is shared by every subclass rather than shadowed per-subclass.
    _BANNERED = False

    # host name -> the module whose importability proves we're inside that DCC. Ordered:
    # the first match wins, so a mayapy that also has a pip-installed ``bpy`` still reads as Maya.
    HOSTS = {
        "maya": "maya.cmds",
        "blender": "bpy",
        "max": "pymxs",
    }

    # Blender startup scripts run before the UI has settled; the Qt host needs a beat (the
    # interval the launch snippet carried before this module existed).
    BLENDER_START_DELAY = 0.5

    #: Distribution this package installs as — the base of every ``[extra]`` spec. Each
    #: extra is named after a HOSTS key above, so ``host()`` resolves which one applies.
    DIST = "tentacletk"

    # The two halves of the PEP 508 rows ``importlib.metadata.requires`` returns (see
    # ``_requires``). Where a requirement name ends, and the ``extra ==`` clause that
    # assigns a row to an extra — matched as a CLAUSE so a combined marker
    # (``python_version >= "3.10" and extra == "maya"``) still resolves.
    _REQ_BOUNDARY = re.compile(r"""[<>=!~;\[\s]""")
    _EXTRA_CLAUSE = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")

    @staticmethod
    def _maya_is_batch():
        """True under ``maya -batch`` / ``maya.standalone`` (no GUI, no real Qt)."""
        try:
            from maya import cmds

            return bool(cmds.about(batch=True))
        except Exception:  # cmds unavailable/uninitialized — assume interactive
            return False

    @classmethod
    def _launch_maya(cls, **kwargs):
        """Maya: build on an idle event — ``userSetup.py`` runs before the UI exists.

        A batch/standalone session is a deliberate, quiet no-op. The same ``userSetup.py`` also
        runs under ``mayapy`` / ``maya -batch``, so raising there would break every headless run —
        and there is nothing to build anyway: batch has no GUI Qt (QWidget construction on Maya's
        non-GUI stub takes the interpreter down natively — 0xC0000409, no traceback) and no idle
        queue to defer onto. Checked up front rather than relying on which branch below happens to
        fire: ``mayapy`` ships ``maya.utils`` *without* ``executeDeferred`` until
        ``standalone.initialize()`` has run, so the fallback's meaning flips mid-session.
        """
        if cls._maya_is_batch():
            return None

        def build():
            TclMaya = cls._import_entry("maya", "tentacle.tcl_maya", "TclMaya")

            return TclMaya(**kwargs)

        try:
            from maya.utils import executeDeferred
        except (
            ImportError
        ):  # no idle queue to defer onto — interactive but unusual; build now.
            return build()
        executeDeferred(build)
        return None

    @classmethod
    def _launch_blender(cls, **kwargs):
        """Blender: build on a one-shot timer, through the add-on entry (Qt host + diagnostics)."""
        import bpy

        def build():
            try:
                tcl_blender = cls._import_entry("blender", "tentacle.tcl_blender")
                tcl_blender.register(**kwargs)
            except ImportError as error:
                # A timer callback has no handler, so this would print a traceback
                # to the SYSTEM console -- hidden by default on Windows -- and the
                # user would see the launcher simply do nothing. The install hint
                # is the entire value of this error, so it has to reach a surface
                # they are looking at. Scoped to ImportError deliberately: a real
                # bug in registration keeps its traceback rather than being dressed
                # up as "not installed".
                cls._report_blender_startup_error(error)
            return None  # a timer returning None is unregistered — one shot, not a poll

        bpy.app.timers.register(build, first_interval=cls.BLENDER_START_DELAY)
        return None

    @staticmethod
    def _report_blender_startup_error(error):
        """Show *error* in Blender, falling back to the console.

        ``popup_menu`` is the only surface available here: there is no operator to
        ``self.report`` from, and a timer callback is not guaranteed a UI context,
        so the call itself can raise. Both the popup and the fallback are inside
        the guard because the thing that must not happen is the ORIGINAL error
        escaping the callback -- Blender then reports the add-on as broken, which
        is a worse answer than the one this exists to deliver.

        The message is split on sentences rather than drawn as one label: Blender
        does not wrap a ``layout.label``, so the pip line -- the part the user has
        to read -- would be clipped at the popup's edge.
        """
        import bpy

        text = str(error)
        try:
            # Split AFTER the terminator, keeping it: appending "." to each
            # piece double-punctuates the last one -- and the last one is the
            # pip line, the part that has to be readable.
            lines = [s for s in (p.strip() for p in re.split(r"(?<=\.)\s+", text)) if s]

            def draw(self, _context):
                for line in lines:
                    self.layout.label(text=line)

            bpy.context.window_manager.popup_menu(draw, title="Tentacle", icon="ERROR")
        except Exception:  # noqa: BLE001 -- no UI context; the console is all that is left
            print(f"[tentacle] {text}")

    @classmethod
    def _launch_max(cls, **kwargs):
        """3ds Max: no deferral needed — its startup scripts already run against a live UI."""
        TclMax = cls._import_entry("max", "tentacle.tcl_max", "TclMax")

        return TclMax(**kwargs)

    # ---------------------------------------------------------------- engine extras
    @classmethod
    def engine_dists(cls, host):
        """Distribution names ``pyproject``'s ``[project.optional-dependencies]`` declares for *host*.

        Read from the INSTALLED metadata rather than a second copy in code, so the pins
        push.ps1 syncs stay the only source of truth. Returns ``()`` for an unknown host,
        for a host with no extra (``max``, until a ``maxtk`` exists), and on a source
        checkout with no ``.egg-info``/``.dist-info`` — where the engines are on
        ``sys.path`` anyway and there is nothing to install.

        The ``if host`` guard is load-bearing: ``_requires(extra=None)`` means "the BASE
        set", so a falsy host would answer "this host's engine is pythontk and uitk" —
        and ``host()`` returns None outside any DCC.
        """
        return cls._requires(extra=host) if host else ()

    @classmethod
    def _requires(cls, extra=None):
        """Distribution names from :attr:`DIST`'s metadata: the base set, or one *extra*'s.

        ``importlib.metadata.requires`` hands back raw PEP 508 strings
        (``'mayatk>=0.13.53; extra == "maya"'``). Base rows carry no ``extra ==`` clause;
        an extra's rows carry exactly theirs.

        Parsed here rather than with ``packaging`` (not guaranteed inside a DCC
        interpreter) or uitk's ``split_requirement``: this method already parses the
        marker half of the same PEP 508 string, so delegating only the name half would
        split one parse across two packages for no gain — the two halves read different
        fields and cannot drift into disagreement. Keeping it local also means TOTAL:
        nothing here can raise, which matters because :meth:`_import_entry` calls into
        it from inside an ``except ImportError`` handler.
        """
        try:
            from importlib.metadata import requires

            lines = requires(cls.DIST)
        except Exception:  # not installed (source checkout), or metadata unreadable
            return ()
        if not lines:
            return ()

        names = []
        for line in lines:
            spec, _, marker = line.partition(";")
            # Match the CLAUSE, not the whole marker. setuptools writes a lone
            # ``extra == "maya"`` today, but a combined marker
            # (``python_version >= "3.10" and extra == "maya"``) is legal — and an
            # exact-string compare would silently drop that engine, leaving the
            # launcher with no diagnostic and the updater blind to it.
            clause = cls._EXTRA_CLAUSE.search(marker)
            if extra is None:
                if clause:  # an extra's row is not part of the base set
                    continue
            elif not clause or clause.group(1) != extra:
                continue
            name = cls._REQ_BOUNDARY.split(spec.strip(), maxsplit=1)[0].strip()
            if name:
                names.append(name)
        return tuple(names)

    @classmethod
    def _import_entry(cls, host, module, attr=None):
        """Import a DCC entry module, re-raising a MISSING ENGINE with the fix.

        The engine is an extra, so the one import error a user can actually hit here is
        "you installed ``tentacletk`` without its engine". Only a ``ModuleNotFoundError``
        for a distribution this host's extra DECLARES is rewritten — a missing ``PIL``
        propagates untouched (the check is against the declared names, not merely "an
        ImportError happened"), and so does a ``from mayatk import Gone``, which raises a
        PLAIN ImportError whose ``.name`` is still ``mayatk``: there the engine IS
        installed and a symbol it exports moved, so a pip line would reinstall what is
        already there and hide the rename.

        Deliberately does NOT pip-install: driving pip from a DCC's startup tick blocks
        the host on network I/O, and Blender's bundled interpreter keeps user-site off
        ``sys.path`` so the obvious install would not even be importable (see
        ``blendertk.CoreUtils.ensure_packages``). A precise, actionable error beats a
        frozen DCC — the install line is right there to paste.
        """
        package, _, leaf = module.rpartition(".")
        try:
            # ``from <package> import <leaf>`` semantics, NOT ``import_module(module)``:
            # this package resolves submodules through ``bootstrap_package``'s lazy
            # ATTRIBUTE hook, and the suite patches the entry module onto
            # ``tentacle.__dict__`` (see ``_as_blender``) precisely because attribute
            # lookup wins over ``sys.modules``. Going straight to ``import_module``
            # bypassed both and imported the real Blender/Qt stack mid-test.
            parent = importlib.import_module(package) if package else None
            imported = getattr(parent, leaf, None) if parent is not None else None
            if imported is None:
                imported = importlib.import_module(module)
        except ImportError as error:
            missing = getattr(error, "name", None) or ""
            # ``import mayatk.foo`` failing reports ``mayatk.foo``; match the root too.
            root = missing.split(".")[0]
            # ModuleNotFoundError ONLY: a plain ImportError carrying the same ``name``
            # is ``from mayatk import Gone`` — the engine IS installed and a symbol it
            # exports moved. That is the cascade break, and answering it with a pip
            # line for an already-installed dist buries the real cause.
            if (
                root
                and isinstance(error, ModuleNotFoundError)
                and root in cls.engine_dists(host)
            ):
                raise ImportError(
                    f"tentacle: the {host} engine ({root}) is not installed. "
                    f"{cls.engine_install_hint(host)}"
                ) from error
            raise
        return getattr(imported, attr) if attr else imported

    @classmethod
    def engine_install_hint(cls, host=None):
        """The pip line that installs *host*'s engine, naming the interpreter to use.

        Quoted because ``[maya]`` is a glob character class in POSIX shells; harmless in
        cmd/PowerShell, which pass it through literally.

        The interpreter is named ONLY when uitk blesses one. ``pip_python`` returns None
        for a DCC host binary with no sibling python, and ``sys.executable`` is then
        ``maya.exe`` / ``blender.exe`` — pip driven through the host routes into its
        ``-c`` handler and HANGS it (see ``OptionalPackageManager.default_install``), so
        falling back to it would hand the user a command that freezes their DCC. Better
        to describe the interpreter than to name a fatal one.
        """
        host = host or cls.host()
        # A host that declares no engine has no extra to install — ``"tentacletk[max]"``
        # resolves to nothing and pip merely warns. Fall through to the hostless branch,
        # which names the hosts that DO ship one. Gated on metadata being readable: on a
        # source checkout every host reads as engine-less, and demoting a real Maya user
        # there would cost them the interpreter-specific pip line for nothing.
        if host and cls._requires() and not cls.engine_dists(host):
            host = None
        spec = f'"{cls.DIST}[{host}]"'
        if not host:  # asked outside any DCC — name the hosts rather than "[None]"
            # Only hosts that actually DECLARE an extra: offering ``[max]``, which
            # ships no engine, sends the reader to a pip line that resolves to nothing.
            hosts = [h for h in cls.HOSTS if cls.engine_dists(h)] or list(cls.HOSTS)
            spec = " / ".join(f'"{cls.DIST}[{h}]"' for h in hosts)
            return f"Install it with:  python -m pip install {spec}"

        python = None
        try:  # the sibling that can actually run pip (maya.exe -> mayapy.exe)
            from uitk.managers.optional_package_manager import OptionalPackageManager

            python = OptionalPackageManager.pip_python()
        except Exception:
            # uitk unreachable — NOT exotic: ``pip_python`` imports ``ExternalAppHandler``,
            # which pulls qtpy, which raises when no Qt binding is installed (a bare venv,
            # CI). Fall back only on a positive match — an interpreter literally named
            # ``python*`` cannot be a DCC host binary, and that covers the venv/CI case
            # plus Blender's bundled ``<prefix>/bin/python.exe``. Deliberately an
            # ALLOWLIST: "not a known host" would name the host binary of any DCC whose
            # probe module failed to import, and that command hangs the session.
            name = os.path.basename(sys.executable or "").lower()
            python = sys.executable if name.startswith("python") else None
        if not python:
            return (
                f"Install it into this DCC's own Python (mayapy.exe, or Blender's "
                f"bundled python.exe) with:  -m pip install {spec}"
            )
        return f'Install it with:  "{python}" -m pip install {spec}'


class Tcl(_TclInternal):
    """Launch tentacle in whichever DCC is hosting this process.

    The documented startup snippet for every supported DCC (``key_show`` names
    the DEFAULT activation key; a rebind the user saves in the shortcut editor
    persists and outranks it — see :meth:`resolve_key`)::

        from tentacle import Tcl
        Tcl.launch(key_show="Z")
    """

    @classmethod
    def host(cls):
        """The DCC hosting this process (``'maya'``/``'blender'``/``'max'``), or None.

        Checks ``sys.modules`` first — inside a running DCC its own module is always already
        imported, so the answer is free and unambiguous — then falls back to an import attempt for
        a host that hasn't touched it yet (3ds Max does not pre-import ``pymxs``).
        """
        for name, probe in cls.HOSTS.items():
            if probe in sys.modules:
                return name
        for name, probe in cls.HOSTS.items():
            try:
                importlib.import_module(probe)
                return name
            except ImportError:
                continue
        return None

    @classmethod
    def declared_dists(cls, host=None, include_self=True):
        """Every ecosystem distribution THIS install actually uses, for *host*.

        The base dependencies plus, when *host* names one, that host's engine extra —
        so a Maya install reports ``mayatk`` and never ``blendertk``, and a package the
        host cannot use can't be reported stale (or silently reinstalled) by the updater
        in ``slots/_settings.py``, which is this method's caller.

        Read from installed metadata, so it tracks ``pyproject.toml`` with no second
        copy. Returns ``()`` on a source checkout with no metadata — a caller that must
        degrade gracefully should treat empty as "unknown", not as "nothing installed".

        Parameters:
            host (str): A :attr:`HOSTS` key. ``None`` (default) resolves the running
                    host via :meth:`host`; pass a name explicitly to ask about another.
            include_self (bool): Append :attr:`DIST` itself.

        Returns:
            tuple: Distribution names, base first, engine next, self last.
        """
        host = cls.host() if host is None else host
        dists = list(cls._requires())
        if not dists:  # no metadata — nothing trustworthy to report
            return ()
        dists += [d for d in cls.engine_dists(host) if d not in dists]
        if include_self and cls.DIST not in dists:
            dists.append(cls.DIST)
        return tuple(dists)

    @classmethod
    def qt_key_name(cls, key_show=None):
        """Normalize an activation key to its Qt name: ``'Z'`` and ``'Key_Z'`` both → ``'Key_Z'``.

        ``None`` resolves to :attr:`DEFAULT_KEY`, so a caller can pass an unset value straight
        through rather than repeating the default.
        """
        key = key_show or cls.DEFAULT_KEY
        return key if key.startswith("Key_") else f"Key_{key}"

    @classmethod
    def resolve_key(cls, key_show=None, context_tags=None):
        """The activation key to launch with: **user-persisted > ``key_show`` > :attr:`DEFAULT_KEY`**.

        The precedence *is* the contract, and each rung answers a different question:

        * **persisted** — a key the user actively CHOSE: the shortcut editor, tentacle's own
          Preferences, or (Blender) an adopted Preferences ▸ Keymap rebind — every route goes
          through ``MarkingMenu.set_activation_key``, the sole writer of this value, so its
          presence is provenance. The user's choice outranks everything: a startup script
          re-asserts its ``key_show`` at every launch, and letting that overwrite the persisted
          choice was the "shortcut editor keeps resetting my key" bug.
        * **``key_show``** — the startup script names this install's DEFAULT. It applies on first
          run and for every user who never rebound — which is also what lets a changed default
          reach exactly those installs (a seeded chord table alone is not a user choice).
        * **default** — nothing named, nothing chosen: :attr:`DEFAULT_KEY`.

        ``context_tags`` selects the host's store (``{"maya"}`` / ``{"blender"}``) and must
        match the tags the entry class passes to ``MarkingMenu``, or it reads another host's key.
        """
        try:  # lazy: keeps this module importable without Qt/uitk (see the module docstring)
            from uitk import MarkingMenu

            stored = MarkingMenu.stored_activation_key(context_tags)
        except (
            Exception
        ):  # uitk unavailable or store unreadable — fall back to the default
            stored = None
        return cls.qt_key_name(stored or key_show)

    @classmethod
    def chord_bindings(cls, key_show=None, chord_target=None):
        """The default chord→menu table for ``key_show`` (bare or Qt-named).

        ``chord_target`` is the both-buttons chord's page — each DCC's own native menu set
        (``'maya#startmenu'`` / ``'blender#startmenu'``). Omitted, that chord is left unbound:
        3ds Max ships no native-menu page, and binding a gesture to a target that cannot resolve
        is worse than leaving the gesture free.
        """
        key = cls.qt_key_name(key_show)
        bindings = {
            key: "hud#startmenu",  # activation key alone + the default UI
            f"{key}|LeftButton": "cameras#startmenu",
            f"{key}|MiddleButton": "editors#startmenu",
            f"{key}|RightButton": "main#startmenu",
        }
        if chord_target:
            bindings[f"{key}|LeftButton|RightButton"] = chord_target
        return bindings

    @classmethod
    def banner(cls, template=None, force=False):
        """Print the startup banner — the one sanctioned emitter of :func:`tentacle.greeting`.

        Lives on the launch path, not at package import: ``import tentacle`` must stay
        side-effect free (root CLAUDE.md), while an actual DCC launch is exactly the moment
        a version/interpreter line is wanted. Never raises — a banner must not be able to
        stop a launch.

        Emits ONCE per process, which is exactly what the retired import-time call gave
        (a module body runs once). That guard is what lets every launch entry point call
        this unconditionally: a host entered directly (``tcl_blender.launch``) banners, and
        the same host reached through :meth:`launch` does not banner twice.

        Parameters:
            template (str): Greeting format string. Defaults to the shipped banner. See
                    :func:`tentacle.greeting` for the available placeholders.
            force (bool): Re-emit even if this process already bannered.

        Returns:
            (str)(None): The formatted banner, or None if already emitted or unavailable.
        """
        if cls._BANNERED and not force:
            return None
        try:  # imported here: tcl.py is bootstrapped BY the package __init__
            from tentacle import greeting

            text = greeting(template or cls.BANNER)
        except Exception:  # a banner must never block a launch
            return None
        _TclInternal._BANNERED = (
            True  # set on the base: every subclass shares the latch
        )
        return text

    @classmethod
    def launch(cls, key_show=None, **kwargs):
        """Start tentacle in the host DCC, deferring startup the way that host requires.

        Parameters:
            key_show (str): DEFAULT activation key — bare (``'Z'``, ``'Space'``) or Qt-named
                    (``'Key_Z'``). A key the user persisted (shortcut editor / DCC rebind)
                    outranks it. Omitted, each entry class applies its own default (Blender
                    additionally honors ``TENTACLE_KEY``; all fall back to :attr:`DEFAULT_KEY`).
            **kwargs: Forwarded verbatim to the DCC's entry class (``slot_source``, ``log_level``,
                    an explicit ``bindings`` dict, …).

        Returns:
            The marking-menu instance when startup is immediate (3ds Max, and a ``mayapy`` with no
            idle queue), else None — a deferred build has nothing to hand back yet.

        Raises:
            RuntimeError: No supported DCC detected (see :meth:`host`).
        """
        host = cls.host()
        if host is None:
            raise RuntimeError(
                "tentacle: no supported DCC host detected (looked for "
                f"{', '.join(cls.HOSTS.values())}). Tcl.launch() must be called from inside "
                "Maya, Blender or 3ds Max."
            )
        cls.banner()
        if key_show is not None:
            kwargs["key_show"] = key_show
        return getattr(cls, f"_launch_{host}")(**kwargs)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
