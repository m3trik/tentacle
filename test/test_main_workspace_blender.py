#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.blender.main's Workspace list (``list000``).

Sibling of ``test_main_workspace.py`` (the Maya side of this exact feature) — kept
AST-based like every other Blender slot test (``test_materials_blender.py``,
``test_blender_slots.py``) because ``tentacle.slots.blender._slots_blender`` imports
``bpy`` at module scope, so the module can't be imported outside a real Blender process
(no offline ``bpy`` stub in this repo). ``Main._is_workspace``/``btk.find_workspaces`` are
pure ``os``-path logic already covered behaviorally in blendertk's own test suite
(``test_reference_manager.py``); this file pins the *wiring* — that Blender's ``list000``
mirrors Maya's Set Workspace / Auto Set Workspace / Recent Workspaces structure at the
behavior level (including the folder-icon differentiator on the dir-browser rows), per
``main.py``'s module docstring.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_PY = ROOT / "tentacle" / "slots" / "blender" / "main.py"


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
            "_auto_set_workspace",
            "_switch_to_workspace",
            "_open_workspace_editor",
            # MainMixin hooks
            "_current_workspace_root",
            "_browse_workspace_dir",
            "_create_default_workspace",
        ):
            self.assertTrue(
                self.mod.has_method("Main", name), f"Main must define {name}"
            )

    def test_does_not_reimplement_shared_flow(self):
        """Set Workspace / recent selection live once in ``slots/_main.py``
        (``MainMixin``, pinned by ``test_main_workspace.py``); the fork supplies
        hooks only."""
        for name in ("_set_workspace_interactive", "_set_workspace_from_path"):
            self.assertFalse(
                self.mod.has_method("Main", name),
                f"{name} belongs to MainMixin — the fork must not re-implement it",
            )
        self.assertIn("class Main(MainMixin, SlotsBlender)", self.mod.source)

    def test_list000_builds_store_and_actions(self):
        """list000_init must build the store, add the editing actions, render the
        store's recent values, and icon the dir-browser row."""
        init = self.mod.method_source("Main", "list000_init")
        for needle in (
            "RecentValuesStore",
            "workspace_recent_projects_blender",  # namespaced -- must not collide with Maya's key
            "__set_dir__",
            "__auto__",
            'set_label_icon(w, "folder_filled")',  # dir-browser root row gets a folder icon
            "valid_values",
            "display_map",
        ):
            self.assertIn(needle, init, f"list000_init must reference {needle}")

    def test_no_separator_between_actions_and_browser(self):
        """The old titled separator is gone — the folder icon on the dir rows is the
        differentiator now, so no Separator widget should be constructed or imported."""
        init = self.mod.method_source("Main", "list000_init")
        self.assertNotIn("Separator(", init, "no Separator widget should be added")
        self.assertNotIn("widgets.separator", init, "no Separator import should remain")

    def test_dir_browser_rows_get_folder_icon(self):
        """Every dir-browser row (root + each nested folder) is marked with the
        folder icon so it reads as a directory, not an action — parity with Maya."""
        init = self.mod.method_source("Main", "list000_init")
        self.assertIn('set_label_icon(w, "folder_filled")', init)
        populate = self.mod.method_source("Main", "_populate_dir_contents")
        self.assertIn('set_label_icon(item, "folder_filled")', populate)

    def test_auto_and_recents_nest_under_set_workspace(self):
        """Auto Set + Recent Workspaces live in the Set Workspace flyout, not at
        the root — the root holds only Set Workspace and the dir browser."""
        init = self.mod.method_source("Main", "list000_init")
        self.assertIn('set_ws.sublist.add("Auto Set Workspace"', init)
        self.assertIn('set_ws.sublist.add("Recent Workspaces")', init)

    def test_set_workspace_is_always_present(self):
        """Unlike the old inert hint row, Set Workspace must be added unconditionally
        (not gated behind an ``if workspace:`` — that was the dead-end this ported)."""
        init = self.mod.method_source("Main", "list000_init")
        set_ws_line = next(
            line for line in init.splitlines() if 'widget.add("Set Workspace"' in line
        )
        self.assertIn('data="__set_dir__"', set_ws_line)
        self.assertNotIn(
            "Save the .blend to browse its folder",
            init,
            "the old inert/unclickable hint row must be gone",
        )

    def test_list000_dispatches_all_row_kinds(self):
        src = self.mod.method_source("Main", "list000")
        for needle in (
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_open_workspace_editor",
            "_set_workspace_from_path",
            "__recent__",
            "os.path.isdir",  # dir-browser entries (folders only, like Maya's tree)
        ):
            self.assertIn(needle, src, f"list000 must handle {needle}")

    def test_set_workspace_hooks_pin_via_dir_picker_and_shared_template(self):
        """Mirror of Maya's Set Workspace: a directory picker feeding the session
        pin — NOT the old Open/Save-As file-dialog workaround, which predates Blender
        having real workspace state (``btk.set_current_workspace``). A pick that is
        neither a marked project nor a folder of .blend files is OFFERED (by the
        shared flow) as a new workspace built from the shared template —
        ``btk.create_workspace``: marker + rule folders — never silently pinned
        as-is and never built unasked."""
        browse = self.mod.method_source("Main", "_browse_workspace_dir")
        self.assertIn("getExistingDirectory", browse)
        self.assertNotIn("wm.open_mainfile", self.mod.source)
        self.assertNotIn("wm.save_as_mainfile", self.mod.source)
        self.assertIn(
            "btk.create_workspace",
            self.mod.method_source("Main", "_create_default_workspace"),
        )

    def test_switch_pins_records_and_reports(self):
        """_switch_to_workspace = pin + recent-store bump + toast — the twin of Maya's
        ``cmds.workspace(path, openWorkspace=True)`` switch."""
        src = self.mod.method_source("Main", "_switch_to_workspace")
        self.assertIn("btk.set_current_workspace", src)
        self.assertIn("_workspace_store.record", src)

    def test_auto_set_resolves_then_pins(self):
        """Auto Set resolves from the open file (marked root walk-up) and actually
        switches — no more find-and-record-only toast."""
        src = self.mod.method_source("Main", "_auto_set_workspace")
        self.assertIn("btk.current_workspace", src)
        self.assertIn("_switch_to_workspace", src)

    def test_editor_row_opens_workspace_editor_panel(self):
        """The Edit Workspace row opens blendertk's workspace_editor panel (Maya's
        twin row opens the native Project Window)."""
        init = self.mod.method_source("Main", "list000_init")
        self.assertIn('widget.add("Edit Workspace", data="__editor__")', init)
        src = self.mod.method_source("Main", "_open_workspace_editor")
        self.assertIn('marking_menu.show("workspace_editor")', src)

    def test_is_workspace_uses_find_workspaces_primitive(self):
        """DRY: must delegate to btk.find_workspaces, not hand-roll a .blend scan."""
        src = self.mod.method_source("Main", "_is_workspace")
        self.assertIn("btk.find_workspaces", src)


if __name__ == "__main__":
    unittest.main()
