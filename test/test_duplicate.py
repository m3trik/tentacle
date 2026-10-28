#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.duplicate, the one Duplicate Slots class
(the marking-menu page; the Linear / Radial / Grid tool panels have their own).

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- tb000 (Convert to Instances): nothing selected warns without a call; the
  option box reaches ``NodeUtils.replace_with_instances(None, ...)``; the
  host's "fewer than two objects" reaches the user; Delete History is Maya's.
- tb001 (Select Instanced Objects): the All Instanced option picks the whole
  scene; otherwise the selection (warned when empty), and "none found" says so.
  The original selection stays selected beside its instances (the bug once
  fixed on the Maya side) -- pinned in Maya below and in the libraries.
- tb002 (Auto Instance): the option box reaches ``AutoInstancer.run_once``,
  which selects what survives; the report distinguishes "matched but not
  instanced" from "nothing matched".
The operations themselves are tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.duplicate import DuplicateSlots


def _widget(**values):
    """A widget whose option-box menu holds fakes reading *values*."""
    widget = mock.MagicMock()
    for name, value in values.items():
        child = getattr(widget.option_box.menu, name)
        child.value.return_value = value
        child.isChecked.return_value = value
    return widget


#: tb002's option box, at the .ui defaults.
AUTO_DEFAULTS = dict(
    s000=0.001,
    chk004=True,
    chk005=False,
    chk006=False,
    chk007=False,
    chk008=False,
    chk009=True,
    chk010=True,
    chk011=True,
    s001=10000.0,
)


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = DuplicateSlots(self.sb)
        self.tk = self.sb.tk
        self.tk.CoreUtils.selected_objects.return_value = ["a", "b"]

    def _message(self):
        call = self.sb.message_box.call_args
        return call.args[0] if call else None


class TestTb000ConvertToInstances(_SlotsCase):
    def _widget(self, **overrides):
        values = dict(
            chk000=False, chk001=True, chk002=True, chk012=False, chk013=False
        )
        values.update(overrides)
        return _widget(**values)

    def test_nothing_selected_warns_without_a_call(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb000(self._widget())
        self.tk.NodeUtils.replace_with_instances.assert_not_called()
        self.assertIn("Nothing selected", self._message())

    def test_the_option_box_reaches_the_host_on_the_selection(self):
        self.slots.tb000(
            self._widget(
                chk000=True, chk001=False, chk002=True, chk012=True, chk013=True
            )
        )
        self.tk.NodeUtils.replace_with_instances.assert_called_once_with(
            None,
            freeze_transforms=True,
            center_pivot=True,
            delete_history=False,
            retain_bbox_scale=True,
            retain_bbox_per_axis=True,
        )
        self.sb.message_box.assert_not_called()

    def test_too_few_objects_reaches_the_user(self):
        self.tk.NodeUtils.replace_with_instances.side_effect = ValueError("two objects")
        self.slots.tb000(self._widget())
        self.assertIn("Insufficient selection", self._message())
        self.assertIn("two objects", self._message())

    def test_a_refused_object_mode_reaches_the_user(self):
        self.tk.NodeUtils.replace_with_instances.side_effect = RuntimeError("Edit Mode")
        self.slots.tb000(self._widget())
        self.sb.message_box.assert_called_once_with("Edit Mode")

    def test_delete_history_is_mayas(self):
        menu = mock.MagicMock()
        made = {}

        def add(_kind, **kwargs):
            made[kwargs["setObjectName"]] = mock.MagicMock()
            return made[kwargs["setObjectName"]]

        menu.add.side_effect = add
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        self.slots.tb000_init(widget)
        made["chk001"].setProperty.assert_called_once_with("requires", "maya")
        self.sb.apply_visibility_policy.assert_called_once_with(made["chk001"])
        self.assertEqual(
            sorted(made), ["chk000", "chk001", "chk002", "chk012", "chk013"]
        )


class TestTb001SelectInstanced(_SlotsCase):
    def test_all_instanced_selects_the_whole_scene(self):
        self.tk.NodeUtils.select_instances.return_value = ["i1", "i2"]
        self.slots.tb001(_widget(chk003=True))
        self.tk.NodeUtils.select_instances.assert_called_once_with(whole_scene=True)
        self.sb.message_box.assert_not_called()

    def test_the_selection_and_its_instances(self):
        self.tk.NodeUtils.select_instances.return_value = ["a", "i1"]
        self.slots.tb001(_widget(chk003=False))
        self.tk.NodeUtils.select_instances.assert_called_once_with(["a", "b"])
        self.sb.message_box.assert_not_called()

    def test_nothing_selected_warns_without_a_call(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb001(_widget(chk003=False))
        self.tk.NodeUtils.select_instances.assert_not_called()
        self.assertIn("All Instanced Objects", self._message())

    def test_none_found_says_so(self):
        self.tk.NodeUtils.select_instances.return_value = []
        for scene in (True, False):
            with self.subTest(whole_scene=scene):
                self.slots.tb001(_widget(chk003=scene))
                self.assertIn("No instanced objects found", self._message())


class TestTb002AutoInstance(_SlotsCase):
    def setUp(self):
        super().setUp()
        self.summary = {"matched_groups": 0}
        self.made = []
        self.tk.AutoInstancer.run_once.side_effect = lambda *a, **k: (
            self.made,
            self.summary,
        )
        self.tk.AutoInstancer.format_summary.return_value = "line one\nline two"

    def test_the_option_box_reaches_run_once_on_the_selection_or_scene(self):
        values = dict(AUTO_DEFAULTS, s000=0.05, chk004=False, chk005=True, s001=250.0)
        self.slots.tb002(_widget(**values))
        call = self.tk.AutoInstancer.run_once.call_args
        self.assertEqual(call.args, (None,))
        self.assertEqual(
            call.kwargs,
            dict(
                tolerance=0.05,
                require_same_material=False,
                check_uvs=True,
                check_hierarchy=False,
                separate_combined=False,
                combine_assemblies=False,
                combine_non_instanced=True,
                combine_by_material=True,
                combine_by_distance=True,
                combine_distance_threshold=250.0,
                return_summary=True,
                select=True,
            ),
        )

    def test_a_run_reports_its_summary(self):
        self.made = ["inst1", "inst2"]
        self.slots.tb002(_widget(**AUTO_DEFAULTS))
        self.tk.AutoInstancer.format_summary.assert_called_once_with(self.summary, 2)
        self.assertEqual(self._message(), "line one<br>line two")

    def test_no_match_says_so(self):
        self.slots.tb002(_widget(**AUTO_DEFAULTS))
        self.assertIn("No matching geometry found", self._message())

    def test_matched_but_none_instanced_reports_why(self):
        self.summary["matched_groups"] = 2
        self.slots.tb002(_widget(**AUTO_DEFAULTS))
        self.assertIn("No objects were instanced", self._message())
        self.assertIn("line one<br>line two", self._message())
        self.assertNotIn("No matching geometry found", self._message())


class TestUninstanceAndPanels(_SlotsCase):
    def test_b005_uninstances_the_selection(self):
        self.slots.b005()
        self.tk.NodeUtils.uninstance.assert_called_once_with(None)
        self.sb.message_box.assert_not_called()

    def test_b005_a_refused_object_mode_reaches_the_user(self):
        self.tk.NodeUtils.uninstance.side_effect = RuntimeError("Edit Mode")
        self.slots.b005()
        self.sb.message_box.assert_called_once_with("Edit Mode")

    def test_the_launchers_open_their_panels(self):
        for slot in (
            self.slots.b000,
            self.slots.b006,
            self.slots.b007,
            self.slots.b008,
        ):
            slot()
        shown = [c.args[0] for c in self.sb.handlers.marking_menu.show.call_args_list]
        self.assertEqual(
            shown, ["mirror", "duplicate_linear", "duplicate_radial", "duplicate_grid"]
        )

    def test_the_header_lists_the_launchers(self):
        widget = mock.MagicMock()
        self.slots.header_init(widget)
        names = [c.kwargs["setObjectName"] for c in widget.menu.add.call_args_list]
        self.assertEqual(names, ["b000", "b006", "b007", "b008"])
        self.assertTrue(widget.menu.hide_on_trigger)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestDuplicateInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def _tb000(self):
        self.slots.tb000(
            _widget(chk000=False, chk001=True, chk002=True, chk012=False, chk013=False)
        )

    def test_convert_to_instances_with_one_object_warns(self):
        self.cmds.select(self.cmds.polyCube(name="dup_one")[0])
        self._tb000()
        self.assertIn("Insufficient selection", self._message())

    def test_convert_to_instances_shares_the_first_selected_shape(self):
        src = self.cmds.polyCube(name="dup_src")[0]
        tgt = self.cmds.polyCube(name="dup_tgt")[0]
        self.cmds.select([src, tgt])
        self._tb000()
        self.sb.message_box.assert_not_called()
        self.assertTrue(self.sb.tk.NodeUtils.get_instances(src))

    def test_select_instanced_keeps_the_original_beside_its_instance(self):
        """Regression: only the *other* instances survived, dropping the object
        the user had selected."""
        src = self.cmds.polyCube(name="dup_tb001_src")[0]
        inst = self.cmds.instance(src, name="dup_tb001_inst")[0]
        self.cmds.select(src)
        self.slots.tb001(_widget(chk003=False))
        selected = self.cmds.ls(selection=True)
        self.assertIn(src, selected)
        self.assertIn(inst, selected)

    def test_select_instanced_on_a_lone_object_warns(self):
        self.cmds.select(self.cmds.polyCube(name="dup_tb001_lonely")[0])
        self.slots.tb001(_widget(chk003=False))
        self.assertIn("No instanced objects found", self._message())

    def test_uninstance_forks_the_selection(self):
        src = self.cmds.polyCube(name="dup_b005_src")[0]
        inst = self.cmds.instance(src, name="dup_b005_inst")[0]
        self.cmds.select(inst)
        self.slots.b005()
        self.assertFalse(self.sb.tk.NodeUtils.get_instances(src))


if __name__ == "__main__":
    unittest.main()
