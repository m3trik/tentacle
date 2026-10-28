"""GUI harness: the editors start menu shows Blender's buttons and hides Maya's (no dead links).

Launch a **fresh** GUI Blender (never an existing session)::

    blender --factory-startup --python tentacle/test/blender/editors_relabel_check.py

The start menu's ``.ui`` is shared by both hosts. Maya's main-window chrome toggles and its
Dependency Graph (``b006``/``b007``/``b008``/``b012``/``b013``) have no Blender counterpart, so the
``.ui`` tags them ``requires="maya"``; the editors Blender shows in their place
(``b014``-``b018``: Geometry Nodes, UV, Image, Graph and Text editors) are ``requires="blender"``.
uitk's ``Switchboard.apply_visibility_policy`` hides a widget whose tag the host lacks. This shows
the editors menu through the real ``tcl.show()`` path and reads each button's live visibility and
label (the policy runs at registration, so only the loaded widget proves it). Editor *opening* is
proven headless by ``deepened_slots_check.py`` (every name a Blender editor).
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
# A throwaway Blender: keep its settings off the developer's live uitk stores.
from uitk.testing import TestSandbox  # noqa: E402

try:
    TestSandbox.activate()
except ImportError:  # a first launch: tentacle provisions Qt as it imports
    from tentacle import tcl_blender  # noqa: E402, F401

    TestSandbox.activate()

import bpy  # noqa: E402 - after the sandbox, as every GUI harness
from tentacle import tcl_blender as tb  # noqa: E402

lines = []

# Blender's buttons: their label, shown
BLENDER_BUTTONS = {
    "b014": "Geometry Nodes",
    "b015": "UV Editor",
    "b016": "Image Editor",
    "b017": "Graph Editor",
    "b018": "Text Editor",
}
# Maya's buttons: hidden here by their requires tag
MAYA_BUTTONS = ("b006", "b007", "b008", "b012", "b013")
# buttons both hosts serve keep their .ui label
SHARED = {"b001": "Outliner", "b005": "Node Editor"}


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
        shown = tcl.show("editors#startmenu")
        for _ in range(20):
            app.processEvents()
        ui = tcl.sb.get_ui("editors#startmenu")

        def button(name):
            return ui.findChild(QtWidgets.QAbstractButton, name)

        for name, label in BLENDER_BUTTONS.items():
            w = button(name)
            check(
                f"{name} shows '{label}'",
                w is not None and not w.isHidden() and w.text() == label,
                f"hidden={w is not None and w.isHidden()} text={w.text() if w else None!r}",
            )
        for name in MAYA_BUTTONS:
            w = button(name)
            check(
                f"{name} (Maya's) is hidden by its requires tag",
                w is not None
                and w.isHidden()
                and getattr(w, "hidden_by_policy", None) == "requires",
                f"hidden={w is not None and w.isHidden()} "
                f"policy={getattr(w, 'hidden_by_policy', None)}",
            )
        for name, label in SHARED.items():
            w = button(name)
            check(
                f"{name} keeps its .ui label '{label}'",
                w is not None and not w.isHidden() and w.text() == label,
                f"text={w.text() if w else None!r}",
            )

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
