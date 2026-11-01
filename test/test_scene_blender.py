#!/usr/bin/python
# coding=utf-8
"""tentacle.slots.scene as Blender sees it -- over a toolkit answering like blendertk's.

The Scene panel is one class for both hosts (``slots/scene.py``); what differs is what
the host toolkit answers. A Blender-like fake toolkit stands in for ``btk`` here (no
``bpy``), pinning what a Blender user gets from the shared class:

- the Import list: Blender's own operators (``EnvUtils.get_file_commands``), its FBX
  row through ``btk.FbxUtils.import_fbx`` (ALL the file's takes -- the stock operator
  played the first take keying each object), the Maya-scene pull;
- the Export list: ``Export .ma``, Blender's own glTF exporter beside Maya's GLB
  one-shot (tagged ``maya``, hidden here);
- the other DCC named Maya everywhere (the format combo's "MA", the Maya Bridge);
- the Tools leaves only Maya serves hidden, Blender's Scene Cleanup shown.
The real btk run is ``test/blender/deepened_slots_check.py``'s scene sections.
"""

import unittest
from types import SimpleNamespace as NS
from unittest import mock

from tentacle.slots._slots import Slots
from tentacle.slots.scene import SceneSlots

#: What blendertk's ``EnvUtils.get_file_commands`` answers in a Blender with every
#: operator registered (pinned in blendertk's ``test_env_utils.py``).
BLENDER_COMMANDS = {
    "import": ["Import OBJ", "Import Collada", "Append from .blend", "Link from .blend"],
    "export": [
        "Export Selection",
        "Export FBX",
        "Export OBJ",
        "Export glTF",
        "Export Collada",
    ],
}


def _blender_toolkit(commands=BLENDER_COMMANDS):
    tk = mock.MagicMock()
    tk.EnvUtils.foreign_scene_bridge.return_value = NS(
        spec=NS(app=NS(name="Maya")), save_extensions=(".ma", ".mb")
    )
    tk.EnvUtils.foreign_scene_import.return_value.SCENE_EXTENSIONS = (".ma", ".mb")
    tk.EnvUtils.get_file_commands.side_effect = lambda direction: list(
        commands[direction]
    )
    tk.EnvUtils.saved_scene_path.return_value = ""
    tk.EnvUtils.workspace_root.return_value = "W:/proj"
    return tk


class _BlenderCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.sb.tk = _blender_toolkit()
        self.sb.loaded_ui.scene.footer = None
        self.slots = SceneSlots(self.sb)
        self.tk = self.sb.tk

    def _rows(self, table, direction):
        return [(label, req) for label, _, req in self.slots._list_rows(table, direction)]


class TestImportList(_BlenderCase):
    def test_blender_s_import_list(self):
        self.assertEqual(
            self._rows(SceneSlots._IMPORT_ROWS, "import"),
            [
                ("Import FBX", "blender"),
                ("Import OBJ", None),
                ("Import Maya Scene", None),
                ("Import glTF", None),
                ("Import USD", None),
                ("Import Collada", None),
                ("Append from .blend", None),
                ("Link from .blend", None),
            ],
        )

    def test_an_operator_this_blender_lacks_is_not_offered(self):
        """Collada left in Blender 5.0: blendertk stops listing it, the row goes."""
        self.tk.EnvUtils.get_file_commands.side_effect = lambda d: [
            c for c in BLENDER_COMMANDS[d] if "Collada" not in c
        ]
        labels = [label for label, _ in self._rows(SceneSlots._IMPORT_ROWS, "import")]
        self.assertNotIn("Import Collada", labels)

    def test_a_command_row_invokes_the_host_operator_by_name(self):
        rows = dict(
            (label, action)
            for label, action, _ in self.slots._list_rows(
                SceneSlots._IMPORT_ROWS, "import"
            )
        )
        rows["Link from .blend"]()
        self.tk.EnvUtils.run_file_command.assert_called_once_with("Link from .blend")

    def test_import_fbx_pulls_every_take_through_fbx_utils(self):
        self.sb.file_dialog.return_value = "X:/in/shots.fbx"
        self.tk.FbxUtils.import_fbx.return_value = ["a", "b", "c"]
        self.slots._import_fbx()
        self.tk.FbxUtils.import_fbx.assert_called_once_with("X:/in/shots.fbx")
        self.tk.EnvUtils.foreign_scene_import.return_value.assert_not_called()
        self.assertIn("Imported <hl>3</hl>", self.sb.message_box.call_args.args[0])

    def test_import_maya_scene_browses_maya_s_files(self):
        self.sb.file_dialog.return_value = None
        self.slots._import_foreign_scene()
        kwargs = self.sb.file_dialog.call_args.kwargs
        self.assertEqual(kwargs["file_types"], ["*.ma", "*.mb"])
        self.assertEqual(kwargs["title"], "Import Maya Scene")


class TestExportList(_BlenderCase):
    def test_blender_s_export_list(self):
        self.assertEqual(
            self._rows(SceneSlots._EXPORT_ROWS, "export"),
            [
                ("Export Selection", None),
                ("Export .ma", None),
                ("Export USD", None),
                ("Export FBX", None),
                ("Export OBJ", None),
                ("Export glTF", "maya"),  # Maya's GLB one-shot, hidden here
                ("Export glTF", None),  # Blender's own exporter, its options dialog
                ("Export Collada", None),
            ],
        )

    def test_the_format_combo_names_maya_s_format(self):
        self.assertEqual(self.slots._export_format_items()[-1], ("MA", "foreign"))
        self.assertEqual(self.slots._export_spellings("foreign"), (".ma", ".mb"))


class TestToolsInBlender(_BlenderCase):
    def setUp(self):
        super().setUp()
        self.sb.tooltip.fmt.return_value = "formatted"
        self.rows = {
            name: (label, requires)
            for entries in self.slots._tools_items().values()
            for label, name, _tip, requires in entries
        }

    def test_maya_only_leaves_are_tagged_and_scene_cleanup_is_blender_s(self):
        for name in ("b014", "b006", "b009", "b018", "b012"):
            with self.subTest(leaf=name):
                self.assertEqual(self.rows[name][1], "maya")
        self.assertEqual(self.rows["b_cleanup"], ("Scene Cleanup", "blender"))

    def test_the_bridge_leaf_is_the_maya_bridge(self):
        self.assertEqual(self.rows["b010"][0].format(app="Maya"), "Maya Bridge")
        self.slots.b010()
        self.sb.handlers.marking_menu.show.assert_called_once_with("dcc_bridge")

    def test_audio_clips_and_blendshape_animator_stay_in_manage(self):
        self.assertEqual(self.rows["b003"], ("Audio Clips", None))
        self.assertEqual(self.rows["b015"], ("Blendshape Animator", None))


if __name__ == "__main__":
    unittest.main()
