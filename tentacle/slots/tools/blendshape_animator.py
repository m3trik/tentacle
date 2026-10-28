# !/usr/bin/python
# coding=utf-8
"""Blendshape Animator: build a morph between two meshes, add in-between
(tween) shapes for custom curve control, edit them, and apply the edits back.

One Slots class for both hosts over the host toolkit's ``BlendshapeAnimator``
(``self.tk``): Maya builds a blendShape node, Blender a shape key on the base
mesh with driver-driven corrective keys for the tweens. The panel holds one
animator (``self.animator``), swaps in another when the selection or the
option box loads a different setup, and lists the setup's tweens.
"""

from qtpy import QtCore, QtWidgets

from tentacle import Slots

from ._blendshape_animator.sort_item import NumericSortItem

# Tree column indices -- kept as constants so the refresh and the formatters
# stay in lockstep with the .ui column declarations.
COL_NAME = 0
COL_WEIGHT = 1
COL_FRAME = 2
COL_TOPOLOGY = 3
COL_STATUS = 4

# Edit-mode combo entries (cmb000), in order (the combo saves its index).
MODE_WEIGHT = "Weight-based"
MODE_FRAME = "Frame-based"

#: An apply result (``ApplyStatus.value``) -> the Status column's key.
STATUS_KEYS = {
    "applied": "applied",
    "skipped_duplicate": "skipped",
    "error": "error",
}


class BlendshapeAnimatorSlots(Slots):
    #: The groups that need a bound setup.
    _GATED_GROUPS = ("edit_group", "diagnostics_group", "export_group")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.blendshape_animator
        # The setup the panel acts on; replaced (never mutated in place) when the
        # selection or the option box loads another one.
        self.animator = self.tk.BlendshapeAnimator()

        # Per-row last-apply status, keyed by tween mesh name. Survives refreshes
        # so a tween that errored on apply stays red until the next attempt.
        self._row_status = {}
        self._mode_fields = None  # which input the edit-mode combo shows (cmb000_init)
        self._show_only_mismatches = False  # the tree's header filter toggle
        self._sel_token = None
        self._syncing_selection = False

        self._wire_tree()
        self._wire_dynamic_tooltips()
        self.ui.run_when_ready(self._on_first_show)

    def _on_first_show(self) -> None:
        """Load an existing setup from the selection, if any, and start
        following the selection."""
        bound = self._try_bind_from_selection()
        self._refresh_tree()
        self._update_setup_active()
        self._install_selection_sync()
        if bound and self.animator.has_setup():
            self._set_status(f"Loaded existing setup on {self.animator.base_mesh}")
        else:
            self._set_status(
                "Ready. Select 2 meshes (source, target) and click Create Setup."
            )

    # =========================================================================
    # Setup state + selection sync
    # =========================================================================

    def _update_setup_active(self) -> None:
        """Enable the edit / diagnostics / export groups only with a setup bound."""
        active = self.animator.has_setup()
        for name in self._GATED_GROUPS:
            getattr(self.ui, name).setEnabled(active)

    def _install_selection_sync(self) -> None:
        """Follow the selection: a selected base mesh with a setup rebinds the panel.

        Persistent (the callback re-reads the selection each time); it ends with
        the window (``connect_cleanup``).
        """
        if self._sel_token is not None:
            return
        try:
            mgr = self.tk.ScriptJobManager.instance()
            self._sel_token = mgr.subscribe(
                "SelectionChanged", self._on_selection_changed, owner=self
            )
            mgr.connect_cleanup(self.ui, owner=self)
        except RuntimeError:
            pass

    def _adopt(self, animator) -> bool:
        """Make *animator* the panel's setup. Returns whether there was one."""
        if animator is None:
            return False
        self.animator = animator
        return True

    def _try_bind_from_selection(self) -> bool:
        """Bind to the setup on the first selected base mesh.

        Returns True only when the bound setup changed: False when nothing
        selected carries one, or when it is the setup already bound.
        """
        base = self.tk.BlendshapeAnimator.selected_base()
        if base is None:
            return False
        if base == self.animator.base_mesh and self.animator.has_setup():
            return False  # the same setup, still valid
        return self._adopt(self.tk.BlendshapeAnimator.from_existing(base))

    def _on_selection_changed(self) -> None:
        """SelectionChanged: rebind to the selected base mesh's setup."""
        # A tree click selects its tween meshes too: don't bounce that back.
        if self._syncing_selection:
            return
        if self._try_bind_from_selection():
            self._set_status(f"Loaded existing setup on {self.animator.base_mesh}")
            self._refresh_tree()
            self._update_setup_active()

    # =========================================================================
    # Header
    # =========================================================================

    def header_init(self, widget) -> None:
        """Configure header buttons and help."""
        widget.config_buttons("menu", "minimize", "hide")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Blendshape Animator",
                body="Build a morph between two meshes, add in-between "
                "(tween) shapes for custom curve control, edit them, and "
                "apply the edits back to the morph (Maya: a blendShape node; "
                "Blender: a shape key).",
                sections=[
                    (
                        "Setup",
                        [
                            "Select two meshes — Maya: the <b>source</b> first, "
                            "the <b>target</b> second; Blender: the contributing "
                            "shape, then the receiving mesh last (active).",
                            "Click <b>Create Setup</b>. The option box (▸) offers "
                            "<i>Load From Existing</i> for resuming an in-progress "
                            "setup.",
                        ],
                    ),
                    (
                        "Edit",
                        [
                            "Add tweens by <b>weight</b> (count or comma-separated "
                            "values) or by <b>frame</b>.",
                            "Click rows in the tween list to select; right-click "
                            "for per-tween actions (re-apply, delete, etc.) — "
                            "supports multi-select.",
                        ],
                    ),
                    (
                        "Apply &amp; export",
                        [
                            "<b>Apply All Edits</b> — bulk-apply every queued edit "
                            "back to the morph.",
                            "<b>Diagnostics</b> — flag topology mismatches and "
                            "recover lost keys.",
                            "<b>Export</b> — finalize the scene for baking / FBX.",
                        ],
                    ),
                ],
            )
        )

    # =========================================================================
    # Setup section (b000)
    # =========================================================================

    def b000_init(self, widget) -> None:
        """Create Setup — the option box offers the other ways in."""
        menu = widget.option_box.menu
        menu.setTitle("Create / Load")
        menu.add(
            "QPushButton",
            setText="Load From Existing",
            setObjectName="btn_from_existing",
            setToolTip=self.sb.tooltip.fmt(
                title="Load From Existing",
                body="Bind to the morph setup on the selected base mesh instead "
                "of creating a new one.",
            ),
        )
        menu.btn_from_existing.clicked.connect(self._action_from_existing)

        # Rebuilding a corrupted blendShape node is Maya's alone: a Blender
        # shape key is data on the mesh, with no deformer node to corrupt.
        if getattr(self.tk.BlendshapeAnimator, "recover_setup", None) is not None:
            menu.add(
                "QPushButton",
                setText="Recover Setup",
                setObjectName="btn_recover_setup",
                setToolTip=self.sb.tooltip.fmt(
                    title="Recover Setup",
                    body="Rebuild a corrupted blendShape, preserving keyframes "
                    "and re-applying tagged tween meshes.",
                ),
            )
            menu.btn_recover_setup.clicked.connect(self._action_recover_setup)

    def b000(self, widget) -> None:
        """Create Setup from the two selected meshes."""
        ok = self.animator.create(
            start_frame=self.ui.s000.value(),
            end_frame=self.ui.s001.value(),
            name=self.ui.le000.text() or "morph",
            test_setup=False,
        )
        if ok:
            self._set_status(
                f"Setup created: {self.animator.base_mesh} -> "
                f"{self.animator.target_mesh}",
                level="success",
            )
        else:
            self._set_status("Create Setup failed — see the log.", level="error")
        self._refresh_tree()
        self._update_setup_active()

    def _action_from_existing(self) -> None:
        ok = self._adopt(self.tk.BlendshapeAnimator.from_existing())
        self._set_status(
            f"Loaded existing setup on {self.animator.base_mesh}"
            if ok
            else "Load From Existing failed — see the log.",
            level="success" if ok else "error",
        )
        self._refresh_tree()
        self._update_setup_active()

    def _action_recover_setup(self) -> None:
        ok = self._adopt(self.tk.BlendshapeAnimator.recover_setup())
        self._set_status(
            f"Recovered setup on {self.animator.base_mesh}"
            if ok
            else "Recover Setup failed — see the log.",
            level="success" if ok else "error",
        )
        self._refresh_tree()
        self._update_setup_active()

    # =========================================================================
    # Edit section (cmb000, le001, b001)
    # =========================================================================

    def cmb000_init(self, widget) -> None:
        """Populate the edit-mode combo, and say which input each mode uses."""
        widget.clear()
        widget.addItems([MODE_WEIGHT, MODE_FRAME])
        # Each mode NAMES its input, so neither is described as the absence of
        # the other; binding applies the opening one.
        self._mode_fields = self.sb.FieldVisibility()
        self._mode_fields.define(MODE_WEIGHT, [self.ui.le001])
        self._mode_fields.define(MODE_FRAME, [self.ui.s003])
        self._mode_fields.bind(widget)

    def le000_init(self, widget) -> None:
        """Name field — optional, so an empty name is a real choice."""
        widget.option_box.clear_option = True

    def le001_init(self, widget) -> None:
        """CSV weights field — the option box offers preset lists."""
        widget.option_box.menu.setTitle("Weight Presets")
        widget.option_box.clear_option = True
        for label, csv in (
            ("Quarters (0.25, 0.5, 0.75)", "0.25, 0.5, 0.75"),
            ("Thirds (0.33, 0.67)", "0.33, 0.67"),
            ("Quintiles (0.2 .. 0.8)", "0.2, 0.4, 0.6, 0.8"),
            ("Easing-in (0.1, 0.3, 0.7, 0.9)", "0.1, 0.3, 0.7, 0.9"),
        ):
            btn = widget.option_box.menu.add(
                "QPushButton",
                setText=label,
                setToolTip=f"Set Weights field to: {csv}",
            )
            btn.clicked.connect(lambda _checked=False, c=csv: widget.setText(c))

    def b001_init(self, widget) -> None:
        """Add Tweens — the option box holds the count and the group / prefix."""
        menu = widget.option_box.menu
        menu.setTitle("Add Tweens")
        menu.add(
            "QSpinBox",
            setObjectName="count",
            setMinimum=1,
            setMaximum=20,
            setValue=3,
            setPrefix="Count:  ",
            setToolTip=(
                "Number of evenly-spaced weight-based tweens to create when no\n"
                "explicit weights are provided. Ignored in Frame-based mode."
            ),
        )
        menu.add(
            "QLineEdit",
            setText=self.tk.BlendshapeAnimator.TWEEN_GROUP,
            setObjectName="group_name",
            setToolTip="Group to parent newly-created tween meshes under "
            "(Blender: an Empty).",
        )
        menu.add(
            "QLineEdit",
            setText="morph_ib",
            setObjectName="name_prefix",
            setToolTip="Name prefix for newly-created tween meshes.",
        )

    def _require_setup(self) -> bool:
        """True with a setup bound; else say so in the footer."""
        if self.animator.has_setup():
            return True
        self._set_status("Setup not complete — Create or Load first.", level="warning")
        return False

    def b001(self, widget) -> None:
        """Add Tweens — by weight or by frame, as the edit-mode combo says (one
        undo step per batch, in Maya)."""
        if not self._require_setup():
            return
        menu = widget.option_box.menu
        # None keeps the engine's defaults.
        group_name = name_prefix = None
        try:
            group_name = menu.group_name.text() or None
            name_prefix = menu.name_prefix.text() or None
        except (AttributeError, RuntimeError):
            pass

        if self.ui.cmb000.currentText() == MODE_WEIGHT:
            csv = (self.ui.le001.text() or "").strip()
            weights = None
            count = 3
            if csv:
                try:
                    weights = [float(p.strip()) for p in csv.split(",") if p.strip()]
                except ValueError:
                    self._set_status(
                        "Invalid CSV in Weights — expected comma-separated floats.",
                        level="warning",
                    )
                    return
            else:
                try:
                    count = menu.count.value()
                except (AttributeError, RuntimeError):
                    pass
            tweens = self.animator.edit_weight_based(
                weights=weights,
                count=count,
                group_name=group_name,
                name_prefix=name_prefix,
            )
            requested = len(weights) if weights else count
            self._set_status(
                f"Added {len(tweens)}/{requested} weight-based tween(s)."
                if tweens
                else "No tweens added — see the log.",
                level="success" if tweens else "error",
            )
        else:
            frame = self.ui.s003.value()
            tweens = self.animator.edit_frame_based(
                target_frame=frame, group_name=group_name, name_prefix=name_prefix
            )
            self._set_status(
                f"Added frame-based tween at frame {frame}"
                if tweens
                else "Frame-based tween creation failed — see the log.",
                level="success" if tweens else "error",
            )
        self._refresh_tree()

    # =========================================================================
    # Diagnostics section (b003, b004, b005)
    # =========================================================================

    def b003(self, widget) -> None:
        """Diagnose Topology."""
        if not self._require_setup():
            return
        ok = self.animator.diagnose_topology_issues()
        self._set_status(
            "Topology OK" if ok else "Topology mismatches detected.",
            level="success" if ok else "warning",
        )
        self._refresh_tree()

    def b004_init(self, widget) -> None:
        """Cleanup Topology Mismatches — the option box holds its two flags."""
        menu = widget.option_box.menu
        menu.setTitle("Cleanup Topology Mismatches")
        menu.add(
            "QCheckBox",
            setText="Apply valid first",
            setChecked=True,
            setObjectName="apply_valid_only",
            setToolTip="Re-apply tweens that DO match base topology before deleting bad ones.",
        )
        menu.add(
            "QCheckBox",
            setText="Delete mismatched",
            setChecked=True,
            setObjectName="delete_mismatched",
            setToolTip="Delete tween meshes whose vertex count no longer matches the base.",
        )

    def b004(self, widget) -> None:
        """Clean up tweens whose topology doesn't match the base mesh."""
        if not self._require_setup():
            return
        menu = widget.option_box.menu
        self.animator.cleanup_topology_mismatches(
            delete_mismatched=menu.delete_mismatched.isChecked(),
            apply_valid_only=menu.apply_valid_only.isChecked(),
        )
        self._set_status("Cleanup complete.", level="success")
        self._refresh_tree()

    def b005(self, widget) -> None:
        """Recover Animation."""
        if not self._require_setup():
            return
        ok = self.animator.recover_animation()
        self._set_status(
            "Animation recovered." if ok else "Animation recovery failed.",
            level="success" if ok else "error",
        )

    # =========================================================================
    # Export section (b006, b007, b008)
    # =========================================================================

    def b006_init(self, widget) -> None:
        """Apply All Edits — the option box holds its two flags."""
        menu = widget.option_box.menu
        menu.setTitle("Apply All Edits")
        menu.add(
            "QCheckBox",
            setText="Skip duplicates",
            setChecked=True,
            setObjectName="skip_duplicates",
            setToolTip="Treat a weight the morph already holds as a skip, not an "
            "error (Maya's 'Weights must be unique'; Blender updates such a tween "
            "in place, so never skips).",
        )
        menu.add(
            "QCheckBox",
            setText="Validate topology first",
            setChecked=False,
            setObjectName="validate_topology",
            setToolTip=(
                "Filter out tweens whose vertex count no longer matches the base.\n"
                "Off by default to avoid silently masking problems."
            ),
        )

    def _record(self, results) -> None:
        """Remember each tween's apply result for the Status column."""
        for tween, status in results:
            self._row_status[tween.mesh] = getattr(status, "value", status)

    @staticmethod
    def _count(results, value: str) -> int:
        return sum(1 for _, s in results if getattr(s, "value", s) == value)

    def b006(self, widget) -> None:
        """Apply All Edits — every tween of the setup, with the option box's flags."""
        if not self._require_setup():
            return
        try:
            skip = widget.option_box.menu.skip_duplicates.isChecked()
            validate = widget.option_box.menu.validate_topology.isChecked()
        except (AttributeError, RuntimeError):
            skip, validate = True, False
        results = self.animator.apply_tweens(
            None, skip_duplicates=skip, validate_topology=validate
        )
        self._record(results)
        if results:
            errors = self._count(results, "error")
            self._set_status(
                f"Applied {self._count(results, 'applied')}/{len(results)} — "
                f"skipped {self._count(results, 'skipped_duplicate')}, errors {errors}",
                level="warning" if errors else "success",
            )
        else:
            self._set_status("No tweens to apply.")
        self._refresh_tree()

    def b007(self, widget) -> None:
        """Remove Target Mesh."""
        if not self._require_setup():
            return
        ok = self.animator.remove_target_for_export()
        self._set_status(
            "Target mesh removed." if ok else "Removal failed — see the log.",
            level="success" if ok else "error",
        )

    def b008_init(self, widget) -> None:
        """Finalize for Export — the option box holds its four flags."""
        widget.option_box.menu.setTitle("Finalize for Export")
        for name, label, tip in (
            ("cleanup_scene", "Cleanup scene", "Hide target mesh and tween meshes."),
            (
                "delete_construction_history",
                "Delete construction history",
                "Delete construction history except the blendShape itself (Maya; "
                "a Blender shape key has no history to bake).",
            ),
            (
                "hide_target_mesh",
                "Hide target mesh",
                "Hide the target instead of leaving it visible.",
            ),
            (
                "delete_inbetween_meshes",
                "Delete in-between meshes",
                "Delete the tween meshes after applying their edits.",
            ),
        ):
            widget.option_box.menu.add(
                "QCheckBox",
                setText=label,
                setChecked=True,
                setObjectName=name,
                setToolTip=tip,
            )

    def b008(self, widget) -> None:
        """Finalize the setup for export: apply, clean up, hide the source."""
        if not self._require_setup():
            return
        menu = widget.option_box.menu
        ok = self.animator.finalize_for_export(
            cleanup_scene=menu.cleanup_scene.isChecked(),
            delete_construction_history=menu.delete_construction_history.isChecked(),
            hide_target_mesh=menu.hide_target_mesh.isChecked(),
            delete_inbetween_meshes=menu.delete_inbetween_meshes.isChecked(),
        )
        self._set_status(
            "Finalized for export." if ok else "Finalize failed.",
            level="success" if ok else "error",
        )
        self._refresh_tree()

    # =========================================================================
    # Tween tree (tree000)
    # =========================================================================

    def _wire_tree(self) -> None:
        """One-time tree setup: column formatters, header actions, signals."""
        tree = self.ui.tree000
        # Per-column colors, read from each cell's UserRole key.
        topology_map = {
            "match": ("#3C8D3C", None),  # green text
            "mismatch": ("#B97A7A", None),  # red text
            "unknown": ("#AAAAAA", None),  # gray
        }
        status_map = {
            "applied": ("#3C8D3C", None),
            "pending": ("#B49B5C", None),
            "skipped": ("#6D9BAA", None),
            "error": ("#B97A7A", None),
        }
        tree.set_column_formatter(
            COL_TOPOLOGY, tree.make_color_map_formatter(topology_map)
        )
        tree.set_column_formatter(COL_STATUS, tree.make_color_map_formatter(status_map))

        # Clicking a row selects its tween mesh in the scene.
        tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_tree_context_menu)

        tree.header_actions.add(
            "refresh",
            "refresh",
            tooltip="Re-scan tween meshes",
            callback=self._refresh_tree,
        )
        tree.header_actions.add(
            "filter",
            "filter",
            tooltip="Show only topology mismatches",
            callback=self._toggle_filter_mismatches,
            toggle=True,
        )
        # Subtle tints to tell the numeric columns apart.
        tint = self.sb.QtGui.QColor(255, 255, 255, 8)
        tree.set_column_tint(COL_WEIGHT, tint)
        tree.set_column_tint(COL_FRAME, tint)
        tree.selection_style = "tint"
        # Weight ascending, so new tweens land where users expect; a header
        # click overrides it.
        tree.sortByColumn(COL_WEIGHT, QtCore.Qt.AscendingOrder)

    def _wire_dynamic_tooltips(self) -> None:
        """Tooltips that read the current state on hover."""
        try:
            self.ui.tree000.tooltip.bind(self._tree_tooltip_provider)
            self.ui.footer.tooltip.bind(
                lambda: (
                    f"Setup: {self.animator.blendshape or '(none)'} on "
                    f"{self.animator.base_mesh or '(none)'}"
                )
            )
        except (AttributeError, RuntimeError):  # a widget without the tooltip helper
            pass

    def _tree_tooltip_provider(self) -> str:
        if not self.animator.has_setup():
            return "No setup loaded. Click Create Setup or load via the option box."
        base_count, rows = self.animator.tween_topology()
        mismatches = sum(1 for _, count in rows if count != base_count)
        return f"{len(rows)} tween(s), {mismatches} topology mismatch(es)"

    def _refresh_tree(self) -> None:
        """Rebuild the tree from the setup's tweens in the scene."""
        tree = self.ui.tree000
        tree.blockSignals(True)
        tree.setSortingEnabled(False)
        tree.clear()
        try:
            base_count, rows = self.animator.tween_topology()
            for tween, count in rows:
                if count is None:
                    topology = "unknown"
                elif count == base_count:
                    topology = "match"
                else:
                    topology = "mismatch"
                if self._show_only_mismatches and topology == "match":
                    continue
                tree.addTopLevelItem(self._row(tween, count, base_count, topology))
            tree.apply_formatting()
        finally:
            tree.setSortingEnabled(True)
            tree.blockSignals(False)

    def _row(self, tween, count, base_count, topology) -> QtWidgets.QTreeWidgetItem:
        """One tween's row: the cells, their color keys and numeric sort keys."""
        # A tween with no recorded apply result is pending: showing it applied
        # would paint green an edit never applied back.
        status = STATUS_KEYS.get(self._row_status.get(tween.mesh), "pending")
        frame = tween.target_frame
        if topology == "match":
            topology_text = "Match"
        elif count is None:
            topology_text = "Unknown"
        else:
            topology_text = f"Mismatch ({count} vs {base_count})"
        item = NumericSortItem(
            [
                tween.mesh,
                f"{tween.weight:.3f}",
                "" if frame is None else str(frame),
                topology_text,
                status.capitalize(),
            ]
        )
        role = QtCore.Qt.UserRole
        item.setData(COL_TOPOLOGY, role, topology)  # what the formatters read
        item.setData(COL_STATUS, role, status)
        item.setData(COL_NAME, role, tween)  # the handlers' tween
        item.setData(COL_WEIGHT, NumericSortItem.NUM_ROLE, tween.weight)
        if frame is not None:
            item.setData(COL_FRAME, NumericSortItem.NUM_ROLE, frame)
        right = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        item.setTextAlignment(COL_WEIGHT, right)
        item.setTextAlignment(COL_FRAME, right)
        return item

    def _selected_tweens(self) -> list:
        tweens = []
        for item in self.ui.tree000.selectedItems():
            tween = item.data(COL_NAME, QtCore.Qt.UserRole)
            if tween is not None:
                tweens.append(tween)
        return tweens

    def _select_in_scene(self, tweens) -> list:
        """Select *tweens*' meshes without the selection sync rebinding the panel
        to them (a tween mesh is a target, not a base)."""
        self._syncing_selection = True
        try:
            return self.tk.BlendshapeAnimator.select_tweens(tweens)
        finally:
            self._syncing_selection = False

    def _on_tree_selection_changed(self) -> None:
        """Tree selection -> scene selection."""
        tweens = self._selected_tweens()
        if tweens:
            self._select_in_scene(tweens)

    def _show_tree_context_menu(self, pos) -> None:
        tree = self.ui.tree000
        clicked = tree.itemAt(pos)
        if clicked is None:
            return
        # A right-click on an unselected row selects it, so the actions act on
        # what was clicked; on a selected row the multi-selection stays.
        if not clicked.isSelected():
            tree.setCurrentItem(clicked)
        tweens = self._selected_tweens()
        if not tweens:
            one = clicked.data(COL_NAME, QtCore.Qt.UserRole)
            tweens = [one] if one is not None else []
        if not tweens:
            return

        multi = len(tweens) > 1
        single = tweens[0]  # Jump to Frame is single-row only
        menu = QtWidgets.QMenu(tree)
        self.sb.StyleSheet.cast_shadow(menu)
        act_select = menu.addAction(
            f"Select {len(tweens)} in Scene" if multi else "Select in Scene"
        )
        act_jump = menu.addAction("Jump to Frame")
        act_jump.setEnabled(not multi and single.target_frame is not None)
        menu.addSeparator()
        act_reapply = menu.addAction(
            f"Re-apply {len(tweens)} Tweens" if multi else "Re-apply This Tween"
        )
        menu.addSeparator()
        act_delete = menu.addAction(
            f"Delete {len(tweens)} Tween Meshes" if multi else "Delete Tween Mesh"
        )

        chosen = menu.exec_(tree.viewport().mapToGlobal(pos))
        if chosen is act_select:
            selected = self._select_in_scene(tweens)
            if selected:
                self._set_status(f"Selected {len(selected)} mesh(es)")
        elif chosen is act_jump:
            self.tk.AnimUtils.set_current_frame(single.target_frame)
            self._set_status(f"Jumped to frame {single.target_frame}")
        elif chosen is act_reapply:
            results = self.animator.apply_tweens(list(tweens))
            self._record(results)
            self._set_status(
                f"Re-applied {self._count(results, 'applied')}/{len(results)} tween(s)"
            )
            self._refresh_tree()
        elif chosen is act_delete:
            deleted = self.animator.delete_tweens(tweens)
            for name in deleted:
                self._row_status.pop(name, None)
            self._set_status(f"Deleted {len(deleted)}/{len(tweens)} tween mesh(es)")
            self._refresh_tree()

    def _toggle_filter_mismatches(self, checked: bool) -> None:
        self._show_only_mismatches = bool(checked)
        self._refresh_tree()

    # =========================================================================
    # Footer
    # =========================================================================

    def _set_status(self, text: str, level: str = "info") -> None:
        """Write *text* to the footer, colored by *level* (one of uitk Footer's
        ``LEVEL_COLORS``: info / success / warning / error)."""
        try:
            self.ui.footer.setText(text, level=level)
        except RuntimeError:  # the footer is already deleted (a teardown race)
            self.animator.logger.info(text)
