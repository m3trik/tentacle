# !/usr/bin/python
# coding=utf-8
"""Blender add-on entry for tentacle's marking menu: the add-on stub over ``Tcl`` and blendertk.

Blender's add-on contract requires module-scope ``bl_info`` / :func:`register` /
:func:`unregister`; :func:`launch` / :func:`reload` / :func:`diagnose` are the documented console
API. Each forwards to :class:`BlenderHost`, which builds the menu through tentacle's one
launcher (``Tcl.build``, the same ``uitk.MarkingMenu`` every host gets), or to the launcher
itself (:func:`reload` is ``Tcl.reload``, the same reload every host gets), and leaves
Blender's Qt hosting to blendertk (``btk.BlenderMarkingMenuHost`` over ``btk.QtRuntime``,
``btk.KeymapBridge`` and ``btk.BlenderWindow``).

What only this file can own is the path bootstrap (:class:`_Config`): a monorepo checkout's
sibling packages go on ``sys.path`` before blendertk is importable. It runs here, not in the
installer-written startup script, because this file is what a Text-Editor ▸ Run-Script or
``blender --python`` runs, and its own location is what finds the checkout; a pip install
(the installer's route) resolves everything from site-packages and the bootstrap no-ops. Qt is
provisioned on import too (``btk.QtBootstrap.ensure_qt``, for the application named
``Tcl.APP_NAME``: ``btk.HostedApp``), so importing this module is what a Blender harness does
to get a Qt binding.

Usage (inside a running Blender — console, startup script, or add-on)::

    from tentacle import tcl_blender
    tcl_blender.register()            # stand up the host + wire the activation key
    # ...or for a handle: tcl = tcl_blender.launch(); tcl.show("main#startmenu")

Install — exactly like the Maya version (≈ ``userSetup.py``): a module in Blender's user
``scripts/startup`` that puts the **sibling package dirs** (pythontk/uitk/tentacle/blendertk) on
``sys.path`` and then calls :func:`register` (deferred via a one-shot ``bpy.app.timers``). The path
step must cover all siblings *before* ``import tentacle`` — the package ``__init__`` imports
pythontk at the top, so this module's own :meth:`_Config.bootstrap_paths` (and
``TENTACLE_MONOREPO``) runs too late to provide them; the bare two-line snippet above only works
once they resolve. Blender's Qt-less Python gets PySide6 + qtpy **pip-installed on first launch**
— point ``TENTACLE_QT_DEPS`` at a pre-staged folder to skip the download. Env overrides:
``TENTACLE_MONOREPO``, ``TENTACLE_QT_DEPS``, ``TENTACLE_KEY`` (DEFAULT activation key; an explicit
``register(key_show=...)`` names the default over it, ``Tcl.DEFAULT_KEY`` applies when neither is
given, and a key the user persisted — shortcut editor or Preferences ▸ Keymap — outranks all
three; see ``Tcl.resolve_key``).

See ``tentacle/docs/archive/BLENDER_PORT_PLAN.md``.
"""

import os
import sys

bl_info = {
    "name": "Tentacle Marking Menu",
    "author": "m3trik",
    "version": (0, 1, 0),
    "blender": (4, 1, 0),
    "location": "3D View ▸ activation key (default Z)",
    "description": "Qt marking menu (tentacle) for Blender — press the activation key in the 3D view.",
    "category": "Interface",
}


class _Config:
    """Env-overridable configuration (defaults derive from this file's own location) and the
    path bootstrap that must run before blendertk is importable.

    Class attributes rather than module globals so the stub reads one source. The Qt-deps folder
    (``TENTACLE_QT_DEPS``) is ``btk.HostedApp.env("QT_DEPS")``, spelled from ``Tcl.APP_NAME``;
    the default key (``TENTACLE_KEY``) is ``Tcl.KEY_ENV``; the activation-fire log switch is
    ``btk.KeymapBridge.DEBUG``.
    """

    # Where the sibling package dirs (pythontk/uitk/tentacle/blendertk/extapps) live: the explicit
    # ``TENTACLE_MONOREPO`` override, else this file's own checkout
    # (``<root>/tentacle/tentacle/tcl_blender.py`` → ``<root>``) so any clone works unconfigured.
    # No hardcoded fallback — this is a public repo, and a maintainer's drive layout has no business
    # shipping in it; an unresolved root is inert because ``bootstrap_paths`` skips a falsy value and
    # site-packages resolves the imports as usual.
    #
    # The probe is ``<root>/uitk/uitk``, NOT ``<root>/uitk``, because the ``uitk/uitk`` NESTING is
    # what identifies a monorepo checkout: only there does a repo dir hold a package dir of the same
    # name. The three ``dirname`` calls are calibrated for it
    # (``<root>/tentacle/tentacle/tcl_blender.py`` → ``<root>``); under a pip install this file is
    # ``<site-packages>/tentacle/tcl_blender.py``, one level shallower, so ``_SELF_ROOT`` lands on
    # site-packages' PARENT, where neither ``uitk`` nor ``uitk/uitk`` exists and the guard correctly
    # yields "". Probing the flat ``<root>/uitk`` instead would match a plain package dir and put
    # uitk's own submodules (``widgets``, ``managers``, …) on the top-level import path.
    _SELF_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    MONOREPO = os.environ.get("TENTACLE_MONOREPO") or (
        _SELF_ROOT if os.path.isdir(os.path.join(_SELF_ROOT, "uitk", "uitk")) else ""
    )

    @classmethod
    def bootstrap_paths(cls):
        """Put the monorepo packages on ``sys.path`` (idempotent). ``QT_API`` is pinned by
        ``btk.QtBootstrap.ensure_qt``, which runs next."""
        # ``extapps`` rides along so the standalone apps the menus open in process by name (Map
        # Converter / Packer / Compositor + the photogrammetry workflows) import in Blender's own
        # interpreter from a checkout -- Maya gets it from mayapy's site-packages; Blender's bundled
        # Python has no such install, and without it an app's import fails at launch. A sys.path
        # entry, never an import: extapps is a separate product, no tentacle dependency. A
        # pip-installed deployment finds it in site-packages and this path-add simply no-ops (the
        # dir guard below).
        if not cls.MONOREPO:
            return  # not a monorepo checkout (pip install): site-packages already resolves these
        for pkg in ("pythontk", "uitk", "tentacle", "blendertk", "extapps"):
            path = os.path.join(cls.MONOREPO, pkg)
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)


# The import-time side effect that makes this file a self-contained drop-in: the sibling
# packages first (blendertk has to be importable), then a Qt binding (``QT_API`` has to be set
# before qtpy is first imported), provisioned for tentacle: the application blendertk names its
# env vars, its qt_deps folder and its messages after. A normal ``import tentacle`` has already
# satisfied the first two, so their guards no-op.
_Config.bootstrap_paths()

from tentacle.tcl import Tcl  # noqa: E402  (needs bootstrap_paths; stdlib only)

import blendertk as btk  # noqa: E402  (needs bootstrap_paths; lazy resolver)

btk.HostedApp.name = Tcl.APP_NAME
btk.QtBootstrap.ensure_qt()


class BlenderHost:
    """Blender add-on lifecycle: launch / register / unregister. The menu itself is
    ``Tcl.build``'s, its reload ``Tcl.reload``'s and its Qt hosting blendertk's. The thin
    module-level functions below delegate here (Blender's add-on contract requires
    module-scope ``register``/``unregister``; the rest are the documented console API)."""

    @staticmethod
    def launch(**kwargs):
        """Build tentacle's marking menu in Blender now and return it (``Tcl.build``).

        Idempotent: a repeat call (e.g. re-running :meth:`register` from a startup snippet) returns
        the live instance instead of stacking a second marking menu; :meth:`unregister` clears it,
        so unregister→register builds fresh. ``**kwargs`` are forwarded to ``Tcl.build`` (e.g.
        ``key_show``, ``log_level``) and only take effect when a new instance is built.
        """
        Tcl.banner()  # no-op when Tcl.launch already bannered (once-per-process latch)
        # Tcl.build hands back the menu the keymap bridge drives (the adapter's
        # live_menu); there is none after unregister.
        return Tcl.build("blender", **kwargs)

    @staticmethod
    def register(**kwargs):
        """Blender add-on / startup entry: build the menu (:meth:`launch`).

        ``**kwargs`` are forwarded to :meth:`launch` — notably ``key_show``, the DEFAULT
        activation key (bare ``"Z"``-style or Qt ``"Key_Z"``-style); omitted, the
        ``TENTACLE_KEY`` env var applies, then ``Tcl.DEFAULT_KEY`` — and a key the user persisted
        outranks all three (``Tcl.resolve_key``). Only honored when a new instance is built.

        Silent on success — the greeting banner already confirms the load. A PROBLEM/CONFLICT
        in the activation path is printed in full and raised as a Blender popup when the menu
        is built (``btk.BlenderMarkingMenuHost.report_activation``). Returns the report string
        either way; run :func:`diagnose` for it on demand."""
        BlenderHost.launch(**kwargs)
        return btk.ActivationDiagnostics.report(emit=False)

    @staticmethod
    def unregister():
        """Blender add-on teardown: remove the keymap items + bridge operator."""
        btk.KeymapBridge.teardown()


# --------------------------------------------------------------------------------------------
# Module-level surface — Blender's add-on contract requires module-scope ``bl_info`` +
# ``register``/``unregister``; the rest are the documented console API. Each is a thin
# delegator — all logic and state live in the classes.
# --------------------------------------------------------------------------------------------
def launch(**kwargs):
    """Build the marking menu and return it (idempotent). See :meth:`BlenderHost.launch`."""
    return BlenderHost.launch(**kwargs)


def register(**kwargs):
    """Blender add-on / startup entry. See :meth:`BlenderHost.register`."""
    return BlenderHost.register(**kwargs)


def unregister():
    """Blender add-on teardown. See :meth:`BlenderHost.unregister`."""
    return BlenderHost.unregister()


def reload():
    """Reload the tentacle ecosystem in place and rebuild the menu -- the Blender "Reload
    Scripts" (``bpy.ops.script.reload()`` would tear the Qt host down with it). The same reload
    every host gets: ``Tcl.reload``. Returns the number of modules reloaded."""
    return Tcl.reload()


def diagnose():
    """Return (and print) the live activation state. See ``btk.ActivationDiagnostics.report``."""
    return btk.ActivationDiagnostics.report()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    # Text-Editor ▸ Run-Script (or `blender --python tcl_blender.py`) lands here. Make it
    # idempotent: re-running otherwise errors on the already-registered operator.
    try:
        unregister()
    except Exception:
        pass
    register()


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
