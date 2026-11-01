# !/usr/bin/python
# coding=utf-8
"""Find the Hierarchy Sync trees' items by the hierarchy paths a diff names.

A diff names nodes by path (``GRP|child``); the trees show them by name. The
host decides two things a match depends on, handed in by the panel from its
``HierarchySyncSession``: how a path is cleaned for comparison (``clean_path``:
Maya drops each component's namespace, Blender leaves the path as it is) and
what a tree item's node is named by (``node_path``: Maya's DAG path string,
Blender's object hierarchy path).

Private to :mod:`tentacle.slots.tools.hierarchy_sync`.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from qtpy import QtCore

import pythontk as ptk

#: UserRole payloads that are the trees' prompts, not scene nodes.
PLACEHOLDERS = frozenset({"browse_placeholder", "open_scene_placeholder"})


def _same_path(path: str) -> str:
    return path


def _string_node(node) -> str:
    return node if isinstance(node, str) else ""


class TreePathMatcher(ptk.LoggingMixin):
    """Index a tree's items by path and find the items a diff path names.

    Parameters:
        clean_path: How a path is cleaned for comparison (the host's
            ``HierarchySyncSession.clean_path``); the default leaves it as it is.
        node_path: What a tree item's node is named by (the host's
            ``HierarchySyncSession.node_path``); the default takes a string
            node as its own name.
    """

    def __init__(
        self,
        clean_path: Optional[Callable[[str], str]] = None,
        node_path: Optional[Callable[[Any], str]] = None,
    ):
        super().__init__()
        self.clean_path = clean_path or _same_path
        self.node_path = node_path or _string_node

    # ------------------------------------------------------------------ items
    @staticmethod
    def iter_items(widget):
        """Every item of *widget*, depth first in display order."""
        stack = [widget.topLevelItem(i) for i in range(widget.topLevelItemCount())]
        stack.reverse()
        while stack:
            item = stack.pop()
            if not item:
                continue
            yield item
            for i in range(item.childCount() - 1, -1, -1):
                stack.append(item.child(i))

    @staticmethod
    def item_path(item) -> str:
        """The item's display path: its and its ancestors' names, root first."""
        parts = []
        current = item
        while current:
            parts.insert(0, current.text(0))
            current = current.parent()
        return ptk.HierarchyPath.join(parts)

    @staticmethod
    def raw_item_path(item) -> str:
        """The item's path by its nodes' own names (``_raw_name``: a Maya node's
        namespace kept), its display names where none was stored."""
        parts = []
        current = item
        while current:
            parts.insert(0, getattr(current, "_raw_name", current.text(0)))
            current = current.parent()
        return ptk.HierarchyPath.join(parts)

    def item_key(self, item) -> str:
        """The name the host takes *item*'s node by (a pull's target).

        The stored node wins: a leaf name is ambiguous where names repeat, and
        the display chain can drift from the node's real name. A prompt row is
        no node (``""``). Without a node: the node's own name, then the
        display path.
        """
        try:
            data = item.data(0, QtCore.Qt.UserRole)
        except Exception:
            data = None
        if isinstance(data, str) and data in PLACEHOLDERS:
            return ""
        if data is not None:
            key = self.node_path(data)
            if key:
                return key
        raw_name = getattr(item, "_raw_name", None)
        if raw_name:
            return raw_name
        return self.item_path(item)

    # ------------------------------------------------------------------ matching
    def build_tree_index(self, widget) -> Tuple[dict, dict, Dict[str, list]]:
        """Index *widget*'s items three ways for :meth:`find_path_matches`.

        Returns:
            ``(by_full, by_clean_full, by_last)``: by raw path, by cleaned raw
            path (an entry is an item, or a list where paths collide), and by
            cleaned leaf name (always a list).
        """
        by_full: Dict[str, Any] = {}
        by_clean_full: Dict[str, Any] = {}
        by_last: Dict[str, list] = {}
        for item in self.iter_items(widget):
            raw_path = self.raw_item_path(item)
            if raw_path:
                self._add(by_full, raw_path, item)
                self._add(by_clean_full, self.clean_path(raw_path), item)
            path = self.item_path(item)
            if path:
                leaf = self.clean_path(ptk.HierarchyPath.leaf(path))
                by_last.setdefault(leaf, []).append(item)
        return by_full, by_clean_full, by_last

    @staticmethod
    def _add(index: dict, key: str, item) -> None:
        existing = index.get(key)
        if existing is None:
            index[key] = item
        elif isinstance(existing, list):
            existing.append(item)
        else:
            index[key] = [existing, item]

    def find_path_matches(
        self,
        target_path: str,
        by_full: dict,
        by_clean_full: dict,
        by_last: dict,
        prefer_cleaned: bool = False,
        strict: bool = False,
    ) -> Tuple[List[Any], str]:
        """The items *target_path* names, and the strategy that found them.

        Exact raw path and cleaned path, in the order *prefer_cleaned* asks;
        unless *strict*, the cleaned leaf name last.

        Returns:
            ``(items, strategy)``: strategy is ``"full"``, ``"clean_full"``,
            ``"last"`` or ``"none"``.
        """
        cleaned_path = self.clean_path(target_path)
        lookups = [
            ("clean_full", by_clean_full, cleaned_path),
            ("full", by_full, target_path),
        ]
        if not prefer_cleaned:
            lookups.reverse()

        candidates: list = []
        strategy = "none"
        for name, index, key in lookups:
            hit = index.get(key)
            if hit is not None:
                candidates, strategy = [hit], name
                break
        if not candidates and not strict:
            leaf = self.clean_path(ptk.HierarchyPath.leaf(target_path))
            candidates = by_last.get(leaf, [])
            if candidates:
                strategy = "last"

        flat: list = []
        for entry in candidates:
            for sub in entry if isinstance(entry, (list, tuple, set)) else (entry,):
                if sub is not None and sub not in flat:
                    flat.append(sub)
        return flat, strategy

    def log_matching_debug(self, path, candidates, strategy, prefix="") -> None:
        """Log how *path* matched."""
        self.logger.debug(
            f"{prefix} path '{path}' -> {len(candidates)} candidates via {strategy}"
        )
