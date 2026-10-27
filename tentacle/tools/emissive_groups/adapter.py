# !/usr/bin/python
# coding=utf-8
"""The scene operations the Emissive Groups model needs from a host.

``maya.MayaEmissiveGroups`` and ``blender.BlenderEmissiveGroups`` implement
it. Membership is spoken as ``{object: [face index, ...]}`` (a ``FaceMap``),
objects named as the host names them uniquely (Maya: long transform paths;
Blender: object names). A membership *store* is the host's container for one
group (Maya: an ``objectSet``; Blender: a boolean FACE attribute), named
``emissiveGroup_<name>``; a group's keyable weight on the ``data_export``
carrier takes the same name.
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Tuple

FaceMap = Dict[str, List[int]]


class EmissiveGroupsAdapter(Protocol):
    """A host's half of Emissive Groups."""

    #: The host's scene-record store (``DataNodes``): the registry and the
    #: manifest are read and written through it.
    data_nodes: Any

    # Membership --------------------------------------------------------

    def faces(self, faces=None) -> FaceMap:
        """*faces* (a ``FaceMap``, or the host's own spelling) or, for ``None``,
        the selected faces, as a ``FaceMap``; empty when there are none."""

    def add_members(self, store: str, face_map: FaceMap) -> None:
        """Add *face_map* to *store*, creating it when absent."""

    def remove_members(self, store: str) -> None:
        """Delete *store* wherever it lives."""

    def members(self, store: str) -> Optional[FaceMap]:
        """*store*'s faces; ``None`` when the store itself is gone."""

    def select(self, face_map: FaceMap) -> None:
        """Select exactly these faces."""

    def membership_stores(self, prefix: str) -> Iterable[Tuple[str, str]]:
        """``(where, group name)`` for every store named *prefix*``<name>``,
        *where* a phrase naming it for a warning."""

    # Keyable weights (on the ``data_export`` carrier) -------------------

    def carrier_weights(self, prefix: str) -> List[str]:
        """The carrier's weight attrs named *prefix*``<name>``."""

    def weight_exists(self, attr: str) -> bool:
        """Whether the carrier holds weight *attr*."""

    def ensure_weight(self, attr: str, default: float) -> str:
        """Create keyable 0-1 weight *attr* (default *default*), or make an
        existing one keyable; returns its path."""

    def delete_weight(self, attr: str) -> bool:
        """Delete weight *attr* and its animation; False when there was none."""

    def sync_weight(self, attr: str, value: float) -> None:
        """Set an un-animated weight *attr* to *value*; an animated one is left."""

    def key_weight(self, attr: str, value: Optional[float], frame: Optional[float]) -> str:
        """Key weight *attr* (at *value*, else its current value; at *frame*,
        else the current time); returns its path."""

    # Bakes --------------------------------------------------------------

    def foreign_color_sets(self, objects: List[str], color_set: str) -> Dict[str, List[str]]:
        """``{object: [color set, ...]}`` for the objects carrying sets other
        than *color_set*."""

    def write_colors(self, obj: str, channels: Mapping[int, List[float]], color_set: str) -> None:
        """Write *color_set* on *obj*: each listed face's corners take its RGBA
        weights, every other corner zero (a re-bake clears stale membership)."""

    def uv_triangles(self, obj: str, indices: List[int], uv_set: Optional[str]) -> list:
        """Triangulated UVs of *obj*'s faces *indices*: ``[[(u, v)] * 3, ...]``."""

    def mask_path(self, suffix: str) -> str:
        """``<scene project texture folder>/<scene stem><suffix>``; raises
        ``ValueError`` when the scene has no project."""

    # Crossings -----------------------------------------------------------

    def object_names(self, objects) -> List[str]:
        """*objects* named as the ``FaceMap`` keys name them."""

    def face_count(self, obj: str) -> int:
        """*obj*'s face count."""

    def mesh(self, name: str) -> Optional[str]:
        """The mesh object *name* resolves to, as a ``FaceMap`` key, or ``None``."""

    def merge_stores(self, stores: List[str], ctx) -> None:
        """An imported scene's *stores* join this scene's of the same name."""

    def discard_stores(self, stores: List[str], ctx) -> None:
        """Delete the *stores* an import brought, which nothing describes now."""

    # Export ----------------------------------------------------------------

    def publish(self, records: Mapping[Any, Any]) -> None:
        """Commit authored *records* to the export carrier
        (``FbxUtils.publish_authored``)."""

    def extra_warnings(self) -> List[str]:
        """The host's own validation warnings (Blender: leftover curve proxies)."""
