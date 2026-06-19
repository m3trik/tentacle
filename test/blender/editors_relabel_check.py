"""GUI harness: the editors start-menu buttons relabel + open real editors (no dead links).

Launch a **fresh** GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/editors_relabel_check.py

The five Maya buttons with no Blender analogue (Dependency Graph / Status Line / Shelf /
Help Line / Tool Box) are relabeled per-DCC in ``Editors.bNNN_init`` to a substitute editor;
the shared ``.ui`` keeps the Maya text for the Maya slot, so the relabel must happen live on
the loaded widget. This shows the editors menu through the real ``tcl.show()`` path and reads
the actual ``QPushButton.text()`` to prove the relabel took (and that kept buttons are
untouched). Editor *opening* itself is proven separately (every ui_type opens — probe), so the
no-dead-links guarantee is the headless check in ``deepened_slots_check.py``.
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

lines = []

# expected live label after _init relabel (substitute editor names)
EXPECTED_RELABEL = {
    "b006": "Geometry Nodes",
    "b007": "UV Editor",
    "b008": "Image Editor",
    "b012": "Graph Editor",
    "b013": "Text Editor",
}
# a couple of kept buttons whose .ui label must be untouched by the Blender slot
EXPECTED_KEPT = {"b001": "Outliner", "b005": "Node Editor"}


def log(*a):
    print(*a)
    sys.stdout.flush()


def check(name, cond, detail=""):
    lines.append(f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + detail) if detail else ''}")


def _quit():
    bpy.ops.wm.quit_blender()
    return None


def _run():
    try:
        tb.register()
        from qtpy import QtWidgets

        app = QtWidgets.QApplication.instance()
        tcl = tb._KeymapBridge.tcl
        # The 14 editor buttons live in the radial start-menu UI (where the per-button
        # _init relabel fires); 'editors' is a base shell without them.
        shown = tcl.show("editors#startmenu")
        for _ in range(20):
            app.processEvents()
        ui = tcl.sb.get_ui("editors#startmenu")

        def btn_text(name):
            w = ui.findChild(QtWidgets.QAbstractButton, name)
            return w.text() if w is not None else None

        for name, expected in EXPECTED_RELABEL.items():
            got = btn_text(name)
            check(f"{name} relabeled to '{expected}'", got == expected, f"text={got!r}")
        for name, expected in EXPECTED_KEPT.items():
            got = btn_text(name)
            check(f"{name} keeps its .ui label '{expected}'", got == expected, f"text={got!r}")

        if shown is not None:
            shown.hide()
        tcl.hide()
    except Exception as error:
        lines.append(f"FAIL setup: {error!r}")
        lines.append(traceback.format_exc())
    finally:
        for line in lines:
            log(line)
        ok = all(line.startswith("OK") for line in lines) and lines
        log(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
        bpy.app.timers.register(_quit, first_interval=1.0)
    return None


bpy.app.timers.register(_run, first_interval=2.5)
