# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest table's Start / End column: what a step's range is
(typed, auto-filled from the scene's animation regions, or its shot's), how a
typed one is checked and cascades, and how the cells show it.

The rules are ``pythontk``'s ``RangeResolver``; this is the column's glue.  A
double-click or a committed cell is offered to Local Edits first.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

from typing import List, Optional, Tuple

import pythontk as ptk
from pythontk import BuilderStep

from .manifest_data import COL_END, COL_START, PASTEL_STATUS


class RangeColumnMixin:
    """The Start / End column, mixed into ``ShotManifestController``.

    Uses the controller's ``ui.tbl_steps``, ``_steps``, ``_user_ranges`` /
    ``_seeded_ranges``, ``_last_resolved`` / ``_projected`` /
    ``_typed_shift`` / ``_inserts``, ``_cached_gaps`` / ``_cached_gap_ends``,
    ``_range_issues``, ``_editor``, ``_pairing()``, ``_is_built``,
    ``_step_is_built()``, ``_shown_steps()``, ``_manifest()``,
    ``_active_store()``, ``_detect_regions()``, ``_initial_shot_length`` /
    ``_fit_mode`` and ``sb``.
    """

    #: The Start / End tip of an unbuilt step a Build inserts in sheet order
    #: (``{where}``: after which shot).
    PROJECTED_TIP = (
        "Build inserts this step's shot {where}: these are its frames once the "
        "shots after it have moved later to make room."
    )
    #: The Start / End tip of an unbuilt step whose typed range Build's
    #: inserts move (``{typed}``: the range as typed; ``{push}``: how far).
    TYPED_RIDE_TIP = (
        "Typed as {typed} on the timeline as it is now. Build inserts shots "
        "before it, moving it {push:.0f} frames later with the shots after "
        "them: these are its frames then."
    )

    @property
    def _is_detection_mode(self) -> bool:
        """True when the steps came from the scene (its shots or detected
        animation), not a CSV -- so a build never removes a shot."""
        return bool(self._steps) and not self._csv_path

    @property
    def _use_selected_keys(self) -> bool:
        """True when a selected-keys detection mode is active.

        The store's detection_mode controls this regardless of whether
        steps came from a CSV or from scene detection.  CSV defines
        step names/objects; the detection mode defines how ranges are
        inferred.
        """
        store = self._active_store()
        return store is not None and store.detection_mode != "auto"

    def _all_ranges_complete(self) -> bool:
        """True when every step has a user-supplied (start, end) pair."""
        return ptk.RangeResolver.all_ranges_complete(self._steps, self._user_ranges)

    def _typed_ranges(self) -> dict:
        """The ranges the user typed: ``_user_ranges`` less what a load seeded
        from the steps' shots -- a step whose shot is gone since is placed
        like any unbuilt one, not where that shot was."""
        return {
            sid: rng
            for sid, rng in self._user_ranges.items()
            if self._seeded_ranges.get(sid) != rng
        }

    def _projected_inserts(self) -> list:
        """Where Build inserts each unbuilt step's shot on a built timeline
        (``ShotManifest.plan_insertions``' ``PlannedInsert`` s) -- in sheet
        order, the later shots moving out of its way.  A step with a typed
        range goes there instead, and the next new step follows it; nothing
        is projected before a first build or in a selected-keys mode.

        Planned afresh on every call: a plan reads what no store event
        announces -- keys trailing the last shot, the clips' lengths -- and
        each clip's length is read once per file as it is on disk
        (``AudioUtils.memo_duration``), so planning costs little (about 8 ms
        for 65 steps, 30 of them inserts, on 35 shots).
        """
        store = self._active_store()
        if store is None or self._use_selected_keys or not self._is_built:
            return []
        try:
            return self._manifest(store).plan_insertions(
                self._shown_steps(),
                typed=self._typed_ranges(),
                fit_mode=self._fit_mode,
                initial_shot_length=self._initial_shot_length,
            )
        except Exception as exc:  # a preview never breaks the table
            self.logger.debug("Insert preview failed: %s", exc)
            return []

    def _landed(self, ranges: dict) -> dict:
        """*ranges* (``{step_id: (start, end)}``, the timeline's current
        frames) where Build's inserts leave them (``ride_inserts`` through the
        inserts the table shows, ``_inserts``)."""
        return ptk.ShotManifest.ride_inserts(ranges, self._inserts)

    def _insert_place(self, plan, names: dict) -> str:
        """Where *plan* (a ``PlannedInsert``) puts its shot, in words: after
        which shot, or at the timeline's head."""
        if plan.after_step_id is not None:
            name = names.get(plan.after_step_id, plan.after_step_id)
            return f"after the shot Build gives '{name}'"
        if plan.after_shot_id is None:
            return "at the head of the timeline"
        shot = self._active_store().shot_by_id(plan.after_shot_id)
        return f"after shot '{shot.name}'" if shot is not None else "here"

    def _on_range_double_clicked(self, item, column) -> None:
        """Edit the double-clicked cell, else toggle the row.

        A step's name or description, or an object's name, edits through
        Local Edits (:class:`ManifestEditor`); Start / End edit
        on an unbuilt step's row.  Any other cell of a step row toggles it.
        """
        if self._editor.begin_edit(item, column):
            return
        from qtpy.QtCore import Qt

        is_parent = item.parent() is None
        if is_parent and column in (COL_START, COL_END):
            step_data = item.data(0, Qt.UserRole)
            if isinstance(step_data, BuilderStep) and not self._step_is_built(
                step_data.step_id
            ):
                self.ui.tbl_steps.editItem(item, column)
                return
        if is_parent:
            item.setExpanded(not item.isExpanded())

    def _on_item_changed(self, item, column) -> None:
        """Capture a committed cell: Local Edits' cells go to the editor
        (:meth:`ManifestEditor.commit_edit`); Start / End are ranges.

        Validation rules (Start/End):
        - Negative start values are rejected.
        - End must be > start when both are given.
        - Start must not precede the previous step's resolved end.

        After a valid range edit, downstream user ranges are cleared so
        the resolver can re-flow them from the new anchor, and the full
        table is refreshed.
        """
        if self._editor.commit_edit(item, column):
            return
        if column not in (COL_START, COL_END):
            return
        if item.parent() is not None:
            return
        from qtpy.QtCore import Qt

        step_data = item.data(0, Qt.UserRole)
        if not isinstance(step_data, BuilderStep):
            return

        # The edit rules (numbers, a start, start >= 0, end > start) are
        # RangeResolver.parse_range_edit's; both cells empty clears the range.
        # A typed range's cells show where Build's inserts move it: the cell
        # not edited is read as typed, or the range would move twice.
        texts = {COL_START: item.text(COL_START), COL_END: item.text(COL_END)}
        if step_data.step_id in self._typed_shift:
            typed_start, typed_end = self._user_ranges[step_data.step_id]
            other = COL_END if column == COL_START else COL_START
            kept = typed_end if other == COL_END else typed_start
            texts[other] = "" if kept is None else f"{kept:g}"
        try:
            user_range = ptk.RangeResolver.parse_range_edit(
                texts[COL_START], texts[COL_END]
            )
        except ValueError:
            self._revert_range_cell(item, step_data.step_id)
            return
        if user_range is None:
            self._user_ranges.pop(step_data.step_id, None)
            self._refresh_ranges()
            return
        start, end = user_range

        # Reject start before the previous step's resolved end -- both where
        # Build leaves them: the typed start (current frames) moved by the
        # inserts, against the step before as the table shows it.
        step_idx = self._step_index(step_data.step_id)
        if step_idx < 0:
            return
        landed = self._landed({step_data.step_id: (start, end)})
        prev_end = self._landed_previous_end(step_idx)
        if prev_end is not None and landed[step_data.step_id][0] < prev_end:
            self._revert_range_cell(item, step_data.step_id)
            return

        # Valid — store, clear downstream, and refresh.
        self._user_ranges[step_data.step_id] = (start, end)
        self._cascade_from(step_idx)
        self._refresh_ranges(from_step_idx=step_idx)

    def _landed_previous_end(self, step_idx: int) -> Optional[float]:
        """The end of the nearest step before *step_idx* that has one, where
        Build leaves it: a built step's shot moved by the inserts before it
        (the other rows already show where they land)."""
        built = self._pairing().shots
        landed = self._landed(
            {sid: (s, e) for sid, s, e, _u in self._last_resolved if sid in built}
        )
        resolved = [
            (sid, *landed[sid], user) if sid in landed else (sid, s, e, user)
            for sid, s, e, user in self._last_resolved
        ]
        return ptk.RangeResolver.previous_end(self._steps, resolved, step_idx)

    def _step_index(self, step_id: str) -> int:
        """Return the list index for *step_id*, or -1 if not found."""
        return ptk.RangeResolver.step_index(self._steps, step_id)

    def _refresh_ranges(self, from_step_idx: int = 0, mark: bool = True) -> list:
        """Re-resolve, auto-fill, and validate all ranges.

        This is the single entry point for updating the Range column
        after any edit, cascade, or clear operation.

        Parameters:
            from_step_idx: Passed to :meth:`_resolve_ranges` so steps before
                this index keep their last-resolved positions.
            mark: Mark the step rows with what the checks found
                (:meth:`_validate_range_collisions`); off for a caller that
                marks them next with an assessment (``_apply_assessment``).

        Returns:
            The resolved ranges list.
        """
        resolved = self._auto_fill_ranges(
            resolved=self._resolve_ranges(from_step_idx=from_step_idx)
        )
        self._validate_range_collisions(resolved, mark=mark)
        self._refresh_export_preview()  # an open one shows these frames
        return resolved

    def _cascade_from(self, step_idx: int) -> None:
        """Clear user ranges on all steps after *step_idx* so they re-flow."""
        ptk.RangeResolver.cascade_from(self._steps, self._user_ranges, step_idx)

    def _placement_on_regions(self) -> Optional[bool]:
        """Whether new shots go on the detected animation regions (``True``),
        one after another (``False``), or the build stops (``None``).

        Steps meet regions IN ORDER, which is right only when there is one
        region per step; when the counts differ that pairing is a guess, so
        the user decides with both counts in front of them.  Selected keys
        are the user's own boundaries and never ask.
        """
        regions = len(self._cached_gaps or [])
        auto = [s for s in self._steps if s.step_id not in self._user_ranges]
        if self._use_selected_keys or not regions or len(auto) in (0, regions):
            return True
        answer = self.sb.message_box(
            f"<b>{len(auto)} steps, {regions} animation regions.</b><br>"
            "New shots are placed on the scene's animation regions in order, "
            "which only lines up with one region per step.<br><br>"
            "<b>Yes</b> \u2014 place them on the regions anyway<br>"
            "<b>No</b> \u2014 place them one after another (adjust later)<br>"
            "<b>Cancel</b> \u2014 set the steps' ranges first",
            "Yes",
            "No",
            "Cancel",
        )
        if answer == "Yes":
            return True
        return False if answer == "No" else None

    def _resolve_ranges(
        self,
        from_step_idx: int = 0,
        regions: bool = True,
    ) -> List[Tuple[str, float, Optional[float], bool]]:
        """Compute a resolved (start, end) for every step.

        Detects/caches animation regions, then delegates to the
        standalone :func:`._range_resolver.resolve_ranges` algorithm.
        ``regions=False`` ignores them: steps are placed one after another.
        On a built timeline the regions place nothing (no scan): a built step
        is its shot, an unbuilt one goes where Build inserts it
        (:meth:`_projected_inserts`), or to its typed range -- where Build's
        inserts move it (``ShotManifest.ride_inserts``: a typed range is in
        the timeline's current frames).
        """
        # Nothing here survives from the last resolve: a step that stops
        # being projected (built, hidden, typed) must not keep its tip.
        self._projected = {}
        self._typed_shift = {}
        self._range_issues = {}
        self._inserts = []
        if not self._steps:
            return []

        store = self._active_store()
        gap = store.gap if store else 0.0
        det_threshold = store.detection_threshold if store else 5.0
        use_sel = self._use_selected_keys
        built = {}
        if store is not None and not use_sel:
            built = {
                sid: (shot.start, shot.end)
                for sid, shot in self._pairing(store=store).shots.items()
            }

        # Detect animation regions for auto-fill (cached per assess cycle).
        if built:
            gap_starts = []
        elif self._cached_gaps is not None:
            gap_starts = self._cached_gaps
        else:
            gap_starts, self._cached_gap_ends = ptk.RangeResolver.gaps_from_regions(
                self._detect_regions(det_threshold)
            )
            self._cached_gaps = gap_starts

        if not regions:
            gap_starts = []
        if use_sel and not gap_starts:
            return []

        # When no animation regions are detected (regardless of mode),
        # use uniform default durations so steps get sensible placeholder
        # ranges instead of behavior-derived micro-durations.  This also
        # covers the case where the scene has animation but the chosen
        # detection mode found no boundaries (e.g. skip_zero with no
        # zero-valued keys).  The store's initial_shot_length is the
        # user-facing policy for new-shot sizing (default 200f).
        default_dur = (
            self._initial_shot_length if (not gap_starts and not use_sel) else 0
        )

        resolved = self.manifest_host.range_resolver_cls().resolve_ranges(
            steps=self._steps,
            user_ranges={**self._user_ranges, **built},
            gap_starts=gap_starts,
            gap_end_map=self._cached_gap_ends or {},
            gap=gap,
            use_selected_keys=use_sel,
            last_resolved=self._last_resolved,
            from_step_idx=from_step_idx,
            default_duration=default_dur,
        )
        # A built timeline takes a new step's shot in sheet order, rippling
        # the rest: those are its frames, not the regions' guess -- and a
        # typed range rides the ripple, as the shots after the inserts do.
        inserts = self._inserts = self._projected_inserts()
        plans = {p.step.step_id: p for p in inserts}
        names = {s.step_id: s.shot_name for s in self._steps}
        self._projected = {
            sid: self._insert_place(plan, names) for sid, plan in plans.items()
        }
        typed = {
            sid: rng
            for sid, rng in self._typed_ranges().items()
            if sid not in built and sid not in plans and rng[0] is not None
        }
        ridden = ptk.ShotManifest.ride_inserts(typed, inserts)
        self._typed_shift = {
            sid: ridden[sid][0] - rng[0]
            for sid, rng in typed.items()
            if ridden[sid][0] != rng[0]
        }
        if plans or self._typed_shift:
            resolved = [
                (r[0], plans[r[0]].start, plans[r[0]].end, False)
                if r[0] in plans
                else (r[0], *ridden[r[0]], True)
                if r[0] in self._typed_shift
                else r
                for r in resolved
            ]
        self._last_resolved = resolved
        return resolved

    def _set_range_to_current_frame(self, item, step_id: str) -> None:
        """Set the range start for *step_id* to the playhead's frame
        (``ManifestHost.current_frame``).

        Clears user ranges on subsequent steps so they cascade from the
        new anchor point.
        """
        frame = self.manifest_host.current_frame()
        if frame is None:
            return
        self._user_ranges[step_id] = (frame, None)

        step_idx = self._step_index(step_id)
        self._cascade_from(step_idx)
        self._refresh_ranges(from_step_idx=step_idx)

    def _auto_fill_ranges(self, resolved=None) -> list:
        """Auto-fill the Range column using resolved ranges.

        User-entered values are preserved; auto-filled values appear dim
        and italic.

        Parameters
        ----------
        resolved
            Pre-computed resolved ranges.  When ``None``,
            :meth:`_resolve_ranges` is called internally.

        Returns
        -------
        list
            The resolved ranges list (for reuse by collision validation).
        """
        if resolved is None:
            resolved = self._resolve_ranges()
        if not resolved:
            return resolved

        from qtpy.QtCore import Qt
        from qtpy.QtGui import QColor, QBrush

        tree = self.ui.tbl_steps
        dim = QBrush(QColor(PASTEL_STATUS["locked"][0]))
        step_map = {r[0]: r for r in resolved}
        # A built row shows its shot (``_refresh_timing``), never a guess.
        built = self._pairing().shots

        tree.blockSignals(True)
        try:
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                step_data = parent.data(0, Qt.UserRole)
                if not isinstance(step_data, BuilderStep):
                    continue
                entry = step_map.get(step_data.step_id)
                if entry is None or step_data.step_id in built:
                    continue
                step_id, start, end, is_user = entry
                parent.setText(COL_START, f"{start:.0f}")
                if end is not None:
                    parent.setText(COL_END, f"{end:.0f}")
                else:
                    parent.setText(COL_END, "")
                for col in (COL_START, COL_END):
                    font = parent.font(col)
                    if not is_user:
                        parent.setForeground(col, dim)
                        font.setItalic(True)
                    else:
                        font.setItalic(False)
                    parent.setFont(col, font)
        finally:
            tree.blockSignals(False)
        return resolved

    def _validate_range_collisions(self, resolved=None, mark: bool = True) -> int:
        """Find the shown steps whose ranges overlap a neighbour's and mark them.

        Each range is read where a Build leaves it: a built step's shot moved
        by the inserts before it (``ShotManifest.ride_inserts``), a projected
        insert where it lands, a typed range moved with the shots -- so a
        projection is checked like any range -- and a step the table hides is
        not checked at all.  Each such step's row says so
        (``_mark_step_rows``: its icon and row tooltip, nothing tinted; with
        *mark* -- off for a caller that marks the rows next).  An unbuilt
        row's Start / End cells show which ranges are typed (plain) and which
        auto-filled (dim), and what moves them; a built row's are its shot's
        (``_refresh_timing``).

        Returns the number of collisions found.
        """
        if resolved is None:
            resolved = self._resolve_ranges()

        from qtpy.QtCore import Qt
        from qtpy.QtGui import QColor, QBrush

        tree = self.ui.tbl_steps
        dim = QBrush(QColor(PASTEL_STATUS["locked"][0]))
        names = {s.step_id: s.shot_name for s in self._steps}
        resolved_map = {r[0]: r for r in resolved}
        built = self._pairing().shots

        shown = {s.step_id for s in self._shown_steps()}
        landing = self._landed({r[0]: (r[1], r[2]) for r in resolved if r[0] in built})
        placed = [
            (r[0], *landing[r[0]], r[3]) if r[0] in landing else r
            for r in resolved
            if r[0] in shown
        ]
        pairs = ptk.RangeResolver.find_collisions(placed) if len(placed) > 1 else []
        self._range_issues = {}
        for curr_id, next_id in pairs:
            for sid, other in ((curr_id, next_id), (next_id, curr_id)):
                self._range_issues.setdefault(sid, []).append(
                    ("collision", f"Its range overlaps '{names.get(other, other)}'s.")
                )

        # Block signals to prevent _on_item_changed from firing
        # recursively while we update foregrounds/tooltips.
        tree.blockSignals(True)
        try:
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                step_data = item.data(0, Qt.UserRole)
                if not isinstance(step_data, BuilderStep):
                    continue
                sid = step_data.step_id
                if sid in built:
                    continue  # its shot's frames and length (_refresh_timing)
                entry = resolved_map.get(sid)
                brush = QBrush() if entry and entry[3] else dim
                for col in (COL_START, COL_END):
                    item.setForeground(col, brush)
                    item.setBackground(col, QBrush())
                    item.setToolTip(col, self._range_tip(sid))
        finally:
            tree.blockSignals(False)
        if mark:
            self._mark_step_rows()
        return len(pairs)

    def _range_tip(self, step_id: str) -> str:
        """An unbuilt row's Start / End tooltip: where Build inserts its shot,
        or how far Build's inserts move its typed range (``""``: neither)."""
        where = self._projected.get(step_id)
        if where:
            return self.PROJECTED_TIP.format(where=where)
        push = self._typed_shift.get(step_id)
        if not push:
            return ""
        start, end = self._user_ranges[step_id]
        typed = f"{start:.0f}" if end is None else f"{start:.0f}-{end:.0f}"
        return self.TYPED_RIDE_TIP.format(typed=typed, push=push)

    def _revert_range_cell(self, item, step_id: str) -> None:
        """Revert Start/End cells to their last resolved values after a rejected edit."""
        tree = self.ui.tbl_steps
        tree.blockSignals(True)
        for entry in self._last_resolved:
            if entry[0] == step_id:
                _, s, e, _ = entry
                item.setText(COL_START, f"{s:.0f}")
                item.setText(COL_END, f"{e:.0f}" if e is not None else "")
                break
        else:
            item.setText(COL_START, "")
            item.setText(COL_END, "")
        tree.blockSignals(False)

    def _restore_user_ranges(self, tree) -> None:
        """Write ``_user_ranges`` values back into Start/End cells after a table rebuild."""
        from qtpy.QtCore import Qt
        from qtpy.QtGui import QColor, QBrush

        dim = QBrush(QColor(PASTEL_STATUS["locked"][0]))
        tree.blockSignals(True)
        try:
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                step_data = parent.data(0, Qt.UserRole)
                if not isinstance(step_data, BuilderStep):
                    continue
                user_range = self._user_ranges.get(step_data.step_id)
                if user_range is None:
                    # Auto-filled values appear dim (set by assess/auto-fill later)
                    if parent.text(COL_START):
                        parent.setForeground(COL_START, dim)
                        parent.setForeground(COL_END, dim)
                    continue
                start, end = user_range
                parent.setText(COL_START, f"{start:.0f}")
                if end is not None:
                    parent.setText(COL_END, f"{end:.0f}")
                else:
                    parent.setText(COL_END, "")
        finally:
            tree.blockSignals(False)
