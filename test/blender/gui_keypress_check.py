"""Ground-truth GUI test: does a REAL F12 keypress over the viewport reach OUR keymap, or render?

Launch a fresh GUI Blender (never an existing session)::

    blender --python tentacle/test/blender/gui_keypress_check.py

Why a stub, not the real menu: ``MarkingMenu.__init__`` calls ``showFullScreen()``, so the real
overlay is *always* visible after ``register()`` (``isVisible()`` is a false-positive signal) and it
grabs OS focus — an injected F12 would then go to Qt, never to Blender's keymap, so that path can't
measure dispatch. Here we point the keymap at a lightweight **stub** (records ``show`` calls, no Qt
window), so Blender keeps focus and a physical F12 over the viewport is dispatched by Blender exactly
as for the user. We then click the viewport (focus + active area), inject F12, and report whether our
operator fired (3D-View keymap won) or a render fired (``Screen`` keymap won). Windows-only (uses
``user32``); requires ``TENTACLE_QT_DEPS`` (or on-demand Qt). Moves the real mouse + sends a real
click and keystroke — run only when you can spare the focus for ~6 s.
"""
import sys
import os
import ctypes
import threading
import time
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

# Keymap → stub (records show()); raise_/activateWindow are no-ops so the operator returns FINISHED
# and consumes the event (a bare stub would AttributeError → CANCELLED → fall through to render).
_calls = []
_stub = NS(
    show=lambda ui: _calls.append(ui),
    raise_=lambda: None,
    activateWindow=lambda: None,
)


def _ghost_hwnd():
    """Top-level GHOST window handle for THIS Blender process (None on failure)."""
    from ctypes import wintypes

    u = ctypes.windll.user32
    pid = os.getpid()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        wpid = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and u.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(hwnd, buf, 64)
            if buf.value == "GHOST_WindowClass":
                found.append(hwnd)
                return False
        return True

    u.EnumWindows(_enum, 0)
    return found[0] if found else None


def _viewport_screen_center():
    """Screen-pixel center of the 3D viewport.

    Preferred: center of the GHOST window's real Windows rect (factory layout puts the 3D
    viewport there) — Blender's own win.x/win.y→desktop mapping is unreliable on multi-monitor.
    keybd_event also goes to the FOREGROUND window, and a Blender launched from a background
    shell is denied foreground by Windows — so the caller must SetForegroundWindow first.
    """
    from ctypes import wintypes

    u = ctypes.windll.user32
    hwnd = _ghost_hwnd()
    if hwnd:
        rect = wintypes.RECT()
        if u.GetWindowRect(hwnd, ctypes.byref(rect)):
            return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
    win = bpy.context.window  # fallback: Blender's own coords (Y bottom-up)
    for area in win.screen.areas:
        if area.type == "VIEW_3D":
            cx = win.x + area.x + area.width // 2
            cy = win.y + win.height - (area.y + area.height // 2)
            return int(cx), int(cy)
    return None


def _click_viewport_then_f12():
    time.sleep(3.0)  # let the window settle
    u = ctypes.windll.user32
    hwnd = _ghost_hwnd()
    if hwnd:
        # Windows denies SetForegroundWindow to a process that isn't already foreground
        # (Blender launched from a background shell). The documented escape hatch: an
        # injected Alt press marks our process as the last-input source first.
        _VK_MENU = 0x12
        u.keybd_event(_VK_MENU, 0, 0, 0)
        u.SetForegroundWindow(hwnd)
        u.keybd_event(_VK_MENU, 0, _KEYUP, 0)
    time.sleep(0.3)
    fg_ok = hwnd is not None and u.GetForegroundWindow() == hwnd
    center = _viewport_screen_center()
    if center:
        u.SetCursorPos(*center)
    time.sleep(0.3)
    print(f"[keypress] hwnd={hwnd} foreground_ok={fg_ok} cursor={center}")
    sys.stdout.flush()
    # Two clicks: the first dismisses the factory-startup splash; the second lands in the
    # viewport proper (focus + active area).
    for _ in range(2):
        u.mouse_event(_LDOWN, 0, 0, 0, 0)
        u.mouse_event(_LUP, 0, 0, 0, 0)
        time.sleep(0.3)
    # GHOST consumes keyboard via Raw Input — send a real scancode, not just the virtual key.
    scan = u.MapVirtualKeyW(_VK_F12, 0)
    u.keybd_event(_VK_F12, scan, 0, 0)       # F12 down
    time.sleep(0.05)
    u.keybd_event(_VK_F12, scan, _KEYUP, 0)  # F12 up


def _report_and_quit():
    fired = bool(_calls)
    n_windows = len(bpy.context.window_manager.windows)
    rr = bpy.data.images.get("Render Result")
    rendered = bool(rr and rr.has_data) or n_windows > 1
    print("\n===F12-DISPATCH===")
    print(f"operator_fired = {fired}  (show calls: {_calls})")
    print(f"rendered       = {rendered}  (windows={n_windows})")
    print("verdict        =",
          "OUR KEYMAP WINS" if fired and not rendered
          else "RENDER WINS" if rendered and not fired
          else "INCONCLUSIVE (F12 may not have reached Blender)")
    print("===END===")
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()
    return None


tb._install_keymap(_stub, "F12", "main#startmenu")  # no register() → no overlay → Blender keeps focus
threading.Thread(target=_click_viewport_then_f12, daemon=True).start()
bpy.app.timers.register(_report_and_quit, first_interval=6.0)
