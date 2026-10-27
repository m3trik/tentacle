#!/usr/bin/python
# coding=utf-8
"""The Emissive Groups model, host-free: an in-memory host stands in for Maya
and Blender (the halves are tested in each: ``test_emissive_groups.py`` in a
fresh Maya, ``blender/emissive_groups_check.py`` in a fresh Blender).
"""

import json
import unittest
from typing import Any, Dict

import pythontk as ptk
from pythontk.core_utils.engines.scene_export.scene_store import SceneStoreBase
from pythontk.core_utils.engines.scene_export.scene_records import Scope

from tentacle.tools.emissive_groups.model.emissive_groups_model import (
    EmissiveGroupsModel,
)


class _Store(SceneStoreBase):
    """One dict per scope (pythontk's ``DictStore`` test double)."""

    data: Dict[Scope, Dict[str, Any]] = {}

    @classmethod
    def read(cls, scope, key):
        value = cls.data.get(Scope(scope), {}).get(key)
        return value if isinstance(value, str) and value else None

    @classmethod
    def write(cls, scope, key, text):
        scope = Scope(scope)
        if not text:
            group = cls.data.get(scope)
            if group is None or key not in group:
                return None
            group[key] = ""
            return cls.name(scope)
        cls.data.setdefault(scope, {})[key] = text
        return cls.name(scope)

    @classmethod
    def values(cls, scope):
        return dict(cls.data.get(Scope(scope), {}))


class _Host:
    """An in-memory scene: meshes with face counts, membership stores, the
    carrier's weights and their keys, color sets, a selection."""

    data_nodes = _Store

    def __init__(self, meshes=None):
        self.meshes = dict(meshes or {"cube": 6, "ball": 8})
        self.stores: Dict[str, Dict[str, set]] = {}
        self.weights: Dict[str, float] = {}
        self.keys = []
        self.colors: Dict[str, Dict[str, dict]] = {}
        self.foreign: Dict[str, list] = {}
        self.selection = {}
        self.published = []
        self.merged = []

    def faces(self, faces=None):
        source = self.selection if faces is None else faces
        return {o: list(i) or list(range(self.meshes[o])) for o, i in source.items() if o in self.meshes}

    def add_members(self, store, face_map):
        group = self.stores.setdefault(store, {})
        for obj, indices in face_map.items():
            group.setdefault(obj, set()).update(indices)

    def remove_members(self, store):
        self.stores.pop(store, None)

    def members(self, store):
        if store not in self.stores:
            return None
        return {o: sorted(i) for o, i in self.stores[store].items() if i}

    def select(self, face_map):
        self.selection = dict(face_map)

    def membership_stores(self, prefix):
        return [(f"Store {s!r}", s[len(prefix):]) for s in self.stores if s.startswith(prefix)]

    def carrier_weights(self, prefix):
        return [w for w in self.weights if w.startswith(prefix)]

    def weight_exists(self, attr):
        return attr in self.weights

    def ensure_weight(self, attr, default):
        self.weights.setdefault(attr, default)
        return f"carrier.{attr}"

    def delete_weight(self, attr):
        return self.weights.pop(attr, None) is not None

    def sync_weight(self, attr, value):
        if attr in self.weights and not any(k[0] == attr for k in self.keys):
            self.weights[attr] = value

    def key_weight(self, attr, value, frame):
        self.keys.append((attr, value, frame))
        return f"carrier.{attr}"

    def foreign_color_sets(self, objects, color_set):
        return {o: self.foreign[o] for o in objects if self.foreign.get(o)}

    def write_colors(self, obj, channels, color_set):
        self.colors.setdefault(obj, {})[color_set] = {i: list(v) for i, v in channels.items()}

    def uv_triangles(self, obj, indices, uv_set):
        return [[(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)] for _ in indices]

    def mask_path(self, suffix):
        raise ValueError("no project")

    def object_names(self, objects):
        return [str(o) for o in objects]

    def face_count(self, obj):
        return self.meshes[obj]

    def mesh(self, name):
        return name if name in self.meshes else None

    def merge_stores(self, stores, ctx):
        self.merged.append(("merge", list(stores)))

    def discard_stores(self, stores, ctx):
        self.merged.append(("discard", list(stores)))

    def publish(self, records):
        self.published.append(records)
        for spec, record in records.items():
            spec.write_text(self.data_nodes, record.text if record is not None else None)

    def extra_warnings(self):
        return []


class _ModelCase(unittest.TestCase):
    def setUp(self):
        _Store.data = {}
        self.host = _Host()
        self.model = EmissiveGroupsModel(self.host)


class TestAuthoring(_ModelCase):
    def test_add_assigns_a_slot_and_extending_keeps_it(self):
        store = self.model.add_group("front", {"cube": [0]})
        self.assertEqual(store, "emissiveGroup_front")
        self.model.add_group("top", {"cube": [1, 3]})
        self.model.add_group("front", {"cube": [2]})
        groups = self.model.list_groups()
        self.assertEqual(groups["front"]["slot"], 0)
        self.assertEqual(groups["front"]["faces"], 2)
        self.assertEqual(groups["top"]["slot"], 1)

    def test_none_takes_the_selection_and_nothing_raises(self):
        self.host.selection = {"ball": [4]}
        self.model.add_group("sel")
        self.assertEqual(self.model.list_groups()["sel"]["faces"], 1)
        self.host.selection = {}
        with self.assertRaisesRegex(ValueError, "No faces"):
            self.model.add_group("none")

    def test_remove_retires_the_slot_until_compacted(self):
        self.model.add_group("a", {"cube": [0]})
        self.model.add_group("b", {"cube": [1]})
        self.model.make_weights_keyable(["a"])
        self.model.remove_group("a")
        self.assertNotIn("emissiveGroup_a", self.host.stores)
        self.assertNotIn("emissiveGroup_a", self.host.weights)
        self.model.add_group("c", {"cube": [2]})
        self.assertEqual(self.model.list_groups()["c"]["slot"], 2, "retired slot 0 is never reused")
        self.assertEqual(self.model.compact_slots(), [0])

    def test_a_vanished_store_reads_missing(self):
        self.model.add_group("a", {"cube": [0]})
        del self.host.stores["emissiveGroup_a"]
        self.assertTrue(self.model.list_groups()["a"]["missing"])
        with self.assertRaisesRegex(ValueError, "no members"):
            self.model.select_group("a")

    def test_select_hands_the_host_the_members(self):
        self.model.add_group("a", {"cube": [0, 2]})
        self.model.select_group("a")
        self.assertEqual(self.host.selection, {"cube": [0, 2]})


class TestWeights(_ModelCase):
    def test_keyable_weights_round_trip_through_the_manifest(self):
        self.model.add_group("a", {"cube": [0]}, default=0.5)
        plugs = self.model.make_weights_keyable()
        self.assertEqual(plugs, {"a": "carrier.emissiveGroup_a"})
        self.assertEqual(self.host.weights["emissiveGroup_a"], 0.5)
        manifest = json.loads(self.model.refresh_export_metadata())
        self.assertEqual(manifest["groups"][0]["attr"], "emissiveGroup_a")
        self.assertEqual(self.model.remove_keyable_weights(), ["a"])
        manifest = json.loads(self.model.refresh_export_metadata())
        self.assertIsNone(manifest["groups"][0].get("attr"))

    def test_key_weight_clamps_and_makes_keyable_on_demand(self):
        self.model.add_group("a", {"cube": [0]})
        self.model.key_weight("a", 3.0, frame=10)
        self.assertEqual(self.host.keys, [("emissiveGroup_a", 1.0, 10)])
        self.model.add_group("b", {"cube": [1]})
        with self.assertRaisesRegex(ValueError, "no keyable weight"):
            self.model.key_weight("b", auto_keyable=False)

    def test_an_unkeyed_weight_follows_the_default(self):
        self.model.add_group("a", {"cube": [0]})
        self.model.make_weights_keyable()
        self.model.set_default("a", 0.25)
        self.assertEqual(self.host.weights["emissiveGroup_a"], 0.25)

    def test_unknown_names_are_refused(self):
        self.model.add_group("a", {"cube": [0]})
        with self.assertRaisesRegex(ValueError, "Unknown group"):
            self.model.make_weights_keyable(["zz"])


class TestValidate(_ModelCase):
    def test_empty_missing_overlap_orphans_and_foreign_sets(self):
        self.model.add_group("top", {"cube": [1]})
        self.model.add_group("front", {"cube": [1]})  # overlaps 'top'
        self.model.add_group("gone", {"ball": [0]})
        del self.host.stores["emissiveGroup_gone"]
        self.host.stores["emissiveGroup_stray"] = {"cube": {5}}  # no registry entry
        self.host.weights["emissiveGroup_ghost"] = 1.0  # stale carrier weight
        self.host.foreign = {"cube": ["map1"]}
        text = "\n".join(self.model.validate())
        for expected in ("is missing", "overlaps 'top'", "'stray'", "'ghost'", "foreign color set 'map1'"):
            self.assertIn(expected, text)

    def test_a_clean_scene_warns_nothing(self):
        self.model.add_group("a", {"cube": [0]})
        self.assertEqual(self.model.validate(), [])


class TestBakes(_ModelCase):
    def test_vertex_colors_carry_each_group_in_its_slot_channel(self):
        self.model.add_group("a", {"cube": [0, 1]})
        self.model.add_group("b", {"cube": [1], "ball": [2]})
        manifest = self.model.bake_vertex_colors()
        self.assertEqual(manifest["encoding"], "vertex-color")
        cube = self.host.colors["cube"]["emissiveGroups"]
        self.assertEqual(cube[0], [1.0, 0.0, 0.0, 0.0])
        self.assertEqual(cube[1], [1.0, 1.0, 0.0, 0.0], "overlapping groups accumulate")
        self.assertEqual(self.host.colors["ball"]["emissiveGroups"], {2: [0.0, 1.0, 0.0, 0.0]})

    def test_a_foreign_color_set_is_refused_unless_forced(self):
        self.model.add_group("a", {"cube": [0]})
        self.host.foreign = {"cube": ["colorSet1"]}
        with self.assertRaisesRegex(ValueError, "Foreign color set"):
            self.model.bake_vertex_colors()
        self.assertEqual(self.model.bake_vertex_colors(force=True)["encoding"], "vertex-color")

    def test_nothing_to_bake_raises(self):
        with self.assertRaisesRegex(ValueError, "No emissive groups"):
            self.model.bake_vertex_colors()
        with self.assertRaisesRegex(ValueError, "no project"):
            self.model.add_group("a", {"cube": [0]})
            self.model.bake_mask()


class TestRecords(_ModelCase):
    def test_export_record_is_the_registry_manifest_and_writes_nothing(self):
        self.assertIsNone(self.model.export_record(ptk.ExportContext()))
        self.model.add_group("a", {"cube": [0]}, default=0.75)
        before = dict(_Store.data)
        record = self.model.export_record(ptk.ExportContext())
        self.assertEqual(_Store.data, before)
        payload = json.loads(record.text)
        self.assertEqual(payload["groups"][0]["name"], "a")
        self.assertEqual(payload["groups"][0]["default"], 0.75)

    def test_authoring_refreshes_a_published_manifest_only(self):
        self.model.add_group("a", {"cube": [0]})
        self.assertEqual(self.host.published, [], "never stamps a manifest unasked")
        self.model.refresh_export_metadata()
        self.model.add_group("b", {"cube": [1]})
        manifest = ptk.SceneRecords.EMISSIVE_GROUPS.load(_Store)
        self.assertEqual([g["name"] for g in manifest["groups"]], ["a", "b"])

    def test_a_crossing_restores_membership_where_the_face_count_held(self):
        self.model.add_group("a", {"cube": [0, 2], "ball": [1]})
        payload = self.model.transfer_out(ptk.TransferContext())
        self.assertEqual(payload["members"]["a"], {"cube": [0, 2], "ball": [1]})
        self.assertEqual(payload["faces"], {"cube": 6, "ball": 8})

        _Store.data = {}
        far = _Host(meshes={"cube": 6, "ball": 12})  # the ball's topology changed
        notes = []
        ctx = ptk.TransferContext()
        ctx.note = notes.append
        EmissiveGroupsModel(far).transfer_in(payload, ctx)
        self.assertEqual(far.members("emissiveGroup_a"), {"cube": [0, 2]})
        self.assertTrue(any("'ball' has 12 faces" in n for n in notes), notes)

    def test_carrier_merges_go_to_the_host_by_store_name(self):
        other = {ptk.SceneRecords.EMISSIVE_REGISTRY: {"groups": {"a": {}, "b": {}}}}
        self.model.merge_carrier({}, other, None)
        self.model.discard_carrier({}, other, None)
        self.assertEqual(
            self.host.merged,
            [
                ("merge", ["emissiveGroup_a", "emissiveGroup_b"]),
                ("discard", ["emissiveGroup_a", "emissiveGroup_b"]),
            ],
        )


if __name__ == "__main__":
    unittest.main()
