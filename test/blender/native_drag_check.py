# !/usr/bin/python
# coding=utf-8
"""Manual GUI harness: does dragging a NATIVE Blender window still work with tentacle's Qt
pump running?

A native title-bar drag runs a modal move loop inside GHOST's wndproc; Blender timers still
fire inside it (WM_TIMER), so an ungated ``app.processEvents()`` runs INSIDE the move loop and
Qt's dispatcher PeekMessages the whole thread queue — stealing the drag's WM_MOUSEMOVE /
WM_LBUTTONUP from the modal loop. Symptom: the window can't be repositioned and Blender wedges
("unrecoverable"). The pump must skip ticks while ``GetGUIThreadInfo`` reports a modal
size/move loop.

Run against a *fresh* GUI Blender (never an existing session); self-launches tentacle when the
startup module didn't::

    blender --factory-startup --python tentacle/test/blender/native_drag_check.py

Injects a real title-bar drag (+120 px right). PASS = the window rect moved AND the post-drag
timer still runs (Blender alive) AND Blender quits cleanly. A WEDGED Blender never writes the
output file — the caller's timeout + taskkill handles that. Steals foreground + moves the real
mouse — throwaway instance only.
"""
import sys
import os
import time
import ctypes
import threading
from ctypes import wintypes
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender --python doesn't
import _input  # noqa: E402  (shared Win32 helpers for these harnesses)

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "native_drag_out.txt")

_u = _input.user32
_lines = []
_ctx = {}


def _rect(hwnd):
    rect = wintypes.RECT()
    _u.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def _drag(hwnd):
    """Input thread: real title-bar drag, +120 px right (OS calls only — no bpy)."""
    time.sleep(0.4)
    _ctx["fg"] = _input.force_foreground(hwnd)
    if _u.IsZoomed(hwnd):  # a maximized window doesn't reposition on drag — restore first
        _u.ShowWindow(hwnd, _input.SW_RESTORE)
        time.sleep(0.4)
    _ctx["rect_before"] = _rect(hwnd)  # re-read after any restore
    left, top, right, _bottom = _ctx["rect_before"]
    x, y = (left + right) // 2, top + 12
    _u.SetCursorPos(x, y)
    time.sleep(0.2)
    _u.mouse_event(_input.BTN["L"][0], 0, 0, 0, 0)
    time.sleep(0.15)
    for _step in range(12):  # smooth relative motion the modal loop must track
        _u.mouse_event(_input.MOUSE_MOVE, 10, 0, 0, 0)
        time.sleep(0.05)
    time.sleep(0.15)
    _u.mouse_event(_input.BTN["L"][1], 0, 0, 0, 0)
    cursor = wintypes.POINT()
    _u.GetCursorPos(ctypes.byref(cursor))
    _ctx["cursor_end"] = (cursor.x, cursor.y, "start", x, y)
    _ctx["drag_done"] = True


def _go():
    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    if tb._KeymapBridge.tcl is None:
        tb.launch()

    hwnd = _input.main_ghost_hwnd()
    if hwnd is None:
        _lines.append("PROBE ERROR: no GHOST window")
        _finish()
        return None
    _ctx["hwnd"] = hwnd
    _ctx["rect_before"] = _rect(hwnd)
    _ctx["ticks"] = 0

    def _liveness():  # keeps counting only while Blender's loop is healthy
        _ctx["ticks"] += 1
        return 0.1

    bpy.app.timers.register(_liveness, persistent=True)
    threading.Thread(target=_drag, args=(hwnd,), daemon=True).start()
    bpy.app.timers.register(_finish, first_interval=8.0)
    return None


def _finish():
    rect_after = _rect(_ctx["hwnd"])
    moved = rect_after[:2] != _ctx["rect_before"][:2]
    _lines.append("=== native window drag with Qt pump ===")
    _lines.append(f"fg_ok       : {_ctx.get('fg')}")
    _lines.append(f"drag_done   : {_ctx.get('drag_done', False)}")
    _lines.append(f"rect_before : {_ctx['rect_before']}")
    _lines.append(f"rect_after  : {rect_after}")
    _lines.append(f"cursor      : {_ctx.get('cursor_end')}")
    _lines.append(f"moved       : {moved}")
    _lines.append(f"alive_ticks : {_ctx['ticks']}")
    _lines.append(f"verdict     : {'PASS' if moved and _ctx['ticks'] > 40 else 'FAIL'}")
    report = "\n".join(_lines)
    print(report)
    sys.stdout.flush()
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        f.write(report)
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(_go, first_interval=5.0)
