# !/usr/bin/python
# coding=utf-8
"""Does the scene_exporter FBX-preset option-box menu open ON TOP and take clicks over Blender?

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/scene_exporter_optionbox_check.py

Regression guard for the live report "the FBX-preset option menu's buttons can't
be pressed" — the FBX Preset row (``cmb000``) lives inside the Settings dropdown
(``cmb008``, a WidgetComboBox popup), and its option-box ☐ opens a ``Menu`` ON
TOP of that popup's grab. CONFIRMED mechanism (this harness, 2026-08-20): Qt 6.8+
removed ``QWidgetWindow``'s remap of mouse events off an older popup, and the
combo's native dropdown keeps the Windows mouse capture — so pre-fix, every press
at the menu's own buttons was delivered into the combo view beneath
(``GetCapture`` = the container throughout; z-order and coordinates were always
correct, which is why the menu LOOKED fine while acting dead / "behind"). Fixed
by uitk ``Menu._ensure_popup_input_grab`` — the window-level grab handoff this
script now pins. See the uitk CHANGELOG 2026-08-20 entries and
``reference_qt68_popup_native_grab`` for the full story.

Two identical attempts are run (the report said the FIRST differed). Each: open
the panel via the live ``tcl.show`` path, real-click ``cmb008`` to open the
Settings dropdown, real-click cmb000's ☐, then probe: menu visible? window type?
top-most at its own center (``WindowFromPoint``)? OS owner chain? native
``GetCapture``? Then real-click ``b007`` with a recorder on its ``clicked``
(the real slot is neutralized so a fired click can't open Explorer mid-run).
PASS = menu on top, ``b007`` fires, capture reads the menu — on both attempts.

Steals foreground + moves the real mouse for ~30 s — throwaway instance only.
Report goes to stdout and ``../temp_tests/scene_exporter_optionbox_out.txt``.
"""
import sys
import os
import ctypes
from ctypes import wintypes
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender --python doesn't
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "scene_exporter_optionbox_out.txt")

_u = _input.user32
_lines = []

GA_ROOT = 2


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _pump(app, n=40):
    for _ in range(n):
        app.processEvents()


def _center(widget):
    gp = widget.mapToGlobal(widget.rect().center())
    return int(gp.x()), int(gp.y())


def _hwnd_at(x, y):
    """Top-most hwnd at screen (x, y), resolved to its root window."""
    _u.WindowFromPoint.restype = ctypes.c_void_p
    hwnd = _u.WindowFromPoint(wintypes.POINT(x, y))
    if not hwnd:
        return 0
    _u.GetAncestor.restype = ctypes.c_void_p
    return int(_u.GetAncestor(ctypes.c_void_p(hwnd), GA_ROOT) or 0)


def _owner_of(hwnd):
    """The OS owner (GWLP_HWNDPARENT) of *hwnd*, 0 when unowned."""
    if not hwnd:
        return 0
    _u.GetWindowLongPtrW.restype = ctypes.c_void_p
    _u.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return int(_u.GetWindowLongPtrW(ctypes.c_void_p(int(hwnd)), -8) or 0)


def _win_name(hwnd, known):
    for name, h in known.items():
        if h and hwnd == h:
            return name
    return hex(hwnd) if hwnd else "0"


def _flags_str(widget):
    from qtpy import QtCore

    t = widget.windowFlags() & QtCore.Qt.WindowType_Mask
    names = {QtCore.Qt.Popup: "Popup", QtCore.Qt.Tool: "Tool",
             QtCore.Qt.Window: "Window", QtCore.Qt.Widget: "Widget"}
    return names.get(t, hex(int(t)))


class _Recorder:
    def __init__(self, btn):
        from qtpy import QtCore

        self.presses = 0
        self.clicks = 0
        btn.clicked.connect(lambda *a: setattr(self, "clicks", self.clicks + 1))
        rec = self

        class _F(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    rec.presses += 1
                return False

        self._filter = _F()
        btn.installEventFilter(self._filter)


class _EventSpy:
    """App-level spy: logs where mouse presses/releases and menu show/hides land."""

    def __init__(self, app):
        from qtpy import QtCore

        self.rows = []
        spy = self
        watched = {QtCore.QEvent.MouseButtonPress: "press",
                   QtCore.QEvent.MouseButtonRelease: "release",
                   QtCore.QEvent.Hide: "hide",
                   QtCore.QEvent.Show: "show"}

        class _F(QtCore.QObject):
            def eventFilter(self, obj, event):
                kind = watched.get(event.type())
                if kind and len(spy.rows) < 60:
                    try:
                        name = obj.objectName() or obj.__class__.__name__
                    except Exception:
                        name = repr(obj)
                    if kind in ("hide", "show") and "Menu" not in type(obj).__name__:
                        return False  # only menu show/hide is interesting
                    host = ""
                    try:  # which top-level the receiver belongs to
                        w = obj.window() if hasattr(obj, "window") else None
                        if w is not None:
                            host = "@" + (w.objectName() or type(w).__name__)
                    except Exception:
                        pass
                    spy.rows.append(f"{kind}:{name}{host}")
                return False

        self._filter = _F()
        self._app = app
        app.installEventFilter(self._filter)

    def stop(self):
        self._app.removeEventFilter(self._filter)
        return self.rows


def _shim_setup_as_popup(log):
    """Class-level shim: log every Menu._setup_as_popup resolution."""
    from uitk.widgets.menu import Menu

    if getattr(Menu, "_orig_setup_as_popup", None):
        return
    Menu._orig_setup_as_popup = Menu._setup_as_popup

    def _shimmed(self):
        before = getattr(self, "_popup_window_type", None)
        resolved = self._resolve_popup_window_type()
        Menu._orig_setup_as_popup(self)
        log(f"    [_setup_as_popup] menu={self.objectName() or id(self)} "
            f"before={before} resolved={int(resolved)} "
            f"after={getattr(self, '_popup_window_type', None)}")

    Menu._setup_as_popup = _shimmed


def _attempt(tcl, app, n):
    from qtpy import QtCore, QtWidgets

    _log(f"\n=== attempt {n} ===")
    sb = tcl.sb

    win = tcl.show("scene_exporter")
    _pump(app)
    if win is None or not win.isVisible():
        _log("  FAIL: scene_exporter window did not show:", repr(win))
        return
    try:
        win.set_pinned(True)
    except Exception:
        pass
    win.move(120, 120)
    win.raise_()
    _pump(app, 20)

    ui = sb.loaded_ui.scene_exporter
    ghost = _input.main_ghost_hwnd()
    known = {"ghost": ghost, "panel": int(win.winId())}

    # Let the first-show layout settle fully before measuring click targets —
    # a combo that moves between press and release closes its own popup.
    _pump(app, 80)

    # Open the Settings dropdown with a real click (re-measure per try).
    cmb008 = ui.cmb008
    view_visible = False
    for attempt_click in range(3):
        x, y = _center(cmb008)
        hit = QtWidgets.QApplication.widgetAt(x, y)
        _log(f"  cmb008 click try {attempt_click + 1}: at=({x},{y}) "
             f"widgetAt={(hit.objectName() or type(hit).__name__) if hit else None} "
             f"hwndAt={_win_name(_hwnd_at(x, y), known)}")
        _input.click_and_pump(app, x, y)
        popup = QtWidgets.QApplication.activePopupWidget()
        view_visible = bool(cmb008.view().isVisible())
        _log(f"    -> dropdown_visible={view_visible} "
             f"activePopup={popup.__class__.__name__ if popup else None}")
        if view_visible:
            break
        _pump(app, 40)
    if not view_visible:
        _log("  FAIL: Settings dropdown never opened")
        return
    if popup is not None:
        known["combo_popup"] = int(popup.window().winId())

    cmb000 = getattr(ui, "cmb000", None)
    if cmb000 is None:
        _log("  FAIL: cmb000 row not found on ui")
        return
    box = cmb000.option_box
    container = box.container
    opt_btn = container.findChild(QtWidgets.QPushButton, "cmb000_MenuOption")
    if opt_btn is None:
        names = [b.objectName() for b in container.findChildren(QtWidgets.QPushButton)]
        _log(f"  FAIL: option ☐ not found; container buttons: {names}")
        return
    _log(f"  option ☐: visible={opt_btn.isVisible()} at={_center(opt_btn)}")

    # Click the ☐ (spy on the event flow it triggers).
    spy = _EventSpy(app)
    _input.click_and_pump(app, *_center(opt_btn))
    _log(f"    event flow: {spy.stop()}")
    menu = box.menu
    menu_hwnd = (int(menu.winId())
                 if menu.testAttribute(QtCore.Qt.WA_WState_Created) else 0)
    known["menu"] = menu_hwnd
    cx, cy = _center(menu)
    top = _hwnd_at(cx, cy)
    fg = _u.GetForegroundWindow()
    grabber = QtWidgets.QWidget.mouseGrabber()
    owner_chain = []
    h = menu_hwnd
    for _ in range(4):
        h = _owner_of(h)
        if not h:
            break
        owner_chain.append(_win_name(h, known))
    _log(f"  after ☐ click: menu_visible={menu.isVisible()} "
         f"type={_flags_str(menu)} resolved={getattr(menu, '_popup_window_type', None)} "
         f"activePopup={type(QtWidgets.QApplication.activePopupWidget()).__name__} "
         f"grabber={(grabber.objectName() or type(grabber).__name__) if grabber else None}")
    _log(f"    menu geo={menu.geometry().getRect()} "
         f"z-order: window at menu center = {_win_name(top, known)} "
         f"(menu on top = {top == menu_hwnd and menu_hwnd != 0})")
    _log(f"    fg={_win_name(int(fg), known)} menu_owner_chain={owner_chain or ['<unowned>']} "
         f"dropdown_still_open={cmb008.view().isVisible()}")

    verdict_top = menu.isVisible() and top == menu_hwnd and menu_hwnd != 0

    # Press b007 inside the menu.
    b007 = getattr(ui, "b007", None)
    fired = None
    if b007 is not None and menu.isVisible():
        rec = _Recorder(b007)
        bx, by = _center(b007)
        hit = QtWidgets.QApplication.widgetAt(bx, by)
        inside = menu.geometry().contains(QtCore.QPoint(bx, by))
        child = menu.childAt(menu.mapFromGlobal(QtCore.QPoint(bx, by)))
        _u.GetCapture.restype = ctypes.c_void_p
        cap = int(_u.GetCapture() or 0)
        _log(f"  b007: at=({bx},{by}) visible={b007.isVisible()} inside_menu_geo={inside} "
             f"widgetAt={(hit.objectName() or type(hit).__name__) if hit else None} "
             f"hwndAt={_win_name(_hwnd_at(bx, by), known)}")
        _log(f"    menu.childAt(click)={(child.objectName() or type(child).__name__) if child else None} "
             f"capture={_win_name(cap, known)} "
             f"dpr={menu.devicePixelRatioF():.2f}")
        spy = _EventSpy(app)
        _input.click_and_pump(app, bx, by)
        _log(f"    event flow: {spy.stop()}")
        fired = rec.clicks > 0
        _log(f"  b007 click: presses={rec.presses} clicked_fired={rec.clicks} "
             f"menu_visible_after={menu.isVisible()}")
    else:
        _log(f"  b007 unreachable: widget={b007!r} menu_visible={menu.isVisible()}")

    # Post-fix behavior: a click inside the dropdown but outside the menu must
    # close the menu and leave the dropdown alive (the stolen grab was handed
    # back); a click outside everything must then dismiss the dropdown.
    from uitk.widgets.separator import Separator

    dropdown_alive = None
    sep = next((s for s in cmb008.view().findChildren(Separator)
                if s.isVisible()), None)
    if sep is not None:
        sx, sy = _center(sep)
        if not menu.frameGeometry().contains(QtCore.QPoint(sx, sy)):
            _input.click_and_pump(app, sx, sy)
            dropdown_alive = cmb008.view().isVisible()
            _log(f"  separator click (in dropdown, outside menu): "
                 f"menu_visible={menu.isVisible()} dropdown_visible={dropdown_alive}")
        else:
            _log("  separator overlaps menu — dropdown-liveness step skipped")
    if cmb008.view().isVisible():
        hx, hy = int(win.x() + 40), int(win.y() + 12)
        _input.click_and_pump(app, hx, hy)
        _log(f"  outside click (panel header): "
             f"dropdown_visible={cmb008.view().isVisible()}")

    _log(f"  VERDICT attempt {n}: menu_on_top={verdict_top} b007_fired={fired} "
         f"dropdown_alive_after_menu_close={dropdown_alive}")

    # Teardown for the next attempt.
    try:
        menu.hide()
        cmb008.hidePopup()
    except Exception:
        pass
    try:
        win.set_pinned(False)
    except Exception:
        pass
    win.hide()
    _pump(app, 20)


def _go():
    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from qtpy import QtWidgets
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()
    app = QtWidgets.QApplication.instance()
    _shim_setup_as_popup(_log)

    # Neutralize the real slot BEFORE the panel is built: a fired b007 would
    # otherwise os.startfile an Explorer window mid-harness. The recorder
    # counts the button's own `clicked` — unaffected by this.
    from blendertk.env_utils.scene_exporter.scene_exporter_slots import (
        SceneExporterSlots,
    )

    SceneExporterSlots.b007 = lambda self: None

    try:
        ghost = _input.main_ghost_hwnd()
        _input.force_foreground(ghost, allow_minimize=False)
        _pump(app, 20)
        _attempt(tcl, app, 1)
        _attempt(tcl, app, 2)
    except Exception as error:
        import traceback

        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
        _finish()
    return None


def _finish():
    report = "\n".join(_lines)
    os.makedirs(os.path.dirname(os.path.normpath(OUT)), exist_ok=True)
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        f.write(report)
    print("\n[written to]", os.path.normpath(OUT))
    sys.stdout.flush()

    def _quit():
        bpy.ops.wm.quit_blender()
        return None

    bpy.app.timers.register(_quit, first_interval=1.0)


bpy.app.timers.register(_go, first_interval=4.0)
