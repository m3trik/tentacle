# !/usr/bin/python
# coding=utf-8
"""Clip and key motion for the Shot Sequencer panel: moving and resizing clips,
dragging and deleting keys, and growing a shot over content dragged past it.

:class:`ClipMotionMixin` is one of the concept mixins of
:class:`~tentacle.slots.tools._shot_sequencer.controller.ShotSequencerController`.
The writes are the host's (``self.host``, the host library's ``SequencerHost``):
the curves behind an attribute row, a sub-row's retime, an audio track's move,
the per-curve key commit and key deletes.  The shot edits are the engine's
(``self.sequencer``).
"""

import math

from pythontk import ShotBoundaryConflict

#: Near-zero guard for floating-point comparisons.
FLOAT_ZERO_EPS = 1e-6
#: How close a dragged key's reported time must be to a curve's key to be it.
KEY_MATCH_EPS = 1e-3

__all__ = ["ClipMotionMixin"]


class ClipMotionMixin:
    """Clip move / resize, per-key drag and delete handlers.

    Expects the controller to provide ``sequencer``, ``host``,
    ``_get_sequencer_widget()``, ``_shifted_out_keys``, ``_segment_cache`` /
    ``_sub_row_cache`` (flushed after boundary-moving edits),
    ``_audio_segments_cache`` (invalidated after audio-clip moves),
    ``_syncing`` (the re-entrancy guard shared with the store listener),
    ``_sync_to_widget()`` / ``_sync_combobox()``, ``_gap_edit_epilogue()``
    (:class:`~.gap_manager.GapManagerMixin`), ``_set_footer()`` and ``logger``.
    Edits bracket through ``sequencer.store.scene_edit()``, which records the
    restore point; an edit that turned out a no-op cancels it.
    """

    def _edit_bracket(self, label: str):
        """The undo bracket for a key edit: the store's ``scene_edit`` (restore
        point + paired, named step), or a plain named step when no sequencer
        is bound -- a key move needs no shots.  Either yields a handle whose
        ``cancel()`` drops the step of an edit that changed nothing."""
        if self.sequencer is not None:
            return self.sequencer.store.scene_edit(label)
        return self.host.undo_chunk(label)

    def on_clip_resized(
        self, clip_id: int, new_start: float, new_duration: float
    ) -> None:
        """Handle one clip's edge drag -- see :meth:`_commit_clip_resizes`."""
        self._commit_clip_resizes([(clip_id, new_start, new_duration)])

    def on_clips_batch_resized(self, resizes) -> None:
        """Handle an edge drag that scaled a SELECTION of clips as one unit.

        *resizes* is ``[(clip_id, new_start, new_duration), ...]``, already
        ordered so committing them one at a time never lands a clip on a
        span another has not left yet (the widget's
        ``ClipItem._collision_free_order``).  The whole gesture rides ONE
        undo step, so the selection comes back in a single Ctrl+Z.
        """
        self._commit_clip_resizes(list(resizes))

    def _resize_one_clip(self, widget, clip_id, new_start, new_duration):
        """Scale one clip's keys into its new span; ``None`` if nothing moved.

        Sub-row attribute clips scale only the targeted attribute's curves
        (``SequencerHost.scale_attribute_keys``).  Main track clips scale all
        curves on the object via :meth:`ShotSequencer.resize_object`, which
        also ripple-shifts downstream shots.  Audio clips are not resizable.

        Returns the label to report the clip by, or ``None`` when the resize
        wrote nothing (missing clip, audio, curves gone, zero-length span).
        """
        clip = widget.get_clip(clip_id) if widget else None
        if clip is None or clip.data.get("is_audio"):
            return None

        shot_id = clip.data.get("shot_id")
        obj_name = clip.data.get("obj")
        if shot_id is None or obj_name is None:
            return None

        orig_start = clip.data.get("orig_start")
        orig_end = clip.data.get("orig_end")
        if orig_start is None or orig_end is None:
            return None

        new_end = new_start + new_duration
        attr_name = clip.data.get("attr_name")
        if attr_name:
            if not self.host.scale_attribute_keys(
                obj_name,
                attr_name,
                orig_start,
                orig_end,
                new_start,
                new_end,
                ledger=self.sequencer.ledger,
            ):
                return None
            return f"{obj_name}.{attr_name}"
        self.sequencer.resize_object(
            shot_id, obj_name, orig_start, orig_end, new_start, new_end
        )
        return obj_name

    def _commit_clip_resizes(self, resizes) -> None:
        """Commit one edge-drag gesture, however many clips it scaled.

        Every clip in *resizes* is written inside ONE ``scene_edit`` -- the
        gesture is one edit, so it is one undo step -- and the epilogue runs
        once at the end rather than once per clip.
        """
        if self.sequencer is None:
            return
        widget = self._get_sequencer_widget()
        if widget is None or not resizes:
            return

        # _syncing up while our own key edits run: the host's key-edit
        # callbacks fire on them and would arm the debounce into a SECOND full
        # rebuild after the epilogue's own sync (the issue-7 refresh storm).
        # Same pattern as the gap handlers; the epilogue runs after the guard
        # is released.
        labels: list = []
        spans: list = []
        was_syncing = self._syncing
        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("Resize Clip") as edit:
                for clip_id, new_start, new_duration in resizes:
                    label = self._resize_one_clip(
                        widget, clip_id, new_start, new_duration
                    )
                    if label is None:
                        continue
                    labels.append(label)
                    spans.append((new_start, new_start + new_duration))
                if not labels:
                    # Nothing was scaled (curves gone, zero-length span): no
                    # dead restore point.
                    edit.cancel()
        finally:
            self._syncing = was_syncing
        if not labels:
            return
        # Full edit epilogue: resize_object can move shot boundaries and
        # ripple downstream -- without the cache flush, adjacent/all view
        # keeps painting downstream shots from stale segments, and the
        # combobox range labels go stale.
        self._gap_edit_epilogue()
        lo = min(a for a, _b in spans)
        hi = max(b for _a, b in spans)
        what = labels[0] if len(labels) == 1 else f"{len(labels)} clips"
        self._set_footer(f"Resized {what} · {lo:.0f}–{hi:.0f} ({int(hi - lo)}f)")

    def _apply_clip_move(self, clip_id: int, new_start: float) -> bool:
        """Move a single clip's keys without rebuilding the widget.

        Returns True if a widget sync is needed afterward.
        """
        widget = self._get_sequencer_widget()
        clip = widget.get_clip(clip_id) if widget else None
        if clip is None:
            return False

        # Audio clip move: the track's content moves (Maya: its keys in the
        # canonical store, the derived DG node re-synced when the batch
        # closes; Blender: the VSE sound strip, whose position IS its keyed
        # state).
        if clip.data.get("is_audio"):
            return self._move_audio_clip(clip, new_start)
        # Sub-row attribute clip move
        attr_name = clip.data.get("attr_name")
        if attr_name:
            return self._move_attribute_clip(clip, new_start, attr_name)
        # Animation clip move -- per-object within a shot
        return self._move_animation_clip(clip, new_start, widget)

    def _move_audio_clip(self, clip, new_start: float) -> bool:
        """The audio half of :meth:`_apply_clip_move`."""
        orig_start = clip.data.get("orig_start")
        orig_end = clip.data.get("orig_end")
        track_id = clip.data.get("audio_track_id")
        if orig_start is None or orig_end is None or not track_id:
            return False
        # The widget draws only the part of the segment inside its shot and
        # reports where THAT landed, so the move is measured from it: from
        # the segment's own start it was off by however much of the
        # segment began before the shot.
        delta = new_start - clip.data.get("vis_start", orig_start)
        if abs(delta) < FLOAT_ZERO_EPS:
            return False
        ledger = self.sequencer.ledger if self.sequencer is not None else None
        with self.host.moving_audio_track(track_id, ledger=ledger) as (
            move,
            lowest,
        ):
            self._lift_make_room_land(
                clip,
                orig_start,
                orig_end,
                delta,
                lowest,
                move,
                shown_from=clip.data.get("vis_start"),
            )
        clip.data["orig_start"] = orig_start + delta
        clip.data["orig_end"] = orig_end + delta
        if "vis_start" in clip.data:
            clip.data["vis_start"] += delta
        # The audio segment cache still holds the pre-move span -- the
        # immediate rebuild would snap the clip back to its old position
        # until the next refresh.
        self._audio_segments_cache = None
        return True

    def _move_attribute_clip(self, clip, new_start: float, attr_name: str) -> bool:
        """The sub-row attribute half of :meth:`_apply_clip_move`."""
        obj_name = clip.data.get("obj")
        orig_start = clip.data.get("orig_start")
        orig_end = clip.data.get("orig_end")
        if not obj_name or orig_start is None or orig_end is None:
            return False
        if not self.host.object_exists(obj_name):
            return False
        delta = new_start - orig_start
        if abs(delta) < FLOAT_ZERO_EPS:
            return False
        if self.sequencer is None:
            return True
        curves = self.host.curves_for_attr(obj_name, attr_name)
        if clip.data.get("is_stepped"):
            # Stepped sub-row clip: a point window at orig_start.
            # Shift-out tracking is omitted here because sub-rows are
            # built from live scene data (_provide_sub_rows), not from the
            # cached segments that _shifted_out_keys filters.

            def move(lo, _hi, d):
                self.sequencer.move_stepped_keys(
                    obj_name, lo, lo + d, attr_name=attr_name
                )

        elif curves:
            # Move to Shot's key-level primitive, not a plain relative key
            # shift: that one refuses to slide a key past another (the lift
            # below the curve's first key did nothing) and leaves the edit
            # ledger's claims behind.

            def move(lo, hi, d):
                self.sequencer.move_attribute_keys(
                    obj_name, attr_name, d, window=(lo, hi)
                )

        else:
            return True
        self._lift_make_room_land(
            clip, orig_start, orig_end, delta, self.host.first_key(curves), move
        )
        return True

    def _move_animation_clip(self, clip, new_start: float, widget) -> bool:
        """The per-object animation half of :meth:`_apply_clip_move`."""
        if self.sequencer is None:
            return False

        shot_id = clip.data.get("shot_id")
        obj_name = clip.data.get("obj")
        orig_start = clip.data.get("orig_start")
        orig_end = clip.data.get("orig_end")
        if shot_id is None or obj_name is None:
            return False
        if orig_start is None or orig_end is None:
            return False

        delta = new_start - orig_start
        if abs(delta) < FLOAT_ZERO_EPS:
            return False

        # Stepped (zero-duration) clips use delete-and-recreate
        if clip.data.get("is_stepped"):
            self.logger.debug(
                "[ANIM MOVE] stepped obj=%s from=%s to=%s shot=%s shift=%s",
                obj_name,
                orig_start,
                new_start,
                shot_id,
                getattr(widget, "shift_held_at_press", False),
            )
            self._lift_make_room_land(
                clip,
                orig_start,
                orig_start,
                delta,
                self.host.first_key(self.host.object_curves(obj_name)),
                lambda lo, _hi, d: self.sequencer.move_stepped_keys(
                    obj_name, lo, lo + d
                ),
            )
            shift_held = getattr(widget, "shift_held_at_press", False)
            if shift_held:
                shot = self.sequencer.shot_by_id(shot_id)
                if shot and (new_start < shot.start or new_start > shot.end):
                    self._shifted_out_keys.setdefault(obj_name, set()).add(new_start)
            else:
                # Normal move clears any shift-out exclusions for this object
                self._shifted_out_keys.pop(obj_name, None)
            return True

        shot = self.sequencer.shot_by_id(shot_id)
        # shot_by_id returns the live ShotBlock -- capture the pre-move
        # bounds by value for the post-move staleness check below.
        pre_bounds = (shot.start, shot.end) if shot else None
        self.logger.debug(
            "[ANIM MOVE] obj=%s orig=(%s,%s) new_start=%s delta=%s "
            "shot=%s range=(%s,%s) shift=%s",
            obj_name,
            orig_start,
            orig_end,
            new_start,
            delta,
            shot_id,
            shot.start if shot else "?",
            shot.end if shot else "?",
            getattr(widget, "shift_held_at_press", False),
        )

        shift_held = getattr(widget, "shift_held_at_press", False)

        if shift_held:
            self.sequencer.move_object_keys(obj_name, orig_start, orig_end, new_start)
        else:
            self.sequencer.move_object_in_shot(
                shot_id, obj_name, orig_start, orig_end, new_start
            )
            # Normal move clears any shift-out exclusions for this object
            self._shifted_out_keys.pop(obj_name, None)

        shot_after = self.sequencer.shot_by_id(shot_id)
        if shot_after:
            self.logger.debug(
                "[ANIM MOVE] post-move shot range=(%s,%s)",
                shot_after.start,
                shot_after.end,
            )
        # move_object_in_shot may have expanded the boundary and rippled
        # downstream -- cached segments for the other visible shots are
        # stale until flushed.
        if (
            pre_bounds is not None
            and shot_after is not None
            and (
                abs(shot_after.start - pre_bounds[0]) > FLOAT_ZERO_EPS
                or abs(shot_after.end - pre_bounds[1]) > FLOAT_ZERO_EPS
            )
        ):
            self._segment_cache.clear()
            self._sub_row_cache.clear()
        return True

    def _expand_shot_for_clip(self, clip, new_start: float, new_end: float) -> None:
        """Grow the shot if the clip's new range exceeds shot boundaries.

        Skipped when shift is held -- shift means "move freely across shot
        boundaries without changing them".
        """
        obj, attr = clip.data.get("obj"), clip.data.get("attr_name")
        curves = self.host.curves_for_attr(obj, attr) if obj and attr else None
        self._expand_shot_range(
            clip.data.get("shot_id"), new_start, new_end, curves=curves
        )

    def _lift_make_room_land(
        self, clip, lo, hi, delta, lowest, move, shown_from=None
    ) -> None:
        """Move a clip's content ``[lo, hi]`` by *delta*, its shot grown to
        enclose the landing, without the ripple ever touching that content.

        Making room ripples every envelope beyond the grown bound, and a clip's
        own content can sit inside one: an audio segment is track-wide (its
        clip draws only the part inside the shot) and a sub-row run can outlast
        its shot.  Rippled first it was swept along with the neighbour; landed
        first it stacked on the neighbour's pose.  So it is LIFTED below every
        shot's start -- no ripple window reaches there, since every envelope
        opens at its own shot's start -- and below *lowest*, the earliest key
        it could meet; then the room is made, then it lands.  A refused
        expansion lands it back where it was.  *move(lo, hi, delta)* shifts
        the content inside ``[lo, hi]``.

        The lift also clears where the ripple can LAND: growing the shot's
        head ripples the shots before it back by as far, and a long enough
        drag back carried the previous shot onto the lifted content.

        *shown_from* is where the clip's SHOWN part starts when that is later
        than *lo*: an audio clip draws only the part of its segment inside its
        shot, and the shot grows to enclose what was dragged, never the part
        of the segment that already lay before it -- enclosing that grew the
        shot backward and rippled the previous shot the other way.
        """
        seq = self.sequencer
        shots = seq.sorted_shots() if seq is not None else []
        grow_lo = lo if shown_from is None else max(lo, shown_from)
        shot = seq.shot_by_id(clip.data.get("shot_id")) if seq is not None else None
        head_growth = max(0.0, shot.start - (grow_lo + delta)) if shot else 0.0
        floors = (
            [lo] + [s.start for s in shots] + ([lowest] if lowest is not None else [])
        )
        # Whole frames: the content's net move is *delta* whatever the park,
        # and a VSE strip can only sit on a whole frame -- a fractional park
        # rounded twice could land it a frame off.
        park = float(math.floor((min(floors) - head_growth - 1000.0) - hi))
        move(lo, hi, park)
        try:
            self._expand_shot_for_clip(clip, grow_lo + delta, hi + delta)
        except Exception:
            move(lo + park, hi + park, -park)  # declined: back where it was
            raise
        move(lo + park, hi + park, delta - park)

    def _expand_shot_range(
        self, shot_id, new_start: float, new_end: float, curves=None
    ) -> None:
        """Grow *shot_id* so ``[new_start, new_end]`` fits inside it.

        *curves* are the curves the moved content rides on (the host's own
        handles): a landing on a contiguous seam steps the bound one frame
        past it only when one of them holds a key ON the seam -- the shared
        sample the landing would take (``ShotStore.enclosing_bounds``).
        ``None`` assumes one does.

        The single chokepoint for "content moved past the shot edge, so the
        shot follows it" -- shared by clip drags and per-key drags.  Without
        it a key dragged onto the next shot's first frame ends up owned by
        that shot while its siblings stay behind, which is what splits one
        dragged selection across two shots at zero gap.

        Call it BEFORE the moved content lands.  The ripple moves every
        envelope beyond the grown bound, so content that has already landed
        there is swept a second time, and a landing on the neighbour's keyed
        boundary stacks on the pose the ripple was about to carry away.

        Skipped when shift is held -- shift means "move freely across shot
        boundaries without changing them".
        """
        widget = self._get_sequencer_widget()
        if getattr(widget, "shift_held_at_press", False):
            self.logger.debug("[EXPAND] skipped -- shift held")
            return
        if self.sequencer is None:
            self.logger.debug("[EXPAND] skipped -- no sequencer")
            return
        if shot_id is None:
            self.logger.debug("[EXPAND] skipped -- no shot_id in clip data")
            return
        shot = self.sequencer.shot_by_id(shot_id)
        if shot is None:
            self.logger.debug(
                "[EXPAND] skipped -- shot_by_id(%s) returned None", shot_id
            )
            return
        prior_start = shot.start
        prior_end = shot.end
        # Outward to whole frames, so the shot ENCLOSES what moved (rounded to
        # the nearest frame, a key dragged to 50.4 past an end at 50 left the
        # key outside it), and one frame past a contiguous seam the landing
        # would sit on, so the touching neighbour keeps its opening pose.
        seam_keyed = None
        if curves:
            riding = list(curves)
            host = self.host

            def seam_keyed(frame: float) -> bool:
                return host.any_key_at(riding, frame)

        expanded_start, expanded_end = self.sequencer.store.enclosing_bounds(
            shot_id, new_start, new_end, seam_keyed
        )
        start_delta = expanded_start - prior_start
        end_delta = expanded_end - prior_end
        # One epsilon gate for the whole block: an exact != here with
        # epsilon-gated ripples below could update the shot yet skip
        # both ripples on sub-epsilon drift, desyncing neighbors.
        if abs(start_delta) > 1e-6 or abs(end_delta) > 1e-6:
            # Guard the store event so the mid-drag update_shot doesn't
            # trigger a full widget rebuild -- the caller syncs once at
            # the end of the move (same pattern as the gap handlers).
            was_syncing = self._syncing
            self._syncing = True
            try:
                # Ripple FIRST, from the bound the shot is about to have.
                # Writing the grown bound first made the store read the two
                # shots as contiguous for a moment when the key landed on the
                # neighbour's start, and the planner then "split" a shared
                # sample that never was one -- re-keying the neighbour's
                # opening pose at its new start (measured 2026-09-05: every
                # FAILED_CMPT_LOC curve gained a key).  From the NEW bound the
                # gap's content beyond it rides and what the shot grew over
                # stays; the planner never cuts into the neighbour, so a bound
                # on its keyed start (or inside it) moves it whole, boundary
                # pose included, and the dragged key lands on a free frame.
                # The room is the landing's: declared, the ripple's moment of
                # gap is no split, and no keyless seam is pinned in its way
                # (ShotSequencer.pending_bounds).
                with self.sequencer.pending_bounds(
                    {shot_id: (expanded_start, expanded_end)}
                ):
                    if abs(start_delta) > 1e-6:
                        self.sequencer.ripple_upstream(
                            shot_id, expanded_start, start_delta
                        )
                    if abs(end_delta) > 1e-6:
                        self.sequencer.ripple_downstream(
                            shot_id, expanded_end, end_delta
                        )
                self.sequencer.store.update_shot(
                    shot_id, start=expanded_start, end=expanded_end
                )
            finally:
                self._syncing = was_syncing
            # Downstream/upstream shots may have moved -- flush stale cache
            # so _sync_to_widget re-collects their segments.
            self._segment_cache.clear()
        self.logger.debug(
            "[EXPAND] shot=%s prior=(%s,%s) new_clip=(%s,%s) result=(%s,%s)",
            shot_id,
            prior_start,
            prior_end,
            new_start,
            new_end,
            shot.start,
            shot.end,
        )

    def _report_boundary_refusal(self, exc) -> None:
        """Surface a declined boundary edit instead of raising through a drag.

        Overrunning a shot's bound expands it and ripples the neighbour,
        which the planner can REFUSE (:class:`ShotBoundaryConflict`) when
        the ripple would force two shots' disagreeing poses onto one frame.
        A refusal is an answer, not a crash -- and this arrives on the end
        of a mouse drag, where a traceback is the worst possible reply.

        The restore point is deliberately KEPT: each ripple declines before
        it writes, and a clip makes its room before it lands, but
        :meth:`_expand_shot_range` ripples the head before the tail: a refused
        tail can follow a head that already moved the scene, and the user
        must still be able to undo it.
        """
        self.logger.warning(str(exc))
        self._set_footer(str(exc))

    def on_clip_moved(self, clip_id: int, new_start: float) -> None:
        """Handle clip move -- routes to audio or shot-level logic."""
        widget = self._get_sequencer_widget()
        clip = widget.get_clip(clip_id) if widget else None
        self.logger.debug(
            "[CLIP MOVED] clip_id=%s new_start=%s clip_data=%s",
            clip_id,
            new_start,
            dict(clip.data) if clip else None,
        )
        shot_id = clip.data.get("shot_id") if clip else None
        obj_name = clip.data.get("obj", "") if clip else ""
        if self.sequencer is None:
            return

        # Guarded commit (see _commit_clip_resizes); the rebuild runs after
        # the guard is released -- _rebuild_content resets _syncing in its
        # own finally, so a guard spanning it would be silently dropped.
        was_syncing = self._syncing
        self._syncing = True
        refused = None
        try:
            with self.sequencer.store.scene_edit("Move Clip") as edit:
                applied = self._apply_clip_move(clip_id, new_start)
                if not applied:
                    edit.cancel()
        except ShotBoundaryConflict as exc:
            applied, refused = True, exc  # a ripple may have run (see the report)
        finally:
            self._syncing = was_syncing
        if refused is not None:
            self._report_boundary_refusal(refused)
        if not applied:
            return
        self.logger.debug(
            "[CLIP MOVED] sync triggered -- cache_keys=%s shifted_out=%s",
            list(self._segment_cache.keys()),
            {k: sorted(v) for k, v in self._shifted_out_keys.items()},
        )
        self._sync_to_widget(shot_id=shot_id)
        self._sync_combobox()
        # A refusal already owns the footer; "Moved ..." would overwrite the
        # only notice the user gets, and claim a move that was declined.
        if obj_name and refused is None:
            self._set_footer(f"Moved {obj_name} → {new_start:.0f}")

    def on_clips_batch_moved(self, moves) -> None:
        """Handle a batch of clip moves (group drag), syncing once at the end.

        *moves* arrives in a collision-free ORDER (see uitk's
        ``ClipItem._collision_free_order``), not selection order, and it has to
        be applied in that order: each move addresses its clip's content by the
        range that clip used to occupy, so a landing that overruns a clip which
        has not moved yet would be grabbed twice and the group would deform.
        """
        shot_id = None
        widget = self._get_sequencer_widget() if moves else None
        if widget is not None:
            # Any member's shot will do -- this only picks which shot to
            # re-render -- but reading moves[0] tied that choice to the
            # batch's ORDER, which is now decided by direction of travel.
            for clip_id, _new_start in moves:
                clip = widget.get_clip(clip_id)
                if clip is not None and clip.data.get("shot_id") is not None:
                    shot_id = clip.data.get("shot_id")
                    break
        if self.sequencer is None:
            return
        was_syncing = self._syncing
        self._syncing = True  # see _commit_clip_resizes -- own edits must not
        needs_sync = False
        refused = None
        try:  # arm the debounce into a second rebuild
            with self.sequencer.store.scene_edit("Move Clips") as edit:
                for clip_id, new_start in moves:
                    if self._apply_clip_move(clip_id, new_start):
                        needs_sync = True
                if not needs_sync:
                    edit.cancel()
        except ShotBoundaryConflict as exc:
            # Whatever landed before the refusal stands and must be drawn.
            needs_sync, refused = True, exc
        finally:
            self._syncing = was_syncing
        if refused is not None:
            self._report_boundary_refusal(refused)
        if not needs_sync:
            return
        self._sync_to_widget(shot_id=shot_id)
        self._sync_combobox()
        if refused is None:  # see on_clip_moved -- a refusal keeps the footer
            self._set_footer(f"Moved {len(moves)} clip{'s' if len(moves) != 1 else ''}")

    # -- per-key handlers ---------------------------------------------------

    def _gesture_plan(self, widget, groups):
        """Resolve one key gesture into per-curve merged moves.

        Returns ``(curve_moves, shot_extents, labels, moved)``:

        * ``curve_moves`` -- ``{curve_id: {"curve": curve, "obj": obj,
          "plug": "obj.attr", "pairs": [(old, new, shot_id), ...]}}``, merged
          across clips and keyed by ``SequencerHost.curve_id`` (Maya's curve
          node name; Blender's fcurve data pointer -- bpy hands out a fresh
          wrapper per access, and linked duplicates' clips name one shared
          curve).  Two clips of the SAME ``obj.attr`` (split_static segments)
          share curves; committing them as separate groups lets one group's
          landed key be re-grabbed -- or overwritten -- by the next group's
          time window.  The graph editor's ``GraphSync`` builds the same shape.
        * ``shot_extents`` -- ``{shot_id: (lo, hi)}`` landing extents of the
          pairs that actually qualified (a key exists at ``old_t`` on the
          pristine curve), never from times the commit won't apply.
        * ``moved`` -- unique qualified key times across the gesture.

        All queries run against the PRISTINE curves -- nothing has been
        committed when this runs.
        """
        host = self.host
        curve_moves: dict = {}
        shot_extents: dict = {}
        labels: list = []
        moved = 0
        for clip_id, changes in groups:
            clip = widget.get_clip(clip_id)
            if clip is None:
                continue
            obj_name = clip.data.get("obj")
            attr_name = clip.data.get("attr_name")
            if not obj_name or not attr_name:
                continue
            curves = host.curves_for_attr(obj_name, attr_name)
            if not curves:
                continue
            sid = clip.data.get("shot_id")
            wanted = [(old, new) for old, new in changes if abs(new - old) >= 1e-6]
            clip_applied: dict = {}  # old_t -> new_t (unique per gesture step)
            for crv in curves:
                entry = curve_moves.setdefault(
                    host.curve_id(crv),
                    {
                        "curve": crv,
                        "obj": obj_name,
                        "plug": f"{obj_name}.{attr_name}",
                        "pairs": [],
                    },
                )
                known = entry["pairs"]
                present = host.keyed_at(
                    crv, [old for old, _new in wanted], KEY_MATCH_EPS
                )
                for (old_t, new_t), here in zip(wanted, present):
                    if not here:
                        continue
                    # Dedupe within the eps window -- times arrive from widget
                    # drag records and curve queries that agree only to
                    # rounding.
                    if any(abs(o - old_t) <= KEY_MATCH_EPS for o, _n, _s in known):
                        continue
                    known.append((old_t, new_t, sid))
                    clip_applied[round(old_t, 3)] = new_t
            if clip_applied:
                moved += len(clip_applied)
                labels.append(f"{obj_name}.{attr_name}")
                if sid is not None:
                    lo = min(clip_applied.values())
                    hi = max(clip_applied.values())
                    prev = shot_extents.get(sid)
                    shot_extents[sid] = (
                        (lo, hi)
                        if prev is None
                        else (min(prev[0], lo), max(prev[1], hi))
                    )
        curve_moves = {k: v for k, v in curve_moves.items() if v["pairs"]}
        return curve_moves, shot_extents, labels, moved

    def _expand_and_compensate(self, curve_moves, shot_extents) -> None:
        """Open the touched shots' boundaries, dragging pending landings along.

        Runs BEFORE the key commit: expansion ripples the NEXT shot's keys
        through its envelope, and a freshly-landed key at/past that
        envelope's start would be swept a second time.  Pre-commit, the
        dragged keys still sit at their old times inside the pivot shot --
        outside every rippled envelope (the pivot is excluded from the
        ripple plan) -- so the ripple cannot touch them.

        When one expansion ripples ANOTHER touched shot, that shot's
        pending (old, new) times and extents ride the ripple, exactly as
        its existing keys just did.  (Reachable only by a gesture spanning
        shots -- rare, since sub-rows are built for the active shot -- but a
        wrong answer here silently corrupts key times.)

        *curve_moves* is :meth:`_gesture_plan`'s shape (``GraphSync`` builds
        it too): each entry's ``"curve"`` is the host curve the seam test
        reads.
        """
        if self.sequencer is None:
            return
        sids = sorted(
            (sid for sid in shot_extents if self.sequencer.shot_by_id(sid)),
            key=lambda sid: self.sequencer.shot_by_id(sid).start,
        )
        for sid in sids:
            others = {
                o: self.sequencer.shot_by_id(o).start
                for o in sids
                if o != sid and self.sequencer.shot_by_id(o) is not None
            }
            lo, hi = shot_extents[sid]
            curves = [
                entry["curve"]
                for entry in curve_moves.values()
                if any(psid == sid for _old, _new, psid in entry["pairs"])
            ]
            self._expand_shot_range(sid, lo, hi, curves=curves)
            for o, pre_start in others.items():
                shot_o = self.sequencer.shot_by_id(o)
                if shot_o is None:
                    continue
                shift = shot_o.start - pre_start
                if abs(shift) < 1e-6:
                    continue
                olo, ohi = shot_extents[o]
                shot_extents[o] = (olo + shift, ohi + shift)
                for entry in curve_moves.values():
                    entry["pairs"] = [
                        (old + shift, new + shift, psid)
                        if psid == o
                        else (old, new, psid)
                        for old, new, psid in entry["pairs"]
                    ]

    def _commit_curve_moves(self, curve_moves, ledger=None) -> None:
        """Land every merged move, one primitive call per curve
        (``SequencerHost.commit_curve_moves``).

        A single shared delta travels as a real move (tangents intact);
        mixed deltas take the two-pass recreate.  Both primitives handle
        intra-call collisions -- which is exactly why the gesture is merged
        per curve first.

        *ledger* rides along so a gap hold or boundary sample the drag picks
        up moves with its key: a key dragged AWAY from a seam has to be
        findable at its new frame for the hold to be released there.
        """
        self.host.commit_curve_moves(curve_moves, ledger=ledger, eps=KEY_MATCH_EPS)

    def on_keys_moved(self, clip_id: int, changes: list) -> None:
        """Move individual keyframes on the curves, then refresh.

        Parameters:
            clip_id: The sequencer clip whose keys were dragged.
            changes: ``[(old_time, new_time), ...]`` for every key that moved.
        """
        self.on_keys_batch_moved([(clip_id, changes)])

    def on_keys_batch_moved(self, groups) -> None:
        """Commit one key drag that spanned any number of clips.

        *groups* is ``[(clip_id, [(old_time, new_time), ...]), ...]`` -- the
        whole gesture, resolved into per-curve merged moves first (see
        :meth:`_gesture_plan`) and committed inside ONE undo step so a drag
        across several attribute rows reverses in a single step.

        Boundary follow-up runs BEFORE the keys land (see
        :meth:`_expand_and_compensate`) and rides the same step, so undo
        reverses keys and bounds together.  An empty plan costs nothing:
        no snapshot, no undo step, no rebuild.
        """
        widget = self._get_sequencer_widget()
        if widget is None or not groups:
            return

        # The drag it started in stays the shot on screen -- expansion can
        # ripple neighbours, and picking the target from the touched set
        # would retarget the panel to whichever shot came first.
        origin = widget.get_clip(groups[0][0])
        origin_shot_id = origin.data.get("shot_id") if origin else None

        curve_moves, shot_extents, labels, moved = self._gesture_plan(widget, groups)
        if not curve_moves:
            return

        was_syncing = self._syncing
        self._syncing = True  # own key edits must not arm the keyframe
        try:  # debounce into a second full rebuild (issue-7 storm)
            # The restore point is pushed BEFORE any mutation -- one taken
            # after the boundary expansion records the post-edit bounds, so
            # undo would re-apply the very expansion it should reverse.
            with self._edit_bracket("Move Keys"):
                self._expand_and_compensate(curve_moves, shot_extents)
                seq = self.sequencer
                self._commit_curve_moves(
                    curve_moves, ledger=seq.ledger if seq is not None else None
                )
                # The drag may have grown a bound and it may have moved the
                # seam: the system's own samples follow, in the same step.
                if seq is not None:
                    seq.reconcile_system_edits()
        finally:
            self._syncing = was_syncing

        # A shot whose bounds moved rippled its neighbours; adjacent shots'
        # cached segments are stale either way once keys crossed an edge.
        if shot_extents:
            self._segment_cache.clear()
            self._sub_row_cache.clear()

        self._sync_to_widget(shot_id=origin_shot_id)
        self._sync_combobox()
        names = set(labels)
        where = names.pop() if len(names) == 1 else f"{len(names)} curves"
        self._set_footer(f"Moved {moved} key{'s' if moved != 1 else ''} on {where}")

    def on_keys_deleted(self, clip_id: int, times: list) -> None:
        """Delete individual keyframes from the curves, then refresh.

        The Delete key's own path is ``_delete_selected_clip_keys`` (batched
        over the whole key selection); this handler stays connected to the
        widget's ``keys_deleted`` signal for anything that emits it directly.

        Parameters:
            clip_id: The sequencer clip whose keys should be removed.
            times: Absolute times of the keys to delete.
        """
        widget = self._get_sequencer_widget()
        clip = widget.get_clip(clip_id) if widget else None
        if clip is None:
            return

        obj_name = clip.data.get("obj")
        attr_name = clip.data.get("attr_name")
        if not obj_name or not attr_name:
            return

        curves = self.host.curves_for_attr(obj_name, attr_name)
        if not curves:
            return

        deleted = False
        # Guarded like every other key edit here.  Maya's SYNCHRONOUS
        # anim-curve-edited callback fires inside each cut and banks the curve
        # as "freshly keyed" for _auto_add_keyed_objects, which a curve we
        # just CUT is not (the keyframe-edited one is idle-deferred, so this
        # does not stop the refresh debounce); Blender's depsgraph handler
        # reacts to the Action tag a removed point leaves.
        was_syncing = self._syncing
        self._syncing = True
        try:
            # The restore point is pushed BEFORE the edit: the reconcile below
            # releases the deleted keys' claims, so a point taken after it
            # handed undo a ledger without them.
            with self._edit_bracket("Delete Keys") as edit:
                # Every claim on a deleted key goes with it, a behavior's too
                # (the reconcile below reaches samples and holds only).
                release = (
                    self.sequencer.store.release_replaced([obj_name])
                    if self.sequencer is not None
                    else None
                )
                deleted = self.host.delete_keys_at(curves, times, release=release) > 0
                if not deleted:
                    edit.cancel()  # nothing happened -- no dead restore point
                elif self.sequencer is not None:
                    # A key edit like any other (``_key_scene_edit``): the claims
                    # on the deleted keys go with them and the gap holds re-settle.
                    self.sequencer.reconcile_system_edits()
        finally:
            self._syncing = was_syncing

        if not deleted:
            return

        shot_id = clip.data.get("shot_id")
        self._sync_to_widget(shot_id=shot_id)
        n = len(times)
        self._set_footer(
            f"Deleted {n} key{'s' if n != 1 else ''} on {obj_name}.{attr_name}"
        )
