# !/usr/bin/python
# coding=utf-8
"""Reproduce "works once, then the next press needs repeating" — repeated SAME-action gestures.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/repeat_gesture_check.py

The user reports the marking menu registers an action once, then the *next* time needs several
presses — intermittent, any menu. That's a stateful leak (something stays armed after an action),
which single-shot harnesses miss. This drives the REAL bridge entry points the keymap operator
uses — ``_KeymapBridge.drive_press`` / ``_KeymapBridge.drive_release`` — to run the same leaf click
several times in a row, and snapshots the activation state machine before/after each gesture
(``_activation_key_held``, ``_standalone_suppress``, ``_KeymapBridge.gesture_active``, the mouse-grab owner)
plus whether the click fired on the FIRST try. A degrade on gesture N>1, or state that doesn't
reset between gestures, pins the leak.

Two passes: ``clean_release`` (release fired every time) and ``missed_release`` (release skipped
on alternate gestures — the Blender failure mode where GHOST/region scoping drops the key-up and
only the poller would catch it). Steals foreground + moves the real mouse for a few seconds —
throwaway instance only. Report to stdout and ``../temp_tests/repeat_gesture_out.txt``.
"""
import sys
import os
import time
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "repeat_gesture_out.txt")
_u = _input.user32
_lines = []


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _find(ui, name):
    from qtpy import QtWidgets

    for b in ui.findChildren(QtWidgets.QAbstractButton):
        if b.objectName() == name and b.isVisible() and b.isEnabled():
            return b
    return None


def _state(tcl, tb):
    from qtpy import QtWidgets

    g = QtWidgets.QWidget.mouseGrabber()
    grab = None if g is None else ("tcl" if g is tcl else type(g).__name__)
    return (f"held={tcl._activation_key_held} suppress={tcl._standalone_suppress} "
            f"gesture_active={tb._KeymapBridge.gesture_active} grab={grab} visible={tcl.isVisible()}")


def _gesture(app, tcl, tb, name, center, n, do_release):
    from qtpy import QtWidgets

    _log(f"\n  gesture {n} (release={do_release})")
    _log(f"    pre : {_state(tcl, tb)}")
    _u.SetCursorPos(*center)
    time.sleep(0.05)
    bpy.ops.tentacle.show_marking_menu()          # phase 'press' → _KeymapBridge.drive_press
    for _ in range(20):
        app.processEvents()
    tcl.show("normals#submenu", force=True)
    for _ in range(25):
        app.processEvents()
    ui = tcl.sb.current_ui
    btn = _find(ui, name) if ui else None
    if btn is None:
        _log(f"    SKIP — {name} not found (current_ui={ui.objectName() if ui else None!r})")
        return None
    fired = {"n": 0}
    btn.clicked.connect(lambda *a: fired.__setitem__("n", fired["n"] + 1))
    gp = btn.mapToGlobal(btn.rect().center())
    x, y = int(gp.x()), int(gp.y())
    hit = QtWidgets.QApplication.widgetAt(x, y)
    on_btn = (hit is not None) and (hit.objectName() == name or btn.isAncestorOf(hit))
    _input.click_and_pump(app, x, y)
    first_ok = fired["n"] >= 1
    _log(f"    click: on_button={on_btn} widgetAt={(hit.objectName() if hit else None)!r} "
         f"first_click_fired={first_ok}")
    if do_release:
        bpy.ops.tentacle.show_marking_menu(phase="release")
        for _ in range(20):
            app.processEvents()
    _log(f"    post: {_state(tcl, tb)}")
    return first_ok if on_btn else None


def _run():
    from qtpy import QtWidgets

    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()
    app = QtWidgets.QApplication.instance()
    tb.enable_click_debug()
    geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
    center = (geo.center().x(), geo.center().y())
    try:
        _log("=== PASS A: clean_release (release every gesture) ===")
        a = [_gesture(app, tcl, tb, "b006", center, i, do_release=True) for i in range(1, 5)]
        # reset any residue before pass B
        try:
            tb._KeymapBridge.drive_release()
        except Exception:
            pass
        for _ in range(20):
            app.processEvents()
        _log("\n=== PASS B: missed_release (skip release on even gestures) ===")
        b = [_gesture(app, tcl, tb, "b006", center, i, do_release=(i % 2 == 1)) for i in range(1, 5)]
        _log(f"\nPASS A first-click results: {a}")
        _log(f"PASS B first-click results: {b}")
        degraded = any(v is False for v in (a + b))
        _log(f"VERDICT: {'REPRODUCED — a gesture needed multiple clicks' if degraded else 'all first-clicks fired'}")
    except Exception as error:
        import traceback
        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
        try:
            tb.disable_click_debug()
        except Exception:
            pass
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
    return None


bpy.app.timers.register(_run, first_interval=4.0)
