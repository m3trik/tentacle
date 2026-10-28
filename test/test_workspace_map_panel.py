#!/usr/bin/python
# coding=utf-8
"""The Workspace Map panel's Slots class (``slots/tools/workspace_map.py``).

It reaches its host only through ``self.tk`` -- the host library's
``WorkspaceMap`` (the scan) and ``EnvUtils`` (switching project, publishing a
template) -- so a fake toolkit stands in for ``mtk`` and records what the panel
asks of it: plain unittest, no DCC. The tree is written through stand-in items
(no Qt). A Maya tool for now (``tentacle.slots.tools.HOSTS``): in Maya the same
class scans real workspace folders through the real ``mtk``. The scan's own
behavior is mayatk's ``test_workspace.py``.
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools import HOSTS
from tentacle.slots.tools.workspace_map import WorkspaceMapSlots


class _FakeItem:
    """Minimal QTreeWidgetItem stand-in (no Qt needed to pin the tree's shape)."""

    def __init__(self, parent=None):
        self.texts = {}
        self.values = {}
        self.children = []
        if parent is not None:
            parent.children.append(self)

    def setText(self, column, text):
        self.texts[column] = text

    def setData(self, column, role, value):
        self.values[column] = value

    def data(self, column, role):
        return self.values.get(column)


class _FakeTree(_FakeItem):
    def __init__(self):
        super().__init__()
        self.clear_calls = 0
        self.current = None

    def clear(self):
        self.clear_calls += 1
        self.children = []

    def expandAll(self):
        pass

    def currentItem(self):
        return self.current


TREE = {
    "projects": {
        "path": "/projects",
        "type": "directory",
        "workspaces": {
            "alpha": {"type": "workspace", "path": "/projects/alpha", "scene_count": 2, "size_mb": 1.5},
            "beta": {"type": "workspace", "path": "/projects/beta", "scene_count": 0, "size_mb": 0},
        },
    }
}


def _panel(tk=None):
    """A ``WorkspaceMapSlots`` over a mock ui (a stand-in tree) and *tk* (a fake
    whose scan answers :data:`TREE`), handed over before the panel is built, as
    ``Slots.tk`` is."""
    sb = mock.MagicMock()
    if tk is None:
        tk = mock.MagicMock()
        engine = tk.WorkspaceMap.return_value
        engine.current_working_dir = "/projects"
        engine.current_workspace = "/projects/alpha"
        engine.recursive_search = True
        engine.get_workspace_tree_data.return_value = TREE
    sb.tk = tk
    sb.QtWidgets.QTreeWidgetItem = _FakeItem
    sb.QtCore.Qt.UserRole = 0
    sb.loaded_ui.workspace_map.tree000 = _FakeTree()
    return WorkspaceMapSlots(sb), sb


def _rows(tree):
    """``(folder, workspace, scenes, size)`` per workspace row."""
    return [
        (folder.texts[0], row.texts[0], row.texts[1], row.texts[2])
        for folder in tree.children
        for row in folder.children
    ]


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.tmp = tempfile.mkdtemp(prefix="ws_map_panel_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class TestWorkspaceMapPanel(_PanelCase):
    def test_a_maya_tool_until_blendertk_has_the_engine(self):
        self.assertEqual(HOSTS["workspace_map"], ("maya",))

    def test_opens_on_the_scan_root_and_scans_once_shown(self):
        slots, sb = _panel()
        sb.loaded_ui.workspace_map.txt000.setText.assert_called_once_with("/projects")
        sb.defer_with_timer.assert_called_once()
        slots.engine.invalidate_workspace_data.assert_not_called()
        sb.defer_with_timer.call_args.args[0]()  # the deferred first scan
        slots.engine.invalidate_workspace_data.assert_called_once_with()

    def test_the_tree_has_a_row_per_folder_and_workspace(self):
        slots, sb = _panel()
        slots.update_tree()
        tree = sb.loaded_ui.workspace_map.tree000
        self.assertEqual(
            _rows(tree),
            [("projects", "alpha", "2", "1.5 MB"), ("projects", "beta", "0", "0.0 MB")],
        )
        self.assertEqual(tree.children[0].values[0], TREE["projects"])

    def test_refilling_never_duplicates_rows(self):
        """Filtering refills on every keystroke: without the clear, one more copy
        of every row per character typed."""
        slots, sb = _panel()
        slots.update_tree()
        slots.update_tree()
        tree = sb.loaded_ui.workspace_map.tree000
        self.assertEqual(len(_rows(tree)), 2)
        self.assertEqual(tree.clear_calls, 2)

    def test_the_filter_narrows_through_the_engine(self):
        slots, _sb = _panel()
        slots.filter_workspaces("alp")
        slots.engine.get_workspace_tree_data.assert_called_with("alp")

    def test_a_new_valid_root_rescans(self):
        slots, sb = _panel()
        sb.loaded_ui.workspace_map.txt000.text.return_value = self.tmp
        slots.update_current_dir()
        self.assertEqual(slots.engine.current_working_dir, os.path.normpath(self.tmp))
        sb.loaded_ui.workspace_map.txt000.set_action_color.assert_called_with("reset")
        slots.engine.get_workspace_tree_data.assert_called_with(None)

    def test_an_invalid_root_clears_the_tree(self):
        slots, sb = _panel()
        slots.update_tree()
        missing = os.path.join(self.tmp, "missing")
        slots.update_current_dir(missing)
        self.assertEqual(sb.loaded_ui.workspace_map.tree000.children, [])
        self.assertEqual(slots.engine.current_working_dir, "/projects")
        sb.loaded_ui.workspace_map.txt000.set_action_color.assert_called_with("invalid")

    def test_the_buttons_browse_set_and_rescan(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.workspace_map
        slots.b001()
        ui.txt000.setText.assert_called_with("/projects/alpha")
        slots.b002()
        slots.engine.invalidate_workspace_data.assert_called_once_with()
        slots._browse_option = mock.MagicMock()
        slots.b000()
        slots._browse_option.browse.assert_called_once_with()

    def test_recursive_search_rescans_only_on_a_change(self):
        slots, _sb = _panel()
        slots.chk000(2)  # stateChanged's Qt.Checked: already on
        slots.chk000(True)
        slots.engine.invalidate_workspace_data.assert_not_called()
        slots.chk000(False)
        self.assertIs(slots.engine.recursive_search, False)
        self.assertEqual(slots.engine.invalidate_workspace_data.call_count, 1)

    def test_rechecking_recursive_search_turns_it_back_on(self):
        """``toggled`` sends a bool, which is an int: read as a check state,
        ``True == 2`` turned the search OFF, so it could never come back on."""
        slots, _sb = _panel()
        slots.chk000(False)
        slots.chk000(True)
        self.assertIs(slots.engine.recursive_search, True)
        self.assertEqual(slots.engine.invalidate_workspace_data.call_count, 2)

    def test_double_clicking_a_workspace_makes_it_the_project(self):
        slots, sb = _panel()
        tree = sb.loaded_ui.workspace_map.tree000
        tree.current = _FakeItem()
        tree.current.setData(0, 0, {"type": "workspace", "path": self.tmp})
        sb.tk.EnvUtils.set_current_workspace.return_value = self.tmp
        slots.btn_open_workspace()
        sb.tk.EnvUtils.set_current_workspace.assert_called_once_with(self.tmp)
        self.assertIn(self.tmp, sb.message_box.call_args.args[0])

    def test_a_folder_row_opens_nothing(self):
        slots, sb = _panel()
        tree = sb.loaded_ui.workspace_map.tree000
        tree.current = _FakeItem()
        tree.current.setData(0, 0, {"type": "directory", "path": self.tmp})
        slots.btn_open_workspace()
        sb.tk.EnvUtils.set_current_workspace.assert_not_called()

    def test_new_project_builds_from_the_active_template(self):
        slots, sb = _panel()
        sb.input_dialog.return_value = " shot_010 "
        slots.engine.create_project.return_value = mock.MagicMock(root="/projects/shot_010")
        slots.new_project()
        slots.engine.create_project.assert_called_once_with("shot_010")
        self.assertIn("/projects/shot_010", sb.message_box.call_args.args[0])

    def test_marking_a_marked_root_says_so(self):
        with open(os.path.join(self.tmp, "workspace.mel"), "w", encoding="utf-8") as f:
            f.write('workspace -fr "scene" "scenes";\n')
        slots, sb = _panel()
        slots.engine.current_working_dir = self.tmp
        slots.mark_root()
        slots.engine.mark_root_as_project.assert_not_called()
        self.assertIn("already a project", sb.message_box.call_args.args[0])

    def test_save_template_publishes_through_the_host(self):
        slots, sb = _panel()
        sb.input_dialog.return_value = "studio"
        sb.tk.EnvUtils.save_workspace_template.return_value = "studio"
        slots.save_template()
        sb.tk.EnvUtils.save_workspace_template.assert_called_once_with("studio")
        sb.tk.EnvUtils.save_workspace_template.side_effect = ValueError("No file rules")
        slots.save_template()
        self.assertEqual(sb.message_box.call_args.args[0], "No file rules")


def _make_workspace(parent, name):
    """A marked workspace folder (``workspace.mel``) holding one scene."""
    root = os.path.join(parent, name)
    os.makedirs(os.path.join(root, "scenes"), exist_ok=True)
    with open(os.path.join(root, "workspace.mel"), "w", encoding="utf-8") as f:
        f.write('workspace -fr "scene" "scenes";\n')
    with open(os.path.join(root, "scenes", "scene1.ma"), "w", encoding="utf-8") as f:
        f.write("//Maya ASCII scene\n")
    return root


@unittest.skipUnless(MAYA_AVAILABLE, "needs a Maya runtime")
class TestWorkspaceMapPanelInMaya(_PanelCase):
    """The panel's tree over the real ``mtk.WorkspaceMap`` scan (the cases
    mayatk's ``TestWorkspaceMapTreePopulation`` held before the panel moved)."""

    def setUp(self):
        super().setUp()
        for name in ("alpha", "beta"):
            _make_workspace(self.tmp, name)
        self.slots, self.sb = _panel(tk=maya_module("mayatk"))
        self.slots.engine.current_working_dir = self.tmp
        self.tree = self.sb.loaded_ui.workspace_map.tree000

    def test_refilling_does_not_duplicate_rows(self):
        self.slots.update_tree()
        first = len(_rows(self.tree))
        self.assertGreaterEqual(first, 2)
        self.slots.update_tree()
        self.assertEqual(len(_rows(self.tree)), first)

    def test_the_filter_narrows_instead_of_appending(self):
        self.slots.update_tree()
        self.slots.update_tree(filter_text="alpha")
        self.assertEqual([row[1] for row in _rows(self.tree)], ["alpha"])


if __name__ == "__main__":
    unittest.main()
