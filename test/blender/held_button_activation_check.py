# !/usr/bin/python
# coding=utf-8
"""Manual GUI harness: (A) overlay transient-parenting state and (B) held-button activation â€”
does the activation key reach tentacle while each mouse button is held BEFORE the key?

Like the sibling ``gui_*_check.py`` harnesses this needs a real GUI Blender (it injects real
input), is not a CI/unittest target, and must run against a *fresh* Blender â€” never an existing
session. Works in either launch mode (it ``launch()``\\ es tentacle itself if the startup module
didn't)::

    blender --python tentacle/test/blender/held_button_activation_check.py
    blender --factory-startup --python tentacle/test/blender/held_button_activation_check.py

Phase A (passive, main thread): the live overlay's ``windowHandle().transientParent()`` and the
Win32 owner (``GWLP_HWNDPARENT``), plus the GHOST window inventory.
Phase B: stub the live instance's press/release with recorders (no overlay ever shows), then a
background thread injects real input (Raw-Input level: ``mouse_event``/``keybd_event``) over the
viewport: a click-then-key positive control (keymap path), then L/M/R/LR held â€” button(s) down â†’
key tap â†’ button(s) up â†’ ESC. Expected: control = press(None); L/M/R held = poller press with
masks 1/4/2 DURING the hold (Qt: Left=1, Right=2, Middle=4); LR (both buttons, the
``F12|LeftButton|RightButton`` â†’ ``blender#startmenu`` chord) = mask 3; ghost_count stays 1 (a
render would open a new GHOST window).
Phase C (watchdog): arm ``_activation_key_held`` with the key physically up â€” a simulated lost
key-up (focus tussle ate it) â€” and expect the poll watchdog to drive the release within a tick.
Phase D (gesture pairing): arm ``_KeymapBridge.gesture_active`` with the held flag CLEARED â€” the state uitk's
``_show_window`` leaves when a standalone window opens mid-gesture â€” and expect the release
anyway (it's what clears ``_standalone_suppress`` and hides unpinned standalone windows).
Steals foreground and moves the real mouse for ~10 s â€” throwaway instance only. Report goes to
stdout and ``../temp_tests/held_button_activation_out.txt``.
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

# Monorepo root = .../_scripts (this file is _scripts/tentacle/test/blender/<name>.py).
MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "held_button_activation_out.txt")

_VK_F12, _VK_ESC = 0x7B, 0x1B
_GWLP_HWNDPARENT = -8

_u = _input.user32
_BTN = _input.BTN
_events = []  # appended from operator stubs (main thread) and scenario markers (input thread)
_lines = []
_ctx = {}  # main-thread handles shared between the timer phases (tcl, â€¦)


def _viewport_point(hwnd):
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    rect = wintypes.RECT()
                    _u.GetClientRect(hwnd, ctypes.byref(rect))
                    pt = wintypes.POINT(region.x + region.width // 2,
                                        rect.bottom - (region.y + region.height // 2))
                    _u.ClientToScreen(hwnd, ctypes.byref(pt))
                    return pt.x, pt.y
    return None


def _phase_a(tb, tcl):
    _lines.append("=== A: parenting after normal startup ===")
    handle = tcl.windowHandle()
    native = tb.blender_native_window()
    owner = _u.GetWindowLongPtrW(wintypes.HWND(int(tcl.winId())), _GWLP_HWNDPARENT)
    _lines.append(f"ghost_windows      : {_input.ghost_windows()}")
    _lines.append(f"windowHandle       : {handle!r}")
    _lines.append(f"transientParent    : {handle.transientParent() if handle else None!r}")
    _lines.append(f"GWLP_HWNDPARENT    : {owner:#x}")
    _lines.append(f"blender_native_now : {native!r}")
    # Retry the parenting NOW (proves whether the failure was construction-time timing).
    tb.TclBlender._parent_to_blender(tcl, tcl)
    owner2 = _u.GetWindowLongPtrW(wintypes.HWND(int(tcl.winId())), _GWLP_HWNDPARENT)
    _lines.append(f"owner after retry  : {owner2:#x}")


# Buttons to physically hold across the F12 tap, per scenario (Qt masks: L=1, R=2, M=4 →
# the poller should report the OR of these). "LR" is the both-button chord (mask 3) feeding
# the F12|LeftButton|RightButton → blender#startmenu binding.
_HOLD = {"L": ["L"], "M": ["M"], "R": ["R"], "LR": ["L", "R"]}


def _inject(hwnd, x, y):
    """Input thread: OS calls only (no bpy)."""
    time.sleep(0.4)
    _events.append(("fg_ok", _input.force_foreground(hwnd)))
    scan = _u.MapVirtualKeyW(_VK_F12, 0) or 0x58
    esc_scan = _u.MapVirtualKeyW(_VK_ESC, 0) or 0x01
    for scenario in ("control", "L", "M", "R", "LR"):
        if _u.GetForegroundWindow() != hwnd:  # re-acquire if something stole it
            _events.append(("refg", scenario, _input.force_foreground(hwnd)))
            time.sleep(0.6)  # let the freshly-restored window settle before injecting
        _u.SetCursorPos(x, y)
        time.sleep(0.1)
        # GHOST tracks hover from real mouse events â€” SetCursorPos alone leaves Blender's
        # region-under-cursor stale, so jiggle with relative moves it actually receives.
        _u.mouse_event(_input.MOUSE_MOVE, 1, 1, 0, 0)  # MOUSEEVENTF_MOVE
        time.sleep(0.05)
        _u.mouse_event(_input.MOUSE_MOVE, -1, -1, 0, 0)
        time.sleep(0.15)
        _events.append(("scenario", scenario))
        if scenario == "control":  # click (down+up) THEN F12 â€” the proven-working gesture
            _u.mouse_event(_BTN["L"][0], 0, 0, 0, 0)
            _u.mouse_event(_BTN["L"][1], 0, 0, 0, 0)
            time.sleep(0.3)
        hold = _HOLD.get(scenario, [])
        for b in hold:  # press each button down (held simultaneously across the F12 tap)
            _u.mouse_event(_BTN[b][0], 0, 0, 0, 0)
            time.sleep(0.12)
        if hold:
            time.sleep(0.2)
        # Record whether the injection target actually has foreground at key-send time â€”
        # separates real dispatch failures from the flaky OS foreground grant.
        _events.append(("fg_at_key", scenario, _u.GetForegroundWindow() == hwnd))
        _u.keybd_event(_VK_F12, scan, 0, 0)
        time.sleep(0.08)
        _u.keybd_event(_VK_F12, scan, _input.KEYUP, 0)
        time.sleep(0.3)
        for b in reversed(hold):  # release in reverse order
            _u.mouse_event(_BTN[b][1], 0, 0, 0, 0)
            time.sleep(0.05)
        if hold:
            _events.append(("btn_up", scenario))
        time.sleep(0.25)
        _u.keybd_event(_VK_ESC, esc_scan, 0, 0)  # dismiss any popup (RMB context menu)
        time.sleep(0.05)
        _u.keybd_event(_VK_ESC, esc_scan, _input.KEYUP, 0)
        time.sleep(0.4)
        _events.append(("ghost_count", scenario, len(_input.ghost_windows())))


def _go():
    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    # Self-sufficient: use the startup module's instance when present (normal launch),
    # otherwise stand the host up ourselves (--factory-startup).
    tcl = tb._KeymapBridge.tcl or tb.launch()

    _phase_a(tb, tcl)
    tb._Config.DEBUG = True  # operator self-reports each fire (visible in captured stdout)

    # Phase B â€” stub the interaction entry points on the LIVE instance: dispatch is measured at
    # the operator/poller level; no overlay ever shows, so Blender keeps focus between
    # scenarios. Stubs mimic the real state machine's _activation_key_held arming so the
    # poller's dedup + release-safety-net branches are exercised as in production.
    t0 = time.monotonic()

    def _press(buttons=None):
        tcl._activation_key_held = True
        mask = None if buttons is None else getattr(buttons, "value", buttons)
        _events.append(("press", mask, round(time.monotonic() - t0, 2)))

    def _release():
        tcl._activation_key_held = False
        _events.append(("release", round(time.monotonic() - t0, 2)))

    tcl._on_activation_press = _press
    tcl._on_activation_release = _release
    tcl.grabMouse = lambda: None
    tcl.raise_ = lambda: None
    tcl.activateWindow = lambda: None
    tcl._probe_t0 = t0

    hwnd = _input.ghost_windows()[0][0]
    point = _viewport_point(hwnd)
    if point is None:
        _lines.append("PROBE ERROR: no 3D viewport region found")
        _finish()
        return None
    _ctx["tcl"] = tcl
    _ctx["tb"] = tb
    threading.Thread(target=_inject, args=(hwnd, *point), daemon=True).start()
    bpy.app.timers.register(_phase_c, first_interval=12.0)
    bpy.app.timers.register(_phase_d, first_interval=13.0)
    bpy.app.timers.register(_finish, first_interval=14.5)
    return None


def _phase_c():
    """Simulate a lost key-up: gesture armed but the key is physically up â€” the release
    watchdog (not any event) must complete the gesture."""
    _events.append(("phase_c_armed",))
    _ctx["tcl"]._activation_key_held = True
    return None


def _phase_d():
    """Simulate the standalone-window aftermath: uitk's ``_show_window`` cleared the held
    flag but the bridge-initiated gesture still owes its key-up â€” only the gesture pairing
    (``_KeymapBridge.gesture_active``) can drive this release."""
    _events.append(("phase_d_armed",))
    _ctx["tcl"]._activation_key_held = False
    _ctx["tb"]._KeymapBridge.gesture_active = True
    return None


def _finish():
    rr = bpy.data.images.get("Render Result")
    _lines.append("=== B: dispatch with held buttons ===")
    _lines.append(f"events        : {_events}")
    _lines.append(f"render_result : {bool(rr and rr.has_data)}")
    for phase in ("c", "d"):
        try:
            armed_at = _events.index((f"phase_{phase}_armed",))
            fired = any(e[0] == "release" for e in _events[armed_at + 1:])
        except ValueError:
            fired = None  # phase never ran
        _lines.append(f"watchdog_release ({phase.upper()}): {fired}")
    report = "\n".join(_lines)
    print(report)
    sys.stdout.flush()
    with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
        f.write(report)
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(_go, first_interval=6.0)
