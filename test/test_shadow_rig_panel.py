#!/usr/bin/python
# coding=utf-8
"""The Shadow Rig panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` / ``btk`` and records what the panel asks of it: plain pytest, no DCC,
no widgets loaded. Pinned here: the preview's hooks (a pass builds, the commit
packs and previews, a discard repairs what no rollback reaches), the combos
read into the engine's builder, the sources, the Utility section acting on
what the selection touches, the retuning boxes, and the scene-free load.

In a fresh GUI Maya (``run_tests.py --in-maya``) the panel itself loads the
way the marking menu opens it and drives the real ``mtk``: the ``.ui``'s
surface, the preview lifecycle around the SOURCE (built inside the preview it
was deleted and recreated at the default position on every refresh), Source
From Selection, a failed preview leaving the box unchecked, Planes / Atlas,
Follow Source and Softness, the retuning boxes, and the Utility section. The
engine half (the selection's casters, a source by name, the selection as
sources, the PNGs a discard leaves) is mayatk's ``test_shadow_rig.py`` and
blendertk's harness.
"""

import contextlib
import os
import types
import unittest
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module, qt_widgets_available
from tentacle.slots._slots import Slots
from tentacle.slots.tools.shadow_rig import ShadowRigSlots


def _rig(plane, kind="projected", texture=None, horizon=None):
    return types.SimpleNamespace(
        shadow_plane=plane,
        rig_type=kind,
        texture_path=texture or f"/tex/{plane}.png",
        horizon_path=horizon,
    )


def _panel(texts=None, values=None, checked=None, previewing=False):
    """A Slots instance over a mock ui and a mock toolkit. *texts* are combo /
    field texts, *values* spin box values, *checked* box states."""
    sb = mock.MagicMock()
    tk = sb.tk
    tk.ShadowRig.DEFAULT_SOURCE_NAME = "shadow_source"
    tk.CoreUtils.leaf_name.side_effect = lambda node: str(node).split("|")[-1]
    tk.CoreUtils.selected_objects.return_value = []
    tk.ShadowRig.find_shadow_planes.return_value = []
    tk.ShadowRig.find_source.return_value = None
    tk.ShadowPreview.language.return_value = ("hlsl", "")
    tk.ShadowPreview.toggle.return_value = ([], [])  # (done, failed), as the host's
    tk.Preview.return_value.is_enabled = previewing
    ui = sb.loaded_ui.shadow_rig
    texts = {
        "cmb_type": "Rig:  Projected",
        "cmb_planes": "Planes:  Combined",
        "cmb_atlas": "Atlas:  Auto",
        "s000": "Resolution: 512",
        "txt_source": "",
        **(texts or {}),
    }
    for name, text in texts.items():
        widget = getattr(ui, name)
        widget.currentText.return_value = text
        widget.text.return_value = text
    for name, value in {"s002": 1.0, "s003": 0.0, **(values or {})}.items():
        getattr(ui, name).value.return_value = value
    for name, state in {"chk_combine": True, **(checked or {})}.items():
        getattr(ui, name).isChecked.return_value = state
    return ShadowRigSlots(sb), sb


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    @staticmethod
    def chunks(sb):
        """The undo chunks the panel opened (each with the refresh held)."""
        return [c.args[0] for c in sb.tk.CoreUtils.undo_chunk.call_args_list]


class TestShadowRigPreview(_PanelCase):
    def test_previews_through_the_host_toolkit_with_both_hooks(self):
        slots, sb = _panel()
        ui = sb.loaded_ui.shadow_rig
        sb.tk.Preview.assert_called_once_with(
            slots,
            ui.chk_preview,
            ui.b000,
            finalize_func=slots._after_commit,
            restore_func=slots._after_discard,
            message_func=sb.message_box,
            undo_message="Shadow Rig",
        )
        for combo in (ui.cmb_type, ui.cmb_planes, ui.cmb_atlas, ui.s000):
            combo.currentIndexChanged.connect.assert_called_with(slots.preview.refresh)
        ui.chk_combine.toggled.connect.assert_called_with(slots.preview.refresh)
        ui.txt_source.editingFinished.connect.assert_called_with(slots._on_sources_edited)

    def test_the_rig_leaves_the_selection_alone(self):
        """No duplicate-and-hide of the selection before each Maya pass: the
        rig never edits or deletes its targets, and a big hierarchy would pay
        for every refresh."""
        self.assertFalse(ShadowRigSlots.MUTATES_SELECTION)
        self.assertFalse(ShadowRigSlots.PRESERVE_GEOMETRY)

    def test_a_pass_builds_one_rig_per_source_through_the_combos_builder(self):
        slots, sb = _panel(
            texts={
                "cmb_type": "Rig:  Horizon",
                "txt_source": "keyLight, fill",
                "s000": "Resolution: 256",
            },
            values={"s003": 1.5},
        )
        engine = sb.tk.ShadowRig
        engine.shadow_targets.return_value = ["|Box"]
        engine.create_horizon_for_sources.return_value = [_rig("Box_shadow", "horizon")]
        # Maya's Preview passes a contract, Blender's none: both are accepted.
        slots.perform_operation(["Box.f[0]"], mock.MagicMock())
        slots.perform_operation(["Box.f[0]"])
        engine.shadow_targets.assert_called_with(
            ["Box.f[0]"], ["keyLight", "fill"], recursive=True
        )
        engine.create_horizon_for_sources.assert_called_with(
            ["|Box"], ["keyLight", "fill"], texture_res=256, recursive=True, ground_height=1.5
        )
        engine.create_for_sources.assert_not_called()
        engine.set_intensity.assert_not_called()  # 1.0 is the build's own
        self.assertEqual(slots._built_sources, ["keyLight", "fill"])

    def test_per_object_builds_a_rig_per_target(self):
        slots, sb = _panel(texts={"cmb_planes": "Planes:  Per object"})
        engine = sb.tk.ShadowRig
        engine.shadow_targets.return_value = ["|a", "|b"]
        engine.create_for_sources.side_effect = lambda group, *a, **k: [
            _rig(f"{group[0]}_shadow")
        ]
        slots.perform_operation(["a", "b"])
        groups = [c.args[0] for c in engine.create_for_sources.call_args_list]
        self.assertEqual(groups, [["|a"], ["|b"]])

    def test_a_darker_intensity_is_applied_to_the_pass(self):
        slots, sb = _panel(values={"s002": 0.4})
        engine = sb.tk.ShadowRig
        engine.create_for_sources.return_value = [_rig("p1"), _rig("p2")]
        slots.perform_operation(["Box"])
        engine.set_intensity.assert_called_once_with(["p1", "p2"], 0.4)

    def test_a_pass_tracks_each_rigs_own_pngs_once(self):
        slots, sb = _panel()
        sb.tk.ShadowRig.create_for_sources.return_value = [
            _rig("p1", "horizon", texture="/t/p1.png", horizon="/t/p1_horizon.png")
        ]
        slots.perform_operation(["Box"])
        slots.perform_operation(["Box"])  # a refresh writes the same files
        self.assertEqual(slots._preview_textures, ["/t/p1.png", "/t/p1_horizon.png"])
        self.assertEqual(len(slots._built_rigs), 1)

    def test_a_planned_rig_type_fails_the_pass_before_anything_is_built(self):
        slots, sb = _panel(texts={"cmb_type": "Rig:  Morphing (planned)"})
        with self.assertRaisesRegex(ValueError, "not available yet"):
            slots.perform_operation(["Box"])
        sb.tk.ShadowRig.create_for_sources.assert_not_called()

    def test_the_rig_combo_names_the_engines_builder(self):
        slots, sb = _panel(texts={"cmb_type": "Rig:  Projected"})
        self.assertIs(slots._rig_builder(), sb.tk.ShadowRig.create_for_sources)

    def test_the_source_exists_before_the_preview_builds(self):
        """Created inside a pass, the source was rolled back and recreated at
        the default position on every refresh."""
        slots, sb = _panel(texts={"txt_source": "keyLight"})
        slots.prepare_operation(["Box"])
        sb.tk.ShadowRig.ensure_source.assert_called_once_with("keyLight")


class TestShadowRigCommitAndDiscard(_PanelCase):
    def _built(self, atlas="Auto", planes=("p1",), kind="projected"):
        slots, sb = _panel(texts={"cmb_atlas": f"Atlas:  {atlas}"})
        engine = sb.tk.ShadowRig
        engine.create_for_sources.return_value = [_rig("p1", kind)]
        slots.perform_operation(["Box"])
        engine.find_shadow_planes.return_value = list(planes)
        return slots, sb

    def test_auto_leaves_a_lone_plane_alone(self):
        slots, sb = self._built(atlas="Auto", planes=("p1",))
        slots._after_commit()
        sb.tk.ShadowRig.pack_atlas.assert_not_called()

    def test_auto_packs_the_whole_scene_once_it_holds_two_rigs(self):
        """There is one atlas per rig type: a second rig joins the first."""
        slots, sb = self._built(atlas="Auto", planes=("p0", "p1"))
        slots._after_commit()
        sb.tk.ShadowRig.pack_atlas.assert_called_once_with(["p0", "p1"])

    def test_off_never_packs_and_on_always_does(self):
        slots, sb = self._built(atlas="Off", planes=("p0", "p1"))
        slots._after_commit()
        sb.tk.ShadowRig.pack_atlas.assert_not_called()
        slots, sb = self._built(atlas="On", planes=("p1",))
        slots._after_commit()
        sb.tk.ShadowRig.pack_atlas.assert_called_once_with(["p1"])

    def test_the_commit_removes_superseded_pngs_and_forgets_the_pass(self):
        slots, sb = self._built()
        slots._after_commit()
        sb.tk.ShadowRig.delete_orphaned_textures.assert_called_once_with(["/tex/p1.png"])
        self.assertEqual((slots._built_rigs, slots._preview_textures), ([], []))
        sb.tk.ShadowRig.refresh_export_metadata.assert_not_called()

    def test_a_committed_horizon_rig_shows_its_live_preview(self):
        slots, sb = self._built(kind="horizon")
        sb.tk.ShadowRig.plane_type.return_value = "horizon"
        slots._after_commit()
        sb.tk.ShadowPreview.toggle.assert_called_once_with(["p1"], on=True)

    def test_a_session_that_cannot_draw_it_only_says_why(self):
        slots, sb = self._built(kind="horizon")
        sb.tk.ShadowPreview.language.return_value = (None, "headless")
        with self.assertLogs(slots.logger, level="INFO") as log:
            slots._after_commit()
        sb.tk.ShadowPreview.toggle.assert_not_called()
        self.assertIn("headless", "\n".join(log.output))

    def test_a_discard_republishes_the_record_then_removes_the_pngs(self):
        slots, sb = self._built()
        slots._after_discard()
        engine = sb.tk.ShadowRig
        calls = [c[0] for c in engine.mock_calls]
        self.assertLess(
            calls.index("refresh_export_metadata"),
            calls.index("delete_orphaned_textures"),
        )
        engine.delete_orphaned_textures.assert_called_once_with(["/tex/p1.png"])
        engine.pack_atlas.assert_not_called()
        self.assertEqual((slots._built_rigs, slots._preview_textures), ([], []))


class TestShadowRigSources(_PanelCase):
    def test_source_names_parse(self):
        slots, sb = _panel(texts={"txt_source": " keyLight, fill ;fill , "})
        self.assertEqual(slots._source_names(), ["keyLight", "fill"])
        slots, sb = _panel(texts={"txt_source": ""})
        self.assertEqual(slots._source_names(), ["shadow_source"])

    def test_an_edit_under_preview_creates_the_source_then_refreshes(self):
        slots, sb = _panel(texts={"txt_source": "keyLight"}, previewing=True)
        slots._on_sources_edited()
        sb.tk.ShadowRig.ensure_source.assert_called_once_with("keyLight")
        slots.preview.refresh.assert_called_once()

    def test_an_unchanged_field_rebuilds_nothing(self):
        """editingFinished also fires on focus loss."""
        slots, sb = _panel(texts={"txt_source": "keyLight"}, previewing=True)
        slots._built_sources = ["keyLight"]
        slots._on_sources_edited()
        sb.tk.ShadowRig.ensure_source.assert_not_called()
        slots.preview.refresh.assert_not_called()

    def test_a_name_the_host_refuses_is_reported(self):
        slots, sb = _panel(texts={"txt_source": "lambert1"}, previewing=True)
        sb.tk.ShadowRig.ensure_source.side_effect = ValueError("not a transform")
        slots._on_sources_edited()
        sb.message_box.assert_called_once_with("not a transform")
        slots.preview.refresh.assert_not_called()

    def test_source_from_selection_writes_the_selected_names(self):
        slots, sb = _panel()
        sb.tk.ShadowRig.source_selection.return_value = (["|sun"], [])
        slots.source_from_selection()
        sb.loaded_ui.shadow_rig.txt_source.setText.assert_called_with("|sun")
        sb.tk.LightUtils.lights_from_geometry.assert_not_called()

    def test_a_fixture_builds_area_lights_as_the_sources(self):
        slots, sb = _panel()
        sb.tk.ShadowRig.source_selection.return_value = ([], ["troffer.f[3]"])
        sb.tk.LightUtils.lights_from_geometry.return_value = ["troffer_light"]
        slots.source_from_selection()
        sb.tk.LightUtils.lights_from_geometry.assert_called_once_with(["troffer.f[3]"])
        sb.loaded_ui.shadow_rig.txt_source.setText.assert_called_with("troffer_light")
        self.assertIn("area light", sb.message_box.call_args.args[0])

    def test_a_fixture_no_light_comes_from_is_reported(self):
        slots, sb = _panel()
        sb.tk.ShadowRig.source_selection.return_value = ([], ["troffer.f[3]"])
        sb.tk.LightUtils.lights_from_geometry.return_value = []
        slots.source_from_selection()
        sb.loaded_ui.shadow_rig.txt_source.setText.assert_not_called()
        self.assertIn("No area light", sb.message_box.call_args.args[0])

    def test_nothing_selected_says_what_to_select(self):
        slots, sb = _panel()
        sb.tk.ShadowRig.source_selection.return_value = ([], [])
        slots.source_from_selection()
        self.assertIn("Select the object(s)", sb.message_box.call_args.args[0])

    def test_reproject_re_renders_what_the_named_sources_light_in_one_step(self):
        slots, sb = _panel(texts={"txt_source": "keyLight, gone"})
        engine = sb.tk.ShadowRig
        engine.find_source.side_effect = lambda name: "|keyLight" if name == "keyLight" else None
        engine.planes_lit_by.return_value = ["p1", "p2"]
        engine.refresh_silhouette.return_value = ["p1", "p2"]
        slots.reproject_sources()
        engine.planes_lit_by.assert_called_once_with("|keyLight")
        engine.refresh_silhouette.assert_called_once_with(["p1", "p2"])
        self.assertEqual(self.chunks(sb), ["Shadow Rig: Reproject"])
        sb.tk.CoreUtils.suspended_refresh.assert_called_once_with()
        self.assertIn("Reprojected 2", sb.message_box.call_args.args[0])

    def test_reproject_with_nothing_lit_names_the_missing(self):
        slots, sb = _panel(texts={"txt_source": "gone"})
        slots.reproject_sources()
        sb.tk.ShadowRig.refresh_silhouette.assert_not_called()
        message = sb.message_box.call_args.args[0]
        self.assertIn("No shadow rig is lit by gone", message)
        self.assertIn("Missing: gone", message)


class TestShadowRigBoxes(_PanelCase):
    def test_softness_shows_a_missing_source_as_none_yet(self):
        slots, sb = _panel()
        slots._sync_softness_box()
        box = sb.loaded_ui.shadow_rig.s001
        box.setValue.assert_called_with(0.0)
        self.assertIn("no source yet", sb.tooltip.fmt.call_args.kwargs["body"])

    def test_softness_shows_a_suns_size_in_degrees(self):
        slots, sb = _panel()
        engine = sb.tk.ShadowRig
        engine.find_source.return_value = "|sun"
        engine.source_is_directional.return_value = True
        engine.source_softness.return_value = None
        engine.source_size.return_value = 0.5  # radians
        slots._sync_softness_box()
        value = sb.loaded_ui.shadow_rig.s001.setValue.call_args.args[0]
        self.assertAlmostEqual(value, 28.6479, places=3)
        self.assertIn("degrees", sb.tooltip.fmt.call_args.kwargs["body"])

    def test_softness_sets_the_sources_and_recalculates_what_they_light(self):
        slots, sb = _panel(texts={"txt_source": "a, b"})
        engine = sb.tk.ShadowRig
        engine.ensure_source.side_effect = lambda name: f"|{name}"
        engine.set_source_softness.side_effect = [["p1"], ["p1", "p2"]]
        slots.s001(0.75)
        engine.set_source_softness.assert_any_call("|a", 0.75)
        engine.refresh_silhouette.assert_called_once_with(["p1", "p2"])
        self.assertEqual(self.chunks(sb), ["Shadow Rig: Softness"])

    def test_intensity_retunes_the_selected_rigs(self):
        slots, sb = _panel()
        engine = sb.tk.ShadowRig
        sb.tk.CoreUtils.selected_objects.return_value = ["Box"]
        engine.planes_for_nodes.return_value = ["p1"]
        slots.s002(0.4)
        engine.set_intensity.assert_called_once_with(["p1"], 0.4)
        slots.s003(2.0)
        engine.set_ground_height.assert_called_once_with(["p1"], 2.0)

    def test_with_no_rig_selected_only_the_setting_changes(self):
        slots, sb = _panel()
        slots.s002(0.3)
        sb.tk.ShadowRig.set_intensity.assert_not_called()
        sb.message_box.assert_not_called()

    def test_under_preview_a_box_rebuilds_the_preview_instead(self):
        slots, sb = _panel(previewing=True)
        sb.tk.CoreUtils.selected_objects.return_value = ["Box"]
        slots.s002(0.2)
        slots.preview.refresh.assert_called_once()
        sb.tk.ShadowRig.set_intensity.assert_not_called()

    def test_follow_source_arms_the_engine(self):
        slots, sb = _panel()
        box = mock.MagicMock()
        box.isChecked.return_value = True
        slots.chk_follow_init(box)
        self.assertTrue(box.refresh_on_show)
        sb.tk.ShadowRig.auto_recalculate.assert_called_with(True)
        sb.tk.ShadowRig.recalculate_stale.return_value = ["p1"]
        slots.chk_follow(True)
        sb.tk.ShadowRig.recalculate_stale.assert_called_once_with()
        slots.chk_follow(False)
        sb.tk.ShadowRig.auto_recalculate.assert_called_with(False)

    def test_the_preview_box_loads_with_no_scene(self):
        """The panel loads without a scene (a plain-Python Blender load): with
        no Horizon rig, the box says so and asks nothing of the viewport."""
        slots, sb = _panel()
        box = sb.loaded_ui.shadow_rig.chk_horizon_preview
        slots.chk_horizon_preview_init(box)
        self.assertFalse(box.restore_state)
        self.assertTrue(box.refresh_on_show)
        box.setEnabled.assert_called_with(False)
        box.setChecked.assert_called_with(False)
        sb.tk.ShadowPreview.language.assert_not_called()
        self.assertIn("No Horizon rig", sb.tooltip.fmt.call_args.kwargs["body"])
        events = [c.args[0] for c in sb.tk.ScriptJobManager.instance().subscribe.call_args_list]
        self.assertEqual(events, ["SceneOpened", "NewSceneOpened"])

    def test_the_preview_box_mirrors_what_stands(self):
        slots, sb = _panel()
        engine = sb.tk.ShadowRig
        engine.find_shadow_planes.return_value = ["p1"]
        engine.plane_type.return_value = "horizon"
        sb.tk.ShadowPreview.attached_planes.return_value = ["p1"]
        slots._sync_preview_box()
        box = sb.loaded_ui.shadow_rig.chk_horizon_preview
        box.setChecked.assert_called_with(True)
        box.setEnabled.assert_called_with(True)

    def test_reset_rides_uitks_reset_grammar(self):
        slots, sb = _panel()
        widget = mock.MagicMock()
        slots.b001_init(widget)
        sb.ResetGesture.assert_called_once_with(widget)


class TestShadowRigUtility(_PanelCase):
    def test_nothing_selected_acts_on_all_or_asks(self):
        slots, sb = _panel()
        sb.tk.ShadowRig.find_shadow_planes.return_value = ["p1"]
        self.assertEqual(slots._selected_planes("bake", allow_all=True), ["p1"])
        self.assertEqual(slots._selected_planes("delete"), [])
        self.assertIn("Select the shadow plane(s) to delete", sb.message_box.call_args.args[0])

    def test_a_selection_touching_no_rig_says_so(self):
        slots, sb = _panel()
        sb.tk.CoreUtils.selected_objects.return_value = ["unrelated"]
        sb.tk.ShadowRig.planes_for_nodes.return_value = []
        self.assertEqual(slots._selected_planes("re-source"), [])
        self.assertIn("touches no shadow rig", sb.message_box.call_args.args[0])

    def test_each_utility_action_is_one_undo_step(self):
        slots, sb = _panel()
        engine = sb.tk.ShadowRig
        sb.tk.CoreUtils.selected_objects.return_value = ["Box"]
        engine.planes_for_nodes.return_value = ["p1"]
        engine.find_shadow_planes.return_value = ["p1"]
        engine.pack_atlas.return_value = {"projected": "/t/shadow_atlas_projected.png"}
        slots.b002()
        slots.b003()
        slots.restore_expression()
        slots.b009()
        slots.b010()
        self.assertEqual(
            self.chunks(sb),
            [
                "Shadow Rig: Bake",
                "Shadow Rig: Recalculate Silhouette",
                "Shadow Rig: Restore Expression",
                "Shadow Rig: Delete",
                "Shadow Rig: Pack Atlas",
            ],
        )
        engine.bake_planes.assert_called_once_with(["p1"])
        engine.delete_rigs.assert_called_once_with(["p1"])
        engine.pack_atlas.assert_called_once_with(["p1"])
        self.assertIn("shadow_atlas_projected.png", sb.message_box.call_args.args[0])

    def test_apply_source_reports_each_plane(self):
        slots, sb = _panel(texts={"txt_source": "sun"})
        engine = sb.tk.ShadowRig
        sb.tk.CoreUtils.selected_objects.return_value = ["grp"]
        engine.planes_for_nodes.return_value = ["|grp|p1", "|grp|p2", "|grp|p3"]
        engine.ensure_source.return_value = "|sun"
        rig_ok, rig_bad = mock.MagicMock(), mock.MagicMock()
        rig_bad.set_source.side_effect = RuntimeError("locked")
        engine.from_plane.side_effect = [rig_ok, None, rig_bad]
        slots.apply_source()
        rig_ok.set_source.assert_called_once_with("|sun", size=512)
        message = sb.message_box.call_args.args[0]
        self.assertIn("Source now sun: p1", message)
        self.assertIn("p2: built before the stamps", message)
        self.assertIn("p3: locked", message)
        self.assertEqual(self.chunks(sb), ["Shadow Rig: Apply Source"])

    def test_rebuild_keeps_the_panels_options(self):
        slots, sb = _panel(texts={"s000": "Resolution: 1024"}, checked={"chk_combine": False})
        engine = sb.tk.ShadowRig
        sb.tk.CoreUtils.selected_objects.return_value = ["p1"]
        engine.planes_for_nodes.return_value = ["p1"]
        slots.rebuild_rig()
        engine.rebuild.assert_called_once_with("p1", texture_res=1024, recursive=False)
        self.assertIn("Rebuilt: p1", sb.message_box.call_args.args[0])

    def test_detach_names_what_had_no_silhouette(self):
        slots, sb = _panel()
        engine = sb.tk.ShadowRig
        sb.tk.CoreUtils.selected_objects.return_value = ["p1"]
        engine.planes_for_nodes.return_value = ["|p1", "|p2"]
        engine.detach_planes.return_value = {"|p1": "/t/p1_plane.png"}
        slots.detach_to_plane()
        message = sb.message_box.call_args.args[0]
        self.assertIn("Detached to plane: p1", message)
        self.assertIn("p2: no silhouette on disk", message)
        self.assertEqual(self.chunks(sb), [])  # the engine's own step

    def test_option_boxes_hold_the_deeper_actions_once(self):
        slots, sb = _panel()
        built = {}

        def menu_for(widget):
            menu = mock.MagicMock()
            for name in ("btn_apply_source", "btn_restore", "btn_detach"):
                delattr(menu, name)

            def add(*args, **kwargs):
                button = mock.MagicMock()
                setattr(menu, kwargs["setObjectName"], button)
                built.setdefault(id(widget), []).append(kwargs["setObjectName"])
                return button

            menu.add.side_effect = add
            widget.option_box.menu = menu
            return widget

        update, bake, delete = (menu_for(mock.MagicMock()) for _ in range(3))
        slots.b003_init(update)
        slots.b003_init(update)  # built once
        slots.b002_init(bake)
        slots.b009_init(delete)
        self.assertEqual(built[id(update)], ["btn_apply_source", "btn_rebuild"])
        self.assertEqual(built[id(bake)], ["btn_restore"])
        self.assertEqual(built[id(delete)], ["btn_detach"])
        update.option_box.menu.btn_rebuild.clicked.connect.assert_called_with(
            slots.rebuild_rig
        )

    def test_a_planned_rig_type_is_listed_but_disabled(self):
        slots, sb = _panel()
        combo = mock.MagicMock()
        combo.count.return_value = 3
        combo.itemText.side_effect = ["Rig:  Projected", "Rig:  Horizon", "Rig:  Morphing (planned)"]
        slots.cmb_type_init(combo)
        combo.model().item.assert_called_once_with(2)
        combo.model().item(2).setEnabled.assert_called_with(False)


# ------------------------------------------------------------ in a GUI Maya
@unittest.skipUnless(
    MAYA_AVAILABLE and qt_widgets_available(), "needs a GUI Maya (--in-maya)"
)
class _MayaPanelCase(unittest.TestCase):
    """The panel loaded the way the marking menu opens it (``MayaUiHandler``
    with tentacle's shared roots), over the real ``mtk``; each test gets a
    clean scene. GUI only: the panel hosts a ``Preview``, which native-crashes
    mayapy in batch.

    The silhouettes are written to ``<project>/sourceimages``, and a launched
    GUI Maya opens the user's last project -- which can sit on a cloud-synced
    drive that refuses a quick rewrite of a file it is still syncing (errno
    22). The module runs in a scratch project.
    """

    @classmethod
    def setUpClass(cls):
        from tentacle.tcl import Tcl

        cls.cmds = maya_module("maya.cmds")
        cls.mtk = maya_module("mayatk")
        cls.ShadowRig = cls.mtk.ShadowRig
        handler = cls.mtk.MayaUiHandler.instance()
        Tcl.register_shared(handler.sb)
        cls.ui = handler.get("shadow_rig")
        cls.slots = cls.ui.slots
        cls._artifacts = ptk.TempArtifacts("shadow_rig_panel", policy="scoped")
        project = cls._artifacts.dir_path("project")
        os.makedirs(os.path.join(project, "sourceimages"), exist_ok=True)
        cls._original_workspace = cls.cmds.workspace(q=True, rd=True)
        cls.cmds.workspace(project, openWorkspace=True)

    @classmethod
    def tearDownClass(cls):
        cls.cmds.workspace(cls._original_workspace, openWorkspace=True)
        cls._artifacts.cleanup()

    def setUp(self):
        cmds = self.cmds
        if self.slots.preview.is_enabled:
            self.slots.preview.disable()
        cmds.file(new=True, force=True)
        self.ui.txt_source.setText(self.ShadowRig.DEFAULT_SOURCE_NAME)
        self.messages = []
        self._orig_message_box = self.slots.sb.message_box
        self.slots.sb.message_box = self._capture
        self.slots.preview.message_func = self._capture
        self.cube = cmds.polyCube(name="panel_cube", width=2, height=2, depth=2)[0]
        self._textures = []

    def tearDown(self):
        if self.slots.preview.is_enabled:
            self.slots.preview.disable()
        self.slots.sb.message_box = self._orig_message_box
        self.slots.preview.message_func = self._orig_message_box
        for plane in self.ShadowRig.find_shadow_planes():
            tex = self.ShadowRig._plane_texture_path(plane)
            if tex:
                self._textures.append(tex)
        for path in self._textures:
            with contextlib.suppress(OSError):
                if os.path.exists(path):
                    os.remove(path)

    def _capture(self, message, *args, **kwargs):
        self.messages.append(str(message))

    def _sun(self, name="panelSunShape"):
        cmds = self.cmds
        shape = cmds.directionalLight(name=name)
        tf = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        cmds.setAttr(f"{tf}.rotate", -50, 30, 0, type="double3")
        return tf

    def _enable(self, *objects):
        self.cmds.select(list(objects) or [self.cube], replace=True)
        self.slots.preview.enable()

    def _commit(self):
        self._enable(self.cube)
        self.slots.preview.finalize_changes()
        self.assertTrue(self.cmds.objExists("panel_cube_shadow"), self.messages)
        return "panel_cube_shadow"

    def _option_menu(self, button):
        """The option-box menu of a Utility *button*, the way a user reaches
        it: the Utility group expanded first (a collapsed checkable group
        disables its children), then the menu built the way the switchboard
        builds it (the ``<name>_init`` hook)."""
        self.ui.groupBox_utility.setChecked(True)
        getattr(self.slots, f"{button.objectName()}_init")(button)
        return button.option_box.menu

    @staticmethod
    def _settle(ms=700):
        """Run the event loop long enough for a debounced slot to fire."""
        from qtpy import QtCore

        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(ms, loop.quit)
        getattr(loop, "exec_", loop.exec)()


class TestShadowRigPanelSurfaceInMaya(_MayaPanelCase):
    def test_the_panel_is_the_shared_one_over_mayatk(self):
        self.assertEqual(type(self.slots).__module__, "tentacle.slots.tools.shadow_rig")
        self.assertIs(self.slots.tk, self.mtk)
        self.assertIsInstance(self.slots.preview, self.mtk.Preview)

    def test_widgets_resolve_and_retired_ones_are_gone(self):
        for name in (
            "header", "chk_preview", "cmb_type", "cmb_planes", "cmb_atlas",
            "chk_combine", "txt_source", "s000", "s001", "s002", "s003",
            "chk_follow", "b000", "b001", "b002", "b003", "b009", "b010",
            "groupBox", "groupBox_utility", "footer",
        ):
            self.assertIsNotNone(getattr(self.ui, name, None), name)
        for name in ("cmb000", "cmb_mode", "b004", "b005", "b006", "b007", "b008"):
            self.assertIsNone(getattr(self.ui, name, None), name)
            self.assertFalse(hasattr(self.slots, name), name)

    def test_utility_collapses_and_the_actions_sit_outside_options(self):
        options, utility = self.ui.groupBox, self.ui.groupBox_utility
        self.assertEqual(type(utility).__name__, "CollapsableGroup")
        for name in ("b000", "b001"):
            self.assertNotIn(getattr(self.ui, name).parent(), (options, utility), name)
        for name in ("b002", "b003", "b009", "b010"):
            self.assertTrue(utility.isAncestorOf(getattr(self.ui, name)), name)
        for name in ("cmb_type", "cmb_planes", "cmb_atlas", "chk_combine", "txt_source", "s000"):
            self.assertTrue(options.isAncestorOf(getattr(self.ui, name)), name)

    def test_option_boxes_hold_the_deeper_actions(self):
        update = self._option_menu(self.ui.b003)
        self.assertIsNotNone(getattr(update, "btn_apply_source", None))
        self.assertIsNotNone(getattr(update, "btn_rebuild", None))
        self.assertIsNotNone(getattr(self._option_menu(self.ui.b002), "btn_restore", None))
        self.assertIsNotNone(getattr(self._option_menu(self.ui.b009), "btn_detach", None))
        field = self.ui.txt_source
        self.slots.txt_source_init(field)
        pick, reproject = field._source_actions
        self.assertEqual(pick.widget.objectName(), "btn_source_from_selection")
        self.assertEqual(reproject.widget.objectName(), "btn_reproject")

    def test_softness_settles_in_the_ui(self):
        box = self.ui.s001
        self.assertFalse(box.keyboardTracking())
        self.assertEqual(int(box.property("debounce")), 400)


class TestShadowRigPreviewInMaya(_MayaPanelCase):
    def test_source_survives_refresh_and_commit(self):
        cmds = self.cmds
        self._enable()
        self.assertTrue(self.slots.preview.is_enabled)
        cmds.setAttr("shadow_source.translate", -3, 8, -4, type="double3")
        self.slots.preview.refresh()
        self.assertEqual(cmds.getAttr("shadow_source.translate")[0], (-3.0, 8.0, -4.0))
        self.slots.preview.finalize_changes()
        self.assertFalse(self.slots.preview.is_enabled)
        self.assertEqual(cmds.getAttr("shadow_source.translate")[0], (-3.0, 8.0, -4.0))
        self.assertTrue(cmds.objExists("panel_cube_shadow"))

    def test_a_cancel_keeps_the_source_drops_the_rig_and_its_png(self):
        cmds = self.cmds
        self._enable()
        png = self.ShadowRig._plane_texture_path("panel_cube_shadow")
        self.assertTrue(png and os.path.exists(png), png)
        self.slots.preview.disable()
        self.assertTrue(cmds.objExists("shadow_source"))
        self.assertFalse(cmds.objExists("panel_cube_shadow"))
        self.assertFalse(os.path.exists(png), "the discard leaves no PNG behind")

    def test_a_renamed_source_is_created_before_the_refresh(self):
        cmds = self.cmds
        self._enable()
        self.ui.txt_source.setText("keyLight")
        self.slots._on_sources_edited()
        self.assertTrue(cmds.objExists("keyLight"))
        self.assertTrue(cmds.objExists("panel_cube_keyLight_shadow"))
        self.slots.preview.disable()
        self.assertTrue(cmds.objExists("keyLight"))

    def test_only_the_source_selected_fails_unchecked(self):
        self.ShadowRig.ensure_source("shadow_source")
        self._enable("shadow_source")
        self.assertFalse(self.slots.preview.is_enabled)
        self.assertFalse(self.ui.chk_preview.isChecked())
        self.assertEqual(self.ShadowRig.find_shadow_planes(), [])
        self.assertTrue(any("shadow source itself" in m for m in self.messages), self.messages)

    def test_a_planned_rig_type_fails_the_preview(self):
        combo = self.ui.cmb_type
        combo.addItem(f"Rig:  Morphing {self.slots.PLANNED_SUFFIX}")
        self.addCleanup(combo.removeItem, combo.count() - 1)
        self.addCleanup(combo.setCurrentIndex, 0)
        self.slots.cmb_type_init(combo)
        self.assertFalse(combo.model().item(combo.count() - 1).isEnabled())
        combo.setCurrentIndex(combo.count() - 1)
        self._enable(self.cube)
        self.assertFalse(self.slots.preview.is_enabled)
        self.assertTrue(any("not available yet" in m for m in self.messages), self.messages)

    def test_source_from_selection_then_preview(self):
        cmds = self.cmds
        sun = self._sun()
        cmds.select(sun, replace=True)
        self.slots.source_from_selection()
        self.assertEqual(self.slots._source_names(), [sun])
        self._enable(self.cube)
        planes = self.ShadowRig.find_shadow_planes()
        self.assertEqual(len(planes), 1)
        self.assertEqual(self.ShadowRig._rig_links(planes[0])[1], sun)

    def test_faces_build_fixture_lights_as_the_sources(self):
        cmds = self.cmds
        fixture = cmds.polyCube(name="troffer", width=1.2, height=0.1, depth=0.6)[0]
        cmds.setAttr(f"{fixture}.translateY", 4)
        cmds.select(f"{fixture}.f[3]", replace=True)  # the bottom (lens) face
        self.slots.source_from_selection()
        names = self.slots._source_names()
        self.assertEqual(len(names), 1, names)
        shape = cmds.listRelatives(names[0], shapes=True, fullPath=True)[0]
        self.assertEqual(cmds.nodeType(shape), "areaLight")
        self.assertTrue(any("area light" in m for m in self.messages), self.messages)


class TestShadowRigAtlasInMaya(_MayaPanelCase):
    def setUp(self):
        super().setUp()
        self.crate = self.cmds.polyCube(name="panel_crate", width=1, height=1, depth=1)[0]
        self.cmds.setAttr(f"{self.crate}.translateX", 4.0)
        self.ui.cmb_planes.setCurrentIndex(1)  # Per object
        self.ui.cmb_atlas.setCurrentIndex(0)  # Auto
        self.addCleanup(self.ui.cmb_planes.setCurrentIndex, 0)

    def tearDown(self):
        for kind in self.ShadowRig.ATLAS_BASENAMES:
            path = self.ShadowRig._atlas_path(kind)
            with contextlib.suppress(OSError):
                if os.path.exists(path):
                    os.remove(path)
        super().tearDown()

    def test_per_object_with_auto_atlas_packs_the_pair_on_commit(self):
        engine = self.ShadowRig
        self._enable(self.cube, self.crate)
        self.assertEqual(len(engine.find_shadow_planes()), 2, self.messages)
        self.assertFalse(os.path.exists(engine._atlas_path("projected")))
        self.slots.preview.finalize_changes()
        self.assertTrue(all(engine.plane_is_atlased(p) for p in engine.find_shadow_planes()))

    def test_a_cancelled_preview_leaves_a_committed_atlas_intact(self):
        engine = self.ShadowRig
        self._enable(self.cube, self.crate)
        self.slots.preview.finalize_changes()
        atlas = engine._atlas_path("projected")
        with open(atlas, "rb") as fh:
            before = fh.read()
        third = self.cmds.polyCube(name="panel_third", width=1, height=1, depth=1)[0]
        self.cmds.setAttr(f"{third}.translateZ", 5.0)
        self._enable(third)
        self.slots.preview.disable()  # discard
        with open(atlas, "rb") as fh:
            self.assertEqual(fh.read(), before)
        self.assertEqual(len(engine.find_shadow_planes()), 2)


class TestShadowRigUtilityInMaya(_MayaPanelCase):
    def test_recalculate_via_a_selected_target(self):
        plane = self._commit()
        path = self.ShadowRig._plane_texture_path(plane)
        with open(path, "rb") as fh:
            before = fh.read()
        self.cmds.setAttr("shadow_source.translate", -6, 4, -2, type="double3")
        self.cmds.select(self.cube, replace=True)
        self.slots.b003()
        self.assertTrue(any("Recalculated 1" in m for m in self.messages), self.messages)
        with open(path, "rb") as fh:
            self.assertNotEqual(fh.read(), before)

    def test_bake_and_restore_via_the_source(self):
        plane = self._commit()
        self.cmds.playbackOptions(min=1, max=3)
        self.cmds.select("shadow_source", replace=True)
        self.slots.b002()
        self.assertTrue(self.ShadowRig.plane_is_baked(plane))
        self.slots.restore_expression()
        self.assertTrue(self.ShadowRig.plane_is_live(plane))

    def test_apply_source_via_the_group(self):
        plane = self._commit()
        sun = self._sun()
        self.ui.txt_source.setText(sun)
        self.cmds.select("panel_cube_shadow_grp", replace=True)
        self.slots.apply_source()
        self.assertEqual(self.ShadowRig._rig_links(plane)[1], sun)
        self.assertTrue(any("Source now" in m for m in self.messages), self.messages)

    def test_rebuild_and_delete_via_the_plane_one_undo_each(self):
        cmds = self.cmds
        plane = self._commit()
        cmds.setAttr(f"{self.cube}.scaleY", 2)
        cmds.select(plane, replace=True)
        self._option_menu(self.ui.b003).btn_rebuild.click()
        self.assertAlmostEqual(cmds.getAttr("panel_cube_shadow.objectHeight"), 4.0, places=3)
        cmds.select("panel_cube_shadow", replace=True)
        self.slots.b009()
        self.assertFalse(cmds.objExists("panel_cube_shadow"))
        cmds.undo()  # the delete is one step
        self.assertTrue(cmds.objExists("panel_cube_shadow"))

    def _set_boxes(self, intensity, ground):
        """Put the boxes back without firing their slots."""
        for box, value in ((self.ui.s002, intensity), (self.ui.s003, ground)):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)

    def test_intensity_and_ground_retune_the_selected_rig(self):
        cmds = self.cmds
        self._set_boxes(1.0, 0.0)
        self.addCleanup(self._set_boxes, 1.0, 0.0)
        plane = self._commit()
        cmds.select(self.cube, replace=True)  # a target reaches its rig
        self.ui.s002.setValue(0.4)  # auto-wired, debounced
        self.ui.s003.setValue(2.0)
        self._settle()
        self.assertAlmostEqual(cmds.getAttr(f"{plane}.shadowIntensity"), 0.4)
        self.assertAlmostEqual(cmds.getAttr(f"{plane}.groundHeight"), 2.0)

    def test_reproject_re_renders_the_named_sources_planes(self):
        plane = self._commit()
        self.ShadowRig.auto_recalculate(False)
        self.cmds.move(-6.0, 8.0, 3.0, "shadow_source", absolute=True)
        self.assertTrue(self.ShadowRig.silhouette_is_stale(plane, degrees=2.0))
        self.slots.reproject_sources()
        self.assertFalse(self.ShadowRig.silhouette_is_stale(plane, degrees=2.0))
        self.assertIn("Reprojected 1 silhouette", self.messages[-1])


if __name__ == "__main__":
    unittest.main()
