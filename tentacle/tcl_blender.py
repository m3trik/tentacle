# !/usr/bin/python
# coding=utf-8
"""Blender add-on entry for tentacle's Qt marking menu: the add-on surface over blendertk's Qt hosting.

Blender is not a Qt app (GHOST event loop, no bundled PySide6), so — unlike Maya, which provides
a live QApplication and whose viewport keystrokes already reach Qt — the menu needs a Qt host
and a keymap bridge. Both are blendertk's (``btk.QtBootstrap`` / ``btk.QtRuntime`` provision Qt
and pump it from Blender's timers; ``btk.KeymapBridge`` bridges the activation key from the 3D
View keymap; ``btk.BlenderWindow`` owns the native-window helpers). This module keeps what only
tentacle can own:

  * the path bootstrap that puts the sibling packages of a monorepo checkout on ``sys.path``
    BEFORE blendertk is importable (:class:`_Config`) — it runs here because this file is what a
    Text-Editor ▸ Run-Script or ``blender --python`` runs, and its own location is what finds the
    checkout;
  * :class:`TclBlender` — the ``MarkingMenu`` subclass;
  * :class:`BlenderHost` — launch / add-on lifecycle / reload, and the module-level surface
    Blender's add-on contract requires (``bl_info`` / :func:`register` / :func:`unregister`) plus
    the documented console API (:func:`launch` / :func:`reload` / :func:`diagnose`) and the Qt-host
    helpers the Blender harnesses call. Each function forwards to a classmethod.

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
once they resolve. Qt itself is handled automatically: Maya bundles PySide6 (used as-is, never
installed), and Blender's Qt-less Python gets PySide6 + qtpy **pip-installed on first launch**
(``btk.QtBootstrap.ensure_qt``) — point ``TENTACLE_QT_DEPS`` at a pre-staged folder to skip the
download. This file also carries ``bl_info`` + :func:`register`/:func:`unregister`, so it doubles as
an add-on / Text-Editor ▸ Run-Script target when loaded from its package location.
Env overrides: ``TENTACLE_MONOREPO``, ``TENTACLE_QT_DEPS``, ``TENTACLE_KEY`` (DEFAULT activation
key; an explicit ``register(key_show=...)`` names the default over it, ``Tcl.DEFAULT_KEY`` applies
when neither is given, and a key the user persisted — shortcut editor or Preferences ▸ Keymap —
outranks all three; see ``Tcl.resolve_key``).

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
    (``TENTACLE_QT_DEPS``) is ``btk.QtBootstrap.QT_DEPS``; the activation-fire log switch is
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
    # None when unset — the effective default lives once, in ``Tcl.DEFAULT_KEY``, and is applied
    # by ``Tcl.qt_key_name`` at the end of the precedence chain (explicit arg > this > default).
    ACTIVATION_KEY = os.environ.get("TENTACLE_KEY")

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
# before qtpy is first imported). A normal ``import tentacle`` has already satisfied both, so
# every guard no-ops.
_Config.bootstrap_paths()

import blendertk as btk  # noqa: E402  (needs bootstrap_paths; lazy resolver)

btk.QtBootstrap.ensure_qt()

from qtpy import QtWidgets, QtCore  # noqa: E402  (deferred until Qt is provisioned above)
from uitk import MarkingMenu, ExternalAppHandler  # noqa: E402

from tentacle.tcl import Tcl  # noqa: E402  (needs bootstrap_paths)


# --------------------------------------------------------------------------------------------
class TclBlender(MarkingMenu):
    """Marking Menu class overridden for use with Blender.

    Blender is not a Qt app (GHOST loop, no bundled PySide6), so — unlike Maya — the
    QApplication, the Qt event pump, and the ``blender_widget`` parent are stood up by
    :meth:`BlenderHost.launch` (the Phase-0-proven recipe) *before* this is constructed.
    See ``tentacle/docs/archive/BLENDER_PORT_PLAN.md``.
    """

    def __init__(self, parent=None, slot_source=None, log_level="WARNING", **kwargs):
        if not parent:
            try:
                parent = self.get_main_window()
            except Exception as error:
                print(f"{__file__}: {error}")

        # The key the user last CHOSE (persisted) > the named default (explicit argument,
        # then TENTACLE_KEY) > Tcl.DEFAULT_KEY. The persisted rung is what lets a shortcut-editor
        # or Preferences ▸ Keymap rebind survive a restart: Blender's addon keyconfig is rebuilt
        # from scratch every launch, so the store is the only place a Blender-side choice can
        # live. See Tcl.resolve_key.
        key_show = Tcl.resolve_key(
            kwargs.pop("key_show", None) or _Config.ACTIVATION_KEY, {"blender"}
        )

        # Activation key + default UI per chord — the shared table (mirrors tcl_maya). Global
        # activation ultimately comes from the Blender keymap operator below (GHOST consumes keys
        # before Qt); these also define what show() displays by default. The both-button chord is
        # the one fork-specific target: it opens Blender's OWN native menu sets, where Maya wraps
        # its Qt menus. Resolved by the held-button poller, which ORs L+R into the chord mask.
        bindings = kwargs.pop("bindings", None) or Tcl.chord_bindings(
            key_show, "blender#startmenu"
        )

        super().__init__(
            parent,
            ui_source=("ui", "ui/blender_menus"),
            slot_source=slot_source,
            bindings=bindings,
            # BlenderUiHandler wraps Blender's native menus; the shared tools (``ui/tools`` +
            # ``slots/tools``) open through ``marking_menu.show("<tool>")``, as in Maya.
            handlers={"ui": btk.BlenderUiHandler, "external_app": ExternalAppHandler},
            log_level=log_level,
            suppress_default_on_reentry=True,
            # Scoped preloading: once Blender's event loop is idle, warm the
            # binding-target startmenus, then the submenus they open, so the
            # FIRST activation and the first hover into each submenu behave
            # like every later one. The blender#startmenu target resolves like
            # any other page; a host-synthesized target would simply be skipped.
            preload=True,
            context_tags={
                "blender"
            },  # `requires` widget filtering (Phase-5 visibility)
            **kwargs,
        )
        # The toolkit a Slots class shared by both hosts calls (Slots.tk).
        self.sb.tk = btk
        # The shot store's host half, injected here; a script that skips this
        # entry point gets it from the store, resolved on first call.
        btk.ShotStore.set_host(btk.BlenderShotsHost.resolve())
        # The composed Slots classes and the tool panels both hosts share.
        Tcl.register_shared(self.sb)

        # The standalone apps -- the same ones Maya opens -- are extapps', a
        # separate product: Tcl.register_apps (from register_shared, above)
        # names it as the handler's provider within tentacletk[apps]'s range, and
        # the apps self-describe via its entry points, so the category slots open
        # each BY NAME (Slots.launch_app), in a switchboard of its own.
        # ``context_tags={"blender"}`` (above) surfaces the Substance/Marmoset
        # apps here (they're gated out of Maya only).

        # Bridge the activation key from Blender's keymap to this Qt menu (GHOST owns the
        # keyboard, so MarkingMenu's QShortcut can't fire from the viewport). Automatic on
        # construction — the same install model as Maya; no separate add-on to enable.
        # The poller covers what the keymap can't: GHOST eats the key while a mouse button
        # is held (see btk.KeymapBridge.install_poller).
        try:
            btk.KeymapBridge.install_keymap(
                self, btk.KeymapBridge.qt_key_to_blender_type(key_show)
            )
            btk.KeymapBridge.install_poller(self, key_show)
        except Exception as error:
            print(f"{__file__}: Blender keymap bridge skipped: {error}")

        # Apply the user's active macro preset on launch so its hotkeys are live
        # immediately. Essential on Blender: the addon keyconfig only lives for
        # the current process, so — unlike Maya's persisted runtimeCommands —
        # macro bindings must be re-applied every launch (the active-preset name
        # persists via the panel's combo, but the keymap itself does not). This
        # is the ``tentacle_startup.py`` entry point referenced by
        # ``Macros.apply_saved_macros``. No active preset -> a no-op.
        try:
            btk.Macros.apply_saved_macros()
        except Exception as error:  # never let a preset issue block launch
            print(f"{__file__}: apply_saved_macros skipped: {error}")

        # Re-open the Script Output console if it was open when the last session ended
        # (≈ Maya's workspaceControl uiScript restore — Blender has no such hook, so the
        # host calls it explicitly once the Qt host is up). Also starts the
        # stdout/stderr/logging capture, so the console's transcript covers the session
        # even before it's first shown (tentacle_startup.py starts it earlier still,
        # before `import tentacle`, to catch the greeting banner).
        try:
            btk.ScriptConsole.restore()
        except Exception as error:  # never let console restore block launch
            print(f"{__file__}: script_output restore skipped: {error}")

        # Arm the ordered-selection tracker from launch so click order is already
        # recorded when an order-consuming tool (Reorder Selection, ordered transfers)
        # first asks for it — enable() is idempotent and its handler no-ops until the
        # selection actually changes.
        try:
            btk.SelectionOrder.enable()
        except Exception as error:  # never let the tracker block launch
            print(f"{__file__}: SelectionOrder enable skipped: {error}")

        # uitk's cancel strategy for this host (BlenderCancelProvider) is installed
        # by ``BlenderUiHandler`` as it is built, as Maya's is by MayaUiHandler.
        # The entry point pins the slots' ExecutionMonitor interpreter.
        try:
            # Maya's is resolved beside maya.exe by
            # ``AppLauncher.companion_python``. ExecutionMonitor spawns the
            # spinner and the over-threshold dialog as subprocesses, so the
            # interpreter it uses has to be a real python: hand it Blender's
            # bundled one rather than relying on its ``sys.executable``
            # fallback. On 5.1 that fallback happens to be correct already
            # (measured, GUI and background alike: ``sys.executable`` is
            # ``<prefix>/bin/python.exe``), but blendertk supports 4.x, where
            # ``sys.executable`` was the Blender binary — the case
            # ``EnvUtils.python_executable`` exists for. Pinning it explicitly costs
            # nothing and cannot regress with the host's semantics.
            import pythontk as ptk

            ptk.ExecutionMonitor.set_interpreter(btk.EnvUtils.python_executable())
        except Exception as error:  # never let the interpreter pin block launch
            print(f"{__file__}: ExecutionMonitor interpreter skipped: {error}")

        # Own the overlay to Blender's GHOST window so the OS keeps it stacked above Blender.
        self._parent_to_blender(self)

    @classmethod
    def get_main_window(cls):
        """Blender parent widget for the marking menu (set by ``btk.QtRuntime.ensure_widget``).

        Returns ``None`` when unset — the menu then shows as a top-level window, which
        works over Blender (Phase 0). Never raises.
        """
        app = QtWidgets.QApplication.instance()
        return getattr(app, "blender_widget", None) if app is not None else None

    def _parent_to_blender(self, widget):
        """Make ``widget`` an *owned* window of Blender's native GHOST window so the OS keeps it
        stacked above Blender (and minimizes/closes it with Blender) — applied to the overlay AND
        to every standalone tool window the menu opens (see :meth:`_show_window`).

        Blender isn't a Qt app, so a top-level Qt window is otherwise an unrelated OS window: it
        falls behind Blender the moment it loses focus and doesn't move/minimize with it. The Qt
        idiom — ``setTransientParent`` to Blender's GHOST window wrapped as a foreign ``QWindow`` —
        is kept for Qt's own stacking bookkeeping and the non-Windows path, but it does **not** set
        the Windows owner (``GWLP_HWNDPARENT``) for a *foreign* transient parent (verified on PySide6
        6.10), which is the bug that left every Blender tool window unowned. So on Windows the owner
        is set explicitly via ``btk.BlenderWindow.set_owner``. Best-effort: a no-op off-Windows or
        before the GHOST handle is enumerable."""
        try:
            native = (
                btk.BlenderWindow.main_qwindow()
            )  # also caches app._blender_native_hwnd
            if native is None or widget is None:
                return
            widget.winId()  # force native-window creation so windowHandle() exists
            handle = widget.windowHandle()
            if handle is not None:
                handle.setTransientParent(native)
            # Foreign transient parents don't set the OS owner — do it directly (Windows).
            app = QtWidgets.QApplication.instance()
            btk.BlenderWindow.set_owner(
                widget, getattr(app, "_blender_native_hwnd", 0) if app else 0
            )
        except Exception as error:
            # Best-effort z-order nicety; DEBUG-gated so a persistent failure can't spam the console
            # (this runs per tool-window open via _show_window, not just once at construction).
            if btk.KeymapBridge.DEBUG:
                print(f"{__file__}: parent-to-Blender skipped: {error}")

    def _show_window(self, widget, *args, **kwargs):
        """Parent standalone tool windows to Blender too (the overlay is done in ``__init__``)."""
        result = super()._show_window(widget, *args, **kwargs)
        self._parent_to_blender(result if result is not None else widget)
        return result

    def set_activation_key(self, new_key):
        """Rebind the activation key — and move Blender's half of the binding with it.

        The base implementation rewrites the chord table (persisting it) and re-installs the Qt
        ``GlobalShortcut``. Maya needs nothing more, because there that shortcut *is* the binding.
        Here GHOST consumes viewport keystrokes before Qt, so the 3D-View keymap item and the
        poller's virtual-key are what actually open the menu — leave those behind and the Qt side
        rebinds while the viewport goes on answering the old key. Overriding here (rather than at
        each call site) means every route lands on the same path: tentacle's Preferences panel, the
        shortcut editor, and ``btk.KeymapBridge.sync_keymap_rebind`` adopting a Preferences ▸
        Keymap edit."""
        super().set_activation_key(new_key)
        try:
            btk.KeymapBridge.rebind(self, self._activation_key_str)
        except Exception as error:  # a live Qt binding beats no binding — never raise
            print(f"{__file__}: Blender keymap rebind skipped: {error}")

    def _host_mouse_buttons(self):
        # GHOST owns the mouse, so the base Qt query (QApplication.mouseButtons()) is blind to a
        # button held over the viewport. Read the physical state instead so the shared MouseTracking
        # runs its drag-gated track() during a chord gesture — that's what synthesizes the enter
        # events the marking menu's `visible_on_mouse_over` Regions (cameras/editors upper+lower)
        # need to reveal their nav buttons. Without this the regions never appear and the chord
        # submenus "don't launch". Falls back to Qt off-Windows / when nothing is physically held.
        physical = btk.KeymapBridge.physical_mouse_buttons()
        return (
            physical
            if physical != QtCore.Qt.NoButton
            else super()._host_mouse_buttons()
        )

    def showEvent(self, event):
        # Re-assert the GHOST ownership on every show: construction can run before the native
        # Blender window is enumerable, and Qt re-creates the overlay's native window on some
        # flag changes — either silently drops the OS owner (GWLP_HWNDPARENT) that keeps the menu
        # stacked above Blender. Can't gate on ``transientParent()``: Qt keeps recording the
        # transient parent across a native-window recreate even though the OS owner was dropped,
        # so the old gate skipped the re-set and the overlay fell behind Blender. Re-asserting is
        # a cheap idempotent SetWindowLongPtr.
        self._parent_to_blender(self)
        super().showEvent(event)

    def keyPressEvent(self, event):
        # Ctrl+Z while the menu holds focus -> Blender undo. (The previous stub referenced a
        # non-existent ``self.key_undo``; it never fired because TclBlender was never launched.)
        if not event.isAutoRepeat():
            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            if (
                event.key() == QtCore.Qt.Key_Z
                and modifiers == QtCore.Qt.ControlModifier
            ):
                try:
                    import bpy

                    bpy.ops.ed.undo()
                except Exception:
                    pass

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # Release detection lives HERE on the Qt side: once shown, the overlay takes OS keyboard
        # focus, so the activation key's RELEASE arrives as a Qt event (not at Blender's keymap, which
        # no longer has focus) — and the menu's own GlobalShortcut release filter is disarmed because
        # its press never fired (GHOST consumed the key-down). Completing the gesture here is what hides
        # the menu + releases the mouse grab. Idempotent with the Blender RELEASE keymap fallback.
        if not event.isAutoRepeat() and event.key() == self._activation_key:
            try:
                btk.KeymapBridge.drive_release()
            except Exception:
                pass
        super().keyReleaseEvent(event)


class BlenderHost:
    """Launcher + Blender add-on lifecycle coordinator — ties blendertk's Qt runtime and keymap
    bridge to the menu. The thin module-level functions below delegate here (Blender's add-on
    contract requires module-scope ``register``/``unregister``; the rest are the documented console API)."""

    @staticmethod
    def launch(**kwargs):
        """Stand up the Qt host (QApplication + ``blender_widget`` + event pump) and return a
        :class:`TclBlender` marking-menu instance.

        Idempotent: a repeat call (e.g. re-running :meth:`register` from a startup snippet) returns
        the live instance instead of stacking a second marking menu; :meth:`unregister` clears it,
        so unregister→register builds fresh. ``**kwargs`` are forwarded to ``TclBlender`` (e.g.
        ``key_show``, ``log_level``) and only take effect when a new instance is built.
        """
        Tcl.banner()  # no-op when Tcl.launch already bannered (once-per-process latch)
        app = btk.QtRuntime.ensure_qapp()
        btk.QtRuntime.ensure_widget(app)
        btk.QtRuntime.start_pump(app)
        if (
            btk.KeymapBridge.tcl is not None
        ):  # set by install_keymap during TclBlender.__init__
            return btk.KeymapBridge.tcl
        return TclBlender(**kwargs)

    @staticmethod
    def register(**kwargs):
        """Blender add-on / startup entry: stand up the host. ``TclBlender`` wires the keymap itself.

        ``**kwargs`` are forwarded to :meth:`launch` → ``TclBlender`` — notably ``key_show``, the
        DEFAULT activation key (bare ``"Z"``-style or Qt ``"Key_Z"``-style, the same contract as
        ``TclMaya``); omitted, the ``TENTACLE_KEY`` env var applies, then ``Tcl.DEFAULT_KEY`` — and
        a key the user persisted outranks all three (``Tcl.resolve_key``). Only honored when a new
        instance is built — :meth:`launch` is idempotent.

        Silent on success — a routine launch shouldn't announce itself (the greeting banner already
        confirms the load). Only on a PROBLEM/CONFLICT does it print the full ``btk.ActivationDiagnostics.report``
        AND raise a Blender popup (a console user can't see the hidden system-console ``print`` output).
        Returns the full report string either way; run :func:`diagnose` for it on demand."""
        import bpy

        BlenderHost.launch(**kwargs)
        report = btk.ActivationDiagnostics.report(emit=False)
        if "PROBLEM" in report or "CONFLICT" in report:
            print(report)  # something's actually wrong — surface the full diagnostic
            message = report.splitlines()[-1].split(": ", 1)[
                -1
            ]  # verdict text, minus the "VERDICT :" label
            try:
                bpy.context.window_manager.popup_menu(
                    lambda menu, _ctx: menu.layout.label(text=message[:200]),
                    title="Tentacle activation",
                    icon="ERROR",
                )
            except Exception:
                pass
        return report

    @staticmethod
    def unregister():
        """Blender add-on teardown: remove the keymap items + bridge operator."""
        btk.KeymapBridge.teardown()

    @staticmethod
    def reload():
        """Reload the tentacle ecosystem in place and re-register — the Blender "Reload Scripts".

        ``bpy.ops.script.reload()`` would tear down the Qt host with it; this instead tears down
        tentacle's own surface (keymap / operator / poller; blendertk's event pump retires itself via its
        generation token) on top of the shared ``Tcl.prepare_reload``, reloads the monorepo
        packages in dependency order via ``Tcl.reload_packages`` (Qt bindings are never touched),
        and re-registers from the freshly loaded module on the next timer tick — after the stale frames (including the slot that
        called this) have unwound. Returns the number of modules reloaded.
        """
        import importlib

        import bpy

        from tentacle.tcl import Tcl

        # Shared, DCC-agnostic teardown, FIRST — retiring hides the menu (ending any
        # live gesture) while the keymap and poller that drive it are still installed,
        # which is the order the bridge expects. It also retires the activation
        # shortcut, which would otherwise keep servicing the gesture from pre-reload
        # code, and resets blendertk's ScriptJobManager, whose handles to its
        # registered scene callbacks the reload would drop while Blender still holds
        # the callbacks themselves.
        retired = Tcl.prepare_reload("blender")
        btk.KeymapBridge.teardown()
        # Tear down the Script Output console from the OLD module before reloading: its
        # draw-handler glue, liveness watchdog, embedded widget, stdout tee and docked
        # Info Log area would all survive the reload, and the reloaded module's restore()
        # (in TclBlender.__init__) would then dock a SECOND area. teardown() leaves the
        # persisted visible-flag untouched, so the post-reload restore() re-opens it
        # fresh. Guarded via sys.modules — never import during teardown
        # (tentacle_startup.unregister pattern).
        so_mod = sys.modules.get("blendertk.env_utils.script_output")
        if so_mod is not None:
            try:  # attribute access inside the guard — tolerate blendertk version skew
                console = so_mod.ScriptConsole._instance
                if console is not None:
                    console.teardown()
            except Exception:
                pass
        reloaded = Tcl.reload_packages("blender")

        def _re_register():
            try:
                importlib.import_module("tentacle.tcl_blender").register()
            finally:
                Tcl.dispose_retired(retired)
            return None

        bpy.app.timers.register(_re_register, first_interval=0.2)
        return len(reloaded)


# --------------------------------------------------------------------------------------------
# Module-level surface — Blender's add-on contract requires module-scope ``bl_info`` +
# ``register``/``unregister``; the rest are the documented console API + the Qt-host helpers the
# blender test harnesses call. Each is a thin delegator — all logic and state live in the classes.
# --------------------------------------------------------------------------------------------
def ensure_qapp():
    """Return the process QApplication, creating one if Blender has none."""
    return btk.QtRuntime.ensure_qapp()


def ensure_blender_widget(app):
    """Establish ``app.blender_widget`` — the parent for the marking menu."""
    return btk.QtRuntime.ensure_widget(app)


def start_event_pump(app, interval=0.01):
    """Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent)."""
    return btk.QtRuntime.start_pump(app, interval)


def blender_native_window():
    """Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication)."""
    return btk.BlenderWindow.main_qwindow()


def launch(**kwargs):
    """Stand up the Qt host and return a :class:`TclBlender` (idempotent). See :meth:`BlenderHost.launch`."""
    return BlenderHost.launch(**kwargs)


def register(**kwargs):
    """Blender add-on / startup entry. See :meth:`BlenderHost.register`."""
    return BlenderHost.register(**kwargs)


def unregister():
    """Blender add-on teardown. See :meth:`BlenderHost.unregister`."""
    return BlenderHost.unregister()


def reload():
    """Reload the tentacle ecosystem in place and re-register. See :meth:`BlenderHost.reload`."""
    return BlenderHost.reload()


def diagnose():
    """Return (and print) the live activation state. See ``btk.ActivationDiagnostics.report``."""
    return btk.ActivationDiagnostics.report()


def enable_click_debug():
    """Turn on the opt-in click tracer. See ``btk.ClickDebugger.enable``."""
    return btk.ClickDebugger.enable()


def disable_click_debug():
    """Remove the click tracer. See ``btk.ClickDebugger.disable``."""
    return btk.ClickDebugger.disable()


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
