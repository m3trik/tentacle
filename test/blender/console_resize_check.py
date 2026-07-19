# !/usr/bin/python
# coding=utf-8
"""GUI harness: does resizing the NATIVE Blender window still work with the Script Output
console docked?

A native border drag runs a modal size loop inside GHOST's wndproc (same loop family as the
title-bar drag ``native_drag_check.py`` pins). Blender timers still fire inside it
(WM_TIMER) — which is why tentacle's Qt pump and key watcher skip their tick while
``GetGUIThreadInfo`` reports ``GUI_INMOVESIZE``. The docked console adds three actors that
run INSIDE that loop with no such gate:

* the QtDock draw handler → ``SetWindowPos`` on the embedded Qt child (every redraw — i.e.
  every mouse move of the drag);
* the 20 Hz focus-follow tick → ``GetFocus``/``SetFocus`` flips;
* the 0.5 s liveness watchdog (reads only — expected harmless).

Symptom under test: the Blender window freezes / becomes unresponsive when resized while
the console is docked. This harness measures it directly:

* **Leg A (control)** — bottom-border resize drag with NO console docked: must work.
* **Leg B** — the same drag with the console docked (its strip is the bottom of the
  window, so the drag drives the exact glue path).
* **Leg C** — right-border drag (width change → full document re-layout in the child).
* **Legs D0/D** — AREA-SPLITTER drag of the console strip's top border (D0 = cold, D =
  after hovering the console so the focus-follow poll holds the keys). Blender's
  ``area_move`` MODAL OPERATOR, not a native size loop — none of the modal-loop gates
  apply here.
* **Legs F/F2** — programmatic ``screen.area_move`` on the strip's edge vs a native
  edge. NOTE: exec-mode ``area_move`` proved a no-op even on healthy native edges, so
  these two are diagnostic only — a real drag (G/H) is the ground truth.
* **Leg G** — the same real drag on a NATIVE edge (outliner/properties): validates the
  input technique in-run.
* **Leg H** — a BARE ``dock_editor`` strip (console hidden, no Qt child): isolates the
  strip itself from the embed.
* **Leg E** — maximize + restore with the console docked (instantaneous size jumps).

**Expected status while the mid-session dead-border bug is OPEN** (see the blendertk
probes ``test/temp_tests/dock_heal_check.py`` / ``dock_settle_variants_check.py``): the
no-wedge/no-hang and glue checks all PASS, but the splitter legs (D0/D), F, H, and the
hide→show re-dock check FAIL — any ``dock_editor`` strip docked MID-SESSION has a border
Blender's edge hit-test cannot find (no resize cursor, drags ignored), while a strip
docked at STARTUP (console ``restore()``) resizes fine. The overall verdict stays FAIL
until that bug is fixed; regressions show as NEW failing checks (wedges, hangs, glue).

Every leg's input thread also runs the canonical OS hang probes after its gesture —
``IsHungAppWindow`` + ``SendMessageTimeout(WM_NULL, SMTO_ABORTIFHUNG)`` — which stay
meaningful even when bpy timers stop ticking.

Each leg's input thread injects a REAL border drag, then polls ``GetGUIThreadInfo`` of the
GUI thread: ``GUI_INMOVESIZE`` still set 3 s after the mouse-up = the modal loop never saw
the release = WEDGED (the documented pump-in-modal-loop failure). Results are checkpointed
to JSON after every leg, so a run the caller had to ``taskkill`` still shows which leg
died. Liveness ticks + max tick gap catch the stall flavor as well as the hard wedge.

``CONSOLE_RESIZE_MODE`` env var bisects the mechanism on later runs:
``full`` (default — console as shipped), ``noglue`` (draw handler removed),
``nofocus`` (focus-follow stopped), ``noboth``.

Run against a *fresh* GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/console_resize_check.py

Output: ``test/temp_tests/console_resize_out.json``. Steals foreground + moves the real
mouse — throwaway instance only. Windows-only.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # Blender --python doesn't
import _input  # noqa: E402  (shared Win32 helpers for these harnesses)

MONO = Path(__file__).resolve().parents[3]
TEMP = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests")
)
OUT = os.path.join(TEMP, "console_resize_out.json")
SANDBOX = os.path.join(TEMP, "console_resize_state")
MODE = os.environ.get("CONSOLE_RESIZE_MODE", "full")  # full | noglue | nofocus | noboth

_u = _input.user32
GUI_INMOVESIZE = 0x2
VK_ESCAPE = 0x1B
R = {"mode": MODE, "checks": [], "counters": {}}
_ctx = {}


def _ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})


def _write_json():
    """Checkpoint results — called after every leg AND from the input thread on a wedge,
    so a run the caller must kill still tells which leg died."""
    try:
        os.makedirs(TEMP, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(R, f, indent=2, default=str)
    except Exception:
        pass


def _rect(hwnd):
    rect = wintypes.RECT()
    _u.GetWindowRect(ctypes.c_void_p(int(hwnd)), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def _gui_flags(thread_id):
    """GetGUIThreadInfo flags for ``thread_id`` (0 on failure) — readable from ANY thread,
    unlike tentacle's ``native_modal_loop_active`` which probes the CALLING thread."""
    info = _GUITHREADINFO()
    info.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if not _u.GetGUIThreadInfo(wintypes.DWORD(thread_id), ctypes.byref(info)):
        return 0
    return info.flags


def _gui_focus(thread_id):
    """The GUI thread's focus hwnd (``GetFocus`` is per-thread, so an input thread must
    read it via GetGUIThreadInfo)."""
    info = _GUITHREADINFO()
    info.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if not _u.GetGUIThreadInfo(wintypes.DWORD(thread_id), ctypes.byref(info)):
        return 0
    return int(info.hwndFocus or 0)


def _gui_capture(thread_id):
    """The GUI thread's mouse-capture hwnd — who owns an in-flight drag: the GHOST
    window means Blender's modal op engaged; the Qt child means a text-selection drag."""
    info = _GUITHREADINFO()
    info.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if not _u.GetGUIThreadInfo(wintypes.DWORD(thread_id), ctypes.byref(info)):
        return 0
    return int(info.hwndCapture or 0)


def _window_at(x, y):
    _u.WindowFromPoint.restype = ctypes.c_void_p
    _u.WindowFromPoint.argtypes = [wintypes.POINT]
    return int(_u.WindowFromPoint(wintypes.POINT(x, y)) or 0)


def _hung_probe(hwnd, key):
    """The OS's own is-it-frozen tests, run from the input thread: ``IsHungAppWindow``
    (no GetMessage for ~5 s) + ``SendMessageTimeout(WM_NULL, SMTO_ABORTIFHUNG, 2 s)``.
    Records into R[key]; checkpoints immediately when hung so a kill still reports."""
    SMTO_ABORTIFHUNG = 0x0002
    handle = ctypes.c_void_p(int(hwnd))
    hung = bool(_u.IsHungAppWindow(handle))
    result = ctypes.c_size_t()
    _u.SendMessageTimeoutW.restype = ctypes.c_void_p
    ok = _u.SendMessageTimeoutW(
        handle, 0, 0, 0, SMTO_ABORTIFHUNG, 2000, ctypes.byref(result)
    )
    R[key] = {"is_hung": hung, "wm_null_ok": bool(ok)}
    if hung or not ok:
        _write_json()
    return not hung and bool(ok)


def _drag_edge(hwnd, edge, step, leg):
    """Input thread: REAL border resize drag (OS calls only — no bpy, no Qt).

    ``edge`` = "bottom" (drag up by ``10*|step|``) or "right" (drag right). After the
    mouse-up, polls the GUI thread's ``GUI_INMOVESIZE``: still set 3 s later means the
    modal size loop never received the release — the documented wedge. Attempts an ESC
    cancel so the harness can still tear down and report.
    """
    try:
        time.sleep(0.5)
        _ctx[leg + "_fg"] = _input.force_foreground(hwnd, allow_minimize=False)
        if _u.IsZoomed(ctypes.c_void_p(int(hwnd))):
            _u.ShowWindow(ctypes.c_void_p(int(hwnd)), _input.SW_RESTORE)
            time.sleep(0.5)
        left, top, right, bottom = _rect(hwnd)
        _ctx[leg + "_rect_before"] = (left, top, right, bottom)
        if edge == "bottom":
            x, y, dx, dy = (left + right) // 2, bottom - 4, 0, -abs(step)
        else:  # right
            x, y, dx, dy = right - 4, (top + bottom) // 2, abs(step), 0
        tid = _u.GetWindowThreadProcessId(ctypes.c_void_p(int(hwnd)), None)
        loop_seen = False
        for attempt in range(2):  # a first grab can flake right after a foreground change
            _u.SetCursorPos(x, y)
            time.sleep(0.3)
            _u.mouse_event(_input.BTN["L"][0], 0, 0, 0, 0)
            time.sleep(0.15)
            for _ in range(15):  # smooth relative motion the modal loop must track
                _u.mouse_event(_input.MOUSE_MOVE, dx, dy, 0, 0)
                loop_seen = loop_seen or bool(_gui_flags(tid) & GUI_INMOVESIZE)
                time.sleep(0.05)
            time.sleep(0.15)
            _u.mouse_event(_input.BTN["L"][1], 0, 0, 0, 0)
            if loop_seen:
                break
            R[leg + "_grab_retry"] = attempt + 1
            time.sleep(0.4)
        R[leg + "_loop_seen"] = loop_seen  # False = the press never grabbed the border
        deadline = time.time() + 3.0
        wedged = True
        while time.time() < deadline:
            if not (_gui_flags(tid) & GUI_INMOVESIZE):
                wedged = False
                break
            time.sleep(0.1)
        _ctx[leg + "_wedged"] = wedged
        R[leg + "_wedged"] = wedged
        if wedged:
            _write_json()  # post-mortem data survives even if the caller must kill us
            _u.keybd_event(VK_ESCAPE, 0, 0, 0)  # try to cancel the stuck size loop
            _u.keybd_event(VK_ESCAPE, 0, _input.KEYUP, 0)
            time.sleep(1.0)
            R[leg + "_esc_recovered"] = not (_gui_flags(tid) & GUI_INMOVESIZE)
        _ctx[leg + "_rect_after"] = _rect(hwnd)
        _hung_probe(hwnd, leg + "_hung")
    except Exception:
        import traceback

        R[leg + "_thread_error"] = traceback.format_exc()
        _write_json()
    _ctx[leg + "_done"] = True


def _drag_splitter(hwnd, cx, border_y, console_cy, leg, dwell=True):
    """Input thread: (optionally) hover the console first — the focus-follow poll hands
    the child the keys, as happens whenever a user reads the console — then a REAL drag
    of the console strip's top border — Blender's ``area_move`` modal operator.
    Up 12×8 px, pause, down 6×8 px, release: net +48 px strip height."""
    try:
        time.sleep(0.5)
        _ctx[leg + "_fg"] = _input.force_foreground(hwnd, allow_minimize=False)
        tid = _u.GetWindowThreadProcessId(ctypes.c_void_p(int(hwnd)), None)
        if dwell:
            _u.SetCursorPos(cx, console_cy)  # the 20 Hz poll takes focus for the child
            time.sleep(0.6)
        R[leg + "_focus_at_grab"] = _gui_focus(tid)
        _u.SetCursorPos(cx, border_y)
        time.sleep(0.1)
        # The _input.click() jiggle idiom: GHOST tracks hover from real MOTION, so a bare
        # SetCursorPos leaves Blender's region-under-cursor stale — and area_move's edge
        # hit-test then runs against the stale position and passes the press through.
        _u.mouse_event(_input.MOUSE_MOVE, 1, 1, 0, 0)
        time.sleep(0.03)
        _u.mouse_event(_input.MOUSE_MOVE, -1, -1, 0, 0)
        time.sleep(0.05)
        _u.SetCursorPos(cx, border_y)
        time.sleep(0.15)
        R[leg + "_window_at_border"] = _window_at(cx, border_y)
        R[leg + "_focus_at_press"] = _gui_focus(tid)  # did the poll flip it back already?
        _u.mouse_event(_input.BTN["L"][0], 0, 0, 0, 0)
        time.sleep(0.15)
        R[leg + "_capture_at_press"] = _gui_capture(tid)
        pt = wintypes.POINT()
        _u.GetCursorPos(ctypes.byref(pt))
        R[leg + "_cursor_at_press"] = (pt.x, pt.y)
        captures = set()
        for _ in range(12):
            _u.mouse_event(_input.MOUSE_MOVE, 0, -8, 0, 0)
            captures.add(_gui_capture(tid))
            time.sleep(0.05)
        _u.GetCursorPos(ctypes.byref(pt))
        R[leg + "_cursor_at_peak"] = (pt.x, pt.y)  # proves the OS really moved it
        time.sleep(0.2)
        for _ in range(6):
            _u.mouse_event(_input.MOUSE_MOVE, 0, 8, 0, 0)
            captures.add(_gui_capture(tid))
            time.sleep(0.05)
        R[leg + "_captures_during_drag"] = sorted(captures)
        time.sleep(0.15)
        _u.mouse_event(_input.BTN["L"][1], 0, 0, 0, 0)
        time.sleep(0.6)
        R[leg + "_focus_after"] = _gui_focus(tid)
        _hung_probe(hwnd, leg + "_hung")
    except Exception:
        import traceback

        R[leg + "_thread_error"] = traceback.format_exc()
        _write_json()
    _ctx[leg + "_done"] = True


def _max_restore(hwnd, leg):
    """Input thread: maximize then restore the GHOST window with the console docked —
    two instantaneous full-relayout size jumps (double-click-title / snap analogue)."""
    try:
        time.sleep(0.5)
        handle = ctypes.c_void_p(int(hwnd))
        _u.ShowWindow(handle, 3)  # SW_MAXIMIZE
        time.sleep(1.2)
        R[leg + "_rect_max"] = _rect(hwnd)
        _hung_probe(hwnd, leg + "_hung_max")
        _u.ShowWindow(handle, _input.SW_RESTORE)
        time.sleep(1.2)
        R[leg + "_rect_restored"] = _rect(hwnd)
        _hung_probe(hwnd, leg + "_hung_restore")
    except Exception:
        import traceback

        R[leg + "_thread_error"] = traceback.format_exc()
        _write_json()
    _ctx[leg + "_done"] = True


def _start_liveness():
    """0.1 s ticker; also records the largest inter-tick gap (stall detector)."""
    _ctx["ticks"], _ctx["last_tick"], _ctx["max_gap"] = 0, time.time(), 0.0

    def _tick():
        now = time.time()
        _ctx["max_gap"] = max(_ctx["max_gap"], now - _ctx["last_tick"])
        _ctx["last_tick"] = now
        _ctx["ticks"] += 1
        return 0.1

    bpy.app.timers.register(_tick, persistent=True)


def _await(leg, then, timeout=25.0):
    """Poll for the input thread's done-flag on a bpy timer, then run ``then`` once.
    A deadline miss (thread died / bpy timers stopped ticking) finishes with what we have."""
    deadline = time.time() + timeout

    def _poll():
        if not _ctx.get(leg + "_done"):
            if time.time() < deadline:
                return 0.2
            R[leg + "_await_timeout"] = True
            _finish()
            return None
        try:
            then()
        except Exception:
            import traceback

            R[leg + "_assert_error"] = traceback.format_exc()
            _finish()
        return None

    bpy.app.timers.register(_poll, first_interval=0.2)


def _leg_stats(leg):
    _ctx[leg + "_ticks_start"] = _ctx["ticks"]
    R["counters"][leg + "_position_calls_start"] = _ctx.get("position_calls", 0)
    R["counters"][leg + "_focus_sets_start"] = _ctx.get("focus_sets", 0)


def _leg_report(leg):
    R[leg + "_ticks"] = _ctx["ticks"] - _ctx.get(leg + "_ticks_start", 0)
    R[leg + "_max_gap_so_far"] = round(_ctx["max_gap"], 3)
    R["counters"][leg + "_position_calls"] = _ctx.get("position_calls", 0)
    R["counters"][leg + "_focus_sets"] = _ctx.get("focus_sets", 0)
    R[leg + "_fg"] = _ctx.get(leg + "_fg")
    R[leg + "_rect_before"] = _ctx.get(leg + "_rect_before")
    R[leg + "_rect_after"] = _ctx.get(leg + "_rect_after")


def _resized(leg, axis):
    before, after = _ctx.get(leg + "_rect_before"), _ctx.get(leg + "_rect_after")
    if not before or not after:
        return False
    if axis == "height":
        return (after[3] - after[1]) != (before[3] - before[1])
    return (after[2] - after[0]) != (before[2] - before[0])


def _go():
    try:
        for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
            _p = str(MONO / _pkg)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        os.environ.setdefault("QT_API", "pyside6")

        import shutil

        from blendertk.env_utils import script_output as so

        shutil.rmtree(SANDBOX, ignore_errors=True)
        os.makedirs(SANDBOX, exist_ok=True)
        so.ScriptConsole._state_dir_override = SANDBOX
        so.begin_capture()  # production order — also gives the console a real transcript
        for i in range(200):  # realistic document for the re-layout cost during resize
            print(f"console_resize_check filler line {i}: " + "x" * 60)

        from tentacle import tcl_blender as tb

        if tb._KeymapBridge.tcl is None:
            tb.launch()

        hwnd = _input.main_ghost_hwnd()
        if hwnd is None:
            _ck("GHOST window resolved", False)
            _finish()
            return None
        _ctx["hwnd"] = int(hwnd)

        # Normalize to a known on-screen rect FIRST: a fresh Blender window fills the
        # work area, leaving its bottom/right borders off-screen where no cursor can
        # grab them (measured: rect (-8,30,1928,1088) on a 1920x1080 display).
        if _u.IsZoomed(ctypes.c_void_p(_ctx["hwnd"])):
            _u.ShowWindow(ctypes.c_void_p(_ctx["hwnd"]), _input.SW_RESTORE)
        sw, sh = _u.GetSystemMetrics(0), _u.GetSystemMetrics(1)
        w, h = min(1200, sw - 200), min(800, sh - 200)
        _u.SetWindowPos(ctypes.c_void_p(_ctx["hwnd"]), None, 60, 60, w, h,
                        0x0004 | 0x0010)  # SWP_NOZORDER | SWP_NOACTIVATE
        rect = _rect(_ctx["hwnd"])
        R["normalized_rect"] = rect
        _ck("window normalized to an on-screen rect (borders grabbable)",
            rect[2] <= sw and rect[3] <= sh, f"rect={rect} screen=({sw},{sh})")

        _start_liveness()
        _write_json()

        # --- Leg A: control resize, console NOT docked -------------------------------
        _leg_stats("legA")
        threading.Thread(
            target=_drag_edge, args=(hwnd, "bottom", 8, "legA"), daemon=True
        ).start()
        _await("legA", _after_leg_a)
    except Exception:
        import traceback

        R["go_error"] = traceback.format_exc()
        _finish()
    return None


def _after_leg_a():
    _leg_report("legA")
    _ck("control: the drag actually entered the native modal size loop",
        R.get("legA_loop_seen") is True)
    _ck("control: bottom-border resize with NO console completes (modal loop exits)",
        _ctx.get("legA_wedged") is False)
    _ck("control: window height actually changed", _resized("legA", "height"),
        f"before={_ctx.get('legA_rect_before')} after={_ctx.get('legA_rect_after')}")
    _write_json()

    # --- dock the console, instrument the in-loop actors -----------------------------
    from blendertk.env_utils import script_output as so
    from blendertk.ui_utils.blender_window import BlenderWindow

    inst = so.show()
    _ck("console docked for the resize legs", inst.widget is not None and inst._dock.docked)

    dock = inst._dock
    orig_position = dock._position
    def _counting_position(region, _orig=orig_position):
        _ctx["position_calls"] = _ctx.get("position_calls", 0) + 1
        return _orig(region)
    dock._position = _counting_position

    orig_focus = BlenderWindow.set_keyboard_focus
    def _counting_focus(hwnd, _orig=orig_focus):
        _ctx["focus_sets"] = _ctx.get("focus_sets", 0) + 1
        return _orig(hwnd)
    BlenderWindow.set_keyboard_focus = staticmethod(_counting_focus)

    if MODE in ("noglue", "noboth") and dock._draw_handle is not None:
        dock._space_cls.draw_handler_remove(dock._draw_handle, "WINDOW")
        dock._draw_handle = None
        R["bisect"] = R.get("bisect", "") + " draw-handler-removed"
    if MODE in ("nofocus", "noboth"):
        dock._stop_focus_follow()
        R["bisect"] = R.get("bisect", "") + " focus-follow-stopped"

    # --- Leg B: the same drag with the console docked (its strip IS the bottom) ------
    _leg_stats("legB")
    threading.Thread(
        target=_drag_edge, args=(_ctx["hwnd"], "bottom", 8, "legB"), daemon=True
    ).start()
    _await("legB", _after_leg_b)


def _after_leg_b():
    _leg_report("legB")
    _ck("console docked: the drag actually entered the native modal size loop",
        R.get("legB_loop_seen") is True)
    _ck("console docked: bottom-border resize completes (modal loop exits, no wedge)",
        _ctx.get("legB_wedged") is False,
        f"esc_recovered={R.get('legB_esc_recovered')}")
    _ck("console docked: window height actually changed", _resized("legB", "height"),
        f"before={_ctx.get('legB_rect_before')} after={_ctx.get('legB_rect_after')}")
    _ck("bpy timers kept ticking through the docked resize (no stall > 2s)",
        _ctx["max_gap"] < 2.0, f"max_gap={_ctx['max_gap']:.3f}s")
    _write_json()

    # --- Leg C: width change → full document re-layout in the embedded child --------
    _leg_stats("legC")
    threading.Thread(
        target=_drag_edge, args=(_ctx["hwnd"], "right", 8, "legC"), daemon=True
    ).start()
    _await("legC", _after_leg_c)


def _after_leg_c():
    _leg_report("legC")
    _ck("console docked: the drag actually entered the native modal size loop",
        R.get("legC_loop_seen") is True)
    _ck("console docked: right-border resize completes (modal loop exits, no wedge)",
        _ctx.get("legC_wedged") is False,
        f"esc_recovered={R.get('legC_esc_recovered')}")
    _ck("console docked: window width actually changed", _resized("legC", "width"),
        f"before={_ctx.get('legC_rect_before')} after={_ctx.get('legC_rect_after')}")

    _glue_check("after the window-border drags")
    _write_json()

    # --- Legs D0/D: area-splitter drag (Blender modal op — the UNGATED resize path).
    # D0 = control, no prior hover; D = hover the console first (focus-follow hands the
    # child the keys — what always precedes a real user's grab of the console border).
    _start_splitter_leg("legD0", dwell=False,
                        next_cb=lambda: _after_splitter_leg("legD0", _start_leg_d))


def _start_leg_d():
    _start_splitter_leg("legD", dwell=True,
                        next_cb=lambda: _after_splitter_leg("legD", _start_leg_f))


def _start_leg_f():
    """Leg F: programmatic ``screen.area_move`` on the console strip's top edge — does
    the AREA SYSTEM itself allow moving this edge (vs the input path refusing to)?"""
    from blendertk.env_utils import script_output as so

    try:
        inst = so.ScriptConsole._instance
        area = inst._dock.area
        win = bpy.context.window_manager.windows[0]
        R["areas_layout"] = [
            (a.type, a.x, a.y, a.width, a.height) for a in win.screen.areas
        ]
        h0 = int(area.height)
        results = {}
        for delta in (30, -30):
            ex = int(area.x + area.width // 2)
            ey = int(area.y + area.height) + 1  # center of the 3px border band
            with bpy.context.temp_override(window=win, screen=win.screen, area=area):
                res = bpy.ops.screen.area_move(x=ex, y=ey, delta=delta)
            results[str(delta)] = (str(res), int(area.height))
        R["legF"] = {"h0": h0, "results": results}
        _ck("programmatic screen.area_move moves the console strip's edge",
            any(h != h0 for _res, h in results.values()), str(R["legF"]))

        # Control: the same programmatic move on a NATIVE edge (outliner/properties) —
        # discriminates "area_move exec is quirky" from "the docked strip's edge is dead".
        pair = _horizontal_edge_pair(win, area.as_pointer())
        if pair is not None:
            upper, lower, edge_cx = pair
            lh0 = int(lower.height)
            ey = (int(lower.y) + int(lower.height) + int(upper.y)) // 2
            with bpy.context.temp_override(window=win, screen=win.screen, area=lower):
                res = bpy.ops.screen.area_move(x=edge_cx, y=ey, delta=30)
            R["legF2"] = {
                "pair": f"{upper.type} over {lower.type}", "h0": lh0,
                "res": str(res), "h1": int(lower.height),
            }
            _ck("programmatic screen.area_move moves a NATIVE edge (control)",
                int(lower.height) != lh0, str(R["legF2"]))
    except Exception:
        import traceback

        R["legF_error"] = traceback.format_exc()
        _ck("programmatic screen.area_move moves the console strip's edge", False,
            "raised — see legF_error")
    _write_json()
    _start_leg_g()


def _horizontal_edge_pair(win, exclude_ptr):
    """(upper, lower, center_x) for two stacked areas sharing a horizontal edge,
    neither being ``exclude_ptr`` — a control edge far from the Qt child."""
    areas = list(win.screen.areas)
    for upper in areas:
        for lower in areas:
            if upper is lower:
                continue
            if exclude_ptr in (upper.as_pointer(), lower.as_pointer()):
                continue
            # Adjacent areas are separated by the ~3px border band itself.
            if 0 <= int(upper.y) - (int(lower.y) + int(lower.height)) <= 6:
                x0 = max(int(upper.x), int(lower.x))
                x1 = min(int(upper.x) + int(upper.width),
                         int(lower.x) + int(lower.width))
                if x1 - x0 > 60:
                    return upper, lower, (x0 + x1) // 2
    return None


def _start_edge_drag(leg, area_getter, edge_cx_client, next_cb):
    """Shared driver for legs G/H: real drag of the TOP edge of ``area_getter()``,
    sampling its height during the drag."""
    from blendertk.ui_utils.blender_window import BlenderWindow

    area = area_getter()
    client_h = BlenderWindow.client_size(_ctx["hwnd"])[1]
    # +2: press the CENTER of the ~3px border band above the area, not its bottom row.
    edge_cy = client_h - (int(area.y) + int(area.height) + 2)
    pt = wintypes.POINT(0, 0)
    _u.ClientToScreen(ctypes.c_void_p(_ctx["hwnd"]), ctypes.byref(pt))
    cx, border_y = pt.x + edge_cx_client, pt.y + edge_cy
    _ctx[leg + "_h_before"] = int(area.height)
    _ctx[leg + "_heights"] = set()

    def _sample():
        if _ctx.get(leg + "_done"):
            R[leg + "_heights_during"] = sorted(_ctx[leg + "_heights"])
            return None
        try:
            a = area_getter()
            if a is not None:
                _ctx[leg + "_heights"].add(int(a.height))
        except Exception:
            pass
        return 0.05

    bpy.app.timers.register(_sample, persistent=True)
    _leg_stats(leg)
    threading.Thread(
        target=_drag_splitter,
        args=(_ctx["hwnd"], cx, border_y, border_y, leg, False),
        daemon=True,
    ).start()
    _await(leg, next_cb)


def _after_edge_drag(leg, area_getter, label, next_cb):
    _leg_report(leg)
    try:
        area = area_getter()
        h = int(area.height) if area is not None else -1
    except Exception:
        h = -1
    moved = abs(h - _ctx.get(leg + "_h_before", 0))
    hung = R.get(leg + "_hung", {})
    _ck(f"{label}: Blender is not hung after the drag",
        hung.get("is_hung") is False and hung.get("wm_null_ok") is True, str(hung))
    _ck(f"{label}: the edge TRACKED the real drag (net ~48px)",
        20 <= moved <= 80,
        f"h {_ctx.get(leg + '_h_before')} -> {h}; "
        f"heights_during={R.get(leg + '_heights_during')}")
    _write_json()
    next_cb()


def _start_leg_g():
    """Leg G: the same real-input drag on an UNRELATED area edge (control for the
    input technique — no Qt child anywhere near it)."""
    from blendertk.env_utils import script_output as so

    win = bpy.context.window_manager.windows[0]
    inst = so.ScriptConsole._instance
    try:
        console_ptr = inst._dock.area.as_pointer()
    except (ReferenceError, AttributeError):
        console_ptr = 0
    pair = _horizontal_edge_pair(win, console_ptr)
    if pair is None:
        _ck("an unrelated horizontal area edge exists to control-drag", False,
            str(R.get("areas_layout")))
        _write_json()
        _start_leg_h()
        return
    upper, lower, edge_cx = pair
    R["legG_pair"] = f"{upper.type} over {lower.type}"
    lower_ptr = lower.as_pointer()

    def _getter():
        for a in win.screen.areas:
            if a.as_pointer() == lower_ptr:
                return a
        return None

    _start_edge_drag(
        "legG", _getter, edge_cx,
        lambda: _after_edge_drag(
            "legG", _getter,
            f"unrelated edge ({R['legG_pair']})", _start_leg_h),
    )


def _start_leg_h():
    """Leg H: hide the console (its area closes), dock a BARE strip via dock_editor —
    same split, NO Qt child — and drag ITS top edge with the same technique."""
    import blendertk as btk
    from blendertk.env_utils import script_output as so

    so.hide()
    win = bpy.context.window_manager.windows[0]
    bare = btk.dock_editor("Info Log", edge_size=150, window=win)
    if bare is None:
        _ck("bare dock_editor strip created for the no-child control", False)
        _write_json()
        _start_leg_e()
        return
    _ctx["legH_win"], _ctx["legH_area"] = win, bare
    bare_ptr = bare.as_pointer()

    def _getter():
        for a in win.screen.areas:
            if a.as_pointer() == bare_ptr:
                return a
        return None

    _start_edge_drag(
        "legH", _getter, int(bare.x) + int(bare.width) // 2,
        lambda: _after_edge_drag(
            "legH", _getter, "bare docked strip (no Qt child)", _close_bare_then_e),
    )


def _close_bare_then_e():
    import blendertk as btk
    from blendertk.env_utils import script_output as so

    try:
        btk.close_area(_ctx["legH_win"], _ctx["legH_area"])
    except Exception:
        pass
    inst = so.show()  # console back for the maximize/restore leg

    def _redock_check():  # deferred: a re-typed area rebuilds its regions on next draw
        _ck("console re-docked after the bare-strip control leg (hide -> show cycle)",
            inst.widget is not None and inst._dock.docked,
            f"widget={inst.widget is not None} docked={inst._dock.docked}")
        _write_json()
        _start_leg_e()
        return None

    bpy.app.timers.register(_redock_check, first_interval=0.6)


def _start_splitter_leg(leg, dwell, next_cb):
    try:
        from blendertk.env_utils import script_output as so
        from blendertk.ui_utils.blender_window import BlenderWindow

        inst = so.ScriptConsole._instance
        region = inst._dock.content_region()
        base = BlenderWindow.region_client_rect(_ctx["hwnd"], region)
        pt = wintypes.POINT(0, 0)
        _u.ClientToScreen(ctypes.c_void_p(_ctx["hwnd"]), ctypes.byref(pt))
        cx = pt.x + base[0] + base[2] // 2
        # Region top == area top (header hidden); -2 presses the CENTER of the ~3px
        # border band between the strip and the viewport, not its bottom row.
        border_y = pt.y + base[1] - 2
        console_cy = pt.y + base[1] + base[3] // 2
        _ctx[leg + "_area_h_before"] = int(inst._dock.area.height)
        R[leg + "_child"] = int(inst.widget.internalWinId() or 0)
        R[leg + "_ghost"] = _ctx["hwnd"]

        # 20 Hz GUI-side sampler: did the border move AT ALL mid-drag (area_move engaged
        # then snapped back), or never (the press never started the operator)?
        _ctx[leg + "_heights"] = set()

        def _sample_height():
            if _ctx.get(leg + "_done"):
                R[leg + "_heights_during"] = sorted(_ctx[leg + "_heights"])
                return None
            try:
                _ctx[leg + "_heights"].add(int(inst._dock.area.height))
            except (ReferenceError, AttributeError):
                pass
            return 0.05

        bpy.app.timers.register(_sample_height, persistent=True)
    except Exception:
        import traceback

        R[leg + "_setup_error"] = traceback.format_exc()
        _finish()
        return
    _leg_stats(leg)
    threading.Thread(
        target=_drag_splitter,
        args=(_ctx["hwnd"], cx, border_y, console_cy, leg, dwell),
        daemon=True,
    ).start()
    _await(leg, next_cb)


def _after_splitter_leg(leg, next_cb):
    from blendertk.env_utils import script_output as so

    _leg_report(leg)
    inst = so.ScriptConsole._instance
    try:
        area_h = int(inst._dock.area.height)
    except (ReferenceError, AttributeError):
        area_h = -1
    grew = area_h - _ctx.get(leg + "_area_h_before", 0)
    hung = R.get(leg + "_hung", {})
    label = "no prior hover" if leg == "legD0" else "console hovered first"
    _ck(f"splitter drag ({label}): Blender is not hung afterward",
        hung.get("is_hung") is False and hung.get("wm_null_ok") is True, str(hung))
    _ck(f"splitter drag ({label}): the console strip's border TRACKED the drag (net +48px)",
        20 <= grew <= 80,
        f"height {_ctx.get(leg + '_area_h_before')} -> {area_h} (net {grew}); "
        f"heights_during={R.get(leg + '_heights_during')} "
        f"focus_at_grab={R.get(leg + '_focus_at_grab')} child={R.get(leg + '_child')} "
        f"focus_after={R.get(leg + '_focus_after')}")
    _ck(f"splitter drag ({label}): bpy timers kept ticking (no stall > 2s)",
        _ctx["max_gap"] < 2.0, f"max_gap={_ctx['max_gap']:.3f}s")
    _glue_check(f"after the splitter drag ({label})")
    _write_json()
    next_cb()


def _start_leg_e():
    # --- Leg E: maximize + restore with the console docked ---------------------------
    from blendertk.env_utils import script_output as so

    inst = so.ScriptConsole._instance
    _ctx["legE_alive"] = []

    def _sample_alive():  # timestamp WHERE the docked area dies, if it does
        if _ctx.get("legE_done"):
            R["legE_area_alive_trace"] = _ctx["legE_alive"][-40:]
            return None
        try:
            alive = inst._dock.content_region() is not None
            rect = _rect(_ctx["hwnd"])
            _ctx["legE_alive"].append((alive, rect[3] - rect[1]))
        except Exception:
            pass
        return 0.1

    bpy.app.timers.register(_sample_alive, persistent=True)
    _leg_stats("legE")
    threading.Thread(
        target=_max_restore, args=(_ctx["hwnd"], "legE"), daemon=True
    ).start()
    _await("legE", _after_leg_e)


def _after_leg_e():
    _leg_report("legE")
    hung_max = R.get("legE_hung_max", {})
    hung_restore = R.get("legE_hung_restore", {})
    _ck("maximize with console docked: not hung",
        hung_max.get("is_hung") is False and hung_max.get("wm_null_ok") is True,
        str(hung_max))
    _ck("restore with console docked: not hung",
        hung_restore.get("is_hung") is False and hung_restore.get("wm_null_ok") is True,
        str(hung_restore))
    rect_max, rect_rest = R.get("legE_rect_max"), R.get("legE_rect_restored")
    _ck("maximize/restore actually changed the window rect",
        bool(rect_max and rect_rest and tuple(rect_max) != tuple(rect_rest)),
        f"max={rect_max} restored={rect_rest}")
    _ck("bpy timers kept ticking through maximize/restore (no stall > 2s)",
        _ctx["max_gap"] < 2.0, f"max_gap={_ctx['max_gap']:.3f}s")
    _glue_check("after maximize/restore")
    _finish()


def _glue_check(label):
    """The child must sit exactly on its region (minus the exposed resize edge)."""
    try:
        from qtpy import QtWidgets
        from blendertk.env_utils import script_output as so
        from blendertk.ui_utils.blender_window import BlenderWindow

        app = QtWidgets.QApplication.instance()
        for _ in range(10):
            app.processEvents()
        inst = so.ScriptConsole._instance
        dock = inst._dock
        region = dock.content_region()
        child = int(inst.widget.winId())
        rect = wintypes.RECT()
        _u.GetWindowRect(ctypes.c_void_p(child), ctypes.byref(rect))
        pt = wintypes.POINT(0, 0)
        _u.ClientToScreen(ctypes.c_void_p(_ctx["hwnd"]), ctypes.byref(pt))
        actual = [rect.left - pt.x, rect.top - pt.y,
                  rect.right - rect.left, rect.bottom - rect.top]
        base = BlenderWindow.region_client_rect(_ctx["hwnd"], region) if region else None
        pad = dock._edge_pad
        expected = [base[0], base[1] + pad, base[2], base[3] - pad] if base else None
        delta = (max(abs(a - e) for a, e in zip(actual, expected))
                 if expected else 9999)
        _ck(f"console re-glued to its region {label} (<=2px)",
            delta <= 2, f"delta={delta} actual={actual} expected={expected}")
    except Exception:
        import traceback

        R["glue_error_" + label] = traceback.format_exc()
        _ck(f"console re-glued to its region {label} (<=2px)", False, "glue check raised")


def _finish():
    import shutil

    R["verdict"] = "PASS" if R["checks"] and all(c["pass"] for c in R["checks"]) else "FAIL"
    R["final_ticks"] = _ctx.get("ticks")
    R["max_tick_gap"] = round(_ctx.get("max_gap", 0.0), 3)
    _write_json()
    shutil.rmtree(SANDBOX, ignore_errors=True)
    print("console_resize verdict:", R["verdict"])
    sys.stdout.flush()
    _quit()
    return None


def _quit():
    """Quit with an explicit window override — from a bpy timer the context window can be
    NULL and ``wm.quit_blender`` then crashes (see console_dock_check._quit)."""
    windows = bpy.context.window_manager.windows
    if windows:
        with bpy.context.temp_override(window=windows[0]):
            bpy.ops.wm.quit_blender()
    else:
        bpy.ops.wm.quit_blender()


if sys.platform != "win32":
    print("console_resize_check: N/A off-Windows (no WS_CHILD embed there)")
else:
    bpy.app.timers.register(_go, first_interval=5.0)
