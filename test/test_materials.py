#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.materials, driving the real ``mtk`` in Maya.

The one Materials Slots class reaches its host only through ``self.tk``; here that is
mayatk, in a fresh Maya (``run_tests.py --in-maya``). The operations themselves are
tested in mayatk (``test_mat_utils.py`` TestNamedMaterialOperations) and blendertk; what
is pinned here is the panel's use of them in a real scene.

Remove Duplicate Materials (``b014``) once handed the finder's ``{kept: [duplicates]}``
to ``MatUtils.reassign_duplicate_materials`` as the materials to scan: the merge saw
only the kept ones, found nothing duplicated among them, and merged nothing.
"""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import pythontk as ptk

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.materials import MaterialsSlots

cmds = maya_module("maya.cmds")
mtk = maya_module("mayatk")


class _MayaCase(unittest.TestCase):
    """The composed class over the real ``mtk``, with no panel window: the
    table's refills are skipped, the messages recorded."""

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        cmds.file(new=True, force=True)
        self.sb = mock.MagicMock()
        self.sb.tk = mtk
        self.slots = MaterialsSlots(self.sb)
        self.slots.ui = SimpleNamespace()
        self.slots._refresh_material_lists = lambda *a, **k: None

    def tearDown(self):
        cmds.file(new=True, force=True)

    def message(self):
        return self.sb.message_box.call_args.args[0]


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestRemoveDuplicateMaterials(_MayaCase):
    """b014 merges every duplicate and reports what went; a baked pair needs no
    lightmap step after."""

    def setUp(self):
        super().setUp()
        store = ptk.TempArtifacts.scoped("tentacle_dup_mats")
        self.addCleanup(store.cleanup, force=True)
        tex = os.path.join(store.dir_path(), "Crate_BaseColor.png").replace("\\", "/")
        with open(tex, "wb") as fh:
            fh.write(b"crate")
        self.cubes = []
        for name in ("dupA", "dupB"):
            cube = cmds.polyCube(name=name)[0]
            mat = cmds.shadingNode("lambert", asShader=True, name=f"{name}_mat")
            node = cmds.shadingNode("file", asTexture=True, name=f"{name}_file")
            cmds.setAttr(f"{node}.fileTextureName", tex, type="string")
            cmds.connectAttr(f"{node}.outColor", f"{mat}.color")
            mtk.MatUtils.assign_mat(cube, mat)
            self.cubes.append(cube)

    def test_b014_merges_every_duplicate(self):
        self.slots.b014()
        mats = {str(m) for cube in self.cubes for m in mtk.MatUtils.get_mats(cube)}
        self.assertEqual(len(mats), 1, mats)
        self.assertEqual(
            len([m for m in ("dupA_mat", "dupB_mat") if cmds.objExists(m)]), 1
        )
        self.assertIn("Removed <hl>1</hl> duplicate material.", self.message())
        self.assertNotIn("lightmap", self.message().lower(), "nothing here is baked")

    def test_b014_on_a_baked_pair_asks_for_no_lightmap_step(self):
        """The Lightmap Baker groups a duplicate's atlas with the one it
        duplicates, so merging the pair splits nothing: no re-pack to ask for.
        Changed: 2026-10-22 (was a "re-bake to pack the pair" note)."""
        store = ptk.TempArtifacts.scoped("tentacle_dup_maps")
        self.addCleanup(store.cleanup, force=True)
        mapping = {}
        for cube in self.cubes:
            mtk.UvUtils.create_lightmap_uvs([cube], map_size=64, quiet=True)
            long = cmds.ls(cube, long=True)[0]
            mapping[long] = os.path.join(store.dir_path(), f"{cube}_Lightmap.exr")
            open(mapping[long], "wb").close()
        mtk.LightmapBaker(resolution=64).commit_lightmap(mapping)
        self.slots.b014()
        self.assertEqual(self.message(), "Removed <hl>1</hl> duplicate material.")
        self.assertEqual(mtk.LightmapBaker(resolution=64).stale_report().repack, {})

    def test_b014_reports_what_it_merged_not_what_it_found(self):
        """An original with no shading engine: the merge skips the pair, so
        nothing was removed and the report says so.
        Added: 2026-10-24 (it reported the finder's count: 1)."""
        for mat in ("dupA_mat", "dupB_mat"):
            cmds.delete(sorted(set(cmds.listConnections(mat, type="shadingEngine"))))
        self.slots.b014()
        self.assertTrue(cmds.objExists("dupA_mat") and cmds.objExists("dupB_mat"))
        self.assertEqual(self.message(), "Removed <hl>0</hl> duplicate materials.")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTheMaterialTableInMaya(_MayaCase):
    """What the panel's material table reads and does in a real scene: one
    material fine, its duplicate, one unused, one missing its texture.
    Added: 2026-10-22"""

    def setUp(self):
        super().setUp()
        store = ptk.TempArtifacts.scoped("tentacle_mat_table")
        self.addCleanup(store.cleanup, force=True)
        tex = os.path.join(store.dir_path(), "Crate_BaseColor.png").replace("\\", "/")
        with open(tex, "wb") as fh:
            fh.write(b"crate")
        gone = os.path.join(store.dir_path(), "gone", "Wood_BaseColor.png").replace("\\", "/")
        for name, path in (("crateA", tex), ("crateB", tex), ("wood", gone)):
            cube = cmds.polyCube(name=f"{name}_geo")[0]
            mat = cmds.shadingNode("lambert", asShader=True, name=f"{name}_mat")
            node = cmds.shadingNode("file", asTexture=True, name=f"{name}_file")
            cmds.setAttr(f"{node}.fileTextureName", path, type="string")
            cmds.connectAttr(f"{node}.outColor", f"{mat}.color")
            mtk.MatUtils.assign_mat(cube, mat)
        cmds.shadingNode("lambert", asShader=True, name="old_mat")
        cmds.select(clear=True)

    def test_each_material_is_a_row(self):
        names = {row["name"] for row in self.slots._material_rows()}
        self.assertLessEqual({"crateA_mat", "crateB_mat", "wood_mat", "old_mat"}, names)

    def test_the_details_flag_what_needs_attention(self):
        names = ["crateA_mat", "crateB_mat", "wood_mat", "old_mat", "lambert1"]
        details = self.slots._material_details(names)
        issues = {name: (details[name]["issue"] or ("",))[0] for name in names}
        self.assertEqual(
            {k: v for k, v in issues.items() if v},
            {"crateB_mat": "duplicate", "wood_mat": "missing", "old_mat": "unused"},
            "a default material (lambert1) is never unused",
        )
        self.assertEqual(details["crateB_mat"]["issue"][2], "crateA_mat")
        self.assertIn("Wood_BaseColor.png", details["wood_mat"]["issue"][1])
        self.assertEqual(
            (details["crateA_mat"]["users"], details["crateA_mat"]["textures"]), (1, 1)
        )
        self.assertEqual(details["crateA_mat"]["type"], "lambert")

    def test_a_material_inside_an_assigned_layered_network_is_in_use(self):
        """A lambert feeding an assigned layeredShader is used (Maya's Delete
        Unused keeps it): flagged unused, its click deleted it and broke the
        network. Added: 2026-10-24 (only a directly connected shading engine
        counted)."""
        cube = cmds.polyCube(name="layered_geo")[0]
        layer = cmds.shadingNode("lambert", asShader=True, name="layer_mat")
        layered = cmds.shadingNode("layeredShader", asShader=True, name="layered_mat")
        cmds.connectAttr(f"{layer}.outColor", f"{layered}.inputs[0].color")
        mtk.MatUtils.assign_mat(cube, layered)
        details = self.slots._material_details(["layer_mat", "layered_mat", "old_mat"])
        self.assertIsNone(details["layer_mat"]["issue"])
        self.assertEqual(details["layer_mat"]["users"], 1)
        self.assertIsNone(details["layered_mat"]["issue"])
        self.assertEqual(details["old_mat"]["issue"][0], "unused", "still caught")

    def test_a_duplicates_status_merges_it_into_its_original(self):
        self.slots._merge_and_report({"crateB_mat": "crateA_mat"})
        self.assertFalse(cmds.objExists("crateB_mat"))
        self.assertEqual(
            [str(m) for m in mtk.MatUtils.get_mats("crateB_geo")], ["crateA_mat"]
        )

    def test_delete_is_one_undo(self):
        cmds.undoInfo(state=True)
        self.slots._delete_and_report(["old_mat", "wood_mat"])
        self.assertFalse(cmds.objExists("old_mat") or cmds.objExists("wood_mat"))
        cmds.undo()
        self.assertTrue(cmds.objExists("old_mat") and cmds.objExists("wood_mat"))

    def test_an_assign_is_one_undo(self):
        cmds.undoInfo(state=True)
        cmds.select("wood_geo")
        self.slots._assign_named("old_mat")
        self.assertEqual(mtk.MatUtils.get_mat_names(["wood_geo"]), ["old_mat"])
        self.assertEqual(self.slots._current_mat(), "old_mat")
        cmds.undo()
        self.assertEqual(mtk.MatUtils.get_mat_names(["wood_geo"]), ["wood_mat"])

    def test_assigning_a_material_gone_meanwhile_makes_none(self):
        cmds.select("wood_geo")
        self.slots._assign_named("gone_mat")
        self.assertFalse(cmds.objExists("gone_mat"))
        self.assertIn("no longer exists", self.message())

    def test_rename_acts_on_the_current_material(self):
        self.slots._current = "old_mat"
        self.assertEqual(self.slots._rename_current("retired_mat"), "retired_mat")
        self.assertTrue(cmds.objExists("retired_mat"))
        self.assertEqual(self.slots._current_mat(), "retired_mat")

    def test_select_users_of_the_current_material(self):
        self.slots._current = "wood_mat"
        self.slots.select_by_mat(shell=True)
        self.assertEqual(cmds.ls(sl=True), ["wood_geo"])

    def test_the_selections_materials(self):
        cmds.select("crateA_geo", "wood_geo")
        self.assertEqual(sorted(self.slots._selected_mat_names()), ["crateA_mat", "wood_mat"])

    def test_a_random_material_replaces_the_last_one(self):
        cmds.select("wood_geo")
        self.slots.b004()
        first = self.slots._current_mat()
        self.slots.b004()
        second = self.slots._current_mat()
        self.assertFalse(cmds.objExists(first), "nothing used it any more")
        self.assertEqual(mtk.MatUtils.get_mat_names(["wood_geo"]), [second])
        self.assertEqual(cmds.ls(sl=True), ["wood_geo"], "the selection is kept")


if __name__ == "__main__":
    unittest.main()
