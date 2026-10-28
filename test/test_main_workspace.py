#!/usr/bin/python
# coding=utf-8
"""Tests for the Workspace tab of tentacle.slots.main (the one Main Slots class).

The tab (``list000``): Set Workspace (browse -> offer to build a default
workspace -> open), Auto Set Workspace, Recent Workspaces, Edit Workspace, the
current workspace's dir browser and the Scene Directory row. It reaches its host
only through ``self.tk``: a fake toolkit records what each step asks of it (plain
pytest), and in Maya the same class drives the real ``mtk``. Blender-shaped
answers are pinned in ``test_main_workspace_blender.py``; the operations
themselves (``EnvUtils.is_workspace`` / ``set_current_workspace`` / ...) in mayatk
and blendertk.
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.main import MainSlots

cmds = maya_module("maya.cmds")


class _Store:
    """A ``RecentValuesStore`` double: each settings key's history, shared by the
    stores built on it (as QSettings is)."""

    histories = {}

    def __init__(self, settings_key=None, validator=None, **_):
        self.key = settings_key
        self.validator = validator
        self._values = _Store.histories.setdefault(settings_key, [])

    @property
    def values(self):
        return list(self._values)

    def add(self, value):
        if value not in self._values:
            self._values.append(value)

    def record(self, value):
        if value in self._values:
            self._values.remove(value)
        self._values.insert(0, value)

    def valid_values(self):
        return [v for v in self._values if self.validator is None or self.validator(v)]

    def display_map(self, values):
        return {v: os.path.basename(v) for v in values}


class _StubRow:
    """An ExpandableList row: what ``add()`` was given, readable back through
    ``item_data()`` the way the dispatcher reads a clicked row."""

    def __init__(self, label, data, kwargs):
        self.label, self.data, self.kwargs = label, data, kwargs
        self.sublist = _StubList()

    def item_data(self):
        return self.data


class _StubList:
    def __init__(self):
        self.rows = []
        self.is_initialized = False

    def add(self, label, data=None, **kwargs):
        row = _StubRow(label, data, kwargs)
        self.rows.append(row)
        return row

    def clear(self):
        self.rows = []

    def apply_preset(self, name):
        self.preset = name

    def setVisible(self, visible):
        pass

    def labels(self):
        return [r.label for r in self.rows]


def _mark(path):
    """Make *path* a workspace (a ``workspace.mel``)."""
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "workspace.mel"), "w") as f:
        f.write("//Maya workspace stub\n")
    return path


class _MainCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        _Store.histories = {}
        self.sb = mock.MagicMock()
        self.sb.ShortcutManager.host_namespace_suffix.return_value = "_maya"
        self.sb.RecentValuesStore = _Store
        self.slots = MainSlots(self.sb)
        self.env = self.sb.tk.EnvUtils
        self.ui_utils = self.sb.tk.UiUtils
        self.env.workspace_root.return_value = ""
        self.env.saved_scene_path.return_value = ""
        self.env.get_recent_projects.return_value = []
        self.env.is_workspace.side_effect = lambda p: bool(p) and os.path.isfile(
            os.path.join(str(p), "workspace.mel")
        )
        self.root = tempfile.mkdtemp(prefix="tentacle_main_ws_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def _messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]


class TestWorkspaceTab(_MainCase):
    def test_the_rows_in_order(self):
        widget = _StubList()
        self.slots.list000_init(widget)
        self.assertEqual(widget.labels(), ["Set Workspace", "Edit Workspace"])
        self.assertEqual(widget.rows[0].data, "__set_dir__")
        self.assertEqual(widget.rows[0].sublist.labels(), ["Auto Set Workspace"])
        self.assertEqual(widget.rows[1].data, "__editor__")
        self.assertEqual(widget.preset, "expand_right")

    def test_the_workspace_row_browses_its_folders(self):
        os.makedirs(os.path.join(self.root, "scenes"))
        self.env.workspace_root.return_value = self.root + "/"
        widget = _StubList()
        self.slots.list000_init(widget)
        row = widget.rows[2]
        self.assertEqual(row.label, os.path.basename(self.root))
        self.assertEqual(row.data, os.path.normpath(self.root))
        self.assertEqual(row.sublist.labels(), ["scenes"])
        self.sb.IconManager.set_label_icon.assert_any_call(row, "folder_filled")

    def test_recents_are_kept_under_the_hosts_key(self):
        """QSettings is shared by both hosts: each keeps its own history."""
        self.slots.list000_init(_StubList())
        self.assertEqual(self.slots._workspace_store.key, "workspace_recent_projects_maya")
        self.sb.ShortcutManager.host_namespace_suffix.assert_called_with(
            self.sb.context_tags
        )

    def test_the_shared_key_history_carries_over_once(self):
        """The history kept under the pre-namespacing key (Maya's) seeds the host's
        key on its first use, so no recent workspace is lost."""
        ws = _mark(os.path.join(self.root, "proj"))
        _Store.histories["workspace_recent_projects"] = [ws]
        widget = _StubList()
        self.slots.list000_init(widget)
        self.assertEqual(self.slots._workspace_store.values, [ws])
        recent = widget.rows[0].sublist.rows[1]
        self.assertEqual(recent.label, "Recent Workspaces")
        self.assertEqual(recent.sublist.rows[0].data, ("__recent__", ws))

    def test_the_hosts_recent_projects_seed_it_valid_only(self):
        ws = _mark(os.path.join(self.root, "proj"))
        plain = os.path.join(self.root, "plain")
        os.makedirs(plain)
        self.env.get_recent_projects.return_value = [ws, plain]
        self.slots.list000_init(_StubList())
        self.assertEqual(self.slots._workspace_store.values, [ws])
        self.env.get_recent_projects.assert_called_with(slice(0, 10))


class TestSceneDirRow(_MainCase):
    """The link to the open scene's folder: present (folder icon, full path as
    tooltip) only when the scene is saved and its folder exists."""

    def test_saved_scene_adds_folder_row(self):
        # Maya names a scene forward-slashed; the row's data must be native.
        self.env.saved_scene_path.return_value = os.path.join(
            self.root, "shot_010.ma"
        ).replace("\\", "/")
        rows = _StubList()
        self.slots._add_scene_dir_row(rows)
        (row,) = rows.rows
        self.assertEqual(row.label, "Scene Directory")
        self.assertEqual(row.data, os.path.normpath(self.root))
        self.assertEqual(row.kwargs.get("setToolTip"), os.path.normpath(self.root))
        self.sb.IconManager.set_label_icon.assert_called_once_with(row, "folder_filled")

    def test_click_opens_the_folder_and_copy_path_copies_it(self):
        self.env.saved_scene_path.return_value = os.path.join(self.root, "shot.ma")
        rows = _StubList()
        self.slots._add_scene_dir_row(rows)
        with mock.patch.object(ptk.FileUtils, "open_explorer") as open_explorer:
            self.slots.list000(rows.rows[0])
        open_explorer.assert_called_once_with(os.path.normpath(self.root))
        (copy_row,) = rows.rows[0].sublist.rows
        self.assertEqual(copy_row.label, "Copy Path")
        self.slots.list000(copy_row)
        clipboard = self.sb.QtWidgets.QApplication.clipboard.return_value
        clipboard.setText.assert_called_once_with(os.path.normpath(self.root))

    def test_unsaved_or_moved_scene_adds_nothing(self):
        rows = _StubList()
        self.slots._add_scene_dir_row(rows)
        self.env.saved_scene_path.return_value = os.path.join(self.root, "gone", "a.ma")
        self.slots._add_scene_dir_row(rows)
        self.assertEqual(rows.rows, [])


class TestSetWorkspace(_MainCase):
    """Browse -> offer to build a default workspace -> open; nothing built unasked."""

    def setUp(self):
        super().setUp()
        self.slots._workspace_store = _Store(settings_key="k")

    def _pick(self, *paths):
        self.ui_utils.browse_directory.side_effect = list(paths)

    def test_a_workspace_opens_without_an_offer(self):
        ws = _mark(os.path.join(self.root, "proj"))
        self._pick(ws)
        self.slots._set_workspace_interactive()
        self.env.create_workspace.assert_not_called()
        self.env.set_current_workspace.assert_called_once_with(os.path.normpath(ws))
        self.assertEqual(self.slots._workspace_store.values, [os.path.normpath(ws)])
        self.assertEqual(self._messages(), ["Workspace set to <hl>proj</hl>."])

    def test_the_offer_accepted_builds_then_opens(self):
        self._pick(self.root)
        self.sb.message_box.return_value = "Yes"
        self.slots._set_workspace_interactive()
        self.env.create_workspace.assert_called_once_with(os.path.normpath(self.root))
        self.env.set_current_workspace.assert_called_once_with(os.path.normpath(self.root))

    def test_retry_re_browses_from_the_picks_parent(self):
        plain = os.path.join(self.root, "plain")
        os.makedirs(plain)
        ws = _mark(os.path.join(self.root, "proj"))
        self._pick(plain, ws)
        self.sb.message_box.return_value = "Retry"
        self.slots._set_workspace_interactive()
        second = self.ui_utils.browse_directory.call_args_list[1]
        self.assertEqual(second.args[0], os.path.normpath(self.root))
        self.env.create_workspace.assert_not_called()
        self.env.set_current_workspace.assert_called_once_with(os.path.normpath(ws))

    def test_the_offer_declined_changes_nothing(self):
        self._pick(self.root)
        self.sb.message_box.return_value = "Cancel"
        self.slots._set_workspace_interactive()
        self.env.create_workspace.assert_not_called()
        self.env.set_current_workspace.assert_not_called()

    def test_a_dismissed_browser_is_a_noop(self):
        self._pick("")
        self.slots._set_workspace_interactive()
        self.env.set_current_workspace.assert_not_called()
        self.sb.message_box.assert_not_called()

    def test_it_starts_beside_the_current_workspace(self):
        self.env.workspace_root.return_value = os.path.join(self.root, "current")
        self._pick("")
        self.slots._set_workspace_interactive()
        args = self.ui_utils.browse_directory.call_args
        self.assertEqual(args.args[0], os.path.normpath(self.root))
        self.assertEqual(args.kwargs, {"caption": "Set Workspace", "ok_caption": "Set"})


class TestSwitching(_MainCase):
    def setUp(self):
        super().setUp()
        self.slots._workspace_store = _Store(settings_key="k")

    def test_a_recent_path_is_re_validated(self):
        self.slots._set_workspace_from_path(self.root)
        self.env.set_current_workspace.assert_not_called()
        self.assertEqual(self._messages(), ["Not a valid workspace."])

    def test_the_message_names_a_trailing_slash_path(self):
        """``basename`` of a trailing-separator path is "": the message would read
        "Workspace set to ."."""
        ws = _mark(os.path.join(self.root, "proj"))
        self.slots._set_workspace_from_path(ws + os.sep)
        self.assertIn("proj", self._messages()[-1])

    def test_auto_set_opens_the_scenes_workspace(self):
        ws = _mark(os.path.join(self.root, "proj"))
        self.env.find_workspace_using_path.return_value = ws
        self.slots._auto_set_workspace()
        self.env.set_current_workspace.assert_called_once_with(os.path.normpath(ws))
        self.env.find_workspace_using_path.return_value = None
        self.slots._auto_set_workspace()
        self.assertEqual(self._messages()[-1], "No workspace found.")

    def test_edit_workspace_opens_the_project_window_where_no_tool_serves(self):
        """Maya: tentacle's Workspace Editor is not served (``slots.tools.HOSTS``),
        so the row opens the host's own Project Window."""
        self.sb.ui_name_resolves.return_value = False
        self.ui_utils.open_editor.return_value = "ProjectWindow"
        self.slots._open_workspace_editor()
        self.ui_utils.open_editor.assert_called_once_with("Project Window")
        self.sb.handlers.marking_menu.show.assert_not_called()
        self.sb.ui_name_resolves.assert_called_once_with("workspace_editor")
        self.ui_utils.open_editor.return_value = None
        self.slots._open_workspace_editor()
        self.assertIn("Project Window", self._messages()[-1])


class TestDispatch(_MainCase):
    def test_each_row_kind_reaches_its_step(self):
        for name in (
            "_set_workspace_interactive",
            "_auto_set_workspace",
            "_open_workspace_editor",
            "_set_workspace_from_path",
        ):
            setattr(self.slots, name, mock.Mock(name=name))
        for data in ("__set_dir__", "__auto__", "__editor__", ("__recent__", "C:/p")):
            self.slots.list000(_StubRow("row", data, {}))
        self.slots._set_workspace_interactive.assert_called_once_with()
        self.slots._auto_set_workspace.assert_called_once_with()
        self.slots._open_workspace_editor.assert_called_once_with()
        self.slots._set_workspace_from_path.assert_called_once_with("C:/p")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestWorkspaceInMaya(_MainCase):
    """The same class over the real ``mtk``: a ``workspace.mel`` is what makes a
    workspace, and accepting the offer builds the template's rule folders."""

    def setUp(self):
        super().setUp()
        cmds.file(new=True, force=True)
        self._before = cmds.workspace(query=True, rd=True)
        self.mtk = maya_module("mayatk")
        self.sb.tk = self.mtk
        self.slots._workspace_store = _Store(settings_key="k")

    def tearDown(self):
        # Restore the workspace BEFORE the folder Maya may point at goes.
        cmds.workspace(self._before, openWorkspace=True)
        cmds.file(new=True, force=True)

    def _same(self, a, b):
        return os.path.normcase(os.path.normpath(a)) == os.path.normcase(
            os.path.normpath(b)
        )

    def test_a_folder_without_workspace_mel_is_refused(self):
        self.slots._set_workspace_from_path(self.root)
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self._before))
        self.assertEqual(self._messages(), ["Not a valid workspace."])

    def test_a_marked_folder_opens(self):
        _mark(self.root)
        self.slots._set_workspace_from_path(self.root)
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self.root))
        self.assertEqual(self.slots._workspace_store.values, [os.path.normpath(self.root)])

    def test_the_offer_accepted_builds_marker_and_rule_folders(self):
        with mock.patch.object(
            self.mtk.UiUtils, "browse_directory", return_value=self.root
        ):
            self.sb.message_box.return_value = "Yes"
            self.slots._set_workspace_interactive()
        ws = ptk.Workspace.load(self.root)
        self.assertTrue(ws.is_marked, "workspace.mel must be written")
        for rel in {
            v for v in ptk.DEFAULT_FILE_RULES.values() if v != "." and not os.path.isabs(v)
        }:
            self.assertTrue(
                os.path.isdir(os.path.join(self.root, rel)), f"missing rule folder {rel}"
            )
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self.root))

    def test_the_offer_declined_writes_nothing(self):
        with mock.patch.object(
            self.mtk.UiUtils, "browse_directory", return_value=self.root
        ):
            self.sb.message_box.return_value = "Cancel"
            self.slots._set_workspace_interactive()
        self.assertEqual(os.listdir(self.root), [])
        self.assertTrue(self._same(cmds.workspace(query=True, rd=True), self._before))


if __name__ == "__main__":
    unittest.main()
