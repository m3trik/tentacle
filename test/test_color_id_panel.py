#!/usr/bin/python
# coding=utf-8
"""The Color ID panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain pytest, no DCC, no widgets loaded. In Maya, the same
class drives the real ``mtk``. How each host stores a channel, and the engine
calls themselves (``select_by_color``, ``get_color``, ``lead_object``,
``scene_objects``), are the libraries': mayatk's ``test_display_utils.py``,
blendertk's ``test_color_id.py``.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.color_id import ColorIdSlots

RED = (0.8, 0.1, 0.1)
#: Exact in binary (and float32): the 0-255 swatch values below are stable.
BLUE = (0.25, 0.5, 0.75)

#: Channel -> its checkbox (the same objectName in both hosts' old panels).
CHANNEL_BOXES = {
    "wireframe": "chk012",
    "outliner": "chk013",
    "material": "chk014",
    "vertex": "chk015",
    "set": "chk016",
}


def _swatch(name="chk000", color=RED, checked=True):
    """A palette swatch whose color is a QColor-like (``redF``...) value."""
    button = mock.MagicMock()
    button.objectName.return_value = name
    button.isChecked.return_value = checked
    button.color.redF.return_value = color[0]
    button.color.greenF.return_value = color[1]
    button.color.blueF.return_value = color[2]
    return button


def _set_channels(ui, **on):
    for channel, box in CHANNEL_BOXES.items():
        getattr(ui, box).isChecked.return_value = bool(on.get(channel))


def _panel(swatches=None, tk=None, **channels):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is); *channels* are the checked
    channel boxes."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.ColorId.DEFAULT_SWATCH_COLORS = [(180, 120, 120), (120, 180, 120)]
        sb.tk.ColorId.SWATCH_PRESET_DIR = "host/color_id"
        sb.tk.CoreUtils.selected_objects.return_value = ["pCube1"]
    swatches = [_swatch()] if swatches is None else swatches
    sb.create_button_groups.return_value.buttons.return_value = swatches
    ui = sb.loaded_ui.color_id
    ui.settings.value.return_value = ""
    _set_channels(ui, **channels)
    return ColorIdSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestColorIdPanelSetup(_PanelCase):
    def test_the_swatches_take_the_host_palette(self):
        swatches = [_swatch("chk000"), _swatch("chk001", checked=False)]
        slots, sb = _panel(swatches)
        sb.create_button_groups.assert_called_once_with(
            sb.loaded_ui.color_id, "chk000-11"
        )
        self.assertEqual(
            sb.QtGui.QColor.call_args_list,
            [mock.call(180, 120, 120), mock.call(120, 180, 120)],
        )
        for button in swatches:
            self.assertIs(button.keep_square, True)
            self.assertIs(button.settings, sb.loaded_ui.color_id.settings)
        sb.loaded_ui.color_id.chk000.setChecked.assert_called_once_with(True)

    def test_the_header_keeps_palettes_in_the_hosts_store(self):
        slots, sb = _panel()
        header = mock.MagicMock()
        header.menu.presets.exists.return_value = True
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("menu", "collapse", "pin")
        header.set_help_text.assert_called_once()
        presets = header.menu.presets
        self.assertEqual(presets.preset_dir, "host/color_id")
        self.assertEqual(presets.metadata_provider, slots._export_swatch_colors)
        self.assertEqual(presets.on_metadata_loaded, slots._import_swatch_colors)
        presets.save.assert_not_called()

    def test_the_factory_preset_is_written_once(self):
        slots, sb = _panel()
        header = mock.MagicMock()
        presets = header.menu.presets
        presets.exists.return_value = False
        saved = {}
        presets.save.side_effect = lambda name: saved.update(
            {name: presets.metadata_provider()}
        )
        slots.header_init(header)
        self.assertEqual(saved, {"default": {"swatches": ["#B47878", "#78B478"]}})
        # The swatch provider is back in place once the factory preset is out.
        self.assertEqual(presets.metadata_provider, slots._export_swatch_colors)

    def test_presets_round_trip_the_swatch_colors(self):
        swatches = [_swatch("chk000"), _swatch("chk001", checked=False)]
        slots, sb = _panel(swatches)
        swatches[0].color.name.return_value = "#b47878"
        swatches[1].color.name.return_value = "#78b478"
        self.assertEqual(
            slots._export_swatch_colors(), {"swatches": ["#b47878", "#78b478"]}
        )
        slots._import_swatch_colors({"swatches": ["#102030"]})
        sb.QtGui.QColor.assert_called_with("#102030")
        self.assertIs(swatches[0].color, sb.QtGui.QColor.return_value)


class TestColorIdPanelActions(_PanelCase):
    def test_set_color_applies_on_the_checked_channels(self):
        slots, sb = _panel(wireframe=True, material=True)
        slots.b001()
        sb.tk.ColorId.apply_color.assert_called_once_with(
            ["pCube1"],
            color=RED,
            apply_to_wireframe=True,
            apply_to_vertex=False,
            apply_to_outliner=False,
            apply_to_material=True,
            set_per_color=False,
        )

    def test_reset_clears_only_the_checked_channels(self):
        """Regression: Reset passed no flags, so every channel's default (True)
        fired — clearing a wireframe tint also cost the materials, vertex colors,
        outliner color and ID set."""
        slots, sb = _panel(wireframe=True, set=True)
        slots.b000()
        sb.tk.ColorId.reset_colors.assert_called_once_with(
            ["pCube1"],
            reset_wireframe=True,
            reset_outliner=False,
            reset_material=False,
            reset_vertex=False,
            reset_sets=True,
        )
        sb.tk.ColorId.scene_objects.assert_not_called()

    def test_ctrl_click_reset_covers_the_whole_scene(self):
        slots, sb = _panel(outliner=True)
        sb.app.keyboardModifiers.return_value = sb.QtCore.Qt.ControlModifier
        sb.tk.ColorId.scene_objects.return_value = ["|a", "|b"]
        sb.tk.CoreUtils.selected_objects.return_value = []
        slots.b000()
        self.assertEqual(sb.tk.ColorId.reset_colors.call_args.args, (["|a", "|b"],))
        sb.message_box.assert_not_called()  # no selection needed

    def test_select_by_color_reads_the_checked_channels(self):
        slots, sb = _panel(outliner=True, vertex=True)
        slots.b002()
        sb.tk.ColorId.select_by_color.assert_called_once_with(
            RED,
            check_wireframe_color=False,
            check_outliner_color=True,
            check_material_color=False,
            check_vertex_color=True,
            check_set=False,
        )

    def test_get_color_reads_the_lead_object_into_the_swatch(self):
        swatch = _swatch()
        slots, sb = _panel([swatch], set=True)
        sb.tk.ColorId.lead_object.return_value = "pCube1"
        sb.tk.ColorId.get_color.return_value = BLUE
        slots.b003()
        sb.tk.ColorId.get_color.assert_called_once_with(
            "pCube1",
            check_wireframe_color=False,
            check_outliner_color=False,
            check_material_color=False,
            check_vertex_color=False,
            check_set=True,
        )
        sb.QtGui.QColor.assert_called_with(64, 128, 191)
        self.assertIs(swatch.color, sb.QtGui.QColor.return_value)

    def test_get_color_says_when_nothing_answers(self):
        slots, sb = _panel(wireframe=True)
        sb.tk.ColorId.lead_object.return_value = None
        slots.b003()
        sb.tk.ColorId.get_color.assert_not_called()
        self.assertIn("Select an object", sb.message_box.call_args.args[0])

        slots, sb = _panel(wireframe=True)
        sb.tk.ColorId.lead_object.return_value = "pCube1"
        sb.tk.ColorId.get_color.return_value = None
        slots.b003()
        self.assertIn("No color found", sb.message_box.call_args.args[0])

    def test_no_channel_checked_does_nothing_and_says_so(self):
        """Every action is channel-scoped; with none checked Select By Color used
        to answer "no matches" by clearing the user's selection."""
        for button in ("b000", "b001", "b002", "b003"):
            with self.subTest(button=button):
                slots, sb = _panel()
                getattr(slots, button)()
                sb.message_box.assert_called_once_with("No channels enabled.")
                for engine in (
                    "apply_color",
                    "reset_colors",
                    "select_by_color",
                    "get_color",
                ):
                    getattr(sb.tk.ColorId, engine).assert_not_called()

    def test_nothing_selected_is_said(self):
        for button, engine in (("b000", "reset_colors"), ("b001", "apply_color")):
            with self.subTest(button=button):
                slots, sb = _panel(wireframe=True)
                sb.tk.CoreUtils.selected_objects.return_value = []
                getattr(slots, button)()
                sb.message_box.assert_called_once_with("No objects selected.")
                getattr(sb.tk.ColorId, engine).assert_not_called()

    def test_no_swatch_checked_applies_and_selects_nothing(self):
        slots, sb = _panel([_swatch(checked=False)], wireframe=True)
        self.assertIsNone(slots.target_color)
        slots.b001()
        slots.b002()
        sb.tk.ColorId.apply_color.assert_not_called()
        sb.tk.ColorId.select_by_color.assert_not_called()

    def test_a_swatch_color_may_be_a_plain_tuple(self):
        swatch = _swatch()
        slots, sb = _panel([swatch])
        swatch.color = (0.25, 0.5, 0.75)
        self.assertEqual(slots.target_color, (0.25, 0.5, 0.75))

    def test_a_read_color_is_clamped_into_the_swatch_range(self):
        self.assertEqual(ColorIdSlots._rgb255((1.2, -0.1, 0.5)), (255, 0, 128))


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestColorIdPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def _real(self, color=RED, **channels):
        swatch = _swatch(color=color)
        slots, sb = _panel([swatch], tk=self.mtk, **channels)
        return slots, sb, swatch

    def test_set_color_then_select_by_color_finds_it(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="cidPanelCube")[0]
        other = cmds.polyCube(name="cidPanelOther")[0]
        cmds.select(cube)
        slots, sb, _ = self._real(wireframe=True)
        slots.b001()
        self.assertTrue(cmds.getAttr(f"{cube}.overrideEnabled"))
        self.assertFalse(cmds.getAttr(f"{other}.overrideEnabled"))

        cmds.select(other)
        slots.b002()
        self.assertEqual(cmds.ls(selection=True, long=True), cmds.ls(cube, long=True))

    def test_reset_leaves_the_unchecked_channels(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="cidPanelScope")[0]
        self.mtk.ColorId.apply_color(
            [cube], RED, apply_to_wireframe=True, apply_to_outliner=True
        )
        cmds.select(cube)
        slots, sb, _ = self._real(wireframe=True)
        slots.b000()
        self.assertFalse(cmds.getAttr(f"{cube}.overrideEnabled"))
        self.assertTrue(cmds.getAttr(f"{cube}.useOutlinerColor"))

    def test_ctrl_click_reset_needs_no_selection(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="cidPanelAll")[0]
        self.mtk.ColorId.apply_color([cube], RED, apply_to_wireframe=True)
        cmds.select(clear=True)
        slots, sb, _ = self._real(wireframe=True)
        sb.app.keyboardModifiers.return_value = sb.QtCore.Qt.ControlModifier
        slots.b000()
        self.assertFalse(cmds.getAttr(f"{cube}.overrideEnabled"))

    def test_select_by_color_with_no_channels_keeps_the_selection(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="cidPanelKeep")[0]
        cmds.select(cube)
        slots, sb, _ = self._real()
        slots.b002()
        self.assertEqual(cmds.ls(selection=True, long=True), cmds.ls(cube, long=True))
        sb.message_box.assert_called_once_with("No channels enabled.")

    def test_get_color_reads_the_last_selected(self):
        cmds = self.cmds
        first = cmds.polyCube(name="cidPanelFirst")[0]
        last = cmds.polyCube(name="cidPanelLast")[0]
        self.mtk.ColorId.apply_color([first], RED, apply_to_wireframe=True)
        self.mtk.ColorId.apply_color([last], BLUE, apply_to_wireframe=True)
        cmds.select([first, last])
        slots, sb, swatch = self._real(wireframe=True)
        slots.b003()
        sb.QtGui.QColor.assert_called_with(64, 128, 191)
        self.assertIs(swatch.color, sb.QtGui.QColor.return_value)


if __name__ == "__main__":
    unittest.main()
