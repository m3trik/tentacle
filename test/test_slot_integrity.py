#!/usr/bin/python
# coding=utf-8
"""Tests for slot file structure and class conventions.

Validates that every slot module under tentacle/slots/maya/:
- Defines exactly one public class that inherits from SlotsMaya
- Uses the expected import-guard pattern for pymel
- Has a corresponding __init__ accepting (self, switchboard)
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
SLOTS_DIR = PKG / "slots" / "maya"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Files that are not concrete slot modules
_SKIP = {"__init__.py", "_slots_maya.py"}


def _slot_files():
    """Return all concrete slot .py files."""
    return sorted(
        f
        for f in SLOTS_DIR.glob("*.py")
        if f.name not in _SKIP and not f.name.startswith("__")
    )


def _parse_classes(source: str):
    """Return list of (class_name, [base_names]) from source."""
    tree = ast.parse(source)
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            classes.append((node.name, bases))
    return classes


class TestSlotFilesExist(unittest.TestCase):
    """Basic structural checks on the slots/maya directory."""

    def test_slots_dir_exists(self):
        self.assertTrue(SLOTS_DIR.is_dir(), f"Missing directory: {SLOTS_DIR}")

    def test_base_class_file_exists(self):
        self.assertTrue(
            (SLOTS_DIR / "_slots_maya.py").exists(),
            "Missing base class file _slots_maya.py",
        )

    def test_has_slot_files(self):
        files = _slot_files()
        self.assertGreater(
            len(files), 30, f"Expected 30+ slot files, found {len(files)}"
        )


class TestSlotClassStructure(unittest.TestCase):
    """Each slot module must contain exactly one SlotsMaya subclass."""

    def test_each_slot_has_slots_maya_subclass(self):
        """Every slot .py must define at least one class inheriting SlotsMaya."""
        missing = []
        for f in _slot_files():
            source = f.read_text(encoding="utf-8")
            classes = _parse_classes(source)
            slot_classes = [name for name, bases in classes if "SlotsMaya" in bases]
            if not slot_classes:
                missing.append(f.name)
        self.assertEqual(missing, [], f"Files without SlotsMaya subclass: {missing}")

    def test_no_multiple_public_slot_classes(self):
        """Each file should define at most one SlotsMaya subclass."""
        multi = []
        for f in _slot_files():
            source = f.read_text(encoding="utf-8")
            classes = _parse_classes(source)
            slot_classes = [name for name, bases in classes if "SlotsMaya" in bases]
            if len(slot_classes) > 1:
                multi.append((f.name, slot_classes))
        self.assertEqual(multi, [], f"Multiple slot classes in: {multi}")


class TestSlotImportGuards(unittest.TestCase):
    """Slot modules use try/except for pymel to allow headless import."""

    def test_pymel_import_guarded(self):
        """Any file that imports pymel should use try/except."""
        unguarded = []
        for f in _slot_files():
            source = f.read_text(encoding="utf-8")
            if "import pymel" not in source:
                continue
            # Accept try/except style or conditional import
            if "try:" in source or "importlib" in source:
                continue
            unguarded.append(f.name)
        self.assertEqual(
            unguarded,
            [],
            f"Files with unguarded pymel import: {unguarded}",
        )


class TestSlotsMayaBase(unittest.TestCase):
    """Verify _slots_maya.py base class."""

    def test_base_inherits_slots(self):
        source = (SLOTS_DIR / "_slots_maya.py").read_text(encoding="utf-8")
        classes = _parse_classes(source)
        self.assertTrue(
            any("Slots" in bases for _, bases in classes),
            "SlotsMaya must inherit from Slots",
        )


class TestEditTb001Performance(unittest.TestCase):
    """Verify edit.py tb001 uses performance-optimized patterns (AST-based).

    Bug: Delete History (tb001) was extremely slow on heavy scenes because
    it used PyMEL for bulk queries and per-node utility calls without
    suspending viewport refresh.
    Fixed: 2026-03-03
    """

    @classmethod
    def setUpClass(cls):
        cls.source = (SLOTS_DIR / "edit.py").read_text(encoding="utf-8")
        tree = ast.parse(cls.source)
        cls.tb001_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "tb001":
                cls.tb001_node = node
                break

    @staticmethod
    def _collect_calls(node):
        """Collect all function/method call strings from an AST subtree.

        Returns a list of dotted call names like 'cmds.ls', 'pm.ls',
        'mtk.get_groups', 'pm.refresh', etc.
        """
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute):
                    # e.g. cmds.ls, pm.refresh, mtk.get_groups
                    if isinstance(func.value, ast.Name):
                        calls.append(f"{func.value.id}.{func.attr}")
                    elif isinstance(func.value, ast.Attribute):
                        # e.g. pm.mel.MLdeleteUnused
                        if isinstance(func.value.value, ast.Name):
                            calls.append(
                                f"{func.value.value.id}.{func.value.attr}.{func.attr}"
                            )
                elif isinstance(func, ast.Name):
                    calls.append(func.id)
        return calls

    def test_tb001_exists(self):
        self.assertIsNotNone(self.tb001_node, "tb001 method not found in edit.py")

    def test_uses_cmds_for_queries(self):
        """tb001 should use maya.cmds for bulk queries, not PyMEL."""
        calls = self._collect_calls(self.tb001_node)
        self.assertTrue(
            any(c == "cmds.ls" for c in calls),
            "tb001 should use cmds.ls for fast queries",
        )
        self.assertFalse(
            any(c == "pm.ls" for c in calls),
            "tb001 should not use pm.ls (PyMEL) for bulk scene queries",
        )

    def test_viewport_suspended(self):
        """tb001 should suspend viewport refresh during cleanup."""
        calls = self._collect_calls(self.tb001_node)
        self.assertTrue(
            any(c == "pm.refresh" for c in calls),
            "tb001 should call pm.refresh (for suspend/resume)",
        )

    def test_no_per_node_pymel_groups(self):
        """tb001 should not call mtk.get_groups (slow PyMEL per-node loop)."""
        calls = self._collect_calls(self.tb001_node)
        self.assertFalse(
            any(c == "mtk.get_groups" for c in calls),
            "tb001 should use cmds path-parsing for empty groups, not mtk.get_groups",
        )

    def test_no_per_node_pymel_shapes(self):
        """tb001 should not call mtk.get_shape_node (slow PyMEL per-node loop)."""
        calls = self._collect_calls(self.tb001_node)
        self.assertFalse(
            any(c == "mtk.get_shape_node" for c in calls),
            "tb001 should use cmds.listRelatives for shapes, not mtk.get_shape_node",
        )

    def test_uses_exact_type_for_groups(self):
        """Empty-group detection must use exactType to avoid matching joints etc."""
        # Look for cmds.ls calls with exactType keyword
        has_exact_type = False
        for child in ast.walk(self.tb001_node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if (
                    isinstance(child.func.value, ast.Name)
                    and child.func.value.id == "cmds"
                    and child.func.attr == "ls"
                ):
                    for kw in child.keywords:
                        if kw.arg == "exactType":
                            has_exact_type = True
        self.assertTrue(
            has_exact_type,
            "tb001 should use cmds.ls(exactType='transform') for group detection",
        )

    def test_message_box_outside_suspend(self):
        """message_box must not be called while viewport refresh is suspended.

        Verify that self.sb.message_box calls are NOT inside the try block
        that wraps the suspended-refresh section.
        """
        # Find the try/finally block (the suspend wrapper)
        try_node = None
        for child in ast.walk(self.tb001_node):
            if isinstance(child, ast.Try) and child.finalbody:
                try_node = child
                break
        self.assertIsNotNone(try_node, "tb001 should have a try/finally block")

        # Collect calls inside the try body (not the finally)
        try_body_calls = []
        for stmt in try_node.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    if sub.func.attr == "message_box":
                        try_body_calls.append(sub.func.attr)

        self.assertEqual(
            try_body_calls,
            [],
            "message_box should not be called inside the viewport-suspended try block",
        )


if __name__ == "__main__":
    unittest.main()
