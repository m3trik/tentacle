# !/usr/bin/python
# coding=utf-8
"""Regression guard: the Blender bridge grabs the mouse ONLY for the chord gesture, never for a
plain key-hold — the fix for "Blender menu buttons need several clicks".

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/grab_policy_check.py

Deterministic by design (no injected mouse / hover — those are timing-flaky over GHOST; see
``hover_nav_check.py`` for the input-level demonstration). It drives the genuine bridge entry
point ``tcl_blender._KeymapBridge.drive_press`` and asserts the resulting **mouse-grab owner**,
which is the exact product state the fix turns on:

  * plain key-hold (``buttons=None``)         → overlay must NOT hold the mouse grab. An explicit
                                                 grab here suppressed the child enter/leave events
                                                 hover-nav needs and re-read clicks as the
                                                 ``F12|LeftButton`` chord (the bug).
  * chord (``buttons=LeftButton``)            → overlay SHOULD hold the grab — the shared
                                                 ``_transfer_mouse_control`` establishes it for the
                                                 chord gesture, same as Maya.

Quits itself. Report to stdout and ``../temp_tests/grab_policy_out.txt``.
"""
import sys
import os
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "grab_policy_out.txt")
_lines = []


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _grabber_is_tcl(tcl):
    from qtpy import QtWidgets

    return QtWidgets.QWidget.mouseGrabber() is tcl


def _run():
    from qtpy import QtCore, QtWidgets

    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()
    app = QtWidgets.QApplication.instance()
    results = []
    try:
        # --- plain key-hold: must NOT grab ------------------------------------------------
        tb._KeymapBridge.drive_press()                 # buttons=None (keymap-operator path)
        for _ in range(20):
            app.processEvents()
        keyhold_grabbed = _grabber_is_tcl(tcl)
        _log(f"key-hold (no button): overlay holds grab = {keyhold_grabbed}  (want False)")
        results.append(not keyhold_grabbed)
        tb._KeymapBridge.drive_release()
        for _ in range(20):
            app.processEvents()

        # --- chord (button held at activation): SHOULD grab --------------------------------
        tb._KeymapBridge.drive_press(buttons=QtCore.Qt.LeftButton)
        for _ in range(20):
            app.processEvents()
        chord_grabbed = _grabber_is_tcl(tcl)
        _log(f"chord (LeftButton)  : overlay holds grab = {chord_grabbed}  (want True)")
        results.append(chord_grabbed)
        tb._KeymapBridge.drive_release()
        for _ in range(20):
            app.processEvents()

        ok = all(results)
        _log(f"\nVERDICT: {'PASS — grab only for the chord gesture (Maya parity)' if ok else 'FAIL'}")
    except Exception as error:
        import traceback
        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
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
