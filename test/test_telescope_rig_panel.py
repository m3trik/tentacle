#!/usr/bin/python
# coding=utf-8
"""The Telescope Rig panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``. The selection roles themselves are the library's
(``TelescopeRig.partition_selection``), tested in mayatk and blendertk.
"""

import logging
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.telescope_rig import TelescopeRigSlots


def _panel(collapsed=2.0, axis=1, roles=(None, [], None)):
    """A Slots instance over a mock ui and a mock toolkit whose selection reads
    as *roles* (``(base, segments, end)``)."""
    sb = mock.MagicMock()
    ui = sb.loaded_ui.telescope_rig
    ui.spin_collapsed.value.return_value = collapsed
    ui.cmb_axis.currentIndex.return_value = axis
    sb.tk.TelescopeRig.partition_selection.return_value = roles
    return TelescopeRigSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestTelescopeRigBuild(_PanelCase):
    def test_the_roles_and_options_reach_the_host_engine(self):
        slots, sb = _panel(roles=("Base", ["S1", "S2"], "End"))
        slots.build_rig()
        engine = sb.tk.TelescopeRig.return_value
        engine.setup_telescope_rig.assert_called_once_with(
            base_locator="Base",
            end_locator="End",
            segments=["S1", "S2"],
            collapsed_distance=2.0,
            aim_axis="y",
        )
        self.assertIs(slots.bundle, engine.setup_telescope_rig.return_value)
        sb.message_box.assert_not_called()

    def test_missing_handles_are_left_for_the_engine_to_create(self):
        slots, sb = _panel(roles=(None, ["outer", "inner"], None))
        slots.build_rig()
        kwargs = sb.tk.TelescopeRig.return_value.setup_telescope_rig.call_args.kwargs
        self.assertIsNone(kwargs["base_locator"])
        self.assertIsNone(kwargs["end_locator"])
        self.assertEqual(kwargs["segments"], ["outer", "inner"])

    def test_a_zero_collapsed_distance_is_auto(self):
        """0 is the spinbox's Auto special value: the engine derives it."""
        slots, sb = _panel(collapsed=0.0, roles=(None, ["s1", "s2", "s3"], None))
        slots.build_rig()
        kwargs = sb.tk.TelescopeRig.return_value.setup_telescope_rig.call_args.kwargs
        self.assertIsNone(kwargs["collapsed_distance"])

    def test_the_axis_combo_index_names_the_aim_axis(self):
        for index, axis in enumerate(("x", "y", "z")):
            with self.subTest(axis=axis):
                slots, sb = _panel(axis=index, roles=(None, ["s1", "s2"], None))
                slots.build_rig()
                engine = sb.tk.TelescopeRig.return_value.setup_telescope_rig
                self.assertEqual(engine.call_args.kwargs["aim_axis"], axis)

    def test_fewer_than_two_segments_is_refused_before_the_engine_runs(self):
        for roles in ((None, [], None), ("Base", ["only"], None)):
            with self.subTest(roles=roles):
                slots, sb = _panel(roles=roles)
                slots.build_rig()
                sb.tk.TelescopeRig.assert_not_called()
                sb.message_box.assert_called_once()
                self.assertIn("at least 2 segments", sb.message_box.call_args.args[0])

    def test_an_engine_refusal_reaches_the_message_box(self):
        slots, sb = _panel(roles=("Base", ["S1", "S2"], "End"))
        engine = sb.tk.TelescopeRig.return_value
        engine.setup_telescope_rig.side_effect = ValueError("boom")
        slots.build_rig()
        sb.message_box.assert_called_once()
        self.assertIn("boom", sb.message_box.call_args.args[0])
        self.assertIsNone(slots.bundle)

    def test_each_engine_streams_into_the_log_panel_after_it_is_built(self):
        """The redirect is what raises the engine to INFO, ungating its report;
        ``TelescopeRig()`` sets WARNING, so it must follow the construction."""
        slots, sb = _panel(roles=("Base", ["S1", "S2"], "End"))
        slots.build_rig()
        engine = sb.tk.TelescopeRig.return_value
        engine.logger.setup_logging_redirect.assert_called_with(
            sb.loaded_ui.telescope_rig.txt003
        )
        engine.logger.set_text_handler.assert_called_with(
            sb.registered_widgets.TextEditLogHandler
        )

    def test_the_panel_logs_at_info_so_its_read_back_renders(self):
        slots, _ = _panel()
        self.assertTrue(slots.logger.isEnabledFor(logging.INFO))


class TestTelescopeRigRemove(_PanelCase):
    def test_the_rigs_on_the_selection_are_torn_down_in_one_call(self):
        """A selection spanning two rigs is ONE teardown: one undo step."""
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = ["S1", "T1"]
        first, second = object(), object()
        sb.tk.TelescopeRig.find_bundles.return_value = [first, second]
        slots.remove_rig()
        sb.tk.TelescopeRig.find_bundles.assert_called_once_with(["S1", "T1"])
        sb.tk.TelescopeRig.return_value.teardown.assert_called_once_with(
            [first, second]
        )
        sb.message_box.assert_not_called()

    def test_a_selection_without_a_rig_says_so(self):
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = ["stray"]
        sb.tk.TelescopeRig.find_bundles.return_value = []
        slots.remove_rig()
        sb.tk.TelescopeRig.return_value.teardown.assert_not_called()
        self.assertIn("No telescope rig", sb.message_box.call_args.args[0])

    def test_nothing_selected_removes_the_last_build(self):
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = []
        last = object()
        slots.bundle = last
        slots.remove_rig()
        sb.tk.TelescopeRig.find_bundles.assert_not_called()
        sb.tk.TelescopeRig.return_value.teardown.assert_called_once_with([last])
        self.assertIsNone(slots.bundle)

    def test_nothing_selected_and_nothing_built_says_so(self):
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = []
        slots.remove_rig()
        sb.tk.TelescopeRig.assert_not_called()
        self.assertIn("Nothing selected", sb.message_box.call_args.args[0])

    def test_log_links_dispatch_through_the_host(self):
        slots, sb = _panel()
        slots._on_log_link_clicked("action://select?node=Base")
        sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=Base", slots.logger
        )


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestTelescopeRigPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)

    def _real(self):
        slots, sb = _panel(collapsed=2.0, axis=1)
        sb.tk = maya_module("mayatk")
        return slots, sb

    def test_build_reads_the_selection_order_and_remove_takes_it_back(self):
        cmds = self.cmds
        base = cmds.spaceLocator(name="tscBase")[0]
        end = cmds.spaceLocator(name="tscEnd")[0]
        cmds.xform(end, worldSpace=True, translation=(0, 10, 0))
        segments = []
        for i in range(3):
            seg = cmds.polyCube(name=f"tscSeg{i}")[0]
            cmds.xform(seg, worldSpace=True, translation=(0, 1 + i * 2, 0))
            segments.append(seg)
        cmds.select(base, *segments, end)  # base first, end last

        slots, sb = self._real()
        slots.build_rig()
        sb.message_box.assert_not_called()
        bundle = slots.bundle
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.segments, segments)
        self.assertEqual(bundle.created_locators, [])  # the selected locators ride
        self.assertTrue(cmds.objExists(bundle.distance_node))

        cmds.select(segments[1])  # any part of the rig
        slots.remove_rig()
        sb.message_box.assert_not_called()
        self.assertFalse(cmds.objExists(bundle.distance_node))
        self.assertEqual(sb.tk.TelescopeRig.scene_bundles(), [])
        for node in (base, end, *segments):
            self.assertTrue(cmds.objExists(node))

    def test_a_bare_two_part_strut_builds_its_own_handles(self):
        cmds = self.cmds
        outer = cmds.polyCylinder(name="tscOuter", height=4)[0]
        inner = cmds.polyCylinder(name="tscInner", height=4, radius=0.5)[0]
        cmds.xform(inner, worldSpace=True, translation=(0, 3, 0))
        cmds.select(outer, inner)

        slots, sb = self._real()
        slots.build_rig()
        sb.message_box.assert_not_called()
        self.assertEqual(len(slots.bundle.created_locators), 2)

        cmds.select(clear=True)  # nothing selected: the last build goes
        slots.remove_rig()
        sb.message_box.assert_not_called()
        self.assertIsNone(slots.bundle)
        self.assertFalse(cmds.ls("telescope_*_LOC"))


if __name__ == "__main__":
    unittest.main()
