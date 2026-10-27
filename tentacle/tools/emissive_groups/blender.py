# !/usr/bin/python
# coding=utf-8
"""Emissive Groups' Blender half: one boolean FACE attribute per group on its
member meshes (per-group booleans, not one ID attribute, so overlapping
membership stays expressible, as Maya's sets allow), keyable weights as custom
properties on the ``data_export`` carrier. ``EmissiveGroups`` is the tool in
Blender.

Blender's FBX exporter ships the carrier's custom properties (enable *Custom
Properties*) but no custom-property *animation*, so at export time one
transient Empty per keyed group carries the weight curve on ``scale.x``
(:meth:`BlenderEmissiveGroups.create_export_curve_proxies`, the
``emissive_groups`` export stager); Unity's importer rebinds it and deletes
the node, and the proxies leave the scene right after the write.

``import bpy`` is deferred into the call bodies (no import side effects).
"""

from typing import Dict, List, Optional

import blendertk as btk

from tentacle.tools.emissive_groups.model.emissive_groups_model import (
    EmissiveGroupsModel,
)

FaceMap = Dict[str, List[int]]


class _BlenderEmissiveGroupsInternal:
    """Implementation-detail base for :class:`BlenderEmissiveGroups`."""

    #: Custom-prop marker on export curve proxies: the handle the post-export
    #: cleanup (and validation's leftover sweep) matches on.
    PROXY_MARKER = "emissiveGroupCurveProxy"

    @staticmethod
    def _mesh_objects():
        """Every mesh object the view layer holds (window-independent: the Qt
        pump runs the panel where ``bpy.context.window`` is ``None``)."""
        layer = btk.CoreUtils.active_view_layer()
        return [o for o in layer.objects if o and o.type == "MESH"] if layer else []

    @staticmethod
    def _carrier():
        return btk.DataNodes.get_export_node(create=False)

    @classmethod
    def _weight_fcurve(cls, attr: str):
        """The carrier's fcurve for weight *attr*, or None."""
        carrier = cls._carrier()
        if carrier is None:
            return None
        path = f'["{attr}"]'
        return next(
            (fc for fc in btk.AnimUtils.get_fcurves([carrier]) if fc.data_path == path),
            None,
        )

    @staticmethod
    def _selected_faces() -> FaceMap:
        """The selected faces; a selected mesh in Object Mode with none selected
        counts whole."""
        out: FaceMap = {}
        for obj in btk.CoreUtils.selected_objects():
            if obj.type != "MESH":
                continue
            obj.update_from_editmode()
            selected = [p.index for p in obj.data.polygons if p.select]
            if not selected and obj.mode == "OBJECT":
                selected = list(range(len(obj.data.polygons)))
            if selected:
                out[obj.name] = selected
        return out


class BlenderEmissiveGroups(_BlenderEmissiveGroupsInternal):
    """The Blender scene operations of the Emissive Groups model
    (``EmissiveGroupsAdapter``), and its export stager."""

    data_nodes = btk.DataNodes
    COLOR_SET_NOUN = "color attribute"
    WEIGHT_NOUN = "prop"

    # Membership --------------------------------------------------------

    def faces(self, faces=None) -> FaceMap:
        import bpy

        if not faces:  # None or empty: the selection, as Blender's engine read it
            return self._selected_faces()
        out: FaceMap = {}
        for name, indices in dict(faces).items():
            obj = bpy.data.objects.get(str(name))
            if obj is None or obj.type != "MESH":
                continue
            idx = [int(i) for i in indices]
            out[obj.name] = idx or list(range(len(obj.data.polygons)))
        return {k: v for k, v in out.items() if v}

    def add_members(self, store: str, face_map: FaceMap) -> None:
        import bpy

        for name, indices in face_map.items():
            mesh = bpy.data.objects[name].data
            attr = mesh.attributes.get(store) or mesh.attributes.new(store, "BOOLEAN", "FACE")
            for i in indices:
                attr.data[i].value = True

    def remove_members(self, store: str) -> None:
        for obj in self._mesh_objects():
            attr = obj.data.attributes.get(store)
            if attr is not None:
                obj.data.attributes.remove(attr)

    def members(self, store: str) -> Optional[FaceMap]:
        # foreach_get fills the buffer in one C call; a per-face Python loop cost
        # seconds on a dense mesh, paid again per group on each table refresh.
        import numpy as np

        out: Optional[FaceMap] = None
        for obj in self._mesh_objects():
            attr = obj.data.attributes.get(store)
            if attr is None:
                continue
            out = out if out is not None else {}
            values = np.empty(len(attr.data), dtype=bool)
            attr.data.foreach_get("value", values)
            indices = np.flatnonzero(values)
            if indices.size:
                out[obj.name] = indices.tolist()
        # No member face anywhere reads as missing (the panel's "(missing)"),
        # an attribute left with none included.
        return out or None

    def select(self, face_map: FaceMap) -> None:
        import bpy

        layer = btk.CoreUtils.active_view_layer()
        for obj in list(layer.objects) if layer else []:
            # On the layer: a bare select_set addresses the context's layer,
            # which windowless is the scene's default, not the window's.
            obj.select_set(obj.name in face_map, view_layer=layer)
        for name, indices in face_map.items():
            wanted = set(indices)
            for poly in bpy.data.objects[name].data.polygons:
                poly.select = poly.index in wanted
        if layer is not None:
            layer.objects.active = bpy.data.objects[next(iter(face_map))]

    def membership_stores(self, prefix: str):
        for obj in self._mesh_objects():
            for attr in obj.data.attributes:
                if attr.name.startswith(prefix):
                    yield f"{obj.name}: attribute {attr.name!r}", attr.name[len(prefix) :]

    # Keyable weights -----------------------------------------------------

    def carrier_weights(self, prefix: str) -> List[str]:
        carrier = self._carrier()
        return [k for k in carrier.keys() if k.startswith(prefix)] if carrier else []

    def weight_exists(self, attr: str) -> bool:
        carrier = self._carrier()
        return carrier is not None and attr in carrier

    def ensure_weight(self, attr: str, default: float) -> str:
        carrier = btk.DataNodes.ensure_export()
        if attr not in carrier:
            carrier[attr] = default
        try:
            carrier.id_properties_ui(attr).update(
                min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, default=default
            )
        except (AttributeError, TypeError, KeyError):
            pass
        return f'{carrier.name}["{attr}"]'

    def delete_weight(self, attr: str) -> bool:
        carrier = self._carrier()
        if carrier is None or attr not in carrier:
            return False
        fc = self._weight_fcurve(attr)
        data = getattr(carrier, "animation_data", None)
        if fc is not None and data is not None and data.action is not None:
            try:
                btk.AnimUtils.remove_fcurve(data.action, getattr(data, "action_slot", None), fc)
            except (RuntimeError, ReferenceError, ValueError):
                pass
        del carrier[attr]
        return True

    def sync_weight(self, attr: str, value: float) -> None:
        # Once keyed, the animation owns the value.
        if self.weight_exists(attr) and self._weight_fcurve(attr) is None:
            self._carrier()[attr] = float(value)

    def key_weight(self, attr: str, value: Optional[float], frame: Optional[float]) -> str:
        carrier = self._carrier()
        if value is not None:
            carrier[attr] = value
        if frame is None:
            layer = btk.CoreUtils.active_view_layer()  # its scene, window-independently
            frame = layer.id_data.frame_current if layer is not None else 1
        carrier.keyframe_insert(data_path=f'["{attr}"]', frame=frame)
        return f'{carrier.name}["{attr}"]'

    # Bakes ---------------------------------------------------------------

    def foreign_color_sets(self, objects: List[str], color_set: str) -> Dict[str, List[str]]:
        import bpy

        foreign = {}
        for name in objects:
            mesh = bpy.data.objects[name].data
            others = [c.name for c in mesh.color_attributes if c.name != color_set]
            if others:
                foreign[name] = others
        return foreign

    def write_colors(self, obj: str, channels, color_set: str) -> None:
        import bpy
        import numpy as np

        mesh = bpy.data.objects[obj].data
        cattr = mesh.color_attributes.get(color_set) or mesh.color_attributes.new(
            name=color_set, type="BYTE_COLOR", domain="CORNER"
        )
        mesh.color_attributes.active_color = cattr
        # Per corner (hard group boundaries); the zeros clear stale membership,
        # and the whole buffer goes in one call.
        colors = np.zeros((len(mesh.loops), 4), dtype=np.float32)
        for index, vec in channels.items():
            poly = mesh.polygons[index]
            colors[poly.loop_start : poly.loop_start + poly.loop_total] = vec
        cattr.data.foreach_set("color", colors.ravel())
        mesh.update()

    def uv_triangles(self, obj: str, indices: List[int], uv_set: Optional[str]) -> list:
        import bpy

        mesh = bpy.data.objects[obj].data
        layer = mesh.uv_layers.get(uv_set) if uv_set else mesh.uv_layers.active
        if layer is None:
            return []
        members = set(indices)
        mesh.calc_loop_triangles()
        return [
            [tuple(layer.data[lo].uv) for lo in tri.loops]
            for tri in mesh.loop_triangles
            if tri.polygon_index in members
        ]

    def mask_path(self, suffix: str) -> str:
        import os

        import bpy

        folder = btk.DataNodes.scene_source_images_dir()
        if not folder:
            raise ValueError(
                "No project to write the mask into; save the .blend, set a "
                "workspace, or pass output_path."
            )
        stem = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        return os.path.join(folder, f"{stem or 'untitled'}{suffix}")

    # Crossings -----------------------------------------------------------

    def object_names(self, objects) -> List[str]:
        return [getattr(o, "name", str(o)) for o in objects]

    def face_count(self, obj: str) -> int:
        import bpy

        return len(bpy.data.objects[obj].data.polygons)

    def mesh(self, name: str) -> Optional[str]:
        import bpy

        obj = bpy.data.objects.get(name)
        return obj.name if obj is not None and obj.type == "MESH" else None

    def merge_stores(self, stores: List[str], ctx) -> None:
        """Nothing to do: the attributes arrive on their meshes."""

    def discard_stores(self, stores: List[str], ctx) -> None:
        """Nothing to do: the attributes leave with their meshes."""

    # Export ----------------------------------------------------------------

    def publish(self, records) -> None:
        btk.FbxUtils.publish_authored(records)

    def extra_warnings(self) -> List[str]:
        """Leftover curve proxies: export-transient, so one outside an export
        means an interrupted run failed to clean up."""
        import bpy

        return [
            f"Leftover export curve proxy {obj.name!r} (an export was "
            "interrupted) — remove_export_curve_proxies() clears it."
            for obj in bpy.data.objects
            if obj.get(self.PROXY_MARKER)
        ]

    # Export stager -----------------------------------------------------------

    @classmethod
    def create_export_curve_proxies(cls) -> List:
        """Stage the keyed-weight FBX transport (the ``emissive_groups`` export
        stager, which every bracketed write stages and finishes).

        Each keyable group with a weight fcurve gets one transient Empty under
        the ``data_export`` carrier, named exactly the group's manifest
        ``attr``, whose ``scale.x`` is keyed with the weight curve: scale
        because it is unitless (translation would pick up the exporter's unit
        conversion, rotation its degrees). Marked with :attr:`PROXY_MARKER` and
        removed right after the write (:meth:`remove_export_curve_proxies`);
        stale ones from an interrupted export are pre-cleaned here.

        Returns:
            The created proxy objects (empty when nothing is keyed).
        """
        cls.remove_export_curve_proxies()  # stale pre-clean (idempotent)
        carrier = cls._carrier()
        if carrier is None:
            return []
        proxies = []
        for name, attr in EmissiveGroups.weight_attrs().items():
            fc = cls._weight_fcurve(attr)
            if fc is None or not len(fc.keyframe_points):
                continue
            # The shared transport (also RenderEffects'), stamped with this
            # tool's marker for its cleanup and the ecosystem marker the GLB
            # conversion strips on.
            proxy = btk.FbxUtils.stage_curve_proxy(attr, carrier, fc, cls.PROXY_MARKER)
            if proxy is None:
                EmissiveGroups.logger.warning(
                    f"Curve-proxy name {attr!r} is taken by an existing object "
                    f"— group {name!r}'s weight animation will not ship this export."
                )
                continue
            proxies.append(proxy)
        if proxies:
            EmissiveGroups.logger.info(
                "Staged keyed-weight curve prox"
                + ("y" if len(proxies) == 1 else "ies")
                + ": "
                + ", ".join(o.name for o in proxies)
            )
        return proxies

    @classmethod
    def remove_export_curve_proxies(cls) -> List[str]:
        """Delete every staged curve proxy (marker-matched) and its action.
        Idempotent; doubles as the stale pre-clean and the leftover sweep.

        Returns:
            The removed proxy names.
        """
        import bpy

        removed = []
        for obj in [o for o in bpy.data.objects if o.get(cls.PROXY_MARKER)]:
            data = getattr(obj, "animation_data", None)
            action = data.action if data is not None else None
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
            if action is not None and action.users == 0:
                bpy.data.actions.remove(action)
        return removed


#: The tool in Blender: the model over the Blender half.
EmissiveGroups = EmissiveGroupsModel(BlenderEmissiveGroups())
