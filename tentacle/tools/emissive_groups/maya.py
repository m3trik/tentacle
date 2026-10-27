# !/usr/bin/python
# coding=utf-8
"""Emissive Groups' Maya half: one ``objectSet`` of faces per group, keyable
weights as custom attrs on the ``data_export`` carrier (their curves ride the
FBX as animated custom properties). ``EmissiveGroups`` is the tool in Maya.
"""

from collections import defaultdict
from typing import Dict, List, Optional

try:
    import maya.cmds as cmds
except ImportError:
    pass

import mayatk as mtk

from tentacle.tools.emissive_groups.model.emissive_groups_model import (
    EmissiveGroupsModel,
)

FaceMap = Dict[str, List[int]]


class _MayaEmissiveGroupsInternal:
    """Implementation-detail base for :class:`MayaEmissiveGroups`."""

    @staticmethod
    def _transform(node: str) -> Optional[str]:
        """*node*'s transform as a long name (a shape's parent), else ``None``."""
        found = cmds.ls(node, long=True) or []
        if not found:
            return None
        if cmds.nodeType(found[0]) == "transform":
            return found[0]
        parent = cmds.listRelatives(found[0], parent=True, fullPath=True) or []
        return parent[0] if parent else None

    @classmethod
    def _face_map(cls, components) -> FaceMap:
        """Face components as a ``FaceMap`` keyed by long transform.

        Read compact (``f[a:b]`` ranges, as ``filterExpand -ex 0`` gives them)
        and expanded here: a flattened list of a dense mesh's faces costs Maya
        one string per face, on every panel refresh.
        """
        out: Dict[str, set] = {}
        transforms: Dict[str, Optional[str]] = {}  # one query per node, not per range
        for comp in components:
            node, _, span = comp.partition(".f[")
            if node not in transforms:
                transforms[node] = cls._transform(node)
            if not transforms[node]:
                continue
            start, _, stop = span.rstrip("]").partition(":")
            indices = out.setdefault(transforms[node], set())
            if start == "*":  # the whole mesh
                indices.update(range(int(cmds.polyEvaluate(node, face=True))))
            else:
                indices.update(range(int(start), int(stop or start) + 1))
        return {obj: sorted(indices) for obj, indices in out.items()}

    @staticmethod
    def _components(face_map: FaceMap) -> List[str]:
        """``FaceMap`` -> face components, contiguous indices as ``f[a:b]`` ranges;
        an empty index list names the whole object."""
        comps = []
        for obj, indices in face_map.items():
            if not indices:
                comps.append(obj)
                continue
            ordered = sorted(set(int(i) for i in indices))
            start = prev = ordered[0]
            for index in ordered[1:] + [None]:
                if index is not None and index == prev + 1:
                    prev = index
                    continue
                comps.append(f"{obj}.f[{start}]" if start == prev else f"{obj}.f[{start}:{prev}]")
                if index is not None:
                    start = prev = index
        return comps

    @staticmethod
    def _arrived_sets(stores, ctx, renamed_only: bool = True):
        """``(set, canonical name)`` for each store an import brought: renamed or
        namespaced ones (a clash with this scene's set), plus -- unless
        *renamed_only* -- those that arrived under their own name."""
        for canonical in stores:
            arrived = ctx.spell(canonical)
            if not cmds.objExists(arrived) or cmds.nodeType(arrived) != "objectSet":
                continue
            if arrived != canonical or not renamed_only:
                yield arrived, canonical


class MayaEmissiveGroups(_MayaEmissiveGroupsInternal):
    """The Maya scene operations of the Emissive Groups model
    (``EmissiveGroupsAdapter``)."""

    data_nodes = mtk.DataNodes

    # Membership --------------------------------------------------------

    def faces(self, faces=None) -> FaceMap:
        source = faces if faces is not None else (cmds.ls(sl=True) or [])
        if isinstance(source, dict):
            source = self._components(source)
        source = [str(s) for s in (source if isinstance(source, (list, tuple)) else [source])]
        if not source:
            return {}
        converted = cmds.polyListComponentConversion(source, toFace=True) or []
        return self._face_map(cmds.filterExpand(converted, sm=34, expand=False) or [])

    def add_members(self, store: str, face_map: FaceMap) -> None:
        comps = self._components(face_map)
        if cmds.objExists(store):
            cmds.sets(comps, add=store)
        else:
            cmds.sets(comps, name=store)

    def remove_members(self, store: str) -> None:
        if cmds.objExists(store):
            cmds.delete(store)

    def members(self, store: str) -> Optional[FaceMap]:
        if not cmds.objExists(store):
            return None
        found = cmds.sets(store, q=True) or []
        return self._face_map(cmds.filterExpand(found, sm=34, expand=False) or [])

    def select(self, face_map: FaceMap) -> None:
        cmds.select(self._components(face_map), replace=True)

    def membership_stores(self, prefix: str):
        for node in cmds.ls(f"{prefix}*", type="objectSet") or []:
            yield f"Set {node!r}", node[len(prefix) :]

    # Keyable weights -----------------------------------------------------

    def _plug(self, attr: str) -> str:
        return f"{self.data_nodes.EXPORT}.{attr}"

    def carrier_weights(self, prefix: str) -> List[str]:
        if not cmds.objExists(self.data_nodes.EXPORT):
            return []
        attrs = cmds.listAttr(self.data_nodes.EXPORT, userDefined=True) or []
        return [attr for attr in attrs if attr.startswith(prefix)]

    def weight_exists(self, attr: str) -> bool:
        export = self.data_nodes.EXPORT
        return bool(
            cmds.objExists(export) and cmds.attributeQuery(attr, node=export, exists=True)
        )

    def ensure_weight(self, attr: str, default: float) -> str:
        export = str(self.data_nodes.ensure_export())
        if not cmds.attributeQuery(attr, node=export, exists=True):
            cmds.addAttr(
                export,
                longName=attr,
                attributeType="float",
                minValue=0.0,
                maxValue=1.0,
                defaultValue=default,
                keyable=True,
            )
        else:
            # Relink path: an FBX reimport restores the attr, not necessarily keyable.
            cmds.setAttr(f"{export}.{attr}", keyable=True)
        return f"{export}.{attr}"

    def delete_weight(self, attr: str) -> bool:
        if not self.weight_exists(attr):
            return False
        plug = self._plug(attr)
        # Anim curves first: deleteAttr errors on connected attrs.
        curves = cmds.listConnections(plug, type="animCurve") or []
        if curves:
            cmds.delete(curves)
        cmds.deleteAttr(plug)
        return True

    def sync_weight(self, attr: str, value: float) -> None:
        # ANY incoming connection (anim curve, expression, constraint) owns the
        # value, and would make the setAttr raise.
        if self.weight_exists(attr):
            plug = self._plug(attr)
            if not cmds.connectionInfo(plug, isDestination=True):
                cmds.setAttr(plug, float(value))

    def key_weight(self, attr: str, value: Optional[float], frame: Optional[float]) -> str:
        plug = self._plug(attr)
        kwargs = {}
        if frame is not None:
            kwargs["time"] = frame
        if value is not None:
            kwargs["value"] = value
        cmds.setKeyframe(plug, **kwargs)
        return plug

    # Bakes ---------------------------------------------------------------

    def foreign_color_sets(self, objects: List[str], color_set: str) -> Dict[str, List[str]]:
        foreign = {}
        for obj in objects:
            others = [
                c
                for c in (cmds.polyColorSet(obj, q=True, allColorSets=True) or [])
                if c != color_set
            ]
            if others:
                foreign[obj] = others
        return foreign

    def write_colors(self, obj: str, channels, color_set: str) -> None:
        if color_set not in (cmds.polyColorSet(obj, q=True, allColorSets=True) or []):
            cmds.polyColorSet(
                obj, create=True, colorSet=color_set, representation="RGBA", clamped=True
            )
        cmds.polyColorSet(obj, currentColorSet=True, colorSet=color_set)
        cmds.polyColorPerVertex(f"{obj}.f[*]", rgb=(0.0, 0.0, 0.0), a=0.0)
        # One assignment per distinct channel combination (few, so fast).
        by_vec = defaultdict(list)
        for index, vec in channels.items():
            by_vec[tuple(vec)].append(index)
        for vec, indices in by_vec.items():
            cmds.polyColorPerVertex(self._components({obj: indices}), rgb=vec[:3], a=vec[3])

    def uv_triangles(self, obj: str, indices: List[int], uv_set: Optional[str]) -> list:
        import maya.api.OpenMaya as om

        sel = om.MSelectionList()
        for comp in self._components({obj: indices}):
            sel.add(comp)
        dag, comp = sel.getComponent(0)
        uv_set = uv_set or om.MFnMesh(dag).currentUVSetName()
        tris = []
        it = om.MItMeshPolygon(dag, comp)
        while not it.isDone():
            if it.hasUVs():
                local = {it.vertexIndex(i): i for i in range(it.polygonVertexCount())}
                us, vs = it.getUVs(uv_set)
                for t in range(it.numTriangles()):
                    _, vtx_ids = it.getTriangle(t)
                    tris.append([(us[local[v]], vs[local[v]]) for v in vtx_ids])
            it.next()
        return tris

    def mask_path(self, suffix: str) -> str:
        import os

        folder = self.data_nodes.scene_source_images_dir()
        if not folder:
            raise ValueError(
                "No project to write the mask into; save the scene, set a "
                "project, or pass output_path."
            )
        stem = os.path.splitext(os.path.basename(self.data_nodes.scene_path()))[0]
        return os.path.join(folder, f"{stem or 'untitled'}{suffix}")

    # Crossings -----------------------------------------------------------

    def object_names(self, objects) -> List[str]:
        return cmds.ls([str(o) for o in objects], long=True) or []

    def face_count(self, obj: str) -> int:
        return int(cmds.polyEvaluate(obj, face=True))

    def mesh(self, name: str) -> Optional[str]:
        return self._transform(name) if name and cmds.objExists(name) else None

    def merge_stores(self, stores: List[str], ctx) -> None:
        for arrived, canonical in self._arrived_sets(stores, ctx):
            if cmds.objExists(canonical):
                members = cmds.sets(arrived, q=True) or []
                # Only with members: `sets -add` given none falls back to the
                # live selection, which would join the group.
                if members:
                    cmds.sets(members, add=canonical)
                cmds.delete(arrived)
            else:
                cmds.rename(arrived, canonical)

    def discard_stores(self, stores: List[str], ctx) -> None:
        for arrived, _canonical in self._arrived_sets(stores, ctx, renamed_only=False):
            cmds.delete(arrived)

    # Export ----------------------------------------------------------------

    def publish(self, records) -> None:
        mtk.FbxUtils.publish_authored(records)

    def extra_warnings(self) -> List[str]:
        return []


#: The tool in Maya: the model over the Maya half.
EmissiveGroups = EmissiveGroupsModel(MayaEmissiveGroups())
