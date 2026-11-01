# !/usr/bin/python
# coding=utf-8
"""The Hierarchy Sync trees: filling them, the diff's colours, the ignored
items' styling, the selection the diff picks and the selection a refresh keeps.

What a tree shows comes from the host (``HierarchySyncSession``: the scene's
nodes and their structure, ``NodeIcons`` for their icons); everything here is
Qt. The panel state it reads (the diff, the ignored paths) is the controller's
(:class:`~tentacle.slots.tools._hierarchy_sync.controller.HierarchySyncController`).

Private to :mod:`tentacle.slots.tools.hierarchy_sync`.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

from qtpy import QtCore, QtGui

import pythontk as ptk

from .tree_matcher import TreePathMatcher

#: Item data role holding an item's tooltip from before the diff annotated it,
#: so a clear restores it instead of stacking stale diff text.
ORIG_TOOLTIP_ROLE = QtCore.Qt.UserRole + 500

#: The prompt rows' payloads (what a click on one opens).
BROWSE_PLACEHOLDER = "browse_placeholder"
OPEN_SCENE_PLACEHOLDER = "open_scene_placeholder"

#: The prompt rows' link colour.
_LINK_COLOR = "#6699CC"


class HierarchyTreeRenderer(ptk.LoggingMixin):
    """Owns the two trees' content and look; reads the controller's state."""

    #: Desaturated diff colours (``Palette.diff()``), by diff category.
    DIFF_COLORS = ptk.Palette.diff().alias(
        {
            "missing": "removed",
            "extra": "added",
            "fuzzy": "changed",
            "reparented": "moved",
        }
    )

    def __init__(self, controller):
        super().__init__()
        self._ctrl = controller
        self.use_logger(controller.logger)

    @property
    def session(self):
        """The host's ``HierarchySyncSession``."""
        return self._ctrl.session

    def matcher(self) -> TreePathMatcher:
        """A path matcher over the host's path rules, logging into the panel."""
        matcher = TreePathMatcher(
            clean_path=self.session.clean_path, node_path=self.session.node_path
        )
        matcher.use_logger(self.logger)
        return matcher

    # ------------------------------------------------------------------ filling
    def populate_current_scene_tree(self, tree_widget) -> None:
        """Fill *tree_widget* with the current scene's hierarchy, or an Open
        Scene prompt when the scene has no nodes."""
        if self._ctrl.importing_reference:
            self.logger.debug(
                "Skipping current scene tree refresh during reference import"
            )
            return
        try:
            scene = self.session.scene_path()
            scene_name = (
                (Path(scene).stem or "Untitled Scene") if scene else "Current Scene"
            )
            tree_widget.clear()
            tree_widget.setHeaderLabels([scene_name])
            nodes = self.session.current_scene_nodes()
            if not nodes:
                self._prompt(tree_widget, "Open Scene", OPEN_SCENE_PLACEHOLDER)
                self.logger.debug("No objects found in the current scene.")
                return
            tree_widget.blockSignals(True)
            try:
                self.populate_tree_with_hierarchy(tree_widget, nodes, "current")
            finally:
                tree_widget.blockSignals(False)
        except Exception as e:
            self.logger.error(f"Error populating current scene tree: {e}")
            tree_widget.clear()
            tree_widget.setHeaderLabels(["Current Scene"])
            tree_widget.create_item([f"Error: {e}"])

    def populate_reference_tree(
        self, tree_widget, nodes, reference_name="Reference Scene"
    ) -> None:
        """Fill *tree_widget* with the reference's *nodes* (already loaded)."""
        tree_widget.clear()
        tree_widget.setHeaderLabels([reference_name])
        if not nodes:
            tree_widget.create_item(["No objects in reference"])
            return
        self.populate_tree_with_hierarchy(tree_widget, nodes, "reference")
        self.logger.debug("Reference tree populated successfully")

    def show_reference_placeholder(
        self, tree_widget, reference_name="Reference Scene"
    ) -> None:
        """A 'Browse for Reference Scene' prompt in the reference tree."""
        tree_widget.clear()
        tree_widget.setHeaderLabels([reference_name])
        self._prompt(tree_widget, "Browse for Reference Scene", BROWSE_PLACEHOLDER)

    def show_reference_error(
        self, tree_widget, reference_name="Reference Scene", message="File Not Found"
    ) -> None:
        """A status *message* in the reference tree."""
        tree_widget.clear()
        tree_widget.setHeaderLabels([reference_name])
        tree_widget.create_item([message])

    @staticmethod
    def _prompt(tree_widget, text: str, payload: str) -> None:
        item = tree_widget.create_item([text])
        font = item.font(0)
        font.setUnderline(True)
        item.setFont(0, font)
        item.setForeground(0, QtGui.QBrush(QtGui.QColor(_LINK_COLOR)))
        item.setData(0, QtCore.Qt.UserRole, payload)

    def populate_tree_with_hierarchy(self, tree_widget, nodes, tree_type="current"):
        """Add *nodes* to *tree_widget*, nested as the scene nests them.

        Each item carries its node (UserRole) and the node's own name
        (``_raw_name``); a reference item shows its name without the namespace
        and its full path in a tooltip.
        """
        try:
            items, roots = self.session.hierarchy_structure(nodes)
            if not items:
                tree_widget.create_item(["No Objects"])
                return
            children: Dict[Any, List[str]] = {}
            for key, info in items.items():
                children.setdefault(info["parent"], []).append(key)
            self.logger.debug(
                f"Tree building for {tree_type}: {len(items)} items, {len(roots)} roots"
            )

            def add(key, parent_item=None):
                info = items[key]
                name = (
                    info["display_name"]
                    if tree_type == "reference"
                    else info["short_name"]
                )
                item = tree_widget.create_item(
                    [name, info["type"]], info["object"], parent_item
                )
                icon = self._icon(info["node_name"])
                if icon:
                    item.setIcon(0, icon)
                try:
                    item._raw_name = info["short_name"]
                except Exception:
                    pass
                if tree_type == "reference":
                    item.setToolTip(0, f"Full Name: {key}\nType: {info['type']}")
                for child in sorted(children.get(key, [])):
                    add(child, item)

            for root in sorted(roots):
                add(root)
            tree_widget.expandToDepth(0)
            self.logger.debug(
                f"Populated {tree_type} tree with {len(items)} objects in hierarchy."
            )
        except Exception as e:
            self.logger.error(f"Error populating {tree_type} tree with hierarchy: {e}")
            tree_widget.create_item([f"Error: {e}"])

    def _icon(self, node_name):
        """The host's icon for a node (``NodeIcons``), or ``None``."""
        try:
            return self._ctrl.tk.NodeIcons.get_icon(node_name)
        except Exception:
            return None

    # ------------------------------------------------------------------ diff colours
    def apply_difference_formatting(self, tree001, tree000) -> None:
        """Colour the diff into both trees (tint selection while it shows)."""
        if not self._ctrl.diff_result:
            return
        try:
            for tree_widget in (tree001, tree000):
                self.clear_tree_colors(tree_widget)
                tree_widget.selection_style = "tint"
            matcher = self.matcher()
            self.format_tree_differences(
                tree001, "current", matcher, *matcher.build_tree_index(tree001)
            )
            self.format_tree_differences(
                tree000, "reference", matcher, *matcher.build_tree_index(tree000)
            )
        except Exception as e:
            self.logger.error(f"Error applying difference formatting: {e}")

    def clear_tree_colors(self, tree_widget) -> None:
        """Drop the diff's colours and tooltips from every item; selection
        back to its border style."""
        try:
            default_brush = QtGui.QBrush()
            for item in TreePathMatcher.iter_items(tree_widget):
                for col in range(tree_widget.columnCount()):
                    item.setForeground(col, default_brush)
                    item.setBackground(col, default_brush)
                orig_tip = item.data(0, ORIG_TOOLTIP_ROLE)
                if orig_tip is not None:
                    item.setToolTip(0, orig_tip)
                    item.setData(0, ORIG_TOOLTIP_ROLE, None)
            tree_widget.selection_style = "border"
            # A transparent-selection block an earlier version appended.
            ss = tree_widget.styleSheet()
            if "selection-background-color: transparent" in ss:
                cleaned = re.sub(
                    r"\s*QTreeWidget\s*\{\s*selection-background-color:\s*transparent;\s*\}"
                    r"\s*QTreeWidget::item:selected\s*\{[^}]*\}"
                    r"\s*QTreeWidget::item:hover:!selected\s*\{[^}]*\}",
                    "",
                    ss,
                )
                tree_widget.setStyleSheet(cleaned.strip())
        except Exception as e:
            self.logger.debug(f"Error clearing tree colors: {e}")

    def format_tree_differences(
        self, tree_widget, tree_type, matcher, by_full, by_clean, by_last
    ) -> None:
        """Colour one tree: extras and the current side of a reparent in the
        current tree, missing nodes and the reference side in the reference
        tree, fuzzy matches in both."""
        diff = self._ctrl.diff_result
        if not diff:
            return

        def mark(path, category, tooltip):
            candidates, strategy = matcher.find_path_matches(
                path, by_full, by_clean, by_last, prefer_cleaned=True, strict=False
            )
            self.logger.debug(
                f"[DIFF-FMT] {tree_type}: '{path}' -> "
                + (f"found via {strategy}" if candidates else "NOT FOUND")
            )
            if not candidates:
                return
            item = candidates[0]
            self._apply_diff_color(item, category, tooltip)
            self._expand_parents(item)

        try:
            if tree_type == "current":
                for path in diff.get("extra", []):
                    mark(path, "extra", f"Extra — not in reference\n{path}")
                for entry in diff.get("reparented", []):
                    if entry.get("current_path"):
                        mark(
                            entry["current_path"],
                            "reparented",
                            f"Reparented — was at:\n{entry.get('reference_path', '')}",
                        )
                for entry in diff.get("fuzzy_matches", []):
                    if entry.get("current_name"):
                        mark(
                            entry["current_name"],
                            "fuzzy",
                            f"Fuzzy match — reference name:\n{entry.get('target_name', '')}",
                        )
            else:
                for path in diff.get("missing", []):
                    mark(path, "missing", f"Missing — not in current scene\n{path}")
                for entry in diff.get("reparented", []):
                    if entry.get("reference_path"):
                        mark(
                            entry["reference_path"],
                            "reparented",
                            f"Reparented — now at:\n{entry.get('current_path', '')}",
                        )
                for entry in diff.get("fuzzy_matches", []):
                    if entry.get("target_name"):
                        mark(
                            entry["target_name"],
                            "fuzzy",
                            f"Fuzzy match — current name:\n{entry.get('current_name', '')}",
                        )
        except Exception as e:
            self.logger.error(f"Error formatting tree differences: {e}")

    def _apply_diff_color(self, item, diff_type: str, tooltip: str = "") -> None:
        """Colour *item* for *diff_type* and add *tooltip* under its own."""
        pair = self.DIFF_COLORS.get(diff_type)
        if pair is None:
            return
        fg_hex, bg_hex = pair
        if not fg_hex:
            return
        for col in range(item.treeWidget().columnCount()):
            item.setForeground(col, QtGui.QBrush(QtGui.QColor(fg_hex)))
            if bg_hex:
                item.setBackground(col, QtGui.QBrush(QtGui.QColor(bg_hex)))
        if tooltip:
            if item.data(0, ORIG_TOOLTIP_ROLE) is None:
                item.setData(0, ORIG_TOOLTIP_ROLE, item.toolTip(0) or "")
            original = item.data(0, ORIG_TOOLTIP_ROLE) or ""
            item.setToolTip(0, f"{original}\n\n{tooltip}" if original else tooltip)

    @staticmethod
    def _expand_parents(item) -> int:
        """Expand *item*'s ancestors; returns how many were collapsed."""
        count = 0
        parent = item.parent()
        while parent:
            if not parent.isExpanded():
                parent.setExpanded(True)
                count += 1
            parent = parent.parent()
        return count

    # ------------------------------------------------------------------ ignored items
    def apply_ignore_styling(self, tree_widget) -> None:
        """Style the ignored items: a directly ignored one struck through and
        dimmed, one under an ignored ancestor italic and dimmed; with Hide
        Ignored on, both are hidden instead."""
        ignored = self._ctrl.ignored_set(tree_widget)
        hide = self._ctrl.hide_ignored
        direct_fg = QtGui.QColor("#666666")
        inherited_fg = QtGui.QColor("#888888")
        for item in TreePathMatcher.iter_items(tree_widget):
            path = self.build_item_path(item)
            font = item.font(0)
            direct = path in ignored
            inherited = not direct and self._ctrl.is_path_ignored(tree_widget, path)
            if direct or inherited:
                font.setStrikeOut(direct)
                font.setItalic(inherited)
                fg = QtGui.QBrush(direct_fg if direct else inherited_fg)
                for col in range(tree_widget.columnCount()):
                    item.setFont(col, font)
                    item.setForeground(col, fg)
                    item.setBackground(col, QtGui.QBrush())
            elif font.strikeOut() or font.italic():
                font.setStrikeOut(False)
                font.setItalic(False)
                for col in range(tree_widget.columnCount()):
                    item.setFont(col, font)
            item.setHidden(hide and (direct or inherited))

    # ------------------------------------------------------------------ queries
    @staticmethod
    def build_item_path(item) -> str:
        """*item*'s display path (what the ignored paths store)."""
        parts = []
        current = item
        while current:
            parts.insert(0, current.text(0))
            current = current.parent()
        return "|".join(parts)

    #: Every item of a tree, depth first in display order.
    iter_items = staticmethod(TreePathMatcher.iter_items)

    def selected_item_keys(self, tree_widget) -> List[str]:
        """The names the host takes the selected items' nodes by (a pull's
        targets: ``TreePathMatcher.item_key``), ignored items and prompt rows
        left out. The ignored paths are TREE paths, the keys the nodes' own."""
        matcher = self.matcher()
        keys = []
        for item in self.get_selected_tree_items(tree_widget):
            if self._ctrl.is_path_ignored(tree_widget, self.build_item_path(item)):
                continue
            key = matcher.item_key(item)
            if key:
                keys.append(key)
        return keys

    def get_selected_tree_items(self, tree_widget) -> list:
        """*tree_widget*'s selected items, in selection order."""
        try:
            return tree_widget.selectedItems()
        except Exception as e:
            self.logger.debug(f"Error getting selected tree items: {e}")
            return []

    @staticmethod
    def count_tree_items(tree_widget) -> int:
        """How many items *tree_widget* holds."""
        return sum(1 for _ in TreePathMatcher.iter_items(tree_widget))

    # ------------------------------------------------------------------ selection kept
    def store_tree_selection(self, tree_widget) -> List[str]:
        """The selected items' paths."""
        return [
            self.build_item_path(item)
            for item in TreePathMatcher.iter_items(tree_widget)
            if item.isSelected()
        ]

    def restore_tree_selection(self, tree_widget, selected_paths) -> int:
        """Select the items at *selected_paths*; returns how many were found."""
        tree_widget.clearSelection()
        wanted = set(selected_paths)
        restored = 0
        for item in TreePathMatcher.iter_items(tree_widget):
            if self.build_item_path(item) in wanted:
                item.setSelected(True)
                restored += 1
        return restored

    def get_tree_structure(self, tree_widget) -> List[str]:
        """Every item's path, sorted: equal before and after a refresh when the
        hierarchy did not change."""
        return sorted(
            self.build_item_path(item)
            for item in TreePathMatcher.iter_items(tree_widget)
        )

    # ------------------------------------------------------------------ diff selection
    @staticmethod
    def condense_to_roots(paths) -> List[str]:
        """Drop paths whose ancestor is also in *paths* (keep shallow roots)."""
        condensed: List[str] = []
        for path in sorted(paths, key=lambda p: p.count("|")):
            if not any(path.startswith(root + "|") for root in condensed):
                condensed.append(path)
        return condensed

    @staticmethod
    def filter_to_leaves(paths) -> List[str]:
        """Keep only paths that are not a parent of another path in *paths*."""
        ordered = sorted(paths, key=lambda p: p.count("|"), reverse=True)
        return [
            p
            for p in ordered
            if not any(o != p and o.startswith(p + "|") for o in ordered)
        ]

    @classmethod
    def _select_and_reveal(cls, candidates) -> int:
        """Select *candidates* and expand their ancestors; returns how many
        were newly selected."""
        count = 0
        for item in candidates:
            if not item.isSelected():
                item.setSelected(True)
                count += 1
                cls._expand_parents(item)
        return count

    def apply_diff_options(
        self,
        tree001,
        tree000,
        auto_select: bool,
        expand_diff: bool,
        select_root_only: bool = False,
        select_leaves_only: bool = False,
    ) -> None:
        """Select and expand the diff in the trees.

        Missing nodes go to the reference tree (*tree000*), extras to the
        current tree (*tree001*), reparented and fuzzy-matched nodes to both.
        With fuzzy matching, a missing path no item matches tries its parent's
        closest-named child, then its name with a ``_GRP`` / ``_LOC`` number
        suffix dropped. Each selected item's subtree is selected with it.
        """
        diff = self._ctrl.diff_result
        if not diff:
            return
        if auto_select:
            self._auto_select_diff(
                diff, tree001, tree000, select_root_only, select_leaves_only
            )
        if expand_diff:
            self._expand_diff(diff, tree000, tree001)
        if auto_select:
            self._report_selection(tree000, tree001)

    def _condensed(self, paths, tree, select_root_only, select_leaves_only):
        """*paths* condensed to their roots or leaves as asked, ignored ones out."""
        if select_root_only and paths:
            paths = self.condense_to_roots(paths)
        elif select_leaves_only and paths:
            paths = self.filter_to_leaves(paths)
        return [p for p in paths if not self._ctrl.is_path_ignored(tree, p)]

    def _auto_select_diff(
        self, diff, tree001, tree000, select_root_only, select_leaves_only
    ) -> None:
        """Select the diff's items in both trees (:meth:`apply_diff_options`)."""
        strict = not self.session.fuzzy_matching

        def condensed(paths, tree):
            return self._condensed(paths, tree, select_root_only, select_leaves_only)

        tree001.clearSelection()
        tree000.clearSelection()
        matcher = self.matcher()
        ref_index = matcher.build_tree_index(tree000)
        cur_index = matcher.build_tree_index(tree001)
        selected = 0

        unresolved_missing = []
        for path in condensed(diff.get("missing", []), tree000):
            candidates, strategy = matcher.find_path_matches(
                path, *ref_index, prefer_cleaned=True, strict=strict
            )
            if not candidates:
                unresolved_missing.append(path)
                continue
            self.logger.debug(
                f"Missing '{path}' -> {len(candidates)} via {strategy}"
            )
            selected += self._select_and_reveal(candidates)

        if unresolved_missing and not strict:
            unresolved_missing, found = self._select_fuzzy_children(
                unresolved_missing, matcher, ref_index
            )
            selected += found

        unresolved_extra = []
        for path in condensed(diff.get("extra", []), tree001):
            candidates, strategy = matcher.find_path_matches(
                path, *cur_index, prefer_cleaned=False, strict=strict
            )
            if not candidates:
                unresolved_extra.append(path)
                continue
            matcher.log_matching_debug(path, candidates, strategy, "Extra")
            selected += self._select_and_reveal(candidates)

        for diff_key, ref_key, cur_key in (
            ("reparented", "reference_path", "current_path"),
            ("fuzzy_matches", "target_name", "current_name"),
        ):
            for entry in diff.get(diff_key, []):
                for key, index in ((ref_key, ref_index), (cur_key, cur_index)):
                    path = entry.get(key, "")
                    if path:
                        candidates, _ = matcher.find_path_matches(
                            path, *index, prefer_cleaned=True, strict=False
                        )
                        selected += self._select_and_reveal(candidates)

        if unresolved_missing and not strict:
            unresolved_missing, found = self._select_suffix_variants(
                unresolved_missing, matcher, ref_index
            )
            selected += found

        for tree in (tree000, tree001):
            for item in list(TreePathMatcher.iter_items(tree)):
                if item.isSelected() and item.childCount():
                    selected += self._select_children(item)

        if unresolved_missing or unresolved_extra:
            self.logger.warning(
                f"Unresolved diff paths (missing={len(unresolved_missing)}, "
                f"extra={len(unresolved_extra)}) "
                f"sample missing={unresolved_missing[:5]} "
                f"extra={unresolved_extra[:5]}"
            )
        self.logger.debug(f"Auto-selected {selected} diff items")
        for tree in (tree000, tree001):
            tree.viewport().update()

    def _expand_diff(self, diff, tree000, tree001) -> None:
        """Expand the parents of every item the diff names (:meth:`apply_diff_options`)."""
        ctrl = self._ctrl
        expanded = 0
        for diff_key, entry_key, tree in (
            ("missing", None, tree000),
            ("extra", None, tree001),
            ("reparented", "reference_path", tree000),
            ("reparented", "current_path", tree001),
            ("fuzzy_matches", "target_name", tree000),
            ("fuzzy_matches", "current_name", tree001),
        ):
            for entry in diff.get(diff_key, []):
                path = entry.get(entry_key, "") if entry_key else entry
                if not path or ctrl.is_path_ignored(tree, path):
                    continue
                for item in tree.findItems(
                    path.split("|")[-1], QtCore.Qt.MatchRecursive
                ):
                    if self._matches_hierarchy_path(item, path):
                        expanded += self._expand_parents(item)
        if expanded:
            self.logger.debug(f"Expanded {expanded} nodes showing differences")

    def _report_selection(self, tree000, tree001) -> None:
        """Focus the tree holding more of the selection and say what was selected."""
        n_ref = sum(
            1 for i in TreePathMatcher.iter_items(tree000) if i.isSelected()
        )
        n_cur = sum(
            1 for i in TreePathMatcher.iter_items(tree001) if i.isSelected()
        )
        (tree000 if n_ref >= n_cur else tree001).setFocus()
        if n_ref or n_cur:
            self.logger.success(
                f"Auto-select complete: {n_ref} item(s) in the REFERENCE tree, "
                f"{n_cur} in the CURRENT tree. "
                "Use 'Pull' to import missing or 'Fix' to repair."
            )
        else:
            self.logger.warning("No items remain selected after auto-select.")

    def _select_fuzzy_children(self, unresolved, matcher, ref_index):
        """Select, for each unresolved missing path whose parent resolves to
        one item, that parent's closest-named child. Returns the paths still
        unresolved and how many items were selected."""
        still, selected = [], 0
        for path in unresolved:
            if "|" not in path:
                still.append(path)
                continue
            parent_path, last = path.rsplit("|", 1)
            parents, _ = matcher.find_path_matches(
                parent_path, *ref_index, prefer_cleaned=True, strict=False
            )
            if len(parents) != 1:
                still.append(path)
                continue
            parent = parents[0]
            names = [parent.child(i).text(0) for i in range(parent.childCount())]
            try:
                matches = (
                    ptk.FuzzyMatcher.find_all_matches(
                        [last], names, score_threshold=0.6
                    )
                    if names
                    else {}
                )
            except Exception as e:
                self.logger.debug(f"Fuzzy match error for '{path}': {e}")
                matches = {}
            if not matches:
                still.append(path)
                continue
            matched, score = matches[next(iter(matches))]
            child = next(
                (
                    parent.child(i)
                    for i in range(parent.childCount())
                    if parent.child(i).text(0) == matched
                ),
                None,
            )
            if child is None:
                still.append(path)
                continue
            selected += self._select_and_reveal([child])
            self.logger.debug(
                f"Fuzzy child match: '{path}' -> '{matched}' (score {score:.2f})"
            )
        return still, selected

    def _select_suffix_variants(self, unresolved, matcher, ref_index):
        """Select each unresolved missing path with a ``_GRP`` / ``_LOC``
        number suffix dropped (``ARM_GRP1`` -> ``ARM_GRP``). Returns the paths
        still unresolved and how many items were selected."""
        pattern = re.compile(r"(.+_(?:GRP|LOC))\d+$")
        still, selected = [], 0
        for path in unresolved:
            parts = [pattern.match(c) for c in path.split("|")]
            if not any(parts):
                still.append(path)
                continue
            variant = "|".join(
                m.group(1) if m else c for m, c in zip(parts, path.split("|"))
            )
            candidates, _ = matcher.find_path_matches(
                variant, *ref_index, prefer_cleaned=True, strict=False
            )
            if candidates:
                selected += self._select_and_reveal(candidates)
            else:
                still.append(path)
        return still, selected

    def _select_children(self, item) -> int:
        """Select *item*'s subtree, ignored paths left out; returns how many
        were newly selected."""
        count = 0
        tree_widget = item.treeWidget()
        for i in range(item.childCount()):
            child = item.child(i)
            if self._ctrl.is_path_ignored(tree_widget, self.build_item_path(child)):
                continue
            if not child.isSelected():
                child.setSelected(True)
                count += 1
            count += self._select_children(child)
        return count

    def _matches_hierarchy_path(self, tree_item, full_path: str) -> bool:
        """Whether *tree_item* is the node at *full_path* (exact, cleaned, or
        one path ending the other)."""
        try:
            item_path = self.build_item_path(tree_item)
            clean = self.session.clean_path(full_path)
            return (
                item_path == clean
                or item_path == full_path
                or item_path.endswith(clean)
                or clean.endswith(item_path)
            )
        except Exception:
            return False
