#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.blender.materials — AST-based, no ``bpy`` required.

Pins the ``@btk.undoable`` decoration convention documented in
``tentacle/slots/blender/edit.py`` ("the undoable wrap sits on the action helpers, not the
list handlers — the handlers also fire for category/expand clicks, which would otherwise
push no-op undo steps"): the Assign list's ``list000``/``list001`` dispatch handlers must
stay undecorated, while the mutation helpers they call (and the sibling b-button actions)
must stay wrapped so Ctrl+Z reverts a Blender material assignment. A raw ``bpy.data`` edit
(``btk.assign_mat`` -> ``data.materials.clear()``/``append()``) pushes nothing onto Blender's
undo stack on its own -- see ``blendertk.core_utils.undoable``'s docstring.

This module was born from a real gap: ``list000``'s "assign an existing material by name"
and "release-on-root reassigns current material" paths both routed through
``_assign_named``, which was missing ``@btk.undoable`` while every sibling assignment
action (b004/b005/b006/b014/b015) had it -- so Ctrl+Z silently no-op'd for those two paths
only. Fixed by decorating ``_assign_named`` directly; this test guards the regression.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATERIALS_FILE = ROOT / "tentacle" / "slots" / "blender" / "materials.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SLOTS_TEST_DIR = str(ROOT / "test" / "slots")
if _SLOTS_TEST_DIR not in sys.path:
    sys.path.insert(0, _SLOTS_TEST_DIR)

from _helpers import attr_chain  # noqa: E402 — generic AST helper, DCC-agnostic


def _method_decorators(source, class_name, method_name):
    """Dotted-chain decorators (e.g. ``["btk", "undoable"]``) on a class method, or None
    if the class/method isn't found."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ):
                    chains = []
                    for dec in item.decorator_list:
                        target = dec.func if isinstance(dec, ast.Call) else dec
                        chains.append(attr_chain(target))
                    return chains
    return None


class TestAssignListUndoableConvention(unittest.TestCase):
    """MaterialsSlots (Blender): undo-decoration must sit on helpers, not list handlers."""

    def setUp(self):
        self.source = MATERIALS_FILE.read_text(encoding="utf-8")

    def test_assign_named_is_undoable(self):
        """_assign_named (list000's root-release + named-leaf target) must be wrapped —
        this is the exact method the undo gap was found in."""
        decorators = _method_decorators(self.source, "MaterialsSlots", "_assign_named")
        self.assertIsNotNone(decorators, "_assign_named not found in MaterialsSlots")
        self.assertIn(
            ["btk", "undoable"],
            decorators,
            "_assign_named must be @btk.undoable — a raw btk.assign_mat edit pushes no "
            "undo step on its own, so Ctrl+Z would silently no-op after assigning a "
            "material by name (or reassigning the current one) via the Assign list.",
        )

    def test_list_handlers_stay_undecorated(self):
        """list000/list001 dispatch on every category/expand click too — decorating the
        handler itself (instead of the helper it calls) would push no-op undo steps."""
        for handler in ("list000", "list001"):
            with self.subTest(handler=handler):
                decorators = _method_decorators(self.source, "MaterialsSlots", handler)
                self.assertIsNotNone(decorators, f"{handler} not found in MaterialsSlots")
                self.assertNotIn(["btk", "undoable"], decorators)

    def test_sibling_assignment_actions_stay_undoable(self):
        """Locks in the existing convention _assign_named was missing: every other
        material-assignment / bulk-mutation action in the class stays wrapped."""
        for method in ("b004", "b005", "b006", "b014", "b015"):
            with self.subTest(method=method):
                decorators = _method_decorators(self.source, "MaterialsSlots", method)
                self.assertIsNotNone(decorators, f"{method} not found in MaterialsSlots")
                self.assertIn(["btk", "undoable"], decorators)


if __name__ == "__main__":
    unittest.main()
