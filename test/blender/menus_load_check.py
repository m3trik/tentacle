"""GUI harness: load EVERY ported Blender menu through the real ``tcl.show()`` path.

Launch a **fresh** GUI Blender (never an existing session — session-safety rule)::

    blender --factory-startup --python tentacle/test/blender/menus_load_check.py

For each Blender slot domain this exercises the full stack — switchboard UI load, slot-class
discovery + connection, every ``<widget>_init`` (option-box builds, hide-policies), and a real
render via ``show()`` — the live-session verification the headless harnesses can't give
(``--background`` has no GUI windows, and several inits touch real widgets). Prints one OK/FAIL
line per domain and quits.
"""
import sys
import os
import traceback
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for _pkg in ("pythontk", "uitk", "tentacle", "blendertk"):
    _p = str(MONO / _pkg)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("QT_API", "pyside6")

import bpy
from tentacle import tcl_blender as tb

# Every Blender slot domain (slot-file stems); hud's UI is the hud#startmenu overlay.
DOMAINS = [
    "animation", "cameras", "crease", "deformation", "display", "duplicate", "edit",
    "editors", "hud#startmenu", "lighting", "main", "materials", "normals", "nurbs",
    "pivot", "polygons", "preferences", "rendering", "rigging", "scene", "selection",
    "settings", "subdivision", "symmetry", "transform", "utilities", "uv",
]

lines = []


def log(*args):
    print(*args)
    sys.stdout.flush()


def _quit():
    bpy.ops.wm.quit_blender()
    return None


def _run():
    try:
        log("=== BLENDER-MENUS-LOAD ===")
        log("blender:", bpy.app.version_string)
        tb.register()
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        tcl = tb._ACTIVE_TCL
        for name in DOMAINS:
            try:
                # show() returns the shown widget: the overlay for startmenu/submenu-tagged
                # UIs, a standalone window for regular menus — check THAT, not the overlay.
                shown = tcl.show(name)
                for _ in range(20):
                    app.processEvents()
                visible = shown is not None and bool(shown.isVisible())
                ui = tcl.sb.get_ui(name)
                slot_cls = type(ui.slots).__name__ if getattr(ui, "slots", None) else None
                if shown is not None:
                    shown.hide()
                tcl.hide()
                for _ in range(10):
                    app.processEvents()
                ok = visible and slot_cls is not None
                lines.append(
                    f"{'OK  ' if ok else 'FAIL'} {name} | visible={visible} slots={slot_cls}"
                )
            except Exception as error:
                lines.append(f"FAIL {name} | {error!r}")
                lines.append(traceback.format_exc())
    except Exception as error:
        lines.append(f"FAIL setup: {error!r}")
        lines.append(traceback.format_exc())
    finally:
        for line in lines:
            log(line)
        ok = all(line.startswith("OK") for line in lines)
        log(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
        bpy.app.timers.register(_quit, first_interval=1.0)
    return None


# Defer until the UI + keyconfig have settled (GUI main loop is required for the timer to fire).
bpy.app.timers.register(_run, first_interval=2.5)
