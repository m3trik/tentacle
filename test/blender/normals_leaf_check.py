# !/usr/bin/python
# coding=utf-8
"""Does a single click on a normals-submenu leaf button (Average / Set To Face) execute it?

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/normals_leaf_check.py

Reproduces the user's report ("normals Average / Set To Face often need several clicks"). Unlike
the hover harnesses this needs no flaky radial hover: it shows ``normals#submenu`` directly in the
overlay (the same stacked submenu the gesture lands on), makes Blender's GHOST window hold OS
foreground (the real state after a key-hold — the overlay is visible but may not be OS-active),
then injects ONE real click on each named leaf and records whether its ``clicked`` fired. Runs
with ``tcl_blender.enable_click_debug()`` on, so ``~/tentacle_click_debug.log`` captures what each
click actually hit.

Steals foreground + moves the real mouse for a few seconds — throwaway instance only. Report to
stdout and ``../temp_tests/normals_leaf_out.txt``.
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
                   "normals_leaf_out.txt")
_u = _input.user32
_lines = []


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _find(ui, name):
    from qtpy import QtWidgets

    for b in ui.findChildren(QtWidgets.QAbstractButton):
        if b.objectName() == name and b.isVisible() and b.isEnabled():
            return b
    return None


def _test_leaf(app, tcl, tb, ghost, name, center):
    from qtpy import QtWidgets

    # Park the cursor at screen-center BEFORE showing so the submenu anchors on-screen (a stale
    # cursor put the buttons at negative-Y / off-screen in the first pass), then re-show fresh.
    _u.SetCursorPos(*center)
    time.sleep(0.05)
    tcl._on_activation_press()
    for _ in range(20):
        app.processEvents()
    tcl.show("normals#submenu", force=True)
    for _ in range(30):
        app.processEvents()
    ui = tcl.sb.current_ui
    btn = _find(ui, name) if ui else None
    if btn is None:
        _log(f"  [{name}] SKIP — not found in {ui.objectName() if ui else None!r}")
        return None
    fired = {"n": 0}
    btn.clicked.connect(lambda *a: fired.__setitem__("n", fired["n"] + 1))

    _input.force_foreground(ghost, allow_minimize=False)  # GHOST holds foreground (real state)
    for _ in range(15):
        app.processEvents()

    gp = btn.mapToGlobal(btn.rect().center())
    x, y = int(gp.x()), int(gp.y())
    hit = QtWidgets.QApplication.widgetAt(x, y)
    hit_name = hit.objectName() if hit else None
    on_button = hit_name == name or (hit is not None and btn.isAncestorOf(hit))
    _log(f"  [{name}] click at ({x},{y}) on_screen={x >= 0 and y >= 0} widgetAt={hit_name!r} "
         f"on_button={on_button} fg_is_ghost={_u.GetForegroundWindow() == ghost}")
    if not on_button:
        _log(f"  [{name}] SKIP — target not under cursor (harness positioning); not a product result")
        try:
            tb._KeymapBridge.drive_release()
        except Exception:
            pass
        return None
    # Click up to 3 times (as a frustrated user would) and record which click first fired.
    fired_on = None
    for attempt in range(1, 4):
        _input.click_and_pump(app, x, y)
        if fired["n"] >= 1:
            fired_on = attempt
            break
    needed = str(fired_on) if fired_on else ">3"
    _log(f"  [{name}] first_click_fired={fired_on == 1}  clicks_needed={needed}  (total clicked={fired['n']})")
    try:
        tb._KeymapBridge.drive_release()
    except Exception:
        pass
    for _ in range(15):
        app.processEvents()
    return fired_on == 1


def _run():
    from qtpy import QtWidgets

    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()
    app = QtWidgets.QApplication.instance()
    tb.enable_click_debug()
    ghost = _input.main_ghost_hwnd()
    geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
    center = (geo.center().x(), geo.center().y())
    _log(f"screen center = {center}")
    try:
        results = {}
        for name in ("b006", "tb004", "b000"):   # Set To Face, Average, Soften (all leaves)
            results[name] = _test_leaf(app, tcl, tb, ghost, name, center)
        ok = all(v for v in results.values() if v is not None)
        _log(f"\nVERDICT: {'PASS — single click executes each leaf' if ok else 'FAIL — a leaf needed multiple clicks'}  {results}")
    except Exception as error:
        import traceback
        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
        try:
            tb.disable_click_debug()
        except Exception:
            pass
        # Tail the click-debug log so the captured events show up in this report too.
        try:
            with open(tb._ClickDebugger.path, encoding="utf-8") as f:
                tail = f.read().splitlines()[-40:]
            _log("\n--- tentacle_click_debug.log (tail) ---")
            for ln in tail:
                _log(ln)
        except Exception as e:
            _log("could not read click-debug log:", repr(e))
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
