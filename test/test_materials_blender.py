#!/usr/bin/python
# coding=utf-8
"""MaterialsSlots: one click, one host operation -- so one undo step in Blender too.

This module was born from a real Blender gap: the Assign list's "assign an existing
material by name" and "release-on-root reassigns the current material" paths went
through a helper the Blender fork had left without its undo wrap, while every sibling
assignment action had one -- so Ctrl+Z silently no-op'd for those two paths only (a raw
``bpy.data`` edit pushes nothing onto Blender's undo stack on its own).

The composed class keeps the guarantee by construction, and these tests pin it over a
fake toolkit: every mutating click is ONE ``self.tk.MatUtils`` operation, which the host
library makes one undo step (blendertk's ``@CoreUtils.undoable``, mayatk's undo chunk;
their own tests pin the decorators). ``MatUtils.assign_mat`` -- a raw primitive bulk
callers use, so blendertk leaves it unwrapped -- runs inside
``self.tk.CoreUtils.undo_chunk`` here. The list handlers stay plain dispatchers: they
fire on category / expand clicks too, which must touch nothing.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.materials import MaterialsSlots  # noqa: E402


class _Item:
    """An ExpandableList row as the list handlers read it."""

    def __init__(self, text, parent=None, children=()):
        self._text, self._parent = text, parent
        self.sublist = SimpleNamespace(get_items=lambda: list(children))

    def item_text(self):
        return self._text

    def parent_item_text(self):
        return self._parent


class _ClickCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = MaterialsSlots(self.sb)
        self.slots.ui = SimpleNamespace()  # no table
        self.slots._refresh_material_lists = mock.Mock()
        # The b-slots' Alt check reads the keyboard; no modifier is held here.
        self.slots._random_held = lambda: False
        self.tk = self.sb.tk
        self.tk.CoreUtils.selected_objects.return_value = ["Cube"]
        self.events = []
        chunk = self.tk.CoreUtils.undo_chunk.return_value
        chunk.__enter__.side_effect = lambda *a: self.events.append("open")
        chunk.__exit__.side_effect = lambda *a: self.events.append("close")
        self.tk.MatUtils.assign_mat.side_effect = lambda *a, **k: self.events.append(
            ("assign", a[1])
        )

    def mat_calls(self):
        """The ``MatUtils`` operations asked for, by name (queries included)."""
        return [c[0] for c in self.tk.MatUtils.method_calls]


class TestAnAssignIsOneUndoStep(_ClickCase):
    def test_a_named_leaf_assigns_inside_one_chunk(self):
        self.slots.list000(_Item("matB", parent="Assign"))
        self.assertEqual(self.events, ["open", ("assign", "matB"), "close"])
        self.tk.MatUtils.assign_mat.assert_called_once_with(["Cube"], "matB", create=False)

    def test_the_root_release_assigns_the_current_material_inside_one_chunk(self):
        self.slots._current = "matA"
        self.slots.list000(_Item("Assign: matA"))
        self.assertEqual(self.events, ["open", ("assign", "matA"), "close"])

    def test_the_root_release_with_no_current_material_assigns_nothing(self):
        self.slots.list000(_Item("Assign"))
        self.assertEqual(self.events, [])
        self.assertIn("No current material", self.sb.message_box.call_args.args[0])

    def test_nothing_selected_assigns_nothing(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.list000(_Item("matB", parent="Assign"))
        self.assertEqual(self.events, [])
        self.assertIn("Nothing selected", self.sb.message_box.call_args.args[0])

    def test_a_material_gone_meanwhile_refills_instead(self):
        self.tk.MatUtils.assign_mat.side_effect = ValueError("No material named 'matB'.")
        self.slots.list000(_Item("matB", parent="Assign"))
        self.assertIn("no longer exists", self.sb.message_box.call_args.args[0])
        self.slots._refresh_material_lists.assert_called_once_with()
        self.assertIsNone(self.slots._current_mat(), "a gone material never becomes current")

    def test_new_and_random_are_one_operation_each(self):
        self.tk.MatUtils.assign_new_mat.return_value = "Material"
        self.tk.MatUtils.assign_random_mat.return_value = "mat_1a2b3c"
        self.slots.list000(_Item("New", parent="Assign"))
        self.slots.list000(_Item("Random", parent="Assign"))
        self.tk.MatUtils.assign_new_mat.assert_called_once_with(None)
        self.tk.MatUtils.assign_random_mat.assert_called_once_with(None, previous=None)
        self.assertEqual(self.events, [], "no assign_mat around them")

    def test_a_second_random_replaces_the_first(self):
        self.tk.MatUtils.assign_random_mat.side_effect = ["mat_1", "mat_2"]
        self.slots.b004()
        self.slots.b004()
        self.assertEqual(
            self.tk.MatUtils.assign_random_mat.call_args_list[-1],
            mock.call(None, previous="mat_1"),
        )
        self.assertEqual(self.slots._current_mat(), "mat_2")

    def test_the_hosts_refusal_of_new_is_said(self):
        """Maya: no renderable geometry selected; Blender: nothing holds a material."""
        self.tk.MatUtils.assign_new_mat.side_effect = ValueError("No renderable object.")
        self.slots.b006()
        self.assertEqual(self.sb.message_box.call_args.args[0], "No renderable object.")


class TestTheListHandlersTouchNothingOnNavigation(_ClickCase):
    def test_a_tools_category_click_dispatches_nothing(self):
        self.slots.list001(_Item("Utilities", children=("row",)))
        self.assertEqual(self.tk.method_calls, [])
        self.sb.handlers.marking_menu.show.assert_not_called()

    def test_a_tools_row_runs_its_slot(self):
        self.slots.list001(_Item("Texture Path Editor", parent="Setup"))
        self.sb.handlers.marking_menu.show.assert_called_once_with("texture_path_editor")


class TestEachCleanupIsOneOperation(_ClickCase):
    def test_delete_all_unused(self):
        self.tk.MatUtils.delete_unused_materials.return_value = ["a", "b"]
        self.slots.b015()
        self.assertEqual(self.mat_calls(), ["delete_unused_materials"])
        self.assertEqual(
            self.sb.message_box.call_args.args[0], "Deleted <hl>2</hl> unused materials."
        )

    def test_remove_duplicates_finds_then_merges_once(self):
        self.tk.MatUtils.find_duplicate_materials.return_value = {"Crate1": "Crate"}
        self.tk.MatUtils.merge_duplicate_materials.return_value = 1
        self.slots.b014()
        self.assertEqual(
            self.mat_calls(), ["find_duplicate_materials", "merge_duplicate_materials"]
        )
        self.tk.MatUtils.merge_duplicate_materials.assert_called_once_with({"Crate1": "Crate"})

    def test_a_status_merge_and_a_delete(self):
        self.tk.MatUtils.merge_duplicate_materials.return_value = 1
        self.tk.MatUtils.delete_mats.return_value = ["Old"]
        self.slots._merge_and_report({"Crate1": "Crate"})
        self.slots._delete_and_report(["Old"])
        self.assertEqual(self.mat_calls(), ["merge_duplicate_materials", "delete_mats"])

    def test_a_rename(self):
        self.slots._current = "Old"
        self.tk.MatUtils.rename_mat.return_value = "Retired.001"
        self.assertEqual(self.slots._rename_current("Retired"), "Retired.001")
        self.assertEqual(self.mat_calls(), ["rename_mat"])
        self.assertEqual(self.slots._current_mat(), "Retired.001", "the host's name")

    def test_a_refused_rename_resyncs_the_list(self):
        self.slots._current = "Old"
        self.tk.MatUtils.rename_mat.side_effect = RuntimeError("locked")
        self.assertIsNone(self.slots._rename_current("Retired"))
        self.assertIn("Rename failed", self.sb.message_box.call_args.args[0])
        self.slots._refresh_material_lists.assert_called_once_with()
        self.assertEqual(self.slots._current_mat(), "Old")


if __name__ == "__main__":
    unittest.main()
