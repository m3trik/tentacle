"""Ground-truth GUI test: does a REAL F12 keypress over the viewport show the menu or render?

Launch a fresh GUI Blender (never an existing session)::

    blender --python tentacle/test/blender/gui_keypress_check.py

The headless/diagnose harnesses only prove the operator + keymap *exist*; they cannot prove which
keymap actually wins a physical F12 (region ``3D View`` vs the global ``Screen`` render shortcut).
This injects an OS-level F12 into the foreground Blender window with the cursor parked over the 3D
viewport, then reports whether tentacle's menu became visible or a render fired. Windows-only
(uses ``user32``); requires ``TENTACLE_QT_DEPS`` (or on-demand Qt). It moves the real mouse + sends
a real keystroke — run only when you can spare the focus for ~6 s.
"""
import sys
import os
import ctypes
import threading
import time
from pathlib import Path

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


def _viewport_screen_center():
    """Screen-pixel center of the 3D viewport (Blender Y is bottom-up; Windows is top-down)."""
    win = bpy.context.window
    for area in win.screen.areas:
        if area.type == "VIEW_3D":
            cx = win.x + area.x + area.width // 2
            cy = win.y + win.height - (area.y + area.height // 2)  # flip Y
            return int(cx), int(cy)
    return None


def _send_f12():
    time.sleep(3.0)  # let the window settle + come to foreground
    u = ctypes.windll.user32
    center = _viewport_screen_center()
    if center:
        u.SetCursorPos(*center)
    time.sleep(0.4)
    u.keybd_event(_VK_F12, 0, 0, 0)       # F12 down
    u.keybd_event(_VK_F12, 0, _KEYUP, 0)  # F12 up


def _report_and_quit():
    menu_visible = bool(tb._ACTIVE_TCL is not None and tb._ACTIVE_TCL.isVisible())
    n_windows = len(bpy.context.window_manager.windows)
    rr = bpy.data.images.get("Render Result")
    rendered = bool(rr and rr.has_data) or n_windows > 1
    print("\n===F12-DISPATCH===")
    print(f"menu_visible = {menu_visible}")
    print(f"rendered     = {rendered}  (windows={n_windows})")
    print("verdict      =",
          "MENU WINS" if menu_visible and not rendered
          else "RENDER WINS" if rendered and not menu_visible
          else "INCONCLUSIVE")
    if menu_visible:
        # Phase-0 sizing check: the overlay shown via the real keypress path must be a sane
        # fit_to_window size — non-degenerate and within the screen IT OPENED ON (multi-monitor:
        # comparing against primaryScreen false-fails when Blender is on a secondary display).
        from qtpy import QtWidgets

        geo = tb._ACTIVE_TCL.geometry()
        screen = (QtWidgets.QApplication.screenAt(geo.center())
                  or QtWidgets.QApplication.primaryScreen()).geometry()
        fits = (50 < geo.width() <= screen.width()
                and 50 < geo.height() <= screen.height())
        print(f"sizing       = {'PASS' if fits else 'FAIL'}  "
              f"menu={geo.width()}x{geo.height()}@{geo.x()},{geo.y()} "
              f"screen={screen.width()}x{screen.height()}@{screen.x()},{screen.y()}")
        wh = tb._ACTIVE_TCL.windowHandle()
        print(f"transient    = {bool(wh and wh.transientParent())}  (owned by GHOST window)")
    print("===END===")
    sys.stdout.flush()
    bpy.ops.wm.quit_blender()
    return None


tb.register()
threading.Thread(target=_send_f12, daemon=True).start()
bpy.app.timers.register(_report_and_quit, first_interval=6.0)
