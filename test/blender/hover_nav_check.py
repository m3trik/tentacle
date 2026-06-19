# !/usr/bin/python
# coding=utf-8
"""Does hover-navigation (the Maya gesture) work over Blender — with vs without the grab?

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/hover_nav_check.py

The shared marking menu navigates submenus on **hover** (``child_enterEvent`` opens a
``MenuButton``'s target), and executes a leaf by clicking it. In Maya the plain key-hold does
NOT grab the mouse, so child enter/leave events reach the buttons (hover-nav works) and a leaf
click reaches the leaf (executes). The Blender bridge's ``_KeymapBridge.drive_press`` grabs the
mouse unconditionally — and an explicit Qt mouse grab suppresses enter/leave delivery to other
widgets, so hover-nav can't fire and the click is re-read as the ``F12|LeftButton`` chord.

Experiment: arm ``main#startmenu`` with and without the grab, then move the real cursor ONTO a
navigating ``MenuButton`` in small steps and dwell, reporting whether ``current_ui`` becomes the
button's target submenu (hover-nav worked).

  * ``with_grab`` — today's Blender path. Expected (bug): hover-nav does NOT fire.
  * ``no_grab``   — the Maya path. Expected (fix): hover opens the target submenu.

If ``no_grab`` navigates on hover while ``with_grab`` doesn't, the fix is to stop grabbing for
the no-button activation in ``tcl_blender._KeymapBridge.drive_press`` (grab only when a button is
held, matching the shared ``_transfer_mouse_control``).

Steals foreground + moves the real mouse for a few seconds — throwaway instance only. Report to
stdout and ``../temp_tests/hover_nav_out.txt``.
"""
import sys
import os
import time
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "hover_nav_out.txt")
_u = _input.user32
_lines = []


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _menu_button(ui):
    from uitk.widgets.menuButton import MenuButton

    for b in ui.findChildren(MenuButton):
        if b.isVisible() and b.isEnabled() and b.property("target") and b.width() > 8:
            return b
    return None


def _hover_to(app, x, y, steps=14):
    """Glide the real cursor to (x, y) in small steps with relative jiggles so GHOST and Qt
    both generate the move/enter events hover-nav depends on, then dwell. Pumps Qt throughout."""
    sx, sy = 700, 450
    _u.SetCursorPos(sx, sy)
    for i in range(1, steps + 1):
        cx = int(sx + (x - sx) * i / steps)
        cy = int(sy + (y - sy) * i / steps)
        _u.SetCursorPos(cx, cy)
        _u.mouse_event(_input.MOUSE_MOVE, 1, 0, 0, 0)   # nudge so GHOST refreshes hover
        _u.mouse_event(_input.MOUSE_MOVE, -1, 0, 0, 0)
        for _ in range(3):
            app.processEvents()
        time.sleep(0.03)
    # Dwell on the target so the enter event + any hover debounce settle.
    t0 = time.time()
    while time.time() - t0 < 0.8:
        app.processEvents()
        time.sleep(0.02)


def _run_case(tb, tcl, name, grab):
    from qtpy import QtWidgets

    app = QtWidgets.QApplication.instance()
    _log(f"\n=== case: {name} (grab={grab}) ===")
    _u.SetCursorPos(700, 450)
    time.sleep(0.1)
    tcl._on_activation_press()
    if grab:
        try:
            tcl.grabMouse()
        except Exception:
            pass
    for _ in range(30):
        app.processEvents()
    tcl.show("main#startmenu", force=True)
    for _ in range(30):
        app.processEvents()

    ui = tcl.sb.current_ui
    btn = _menu_button(ui) if ui else None
    if btn is None:
        _log("  FAIL: no navigating MenuButton")
    else:
        target = btn.property("target")
        gp = btn.mapToGlobal(btn.rect().center())
        _log(f"  start_ui={ui.objectName()!r} hover->button={btn.objectName()!r} target={target!r}")
        _hover_to(app, int(gp.x()), int(gp.y()))
        after = tcl.sb.current_ui
        after_name = after.objectName() if after else None
        navigated = bool(after_name and target and target in after_name)
        _log(f"  after hover: current_ui={after_name!r}  hover_nav_worked={navigated}")
        _log(f"  VERDICT: {'OK — hover opened target submenu' if navigated else 'NO hover-nav'}")

    try:
        tb._KeymapBridge.drive_release()
    except Exception:
        pass
    for _ in range(20):
        app.processEvents()


def _run():
    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()
    try:
        _run_case(tb, tcl, "with_grab", grab=True)
        _run_case(tb, tcl, "no_grab", grab=False)
    except Exception as error:
        import traceback
        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
        report = "\n".join(_lines)
        os.makedirs(os.path.dirname(os.path.normpath(OUT)), exist_ok=True)
        with open(os.path.normpath(OUT), "w", encoding="utf-8") as f:
            f.write(report)
        print("\n[written to]", os.path.normpath(OUT))
        sys.stdout.flush()

        def _quit():
            bpy.ops.wm.quit_blender()
            return None

        bpy.app.timers.register(_quit, first_interval=1.0)
    return None


bpy.app.timers.register(_run, first_interval=4.0)
