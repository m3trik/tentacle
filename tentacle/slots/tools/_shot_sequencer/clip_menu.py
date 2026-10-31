# !/usr/bin/python
# coding=utf-8
"""Clip context menus and clip-level key operations.

Provides :class:`ClipMenuMixin` -- mixed into
:class:`~.controller.ShotSequencerController`. The clip and gap context menus,
Move / Copy to Shot, clip locking, and deleting, stashing and retrieving the
keys under clips.

The keys themselves are the host's: a clip names its object, its channels and
its span as plain values, and the host's ``SequencerHost`` cuts or stashes
them (``delete_span_keys``, ``delete_keys_at``, ``stash_keys``); stored clips
are listed and retrieved through the host's ``KeyStash``.
"""

from pythontk import ShotBoundaryConflict
from qtpy import QtWidgets


class ClipMenuMixin:
    """Clip and gap context menus, and the clip-level key operations they run."""

    # -- item menu extensibility hooks -------------------------------------

    def on_clip_menu(self, menu, clip_id: int) -> None:
        """Add domain-specific actions to a clip's context menu.

        Called before ``menu.exec_`` so consumers can append actions.

        When multiple clips are selected the actions operate on all of
        them.  The *clip_id* parameter identifies the right-clicked clip
        for actions that need a single target (e.g. "Lock Others").
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        clip = widget.get_clip(clip_id)
        if clip is None:
            return

        obj_name = clip.data.get("obj")

        # Gather all selected clip IDs for batch operations.
        selected_ids = widget.selected_clips() or [clip_id]
        if clip_id not in selected_ids:
            selected_ids = [clip_id]
        multi = len(selected_ids) > 1

        menu.addSeparator()
        # No Delete row: the Delete KEY runs _delete_selected_clip_keys over
        # this same selection (selected keyframes, or every key on the
        # selected clips), so a row here would duplicate a key every editor
        # already binds.
        #
        # Key stash: park the clips' keys out of the working animation (inert,
        # never exported, retrievable across sessions) — the non-destructive
        # sibling of deleting them — and bring stored clips back onto this lane.
        act_store = menu.addAction(
            f"Store Keys ({len(selected_ids)})" if multi else "Store Keys"
        )
        act_store.triggered.connect(lambda: self._stash_clip_keys(selected_ids))
        if obj_name:
            self._add_retrieve_menu(menu, obj_name)

        # Per-object lock helpers
        if obj_name and self.sequencer:
            menu.addSeparator()
            act_lock_others = menu.addAction("Lock Others")
            act_unlock_all = menu.addAction("Unlock All")
            act_lock_others.triggered.connect(
                lambda: self._lock_others(widget, obj_name)
            )
            act_unlock_all.triggered.connect(lambda: self._unlock_all(widget))

        # "Move to Shot" submenu — anim/audio clips moved as sequences.
        if self.sequencer:
            seqs = self._clips_to_sequences(
                widget, selected_ids, include_read_only=True
            )
            shots = self.sequencer.sorted_shots()
            if seqs and len(shots) > 1:
                menu.addSeparator()
                self._add_send_to_shot_menu(
                    menu, seqs, suffix=f" ({len(seqs)})" if multi else ""
                )

    def _clips_to_sequences(self, widget, clip_ids, include_read_only=False):
        """Convert widget clip ids to unified sequence dicts.

        A stepped (zero-duration) clip is ONE key and moves as one: it rides
        the key-level path (``"times"`` on the dict), the same one a key
        selection takes from the key context menu.  A single-attribute
        sub-row clip moves as THAT attribute's sequence (``"attr"``): the
        engine then relocates only its curves, where a whole-object move
        would take every attribute's keys in the span along with the one the
        user grabbed.

        Clips of a non-active visible shot are read-only for DRAGS (the drag
        path assumes the active shot) and are skipped unless
        *include_read_only*; Move to Shot passes it, because the engine
        resolves each sequence's source shot itself and "you cannot move a
        clip you can see" was the report ("move to shot sometimes fails").
        """
        seqs = []
        seen: set = set()
        for cid in clip_ids:
            clip = widget.get_clip(cid)
            if clip is None:
                continue
            if clip.data.get("read_only") and not include_read_only:
                continue
            start = clip.data.get("orig_start")
            end = clip.data.get("orig_end")
            if start is None or end is None:
                continue
            stepped = bool(clip.data.get("is_stepped"))
            if end <= start and not stepped:
                continue
            attr = None
            if clip.data.get("is_audio"):
                obj = clip.data.get("audio_track_id")
                kind = "audio"
            else:
                obj = clip.data.get("obj")
                kind = "anim"
                attr = clip.data.get("attr_name") or None
            if not obj:
                continue
            # Dedupe: the same underlying segment can produce multiple
            # clips when it spans multiple visible shots (esp. audio).
            key = (kind, obj, attr, round(start, 6), round(end, 6))
            if key in seen:
                continue
            seen.add(key)
            seq = {"kind": kind, "obj": obj, "start": start, "end": end}
            if attr:
                seq["attr"] = attr
            if stepped:
                seq["times"] = [float(start)]
                seq["end"] = start
            seqs.append(seq)
        return seqs

    def _add_send_to_shot_menu(
        self, menu, seqs: list, noun: str = "clip", suffix: str = ""
    ):
        """Add the Move / Copy to Shot submenu to *menu* and return it.

        ONE list of shots with a Copy toggle at its head, not a Move and a
        Copy submenu listing the same shots twice ("copy to shot alongside
        the existing move to shot.  Is there a way to make this less
        redundant?").  The toggle keeps the menu open and retitles the
        submenu with what a pick now does; it holds for the session, so a run
        of copies is one toggle.  *suffix* follows the title (a selection
        count).  The submenu is parented explicitly: PySide 6.11's
        ``addMenu(str)`` hands back a wrapper that goes stale once the
        building frame drops it.
        """
        sub = QtWidgets.QMenu(menu)
        menu.addMenu(sub)

        def retitle() -> None:
            verb = "Copy" if self._copy_to_shot else "Move"
            sub.setTitle(f"{verb} to Shot{suffix}")

        def set_copy(on: bool) -> None:
            self._copy_to_shot = bool(on)
            retitle()

        box = QtWidgets.QCheckBox("Copy  (keep the originals)")
        box.setChecked(self._copy_to_shot)
        box.setToolTip(
            "On: a pick copies the selection into that shot, leaving it where\n"
            "it is.  Off: a pick moves it.  Audio clips move only."
        )
        box.toggled.connect(set_copy)
        holder = QtWidgets.QWidget(sub)
        lay = QtWidgets.QHBoxLayout(holder)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.addWidget(box)
        row = QtWidgets.QWidgetAction(sub)
        row.setDefaultWidget(holder)
        sub.addAction(row)
        sub.addSeparator()
        retitle()
        self._populate_send_to_shot(sub, seqs, noun=noun)
        return sub

    #: The two moves an animator makes most: one shot along the sequence.
    _RELATIVE_MOVES = (("Next Shot", "merge_next"), ("Previous Shot", "merge_prev"))

    def _populate_send_to_shot(self, move_menu, seqs: list, noun: str = "clip"):
        """Fill a Move / Copy to Shot submenu: the neighbours first, then
        every shot.

        **Next Shot** and **Previous Shot** head the list so the common move --
        nudging a selection one shot along the sequence -- is always in the
        same place, whatever the shots are called.  They are relative to the
        shot the selection lives in (the active shot when it spans several),
        and each is listed only when that neighbour exists.  Below a
        separator comes every shot by name and range, minus the one the whole
        selection already occupies.  A pick moves or copies by the submenu's
        toggle as it stands when clicked (:attr:`_copy_to_shot`).

        Parameters:
            move_menu: The submenu to fill.
            seqs: Sequence dicts to send (clips or key selections).
            noun: What the footer counts afterwards -- ``"clip"`` or ``"key"``.
        """
        source_ids = {self.sequencer.source_shot_id(sq) for sq in seqs}
        single = next(iter(source_ids)) if len(source_ids) == 1 else None
        anchor = single if single is not None else self.active_shot_id
        near = (
            self._neighbour_shots(anchor)
            if anchor is not None
            else {"merge_prev": None, "merge_next": None}
        )
        entries = [
            (f"{label}  ({near[key].name})", near[key].shot_id)
            for label, key in self._RELATIVE_MOVES
            if near[key] is not None
        ]
        if entries:
            entries.append(None)  # separator
        entries += [
            (f"{sh.name}  [{sh.start:.0f}–{sh.end:.0f}]", sh.shot_id)
            for sh in self.sequencer.sorted_shots()
            if single is None or sh.shot_id != single
        ]
        for entry in entries:
            if entry is None:
                move_menu.addSeparator()
                continue
            label, shot_id = entry
            act = move_menu.addAction(label)
            act.triggered.connect(
                lambda _checked=False, sid=shot_id: self._send_to_shot(
                    seqs, sid, noun=noun, copy=self._copy_to_shot
                )
            )

    def _send_to_shot(
        self, sequences, dest_shot_id, noun: str = "clip", copy: bool = False
    ):
        """Move -- or *copy* -- *sequences* into *dest_shot_id* as one undo
        step (``move_sequences_to_shot`` / ``copy_sequences_to_shot``), then
        refresh.

        Reports the outcome in the footer.  Nothing happens when every
        selected sequence already lives in the destination, and the footer
        says so -- that used to look like the command silently failing; a
        copy of audio alone says audio is not copied.  *noun* is what the
        footer counts: a clip menu sends clips, a key menu sends keys.
        """
        title = "Copy to Shot" if copy else "Move to Shot"
        if copy and sequences:
            sequences = [sq for sq in sequences if sq["kind"] == "anim"]
            if not sequences:
                self._set_footer(
                    f"{title}: audio clips are not copied.", color="#E0A0A0"
                )
                return
        if self.sequencer is None or not sequences:
            self._set_footer(
                f"{title}: nothing to send in the selection.", color="#E0A0A0"
            )
            return
        dest = self.sequencer.shot_by_id(dest_shot_id)
        movable = [
            sq
            for sq in sequences
            if self.sequencer.source_shot_id(sq) != dest_shot_id
        ]
        if not movable:
            self._set_footer(
                f"{title}: selection is already in "
                f"{dest.name if dest else 'that shot'}.",
                color="#E0A0A0",
            )
            return

        send = (
            self.sequencer.copy_sequences_to_shot
            if copy
            else self.sequencer.move_sequences_to_shot
        )
        try:
            with self.sequencer.store.scene_edit(title):
                send(movable, dest_shot_id)
        except ShotBoundaryConflict as exc:
            # A refusal is an answer, not a crash (the shot lane reports its
            # own the same way).  The restore point stays: room may have been
            # opened before a ripple was declined, and Ctrl+Z takes it back.
            self.logger.warning(str(exc))
            self._after_shot_change()  # the redraw sets a footer of its own
            self._set_footer(f"{title}: {exc}", color="#E0A0A0")
            return
        self._after_shot_change()
        n = (
            sum(len(sq.get("times") or ()) for sq in movable)
            if noun == "key"
            else len(movable)
        )
        self._set_footer(
            f"{'Copied' if copy else 'Moved'} {n} {noun}{'s' if n != 1 else ''} to "
            f"{dest.name if dest else dest_shot_id}"
        )

    # -- lock helpers -------------------------------------------------------

    def _lock_others(self, widget, keep_obj: str) -> None:
        """Lock every main-row object clip except *keep_obj*."""
        store = self.sequencer.store if self.sequencer else None
        if store is None:
            return
        # Every unique main-row object name in the view (sub-rows and
        # other shots' read-only clips are not lockable rows).
        obj_names = {
            cd.data.get("obj")
            for cd in widget.clips()
            if cd.data.get("obj")
            and not getattr(cd, "sub_row", False)
            and not cd.data.get("read_only")
        }
        for o in obj_names:
            if o == keep_obj:
                store.locked_objects.discard(o)
            else:
                store.locked_objects.add(o)
        # Apply to all clips
        for cd in widget.clips():
            o = cd.data.get("obj")
            if o and not cd.data.get("read_only"):
                widget.set_clip_locked(cd.clip_id, o != keep_obj)
        self._sub_row_cache.clear()

    def _unlock_all(self, widget) -> None:
        """Unlock every clip in the current view."""
        store = self.sequencer.store if self.sequencer else None
        if store is not None:
            store.locked_objects.clear()
        for cd in widget.clips():
            if cd.locked and not cd.data.get("read_only"):
                widget.set_clip_locked(cd.clip_id, False)
        self._sub_row_cache.clear()

    def on_gap_menu(self, menu, gap_start: float, gap_end: float) -> None:
        """Add domain-specific actions to a gap overlay's context menu.

        Called before ``menu.exec_`` so consumers can append actions; the
        panel adds none of its own.
        """

    # -- the keys under clips --------------------------------------------------

    @staticmethod
    def _clip_channels(clip) -> list:
        """The channels *clip* stands for: its ``attributes``, or a sub-row
        clip's one ``attr_name``.  Empty for a clip naming no channel (a
        stepped point clip), which the host reads as the object's content
        curves (``SequencerHost.delete_span_keys`` / ``stash_keys``)."""
        attrs = list(clip.data.get("attributes") or [])
        if not attrs and clip.data.get("attr_name"):
            attrs = [clip.data["attr_name"]]
        return attrs

    def _clip_scopes(self, widget, clip_ids: list) -> list:
        """``(obj, channels, start, end, shot_id)`` per editable clip of
        *clip_ids*: what a clip-level key operation acts on.

        A clip missing, read-only (another visible shot's), naming no object
        or no span is left out -- logged, since the user asked for it.
        """
        scopes = []
        for cid in clip_ids:
            clip = widget.get_clip(cid)
            if clip is None:
                self.logger.debug("clip %s not found.", cid)
                continue
            if clip.data.get("read_only"):
                self.logger.debug("clip %s is read-only.", cid)
                continue
            obj = clip.data.get("obj")
            if not obj:
                self.logger.debug("clip %s has no obj.", cid)
                continue
            start, end = clip.data.get("orig_start"), clip.data.get("orig_end")
            if start is None or end is None:
                self.logger.debug("clip %s missing orig_start/end.", cid)
                continue
            shot_id = clip.data.get("shot_id")
            scopes.append(
                (
                    obj,
                    self._clip_channels(clip),
                    start,
                    end,
                    None if shot_id == -1 else shot_id,
                )
            )
        return scopes

    def _delete_clip_keys(self, clip_ids: list) -> None:
        """Delete the given clips' keys within their span, and refresh.

        A clip is scoped to its own channels (a sub-row clip: its one
        attribute) over its original span -- never every curve on the object:
        custom-property, constraint and modifier curves are no part of a
        transform clip and must survive a Delete.  One undo step for every
        clip; the claims the shot system held on the deleted keys go with
        them.
        """
        widget = self._get_sequencer_widget()
        if widget is None or self.sequencer is None:
            self.logger.debug("_delete_clip_keys: no widget, skipping.")
            return
        scopes = self._clip_scopes(widget, clip_ids)
        if not scopes:
            return

        deleted = 0
        # ``_syncing`` up while the host cuts, like every other edit path
        # here: a cut fires the host's keyed-curve watchers (Maya's
        # SYNCHRONOUS anim-curve-edited callback; Blender's depsgraph
        # handler), and an unguarded one banks the curve as "freshly keyed"
        # for ``_auto_add_keyed_objects``, which a curve we just CUT is not.
        # (It does not stop the refresh debounce: Maya's keyframe-edited
        # callback is idle-deferred, measured 2026-09-11.)
        was_syncing = self._syncing
        self._syncing = True
        try:
            store = self.sequencer.store
            with store.scene_edit("Delete Keys") as edit:
                # Every claim on a deleted key goes with it -- a behavior's
                # authored one too, which the reconcile below (samples and
                # holds) never reaches.  One hook for every clip's object.
                release = store.release_replaced([s[0] for s in scopes])
                for obj, attrs, start, end, _sid in scopes:
                    deleted += self.host.delete_span_keys(
                        obj, attrs, start, end, release=release
                    )
                if deleted:
                    # A key edit like any other (``_key_scene_edit``): the claims
                    # on the deleted keys go with them and the gap holds re-settle.
                    self.sequencer.reconcile_system_edits()
                else:
                    # Nothing happened (every cut refused, or no key in span):
                    # no dead restore point, and the redo branch kept.
                    edit.cancel()
        finally:
            self._syncing = was_syncing

        if not deleted:
            return
        self._segment_cache.clear()
        self._sub_row_cache.clear()
        self._sync_to_widget()
        self._set_footer(f"Deleted {deleted} key{'s' if deleted != 1 else ''}")

    def _stash_clip_keys(self, clip_ids: list) -> None:
        """Move the given clips' keys into the key stash.

        Same scoping as :meth:`_delete_clip_keys` — the clip's object, its
        channels (a sub-row clip is one attribute) and its original span —
        but the keys are parked, not destroyed: the shot block stays as it is
        and the clip records the shot it came from.
        """
        widget = self._get_sequencer_widget()
        if widget is None or self.sequencer is None:
            return
        self._run_stash(self._clip_scopes(widget, clip_ids))

    def _run_stash(self, jobs: list) -> None:
        """Park ``(obj, attrs, start, end, shot_id)`` *jobs* in the key stash.

        The half of "Store Keys" that does not depend on where the gesture
        came from, so a clip selection and a key selection reach the stash
        through the same call rather than two copies of this loop.  *obj* is
        the object's name as the panel shows it and *attrs* its channels
        (empty: the object's content curves); the host resolves both
        (``SequencerHost.stash_keys``).

        ONE clip, however many objects, channels and spans the gesture
        covered.  A stash is the thing the animator put away, and a
        three-channel selection stored as three clips left three rows to
        find, and to retrieve one at a time.  The stash takes the whole scope
        list, so the merge happens where the clip is built instead of by
        stitching clips back together afterwards.

        The shot is recorded only when every job came from the same one:
        a clip that spans two shots belongs to neither.
        """
        if not jobs or self.sequencer is None:
            return
        shots = {sid for *_scope, sid in jobs if sid is not None}
        with self.sequencer.store.scene_edit("Store Keys") as edit:
            try:
                clip_rec = self.host.stash_keys(
                    [(obj, attrs, start, end) for obj, attrs, start, end, _sid in jobs],
                    source_shot_id=shots.pop() if len(shots) == 1 else None,
                )
            except Exception:
                # One call for the whole gesture, so a raise means nothing
                # landed: no step, and no restore point "restoring" the state
                # we are in.
                edit.cancel()
                raise
            stored = clip_rec.key_count if clip_rec is not None else 0
            if not stored:
                edit.cancel()  # nothing happened -- keep the ledger clean
        if not stored:
            self._set_footer("No keys to store")
            return
        self._segment_cache.clear()
        self._sub_row_cache.clear()
        self._sync_to_widget()
        self._set_footer(
            f"Stored {stored} key{'s' if stored != 1 else ''} in the key stash"
        )

    def _add_retrieve_menu(self, menu, obj_name: str) -> None:
        """Append a "Retrieve Stored Keys" submenu listing *obj_name*'s clips."""
        clips = self.tk.KeyStash.active().clips_for_object(
            self.host.full_name(obj_name)
        )
        if not clips:
            return
        # Parented explicitly (see _add_send_to_shot_menu).
        sub = QtWidgets.QMenu("Retrieve Stored Keys", menu)
        menu.addMenu(sub)
        for clip in clips:
            act = sub.addAction(clip.label)
            act.triggered.connect(
                lambda _checked=False, cid=clip.clip_id: self._retrieve_stashed_clip(
                    cid
                )
            )
        # The rows above put a clip straight back on its own frames.  The
        # panel is for everything that needs more than that -- retrieve at a
        # different time, preview before committing, drop a clip -- so it
        # hangs here, under the object that HAS stored keys, rather than
        # adding a second row to the menu root.
        sub.addSeparator()
        sub.addAction("Restore Keys…").triggered.connect(self._open_key_stash)

    def _open_key_stash(self) -> None:
        """Open the Key Stash panel."""
        self.sb.handlers.marking_menu.show("key_stash")

    def _retrieve_stashed_clip(self, clip_id: int) -> None:
        """Put a stored clip back on its original frames (``KeyStash.retrieve``)."""
        if self.sequencer is None:
            return
        with self.sequencer.store.scene_edit("Retrieve Stored Keys") as edit:
            restored = self.tk.KeyStash.active().retrieve(clip_id)
            if not restored:
                edit.cancel()  # no dead restore point
        if not restored:
            self._set_footer("Nothing retrieved — the reason is in the log")
            return
        self._segment_cache.clear()
        self._sub_row_cache.clear()
        self._sync_to_widget()
        self._set_footer(f"Retrieved {restored} key{'s' if restored != 1 else ''}")

    def _delete_selected_clip_keys(self) -> None:
        """Delete selected keyframes or, if none, all keys on selected clips.

        Individual keyframes are batched into a single undo step so that
        Ctrl+Z restores all deleted keys at once.
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            self.logger.debug("_delete_selected_clip_keys: no widget.")
            return

        # The widget's key selection, grouped by clip (``selected_keys``).
        by_clip = {g["clip_id"]: list(g["times"]) for g in widget.selected_keys()}

        if by_clip:
            deleted = 0
            # The restore point is pushed BEFORE the edit (``scene_edit``): its
            # reconcile releases the deleted keys' claims, so a point taken
            # after it handed undo a ledger without them.  ``_syncing`` is up
            # while the host cuts, as in _delete_clip_keys.
            was_syncing = self._syncing
            self._syncing = True
            try:
                store = self.sequencer.store
                with store.scene_edit("Delete Keys") as edit:
                    # Every claim on a deleted key goes with it, a behavior's
                    # too (the reconcile below reaches samples and holds only).
                    # One hook for every clip's object.
                    clips = {cid: widget.get_clip(cid) for cid in by_clip}
                    release = store.release_replaced(
                        [c.data.get("obj") for c in clips.values() if c is not None]
                    )
                    for clip_id, times in by_clip.items():
                        clip = clips[clip_id]
                        if clip is None:
                            continue
                        obj_name = clip.data.get("obj")
                        attr_name = clip.data.get("attr_name")
                        if not obj_name or not attr_name:
                            continue
                        # A time counts only when a key there was cut: an
                        # all-failed pass must not report "Deleted N keys" and
                        # resync for nothing.
                        deleted += self.host.delete_keys_at(
                            self.host.curves_for_attr(obj_name, attr_name),
                            times,
                            release=release,
                        )
                    if deleted:
                        # A key edit like any other (``_key_scene_edit``): the
                        # claims on the deleted keys go with them and the gap
                        # holds re-settle.
                        self.sequencer.reconcile_system_edits()
                    else:
                        edit.cancel()  # nothing happened -- no dead point
            finally:
                self._syncing = was_syncing

            if not deleted:
                return
            shot_id = self.active_shot_id
            self._segment_cache.clear()
            self._sub_row_cache.clear()
            self._sync_to_widget(shot_id=shot_id)
            self._set_footer(f"Deleted {deleted} key{'s' if deleted != 1 else ''}")
            return

        # Fallback: delete entire clips when no individual keys are selected.
        clip_ids = widget.selected_clips() or []
        self.logger.debug("_delete_selected_clip_keys: selected_clips=%s", clip_ids)
        if clip_ids:
            self._delete_clip_keys(clip_ids)
            return

        # Nothing at all is selected inside the tracks, so Delete is about the
        # SHOT -- the only other thing the panel has selected.  It confirms
        # first, so the key cannot quietly take a shot and its animation.
        selected = self._shot_layer(widget).selected_shot()
        if selected is not None and selected.get("id") is not None:
            self.delete_shot(selected["id"])
