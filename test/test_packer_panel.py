#!/usr/bin/python
# coding=utf-8
"""Tests for the standalone Map Packer panel (``slots/tools/packer.py``): channel packing.

Regression guard for the conversion branch of ``_pack_set``: when a
requested channel map is absent but derivable from another present map
(e.g. Smoothness from Roughness), the slot must convert and pack it.
The line that did this called ``self.get_converted_map`` — a static that
lives on ``MapFactory``, not on ``ImgUtils`` (then the slot's base) — so it
raised ``AttributeError`` and the conversion path never worked.

The heavy UI wiring in ``__init__`` is bypassed (``__new__``); ``_pack_set``
touches no UI, so it is exercised directly.
"""

import os

# The preset-combo test constructs the real panel; force the offscreen Qt
# platform so it runs headless (and never flashes a window on a dev display).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import types
import unittest
from unittest import mock

from PIL import Image

import pythontk as ptk
from pythontk import ImgUtils

from uitk.testing import TestSandbox

# A direct `python test/test_packer_panel.py` loads no conftest, so the sandbox is
# activated here too -- before the preset-combo test's panel opens its preset
# store and restores widget state. Idempotent.
TestSandbox.activate()

from tentacle.slots.tools.packer import PackerSlots


class TestMapPackerConversion(unittest.TestCase):
    """``_pack_set`` derives missing channels from convertible maps."""

    @classmethod
    def setUpClass(cls):
        cls._temp = ptk.TempArtifacts("packer_panel_test", policy="scoped")
        cls.test_dir = cls._temp.dir_path()
        # Only a Roughness map is present; Smoothness must be derived from it.
        cls.roughness = os.path.join(cls.test_dir, "mat_Roughness.png")
        ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), 64), cls.roughness)

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def test_pack_set_converts_missing_channel(self):
        """Smoothness absent → converted from Roughness, packed, file written."""
        inst = self._bare_slots()
        # R=Smoothness (must convert), G/B/A=None.
        combos = ["Smoothness", "None", "None", "None"]
        result = inst._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=combos,
            suffix="_Test",
            ext="png",
            fmt="PNG",
        )
        self.assertTrue(result)
        out = os.path.join(self.test_dir, "mat_Test.png")
        self.assertTrue(os.path.isfile(out), f"expected packed output at {out}")

    def test_pack_set_no_assignable_channels(self):
        """All channels None → nothing assigned, returns False, no file."""
        inst = self._bare_slots()
        combos = ["None", "None", "None", "None"]
        result = inst._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=combos,
            suffix="_Empty",
            ext="png",
            fmt="PNG",
        )
        self.assertFalse(result)
        self.assertFalse(os.path.isfile(os.path.join(self.test_dir, "mat_Empty.png")))


class TestMapPackerCompleteness(unittest.TestCase):
    """``_pack_set`` only packs complete sets unless the Missing Maps rule allows it.

    Regression: an unresolvable channel map used to be reported and skipped,
    but whatever had already been assigned was still packed — writing a map
    whose missing channels are filled with a constant, indistinguishable
    downstream from a legitimately flat channel. The default is now to skip
    the whole set; the header's 'Missing Maps' policy opts back in, either
    always (``force``) or only when 2+ channels resolved (``multi``).
    """

    @classmethod
    def setUpClass(cls):
        cls._temp = ptk.TempArtifacts("packer_panel_complete", policy="scoped")
        cls.test_dir = cls._temp.dir_path()
        # Roughness only — Metallic is neither present nor derivable from it.
        # Smoothness IS derivable from Roughness (inversion), so a set asking
        # for Roughness+Smoothness+Metallic resolves 2 of 3 channels.
        cls.roughness = os.path.join(cls.test_dir, "mat_Roughness.png")
        ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), 64), cls.roughness)

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def _pack(self, suffix, combos, **kwargs):
        return self._bare_slots()._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=combos,
            suffix=suffix,
            ext="png",
            fmt="PNG",
            **kwargs,
        )

    def _path(self, suffix):
        return os.path.join(self.test_dir, f"mat{suffix}.png")

    def _written(self, suffix):
        return os.path.isfile(self._path(suffix))

    # One channel resolves, one doesn't. Channel ORDER is load-bearing here:
    # the old code stopped at the first unresolvable channel and packed
    # whatever preceded it, so only the resolvable-first layout exposes the
    # partial write. The missing-first layout instead proves the packing rules
    # keep resolving channels *past* the gap (the old break never did).
    RESOLVABLE_FIRST = ["Roughness", "Metallic", "None", "None"]
    MISSING_FIRST = ["Metallic", "Roughness", "None", "None"]
    # Two resolve (Roughness directly, Smoothness by conversion), one doesn't.
    TWO_OF_THREE = ["Roughness", "Smoothness", "Metallic", "None"]

    def test_incomplete_set_skipped_by_default(self):
        """Caller omits the rule → safe default, nothing written."""
        self.assertFalse(self._pack("_Default", self.RESOLVABLE_FIRST))
        self.assertFalse(self._written("_Default"))

    def test_incomplete_set_skipped_under_skip_rule(self):
        self.assertFalse(
            self._pack("_Skip", self.RESOLVABLE_FIRST, rule=PackerSlots.MISSING_SKIP)
        )
        self.assertFalse(self._written("_Skip"))

    def test_incomplete_set_packed_under_force_rule(self):
        """Pack Anyway → resolution continues past the gap, missing channels fill."""
        self.assertTrue(
            self._pack("_Forced", self.MISSING_FIRST, rule=PackerSlots.MISSING_FORCE)
        )
        self.assertTrue(self._written("_Forced"))

    def test_multi_rule_skips_single_resolved_channel(self):
        """Pack If 2+ Maps → one resolved channel isn't enough."""
        self.assertFalse(
            self._pack(
                "_MultiOne", self.RESOLVABLE_FIRST, rule=PackerSlots.MISSING_MULTI
            )
        )
        self.assertFalse(self._written("_MultiOne"))

    def test_multi_rule_packs_two_resolved_channels(self):
        """Pack If 2+ Maps → two resolved channels pack despite the third missing."""
        self.assertTrue(
            self._pack("_MultiTwo", self.TWO_OF_THREE, rule=PackerSlots.MISSING_MULTI)
        )
        self.assertTrue(self._written("_MultiTwo"))

    def test_complete_set_packs_under_every_rule(self):
        """A set with no missing maps is unaffected by the policy."""
        for rule in (
            PackerSlots.MISSING_SKIP,
            PackerSlots.MISSING_MULTI,
            PackerSlots.MISSING_FORCE,
        ):
            with self.subTest(rule=rule):
                suffix = f"_Complete_{rule}"
                self.assertTrue(
                    self._pack(suffix, ["Roughness", "None", "None", "None"], rule=rule)
                )
                self.assertTrue(self._written(suffix))

    def test_wholly_unresolvable_set_is_reported_not_silent(self):
        """No channel resolves → skipped WITH a reason, under every rule.

        The empty-assignment early-out used to return before the missing-map
        report, so a set whose *only* requested map was absent dropped out
        with no per-set explanation at all. 'Pack Anyway' must also land here
        rather than in ``pack_channels``, which raises on an empty assignment.
        """
        for rule in (
            PackerSlots.MISSING_SKIP,
            PackerSlots.MISSING_MULTI,
            PackerSlots.MISSING_FORCE,
        ):
            with self.subTest(rule=rule):
                suffix = f"_NoneResolved_{rule}"
                with self.assertLogs(PackerSlots.logger, "WARNING") as logs:
                    result = self._pack(
                        suffix, ["Metallic", "None", "None", "None"], rule=rule
                    )
                self.assertFalse(result)
                self.assertFalse(self._written(suffix))
                self.assertIn("Metallic", "\n".join(logs.output))
                self.assertIn("mat", "\n".join(logs.output))

    def test_output_mode_follows_the_configured_layout(self):
        """Channel count comes from the layout, not from what happened to resolve.

        A 3-channel layout (ORM / MRAO — A on 'None') must stay RGB, which is
        the point of those formats. Conversely a force-packed set whose alpha
        map is missing still writes RGBA, so one batch can't emit a mix of RGB
        and RGBA files under a single suffix.
        """
        self.assertTrue(
            self._pack(
                "_RGB",
                ["Metallic", "Roughness", "Smoothness", "None"],
                rule=PackerSlots.MISSING_FORCE,
            )
        )
        self.assertEqual(Image.open(self._path("_RGB")).mode, "RGB")

        # A requested but unresolvable (Metallic) -> still RGBA, alpha filled.
        self.assertTrue(
            self._pack(
                "_RGBA",
                ["Roughness", "Smoothness", "None", "Metallic"],
                rule=PackerSlots.MISSING_FORCE,
            )
        )
        self.assertEqual(Image.open(self._path("_RGBA")).mode, "RGBA")

    def test_rule_reads_the_missing_maps_combo(self):
        """``_missing_map_rule`` mirrors the window combo; safe default if absent."""
        inst = self._bare_slots()
        # Combo not registered yet (bare instance) → safe default.
        inst.ui = types.SimpleNamespace()
        self.assertEqual(inst._missing_map_rule(), PackerSlots.MISSING_SKIP)

        combo = _FakeDataCombo(PackerSlots.MISSING_FORCE)
        inst.ui = types.SimpleNamespace(cmbMissing=combo)
        self.assertEqual(inst._missing_map_rule(), PackerSlots.MISSING_FORCE)
        # No selection (currentData() -> None) must not disable the guard.
        combo.data = None
        self.assertEqual(inst._missing_map_rule(), PackerSlots.MISSING_SKIP)


class TestMapPackerOpenPBRLobes(unittest.TestCase):
    """The glTF lobe packings: clearcoat R + its roughness G from an OpenPBR set.

    The lobe maps classified as base maps (``mat_Coat_Roughness`` was a
    Roughness) and the channel combos offered no lobe at all, so the pair
    KHR_materials_clearcoat reads from one texture could not be packed.
    """

    def setUp(self):
        self.temp = ptk.TempArtifacts("packer_panel_lobes", policy="scoped")
        self.dir = self.temp.dir_path()
        self.files = []
        for suffix, value in (
            ("Coat_Weight", 200),
            ("Coat_Roughness", 40),
            ("Roughness", 90),
        ):
            path = os.path.join(self.dir, f"mat_{suffix}.png")
            ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), value), path)
            self.files.append(path)

    def tearDown(self):
        self.temp.cleanup()

    def test_coat_weight_and_roughness_pack_into_one_texture(self):
        self.assertIn("Clearcoat", PackerSlots.grayscale_types)
        self.assertIn("Clearcoat_Roughness", PackerSlots.grayscale_types)
        self.assertTrue(
            PackerSlots.__new__(PackerSlots)._pack_set(
                base_name="mat",
                files=self.files,
                combos=["Clearcoat", "Clearcoat_Roughness", "None", "None"],
                suffix="_Clearcoat_Pack",
                ext="png",
                fmt="PNG",
            )
        )
        packed = ImgUtils.ensure_image(os.path.join(self.dir, "mat_Clearcoat_Pack.png"))
        # The coat roughness, never the base Roughness (90).
        self.assertEqual(packed.getpixel((0, 0))[:2], (200, 40))

    def test_a_set_named_for_a_lobe_packs_its_own_roughness(self):
        """``Hero_Coat_Roughness`` read alone is a coat roughness; read with its
        set ``Hero_Coat`` it is that set's roughness."""
        files = []
        for suffix, value in (("Metallic", 10), ("Roughness", 90)):
            path = os.path.join(self.dir, f"Hero_Coat_{suffix}.png")
            ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), value), path)
            files.append(path)
        self.assertTrue(
            PackerSlots.__new__(PackerSlots)._pack_set(
                base_name="Hero_Coat",
                files=files,
                combos=["Metallic", "Roughness", "None", "None"],
                suffix="_MR",
                ext="png",
                fmt="PNG",
            )
        )
        packed = ImgUtils.ensure_image(os.path.join(self.dir, "Hero_Coat_MR.png"))
        self.assertEqual(packed.getpixel((0, 0))[:2], (10, 90))


class TestMapPackerOutputAffix(unittest.TestCase):
    """The output name: which side the affix lands on, and never over an input."""

    @classmethod
    def setUpClass(cls):
        cls._temp = ptk.TempArtifacts("packer_panel_affix", policy="scoped")
        cls.test_dir = cls._temp.dir_path()
        cls.roughness = os.path.join(cls.test_dir, "mat_Roughness.png")
        ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), 64), cls.roughness)

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def _pack(self, **kwargs):
        return PackerSlots.__new__(PackerSlots)._pack_set(
            base_name="mat",
            files=[self.roughness],
            combos=["Roughness", "None", "None", "None"],
            ext="png",
            fmt="PNG",
            **kwargs,
        )

    def test_a_prefix_lands_on_the_front_of_the_name(self):
        """_pack_set gained `prefix`; nothing covered the branch."""
        self.assertTrue(self._pack(prefix="ORM_", suffix=""))
        self.assertTrue(
            os.path.isfile(os.path.join(self.test_dir, "ORM_mat.png")),
            "the prefix branch did not reach the output name",
        )

    def test_an_affix_free_name_refuses_to_overwrite_its_own_source(self):
        """An emptied convention entry is legal, and would pack over an input.

        With prefix and suffix both empty the output stem EQUALS the source stem,
        so the pack would read a map and write its own result on top of it --
        destroying an artist's source texture with no warning.
        """
        # a source whose stem is exactly what an affix-free output would be called
        collide = os.path.join(self.test_dir, "mat.png")
        ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), 32), collide)
        before = os.path.getsize(collide)

        packed = PackerSlots.__new__(PackerSlots)._pack_set(
            base_name="mat",
            files=[collide],
            combos=["Roughness", "None", "None", "None"],
            ext="png",
            fmt="PNG",
            prefix="",
            suffix="",
        )
        self.assertFalse(packed)
        self.assertEqual(
            os.path.getsize(collide),
            before,
            "the pack wrote over one of its own source maps",
        )


class TestMapPackerChannelSelection(unittest.TestCase):
    """The channel layout is read once, in channel order, and gates both batches."""

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def test_channel_combos_read_in_channel_order(self):
        inst = self._bare_slots()
        picks = ["Metallic", "Roughness", "Ambient_Occlusion", "Smoothness"]
        inst.ui = types.SimpleNamespace(
            **{f"cmb{c}": _FakeCombo(current=p) for c, p in zip("RGBA", picks)}
        )
        self.assertEqual(inst._channel_combos(), picks)

    def test_empty_selection_is_reported_and_blocks_the_batch(self):
        """All channels 'None' → the run stops before the file dialog.

        Otherwise both batches walk the whole selection to no effect and
        report every set as skipped, blaming the files for an empty layout.
        """
        inst = self._bare_slots()
        with self.assertLogs(PackerSlots.logger, "WARNING") as logs:
            allowed = inst._require_channel_selection(["None"] * 4)
        self.assertFalse(allowed)
        self.assertIn("No channels assigned", "\n".join(logs.output))

    def test_partial_selection_passes(self):
        inst = self._bare_slots()
        self.assertTrue(
            inst._require_channel_selection(["None", "Roughness", "None", "None"])
        )


class TestMapPackerUnpack(unittest.TestCase):
    """``_unpack_one`` splits a packed texture into per-channel maps."""

    @classmethod
    def setUpClass(cls):
        cls._temp = ptk.TempArtifacts("packer_panel_unpack", policy="scoped")
        cls.test_dir = cls._temp.dir_path()
        # An RGB packed map (no alpha), distinct per channel so outputs differ.
        cls.packed = os.path.join(cls.test_dir, "mat_ORM.png")
        ImgUtils.save_image(
            ImgUtils.create_image("RGB", (8, 8), (10, 120, 240)), cls.packed
        )

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    @staticmethod
    def _bare_slots():
        return PackerSlots.__new__(PackerSlots)

    def test_unpack_one_extracts_assigned_channels(self):
        """Each non-None channel → a per-channel map named by its map type;
        an absent channel (A on an RGB input) is skipped without error."""
        inst = self._bare_slots()
        combos = ["Ambient_Occlusion", "Roughness", "Metallic", "Smoothness"]
        result = inst._unpack_one(file=self.packed, combos=combos, ext="png", fmt="PNG")
        self.assertTrue(result)
        for suffix in ("_Ambient_Occlusion", "_Roughness", "_Metallic"):
            out = os.path.join(self.test_dir, f"mat{suffix}.png")
            self.assertTrue(os.path.isfile(out), f"expected {out}")
        # A was requested (Smoothness) but the source is RGB → no alpha output.
        self.assertFalse(
            os.path.isfile(os.path.join(self.test_dir, "mat_Smoothness.png"))
        )

    def test_unpack_one_all_none(self):
        """All channels None → nothing extracted, returns False."""
        inst = self._bare_slots()
        result = inst._unpack_one(
            file=self.packed,
            combos=["None", "None", "None", "None"],
            ext="png",
            fmt="PNG",
        )
        self.assertFalse(result)


class TestMapPackerSelectRemembersDir(unittest.TestCase):
    """``_select_textures`` re-seeds ``source_dir`` from the picked files.

    Regression: the packer only rewrote ``source_dir`` in ``_finish_batch``
    (to the *output* dir, on success), so after the user browsed to a new
    folder the next dialog reopened at the stale seed dir. The sibling
    ``ConverterSlots`` re-seeds after every selection; the packer must too.
    """

    class _FakeSwitchboard:
        def __init__(self, returns):
            self._returns = returns
            self.start_dir = None

        def file_dialog(self, *, file_types, title, start_dir, allow_multiple):
            self.start_dir = start_dir
            return self._returns

    @classmethod
    def _bare_slots(cls, returns):
        inst = PackerSlots.__new__(PackerSlots)
        inst._source_dir = "O:/seed/dir"
        inst.sb = cls._FakeSwitchboard(returns)
        return inst

    def test_selection_updates_source_dir(self):
        picked = ["O:/new/folder/mat_Roughness.png"]
        inst = self._bare_slots(picked)
        result = inst._select_textures("pick")
        self.assertEqual(result, picked)
        # Dialog opened at the old seed; source_dir now points at the pick.
        self.assertEqual(inst.sb.start_dir, "O:/seed/dir")
        self.assertEqual(inst.source_dir.replace("\\", "/"), "O:/new/folder")

    def test_cancel_leaves_source_dir_unchanged(self):
        inst = self._bare_slots([])
        inst._select_textures("pick")
        self.assertEqual(inst.source_dir, "O:/seed/dir")


def _builtin_presets():
    """The shipped templates, ``{stem: payload}``, read straight off disk."""
    import json

    out = {}
    for fname in sorted(os.listdir(PackerSlots.BUILTIN_PRESET_DIR)):
        if fname.endswith(".json"):
            path = os.path.join(PackerSlots.BUILTIN_PRESET_DIR, fname)
            with open(path, encoding="utf-8") as f:
                out[fname[:-5]] = json.load(f)
    return out


class TestMapPackerPresets(unittest.TestCase):
    """The shipped templates: one per supported packing, each a valid layout."""

    # Template -> the registry packing whose channel layout it must match.
    REGISTRY_PACKINGS = {
        "ORM - Unreal glTF Godot": "ORM",
        "MRAO - Metallic Roughness AO": "MRAO",
        "MSAO - Unity HDRP Mask Map": "MSAO",
        "Metallic Smoothness - Unity URP": "Metallic_Smoothness",
    }
    # The glTF extension pairs the lobe combos exist for.
    GLTF_PAIRS = {
        "Clearcoat - glTF": ("Clearcoat", "Clearcoat_Roughness"),
        "Iridescence - glTF": ("Thin_Film", "Thin_Film_Thickness"),
        "Transmission Volume - glTF": ("Transmission", "Thickness"),
    }

    def test_every_supported_packing_has_a_template(self):
        """Each packed type in ``MapRegistry`` whose channels hold grayscale maps
        ships a template, plus the glTF pairs -- and nothing else ships.

        ``Albedo_Transparency`` is the one packing left out: its RGB carries a
        COLOR map, and each channel combo here holds one grayscale map.
        """
        registry = ptk.MapRegistry.instance()
        grayscale = set(PackerSlots.grayscale_types)
        packed = {  # optional ("?") channels are left empty, so they don't count
            name
            for name in registry.get_map_types()
            if registry.get(name).is_packed
            and {
                t for t in registry.get(name).channels.values() if not t.endswith("?")
            }
            <= grayscale
        }
        self.assertEqual(packed, set(self.REGISTRY_PACKINGS.values()))
        self.assertEqual(
            set(_builtin_presets()), set(self.REGISTRY_PACKINGS) | set(self.GLTF_PAIRS)
        )

    def test_templates_name_items_their_combos_hold(self):
        """Stored by TEXT, so a typo or a renamed type would load as nothing."""
        for name, data in _builtin_presets().items():
            with self.subTest(preset=name):
                for c in "RGBA":
                    self.assertIn(data[f"cmb{c}"], PackerSlots.grayscale_types)
                self.assertIn(data["cmbFormat"], PackerSlots.output_formats)
                self.assertTrue(data["txtSuffix"].startswith("_"))
                self.assertEqual(data["_meta"]["affix_mode"], "suffix")
                self.assertTrue(data["_meta"]["description"])
                # The stem the combo lists IS the file name.
                self.assertEqual(ptk.PresetStore.sanitize_preset_name(name), name)

    def test_template_layouts_match_the_registry(self):
        """Locks each layout to ``pythontk.MapRegistry``'s ``MapType.channels``
        (the ecosystem SSoT blendertk's material builder also reads). An RGB
        triplet is carried by R; an optional channel (``?``) stays empty."""
        registry = ptk.MapRegistry.instance()
        presets = _builtin_presets()
        for name, packing in self.REGISTRY_PACKINGS.items():
            with self.subTest(preset=name):
                expected = {c: "None" for c in "RGBA"}
                for ch, map_type in registry.get(packing).channels.items():
                    if not map_type.endswith("?"):
                        expected[ch[0]] = map_type
                self.assertEqual(
                    {c: presets[name][f"cmb{c}"] for c in "RGBA"}, expected
                )
        for name, (r, g) in self.GLTF_PAIRS.items():
            with self.subTest(preset=name):
                self.assertEqual(
                    [presets[name][f"cmb{c}"] for c in "RGBA"], [r, g, "None", "None"]
                )

    def test_output_names_never_classify_as_a_source_map(self):
        """A packed output read back as one of its own inputs (a ``_Clearcoat``
        output is a Clearcoat map) would be packed again by the next batch."""
        from pythontk.core_utils.engines.textures.map_factory import MapFactory

        for name, data in _builtin_presets().items():
            with self.subTest(preset=name):
                map_type = MapFactory.resolve_map_type(f"mat{data['txtSuffix']}.png")
                self.assertNotIn(map_type, [data[f"cmb{c}"] for c in "RGBA"])

    def test_three_channel_presets_pack_to_the_declared_layout(self):
        """ORM / MRAO round-trip: 3-channel RGB, each map in its named channel.

        They stay RGB -- no alpha is what lets these compress as BC1 rather
        than BC3/BC7, and it is the whole point of the format.
        """
        expected = {  # preset -> (R, G, B) source values, per the SSoT layout
            "ORM - Unreal glTF Godot": (50, 100, 200),  # AO, Roughness, Metallic
            "MRAO - Metallic Roughness AO": (200, 100, 50),  # M, R, AO
        }
        values = {"Metallic": 200, "Roughness": 100, "Ambient_Occlusion": 50}

        temp = ptk.TempArtifacts("packer_panel_preset", policy="scoped")
        self.addCleanup(temp.cleanup)
        test_dir = temp.dir_path()
        files = []
        for map_type, value in values.items():
            path = os.path.join(test_dir, f"mat_{map_type}.png")
            ImgUtils.save_image(ImgUtils.create_image("L", (8, 8), value), path)
            files.append(path)

        inst = PackerSlots.__new__(PackerSlots)
        presets = _builtin_presets()
        for name, rgb in expected.items():
            with self.subTest(preset=name):
                preset = presets[name]
                self.assertTrue(
                    inst._pack_set(
                        base_name="mat",
                        files=files,
                        combos=[preset[f"cmb{c}"] for c in "RGBA"],
                        suffix=preset["txtSuffix"],
                        ext=preset["cmbFormat"].lower(),
                        fmt=preset["cmbFormat"],
                    )
                )
                out = os.path.join(test_dir, f"mat{preset['txtSuffix']}.png")
                with Image.open(out) as img:
                    self.assertEqual(img.mode, "RGB")
                    self.assertEqual(img.getpixel((0, 0)), rgb)


class TestMapPackerRetireLegacySeeds(unittest.TestCase):
    """The copies earlier releases seeded into the user store are retired once.

    They predate the built-in tier and would list beside it as duplicates; an
    edited copy is the user's own preset and stays.
    """

    def setUp(self):
        import json
        from uitk.managers.preset_manager import PresetManager

        temp = ptk.TempArtifacts("packer_panel_seeds", policy="scoped")
        self.addCleanup(temp.cleanup)
        self.user_dir = temp.dir_path()
        self.seeded = {}
        for stem, (_, values) in PackerSlots._LEGACY_SEEDS.items():
            data = {"_meta": {"version": 1}, "cmbFormat": 0, **values}
            self.seeded[stem] = os.path.join(self.user_dir, f"{stem}.json")
            with open(self.seeded[stem], "w") as f:
                json.dump(data, f)
        self.presets = PresetManager.from_widgets(
            self.user_dir, widgets=[], builtin_dir=PackerSlots.BUILTIN_PRESET_DIR
        )

    def _user_presets(self):
        return sorted(n for n in self.presets.list() if self.presets.source(n) == "user")

    def test_untouched_seeds_go_and_the_active_pick_follows(self):
        self.presets.active_preset = "ORM _Unreal_ glTF_"
        PackerSlots._retire_legacy_seeds(self.presets)
        self.assertEqual(self._user_presets(), [])
        self.assertEqual(self.presets.active_preset, "ORM - Unreal glTF Godot")
        self.assertEqual(self.presets.source(self.presets.active_preset), "builtin")

    def test_an_edited_seed_is_the_users_and_stays(self):
        import json

        edited = "MRAO _Metallic_ Roughness_ AO_"
        with open(self.seeded[edited]) as f:
            data = json.load(f)
        data["txtSuffix"] = "_Mine"
        with open(self.seeded[edited], "w") as f:
            json.dump(data, f)
        PackerSlots._retire_legacy_seeds(self.presets)
        self.assertEqual(self._user_presets(), [edited])


class TestMapPackerPresetCombo(unittest.TestCase):
    """The preset selector and every option live in the main window."""

    @classmethod
    def setUpClass(cls):
        # conftest's TestSandbox keeps the user preset store and QSettings out
        # of the real user dirs, so the combo lists the built-ins alone.
        from qtpy.QtWidgets import QApplication
        from tentacle.tcl_standalone import PackerUI

        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.ui = PackerUI()
        cls.ui.show()  # offscreen -- drives run_when_ready / the deferred wiring
        for _ in range(20):
            cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ui.deleteLater()
        cls.app.processEvents()

    def test_preset_combo_lists_the_builtin_templates(self):
        combo = self.ui.cmbPreset
        listed = sorted(combo.itemText(i) for i in range(combo.count()))
        self.assertEqual(listed, sorted(self.ui.presets.list()))
        self.assertEqual(listed, sorted(_builtin_presets()))

    def test_header_menu_is_empty(self):
        """Mode and Missing Maps moved into the window; nothing is left behind."""
        from qtpy.QtWidgets import QComboBox

        # The menu wraps a wired combo in its option-box container, so look
        # through the whole menu rather than at its top-level items.
        self.assertEqual(self.ui.header.menu.findChildren(QComboBox), [])

    def test_options_sit_in_workflow_order(self):
        """Mode first (it decides what every row means), then the preset, the
        channels, and the output rows the action writes."""
        from qtpy.QtCore import QPoint

        names = [
            "cmbMode",
            "cmbPreset",
            "cmbR",
            "cmbFormat",
            "txtSuffix",
            "cmbMissing",
            "b000",
        ]
        ys = [getattr(self.ui, n).mapTo(self.ui, QPoint(0, 0)).y() for n in names]
        self.assertEqual(ys, sorted(ys), dict(zip(names, ys)))

    def test_unpack_mode_disables_the_pack_only_rows(self):
        combo = self.ui.cmbMode
        self.addCleanup(combo.setCurrentIndex, combo.findData("pack"))
        combo.setCurrentIndex(combo.findData("unpack"))
        self.app.processEvents()
        self.assertEqual(self.ui.b000.text(), "Unpack")
        self.assertFalse(self.ui.cmbMissing.isEnabled())
        self.assertFalse(self.ui.txtSuffix.isEnabled())

    def test_picking_a_preset_loads_the_channel_layout(self):
        combo = self.ui.cmbPreset
        name = "MRAO - Metallic Roughness AO"
        index = combo.findText(name)
        combo.setCurrentIndex(index)
        combo.activated.emit(index)
        self.app.processEvents()
        preset = _builtin_presets()[name]
        self.assertEqual(
            [getattr(self.ui, f"cmb{c}").currentText() for c in "RGBA"],
            [preset[f"cmb{c}"] for c in "RGBA"],
        )
        self.assertEqual(self.ui.txtSuffix.text(), preset["txtSuffix"])

    def test_a_saved_preset_stores_map_type_names(self):
        """A user preset reads like a template: names, not row numbers."""
        import json

        self.ui.cmbR.setCurrentText("Clearcoat")
        self.ui.presets.save("Test Names")
        self.addCleanup(self.ui.presets.delete, "Test Names")
        path = self.ui.presets.preset_dir / "Test Names.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["cmbR"], "Clearcoat")
        self.assertIn(data["cmbFormat"], PackerSlots.output_formats)


class _FakeCombo:
    """Minimal QComboBox stand-in for exercising slot handlers off-screen."""

    def __init__(self, items=None, current="None"):
        self._items = list(items or [])
        self._current = current
        self._enabled = True

    def currentText(self):
        return self._current

    def setEnabled(self, value):
        self._enabled = bool(value)

    def isEnabled(self):
        return self._enabled

    def findText(self, text):
        return self._items.index(text) if text in self._items else -1

    def setCurrentIndex(self, index):
        if 0 <= index < len(self._items):
            self._current = self._items[index]


class _FakeDataCombo:
    """Minimal data-carrying QComboBox stand-in for the Missing Maps option."""

    def __init__(self, data=None):
        self.data = data

    def currentData(self):
        return self.data


class _FakeUI:
    """Bare namespace exposing the widgets ``_on_format_changed`` touches."""

    def __init__(self, cmbA, mode):
        self.cmbA = cmbA
        self.cmbMode = _FakeDataCombo("unpack" if mode == "Unpack" else "pack")


class TestMapPackerFormatAlphaGuard(unittest.TestCase):
    """``_on_format_changed`` must not clear the alpha combo while unpacking.

    Regression: the format combo's ``currentTextChanged`` fires in both modes.
    Selecting an alpha-less output format (JPG) disabled cmbA and reset it to
    'None' unconditionally — silently dropping the channel the user chose to
    *extract* in Unpack mode. The guard mirrors ``_on_mode_changed``: format
    only constrains alpha in Pack mode.
    """

    @staticmethod
    def _slots(mode, alpha_choice):
        inst = PackerSlots.__new__(PackerSlots)
        cmbA = _FakeCombo(items=PackerSlots.grayscale_types, current=alpha_choice)
        inst.ui = _FakeUI(cmbA, mode)
        return inst, cmbA

    def test_unpack_mode_keeps_alpha_selection_on_jpg(self):
        inst, cmbA = self._slots("Unpack", "Smoothness")
        inst._on_format_changed("JPG")
        # Alpha combo stays enabled and its extraction choice is untouched.
        self.assertTrue(cmbA.isEnabled())
        self.assertEqual(cmbA.currentText(), "Smoothness")

    def test_pack_mode_clears_alpha_on_jpg(self):
        inst, cmbA = self._slots("Pack", "Smoothness")
        inst._on_format_changed("JPG")
        # Pack mode still constrains alpha to the output format's capabilities.
        self.assertFalse(cmbA.isEnabled())
        self.assertEqual(cmbA.currentText(), "None")

    def test_pack_mode_keeps_alpha_on_png(self):
        inst, cmbA = self._slots("Pack", "Smoothness")
        inst._on_format_changed("PNG")
        self.assertTrue(cmbA.isEnabled())
        self.assertEqual(cmbA.currentText(), "Smoothness")


class TestMapPackerOpenOutputDirSafety(unittest.TestCase):
    """``b001`` opens the output dir via a non-shell launcher (no injection).

    Regression: the old handler built ``os.system(f'open "{output_dir}"')`` /
    ``xdg-open`` strings, so a directory named e.g. ``foo$(touch pwned)`` was
    passed through /bin/sh. The fix delegates to ``FileUtils.open_explorer``,
    which passes the path as a single argv entry — shell metacharacters are
    inert and ``os.system`` is never used.
    """

    def test_open_output_dir_delegates_to_non_shell_launcher(self):
        inst = PackerSlots.__new__(PackerSlots)
        malicious = "O:/foo$(touch pwned)/out"
        inst._last_output_dir = malicious

        with (
            mock.patch("os.path.isdir", return_value=True),
            mock.patch("os.system") as system_mock,
            mock.patch(
                "tentacle.slots.tools.packer.FileUtils.open_explorer",
                return_value=True,
            ) as open_mock,
        ):
            inst.b001()

        # No shell was spawned; the raw path went to the safe launcher intact.
        system_mock.assert_not_called()
        open_mock.assert_called_once_with(malicious)

    def test_open_output_dir_noop_without_output(self):
        inst = PackerSlots.__new__(PackerSlots)
        # No _last_output_dir set at all → guarded early-return, no launcher call.
        with (
            mock.patch("os.system") as system_mock,
            mock.patch(
                "tentacle.slots.tools.packer.FileUtils.open_explorer"
            ) as open_mock,
        ):
            inst.b001()
        system_mock.assert_not_called()
        open_mock.assert_not_called()


class TestMapPackerHoldsNoEngine(unittest.TestCase):
    """The panel calls ``ImgUtils``; it is not one.

    Like ``ConverterSlots`` and ``MeshConvertSlots``: a slots class that
    inherited its engine carried the whole image library as its own surface.
    The pack, unpack and file-dialog calls go through the class instead;
    the cases above run each of them.
    """

    def test_slots_do_not_inherit_the_image_engine(self):
        self.assertFalse(issubclass(PackerSlots, ImgUtils))
        self.assertFalse(hasattr(PackerSlots, "pack_channels"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
