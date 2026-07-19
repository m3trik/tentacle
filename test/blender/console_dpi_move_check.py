# !/usr/bin/python
# coding=utf-8
"""GUI harness: cross-monitor (different resolution/DPI) move + maximize with the Script
Output console docked — the USER-REPORTED hard-hang gesture (2026-07-18, razer15:
1920x1080 primary + 2048x1280@125% secondary).

Moving Blender's GHOST window to a monitor with a different DPI sends ``WM_DPICHANGED``
to the parent and ``WM_DPICHANGED_AFTERPARENT`` to the embedded WS_CHILD Qt console;
maximizing there forces a full relayout at the new scale while the QtDock draw handler
repositions the child per redraw. Suspected re-entrant geometry fight → hard hang
(user-confirmed: requires kill; current post-rewrite code).

Legs (each step hang-probed from the INPUT thread — ``IsHungAppWindow`` +
``SendMessageTimeout(WM_NULL, SMTO_ABORTIFHUNG)`` — with JSON written after every step,
so a wedged GUI thread still yields an attributable post-mortem for the caller's kill):

* Leg A (control): move -> maximize -> restore -> move back, NO console.
* Leg B: the same sequence with the console docked.

``CONSOLE_DPI_MODE`` env var bisects on later runs: ``full`` (default), ``noglue``
(draw handler removed), ``nofocus`` (focus-follow stopped), ``noboth``.

Run against a *fresh* GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/console_dpi_move_check.py

PASS = no hang at any step + console re-glued after returning to the primary monitor.
Output: test/temp_tests/console_dpi_move_out.json. Requires >=2 monitors (else N/A).
Steals foreground + moves the window — throwaway instance only. Windows-only.
"""
import sys
import os
import time
import json
import ctypes
import threading
from ctypes import wintypes
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
TEMP = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests")
)
OUT = os.path.join(TEMP, "console_dpi_move_out.json")
SANDBOX = os.path.join(TEMP, "console_dpi_move_state")
MODE = os.environ.get("CONSOLE_DPI_MODE", "full")

_u = _input.user32
R = {"mode": MODE, "checks": [], "steps": []}
_ctx = {}


def _ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})


def _write():
    try:
        os.makedirs(TEMP, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(R, f, indent=2, default=str)
    except Exception:
        pass


def _monitors():
    """[(left, top, right, bottom, primary)] physical px, from THIS (DPI-aware) process."""
    mons = []

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    @ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p,
                        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def _enum(hmon, _hdc, _rect, _l):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if _u.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(info)):
            work = info.rcWork
            mons.append((work.left, work.top, work.right, work.bottom,
                         bool(info.dwFlags & 1)))  # MONITORINFOF_PRIMARY
        return True

    _u.EnumDisplayMonitors(None, None, _enum, 0)
    return mons


def _dpi_for_window(hwnd):
    try:
        _u.GetDpiForWindow.restype = wintypes.UINT
        return int(_u.GetDpiForWindow(ctypes.c_void_p(int(hwnd))))
    except Exception:
        return 0


def _rect(hwnd):
    rect = wintypes.RECT()
    _u.GetWindowRect(ctypes.c_void_p(int(hwnd)), ctypes.byref(rect))
    return [rect.left, rect.top, rect.right, rect.bottom]


def _probe(hwnd, label):
    """Hang probe + telemetry; records a step entry and checkpoints the JSON."""
    SMTO_ABORTIFHUNG = 0x0002
    handle = ctypes.c_void_p(int(hwnd))
    hung = bool(_u.IsHungAppWindow(handle))
    result = ctypes.c_size_t()
    _u.SendMessageTimeoutW.restype = ctypes.c_void_p
    ok = bool(_u.SendMessageTimeoutW(handle, 0, 0, 0, SMTO_ABORTIFHUNG, 3000,
                                     ctypes.byref(result)))
    entry = {
        "step": label, "is_hung": hung, "wm_null_ok": ok,
        "rect": _rect(hwnd), "dpi": _dpi_for_window(hwnd),
        "gui_ticks": _ctx.get("ticks"),
    }
    R["steps"].append(entry)
    _write()
    return not hung and ok


def _sequence(hwnd, mon2, leg):
    """Input thread: primary -> monitor2 -> maximize -> restore -> back to primary,
    probing after every transition. Aborts (leaves state as-is) once a hang is seen —
    the post-mortem matters more than cleanup on a wedged instance."""
    x2, y2 = mon2[0] + 60, mon2[1] + 60
    steps = (
        ("moved_to_mon2", lambda: _u.SetWindowPos(
            ctypes.c_void_p(int(hwnd)), None, x2, y2, 1200, 800, 0x0004 | 0x0010)),
        ("maximized_on_mon2", lambda: _u.ShowWindow(ctypes.c_void_p(int(hwnd)), 3)),
        ("restored_on_mon2", lambda: _u.ShowWindow(ctypes.c_void_p(int(hwnd)), 9)),
        ("moved_back_primary", lambda: _u.SetWindowPos(
            ctypes.c_void_p(int(hwnd)), None, 60, 60, 1200, 800, 0x0004 | 0x0010)),
        ("maximized_on_primary", lambda: _u.ShowWindow(ctypes.c_void_p(int(hwnd)), 3)),
        ("restored_on_primary", lambda: _u.ShowWindow(ctypes.c_void_p(int(hwnd)), 9)),
    )
    for label, action in steps:
        action()
        time.sleep(1.5)
        if not _probe(hwnd, f"{leg}:{label}"):
            R[leg + "_hung_at"] = label
            _write()
            return False
    return True


def _input_main():
    try:
        hwnd = _ctx["hwnd"]
        mon2 = _ctx["mon2"]
        _ctx["fg"] = _input.force_foreground(hwnd, allow_minimize=False)

        _probe(hwnd, "baseline")
        ok_a = _sequence(hwnd, mon2, "legA")
        _ck("control: cross-monitor move + maximize with NO console survives", ok_a,
            R.get("legA_hung_at", ""))
        if not ok_a:
            _ctx["input_done"] = True
            return

        _ctx["req"] = "dock_console"
        deadline = time.time() + 20
        while not _ctx.get("console_ready") and time.time() < deadline:
            time.sleep(0.1)
        if not _ctx.get("console_ready"):
            _ck("console docked for leg B", False, "dock request timed out")
            _ctx["input_done"] = True
            return

        ok_b = _sequence(hwnd, mon2, "legB")
        _ck("console docked: cross-monitor move + maximize survives (no hang)", ok_b,
            f"hung_at={R.get('legB_hung_at')}")
        if ok_b:
            _ctx["req"] = "glue_check"
            deadline = time.time() + 10
            while not _ctx.get("glue_done") and time.time() < deadline:
                time.sleep(0.1)
    except Exception:
        import traceback

        R["input_error"] = traceback.format_exc()
        _write()
    _ctx["input_done"] = True


def _gui_tick():
    _ctx["ticks"] = _ctx.get("ticks", 0) + 1
    if _ctx.get("input_done"):
        _finish()
        return None
    req = _ctx.pop("req", None)
    if req == "dock_console":
        try:
            import shutil

            from blendertk.env_utils import script_output as so

            shutil.rmtree(SANDBOX, ignore_errors=True)
            os.makedirs(SANDBOX, exist_ok=True)
            so.ScriptConsole._state_dir_override = SANDBOX
            inst = so.show()
            dock = inst._dock
            if MODE in ("noglue", "noboth") and dock._draw_handle is not None:
                dock._space_cls.draw_handler_remove(dock._draw_handle, "WINDOW")
                dock._draw_handle = None
                R["bisect"] = R.get("bisect", "") + " draw-handler-removed"
            if MODE in ("nofocus", "noboth"):
                dock._stop_focus_follow()
                R["bisect"] = R.get("bisect", "") + " focus-follow-stopped"

            def _confirm():
                _ck("console docked for leg B",
                    inst.widget is not None and inst._dock.docked)
                _write()
                _ctx["console_ready"] = True
                return None

            bpy.app.timers.register(_confirm, first_interval=0.8)
        except Exception:
            import traceback

            R["dock_error"] = traceback.format_exc()
            _write()
            _ctx["console_ready"] = False
            _ctx["input_done"] = True
    elif req == "glue_check":
        try:
            from qtpy import QtWidgets
            from blendertk.env_utils import script_output as so
            from blendertk.ui_utils.blender_window import BlenderWindow

            app = QtWidgets.QApplication.instance()
            for _ in range(10):
                app.processEvents()
            inst = so.ScriptConsole._instance
            region = inst._dock.content_region()
            child = int(inst.widget.winId())
            rect = wintypes.RECT()
            _u.GetWindowRect(ctypes.c_void_p(child), ctypes.byref(rect))
            pt = wintypes.POINT(0, 0)
            _u.ClientToScreen(ctypes.c_void_p(_ctx["hwnd"]), ctypes.byref(pt))
            actual = [rect.left - pt.x, rect.top - pt.y,
                      rect.right - rect.left, rect.bottom - rect.top]
            base = (BlenderWindow.region_client_rect(_ctx["hwnd"], region)
                    if region else None)
            pad = inst._dock._edge_pad
            expected = ([base[0], base[1] + pad, base[2], base[3] - pad]
                        if base else None)
            delta = (max(abs(a - e) for a, e in zip(actual, expected))
                     if expected else 9999)
            _ck("console re-glued after the round trip (<=2px)", delta <= 2,
                f"delta={delta} actual={actual} expected={expected}")
        except Exception:
            import traceback

            R["glue_error"] = traceback.format_exc()
            _ck("console re-glued after the round trip (<=2px)", False, "raised")
        _write()
        _ctx["glue_done"] = True
    return 0.1


def _go():
    try:
        for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
            _p = str(MONO / _pkg)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        os.environ.setdefault("QT_API", "pyside6")

        from tentacle import tcl_blender as tb

        if tb._KeymapBridge.tcl is None:
            tb.launch()

        mons = _monitors()
        R["monitors"] = mons
        second = next((m for m in mons if not m[4]), None)
        if second is None:
            print("console_dpi_move_check: N/A — only one monitor attached")
            R["verdict"] = "N/A"
            _write()
            _quit()
            return None

        hwnd = _input.main_ghost_hwnd()
        if hwnd is None:
            _ck("GHOST window resolved", False)
            _finish()
            return None
        _u.SetWindowPos(ctypes.c_void_p(int(hwnd)), None, 60, 60, 1200, 800,
                        0x0004 | 0x0010)
        _ctx.update(hwnd=int(hwnd), mon2=second)
        _write()
        threading.Thread(target=_input_main, daemon=True).start()
        bpy.app.timers.register(_gui_tick, persistent=True)
    except Exception:
        import traceback

        R["go_error"] = traceback.format_exc()
        _finish()
    return None


def _finish():
    import shutil

    R["verdict"] = ("PASS" if R["checks"] and all(c["pass"] for c in R["checks"])
                    else "FAIL")
    _write()
    shutil.rmtree(SANDBOX, ignore_errors=True)
    print("console_dpi_move verdict:", R["verdict"])
    sys.stdout.flush()
    _quit()
    return None


def _quit():
    windows = bpy.context.window_manager.windows
    if windows:
        with bpy.context.temp_override(window=windows[0]):
            bpy.ops.wm.quit_blender()
    else:
        bpy.ops.wm.quit_blender()


if sys.platform != "win32":
    print("console_dpi_move_check: N/A off-Windows")
else:
    bpy.app.timers.register(_go, first_interval=5.0)
