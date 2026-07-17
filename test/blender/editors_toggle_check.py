# !/usr/bin/python
# coding=utf-8
"""GUI harness: editors ``b009`` (docked Timeline toggle) + ``b010`` (script-output skin).

Drives the **real** ``Editors`` slot methods in a fresh GUI Blender so both run the way a live
click does (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/editors_toggle_check.py

* **b009** — Maya parity is a *docked* toggle (``btk.toggle_editor("Timeline")``): first click
  closes the docked Timeline in place, second click re-docks it along the bottom of the viewport
  — never spawning a floating window. Asserts the area count, the re-dock geometry (bottom +
  viewport-width), and that no new window appears.
* **b010** — the console is a TRUE dock in the main window (``btk.QtDock``: the
  ``uitk.ScriptOutput`` widget embedded as a native CHILD window of the GHOST window, glued
  to a docked area's content region — no overlay, no separate spawned window), and the
  widget + redirect persist across hide/show — a live "opens but looks empty" symptom was
  reopening a fresh instance each time, discarding history. Checks: docking adds an area to
  the MAIN window's screen with NO new ``bpy.Window`` spawned; the console's OS parent IS
  the GHOST window; the child rect fills the area's content region minus the exposed native
  resize strip at its top (win32-measured, physical px — no dpr math on either side; the
  strip keeps Blender's area-edge grab band Blender-owned so the border drag resizes instead
  of selecting text); a printed marker survives a hide→show cycle (the actual
  persistence fix) alongside a fresh marker printed after reshowing; hiding fully undocks
  the area; show/hide persist the visible-flag (sandboxed via
  ``ScriptConsole._state_dir_override``).

Writes ``tentacle/test/temp_tests/editors_toggle_out.json``. A wedged Blender never writes it —
the caller's timeout + taskkill handles that.
"""
import sys
import os
import json
import traceback
from pathlib import Path
from types import SimpleNamespace as NS

import bpy

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

TEMP = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_tests")
)
OUT = os.path.join(TEMP, "editors_toggle_out.json")
SANDBOX = os.path.join(TEMP, "editors_toggle_state")  # sandboxed persisted-flag dir
R = {"b009": {}, "b010": {}, "checks": []}


def _flag():
    """The sandboxed persisted visible-flag (None = no/unreadable state file)."""
    try:
        with open(os.path.join(SANDBOX, "blendertk_script_output.json"), encoding="utf-8") as f:
            return json.load(f).get("visible")
    except Exception:
        return None


def ck(name, cond, extra=""):
    R["checks"].append({"name": name, "pass": bool(cond), "extra": str(extra)})


def make_slot(cls):
    """Instance without the UI-loading ``__init__`` (b009/b010 touch neither sb.ui nor loaded_ui)."""
    slot = cls.__new__(cls)
    slot.sb = NS(message_box=lambda *a, **k: None)
    return slot


def timelines():
    import blendertk as btk

    return btk.find_editor("Timeline")


def _b009():
    try:
        import shutil
        from blendertk.env_utils import script_output as so

        # Sandbox the console's persisted visible-flag BEFORE tb.launch() — TclBlender's
        # __init__ runs script_output.restore(), and without the override both it and the
        # b010 toggles below would read/clobber the user's REAL Blender config.
        shutil.rmtree(SANDBOX, ignore_errors=True)
        os.makedirs(SANDBOX, exist_ok=True)
        so.ScriptConsole._state_dir_override = SANDBOX

        from tentacle import tcl_blender as tb

        if tb._KeymapBridge.tcl is None:
            tb.launch()
        from tentacle.slots.blender.editors import Editors

        slot = make_slot(Editors)
        win0 = bpy.context.window_manager.windows[0]

        R["b009"]["initial_timelines"] = len(timelines())
        ck("b009: a Timeline is docked at startup", len(timelines()) == 1,
           f"n={len(timelines())}")

        slot.b009()  # hide
        R["b009"]["after_hide"] = len(timelines())
        ck("b009: first click hides the docked Timeline in place", len(timelines()) == 0,
           f"n={len(timelines())}")

        slot.b009()  # show (re-dock)
        tl = timelines()
        R["b009"]["after_show"] = len(tl)
        ck("b009: second click re-docks a Timeline", len(tl) == 1, f"n={len(tl)}")
        if tl:
            _win, area = tl[0]
            v3ds = [a for a in win0.screen.areas if a.type == "VIEW_3D"]
            v3d = max(v3ds, key=lambda a: a.height) if v3ds else None
            R["b009"]["timeline_geo"] = {"x": area.x, "y": area.y, "w": area.width, "h": area.height}
            R["b009"]["viewport_geo"] = (
                {"x": v3d.x, "y": v3d.y, "w": v3d.width, "h": v3d.height} if v3d else None
            )
            ck("b009: re-docked Timeline sits below the viewport (bottom strip)",
               v3d is not None and area.y < v3d.y, f"tl.y={area.y} v3d.y={v3d.y if v3d else None}")
            ck("b009: re-docked Timeline spans the viewport width",
               v3d is not None and abs(area.width - v3d.width) <= 4,
               f"tl.w={area.width} v3d.w={v3d.width if v3d else None}")
            ck("b009: re-docked Timeline height is a strip (~edge_size)", area.height <= 160,
               f"h={area.height}")

        R["b009"]["n_windows"] = len(bpy.context.window_manager.windows)
        ck("b009: toggle never spawned a floating window",
           len(bpy.context.window_manager.windows) == 1,
           f"windows={len(bpy.context.window_manager.windows)}")
    except Exception:
        R["b009"]["error"] = traceback.format_exc()
    bpy.app.timers.register(_b010_show, first_interval=0.5)
    return None


def _main_areas():
    return bpy.context.window_manager.windows[0].screen.areas


def _b010_show():
    try:
        from tentacle.slots.blender.editors import Editors
        from blendertk.env_utils import script_output as so
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        R["b010"]["qapp_present"] = app is not None
        R["b010"]["skin_supported"] = so.QtDock.supported()
        R["b010"]["platform"] = sys.platform
        R["_wins_before_b010"] = len(bpy.context.window_manager.windows)
        R["_areas_before_b010"] = len(_main_areas())

        make_slot(Editors).b010()  # toggle -> show (docks the Info Log into the main window)
        for _ in range(20):
            if app:
                app.processEvents()
    except Exception:
        R["b010"]["error_show"] = traceback.format_exc()
    bpy.app.timers.register(_b010_measure, first_interval=1.0)
    return None


def _b010_measure():
    try:
        from blendertk.env_utils import script_output as so
        from blendertk.ui_utils.blender_window import BlenderWindow
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        inst = so.ScriptConsole._instance
        R["b010"]["no_new_window_spawned"] = (
            len(bpy.context.window_manager.windows) == R.get("_wins_before_b010", 0)
        )
        R["b010"]["area_docked_in_main_window"] = (
            len(_main_areas()) == R.get("_areas_before_b010", 0) + 1
        )
        R["b010"]["skin_built"] = inst is not None and inst.widget is not None
        R["b010"]["is_open"] = inst is not None and inst.is_open()
        R["b010"]["flag_after_show"] = _flag()
        ck("b010: embedding is supported here (win32 + QApplication)", R["b010"].get("skin_supported"),
           f"platform={sys.platform} qapp={R['b010'].get('qapp_present')}")
        ck("b010: docking spawned NO new bpy.Window (true dock, not a separate window)",
           R["b010"]["no_new_window_spawned"],
           f"windows_before={R.get('_wins_before_b010')} windows_after={len(bpy.context.window_manager.windows)}")
        ck("b010: Info Log area appears in the MAIN window's screen",
           R["b010"]["area_docked_in_main_window"],
           f"areas_before={R.get('_areas_before_b010')} areas_after={len(_main_areas())}")
        ck("b010: uitk.ScriptOutput widget was BUILT (formatted console)", R["b010"].get("skin_built"))
        ck("b010: console reports is_open() True after show", R["b010"]["is_open"])
        ck("b010: show persists visible=true (sandboxed state file)",
           R["b010"]["flag_after_show"] is True)

        if inst is not None and inst.widget is not None:
            import ctypes
            from ctypes import wintypes

            if app:
                app.processEvents()
            skin = inst.widget
            u = ctypes.windll.user32
            hwnd = inst._dock._hwnd
            child = int(skin.winId())
            parent_now = int(u.GetParent(ctypes.c_void_p(child)) or 0)
            R["b010"]["child_parent"] = parent_now
            ck("b010: console is a true CHILD of the main GHOST window",
               hwnd is not None and parent_now == int(hwnd),
               f"parent={parent_now} ghost={hwnd}")
            rect = wintypes.RECT()
            u.GetWindowRect(ctypes.c_void_p(child), ctypes.byref(rect))
            pt = wintypes.POINT(0, 0)
            u.ClientToScreen(ctypes.c_void_p(int(hwnd or 0)), ctypes.byref(pt))
            actual = [rect.left - pt.x, rect.top - pt.y,
                      rect.right - rect.left, rect.bottom - rect.top]
            region = inst._dock.content_region()
            base = BlenderWindow.region_client_rect(hwnd, region) if region else None
            # The child starts BELOW the region top by the dock's edge pad — the native
            # area-edge grab band stays Blender-owned (resize, not text selection).
            pad = inst._dock._edge_pad
            expected = [base[0], base[1] + pad, base[2], base[3] - pad] if base else None
            R["b010"]["skin_geo"] = actual
            R["b010"]["expected_rect"] = expected
            R["b010"]["skin_visible"] = skin.isVisible()
            ck("b010: console widget is visible", skin.isVisible())
            if expected:
                delta = max(abs(a - e) for a, e in zip(actual, expected))
                R["b010"]["geo_delta"] = delta
                ck("b010: console fills the content region minus the resize strip (<=2px)",
                   delta <= 2, f"delta={delta} actual={actual} expected={expected} pad={pad}")
            else:
                ck("b010: console fills the content region minus the resize strip (<=2px)",
                   False, "no docked region")

            # The actual bug report: printed output must reach the console AND survive a
            # hide -> show cycle (the prior design rebuilt a fresh, empty widget every reopen).
            print("EDITORS_TOGGLE_CHECK_MARKER_1 (printed before hide)")
            if app:
                app.processEvents()
            R["b010"]["marker1_visible_before_hide"] = (
                "EDITORS_TOGGLE_CHECK_MARKER_1" in skin.toPlainText()
            )
            ck("b010: print() reaches the console through the real slot path",
               R["b010"]["marker1_visible_before_hide"])
    except Exception:
        R["b010"]["error_measure"] = traceback.format_exc()
    bpy.app.timers.register(_b010_hide, first_interval=0.5)
    return None


def _b010_hide():
    try:
        from tentacle.slots.blender.editors import Editors
        from blendertk.env_utils import script_output as so
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        inst = so.ScriptConsole._instance

        make_slot(Editors).b010()  # toggle -> hide
        for _ in range(10):
            if app:
                app.processEvents()

        R["b010"]["areas_after_hide"] = len(_main_areas())
        R["b010"]["area_undocked_on_hide"] = (
            len(_main_areas()) == R.get("_areas_before_b010", 0)
        )
        R["b010"]["is_open_after_hide"] = inst is not None and inst.is_open()
        R["b010"]["skin_survives_hide"] = inst is not None and inst.widget is not None
        R["b010"]["flag_after_hide"] = _flag()
        ck("b010: hide fully undocks the Info Log area",
           R["b010"]["area_undocked_on_hide"],
           f"areas_before={R.get('_areas_before_b010')} areas_after_hide={R['b010']['areas_after_hide']}")
        ck("b010: is_open() False after hide", not R["b010"]["is_open_after_hide"])
        ck("b010: console widget itself is NOT destroyed by hide (capture keeps running)",
           R["b010"]["skin_survives_hide"])
        ck("b010: hide persists visible=false (sandboxed state file)",
           R["b010"]["flag_after_hide"] is False)
    except Exception:
        R["b010"]["error_hide"] = traceback.format_exc()
    bpy.app.timers.register(_b010_reshow, first_interval=0.5)
    return None


def _b010_reshow():
    try:
        from tentacle.slots.blender.editors import Editors
        from blendertk.env_utils import script_output as so
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        inst = so.ScriptConsole._instance

        print("EDITORS_TOGGLE_CHECK_MARKER_2 (printed before reshow — must NOT appear yet)")
        make_slot(Editors).b010()  # toggle -> show again
        for _ in range(20):
            if app:
                app.processEvents()

        R["b010"]["areas_after_reshow"] = len(_main_areas())
        R["b010"]["area_redocked_on_reshow"] = (
            len(_main_areas()) == R.get("_areas_before_b010", 0) + 1
        )
        ck("b010: reshow re-docks the Info Log area", R["b010"]["area_redocked_on_reshow"],
           f"areas={R['b010']['areas_after_reshow']}")

        if inst is not None and inst.widget is not None:
            text = inst.widget.toPlainText()
            R["b010"]["marker1_survived_hide_cycle"] = "EDITORS_TOGGLE_CHECK_MARKER_1" in text
            R["b010"]["marker2_visible_after_reshow"] = "EDITORS_TOGGLE_CHECK_MARKER_2" in text
            ck("b010: THE FIX — a marker printed before hide is still in the console after "
               "hide->show (history isn't lost on reopen)",
               R["b010"]["marker1_survived_hide_cycle"])
            ck("b010: a marker printed while hidden also shows once reshown (capture ran "
               "in the background)",
               R["b010"]["marker2_visible_after_reshow"])

        make_slot(Editors).b010()  # toggle -> hide (cleanup)
        for _ in range(10):
            if app:
                app.processEvents()
    except Exception:
        R["b010"]["error_reshow"] = traceback.format_exc()
    bpy.app.timers.register(_finish, first_interval=0.5)
    return None


def _finish():
    import shutil

    R["verdict"] = "PASS" if R["checks"] and all(c["pass"] for c in R["checks"]) else "FAIL"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, default=str)
    shutil.rmtree(SANDBOX, ignore_errors=True)  # temp_tests artifacts clean up in teardown
    print("editors_toggle verdict:", R["verdict"])
    print(json.dumps(R["checks"], indent=2))
    sys.stdout.flush()
    bpy.app.timers.register(_quit, first_interval=0.4)
    return None


def _quit():
    """Quit with an explicit window override. From a bpy timer the context window can be
    NULL (e.g. an OS-owned Qt overlay held focus, clearing Blender's winactive) and
    ``wm.quit_blender`` then crashes in ``wm_exit_schedule_delayed``."""
    windows = bpy.context.window_manager.windows
    if windows:
        with bpy.context.temp_override(window=windows[0]):
            bpy.ops.wm.quit_blender()
    else:
        bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(_b009, first_interval=4.0)
