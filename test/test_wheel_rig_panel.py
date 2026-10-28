#!/usr/bin/python
# coding=utf-8
"""The Wheel Rig panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``. Which object drives and which are wheels is the
library's (``WheelRig.from_selection``), tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.wheel_rig import WheelRigSlots


def _panel(axis=2, height="1.0", name="", freeze=False, placeholder=None):
    """A Slots instance over a mock ui and a mock toolkit; *placeholder* is the
    rig name the toolkit gives the selection's driver."""
    sb = mock.MagicMock()
    ui = sb.loaded_ui.wheel_rig
    ui.cmb000.currentIndex.return_value = axis
    ui.s000.text.return_value = height
    ui.txt000.text.return_value = name
    ui.chk010.isChecked.return_value = freeze
    sb.tk.WheelRig.default_rig_name.return_value = placeholder
    return WheelRigSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestWheelRigPanelSetup(_PanelCase):
    def test_the_axis_combo_pairs_each_travel_with_its_rotation(self):
        _, sb = _panel()
        ui = sb.loaded_ui.wheel_rig
        ui.cmb000.addItems.assert_called_once_with(
            ["Move X → Rotate Z", "Move Y → Rotate Y", "Move Z → Rotate X"]
        )
        ui.cmb000.setCurrentIndex.assert_called_once_with(2)  # Move Z -> Rotate X

    def test_the_retired_widgets_are_hidden_not_deleted(self):
        """Their objectNames are saved settings: they stay in the .ui."""
        _, sb = _panel()
        ui = sb.loaded_ui.wheel_rig
        for widget in (ui.chk000, ui.cmb001):
            widget.setVisible.assert_called_once_with(False)
            widget.deleteLater.assert_not_called()

    def test_the_placeholder_follows_the_selections_driver(self):
        slots, sb = _panel(placeholder="Car_wheel_rig")
        ui = sb.loaded_ui.wheel_rig
        ui.txt000.setPlaceholderText.assert_called_once_with("Car_wheel_rig")
        mgr = sb.tk.ScriptJobManager.instance.return_value
        mgr.subscribe.assert_called_once_with(
            "SelectionChanged", slots._on_selection_changed, owner=slots
        )
        mgr.connect_cleanup.assert_called_once_with(ui, owner=slots)

        # Nothing selected: the last placeholder stays.
        sb.tk.WheelRig.default_rig_name.return_value = None
        slots._on_selection_changed()
        ui.txt000.setPlaceholderText.assert_called_once_with("Car_wheel_rig")


class TestWheelRigRotation(_PanelCase):
    def test_rig_rotation_runs_the_host_engine_on_the_selection(self):
        slots, sb = _panel(axis=1, height="2.5", freeze=True)
        slots.b000()
        sb.tk.WheelRig.from_selection.assert_called_once_with(
            rig_name=None,
            freeze_transforms=True,
            movement_axis="translateY",
            rotation_axis="rotateY",
            wheel_height=2.5,
            use_world_space=False,
        )
        sb.message_box.assert_not_called()

    def test_each_axis_entry_names_mayatks_channels(self):
        expected = (
            ("translateX", "rotateZ"),
            ("translateY", "rotateY"),
            ("translateZ", "rotateX"),
        )
        for index, (movement, rotation) in enumerate(expected):
            with self.subTest(index=index):
                slots, _ = _panel(axis=index)
                self.assertEqual(slots.movement_axis, movement)
                self.assertEqual(slots.rotation_axis, rotation)

    def test_a_named_rig_passes_its_name(self):
        slots, sb = _panel(name="  truck  ")
        slots.b000()
        kwargs = sb.tk.WheelRig.from_selection.call_args.kwargs
        self.assertEqual(kwargs["rig_name"], "truck")

    def test_world_space_mode_reaches_the_engine(self):
        slots, sb = _panel()
        slots._on_space_changed("World Space")
        slots.b000()
        kwargs = sb.tk.WheelRig.from_selection.call_args.kwargs
        self.assertTrue(kwargs["use_world_space"])
        slots._on_space_changed("Local")
        slots.b000()
        self.assertFalse(sb.tk.WheelRig.from_selection.call_args.kwargs["use_world_space"])

    def test_an_empty_height_rigs_a_unit_wheel(self):
        slots, sb = _panel(height="")
        slots.b000()
        self.assertEqual(
            sb.tk.WheelRig.from_selection.call_args.kwargs["wheel_height"], 1.0
        )

    def test_a_non_numeric_height_is_refused_before_the_engine_runs(self):
        slots, sb = _panel(height="tall")
        slots.b000()
        sb.tk.WheelRig.from_selection.assert_not_called()
        self.assertIn("Wheel Height", sb.message_box.call_args.args[0])

    def test_a_refused_selection_reaches_the_message_box(self):
        slots, sb = _panel()
        reason = "Select one or more wheel objects, then the driver (last)."
        sb.tk.WheelRig.from_selection.side_effect = ValueError(reason)
        slots.b000()
        sb.message_box.assert_called_once_with(reason)

    def test_an_engine_failure_reaches_the_message_box(self):
        slots, sb = _panel()
        sb.tk.WheelRig.from_selection.side_effect = RuntimeError("locked")
        slots.b000()
        self.assertIn("locked", sb.message_box.call_args.args[0])


class TestWheelRigGetWheelSize(_PanelCase):
    def test_the_measured_diameter_fills_wheel_height(self):
        slots, sb = _panel(axis=0)
        sb.tk.WheelRig.wheel_size.return_value = 1.23456
        slots.set_wheel_height()
        sb.tk.WheelRig.wheel_size.assert_called_once_with(movement_axis="translateX")
        sb.loaded_ui.wheel_rig.s000.setText.assert_called_once_with("1.235")

    def test_nothing_to_measure_says_so(self):
        slots, sb = _panel()
        sb.tk.WheelRig.wheel_size.return_value = None
        slots.set_wheel_height()
        sb.loaded_ui.wheel_rig.s000.setText.assert_not_called()
        sb.message_box.assert_called_once()


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestWheelRigPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)

    def _real(self, **values):
        # Built over the fake toolkit (no scriptJob outlives the test), then
        # pointed at the real mtk for the slots under test.
        slots, sb = _panel(**values)
        sb.tk = maya_module("mayatk")
        return slots, sb

    def test_rig_rotation_rolls_the_wheels_from_the_last_selected(self):
        cmds = self.cmds
        control = cmds.polyCube(name="whlCtrl")[0]
        wheel = cmds.polyCylinder(name="whlWheel")[0]
        cmds.select(wheel, control)  # the driver last

        slots, sb = self._real(axis=2, height="2.0")
        slots.b000()
        sb.message_box.assert_not_called()
        self.assertEqual(cmds.getAttr(f"{control}.wheelRigId"), "whlCtrl_wheel_rig")

        cmds.setAttr(f"{control}.translateZ", 5.0)
        cmds.dgeval(f"{wheel}.rotateX")
        self.assertNotAlmostEqual(cmds.getAttr(f"{wheel}.rotateX"), 0.0, places=2)

    def test_one_undo_takes_the_whole_click_back(self):
        cmds = self.cmds
        control = cmds.polyCube(name="whlUndoCtrl")[0]
        wheel = cmds.polyCylinder(name="whlUndoWheel")[0]
        cmds.select(wheel, control)

        slots, sb = self._real(axis=2, freeze=True)
        slots.b000()
        sb.message_box.assert_not_called()
        cmds.undo()  # the rig ID stamp, the freeze and the expressions together
        self.assertFalse(cmds.attributeQuery("wheelRigId", node=control, exists=True))
        self.assertFalse(cmds.ls(type="expression"))

    def test_get_wheel_size_measures_the_selected_wheel(self):
        cmds = self.cmds
        wheel = cmds.polyCylinder(name="whlSized", radius=2.0, height=0.5)[0]
        cmds.select(wheel)

        slots, sb = self._real(axis=2)  # Move Z: the Y/Z extents
        slots.set_wheel_height()
        sb.loaded_ui.wheel_rig.s000.setText.assert_called_once_with("4.0")


if __name__ == "__main__":
    unittest.main()
