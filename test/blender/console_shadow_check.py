# !/usr/bin/python
# coding=utf-8
"""GUI harness: does the Blender Script Output console (Route 2+) shadow its anchor?

``blendertk.env_utils.script_output.show()`` opens a native, dockable **Info Log window**
(the anchor) and floats a *frameless* ``uitk.ScriptOutput`` skin exactly over its content
region — Blender areas can't host a Qt HWND like Maya's ``workspaceControl``, so the native
window supplies the dock/chrome and Qt supplies the styled content. This pins the whole chain:

* the anchor window opens and the skin is built (Windows + Qt host present);
* the skin's on-screen rect MATCHES the anchor content-region rect — the coordinate transform
  in :class:`blendertk.ui_utils.blender_window.BlenderWindow` (bottom-left→top-left y-flip);
* the skin is OS-owned by the anchor (``GWLP_HWNDPARENT``);
* ``stdout`` + ``logging`` land in the skin and the error line is colored;
* ``close()`` restores ``stdout``, removes the skin, and closes the anchor window.

Run against a *fresh* GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/console_shadow_check.py

PASS = every check true (written to ``test/temp_tests/console_shadow_out.json``). A wedged
Blender never writes the file — the caller's timeout + taskkill handles that. Opens a real
Blender window + a Qt overlay; throwaway instance only. Windows-only (the skin path); on
other platforms the console degrades to the bare native Info Log and this harness is N/A.
"""
import sys
import os
import ctypes
import json
from pathlib import Path

import bpy

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                 "console_shadow_out.json")
)
_u = ctypes.windll.user32
R = {"checks": []}


def _ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})


def _go():
    try:
        from tentacle import tcl_blender as tb
        if tb._KeymapBridge.tcl is None:
            tb.launch()
        from blendertk.env_utils import script_output as so

        R["orig_stdout_id"] = id(sys.stdout)
        R["win_before"] = len(bpy.context.window_manager.windows)
        inst = so.show()
        R["skin_supported"] = so.ScriptConsole._skin_supported()
        _ck("anchor window opened",
            len(bpy.context.window_manager.windows) == R["win_before"] + 1)
        _ck("skin built", inst._skin is not None)
        _ck("stdout redirected", id(sys.stdout) != R["orig_stdout_id"])
        bpy.app.timers.register(_measure, first_interval=0.8)
    except Exception:
        import traceback
        R["go_error"] = traceback.format_exc()
        _finish()
    return None


def _measure():
    try:
        import logging
        from qtpy import QtWidgets
        from blendertk.env_utils import script_output as so
        from blendertk.ui_utils.blender_window import BlenderWindow

        inst = so.ScriptConsole._instance
        app = QtWidgets.QApplication.instance()

        print("Result: console verification print")
        logging.getLogger("console_check").error("boom from logging")
        inst._sync_geometry()
        app.processEvents()
        skin = inst._skin

        g = skin.geometry()
        actual = [g.x(), g.y(), g.width(), g.height()]
        region = inst._anchor_content_region()
        expected = BlenderWindow.region_screen_rect(inst._anchor_hwnd, region, dpr=1.0)
        R["skin_geometry"], R["expected_rect"] = actual, list(expected) if expected else None
        if expected:
            delta = max(abs(a - e) for a, e in zip(actual, expected))
            _ck("skin shadows anchor region (<=2px)", delta <= 2,
                f"delta={delta} actual={actual} expected={list(expected)}")
        else:
            _ck("skin shadows anchor region (<=2px)", False, "no region")

        _u.GetWindowLongPtrW.restype = ctypes.c_void_p
        _u.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        owner = _u.GetWindowLongPtrW(ctypes.c_void_p(int(skin.winId())), -8)
        _ck("skin OS-owned by anchor", int(owner or 0) == int(inst._anchor_hwnd or -1),
            f"owner={owner} anchor={inst._anchor_hwnd}")

        text = skin.toPlainText()
        _ck("print reached console", "console verification print" in text)
        _ck("logging reached console", "boom from logging" in text)

        skin.highlighter.rehighlight(); app.processEvents()
        colors = set()
        blk = skin.document().begin()
        while blk.isValid():
            if "ERROR" in blk.text() or "boom" in blk.text():
                for fr in blk.layout().formats():
                    c = fr.format.foreground().color()
                    colors.add((c.red(), c.green(), c.blue()))
            blk = blk.next()
        _ck("error line colored red (165,75,75)", (165, 75, 75) in colors, str(colors))
        _ck("skin visible", skin.isVisible())

        bpy.app.timers.register(_teardown, first_interval=0.5)
    except Exception:
        import traceback
        R["measure_error"] = traceback.format_exc()
        _finish()
    return None


def _teardown():
    try:
        from blendertk.env_utils import script_output as so
        inst = so.ScriptConsole._instance
        wc_before = len(bpy.context.window_manager.windows)
        inst.close()
        _ck("stdout restored on close", id(sys.stdout) == R.get("orig_stdout_id"))
        _ck("skin removed on close", inst._skin is None)
        _ck("anchor window closed on close",
            len(bpy.context.window_manager.windows) == wc_before - 1)
    except Exception:
        import traceback
        R["teardown_error"] = traceback.format_exc()
    _finish()
    return None


def _finish():
    R["verdict"] = "PASS" if R["checks"] and all(c["pass"] for c in R["checks"]) else "FAIL"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, default=str)
    print("console_shadow verdict:", R["verdict"])
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()


if sys.platform != "win32":
    print("console_shadow_check: N/A off-Windows (console degrades to native Info Log)")
else:
    bpy.app.timers.register(_go, first_interval=5.0)
