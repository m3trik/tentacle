# !/usr/bin/python
# coding=utf-8
"""Emissive groups: named face sets that gate emissive regions at runtime.

Author groups of faces ("headlights", "panel_leds") whose emissive texels a
game engine can toggle or dim independently while sharing one all-on
emissive map. The runtime gate is ``emissive * dot(mask, weights)``; this
tool authors the mask side. Two encodings (pythontk's region-mask engine is
the shared model, ``ptk.RegionGroupRegistry`` / ``ptk.RegionMaskPacker``):

- **vertex-color** (default): membership baked into the ``emissiveGroups``
  RGBA color set, one group per channel, written per face corner so group
  boundaries stay hard. No textures; rides the FBX. Claims the mesh's one
  Unity color channel and caps at 4 groups.
- **channels**: membership rasterized into an ``_EMask`` RGBA texture, for
  emissive detail painted sub-face or meshes whose color set is spoken for.

Scene data (nothing is created until the tool is used): membership is the
host's (Maya: one ``objectSet`` of faces per group; Blender: one boolean FACE
attribute per group, both named ``emissiveGroup_<name>``); the registry
(slots, defaults, encoding) is ``ptk.SceneRecords.EMISSIVE_REGISTRY`` on the
``data_internal`` carrier; the manifest is ``ptk.SceneRecords.EMISSIVE_GROUPS``
on ``data_export``, read by unitytk's ``EmissiveGroupController`` importer.
Slots are assigned once and never reshuffled: downstream Unity scenes key
against them. Removing a group *retires* its slot; :meth:`compact_slots` is
the explicit, binding-breaking reclaim.

This module is host-free: every scene read and write goes through the
adapter (:class:`~tentacle.tools.emissive_groups.adapter.EmissiveGroupsAdapter`),
which speaks membership as ``{object: [face index, ...]}``.

Constraints artists should know (also in the panel help): a face's group
membership tracks face *indices*, so topology edits can silently shift it;
mirrored or stacked UV shells share texels in the channels encoding, so such
groups toggle together; baked-GI bounce light does not react to runtime
toggles.
"""

import json
from typing import Dict, List, Optional

import pythontk as ptk

#: ``{object: [face index, ...]}``: membership as the model speaks it.
FaceMap = Dict[str, List[int]]


class _EmissiveGroupsModelInternal:
    """Implementation-detail base for :class:`EmissiveGroupsModel`."""

    SET_PREFIX = "emissiveGroup_"
    COLOR_SET = "emissiveGroups"
    #: The ``data_export`` manifest's channel; the ``data_internal`` registry
    #: keeps its own (``ptk.SceneRecords.EMISSIVE_REGISTRY``).
    DATA_CHANNEL = ptk.SceneRecords.EMISSIVE_GROUPS.key

    def _registry(self) -> "ptk.RegionGroupRegistry":
        nodes = self.adapter.data_nodes
        return ptk.RegionGroupRegistry(
            load=lambda: ptk.SceneRecords.EMISSIVE_REGISTRY.read_text(nodes),
            save=lambda text: ptk.SceneRecords.EMISSIVE_REGISTRY.write_text(
                nodes, text
            ),
            logger=self.logger,
        )

    def _store(self, name: str) -> str:
        """The membership store's (and weight attr's) name for group *name*."""
        return f"{self.SET_PREFIX}{name}"

    def _refresh_export_if_published(self) -> None:
        """Keep an already-published manifest current, never create one.

        Authoring must not stamp a ``data_export`` channel into a scene that
        has never been baked or exported: the export regenerates it anyway, so
        creating it early is scene clutter. Once one exists, leaving it stale
        would ship wrong data.
        """
        if ptk.SceneRecords.EMISSIVE_GROUPS.is_present(self.adapter.data_nodes):
            self.refresh_export_metadata()

    def _known(self) -> Dict[str, dict]:
        return {entry["name"]: entry for entry in self._registry().groups()}

    def _resolve_names(self, names, known) -> List[str]:
        names = list(known) if names is None else [str(n) for n in names]
        unknown = [n for n in names if n not in known]
        if unknown:
            raise ValueError(f"Unknown group(s): {unknown}.")
        return names

    def _member_objects(self, members: Dict[str, Optional[FaceMap]]) -> List[str]:
        objects: List[str] = []
        for face_map in members.values():
            for obj in face_map or {}:
                if obj not in objects:
                    objects.append(obj)
        return objects

    def _overlap_warnings(self, members: Dict[str, Optional[FaceMap]]) -> List[str]:
        warnings = []
        owner: Dict[tuple, str] = {}
        for name, face_map in members.items():
            reported = False
            for obj, indices in (face_map or {}).items():
                for index in indices:
                    key = (obj, index)
                    if key in owner and not reported:
                        warnings.append(
                            f"Group {name!r} overlaps {owner[key]!r} (e.g. {obj} "
                            f"face {index}); shared faces glow when either group "
                            "is on."
                        )
                        reported = True
                    owner.setdefault(key, name)
        return warnings

    def _orphan_warnings(self, known) -> List[str]:
        warnings = [
            f"{where} has no registry entry — re-add it with add_group({name!r}) "
            "to assign a slot."
            for where, name in self.adapter.membership_stores(self.SET_PREFIX)
            if name not in known
        ]
        # An FBX REimport restores the carrier's keyable weights but not the
        # registry (data_internal never rides the FBX).
        for attr in self.adapter.carrier_weights(self.SET_PREFIX):
            name = attr[len(self.SET_PREFIX) :]
            if name not in known:
                warnings.append(
                    f"Carrier attr {attr!r} has no registry entry — a stale "
                    "keyable weight (removed or imported group); re-add the "
                    f"group or remove_keyable_weights([{name!r}])."
                )
        return warnings

    def _mask_triangles(self, face_map: FaceMap, uv_set: Optional[str]) -> list:
        tris = []
        for obj, indices in face_map.items():
            tris.extend(self.adapter.uv_triangles(obj, indices, uv_set))
        return tris


class EmissiveGroupsModel(_EmissiveGroupsModelInternal, ptk.LoggingMixin, ptk.HelpMixin):
    """Author, bake, and export named emissive face groups (see module doc).

    All state lives in the scene, so an instance holds only its host adapter:
    each host half binds one (``maya.EmissiveGroups``,
    ``blender.EmissiveGroups``).

    Parameters:
        adapter: The host's scene operations.
    """

    def __init__(self, adapter):
        self.adapter = adapter

    # ------------------------------------------------------------------
    # Authoring
    # ------------------------------------------------------------------

    def add_group(self, name: str, faces=None, default: float = 1.0) -> str:
        """Create a group from faces (or the selection), or extend one.

        Parameters:
            name: Group name (sanitized to safe characters).
            faces: ``{object: [face indices]}`` (``[]`` = every face), or the
                host's own spelling (Maya: face components or meshes);
                ``None`` takes the selected faces.
            default: Default gate weight consumers apply (1.0 = on).

        Returns:
            The membership store's name (``emissiveGroup_<name>``).
        """
        name = ptk.RegionGroupRegistry.sanitize(name)
        face_map = self.adapter.faces(faces)
        if not face_map:
            raise ValueError("No faces in the input or selection.")
        slot, is_new = self._registry().add(name, default)
        store = self._store(name)
        self.adapter.add_members(store, face_map)
        count = sum(len(indices) for indices in face_map.values())
        self.logger.info(
            f"Added group {name!r} (slot {slot})."
            if is_new
            else f"Extended group {name!r} (+{count} face(s))."
        )
        self._refresh_export_if_published()
        return store

    def remove_group(self, name: str) -> None:
        """Delete a group's membership, registry entry and any keyable weight;
        its slot is retired (never auto-reused) so engine bindings stay valid."""
        self._registry().remove(name)
        self.adapter.remove_members(self._store(name))
        self.adapter.delete_weight(self._store(name))
        self._refresh_export_if_published()
        self.logger.info(f"Removed group {name!r}.")

    def list_groups(self) -> Dict[str, dict]:
        """``{name: {"slot", "default", "faces"(count), "missing"(membership
        gone), "attr"(keyable weight attr or None)}}`` in slot order."""
        out = {}
        for entry in self._registry().groups():
            name = entry["name"]
            members = self.adapter.members(self._store(name))
            out[name] = {
                "slot": entry["slot"],
                "default": entry["default"],
                "faces": sum(len(i) for i in (members or {}).values()),
                "missing": members is None,
                "attr": entry.get("attr"),
            }
        return out

    def weight_attrs(self) -> Dict[str, str]:
        """``{group: keyable weight attr}`` for the groups that have one, read
        from the registry alone (no membership scan)."""
        return {e["name"]: e["attr"] for e in self._registry().groups() if e.get("attr")}

    def select_group(self, name: str) -> None:
        """Select the group's faces."""
        members = self.adapter.members(self._store(name))
        if not members:
            raise ValueError(f"Group {name!r} has no members.")
        self.adapter.select(members)

    def set_default(self, name: str, default: float) -> None:
        """Set the group's default gate weight (0-1; clamped). An un-keyed
        keyable weight follows the default; a keyed one is animation-owned and
        left alone."""
        value = self._registry().set_default(name, default)
        self.adapter.sync_weight(self._store(name), value)
        self._refresh_export_if_published()

    def compact_slots(self) -> List[int]:
        """Reclaim retired slots. Explicit and binding-breaking: any engine
        scene keyed against a previously exported slot layout must be re-wired
        after the next bake and export.

        Returns:
            The slot indices reclaimed.
        """
        reclaimed = self._registry().compact()
        if reclaimed:
            self.logger.warning(
                f"Reclaimed retired slot(s) {reclaimed}; re-bake and re-export "
                "— existing engine bindings for those slots are now invalid."
            )
        return reclaimed

    # ------------------------------------------------------------------
    # Keyable weights (opt-in)
    # ------------------------------------------------------------------

    def make_weights_keyable(self, names=None) -> Dict[str, str]:
        """Add a keyable 0-1 weight per group on the ``data_export`` carrier.

        Explicitly export-facing (this publishes the manifest, creating the
        carrier if needed): the weights exist so their animation rides the
        export, where Unity's importer rebinds it to
        ``EmissiveGroupController.groups[i].weight``. Key them in the host or
        with :meth:`key_weight`.

        Parameters:
            names: Groups to make keyable; None = every group.

        Returns:
            ``{group_name: weight path}`` for the affected groups.
        """
        registry = self._registry()
        known = {entry["name"]: entry for entry in registry.groups()}
        if not known:
            raise ValueError("No emissive groups.")
        plugs = {}
        for name in self._resolve_names(names, known):
            attr = self._store(name)
            plugs[name] = self.adapter.ensure_weight(
                attr, float(known[name]["default"])
            )
            registry.set_attr(name, attr)
        self.refresh_export_metadata()
        self.logger.info(f"Keyable weight attr(s): {sorted(plugs.values())}")
        return plugs

    def remove_keyable_weights(self, names=None) -> List[str]:
        """Delete the keyable weights, animation included, and clear the
        manifest's attr records. Membership, slots and defaults are untouched.

        Parameters:
            names: Groups to strip; None = every group.

        Returns:
            The group names that actually had a weight to remove.
        """
        registry = self._registry()
        known = {entry["name"] for entry in registry.groups()}
        names = sorted(known) if names is None else [str(n) for n in names]
        removed = []
        for name in names:
            if self.adapter.delete_weight(self._store(name)):
                removed.append(name)
            if name in known:
                registry.set_attr(name, None)
        self._refresh_export_if_published()
        if removed:
            self.logger.info(f"Removed keyable weight attr(s): {removed}")
        return removed

    def key_weight(
        self,
        name: str,
        value: Optional[float] = None,
        frame: Optional[float] = None,
        auto_keyable: bool = True,
    ) -> str:
        """Key one group's weight on the carrier.

        Parameters:
            name: Group name.
            value: Weight to key (clamped 0-1); None = its current value.
            frame: Time to key at; None = the current time.
            auto_keyable: Make the group keyable first when it isn't yet.

        Returns:
            The keyed weight's path.
        """
        attr = self._store(name)
        if not self.adapter.weight_exists(attr):
            if not auto_keyable:
                raise ValueError(
                    f"Group {name!r} has no keyable weight; run "
                    f"make_weights_keyable([{name!r}])."
                )
            self.make_weights_keyable([name])
        if value is not None:
            value = max(0.0, min(1.0, float(value)))
        return self.adapter.key_weight(attr, value, frame)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """Non-fatal authoring warnings (empty list = clean)."""
        groups = self._registry().groups()
        known = {entry["name"] for entry in groups}
        members = {e["name"]: self.adapter.members(self._store(e["name"])) for e in groups}
        warnings = []
        for name, face_map in members.items():
            if face_map is None:
                warnings.append(
                    f"Group {name!r}: membership {self._store(name)!r} is missing."
                )
            elif not face_map:
                warnings.append(f"Group {name!r} is empty.")
        warnings += self._overlap_warnings(members)
        warnings += self._orphan_warnings(known)
        warnings += self.adapter.extra_warnings()
        # Foreign color sets fight ours for Unity's single color stream.
        objects = self._member_objects(members)
        for obj, others in self.adapter.foreign_color_sets(objects, self.COLOR_SET).items():
            for other in others:
                warnings.append(
                    f"{obj}: foreign color set {other!r} — Unity imports only one "
                    "color stream; vertex-color encoding may not survive."
                )
        for msg in warnings:
            self.logger.warning(msg)
        return warnings

    # ------------------------------------------------------------------
    # Bakes
    # ------------------------------------------------------------------

    def bake_vertex_colors(self, force: bool = False) -> dict:
        """Bake membership into the ``emissiveGroups`` RGBA color set.

        Written per face corner (hard group boundaries); each mesh is zeroed
        first so a re-bake never leaves stale membership behind.

        Parameters:
            force: Proceed even when member meshes carry foreign color sets
                (Unity imports a single color stream, the first set).

        Returns:
            The published manifest dict (vertex-color encoding).
        """
        registry = self._registry()
        groups = registry.groups()
        if not groups:
            raise ValueError("No emissive groups to bake.")
        members = {e["name"]: self.adapter.members(self._store(e["name"])) for e in groups}
        objects = self._member_objects(members)
        if not objects:
            raise ValueError("No member meshes found (empty groups?).")
        foreign = self.adapter.foreign_color_sets(objects, self.COLOR_SET)
        if foreign and not force:
            raise ValueError(
                f"Foreign color set(s) present: {foreign} — Unity imports only "
                "one color stream. Remove them, use the channels encoding, or "
                "pass force=True."
            )
        for obj in objects:
            # face index -> channel weights; overlapping groups accumulate.
            channels: Dict[int, List[float]] = {}
            for entry in groups:
                for index in (members[entry["name"]] or {}).get(obj, []):
                    channels.setdefault(index, [0.0, 0.0, 0.0, 0.0])[entry["slot"]] = 1.0
            self.adapter.write_colors(obj, channels, self.COLOR_SET)
        registry.set_encoding("vertex-color")
        manifest = self.refresh_export_metadata()
        self.logger.info(
            f"Baked {len(groups)} group(s) into color set {self.COLOR_SET!r} on "
            f"{len(objects)} mesh(es)."
        )
        return json.loads(manifest)

    def bake_mask(
        self,
        output_path: Optional[str] = None,
        resolution: int = 512,
        padding_px: int = 4,
        uv_set: Optional[str] = None,
    ) -> dict:
        """Rasterize membership into an ``_EMask`` RGBA texture (channels encoding).

        Harvests each group's UV triangles and packs them through
        ``ptk.RegionMaskPacker``; the manifest goes to the export carrier only,
        no sidecar beside the mask.

        Parameters:
            output_path: Mask image path. Defaults to
                ``<scene project texture folder>/<scene>_EMask.png`` (the
                project the scene is saved in); a scene with none raises.
            resolution: Mask resolution (masks are chunky; 512 usually suffices).
            padding_px: Edge padding; keep >= the emissive bake's padding.
            uv_set: UV set to harvest; defaults to each mesh's current one
                (must be the set the engine samples as UV0).

        Returns:
            The published manifest dict (channels encoding).
        """
        import os

        registry = self._registry()
        groups = registry.groups()
        if not groups:
            raise ValueError("No emissive groups to bake.")
        if output_path is None:
            output_path = self.adapter.mask_path("_EMask.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        packer = ptk.RegionMaskPacker(resolution=resolution, padding_px=padding_px)
        for entry in groups:
            face_map = self.adapter.members(self._store(entry["name"])) or {}
            if not face_map:
                self.logger.warning(f"Group {entry['name']!r} is empty; skipped.")
                continue
            tris = self._mask_triangles(face_map, uv_set)
            if not tris:
                self.logger.warning(f"Group {entry['name']!r} has no mapped UVs; skipped.")
                continue
            packer.add_group(
                entry["name"],
                tris,
                slot=entry["slot"],
                default=entry["default"],
                attr=entry.get("attr"),
            )
        packer.validate()
        manifest = packer.write(output_path, write_manifest=False)
        registry.set_encoding("channels", mask=os.path.basename(output_path), uv_channel=0)
        published = self.refresh_export_metadata()
        self.logger.info(f"Baked mask: {output_path}")
        return json.loads(published) if published else manifest.to_dict()

    # ------------------------------------------------------------------
    # Scene-record crossings (the stores' owner: ``EMISSIVE_REGISTRY``)
    # ------------------------------------------------------------------

    def transfer_out(self, ctx: "ptk.TransferContext") -> Optional[dict]:
        """The emissive registry's hand-off payload: the registry, each group's
        membership as ``{group: {object: [face index, ...]}}`` and each member
        object's face count -- the far side has no membership store to read,
        and a face index names the same face only on a mesh whose face count
        survived the crossing. Objects are spelled as the carrier writes them
        (``ctx.rename``) and scoped to ``ctx.objects``; ``None`` without groups.
        Either host reads it."""
        registry = ptk.SceneRecords.EMISSIVE_REGISTRY.load(self.adapter.data_nodes)
        if not registry or not registry.get("groups"):
            return None
        spell = ctx.rename or str
        scope = None if ctx.objects is None else set(self.adapter.object_names(ctx.objects))
        members: Dict[str, FaceMap] = {}
        faces: Dict[str, int] = {}
        for name in registry["groups"]:
            by_object: FaceMap = {}
            for obj, indices in (self.adapter.members(self._store(name)) or {}).items():
                if scope is not None and obj not in scope:
                    continue
                spelled = spell(obj)
                by_object[spelled] = sorted({int(i) for i in indices})
                faces.setdefault(spelled, self.adapter.face_count(obj))
            if by_object:
                members[name] = by_object
        return {"registry": registry, "members": members, "faces": faces}

    def transfer_in(self, payload: dict, ctx: "ptk.TransferContext") -> None:
        """Land a received payload (:meth:`transfer_out`'s shape, from either
        host): the registry merges by its rule -- a group whose slot is taken
        here is re-slotted, noted -- and each group's faces join its membership
        on the object ``ctx.rename`` resolves. An object whose face count
        changed in the crossing keeps no membership (noted): its indices would
        name other faces."""
        registry = (payload or {}).get("registry")
        if registry:
            ptk.RecordTransfer.merge_record(
                self.adapter.data_nodes, ptk.SceneRecords.EMISSIVE_REGISTRY, registry, ctx
            )
        counts = (payload or {}).get("faces") or {}
        known = {g["name"] for g in self._registry().groups()}
        for name, by_object in ((payload or {}).get("members") or {}).items():
            if name not in known:
                continue  # the merge left it out (no free slot), and said so
            face_map = self._arrived(name, by_object, counts, ctx)
            if face_map:
                self.add_group(name, face_map)

    def _arrived(self, name, by_object, counts, ctx) -> FaceMap:
        """The part of a group's received membership that still names faces here."""
        face_map: FaceMap = {}
        for spelled, indices in by_object.items():
            target = ctx.rename(spelled) if ctx.rename else spelled
            obj = self.adapter.mesh(target) if target else None
            if obj is None:
                ctx.note(
                    f"Emissive group {name!r}: {spelled!r} did not arrive; "
                    "its faces were not added."
                )
                continue
            count = self.adapter.face_count(obj)
            if counts.get(spelled) not in (None, count):
                ctx.note(
                    f"Emissive group {name!r}: {spelled!r} has {count} faces "
                    f"here and had {counts[spelled]}; its membership was not "
                    "restored."
                )
                continue
            face_map[obj] = [int(i) for i in indices]
        return face_map

    def merge_carrier(self, carriers, other, ctx) -> None:
        """Another scene's groups merged into the registry: its membership
        stores join this scene's (the host decides how)."""
        registry = other.get(ptk.SceneRecords.EMISSIVE_REGISTRY) or {}
        stores = [self._store(name) for name in registry.get("groups") or {}]
        self.adapter.merge_stores(stores, ctx)

    def discard_carrier(self, carriers, other, ctx) -> None:
        """Another scene's groups were dropped: the membership stores it brought,
        which no registry entry describes any more, go too."""
        registry = other.get(ptk.SceneRecords.EMISSIVE_REGISTRY) or {}
        stores = [self._store(name) for name in registry.get("groups") or {}]
        self.adapter.discard_stores(stores, ctx)

    # ------------------------------------------------------------------
    # Export carrier
    # ------------------------------------------------------------------

    def export_record(self, ctx: "ptk.ExportContext") -> Optional["ptk.Record"]:
        """The ``emissive_groups`` manifest record, or ``None`` when no group
        exists: the ``ptk.SceneRecords.EMISSIVE_GROUPS`` producer, read
        Unity-side by ``EmissiveGroupController``'s importer. Pure: it reads
        the registry and never writes.

        Parameters:
            ctx: The export's decisions (unused: the manifest is a function of
                the registry alone).
        """
        manifest = self._registry().manifest(color_set=self.COLOR_SET)
        if manifest is None:
            return None
        return ptk.SceneRecords.EMISSIVE_GROUPS.make(manifest.to_dict())

    def refresh_export_metadata(self) -> Optional[str]:
        """Republish the ``emissive_groups`` channel on the ``data_export``
        carrier from the registry: the authoring-time publish of
        :meth:`export_record` (an export runs the producer itself). Clears the
        channel when no groups exist.

        Returns:
            The published JSON string, or None when cleared.
        """
        record = self.export_record(ptk.ExportContext(mode=ptk.ExportContext.AUTHORING))
        self.adapter.publish({ptk.SceneRecords.EMISSIVE_GROUPS: record})
        return record.text if record is not None else None
