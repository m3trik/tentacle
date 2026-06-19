# !/usr/bin/python
# coding=utf-8
"""Confirm the root cause of "cameras/editors hover-reveal regions don't launch" in Blender.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --python tentacle/test/blender/cameras_track_check.py

The cameras nav button ``i000`` ("Camera Options") lives inside ``visible_on_mouse_over`` Regions
(``region_3`` → ``region_5``) — hidden until the cursor enters, revealed by
``Region.on_enter`` → ``show_top_level_children``. During a CHORD menu the marking menu holds a
mouse grab, which suppresses Qt's native ``enterEvent``; the grab-time fallback that synthesizes
enter events for non-grabbable widgets (Regions) is ``MouseTracking.track()``.

But ``MouseTracking.eventFilter`` only calls ``track()`` while a mouse button is held, tested via
``QApplication.mouseButtons()`` — and that is **blind to GHOST's mouse in Blender**. So during a
Blender chord ``track()`` never runs → the Region never reveals ``i000`` → the region "doesn't
launch". This harness proves it:

  A. open the cameras chord, put the cursor over the region, and confirm ``i000`` stays hidden
     while ``QApplication.mouseButtons()`` reads empty (the blind gate).
  B. drive ``MouseTracking.track()`` directly (bypassing the blind gate) and confirm ``i000``
     becomes visible — i.e. tracking is the cure; only the button-detection gate is broken.

Quits itself. Report to stdout and ``../temp_tests/cameras_track_out.txt``.
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
                   "cameras_track_out.txt")
_u = _input.user32
_lines = []


def _log(*args):
    msg = " ".join(str(a) for a in args)
    _lines.append(msg)
    print(msg)
    sys.stdout.flush()


def _find_i000(ui):
    from uitk.widgets.menuButton import MenuButton

    for b in ui.findChildren(MenuButton):
        if b.property("target"):
            return b
    return None


def _region_chain(widget):
    """The Region ancestors of *widget*, outermost first."""
    from uitk.widgets.region import Region

    chain = []
    p = widget.parent()
    while p is not None:
        if isinstance(p, Region):
            chain.append(p)
        p = p.parent()
    return list(reversed(chain))


def _run():
    from qtpy import QtCore, QtWidgets

    for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
        _p = str(MONO / _pkg)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    os.environ.setdefault("QT_API", "pyside6")
    from tentacle import tcl_blender as tb

    tcl = tb._KeymapBridge.tcl or tb.launch()
    app = QtWidgets.QApplication.instance()
    try:
        tb._KeymapBridge.drive_press(buttons=QtCore.Qt.LeftButton)
        for _ in range(25):
            app.processEvents()
        tcl.show("cameras#startmenu", force=True)
        for _ in range(25):
            app.processEvents()
        ui = tcl.sb.current_ui
        if ui is None or ui.objectName() != "cameras#startmenu":
            _log(f"FAIL: cameras#startmenu not current (got {ui.objectName() if ui else None!r})")
            return
        try:
            ui.register_children()
        except Exception:
            pass
        for _ in range(15):
            app.processEvents()

        i000 = _find_i000(ui)
        if i000 is None:
            _log("FAIL: i000 not found")
            return
        chain = _region_chain(i000)
        _log(f"i000 region chain (outer->inner): {[r.objectName() for r in chain]}")
        outer = chain[0] if chain else i000

        # widgetAt() (used by track()) only resolves the menu's regions if the overlay is the
        # topmost window at that pixel. Real usage keeps it above Blender via window-ownership;
        # the harness must assert it explicitly or z-order flakes the reveal (memory: real-OS
        # Qt widgetAt/activation is unreliable in tests).
        try:
            _input.force_foreground(int(tcl.winId()), allow_minimize=False)
        except Exception:
            pass
        tcl.raise_()
        for _ in range(15):
            app.processEvents()
        gp = outer.mapToGlobal(outer.rect().center())
        topmost = QtWidgets.QApplication.widgetAt(int(gp.x()), int(gp.y()))
        _log(f"overlay topmost at region center: widgetAt={topmost.objectName() if topmost else None!r} "
             f"(None/foreign → z-order will block the reveal)")

        # --- A: normal tracking — the blind gate blocks reveal -----------------------------
        _u.SetCursorPos(int(gp.x()), int(gp.y()))
        for _ in range(10):
            app.processEvents()
        time.sleep(0.2)
        # Nudge a real move so the (gated) MouseTracking.eventFilter runs as it would live.
        _u.mouse_event(_input.MOUSE_MOVE, 1, 0, 0, 0)
        _u.mouse_event(_input.MOUSE_MOVE, -1, 0, 0, 0)
        for _ in range(10):
            app.processEvents()
        mb = QtWidgets.QApplication.mouseButtons()
        mb_empty = (mb == QtCore.Qt.NoButton)
        grabber = QtWidgets.QWidget.mouseGrabber()
        _log(f"A normal: QApplication.mouseButtons()={mb!r} empty={mb_empty} (blind→empty)  "
             f"grab={'tcl' if grabber is tcl else type(grabber).__name__ if grabber else None}  "
             f"track_on_drag_only={tcl.mouse_tracking.track_on_drag_only}")
        _log(f"A normal: i000.isVisible()={i000.isVisible()}  "
             f"{'(hidden — region never revealed: the bug)' if not i000.isVisible() else '(visible)'}")

        # --- B: drive track() directly (what the bridge poller does) -----------------------
        # This is the shipped fix's mechanism: the bpy-timer poller calls MouseTracking.track()
        # during a chord (chord_active), because GHOST never delivers MouseMove to the grabbed
        # overlay. Driving it here (cursor over the region) must reveal the nested nav button.
        for _ in range(4):  # cascade through nested Regions (one enter per call)
            tcl.mouse_tracking.update_child_widgets()
            tcl.mouse_tracking.track()
            for _ in range(8):
                app.processEvents()
            time.sleep(0.05)
        revealed = i000.isVisible()
        _log(f"B track(): i000.isVisible()={revealed}  "
             f"{'(REVEALED — tracking is the cure)' if revealed else '(still hidden — track() alone is not enough)'}")

        # --- C: hover-nav onto the revealed button must open the submenu -------------------
        nav_ok = False
        if revealed:
            ig = i000.mapToGlobal(i000.rect().center())
            _u.SetCursorPos(int(ig.x()), int(ig.y()))
            for _ in range(4):
                tcl.mouse_tracking.update_child_widgets()
                tcl.mouse_tracking.track()
                for _ in range(8):
                    app.processEvents()
                time.sleep(0.05)
            after = tcl.sb.current_ui
            after_name = after.objectName() if after else None
            nav_ok = after_name == "cameras#lower#submenu"
            _log(f"C nav   : current_ui={after_name!r}  "
                 f"{'(OK — hover opened cameras#lower#submenu)' if nav_ok else '(submenu did not open on hover)'}")

        ok = revealed and nav_ok and mb_empty
        _log(f"\nVERDICT: {'FIX MECHANISM CONFIRMED — poller-driven track() reveals + navigates' if ok else 'INCOMPLETE — see above'}")

        tb._KeymapBridge.drive_release()
        for _ in range(15):
            app.processEvents()
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
