#!/usr/bin/python
# coding=utf-8
"""The Texture Combine panel's one Slots class (and its Transfer controller),
shared by both hosts.

It reaches its host only through ``self.tk`` (the toolkit the entry point set),
so a fake toolkit stands in for ``mtk`` / ``btk`` here and records what the
panel asks of it: plain unittest, no DCC, no widgets loaded. The two hosts
differ only in what the toolkit answers -- Maya's shader types and words
(``TextureTransfer.TERMS``: the selection order, "UV Set"), Blender's (none;
the active object, "UV Map") -- so each case runs against the vocabulary it is
about. The ``.ui`` is read as XML. In Maya, the same classes drive the real
``mtk`` on real geometry. The host's own side (``TextureCombine.select`` /
``material_faces`` / ``selected_faces``, ``TextureTransfer.selection_sides``)
is the libraries': each ``test_texture_combine.py``.
"""

import os
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import pythontk as ptk

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools._texture_combine.transfer_mode import TransferMode
from tentacle.slots.tools.texture_combine import TextureCombineSlots

UI_PATH = os.path.join(
    os.path.dirname(tentacle.__file__), "ui", "tools", "texture_combine.ui"
)

#: What each host's ``TextureTransfer`` answers (the libraries' ``TERMS`` /
#: ``shader_types()``), trimmed to what these cases read.
MAYA = dict(
    terms={
        "uv": "UV Set",
        "uv_current": "current",
        "uv_linked": "the set the mesh's textures are uvLink-ed to",
        "group": "group",
        "instances": "instances",
        "first": "First Selected Mesh",
        "first_who": "the first-selected object",
        "last": "All But Last Selected",
        "last_who": "the last-selected mesh",
        "pick_first": "Select the source first (a mesh or a group), then the target(s).",
        "pick_last": "Select the source mesh(es) first, then the target last.",
    },
    shader_types={"standard_surface": "Standard Surface", "stingray": "Stingray PBS"},
)
BLENDER = dict(
    terms={
        "uv": "UV Map",
        "uv_current": "active",
        "uv_linked": "the map the textures sample",
        "group": "parent",
        "instances": "linked duplicates",
        "first": "Active Mesh",
        "first_who": "the active object",
        "last": "All But Active",
        "last_who": "the active object",
        "pick_first": "Make the source active and selected, with the target(s) selected.",
        "pick_last": "Make the target mesh active and selected.",
    },
    shader_types={},
)


def _fake_tk(host=MAYA):
    """A toolkit double answering the host's words and shader types."""
    tk = mock.MagicMock()
    tk.TextureTransfer.TERMS = dict(host["terms"])
    tk.TextureTransfer.shader_types.return_value = dict(host["shader_types"])
    tk.TextureTransfer.ASSIGN_FROM = ("target", "source", "in_place")
    tk.TextureTransfer.live_sources.side_effect = lambda names: [
        n for n in names if "gone" not in n
    ]
    tk.TextureCombine.names.return_value = []
    tk.TextureCombine.entry.return_value = {}
    tk.TextureCombine.stale.return_value = []
    tk.TextureCombine.resolve_meshes.return_value = []
    tk.TextureCombine.leaf_name.side_effect = lambda n: str(n).rsplit("|", 1)[-1]
    tk.UvUtils.transfer_uvs.return_value = []
    return tk


def _affix_row(widget, text="", mode="auto"):
    """The Material Affix row over the same ``ptk.StrUtils.split_affix`` the
    real ``AffixOption`` resolves through."""
    widget.text.return_value = text
    widget.option_box.resolve_affix.side_effect = lambda t=None, default="prefix": (
        ptk.StrUtils.split_affix(text if t is None else t, mode=mode, default=default)
    )


#: The rows a run reads, at their defaults.
DEFAULTS = {
    "cmb_set": "",
    "cmb_tt_source": "first",
    "cmb_tt_targets": "order",
    "cmb_tt_transfer": "uvs",
    "cmb_tt_resolution": 0,
    "t_tt_src_uvset": "",
    "t_tt_dst_uvset": "",
    "t_name": "hero",
    "t_output": "",
    "cmb_quality": 2,
    "s_padding": -1,
    "s_spacing": -1,
    "cmb_atlas": 2048,
    "cmb_sizing": "proportional",
    "cmb_normalize": "resolution",
    "chk_rotate": True,
    "chk_lightmaps": True,
    "chk_assign": True,
    "chk_tt_lightmaps": False,
    "cmb_shader": "source",
}


def _panel(values=None, host=MAYA, tk=None, mode=None, affix="", affix_mode="auto"):
    """A Slots instance over a mock ui (*values* on its widgets) and a fake
    toolkit (or *tk*, handed over before the panel is built, as ``Slots.tk``
    is). *mode* puts it in Combine / Transfer as the bound FieldVisibility
    would."""
    sb = mock.MagicMock()
    sb.tk = tk if tk is not None else _fake_tk(host)
    ui = sb.loaded_ui.texture_combine
    for name, value in {**DEFAULTS, **(values or {})}.items():
        widget = getattr(ui, name)
        widget.currentData.return_value = value
        widget.text.return_value = value
        widget.isChecked.return_value = value
        widget.value.return_value = value
        widget.findData.return_value = -1
    _affix_row(ui.t_affix, affix, affix_mode)
    slots = TextureCombineSlots(sb)
    if mode is not None:
        slots._fields = types.SimpleNamespace(mode=mode)
    return slots, sb, ui


def _items(widget):
    """``[(label, data)]`` a combo was filled with."""
    return [tuple(c.args) for c in widget.addItem.call_args_list]


def _message(sb):
    return sb.message_box.call_args.args[0]


def _footer(ui):
    return ui.footer.setText.call_args.args[0]


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        # The class logger is shared: a fake keeps the run's records off it.
        patcher = mock.patch.object(TextureCombineSlots, "logger", mock.MagicMock())
        patcher.start()
        self.addCleanup(patcher.stop)


class TestTextureCombineSetup(_PanelCase):
    def test_init_builds_the_hosts_engine_and_defers_the_wiring(self):
        slots, sb, ui = _panel()
        sb.tk.TextureCombine.assert_called_once_with(log_level="WARNING")
        self.assertIs(slots.engine, sb.tk.TextureCombine.return_value)
        self.assertIsInstance(slots.transfer, TransferMode)
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._initialize_ui)
        sb.FieldVisibility.assert_not_called()

    def _modes(self, host):
        slots, sb, ui = _panel(host=host)
        slots._initialize_ui()
        fields = sb.FieldVisibility.return_value
        combine = fields.define.call_args.args
        transfer = fields.define.return_value.define.call_args.args
        return ui, combine, transfer

    def test_each_mode_shows_its_groups_and_the_shared_rows(self):
        ui, (mode, combine), (mode2, transfer) = self._modes(MAYA)
        self.assertEqual((mode, mode2), ("combine", "transfer"))
        for widget in (
            ui.cmb_set,
            ui.grp_sources,
            ui.grp_layout,
            ui.grp_output,
            ui.t_affix,
        ):
            self.assertIn(widget, combine)
        for widget in (ui.grp_transfer, ui.grp_textures, ui.chk_assign, ui.grp_output):
            self.assertIn(widget, transfer)
        self.assertNotIn(ui.grp_transfer, combine)
        self.assertNotIn(ui.grp_sources, transfer)

    def test_the_material_row_is_a_combines_only_with_shader_types(self):
        """Maya rebuilds a combine on a shader type; Blender has none, so its
        Combine mode would offer choices that do nothing -- Transfer only."""
        ui, (_, combine), (_, transfer) = self._modes(MAYA)
        self.assertIn(ui.cmb_shader, combine)
        self.assertIn(ui.cmb_shader, transfer)
        ui, (_, combine), (_, transfer) = self._modes(BLENDER)
        self.assertNotIn(ui.cmb_shader, combine)
        self.assertIn(ui.cmb_shader, transfer)

    def test_scene_events_subscribe_through_the_host(self):
        slots, sb, ui = _panel()
        slots._initialize_ui()
        jobs = sb.tk.ScriptJobManager.instance.return_value
        self.assertEqual(
            [c.args[0] for c in jobs.subscribe.call_args_list],
            ["SelectionChanged", "SceneOpened", "NewSceneOpened", "Undo", "Redo"],
        )
        jobs.connect_cleanup.assert_called_once_with(ui, owner=slots)

    def test_the_material_combo_keeps_overwrite_last(self):
        """The row persists by INDEX: source, target, the host's shader types,
        then Overwrite target -- Blender (none) keeps its three in order."""
        for host, data in (
            (MAYA, ["source", "target", "standard_surface", "stingray", "in_place"]),
            (BLENDER, ["source", "target", "in_place"]),
        ):
            slots, sb, ui = _panel(host=host)
            combo = mock.MagicMock()
            slots.cmb_shader_init(combo)
            self.assertEqual([d for _, d in _items(combo)], data)
            self.assertTrue(
                all(label.startswith("Material: ") for label, _ in _items(combo))
            )

    def test_the_mode_combo_saves_its_index(self):
        slots, sb, ui = _panel()
        combo = mock.MagicMock()
        slots.cmb_mode_init(combo)
        self.assertEqual([d for _, d in _items(combo)], ["combine", "transfer"])

    def test_help_speaks_the_hosts_uv_word_and_links_the_docs(self):
        for host in (MAYA, BLENDER):
            slots, sb, ui = _panel(host=host)
            header = mock.MagicMock()
            slots.header_init(header)
            steps = sb.tooltip.fmt.call_args.kwargs["steps"]
            self.assertIn(host["terms"]["uv"], steps[-1])
            self.assertEqual(
                header.set_help_text.call_args.kwargs["url"], slots.HELP_URL
            )

    def test_parse_scale(self):
        parse = TextureCombineSlots.parse_scale
        self.assertAlmostEqual(parse("1/3"), 1 / 3)
        self.assertAlmostEqual(parse("33%"), 0.33)
        self.assertAlmostEqual(parse("0,5"), 0.5)
        self.assertIsNone(parse("abc"))
        self.assertIsNone(parse("-1"))


class TestCombineMode(_PanelCase):
    def test_the_picker_lists_the_hosts_combines_and_their_revisions(self):
        slots, sb, ui = _panel()
        sb.tk.TextureCombine.names.return_value = ["kit", "crate"]
        sb.tk.TextureCombine.stale.side_effect = lambda n: (
            ["a.png"] if n == "kit" else []
        )
        slots._refresh_sets()
        self.assertEqual(
            _items(ui.cmb_set),
            [
                ("New Combine", ""),
                ("kit  (1 map(s) revised)", "kit"),
                ("crate", "crate"),
            ],
        )

    def test_select_set_selects_the_members_through_the_host(self):
        slots, sb, ui = _panel({"cmb_set": "kit"})
        sb.tk.TextureCombine.members.return_value = ["|a", "|b"]
        slots.select_set()
        sb.tk.TextureCombine.select.assert_called_once_with(["|a", "|b"])
        self.assertEqual(_footer(ui), "Selected 2 mesh(es) of kit.")
        sb.tk.TextureCombine.members.return_value = []
        slots.select_set()
        self.assertIn("none of its meshes are in the scene", _footer(ui))

    def test_a_material_row_selects_its_faces_and_an_override_its_target(self):
        slots, sb, ui = _panel()
        slots._inputs = object()
        slots._rows = [{"kind": "faces", "target": ["|a.f[2]"], "scale": 1.0}]
        slots._table_rows = [("material", "matA"), ("faces", 0)]
        combines = sb.tk.TextureCombine
        combines.material_faces.return_value = ["|a.f[0:1]"]
        ui.tbl_sources.currentRow.return_value = 0
        slots.select_row_members()
        combines.material_faces.assert_called_once_with(slots._inputs, "matA")
        combines.select.assert_called_with(["|a.f[0:1]"])
        ui.tbl_sources.currentRow.return_value = 1
        slots.select_row_members()
        combines.select.assert_called_with(["|a.f[2]"])

    def test_mesh_overrides_read_the_hosts_selection(self):
        slots, sb, ui = _panel()
        sb.tk.TextureCombine.resolve_meshes.return_value = ["|a", "|b"]
        slots.b001()
        sb.tk.TextureCombine.resolve_meshes.assert_called_with(None)
        self.assertEqual([r["target"] for r in slots._rows], ["|a", "|b"])
        # The table labels them by the host's leaf name.
        sb.tk.TextureCombine.leaf_name.assert_any_call("|a")

    def test_island_overrides_read_the_hosts_faces(self):
        slots, sb, ui = _panel()
        sb.tk.TextureCombine.selected_faces.return_value = []
        slots.b002()
        self.assertEqual(slots._rows, [])
        self.assertIn("Select faces", _footer(ui))
        sb.tk.TextureCombine.selected_faces.return_value = ["|a.f[0:3]"]
        slots.b002()
        self.assertEqual(
            slots._rows, [{"kind": "faces", "target": ["|a.f[0:3]"], "scale": 1.0}]
        )

    def _result(self):
        return {
            "name": "kit",
            "material": "kit_MAT",
            "maps": {"baseColor": "/out/kit_BaseColor.png"},
            "meshes": 2,
            "map_size": 2048,
            "utilization": 0.5,
            "groups": {},
            "lightmaps": {},
        }

    def test_combine_reads_the_meshes_now_and_sends_the_panel(self):
        slots, sb, ui = _panel({"t_name": "kit"}, mode="combine")
        slots._inputs = types.SimpleNamespace(transforms=["|a", "|b"], sources={})
        engine = slots.engine
        engine.combine.return_value = self._result()
        slots.combine()
        engine.gather.assert_any_call(["|a", "|b"])
        kwargs = engine.combine.call_args.kwargs
        self.assertEqual(kwargs["name"], "kit")
        self.assertIs(kwargs["inputs"], engine.gather.return_value)
        self.assertEqual(kwargs["map_size"], 2048)
        self.assertIsNone(kwargs["padding"])  # Spacing: Auto
        self.assertIsNone(kwargs["assign_shader_type"])  # Same as source
        self.assertEqual(
            (kwargs["sizing"], kwargs["normalize"]), ("proportional", "resolution")
        )
        self.assertIn("Combined <b>2</b> mesh(es) into <b>kit_MAT</b>", _message(sb))

    def test_a_shader_type_reaches_the_combine(self):
        slots, sb, ui = _panel({"cmb_shader": "stingray"}, mode="combine")
        slots.engine.combine.return_value = self._result()
        slots.combine()
        self.assertEqual(
            slots.engine.combine.call_args.kwargs["assign_shader_type"], "stingray"
        )

    def test_a_stored_combine_updates(self):
        slots, sb, ui = _panel({"cmb_set": "kit"}, mode="combine")
        slots.engine.update.return_value = self._result()
        slots.combine()
        self.assertEqual(slots.engine.update.call_args.args, ("kit",))
        slots.engine.combine.assert_not_called()

    def test_a_refused_combine_says_why(self):
        slots, sb, ui = _panel(mode="combine")
        slots.engine.gather.side_effect = ValueError("no meshes to combine")
        slots.combine()
        self.assertIn("Nothing to combine", _message(sb))
        slots.engine.combine.assert_not_called()

    def test_a_stored_combines_settings_touch_the_material_row_only_with_types(self):
        for host, touched in ((MAYA, True), (BLENDER, False)):
            slots, sb, ui = _panel(host=host)
            slots._apply_settings({"assign_shader_type": None})
            self.assertEqual(
                ui.cmb_shader.findData.called, touched, host["terms"]["uv"]
            )


class _TransferCase(_PanelCase):
    """The run is the host's (``TextureCombine.run_transfer``: ``ptk.TransferRun``
    over the host, pinned in pythontk's ``test_uv_transfer_run.py``): these
    cases hand the panel a ``ptk.TransferResult`` and read what it says, and
    read the rows it hands the run."""

    def _run(self, result=None, values=None, host=MAYA, affix="", affix_mode="auto"):
        slots, sb, ui = _panel(
            values, host=host, mode="transfer", affix=affix, affix_mode=affix_mode
        )
        slots.engine.run_transfer.return_value = (
            result if result is not None else ptk.TransferResult(mode="first")
        )
        slots.transfer.run()
        return slots, sb, ui

    def _kwargs(self, values=None, **kwargs):
        slots, sb, ui = self._run(values=values, **kwargs)
        slots.engine.run_transfer.assert_called_once()
        return slots.engine.run_transfer.call_args.kwargs


class TestTransferRows(_TransferCase):
    def test_the_rows_reach_the_hosts_run(self):
        kw = self._kwargs()
        self.assertEqual(
            (kw["source"], kw["transfer"], kw["scope"], kw["stored"]),
            ("first", "uvs", "order", []),
        )
        self.assertEqual((kw["similarity"], kw["lightmaps"]), (0.9, False))
        self.assertEqual(
            (kw["output_name"], kw["supersample"], kw["padding"]), ("hero", 2, -1)
        )
        self.assertIsNone(kw["size"])  # Resolution: Auto
        self.assertEqual((kw["output_dir"], kw["source_uv_set"]), (None, None))
        self.assertEqual((kw["assign_prefix"], kw["assign_suffix"]), ("", None))
        self.assertEqual((kw["assign"], kw["assign_from"]), (True, "source"))
        self.assertNotIn("assign_shader_type", kw)

    def test_the_stored_meshes_and_the_similarity_reach_the_run(self):
        slots, sb, ui = _panel(mode="transfer")
        slots.transfer.sources = ["|a"]
        slots.transfer.similarity = mock.MagicMock(**{"value.return_value": 0.7})
        slots.engine.run_transfer.return_value = ptk.TransferResult(mode="first")
        slots.transfer.run()
        kw = slots.engine.run_transfer.call_args.kwargs
        self.assertEqual((kw["stored"], kw["similarity"]), (["|a"], 0.7))

    def test_the_affix_picker(self):
        self.assertEqual(self._kwargs(affix="_MAT")["assign_suffix"], "_MAT")
        self.assertEqual(self._kwargs(affix="MAT_")["assign_prefix"], "MAT_")
        kw = self._kwargs(affix="MAT", affix_mode="prefix")
        self.assertEqual((kw["assign_prefix"], kw["assign_suffix"]), ("MAT", ""))
        kw = self._kwargs(affix="MAT")  # Auto falls back to the suffix
        self.assertEqual((kw["assign_prefix"], kw["assign_suffix"]), ("", "MAT"))

    def test_the_material_row(self):
        kw = self._kwargs({"cmb_shader": "stingray"})
        self.assertEqual(
            (kw["assign_shader_type"], kw["assign_from"]), ("stingray", "source")
        )
        kw = self._kwargs({"cmb_shader": "target"})
        self.assertEqual(kw["assign_from"], "target")
        self.assertNotIn("assign_shader_type", kw)

    def test_overwrite_target_re_uses_the_material_and_drops_the_affix(self):
        kw = self._kwargs({"cmb_shader": "in_place"}, affix="_MAT")
        self.assertEqual(kw["assign_from"], "in_place")
        self.assertEqual((kw["assign_prefix"], kw["assign_suffix"]), ("", None))

    def test_each_pass_names_its_progress_in_the_hosts_words(self):
        slots, sb, ui = self._run(host=BLENDER)
        progress = slots.engine.run_transfer.call_args.kwargs["progress"]
        tick = sb.progress.return_value.__enter__.return_value
        progress("uvs")
        tick.assert_called_with(text="Working: Transfer UV Map")
        progress("textures")
        tick.assert_called_with(text="Working: Transfer Textures")

    def test_a_typed_name_that_produced_maps_is_remembered(self):
        maps = {"m": {"baseColor": "/out/hero_BaseColor.png"}}
        result = ptk.TransferResult(
            mode="first", do_textures=True, maps=maps, typed=True,
            output_name="hero", named="hero",
        )  # fmt: skip
        for typed, recorded in ((True, [mock.call("hero")]), (False, [])):
            result.typed = typed
            slots, sb, ui = _panel(mode="transfer")
            slots._name_recent = mock.MagicMock()  # the Output Name's history
            slots.engine.run_transfer.return_value = result
            slots.transfer.run()
            self.assertEqual(slots._name_recent.record.call_args_list, recorded)


class TestTransferWords(_TransferCase):
    """How the panel words a run's result, in each host's terms."""

    def test_every_refusal_the_run_names_has_words(self):
        for host in (MAYA, BLENDER):
            slots, sb, ui = _panel(host=host, mode="transfer")
            for refusal in ptk.TransferRun.REFUSALS:
                result = ptk.TransferResult(mode="first", refusal=refusal)
                self.assertTrue(slots.transfer.report(result), refusal)

    def test_no_selection_refuses_with_the_hosts_hint(self):
        for host in (MAYA, BLENDER):
            for refusal in ("pick_first", "pick_last"):
                slots, sb, ui = self._run(
                    ptk.TransferResult(mode="first", refusal=refusal), host=host
                )
                self.assertIn(host["terms"][refusal], _message(sb))

    def test_the_uv_pass_refuses_a_combined_target(self):
        result = ptk.TransferResult(mode="last", refusal="one_source_per_target")
        slots, sb, ui = self._run(result)
        self.assertIn("one source per target", _message(sb))

    def test_no_similar_mesh_names_the_hosts_instances(self):
        for host in (MAYA, BLENDER):
            result = ptk.TransferResult(mode="first", refusal="no_similar")
            slots, sb, ui = self._run(result, host=host)
            self.assertIn("No similar meshes found", _message(sb))
            self.assertIn(host["terms"]["instances"], _message(sb))

    def test_the_hosts_message_is_quoted(self):
        result = ptk.TransferResult(
            mode="first", refusal="uv_error", error="no shared topology"
        )
        slots, sb, ui = self._run(result, host=BLENDER)
        self.assertEqual(_message(sb), "<b>Transfer UV Map:</b><br>no shared topology")

    def test_auto_says_how_it_read_the_selection(self):
        maps = {"m": {"baseColor": "/out/hero_BaseColor.png"}}
        result = ptk.TransferResult(
            mode="last", source_auto=True, do_textures=True, maps=maps,
            typed=True, output_name="hero", named="hero",
        )  # fmt: skip
        slots, sb, ui = self._run(result)
        self.assertIn("<i>Source: Auto</i> read a mesh combined", _message(sb))
        # A refusal reads the same way, with Auto's pick.
        result = ptk.TransferResult(
            mode="first", source_auto=True, transfer_auto=True, do_textures=True,
            refusal="similar_needs_uvs",
        )  # fmt: skip
        slots, sb, ui = self._run(result)
        self.assertIn("chose Textures", _message(sb))
        self.assertIn(
            "<i>Source: Auto</i> read the first-selected object", _message(sb)
        )

    def test_the_uv_pass_says_what_it_sampled_by_proximity(self):
        result = ptk.TransferResult(
            mode="first", do_uvs=True, uvs=[("src", "tgt", "topology")]
        )
        slots, sb, ui = self._run(result)
        self.assertIn("Transferred UVs to <b>1</b> object(s).", _message(sb))
        self.assertNotIn("proximity", _message(sb))
        result.uvs = [("src", "tgt", "nearest")]
        slots, sb, ui = self._run(result)
        self.assertIn("sampled by proximity", _message(sb))

    def test_the_texture_pass_links_its_folder_and_says_its_name(self):
        maps = {"m": {"baseColor": "/out/crate_BaseColor.png"}}
        result = ptk.TransferResult(
            mode="first", do_textures=True, maps=maps,
            output_name="crate", named="crate",
        )  # fmt: skip
        slots, sb, ui = self._run(result)
        text = _message(sb)
        self.assertIn("Transferred <b>1</b> map(s) for <b>1</b> material(s)", text)
        self.assertIn('<a href="action://open?path=/out">/out</a>', text)
        self.assertIn("Named <b>crate</b> after the source", text)
        result.typed, result.named = True, "crate_1"
        slots, sb, ui = self._run(result)
        self.assertIn("<b>crate</b> is held outside this run", _message(sb))
        result = ptk.TransferResult(
            mode="first", do_textures=True, texture_error="no source maps"
        )
        slots, sb, ui = self._run(result)
        self.assertEqual(_message(sb), "<b>Transfer Textures:</b> no source maps")

    def test_the_lightmap_pass_links_the_maps_home(self):
        result = ptk.TransferResult(
            mode="first", do_textures=True, maps={}, typed=True,
            output_name="hero", named="hero",
            lightmap_results={
                "tgt": {"how": "resampled", "path": "/session/hero_Lightmap.exr"},
                "t2": {"how": "rebound", "path": "/maps/lm.exr"},
            },
            lightmap_folder="/proj/lightmaps",
        )  # fmt: skip
        slots, sb, ui = self._run(result)
        text = _message(sb)
        self.assertIn("<b>1</b> bound to the source's own map", text)
        self.assertIn("<b>1</b> resampled into the target's layout", text)
        self.assertIn('<a href="action://open?path=/proj/lightmaps">', text)
        result.lightmap_results = {}
        slots, sb, ui = self._run(result)
        self.assertIn("No lightmaps transferred", _message(sb))

    def test_overwrite_note_names_the_files_rewritten_in_place(self):
        result = ptk.TransferResult(
            overwritten=["/maps/own.png"],
            added=["/maps/new.png"],
            warnings=["kept <x>"],
        )
        note = TransferMode.overwrite_note(result)
        self.assertIn("Overwrote <b>1</b> file(s) in place: own.png", note)
        self.assertIn("Wrote <b>1</b> new file(s)", note)
        self.assertIn("&bull; kept &lt;x&gt;", note)
        note = TransferMode.overwrite_note(
            ptk.TransferResult(warnings=[f"w{i}" for i in range(9)])
        )
        self.assertIn("No file was overwritten in place.", note)
        self.assertIn("... and 3 more (the log).", note)


class TestStoredSources(_TransferCase):
    def test_capture_stores_the_hosts_names_and_switches_to_stored(self):
        slots, sb, ui = _panel(mode="transfer")
        sb.tk.TextureTransfer.capture_sources.return_value = ["|a"]
        ui.cmb_tt_source.findData.return_value = 3
        slots.transfer.capture_source()
        self.assertEqual(slots.transfer.sources, ["|a"])
        ui.cmb_tt_source.setCurrentIndex.assert_called_once_with(3)
        self.assertEqual(_footer(ui), "Stored 1 source mesh(es).")

    def test_select_reports_the_deleted_and_the_unselectable(self):
        slots, sb, ui = _panel(mode="transfer")
        slots.transfer.sources = ["|a", "|gone"]
        sb.tk.TextureCombine.select.return_value = 1
        slots.transfer.select_source()
        sb.tk.TextureCombine.select.assert_called_once_with(["|a"])
        self.assertEqual(
            _footer(ui),
            "Selected 1 stored source mesh(es). 1 no longer in the scene; skipped.",
        )
        # Blender declines an object in an excluded collection: said, not forced.
        sb.tk.TextureCombine.select.return_value = 0
        slots.transfer.select_source()
        self.assertIn("1 not selectable", _footer(ui))

    def test_select_with_nothing_stored_leaves_the_selection_alone(self):
        slots, sb, ui = _panel(mode="transfer")
        slots.transfer.select_source()
        sb.tk.TextureCombine.select.assert_not_called()
        self.assertIn("Nothing stored", _footer(ui))

    def test_the_tooltip_lists_short_names_and_calls_out_the_deleted(self):
        slots, sb, ui = _panel(mode="transfer")
        sb.tooltip = ptk.TooltipFormat
        slots.transfer.sources = ["|grp|pCube1", "|grp|gone"]
        html = slots.transfer.source_tooltip()
        self.assertIn("<li>pCube1</li>", html)
        self.assertNotIn("|grp", html)
        self.assertIn("1 no longer in the scene", html)


class TestTransferWidgets(_PanelCase):
    def test_the_source_combo_speaks_the_hosts_convention(self):
        for host, first in ((MAYA, "First Selected Mesh"), (BLENDER, "Active Mesh")):
            slots, sb, ui = _panel(host=host)
            combo = mock.MagicMock()
            slots.transfer.init_source(combo)
            self.assertEqual(
                [d for _, d in _items(combo)],
                ["auto", "first", "last", "stored", "uvset"],
            )
            labels = [label for label, _ in _items(combo)]
            self.assertEqual(labels[1], f"Source: {first}")
            self.assertEqual(labels[4], f"Source: {host['terms']['uv']}s On Same Mesh")

    def test_the_transfer_combo_saves_its_index(self):
        slots, sb, ui = _panel(host=BLENDER)
        combo = mock.MagicMock()
        slots.transfer.init_transfer(combo)
        self.assertEqual(_items(combo)[2], ("Transfer: UV Map", "uvs"))
        self.assertEqual([d for _, d in _items(combo)], ["auto", "textures", "uvs"])

    def test_the_uv_fields_take_the_hosts_word(self):
        slots, sb, ui = _panel(host=BLENDER)
        src, dst = mock.MagicMock(), mock.MagicMock()
        slots.transfer.init_uv_sets(src, dst)
        src.setPlaceholderText.assert_called_once_with("Source UV Map: Auto")
        dst.setPlaceholderText.assert_called_once_with("Target UV Map: Auto")

    def test_targets_grey_unless_the_first_pick(self):
        for mode, live in (("first", True), ("auto", False), ("last", False)):
            slots, sb, ui = _panel({"cmb_tt_source": mode}, mode="transfer")
            slots.transfer.sync()
            ui.cmb_tt_targets.setEnabled.assert_called_with(live)

    def test_overwrite_target_greys_the_affix(self):
        slots, sb, ui = _panel(
            {"cmb_shader": "in_place"}, mode="transfer", affix="_MAT"
        )
        self.assertEqual(slots.assign_options(), {"assign_from": "in_place"})
        self.assertEqual(slots.material_affix(), ("", None))
        slots.sync_shared(textures=True)
        ui.t_affix.setEnabled.assert_called_with(False)


class TestTextureCombineUi(unittest.TestCase):
    """The ``.ui``: the controls the panel reads, in neutral words."""

    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(UI_PATH).getroot()
        cls.widgets = {w.get("name"): w for w in cls.root.iter("widget")}

    def test_every_widget_the_panel_uses_exists(self):
        for name in (
            "header", "cmb_mode", "cmb_set", "grp_sources", "tbl_sources", "b001",
            "b002", "grp_layout", "cmb_sizing", "cmb_normalize", "cmb_atlas",
            "s_spacing", "chk_rotate", "chk_lightmaps", "grp_transfer",
            "cmb_tt_transfer", "cmb_tt_source", "cmb_tt_targets", "grp_textures",
            "t_tt_src_uvset", "t_tt_dst_uvset", "cmb_tt_resolution",
            "chk_tt_lightmaps", "grp_output", "t_name", "t_output", "cmb_quality",
            "s_padding", "grp_material", "chk_assign", "t_affix", "cmb_shader",
            "b000", "footer",
        ):  # fmt: skip
            self.assertIn(name, self.widgets, name)
        self.assertEqual(self.widgets["tbl_sources"].get("class"), "TableWidget")

    def test_no_host_specific_words(self):
        text = ET.tostring(self.root, encoding="unicode")
        for word in ("sourceimages", "UV Set:", "UV Map:", ".blend"):
            self.assertNotIn(word, text)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestTextureCombinePanelInMaya(_PanelCase):
    """The panel over the real ``mtk`` on real geometry (the widgets stay
    mocks, set to the options under test). Transfer's passes are captured, the
    selection reading is Maya's own."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        self.uv_calls = []

        def fake_transfer_uvs(frm, to, **kwargs):
            self.uv_calls.append((list(frm), list(to), kwargs))
            return [(s, t, "topology") for s, t in zip(frm, to)]

        patcher = mock.patch.object(
            self.mtk.UvUtils, "transfer_uvs", side_effect=fake_transfer_uvs
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _capture_textures(self):
        captured = []

        def transfer(engine, targets, source=None, **kwargs):
            captured.append((list(targets), source, kwargs))
            return {"m": {"baseColor": "/out/hero_BaseColor.png"}}

        # The engine the host's run builds (``TextureTransfer()``), wherever
        # it is imported from: the class's own method.
        patcher = mock.patch.object(
            self.mtk.TextureTransfer, "transfer", autospec=True, side_effect=transfer
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return captured

    def _run(self, values):
        slots, sb, ui = _panel(values, tk=self.mtk, mode="transfer")
        slots.transfer.run()
        return slots, sb

    def _long(self, *names):
        return [self.cmds.ls(n, long=True)[0] for n in names]

    def test_two_objects_transfer_as_one_pair(self):
        a, b = self._long(
            self.cmds.polyCube(name="tm_a")[0], self.cmds.polyCube(name="tm_b")[0]
        )
        self.cmds.select([a, b], replace=True)
        slots, sb = self._run({})
        self.assertEqual(self.uv_calls, [([a], [b], {"match_by_similarity": False})])
        self.assertIn("Transferred UVs to <b>1</b> object(s).", _message(sb))

    def test_auto_finds_the_combined_target_wherever_it_was_picked(self):
        cmds = self.cmds
        a = cmds.polyCube(name="srcA")[0]
        b = cmds.polySphere(name="srcB", sx=6, sy=4)[0]
        cmds.move(3, 0, 0, b)
        c = cmds.polyUnite(cmds.duplicate([b, a]), ch=False, name="comb")[0]
        c = cmds.rename(cmds.parent(c, cmds.group(empty=True, name="out"))[0], a)
        a, b, c = self._long(f"|{a}", f"|{b}", c)
        captured = self._capture_textures()
        cmds.select([c, a, b], replace=True)
        slots, sb = self._run({"cmb_tt_source": "auto", "cmb_tt_transfer": "textures"})
        self.assertEqual([(t, s) for t, s, _ in captured], [([c], [a, b])])
        self.assertIn("Source: Auto", _message(sb))

    def test_a_blank_name_is_named_after_the_source(self):
        cmds = self.cmds
        grp = cmds.group(empty=True, name="hero_GRP")
        src = cmds.parent(cmds.polyCube(name="hero_body_GEO")[0], grp)[0]
        tgt = cmds.polyCube(name="tm_named_tgt")[0]
        captured = self._capture_textures()
        cmds.select([cmds.ls(src, long=True)[0], tgt], replace=True)
        self._run({"t_name": "", "cmb_tt_transfer": "textures"})
        self.assertEqual(captured[0][2]["output_name"], "hero_body")

    def test_select_source_skips_meshes_deleted_since_the_capture(self):
        cmds = self.cmds
        cube = self._long(cmds.polyCube()[0])[0]
        slots, sb, ui = _panel(tk=self.mtk, mode="transfer")
        slots.transfer.sources = [cube, "|goneForever"]
        cmds.select(clear=True)
        slots.transfer.select_source()
        self.assertEqual(cmds.ls(selection=True, long=True), [cube])
        self.assertIn("1 no longer in the scene", _footer(ui))

    def test_one_run_is_one_undo_step(self):
        import numpy as np
        from PIL import Image

        cmds = self.cmds
        artifacts = ptk.TempArtifacts("tcl_tc_undo", policy="scoped")
        self.addCleanup(artifacts.cleanup)
        tmp = artifacts.dir_path()
        texture = os.path.join(tmp, "tc_undo.png").replace("\\", "/")
        Image.fromarray(np.full((8, 8, 3), (255, 0, 0), np.uint8)).save(texture)
        src = cmds.polyPlane(name="tc_undo_src", sx=1, sy=1, ch=False)[0]
        mat = cmds.shadingNode("lambert", asShader=True, name="tc_undo_mat")
        sg = cmds.sets(
            renderable=True, noSurfaceShader=True, empty=True, name="tc_undo_sg"
        )
        cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader")
        f = cmds.shadingNode("file", asTexture=True)
        cmds.setAttr(f"{f}.fileTextureName", texture, type="string")
        cmds.connectAttr(f"{f}.outColor", f"{mat}.color")
        cmds.sets(src, edit=True, forceElement=sg)
        tgt = cmds.duplicate(src, name="tc_undo_tgt")[0]
        cmds.polyEditUV(
            f"{tgt}.map[*]", rotation=True, angle=90, pivotU=0.5, pivotV=0.5
        )
        cmds.select([src, tgt], replace=True)
        out_dir = os.path.join(tmp, "out").replace("\\", "/")
        slots, sb = self._run(
            {
                "cmb_tt_transfer": "textures",
                "t_name": "tc_undo_hero",
                "t_output": out_dir,
            }
        )
        worn = self.mtk.TextureTransfer.face_materials(tgt)[0]
        self.assertNotEqual(worn, ["tc_undo_mat"], sb.message_box.call_args)
        cmds.undo()
        self.assertEqual(
            self.mtk.TextureTransfer.face_materials(tgt)[0], ["tc_undo_mat"]
        )

    def test_a_material_row_selects_its_faces(self):
        cmds = self.cmds
        plane = self._long(cmds.polyPlane(name="tc_rows", sx=2, sy=1, ch=False)[0])[0]
        slots, sb, ui = _panel(tk=self.mtk, mode="combine")
        inputs = self.mtk.CombineInputs(transforms=[plane])
        import numpy as np

        inputs.shapes["s"] = {
            "materials": ["matX", "matY"],
            "face_material": np.array([0, 1]),
            "transforms": [plane],
        }
        slots._inputs = inputs
        slots._table_rows = [("material", "matY")]
        ui.tbl_sources.currentRow.return_value = 0
        slots.select_row_members()
        self.assertEqual(cmds.ls(selection=True, long=True), [f"{plane}.f[1]"])


if __name__ == "__main__":
    unittest.main()
