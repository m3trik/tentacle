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
"""
import sys
import importlib


class _TclInternal:
    """Host detection data + the per-DCC startup mechanics behind :class:`Tcl`."""

    # Default activation key. Bare (no ``Key_`` prefix) — normalized by ``qt_key_name``.
    DEFAULT_KEY = "Z"

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
            from tentacle.tcl_maya import TclMaya

            return TclMaya(**kwargs)

        try:
            from maya.utils import executeDeferred
        except ImportError:  # no idle queue to defer onto — interactive but unusual; build now.
            return build()
        executeDeferred(build)
        return None

    @classmethod
    def _launch_blender(cls, **kwargs):
        """Blender: build on a one-shot timer, through the add-on entry (Qt host + diagnostics)."""
        import bpy

        def build():
            from tentacle import tcl_blender

            tcl_blender.register(**kwargs)
            return None  # a timer returning None is unregistered — one shot, not a poll

        bpy.app.timers.register(build, first_interval=cls.BLENDER_START_DELAY)
        return None

    @staticmethod
    def _launch_max(**kwargs):
        """3ds Max: no deferral needed — its startup scripts already run against a live UI."""
        from tentacle.tcl_max import TclMax

        return TclMax(**kwargs)


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
        except Exception:  # uitk unavailable or store unreadable — fall back to the default
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
        if key_show is not None:
            kwargs["key_show"] = key_show
        return getattr(cls, f"_launch_{host}")(**kwargs)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
