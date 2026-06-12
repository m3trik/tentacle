# !/usr/bin/python
# coding=utf-8
"""Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.

Blender is not a Qt app (GHOST event loop, no bundled PySide6), so — unlike Maya, which provides
a live QApplication and whose viewport keystrokes already reach Qt — tentacle must:

  1. **Host** a QApplication itself and pump Qt events from Blender's timer loop
     (:func:`ensure_qapp` / :func:`ensure_blender_widget` / :func:`start_event_pump`).
  2. **Bridge** the activation key: GHOST consumes viewport keystrokes before Qt, so
     ``MarkingMenu``'s ``QShortcut`` never fires. A 3D-View keymap operator calls ``tcl.show(...)``
     instead — wired automatically in :meth:`TclBlender.__init__`, so instantiating ``TclBlender``
     "just works" with the key, the same install model as Maya (no separate add-on to enable).

Usage (inside a running Blender — console, startup script, or add-on)::

    from tentacle import tcl_blender
    tcl_blender.register()            # stand up the host + wire the activation key
    # ...or for a handle: tcl = tcl_blender.launch(); tcl.show("main#startmenu")

Install — exactly like the Maya version: put the monorepo on Blender's Python path (Preferences ▸
File Paths ▸ Scripts, or ``PYTHONPATH`` / ``TENTACLE_MONOREPO``) so ``from uitk import MarkingMenu``
resolves, then call :func:`register` from a startup snippet. Qt itself is handled automatically:
Maya bundles PySide6 (used as-is, never installed), and Blender's Qt-less Python gets PySide6 + qtpy
**pip-installed on first launch** (:func:`_ensure_qt`) — point ``TENTACLE_QT_DEPS`` at a pre-staged
folder to skip the download. This file also carries ``bl_info`` + :func:`register`/:func:`unregister`,
so it doubles as an add-on / Text-Editor ▸ Run-Script target when loaded from its package location.
Env overrides: ``TENTACLE_MONOREPO``, ``TENTACLE_QT_DEPS``, ``TENTACLE_KEY`` (default ``F12`` —
see Preferences ▸ Keymap; the activation key is configurable).

See ``tentacle/docs/BLENDER_PORT_PLAN.md``.
"""
import os
import sys

bl_info = {
    "name": "Tentacle Marking Menu",
    "author": "m3trik",
    "version": (0, 1, 0),
    "blender": (4, 1, 0),
    "location": "3D View ▸ activation key (default F12)",
    "description": "Qt marking menu (tentacle) for Blender — press the activation key in the 3D view.",
    "category": "Interface",
}

# --- Configuration (env-overridable; defaults target the dev box) ----------------------------
_MONOREPO = os.environ.get("TENTACLE_MONOREPO", r"o:\Cloud\Code\_scripts")
_QT_DEPS = os.environ.get("TENTACLE_QT_DEPS")  # optional pre-staged Qt folder (skips on-demand)
_ACTIVATION_KEY = os.environ.get("TENTACLE_KEY", "F12")


def _bootstrap_paths():
    """Put the monorepo packages on ``sys.path`` and pin ``QT_API`` (idempotent).

    Entry-point side effect: this *must* run before the ``from uitk import MarkingMenu`` below —
    ``QT_API`` has to be set before qtpy is first imported, and the monorepo has to be importable
    for the import to resolve. Running it here (not in :func:`register`, which Blender calls only
    *after* importing the module) is what makes this file a self-contained drop-in, mirroring the
    Maya install's "monorepo on the path and you're done". A normal ``import tentacle`` has already
    satisfied these, so every guard below no-ops — matching ``tentacle/__init__.py``'s own
    import-time setup.
    """
    os.environ.setdefault("QT_API", "pyside6")
    for pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        path = os.path.join(_MONOREPO, pkg)
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


# --------------------------------------------------------------------------------------------
# Qt binding provisioning — the asymmetry between Maya and Blender.
# --------------------------------------------------------------------------------------------
# Maya (2025+) *bundles* PySide6, so qtpy resolves a binding with zero setup — and we must NEVER
# pip-install Qt into Maya (it would shadow/clash with the bundled copy). That's also why
# tentacle/uitk deliberately exclude qtpy/PySide from their pyproject ``dependencies``. Blender's
# bundled Python ships *no* Qt, so tentacle has to provide one. ``_ensure_qt`` adds a pre-staged
# folder if you point ``TENTACLE_QT_DEPS`` at one, otherwise pip-installs PySide6 + qtpy into
# Blender's *own* user-modules dir **on first launch** (the on-demand install) — gated on actually
# running inside Blender so a bare interpreter never gets an unsolicited download.
def _qt_importable():
    """True if qtpy can resolve a real Qt binding (Maya's bundled PySide, or Blender's installed one)."""
    try:
        from qtpy import QtWidgets  # noqa: F401

        return True
    except Exception:
        return False


def _qt_install_dir():
    """Where Blender's on-demand Qt deps live. Prefer Blender's *own* per-version user-modules dir
    (``bpy.utils.user_resource('SCRIPTS', 'modules')``) — Blender creates it and already has it on
    ``sys.path`` in a normal launch, so once installed Qt imports with no further wiring, and it's a
    folder the user can see/clear in their Blender profile. Falls back to a non-roaming managed dir
    when bpy isn't importable (the install itself is bpy-gated, so that branch is just the reuse-scan)."""
    try:
        import bpy

        return bpy.utils.user_resource("SCRIPTS", path="modules", create=True)
    except Exception:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "tentacle", "qt_deps", f"py{sys.version_info[0]}{sys.version_info[1]}")


def _blender_python_exe():
    """Blender's bundled Python interpreter (``sys.executable`` is the Blender binary, not python)."""
    for name in ("python.exe", "python3.exe", "python", "python3"):
        exe = os.path.join(sys.prefix, "bin", name)
        if os.path.isfile(exe):
            return exe
    return sys.executable


def _ensure_qt():
    """Make a Qt binding importable; no-op under Maya, on-demand pip-install under Blender."""
    if _qt_importable():  # Maya (bundled) and any already-provisioned interpreter stop here.
        return
    install_dir = _qt_install_dir()
    for target in (_QT_DEPS, install_dir):  # reuse a pre-staged / previously-installed dir
        if target and os.path.isdir(target) and target not in sys.path:
            sys.path.insert(0, target)
    if _qt_importable():
        return
    try:
        import bpy  # noqa: F401 — only auto-install inside Blender, never a bare interpreter
    except Exception:
        return
    if not install_dir:  # user_resource can return "" if the path can't be resolved/created
        return
    import subprocess

    py = _blender_python_exe()
    print(f"tentacle: Blender has no Qt — installing PySide6 + qtpy into {install_dir} (first launch only)…")
    try:
        os.makedirs(install_dir, exist_ok=True)
        subprocess.run([py, "-m", "ensurepip", "--upgrade"], check=False)
        subprocess.check_call(
            [py, "-m", "pip", "install", "--target", install_dir, "PySide6", "qtpy"]
        )
    except Exception as error:
        print(
            f"tentacle: on-demand Qt install failed ({error}). Set TENTACLE_QT_DEPS to a folder "
            "holding PySide6 + qtpy, or pip-install them into Blender's Python."
        )
        return
    if install_dir not in sys.path:
        sys.path.insert(0, install_dir)


_bootstrap_paths()
_ensure_qt()

from qtpy import QtWidgets, QtCore  # noqa: E402  (deferred until paths/Qt are provisioned above)
from uitk import MarkingMenu  # noqa: E402


# --------------------------------------------------------------------------------------------
# Qt host — Blender has no QApplication of its own, so stand one up and pump it from the timer
# loop. ``launch()`` wires these together; idempotent so re-launching reuses the live host.
# --------------------------------------------------------------------------------------------
_PUMP_REGISTERED = False


def ensure_qapp():
    """Return the process QApplication, creating one if Blender has none."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv or ["blender"])
    return app


def ensure_blender_widget(app):
    """Establish ``app.blender_widget`` — the parent for the marking menu.

    A hidden top-level ``QWidget`` (top-level Qt windows over Blender work — Phase 0).
    Native z-order against Blender's own window is handled separately by transient-parenting
    the menu to the GHOST window (:func:`blender_native_window`), not by this widget.
    """
    if getattr(app, "blender_widget", None) is None:
        widget = QtWidgets.QWidget()
        widget.setObjectName("BlenderWindow")
        app.blender_widget = widget
    return app.blender_widget


def blender_native_window():
    """Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication).

    Used as the marking menu's *transient parent* so the OS keeps the overlay stacked above
    Blender natively (an owned window on Windows) instead of relying solely on raise_().
    Light-touch on purpose — no bqt-style ``createWindowContainer`` reparenting, which would
    take ownership of the GHOST window. Returns ``None`` off-Windows or on any failure
    (top-level behavior then continues to work as before).
    """
    app = QtWidgets.QApplication.instance()
    cached = getattr(app, "_blender_native_window", None) if app else None
    if cached is not None:
        return cached
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        from qtpy import QtGui

        user32 = ctypes.windll.user32
        pid = os.getpid()
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _enum(hwnd, _lparam):
            wpid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value == pid and user32.IsWindowVisible(hwnd):
                buf = ctypes.create_unicode_buffer(64)
                user32.GetClassNameW(hwnd, buf, 64)
                if buf.value == "GHOST_WindowClass":
                    found.append(hwnd)
                    return False  # stop enumeration
            return True

        user32.EnumWindows(_enum, 0)
        if not found:
            return None
        window = QtGui.QWindow.fromWinId(int(found[0]))
        if app is not None:
            app._blender_native_window = window
        return window
    except Exception:
        return None


def start_event_pump(app, interval=0.01):
    """Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent)."""
    global _PUMP_REGISTERED
    import bpy

    if _PUMP_REGISTERED:
        return

    def _pump():
        app.processEvents()
        return interval

    bpy.app.timers.register(_pump)
    _PUMP_REGISTERED = True


# --------------------------------------------------------------------------------------------
# Blender keymap bridge
# --------------------------------------------------------------------------------------------
# Maya is a Qt app, so MarkingMenu's ``QShortcut`` (ApplicationShortcut context) catches the
# activation key from anywhere — TclMaya adds nothing. Blender's GHOST owns the keyboard, so that
# shortcut never sees viewport keystrokes. These helpers register one Blender operator + a **3D-View**
# keymap item that calls ``tcl.show(...)``, restoring the "instantiate and the key works" behavior —
# automatically, on construction, with no separate add-on to enable. Scoped to the viewport on
# purpose: a 3D-View region keymap item is evaluated before the global ``Screen`` keymap, so it takes
# the key when the viewport has focus *without* us disabling anyone's global shortcut (F12 still
# renders everywhere else). ``import bpy`` is deferred so importing this module never needs Blender.
_ACTIVE_TCL = None  # the live TclBlender the operator drives (one Qt host per Blender process)
_KEYMAPS = []  # (keymap, keymap_item) pairs we added, for clean removal
_DEBUG = False  # set True to log each activation (helps confirm the keymap is firing live)


# Qt key-name → Blender keymap ``type`` enum. Most keys line up after stripping ``Key_`` and
# upper-casing (``F12``→``F12``, ``A``→``A``, ``SPACE``→``SPACE``); these are the ones that don't —
# notably the Windows/Cmd/Super key, which Qt calls ``Meta``/``Super_L`` and Blender calls ``OSKEY``.
_BLENDER_KEY_ALIASES = {
    "META": "OSKEY", "SUPER_L": "OSKEY", "SUPER_R": "OSKEY",
    "ESCAPE": "ESC", "RETURN": "RET", "ENTER": "RET",
    "CONTROL": "LEFT_CTRL", "ALT": "LEFT_ALT", "SHIFT": "LEFT_SHIFT",
    "PAGEUP": "PAGE_UP", "PAGEDOWN": "PAGE_DOWN", "DELETE": "DEL",
}


def _qt_key_to_blender_type(key_show):
    """Translate a Qt key name (``'Key_F12'`` / ``'Key_Meta'``) to a Blender keymap ``type``
    (``'F12'`` / ``'OSKEY'``). Falls back to the stripped-upper name for keys that already match."""
    name = (key_show or "").replace("Key_", "").upper()
    return _BLENDER_KEY_ALIASES.get(name, name)


def _ensure_show_operator():
    """Register the bridge operator once per process (idempotent)."""
    import bpy

    if hasattr(bpy.types, "TENTACLE_OT_show_marking_menu"):
        return

    class TENTACLE_OT_show_marking_menu(bpy.types.Operator):
        """Show the tentacle Qt marking menu (Blender keymap → Qt bridge)."""

        bl_idname = "tentacle.show_marking_menu"
        bl_label = "Show Tentacle Marking Menu"
        ui_name: bpy.props.StringProperty(default="main#startmenu")

        def execute(self, context):
            # No live menu → tentacle isn't active, so let F12 do its normal thing (CANCELLED
            # passes the event through to Blender's render shortcut). The _DEBUG report distinguishes
            # this ("fired, but no menu") from "keymap never dispatched to us" (nothing at all).
            # NOTE: report() (status bar / Info editor), not print() — a keymap-invoked operator's
            # print() goes to the *system* console (hidden), never the Python Console panel, so the
            # user would see "nothing" whether or not we fired. report() is actually visible.
            if _ACTIVE_TCL is None:
                if _DEBUG:
                    self.report({"WARNING"}, "Tentacle: key fired but no live menu → render")
                return {"CANCELLED"}
            if _DEBUG:
                self.report({"INFO"}, f"Tentacle: key fired → show({self.ui_name})")
            try:
                _ACTIVE_TCL.show(self.ui_name)
            except Exception as error:  # surface in the status bar, never crash Blender
                self.report({"ERROR"}, f"Tentacle: {error}")
                if _DEBUG:
                    print(f"tentacle: show() failed → {error!r}")
            # Blender (GHOST) keeps the OS focus, so nudge the fullscreen overlay to the front and
            # give it keyboard focus — best-effort, never fatal (z-order niceties only).
            for nudge in ("raise_", "activateWindow"):
                try:
                    getattr(_ACTIVE_TCL, nudge)()
                except Exception:
                    pass
            # ALWAYS consume the event once tentacle is active: the user bound F12 to the menu, so
            # it must never fall through to render over the viewport — even if show() errored, they
            # get the menu (or an error message), not a surprise render. (Returning CANCELLED on a
            # show()/raise_() exception was the bug: it passed F12 through to render.render.)
            return {"FINISHED"}

    bpy.utils.register_class(TENTACLE_OT_show_marking_menu)


def _uninstall_keymap():
    """Remove the keymap items added by :func:`_install_keymap`."""
    for km, kmi in _KEYMAPS:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _KEYMAPS.clear()


def _is_bare_press(kmi):
    """True if ``kmi`` is an unmodified PRESS chord (no Ctrl/Alt/Shift/OS/any) — the kind that
    collides with a bare activation key. A modified combo like ``Ctrl+F12`` does not."""
    return kmi.value == "PRESS" and not (
        kmi.any or kmi.ctrl or kmi.alt or kmi.shift or kmi.oskey
    )


def _install_keymap(tcl, key_type, ui_name):
    """Bind ``key_type`` in Blender's **3D View** keymap to the bridge operator so it shows
    ``ui_name`` when the viewport has focus.

    Scoped to the viewport on purpose: a 3D-View region keymap item is evaluated before the global
    ``Screen`` keymap, so it takes the key over the viewport and naturally wins over ``render.render``
    — *without* us disabling anyone's global F12 (it still renders everywhere else). No muting needed.
    """
    import bpy

    global _ACTIVE_TCL
    _ACTIVE_TCL = tcl
    _ensure_show_operator()
    _uninstall_keymap()  # re-launch safe
    kc = bpy.context.window_manager.keyconfigs.addon
    if not (kc and key_type):
        return
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    kmi = km.keymap_items.new("tentacle.show_marking_menu", type=key_type, value="PRESS")
    kmi.properties.ui_name = ui_name
    _KEYMAPS.append((km, kmi))


def _teardown_keymap():
    """Remove the keymap items and unregister the bridge operator (for add-on unregister)."""
    import bpy

    global _ACTIVE_TCL
    _ACTIVE_TCL = None  # the next launch() builds a fresh instance (with a fresh keymap)
    _uninstall_keymap()
    op = getattr(bpy.types, "TENTACLE_OT_show_marking_menu", None)
    if op is not None:
        try:
            bpy.utils.unregister_class(op)
        except Exception:
            pass


# --------------------------------------------------------------------------------------------
class TclBlender(MarkingMenu):
    """Marking Menu class overridden for use with Blender.

    Blender is not a Qt app (GHOST loop, no bundled PySide6), so — unlike Maya — the
    QApplication, the Qt event pump, and the ``blender_widget`` parent are stood up by
    :func:`launch` (the Phase-0-proven recipe) *before* this is constructed.
    See ``tentacle/docs/BLENDER_PORT_PLAN.md``.
    """

    def __init__(
        self, parent=None, slot_source="slots/blender", log_level="WARNING", **kwargs
    ):
        if not parent:
            try:
                parent = self.get_main_window()
            except Exception as error:
                print(f"{__file__}: {error}")

        key_show = kwargs.pop("key_show", "F12")
        key_show = f"Key_{key_show}" if not key_show.startswith("Key_") else key_show

        # Activation key + default UI per chord (mirrors tcl_maya). Global activation
        # ultimately comes from the Blender keymap operator below (GHOST consumes keys
        # before Qt); these also define what show() displays by default.
        bindings = kwargs.pop("bindings", None) or {
            key_show: "hud#startmenu",  # Maya-parity default (hud ported 2026-06-12)
            f"{key_show}|LeftButton": "cameras#startmenu",
            f"{key_show}|MiddleButton": "editors#startmenu",
            f"{key_show}|RightButton": "main#startmenu",
        }

        super().__init__(
            parent,
            ui_source=("ui", "ui/blender_menus"),
            slot_source=slot_source,
            bindings=bindings,
            log_level=log_level,
            suppress_default_on_reentry=True,
            context_tags={"blender"},  # `requires` widget filtering (Phase-5 visibility)
            **kwargs,
        )

        # Bridge the activation key from Blender's keymap to this Qt menu (GHOST owns the
        # keyboard, so MarkingMenu's QShortcut can't fire from the viewport). Automatic on
        # construction — the same install model as Maya; no separate add-on to enable.
        try:
            _install_keymap(
                self,
                _qt_key_to_blender_type(key_show),
                bindings.get(key_show, "main#startmenu"),
            )
        except Exception as error:
            print(f"{__file__}: Blender keymap bridge skipped: {error}")

        # Transient-parent the overlay to Blender's GHOST window so the OS keeps it stacked
        # above Blender natively (owned window). Best-effort — top-level already works.
        try:
            native = blender_native_window()
            if native is not None:
                self.winId()  # force native-window creation so windowHandle() exists
                self.windowHandle().setTransientParent(native)
        except Exception as error:
            print(f"{__file__}: transient-parent skipped: {error}")

    @classmethod
    def get_main_window(cls):
        """Blender parent widget for the marking menu (set by :func:`ensure_blender_widget`).

        Returns ``None`` when unset — the menu then shows as a top-level window, which
        works over Blender (Phase 0). Never raises.
        """
        app = QtWidgets.QApplication.instance()
        return getattr(app, "blender_widget", None) if app is not None else None

    def keyPressEvent(self, event):
        # Ctrl+Z while the menu holds focus -> Blender undo. (The previous stub referenced a
        # non-existent ``self.key_undo``; it never fired because TclBlender was never launched.)
        if not event.isAutoRepeat():
            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            if event.key() == QtCore.Qt.Key_Z and modifiers == QtCore.Qt.ControlModifier:
                try:
                    import bpy

                    bpy.ops.ed.undo()
                except Exception:
                    pass

        super().keyPressEvent(event)


# --------------------------------------------------------------------------------------------
# Launcher + Blender add-on surface
# --------------------------------------------------------------------------------------------
def launch(**kwargs):
    """Stand up the Qt host (QApplication + ``blender_widget`` + event pump) and return a
    :class:`TclBlender` marking-menu instance.

    Idempotent: a repeat call (e.g. re-running :func:`register` from a startup snippet) returns
    the live instance instead of stacking a second marking menu; :func:`unregister` clears it,
    so unregister→register builds fresh. ``**kwargs`` are forwarded to ``TclBlender`` (e.g.
    ``key_show``, ``log_level``) and only take effect when a new instance is built.
    """
    app = ensure_qapp()
    ensure_blender_widget(app)
    start_event_pump(app)
    if _ACTIVE_TCL is not None:  # set by _install_keymap during TclBlender.__init__
        return _ACTIVE_TCL
    return TclBlender(**kwargs)


def register():
    """Blender add-on / startup entry: stand up the host. ``TclBlender`` wires the keymap itself.

    Returns the :func:`diagnose` report (so ``tcl_blender.register()`` typed in the Python Console
    shows the live state right there) and, if anything's wrong, raises a Blender popup — because a
    user running this from the console can't see ``print()`` output (it goes to the hidden *system*
    console, not the Python Console panel)."""
    import bpy

    launch(key_show=_ACTIVATION_KEY)
    report = diagnose()
    if "PROBLEM" in report or "CONFLICT" in report:
        message = report.splitlines()[-1].split(": ", 1)[-1]  # verdict text, minus the "VERDICT :" label
        try:
            bpy.context.window_manager.popup_menu(
                lambda menu, _ctx: menu.layout.label(text=message[:200]),
                title="Tentacle activation", icon="ERROR",
            )
        except Exception:
            pass
    return report


def unregister():
    """Blender add-on teardown: remove the keymap items + bridge operator."""
    _teardown_keymap()


def diagnose():
    """Return (and print) the live activation state — run in Blender's Python console to see why
    the key isn't showing the menu::

        print(tcl_blender.diagnose())

    The returned string is shown right in the Python Console panel (``print()`` alone would land in
    the hidden *system* console). Reports the live module file (a stale/duplicate ``tentacle`` on
    ``sys.path`` is the #1 cause of "nothing happens"), whether the bridge operator is registered,
    whether a live ``TclBlender`` is wired, the keymap item(s) we installed, any *other* active item
    bound to the same bare key in the ``3D View`` keymap (the only thing that could beat us over the
    viewport), and a plain-language VERDICT. Blender's bare-F12 ``render.render`` lives in the global
    ``Screen`` keymap and is evaluated *after* our region item, so it is intentionally not a rival."""
    import bpy

    wm = bpy.context.window_manager
    operator_ok = hasattr(bpy.types, "TENTACLE_OT_show_marking_menu")
    our_active = [kmi for _km, kmi in _KEYMAPS if kmi.active]
    our_keys = {kmi.type for _km, kmi in _KEYMAPS}
    rivals = []
    seen = set()
    # Scan every evaluated config — including ``addon`` (another add-on binding bare F12 in the
    # viewport is a real conflict the clean factory session can't show, so it must be checked too).
    # Dedup by name, not id(): ``active`` often aliases ``user``/``default`` but Blender hands back a
    # fresh Python wrapper each access (distinct id), so id()-dedup would double-list its rivals.
    for kc in (wm.keyconfigs.addon, wm.keyconfigs.user, wm.keyconfigs.active, wm.keyconfigs.default):
        if kc is None or kc.name in seen:
            continue
        seen.add(kc.name)
        # Only a *bare* same-key PRESS in the 3D View keymap could beat us when the viewport has
        # focus — modified combos coexist and the global Screen render shortcut is evaluated after us.
        rivals += [
            f"{kc.name}:{kmi.idname}"
            for km in kc.keymaps if km.name == "3D View"
            for kmi in km.keymap_items
            if kmi.active and kmi.type in our_keys and _is_bare_press(kmi)
            and kmi.idname != "tentacle.show_marking_menu"
        ]

    if not (operator_ok and our_active):
        verdict = ("PROBLEM: activation key not installed — call tcl_blender.register(). If you "
                   "just did, a stale/duplicate tentacle is on sys.path — check 'module file' above.")
    elif _ACTIVE_TCL is None:
        verdict = "PROBLEM: no live menu wired — call tcl_blender.register() (it runs launch())."
    elif rivals:
        verdict = (f"CONFLICT: another 3D View binding {rivals} shares the key and may win — "
                   "disable it, or set TENTACLE_KEY to a different key.")
    else:
        key = next(iter(our_keys), _ACTIVATION_KEY)
        verdict = (f"LIKELY WORKING: '{key}' is bound in the 3D View keymap. Hover the 3D viewport "
                   "and press it. If render still opens, set tcl_blender._DEBUG=True — each fire "
                   "then shows 'Tentacle: key fired' in the status bar (print() output is in the "
                   "hidden system console: Window > Toggle System Console).")

    lines = [
        "=== tentacle Blender activation ===",
        f"module file        : {__file__}",
        f"operator registered: {operator_ok}",
        f"live TclBlender     : {_ACTIVE_TCL!r}",
        f"_DEBUG (logs fires) : {_DEBUG}",
        f"our keymap items    : {[(km.name, kmi.type, kmi.value, kmi.active) for km, kmi in _KEYMAPS]}",
        f"3D View rivals      : {rivals or 'none'}",
        f"VERDICT             : {verdict}",
    ]
    report = "\n".join(lines)
    print(report)
    return report


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
