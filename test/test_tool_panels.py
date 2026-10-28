#!/usr/bin/python
# coding=utf-8
"""The small shared tool panels' Slots classes (``slots/tools/``), one per tool.

Each reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` / ``btk`` and records what the panel asks of it: plain pytest, no DCC,
no widgets loaded. In Maya the same classes drive the real ``mtk`` (the
``InMaya`` cases); Blender's are ``test/blender/panel_slots_check.py``.
"""

import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.bevel import BevelSlots
from tentacle.slots.tools.calculator import CalculatorSlots
from tentacle.slots.tools.cut_on_axis import CutOnAxisSlots
from tentacle.slots.tools.duplicate_grid import DuplicateGridSlots
from tentacle.slots.tools.duplicate_linear import DuplicateLinearSlots
from tentacle.slots.tools.dynamic_pipe import DynamicPipeSlots
from tentacle.slots.tools.exploded_view import ExplodedViewSlots
from tentacle.slots.tools.snap import SnapSlots


def _panel(cls, ui_name, values=None, tk=None):
    """A *cls* instance over a mock ui (*values* set on its widgets) and a mock
    toolkit, or *tk* (handed over before the panel is built, as ``Slots.tk``
    is)."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    ui = getattr(sb.loaded_ui, ui_name)
    for name, value in (values or {}).items():
        widget = getattr(ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value
        widget.currentIndex.return_value = value
        widget.currentData.return_value = value
    return cls(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestBevelPanel(_PanelCase):
    def test_previews_through_the_host_toolkit(self):
        slots, sb = _panel(BevelSlots, "bevel")
        ui = sb.loaded_ui.bevel
        sb.tk.Preview.assert_called_once_with(
            slots,
            ui.chk000,
            ui.b000,
            message_func=sb.message_box,
            undo_message="Bevel",
        )

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        slots, sb = _panel(BevelSlots, "bevel", {"s000": 0.25, "s001": 3})
        # Maya's Preview passes a contract, Blender's none: both are accepted.
        slots.perform_operation(["cube.e[0]"], None)
        slots.perform_operation(["cube.e[0]"])
        sb.tk.Bevel.bevel.assert_called_with(["cube.e[0]"], 0.25, 3)

    def test_preserves_geometry_for_the_preview(self):
        """polyBevel3 rewrites the mesh's edge topology in place: without the
        snapshot, each refresh stacks a bevel on different edges."""
        self.assertTrue(getattr(BevelSlots, "PRESERVE_GEOMETRY", False))


class TestDuplicateLinearPanel(_PanelCase):
    def test_lists_the_host_pivots_and_previews_through_the_host(self):
        slots, sb = _panel(DuplicateLinearSlots, "duplicate_linear")
        ui = sb.loaded_ui.duplicate_linear
        self.assertIs(slots.pivot_options, sb.tk.XformUtils.get_pivot_options())
        ui.cmb002.add.assert_called_once_with(slots.pivot_options, prefix="Pivot:")
        sb.tk.Preview.assert_called_once_with(
            slots,
            ui.chk000,
            ui.b000,
            message_func=sb.message_box,
            undo_message="Duplicate Linear",
        )

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        values = {f"s{i:03d}": float(i) for i in range(12)}
        values.update(s009=5, cmb002="world", cmb001="weighted", cmb_inst="instance")
        slots, sb = _panel(DuplicateLinearSlots, "duplicate_linear", values)
        slots.perform_operation(["cube"], None)
        slots.perform_operation(["cube"])
        engine = sb.tk.DuplicateLinear.duplicate_linear
        engine.assert_called_with(
            ["cube"],
            4,  # five copies counting the original
            (0.0, 1.0, 2.0),
            (3.0, 4.0, 5.0),
            (6.0, 7.0, 8.0),
            10.0,
            11.0,
            "world",
            "weighted",
            True,
        )
        self.assertIs(slots.copies, engine.return_value)

    def test_weight_spinners_follow_the_mode(self):
        slots, sb = _panel(DuplicateLinearSlots, "duplicate_linear", {"cmb001": "linear"})
        ui = sb.loaded_ui.duplicate_linear
        slots.toggle_weight_ui()
        ui.s010.setEnabled.assert_called_with(False)
        ui.s011.setEnabled.assert_called_with(False)
        ui.cmb001.currentData.return_value = "weighted"
        slots.toggle_weight_ui()
        ui.s010.setEnabled.assert_called_with(True)
        ui.s011.setEnabled.assert_called_with(True)

    def test_mutates_selection_for_the_preview(self):
        """The captured selection can be invalidated between refreshes; Maya's
        Preview restores it by UUID when the class says so."""
        self.assertTrue(getattr(DuplicateLinearSlots, "MUTATES_SELECTION", False))


class TestDuplicateGridPanel(_PanelCase):
    VALUES = {"s000": 2, "s001": 3, "s002": 1, "s003": 0.5, "s004": 0.0, "s005": 1.0}

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        slots, sb = _panel(
            DuplicateGridSlots, "duplicate_grid", {**self.VALUES, "cmb000": "combine"}
        )
        slots.perform_operation(["cube"], None)
        slots.perform_operation(["cube"])
        engine = sb.tk.DuplicateGrid.duplicate_grid
        engine.assert_called_with(
            ["cube"], dimensions=(2, 3, 1), spacing=(0.5, 0.0, 1.0), mode="combine"
        )
        self.assertIs(slots.copies, engine.return_value)

    def test_a_declined_bulk_build_runs_nothing_and_stops_the_preview(self):
        slots, sb = _panel(
            DuplicateGridSlots, "duplicate_grid", {"s000": 20, "s001": 20, "s002": 20}
        )
        sb.message_box.return_value = "No"
        slots.preview.is_enabled = True
        with mock.patch("qtpy.QtCore.QTimer.singleShot") as later:
            slots.perform_operation(["cube"])
        sb.tk.DuplicateGrid.duplicate_grid.assert_not_called()
        self.assertEqual(slots.copies, [])
        later.assert_called_once_with(0, slots.preview.disable)

    def test_a_confirmed_bulk_build_asks_once(self):
        slots, sb = _panel(
            DuplicateGridSlots, "duplicate_grid", {"s000": 20, "s001": 20, "s002": 20}
        )
        sb.message_box.return_value = "Yes"
        slots.perform_operation(["cube"])
        slots.perform_operation(["cube"])
        self.assertEqual(sb.message_box.call_count, 1)
        self.assertEqual(sb.tk.DuplicateGrid.duplicate_grid.call_count, 2)

    def test_mutates_selection_for_the_preview(self):
        self.assertTrue(getattr(DuplicateGridSlots, "MUTATES_SELECTION", False))


class TestCutOnAxisPanel(_PanelCase):
    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        values = {"s000": 3, "s001": 0.5, "s002": 0.0, "s003": 0.4, "s004": 2.0}
        values.update(cmb000=1, cmb001="weighted", chk005=True, chk006=False)
        slots, sb = _panel(CutOnAxisSlots, "cut_on_axis", values)
        sb.get_axis_from_checkboxes.return_value = "-y"
        slots.perform_operation(["cube"], None)
        slots.perform_operation(["cube"])
        sb.tk.CutOnAxis.perform_cut_on_axis.assert_called_with(
            ["cube"],
            axis="-y",
            pivot="object",
            cuts=3,
            cut_offset=0.5,
            cut_spacing=0.0,
            distribution="weighted",
            weight_bias=0.4,
            weight_curve=2.0,
            delete=True,
            mirror=False,
        )

    def test_watches_the_pivot_where_the_host_can(self):
        slots, sb = _panel(CutOnAxisSlots, "cut_on_axis")
        sb.tk.PivotWatcher.return_value.start.assert_called_once_with()
        self.assertIs(slots._pivot_watcher, sb.tk.PivotWatcher.return_value)

        sb = mock.MagicMock()
        del sb.tk.PivotWatcher  # a host without one (Blender)
        slots = CutOnAxisSlots(sb)
        self.assertFalse(hasattr(slots, "_pivot_watcher"))

    def test_preserves_geometry_for_the_preview(self):
        """polyCut on a historyless mesh holds the only pristine copy in an
        intermediate shape: without the snapshot, cuts stack on every refresh."""
        self.assertTrue(getattr(CutOnAxisSlots, "PRESERVE_GEOMETRY", False))


class TestExplodedViewPanel(_PanelCase):
    def test_each_button_drives_the_host_engine(self):
        slots, sb = _panel(ExplodedViewSlots, "exploded_view")
        engine = sb.tk.ExplodedView.return_value
        self.assertIs(slots.engine, engine)
        for button, method in (
            ("b000", "explode"),
            ("b001", "un_explode"),
            ("b002", "un_explode_all"),
            ("b003", "toggle_explode"),
        ):
            getattr(slots, button)()
            getattr(engine, method).assert_called_once_with()


class TestDynamicPipePanel(_PanelCase):
    def test_initialize_builds_through_the_host_selection(self):
        slots, sb = _panel(DynamicPipeSlots, "dynamic_pipe")
        slots.b000()
        self.assertIs(slots.pipe, sb.tk.DynamicPipe.from_selection.return_value)
        sb.message_box.assert_not_called()

    def test_an_under_selection_is_said(self):
        slots, sb = _panel(DynamicPipeSlots, "dynamic_pipe")
        sb.tk.DynamicPipe.from_selection.side_effect = ValueError("Select two.")
        slots.b000()
        self.assertIsNone(slots.pipe)
        self.assertIn("Select two.", sb.message_box.call_args.args[0])


class TestSnapPanel(_PanelCase):
    def _snap(self, split):
        slots, sb = _panel(SnapSlots, "snap")
        sb.tk.Snap.source_and_target.return_value = split
        return slots, sb, sb.tk.Snap, sb.loaded_ui.snap

    def test_snap_to_surface_reads_the_option_box(self):
        slots, sb, snap, ui = self._snap((["a", "b"], "target"))
        ui.b000.menu.s000.value.return_value = 0.5
        ui.b000.menu.s001.value.return_value = 0.0  # 0: no limit
        ui.b000.menu.chk000.isChecked.return_value = True
        snap.snap_to_surface.return_value = 7
        slots.b000()
        snap.snap_to_surface.assert_called_once_with(
            ["a", "b"], "target", offset=0.5, threshold=None, invert=True
        )
        self.assertIn("7 vertices", sb.message_box.call_args.args[0])

    def test_closest_vertex_needs_exactly_two(self):
        slots, sb, snap, ui = self._snap((["a", "b"], "target"))
        slots.b001()
        snap.snap_to_closest_vertex.assert_not_called()
        self.assertIn("exactly two", sb.message_box.call_args.args[0])

        slots, sb, snap, ui = self._snap((["a"], "target"))
        ui.b001.menu.s002.value.return_value = 2.5
        slots.b001()
        snap.snap_to_closest_vertex.assert_called_once_with("a", "target", tolerance=2.5)

    def test_an_under_selection_runs_nothing(self):
        slots, sb, snap, ui = self._snap(([], None))
        slots.b000()
        snap.snap_to_surface.assert_not_called()
        sb.message_box.assert_called_once()

    def test_snap_to_grid_defaults_to_every_axis(self):
        slots, sb, snap, ui = self._snap(([], None))
        ui.b002.menu.s003.value.return_value = 0.25
        ui.b002.menu.txt000.text.return_value = ""
        slots.b002()
        snap.snap_to_grid.assert_called_once_with(grid_size=0.25, axes="xyz")


class _Controller:
    """A host's ``CalculatorController``: pythontk's math, a 24 fps scene at 12."""

    @staticmethod
    def calculate(expression):
        return ptk.MathUtils.eval_expression(expression)

    @staticmethod
    def convert_unit(value, from_unit, to_unit):
        return ptk.MathUtils.convert_length_unit(value, from_unit, to_unit)

    @staticmethod
    def get_fps_value():
        return 24.0

    @staticmethod
    def get_current_time():
        return "12"

    @classmethod
    def frames_to_sec(cls, frames):
        return str(round(frames / cls.get_fps_value(), 4))

    @classmethod
    def sec_to_frames(cls, seconds):
        return str(round(seconds * cls.get_fps_value(), 2))


class TestCalculatorPanel(_PanelCase):
    def setUp(self):
        super().setUp()
        sb = mock.MagicMock()
        sb.tk.CalculatorController = _Controller
        self.ui = sb.loaded_ui.calculator
        self.ui.txt_display.text.return_value = ""
        with mock.patch("qtpy.QtWidgets.QPushButton"):
            self.calc = CalculatorSlots(sb)

    def _shows(self, display, action, expected):
        self.ui.txt_display.text.return_value = display
        action()
        self.ui.txt_display.setText.assert_called_with(expected)

    def test_builds_the_grids_and_the_unit_combos(self):
        self.assertTrue(self.ui.calc_container.layout().addWidget.called)
        self.assertTrue(self.ui.maya_container.layout().addWidget.called)
        self.ui.cmb_unit_from.addItems.assert_called_once_with(CalculatorSlots._UNITS)

    def test_entry_keys(self):
        self._shows("1", lambda: self.calc.on_input("+"), "1+")
        self._shows("123", self.calc.on_backspace, "12")
        self.calc.on_clear()
        self.ui.txt_display.clear.assert_called()

    def test_evaluation(self):
        self._shows("2+2", self.calc.on_equal, "4")
        self._shows("10/4", self.calc.on_equal, "2.5")
        self._shows("1/0", self.calc.on_equal, "Error")

    def test_unit_conversion_evaluates_the_display_first(self):
        self.ui.cmb_unit_from.currentText.return_value = "cm"
        self.ui.cmb_unit_to.currentText.return_value = "m"
        self._shows("50*2", self.calc.on_convert_units, "1.0")
        self._shows("1/0", self.calc.on_convert_units, "Error")

    def test_time_helpers_read_the_host_scene(self):
        self._shows("", self.calc.get_fps, "24.0")
        self._shows("", self.calc.get_current_time, "12")
        self._shows("48", self.calc.frames_to_sec, "2.0")
        self._shows("1+1", self.calc.sec_to_frames, "48.0")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestToolPanelsInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)

    def _real(self, cls, ui_name, values):
        slots, _sb = _panel(cls, ui_name, values, tk=maya_module("mayatk"))
        return slots

    def test_bevel_chamfers_the_edges(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="bevSrc")[0]
        faces = cmds.polyEvaluate(cube, face=True)
        self._real(BevelSlots, "bevel", {"s000": 0.2, "s001": 1}).perform_operation(
            [f"{cube}.e[0]"], None
        )
        self.assertGreater(cmds.polyEvaluate(cube, face=True), faces)

    def test_duplicate_linear_makes_the_copies(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="linSrc")[0]
        values = {f"s{i:03d}": 0.0 for i in range(12)}
        values.update(
            s000=2.0, s006=1.0, s007=1.0, s008=1.0, s009=3, s010=0.5, s011=1.0,
            cmb002="object", cmb001="linear", cmb_inst="copy",
        )
        slots = self._real(DuplicateLinearSlots, "duplicate_linear", values)
        slots.perform_operation([cube], None)
        meshes = cmds.ls(type="mesh", noIntermediate=True)
        self.assertEqual(len(meshes), 3, meshes)

    def test_duplicate_grid_fills_the_grid(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="gridSrc")[0]
        values = {"s000": 2, "s001": 2, "s002": 1, "s003": 0.0, "s004": 0.0, "s005": 0.0}
        values["cmb000"] = "copy"
        slots = self._real(DuplicateGridSlots, "duplicate_grid", values)
        slots.perform_operation([cube], None)
        self.assertGreaterEqual(len(cmds.ls(type="mesh", noIntermediate=True)), 4)

    def test_exploded_view_round_trips_the_selection(self):
        cmds = self.cmds
        # Overlapping but apart: two cubes at one spot give the push no direction.
        a, b = cmds.polyCube(name="expA")[0], cmds.polyCube(name="expB")[0]
        cmds.move(0.25, 0, 0, a)
        cmds.move(-0.25, 0, 0, b)
        cmds.select(a, b)
        slots = self._real(ExplodedViewSlots, "exploded_view", {})
        slots.b000()
        # The explode stamps each object's original position (its undo record).
        self.assertTrue(cmds.attributeQuery("original_position", node=a, exists=True))
        slots.b002()
        self.assertFalse(cmds.attributeQuery("original_position", node=a, exists=True))
        restored = cmds.xform(a, q=True, translation=True, worldSpace=True)
        self.assertEqual([round(v, 4) for v in restored], [0.25, 0.0, 0.0])

    def test_snap_to_grid_snaps_the_selected_pivot(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="snapSrc")[0]
        cmds.move(0.3, 1.6, 0, cube)
        cmds.select(cube)
        slots = self._real(SnapSlots, "snap", {})
        slots.ui.b002.menu.s003.value.return_value = 1.0
        slots.ui.b002.menu.txt000.text.return_value = "xyz"
        slots.b002()
        pivot = cmds.xform(cube, q=True, rotatePivot=True, worldSpace=True)
        self.assertEqual([round(v, 4) for v in pivot], [0.0, 2.0, 0.0])

    def test_dynamic_pipe_lofts_through_the_selected_locators(self):
        cmds = self.cmds
        locators = [cmds.spaceLocator(name=f"pipeLoc{i}")[0] for i in range(3)]
        for i, loc in enumerate(locators):
            cmds.move(0, i * 5, 0, loc)
        cmds.select(locators)
        slots = self._real(DynamicPipeSlots, "dynamic_pipe", {})
        slots.b000()
        self.assertIsNotNone(slots.pipe)
        self.assertEqual(len(slots.pipe.pipe_segments), 2)


if __name__ == "__main__":
    unittest.main()
