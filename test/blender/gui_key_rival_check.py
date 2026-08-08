"""Ground-truth SAME-KEYMAP precedence test: does our addon-keyconfig item beat a factory item
bound to the same bare key in the same ``3D View`` keymap?

Launch a fresh GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/gui_key_rival_check.py

``gui_keypress_check.py`` proves our region item beats the *global Screen* keymap (``F12`` vs
``render.render`` — different keymaps, region-before-window dispatch). This check answers the
question that one can't: ``Z`` — the default activation key — is ALSO bound in the factory ``3D
View`` keymap itself (``wm.call_menu_pie`` → shading pie, bare PRESS), so both items sit in the
same keymap and dispatch order between the *addon* keyconfig and the *user/default* keyconfig
decides which fires. That order is undocumented; this measures it on a real event.

Protocol: install the real bridge (``install_keymap`` with ``Z``) plus an ``F12`` control pair on
the same addon keymap, then inject two real keystrokes — F12 first (no same-keymap factory rival →
proves delivery + mechanism), then Z (contested by the pie). The stub records which presses reach
our operator; the input thread snapshots between keys. An ESC follows Z so a pie that won is closed
before quitting. Delivery mechanics (Raw Input, minimize→restore foreground hatch, viewport click,
background input thread) are ``gui_keypress_check.py``'s, documented there. Windows-only; **moves
the real mouse + steals foreground for ~3 s** — run only in a throwaway ``--factory-startup``
instance.
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

_VK = {"F12": 0x7B, "Z": 0x5A, "ESC": 0x1B}
_KEYUP = 0x0002
_LDOWN, _LUP = 0x0002, 0x0004
_SW_MINIMIZE, _SW_RESTORE = 6, 9

_u = ctypes.windll.user32

_events = []
_stub = NS(
    _on_activation_press=lambda: _events.append("press"),
    _on_activation_release=lambda: _events.append("release"),
    grabMouse=lambda: _events.append("grab"),
    raise_=lambda: None,
    activateWindow=lambda: None,
)
_result = {}  # input thread → report timer


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
                    pt = wintypes.POINT(region.x + region.width // 2,
                                        rect.bottom - (region.y + region.height // 2))
                    _u.ClientToScreen(hwnd, ctypes.byref(pt))
                    return pt.x, pt.y
    rect = wintypes.RECT()
    _u.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2


def _tap(key):
    vk = _VK[key]
    scan = _u.MapVirtualKeyW(vk, 0)
    _u.keybd_event(vk, scan, 0, 0)
    time.sleep(0.05)
    _u.keybd_event(vk, scan, _KEYUP, 0)


def _inject(hwnd, x, y):
    # OS calls only — no bpy off the main thread (viewport point computed in _go, passed in).
    time.sleep(0.5)
    if not hwnd:
        _result["error"] = "no GHOST hwnd — cannot inject"
        return
    _u.ShowWindow(hwnd, _SW_MINIMIZE)
    time.sleep(0.3)
    _u.ShowWindow(hwnd, _SW_RESTORE)
    _u.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    _result["fg_ok"] = _u.GetForegroundWindow() == hwnd
    _u.SetCursorPos(x, y)
    time.sleep(0.2)
    _u.mouse_event(_LDOWN, 0, 0, 0, 0)  # click → focus + active region = the 3D viewport
    _u.mouse_event(_LUP, 0, 0, 0, 0)
    time.sleep(0.3)

    _tap("F12")  # control: no same-keymap factory rival
    time.sleep(1.2)
    _result["control"] = list(_events)
    _events.clear()

    _tap("Z")  # contested: factory shading pie on bare Z PRESS
    time.sleep(1.2)
    _result["contested"] = list(_events)

    _tap("ESC")  # close the pie if it won
    time.sleep(0.3)


def _report_and_quit():
    control = _result.get("control", [])
    contested = _result.get("contested", [])
    ctrl_ok = "press" in control and "release" in control
    z_ok = "press" in contested and "release" in contested
    print("\n===Z-RIVAL-DISPATCH===")
    print(f"fg_ok     = {_result.get('fg_ok')}  error={_result.get('error')}")
    print(f"control   = {control}  (F12, no same-keymap rival)")
    print(f"contested = {contested}  (Z vs factory shading pie)")
    print("verdict   =",
          "ADDON ITEM WINS — bare Z reaches tentacle; the factory pie is shadowed"
          if ctrl_ok and z_ok
          else "FACTORY PIE WINS — the user/default item outranks our addon item" if ctrl_ok and not contested
          else "PARTIAL (Z press or release missing — investigate)" if ctrl_ok
          else "INCONCLUSIVE (control key never reached Blender)")
    print("===END===")
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()
    return None


def _go():
    tb._KeymapBridge.install_keymap(_stub, "Z")  # the real product path for the contested key
    # F12 control pair on the SAME addon keymap, same operator — proves delivery + mechanism.
    km = tb._KeymapBridge.keymaps[0][0]
    for value, phase in (("PRESS", "press"), ("RELEASE", "release")):
        kmi = km.keymap_items.new("tentacle.show_marking_menu", type="F12", value=value)
        kmi.properties.phase = phase
    hwnd = _ghost_hwnd()
    x, y = _screen_viewport_point(hwnd) if hwnd else (0, 0)
    threading.Thread(target=_inject, args=(hwnd, x, y), daemon=True).start()
    bpy.app.timers.register(_report_and_quit, first_interval=8.0)
    return None


# Defer until the window + keyconfig have settled (the addon keymap merges on the next event-loop pass).
bpy.app.timers.register(_go, first_interval=2.0)
