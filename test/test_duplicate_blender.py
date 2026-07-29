#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.blender.duplicate — AST-based, no ``bpy`` required.

``duplicate.py`` imports ``bpy`` at module scope, so it can't be imported outside a real
Blender process (there is no offline ``bpy`` stub in this repo — see
``test_scene_blender.py``). This pins the ``Duplicate`` slot's structure the way
``test_materials_blender.py`` / ``test_scene_blender.py`` do. Real-``bpy`` behavioral coverage
(actual object-selection outcomes) lives in the manual harness
``test/blender/duplicate_check.py`` — not auto-discovered, run by hand against a fresh Blender.

The tb001 guard below exists because of a real bug fixed on the Maya side
(``tentacle/slots/maya/duplicate.py``): "Select Instanced Objects" dropped the originally
selected object(s) from the final selection, keeping only their *other* instances
(``mayatk.get_instances`` excludes the query objects by default). ``blendertk.get_instances``
doesn't exclude them, so Blender's ``tb001`` was never bitten by the same bug — but nothing
stopped a future edit from re-introducing it by filtering ``instances`` against the original
selection before selecting. This pins the invariant structurally: whatever
``btk.get_instances(selection)`` returns is what gets selected, unfiltered.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUPLICATE_FILE = ROOT / "tentacle" / "slots" / "blender" / "duplicate.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SLOTS_TEST_DIR = str(ROOT / "test" / "slots")
if _SLOTS_TEST_DIR not in sys.path:
    sys.path.insert(0, _SLOTS_TEST_DIR)

from _helpers import attr_chain, iter_calls  # noqa: E402 — generic AST helper, DCC-agnostic


def _class_node(source, class_name):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _method(class_node, name):
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name:
            return item
    return None


def _decorator_chains(method_node):
    chains = []
    for dec in method_node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        chains.append(attr_chain(target))
    return chains


def _call_chains(node):
    """Dotted-chain name (e.g. ``("btk", "get_instances")``) for every call in ``node``'s
    subtree — shared by the routing/forwarding assertions below."""
    return {tuple(attr_chain(c.func)) for c in iter_calls(node)}


class TestDuplicateBlenderStructure(unittest.TestCase):
    """Pins tb000/tb001/tb002/b005 routing + the tb001 anti-regression guard."""

    def setUp(self):
        self.source = DUPLICATE_FILE.read_text(encoding="utf-8")
        self.cls = _class_node(self.source, "Duplicate")
        self.assertIsNotNone(self.cls, "Duplicate class not found")

    def test_tb000_gates_on_fewer_than_two_objects(self):
        """Convert to Instances requires >=2 objects, mirroring the Maya slot's gate."""
        tb000 = _method(self.cls, "tb000")
        self.assertIsNotNone(tb000, "tb000 not found")
        found = any(
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "len"
            and any(isinstance(op, ast.Lt) for op in node.ops)
            for node in ast.walk(tb000)
        )
        self.assertTrue(found, "tb000 must gate on len(objects) < 2")

    def test_tb001_routes_via_get_instances(self):
        tb001 = _method(self.cls, "tb001")
        self.assertIsNotNone(tb001, "tb001 not found")
        self.assertIn(
            ("btk", "get_instances"),
            _call_chains(tb001),
            "tb001 must resolve instances via btk.get_instances",
        )

    def test_tb001_does_not_filter_instances_against_selection(self):
        """Anti-regression: nothing may subtract ``selection`` (or wrap it in a
        comprehension) between the ``btk.get_instances()`` call and the selection
        loop — that's exactly the shape of the bug fixed on the Maya side."""
        tb001 = _method(self.cls, "tb001")
        assigns_to_instances = [
            node
            for node in ast.walk(tb001)
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "instances" for t in node.targets)
        ]
        self.assertTrue(assigns_to_instances, "tb001 has no `instances` assignment")
        for node in assigns_to_instances:
            with self.subTest(line=node.lineno):
                # Every assignment to `instances` must come directly from a
                # btk.get_instances(...) call — never a comprehension/filter
                # derived from another variable (that's how the Maya bug
                # dropped the original selection from the final result).
                self.assertIsInstance(
                    node.value,
                    ast.Call,
                    "instances must be assigned directly from a call, not filtered",
                )
                self.assertEqual(attr_chain(node.value.func), ["btk", "get_instances"])

    def test_tb001_selects_via_select_set_not_bpy_ops(self):
        """Must use the direct select_set loop (mode-independent, Qt-pump-safe) — not
        bpy.ops.object.select_all, which poll-fails in Edit Mode (see the code comment
        this pins)."""
        tb001 = _method(self.cls, "tb001")
        self.assertNotIn(("bpy", "ops", "object", "select_all"), _call_chains(tb001))
        select_set_calls = [
            c for c in iter_calls(tb001) if attr_chain(c.func)[-1:] == ["select_set"]
        ]
        self.assertTrue(select_set_calls, "tb001 must call .select_set(...) directly")

    def test_tb002_forwards_to_auto_instancer_with_summary(self):
        tb002 = _method(self.cls, "tb002")
        self.assertIsNotNone(tb002, "tb002 not found")
        run_once_calls = [
            c
            for c in iter_calls(tb002)
            if attr_chain(c.func) == ["btk", "AutoInstancer", "run_once"]
        ]
        self.assertEqual(
            len(run_once_calls), 1, "tb002 must call btk.AutoInstancer.run_once exactly once"
        )
        kwarg_names = {kw.arg for kw in run_once_calls[0].keywords}
        self.assertIn("return_summary", kwarg_names)

    def test_b005_is_undoable_and_uninstances_selection(self):
        b005 = _method(self.cls, "b005")
        self.assertIsNotNone(b005, "b005 not found")
        self.assertIn(["btk", "undoable"], _decorator_chains(b005))
        self.assertIn(("btk", "uninstance"), _call_chains(b005))


if __name__ == "__main__":
    unittest.main()
