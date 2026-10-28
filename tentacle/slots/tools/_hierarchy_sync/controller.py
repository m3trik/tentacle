# !/usr/bin/python
# coding=utf-8
"""The Hierarchy Sync panel's state: the reference path, the paths the user
ignored in each tree, the trees' refresh, and the diff's log and report.

The host half -- the reference held in the scene, the analysis, the repairs
and the scene edits -- is the host library's ``HierarchySyncSession``
(:attr:`HierarchySyncController.session`, built from ``Slots.tk``); the trees'
drawing is the renderer's
(:class:`~tentacle.slots.tools._hierarchy_sync.tree_renderer.HierarchyTreeRenderer`).

Private to :mod:`tentacle.slots.tools.hierarchy_sync`.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import pythontk as ptk

from .tree_renderer import HierarchyTreeRenderer

#: How many recent reference scenes the history keeps.
RECENT_LIMIT = 10

#: How many entries a diff log box lists before "... and N more".
LOG_LIMIT = 10


class HierarchySyncController(ptk.LoggingMixin):
    """The panel's state and the orchestration between it, the host's session
    and the trees. Logs through the panel's logger."""

    def __init__(self, slots):
        super().__init__()
        self.sb = slots.sb
        self.ui = slots.ui
        #: The host toolkit (``Slots.tk``).
        self.tk = slots.tk
        self.use_logger(slots.logger)
        #: The host's half: the reference held for the diff, the analysis and
        #: every scene operation.
        self.session = self.tk.HierarchySyncSession()
        self._reference_path = ""
        #: True while the reference loads: a scene callback it triggers must
        #: not rebuild the current-scene tree mid-load.
        self.importing_reference = False
        #: The paths the user ignored, per tree (display paths: what
        #: ``HierarchyTreeRenderer.build_item_path`` gives).
        self._ignored_ref_paths = set()
        self._ignored_cur_paths = set()
        #: Hide ignored items instead of dimming them (header menu toggle).
        self.hide_ignored = False
        #: The trees' renderer.
        self.tree = HierarchyTreeRenderer(self)

    # ------------------------------------------------------------------ reference
    @property
    def diff_result(self) -> Optional[dict]:
        """The session's last analysis (``None`` before one)."""
        return self.session.diff_result

    @property
    def reference_path(self) -> str:
        """The reference scene's path (``""`` when none is set)."""
        return self._reference_path

    @reference_path.setter
    def reference_path(self, text: str) -> None:
        """Set the reference and show it: its tree, an error, or the prompt."""
        text = (text or "").strip()
        if text == self._reference_path:
            return
        self._reference_path = text
        self.logger.debug(f"Reference path changed: {text}")
        if not text:
            self.clear_analysis()
            self.tree.show_reference_placeholder(self.ui.tree000)
        elif not os.path.exists(text):
            self.clear_analysis()
            self.tree.show_reference_error(
                self.ui.tree000, Path(text).stem, "File Not Found"
            )
        else:
            self.populate_reference_tree(self.ui.tree000, text)
        self.update_header_tooltips()

    def update_header_tooltips(self) -> None:
        """Each tree's header tooltip: its file's full path."""
        self.ui.tree000.headerItem().setToolTip(
            0, self._reference_path or "No reference scene set"
        )
        self.ui.tree001.headerItem().setToolTip(
            0, self.session.scene_path() or "Untitled"
        )

    def clear_analysis(self) -> None:
        """Drop the analysis and the held reference (the session's) and the
        ignored paths (they named the old analysis' trees)."""
        self.session.clear_analysis()
        self.clear_ignored_paths()

    def on_window_hidden(self) -> None:
        """Release the reference while the panel is hidden."""
        self.session.release_reference()
        self.ui.tree000.clear()
        self.logger.debug("Reference scene released on window hide.")

    # ------------------------------------------------------------------ trees
    def populate_reference_tree(self, tree_widget, reference_path: str = None) -> None:
        """Fill the reference tree from *reference_path*, loading it (or
        reusing the held load). A different reference drops the analysis."""
        if not (reference_path and self.session.is_loaded(reference_path)):
            self.clear_analysis()
        name = (
            Path(reference_path).stem if reference_path else ""
        ) or "Reference Scene"
        if not reference_path:
            self.tree.show_reference_placeholder(tree_widget, name)
            return
        if not os.path.exists(reference_path):
            self.tree.show_reference_error(tree_widget, name)
            return
        try:
            self.importing_reference = True
            nodes = self.session.load_reference(reference_path)
            if not nodes:
                self.tree.show_reference_error(
                    tree_widget, name, "Failed to load reference"
                )
                return
            self.tree.populate_reference_tree(tree_widget, nodes, name)
        except Exception as e:
            self.logger.error(f"Error loading reference hierarchy: {e}")
            self.tree.show_reference_error(tree_widget, name, f"Error: {e}")
        finally:
            self.importing_reference = False

    def refresh_trees(self, restore_selection: bool = True) -> None:
        """Rebuild both trees.

        Parameters:
            restore_selection: Keep each tree's selection when its hierarchy
                did not change; ``False`` after an edit that makes the old
                selection meaningless (a fix, a pull).
        """
        tree000, tree001 = self.ui.tree000, self.ui.tree001
        if restore_selection:
            kept = {
                tree: (
                    self.tree.store_tree_selection(tree),
                    self.tree.get_tree_structure(tree),
                )
                for tree in (tree001, tree000)
            }

        self.tree.populate_current_scene_tree(tree001)
        if self._reference_path:
            self.populate_reference_tree(tree000, self._reference_path)

        restored = 0
        if restore_selection:
            for tree, (selection, structure) in kept.items():
                if tree is tree000 and not self._reference_path:
                    continue
                if selection and structure == self.tree.get_tree_structure(tree):
                    restored += self.tree.restore_tree_selection(tree, selection)
        if restored:
            self.logger.success(
                f"Refreshed trees and restored {restored} selections (hierarchy unchanged)."
            )
        else:
            self.logger.result(
                "Refreshed trees (hierarchy may have changed — selection cleared)."
            )
        self.tree.apply_ignore_styling(tree000)
        self.tree.apply_ignore_styling(tree001)

    def refresh_styling(self) -> None:
        """Diff colours (or none), then the ignored styling, on both trees."""
        tree000, tree001 = self.ui.tree000, self.ui.tree001
        if self.diff_result:
            self.tree.apply_difference_formatting(tree001, tree000)
        else:
            self.tree.clear_tree_colors(tree001)
            self.tree.clear_tree_colors(tree000)
        self.tree.apply_ignore_styling(tree000)
        self.tree.apply_ignore_styling(tree001)

    # ------------------------------------------------------------------ ignored paths
    def ignored_set(self, tree_widget) -> set:
        """The ignored paths of *tree_widget* (an empty set for another widget)."""
        if tree_widget is self.ui.tree000:
            return self._ignored_ref_paths
        if tree_widget is self.ui.tree001:
            return self._ignored_cur_paths
        return set()

    def is_path_ignored(self, tree_widget, path: str) -> bool:
        """Whether *path*, or an ancestor of it, is ignored in *tree_widget*."""
        ignored = self.ignored_set(tree_widget)
        return path in ignored or any(path.startswith(ip + "|") for ip in ignored)

    def clear_ignored_paths(self) -> None:
        """Forget every ignored path, in both trees."""
        self._ignored_ref_paths.clear()
        self._ignored_cur_paths.clear()

    def effective_diff(self) -> Dict[str, list]:
        """The analysis' differences, the ignored paths left out (a reparent or
        fuzzy match drops when either side is ignored)."""
        diff = self.diff_result
        if not diff:
            return {"missing": [], "extra": [], "reparented": [], "fuzzy_matches": []}
        ref, cur = self.ui.tree000, self.ui.tree001
        return {
            "missing": [
                p for p in diff.get("missing", []) if not self.is_path_ignored(ref, p)
            ],
            "extra": [
                p for p in diff.get("extra", []) if not self.is_path_ignored(cur, p)
            ],
            "reparented": [
                r
                for r in diff.get("reparented", [])
                if not self.is_path_ignored(cur, r.get("current_path", ""))
                and not self.is_path_ignored(ref, r.get("reference_path", ""))
            ],
            "fuzzy_matches": [
                f
                for f in diff.get("fuzzy_matches", [])
                if not self.is_path_ignored(cur, f.get("current_name", ""))
                and not self.is_path_ignored(ref, f.get("target_name", ""))
            ],
        }

    # ------------------------------------------------------------------ the diff's log
    def log_diff_results(self) -> None:
        """Log the differences (ignored ones left out): the top-level missing
        and extra nodes, the reparented, the fuzzy matches, and a link to the
        full report."""
        if not self.diff_result:
            self.logger.error(
                "No diff results available. Please analyze hierarchies first."
            )
            return
        effective = self.effective_diff()
        missing, extra = effective["missing"], effective["extra"]
        reparented, fuzzy = effective["reparented"], effective["fuzzy_matches"]
        sidecar = ptk.SceneDataSidecarBase

        self.logger.log_divider()
        for paths, sign, title, level, linked in (
            (missing, "-", "MISSING IN CURRENT SCENE", "WARNING", False),
            (extra, "+", "EXTRA IN CURRENT SCENE", "INFO", True),
        ):
            if not paths:
                continue
            top = sidecar.get_top_level(paths)
            path_set = set(paths)
            items = []
            for t in top[:LOG_LIMIT]:
                count = sidecar.count_descendants(t, path_set)
                label = self.logger.log_link(t, "select", node=t) if linked else t
                items.append(
                    f"  {sign} {label}" + (f"  ({count} nodes)" if count > 1 else "")
                )
            if len(top) > LOG_LIMIT:
                items.append(f"  ... and {len(top) - LOG_LIMIT} more top-level")
            self.logger.log_box(
                f"{title} ({len(paths)} nodes, {len(top)} top-level)",
                items,
                level=level,
            )
        if reparented:
            items = [
                "  ~ "
                + self.logger.log_link(
                    r.get("leaf", ""), "select", node=r.get("current_path", "")
                )
                for r in reparented[:LOG_LIMIT]
            ]
            if len(reparented) > LOG_LIMIT:
                items.append(f"  ... and {len(reparented) - LOG_LIMIT} more")
            self.logger.log_box(
                f"REPARENTED OBJECTS ({len(reparented)})", items, level="WARNING"
            )
        if fuzzy:
            self.log_table(
                data=[
                    [m.get("current_name", ""), m.get("target_name", "")]
                    for m in fuzzy[:LOG_LIMIT]
                ],
                headers=["Current", "Reference"],
                title=f"FUZZY MATCHES ({len(fuzzy)})",
            )
            if len(fuzzy) > LOG_LIMIT:
                self.logger.notice(
                    f"  ... and {len(fuzzy) - LOG_LIMIT} more fuzzy matches"
                )

        if not missing and not extra and not reparented:
            self.logger.success("Hierarchies match perfectly!")
        else:
            self.logger.warning(
                f"Found {len(missing) + len(extra) + len(reparented)} hierarchy differences"
            )
            report = self.write_diff_report(missing, extra, reparented, fuzzy)
            if report:
                self.logger.info(
                    self.logger.log_link("Open full diff report", "open", path=report)
                )
        self.logger.log_divider()

    @staticmethod
    def write_diff_report(missing, extra, reparented, fuzzy_matches) -> Optional[str]:
        """Write the full diff to a text file.

        Detached: the user opens it after this returns, so nothing deletes it
        here; allocation sweeps earlier sessions' reports (``TempArtifacts``).

        Returns:
            The file's path, or ``None`` when it could not be written.
        """
        lines = [
            "Hierarchy Diff Report",
            "=" * 60,
            "",
            "Summary",
            "-" * 40,
            f"  Missing in current scene:  {len(missing)}",
            f"  Extra in current scene:    {len(extra)}",
            f"  Reparented:                {len(reparented)}",
            f"  Fuzzy matches:             {len(fuzzy_matches)}",
            f"  Total differences:         {len(missing) + len(extra) + len(reparented)}",
            "",
        ]
        if missing:
            lines += [f"Missing in current scene ({len(missing)}):"]
            lines += [f"  - {p}" for p in missing] + [""]
        if extra:
            lines += [f"Extra in current scene ({len(extra)}):"]
            lines += [f"  + {p}" for p in extra] + [""]
        if reparented:
            lines += [f"Reparented ({len(reparented)}):"]
            for r in reparented:
                lines += [
                    f"  ~ {r.get('leaf', '')}",
                    f"      reference: {r.get('reference_path', '')}",
                    f"      current:   {r.get('current_path', '')}",
                ]
            lines += [""]
        if fuzzy_matches:
            lines += [f"Fuzzy matches ({len(fuzzy_matches)}):"]
            lines += [
                f"  {m.get('current_name', '')}  <->  {m.get('target_name', '')}  "
                f"({m.get('score', 0):.0%} match)"
                for m in fuzzy_matches
            ]
        try:
            path = ptk.TempArtifacts("hierarchy_diff").path(extension=".txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            return path
        except OSError:
            return None

    # ------------------------------------------------------------------ recent references
    @staticmethod
    def coerce_str_list(value) -> List[str]:
        """A settings value as a list: QSettings hands a one-item list back as
        a bare string."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    def get_recent_reference_scenes(self) -> List[str]:
        """The recent reference scenes that still exist (the last ten)."""
        recent = self.coerce_str_list(
            self.ui.settings.value("recent_reference_scenes", [])
        )
        return [scene for scene in recent if os.path.exists(scene)][-RECENT_LIMIT:]

    def save_recent_reference_scene(self, scene_path: str) -> None:
        """Put *scene_path* last in the recent references (the last ten kept)."""
        if not scene_path:
            return
        scene_path = str(Path(scene_path).resolve())
        recent = self.coerce_str_list(
            self.ui.settings.value("recent_reference_scenes", [])
        )
        if scene_path in recent:
            recent.remove(scene_path)
        recent.append(scene_path)
        self.ui.settings.setValue("recent_reference_scenes", recent[-RECENT_LIMIT:])
