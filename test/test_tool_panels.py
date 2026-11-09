#!/usr/bin/python
# coding=utf-8
"""The small shared tool panels' Slots classes (``slots/tools/``), one per tool.

Each reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` / ``btk`` and records what the panel asks of it: plain pytest, no DCC,
no widgets loaded. In Maya the same classes drive the real ``mtk`` (the
``InMaya`` cases); Blender's are ``test/blender/panel_slots_check.py``.
"""

import unittest
from pathlib import Path
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
from tentacle.slots.tools.mirror import MirrorSlots
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


class TestMirrorPanel(_PanelCase):
    def test_resolve_pivot(self):
        """The combo's index names the pivot; the bounding-box border (4) takes
        the axis sign: +axis the max face, -axis the min."""
        resolve = MirrorSlots._resolve_pivot
        for index, pivot in ((0, "manip"), (1, "object"), (2, "world"), (3, "center")):
            self.assertEqual(resolve(index, "x"), pivot)
        for axis, face in (("x", "xmax"), ("-x", "xmin"), ("y", "ymax"), ("-y", "ymin")):
            self.assertEqual(resolve(4, axis), face)
        self.assertEqual(resolve(4, "-z"), "zmin")
        self.assertEqual(resolve(4, "bogus"), "xmax")
        self.assertEqual(resolve(99, "x"), "manip")

    def test_the_axis_sign_matters_only_for_the_bounding_box_pivots(self):
        relevant = MirrorSlots._axis_sign_relevant
        self.assertEqual([relevant(i) for i in range(5)], [False] * 3 + [True] * 2)

    def test_disables_the_merge_modes_the_host_lacks(self):
        sb = mock.MagicMock()
        sb.tk.EditUtils.MIRROR_MERGE_MODES = (-1, 0, 1)  # Blender's: no Extrude
        ui = sb.loaded_ui.mirror
        ui.cmb001.count.return_value = 4
        MirrorSlots(sb)
        ui.cmb001.model().item.assert_called_once_with(3)

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        values = {"cmb000": 2, "cmb001": 2, "chk006": True, "chk007": False}
        slots, sb = _panel(MirrorSlots, "mirror", values)
        sb.get_axis_from_checkboxes.return_value = "x"
        slots.perform_operation(["cube"], None)
        slots.perform_operation(["cube"])
        sb.tk.EditUtils.mirror.assert_called_with(
            ["cube"], axis="x", pivot="world", mergeMode=1, delete_original=True
        )

    def test_the_center_pivot_symmetrizes_and_instance_refuses_it(self):
        slots, sb = _panel(MirrorSlots, "mirror", {"cmb000": 3, "chk007": False})
        sb.get_axis_from_checkboxes.return_value = "-y"
        slots.perform_operation(["cube"])
        sb.tk.NodeUtils.uninstance.assert_called_once_with(["cube"])
        kwargs = sb.tk.EditUtils.cut_along_axis.call_args.kwargs
        self.assertEqual(
            (kwargs["axis"], kwargs["invert"], kwargs["delete"], kwargs["mirror"]),
            ("-y", True, True, True),
        )
        sb.loaded_ui.mirror.chk007.isChecked.return_value = True
        with self.assertRaisesRegex(ValueError, "can't symmetrize"):
            slots.perform_operation(["cube"])

    def test_no_axis_is_a_fixable_error(self):
        slots, sb = _panel(MirrorSlots, "mirror")
        sb.get_axis_from_checkboxes.return_value = "-"
        with self.assertRaisesRegex(ValueError, "Select an axis"):
            slots.perform_operation(["cube"])
        sb.tk.EditUtils.mirror.assert_not_called()

    def test_mutates_selection_for_the_preview(self):
        self.assertTrue(getattr(MirrorSlots, "MUTATES_SELECTION", False))


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
    """The real ``calculator.ui`` (offscreen): the keys, the display and the
    footer are live widgets, so what the user sees is what is asserted."""

    UI_PATH = Path(__file__).resolve().parents[1] / "tentacle/ui/tools/calculator.ui"

    @classmethod
    def setUpClass(cls):
        try:
            from qtpy import QtWidgets
        except Exception as error:  # pragma: no cover - Qt-less environment
            raise unittest.SkipTest(f"Qt unavailable: {error}") from error
        from uitk.testing import TestSandbox

        TestSandbox.activate()  # the panel's settings stay off the live stores
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        super().setUp()
        from uitk import Switchboard

        sb = Switchboard(ui_source=str(self.UI_PATH), slot_source=CalculatorSlots)
        sb.tk = mock.MagicMock()
        sb.tk.CalculatorController = _Controller
        self.ui = sb.loaded_ui.calculator
        self.calc = sb.get_slots_instance(self.ui)
        self.addCleanup(self.ui.close)
        self.display = self.ui.txt_display
        self.display.clear()  # the field restores its last text

    def _key(self, label):
        """Click the keypad key showing *label*."""
        for button in self.ui.calc_container.findChildren(type(self.ui.btn_convert)):
            if button.text() == label:
                button.click()
                return
        raise AssertionError(f"no key {label!r}")

    def _type(self, text):
        self.display.setText(text)
        self.calc._on_typed(text)

    def _failed(self):
        return self.display.property("actionState") == "invalid"

    def test_builds_the_grids_and_the_unit_combos(self):
        self.assertEqual(self.ui.calc_container.layout().count(), 20)
        self.assertEqual(self.ui.maya_container.layout().count(), 4)
        self.assertEqual(self.ui.cmb_unit_from.count(), len(CalculatorSlots._UNITS))
        self.assertFalse(self.ui.btn_swap_units.icon().isNull(), "the arrow is an icon")

    def test_the_typeset_keys_type_the_engine_operators(self):
        for label in ("7", "×", "2", "−", "1", "÷", "3", "+", "1"):
            self._key(label)
        self.assertEqual(self.display.text(), "7*2-1/3+1")
        self._key("⌫")
        self.assertEqual(self.display.text(), "7*2-1/3+")
        self._key("C")
        self.assertEqual(self.display.text(), "")

    def test_keys_insert_at_the_cursor(self):
        self._type("12")
        self.display.setCursorPosition(1)
        self._key("+")
        self.assertEqual(self.display.text(), "1+2")

    def test_evaluation_keeps_the_expression_on_the_footer(self):
        self._type("10/4")
        self._key("=")
        self.assertEqual(self.display.text(), "2.5")
        self.assertEqual(self.ui.footer.text(), "10/4 =")
        self.assertFalse(self._failed())

    def test_after_a_result_a_number_starts_over_and_an_operator_continues(self):
        self._type("2+2")
        self._key("=")
        self._key("5")
        self.assertEqual(self.display.text(), "5")
        self._type("2+2")
        self._key("=")
        self._key("×")
        self.assertEqual(self.display.text(), "4*")

    def test_a_failure_keeps_the_expression_and_marks_it(self):
        self._type("1/0")
        self._key("=")
        self.assertEqual(self.display.text(), "1/0", "the user's expression stays")
        self.assertTrue(self._failed())
        self.assertIn("1/0", self.ui.footer.text())
        self.assertIn(
            ptk.Palette.status()["error"][0],
            self.ui.footer.status_label.styleSheet(),
            "the reason is in the shared status palette's error color",
        )
        self._key("⌫")  # editing makes it the user's expression again
        self.assertFalse(self._failed())
        self.assertEqual(self.ui.footer.text(), "")

    def test_unit_conversion_evaluates_the_display_first(self):
        self.ui.cmb_unit_from.setCurrentText("cm")
        self.ui.cmb_unit_to.setCurrentText("m")
        self._type("50*2")
        self.calc.on_convert_units()
        self.assertEqual(self.display.text(), "1.0")
        self.assertEqual(self.ui.footer.text(), "100 cm = 1.0 m")
        self._type("1/0")
        self.calc.on_convert_units()
        self.assertEqual(self.display.text(), "1/0")
        self.assertTrue(self._failed())

    def test_the_arrow_swaps_the_units(self):
        self.ui.grp_units.setChecked(True)  # a collapsed group disables its rows
        self.ui.cmb_unit_from.setCurrentText("cm")
        self.ui.cmb_unit_to.setCurrentText("m")
        self.ui.btn_swap_units.click()
        self.assertEqual(
            (self.ui.cmb_unit_from.currentText(), self.ui.cmb_unit_to.currentText()),
            ("m", "cm"),
        )

    def test_time_helpers_read_the_host_scene(self):
        self.calc.get_fps()
        self.assertEqual(self.display.text(), "24.0")
        self.calc.get_current_time()
        self.assertEqual(self.display.text(), "12")
        self._type("48")
        self.calc.frames_to_sec()
        self.assertEqual(self.display.text(), "2.0")
        self.assertEqual(self.ui.footer.text(), "48 frames = 2.0 s at 24 fps")
        self._type("1+1")
        self.calc.sec_to_frames()
        self.assertEqual(self.display.text(), "48.0")

    def test_editing_a_result_drops_its_note(self):
        """The footer names what produced the value on display -- so once the
        user edits it (a key, a backspace, a real keystroke), the note goes."""
        from qtpy.QtTest import QTest

        for edit in (
            lambda: self._key("5"),
            lambda: self._key("⌫"),
            lambda: QTest.keyClicks(self.display, "1"),  # the textEdited wiring
        ):
            self._type("2+2")
            self._key("=")
            self.assertEqual(self.ui.footer.text(), "2+2 =")
            edit()
            self.assertEqual(self.ui.footer.text(), "")

    def test_equal_on_a_result_keeps_its_tape(self):
        self._type("2+2")
        self._key("=")
        self._key("=")
        self.assertEqual((self.display.text(), self.ui.footer.text()), ("4", "2+2 ="))

    def test_the_tape_shows_the_converted_value_in_full(self):
        self.ui.cmb_unit_from.setCurrentText("ft")
        self.ui.cmb_unit_to.setCurrentText("in")
        self._type("1234567")
        self.calc.on_convert_units()
        self.assertTrue(self.ui.footer.text().startswith("1234567 ft = "))

    def test_an_empty_display_asks_for_a_value(self):
        self._type("")
        self.calc.frames_to_sec()
        self.assertTrue(self._failed())
        self.assertEqual(self.display.text(), "")


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
