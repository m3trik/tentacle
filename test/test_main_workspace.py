#!/usr/bin/python
# coding=utf-8
"""Tests for the main lower submenu's Workspace list (slots/maya/main.py).

The workspace controls (Set Dir / Auto Set / Open Root + recent-workspace
history) live in the Main slot's ``list000`` — the existing Workspace Browser —
above a separator, with the current workspace's directory browser below it.
Recent workspaces are backed by a shared ``RecentValuesStore`` (valid Maya
workspaces only).

AST checks run without Maya; the workspace.mel validation is exercised against a
real Maya when available.
"""
import ast
import os
import shutil
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_PY = ROOT / "tentacle" / "slots" / "maya" / "main.py"

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import main as main_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    main_module = None
    _MAYA_AVAILABLE = False


class ModuleAST:
    def __init__(self, source: str):
        self.source = source
        self.tree = ast.parse(source)

    def _find(self, class_name, method_name):
        for cls in ast.walk(self.tree):
            if isinstance(cls, ast.ClassDef) and cls.name == class_name:
                for fn in cls.body:
                    if (
                        isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and fn.name == method_name
                    ):
                        return fn
        return None

    def has_method(self, class_name, method_name):
        return self._find(class_name, method_name) is not None

    def method_source(self, class_name, method_name):
        fn = self._find(class_name, method_name)
        return ast.get_source_segment(self.source, fn) or "" if fn else ""


class TestMainWorkspaceStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = ModuleAST(MAIN_PY.read_text(encoding="utf-8"))

    def test_workspace_methods_present(self):
        for name in (
            "list000_init",
            "list000",
            "_is_workspace",
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_set_workspace_from_path",
        ):
            self.assertTrue(
                self.mod.has_method("Main", name), f"Main must define {name}"
            )

    def test_list000_builds_store_and_actions(self):
        """list000_init must build the store, add the editing actions, render the
        store's recent values, and label the dir-browser row."""
        init = self.mod.method_source("Main", "list000_init")
        for needle in (
            "RecentValuesStore",
            "workspace_recent_projects",  # shared key → history carries over
            "__set_dir__",
            "__auto__",
            "Current Workspace",  # dir-browser row label
            "valid_values",
            "display_map",
        ):
            self.assertIn(needle, init, f"list000_init must reference {needle}")

    def test_auto_and_recents_nest_under_set_workspace(self):
        """Auto Set + Recent Workspaces live in the Set Workspace flyout, not at
        the root — the root holds only Set Workspace and the dir browser."""
        init = self.mod.method_source("Main", "list000_init")
        # Both the auto action and the recents sub-flyout are added to the Set
        # Workspace sublist (captured as ``set_ws``), not directly to ``widget``.
        self.assertIn('set_ws.sublist.add("Auto Set Workspace"', init)
        self.assertIn('set_ws.sublist.add("Recent Workspaces")', init)

    def test_list000_dispatches_all_row_kinds(self):
        src = self.mod.method_source("Main", "list000")
        for needle in (
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_set_workspace_from_path",
            "__recent__",
            "isdir",  # directory-browser entries (incl. workspace root) open in explorer
        ):
            self.assertIn(needle, src, f"list000 must handle {needle}")

    def test_recent_selection_validates(self):
        src = self.mod.method_source("Main", "_set_workspace_from_path")
        self.assertIn("_is_workspace", src)


class _StubSb:
    def __init__(self, choice=None):
        self.choice = choice
        self.messages = []
        # Setters call self.sb.handlers.marking_menu.hide(); stub it out.
        self.handlers = types.SimpleNamespace(
            marking_menu=types.SimpleNamespace(hide=lambda: None)
        )

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))
        return self.choice


class _StubStore:
    def __init__(self):
        self.recorded = []

    def record(self, value):
        self.recorded.append(value)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSetWorkspaceFromPath(unittest.TestCase):
    """Main._set_workspace_from_path validates workspace.mel before switching."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.inst = main_module.Main.__new__(main_module.Main)
        self.inst.sb = _StubSb()
        self.inst._workspace_store = _StubStore()
        self.root = tempfile.mkdtemp(prefix="main_ws_test_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        cmds.file(new=True, force=True)

    def test_rejects_path_with_no_workspace_mel(self):
        before = cmds.workspace(query=True, rd=True)
        self.inst._set_workspace_from_path(self.root)
        self.assertEqual(before, cmds.workspace(query=True, rd=True))
        self.assertTrue(self.inst.sb.messages, "Expected a user-visible warning")
        self.assertEqual(self.inst._workspace_store.recorded, [])

    def test_accepts_path_with_workspace_mel(self):
        with open(os.path.join(self.root, "workspace.mel"), "w") as f:
            f.write("//Maya workspace stub\n")
        self.inst._set_workspace_from_path(self.root)
        new_ws = cmds.workspace(query=True, rd=True)
        self.assertEqual(
            os.path.normpath(new_ws).lower(), os.path.normpath(self.root).lower()
        )
        # Selecting a recent workspace bumps it to most-recent in the store.
        self.assertIn(self.root, self.inst._workspace_store.recorded)


if __name__ == "__main__":
    unittest.main()
