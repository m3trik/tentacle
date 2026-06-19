"""Diagnose WHY the Blender marking menu opens but isn't interactive ("stuck at launch screen").

Launch a fresh GUI Blender (never an existing session)::

    blender --python tentacle/test/blender/menu_interaction_check.py

The activation works (F12 → menu shows), but the menu's interaction is a hold-drag-release state
machine driven by ``_on_activation_press`` / ``_on_activation_release`` (Maya wires these to a Qt
``GlobalShortcut``). The Blender bridge currently calls ``show()`` directly and skips the state
machine, and GHOST keeps OS foreground so the Qt overlay may never get input focus / a working mouse
grab. This reports the live state both ways — ``show()`` vs ``_on_activation_press()`` — plus whether
the overlay is the OS-foreground window and whether forcing it foreground (same-process, allowed) and
grabbing the mouse takes. Read the dump, then fix the bridge accordingly. Windows-only for the hwnd bits.
"""
import sys
import os
import ctypes
from ctypes import wintypes
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender as tb

_u = ctypes.windll.user32 if sys.platform == "win32" else None


def log(*a):
    print(*a)
    sys.stdout.flush()


def _pump(app, n=40):
    for _ in range(n):
        app.processEvents()


def _state(tcl, app):
    from qtpy import QtWidgets

    grabber = QtWidgets.QWidget.mouseGrabber()
    cur = getattr(tcl, "_current_widget", None)
    return {
        "isVisible": bool(tcl.isVisible()),
        "isActiveWindow": bool(tcl.isActiveWindow()),
        "activation_key_held": getattr(tcl, "_activation_key_held", "?"),
        "mouseGrabber_is_self": grabber is tcl,
        "current_widget": cur.objectName() if cur is not None else None,
        "active_ui": (tcl.sb.active_ui.objectName() if tcl.sb.active_ui is not None else None),
    }


def _overlay_hwnd(tcl):
    try:
        return int(tcl.winId())
    except Exception:
        return None


def _run():
    try:
        from qtpy import QtWidgets

        log("=== MENU-INTERACTION ===")
        tb.register()
        tcl = tb._KeymapBridge.tcl
        app = QtWidgets.QApplication.instance()

        # Path A: what the bridge does today — show() directly.
        tcl.show("main#startmenu")
        _pump(app)
        log("after show('main#startmenu'):", _state(tcl, app))

        # Path B: the real Maya entry point — drives the interaction state machine.
        tcl.hide()
        _pump(app)
        tcl._on_activation_press()
        _pump(app)
        log("after _on_activation_press():", _state(tcl, app))

        # OS focus: is the overlay the foreground window, or does GHOST still own it?
        if _u is not None:
            fg = _u.GetForegroundWindow()
            ov = _overlay_hwnd(tcl)
            log(f"foreground hwnd={fg}  overlay hwnd={ov}  overlay_is_foreground={fg == ov}")
            # Same-process SetForegroundWindow is allowed (no cross-process lock) — does it stick?
            if ov:
                _u.SetForegroundWindow(ov)
                _pump(app)
                log(f"after SetForegroundWindow(overlay): isActiveWindow={tcl.isActiveWindow()} "
                    f"foreground_is_overlay={_u.GetForegroundWindow() == ov}")
                # Does an explicit grab take once we're foreground?
                tcl.grabMouse()
                _pump(app, 5)
                log(f"after grabMouse(): mouseGrabber_is_self={QtWidgets.QWidget.mouseGrabber() is tcl}")
                tcl.releaseMouse()

        # Is the start menu actually populated with nav buttons (so clicking COULD navigate)?
        cur = getattr(tcl, "_current_widget", None)
        if cur is not None:
            btns = cur.findChildren(QtWidgets.QAbstractButton)
            log(f"start menu '{cur.objectName()}' button count: {len(btns)}; "
                f"sample: {[b.objectName() or b.text() for b in btns[:6]]}")

            # Decisive: drive navigation the way the menu actually works — grab the mouse, then send a
            # gesture press+release to the MarkingMenu with the real cursor over a nav button. Its
            # mouseReleaseEvent does widgetAt(cursor)→_handle_widget_action, which is the nav path.
            from qtpy import QtCore, QtGui

            nav = next((b for b in btns if b.objectName().startswith("i")), btns[0] if btns else None)
            if nav is not None and _u is not None:
                before = cur.objectName()
                gpos = nav.mapToGlobal(nav.rect().center())
                _u.SetCursorPos(gpos.x(), gpos.y())
                _pump(app, 5)
                if QtWidgets.QWidget.mouseGrabber() is not tcl:
                    tcl.grabMouse()
                for etype, btn_mask in ((QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton),
                                        (QtCore.QEvent.MouseButtonRelease, QtCore.Qt.NoButton)):
                    ev = QtGui.QMouseEvent(etype, QtCore.QPointF(tcl.mapFromGlobal(gpos)),
                                           QtCore.QPointF(gpos), QtCore.Qt.LeftButton, btn_mask,
                                           QtCore.Qt.KeyboardModifier())
                    QtWidgets.QApplication.sendEvent(tcl, ev)
                    _pump(app, 10)
                now = getattr(tcl, "_current_widget", None)
                widget_at = QtWidgets.QApplication.widgetAt(gpos)
                log(f"gesture over '{nav.objectName()}' (widgetAt={widget_at.objectName() if widget_at else None}): "
                    f"current_widget={now.objectName() if now is not None else None} (was {before})")
                if QtWidgets.QWidget.mouseGrabber() is tcl:
                    tcl.releaseMouse()

        # Release detection: re-show, then send the activation-key RELEASE as a Qt key event (the real
        # path — the overlay has focus on key-up, Blender's keymap no longer does). keyReleaseEvent
        # must hide the menu; if it doesn't, the menu stays "stuck open" (the user's report).
        from qtpy import QtCore as _QtCore, QtGui as _QtGui

        tcl._on_activation_press()
        try:
            tcl.grabMouse()
        except Exception:
            pass
        _pump(app)
        log("re-shown for release test:", _state(tcl, app))
        rel = _QtGui.QKeyEvent(_QtCore.QEvent.KeyRelease, tcl._activation_key,
                               _QtCore.Qt.KeyboardModifier())
        QtWidgets.QApplication.sendEvent(tcl, rel)
        _pump(app)
        st = _state(tcl, app)
        log("after synthesized activation-key RELEASE:", st)
        log("RELEASE-HIDES-MENU:", (not st["isVisible"]) and (st["activation_key_held"] is False)
            and (not st["mouseGrabber_is_self"]))
    except Exception as error:
        import traceback

        log("HARNESS ERROR:", repr(error))
        log(traceback.format_exc())
    finally:
        log("=== END ===")
        sys.stdout.flush()
        bpy.app.timers.register(lambda: (bpy.ops.wm.quit_blender(), None)[1], first_interval=0.5)
    return None


bpy.app.timers.register(_run, first_interval=2.5)
