#!/usr/bin/python
# coding=utf-8
"""The Game Shader panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set)
and composes the host's ``GameShader`` engine, so a fake toolkit stands in for
``mtk`` / ``btk`` here and records what the panel asks of it: plain pytest, no
DCC, no widgets loaded. In Maya, the same class drives the real ``mtk``; the
engine API it calls (``shader_type_choices``, ``assign_network``) is tested in
mayatk's and blendertk's ``test_game_shader.py``.
"""

import os
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.game_shader import GameShaderSlots

#: mayatk's shader types; Blender's engine has none.
MAYA_SHADER_TYPES = [
    ("Stingray PBS", "stingray"),
    ("Standard Surface", "standard_surface"),
    ("Open PBR", "open_pbr"),
]


def _panel(
    name="brick",
    affix=("MAT_", ""),
    template="Unity URP Lit",
    ext="PNG",
    normal="DirectX",
    shader_type="standard_surface",
    opacity="Opacity: Masked",
    assign=False,
    files=("C:/art/brick_BaseColor.png", "C:/art/brick_Normal.png"),
    shader_types=MAYA_SHADER_TYPES,
    tk=None,
):
    """A Slots instance over a mock ui and a mock toolkit (or *tk*, handed over
    before the panel is built, as ``Slots.tk`` is); returns it and the
    switchboard."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.GameShader.return_value.shader_type_choices.return_value = list(
            shader_types
        )
        sb.tk.DataNodes.scene_source_images_dir.return_value = "C:/proj/sourceimages"
        sb.tk.CoreUtils.selected_objects.return_value = ["cube"]
    ui = sb.loaded_ui.game_shader
    ui.txt000.text.return_value = name
    ui.txt002.option_box.resolve_affix.return_value = affix
    ui.cmb001.currentText.return_value = normal
    ui.cmb002.currentText.return_value = template
    ui.cmb003.currentText.return_value = ext
    ui.cmb004.currentData.return_value = shader_type
    ui.cmb005.currentText.return_value = opacity
    ui.header.menu.chk_assign_to_selection.isChecked.return_value = assign
    sb.file_dialog.return_value = list(files)
    return GameShaderSlots(sb), sb


def _menu_entry(header, object_name):
    """The keyword arguments ``header.menu.add`` was given for *object_name*."""
    for call in header.menu.add.call_args_list:
        if call.kwargs.get("setObjectName") == object_name:
            return call.kwargs
    raise AssertionError(f"no {object_name} in the header menu")


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestGameShaderComposition(_PanelCase):
    def test_the_engine_is_composed_and_logs_through_the_panel(self):
        """Composed, not inherited: the panel holds the host's engine and lends
        it its own logger, so the engine's report streams into this panel's
        log and no other GameShader caller's does."""
        slots, sb = _panel()
        sb.tk.GameShader.assert_called_once_with()
        self.assertIs(slots.engine, sb.tk.GameShader.return_value)
        slots.engine.use_logger.assert_called_once_with(slots.logger)
        self.assertFalse(hasattr(GameShaderSlots, "create_network"))

    def test_the_log_streams_into_the_text_browser(self):
        with mock.patch.object(
            GameShaderSlots.logger, "setup_logging_redirect"
        ) as redirect:
            slots, sb = _panel()
        redirect.assert_called_once_with(sb.loaded_ui.game_shader.txt001)

    def test_log_links_dispatch_through_the_host(self):
        slots, sb = _panel()
        slots._on_log_link_clicked("action://select?node=brick")
        sb.tk.UiUtils.dispatch_log_link.assert_called_once_with(
            "action://select?node=brick", slots.logger
        )


class TestGameShaderCreateNetwork(_PanelCase):
    def test_create_network_gets_the_panels_values(self):
        slots, sb = _panel()
        slots.b000()
        engine = sb.tk.GameShader.return_value
        engine.create_network.assert_called_once_with(
            ["C:/art/brick_BaseColor.png", "C:/art/brick_Normal.png"],
            "brick",
            prefix="MAT_",
            suffix="",
            progress_callback=mock.ANY,
            config="Unity URP Lit",
            normal_type="DirectX",
            opacity_mode="masked",
            cleanup_base_color=False,
            output_extension="png",
            output_profile=None,
            shader_type="standard_surface",
        )
        sb.loaded_ui.game_shader.txt001.clear.assert_called_once_with()

    def test_profile_default_leaves_the_format_to_the_template(self):
        slots, sb = _panel(ext="Profile default")
        slots.b000()
        kwargs = sb.tk.GameShader.return_value.create_network.call_args.kwargs
        self.assertIsNone(kwargs["output_extension"])
        self.assertEqual(kwargs["output_profile"], "Unity URP Lit")

    def test_a_host_with_one_surface_shader_takes_no_shader_type(self):
        """Blender: the engine offers no shader types, so none is passed, even
        from a combo whose data a stale setting left behind."""
        slots, sb = _panel(shader_types=[])
        slots.b000()
        kwargs = sb.tk.GameShader.return_value.create_network.call_args.kwargs
        self.assertNotIn("shader_type", kwargs)
        self.assertIsNone(slots.shader_type)

    def test_the_opacity_combo_names_the_mode(self):
        for text, mode in (
            ("Opacity: Auto", None),
            ("Opacity: Transparent", "transparent"),
            ("Opacity: Masked", "masked"),
            ("Opacity: None", "none"),
        ):
            with self.subTest(text=text):
                slots, _ = _panel(opacity=text)
                self.assertEqual(slots.opacity_mode, mode)

    def test_browse_starts_in_the_scene_texture_folder(self):
        slots, sb = _panel()
        slots.b000()
        kwargs = sb.file_dialog.call_args.kwargs
        self.assertEqual(kwargs["start_dir"], "C:/proj/sourceimages")
        self.assertIn("*.png", kwargs["file_types"])

    def test_a_cancelled_dialog_builds_nothing(self):
        slots, sb = _panel(files=())
        slots.b000()
        sb.tk.GameShader.return_value.create_network.assert_not_called()
        sb.loaded_ui.game_shader.txt001.clear.assert_not_called()

    def test_a_batch_keeps_only_the_networks_built(self):
        """One network per texture set; a failed set is None."""
        slots, sb = _panel()
        sb.tk.GameShader.return_value.create_network.return_value = ["a", None, "b"]
        slots.b000()
        self.assertEqual(slots.last_created, ["a", "b"])
        sb.message_box.assert_not_called()

    def test_nothing_built_is_said(self):
        for result in (None, [None]):
            with self.subTest(result=result):
                slots, sb = _panel()
                sb.tk.GameShader.return_value.create_network.return_value = result
                slots.b000()
                self.assertEqual(slots.last_created, [])
                self.assertIn("No PBR textures", sb.message_box.call_args.args[0])

    def test_progress_reaches_the_footer(self):
        slots, sb = _panel()
        slots.b000()
        report = sb.tk.GameShader.return_value.create_network.call_args.kwargs[
            "progress_callback"
        ]
        report(50, "Preparing Maps")
        sb.loaded_ui.game_shader.footer.setText.assert_called_with(
            "Preparing Maps (50%)"
        )


class TestGameShaderAssignToSelection(_PanelCase):
    def test_the_selection_is_read_before_the_dialog_and_assigned_after(self):
        slots, sb = _panel(assign=True)
        order = mock.MagicMock()
        order.attach_mock(sb.tk.CoreUtils.selected_objects, "selection")
        order.attach_mock(sb.file_dialog, "dialog")
        engine = sb.tk.GameShader.return_value
        engine.create_network.return_value = "brickSG"
        slots.b000()
        self.assertEqual([c[0] for c in order.mock_calls[:2]], ["selection", "dialog"])
        engine.assign_network.assert_called_once_with(["brickSG"], ["cube"])

    def test_assign_off_never_reads_the_selection(self):
        slots, sb = _panel(assign=False)
        slots.b000()
        sb.tk.CoreUtils.selected_objects.assert_not_called()
        sb.tk.GameShader.return_value.assign_network.assert_not_called()


class TestGameShaderOpenInEditor(_PanelCase):
    def test_graphs_the_last_build(self):
        slots, sb = _panel()
        slots.last_created = ["brickSG"]
        slots.lbl_graph_material()
        sb.tk.MatUtils.graph_materials.assert_called_once_with(["brickSG"])

    def test_else_the_material_the_name_field_names(self):
        slots, sb = _panel(name="brick")
        sb.tk.MatUtils.get_scene_mats.return_value = ["brick"]
        slots.lbl_graph_material()
        sb.tk.MatUtils.get_scene_mats.assert_called_once_with(inc="brick")
        sb.tk.MatUtils.graph_materials.assert_called_once_with(["brick"])

    def test_nothing_to_graph_is_said(self):
        for name, said in (("brick", "not found"), ("", "No material")):
            with self.subTest(name=name):
                slots, sb = _panel(name=name)
                sb.tk.MatUtils.get_scene_mats.return_value = []
                with self.assertLogs(slots.logger, level="WARNING") as logs:
                    slots.lbl_graph_material()
                self.assertIn(said, logs.output[0])
                sb.tk.MatUtils.graph_materials.assert_not_called()


class TestGameShaderWidgets(_PanelCase):
    def test_the_shader_type_combo_lists_the_hosts_shader_types(self):
        slots, _ = _panel()
        widget = mock.MagicMock(is_initialized=False)
        slots.cmb004_init(widget)
        widget.clear.assert_called_once_with()
        self.assertEqual(
            [c.args for c in widget.addItem.call_args_list], MAYA_SHADER_TYPES
        )
        widget.setVisible.assert_not_called()

    def test_the_shader_type_combo_hides_on_a_host_with_one_surface_shader(self):
        slots, _ = _panel(shader_types=[])
        widget = mock.MagicMock(is_initialized=False)
        slots.cmb004_init(widget)
        widget.setVisible.assert_called_once_with(False)
        widget.addItem.assert_not_called()

    def test_the_presets_come_from_the_output_templates(self):
        slots, _ = _panel()
        widget = mock.MagicMock(is_initialized=False)
        widget.count.side_effect = lambda: len(widget.addItem.call_args_list)
        slots.cmb002_init(widget)
        self.assertEqual(
            [c.args[0] for c in widget.addItem.call_args_list],
            [name for name, _ in ptk.OutputTemplates.profile_choices()],
        )

    def test_the_format_combo_keeps_profile_default_last(self):
        """The combo saves its index: the sentinel goes last."""
        slots, _ = _panel()
        widget = mock.MagicMock(is_initialized=False)
        slots.cmb003_init(widget)
        items = widget.add.call_args.args[0]
        self.assertEqual(items[-1][0], ptk.OutputTemplates.PROFILE_DEFAULT_LABEL)

    def test_the_header_menu_offers_open_in_editor_and_assign(self):
        slots, _ = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        self.assertEqual(
            _menu_entry(header, "lbl_graph_material")["setText"], "Open in Editor"
        )
        assign = _menu_entry(header, "chk_assign_to_selection")
        self.assertEqual(assign["setText"], "Assign to Selection")
        self.assertIs(assign["setChecked"], False)
        header.set_help_text.assert_called_once()

    def test_the_affix_field_follows_its_mode(self):
        slots, _ = _panel()
        widget = mock.MagicMock()
        for mode, placeholder in (
            ("prefix", "Prefix"),
            ("suffix", "Suffix"),
            ("convention", "Scene Convention"),
            ("auto", "Affix"),
        ):
            with self.subTest(mode=mode):
                widget.option_box.affix_mode = mode
                slots.txt002_init(widget)
                widget.setPlaceholderText.assert_called_with(placeholder)
        self.assertEqual(
            widget.option_box.set_affix.call_args.kwargs["settings_key"],
            "game_shader_affix",
        )


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestGameShaderPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")
        artifacts = ptk.TempArtifacts("game_shader_panel", policy="scoped")
        self.addCleanup(artifacts.cleanup)
        self.scratch = artifacts.dir_path()

    def _image(self, stem):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed in this Maya")
        path = os.path.join(self.scratch, f"{stem}.png")
        Image.new("RGBA", (16, 16), (128, 128, 128, 255)).save(path)
        return path

    def test_the_real_engine_is_composed_with_the_panels_logger(self):
        slots, _ = _panel(tk=self.mtk)
        self.assertIsInstance(slots.engine, self.mtk.GameShader)
        self.assertIs(slots.engine.logger, slots.logger)

    def test_the_shader_type_combo_lists_mayas_shader_types(self):
        slots, _ = _panel(tk=self.mtk)
        widget = mock.MagicMock(is_initialized=False)
        slots.cmb004_init(widget)
        self.assertEqual(
            [c.args for c in widget.addItem.call_args_list], MAYA_SHADER_TYPES
        )

    def test_browse_starts_in_the_scene_projects_texture_folder(self):
        """Regression: it joined ``get_env_info("workspace_dir")`` -- the
        project folder's NAME, as the HUD shows it -- with ``sourceimages``: a
        path relative to Maya's working directory. Added: 2026-10-13 (moved
        from mayatk's test_game_shader with the panel)."""
        slots, sb = _panel(files=(), tk=self.mtk)
        slots.b000()
        folder = sb.file_dialog.call_args.kwargs["start_dir"]
        self.assertTrue(os.path.isabs(folder), folder)
        self.assertEqual(
            os.path.normcase(folder),
            os.path.normcase(self.mtk.DataNodes.scene_source_images_dir()),
        )

    def test_builds_the_network_and_assigns_it_to_the_selection(self):
        cmds = self.cmds
        cube = cmds.polyCube(name="gs_panel_cube")[0]
        cmds.select(cube, replace=True)
        slots, sb = _panel(
            name="gs_panel_rock",
            affix=("", ""),
            template="PBR Metallic/Roughness",
            ext="Profile default",
            normal="OpenGL",
            shader_type="standard_surface",  # no plug-in needed
            opacity="Opacity: Auto",
            assign=True,
            files=(self._image("rock_BaseColor"),),
            tk=self.mtk,
        )
        slots.b000()
        self.assertTrue(slots.last_created, "no network built")
        shapes = cmds.listRelatives(cube, shapes=True) or []
        groups = cmds.listConnections(shapes, type="shadingEngine") or []
        worn = cmds.ls(cmds.listConnections(groups, source=True) or [], materials=True)
        self.assertIn("gs_panel_rock", worn)
        self.assertFalse(cmds.ls("*SGSG"), "a shading group built for the group")
        sb.message_box.assert_not_called()


if __name__ == "__main__":
    unittest.main()
