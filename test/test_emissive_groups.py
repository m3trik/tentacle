# !/usr/bin/python
# coding=utf-8
"""The Emissive Groups tool's Maya half (``tools/emissive_groups/maya.py``) over
its model, in a fresh Maya (``run_tests.py --in-maya``).

Covers the scene-data contract (objectSet membership + data_internal registry
+ data_export manifest), slot stability/retirement, both bake encodings,
validation, keyable weights and the FBX round trip of the color set and the
weight curves. The model alone is ``test_emissive_groups_model.py``.
"""

import json
import os
import shutil
import tempfile
import unittest

import pythontk as ptk

from _host import MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
_maya_half = maya_module("tentacle.tools.emissive_groups.maya")
EmissiveGroups = _maya_half.EmissiveGroups if _maya_half else None
DataNodes = maya_module("mayatk").DataNodes if MAYA_AVAILABLE else None


@unittest.skipUnless(MAYA_AVAILABLE, "runs in a fresh Maya (--in-maya)")
class _GroupsCase(unittest.TestCase):
    """Shared fixture: a cube with two face groups."""

    def setUp(self):
        cmds.file(new=True, force=True)  # drops the data nodes with the scene
        self.cube = cmds.polyCube(name="eg_cube")[0]

    def _add_two(self):
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        EmissiveGroups.add_group("top", [f"{self.cube}.f[1]", f"{self.cube}.f[3]"])


class TestAuthoring(_GroupsCase):
    def test_add_creates_set_and_registry(self):
        node = EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        self.assertTrue(cmds.objExists(node))
        self.assertEqual(node, "emissiveGroup_front")
        groups = EmissiveGroups.list_groups()
        self.assertEqual(groups["front"]["slot"], 0)
        self.assertEqual(groups["front"]["faces"], 1)

    def test_add_from_selection(self):
        cmds.select(f"{self.cube}.f[2]", replace=True)
        EmissiveGroups.add_group("sel")
        self.assertEqual(EmissiveGroups.list_groups()["sel"]["faces"], 1)

    def test_add_whole_mesh_converts_to_faces(self):
        EmissiveGroups.add_group("all", [self.cube])
        self.assertEqual(EmissiveGroups.list_groups()["all"]["faces"], 6)

    def test_extend_existing_group(self):
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        EmissiveGroups.add_group("front", [f"{self.cube}.f[2]"])
        groups = EmissiveGroups.list_groups()
        self.assertEqual(groups["front"]["faces"], 2)
        self.assertEqual(groups["front"]["slot"], 0)  # slot unchanged

    def test_invalid_name_rejected(self):
        with self.assertRaises(ValueError):
            EmissiveGroups.add_group("1bad", [f"{self.cube}.f[0]"])

    def test_no_faces_rejected(self):
        cmds.select(clear=True)
        with self.assertRaises(ValueError):
            EmissiveGroups.add_group("empty")

    def test_select_group(self):
        self._add_two()
        EmissiveGroups.select_group("top")
        sel = cmds.filterExpand(cmds.ls(sl=True), sm=34, expand=True)
        self.assertEqual(len(sel), 2)

    def test_set_default(self):
        self._add_two()
        EmissiveGroups.set_default("front", 0.25)
        self.assertEqual(EmissiveGroups.list_groups()["front"]["default"], 0.25)


class TestCarrierMerge(_GroupsCase):
    """Another scene's member sets joining this scene's on a reference merge."""

    def test_an_empty_foreign_set_never_joins_the_selection_to_the_group(self):
        """``sets -add`` given no members falls back to the live selection --
        a reference merge from the panel runs with one. Added: 2026-09-19"""
        import pythontk as ptk

        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        canonical = EmissiveGroups._store("front")
        stray = cmds.sets(empty=True, name=f"{canonical}1")
        bystander = cmds.polySphere(name="eg_bystander")[0]
        cmds.select(bystander)

        other = {ptk.SceneRecords.EMISSIVE_REGISTRY: {"groups": {"front": {"slot": 0}}}}
        ctx = ptk.TransferContext(rename={canonical: stray}.get)
        EmissiveGroups.merge_carrier({}, other, ctx)

        members = cmds.sets(canonical, q=True) or []
        self.assertFalse(
            any(bystander in m for m in members),
            f"selection joined the group: {members}",
        )
        self.assertFalse(cmds.objExists(stray))


class TestSlotStability(_GroupsCase):
    def test_removed_slot_is_retired_not_reused(self):
        self._add_two()  # front=0, top=1
        EmissiveGroups.remove_group("front")
        EmissiveGroups.add_group("new", [f"{self.cube}.f[4]"])
        self.assertEqual(EmissiveGroups.list_groups()["new"]["slot"], 2)

    def test_compact_reclaims_retired(self):
        self._add_two()
        EmissiveGroups.remove_group("front")
        reclaimed = EmissiveGroups.compact_slots()
        self.assertEqual(reclaimed, [0])
        EmissiveGroups.add_group("new", [f"{self.cube}.f[4]"])
        self.assertEqual(EmissiveGroups.list_groups()["new"]["slot"], 0)

    def test_slot_exhaustion_raises(self):
        for i in range(4):
            EmissiveGroups.add_group(f"g{i}", [f"{self.cube}.f[{i}]"])
        with self.assertRaises(ValueError):
            EmissiveGroups.add_group("overflow", [f"{self.cube}.f[5]"])


class TestSceneDataHygiene(_GroupsCase):
    def test_no_registry_channel_until_used(self):
        self.assertIsNone(ptk.SceneRecords.EMISSIVE_REGISTRY.read_text(DataNodes))

    def test_registry_cleared_when_last_group_and_retired_gone(self):
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        self.assertIsNotNone(ptk.SceneRecords.EMISSIVE_REGISTRY.read_text(DataNodes))
        EmissiveGroups.remove_group("front")
        EmissiveGroups.compact_slots()
        self.assertIsNone(ptk.SceneRecords.EMISSIVE_REGISTRY.read_text(DataNodes))

    def test_authoring_does_not_create_the_export_carrier(self):
        """Adding / editing / removing groups must not stamp a data_export
        node into a scene that has never been baked or exported — the export
        preparer regenerates the manifest anyway, so creating it early is
        pure clutter."""
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        EmissiveGroups.add_group("top", [f"{self.cube}.f[1]"])
        EmissiveGroups.set_default("front", 0.5)
        EmissiveGroups.remove_group("top")
        self.assertFalse(cmds.objExists(DataNodes.EXPORT))

    def test_authoring_keeps_an_already_published_manifest_current(self):
        """Once a manifest exists, staleness WOULD ship — so it is updated."""
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        EmissiveGroups.refresh_export_metadata()  # explicit publish
        EmissiveGroups.add_group("top", [f"{self.cube}.f[1]"])
        payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertEqual([g["name"] for g in payload["groups"]], ["front", "top"])
        EmissiveGroups.set_default("front", 0.25)
        payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertEqual(payload["groups"][0]["default"], 0.25)

    def test_export_channel_cleared_without_groups(self):
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        EmissiveGroups.refresh_export_metadata()
        self.assertIsNotNone(ptk.SceneRecords.EMISSIVE_GROUPS.read_text(DataNodes))
        EmissiveGroups.remove_group("front")
        self.assertIsNone(ptk.SceneRecords.EMISSIVE_GROUPS.read_text(DataNodes))


class TestExportManifest(_GroupsCase):
    def test_vertex_color_manifest_shape(self):
        self._add_two()
        payload = EmissiveGroups.refresh_export_metadata()
        data = json.loads(payload)
        self.assertEqual(data["version"], ptk.SceneRecords.EMISSIVE_GROUPS.version)
        self.assertNotIn("schema", data)
        self.assertEqual(data["encoding"], "vertex-color")
        self.assertEqual(data["color_set"], "emissiveGroups")
        self.assertEqual(
            [(g["name"], g["slot"]) for g in data["groups"]],
            [("front", 0), ("top", 1)],
        )
        # Round-trips through the shared engine model.
        manifest = ptk.RegionMaskManifest.from_json(payload)
        self.assertEqual(len(manifest.groups), 2)


class TestVertexColorBake(_GroupsCase):
    def test_bake_writes_membership_channels(self):
        self._add_two()
        manifest = EmissiveGroups.bake_vertex_colors()
        self.assertEqual(manifest["encoding"], "vertex-color")
        sets = cmds.polyColorSet(self.cube, q=True, allColorSets=True)
        self.assertIn(EmissiveGroups.COLOR_SET, sets)
        # front (slot 0) faces: R=1; top (slot 1) faces: G=1; others zero.
        r = cmds.polyColorPerVertex(f"{self.cube}.f[0]", q=True, r=True)
        g = cmds.polyColorPerVertex(f"{self.cube}.f[0]", q=True, g=True)
        self.assertTrue(all(v == 1.0 for v in r))
        self.assertTrue(all(v == 0.0 for v in g))
        g_top = cmds.polyColorPerVertex(f"{self.cube}.f[1]", q=True, g=True)
        self.assertTrue(all(v == 1.0 for v in g_top))
        r_other = cmds.polyColorPerVertex(f"{self.cube}.f[5]", q=True, r=True)
        g_other = cmds.polyColorPerVertex(f"{self.cube}.f[5]", q=True, g=True)
        self.assertTrue(all(v == 0.0 for v in r_other + g_other))

    def test_rebake_clears_stale_membership(self):
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        EmissiveGroups.bake_vertex_colors()
        # Move membership to another face and re-bake: old face must zero out.
        EmissiveGroups.remove_group("front")
        EmissiveGroups.add_group("front2", [f"{self.cube}.f[2]"])
        EmissiveGroups.bake_vertex_colors()
        r_old = cmds.polyColorPerVertex(f"{self.cube}.f[0]", q=True, r=True)
        self.assertTrue(all(v == 0.0 for v in r_old))

    def test_overlapping_groups_accumulate_channels(self):
        EmissiveGroups.add_group("a", [f"{self.cube}.f[0]"])
        EmissiveGroups.add_group("b", [f"{self.cube}.f[0]"])
        EmissiveGroups.bake_vertex_colors()
        r = cmds.polyColorPerVertex(f"{self.cube}.f[0]", q=True, r=True)
        g = cmds.polyColorPerVertex(f"{self.cube}.f[0]", q=True, g=True)
        self.assertTrue(all(v == 1.0 for v in r))
        self.assertTrue(all(v == 1.0 for v in g))

    def test_foreign_color_set_refused_without_force(self):
        cmds.polyColorSet(
            self.cube, create=True, colorSet="paintjob", representation="RGBA"
        )
        EmissiveGroups.add_group("front", [f"{self.cube}.f[0]"])
        with self.assertRaises(ValueError):
            EmissiveGroups.bake_vertex_colors()
        manifest = EmissiveGroups.bake_vertex_colors(force=True)
        self.assertEqual(manifest["encoding"], "vertex-color")

    def test_no_groups_raises(self):
        with self.assertRaises(ValueError):
            EmissiveGroups.bake_vertex_colors()


class TestMaskBake(_GroupsCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def test_bake_mask_writes_texture_and_manifest(self):
        self._add_two()
        mask_path = os.path.join(self.tmp, "eg_EMask.png")
        manifest = EmissiveGroups.bake_mask(output_path=mask_path, resolution=64)
        self.assertTrue(os.path.isfile(mask_path))
        # The manifest is published through the scene records, never as a
        # sidecar in the texture folder (pythontk RegionMaskPacker.write).
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "eg_EMask.json")))
        self.assertEqual(manifest["encoding"], "channels")
        self.assertEqual(manifest["mask"], "eg_EMask.png")
        # The mask states its own size; the manifest no longer repeats it
        # (2026-10-20).
        self.assertNotIn("resolution", manifest)
        # Both groups rasterized coverage into their slot channels.
        import numpy as np
        from PIL import Image

        with Image.open(mask_path) as im:
            arr = np.asarray(im)
        self.assertEqual(arr.shape, (64, 64, 4))
        self.assertGreater((arr[..., 0] > 0).sum(), 0)  # front / slot 0
        self.assertGreater((arr[..., 1] > 0).sum(), 0)  # top / slot 1
        # Export carrier now carries the channels manifest.
        payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertEqual(payload["encoding"], "channels")

    def test_default_mask_lands_in_the_scenes_project_texture_folder(self):
        """No path: ``<scene project texture folder>/<scene>_EMask.png`` -- the
        project the scene is saved in, not merely the active one (the same
        folder blendertk writes for a file in that project). Added:
        2026-10-13"""
        self._add_two()
        root = os.path.realpath(self.tmp)
        ptk.Workspace.create(root, create_dirs=False)
        os.makedirs(os.path.join(root, "scenes"))
        cmds.file(rename=os.path.join(root, "scenes", "eg_scene.ma"))
        self.assertNotEqual(
            os.path.normcase(os.path.normpath(cmds.workspace(q=True, rd=True))),
            os.path.normcase(root),
        )
        EmissiveGroups.bake_mask(resolution=32)
        mask = os.path.join(root, "sourceimages", "eg_scene_EMask.png")
        self.assertTrue(os.path.isfile(mask), os.listdir(root))
        self.assertFalse(os.path.exists(os.path.splitext(mask)[0] + ".json"))

    def test_a_default_path_bake_stays_in_the_runs_sandbox(self):
        """The panel's button names no path: the mask goes to the current
        project's sourceimages. Under the test runner that project must be the
        run's sandbox -- a GUI-pass Maya restores the project the user last had
        open, and this fixture's `untitled_EMask.png` was found in a production
        project's sourceimages (2026-10-01)."""
        from pythontk.core_utils.test_sandbox import TestSandbox

        if not TestSandbox.is_active():
            self.skipTest("run outside the suite driver: no sandbox to stay in")
        self._add_two()
        EmissiveGroups.bake_mask(resolution=64)
        root = cmds.workspace(q=True, rootDirectory=True)
        rule = cmds.workspace(fileRuleEntry="sourceImages") or "sourceimages"
        written = os.path.normcase(
            os.path.realpath(os.path.join(root, rule, "untitled_EMask.png"))
        )
        sandbox = os.path.normcase(os.path.realpath(TestSandbox.temp()))
        self.assertTrue(os.path.isfile(written), written)
        self.assertTrue(
            written.startswith(sandbox), f"wrote into a real project: {written}"
        )


class TestFbxRoundTrip(_GroupsCase):
    """The two assumptions the whole Unity hand-off rests on.

    Neither is knowable from the Maya-side state alone: that the color set
    survives an FBX export→import with its per-channel values intact, and
    that the manifest rides along as a ``data_export`` user property (what
    unitytk's ``EmissiveGroupImporter`` reads).
    """

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        cmds.loadPlugin("fbxmaya", quiet=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def test_color_set_and_manifest_survive_fbx(self):
        import maya.mel as mel

        self._add_two()
        EmissiveGroups.bake_vertex_colors()
        path = os.path.join(self.tmp, "eg_roundtrip.fbx").replace("\\", "/")
        mel.eval("FBXResetExport")
        mel.eval(f'FBXExport -f "{path}"')
        self.assertTrue(os.path.isfile(path))

        cmds.file(new=True, force=True)
        cmds.file(path, i=True, type="FBX", ignoreVersion=True)

        mesh = "eg_cube"
        self.assertTrue(cmds.objExists(mesh))
        self.assertIn(
            EmissiveGroups.COLOR_SET,
            cmds.polyColorSet(mesh, q=True, allColorSets=True) or [],
        )
        cmds.polyColorSet(mesh, currentColorSet=True, colorSet=EmissiveGroups.COLOR_SET)
        # front = slot 0 (R), top = slot 1 (G), face 5 in neither.
        self.assertTrue(
            all(
                v > 0.99
                for v in cmds.polyColorPerVertex(f"{mesh}.f[0]", q=True, r=True)
            )
        )
        self.assertTrue(
            all(
                v < 0.01
                for v in cmds.polyColorPerVertex(f"{mesh}.f[0]", q=True, g=True)
            )
        )
        self.assertTrue(
            all(
                v > 0.99
                for v in cmds.polyColorPerVertex(f"{mesh}.f[1]", q=True, g=True)
            )
        )
        self.assertTrue(
            all(
                v < 0.01
                for v in cmds.polyColorPerVertex(f"{mesh}.f[5]", q=True, r=True)
            )
        )

        payload = ptk.SceneRecords.EMISSIVE_GROUPS.read_text(DataNodes)
        self.assertIsNotNone(payload)
        data = json.loads(payload)
        self.assertEqual(data["encoding"], "vertex-color")
        self.assertEqual([g["name"] for g in data["groups"]], ["front", "top"])

    def test_keyed_weight_curves_survive_fbx(self):
        """The keyable-weights hand-off: keyed carrier attrs must round-trip
        as animated custom properties (what Unity flattens to root curves and
        the importer rebinds to the controller)."""
        import maya.mel as mel

        self._add_two()
        EmissiveGroups.bake_vertex_colors()
        EmissiveGroups.key_weight("front", value=1.0, frame=1)
        EmissiveGroups.key_weight("front", value=0.0, frame=10)
        path = os.path.join(self.tmp, "eg_keyed.fbx").replace("\\", "/")
        mel.eval("FBXResetExport")
        mel.eval(f'FBXExport -f "{path}"')

        cmds.file(new=True, force=True)
        cmds.file(path, i=True, type="FBX", ignoreVersion=True)

        plug = f"{DataNodes.EXPORT}.emissiveGroup_front"
        self.assertTrue(
            cmds.attributeQuery(
                "emissiveGroup_front", node=DataNodes.EXPORT, exists=True
            )
        )
        self.assertEqual(cmds.keyframe(plug, q=True, keyframeCount=True), 2)
        values = cmds.keyframe(plug, q=True, valueChange=True)
        self.assertAlmostEqual(values[0], 1.0, places=3)
        self.assertAlmostEqual(values[-1], 0.0, places=3)
        # The manifest names the attr, so the engine importer can find it.
        data = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertEqual(data["groups"][0]["attr"], "emissiveGroup_front")


class TestKeyableWeights(_GroupsCase):
    """The keyable-weights opt-in: 0-1 float attrs on the export carrier."""

    def test_make_weights_keyable_creates_attrs_and_publishes(self):
        self._add_two()
        plugs = EmissiveGroups.make_weights_keyable()
        self.assertEqual(
            sorted(plugs.values()),
            [
                "data_export.emissiveGroup_front",
                "data_export.emissiveGroup_top",
            ],
        )
        for plug in plugs.values():
            attr = plug.split(".", 1)[1]
            self.assertTrue(
                cmds.attributeQuery(attr, node=DataNodes.EXPORT, keyable=True)
            )
            self.assertEqual(
                cmds.attributeQuery(attr, node=DataNodes.EXPORT, range=True),
                [0.0, 1.0],
            )
        # Publishing is part of the opt-in; the manifest records each attr.
        payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertEqual(
            [g["attr"] for g in payload["groups"]],
            ["emissiveGroup_front", "emissiveGroup_top"],
        )

    def test_keyable_is_the_explicit_carrier_opt_in(self):
        """Plain authoring still leaves no carrier; make_weights_keyable is
        the export-facing action that may create it."""
        self._add_two()
        self.assertFalse(cmds.objExists(DataNodes.EXPORT))
        EmissiveGroups.make_weights_keyable(["front"])
        self.assertTrue(cmds.objExists(DataNodes.EXPORT))
        groups = EmissiveGroups.list_groups()
        self.assertEqual(groups["front"]["attr"], "emissiveGroup_front")
        self.assertIsNone(groups["top"]["attr"])

    def test_unknown_group_rejected(self):
        self._add_two()
        with self.assertRaises(ValueError):
            EmissiveGroups.make_weights_keyable(["nope"])

    def test_key_weight_keys_the_carrier_attr(self):
        self._add_two()
        plug = EmissiveGroups.key_weight("front", value=1.0, frame=1)
        EmissiveGroups.key_weight("front", value=0.0, frame=10)
        self.assertEqual(cmds.keyframe(plug, q=True, keyframeCount=True), 2)
        self.assertEqual(cmds.keyframe(plug, q=True, valueChange=True), [1.0, 0.0])
        # Auto-keyable made the group keyable on first use.
        self.assertEqual(
            EmissiveGroups.list_groups()["front"]["attr"], "emissiveGroup_front"
        )
        with self.assertRaises(ValueError):
            EmissiveGroups.key_weight("top", value=1.0, auto_keyable=False)

    def test_set_default_follows_unkeyed_attr_only(self):
        self._add_two()
        EmissiveGroups.make_weights_keyable()
        plug = f"{DataNodes.EXPORT}.emissiveGroup_front"
        EmissiveGroups.set_default("front", 0.25)
        self.assertAlmostEqual(cmds.getAttr(plug), 0.25)
        EmissiveGroups.key_weight("front", value=1.0, frame=1)
        EmissiveGroups.set_default("front", 0.5)  # keyed: animation owns it
        self.assertAlmostEqual(cmds.getAttr(plug, time=1), 1.0)

    def test_remove_keyable_weights_strips_attrs_but_keeps_groups(self):
        self._add_two()
        EmissiveGroups.make_weights_keyable()
        EmissiveGroups.key_weight("front", value=0.0, frame=5)
        removed = EmissiveGroups.remove_keyable_weights()
        self.assertEqual(sorted(removed), ["front", "top"])
        self.assertFalse(
            cmds.attributeQuery(
                "emissiveGroup_front", node=DataNodes.EXPORT, exists=True
            )
        )
        groups = EmissiveGroups.list_groups()
        self.assertEqual(sorted(groups), ["front", "top"])  # groups intact
        self.assertIsNone(groups["front"]["attr"])
        payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
        self.assertNotIn("attr", payload["groups"][0])

    def test_set_default_skips_a_connection_driven_attr(self):
        """ANY incoming connection owns the value — an expression-driven
        weight must not make set_default raise (setAttr on a connected plug
        does) or be clobbered."""
        self._add_two()
        EmissiveGroups.make_weights_keyable(["front"])
        plug = f"{DataNodes.EXPORT}.emissiveGroup_front"
        cmds.expression(string=f"{plug} = 0.5;")
        EmissiveGroups.set_default("front", 0.9)  # must not raise
        self.assertEqual(EmissiveGroups.list_groups()["front"]["default"], 0.9)

    def test_make_weights_keyable_relinks_a_non_keyable_attr(self):
        """An FBX reimport can restore the carrier attr non-keyable; the
        relink must make it keyable again."""
        self._add_two()
        DataNodes.ensure_export()
        cmds.addAttr(
            DataNodes.EXPORT,
            longName="emissiveGroup_front",
            attributeType="float",
            keyable=False,
        )
        EmissiveGroups.make_weights_keyable(["front"])
        # Plug state, not attributeQuery — the latter reads the attribute
        # DEFINITION (still non-keyable); setAttr edits the plug, which is
        # what the channel box and setKeyframe honor.
        self.assertTrue(
            cmds.getAttr(f"{DataNodes.EXPORT}.emissiveGroup_front", keyable=True)
        )

    def test_remove_group_removes_its_keyable_attr(self):
        self._add_two()
        EmissiveGroups.make_weights_keyable()
        EmissiveGroups.key_weight("front", value=0.0, frame=5)
        EmissiveGroups.remove_group("front")
        self.assertFalse(
            cmds.attributeQuery(
                "emissiveGroup_front", node=DataNodes.EXPORT, exists=True
            )
        )


class TestValidate(_GroupsCase):
    def test_clean(self):
        self._add_two()
        self.assertEqual(EmissiveGroups.validate(), [])

    def test_warns_on_empty_overlap_orphan_and_foreign(self):
        self._add_two()
        # Overlap:
        EmissiveGroups.add_group("front", [f"{self.cube}.f[1]"])  # overlaps 'top'
        # Orphan set:
        cmds.sets(name="emissiveGroup_orphan", empty=True)
        # Foreign color set:
        cmds.polyColorSet(
            self.cube, create=True, colorSet="paintjob", representation="RGBA"
        )
        warnings = EmissiveGroups.validate()
        text = "\n".join(warnings)
        self.assertIn("overlaps", text)
        self.assertIn("orphan", text)
        self.assertIn("paintjob", text)

    def test_warns_on_orphan_carrier_attr(self):
        """An FBX REimport restores the carrier's keyable attrs but not the
        registry (data_internal never rides the FBX) — validate must flag it."""
        self._add_two()
        DataNodes.ensure_export()
        cmds.addAttr(
            DataNodes.EXPORT, longName="emissiveGroup_ghost", attributeType="float"
        )
        text = "\n".join(EmissiveGroups.validate())
        self.assertIn("emissiveGroup_ghost", text)
        self.assertIn("no registry entry", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
