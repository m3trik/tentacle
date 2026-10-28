#!/usr/bin/python
# coding=utf-8
"""The Curve to Tube panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``; Blender's engine and its Preview's Select Result
are ``blendertk/test/test_curve_to_tube.py`` and ``test_preview.py``.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.curve_to_tube import CurveToTubeSlots

#: Both hosts' ``CurveToTube.OUTPUT_TYPES``: the combo saves an index, so the order is kept.
OUTPUT_TYPES = (("NURBS Tube", "nurbs"), ("Polygon Tube", "polygon"))

#: The panel's defaults, as its .ui and __init__ set them: what a commit reads untouched.
DEFAULTS = {
    "cmb000": "nurbs",
    "s000": 1.0,
    "s001": 8,
    "s002": 1,
    "s003": 3,
    "chk001": True,
    "cmb_topology": "quads",
    "chk003": False,
    "chk004": True,
}


def _panel(values=None):
    """A Slots instance over a mock ui (*values* set on its widgets) and a mock toolkit."""
    sb = mock.MagicMock()
    sb.tk.CurveToTube.OUTPUT_TYPES = OUTPUT_TYPES
    ui = sb.loaded_ui.curve_to_tube
    for name, value in (values or {}).items():
        widget = getattr(ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value
        widget.currentData.return_value = value
    return CurveToTubeSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestCurveToTubePanel(_PanelCase):
    def test_previews_through_the_host_toolkit_with_select_result(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.curve_to_tube
        sb.tk.Preview.assert_called_once_with(
            slots,
            ui.chk000,
            ui.b000,
            message_func=sb.message_box,
            undo_message="Curve to Tube",
            select_result_checkbox=ui.chk004,
            result_provider=mock.ANY,
        )
        # The provider hands the Preview the current build, not the first one.
        provider = sb.tk.Preview.call_args.kwargs["result_provider"]
        slots.last_tubes = ["tube1", "tube2"]
        self.assertEqual(provider(), ["tube1", "tube2"])

    def test_lists_the_host_output_types_and_the_topologies(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.curve_to_tube
        ui.cmb000.add.assert_called_once_with(list(OUTPUT_TYPES))
        ui.cmb_topology.add.assert_called_once_with(
            [("Quads", "quads"), ("Triangles", "triangles")]
        )
        ui.cmb_topology.setAsCurrent.assert_called_once_with("quads")

    def test_the_operation_reads_the_panel_into_the_host_engine(self):
        values = {**DEFAULTS, "cmb000": "polygon", "s000": 0.5, "s002": 2}
        values.update(cmb_topology="triangles", chk003=True)
        slots, sb = _panel(values)
        engine = sb.tk.CurveToTube.create
        # Maya's Preview passes a contract, Blender's none: both are accepted.
        slots.perform_operation(["curve1"], None)
        slots.perform_operation(["curve1"])
        engine.assert_called_with(
            ["curve1"],
            output_type="polygon",
            radius=0.5,
            sections=8,
            path_divisions=2,
            degree=3,
            caps=True,
            quads=False,
            live=True,
        )
        self.assertIs(slots.last_tubes, engine.return_value)

    def test_the_footer_shows_the_host_stats(self):
        slots, sb = _panel(DEFAULTS)
        footer = sb.loaded_ui.curve_to_tube.footer
        footer.setDefaultStatusText.assert_called_once_with(
            "Select curve(s), then Preview."
        )
        sb.tk.CurveToTube.describe.return_value = "1,024 tris"
        slots.perform_operation(["curve1"])
        sb.tk.CurveToTube.describe.assert_called_once_with(slots.last_tubes)
        footer.setStatusText.assert_called_with("1,024 tris")

    def test_an_engine_refusal_is_left_to_the_preview(self):
        """No curve selected: the engine raises, and the host's Preview says
        why and switches itself off (the panel keeps no gate of its own)."""
        slots, sb = _panel(DEFAULTS)
        sb.tk.CurveToTube.create.side_effect = RuntimeError("No curve selected.")
        with self.assertRaisesRegex(RuntimeError, "No curve"):
            slots.perform_operation(["cube"])
        sb.loaded_ui.curve_to_tube.footer.setStatusText.assert_not_called()

    def test_options_follow_the_output_type(self):
        slots, sb = _panel({"cmb000": "polygon"})
        ui = sb.loaded_ui.curve_to_tube
        for widget, enabled in (
            (ui.s002, True),  # Path Res
            (ui.chk001, True),  # Caps
            (ui.cmb_topology, True),  # Quads / Triangles
            (ui.s003, False),  # Degree: NURBS only
        ):
            widget.setEnabled.assert_called_with(enabled)
        ui.cmb000.currentData.return_value = "nurbs"
        slots._toggle_output_options()
        ui.s002.setEnabled.assert_called_with(False)
        ui.s003.setEnabled.assert_called_with(True)

    def test_preserves_geometry_for_the_preview(self):
        """A live polygon tube resamples its source curve in place (Maya): without
        the snapshot, the rollback leaves the resampled curve behind."""
        self.assertTrue(getattr(CurveToTubeSlots, "PRESERVE_GEOMETRY", False))


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestCurveToTubePanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.curve = self.cmds.curve(
            d=3, p=[(0, 0, 0), (3, 2, 0), (6, -2, 0), (9, 0, 0)], name="tubePath"
        )

    def _build(self, output_type):
        slots, sb = _panel({**DEFAULTS, "cmb000": output_type})
        sb.tk = maya_module("mayatk")
        slots.perform_operation([self.curve], None)
        footer = sb.loaded_ui.curve_to_tube.footer
        return slots, footer.setStatusText.call_args.args[0]

    def test_a_polygon_tube_and_its_triangle_count(self):
        slots, stats = self._build("polygon")
        self.assertEqual(len(slots.last_tubes), 1)
        self.assertTrue(
            self.cmds.listRelatives(slots.last_tubes[0], shapes=True, type="mesh")
        )
        self.assertTrue(self.cmds.objExists(self.curve), "the source curve went")
        self.assertTrue(stats.endswith(" tris"), stats)

    def test_a_nurbs_tube_and_its_spans(self):
        slots, stats = self._build("nurbs")
        self.assertTrue(
            self.cmds.listRelatives(
                slots.last_tubes[0], shapes=True, type="nurbsSurface"
            )
        )
        self.assertIn("spans", stats)


if __name__ == "__main__":
    unittest.main()
