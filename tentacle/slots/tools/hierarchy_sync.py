# !/usr/bin/python
# coding=utf-8
"""Hierarchy Sync: diff the scene's hierarchy against a reference file, then
pull what the scene lacks or fix what drifted.

One Slots class for both hosts. The host half is the host library's
``HierarchySyncSession`` (``self.tk``): it holds the reference in the scene
(Maya: imported into a temporary namespace; Blender: linked as a library),
analyzes, pulls and repairs, and does the trees' scene edits -- rename,
reparent, delete, select. The panel's own state (the reference path, the
ignored paths, the trees' refresh, the diff's log) is the controller's
(:class:`~tentacle.slots.tools._hierarchy_sync.controller.HierarchySyncController`),
the trees' drawing its renderer's.
"""

import os
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets

import pythontk as ptk

from tentacle import Slots
from ._hierarchy_sync.controller import HierarchySyncController
from ._hierarchy_sync.tree_renderer import (
    BROWSE_PLACEHOLDER,
    OPEN_SCENE_PLACEHOLDER,
)


class HierarchySyncSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for the ``hierarchy_sync.ui`` panel."""

    #: The header menu's Log Level rows (index 1, INFO, is the default).
    _LOG_LEVELS = {
        "Log Level: DEBUG": 10,
        "Log Level: INFO": 20,
        "Log Level: WARNING": 30,
        "Log Level: ERROR": 40,
    }

    #: The quarantine group's name when the Fix options name none.
    DEFAULT_QUARANTINE_GROUP = "_QUARANTINE"

    #: The rows this panel builds at runtime (the header menu, the Diff and
    #: Pull option combos) and reads by name. No ``.ui`` declares them; saved
    #: settings key on these names, so they never change.
    RUNTIME_WIDGETS = (
        "chk002",
        "cmb001",
        "cmb_selection_mode",
        "chk_expand_diff",
        "chk_force_reanalysis",
        "chk_fuzzy_matching",
        "chk_filter_meshes",
        "chk_filter_cameras",
        "chk_filter_lights",
        "chk_ignore_quarantine",
        "cmb_pull_mode",
        "chk_pull_children",
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.hierarchy_sync
        self.ui.txt003.setText("")  # Log Output

        self.controller = HierarchySyncController(self)
        # The panel's log takes the panel's lines and everything the host's
        # session and engines report.
        for logger in (self.logger, *self.session.loggers()):
            logger.hide_logger_name(True)
            logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
            logger.setup_logging_redirect(self.ui.txt003)
        if hasattr(self.ui.txt003, "anchorClicked"):
            self.ui.txt003.anchorClicked.connect(self._on_log_link_clicked)

        # Middle-mouse drag in the current-scene tree reparents in the scene.
        self._tree001_drag_filter = self.sb.TreeDragReparentFilter(
            self.ui, reparent_callback=self._on_tree001_drop_reparent
        )

        if self.ui.footer:
            self.ui.footer.setDefaultStatusText(
                "Browse for a reference scene and click Diff or Pull to begin."
            )
        self._show_startup_text()

        jobs = self.tk.ScriptJobManager.instance()
        for event in ("SceneOpened", "NewSceneOpened"):
            try:
                jobs.subscribe(event, self._on_scene_changed, owner=self)
            except Exception as e:
                self.logger.debug(f"event {event!r} unavailable ({e})")
        jobs.connect_cleanup(self.ui, owner=self)
        # The reference is released while the panel is hidden.
        self.ui.on_hide.connect(self.controller.on_window_hidden)

        self.controller.update_header_tooltips()

    @property
    def session(self):
        """The host's ``HierarchySyncSession`` (the controller's)."""
        return self.controller.session

    def _on_log_link_clicked(self, url) -> None:
        """Run a log link (``action://``: select a node, open the report)."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    def _on_scene_changed(self) -> None:
        """A scene opened: the analysis is stale; while visible, show the new scene."""
        self.controller.clear_analysis()
        # Hidden, the reference was released (on_window_hidden): loading it
        # again here would bring it into the new scene unseen.
        if not self.ui.isVisible():
            return
        self.controller.tree.populate_current_scene_tree(self.ui.tree001)
        reference = self.controller.reference_path
        if reference and os.path.exists(reference):
            self.controller.populate_reference_tree(self.ui.tree000, reference)
        else:
            self.controller.tree.show_reference_placeholder(self.ui.tree000)
        self.controller.update_header_tooltips()
        self._show_startup_text()

    def _show_startup_text(self) -> None:
        """The log pane's opening text: the scene, the project, the workflow."""
        scene = self.session.scene_path()
        workspace = self.session.workspace() or "(not set)"
        self.ui.txt003.setHtml(
            '<span style="color:#aaa; font-size:11px;">'
            "<b>Hierarchy Sync</b><br>"
            f"Scene: {Path(scene).name if scene else 'Untitled'}<br>"
            f"Workspace: {workspace}<br><br>"
            "<b>Workflow:</b><br>"
            "&nbsp;&nbsp;1. Browse for a reference scene (folder icon in the source tree header).<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Open or switch scenes via the folder/history icons on the current scene tree header.<br>"
            "&nbsp;&nbsp;2. <b>Diff</b> &mdash; compare the current scene against the reference<br>"
            "&nbsp;&nbsp;3. <b>Pull</b> &mdash; select objects in the reference tree and bring them in<br>"
            "&nbsp;&nbsp;4. <b>Fix</b> &mdash; auto-repair: stubs, quarantine extras, fix reparented and renamed<br><br>"
            "Right-click the trees for more options. "
            "Enable <i>Dry Run</i> in the header menu to preview without changes."
            "</span>"
        )

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """The header menu (Dry Run, Log Level, Hide Ignored) and the help."""
        widget.menu.add(
            "QCheckBox",
            setText="Dry Run Mode",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Perform analysis without making actual changes.",
        )
        widget.menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb001",
            add=self._LOG_LEVELS,
            setCurrentIndex=1,
            setToolTip="Set the log level.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Hide Ignored",
            setObjectName="chk_hide_ignored",
            setChecked=False,
            setToolTip="Hide ignored items from the trees instead of dimming them.",
        )
        widget.menu.chk_hide_ignored.toggled.connect(self._on_hide_ignored_toggled)

        formats = " / ".join(self.session.reference_formats())
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Hierarchy Sync",
                body="Compare the scene's hierarchy against a reference file, "
                "then bring in what is missing or repair what drifted.",
                steps=[
                    "Click the <b>folder icon</b> in the source tree header to "
                    f"browse for a reference scene ({formats}).",
                    "Press <b>Diff</b> to compare the current scene against the "
                    "reference. Differences are highlighted in both trees and "
                    "logged below.",
                    "Select objects in the reference tree and press <b>Pull</b> "
                    "to bring them in at their reference hierarchy position.",
                    "Press <b>Fix</b> to repair: stub missing objects, quarantine "
                    "extras, fix reparented and renamed objects.",
                ],
                sections=[
                    (
                        "Header menu",
                        [
                            "<b>Dry Run</b> — preview changes without modifying the scene.",
                            "<b>Log Level</b> — control verbosity of the output panel.",
                            "<b>Hide Ignored</b> — hide ignored items from the "
                            "trees instead of dimming them.",
                        ],
                    ),
                ],
                notes=[
                    "<b>Right-click</b> either tree for more: refresh, show "
                    "differences, ignore items, select, rename or delete objects.",
                ],
            )
        )

    def _on_hide_ignored_toggled(self, state):
        """Hide the ignored items, or show them dimmed."""
        self.controller.hide_ignored = bool(state)
        self.controller.tree.apply_ignore_styling(self.ui.tree000)
        self.controller.tree.apply_ignore_styling(self.ui.tree001)

    # ------------------------------------------------------------------ trees
    def tree000_init(self, widget):
        """The reference tree: read-only, its menu, and its header's browse,
        history and refresh buttons."""
        if not getattr(widget, "is_initialized", False):
            widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            widget.configure_menu(hide_on_leave=True)
            for name, text, tip in (
                (
                    "b009",
                    "Refresh Reference",
                    "Refresh the reference hierarchy display.",
                ),
                (
                    "b012",
                    "Analyze Hierarchies",
                    "Analyze and compare the current scene with the reference hierarchy.",
                ),
                (
                    "b011",
                    "Show Differences",
                    "Highlight differences between hierarchies.",
                ),
            ):
                widget.menu.add(
                    "QPushButton", setText=text, setObjectName=name, setToolTip=tip
                )
            widget.menu.add("Separator")
            self._add_ignore_rows(widget, "b013", "b014")
            widget.itemClicked.connect(self._on_reference_tree_item_clicked)
            widget.header_actions.add(
                "browse",
                icon="folder",
                tooltip="Browse for reference scene",
                callback=self.b003,
            )
            widget.header_actions.add(
                "history",
                icon="history",
                tooltip="Recent reference scenes",
                callback=self._show_recent_references,
            )
            widget.header_actions.add(
                "refresh",
                icon="refresh",
                tooltip="Refresh reference tree",
                callback=self.b009,
            )
            widget.is_initialized = True
        # No load here: an explicit call fills it, so a re-init never re-imports.
        if not widget.topLevelItemCount():
            self.controller.tree.show_reference_placeholder(widget)

    @staticmethod
    def _add_ignore_rows(widget, ignore_name, unignore_name):
        widget.menu.add(
            "QPushButton",
            setText="Ignore Selected",
            setObjectName=ignore_name,
            setToolTip="Mark selected items as ignored (skipped during auto-selection and dimmed).",
        )
        widget.menu.add(
            "QPushButton",
            setText="Unignore Selected",
            setObjectName=unignore_name,
            setToolTip="Remove ignore mark from selected items.",
        )

    def tree001_init(self, widget):
        """The current-scene tree: its menu, Delete key, header buttons,
        in-place rename and drag-to-reparent; filled from the scene."""
        if not getattr(widget, "is_initialized", False):
            widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            widget.configure_menu(hide_on_leave=True)
            for name, text, tip in (
                (
                    "b005",
                    "Refresh Current Scene",
                    "Refresh the current scene hierarchy display.",
                ),
                (
                    "b006",
                    "Select Objects",
                    "Select the selected items' objects in the scene.",
                ),
                ("b007", "Expand All", "Expand all hierarchy items."),
                ("b008", "Collapse All", "Collapse all hierarchy items."),
            ):
                widget.menu.add(
                    "QPushButton", setText=text, setObjectName=name, setToolTip=tip
                )
            widget.menu.add("Separator")
            self._add_ignore_rows(widget, "b015", "b016")
            widget.menu.add("Separator")
            widget.menu.add(
                "QPushButton",
                setText="Rename from Reference",
                setObjectName="b017",
                setToolTip="Rename selected current-scene items using the names of selected "
                "reference-tree items (matched by order), or auto-apply fuzzy matches from "
                "the last diff if nothing is selected in the reference tree.",
            )
            widget.menu.add("Separator")
            widget.menu.add(
                "QPushButton",
                setText="Delete Selected",
                setObjectName="b018",
                setToolTip="Delete the selected objects from the scene.",
            )

            shortcut = QtWidgets.QShortcut(
                QtGui.QKeySequence(QtCore.Qt.Key_Delete), widget
            )
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.b018)
            widget._del_shortcut = shortcut  # keep it alive

            widget.header_actions.add(
                "open_scene",
                icon="folder",
                tooltip="Open a scene",
                callback=self._open_scene_dialog,
            )
            widget.header_actions.add(
                "recent_scenes",
                icon="history",
                tooltip="Recent scenes",
                callback=self._show_recent_scenes,
            )
            widget.itemClicked.connect(self._on_current_tree_item_clicked)
            widget.itemChanged.connect(self._on_current_tree_item_renamed)
            widget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            widget.setDefaultDropAction(QtCore.Qt.MoveAction)
            self._tree001_drag_filter.install(widget)
            widget.is_initialized = True
        self.controller.tree.populate_current_scene_tree(widget)

    def _on_reference_tree_item_clicked(self, item, column):
        """The Browse prompt opens the reference browser."""
        if item.data(0, QtCore.Qt.UserRole) == BROWSE_PLACEHOLDER:
            self.b003()

    def _on_current_tree_item_clicked(self, item, column):
        """The Open Scene prompt opens the scene browser."""
        if item.data(0, QtCore.Qt.UserRole) == OPEN_SCENE_PLACEHOLDER:
            self._open_scene_dialog()

    def _on_current_tree_item_renamed(self, item, column):
        """An edited name renames the item's node in the scene; a refused or
        failed rename puts the old name back."""
        if column != 0 or getattr(self, "_renaming_in_progress", False):
            return
        self._renaming_in_progress = True
        try:
            node = item.data(0, QtCore.Qt.UserRole)
            if not self.session.node_alive(node):
                return
            new_name = item.text(0).strip()
            old_name = self.session.node_name(node)
            if not new_name or new_name == old_name:
                return
            renamed = self.session.rename_nodes([(node, new_name)])[0]
            if renamed is None:
                item.setText(0, old_name)
                return
            actual = self._take_rename(item, node, renamed)
            # The host may have changed the name to keep it unique.
            if actual != new_name:
                item.setText(0, actual)
        finally:
            self._renaming_in_progress = False

    def _take_rename(self, item, node, renamed) -> str:
        """Point *item* at its renamed node; returns the node's new name."""
        role = QtCore.Qt.UserRole
        actual = self.session.node_name(renamed)
        item.setData(0, role, renamed)
        item._raw_name = actual
        self._patch_descendant_item_paths(item, node, renamed)
        return actual

    @staticmethod
    def _patch_descendant_item_paths(item, old_node, new_node) -> None:
        """Re-point *item*'s descendants at their renamed ancestor's new path.

        Only a node held by a path string embeds its ancestors' names (a Maya
        DAG path); an object reference (Blender) follows the rename by itself.
        """
        if not (isinstance(old_node, str) and isinstance(new_node, str)):
            return
        role = QtCore.Qt.UserRole
        prefix = old_node + "|"
        stack = [item.child(i) for i in range(item.childCount())]
        while stack:
            child = stack.pop()
            data = child.data(0, role)
            if isinstance(data, str) and data.startswith(prefix):
                child.setData(0, role, new_node + data[len(old_node) :])
            stack.extend(child.child(i) for i in range(child.childCount()))

    def _on_tree001_drop_reparent(self, moves):
        """Mirror a drag-drop in the current-scene tree in the scene.

        ``TreeDragReparentFilter`` hands over the whole dropped selection after
        Qt moved the items, as ``(item, new_parent_item)`` pairs
        (``new_parent_item`` ``None``: dropped at the root). Every node is read
        off its item up front -- the rebuild deletes the items -- and the
        session reparents them all as one undo step; one rebuild then shows
        the result (and undoes the visual move of any that failed).
        """
        role = QtCore.Qt.UserRole
        resolved = []
        for item, parent_item in moves:
            node = item.data(0, role)
            if not self.session.node_alive(node):
                continue
            parent = None
            if parent_item is not None:
                parent = parent_item.data(0, role)
                if not self.session.node_alive(parent):
                    self.logger.warning(
                        "Drop target has no scene object — reparent skipped."
                    )
                    continue
            resolved.append((node, parent))
        if resolved and self.session.reparent_nodes(resolved):
            self.controller.refresh_trees()

    def _open_scene_dialog(self):
        """Browse for a scene and open it."""
        files = self.sb.file_dialog(
            file_types=list(self.session.SCENE_FILE_TYPES),
            title="Open Scene:",
            start_dir=self.session.workspace(),
            filter_description="Scene Files",
        )
        if files:
            self._open_scene(files[0])

    def _open_scene(self, path: str) -> None:
        try:
            self.session.open_scene(path)
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def _show_recent_scenes(self):
        """A menu of the recently opened scenes; picking one opens it."""
        chosen = self._recent_menu(
            self.ui.tree001, self.session.recent_scenes(), "(No recent scenes)"
        )
        if chosen:
            self._open_scene(chosen)

    def _show_recent_references(self):
        """A menu of the recent reference scenes; picking one sets it."""
        chosen = self._recent_menu(
            self.ui.tree000,
            self.controller.get_recent_reference_scenes(),
            "(No recent files)",
        )
        if chosen:
            self.controller.reference_path = chosen
            self.controller.save_recent_reference_scene(chosen)

    def _recent_menu(self, parent, paths, empty_text):
        """Pop a menu of *paths* at the cursor; returns the path picked, or None."""
        menu = QtWidgets.QMenu(parent)
        self.sb.StyleSheet.cast_shadow(menu)
        menu.setToolTipsVisible(True)
        if not paths:
            menu.addAction(empty_text).setEnabled(False)
            menu.exec_(QtGui.QCursor.pos())
            return None
        for path in paths:
            action = menu.addAction(Path(path).name)
            action.setToolTip(path)
            action.setData(path)
        action = menu.exec_(QtGui.QCursor.pos())
        return action.data() if action else None

    # ------------------------------------------------------------------ options
    def cmb_diff_options_init(self, widget):
        """The Diff options, rows of the combo under the Diff button (each
        named, so it is ``self.ui.<name>``)."""
        rows = []
        cmb = self.sb.registered_widgets.ComboBox()
        cmb.setObjectName("cmb_selection_mode")
        cmb.setToolTip("Select how differences should be selected in trees.")
        cmb.add(
            {
                "Select: All Differences": "all",
                "Select: Root Only": "root_only",
                "Select: Leaves Only": "leaves_only",
                "Select: No Auto-Selection": "none",
            }
        )
        rows.append((cmb, "Selection Mode"))
        for name, text, checked, tip in (
            (
                "chk_expand_diff",
                "Expand Difference Nodes",
                True,
                "Automatically expand nodes with differences.",
            ),
            (
                "chk_force_reanalysis",
                "Force Re-analysis",
                False,
                "Load the reference again and re-analyze, even if it was already analyzed.",
            ),
            (
                "chk_fuzzy_matching",
                "Enable Fuzzy Matching",
                True,
                "Enable fuzzy name matching for improved object identification.",
            ),
            (
                "chk_filter_meshes",
                "Filter Mesh Objects",
                False,
                "Exclude mesh objects from the comparison. When unchecked, all "
                "objects (including geometry) are compared.",
            ),
            (
                "chk_filter_cameras",
                "Filter Cameras",
                False,
                "Exclude all camera objects from the comparison (Maya's default "
                "cameras -- persp, top, front, side -- are always excluded).",
            ),
            (
                "chk_filter_lights",
                "Filter Lights",
                False,
                "Exclude all light objects from the comparison.",
            ),
            (
                "chk_ignore_quarantine",
                "Ignore Quarantine Group",
                True,
                "Automatically ignore the quarantine group (e.g. _QUARANTINE) in the "
                "current scene tree during diff analysis.",
            ),
        ):
            rows.append(self._check_row(name, text, checked, tip))
        widget.add(rows, header="Diff Options", header_alignment="center", clear=True)
        widget.add_defaults_button = True

    def _check_row(self, name, text, checked, tip):
        chk = self.sb.registered_widgets.CheckBox()
        chk.setText(text)
        chk.setObjectName(name)
        chk.setChecked(checked)
        chk.setToolTip(tip)
        return chk, text

    def cmb_pull_options_init(self, widget):
        """The Pull options, rows of the combo under the Pull button."""
        cmb = self.sb.registered_widgets.ComboBox()
        cmb.setObjectName("cmb_pull_mode")
        cmb.setToolTip("Select how objects should be pulled into the scene.")
        cmb.add(
            {
                "Mode: Add to Scene": "Add to Scene",
                "Mode: Merge Hierarchies": "Merge Hierarchies",
            }
        )
        rows = [
            (cmb, "Pull Mode"),
            self._check_row(
                "chk_pull_children",
                "Pull Children",
                True,
                "Include all children when pulling. When enabled, complete subtrees "
                "are pulled; when disabled, only the selected objects are pulled.",
            ),
        ]
        widget.add(rows, header="Pull Options", header_alignment="center", clear=True)
        widget.add_defaults_button = True

    def tb002_init(self, widget):
        """The Pull button's tooltip."""
        widget.setToolTip(
            "Pull the objects selected in the reference tree into the current scene, "
            "each at its reference hierarchy position."
        )

    def tb003_init(self, widget):
        """The Fix button's option box: what a repair does."""
        menu = widget.option_box.menu
        menu.setTitle("Repair Options:")
        menu.add(
            "QCheckBox",
            setText="Create Stubs (Missing)",
            setObjectName="chk_fix_stubs",
            setChecked=True,
            setToolTip="Create empty placeholder objects for items missing from the current scene.",
        )
        menu.add(
            "QCheckBox",
            setText="Quarantine Extras",
            setObjectName="chk_fix_quarantine",
            setChecked=True,
            setToolTip="Move extra items (not in reference) to a quarantine group.",
        )
        menu.add(
            "QLineEdit",
            setObjectName="txt_quarantine_name",
            setPlaceholderText=self.DEFAULT_QUARANTINE_GROUP,
            setToolTip="Custom name for the quarantine group (leave blank for default).",
        )
        menu.add(
            "QCheckBox",
            setText="Skip Animated",
            setObjectName="chk_skip_animated",
            setChecked=True,
            setToolTip=(
                "Skip repairs that would change motion: extras that are animated "
                "(or ride an animated parent) are not quarantined, and keyed "
                "objects are not reparented."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Fix Reparented",
            setObjectName="chk_fix_reparented",
            setChecked=True,
            setToolTip="Move reparented nodes to match their reference hierarchy position.",
        )
        menu.add(
            "QCheckBox",
            setText="Fix Fuzzy Renames",
            setObjectName="chk_fix_fuzzy_renames",
            setChecked=True,
            setToolTip="Rename nodes identified as fuzzy matches to their reference names.",
        )

    def _quarantine_group(self) -> str:
        """The Fix options' quarantine group name, or the default."""
        name = self.ui.tb003.option_box.menu.txt_quarantine_name.text().strip()
        return name or self.DEFAULT_QUARANTINE_GROUP

    def _diff_filters(self) -> dict:
        """The Diff options the analysis takes."""
        return dict(
            fuzzy_matching=self.ui.chk_fuzzy_matching.isChecked(),
            filter_meshes=self.ui.chk_filter_meshes.isChecked(),
            filter_cameras=self.ui.chk_filter_cameras.isChecked(),
            filter_lights=self.ui.chk_filter_lights.isChecked(),
        )

    # ------------------------------------------------------------------ Diff / Pull / Fix
    def tb001(self, state=None):
        """Diff: analyze, colour the trees, log the differences, and select and
        expand them as the Diff options ask."""
        self.ui.txt003.clear()
        reference_path = self.controller.reference_path
        if not reference_path:
            self.logger.error("Please specify a reference scene path.")
            return
        if not os.path.exists(reference_path):
            self.logger.error(f"Reference scene does not exist: {reference_path}")
            return

        selection_mode = self.ui.cmb_selection_mode.currentData() or "all"
        expand_diff = self.ui.chk_expand_diff.isChecked()
        auto_select = selection_mode != "none"
        if self.ui.chk_force_reanalysis.isChecked():
            self.controller.clear_analysis()
            self.logger.notice("Force re-analysis: cache cleared")

        self.logger.log_divider()
        self.logger.progress("Running diff analysis")
        if not self.session.analyze(
            reference_path, dry_run=self.ui.chk002.isChecked(), **self._diff_filters()
        ):
            return

        # Both trees from the analysis' scene and reference (the reference's
        # load is reused, not repeated).
        self.controller.tree.populate_current_scene_tree(self.ui.tree001)
        self.controller.populate_reference_tree(self.ui.tree000, reference_path)

        # The quarantine group is ignored before the log and the colours, so
        # the counts leave it out.
        if self.ui.chk_ignore_quarantine.isChecked():
            self._auto_ignore_quarantine_group()
        self.controller.log_diff_results()
        if self.controller.diff_result:
            self.controller.tree.apply_difference_formatting(
                self.ui.tree001, self.ui.tree000
            )
            self.controller.tree.apply_ignore_styling(self.ui.tree000)
            self.controller.tree.apply_ignore_styling(self.ui.tree001)

        if auto_select or expand_diff:
            if self.controller.tree.count_tree_items(self.ui.tree000):
                try:
                    self.controller.tree.apply_diff_options(
                        self.ui.tree001,
                        self.ui.tree000,
                        auto_select,
                        expand_diff,
                        select_root_only=selection_mode == "root_only",
                        select_leaves_only=selection_mode == "leaves_only",
                    )
                except Exception as e:
                    self.logger.error(f"Auto-selection failed: {e}")
            else:
                self.logger.warning(
                    "Reference tree is empty - skipping auto-selection."
                )
                self.logger.info(
                    "Trees may need to be refreshed manually. Try the Refresh button."
                )
        self._show_diff_summary()

    def _show_diff_summary(self) -> None:
        """The footer's count of the differences (ignored ones left out)."""
        if not (self.ui.footer and self.controller.diff_result):
            return
        effective = self.controller.effective_diff()
        parts = [
            f"{len(effective[key])} {word}"
            for key, word in (
                ("missing", "missing"),
                ("extra", "extra"),
                ("reparented", "reparented"),
                ("fuzzy_matches", "renamed"),
            )
            if effective[key]
        ]
        self.ui.footer.setText(
            f"Diff: {', '.join(parts)}." if parts else "Diff: hierarchies match."
        )

    def tb002(self, state=None):
        """Pull: bring the reference tree's selected objects into the scene."""
        self.ui.txt003.clear()
        renderer = self.controller.tree
        targets = renderer.selected_item_keys(self.ui.tree000)
        if not targets:
            self.logger.error("Please select objects in the reference hierarchy tree.")
            return
        reference_path = self.controller.reference_path
        if not reference_path:
            self.logger.error("Please specify a reference scene path.")
            return

        dry_run = self.ui.chk002.isChecked()
        pull_mode = self.ui.cmb_pull_mode.currentData() or "Add to Scene"
        pull_children = self.ui.chk_pull_children.isChecked()
        self.logger.log_divider()
        self.logger.notice(
            f"Pull: '{pull_mode}' mode, "
            + ("with children" if pull_children else "individual only")
        )
        if not self.session.pull(
            targets,
            reference_path,
            fuzzy_matching=self.ui.chk_fuzzy_matching.isChecked(),
            dry_run=dry_run,
            pull_children=pull_children,
            pull_mode=pull_mode,
        ):
            return

        self.sb.QtWidgets.QApplication.processEvents()  # let the host settle
        self.logger.progress("Refreshing the trees to show the pulled objects...")
        self.controller.refresh_trees(restore_selection=False)

        if pull_children:
            count, noun = len(renderer.condense_to_roots(targets)), "hierarchies"
        else:
            count, noun = len(targets), "objects"
        summary = f"Pulled {count} {noun} ({pull_mode})"
        if not dry_run:
            self.logger.success(f"{summary}.")
        if self.ui.footer:
            self.ui.footer.setText(f"Dry run: {summary}" if dry_run else summary)

    def tb003(self, state=None):
        """Fix: repair the scene toward the reference, as the Fix options say."""
        self.ui.txt003.clear()
        if not self.controller.diff_result:
            self.logger.error("Please run a diff analysis first (Diff button).")
            return
        dry_run = self.ui.chk002.isChecked()
        menu = self.ui.tb003.option_box.menu
        mode = "DRY-RUN" if dry_run else "LIVE"
        self.logger.log_divider()
        self.logger.progress(f"Running hierarchy repair ({mode})...")
        success = self.session.repair(
            self.controller.effective_diff(),
            create_stubs=menu.chk_fix_stubs.isChecked(),
            quarantine_extras=menu.chk_fix_quarantine.isChecked(),
            quarantine_group=self._quarantine_group(),
            skip_animated=menu.chk_skip_animated.isChecked(),
            fix_reparented=menu.chk_fix_reparented.isChecked(),
            fix_fuzzy_renames=menu.chk_fix_fuzzy_renames.isChecked(),
            dry_run=dry_run,
        )
        if success and not dry_run:
            self.controller.refresh_trees(restore_selection=False)
            self.logger.info("Scene modified — re-run Diff to see updated differences.")
        if self.ui.footer:
            if not success:
                self.ui.footer.setText("Fix: nothing to repair")
            else:
                self.ui.footer.setText(
                    f"Fix: {mode} complete" if dry_run else "Fix: repairs applied"
                )

    def _auto_ignore_quarantine_group(self) -> None:
        """Ignore the current tree's top-level quarantine group, if there is one."""
        name = self._quarantine_group()
        tree = self.ui.tree001
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.text(0) == name:
                self.controller.ignored_set(tree).add(
                    self.controller.tree.build_item_path(item)
                )
                return

    # ------------------------------------------------------------------ the reference
    def b003(self):
        """Browse for the reference scene.

        One filter listing every format the host's reference load accepts
        (``HierarchySyncSession.reference_formats``): ``file_dialog`` takes a
        glob list and one description, and a pre-formatted multi-entry filter
        handed to it once hid every format but the first.
        """
        files = self.sb.file_dialog(
            file_types=[f"*{ext}" for ext in self.session.reference_formats()],
            title="Select Reference Scene:",
            start_dir=self.session.workspace(),
            filter_description="Scene Files",
        )
        if files:
            self.controller.reference_path = files[0]
            self.controller.save_recent_reference_scene(files[0])

    def b009(self):
        """Refresh the reference tree."""
        reference_path = self.controller.reference_path
        if not reference_path:
            self.logger.notice("No reference scene set — browse for one first.")
            return
        self.controller.populate_reference_tree(self.ui.tree000, reference_path)

    def b011(self):
        """Show the differences in the trees."""
        if not self.controller.diff_result:
            self.logger.error("Please analyze hierarchies first.")
            return
        self.controller.tree.apply_difference_formatting(
            self.ui.tree001, self.ui.tree000
        )
        self.controller.tree.apply_ignore_styling(self.ui.tree000)
        self.controller.tree.apply_ignore_styling(self.ui.tree001)
        self.logger.debug("Applied difference highlighting to tree widgets.")

    def b012(self):
        """Analyze (no auto-select or expand: that is Diff's) and refresh the trees."""
        self.ui.txt003.clear()
        reference_path = self.controller.reference_path
        log_level = self.ui.cmb001.currentData()
        if log_level:
            self.logger.setLevel(log_level)
        if self.session.analyze(
            reference_path, dry_run=self.ui.chk002.isChecked(), **self._diff_filters()
        ):
            self.controller.refresh_trees()
            self.controller.save_recent_reference_scene(reference_path)

    # ------------------------------------------------------------------ the current scene
    def b005(self):
        """Refresh the current-scene tree."""
        self.controller.tree.populate_current_scene_tree(self.ui.tree001)

    def b006(self):
        """Select the selected items' objects in the scene."""
        nodes = [
            item.data(0, QtCore.Qt.UserRole) for item in self.ui.tree001.selectedItems()
        ]
        nodes = [n for n in nodes if self.session.node_alive(n)]
        if not nodes:
            self.logger.warning("No objects selected in hierarchy tree.")
            return
        self.session.select_nodes(nodes)

    def b007(self):
        """Expand every item of the current-scene tree."""
        self.ui.tree001.expandAll()

    def b008(self):
        """Collapse every item of the current-scene tree."""
        self.ui.tree001.collapseAll()

    def b013(self):
        """Ignore the reference tree's selected items."""
        self._ignore_selected(self.ui.tree000)

    def b014(self):
        """Unignore the reference tree's selected items."""
        self._unignore_selected(self.ui.tree000)

    def b015(self):
        """Ignore the current-scene tree's selected items."""
        self._ignore_selected(self.ui.tree001)

    def b016(self):
        """Unignore the current-scene tree's selected items."""
        self._unignore_selected(self.ui.tree001)

    def b017(self):
        """Rename current-scene items to reference names.

        With items selected in both trees, they pair by selection order. With
        nothing selected in the reference tree, the last diff's fuzzy matches
        rename -- the selected current items' only, or every one when none is
        selected.
        """
        cur_items = self.ui.tree001.selectedItems()
        ref_items = self.ui.tree000.selectedItems()
        if ref_items:
            if not cur_items:
                self.logger.warning(
                    "Select at least one item in the current scene tree."
                )
                return
            pairs = min(len(cur_items), len(ref_items))
            if len(cur_items) != len(ref_items):
                self.logger.notice(
                    f"Selection counts differ (current={len(cur_items)}, "
                    f"reference={len(ref_items)}). Renaming first {pairs} pairs."
                )
            rename_pairs = [
                (ci, ri.text(0).strip())
                for ci, ri in zip(cur_items[:pairs], ref_items[:pairs])
            ]
        else:
            rename_pairs = self._fuzzy_rename_pairs(cur_items)
            if not rename_pairs:
                return

        role = QtCore.Qt.UserRole
        nodes = [item.data(0, role) for item, _ in rename_pairs]
        results = self.session.rename_nodes(
            [(node, name) for node, (_, name) in zip(nodes, rename_pairs)]
        )
        renamed = 0
        tree = self.ui.tree001
        for (item, _), node, new_node in zip(rename_pairs, nodes, results):
            if new_node is None:
                continue
            actual = self._take_rename(item, node, new_node)
            tree.blockSignals(True)  # not an edit: no rename slot
            try:
                item.setText(0, actual)
            finally:
                tree.blockSignals(False)
            renamed += 1
        if renamed:
            self.logger.success(f"Renamed {renamed} object(s) from reference names.")
            if self.controller.diff_result:
                self.controller.tree.apply_difference_formatting(
                    self.ui.tree001, self.ui.tree000
                )

    def _fuzzy_rename_pairs(self, cur_items) -> list:
        """``(item, reference leaf name)`` for the last diff's fuzzy matches,
        restricted to *cur_items* when any are selected."""
        diff = self.controller.diff_result
        fuzzy = diff.get("fuzzy_matches") if diff else None
        if not fuzzy:
            self.logger.warning(
                "No reference selection and no fuzzy matches available.\n"
                "Select items in both trees, or run Diff first."
            )
            return []
        self.logger.info(f"Auto-rename: {len(fuzzy)} fuzzy match(es) from last diff.")
        renderer = self.controller.tree
        by_path = {
            renderer.build_item_path(item): item
            for item in renderer.iter_items(self.ui.tree001)
        }
        selected = {renderer.build_item_path(i) for i in cur_items}
        pairs = []
        for match in fuzzy:
            cur_path = match.get("current_name", "")
            ref_path = match.get("target_name", "")
            item = by_path.get(cur_path)
            if not (cur_path and ref_path and item):
                continue
            if selected and cur_path not in selected:
                continue
            pairs.append((item, ref_path.rsplit("|", 1)[-1]))
        if not pairs:
            self.logger.notice("No matching fuzzy items found in the current tree.")
        return pairs

    def b018(self):
        """Delete the selected objects from the scene (their subtrees with them)."""
        items = self.ui.tree001.selectedItems()
        if not items:
            self.logger.warning("No items selected to delete.")
            return
        nodes = [item.data(0, QtCore.Qt.UserRole) for item in items]
        nodes = [n for n in nodes if self.session.node_alive(n)]
        if not nodes:
            self.logger.warning("No valid scene objects found in selection.")
            return
        names = [self.session.node_name(n) for n in nodes]  # before they go
        try:
            deleted = self.session.delete_nodes(nodes)
        except Exception as e:
            self.logger.error(f"Delete failed: {e}")
            return
        # The count takes in the subtrees; only the selected roots are listed.
        self.logger.info(
            f"Deleted {len(deleted)} object(s) (selected: {', '.join(names)})"
        )
        self.controller.refresh_trees()

    # ------------------------------------------------------------------ ignored items
    def _ignore_selected(self, tree_widget):
        """Ignore the selected items (their descendants with them)."""
        items = tree_widget.selectedItems()
        if not items:
            self.logger.warning("No items selected to ignore.")
            return
        ignored = self.controller.ignored_set(tree_widget)
        added = 0
        for item in items:
            path = self.controller.tree.build_item_path(item)
            if path not in ignored:
                ignored.add(path)
                added += 1
        self.controller.refresh_styling()
        tree_widget.clearSelection()
        self.logger.info(f"Ignored {added} items (descendants also ignored).")

    def _unignore_selected(self, tree_widget):
        """Unignore the selected items (and any ignored beneath them); an item
        ignored through its parent stays ignored."""
        items = tree_widget.selectedItems()
        if not items:
            self.logger.warning("No items selected to unignore.")
            return
        ignored = self.controller.ignored_set(tree_widget)
        removed = inherited = 0
        for item in items:
            path = self.controller.tree.build_item_path(item)
            if path in ignored:
                below = {p for p in ignored if p.startswith(path + "|")}
                ignored.discard(path)
                ignored -= below
                removed += 1 + len(below)
            elif self.controller.is_path_ignored(tree_widget, path):
                inherited += 1
        self.controller.refresh_styling()
        if removed:
            self.logger.info(f"Unignored {removed} items.")
        if inherited:
            self.logger.warning(
                f"{inherited} item(s) ignored via a parent — unignore the parent to remove."
            )
