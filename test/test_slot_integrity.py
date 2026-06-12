#!/usr/bin/python
# coding=utf-8
"""Maya-specific slot-file conventions.

- No pymel imports (the package is fully migrated to maya.cmds).
- edit.py tb001 heavy-scene performance patterns.
- 30+ slot files sanity floor.

The DCC-agnostic invariants (package/base wiring, one base-subclass per file, unique
objectNames) moved to the parametrized ``test_dcc_invariants.py`` (plan M1).
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


class TestSlotFilesExist(unittest.TestCase):
    """Maya-specific sanity floor (wiring/uniqueness checks live in test_dcc_invariants)."""

    def test_has_slot_files(self):
        files = _slot_files()
        self.assertGreater(
            len(files), 30, f"Expected 30+ slot files, found {len(files)}"
        )


class TestNoPymelImports(unittest.TestCase):
    """Slot modules must not import pymel — the package is migrated to cmds."""

    def test_no_pymel_imports(self):
        offenders = []
        for f in _slot_files():
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] == "pymel" for a in node.names):
                        offenders.append(f.name)
                        break
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] == "pymel":
                        offenders.append(f.name)
                        break
        self.assertEqual(
            offenders, [], f"Slot files re-introduced pymel: {offenders}"
        )


class TestEditTb001Performance(unittest.TestCase):
    """Verify edit.py tb001 uses performance-optimized patterns (AST-based).

    Heavy-scene performance requires bulk cmds queries and a viewport-
    refresh suspend wrapper; PyMEL paths and per-node utility loops are
    forbidden in this hot path.
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
            any(c == "cmds.refresh" for c in calls),
            "tb001 should call cmds.refresh (for suspend/resume)",
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
