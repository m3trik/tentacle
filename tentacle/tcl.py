# !/usr/bin/python
# coding=utf-8
"""The one launcher — the same marking menu, built the same way, in every DCC.

A startup script should not have to know what its DCC needs, nor how that DCC wants startup
deferred. :meth:`Tcl.launch` detects the host, asks the host's toolkit for its marking-menu
host adapter (``mtk.MayaMarkingMenuHost`` / ``btk.BlenderMarkingMenuHost``, both
``uitk.MarkingMenuHost``), defers through it (Maya: ``executeDeferred``; Blender: a one-shot
``bpy.app.timers``) and :meth:`Tcl.build` makes ONE ``uitk.MarkingMenu(host=...)``, so the
documented snippet is the same two lines everywhere::

    from tentacle import Tcl
    Tcl.launch(key_show="Z")

``key_show`` names this install's DEFAULT activation key. A key the user sets in the
shortcut editor (or a DCC-side rebind) persists and outranks it, so the snippet can keep
naming its default without overwriting the user's choice (see :meth:`Tcl.resolve_key`).

Nothing in the launch and build is per host beyond :attr:`_TclInternal.HOSTS` detection: the
host name names the toolkit (:attr:`_TclInternal.ENGINES`), its adapter
(``<Host>MarkingMenuHost``), the chord menus' native-menu pages (``ui/<host>_menus``), the
both-button chord's target (``<host>#startmenu``) and the ``context_tags`` the menus'
``requires`` tags filter on. What a host answers differently -- its main window, its
activation-key half, its mouse, how its windows stack, its UI handler -- is its adapter's.
Settings > Reload is still a method per host (``_reload_maya`` / ``_reload_blender``): each
tears down what that host holds before the reload. This module is also the single source for
the **activation-key contract**: the ``Key_``-prefix normalization and the default chord→menu
table (:meth:`Tcl.chord_bindings`). Import-safe everywhere — stdlib only; the toolkit is
imported when a launch resolves its adapter (its root is lazy, so that costs only the
adapter's module), and Qt on the deferred build.

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
    }

    #: host -> its toolkit: the engine package a Slots class reaches through
    #: ``Slots.tk``, whose ``<Host>MarkingMenuHost`` adapter hosts the menu, and whose
    #: HOST-OWNED state an in-place reload would orphan (registered scriptJobs /
    #: OpenMaya callbacks; see :meth:`Tcl.prepare_reload`).
    ENGINES = {"maya": "mayatk", "blender": "blendertk"}

    #: Env var naming the DEFAULT activation key when a launch names none.
    KEY_ENV = "TENTACLE_KEY"

    #: host -> (module, attribute, call kwargs) that answers "no GUI to build a menu for"
    #: (``mayapy`` / ``maya -batch``, ``blender --background``). Read BEFORE the toolkit is
    #: imported, so a headless start -- every test chunk's ``userSetup.py`` -- pays nothing
    #: for a menu it cannot have (batch Maya has no GUI Qt: a QWidget on its stub takes the
    #: interpreter down natively). ``None`` kwargs read the attribute as a value.
    HEADLESS = {
        "maya": ("maya.cmds", "about", {"batch": True}),
        "blender": ("bpy", "app.background", None),
    }

    #: host -> the method that shows an error carrying its fix when the host's toolkit --
    #: whose adapter would show it -- is the part that failed to import. A host not listed
    #: raises it (Maya shows a startup script's traceback in its script editor).
    STARTUP_ERROR_REPORTERS = {"blender": "_report_blender_startup_error"}

    @staticmethod
    def _report_blender_startup_error(error):
        """Show *error* in Blender on a one-shot timer, falling back to the console.

        A startup script runs before Blender has a window (``popup_menu`` raises
        'context "window" is None' there), so the popup waits for a timer tick;
        ``persistent`` keeps the timer through the .blend a start may open. Raised
        instead, the error would print to the SYSTEM console -- hidden by default on
        Windows -- and the user would see the launcher simply do nothing, though the
        message carries its fix (the install line).

        The message is split on sentences and line breaks rather than drawn as one
        label: Blender does not wrap a ``layout.label``, so the pip line -- the part
        the user has to read -- would be clipped at the popup's edge.
        """
        import bpy

        text = str(error)

        def show():
            try:
                # Split AFTER the terminator, keeping it: appending "." to each
                # piece double-punctuates the last one -- and the last one is the
                # pip line, the part that has to be readable.
                lines = [
                    s
                    for s in (p.strip() for p in re.split(r"(?<=\.)\s+|\n", text))
                    if s
                ]

                def draw(self, _context):
                    for line in lines:
                        self.layout.label(text=line)

                bpy.context.window_manager.popup_menu(
                    draw, title="Tentacle", icon="ERROR"
                )
            except Exception:  # noqa: BLE001 -- no UI context; the console is all that is left
                print(f"[tentacle] {text}")
            return None  # one shot

        bpy.app.timers.register(show, first_interval=0.1, persistent=True)

    #: Distribution this package installs as — the base of every ``[extra]`` spec. Each
    #: extra is named after a HOSTS key above, so ``host()`` resolves which one applies.
    DIST = "tentacletk"

    # The two halves of the PEP 508 rows ``importlib.metadata.requires`` returns (see
    # ``_requires``). Where a requirement name ends, and the ``extra ==`` clause that
    # assigns a row to an extra — matched as a CLAUSE so a combined marker
    # (``python_version >= "3.10" and extra == "maya"``) still resolves.
    _REQ_BOUNDARY = re.compile(r"""[<>=!~;\[\s]""")
    _EXTRA_CLAUSE = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")

    # ---------------------------------------------------------------- reload (Settings)
    @classmethod
    def _reload_maya(cls):
        """Maya: retire, reload, then rebuild DEFERRED onto the idle queue.

        The rebuild cannot run in this frame: the slot that asked belongs to a
        module the reload re-executes, and building a marking menu while Qt is
        still dispatching that click destroys and constructs widget trees under
        the event being delivered. ``Tcl.launch`` defers on its own, so the new
        instance comes up on an idle tick with every stale frame unwound. The
        report goes through Maya (:meth:`_report_maya`), never the retired panel.
        """
        import html

        from maya.utils import executeDeferred

        retired = cls.prepare_reload("maya")

        def rebuild():
            from tentacle import Tcl as ReloadedTcl

            try:
                ReloadedTcl.launch()
            finally:
                cls.dispose_retired(retired)
            return None

        try:
            reloaded = cls.reload_packages("maya")
        except Exception as error:
            # The teardown already retired the menu, so returning here would
            # strand the session with no marking menu at all -- a worse place than
            # the stale one it started from. Rebuild from whatever is loaded.
            print(f"# Error: tentacle: reload failed: {error} #")
            executeDeferred(rebuild)
            cls._report_maya(f"Tentacle reload FAILED: {html.escape(str(error))}")
            return 0

        executeDeferred(rebuild)
        # reload_packages already NAMED each failure on the console; the line here
        # only says the reload was partial. Tolerant access: an older pythontk
        # returns a plain list rather than a ReloadReport.
        failed = getattr(reloaded, "failed", ())
        if failed:
            cls._report_maya(
                f"Tentacle reloaded {len(reloaded)} modules, "
                f"{len(failed)} FAILED (see the script editor)."
            )
        else:
            cls._report_maya(f"Tentacle reloaded ({len(reloaded)} modules).")
        return len(reloaded)

    @staticmethod
    def _report_maya(message):
        """Report through MAYA (an in-view message and the script editor): a
        ``message_box`` would render on the switchboard the reload just retired."""
        try:
            from maya import cmds

            cmds.inViewMessage(amg=message, pos="topCenter", fade=True)
        except Exception:  # no viewport (batch) -- the console still gets it
            pass
        print(f"# Result: {message} #")

    @classmethod
    def _reload_blender(cls):
        """Blender: ``tcl_blender.reload()`` tears tentacle's own surface down
        (blendertk's keymap, operator, poller, the Script Output dock) on top of
        :meth:`prepare_reload`, reloads, and re-registers on the next timer tick.
        It raises when the reload itself fails, before re-registering."""
        tcl_blender = cls._import_entry("blender", "tentacle.tcl_blender")
        count = tcl_blender.reload()
        print(f"tentacle: reloaded {count} module(s); re-registering on the next tick.")
        return count

    # ---------------------------------------------------------------- engine extras
    @classmethod
    def engine_dists(cls, host):
        """Distribution names ``pyproject``'s ``[project.optional-dependencies]`` declares for *host*.

        Read from the INSTALLED metadata rather than a second copy in code, so the pins
        push.ps1 syncs stay the only source of truth. Returns ``()`` for an unknown host,
        for a host with no extra, and on a source
        checkout with no ``.egg-info``/``.dist-info`` — where the engines are on
        ``sys.path`` anyway and there is nothing to install.

        The ``if host`` guard is load-bearing: ``_requires(extra=None)`` means "the BASE
        set", so a falsy host would answer "this host's engine is pythontk and uitk" —
        and ``host()`` returns None outside any DCC.
        """
        return cls._requires(extra=host) if host else ()

    @classmethod
    def _engine_module(cls, host):
        """This host's already-imported engine package, or None.

        ``sys.modules`` only — never an import: the engine is being torn down,
        not stood up, and a host with no engine must answer None rather than
        raise.
        """
        name = cls.ENGINES.get(host)
        return sys.modules.get(name) if name else None

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
        # A host that declares no engine has no extra to install — ``"tentacletk[<host>]"``
        # resolves to nothing and pip merely warns. Fall through to the hostless branch,
        # which names the hosts that DO ship one. Gated on metadata being readable: on a
        # source checkout every host reads as engine-less, and demoting a real Maya user
        # there would cost them the interpreter-specific pip line for nothing.
        if host and cls._requires() and not cls.engine_dists(host):
            host = None
        spec = f'"{cls.DIST}[{host}]"'
        if not host:  # asked outside any DCC — name the hosts rather than "[None]"
            # Only hosts that actually DECLARE an extra: offering one that ships no
            # engine sends the reader to a pip line that resolves to nothing.
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
                f"Install it into this DCC's own Python (mayapy, or Blender's "
                f"bundled python) with:  -m pip install {spec}"
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
        """The DCC hosting this process (``'maya'``/``'blender'``), or None.

        Checks ``sys.modules`` first — inside a running DCC its own module is always already
        imported, so the answer is free and unambiguous — then falls back to an import attempt for
        a host that hasn't touched it yet.
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
    def headless(cls, host=None):
        """True when *host* runs with no GUI to build a menu for (:attr:`HEADLESS`).

        Asks the host's own module, never the toolkit, so it costs nothing before a
        launch decides to import one. An answer the host cannot give (``cmds.about`` in a
        ``mayapy`` before ``standalone.initialize``) and a host with no probe read as a
        GUI, as the launch always assumed.
        """
        host = cls.host() if host is None else host
        spec = cls.HEADLESS.get(host)
        if spec is None:
            return False
        module, attribute, call = spec
        try:
            value = importlib.import_module(module)
            for part in attribute.split("."):
                value = getattr(value, part)
            return bool(value(**call) if call is not None else value)
        except Exception:  # unanswerable: assume a GUI
            return False

    @classmethod
    def declared_dists(cls, host=None, include_self=True):
        """Every ecosystem distribution THIS install actually uses, for *host*.

        The base dependencies plus, when *host* names one, that host's engine extra —
        so a Maya install reports ``mayatk`` and never ``blendertk``, and a package the
        host cannot use can't be reported stale (or silently reinstalled) by the updater
        in ``slots/settings.py`` (``SettingsSlots.ecosystem_dists``), this method's caller.

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
    def prepare_reload(cls, host=None):
        """Release the host resources an in-place reload would ORPHAN.

        ``Settings > Reload Scripts`` re-executes the ecosystem packages through
        ``ptk.ModuleReloader``. That rebinds module globals, but everything the
        DCC itself is still holding — a registered ``scriptJob``, an OpenMaya
        callback, an armed activation shortcut — keeps pointing at the code from
        before the reload, while the handle needed to cancel it is dropped on the
        floor with the old class object. Two consequences, both reported from live
        sessions: the reload appears to do nothing (the pre-reload marking menu
        still owns the activation key), and the DCC dies later, when a scene event
        fires a callback whose widget has since been destroyed.

        So the teardown has to happen HERE, before the reload, while the handles
        are still reachable:

        * every live ``MarkingMenu`` is retired (activation shortcut disposed);
        * the engine's ``ScriptJobManager`` singleton is reset, which kills its
          scriptJobs and removes its OpenMaya callbacks.

        Each step is guarded through ``sys.modules`` and tolerates an engine that
        does not offer it — a reload must never be blocked by a version skew in
        the thing it is about to replace.

        Parameters:
            host (str): A :attr:`HOSTS` key. ``None`` (default) resolves the
                    running host via :meth:`host`.

        Returns:
            list: The retired marking-menu instances. Hand them to
            :meth:`dispose_retired` once their replacement is up.
        """
        host = cls.host() if host is None else host

        retired = []
        # Through uitk's PUBLIC surface, never a private module path: the Maya
        # fork's previous teardown reached for internals (``MarkingMenu._instances``,
        # ``reset_instance``) that uitk had since dropped, and because every step
        # was guarded it no-opped in silence for as long as that skew lasted.
        uitk = sys.modules.get("uitk")
        if uitk is not None:
            try:
                # Normalized inside the guard: a skewed uitk whose retire_all
                # answers a COUNT would otherwise hand dispose_retired an int to
                # iterate, and that raises from inside the caller's finally. The
                # menus are retired by then either way, so degrading to "retired
                # but not disposed" costs a leak, not the reload.
                retired = list(uitk.MarkingMenu.retire_all() or ())
            except Exception as error:
                print(f"# Warning: tentacle: marking-menu teardown skipped: {error} #")

        engine = cls._engine_module(host)
        if engine is not None:
            try:
                engine.ScriptJobManager.reset()
            except Exception as error:
                print(f"# Warning: tentacle: scriptJob teardown skipped: {error} #")

        return retired

    @classmethod
    def reload_packages(cls, host=None):
        """Re-execute the ecosystem packages in dependency order, in place.

        The half of the reload both DCCs share, so the dependency order and the
        ``import_missing`` policy have one home rather than a copy per host.
        Call :meth:`prepare_reload` first and rebuild DEFERRED afterwards — see
        those two for why neither belongs in the same frame as the reload.

        ``import_missing=False`` restricts the refresh to what this session
        actually loaded: discovery-importing the rest would pull in the OTHER
        DCC's slot package, which imports a host that is not running.

        ``ptk.ModuleReloader`` does not abort on a module that raises — it
        records the failure and carries on — so failures are printed here.
        Leaving part of the ecosystem on the old code IS the "reload did
        nothing" report, one module at a time.

        Parameters:
            host (str): A :attr:`HOSTS` key. ``None`` (default) resolves the
                    running host via :meth:`host`.

        Returns:
            ptk.ReloadReport: The modules reloaded (a ``list``), carrying
            ``failed`` and ``skipped`` details.
        """
        import pythontk as ptk

        host = cls.host() if host is None else host
        engine = cls.ENGINES.get(host)
        report = ptk.ModuleReloader().reload(
            "tentacle",
            dependencies_first=tuple(d for d in ("pythontk", engine, "uitk") if d),
            import_missing=False,
        )
        for name, error in getattr(report, "failed", ()):
            print(f"# Error: tentacle: {name} did not reload: {error} #")
        return report

    @staticmethod
    def dispose_retired(instances):
        """Schedule deletion of the pre-reload marking menus in *instances*.

        Retiring makes an instance inert but leaves the widget tree parented to
        the DCC's main window, so without this every reload in a session stacks
        up another full UI. Deferred (``deleteLater``), and called only once the
        replacement has been asked for, so nothing is destroyed while Qt is still
        dispatching the click that started the reload.
        """
        for instance in instances or ():
            try:
                instance.deleteLater()
            except Exception:  # already gone — nothing to schedule
                pass

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
        match the tags :meth:`build` passes to ``MarkingMenu``, or it reads another host's key.
        """
        try:  # lazy: keeps this module importable without Qt/uitk (see the module docstring)
            from uitk import MarkingMenu

            stored = MarkingMenu.stored_activation_key(context_tags)
        except (
            Exception
        ):  # uitk unavailable or store unreadable — fall back to the default
            stored = None
        return cls.qt_key_name(stored or key_show)

    @staticmethod
    def unserved_tools(context_tags=None):
        """The shared tools no host in *context_tags* serves (``slots.tools.HOSTS``):
        what :meth:`register_shared` leaves out. An empty context (a bare test or
        dev switchboard) serves every tool, uitk's rule for ``requires``.

        Parameters:
            context_tags (iterable): The host's tags (``{"maya"}``), as
                    :meth:`build` hands them to ``MarkingMenu``.

        Returns:
            list: Tool names, sorted.
        """
        # The tools' table, not this class's HOSTS (host -> its probe module).
        from tentacle.slots.tools import HOSTS as TOOL_HOSTS

        context = set(context_tags or ())
        if not context:
            return []
        return sorted(
            tool for tool, hosts in TOOL_HOSTS.items() if not context & set(hosts)
        )

    @staticmethod
    def register_shared(switchboard):
        """Register on *switchboard* what every host shares (CODE_STANDARD section 3).

        ``slots/``: the composed Slots classes, one per category, reaching their host
        through ``Slots.tk``. ``ui/tools/`` and ``slots/tools/``: each tool's ``.ui`` and its
        one Slots class, flat, paired by name, and tagged ``UiHandler.PANEL_TAG`` so a tool
        opens sticky in any host (the hosts' handlers defer to that rule). A tool one host
        serves (``slots.tools.HOSTS``) is left out of the other (:meth:`unserved_tools` of
        the switchboard's ``context_tags``), so nothing there offers it. A tool that took
        over other panels' names (``slots.tools.RENAMED_FROM``) first receives their saved
        values (uitk's ``PanelRenames.carry``, once per host). :meth:`build` calls this,
        so the shared roots are written once.
        """
        from uitk import PanelRenames, UiHandler

        from tentacle.slots.tools import RENAMED_FROM

        PanelRenames.carry(switchboard, RENAMED_FROM)
        root = os.path.dirname(os.path.abspath(__file__))
        slots = os.path.join(root, "slots")
        switchboard.register(slot_location=slots)
        unserved = Tcl.unserved_tools(getattr(switchboard, "context_tags", None))
        switchboard.register(
            ui_location=os.path.join(root, "ui", "tools"),
            slot_location=os.path.join(slots, "tools"),
            tags={UiHandler.PANEL_TAG},
            # "<tool>.*": its .ui from ui/tools and its Slots module from slots/tools.
            exclude=[f"{tool}.*" for tool in unserved] or None,
        )
        Tcl.register_apps(switchboard)

    #: The standalone-apps product tentacle's menus open by name, and the extra
    #: (``tentacletk[apps]``) whose range keeps an installed one in step with
    #: this tentacle (``push.ps1`` ratchets it on each release).
    APPS_DIST = "extapps"
    APPS_EXTRA = "apps"

    @classmethod
    def register_apps(cls, switchboard) -> None:
        """Let *switchboard*'s external-app handler open extapps' apps by name.

        extapps is a product beside tentacle, never its dependency: an installed
        one is found by its entry points, a missing one is offered for install
        on first use, and either way within the range ``tentacletk[apps]``
        declares, so the pair never falls out of step. A source checkout (no
        tentacletk metadata) registers it unranged, so a checkout of extapps on
        the path is still found.
        """
        handler = getattr(getattr(switchboard, "handlers", None), "external_app", None)
        if handler is None:
            return
        import pythontk as ptk

        requirement = ptk.PackageRequirement.declared_by(
            cls.DIST, cls.APPS_DIST, extra=cls.APPS_EXTRA
        )
        handler.add_provider(
            str(requirement) if requirement else cls.APPS_DIST,
            probe_module=cls.APPS_DIST,
        )
        handler.discover()

    @classmethod
    def chord_bindings(cls, key_show=None, chord_target=None):
        """The default chord→menu table for ``key_show`` (bare or Qt-named).

        ``chord_target`` is the both-buttons chord's page — each DCC's own native menu set
        (``'maya#startmenu'`` / ``'blender#startmenu'``, :meth:`build` names it from the host).
        Omitted, that chord is left unbound: binding a gesture to a target that cannot resolve
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

    @staticmethod
    def greeting(string, outputToConsole=True):
        """Format a string using preset variables.

        Parameters:
            string (str): The greeting to format as a string with placeholders using the below keywords.
                    ex. 'Good {hr}! You are using {modver} with {pyver}.'
                    {hr} - Gives the current time of day (morning, afternoon, evening)
                    {pyver} - The python interpreter version.
                    {modver} - This modules version.
            outputToConsole = Print the greeting.

        Returns:
            (str)

        Example: Tcl.greeting('Good {hr}! You are using {modver} with {pyver}.')
        """
        import datetime

        from tentacle import __version__  # tcl.py is bootstrapped BY the package

        h = datetime.datetime.now().hour
        # Before 5 is still the evening, not the afternoon.
        hr = "morning" if 5 <= h < 12 else "afternoon" if 12 <= h < 18 else "evening"

        pyver = "python v{}.{}.{}".format(
            sys.version_info[0], sys.version_info[1], sys.version_info[2]
        )

        modver = "tentacle v{}".format(__version__)

        result = string.format(hr=hr, pyver=pyver, modver=modver)

        if outputToConsole:
            print(result)  # noqa: T201 -- greeting() prints only when asked to
        return result

    @classmethod
    def banner(cls, template=None, force=False):
        """Print the startup banner — the one sanctioned emitter of :meth:`greeting`.

        Lives on the launch path, not at package import: ``import tentacle`` must stay
        side-effect free (root CLAUDE.md), while an actual DCC launch is exactly the moment
        a version/interpreter line is wanted. Never raises — a banner must not be able to
        stop a launch.

        Emits ONCE per process, which is exactly what the retired import-time call gave
        (a module body runs once). That guard is what lets every launch entry point call
        this unconditionally: Blender's add-on entry (``tcl_blender.launch``) banners, and
        the same host reached through :meth:`launch` does not banner twice.

        Parameters:
            template (str): Greeting format string. Defaults to the shipped banner. See
                    :meth:`greeting` for the available placeholders.
            force (bool): Re-emit even if this process already bannered.

        Returns:
            (str)(None): The formatted banner, or None if already emitted or unavailable.
        """
        if cls._BANNERED and not force:
            return None
        try:
            text = cls.greeting(template or cls.BANNER)
        except Exception:  # a banner must never block a launch
            return None
        _TclInternal._BANNERED = (
            True  # set on the base: every subclass shares the latch
        )
        return text

    @classmethod
    def toolkit(cls, host=None):
        """The engine package for *host* (``mayatk`` / ``blendertk``), imported.

        A missing engine raises the ``ImportError`` that names the pip line fixing it
        (:meth:`_import_entry`); a host with no toolkit raises ``RuntimeError``.
        """
        host = host or cls.host()
        name = cls.ENGINES.get(host)
        if name is None:
            raise RuntimeError(f"tentacle: no toolkit for host {host!r}.")
        return cls._import_entry(host, name)

    @classmethod
    def host_adapter(cls, host=None, toolkit=None):
        """A new ``uitk.MarkingMenuHost`` adapter for *host*: its toolkit's
        ``<Host>MarkingMenuHost`` (``mtk.MayaMarkingMenuHost``), named by convention."""
        host = host or cls.host()
        toolkit = toolkit or cls.toolkit(host)
        return getattr(toolkit, f"{host.title()}MarkingMenuHost")()

    @classmethod
    def build(cls, host=None, adapter=None, key_show=None, **kwargs):
        """Build tentacle's marking menu for *host* now, and return it.

        ONE ``uitk.MarkingMenu`` for every host: the host's adapter stands Qt up
        (``start``) and answers what the host does differently; everything else is by
        convention from the host name -- the native-menu pages ``ui/<host>_menus``, the
        both-button chord's ``<host>#startmenu``, the ``{host}`` context tag -- and the
        wiring both hosts share is done here once: the toolkit (``Slots.tk``), the shot
        store's host, the shared Slots and tool panels (:meth:`register_shared`), the
        user's active macro preset.

        Parameters:
            host (str): A :attr:`HOSTS` key; ``None`` resolves the running host.
            adapter: The host's ``uitk.MarkingMenuHost``; ``None`` resolves it
                    (:meth:`host_adapter`).
            key_show (str): DEFAULT activation key (see :meth:`launch`); ``None`` falls
                    back to :attr:`KEY_ENV`, then :attr:`DEFAULT_KEY`, and a key the user
                    persisted outranks all of them (:meth:`resolve_key`).
            **kwargs: Forwarded to ``MarkingMenu`` (``parent``, ``slot_source``,
                    ``log_level``, an explicit ``bindings`` dict, …). A relative
                    ``slot_source`` / ``widget_source`` is relative to this package.

        Returns:
            uitk.MarkingMenu: The menu -- the host's live one when it drives one already
            (``adapter.live_menu()``: Blender's keymap bridge drives one per process), so a
            repeat launch never stacks a second menu over it.

        Raises:
            RuntimeError: No supported DCC detected.
            ImportError: The host's engine is not installed (the message names the fix).
        """
        host = host or cls.host()
        if host is None:
            raise RuntimeError(cls._no_host_message())
        toolkit = cls.toolkit(host)
        adapter = adapter if adapter is not None else cls.host_adapter(host, toolkit)
        live = adapter.live_menu()
        if live is not None:
            return live
        adapter.start()  # Qt usable in this process (Blender provisions it) before any import
        from uitk import ExternalAppHandler, MarkingMenu

        root = os.path.dirname(os.path.abspath(__file__))
        for source in ("slot_source", "widget_source"):
            # Relative to this package, as the per-host subclasses resolved them.
            value = kwargs.get(source)
            if isinstance(value, str) and not os.path.isabs(value):
                kwargs[source] = os.path.join(root, value)

        tags = {host}
        key = cls.resolve_key(key_show or os.environ.get(cls.KEY_ENV), tags)
        bindings = kwargs.pop("bindings", None) or cls.chord_bindings(
            key, f"{host}#startmenu"
        )
        ui = os.path.join(root, "ui")
        kwargs.setdefault("log_level", "WARNING")
        menu = MarkingMenu(
            # The chord menus' pages, and each host's native-menu pages: pure navigation
            # (no Slots class) onto menus the host's UI handler builds the first time the
            # switchboard resolves one.
            ui_source=(ui, os.path.join(ui, f"{host}_menus")),
            bindings=bindings,
            # The host's UI handler (it wraps the host's own menus) comes from the adapter.
            handlers={"external_app": ExternalAppHandler},
            host=adapter,
            suppress_default_on_reentry=True,
            precompile=True,
            # Scoped preloading: once the host's event loop is idle, warm the binding-target
            # startmenus, then the submenus they open, so the FIRST activation and the first
            # hover into each submenu behave like every later one.
            preload=True,
            context_tags=tags,  # `requires` widget filtering
            **kwargs,
        )
        # The toolkit a Slots class shared by both hosts calls (Slots.tk).
        menu.sb.tk = toolkit
        # The shot store's host half, resolved now; a script that skips this entry
        # point gets it from the store, resolved on first call.
        toolkit.ShotStore.running_host()
        # The composed Slots classes and the tool panels both hosts share; the
        # standalone apps are extapps' (Tcl.register_apps, from here), opened by name.
        cls.register_shared(menu.sb)
        # Apply the user's active macro preset so its hotkeys are live immediately --
        # the deterministic source of truth over a rebind made in the host's own hotkey
        # editor, and required on Blender, whose addon keyconfig doesn't outlive the
        # process. No active preset -> a no-op (the shipped 'default' set is empty).
        try:
            toolkit.Macros.apply_saved_macros()
        except Exception as error:  # never let a preset issue block launch
            print(f"# Warning: tentacle: apply_saved_macros failed: {error} #")
        return menu

    @classmethod
    def _no_host_message(cls):
        return (
            "tentacle: no supported DCC host detected (looked for "
            f"{', '.join(cls.HOSTS.values())}). Tcl.launch() must be called from inside "
            "Maya or Blender."
        )

    @classmethod
    def launch(cls, key_show=None, **kwargs):
        """Start tentacle in the host DCC, deferring startup the way that host requires.

        A host with no GUI to build for (:meth:`headless`) is a quiet no-op, decided before
        the toolkit is imported. Otherwise resolves the host's adapter (:meth:`host_adapter`)
        and builds the menu (:meth:`build`) through the adapter's ``defer``: Maya's idle
        queue, Blender's one-shot timer. A toolkit that fails to import is shown where the
        user looks on a host that would hide it (:attr:`STARTUP_ERROR_REPORTERS`: Blender's
        popup) and raised elsewhere.

        Parameters:
            key_show (str): DEFAULT activation key — bare (``'Z'``, ``'Space'``) or Qt-named
                    (``'Key_Z'``). A key the user persisted (shortcut editor / DCC rebind)
                    outranks it. Omitted, :attr:`KEY_ENV` names the default, then
                    :attr:`DEFAULT_KEY`.
            **kwargs: Forwarded to :meth:`build` (``slot_source``, ``log_level``, an explicit
                    ``bindings`` dict, …).

        Returns:
            The marking-menu instance when startup is immediate (a ``mayapy`` with no idle
            queue), else None — a deferred build, a headless host and a reported error
            have nothing to hand back.

        Raises:
            RuntimeError: No supported DCC detected (see :meth:`host`).
            ImportError: The host's engine is not installed (the message names the fix),
                on a host with no startup-error reporter.
        """
        host = cls.host()
        if host is None:
            raise RuntimeError(cls._no_host_message())
        cls.banner()
        if cls.headless(host):
            return None
        try:
            adapter = cls.host_adapter(host)
        except ImportError as error:
            report = cls.STARTUP_ERROR_REPORTERS.get(host)
            if report is None:
                raise
            getattr(cls, report)(error)
            return None
        return adapter.defer(
            lambda: cls.build(host, adapter=adapter, key_show=key_show, **kwargs)
        )

    @classmethod
    def reload(cls):
        """Settings > Reload Scripts: tear tentacle down, reload the ecosystem in
        place and rebuild it, the way the running host requires (the twin of
        :meth:`launch`: ``_reload_maya`` / ``_reload_blender``).

        Returns:
            int: The number of modules reloaded (0 after a Maya reload that failed
            and rebuilt from what was loaded).

        Raises:
            RuntimeError: No supported host, or one with no reload; Blender's
                reload when it fails.
        """
        host = cls.host()
        reload = getattr(cls, f"_reload_{host}", None) if host else None
        if reload is None:
            raise RuntimeError(
                f"tentacle: Reload Scripts runs inside Maya or Blender (host: {host})."
            )
        return reload()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
