#!/usr/bin/python
# coding=utf-8
"""The Workspace tab of tentacle.slots.main over Blender-shaped answers.

Sibling of ``test_main_workspace.py``, which pins the flow; this pins what
differs when the host is Blender. The class is the same: a fake toolkit stands
in for ``btk``, answering as blendertk does (a folder of .blend files is a
workspace, the session pin is what opens, Blender has no project window and
the editor part of tentacle's Workspaces tool serves it). blendertk's own
operations are tested in blendertk (``test_env_utils.py``).
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from tentacle.slots._slots import Slots
from tentacle.slots.main import MainSlots
from test_main_workspace import _Store, _StubList


class TestWorkspaceTabInBlender(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        _Store.histories = {}
        self.sb = mock.MagicMock()
        self.sb.ShortcutManager.host_namespace_suffix.return_value = "_blender"
        self.sb.RecentValuesStore = _Store
        self.slots = MainSlots(self.sb)
        self.env = self.sb.tk.EnvUtils
        self.env.workspace_root.return_value = ""
        self.env.saved_scene_path.return_value = ""
        self.env.get_recent_projects.return_value = []
        self.root = tempfile.mkdtemp(prefix="tentacle_main_ws_blender_")
        self.addCleanup(shutil.rmtree, self.root, True)
        # blendertk's answer: marked, or directly holding .blend files
        self.env.is_workspace.side_effect = lambda p: bool(p) and os.path.isdir(p) and any(
            f == "workspace.mel" or f.endswith(".blend") for f in os.listdir(p)
        )

    def _blend_folder(self, name):
        folder = os.path.join(self.root, name)
        os.makedirs(folder)
        open(os.path.join(folder, "shot.blend"), "w").close()
        return folder

    def test_the_history_keeps_blenders_own_key(self):
        """``workspace_recent_projects_blender`` is the key the Blender fork used:
        its history carries on untouched."""
        folder = self._blend_folder("shots")
        _Store.histories["workspace_recent_projects_blender"] = [folder]
        _Store.histories["workspace_recent_projects"] = ["C:/maya/proj"]
        self.slots.list000_init(_StubList())
        self.assertEqual(self.slots._workspace_store.key, "workspace_recent_projects_blender")
        self.assertEqual(self.slots._workspace_store.values, [folder])

    def test_a_folder_of_blend_files_opens_without_an_offer(self):
        folder = self._blend_folder("shots")
        self.slots._workspace_store = _Store(settings_key="k")
        self.sb.tk.UiUtils.browse_directory.side_effect = [folder]
        self.slots._set_workspace_interactive()
        self.env.create_workspace.assert_not_called()
        self.env.set_current_workspace.assert_called_once_with(os.path.normpath(folder))

    def test_recent_files_folders_seed_the_history(self):
        folder = self._blend_folder("shots")
        self.env.get_recent_projects.return_value = [folder]
        self.slots.list000_init(_StubList())
        self.assertEqual(self.slots._workspace_store.values, [folder])

    def test_edit_workspace_opens_the_workspaces_tool(self):
        """Blender has no project window (``UiUtils`` opens none): the Workspaces
        tool's editor part serves it."""
        self.sb.tk.UiUtils.get_editor_types.return_value = {"Outliner": "OUTLINER"}
        self.slots._open_workspace_editor()
        self.sb.handlers.marking_menu.show.assert_called_once_with("workspaces")
        self.sb.tk.UiUtils.open_editor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
