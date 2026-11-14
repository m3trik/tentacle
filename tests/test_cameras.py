#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.cameras, the one Cameras Slots class.

It reaches its host only through ``self.tk`` (``CamUtils`` /
``CameraVisibility``): a fake toolkit stands in for it here and records the
calls (plain pytest), and in Maya the same class drives the real ``mtk``.
What's worth pinning at this layer:

- b000-b006: each maps to mayatk's view name (``switch_viewport_camera``), and a
  failed switch is reported.
- b007 (Align View): nothing selected is reported and makes no camera.
- b010-b013: each arms its navigation mode; a refusal is shown.
- list000: the categories and their leaves in order, Select Camera only with a
  camera to pick, and each leaf's operation.

The DCC-agnostic ``toggle_camera_view`` dispatch lives on the shared base
``tentacle.slots._slots.Slots`` and is pinned, without Maya, in
``test_slots_base.py::TestToggleCameraView``.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.cameras import CamerasSlots


def _item(text, parent, data=None):
    """A list000 leaf: its text, its category's text and its data."""
    item = mock.MagicMock()
    item.item_text.return_value = text
    item.parent_item_text.return_value = parent
    item.item_data.return_value = data
    return item


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = CamerasSlots(self.sb)
        self.cams = self.sb.tk.CamUtils
        self.visibility = self.sb.tk.CameraVisibility


class TestViews(_SlotsCase):
    def test_each_button_maps_to_mayatks_view_name(self):
        """Right is Maya's 'side' camera (historical naming)."""
        for name, view in (
            ("b000", "back"),
            ("b001", "top"),
            ("b002", "side"),
            ("b003", "left"),
            ("b004", "persp"),
            ("b005", "front"),
            ("b006", "bottom"),
        ):
            getattr(self.slots, name)()
            self.cams.switch_viewport_camera.assert_called_with(view)
        self.sb.message_box.assert_not_called()

    def test_a_refused_switch_is_shown(self):
        self.cams.switch_viewport_camera.side_effect = RuntimeError("No 3D viewport")
        self.slots.b001()
        self.sb.message_box.assert_called_once_with("No 3D viewport")

    def test_a_switch_that_found_no_camera_is_reported(self):
        self.cams.switch_viewport_camera.return_value = None  # mayatk: default cam missing
        self.slots.b005()
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("front", message)


class TestAlignView(_SlotsCase):
    def test_nothing_selected_says_so(self):
        self.cams.align_view_to_selection.return_value = []
        self.slots.b007()
        self.sb.message_box.assert_called_once_with(CamerasSlots.NOTHING_SELECTED)

    def test_an_alignment_says_nothing(self):
        self.cams.align_view_to_selection.return_value = ["pCube1.f[0]"]
        self.slots.b007()
        self.sb.message_box.assert_not_called()

    def test_a_refusal_is_shown(self):
        self.cams.align_view_to_selection.side_effect = RuntimeError("No 3D viewport")
        self.slots.b007()
        self.sb.message_box.assert_called_once_with("No 3D viewport")


class TestNavigationTools(_SlotsCase):
    def test_each_button_arms_its_mode(self):
        for name, mode in (
            ("b010", "DOLLY"),
            ("b011", "ROLL"),
            ("b012", "TRACK"),
            ("b013", "ORBIT"),
        ):
            getattr(self.slots, name)()
            self.cams.navigate_view.assert_called_with(mode)

    def test_a_refusal_is_shown(self):
        self.cams.navigate_view.side_effect = RuntimeError("interactive session")
        self.slots.b013()
        self.sb.message_box.assert_called_once_with("interactive session")


class TestList000(_SlotsCase):
    def _build(self, cameras):
        self.cams.get_cameras.return_value = cameras
        widget = mock.MagicMock()
        self.slots.list000_init(widget)
        return widget

    def test_the_categories_in_order_and_their_leaves(self):
        widget = self._build(["shotCam"])
        self.assertEqual(
            [c.args[0] for c in widget.add.call_args_list],
            ["Create Camera", "Select Camera", "Visibility Settings", "Camera Options"],
        )
        added = widget.add.return_value.sublist.add.call_args_list
        self.assertEqual(
            added[0].args[0],
            {"Standard Camera": 35, "Wide Angle Camera": 18, "Telephoto Camera": 85},
        )
        self.assertEqual(added[1].args[0], ["shotCam"])
        self.assertEqual(
            added[2].args[0],
            [
                "Exclusive to Camera",
                "Hidden from Camera",
                "Remove from Exclusive",
                "Remove from Hidden",
                "Remove All for Camera",
                "Remove All",
            ],
        )
        self.assertEqual(added[3].args[0], ["Auto Adjust Clipping", "Reset Clipping"])

    def test_no_camera_to_pick_leaves_out_select_camera(self):
        widget = self._build([])
        self.assertNotIn("Select Camera", [c.args[0] for c in widget.add.call_args_list])

    def test_create_camera_takes_the_leafs_focal_length(self):
        self.slots.list000(_item("Telephoto Camera", "Create Camera", 85))
        self.cams.create_camera.assert_called_once_with(focal_length=85.0)

    def test_select_camera_selects_and_looks_through(self):
        self.slots.list000(_item("shotCam", "Select Camera"))
        self.cams.look_through.assert_called_once_with("shotCam", select=True)

    def test_each_visibility_leaf_runs_its_operation(self):
        for text, operation in (
            ("Exclusive to Camera", "set_exclusive"),
            ("Hidden from Camera", "set_hidden"),
            ("Remove from Exclusive", "remove_from_exclusive"),
            ("Remove from Hidden", "remove_from_hidden"),
            ("Remove All for Camera", "remove_all"),
            ("Remove All", "remove_all_for_all"),
        ):
            self.slots.list000(_item(text, "Visibility Settings"))
            getattr(self.visibility, operation).assert_called_once_with()

    def test_a_grown_set_reports_its_size(self):
        self.visibility.set_exclusive.return_value = ["a", "b"]
        self.slots.list000(_item("Exclusive to Camera", "Visibility Settings"))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("<hl>2</hl>", message)

    def test_a_removal_reports_nothing(self):
        self.slots.list000(_item("Remove All", "Visibility Settings"))
        self.sb.message_box.assert_not_called()

    def test_a_refusal_is_shown(self):
        self.visibility.set_hidden.side_effect = ValueError("A camera is required")
        self.slots.list000(_item("Hidden from Camera", "Visibility Settings"))
        self.sb.message_box.assert_called_once_with("A camera is required")

    def test_clipping_leaves_send_their_directive(self):
        for text, directive in (("Auto Adjust Clipping", "auto"), ("Reset Clipping", "reset")):
            self.slots.list000(_item(text, "Camera Options"))
            self.cams.adjust_camera_clipping.assert_called_with(
                near_clip=directive, far_clip=directive
            )

    def test_a_category_row_runs_nothing(self):
        self.slots.list000(_item("Create Camera", None))
        self.cams.create_camera.assert_not_called()
        self.sb.message_box.assert_not_called()


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestCamerasInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def test_align_with_nothing_selected_warns_and_makes_no_camera(self):
        self.cmds.select(clear=True)
        self.slots.b007()
        self.assertFalse(self.cmds.objExists("alignToPoly"))
        self.assertTrue(self.sb.message_box.called)

    def test_select_camera_lists_user_cameras_only(self):
        cam = self.cmds.camera(name="shot_cam")[0]
        widget = mock.MagicMock()
        self.slots.list000_init(widget)
        added = [c.args[0] for c in widget.add.return_value.sublist.add.call_args_list]
        self.assertIn([cam], added)

    def test_create_camera_sets_the_focal_length(self):
        before = set(self.cmds.ls(type="camera"))
        self.slots.list000(_item("Wide Angle Camera", "Create Camera", 18))
        (shape,) = set(self.cmds.ls(type="camera")) - before
        self.assertAlmostEqual(self.cmds.getAttr(f"{shape}.focalLength"), 18.0)


if __name__ == "__main__":
    unittest.main()
