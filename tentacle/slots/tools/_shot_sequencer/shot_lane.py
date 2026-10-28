# !/usr/bin/python
# coding=utf-8
"""The shot lane: its context menu and the shot structure edits.

Provides :class:`ShotLaneMixin` -- mixed into
:class:`~.controller.ShotSequencerController`. Inserting, deleting, moving,
merging, splitting, padding and trimming shots, growing a shot over new keys,
and the timeline / shot-lane context menus that offer them.

Every edit is the host's ``ShotSequencer`` (``self.tk.ShotSequencer``) inside
its store's ``scene_edit`` -- one undo step per edit, in either host -- so
nothing here names the host.
"""

import pythontk as ptk
from pythontk import ShotBoundaryConflict
from qtpy import QtWidgets


class ShotLaneMixin:
    """The shot lane's menus and the shot structure edits they run."""

    # -- zone context menus ------------------------------------------------

    def on_zone_context_menu(self, zone: str, time: float, global_pos) -> None:
        """Build a context menu specific to the clicked zone.

        ``"shot_lane"`` is every click on the shot lane itself, plus every
        click over the TRACKS at a time some shot covers -- the widget
        resolves both.  Everywhere else (the ruler, and tracks clear of every
        shot) is the timeline, which has its own menu: the two were merged
        before, which buried a display toggle inside a menu about one shot
        and left the ruler with no menu of its own at all.
        """
        if zone == "shot_lane":
            self._show_shot_lane_context_menu(time, global_pos)
            return
        menu = self._build_timeline_context_menu(time)
        if menu is not None:
            menu.exec_(global_pos)

    def _show_shot_lane_context_menu(self, time: float, global_pos) -> None:
        """Context menu for the shots track: selection, editing, creation."""
        menu = self._build_shot_lane_context_menu(time)
        if menu is not None:
            menu.exec_(global_pos)

    def _build_timeline_context_menu(self, time: float):
        """The timeline's own menu at *time*, built but not shown.

        The widget's marker and display entries
        (:meth:`~uitk.widgets.sequencer.TimelineView.default_context_entries`),
        opened by a right-click on the ruler or on the tracks clear of every
        shot.  Returned unshown so a test can read its rows; ``None`` without
        a widget.
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            return None
        menu = self.sb.ContextMenu(parent=widget)
        menu.add_entries(widget.context_entries(time))
        return menu

    def _build_shot_lane_context_menu(self, time: float):
        """The shot lane's menu at *time*, built but not shown.

        A compact root -- one row per verb -- whose rows fan out on hover
        into their finer forms (:class:`uitk.ContextMenu`): New Shot into
        Insert Before / After, Split Here into Split at Current Time, Trim
        Empty Space into Leading / Trailing.  A row that is both an action
        and a category runs its own action when clicked (Trim Empty Space
        trims both ends).

        Everything here acts on THIS shot.  The timeline's own display
        actions have their own menu on the ruler
        (:meth:`_build_timeline_context_menu`), and key editing belongs to a
        key SELECTION rather than to a whole shot (:meth:`on_key_menu`) --
        both used to hang off this menu, which made a compact root the one
        thing it was not.  Extending a shot over new keys is no row here
        either: it is the header menu's one global Extend to Keys option.
        Returned unshown so a test can read its rows; ``None`` without a
        widget or a sequencer.
        """
        widget = self._get_sequencer_widget()
        if widget is None or self.sequencer is None:
            return None
        shot = self._find_shot_at_time(time)
        menu = self.sb.ContextMenu(parent=widget)
        sid = shot.shot_id if shot is not None else None
        neighbours = self._neighbour_shots(sid) if shot is not None else {}

        if shot is not None:
            menu.add(
                f'Edit "{shot.name}"…',
                callback=lambda: self._edit_shot_dialog(shot),
            )
            menu.add_separator()

        new = menu.add("New Shot", callback=self._create_shot_one_click)
        if shot is not None:
            menu.add(
                "Insert Shot Before",
                parent=new,
                callback=lambda: self._insert_shot(sid, before=True),
            )
            menu.add(
                "Insert Shot After",
                parent=new,
                callback=lambda: self._insert_shot(sid, before=False),
            )
            # A split needs room on both sides; on a bound it divides nothing.
            # Two places to cut: where the menu was opened (the row itself)
            # and where the playhead stands -- the playhead is where the
            # animator decided the cut belongs, and it is rarely the pixel
            # they right-clicked.
            now = self._current_time()
            split = menu.add(
                f"Split Here ({time:.0f})",
                callback=lambda: self.split_shot_at(sid, time),
                setEnabled=bool(shot.start + 1e-6 < time < shot.end - 1e-6),
            )
            menu.add(
                "Split at Current Time" + ("" if now is None else f" ({now:.0f})"),
                parent=split,
                callback=lambda t=now: self.split_shot_at(sid, t),
                setEnabled=bool(
                    now is not None and shot.start + 1e-6 < now < shot.end - 1e-6
                ),
            )
            merge = menu.add("Merge")
            for key, label in (
                ("merge_prev", "Merge with Previous"),
                ("merge_next", "Merge with Next"),
            ):
                other = neighbours[key]  # resolved once, when the menu is built
                menu.add(
                    label,
                    parent=merge,
                    callback=lambda o=other: self.merge_shot_with(sid, o.shot_id),
                    setEnabled=other is not None,
                )
            # Re-slot this shot among the others: picking a shot lands this
            # one immediately BEFORE it and pushes it, and everything after
            # it, downstream.
            #
            # ``move_shot_to_position`` takes the index in the FINAL order,
            # which is not the index the user just read off this list.
            # Moving downstream lifts this shot out first, sliding the picked
            # shot one slot up, so passing its current position landed this
            # shot one PAST it -- correct upstream, off by one downstream.
            ordered = self.sequencer.sorted_shots()
            here = next(
                (i for i, s in enumerate(ordered, start=1) if s.shot_id == sid), None
            )
            if len(ordered) > 1 and here is not None:
                move = menu.add("Move To")
                for pos, other in enumerate(ordered, start=1):
                    slot = pos - 1 if pos > here else pos
                    menu.add(
                        f"{pos}. {other.name}",
                        parent=move,
                        callback=lambda p=slot: self.move_shot_to_position(sid, p),
                        # Its own row, and the neighbour it already sits in
                        # front of, both mean "stay where you are".
                        setEnabled=other.shot_id != sid and slot != here,
                    )
            menu.add_separator()
            # Both prompt for the amount (the ellipsis says so) rather than
            # spending a fixed step: how much room a shot needs is the whole
            # question, and a fixed step meant re-opening the menu to get it.
            pad = menu.add("Add Frames")
            for edge, label in (
                ("leading", "Add Leading Frames…"),
                ("trailing", "Add Trailing Frames…"),
            ):
                menu.add(
                    label,
                    parent=pad,
                    callback=lambda e=edge: self._prompt_shot_space(shot, edge=e),
                )
            trim = menu.add("Trim Empty Space", callback=lambda: self._trim_shot(sid))
            for edge, label in (
                ("leading", "Trim Leading Space"),
                ("trailing", "Trim Trailing Space"),
            ):
                menu.add(
                    label,
                    parent=trim,
                    callback=lambda e=edge: self._trim_shot(sid, edge=e),
                )
            # Last, on its own: the one row that takes keys with it.  The same
            # delete as the dropdown's and the Shots window's (it asks first).
            menu.add_separator()
            menu.add(
                f'Delete "{shot.name}"…',
                callback=lambda: self.delete_shot(sid),
            )
        return menu

    # -- padding -------------------------------------------------------------

    def _prompt_shot_space(self, shot, edge: str) -> None:
        """Ask how many frames to pad *shot* at *edge*, then pad it.

        The amount is the whole question a padding gesture asks, so it is
        typed rather than assumed: the field opens on the last answer (the
        class default on the first use) and a run of shots padded by the same
        beat costs one keystroke each.  A negative amount removes room —
        :meth:`ShotSequencer.add_shot_space` clamps it to what is actually
        empty — so the validator gates on "a number that is not zero", not on
        sign.
        """

        def _parse(text):
            try:
                return float(str(text).strip())
            except (TypeError, ValueError):
                return None

        answer = self.sb.input_dialog(
            title=f"Add {edge.capitalize()} Frames",
            label=f'Frames of {edge} space for "{shot.name}":',
            text=f"{self._context_space_frames:g}",
            parent=self._get_sequencer_widget() or self.ui,
            validate=lambda t: (_parse(t) or 0.0) != 0.0,
            error_text="Enter a non-zero number of frames.",
        )
        frames = _parse(answer)
        if not frames:
            return  # cancelled, or an amount that would move nothing
        self._context_space_frames = frames
        self._add_shot_space(shot.shot_id, frames, edge=edge)

    def _add_shot_space(self, shot_id: int, frames: float, edge: str) -> None:
        """Pad *shot_id* by *frames* at *edge*, as one undoable step.

        The context-menu twin of the Shots panel's Add Space field, routed
        through the same engine call so both mean exactly the same thing.
        """
        if self.sequencer is None:
            return
        try:
            with self.sequencer.store.scene_edit("Add Space") as edit:
                head, tail = self.sequencer.add_shot_space(shot_id, frames, edge=edge)
                if abs(head) < 1e-6 and abs(tail) < 1e-6:
                    # Nothing moved: a restore point would make the next undo
                    # visibly do nothing.
                    edit.cancel()
        except ShotBoundaryConflict as exc:
            # Two shots would have had to share a sample whose poses
            # disagree.  A refusal is an answer, not a crash: report it
            # instead of handing the user a traceback for a menu click.
            # The restore point is the store's to keep or drop
            # (``scene_edit``): refused before anything was written, the edit
            # leaves none; a "both" pad slides the head BEFORE the tail ripple
            # can be declined, and that write keeps its point for Ctrl+Z.
            self.logger.warning(str(exc))
            self._set_footer(str(exc))
            return
        if abs(head) < 1e-6 and abs(tail) < 1e-6:
            self._set_footer(f"Add {edge} space: nothing to do")
            return
        # The padded shot, which in the adjacent / all views need not have
        # been the active one; it is now (``_after_shot_change``).
        self._after_shot_change(shot_id)
        self._set_footer(f"Added {tail - head:.0f}f of {edge} space")

    def _neighbour_shots(self, shot_id: int) -> dict:
        """``{"merge_prev": shot|None, "merge_next": shot|None}`` around *shot_id*."""
        shots = self.sequencer.sorted_shots() if self.sequencer else []
        idx = next((i for i, s in enumerate(shots) if s.shot_id == shot_id), None)
        if idx is None:
            return {"merge_prev": None, "merge_next": None}
        return {
            "merge_prev": shots[idx - 1] if idx > 0 else None,
            "merge_next": shots[idx + 1] if idx + 1 < len(shots) else None,
        }

    def _after_shot_change(self, shot_id=None) -> None:
        """Rebuild everything a shot edit, an undo or a redo invalidates.

        The ONE refresh every such path ends with: the cached segments (keys
        and audio both move with shots), the dropdown (it lists the shots and
        follows the store's active one), the timeline, and the host's
        playback range (the view mirror of the active shot).  Each path used
        to run its own subset, and the panel's undo ran neither the dropdown
        nor the range -- an undone new shot stayed listed and highlighted.
        The dropdown goes first: the rebuild resolves the active shot through
        it.  A *shot_id* -- the shot the edit acted on -- becomes the active
        shot.
        """
        if shot_id is not None and self.sequencer is not None:
            if self.sequencer.shot_by_id(shot_id) is not None:
                # The shot an edit acted on is the one drawn -- and so the
                # active one, or the timeline shows it while the dropdown and
                # the playback range stay on another (a shot-lane edit on a
                # neighbour's band).  Our own rebuild follows: no store-event
                # rebuild on top of it.
                was_syncing = self._syncing
                self._syncing = True
                try:
                    self.sequencer.store.set_active_shot(shot_id)
                finally:
                    self._syncing = was_syncing
        self._drop_caches()
        self._sync_combobox()
        self._sync_to_widget(shot_id=shot_id)
        self._apply_view_playback_range()

    # -- shot structure edits ----------------------------------------------

    def delete_shot(self, shot_id: int) -> None:
        """Delete *shot_id* with its contents, closing the timeline behind it.

        This is what "delete a shot" means from the timeline: the shot, the
        animation it owns, and the space it occupied all go, and the next shot
        lands where this one started.  The confirmation says so, because the
        keys are the animator's and a menu click should not eat them silently.
        """
        if self.sequencer is None:
            return
        shot = self.sequencer.shot_by_id(shot_id)
        if shot is None:
            return
        reply = QtWidgets.QMessageBox.question(
            self._get_sequencer_widget() or self.ui,
            "Delete Shot",
            f'Delete "{shot.name}" [{shot.start:.0f}–{shot.end:.0f}]\n'
            "— its keyframes, closing the gap behind it?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        with self.sequencer.store.scene_edit("Delete Shot"):
            result = self.sequencer.delete_shot(shot_id)
        self._after_shot_change()
        cut = result.get("curves_cut", 0)
        closed = result.get("closed", 0.0)
        parts = [f"Deleted {result.get('name', shot.name)}"]
        if cut:
            parts.append(f"{cut} curve(s) cleared")
        if closed:
            parts.append(f"closed {closed:.0f}f")
        self._set_footer(" · ".join(parts))

    def delete_shots(self, scope: str = "stale") -> None:
        """Delete the shots of *scope*, after naming them.

        ``"stale"``, ``"empty"`` or ``"all"`` (``ShotStore.shots_in_scope``) --
        the scopes of the Shots window's Delete Shots, asked the same question
        (``ShotReport.removal_question``).  Records only: no key is touched
        and no shot moves, where :meth:`delete_shot` cuts a shot's keys and
        closes the gap behind it, which would retime every shot after it.  One
        undo.
        """
        if self.sequencer is None:
            return
        store = self.sequencer.store
        kind = "" if scope == "all" else f"{scope} "
        doomed = store.shots_in_scope(scope)
        if not doomed:
            self._set_footer(f"No {kind}shots")
            return
        title, text = ptk.ShotReport.removal_question(doomed, scope)
        reply = QtWidgets.QMessageBox.question(
            self._get_sequencer_widget() or self.ui,
            title,
            text,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        with store.scene_edit(f"Delete {ptk.ShotReport.scope_label(scope)} Shots"):
            removed = store.remove_shots_in_scope(scope)
        self._after_shot_change()
        self._set_footer(f"Deleted {len(removed)} {kind}shot(s)")

    def move_shot_to_position(self, shot_id: int, position: int) -> None:
        """Re-slot *shot_id* at 1-based *position*, pushing the rest along.

        The shot that held the slot -- and every shot after it -- moves
        downstream to make room, so a reorder never writes over a shot or
        drops its keys.  ``ShotSequencer.move_shot_to_position`` resolves the
        whole new order before touching a keyframe, which is why this cannot
        leave two shots transiently claiming one span.
        """
        if self.sequencer is None:
            return
        with self.sequencer.store.scene_edit("Reorder Shot"):
            self.sequencer.move_shot_to_position(shot_id, position)
        self._after_shot_change(shot_id=shot_id)
        shot = self.sequencer.shot_by_id(shot_id)
        if shot is not None:
            self._set_footer(
                f"Moved {shot.name} to {position} · {shot.start:.0f}–{shot.end:.0f}"
            )

    def merge_shot_with(self, shot_id: int, other_id: int) -> None:
        """Fuse two neighbouring shots into one spanning both."""
        if self.sequencer is None:
            return
        with self.sequencer.store.scene_edit("Merge Shots"):
            merged = self.sequencer.merge_shots([shot_id, other_id])
        self._after_shot_change(shot_id=merged.shot_id)  # it becomes active
        self._set_footer(
            f"Merged into {merged.name} · {merged.start:.0f}–{merged.end:.0f}"
        )

    def split_shot_at(self, shot_id: int, time: float) -> None:
        """Cut *shot_id* in two at *time*, leaving its content where it is."""
        if self.sequencer is None:
            return
        try:
            with self.sequencer.store.scene_edit("Split Shot") as edit:
                try:
                    tail = self.sequencer.split_shot(shot_id, time)
                except ValueError:
                    # Refused before anything is cut (``split_shot``): no step
                    # and no restore point.
                    edit.cancel()
                    raise
        except ValueError as exc:
            self._set_footer(str(exc))
            return
        self._after_shot_change(shot_id=tail.shot_id)  # it becomes active
        self._set_footer(
            f"Split at {time:.0f} · {tail.name} {tail.start:.0f}–{tail.end:.0f}"
        )

    def _trim_shot(self, shot_id: int, edge: str = "both") -> None:
        """Trim empty space from *shot_id*, undoable, then refresh the widget.

        *edge* selects which end gives way: ``"both"`` (the default),
        ``"leading"`` (head only) or ``"trailing"`` (tail only).  Trimming
        one end is the common case when hand-tuning a cut — the other end
        is usually already where the animator wants it.
        """
        if self.sequencer is None:
            return
        with self.sequencer.store.scene_edit("Trim Shot") as edit:
            head, tail = self.sequencer.trim_shot_to_content(shot_id, edge=edge)
            if abs(head) < 1e-6 and abs(tail) < 1e-6:
                # Nothing moved: no restore point (a dead one would make the
                # next undo visibly do nothing) and no empty undo step.
                edit.cancel()
        if abs(head) < 1e-6 and abs(tail) < 1e-6:
            self._set_footer("Nothing to trim — the shot already fits its content.")
            return
        self._after_shot_change(shot_id)
        self._set_footer(
            f"Trimmed {abs(head):.0f}f from the head, {abs(tail):.0f}f from the tail"
        )

    # ---- extend to keys (global option) ----------------------------------

    def _set_extend_to_keys(self, enabled: bool) -> None:
        """Turn the global "grow the current shot over new keys" option on/off."""
        self._extend_to_keys = bool(enabled)

    def _set_extend_reach(self, frames: float) -> None:
        """Set how far outside a bound a new key may sit and still be claimed.

        ``ANY_REACH`` (-1, the spin box's special value) removes the cap
        entirely; every other value is a distance in frames.
        """
        value = float(frames)
        self._extend_reach = (
            self.ANY_REACH if value <= self.ANY_REACH else max(0.0, value)
        )

    @property
    def _extend_reach_arg(self):
        """:attr:`_extend_reach` as ``extend_shot_to_fit`` takes it.

        The engine's ``reach=None`` is "no cap", which is what the option's
        -1 means -- the UI cannot offer ``None`` in a spin box.
        """
        return None if self._extend_reach <= self.ANY_REACH else self._extend_reach

    def _auto_extend_to_new_keys(self, shot_id: int) -> bool:
        """Grow *shot_id* over keys just set outside it, when the option is on.

        The one place the "Extend to Keys" option acts: keys were just
        created (or pasted) and some of them landed past the shot's bounds,
        which is the moment the animator means the shot to cover them.  It
        runs as its OWN undo step rather than joining the keying that
        triggered it -- the keys and the bound move are two decisions, and
        undoing the bound must not take the keys with it.

        Returns ``True`` when a bound actually moved (the caller then skips
        its own rebuild, since this one already did it).
        """
        if not self._extend_to_keys or self.sequencer is None:
            return False
        return self._extend_shot_to_keys(shot_id, quiet=True)

    def _extend_shot_to_keys(
        self, shot_id: int, edge: str = "both", quiet: bool = False
    ) -> bool:
        """Grow *shot_id* over the keys its members have within reach of its
        bounds, undoable, then refresh the widget.

        The explicit form of the auto-extend a Move to Shot performs: the
        animator set keys just past a bound and wants the shot to cover
        them.  Reach is the global option's setting (:attr:`_extend_reach`,
        -1 for any distance); keys beyond it, and keys inside a neighbouring
        shot, are left alone.  *edge* limits the growth to ``"leading"`` or
        ``"trailing"``.  With *quiet* a no-op reports nothing -- the
        automatic path runs on every keying burst, and "nothing to extend
        to" is its normal answer, not news.

        Returns whether a bound moved.
        """
        if self.sequencer is None:
            return False
        was_syncing = self._syncing
        # Only the WRITES: re-sampling a bound edits keys, and on the automatic
        # path that would re-arm the very debounce that called us.  The rebuild
        # below runs unguarded, as it does for every other edit here -- it holds
        # its own guard where it needs one (``_rebuild_content``).
        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("Extend Shot") as edit:
                head, tail = self.sequencer.extend_shot_to_fit(
                    shot_id, edge=edge, reach=self._extend_reach_arg
                )
                if abs(head) < 1e-6 and abs(tail) < 1e-6:
                    # The automatic path runs on every keying burst, where
                    # "nothing to extend to" is the normal answer: it must not
                    # leave an empty step in the user's history each time.
                    edit.cancel()
        except ShotBoundaryConflict as exc:
            # A refusal is reported, never raised (see _add_shot_space; the
            # restore point is the store's to keep or drop).
            self.logger.warning(str(exc))
            if not quiet:
                self._set_footer(str(exc))
            return False
        finally:
            self._syncing = was_syncing
        if abs(head) < 1e-6 and abs(tail) < 1e-6:
            if not quiet:
                reach = self._extend_reach_arg
                self._set_footer(
                    "Nothing to extend to — no keys "
                    + (
                        "outside the bounds."
                        if reach is None
                        else f"within {reach:g} frames of the bounds."
                    )
                )
            return False
        self._after_shot_change(shot_id)
        self._set_footer(
            f"Extended {abs(head):.0f}f at the head, {abs(tail):.0f}f at the tail"
        )
        return True

    # -- new shots -----------------------------------------------------------

    def _insert_shot(self, anchor_shot_id: int, before: bool) -> None:
        """Insert a new shot before or after *anchor_shot_id*.

        Downstream shots (and their keys and audio) ripple to open the
        space, so this never overwrites existing content.
        """
        if self.sequencer is None:
            return
        seq = self.sequencer
        anchor = seq.shot_by_id(anchor_shot_id)
        if anchor is None:
            return
        sorted_s = seq.sorted_shots()
        idx = next(
            (i for i, sh in enumerate(sorted_s) if sh.shot_id == anchor_shot_id), 0
        )
        # Guarded: the store announces the new shot from inside the edit, and
        # rebuilding on that drew the panel twice (0.75 s of a 2.8 s New Shot
        # on a production assembly); ``_take_new_shot`` draws it once.
        was_syncing = self._syncing
        self._syncing = True
        try:
            with seq.store.scene_edit("Insert Shot"):
                shot = seq.new_shot(at_position=(idx + 1) if before else (idx + 2))
        finally:
            self._syncing = was_syncing
        self._take_new_shot(shot)
        self._set_footer(f"Inserted {shot.name} · {shot.start:.0f}–{shot.end:.0f}")

    def _take_new_shot(self, shot) -> None:
        """Make the shot just created the one being worked on.

        Every way of making a shot ends here -- the one-click new shot, an
        insert, a detected shot: it becomes the active shot (store first, so
        the dropdown follows it), its objects selected and the playback range
        set to it, with the playhead on its first frame (Playhead to Shot
        Start, header menu) -- then the one post-edit refresh draws all of it.
        """
        self.select_shot(shot.shot_id)
        self._land_on_shot(shot)
        self._after_shot_change(shot.shot_id)

    def _create_shot_one_click(self) -> None:
        """Append a new shot: the configured gap on, Initial Length long."""
        if self.sequencer is None:
            return
        # Through the sequencer-level append (``new_shot`` -> insert_shot with
        # no anchor), not the pure store.append_shot: the engine probes the
        # last shot's trailing envelope content (fade tails, trailing audio)
        # so the new shot is never built on top of it — and the snapshot makes
        # the creation undoable via the ledger's membership diff, its own undo
        # step paired with that restore point (without one, the panel's undo
        # also popped the user's previous, unrelated step).  The Shots
        # window's New Shot is the same call.
        # Guarded: the store announces the new shot from inside the edit, and
        # rebuilding on that drew the panel twice (0.75 s of a 2.8 s New Shot
        # on a production assembly); ``_take_new_shot`` draws it once.
        was_syncing = self._syncing
        self._syncing = True
        try:
            with self.sequencer.store.scene_edit("New Shot"):
                shot = self.sequencer.new_shot()
        finally:
            self._syncing = was_syncing
        self._take_new_shot(shot)
        self._set_footer(f"Created {shot.name} · {shot.start:.0f}–{shot.end:.0f}")

    # -- lookups and the Shots window ----------------------------------------

    def _find_shot_at_time(self, time: float):
        """Return the shot whose range contains *time*, or ``None``."""
        if self.sequencer is None:
            return None
        for s in self.sequencer.sorted_shots():
            if s.start <= time <= s.end:
                return s
        return None

    def _on_shot_switch_requested(self, time: float) -> None:
        """Ctrl+Shift+Click on timeline — switch to the shot at *time*."""
        shot = self._find_shot_at_time(time)
        if shot is not None:
            self.on_shot_block_clicked(shot.name)

    def _edit_shot_dialog(self, shot) -> None:
        """Open Shot Settings with the given shot pre-selected for editing."""
        self.sequencer.store.set_active_shot(shot.shot_id)
        self._show_shots_window()

    def _show_shots_window(self):
        """Open the Shots window PINNED, and return it.

        Opened from here to edit a shot, it has to stay up while the user
        works in it; unpinned, it went the way of a marking-menu window as
        soon as the pointer left it ("edit shot should launch the shots
        window in a pinned state").  Pinned, its pin button is the one that
        puts it away.  A window with no pin button is left as it is: it never
        auto-hides, and pinned it would refuse every hide with no button to
        undo it.
        """
        window = self.sb.handlers.marking_menu.show("shots")
        header = getattr(window, "header", None)
        if "pin" in (getattr(header, "buttons", None) or {}):
            window.set_pinned(True)
        return window
