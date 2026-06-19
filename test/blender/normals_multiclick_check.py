# !/usr/bin/python
# coding=utf-8
"""Reproduce "Average / Set To Face need up to four clicks" — the *grab-held* leaf click.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/normals_multiclick_check.py

Why the earlier harnesses (``normals_leaf_check`` / ``repeat_gesture_check``) all PASS yet the bug
persists live: they activate with ``drive_press()`` and **no buttons**, so the MarkingMenu never
holds the mouse grab (their logs show ``grab=None`` at click time) and ``_chord_gesture`` is False.
But the user reaches ``normals`` through a **chord** (hold the key + a mouse button → main/edit →
Normals), and a chord activation *grabs the mouse* (``_transfer_mouse_control``) and sets
``_chord_gesture=True``. With the grab held, a leaf's left press is routed to the **menu** instead
of the button — exactly the state the passing harnesses skip.

This harness reproduces that state: ``drive_press(buttons=Right)`` (real grab + chord), show
``normals#submenu``, then inject REAL OS clicks on ``b006`` (Set To Face) and ``tb004`` (Average),
pumping ``MouseTracking.track()`` between steps the way the live chord poller does. It clicks each
leaf up to 6 times and records how many clicks it took to fire (and what the menu did on a dead
click — e.g. jumped to ``cameras``). The real slot is disconnected so a fired action can't pop a
modal and wedge the harness; only a click counter is wired. A clean fix fires every leaf on click #1.

Steals foreground + moves the real mouse for a few seconds — throwaway instance only. Report to
stdout and ``../temp_tests/normals_multiclick_out.txt``.
"""
import sys
import os
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _input  # noqa: E402

MONO = Path(__file__).resolve().parents[3]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests",
                   "normals_multiclick_out.txt")
_u = _input.user32
_lines = []
LDOWN, LUP = _input.BTN["L"]


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _finish(tb=None):
    """Always write the report and quit Blender — even on an early error (so the throwaway
    instance never sits open)."""
    if tb is not None:
        try:
            tb.disable_click_debug()
        except Exception:
            pass
        try:
            with open(tb._ClickDebugger.path, encoding="utf-8") as f:
                tail = f.read().splitlines()[-50:]
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


def _find(ui, name):
    from qtpy import QtWidgets

    for b in ui.findChildren(QtWidgets.QAbstractButton):
        if b.objectName() == name and b.isVisible() and b.isEnabled():
            return b
    return None


def _grab_name(tcl):
    from qtpy import QtWidgets

    g = QtWidgets.QWidget.mouseGrabber()
    return None if g is None else ("tcl" if g is tcl else type(g).__name__)


def _show_normals(app, tcl):
    tcl.show("normals#submenu", force=True)
    for _ in range(25):
        app.processEvents()
    ui = tcl.sb.current_ui
    return ui if (ui and ui.objectName() == "normals#submenu") else None


def _rearm_chord_on_normals(app, tcl, tb):
    """Reset to the exact unlucky live state: a chord grab held by the MENU (grab=tcl), normals
    submenu shown, and NO MouseTracking.track() run yet (so the grab has not migrated to the
    button). This is the window a click falls into when it beats the 0.02s poller tick."""
    from qtpy import QtCore

    try:
        tb._KeymapBridge.drive_release()
    except Exception:
        pass
    for _ in range(15):
        app.processEvents()
    tb._KeymapBridge.drive_press(buttons=QtCore.Qt.RightButton)  # grab=tcl, chord_active=True
    for _ in range(15):
        app.processEvents()
    _show_normals(app, tcl)


def _click_leaf(app, tcl, tb, name, label, attempts=3):
    from qtpy import QtWidgets

    _log(f"\n  --- {label} ({name}) ---")
    fired = {"n": 0}
    wired = {"btn": None}

    def _wire(btn):
        if btn is not None and btn is not wired["btn"]:
            # Measure click registration WITHOUT running the real slot (a fired slot could pop a
            # modal and wedge this blocking harness). clicked still emits; we just count it.
            try:
                btn.clicked.disconnect()
            except Exception:
                pass
            btn.clicked.connect(lambda *a: fired.__setitem__("n", fired["n"] + 1))
            wired["btn"] = btn

    for attempt in range(1, attempts + 1):
        # Re-arm the unlucky state fresh each attempt: grab on the MENU, no track() yet.
        _rearm_chord_on_normals(app, tcl, tb)
        ui = tcl.sb.current_ui
        if not (ui and ui.objectName() == "normals#submenu"):
            _log(f"    attempt {attempt}: SKIP — normals not shown (got {ui.objectName() if ui else None!r})")
            continue
        btn = _find(ui, name)
        if btn is None:
            _log(f"    attempt {attempt}: SKIP — {name} not found")
            continue
        _wire(btn)
        gp = btn.mapToGlobal(btn.rect().center())
        x, y = int(gp.x()), int(gp.y())
        before_n = fired["n"]
        grab_before = _grab_name(tcl)

        # A plain click — NO track() pumped first, so the grab stays on the menu (the unlucky
        # window). Pump only Qt (what the real event pump does); never call track() here.
        _u.SetCursorPos(x, y)
        for _ in range(15):
            app.processEvents()
        _u.mouse_event(LDOWN, 0, 0, 0, 0)
        for _ in range(15):
            app.processEvents()
        _u.mouse_event(LUP, 0, 0, 0, 0)
        for _ in range(20):
            app.processEvents()

        after_ui = tcl.sb.current_ui
        after = after_ui.objectName() if after_ui else None
        hit = QtWidgets.QApplication.widgetAt(x, y)
        hit_name = hit.objectName() if hit else None
        got = fired["n"] > before_n
        _log(f"    attempt {attempt}: fired={got} grab_before={grab_before} grab_after={_grab_name(tcl)} "
             f"ui ->{after!r} widgetAt={hit_name!r}")

    n_fired = fired["n"]
    _log(f"    => {label}: fired {n_fired}/{attempts} attempts  "
         f"{'(ALL DEAD — reproduced)' if n_fired == 0 else '(all fired)' if n_fired == attempts else '(intermittent)'}")
    return n_fired


def _run():
    tb = None
    try:
        # Provision the monorepo + a Qt binding FIRST (importing tcl_blender runs _QtBootstrap,
        # which puts PySide6 + qtpy on sys.path), THEN import qtpy — under --factory-startup the
        # normal startup provisioning is skipped, so importing qtpy first would ModuleNotFoundError.
        for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
            _p = str(MONO / _pkg)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        os.environ.setdefault("QT_API", "pyside6")
        from tentacle import tcl_blender as tb  # noqa: F811  (provisions Qt on import)
        from qtpy import QtWidgets

        tcl = tb._KeymapBridge.tcl or tb.launch()
        app = QtWidgets.QApplication.instance()
        tb.enable_click_debug()

        try:
            _input.force_foreground(int(tcl.winId()), allow_minimize=False)
        except Exception:
            pass

        # Each leaf is clicked while the chord grab is held by the MENU (re-armed per attempt
        # inside _click_leaf) — the unlucky window a real click hits before the 0.02s poller's
        # track() migrates the grab to the button. A dead click here == the live bug.
        ATTEMPTS = 3
        results = {}
        results["Set To Face"] = _click_leaf(app, tcl, tb, "b006", "Set To Face", ATTEMPTS)
        results["Average"] = _click_leaf(app, tcl, tb, "tb004", "Average", ATTEMPTS)

        try:
            tb._KeymapBridge.drive_release()
        except Exception:
            pass
        for _ in range(20):
            app.processEvents()

        dead = {k: f"{v}/{ATTEMPTS} fired" for k, v in results.items() if v < ATTEMPTS}
        _log(f"\nRESULTS (attempts fired, of {ATTEMPTS}): {results}")
        if dead:
            _log(f"VERDICT: REPRODUCED — dead clicks on a menu-held grab: {dead}")
        else:
            _log("VERDICT: every click fired (not reproduced)")
    except Exception as error:
        import traceback
        _log("HARNESS ERROR:", repr(error))
        _log(traceback.format_exc())
    finally:
        _finish(tb)
    return None


bpy.app.timers.register(_run, first_interval=4.0)
