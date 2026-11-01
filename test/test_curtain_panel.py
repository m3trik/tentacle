#!/usr/bin/python
# coding=utf-8
"""The Curtain panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``, its Preview included. The drape itself, the rail
resolvers and the ``Curtain`` API are the libraries': mayatk's and blendertk's
``test_curtain.py``.
"""

import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.curtain import CurtainSlots

#: The panel's field defaults, as its .ui sets them.
_DEFAULTS = {
    "s000": 3.0,
    "s001": 6.0,
    "s002": 0.0,
    "s003": 5,
    "s004": 0.3,
    "s005": 1.5,
    "s006": 2.5,
    "s007": 0.5,
    "s008": 0.15,
    "s009": 8.0,
    "s010": 0,
    "s011": 0.0,
    "s012": 0.0,
    "s013": 0.0,
    "s014": 0.0,
    "s015": 0,
    "s016": 0.0,
    "s017": 0.0,
    "s018": 0.25,
    "s019": 0.0,
    "s020": 0.0,
    "s021": 0,
    "s022": 0.0,
    "s023": 0.0,
    "s024": 0,
    "s025": 0.0,
    "s026": 0.0,
    "s027": 0.0,
    "chk001": False,
    "chk004": False,
    "chk005": True,
}

#: ``CurtainMesh`` keyword -> the field that sets it (``closed`` comes from the rail).
_DRAPE_FIELDS = {
    "height": "s000",
    "hanging_points": "s003",
    "hang_jitter": "s023",
    "hang_seed": "s024",
    "gravity": "s004",
    "tension": "s005",
    "round_points": "s013",
    "round_gather": "s022",
    "fullness": "s006",
    "taper": "s007",
    "mid_folds": "s019",
    "mid_fold_seed": "s010",
    "creases": "s014",
    "crease_seed": "s015",
    "sway": "s020",
    "sway_seed": "s021",
    "end_bend_left": "s016",
    "end_bend_right": "s017",
    "end_bend_falloff": "s018",
    "irregularity": "s008",
    "density": "s009",
    "reduce": "s012",
    "thickness": "s011",
    "invert": "chk004",
}

USER_RAIL = ([(0.0, 5.0, 0.0), (4.0, 5.0, 0.0)], False)


def _set(ui, values):
    for name, value in values.items():
        widget = getattr(ui, name)
        widget.value.return_value = value
        widget.isChecked.return_value = value


def _panel(values=None, tk=None, selection=(), rail=None, order=None):
    """A Slots instance over a mock ui (the .ui defaults, then *values*) and a
    mock toolkit (or *tk*, handed over before the panel is built, as
    ``Slots.tk`` is). The fake host reads *selection* and resolves *rail* from
    it; *order* records the Preview and the preview checkbox's connections."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.CoreUtils.selected_objects.return_value = list(selection)
        sb.tk.Curtain.rail_from_selection.return_value = rail
        sb.tk.Curtain.rail_curve.return_value = "curtain_rail"
        sb.tk.Curtain.create.return_value = "curtain"
        sb.tk.Curtain.triangle_count.return_value = 1234
        sb.tk.Curtain.PRESET_DIR = "host/curtain"
        sb.tk.Curtain.BUILTIN_PRESET_DIR = "/host/curtain/presets"
    ui = sb.loaded_ui.curtain
    _set(ui, {**_DEFAULTS, **(values or {})})
    if order is not None:
        ui.chk000.toggled.connect.side_effect = lambda slot: order.append(slot.__name__)
        sb.add_reset_buttons.side_effect = lambda *a, **k: order.append("reset_buttons")
        sb.tk.Preview.side_effect = lambda *a, **k: order.append("Preview")
    return CurtainSlots(sb), sb


def _field_rail(width=6.0, curvature=0.0, closed=False, center=(0.0, 0.0, 0.0)):
    return ptk.Polyline.make(
        width=width, curvature=curvature, closed=closed, center=center
    )


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestCurtainPanelSetup(_PanelCase):
    def test_previews_through_the_host_toolkit(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.curtain
        sb.tk.Preview.assert_called_once_with(
            slots,
            ui.chk000,
            ui.b000,
            finalize_func=slots._finalize,
            message_func=sb.message_box,
            undo_message="Curtain",
            select_result_checkbox=ui.chk005,
            result_provider=mock.ANY,
        )
        provider = sb.tk.Preview.call_args.kwargs["result_provider"]
        slots.last_curtain = "curtain7"
        self.assertEqual(provider(), "curtain7")

    def test_the_rail_hooks_bracket_the_preview(self):
        """The auto-rail is built before the Preview reads the selection, and a
        cancelled preview's rail goes after the Preview's rollback (Blender's
        restores the rail it captured); the reset buttons wrap first."""
        order = []
        _panel(order=order)
        self.assertEqual(
            order,
            ["_ensure_rail", "reset_buttons", "Preview", "_drop_rail_on_cancel"],
        )

    def test_the_position_triplet_has_no_reset_buttons(self):
        slots, sb = _panel()
        sb.add_reset_buttons.assert_called_once_with(
            sb.loaded_ui.curtain, skip=("s025", "s026", "s027")
        )

    def test_every_field_redrapes(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.curtain
        sb.connect_multi.assert_any_call(
            ui, "s000-27", "valueChanged", slots._on_param_changed
        )
        sb.connect_multi.assert_any_call(
            ui, "chk001,chk004", "toggled", slots._on_param_changed
        )
        slots._on_param_changed(1.0)
        slots.preview.refresh.assert_called_once_with()
        sb.tk.Curtain.rail_curve.assert_not_called()  # the rail moves in the operation

    def test_the_position_values_are_tinted_by_axis(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.curtain
        axes = ptk.Palette.axes()
        for name, axis in (("s025", "x"), ("s026", "y"), ("s027", "z")):
            getattr(ui, name).set_text_color.assert_called_once_with(axes[axis].hex)

    def test_the_footer_starts_with_its_hint(self):
        slots, sb = _panel()
        sb.loaded_ui.curtain.footer.setDefaultStatusText.assert_called_once_with(
            "Toggle Preview to drape a curtain."
        )

    def test_the_rail_survives_the_maya_rollback(self):
        """The in-place reshape relies on Maya's Preview NOT preserving the
        selection (that would roll each reshape back)."""
        self.assertIs(CurtainSlots.PRESERVE_GEOMETRY, False)
        self.assertFalse(getattr(CurtainSlots, "MUTATES_SELECTION", False))

    def test_the_header_explains_and_aligns(self):
        slots, sb = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.set_help_text.assert_called_once()
        sb.QtCore.QTimer.singleShot.assert_called_once_with(
            0, slots._align_spinbox_prefixes
        )

    def test_presets_are_the_hosts_store_over_its_shipped_tier(self):
        slots, sb = _panel()
        combo = mock.MagicMock()
        slots.cmb000_init(combo)
        ui = sb.loaded_ui.curtain
        sb.PresetManager.assert_called_once_with(
            parent=ui,
            state=ui.state,
            preset_dir="host/curtain",
            builtin_dir="/host/curtain/presets",
        )
        slots.presets.wire_combo.assert_called_once_with(
            combo, on_loaded=slots._on_param_changed
        )

    def test_reset_to_defaults_is_the_shared_gesture(self):
        slots, sb = _panel()
        button = mock.MagicMock()
        slots.b001_init(button)
        sb.ResetGesture.assert_called_once_with(button)


class TestCurtainPanelRail(_PanelCase):
    def test_nothing_usable_selected_builds_the_auto_rail(self):
        slots, sb = _panel({"s001": 8.0, "s003": 6}, selection=["pCube1"])
        slots._ensure_rail(True)
        sb.tk.Curtain.rail_from_selection.assert_called_once_with(["pCube1"])
        self.assertIs(slots._generated, True)
        self.assertEqual(slots._driver, "curtain_rail")
        args, kwargs = sb.tk.Curtain.rail_curve.call_args
        points, closed = _field_rail(width=8.0)
        self.assertEqual(args, (ptk.Polyline.resample(points, 6), closed))
        self.assertEqual(kwargs, {"curve": None, "select": True})

    def test_a_selected_rail_is_hung_on(self):
        slots, sb = _panel(selection=["curve1"], rail=USER_RAIL)
        slots._ensure_rail(True)
        self.assertIs(slots._generated, False)
        sb.tk.Curtain.rail_curve.assert_not_called()

    def test_the_panels_own_rail_and_curtain_are_not_a_selection(self):
        """Matched by name: Maya's selection reads names, Blender's objects."""
        blender_rail = mock.Mock()
        blender_rail.name = "curtain_rail"
        slots, sb = _panel(
            selection=["curtain_rail", "curtain", blender_rail, "pCube1"]
        )
        slots._driver, slots.last_curtain = "curtain_rail", "curtain"
        slots._ensure_rail(True)
        sb.tk.Curtain.rail_from_selection.assert_called_once_with(["pCube1"])
        # The leftover rail is reused, not orphaned.
        self.assertEqual(
            sb.tk.Curtain.rail_curve.call_args.kwargs["curve"], "curtain_rail"
        )

    def test_a_selected_rail_drops_a_leftover_auto_rail(self):
        slots, sb = _panel(selection=["curve1"], rail=USER_RAIL)
        slots._driver = "curtain_rail"
        slots._ensure_rail(True)
        sb.tk.Curtain.delete_rail_curve.assert_called_once_with("curtain_rail")
        self.assertIsNone(slots._driver)

    def test_preview_off_is_left_to_the_drop_after_the_rollback(self):
        slots, sb = _panel()
        slots._driver, slots._generated = "curtain_rail", True
        slots._ensure_rail(False)
        sb.tk.Curtain.delete_rail_curve.assert_not_called()
        slots._drop_rail_on_cancel(True)
        sb.tk.Curtain.delete_rail_curve.assert_not_called()
        slots._drop_rail_on_cancel(False)
        sb.tk.Curtain.delete_rail_curve.assert_called_once_with("curtain_rail")
        self.assertIsNone(slots._driver)
        self.assertIs(slots._generated, False, "the next preview reads the selection")

    def test_commit_drops_the_auto_rail(self):
        slots, sb = _panel()
        slots._driver, slots._generated = "curtain_rail", True
        slots._finalize()
        sb.tk.Curtain.delete_rail_curve.assert_called_once_with("curtain_rail")
        self.assertIsNone(slots._driver)
        self.assertIs(slots._generated, False)


class TestCurtainPanelDrape(_PanelCase):
    def test_generated_mode_reshapes_the_rail_then_drapes_the_fields(self):
        values = {"s001": 4.0, "s002": 0.2, "s003": 7, "s026": 2.0, "chk001": True}
        slots, sb = _panel(values)
        slots._driver, slots._generated = "curtain_rail", True
        slots.perform_operation(["curtain_rail"], None)
        points, closed = _field_rail(4.0, 0.2, True, (0.0, 2.0, 0.0))
        sb.tk.Curtain.rail_curve.assert_called_once_with(
            ptk.Polyline.resample(points, 7), closed, curve="curtain_rail"
        )
        sb.tk.Curtain.rail_from_selection.assert_not_called()
        args, kwargs = sb.tk.Curtain.create.call_args
        self.assertEqual(args, (points,))
        self.assertIs(kwargs.pop("closed"), True)
        expected = {
            kw: {**_DEFAULTS, **values}[name] for kw, name in _DRAPE_FIELDS.items()
        }
        self.assertEqual(kwargs, expected)
        self.assertEqual(slots.last_curtain, "curtain")

    def test_a_selected_rail_drapes_from_its_points(self):
        slots, sb = _panel({"chk001": True}, rail=USER_RAIL)
        slots.perform_operation(["curve1"])  # Blender's Preview passes no contract
        sb.tk.Curtain.rail_from_selection.assert_called_once_with(["curve1"])
        sb.tk.Curtain.rail_curve.assert_not_called()
        args, kwargs = sb.tk.Curtain.create.call_args
        self.assertEqual(args, (USER_RAIL[0],))
        self.assertIs(kwargs["closed"], True, "Closed closes an open rail")

    def test_a_selection_that_is_no_rail_drapes_the_fields(self):
        slots, sb = _panel(rail=None)
        slots.perform_operation(["pCube1"], None)
        self.assertEqual(sb.tk.Curtain.create.call_args.args, (_field_rail()[0],))

    def test_the_footer_counts_the_curtains_triangles(self):
        slots, sb = _panel()
        slots.perform_operation([], None)
        footer = sb.loaded_ui.curtain.footer
        sb.tk.Curtain.triangle_count.assert_called_with("curtain")
        footer.setStatusText.assert_called_with("1,234 tris")
        sb.tk.Curtain.triangle_count.return_value = None
        slots._update_footer()
        footer.setStatusText.assert_called_with("")  # back to the hint

    def test_get_centers_the_rail_on_the_selection(self):
        slots, sb = _panel(selection=["curtain_rail", "pCube1"])
        slots._driver = "curtain_rail"
        sb.tk.XformUtils.get_bounding_box.return_value = (1.0, 2.0, 3.0)
        slots.b002()
        sb.tk.XformUtils.get_bounding_box.assert_called_once_with(["pCube1"], "center")
        ui = sb.loaded_ui.curtain
        for name, value in (("s025", 1.0), ("s026", 2.0), ("s027", 3.0)):
            widget = getattr(ui, name)
            widget.setValue.assert_called_once_with(value)
            self.assertEqual(
                widget.blockSignals.call_args_list, [mock.call(True), mock.call(False)]
            )
        slots.preview.refresh.assert_called_once_with()

    def test_get_with_nothing_else_selected_says_so(self):
        slots, sb = _panel(selection=["curtain_rail"])
        slots._driver = "curtain_rail"
        slots.b002()
        sb.message_box.assert_called_once_with(
            "Select object(s) to center the rail on."
        )
        sb.tk.XformUtils.get_bounding_box.assert_not_called()


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestCurtainPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def _real(self, values=None):
        return _panel(values, tk=self.mtk)

    def _curtains(self):
        return [
            t
            for t in self.cmds.ls(type="transform")
            if t.startswith("curtain") and not t.startswith("curtain_rail")
        ]

    def test_the_auto_rail_follows_the_fields_and_goes_on_cancel(self):
        cmds = self.cmds
        slots, sb = self._real()
        slots._ensure_rail(True)
        rail = slots._driver
        self.assertTrue(cmds.objExists(rail))
        self.assertEqual(cmds.ls(selection=True), [rail], "the preview reads it")

        slots.preview.enable()
        self.assertTrue(slots.preview.is_enabled)
        self.assertTrue(cmds.objExists(slots.last_curtain))

        sb.loaded_ui.curtain.s001.value.return_value = 12.0  # wider
        slots.preview.refresh()
        self.assertEqual(slots._driver, rail, "reshaped in place, one node")
        bb = cmds.exactWorldBoundingBox(rail)
        self.assertGreater(bb[3] - bb[0], 9.0)
        self.assertEqual(len(self._curtains()), 1, "the rollback rebuilt one curtain")

        slots.preview.disable()
        slots._drop_rail_on_cancel(False)  # the checkbox's toggle, after the Preview
        self.assertFalse(cmds.objExists(rail))
        self.assertEqual(self._curtains(), [])

    def test_commit_keeps_the_curtain_and_drops_the_rail(self):
        cmds = self.cmds
        slots, sb = self._real()
        slots._ensure_rail(True)
        rail = slots._driver
        slots.preview.enable()
        slots.preview.finalize_changes()
        self.assertFalse(cmds.objExists(rail))
        self.assertTrue(cmds.objExists(slots.last_curtain))
        sb.loaded_ui.curtain.footer.setStatusText.assert_called_with(
            f"{cmds.polyEvaluate(slots.last_curtain, triangle=True):,} tris"
        )

    def test_a_selected_curve_is_the_rail(self):
        cmds = self.cmds
        crv = cmds.curve(point=[(0, 5, 0), (2, 5, 1), (4, 5, 0), (6, 5, 1)], degree=3)
        cmds.select(crv)
        slots, sb = self._real()
        slots._ensure_rail(True)
        self.assertIs(slots._generated, False)
        self.assertIsNone(slots._driver)
        slots.perform_operation([crv], None)
        self.assertLess(cmds.exactWorldBoundingBox(slots.last_curtain)[1], 5.0)

    def test_get_centers_on_the_selection(self):
        cmds = self.cmds
        cube = cmds.polyCube()[0]
        cmds.move(1, 2, 3, cube)
        cmds.select(cube)
        slots, sb = self._real()
        slots.b002()
        ui = sb.loaded_ui.curtain
        for name, value in (("s025", 1.0), ("s026", 2.0), ("s027", 3.0)):
            self.assertAlmostEqual(getattr(ui, name).setValue.call_args.args[0], value)


if __name__ == "__main__":
    unittest.main()
