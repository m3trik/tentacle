# !/usr/bin/python
# coding=utf-8
"""GUI harness: OS-frame resize/move/snap of the Blender window with the Script Output
console docked — the gesture battery ``console_resize_check`` (area borders) and
``console_dpi_drag_check`` (cross-monitor) both skip.

SOLVED (2026-07-18) — this harness found the real root cause of the freeze family:

* Field symptoms: Blender froze on same-monitor window resizes/snaps ("drag to the edge
  to auto resize at half the monitor, it breaks"), and the console strip came back BLANK.
* Bisect trail: the ``move_snap_left``/``move_snap_top`` legs froze Blender
  deterministically at RELEASE-into-snap — bpy ticks dead forever, window still
  answering ``WM_NULL``, no DPI change involved (96 -> 96). Freezes reproduced with the
  2026-07-16 QtDock modal guard, WITHOUT it, and with no console docked at all
  (``noconsole``) — the py-spy stack (``test/temp_tests/frame_noconsole_stack.txt``)
  shows the tentacle pump's ``processEvents`` towers: pump -> DispatchMessage -> GHOST
  wndproc -> ``wglSwapBuffers`` -> nested dispatch -> WM_TIMER -> pump again, ~4 layers
  until the innermost dispatch never returns. Same mechanism as the cross-DPI freeze
  (``console_dpi_drag_check``).
* THE FIX (``tcl_blender._QtHost.start_pump``): the pump delivers Qt's POSTED events
  only (``sendPostedEvents``) and never dispatches native messages — GHOST's own loop
  already dispatches those for every thread window. All modes/legs pass with it.
* The QtDock modal guard was REVERTED during this investigation and stays gone: its
  suspend/resume did Qt window-system calls (``fromWinId``/``setParent``/``show``)
  from bpy timers in exactly these hazardous contexts, it hid the console during every
  drag, its unbalanced-suspend path stranded a BLANK strip over a bare Info Log area
  (the field "console is just blank"), and its protective rationale was disproven
  (the freeze needs no embedded child at all).

Legs (env ``FRAME_MODE``), each a fresh Blender instance driven by real injected input:

  guard      — the shipped code as-is (THE regression sentinel; PASS required — the
               snap legs freeze again if anyone reintroduces a ``processEvents`` pump
               or in-loop embed churn)
  noguard    — guard probe patched off when present; on guard-less builds = guard mode
  noconsole  — tentacle running, console never shown (Qt-runtime-only control)

Knobs: ``FRAME_MONITOR=other`` relocates to the second monitor first (programmatic —
proven clean — so the battery isolates the gestures); ``FRAME_PREHISTORY=crossdrag``
REAL-drags the window onto the other monitor first (field-faithful prehistory).

Battery per leg (window restored from Blender's startup-maximized state, then normalized
inside its monitor's work area — a maximized window silently refuses border resizes):
bottom-edge grow / shrink, right-edge grow, title moves, an 8 ms-step resize storm, a
drag-to-LEFT-edge half-snap (the field gesture), a drag-to-top snap-maximize, and a
drag-restore when maximized. Every gesture is a REAL drag (SetCursorPos + mouse_event
with a pre-press jiggle) pressed on a point the window itself hit-tests as frame
(``WM_NCHITTEST`` scan — Win11's invisible extended borders make fixed offsets miss).
The input thread confirms the native size/move loop engaged (GetGUIThreadInfo
``GUI_INMOVESIZE`` on the GUI thread) and watches a 20 Hz bpy tick counter for the
livelock (ticks stall mid-drag or never resume after release — the window still answers
``WM_NULL`` when frozen, so hang APIs stay green and tick progression is the only honest
probe). After each gesture a GUI-thread snapshot records the full embed forensics:
suspend/resume counts (0 on guard-less builds), area/widget/foreign state, the child's
native parent+visibility+rect vs the area's region rect, Qt-side visibility, a paint
canary (``QEvent.Paint`` counter armed by ``viewport().update()`` at the previous
snapshot), a pump canary (a 50 ms ``QTimer`` that only advances when ``processEvents``
runs), and whether the console text still holds the printed marker.

PASS = every gesture engaged + resized/moved the window, no freeze, and (console legs)
the embed is healthy after every gesture: not suspended, resumes == suspends, child
parented+visible+glued (rect matches minus the exposed native resize strip), paint+pump
advancing, marker text intact, ``screen.area_move`` poll healthy at the end.

Run (one leg; the caller owns timeout+taskkill — a frozen Blender never exits itself)::

    $env:FRAME_MODE="guard"; & "C:\\...\\blender.exe" --factory-startup --python `
        tentacle/test/blender/console_frame_resize_check.py

Output: ``test/temp_tests/console_frame_resize_<mode>.json`` (written incrementally — a
freeze leaves the last completed leg on disk). Throwaway instance; steals foreground +
mouse for ~60 s. Windows-only.
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

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

MODE = os.environ.get("FRAME_MODE", "guard").lower()
# born = battery on the monitor Blender opened on; other = programmatically relocate to
# the second monitor first (the mixed-DPI leg — programmatic moves are proven clean by
# console_dpi_move_check, so the battery still measures only the resize gestures).
MONITOR = os.environ.get("FRAME_MONITOR", "born").lower()
# crossdrag = REAL title-drag onto the other monitor before the battery (the field
# prehistory: the user's window got where it is by dragging, not SetWindowPos — the
# drag primes whatever DPI/screen state a later same-monitor resize then trips over).
PREHIST = os.environ.get("FRAME_PREHISTORY", "").lower()
TEMP = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests")
)
_SUFFIX = MODE if MONITOR == "born" else f"{MODE}_{MONITOR}"
if PREHIST:
    _SUFFIX += "_xd"
OUT = os.path.join(TEMP, f"console_frame_resize_{_SUFFIX}.json")
SANDBOX = os.path.join(TEMP, f"console_frame_state_{_SUFFIX}")
MARKER = "FRAME_RESIZE_CHECK_MARKER"

_u = ctypes.windll.user32
_k = ctypes.windll.kernel32
MOUSE_MOVE = 0x0001
BTN_DOWN, BTN_UP = 0x0002, 0x0004
GUI_INMOVESIZE = 0x2
SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010

R = {"mode": MODE, "ticks": 0, "suspends": 0, "resumes": 0, "gestures": []}
_ctx = {"pump": 0, "paints": 0}


class _GTI(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def _write():
    try:
        os.makedirs(TEMP, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(R, f, indent=2, default=str)
    except Exception:
        pass


def _gui_flags():
    info = _GTI()
    info.cbSize = ctypes.sizeof(_GTI)
    if _u.GetGUIThreadInfo(_ctx["gui_tid"], ctypes.byref(info)):
        return int(info.flags)
    return 0


def _win_rect(hwnd):
    rect = wintypes.RECT()
    _u.GetWindowRect(ctypes.c_void_p(int(hwnd)), ctypes.byref(rect))
    return [rect.left, rect.top, rect.right, rect.bottom]


def _child_rect_in_parent_client(child, parent):
    rect = wintypes.RECT()
    _u.GetWindowRect(ctypes.c_void_p(int(child)), ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    _u.ClientToScreen(ctypes.c_void_p(int(parent)), ctypes.byref(pt))
    return [rect.left - pt.x, rect.top - pt.y,
            rect.right - rect.left, rect.bottom - rect.top]


def _answers_wm_null(hwnd):
    res = ctypes.c_size_t()
    SMTO_ABORTIFHUNG = 0x0002
    return bool(_u.SendMessageTimeoutW(
        ctypes.c_void_p(int(hwnd)), 0, 0, 0, SMTO_ABORTIFHUNG, 1000,
        ctypes.byref(res)))


def _window_dpi(hwnd):
    try:
        return int(_u.GetDpiForWindow(ctypes.c_void_p(int(hwnd))))
    except Exception:
        return 0


def _nc_hit(hwnd, x, y):
    """The window's own WM_NCHITTEST verdict for screen point (x, y), or None."""
    res = ctypes.c_size_t()
    lparam = ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)
    if _u.SendMessageTimeoutW(ctypes.c_void_p(int(hwnd)), 0x0084, 0, lparam,
                              0x0002, 1000, ctypes.byref(res)):
        return int(res.value)
    return None


_u.WindowFromPoint.restype = ctypes.c_void_p
_u.WindowFromPoint.argtypes = [wintypes.POINT]
_u.GetAncestor.restype = ctypes.c_void_p


def _screen_root(x, y):
    """Root window a REAL click at screen (x, y) would land on (z-order honest)."""
    hwnd_at = _u.WindowFromPoint(wintypes.POINT(int(x), int(y)))
    if not hwnd_at:
        return 0
    return int(_u.GetAncestor(ctypes.c_void_p(int(hwnd_at)), 2) or 0)  # GA_ROOT


def _find_grab(hwnd, code, points):
    """First candidate screen point that BOTH hit-tests as ``code`` AND is physically
    reachable by a click.

    Win11's themed frames extend an INVISIBLE resize band ~8 px past the visible
    edge and GetWindowRect includes it — a fixed 'rect edge minus 2' guess can miss
    the live band entirely (measured: 4/4 resize drags no-oped). Asking the window
    itself (HTCAPTION=2, HTRIGHT=11, HTBOTTOM=15) is the honest locator — but
    ``WM_NCHITTEST`` via SendMessage ignores z-order, so the point must also pass a
    ``WindowFromPoint`` root check: a MAXIMIZED window's caption top tucks under a
    top taskbar (rect.top=22 vs taskbar rows 0-30 — measured: presses at y=24 went
    to the taskbar and the drag silently no-oped).
    """
    for x, y in points:
        if _nc_hit(hwnd, x, y) == code and _screen_root(x, y) == int(hwnd):
            return int(x), int(y)
    return None


def _normalize_same_monitor(hwnd, relocate=True):
    """Place the window at a fixed size INSIDE its current monitor's work area.

    Positioning at a hardcoded (60,60) can silently move the window onto a
    different-DPI monitor (measured: the first title drag then fired a mid-loop DPI
    rescale, 1200x800 -> 1936x1058) — this harness is the SAME-monitor leg, so the
    window must stay on the monitor it was born on. ``relocate=False`` ignores the
    FRAME_MONITOR knob and just re-sizes in place (used after a crossdrag prehistory,
    which already put the window where it belongs BY DRAGGING).
    """
    class _MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    MONITOR_DEFAULTTONEAREST = 2
    mon = _u.MonitorFromWindow(ctypes.c_void_p(int(hwnd)), MONITOR_DEFAULTTONEAREST)
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not _u.GetMonitorInfoW(mon, ctypes.byref(info)):
        return None
    # Factory Blender opens MAXIMIZED. SetWindowPos on a maximized window changes the
    # rect but leaves WS_MAXIMIZE set — Windows then refuses border resizes entirely
    # (measured: HTBOTTOM presses no-oped) and the first title drag fires
    # drag-to-restore, ballooning the window mid-loop. Restore for real first.
    if _u.IsZoomed(ctypes.c_void_p(int(hwnd))):
        _u.ShowWindow(ctypes.c_void_p(int(hwnd)), 9)  # SW_RESTORE
        time.sleep(0.4)
    work, monitor = info.rcWork, info.rcMonitor
    if relocate and MONITOR == "other":
        other = _other_monitor_work(mon)
        if other is None:
            R.setdefault("problems", []).append(
                "monitor=other requested but only one monitor present")
        else:
            work = monitor = other  # work area is close enough for placement
    x, y = work.left + 40, work.top + 40
    w = min(1200, work.right - work.left - 240)
    h = min(800, work.bottom - work.top - 200)
    _u.SetWindowPos(ctypes.c_void_p(int(hwnd)), None, x, y, w, h,
                    SWP_NOZORDER | SWP_NOACTIVATE)
    time.sleep(1.0)  # let any WM_DPICHANGED from a cross-monitor relocation settle
    # Snap zones hang off the MONITOR edge, not the work-area edge — with a top
    # taskbar, work.top sits ~30 px below the true screen edge and a drag stopping
    # there never engages snap-maximize (measured: the leg read inconclusive).
    R["monitor_area"] = [monitor.left, monitor.top, monitor.right, monitor.bottom]
    return [work.left, work.top, work.right, work.bottom]


def _other_monitor_work(current_mon):
    """The work area of the first monitor that is NOT ``current_mon`` (None if single)."""
    class _MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    handles = []
    proc_t = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p,
                                ctypes.POINTER(wintypes.RECT), ctypes.c_void_p)

    @proc_t
    def _collect(hmon, _hdc, _rect, _lparam):
        handles.append(hmon)
        return True

    _u.EnumDisplayMonitors(None, None, _collect, None)
    for hmon in handles:
        if int(hmon or 0) == int(current_mon or 0):
            continue
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if _u.GetMonitorInfoW(hmon, ctypes.byref(info)):
            work = info.rcWork
            return type(work)(work.left, work.top, work.right, work.bottom)
    return None


def _other_work_now():
    """[l, t, r, b] work area of the monitor the window is NOT on right now."""
    MONITOR_DEFAULTTONEAREST = 2
    mon = _u.MonitorFromWindow(ctypes.c_void_p(int(_ctx["hwnd"])),
                               MONITOR_DEFAULTTONEAREST)
    work = _other_monitor_work(mon)
    return [work.left, work.top, work.right, work.bottom] if work is not None else None


# ---------------------------------------------------------------- GUI-thread side
def _tick():
    R["ticks"] += 1
    return 0.05


def _snapshot(label):
    """Full embed forensics — must run on the GUI thread (bpy + Qt reads)."""
    snap = {"label": label, "ticks": R["ticks"], "pump": _ctx["pump"],
            "suspends": R["suspends"], "resumes": R["resumes"]}
    if MODE == "noconsole":
        return snap
    from blendertk.env_utils import script_output as so
    from blendertk.ui_utils.blender_window import BlenderWindow

    inst = so.ScriptConsole._instance
    dock = inst._dock
    widget = inst.widget
    snap.update(
        area=dock._area is not None,
        widget=dock._widget is not None,
        foreign=dock._foreign is not None,
        suspended=getattr(dock, "_suspended", False),  # guard-era attr; gone post-revert
        visible_flag=inst._visible,
        paints=_ctx["paints"],
    )
    child = 0
    if widget is not None:
        try:
            child = int(widget.internalWinId() or 0)
        except Exception:
            child = 0
        snap["qt_visible"] = bool(widget.isVisible())
        snap["text_marker"] = MARKER in widget.toPlainText()
    snap["child"] = child
    if child:
        snap["child_parent"] = int(_u.GetParent(ctypes.c_void_p(child)) or 0)
        snap["child_visible"] = bool(_u.IsWindowVisible(ctypes.c_void_p(child)))
        snap["child_rect"] = _child_rect_in_parent_client(child, _ctx["hwnd"])
    region = dock.content_region()
    if region is not None:
        snap["region_rect"] = BlenderWindow.region_client_rect(_ctx["hwnd"], region)
    snap["edge_pad"] = dock._edge_pad
    if widget is not None:  # arm the paint canary: next snapshot's count proves delivery
        _paint_target(widget).update()
    return snap


def _paint_target(widget):
    """Where Qt actually delivers Paint events — the viewport for scroll-area widgets."""
    viewport = getattr(widget, "viewport", None)
    return viewport() if callable(viewport) and viewport() is not None else widget


def _poll_ok():
    try:
        win = _ctx["win"]
        area = win.screen.areas[0]
        with bpy.context.temp_override(window=win, screen=win.screen, area=area):
            return bool(bpy.ops.screen.area_move.poll())
    except Exception:
        return False


def _quit():
    windows = bpy.context.window_manager.windows
    if windows:
        with bpy.context.temp_override(window=windows[0]):
            bpy.ops.wm.quit_blender()
    else:
        bpy.ops.wm.quit_blender()


def _gui_tick():
    if _ctx.get("do_quit"):
        import shutil

        shutil.rmtree(SANDBOX, ignore_errors=True)
        _quit()
        return None
    req = _ctx.pop("req", None)
    if req is not None:
        kind, arg = req
        try:
            if kind == "snapshot":
                _ctx["resp"] = _snapshot(arg)
            elif kind == "poll_ok":
                _ctx["resp"] = _poll_ok()
        except Exception:
            import traceback

            R.setdefault("gui_errors", []).append(traceback.format_exc())
            _write()
            _ctx["resp"] = None
        _ctx["resp_ready"] = True
    return 0.05


def _ask(kind, arg=None, timeout=8.0):
    _ctx["resp_ready"] = False
    _ctx["req"] = (kind, arg)
    deadline = time.time() + timeout
    while not _ctx.get("resp_ready") and time.time() < deadline:
        time.sleep(0.05)
    return _ctx.get("resp") if _ctx.get("resp_ready") else None


# ---------------------------------------------------------------- input-thread side
def _wait_ticks(seconds):
    """True if the bpy tick counter advances within ``seconds`` (liveness)."""
    start = R["ticks"]
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(0.1)
        if R["ticks"] > start:
            return True
    return False


def _steps(dx, dy, n=10, delay=0.045):
    """Uniform drag path: n relative moves totaling ~(dx, dy), ``delay`` s apart."""
    return [(dx // n, dy // n, delay)] * n


def _frame_drag(x, y, segments):
    """One real size/move drag along ``segments`` [(dx, dy, delay), ...]; returns
    in-drag telemetry. Never leaves the button held."""
    out = {"in_loop": False, "frozen_during": False}
    _u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    _u.mouse_event(MOUSE_MOVE, 1, 1, 0, 0)  # jiggle: refresh hover state before press
    time.sleep(0.03)
    _u.mouse_event(MOUSE_MOVE, -1, -1, 0, 0)
    time.sleep(0.05)
    _u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    _u.mouse_event(BTN_DOWN, 0, 0, 0, 0)
    try:
        time.sleep(0.15)
        last_tick, last_change = R["ticks"], time.time()
        for step_x, step_y, delay in segments:
            if step_x or step_y:
                _u.mouse_event(MOUSE_MOVE, int(step_x), int(step_y), 0, 0)
            time.sleep(delay)
            if _gui_flags() & GUI_INMOVESIZE:
                out["in_loop"] = True
            tick = R["ticks"]
            if tick != last_tick:
                last_tick, last_change = tick, time.time()
            elif time.time() - last_change > 3.0:  # in-loop ticks run ~3x slow; 3 s = dead
                out["frozen_during"] = True
                break
        time.sleep(0.15)
    finally:
        _u.mouse_event(BTN_UP, 0, 0, 0, 0)
    time.sleep(0.4)
    # Dismiss any snap-layouts flyout / snap-assist chrome the release invoked —
    # left open, it eats the NEXT gesture's press. Esc is a no-op to idle Blender.
    _u.keybd_event(0x1B, 0, 0, 0)
    _u.keybd_event(0x1B, 0, 0x0002, 0)
    time.sleep(0.2)
    return out


def _run_gesture(name, grab, delta, expect):
    """Drive one gesture end-to-end; append its record; return False on freeze."""
    hwnd = _ctx["hwnd"]
    leg = {"name": name}
    R["gestures"].append(leg)
    leg["pre"] = _ask("snapshot", f"{name}:pre")
    rect0 = _win_rect(hwnd)
    leg["rect_before"] = rect0
    leg["dpi_before"] = _window_dpi(hwnd)
    point = grab(rect0)
    if point is None:
        _problem(name, "no grab point (WM_NCHITTEST scan found no frame band)")
        leg["post"] = None
        _write()
        return True  # not a freeze — later gestures may still run
    gx, gy = point
    leg["grab"] = [gx, gy]
    segments = delta(rect0, gx, gy) if callable(delta) else _steps(*delta)
    leg.update(_frame_drag(gx, gy, segments))
    leg["alive_after"] = _wait_ticks(5.0)
    leg["rect_after"] = _win_rect(hwnd)
    leg["dpi_after"] = _window_dpi(hwnd)
    leg["wm_null"] = _answers_wm_null(hwnd)
    leg["hung_api"] = bool(_u.IsHungAppWindow(ctypes.c_void_p(int(hwnd))))
    frozen = leg["frozen_during"] or not leg["alive_after"]
    if frozen:
        leg["post"] = None
        _problem(name, "FROZE (bpy ticks stalled; wm_null=%s hung_api=%s)"
                 % (leg["wm_null"], leg["hung_api"]))
        _write()
        return False
    leg["post"] = _ask("snapshot", f"{name}:post")
    _evaluate(name, leg, expect)
    _write()
    return True


def _problem(name, why):
    R.setdefault("problems", []).append(f"{name}: {why}")


def _evaluate(name, leg, expect):
    if not leg["in_loop"]:
        _problem(name, "native size/move loop never engaged (drag missed the frame)")
        return
    b, a = leg["rect_before"], leg["rect_after"]
    got = {"w": (a[2] - a[0]) - (b[2] - b[0]), "h": (a[3] - a[1]) - (b[3] - b[1]),
           "x": a[0] - b[0], "y": a[1] - b[1]}
    leg["delta"] = got
    if callable(expect):
        expect(name, leg)
    elif expect:
        for axis, want in expect.items():
            if want and (got[axis] * want <= 0 or abs(got[axis]) < abs(want) // 2):
                _problem(name, f"window {axis} delta {got[axis]} (wanted ~{want})")
    pre, post = leg["pre"], leg["post"]
    if post is None:
        _problem(name, "GUI thread stopped answering after the gesture")
        return
    if MODE == "noconsole":
        return
    if post.get("suspended"):
        _problem(name, "still suspended after the loop ended (resume never ran)")
    if post.get("suspends", 0) != post.get("resumes", 0):
        _problem(name, "suspend/resume unbalanced: %s/%s"
                 % (post.get("suspends"), post.get("resumes")))
    if MODE == "noguard" and post.get("suspends", 0):
        _problem(name, "guard suspended despite the probe being patched off")
    if not (post.get("area") and post.get("widget")):
        _problem(name, "dock detached (area=%s widget=%s) — the blank-strip symptom"
                 % (post.get("area"), post.get("widget")))
        return
    if not post.get("child"):
        _problem(name, "widget has no native window after the gesture")
        return
    if post.get("child_parent") != int(_ctx["hwnd"]):
        _problem(name, "child no longer parented to the GHOST window (parent=%s)"
                 % post.get("child_parent"))
    if not post.get("child_visible") or not post.get("qt_visible"):
        _problem(name, "console hidden after the gesture (native=%s qt=%s) — blank strip"
                 % (post.get("child_visible"), post.get("qt_visible")))
    region, child = post.get("region_rect"), post.get("child_rect")
    if region and child:
        pad = int(post.get("edge_pad") or 3)
        drift = max(abs(child[0] - region[0]), abs(child[2] - region[2]),
                    abs((child[1] + child[3]) - (region[1] + region[3])),
                    abs(child[1] - (region[1] + pad)) - pad)  # top may sit 0..2*pad down
        if drift > 4:
            _problem(name, f"child rect {child} drifted from region {region} (pad={pad})")
    elif not region:
        _problem(name, "no content region after the gesture")
    if pre and pre.get("paints") is not None and post.get("paints") is not None:
        if post["paints"] <= pre["paints"]:
            _problem(name, "paint canary flat (%s -> %s) — console not repainting"
                     % (pre["paints"], post["paints"]))
    if pre and post.get("pump", 0) <= pre.get("pump", 0):
        _problem(name, "Qt pump canary flat — processEvents no longer running")
    if post.get("text_marker") is False:
        _problem(name, "console text lost the marker (content wiped)")


def _input_main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _input

        hwnd = _ctx["hwnd"]
        pt = wintypes.POINT()
        _u.GetCursorPos(ctypes.byref(pt))
        cursor_restore = (pt.x, pt.y)
        R["foreground"] = _input.force_foreground(hwnd, allow_minimize=False)
        R["work_area"] = _normalize_same_monitor(hwnd)
        time.sleep(0.8)
        R["poll_ok_baseline"] = _ask("poll_ok")  # tells product breakage from context artifact

        HTCAPTION, HTRIGHT, HTBOTTOM = 2, 11, 15
        mid_x = lambda r: (r[0] + r[2]) // 2

        def _bottom(r):
            return _find_grab(hwnd, HTBOTTOM,
                              [(mid_x(r), y) for y in range(r[3] - 12, r[3] + 10)])

        def _right(r):
            return _find_grab(hwnd, HTRIGHT,
                              [(x, (r[1] + r[3]) // 2)
                               for x in range(r[2] - 12, r[2] + 10)])

        def _caption(r):
            # Quarter-width, not center: after a snap-maximize Win11 parks its
            # snap-layouts flyout at the caption's top-center, eating a press there
            # (measured: the follow-up drag never engaged the move loop).
            quarter_x = r[0] + (r[2] - r[0]) // 4
            return _find_grab(hwnd, HTCAPTION,
                              [(quarter_x, y) for y in range(r[1] + 2, r[1] + 44, 2)])

        def _storm(_rect, _gx, _gy):
            """Fast zigzag: 3 grow/shrink cycles in one hold, ~8 ms per step."""
            cycle = [(0, 14, 0.008)] * 10 + [(0, -14, 0.008)] * 10
            return cycle * 3

        def _to_top_edge(rect, _gx, gy):
            """Drag the caption to the monitor's top edge and hover — Win11 snap-max."""
            top = R["monitor_area"][1] if R.get("monitor_area") else rect[1]
            n = 14
            return [(0, (top + 1 - gy) // n, 0.02)] * n + [(0, 0, 0.6)]

        def _to_left_edge(_rect, gx, _gy):
            """Drag the caption to the monitor's LEFT edge and hover — Win11 edge-snap.
            The field gesture (2026-07-18): 'drag to the edge to auto resize at half
            the monitor, it breaks'. Starts with small tear-away steps so a MAXIMIZED
            window (the leg above leaves one) cleanly enters its restore-drag before
            the fast run to the edge."""
            left = R["monitor_area"][0] if R.get("monitor_area") else 0
            tear = [(-15, 0, 0.04)] * 3
            remaining = (left + 1 - gx) + 45
            n = 11
            return tear + [(remaining // n, 0, 0.02)] * n + [(0, 0, 0.6)]

        def _check_snap_top(name, leg):
            leg["zoomed_after"] = bool(_u.IsZoomed(ctypes.c_void_p(int(hwnd))))
            if not leg["zoomed_after"]:
                R.setdefault("inconclusive", []).append(
                    f"{name}: drag-to-top did not snap-maximize (snap off / missed)")

        def _check_snap_left(name, leg):
            """A DWM edge-snap engaged: the window sits at the monitor's left edge
            (outer rect overhangs by the ~7 px invisible border) and DWM resized it
            at release. Half vs quarter tile is layout-dependent (a caption grab
            lands the cursor in the top-left CORNER zone -> quarter) — either is the
            release-into-snap-transition this leg exists to exercise."""
            mon = R.get("monitor_area") or R.get("work_area")
            a, d = leg["rect_after"], leg.get("delta") or {}
            leg["snapped"] = bool(
                mon and abs(a[0] - mon[0]) <= 10
                and (d.get("w", 0) <= -100 or d.get("h", 0) <= -100))
            if not leg["snapped"]:
                R.setdefault("inconclusive", []).append(
                    f"{name}: drag-to-left did not snap (rect={a} monitor={mon})")

        def _check_restored(name, leg):
            leg["zoomed_after"] = bool(_u.IsZoomed(ctypes.c_void_p(int(hwnd))))
            if leg["zoomed_after"]:
                R.setdefault("inconclusive", []).append(
                    f"{name}: drag did not restore the maximized window")

        battery = [
            ("resize_bottom_grow", _bottom, (0, 100), {"h": 90}),
            ("resize_bottom_shrink", _bottom, (0, -60), {"h": -50}),
            ("resize_right_grow", _right, (90, 0), {"w": 80}),
            ("move_title", _caption, (70, 40), {"x": 60, "y": 30}),
            ("move_title_back", _caption, (-70, -40), {"x": -60, "y": -30}),
            ("resize_storm_bottom", _bottom, _storm, None),
            # snap-max FIRST (from a normal window), then drag-to-left FROM the
            # maximized state — the field flow ("maximize, then tile to a side"),
            # and the left drag then also exercises drag-restore-from-maximized
            # mid-loop. Reversed, the top leg acts on an already-snapped window,
            # which Win11 refuses to move for a short vertical drag (measured).
            ("move_snap_top", _caption, _to_top_edge, _check_snap_top),
            ("move_snap_left", _caption, _to_left_edge, _check_snap_left),
        ]

        def _crossdrag(rect, gx, gy):
            """REAL bounded title-drag onto the other monitor (the A0-style gesture)."""
            other = _other_work_now()
            if other is None:
                return []
            tx, ty = (other[0] + other[2]) // 2, other[1] + 60
            n = 24
            return [((tx - gx) // n, (ty - gy) // n, 0.03)] * n

        if PREHIST == "crossdrag":
            if not _run_gesture("prehistory_crossdrag", _caption, _crossdrag, None):
                battery = []  # frozen during the prehistory drag itself
            else:
                R["work_area"] = _normalize_same_monitor(hwnd, relocate=False)
                time.sleep(0.8)

        frozen = False
        for name, grab, delta, expect in battery:
            if not _run_gesture(name, grab, delta, expect):
                frozen = True
                break  # frozen — nothing further can run
        # Drag-restore only exists when the snap leg actually maximized.
        if not frozen and battery and _u.IsZoomed(ctypes.c_void_p(int(hwnd))):
            frozen = not _run_gesture("move_drag_restore", _caption,
                                      (0, 140), _check_restored)
        if not frozen and battery:
            time.sleep(1.5)  # settle, then the paint canary armed above must have fired
            R["final"] = _ask("snapshot", "final")
            R["poll_ok"] = _ask("poll_ok")
            # Only meaningful against a healthy baseline — the bare temp_override poll
            # reads False in this environment even before any gesture (context artifact).
            if R.get("poll_ok_baseline") is True and R["poll_ok"] is False:
                _problem("final", "screen.area_move poll broken after the battery")
            final = R["final"]
            if MODE != "noconsole" and final and final.get("paints") is not None:
                last = next((g["post"] for g in reversed(R["gestures"])
                             if g.get("post")), None)
                if last and final["paints"] <= last.get("paints", 0):
                    _problem("final", "paint canary flat over the settle window")
        _u.SetCursorPos(*cursor_restore)
    except Exception:
        import traceback

        R["input_error"] = traceback.format_exc()
        R.setdefault("problems", []).append("input thread crashed (see input_error)")
    R["verdict"] = "PASS" if not R.get("problems") else "FAIL"
    _write()
    print(f"console_frame_resize[{MODE}] verdict:", R["verdict"])
    sys.stdout.flush()
    _ctx["do_quit"] = True  # GUI tick performs the context-safe quit
    time.sleep(8)  # if the GUI never gets there (frozen), the caller's timeout kills us


def _go():
    try:
        import shutil

        from blendertk.env_utils import script_output as so

        shutil.rmtree(SANDBOX, ignore_errors=True)
        os.makedirs(SANDBOX, exist_ok=True)
        so.ScriptConsole._state_dir_override = SANDBOX
        so.begin_capture()

        from tentacle import tcl_blender as tb

        if tb._KeymapBridge.tcl is None:
            tb.launch()

        from qtpy import QtCore, QtWidgets

        app = QtWidgets.QApplication.instance()
        R["qt"] = app is not None

        if MODE != "noconsole":
            inst = so.show()
            R["dock_supported"] = so.QtDock.supported()
            if not R["dock_supported"] or inst.widget is None:
                R["verdict"] = "INCONCLUSIVE"
                R["problems"] = ["dock unsupported here — nothing to measure"]
                _write()
                _ctx["do_quit"] = True
                bpy.app.timers.register(_gui_tick, persistent=True)
                return None
            dock = inst._dock

            # Instrument suspend/resume via instance-attribute shadowing (the guard
            # calls self._suspend_embed, so a bound override intercepts cleanly).
            # Post-revert builds have no guard — counters just stay 0, which the
            # evaluation treats as balanced.
            if hasattr(dock, "_suspend_embed"):
                orig_suspend, orig_resume = dock._suspend_embed, dock._resume_embed

                def _counted_suspend():
                    R["suspends"] += 1
                    orig_suspend()

                def _counted_resume():
                    R["resumes"] += 1
                    orig_resume()

                dock._suspend_embed = _counted_suspend
                dock._resume_embed = _counted_resume

            # Paint canary on the console widget.
            class _PaintCounter(QtCore.QObject):
                def eventFilter(self, _obj, event):
                    if event.type() == QtCore.QEvent.Paint:
                        _ctx["paints"] += 1
                    return False

            _ctx["paint_filter"] = _PaintCounter()
            _paint_target(inst.widget).installEventFilter(_ctx["paint_filter"])
            print(MARKER)

        if MODE == "noguard":
            from blendertk.ui_utils.blender_window import BlenderWindow

            if hasattr(BlenderWindow, "modal_move_size_active"):
                BlenderWindow.modal_move_size_active = classmethod(lambda cls: False)
                R["guard_patched_off"] = True
            else:  # post-revert build: no guard exists — identical to shipped mode
                R["guard_patched_off"] = "n/a (no guard in build)"

        # Pump canary: a QTimer only fires when processEvents actually runs.
        timer = QtCore.QTimer()
        timer.setInterval(50)
        timer.timeout.connect(lambda: _ctx.__setitem__("pump", _ctx["pump"] + 1))
        timer.start()
        _ctx["pump_timer"] = timer

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _input

        hwnd = _input.main_ghost_hwnd()
        if hwnd is None:
            R["verdict"] = "FAIL"
            R.setdefault("problems", []).append("no GHOST window")
            _write()
            _ctx["do_quit"] = True
            bpy.app.timers.register(_gui_tick, persistent=True)
            return None
        _ctx["hwnd"] = int(hwnd)
        _ctx["win"] = bpy.context.window_manager.windows[0]
        _ctx["gui_tid"] = _k.GetCurrentThreadId()

        bpy.app.timers.register(_tick, persistent=True)
        bpy.app.timers.register(_gui_tick, persistent=True)
        threading.Thread(target=_input_main, daemon=True).start()
    except Exception:
        import traceback

        R["verdict"] = "FAIL"
        R["go_error"] = traceback.format_exc()
        R.setdefault("problems", []).append("setup crashed (see go_error)")
        _write()
        _quit()
    return None


if sys.platform != "win32":
    print("console_frame_resize_check: N/A off-Windows")
else:
    bpy.app.timers.register(_go, first_interval=5.0)
