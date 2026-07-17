#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.blender.scene — AST-based, no ``bpy`` required.

``SceneSlots`` imports ``bpy`` at module scope, so it can't be imported outside a real
Blender process (there is no offline ``bpy`` stub in this repo — see
``test_main_workspace_blender.py``), and inside Blender ``uitk``'s Qt layer isn't
importable either. So this pins the structure instead, the way
``test_materials_blender.py`` does.

What's guarded: the Scene Exporter panel launcher moved off the header menu (the old
``b002`` button, now deleted along with its slot method) onto the submenu's Export
expandable list, so ``_EXPORTERS`` is the only route to it. That mattered here in a way it
didn't on the Maya side: Blender's ``_EXPORTERS`` values were *all* ``bpy.ops`` path
strings, and ``list002`` passed them straight to ``invoke_op``. The launcher is a callable,
so ``list002`` had to grow the same callable/op-path split ``list001`` already used for
"Import Maya Scene". Revert that split and the lambda gets handed to ``invoke_op`` as if it
were an operator path — the entry dies with no compile-time error, since the list dispatches
by item text.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_FILE = ROOT / "tentacle" / "slots" / "blender" / "scene.py"


def _class_node(source, class_name):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _class_assign(class_node, name):
    """The value node assigned to ``name`` directly in the class body, or None."""
    for item in class_node.body:
        if isinstance(item, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in item.targets
        ):
            return item.value
    return None


def _method(class_node, name):
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name:
            return item
    return None


class TestSceneExporterOnExportList(unittest.TestCase):
    """SceneSlots (Blender): the Export list is the only route to the Scene Exporter."""

    def setUp(self):
        self.cls = _class_node(SCENE_FILE.read_text(encoding="utf-8"), "SceneSlots")
        self.assertIsNotNone(self.cls, "SceneSlots class not found")

    def test_exporters_registers_the_launcher_as_a_callable(self):
        exporters = _class_assign(self.cls, "_EXPORTERS")
        self.assertIsInstance(exporters, ast.Dict, "_EXPORTERS is not a dict literal")

        # Keyed by the _SCENE_EXPORTER constant, not a repeated string literal — the
        # dict key and list002_init's one-shot filter must not drift apart.
        keyed_by_const = [
            v
            for k, v in zip(exporters.keys, exporters.values)
            if isinstance(k, ast.Name) and k.id == "_SCENE_EXPORTER"
        ]
        self.assertEqual(
            len(keyed_by_const), 1, "_EXPORTERS has no _SCENE_EXPORTER-keyed entry"
        )
        self.assertIsInstance(
            keyed_by_const[0],
            ast.Lambda,
            "the Scene Exporter entry must be a callable, not a bpy.ops path string",
        )

    def test_list002_dispatches_callables_not_just_op_paths(self):
        list002 = _method(self.cls, "list002")
        self.assertIsNotNone(list002, "list002 not found")
        calls = {
            node.func.id
            for node in ast.walk(list002)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn(
            "callable",
            calls,
            "list002 must branch on callable(entry) — otherwise the Scene Exporter "
            "lambda is passed to invoke_op as an operator path",
        )

    def test_header_no_longer_carries_the_button(self):
        # b002's removal is what makes the list the only route; a re-added method
        # would mean the button crept back onto the header menu.
        self.assertIsNone(_method(self.cls, "b002"), "b002 is back on Blender SceneSlots")


if __name__ == "__main__":
    unittest.main()
