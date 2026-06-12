"""Ground-truth precedence test: does a REAL F12 over the viewport dispatch to OUR keymap or render?

Launch a fresh GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/gui_keypress_check.py

The open question the headless ``keymap_bridge_check.py`` *can't* answer: our item lives in the
``3D View`` (region) keymap and ``render.render`` lives in the global ``Screen`` (window) keymap —
Blender dispatches region handlers before window handlers, so *in theory* we win over the viewport.
This proves it on a real event.

Why ``PostMessage`` and not ``keybd_event``: ``keybd_event``/``SendInput`` deliver to the OS
*foreground* window, and a Blender launched from a background shell is denied foreground by Windows
(the earlier test was stuck INCONCLUSIVE for exactly this reason). ``PostMessage`` queues a message
to a *specific* ``hwnd`` regardless of foreground, and GHOST's Win32 window proc handles
``WM_KEYDOWN``/``WM_KEYUP``, so a posted key reaches Blender's event loop exactly like a physical one.
We first post ``WM_MOUSEMOVE`` to a point inside the 3D viewport (so the key event's region match
resolves to the viewport), then post F12, then report whether OUR operator fired (region keymap won)
or a render kicked off (Screen keymap won). Windows-only. Uses a **stub** menu (records ``show``
calls, no Qt overlay) so Blender keeps focus and the dispatch is measured, not short-circuited.
"""
import sys
import os
import ctypes
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

_WM_MOUSEMOVE = 0x0200
_WM_KEYDOWN = 0x0100
_WM_KEYUP = 0x0101
_VK_F12 = 0x7B
_MAPVK_VK_TO_VSC = 0

_u = ctypes.windll.user32
_u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_u.PostMessageW.restype = wintypes.BOOL

# Keymap → stub: records show(); raise_/activateWindow are no-ops so the operator returns FINISHED
# (consumes the event). A bare stub would AttributeError on raise_ → operator path differs; mirror
# the real QWidget surface the bridge touches.
_calls = []
_stub = NS(show=lambda ui: _calls.append(ui), raise_=lambda: None, activateWindow=lambda: None)


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


def _viewport_client_point(hwnd):
    """A client-space (x, y) safely inside the 3D viewport region.

    Prefer Blender's own area rect (authoritative for which region the event lands in); fall back to
    a left-of-center fraction of the client rect (factory layout: viewport fills the left/center,
    Properties/Outliner sit right, Timeline bottom). Blender's area Y is bottom-up; client Y is
    top-down, so flip against the client height."""
    rect = wintypes.RECT()
    _u.GetClientRect(hwnd, ctypes.byref(rect))
    cw, ch = rect.right, rect.bottom
    for area in bpy.context.window.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    x = region.x + region.width // 2
                    y_bottomup = region.y + region.height // 2
                    return int(x), int(ch - y_bottomup)
    return int(cw * 0.35), int(ch * 0.45)


def _lparam(scan, up):
    """WM_KEY* lParam: repeat=1, scancode in bits 16-23; bits 30-31 set on key-up."""
    base = 1 | (scan << 16)
    return base | (0xC0000000 if up else 0)


def _post_f12():
    hwnd = _ghost_hwnd()
    if not hwnd:
        print("[keypress] no GHOST hwnd — cannot post")
        return False
    x, y = _viewport_client_point(hwnd)
    # Position Blender's tracked cursor inside the viewport so the key event's region match is the
    # 3D view (region handlers, where our item lives), not the header/properties.
    _u.PostMessageW(hwnd, _WM_MOUSEMOVE, 0, (y << 16) | (x & 0xFFFF))
    scan = _u.MapVirtualKeyW(_VK_F12, _MAPVK_VK_TO_VSC) or 0x58
    _u.PostMessageW(hwnd, _WM_KEYDOWN, _VK_F12, _lparam(scan, up=False))
    _u.PostMessageW(hwnd, _WM_KEYUP, _VK_F12, _lparam(scan, up=True))
    print(f"[keypress] posted MOUSEMOVE({x},{y}) + F12 (scan=0x{scan:02x}) to hwnd={hwnd}")
    sys.stdout.flush()
    return True


def _report_and_quit():
    fired = bool(_calls)
    n_windows = len(bpy.context.window_manager.windows)
    rr = bpy.data.images.get("Render Result")
    rendered = bool(rr and rr.has_data) or n_windows > 1
    print("\n===F12-DISPATCH===")
    print(f"operator_fired = {fired}  (show calls: {_calls})")
    print(f"rendered       = {rendered}  (windows={n_windows}, render_result={bool(rr)})")
    print("verdict        =",
          "OUR KEYMAP WINS (region beats Screen)" if fired and not rendered
          else "RENDER WINS (Screen beat our region item)" if rendered and not fired
          else "BOTH FIRED — event not consumed" if fired and rendered
          else "INCONCLUSIVE (F12 may not have reached Blender)")
    print("===END===")
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()
    return None


def _go():
    tb._install_keymap(_stub, "F12", "main#startmenu")  # no register() → no overlay → Blender keeps focus
    _post_f12()
    bpy.app.timers.register(_report_and_quit, first_interval=2.5)
    return None


# Defer until the window + keyconfig have settled (the addon keymap merges on the next event-loop pass).
bpy.app.timers.register(_go, first_interval=2.5)
