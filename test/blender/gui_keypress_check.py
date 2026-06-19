"""Ground-truth precedence test: does a REAL F12 over the viewport dispatch to OUR keymap or render?

Launch a fresh GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/gui_keypress_check.py

The open question the headless ``keymap_bridge_check.py`` *can't* answer: our item lives in the
``3D View`` (region) keymap and ``render.render`` lives in the global ``Screen`` (window) keymap —
Blender dispatches region handlers before window handlers, so *in theory* we win over the viewport.
This proves it on a real event.

Delivery: a real keystroke needs (1) real input — ``keybd_event``/``SendInput`` generate Raw Input
(``WM_INPUT``), which GHOST reads (``PostMessage`` of ``WM_KEYDOWN`` is *ignored* by GHOST, so that
route is dead) — and (2) the target window in the OS foreground (Raw Input goes to the focused
window). A Blender launched from a background shell is denied ``SetForegroundWindow``, *but*
restoring a just-minimized window is granted foreground by Windows — so we minimize→restore the
GHOST window to legitimately foreground it, click the viewport (focus + active region), then send a
real F12 and report whether OUR operator fired (region keymap won) or a render kicked off (Screen
keymap won). Runs the input in a background thread so Blender's event loop keeps turning and actually
processes the injected event. Windows-only; **moves the real mouse + steals foreground for ~2 s** —
run only in a throwaway ``--factory-startup`` instance. Uses a **stub** menu (records ``show`` calls,
no Qt overlay) so Blender keeps focus and the dispatch is measured, not short-circuited by the overlay.
"""
import sys
import os
import time
import ctypes
import threading
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace as NS

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender as tb

_VK_F12 = 0x7B
_KEYUP = 0x0002
_LDOWN, _LUP = 0x0002, 0x0004
_SW_MINIMIZE, _SW_RESTORE = 6, 9

_u = ctypes.windll.user32

# Keymap → stub: records the interaction-state-machine calls the operator drives. The grab is a
# no-op record (so the *test* never leaves a real mouse grab); raise_/activateWindow mirror the
# QWidget surface the operator nudges. Crucially, this measures whether a real key-up fires the
# RELEASE item — if it didn't, the live menu's mouse grab would stay stuck.
_events = []
_stub = NS(
    _on_activation_press=lambda: _events.append("press"),
    _on_activation_release=lambda: _events.append("release"),
    grabMouse=lambda: _events.append("grab"),
    raise_=lambda: None,
    activateWindow=lambda: None,
)


def _ghost_hwnd():
    """Top-level GHOST window handle for THIS Blender process (None on failure)."""
    pid = os.getpid()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        wpid = wintypes.DWORD()
        _u.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and _u.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(64)
            _u.GetClassNameW(hwnd, buf, 64)
            if buf.value == "GHOST_WindowClass":
                found.append(hwnd)
                return False
        return True

    _u.EnumWindows(_enum, 0)
    return found[0] if found else None


def _screen_viewport_point(hwnd):
    """Screen-pixel (x, y) inside the 3D viewport region (Blender area rect → client → screen)."""
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    rect = wintypes.RECT()
                    _u.GetClientRect(hwnd, ctypes.byref(rect))
                    # Blender area Y is bottom-up; client Y is top-down.
                    pt = wintypes.POINT(region.x + region.width // 2,
                                        rect.bottom - (region.y + region.height // 2))
                    _u.ClientToScreen(hwnd, ctypes.byref(pt))
                    return pt.x, pt.y
    rect = wintypes.RECT()
    _u.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2


def _press_f12(hwnd, x, y):
    # OS calls only — no bpy here (Blender restricts bpy.context off the main thread; the viewport
    # point is computed on the main thread in _go and passed in).
    time.sleep(0.5)
    if not hwnd:
        print("[keypress] no GHOST hwnd — cannot inject")
        sys.stdout.flush()
        return
    # Foreground acquisition: a background-shell Blender is denied SetForegroundWindow, but restoring
    # a just-minimized window is granted foreground — the only reliable hatch found.
    _u.ShowWindow(hwnd, _SW_MINIMIZE)
    time.sleep(0.3)
    _u.ShowWindow(hwnd, _SW_RESTORE)
    _u.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    fg_ok = _u.GetForegroundWindow() == hwnd
    _u.SetCursorPos(x, y)
    time.sleep(0.2)
    _u.mouse_event(_LDOWN, 0, 0, 0, 0)  # click → focus + active region = the 3D viewport
    _u.mouse_event(_LUP, 0, 0, 0, 0)
    time.sleep(0.2)
    # Real F12 via Raw Input (keybd_event), with the real scancode GHOST expects.
    scan = _u.MapVirtualKeyW(_VK_F12, 0) or 0x58
    _u.keybd_event(_VK_F12, scan, 0, 0)
    time.sleep(0.05)
    _u.keybd_event(_VK_F12, scan, _KEYUP, 0)
    print(f"[keypress] fg_ok={fg_ok} cursor=({x},{y}) sent F12 (scan=0x{scan:02x}) to hwnd={hwnd}")
    sys.stdout.flush()


def _report_and_quit():
    pressed = "press" in _events
    released = "release" in _events
    n_windows = len(bpy.context.window_manager.windows)
    rr = bpy.data.images.get("Render Result")
    rendered = bool(rr and rr.has_data) or n_windows > 1
    print("\n===F12-DISPATCH===")
    print(f"events   = {_events}")
    print(f"rendered = {rendered}  (windows={n_windows}, render_result={bool(rr)})")
    print("verdict  =",
          "PRESS+RELEASE BOTH FIRE — grab released on key-up (region beats Screen, safe)"
          if pressed and released and not rendered
          else "PRESS fired but RELEASE did NOT — live grab would stay stuck!" if pressed and not released
          else "RENDER WINS (Screen beat our region item)" if rendered and not pressed
          else "INCONCLUSIVE (F12 may not have reached Blender)")
    print("===END===")
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()
    return None


def _go():
    tb._KeymapBridge.install_keymap(_stub, "F12")  # no register() → no overlay → Blender keeps focus
    hwnd = _ghost_hwnd()
    x, y = _screen_viewport_point(hwnd) if hwnd else (0, 0)  # main-thread bpy.context access
    threading.Thread(target=_press_f12, args=(hwnd, x, y), daemon=True).start()
    bpy.app.timers.register(_report_and_quit, first_interval=4.0)
    return None


# Defer until the window + keyconfig have settled (the addon keymap merges on the next event-loop pass).
bpy.app.timers.register(_go, first_interval=2.0)
