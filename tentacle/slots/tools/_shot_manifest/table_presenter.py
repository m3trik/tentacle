# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest tree's rows: populating them (``ShotPairing.rows``: steps,
the members of their shots, the shots no step pairs with), formatting, colour
tags, assessment colouring and the behavior-label widgets.  The Start / End
cells are :mod:`.range_column`'s.

Mixed into :class:`~.shot_manifest_controller.ShotManifestController`.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

import pythontk as ptk
from pythontk import BuilderObject, BuilderStep, StepStatus

from .manifest_data import (
    COL_BEHAVIORS,
    COL_DESC,
    COL_END,
    COL_START,
    COL_STEP,
    ERROR_COLOR,
    HEADERS,
    STEP_ICON_COLOR,
    ManifestData,
)

#: Tooltip line for an object the sheet's asset column did not list
#: (``BuilderObject.origin``).
_ORIGIN_NOTES = {
    "description": "Named in the step's description -- the asset column lists none.",
    "shot": "Auto-filled from the scene -- not listed in the sheet.",
    # The members of a shot shown under its row (``_add_member_rows``).
    "member": "In the step's shot, not listed in the manifest.",
}

#: Object statuses about a behavior, and the word the step's Behaviors cell
#: counts each by ("2 missing, 1 to re-key").
_BEHAVIOR_WORDS = {
    "missing_behavior": "missing",
    "behavior_conflict": "in conflict",
    "unknown_behavior": "unknown",
    "stale_behavior": "to re-key",
}
_BEHAVIOR_ISSUES = tuple(_BEHAVIOR_WORDS)


class ManifestTableMixin:
    """Presentation methods for the manifest tree widget.

    Expects the host class to provide:

    - ``self.ui``  – the loaded UI with ``tbl_steps`` tree widget.
    - ``self._steps`` / ``self._sheet_steps``  – the steps shown, and the
      source's own.
    - ``self._last_results``  – last assessment result list.
    - ``self._is_built``  – whether shots have been built.
    - ``self._update_build_button()``  – button-state refresh.
    - ``self._set_footer(text, *, color)``  – footer label helper.
    - ``self._settings``  – :class:`SettingsManager` instance.
    - ``self._editor``  – the :class:`ManifestEditor` (Local Edits).
    - ``self._row_tags``  – the tree's ``RowTags`` (colour strip).
    - ``self._active_store()`` / ``self._active_mapping``  – the scene's
      store and the effective mapping template.
    - ``self._rows()``  – the table's ``(step, shot)`` rows (``ShotPairing.rows``).
    - ``self._locked_step_ids()``  – the steps whose shot is locked.
    - the Start / End column's ``_restore_user_ranges()`` /
      ``_refresh_timing()`` (``RangeColumnMixin`` / ``StoreFollowMixin``).
    """

    @property
    def _use_short_names(self) -> bool:
        """Whether to display leaf-only names instead of full DAG paths."""
        settings = getattr(self, "_settings", None)
        if settings is None:
            return True
        return not settings.value("long_names", False)

    @staticmethod
    def _row_key(item):
        """What a top-level row is across redraws: its step's ID (a rename
        changes the text, never the ID), else its text."""
        from qtpy.QtCore import Qt

        data = item.data(0, Qt.UserRole)
        return data.step_id if isinstance(data, BuilderStep) else item.text(0)

    def _row_icon(self, item) -> str:
        """The icon of a top-level row: a lock for a step whose shot is
        locked (final: Build leaves it, Local Edits refuse it), else a step."""
        from qtpy.QtCore import Qt

        data = item.data(0, Qt.UserRole)
        locked = getattr(self, "_locked_rows", ())
        if isinstance(data, BuilderStep) and data.step_id in locked:
            return "lock"
        return "step"

    def _save_tree_state(self):
        """Return expansion state and scroll position for later restore."""
        tree = self.ui.tbl_steps
        expanded = set()
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.isExpanded():
                expanded.add(self._row_key(item))
        scroll_val = tree.verticalScrollBar().value()
        return expanded, scroll_val

    def _restore_tree_state(self, state):
        """Re-expand items and restore scroll position from *state*."""
        expanded, scroll_val = state
        tree = self.ui.tbl_steps
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if self._row_key(item) in expanded:
                item.setExpanded(True)
        tree.verticalScrollBar().setValue(scroll_val)

    def _color_behavior_label(self, obj, label, step_id: str = None) -> None:
        """Set the label HTML and tooltip using the latest assessment data.

        Looks up the object in ``_last_results`` and colours broken
        behaviors accordingly.  Falls back to plain formatting when no
        assessment data is available.

        Parameters:
            step_id: When given, only that step's assessment is
                consulted — the same object can appear in several steps
                with different statuses (e.g. fade_in verified in A01,
                fade_out broken in A05), so a first-match scan would
                colour this row from another step's result.
        """
        broken: list = []
        stale: list = []
        obj_st = ptk.StepStatus.find_object(
            getattr(self, "_last_results", None) or [], obj.name, step_id
        )
        # A missing object's row says so (_set_row_status): its behaviors
        # are not each marked.
        if obj_st is not None and obj_st.status != "missing_object":
            broken = list(obj_st.broken_behaviors or [])
            stale = list(obj_st.stale_behaviors or [])
        off = self._disabled_behaviors()
        marked = self._marked_behaviors()
        label.setText(
            ManifestData.format_behavior_html(
                obj.behaviors,
                broken=broken,
                stale=stale,
                disabled=off,
                marked=marked,
            )
        )
        # Build a per-behavior status tooltip
        if obj_st is not None and obj.behaviors:
            broken_set = set(obj_st.broken_behaviors or [])
            lines = []
            for b in obj.behaviors:
                display = ManifestData.fmt_behavior(b)
                if b in off:
                    lines.append(f"\u2013 {display}  (turned off -- header menu)")
                    continue
                if b in stale:
                    lines.append(
                        f"\u21bb {display}  (keyed under an older effect "
                        "recipe -- Build re-keys it)"
                    )
                    continue
                if obj_st.status == "missing_object":
                    lines.append(f"\u2716 {display}  (object missing)")
                elif b in broken_set and b in marked:
                    lines.append(
                        f"\u2716 {display}  (no marker where its keys would go "
                        "-- Build places it)"
                    )
                elif b in broken_set:
                    lines.append(f"\u2716 {display}  (not verified)")
                elif b in marked:
                    lines.append(
                        f"\u2714 {display}  (marked on the Shot Sequencer's "
                        "timeline -- header menu)"
                    )
                else:
                    lines.append(f"\u2714 {display}")
            label.setToolTip("\n".join(lines))
        elif obj.behaviors:
            label.setToolTip(
                "\n".join(ManifestData.fmt_behavior(b) for b in obj.behaviors)
            )
        else:
            label.setToolTip("")

    def _make_behavior_label(
        self, obj, tree, child_item, choices, step_id: str = None
    ) -> None:
        """Create a clickable label for the Behaviors cell.

        The menu lists all behaviors available for this object's *kind*,
        plus any behaviours already assigned (so they remain toggle-able
        even when no YAML declares that kind).
        """
        Label = self.sb.Label
        from qtpy.QtCore import Qt

        label = Label()
        label.setTextFormat(Qt.RichText)

        # Merge kind-filtered choices with the object's existing behaviors
        # so assigned behaviors are always present in the menu.
        merged = list(dict.fromkeys(list(choices) + list(obj.behaviors)))

        if not merged:
            tree.setItemWidget(child_item, COL_BEHAVIORS, label)
            return

        def _show_menu():
            Menu = self.sb.Menu

            if self._editor.refuse_viewing():
                return
            step = next((s for s in self._steps if s.step_id == step_id), None)
            if self._editor.refuse_locked(step):
                return

            menu = Menu(
                parent=label,
                position="cursorPos",
                add_header=False,
                add_footer=False,
                hide_on_leave=True,
                fixed_item_height=20,
                match_parent_width=False,
            )
            cbs = []
            for raw_name in merged:
                if not raw_name:
                    continue
                display = ManifestData.fmt_behavior(raw_name)
                chk = menu.add("QCheckBox", setText=display)
                chk.setChecked(raw_name in obj.behaviors)
                chk.setProperty("behavior_raw", raw_name)
                cbs.append(chk)
            menu.on_hidden.connect(
                lambda: self._on_behaviors_changed(obj, cbs, step_id)
            )
            # One menu per click, parented to the label: else every click
            # left a hidden menu behind until the table was next drawn.
            menu.on_hidden.connect(menu.deleteLater)
            menu.show()

        self._color_behavior_label(obj, label, step_id=step_id)
        label.clicked.connect(_show_menu)
        tree.setItemWidget(child_item, COL_BEHAVIORS, label)

    def _on_behaviors_changed(self, obj, checkboxes, step_id=None) -> None:
        """Record the ticked behaviors as a Local Edit of *obj*
        (``ManifestEditor.set_behaviors``): the table redraws with them, and
        a Build is due -- it applies them, or releases the unticked ones' keys."""
        behaviors = [
            chk.property("behavior_raw") for chk in checkboxes if chk.isChecked()
        ]
        if behaviors != obj.behaviors:
            self._editor.set_behaviors(step_id, obj, behaviors)

    def _reapply_behavior(
        self, step_id: str, obj: BuilderObject, raise_errors: bool = False
    ) -> bool:
        """Re-apply every behavior of one object on its paired shot, as one
        undo step -- ``ShotManifest.reapply_object``: its previous keys out,
        the new ones recorded as the manifest's own.

        Parameters:
            raise_errors: Also raise why nothing was re-applied, for a caller
                that reports it itself (Render Effects' focused Key).

        Returns:
            Whether it was re-applied.  Why not goes on the footer: no shot
            pairs with the step yet, the scene holds no object of that name
            (or several), or an error.
        """
        try:
            store = self._active_store()
            shot = self._pairing().shots.get(step_id)
            if store is None or shot is None:
                problem = f"No shot pairs with '{step_id}' yet -- build first."
            else:
                with store.scene_edit("manifest_reapply"):
                    applied = self._manifest(store).reapply_object(shot, obj)
                if applied:
                    problem = None
                elif store.resolve_member(obj.name)[1] == "ambiguous":
                    problem = (
                        "Nothing re-applied: several scene objects are named "
                        f"'{obj.name}'."
                    )
                else:
                    problem = f"Nothing re-applied: '{obj.name}' is not in the scene."
            if problem is None:
                # Re-assess so the UI reflects the fixed state.  Skip the
                # selected-keys guard -- we just applied known behaviors and
                # only need a status refresh.
                self.assess(skip_key_check=True)
                return True
        except Exception as exc:
            self.logger.error("Apply behavior failed: %s", exc)
            self._set_footer(f"Error: {exc}", color=ERROR_COLOR)
            if raise_errors:
                raise
            return False
        self._set_footer(problem, color=ERROR_COLOR)
        if raise_errors:
            raise RuntimeError(problem)
        return False

    def _populate_table(self) -> None:
        """Fill the tree with the manifest's rows (``ShotPairing.rows``): a
        step row per step -- its objects, then the members of its shot it does
        not list -- and a "not in doc" row per shot no step pairs with, its
        members under it, where the timeline has it."""
        tree = self.ui.tbl_steps
        tree.clear()
        tree.setHeaderLabels(HEADERS)
        tree.setColumnCount(len(HEADERS))
        pairing = self._pairing()
        # The steps whose shot is locked: their rows draw a lock (_row_icon).
        self._locked_rows = self._locked_step_ids(pairing)

        _kind_cache: dict = {}
        steps_by_id = {s.step_id: s for s in self._steps}

        for step, shot in self._rows(pairing):
            if step is None:
                # A shot split off a step's shot shows that step's section.
                linked = steps_by_id.get(pairing.links.get(shot.shot_id))
                self._add_shot_row(tree, shot, section=self._section_text(linked))
                continue
            section = self._section_text(step)

            parent = tree.create_item(
                [step.shot_name, section, step.display_text, "", "", ""],
                data=step,
            )
            if pairing.how.get(step.step_id) == "order":
                parent.setToolTip(
                    COL_STEP,
                    f"Paired by timeline order with shot "
                    f"'{pairing.shots[step.step_id].name}'; Build records the pairing.",
                )
            # Child rows: object name in Description column, behavior label
            for obj in step.objects:
                display = (
                    self.manifest_host.leaf_name(obj.name)
                    if self._use_short_names
                    else obj.name
                )
                child = tree.create_item(
                    ["", "", display, "", "", ""],
                    data=obj,
                    parent=parent,
                )
                if obj.kind == "audio":
                    font = child.font(COL_DESC)
                    font.setItalic(True)
                    for c in range(tree.columnCount()):
                        child.setFont(c, font)
                if display != obj.name:
                    child.setToolTip(COL_DESC, obj.name)
                origin = _ORIGIN_NOTES.get(obj.origin)
                if origin:
                    child.setToolTip(COL_DESC, f"{obj.name}\n{origin}")
                if obj.kind not in _kind_cache:
                    _kind_cache[obj.kind] = list(
                        self.behaviors.list_behaviors(kind=obj.kind)
                    )
                self._make_behavior_label(
                    obj, tree, child, _kind_cache[obj.kind], step.step_id
                )
            if shot is not None:
                self._add_member_rows(
                    tree, parent, shot, listed=[o.name for o in step.objects]
                )

        # Restrict editability: only Range column on parent rows, and only
        # for steps that aren't built yet — per row, not all-or-nothing,
        # so new steps added to a partially built CSV stay editable.
        from qtpy.QtCore import Qt as _Qt

        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step = parent.data(0, _Qt.UserRole)
            editable = (
                isinstance(step, BuilderStep) and step.step_id not in pairing.shots
            )
            if editable:
                parent.setFlags(parent.flags() | _Qt.ItemIsEditable)
            else:
                parent.setFlags(parent.flags() & ~_Qt.ItemIsEditable)
            for j in range(parent.childCount()):
                child = parent.child(j)
                child.setFlags(child.flags() & ~_Qt.ItemIsEditable)

        self._shown_pairing = self._pairing_key(pairing)

        # Restore user-entered range values that survive table rebuilds,
        # then the built rows' live ranges: the store is their truth.
        self._restore_user_ranges(tree)
        self._refresh_timing()

        self._apply_formatting(tree)
        self._apply_row_tags(tree)
        tree.set_stretch_column(2)  # Stretch "Description" column
        tree.restore_column_state()  # Persist user header changes
        self._editor.decorate()
        self._refresh_export_preview()  # an open one shows these rows

    @staticmethod
    def _section_text(step) -> str:
        """*step*'s Section cell -- ``"A: Title"``, or the bare section --
        ``""`` for no step."""
        if step is None:
            return ""
        if step.section_title:
            return f"{step.section}: {step.section_title}"
        return step.section

    def _add_shot_row(self, tree, shot, section: str = ""):
        """An italic, non-editable "not in doc" row for *shot* -- a shot no
        step pairs with -- its members under it; its context menu adds it to
        the manifest, pairs it with a step, or removes it.  *section*: the
        section of the step it was split off (``ShotPairing.links``).  Its
        status is marked with the rest (:meth:`_apply_formatting`)."""
        from qtpy.QtCore import Qt

        row = tree.create_item(
            [
                shot.name,
                section,
                shot.description or "",
                "",
                f"{shot.start:.0f}",
                f"{shot.end:.0f}",
            ],
            data=shot,
        )
        row.setFlags(row.flags() & ~Qt.ItemIsEditable)
        font = row.font(COL_STEP)
        font.setItalic(True)
        for c in range(tree.columnCount()):
            row.setFont(c, font)
        self._add_member_rows(tree, row, shot, in_step=False)
        return row

    def _add_member_rows(self, tree, parent, shot, listed=(), in_step=True) -> None:
        """A child row under *parent* per member of *shot* not among *listed*
        (names, compared as ``ShotStore.member_key`` does): the shot's own
        objects, shown before any Assess -- italic, never editable; under a
        step (*in_step*) marked ``additional`` (:meth:`_set_row_status`): in
        the shot, not in the step.

        Each row's data is a ``BuilderObject`` of origin ``"member"``: the
        object rows' own actions (Outliner, Copy) reach it, Local Edits do
        not -- the sheet does not list it.
        """
        from qtpy.QtCore import Qt

        key = ptk.ShotStore.member_key
        seen = {key(n) for n in listed}
        issues = [("additional", _ORIGIN_NOTES["member"])] if in_step else []
        for name in shot.objects:
            if key(name) in seen:
                continue
            seen.add(key(name))
            display = self.manifest_host.leaf_name(name) if self._use_short_names else name
            child = tree.create_item(
                ["", "", display, "", "", ""],
                data=BuilderObject(name=name, origin="member"),
                parent=parent,
            )
            child.setFlags(child.flags() & ~Qt.ItemIsEditable)
            font = child.font(COL_DESC)
            font.setItalic(True)
            for c in range(tree.columnCount()):
                child.setFont(c, font)
            if display != name:
                child.setToolTip(COL_DESC, name)
            if issues:
                self._set_row_status(child, issues)

    def _step_items(self, step_ids) -> list:
        """The step rows of *step_ids*, in table order."""
        from qtpy.QtCore import Qt

        wanted = set(step_ids)
        tree = self.ui.tbl_steps
        items = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if isinstance(step, BuilderStep) and step.step_id in wanted:
                items.append(item)
        return items

    def _apply_row_tags(self, tree) -> None:
        """Colour the step rows: the user's tags (the scene's, for the loaded
        sheet) over the template's automatic ``color_by``; an object row
        shows its step's (``RowTags`` inheritance).  A "not in doc" row takes
        the automatic colour of the step row above it: it sits inside that
        span of the timeline, and a gap in the strip there read as a section
        boundary."""
        from qtpy.QtCore import Qt

        tags = self._row_tags
        user = ptk.ManifestTags.read(self._active_store(), self._editor.source_key)
        rule = (self._active_mapping or {}).get("color_by", "none")
        auto = ptk.ManifestTags.auto(
            [*self._sheet_steps, *self._steps], rule, tags.slots
        )
        above = None
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if not isinstance(step, BuilderStep):
                if above:
                    tags.set_tag([item], above, auto=True)
                continue
            if step.step_id in user:
                tags.set_tag([item], user[step.step_id])
            above = auto.get(step.step_id)
            if above:
                tags.set_tag([item], above, auto=True)

    def _apply_formatting(self, tree) -> None:
        """Set column/row tints, behavior colors, icons, and column widths."""
        from qtpy.QtCore import Qt
        from qtpy.QtGui import QColor

        content_col = COL_DESC

        # Row tints via delegate (fillRect bypasses the host's QSS stripping).
        tree._child_row_color = QColor(0, 0, 0, 55)

        # Column tints — darken Step and Behaviors columns
        tree.clear_column_tints()
        tree.set_column_tint(COL_STEP, QColor(0, 0, 0, 45))
        tree.set_column_tint(COL_BEHAVIORS, QColor(0, 0, 0, 45))

        # Icons: step icon on parents -- a "not in doc" row's marked as such
        # -- and a type-coded icon on child Content column.
        not_in_doc = [("not_in_doc", StepStatus.HELP["not_in_doc"])]
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step = parent.data(0, Qt.UserRole)
            self._set_row_status(
                parent,
                [] if isinstance(step, BuilderStep) else not_in_doc,
                icon=self._row_icon(parent),
            )
            for j in range(parent.childCount()):
                child = parent.child(j)
                obj_name = child.text(content_col)
                if not obj_name:
                    continue
                obj_data = child.data(0, Qt.UserRole)
                icon = self.manifest_host.object_icon(obj_data, obj_name)
                if icon is not None:
                    child.setIcon(content_col, icon)
                else:
                    # Neutral grey before assessment; assessment will repaint
                    # with the actual status color if there's a problem.
                    tree.set_item_type_icon(
                        child, "close", column=content_col, color=STEP_ICON_COLOR
                    )

        # Column widths
        header = tree.header()
        header.setMinimumSectionSize(60)
        header.resizeSection(COL_STEP, 140)
        header.resizeSection(COL_BEHAVIORS, 110)
        header.resizeSection(COL_START, 55)
        header.resizeSection(COL_END, 55)

        # Run registered formatters
        tree.apply_formatting()

    def _set_row_status(self, item, issues, icon=None) -> None:
        """Mark *item*'s row with its *issues* -- ``(status, text)`` pairs --
        the one status signal a row carries: its icon in the Step column, in
        the worst issue's colour (*icon*: the row's own shape, else that
        severity's), and a row tooltip on every cell listing them, a coloured
        glyph before each (``TreeWidget.set_row_tooltip``).  No issues: the
        row's own icon, neutral, and no row tooltip."""
        from qtpy import QtGui

        tree = self.ui.tbl_steps
        worst = ManifestData.worst(status for status, _text in issues)
        if icon is None and worst is not None:
            icon = ManifestData.LEVEL_ICONS.get(ManifestData.level(worst))
        if icon:
            color = ManifestData.status_color(worst) if worst else None
            tree.set_item_icon(item, icon, color=color or STEP_ICON_COLOR)
        else:
            item.setIcon(COL_STEP, QtGui.QIcon())
        tree.set_row_tooltip(item, ManifestData.issues_html(issues) or None)

    def _mark_step_row(self, item, step_status=None) -> None:
        """Mark a step row (:meth:`_set_row_status`) with what the shown
        assessment found (*step_status*; ``None``: none) and with its
        range's collisions (``_range_issues``, the Start / End column's)."""
        from qtpy.QtCore import Qt

        issues = self._step_issues(step_status) if step_status is not None else []
        issues += self._range_issues.get(item.data(0, Qt.UserRole).step_id, [])
        self._set_row_status(item, issues, icon=self._row_icon(item))

    def _mark_step_rows(self) -> None:
        """Mark every step row (:meth:`_mark_step_row`) from the shown
        assessment and the range collisions."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        results = {r.step_id: r for r in self._last_results or ()}
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            step = item.data(0, Qt.UserRole)
            if isinstance(step, BuilderStep):
                self._mark_step_row(item, results.get(step.step_id))

    @staticmethod
    def _behavior_names(names) -> str:
        return ", ".join(ManifestData.fmt_behavior(b) for b in names)

    def _step_issues(self, step_status) -> list:
        """A step row's ``(status, text)`` issues (:meth:`_set_row_status`):
        its own status, then each object with a behavior issue, and what a
        Build changes besides."""
        r = step_status
        issues = []
        groups: dict = {}  # an object status -> the objects at it
        for o in r.objects:
            if o.status != "valid" and o.status not in _BEHAVIOR_ISSUES:
                groups.setdefault(o.status, []).append(o.name)
        if (
            r.status in StepStatus.HELP
            and r.status not in groups
            and r.status not in _BEHAVIOR_ISSUES
        ):
            issues.append((r.status, StepStatus.HELP[r.status]))  # the step's own
        for status, names in groups.items():
            if status in StepStatus.HELP:
                issues.append(
                    (status, f"{', '.join(names)}: {StepStatus.HELP[status]}")
                )
        for o in r.objects:
            if o.status not in _BEHAVIOR_ISSUES:
                continue
            names = o.broken_behaviors or o.stale_behaviors or o.behaviors
            word = _BEHAVIOR_WORDS[o.status]
            issues.append((o.status, f"{o.name}: {self._behavior_names(names)} {word}"))
        if r.dropped_behaviors:
            dropped = ", ".join(
                f"{name} \u2192 {ManifestData.fmt_behavior(b)}"
                for name, b in r.dropped_behaviors
            )
            issues.append(
                (
                    "missing_behavior",
                    f"Keys of dropped behaviors -- Build removes them: {dropped}",
                )
            )
        if r.additional_objects:
            extra = ", ".join(r.additional_objects)
            issues.append(("additional", f"In the shot, not in the manifest: {extra}"))
        if r.updates:
            done = " and ".join(StepStatus.UPDATES[u] for u in r.updates)
            issues.append(("missing_shot", f"Build {done}."))
        if r.shrinkable_frames > 0:
            issues.append(("valid", f"{r.shrinkable_frames:.0f}f unused"))
        return issues

    def _object_issues(self, obj_st) -> list:
        """An object row's ``(status, text)`` issues (:meth:`_set_row_status`)."""
        status = obj_st.status
        if status == "missing_object":
            return [
                (
                    status,
                    f"Not found in {self.manifest_host.APP} -- an artist's to add; "
                    "Build never creates objects.",
                )
            ]
        if status == "missing_behavior":
            lines = []
            for b in obj_st.broken_behaviors or obj_st.behaviors:
                entry = ManifestData.fmt_behavior(b)
                try:
                    desc = self.behaviors.load_behavior(b).get("description", "")
                except Exception:
                    desc = ""
                lines.append(f"{entry} \u2014 {desc}" if desc else entry)
            return [(status, "Not verified:\n" + "\n".join(lines))]
        if status == "user_animated" and obj_st.key_range:
            lo, hi = obj_st.key_range
            return [(status, f"User-animated: keys {lo:.0f}-{hi:.0f}")]
        if status in StepStatus.HELP:
            return [(status, StepStatus.HELP[status])]
        return []

    def _apply_assessment(self, results: list) -> None:
        """Mark each row with what the assessment found (:meth:`_set_row_status`:
        an icon and a row tooltip, nothing tinted), count the step's behavior
        issues in its Behaviors cell, and add the objects animating in a
        step's shot that it neither lists nor holds."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        col_count = tree.columnCount()
        content_col = COL_DESC
        beh_col = COL_BEHAVIORS

        status_map = {r.step_id: r for r in results}
        for i in range(tree.topLevelItemCount()):
            parent = tree.topLevelItem(i)
            step_data = parent.data(0, Qt.UserRole)
            if not isinstance(step_data, BuilderStep):
                continue
            step_status = status_map.get(step_data.step_id)
            # Every step row, once: one this assessment did not judge (shown
            # since) still says its range's collisions.
            self._mark_step_row(parent, step_status)
            if step_status is None:
                continue

            # The Behaviors cell counts the objects with a behavior issue.
            counts: dict = {}
            for o in step_status.objects:
                if o.status in _BEHAVIOR_ISSUES:
                    word = _BEHAVIOR_WORDS[o.status]
                    counts[word] = counts.get(word, 0) + 1
            if counts:
                parent.setText(
                    beh_col, ", ".join(f"{n} {word}" for word, n in counts.items())
                )

            obj_status_map = {o.name: o for o in step_status.objects}
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_data = child.data(0, Qt.UserRole)
                if not isinstance(child_data, BuilderObject):
                    continue
                obj_st = obj_status_map.get(child_data.name)
                if obj_st is None:
                    continue
                if obj_st.behaviors:
                    beh_widget = tree.itemWidget(child, beh_col)
                    if beh_widget is not None:
                        self._color_behavior_label(
                            child_data, beh_widget, step_id=step_status.step_id
                        )
                if obj_st.status == "valid":
                    # Re-resolve icon: initial formatting may have set a
                    # fallback X because the node didn't exist yet
                    # (common for audio clips before build).
                    icon = self.manifest_host.object_icon(child_data, child.text(content_col))
                    if icon is not None:
                        child.setIcon(content_col, icon)
                self._set_row_status(child, self._object_issues(obj_st))

            # Additional objects (in shot but not in CSV): the shot's members
            # are listed already (_add_member_rows); what animates in its
            # range without being one is added.
            key = ptk.ShotStore.member_key
            listed = {
                key(parent.child(j).data(0, Qt.UserRole).name)
                for j in range(parent.childCount())
                if isinstance(parent.child(j).data(0, Qt.UserRole), BuilderObject)
            }
            extras = [n for n in step_status.additional_objects if key(n) not in listed]
            for extra_name in extras:
                display = (
                    self.manifest_host.leaf_name(extra_name)
                    if self._use_short_names
                    else extra_name
                )
                extra_item = tree.create_item(
                    ["", "", display, "", "", ""], parent=parent
                )
                if display != extra_name:
                    extra_item.setToolTip(content_col, extra_name)
                font = extra_item.font(content_col)
                font.setItalic(True)  # not the manifest's: set apart, untinted
                for c in range(col_count):
                    extra_item.setFont(c, font)
                icon = self.manifest_host.object_icon(None, extra_name)
                if icon is not None:
                    extra_item.setIcon(content_col, icon)
                self._set_row_status(
                    extra_item,
                    [
                        (
                            "additional",
                            "Animates in the shot's range, but neither the "
                            "manifest nor the shot lists it.",
                        )
                    ],
                )

        self._editor.decorate()
        self._refresh_export_preview()  # an open one shows these rows

    def _issue_ids(self) -> set:
        """The steps the shown assessment found something in: Build has work
        there, or its status is not valid."""
        return {
            r.step_id
            for r in self._last_results or ()
            if r.needs_build or r.status not in ("valid", "locked")
        }

    def _extra_rows(self) -> list:
        """The step rows holding an object the step does not list -- a member
        of its shot, or one animating in its range (once assessed)."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        rows = []
        for i in range(tree.topLevelItemCount()):
            row = tree.topLevelItem(i)
            if not isinstance(row.data(0, Qt.UserRole), BuilderStep):
                continue
            for j in range(row.childCount()):
                data = row.child(j).data(0, Qt.UserRole)
                if not isinstance(data, BuilderObject) or data.origin == "member":
                    rows.append(row)
                    break
        return rows

    def expand_missing(self) -> None:
        """Expand the step rows the shown assessment found something in
        (Expand > Rows with Issues); what it found goes to the log."""
        if not self._last_results:
            self._set_footer("Assess first to find the issues.")
            return
        ids = self._issue_ids()
        if not ids:
            self._set_footer("No issues found.")
            return
        lines = [
            f"  {r.step_id}: {'; '.join(text for _s, text in self._step_issues(r))}"
            for r in self._last_results
            if r.step_id in ids
        ]
        self.logger.info("Expand Missing (%d steps):\n%s", len(lines), "\n".join(lines))
        self._set_footer(f"{len(ids)} step(s) with issues expanded.")
        for item in self._step_items(ids):
            item.setExpanded(True)

    def expand_extra(self) -> None:
        """Expand the step rows holding an object the step does not list
        (Expand > Rows with Objects Not in the Manifest)."""
        rows = self._extra_rows()
        if not rows:
            self._set_footer("No step's shot holds an object it does not list.")
            return
        for row in rows:
            row.setExpanded(True)
        self._set_footer(
            f"{len(rows)} step(s) with objects not in the manifest expanded."
        )
