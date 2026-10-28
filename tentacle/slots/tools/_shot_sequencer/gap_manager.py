# !/usr/bin/python
# coding=utf-8
"""Gap and range-highlight handlers for the Shot Sequencer controller.

Provides :class:`GapManagerMixin` -- mixed into
:class:`~.controller.ShotSequencerController` to handle gap resize, move,
lock, and range-highlight interactions.  Every edit brackets through the
store's ``scene_edit`` (one named undo step, paired with its restore point)
and is expressed through the host-neutral ``ShotSequencer`` surface, so one
copy serves both hosts.
"""

from __future__ import annotations

# Threshold for detecting meaningful time deltas (frame-level tolerance).
TIME_SNAP_EPS = 1e-3

__all__ = ["GapManagerMixin"]


class GapManagerMixin:
    """Mixin supplying gap-overlay and range-highlight handlers.

    Expects the host class to provide:

    * ``sequencer`` — the host's ``ShotSequencer`` instance
    * ``active_shot_id`` — property returning the current shot id
    * ``_sync_to_widget()`` / ``_sync_combobox()`` (edits bracket through
      ``sequencer.store.scene_edit()``, which records the restore point)
    * ``_get_sequencer_widget()``
    * ``_syncing`` — bool flag
    * ``_segment_cache`` / ``_sub_row_cache`` — dicts flushed by
      ``_gap_edit_epilogue`` after boundary edits
    * ``_set_footer()`` — status line (a refused drag is an answer, not a
      silent no-op)
    * ``_neighbour_shots()`` — prev/next around a shot id
    * ``logger``
    """

    # ---- range highlight -------------------------------------------------

    def on_range_highlight_changed(self, start: float, end: float) -> None:
        """Update the active shot when a range-highlight handle is dragged.

        The shot's own bound (its edges, the ruler band's edges) never moves
        the shot's keys.  Set 2026-09-06 after a plain drag slid the whole
        shot:

        * **Drag** -- the bound moves and the neighbouring shots ripple with
          their keys so the gaps survive (``resize_shot_bounds``).
        * **Ctrl+drag** -- the bound moves and no key does: the shot grows
          over the keys in the gap and on into the neighbour, whose facing
          bound gives way, or shrinks and leaves its keys -- to the neighbour
          when the two are flush (``ShotSequencer.set_shot_edge``, *push*).
          Membership follows the keys that changed hands.
        * **Shift+drag** -- retime: the shot's keys scale into the new span,
          neighbours ripple (``resize_shot``).  Shift wins over Ctrl for now.

        The ruler band's body drag carries no modifier and is always a move
        (both edges arrive shifted by one delta).
        """
        if self.sequencer is None or self.active_shot_id is None:
            return

        shot = self.sequencer.shot_by_id(self.active_shot_id)
        if shot is None:
            return

        ctrl_held, shift_held = self._drag_modifiers()

        ds = start - shot.start
        de = end - shot.end

        # Both edges moved by the same amount → translate the entire shot.
        # NOTE: the band's body drag carries no modifier -- it is grabbed on
        # the RULER's shot band, since the highlight's own body has to pass
        # presses through for the timeline's marquee to work inside the
        # active shot.  A body drag always means move_shot(), keys + ripple.
        if abs(ds - de) < TIME_SNAP_EPS and abs(ds) > TIME_SNAP_EPS:
            self._syncing = True
            try:
                with self.sequencer.store.scene_edit("Move Shot"):
                    self.sequencer.move_shot(self.active_shot_id, start)
            finally:
                self._syncing = False
            self._gap_edit_epilogue()
            return

        # One edge moved: Shift retimes, Ctrl moves the bound and nothing
        # else, a plain drag moves the bound and ripples the neighbours.
        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("Resize Shot"):
                if shift_held:
                    self.sequencer.resize_shot(self.active_shot_id, start, end)
                elif ctrl_held:
                    if self.sequencer.set_shot_edge(
                        shot.shot_id,
                        new_start=start if abs(ds) > TIME_SNAP_EPS else None,
                        new_end=end if abs(de) > TIME_SNAP_EPS else None,
                        push=True,
                    ):
                        # Nothing else moves -- the system's own samples
                        # included: a followed pin re-times its ramp.
                        self.sequencer.reconcile_system_edits(follow=False)
                else:
                    self.sequencer.resize_shot_bounds(self.active_shot_id, start, end)
        finally:
            self._syncing = False
        self._gap_edit_epilogue()

    def _drag_modifiers(self):
        """``(ctrl, shift)`` as the widget recorded them at the press."""
        widget = self._get_sequencer_widget()
        return (
            bool(getattr(widget, "ctrl_held_at_press", False)),
            bool(getattr(widget, "shift_held_at_press", False)),
        )

    # ---- helpers ---------------------------------------------------------

    def _find_shot_by_start(self, frame: float):
        """Return the shot whose start is closest to *frame*, or None."""
        for shot in self.sequencer.sorted_shots():
            if abs(shot.start - frame) < TIME_SNAP_EPS:
                return shot
        return None

    def _find_shot_by_end(self, frame: float):
        """Return the shot whose end is closest to *frame*, or None."""
        for shot in self.sequencer.sorted_shots():
            if abs(shot.end - frame) < TIME_SNAP_EPS:
                return shot
        return None

    def _refuse_if_gap_locked(self, shot, side: str) -> bool:
        """True (and the drag is refused) when that gap is locked.

        A lock is a statement about the gap's WIDTH, so it stops the two
        gestures that would change it — either edge handle — and nothing
        else.  The body drag slides the gap at constant width, a shot
        resize ripples its neighbour so the width survives, and a respace
        already skips locked gaps: none of those is a resize, so none is
        refused here.
        """
        # ``_neighbour_shots`` is the host's own prev/next lookup (the shot
        # menu's Merge entries read it); a second copy here would be one more
        # place for "which shot is next" to drift.  Either side is ``None``
        # where the timeline ends -- the span before the first shot and the
        # tail handle after the last one flank no gap, so neither can be
        # locked.
        neighbours = self._neighbour_shots(shot.shot_id)
        if side == "left":
            left, right = neighbours["merge_prev"], shot
        else:
            left, right = shot, neighbours["merge_next"]
        if left is None or right is None:
            return False
        if not self.sequencer.store.is_gap_locked(left.shot_id, right.shot_id):
            return False
        self.logger.debug(
            "Gap %s-%s is locked; resize refused", left.shot_id, right.shot_id
        )
        self._set_footer(
            f"Gap between “{left.name}” and “{right.name}” "
            "is locked — unlock it to resize."
        )
        return True

    def _gap_edit_epilogue(self):
        """Common cleanup after any gap edit: the store saved, then the one
        post-edit refresh (boundaries just moved, so the playback range, set
        from the OLD ones, is stale too)."""
        if self.sequencer is not None:
            self.sequencer.store.mark_dirty()
        self._after_shot_change()

    # ---- gap resize / move -----------------------------------------------

    def on_gap_resized(self, original_next_start: float, new_next_start: float) -> None:
        """Handle a right-edge gap drag: the following shot's ``.start``.

        Same grammar as every other bound handle (:meth:`on_range_highlight_changed`),
        applied to the touched shot whether or not it is the active one:

        * **Drag** -- slide that shot intact, alone: keys ride, nothing else
          moves, so the gap changes width by the drag and the shot stops at
          its other neighbour.  (A SHOT handle is the one that keeps the gaps
          and ripples the rest.)
        * **Ctrl+drag** -- its start moves, its end stays, keys stay; nothing
          else moves (the gap changes width), and past the gap the shot
          before gives way (``ShotSequencer.set_shot_edge``, *push*).
        * **Shift+drag** -- its keys are retimed into the new range.
        """
        if self.sequencer is None:
            return

        delta = new_next_start - original_next_start
        if abs(delta) < TIME_SNAP_EPS:
            return

        target = self._find_shot_by_start(original_next_start)
        if target is None:
            return
        if self._refuse_if_gap_locked(target, "left"):
            return

        ctrl_held, shift_held = self._drag_modifiers()
        # The head cap: the FIRST shot's start, with no gap before it to
        # slide into.  A shot's own bound, so it moves as every other shot
        # border does -- the bound alone, keys stay (nothing upstream to
        # ripple) -- never a slide of the whole shot.
        is_head_cap = self._neighbour_shots(target.shot_id)["merge_prev"] is None

        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("Resize Gap"):
                if ctrl_held or shift_held:
                    if self.sequencer.set_shot_edge(
                        target.shot_id,
                        new_start=new_next_start,
                        scale=shift_held,
                        push=True,
                    ):
                        # Ctrl moves the bound and nothing else, samples
                        # included; a Shift retime carried its own.
                        self.sequencer.reconcile_system_edits(follow=shift_held)
                elif is_head_cap:
                    self.sequencer.resize_shot_bounds(
                        target.shot_id, new_next_start, target.end
                    )
                else:
                    self.sequencer.slide_shot(
                        target.shot_id, new_next_start, direction=None
                    )
        finally:
            self._syncing = False
        self._gap_edit_epilogue()

    def on_gap_left_resized(
        self, original_prev_end: float, new_prev_end: float
    ) -> None:
        """Handle a left-edge gap drag: the preceding shot's ``.end``.

        The overlay placed after the LAST shot is a ``tail`` handle whose left
        edge is that shot's end, so the final shot has the handle every other
        shot has.  Same grammar as :meth:`on_gap_resized`:

        * **Drag** -- slide that shot intact, alone: keys ride, nothing else
          moves.  The tail cap is the exception: it is the last shot's OWN
          bound (no gap follows), so a plain drag moves that bound and
          nothing else, like every other shot border -- it used to slide the
          whole shot, which read as the border misbehaving (2026-09-09).
        * **Ctrl+drag** -- its end moves, its start stays, keys stay; nothing
          else moves, and past the gap the shot after gives way.
        * **Shift+drag** -- its keys are retimed into the new range.
        """
        if self.sequencer is None:
            return

        delta = new_prev_end - original_prev_end
        if abs(delta) < TIME_SNAP_EPS:
            return

        target = self._find_shot_by_end(original_prev_end)
        if target is None:
            return
        if self._refuse_if_gap_locked(target, "right"):
            return

        ctrl_held, shift_held = self._drag_modifiers()
        is_tail_cap = self._neighbour_shots(target.shot_id)["merge_next"] is None

        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("Resize Gap"):
                if ctrl_held or shift_held:
                    if self.sequencer.set_shot_edge(
                        target.shot_id,
                        new_end=new_prev_end,
                        scale=shift_held,
                        push=True,
                    ):
                        # Ctrl moves the bound and nothing else, samples
                        # included; a Shift retime carried its own.
                        self.sequencer.reconcile_system_edits(follow=shift_held)
                elif is_tail_cap:
                    self.sequencer.resize_shot_bounds(
                        target.shot_id, target.start, new_prev_end
                    )
                else:
                    self.sequencer.slide_shot(
                        target.shot_id, target.start + delta, direction=None
                    )
        finally:
            self._syncing = False
        self._gap_edit_epilogue()

    def on_gap_moved(
        self,
        old_start: float,
        old_end: float,
        new_start: float,
        new_end: float,
    ) -> None:
        """Handle body gap drag — slide the gap while preserving its width.

        Determines which gap this is relative to the active shot:

        * **Right gap of active shot** (left_shot == active):
          the active shot's end follows the gap (a bound move, keys left in
          place — Shift retimes them) and the right shot *slides*
          downstream intact (outer edge).
        * **Left gap of active shot** (right_shot == active):
          the active shot's start follows the gap (inner edge, same rule)
          and the left shot *slides* upstream intact (outer edge).
        * **Neither flanking shot is active**: both shots slide in
          their respective directions (outer-only behavior).
        """
        if self.sequencer is None:
            return

        delta = new_start - old_start
        if abs(delta) < TIME_SNAP_EPS:
            return

        left_shot = self._find_shot_by_end(old_start)
        right_shot = self._find_shot_by_start(old_end)

        if left_shot is None and right_shot is None:
            return

        widget = self._get_sequencer_widget()
        shift_held = getattr(widget, "shift_held_at_press", False)
        active_id = self.active_shot_id

        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("Move Gap"):
                # Determine which shot is inner (active, gets scaled)
                # and which is outer (gets slid intact).
                # Order: slide the outer shot first, then resize the
                # inner shot, to avoid stale-position issues.

                left_is_active = (
                    left_shot is not None
                    and active_id is not None
                    and left_shot.shot_id == active_id
                )
                right_is_active = (
                    right_shot is not None
                    and active_id is not None
                    and right_shot.shot_id == active_id
                )

                if left_is_active:
                    # Right gap of active shot.
                    # Outer: slide right shot downstream first.
                    if right_shot is not None:
                        self.sequencer.slide_shot(
                            right_shot.shot_id,
                            right_shot.start + delta,
                            direction="downstream",
                            _enforce=False,
                        )
                    # Inner: the active shot's end follows the gap (no
                    # ripple — the outer slide already repositioned the
                    # adjacent shot).  Shift retimes its keys with it.
                    self.sequencer.set_shot_edge(
                        left_shot.shot_id,
                        new_end=left_shot.end + delta,
                        scale=shift_held,
                    )

                elif right_is_active:
                    # Left gap of active shot.
                    # Outer: slide left shot upstream first.
                    if left_shot is not None:
                        self.sequencer.slide_shot(
                            left_shot.shot_id,
                            left_shot.start + delta,
                            direction="upstream",
                            _enforce=False,
                        )
                    # Inner: the active shot's start follows the gap (no
                    # ripple).  Shift retimes its keys with it.
                    self.sequencer.set_shot_edge(
                        right_shot.shot_id,
                        new_start=right_shot.start + delta,
                        scale=shift_held,
                    )
                else:
                    # Neither flanking shot is active — outer-only.
                    if right_shot is not None:
                        self.sequencer.slide_shot(
                            right_shot.shot_id,
                            right_shot.start + delta,
                            direction="downstream",
                            _enforce=False,
                        )
                    if left_shot is not None:
                        self.sequencer.slide_shot(
                            left_shot.shot_id,
                            left_shot.start + delta,
                            direction="upstream",
                            _enforce=False,
                        )

                # One reconcile pass for the whole compound operation.
                self.sequencer.reconcile_system_edits()
        finally:
            self._syncing = False
        self._gap_edit_epilogue()

    # ---- gap lock --------------------------------------------------------

    def on_gap_lock_changed(
        self, gap_start: float, gap_end: float, locked: bool
    ) -> None:
        """Handle a single gap's lock state being toggled via context menu.

        The overlay reports the gap by its FRAMES, and the store keys locks
        by the flanking shot ids, so the two have to be matched up.  Matching
        each edge independently against an exact-ish frame silently found
        nothing whenever an overlay's cached span had drifted from the store
        by more than a rounding — and a lock that resolves to nothing is
        never written, so the overlay drew itself "[Locked]" while the store
        stayed empty and the next rebuild handed the lock straight back.
        Resolve the PAIR instead: score every adjacent pair against both
        edges and take the best, which cannot come back half-resolved.
        """
        if self.sequencer is None:
            return

        pair = self._gap_pair_at(gap_start, gap_end)
        if pair is None:
            self.logger.warning(
                "Gap lock ignored: no shot pair flanks [%s, %s]", gap_start, gap_end
            )
            self._set_footer("Could not resolve that gap — lock not saved.")
            return

        left_shot, right_shot = pair
        store = self.sequencer.store
        if locked:
            store.lock_gap(left_shot.shot_id, right_shot.shot_id)
        else:
            store.unlock_gap(left_shot.shot_id, right_shot.shot_id)
        self.logger.debug(
            "Gap %s-%s %s",
            left_shot.shot_id,
            right_shot.shot_id,
            "locked" if locked else "unlocked",
        )

    def _gap_pair_at(self, gap_start: float, gap_end: float):
        """The adjacent shot pair whose gap best matches ``[gap_start, gap_end]``.

        Returns ``(left, right)`` or ``None`` when the timeline holds fewer
        than two shots.  The best match is taken outright rather than gated
        on a tolerance: the caller has a gap overlay in hand, so one of these
        pairs IS it, and refusing on a rounding is what lost the lock.
        """
        shots = self.sequencer.sorted_shots() if self.sequencer else []
        if len(shots) < 2:
            return None
        return min(
            zip(shots, shots[1:]),
            key=lambda p: abs(p[0].end - gap_start) + abs(p[1].start - gap_end),
        )

    def on_gap_lock_all(self) -> None:
        """Lock all gaps so they are preserved during respace."""
        if self.sequencer is None:
            return
        self.sequencer.store.lock_all_gaps()
        widget = self._get_sequencer_widget()
        if widget is not None:
            widget.set_all_gap_overlays_locked(True)

    def on_gap_unlock_all(self) -> None:
        """Unlock all gaps so they follow the global gap value."""
        if self.sequencer is None:
            return
        self.sequencer.store.unlock_all_gaps()
        widget = self._get_sequencer_widget()
        if widget is not None:
            widget.set_all_gap_overlays_locked(False)
