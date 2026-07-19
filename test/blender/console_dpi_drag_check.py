# !/usr/bin/python
# coding=utf-8
"""GUI harness + MINIMAL REPRO: a REAL title-bar drag across a monitor DPI boundary
permanently freezes Blender whenever a Qt (PySide6) runtime shares its GUI thread.

The user-reported hard-hang gesture (2026-07-18, razer15: 1920x1080@96dpi primary +
2560x1600@125%/120dpi secondary): title-drag the maximized Blender window (auto-restores
mid-loop) onto the other monitor and grind it into the top Aero-snap zone. Sequence per
leg: maximize on primary -> snap-drag to the secondary's top edge -> drag back down.

SOLVED (2026-07-18) — root cause and fix, after this harness's ~14 runs:

* The freeze was OUR pump. ``processEvents`` from a bpy timer PeekMessage-drains the
  whole thread queue, i.e. it dispatches BLENDER's queued native messages; a WM_TIMER
  delivered inside the DPI transition's nested dispatch (``wglSwapBuffers``/wndproc
  re-entry layers) then pumps from that context and the innermost dispatch never
  returns (py-spy towers: ``test/temp_tests/console_dpi_hang_stack.txt`` original,
  ``dpi_drag_latched_stack2.txt`` with the probe-lie annotated). Every bpy timer stops
  forever while the window still answers ``WM_NULL`` — the OS never flags it.
* Every ``processEvents``-side gate LOST the race and is ruled out: modal-loop flag
  (``GUI_INMOVESIZE`` reads FALSE inside the nested dispatch), a 0.5 s cooldown on it
  (WM_TIMER starves longer), a re-entrancy latch (the nest is GHOST's, not ours),
  ``InSendMessage()`` (NOSEND), deadline-bounded drain (BOUNDED),
  ``AA_PluginApplication`` (QT_PLUGINAPP), ``QT_ENABLE_HIGHDPI_SCALING=0`` (Qt6 no-op),
  QtDock child suspension (reverted separately — it added a blank-console failure mode).
* THE FIX (``tcl_blender._QtHost.start_pump``): never dispatch native messages from the
  pump at all — ``QCoreApplication.sendPostedEvents()`` (+ an explicit DeferredDelete
  flush) delivers everything Qt cannot get from GHOST's own loop, which already
  dispatches every thread window's native messages. With it, ALL legs pass — including
  the previously always-fatal cross-DPI grind — and the Win+Shift+Arrow workaround is
  obsolete. ``first_click_check`` + ``console_dock_check`` prove the Qt UI stays fully
  functional on posted-events-only pumping.
* The "bare QApplication with zero windows" QT_ONLY leg died because it ran its OWN
  ``processEvents`` pump — kept UNFIXED here on purpose: it is the control that proves
  the mechanism (it should still die if run today; factory A0 has no pump and passes).

So: **legs A0/A/B must ALL PASS** — this harness is the regression sentinel for the
pump architecture (a reintroduced ``processEvents`` pump fails legs A/B again).

Soft-wedge detection = bpy tick counter frozen across a 3 s window (the OS hang probes
stay green through this failure, so tick progression is the real liveness signal).
Every check and step checkpoints JSON immediately (a wedged GUI thread can't report).

Env knobs: ``CONSOLE_DPI_ONLY_B=1`` (skip A0/A), ``CONSOLE_DPI_QT_ONLY=1`` (bare
QApplication instead of tentacle), ``CONSOLE_DPI_SKIP_CONSOLE=1`` (no console dock),
``CONSOLE_DPI_REPEATS=N``, ``CONSOLE_DPI_MODE=noglue|nofocus|noboth`` (console-actor
bisect), plus the ruled-out-mitigation switches above (BOUNDED / NOSEND /
QT_PLUGINAPP) kept for re-testing against future Blender/Qt versions.

Run against a *fresh* GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/console_dpi_drag_check.py

Output: test/temp_tests/console_dpi_drag_out.json. Requires >=2 monitors (else N/A).
Steals foreground + the real mouse; throwaway instance only. Windows-only.
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
OUT = os.path.join(TEMP, "console_dpi_drag_out.json")
SANDBOX = os.path.join(TEMP, "console_dpi_drag_state")
MODE = os.environ.get("CONSOLE_DPI_MODE", "full")

_u = _input.user32
GUI_INMOVESIZE = 0x2
R = {"mode": MODE, "checks": [], "steps": []}
_ctx = {}


def _write():
    try:
        os.makedirs(TEMP, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(R, f, indent=2, default=str)
    except Exception:
        pass


def _ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})
    _write()


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def _gui_flags(tid):
    info = _GUITHREADINFO()
    info.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if not _u.GetGUIThreadInfo(wintypes.DWORD(tid), ctypes.byref(info)):
        return 0
    return info.flags


def _monitors():
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
                         bool(info.dwFlags & 1)))
        return True

    _u.EnumDisplayMonitors(None, None, _enum, 0)
    return mons


def _rect(hwnd):
    rect = wintypes.RECT()
    _u.GetWindowRect(ctypes.c_void_p(int(hwnd)), ctypes.byref(rect))
    return [rect.left, rect.top, rect.right, rect.bottom]


def _dpi(hwnd):
    try:
        _u.GetDpiForWindow.restype = wintypes.UINT
        return int(_u.GetDpiForWindow(ctypes.c_void_p(int(hwnd))))
    except Exception:
        return 0


def _probe(hwnd, label):
    SMTO_ABORTIFHUNG = 0x0002
    handle = ctypes.c_void_p(int(hwnd))
    hung = bool(_u.IsHungAppWindow(handle))
    result = ctypes.c_size_t()
    _u.SendMessageTimeoutW.restype = ctypes.c_void_p
    ok = bool(_u.SendMessageTimeoutW(handle, 0, 0, 0, SMTO_ABORTIFHUNG, 3000,
                                     ctypes.byref(result)))
    R["steps"].append({
        "step": label, "os_hung": hung, "wm_null_ok": ok, "rect": _rect(hwnd),
        "dpi": _dpi(hwnd), "gui_ticks": _ctx.get("ticks"),
    })
    _write()
    return not hung and ok


def _ticks_alive(window_s=3.0):
    """True when bpy timers are still turning — THE liveness signal for this failure
    (the OS hang probes stay green while the timer loop is dead)."""
    before = _ctx.get("ticks", 0)
    time.sleep(window_s)
    return _ctx.get("ticks", 0) > before


def _title_drag_to(hwnd, tid, target_x, target_y, leg, label):
    """Real title-bar drag until the cursor is near (target_x, target_y); the grab
    retries once (a press right after a snap/foreground change can miss)."""
    loop_seen = False
    for _attempt in range(2):
        left, top, right, _b = _rect(hwnd)
        x, y = (left + right) // 2, top + 12
        _u.SetCursorPos(x, y)
        time.sleep(0.15)
        _u.mouse_event(_input.MOUSE_MOVE, 1, 1, 0, 0)
        time.sleep(0.03)
        _u.mouse_event(_input.MOUSE_MOVE, -1, -1, 0, 0)
        time.sleep(0.1)
        _u.mouse_event(_input.BTN["L"][0], 0, 0, 0, 0)
        time.sleep(0.15)
        for _ in range(200):
            pt = wintypes.POINT()
            _u.GetCursorPos(ctypes.byref(pt))
            dx = max(-45, min(45, target_x - pt.x))
            dy = max(-45, min(45, target_y - pt.y))
            if abs(dx) <= 2 and abs(dy) <= 2:
                break
            _u.mouse_event(_input.MOUSE_MOVE, dx, dy, 0, 0)
            loop_seen = loop_seen or bool(_gui_flags(tid) & GUI_INMOVESIZE)
            time.sleep(0.025)
        time.sleep(0.15)
        _u.mouse_event(_input.BTN["L"][1], 0, 0, 0, 0)
        if loop_seen:
            break
        time.sleep(0.4)
    R[f"{leg}_{label}_loop_seen"] = loop_seen
    deadline = time.time() + 3.0
    wedged = True
    while time.time() < deadline:
        if not (_gui_flags(tid) & GUI_INMOVESIZE):
            wedged = False
            break
        time.sleep(0.1)
    R[f"{leg}_{label}_move_loop_wedged"] = wedged
    _write()
    time.sleep(0.6)
    return not wedged


def _title_drag_snap_top(hwnd, tid, mon2, leg, label):
    """The run-1 / real-user profile: title-drag (auto-restores a maximized window
    mid-loop), cross the DPI boundary, GRIND in the Aero-snap zone at mon2's top edge
    for ~2 s (cursor pinned at the edge, snap preview showing), then release."""
    left, top, right, _b = _rect(hwnd)
    x, y = (left + right) // 2, top + 12
    _u.SetCursorPos(x, y)
    time.sleep(0.15)
    _u.mouse_event(_input.MOUSE_MOVE, 1, 1, 0, 0)
    time.sleep(0.03)
    _u.mouse_event(_input.MOUSE_MOVE, -1, -1, 0, 0)
    time.sleep(0.1)
    R[f"{leg}_press_time"] = round(time.time(), 3)
    _write()
    _u.mouse_event(_input.BTN["L"][0], 0, 0, 0, 0)
    time.sleep(0.15)
    tx, ty = (mon2[0] + mon2[2]) // 2, mon2[1] + 2
    loop_seen = False
    for _ in range(200):  # travel to the top edge (clamped relative steps)
        pt = wintypes.POINT()
        _u.GetCursorPos(ctypes.byref(pt))
        dx = max(-45, min(45, tx - pt.x))
        dy = max(-45, min(45, ty - pt.y))
        if abs(dx) <= 2 and abs(dy) <= 4:
            break
        _u.mouse_event(_input.MOUSE_MOVE, dx, dy, 0, 0)
        loop_seen = loop_seen or bool(_gui_flags(tid) & GUI_INMOVESIZE)
        time.sleep(0.025)
    for _ in range(40):  # grind in the snap zone ~2s (run 1's oscillation profile)
        _u.mouse_event(_input.MOUSE_MOVE, 1, -2, 0, 0)
        time.sleep(0.025)
        _u.mouse_event(_input.MOUSE_MOVE, -1, -2, 0, 0)
        time.sleep(0.025)
    time.sleep(0.45)
    _u.mouse_event(_input.BTN["L"][1], 0, 0, 0, 0)
    R[f"{leg}_{label}_loop_seen"] = loop_seen
    deadline = time.time() + 3.0
    wedged = True
    while time.time() < deadline:
        if not (_gui_flags(tid) & GUI_INMOVESIZE):
            wedged = False
            break
        time.sleep(0.1)
    R[f"{leg}_{label}_move_loop_wedged"] = wedged
    _write()
    time.sleep(0.8)
    R[f"{leg}_snap_rect"] = _rect(hwnd)
    R[f"{leg}_snap_zoomed"] = bool(_u.IsZoomed(ctypes.c_void_p(int(hwnd))))
    _write()
    return not wedged


def _sequence(hwnd, tid, mon2, primary, leg):
    """The user's gesture: MAXIMIZED on primary -> title-drag (auto-restore) across
    the DPI boundary into mon2's top snap zone -> snap-maximize -> drag back down to
    the primary. OS probes + tick-liveness after each stage; False at first death."""
    handle = ctypes.c_void_p(int(hwnd))
    _u.SetWindowPos(handle, None, primary[0] + 60, primary[1] + 60, 1200, 800,
                    0x0004 | 0x0010)
    time.sleep(0.4)
    _u.ShowWindow(handle, 3)  # SW_MAXIMIZE — the drag must auto-restore mid-loop
    time.sleep(0.8)
    R[leg + "_start_zoomed"] = bool(_u.IsZoomed(handle))
    _probe(hwnd, f"{leg}:start_primary_maximized")

    stages = (
        ("drag_snap_to_mon2_top", lambda: _title_drag_snap_top(
            hwnd, tid, mon2, leg, "drag_snap")),
        ("drag_back_primary", lambda: _title_drag_to(
            hwnd, tid, (primary[0] + primary[2]) // 2,
            (primary[1] + primary[3]) // 2, leg, "drag_back_primary")),
    )
    for label, action in stages:
        action()
        _probe(hwnd, f"{leg}:{label}")
        if not _ticks_alive():
            R[leg + "_timer_loop_died_at"] = label
            R[leg + "_pump_enter"] = _ctx.get("pump_enter")
            R[leg + "_pump_exit"] = _ctx.get("pump_exit")
            _write()
            return False
    return True


def _input_main():
    try:
        hwnd = _ctx["hwnd"]
        tid = _u.GetWindowThreadProcessId(ctypes.c_void_p(int(hwnd)), None)
        mon2, primary = _ctx["mon2"], _ctx["primary"]
        _ctx["fg"] = _input.force_foreground(hwnd, allow_minimize=False)
        _probe(hwnd, "baseline")

        only_b = os.environ.get("CONSOLE_DPI_ONLY_B") == "1"
        if not only_b:
            # --- Leg A0: factory Blender, NO tentacle -------------------------------
            ok = _sequence(hwnd, tid, mon2, primary, "legA0")
            _ck("factory Blender (no tentacle): cross-DPI drag round trip survives",
                ok, f"died_at={R.get('legA0_timer_loop_died_at')}")
            if not ok:
                _ctx["input_done"] = True
                return

        if not _gui_request("launch_tentacle", timeout=30):
            _ck("tentacle launched", False, "request timed out")
            _ctx["input_done"] = True
            return
        if not only_b:
            # --- Leg A: tentacle (Qt pump + marking menu), no console ---------------
            ok = _sequence(hwnd, tid, mon2, primary, "legA")
            _ck("tentacle (no console): cross-DPI drag round trip survives", ok,
                f"died_at={R.get('legA_timer_loop_died_at')}")
            if not ok:
                _ctx["input_done"] = True
                return

        # --- Leg B: console docked ---------------------------------------------------
        repeats = int(os.environ.get("CONSOLE_DPI_REPEATS", "1"))
        if os.environ.get("CONSOLE_DPI_SKIP_CONSOLE") == "1":
            for i in range(repeats):  # Qt host present, NO console docked
                leg = "legQ" if repeats == 1 else f"legQ{i + 1}"
                ok = _sequence(hwnd, tid, mon2, primary, leg)
                _ck(f"Qt host, no console: cross-DPI drag survives ({leg})", ok,
                    f"died_at={R.get(leg + '_timer_loop_died_at')}")
                if not ok:
                    break
            _ctx["input_done"] = True
            return
        if not _gui_request("dock_console", timeout=20):
            _ck("console docked for leg B", False, "request timed out")
            _ctx["input_done"] = True
            return
        for i in range(repeats):
            leg = "legB" if repeats == 1 else f"legB{i + 1}"
            ok = _sequence(hwnd, tid, mon2, primary, leg)
            _ck(f"console docked: cross-DPI drag round trip survives ({leg})", ok,
                f"died_at={R.get(leg + '_timer_loop_died_at')}")
            if not ok:
                break
    except Exception:
        import traceback

        R["input_error"] = traceback.format_exc()
        _write()
    _ctx["input_done"] = True


def _gui_request(kind, timeout):
    _ctx[kind + "_done"] = None
    _ctx["req"] = kind
    deadline = time.time() + timeout
    while _ctx.get(kind + "_done") is None and time.time() < deadline:
        time.sleep(0.1)
    return bool(_ctx.get(kind + "_done"))


def _gui_tick():
    _ctx["ticks"] = _ctx.get("ticks", 0) + 1
    if _ctx.get("input_done"):
        _finish()
        return None
    req = _ctx.pop("req", None)
    if req == "launch_tentacle":
        try:
            if os.environ.get("CONSOLE_DPI_QT_ONLY") == "1":
                # Bisect: bare QApplication + a gated pump — NO tentacle windows,
                # keymaps, or ownership. Does the mere Qt runtime kill the drag?
                # Importing tcl_blender (WITHOUT launch()) provisions the Qt paths
                # via its _QtBootstrap but creates no QApplication and no windows.
                from tentacle import tcl_blender as _tb  # noqa: F401
                from qtpy import QtCore, QtWidgets

                if os.environ.get("CONSOLE_DPI_QT_PLUGINAPP") == "1":
                    QtCore.QCoreApplication.setAttribute(
                        QtCore.Qt.AA_PluginApplication, True
                    )
                    R["qt_pluginapp"] = True
                app = QtWidgets.QApplication.instance()
                if app is None:
                    app = QtWidgets.QApplication(sys.argv or ["blender"])
                _ctx["qt_app"] = app
                kernel32 = ctypes.windll.kernel32
                bounded = os.environ.get("CONSOLE_DPI_BOUNDED") == "1"
                nosend = os.environ.get("CONSOLE_DPI_NOSEND") == "1"
                R["pump_bounded"], R["pump_nosend"] = bounded, nosend

                def _pump():
                    if _gui_flags(kernel32.GetCurrentThreadId()) & GUI_INMOVESIZE:
                        return 0.01
                    # Never pump from inside a sent-message callback: the hang stack
                    # shows this timer firing from a KiUserCallbackDispatcher nest
                    # mid-wglSwapBuffers — dispatching more messages from THERE
                    # re-enters Blender's half-finished paint state.
                    if nosend and _u.InSendMessage():
                        _ctx["pump_skipped_insend"] = (
                            _ctx.get("pump_skipped_insend", 0) + 1)
                        return 0.01
                    # enter/exit stamps: if the loop dies with enter > exit, the
                    # freeze IS a processEvents call that never returned.
                    _ctx["pump_enter"] = time.time()
                    if bounded:
                        # deadline-bounded drain: returns even when the queue never
                        # empties (the post-cross-DPI paint storm) — candidate fix.
                        app.processEvents(QtCore.QEventLoop.AllEvents, 5)
                    else:
                        app.processEvents()
                    _ctx["pump_exit"] = time.time()
                    return 0.01

                bpy.app.timers.register(_pump, persistent=True)
                R["qt_only"] = True
            else:
                from tentacle import tcl_blender as tb

                if tb._KeymapBridge.tcl is None:
                    tb.launch()
            _ctx["launch_tentacle_done"] = True
        except Exception:
            import traceback

            R["launch_error"] = traceback.format_exc()
            _write()
            _ctx["launch_tentacle_done"] = False
    elif req == "dock_console":
        try:
            import shutil

            from blendertk.env_utils import script_output as so

            shutil.rmtree(SANDBOX, ignore_errors=True)
            os.makedirs(SANDBOX, exist_ok=True)
            so.ScriptConsole._state_dir_override = SANDBOX
            inst = so.show()
            dock = inst._dock

            # Guard telemetry — 2026-07-16..18 only. The modal guard was REVERTED (its
            # re-embed racing a Win11 snap-release livelocked Blender and blanked the
            # console; convicted by console_frame_resize_check's guard/noguard A/B), so
            # on current builds these hooks are simply absent and no telemetry records.
            from blendertk.ui_utils.blender_window import BlenderWindow

            if hasattr(dock, "_suspend_embed"):
                orig_susp, orig_res = dock._suspend_embed, dock._resume_embed

                def _susp(_o=orig_susp):
                    R.setdefault("guard_suspends", []).append(round(time.time(), 3))
                    _write()
                    _o()

                def _res(_o=orig_res):
                    R.setdefault("guard_resumes", []).append(round(time.time(), 3))
                    _write()
                    _o()

                dock._suspend_embed, dock._resume_embed = _susp, _res
            if hasattr(BlenderWindow, "modal_move_size_active"):
                orig_active = BlenderWindow.modal_move_size_active

                def _active(_o=orig_active):
                    result = _o()
                    if result and "guard_first_loop_seen" not in R:
                        R["guard_first_loop_seen"] = round(time.time(), 3)
                        _write()
                    return result

                BlenderWindow.modal_move_size_active = staticmethod(_active)

            if MODE in ("noglue", "noboth") and dock._draw_handle is not None:
                dock._space_cls.draw_handler_remove(dock._draw_handle, "WINDOW")
                dock._draw_handle = None
                R["bisect"] = R.get("bisect", "") + " draw-handler-removed"
            if MODE in ("nofocus", "noboth"):
                dock._stop_focus_follow()
                R["bisect"] = R.get("bisect", "") + " focus-follow-stopped"

            def _confirm():
                _ctx["dock_console_done"] = bool(
                    inst.widget is not None and inst._dock.docked
                )
                return None

            bpy.app.timers.register(_confirm, first_interval=0.8)
        except Exception:
            import traceback

            R["dock_error"] = traceback.format_exc()
            _write()
            _ctx["dock_console_done"] = False
    return 0.1


def _go():
    try:
        for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
            _p = str(MONO / _pkg)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        os.environ.setdefault("QT_API", "pyside6")
        # Candidate fix under test: freeze Qt's high-DPI scaling (our embed geometry
        # is pure physical px). Must be set before the QApplication is created.
        if os.environ.get("CONSOLE_DPI_QT_NOSCALE") == "1":
            os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
            R["qt_noscale"] = True

        mons = _monitors()
        R["monitors"] = mons
        primary = next((m for m in mons if m[4]), None)
        second = next((m for m in mons if not m[4]), None)
        if second is None:
            print("console_dpi_drag_check: N/A — only one monitor attached")
            R["verdict"] = "N/A"
            _write()
            _quit()
            return None

        hwnd = _input.main_ghost_hwnd()
        if hwnd is None:
            _ck("GHOST window resolved", False)
            _finish()
            return None
        _ctx.update(hwnd=int(hwnd), mon2=second, primary=primary)
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
    print("console_dpi_drag verdict:", R["verdict"])
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
    print("console_dpi_drag_check: N/A off-Windows")
else:
    bpy.app.timers.register(_go, first_interval=5.0)
