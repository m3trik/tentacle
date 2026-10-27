#!/usr/bin/python
# coding=utf-8
"""The Duplicate Radial panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``; Blender's is ``test/blender/panel_slots_check.py``.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.ui.panels.duplicate_radial.duplicate_radial import DuplicateRadialSlots


def _panel(values=None):
    """A Slots instance over a mock ui and a mock toolkit."""
    sb = mock.MagicMock()
    ui = sb.loaded_ui.duplicate_radial
    for name, value in (values or {}).items():
        widget = getattr(ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value
        widget.currentIndex.return_value = value
        widget.currentData.return_value = value
    return DuplicateRadialSlots(sb), sb


class TestDuplicateRadialPanel(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    def test_previews_through_the_host_toolkit(self):
        slots, sb = _panel()
        sb.tk.Preview.assert_called_once_with(
            slots,
            sb.loaded_ui.duplicate_radial.chk000,
            sb.loaded_ui.duplicate_radial.b000,
            finalize_func=slots.regroup_copies,
            message_func=sb.message_box,
            undo_message="Duplicate Radial",
        )

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        slots, sb = _panel(
            {
                "s009": 6,
                "s013": 10.0,
                "s014": 190.0,
                "chk002": False,
                "chk003": True,
                "cmb000": 1,
                "cmb_inst": "instance",
            }
        )
        engine = sb.tk.DuplicateRadial.duplicate_radial
        # Maya's Preview passes a contract, Blender's none: both are accepted.
        slots.perform_operation(["cube"], None)
        slots.perform_operation(["cube"])
        args, kwargs = engine.call_args
        self.assertEqual(args, (["cube"], 6))
        self.assertEqual(kwargs["start_angle"], 10.0)
        self.assertEqual(kwargs["end_angle"], 190.0)
        self.assertEqual(kwargs["rotate_axis"], "y")
        self.assertEqual(kwargs["pivot"], "world")
        self.assertTrue(kwargs["instance"])
        self.assertIs(slots.copies, engine.return_value)

    def test_too_few_copies_is_a_fixable_error_before_the_host_runs(self):
        slots, sb = _panel({"s009": 0})
        with self.assertRaisesRegex(ValueError, "at least 1"):
            slots.perform_operation(["cube"])
        sb.tk.DuplicateRadial.duplicate_radial.assert_not_called()

    def test_the_commit_regroups_what_the_operation_returned(self):
        slots, sb = _panel({"s009": 3})
        slots.perform_operation(["cube"])
        slots.regroup_copies()
        sb.tk.DuplicateRadial.regroup_copies.assert_called_once_with(
            sb.tk.DuplicateRadial.duplicate_radial.return_value
        )


#: The panel's defaults, as its .ui sets them: what a commit reads untouched.
_DEFAULTS = {
    **{f"s{i:03d}": 0.0 for i in range(17)},
    **{"s006": 1.0, "s007": 1.0, "s008": 1.0, "s009": 4, "s014": 360.0},
    **{"s015": 0.5, "s016": 0.5, "cmb000": 0, "cmb_inst": "copy"},
    **{"chk002": False, "chk003": True, "chk006": False, "chk007": False},
    "chk008": False,
}


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestDuplicateRadialPanelInMaya(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)

    def test_a_commit_leaves_one_array_group_holding_every_copy(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="radSrc")[0]
        cmds.move(3, 0, 0, cube)
        slots, sb = _panel(_DEFAULTS)
        sb.tk = maya_module("mayatk")
        slots.perform_operation([cube], None)
        slots.regroup_copies()
        arrays = [t for t in cmds.ls(type="transform") if t.endswith("_array")]
        self.assertEqual(len(arrays), 1, arrays)
        meshes = cmds.listRelatives(arrays[0], allDescendents=True, type="mesh")
        self.assertEqual(len(meshes or []), 4)


if __name__ == "__main__":
    unittest.main()
