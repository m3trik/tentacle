# !/usr/bin/python
# coding=utf-8
"""Key context menus and the edits run over a key selection, for the Shot
Sequencer panel.

:class:`KeyMenuMixin` is one of the concept mixins of
:class:`~tentacle.slots.tools._shot_sequencer.controller.ShotSequencerController`:
the key menu (the host's tangent types, its interpolation modes where it has
them, Break / Unify, Move / Copy to Shot), dragged tangent handles, and the
edits run over a key selection -- simplify, thin, snap, invert, align, Euler
filter, copy / paste and stash.  What a row writes is the host's (``self.host``,
the host library's ``SequencerHost``): its tangent rows and the edits they
build, the key operations over plain ``targets``, the key clipboard's records.
"""

import pythontk as ptk
from qtpy import QtWidgets


class KeyMenuMixin:
    """Key context menus, tangent edits and drags, and the key-selection edits.

    ``targets`` throughout is ``[(obj, attr, [times], shot_id), ...]`` -- one
    entry per writable attribute row of a key selection (:meth:`_key_targets`).
    """

    # -- key context menu ---------------------------------------------------

    def _key_targets(self, widget, key_groups: list) -> list:
        """``[(obj, attr, [times], shot_id), ...]`` for a key selection.

        One entry per writable sub-row clip in *key_groups* (the payload of
        ``key_selection_changed`` / ``key_menu_requested``); read-only clips
        and object-level rows (no attribute) contribute nothing.
        """
        targets = []
        for group in key_groups:
            clip = widget.get_clip(group["clip_id"])
            if clip is None or clip.data.get("read_only"):
                continue
            obj = clip.data.get("obj")
            attr = clip.data.get("attr_name")
            times = sorted(group.get("times") or [])
            if not obj or not attr or not times:
                continue
            targets.append((obj, attr, times, clip.data.get("shot_id")))
        return targets

    @staticmethod
    def _key_targets_to_sequences(targets: list) -> list:
        """The key-level sequence dicts ``move_sequences_to_shot`` takes."""
        return [
            {
                "kind": "anim",
                "obj": obj,
                "attr": attr,
                "times": list(times),
                "start": times[0],
                "end": times[-1],
            }
            for obj, attr, times, _sid in targets
        ]

    def on_key_menu(self, menu, key_groups: list) -> None:
        """Add the key actions to a key's context menu.

        Mirrors the host Graph Editor's own right-click: a Tangents submenu
        that sets both sides, In / Out submenus for one side (the host's
        tangent types, ``SequencerHost.TANGENT_TYPES``), an Interpolation
        submenu where the host has interpolation modes apart from its tangent
        types (``SequencerHost.INTERPOLATIONS``: Blender's; Maya's step and
        linear are tangent types), Break / Unify, and -- the sequencer's own --
        Move / Copy to Shot, which sends exactly the selected keys, per
        attribute, as sequences.  It also carries the Animation panel's key
        edits (:meth:`_add_key_edit_actions`), which belong to a key
        SELECTION: they were briefly offered per SHOT, where "remove the
        intermediate keys" meant every member's every attribute across the
        whole span -- a far bigger edit than the words promise.  The widget
        appends Delete.
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        targets = self._key_targets(widget, key_groups)
        if not targets:
            return
        host = self.host

        n = sum(len(t) for _o, _a, t, _s in targets)
        suffix = f" ({n})" if n > 1 else ""

        # Explicit parents: an ``addMenu(str)`` wrapper can go stale once this
        # frame drops it (PySide 6.11), and the actions bind to the submenu.
        for label, sides in (
            ("Tangents", ("in", "out")),
            ("In Tangent", ("in",)),
            ("Out Tangent", ("out",)),
        ):
            sub = QtWidgets.QMenu(label, menu)
            menu.addMenu(sub)
            for name, tangent in host.TANGENT_TYPES:
                act = sub.addAction(name)
                act.triggered.connect(
                    lambda _checked=False, t=tangent, s=sides: self._set_key_tangents(
                        targets, t, s
                    )
                )
        if host.INTERPOLATIONS:
            interp = QtWidgets.QMenu("Interpolation", menu)
            menu.addMenu(interp)
            for name, mode in host.INTERPOLATIONS:
                act = interp.addAction(name)
                act.triggered.connect(
                    lambda _checked=False, m=mode: self._set_key_interpolation(
                        targets, m
                    )
                )
        act_break = menu.addAction(f"Break Tangents{suffix}")
        act_break.triggered.connect(lambda: self._lock_key_tangents(targets, False))
        act_unify = menu.addAction(f"Unify Tangents{suffix}")
        act_unify.triggered.connect(lambda: self._lock_key_tangents(targets, True))

        self._add_selection_key_actions(menu, targets, suffix)

    def _add_selection_key_actions(self, menu, targets: list, suffix: str = "") -> None:
        """The key menu's rows past the tangents -- the key edits
        (:meth:`_add_key_edit_actions`) and Move / Copy to Shot -- for a
        selection from any view: the graph's menu offers them too."""
        self._add_key_edit_actions(menu, targets, suffix)

        if self.sequencer:
            seqs = self._key_targets_to_sequences(targets)
            shots = self.sequencer.sorted_shots()
            if seqs and len(shots) > 1:
                menu.addSeparator()
                self._add_send_to_shot_menu(menu, seqs, noun="key", suffix=suffix)

    def _set_key_tangents(self, targets: list, tangent: str, sides=("in", "out")):
        """Set a tangent type (one of ``SequencerHost.TANGENT_TYPES``) on the
        selected keys, one or both sides (``SequencerHost.tangent_type_edit``)."""
        side = "" if len(sides) == 2 else f" {sides[0]}"
        self._edit_key_tangents(
            targets,
            self.host.tangent_type_edit(tangent, sides),
            f"{tangent.lower()}{side}",
        )

    def _set_key_interpolation(self, targets: list, mode: str) -> None:
        """Set the interpolation mode (one of ``SequencerHost.INTERPOLATIONS``)
        of the selected keys (``SequencerHost.interpolation_edit``)."""
        self._edit_key_tangents(
            targets, self.host.interpolation_edit(mode), mode.lower()
        )

    def _lock_key_tangents(self, targets: list, lock: bool) -> None:
        """Break (``lock=False``) or unify the selected keys' tangents
        (``SequencerHost.tangent_lock_edit``: Maya's tangent lock, Blender's
        FREE vs ALIGNED handles)."""
        self._edit_key_tangents(
            targets,
            self.host.tangent_lock_edit(lock),
            "unified" if lock else "broken",
        )

    def on_keys_tangent_dragged(self, groups: list, side: str, broken: bool) -> None:
        """Write the tangents a dragged handle asks for on the keys' curves.

        *groups* is the whole gesture -- ``[(clip_id, [(time, dt, dv), ...]),
        ...]``, one handle VECTOR per key the drag carried, since a tangent
        drag carries the key SELECTION unless the user held Ctrl (Shift makes
        every key take the grabbed one's exact vector; the widget resolves
        both before it emits).  *broken* is the Alt drag: the KEY breaks, so
        its other side stops swinging with the dragged one.  How a vector
        becomes a tangent is the host's (``SequencerHost.handle_drag_edit``:
        Maya's angle, and weight on a weighted curve; Blender's handle placed
        directly).  All in one undo step: the drag is one gesture and takes
        one Ctrl+Z.
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        # Keyed by row, not by time alone: two clips can be the same frame on
        # different objects, and each carries its own vector.
        vectors = {}
        for clip_id, entries in groups:
            clip = widget.get_clip(clip_id)
            if clip is None:
                continue
            row = (clip.data.get("obj"), clip.data.get("attr_name"))
            for time, dt, dv in entries:
                vectors[row + (round(float(time), 6),)] = (dt, dv)
        targets = self._key_targets(
            widget,
            [
                {"clip_id": clip_id, "times": [t for t, _dt, _dv in entries]}
                for clip_id, entries in groups
            ],
        )
        if not targets:
            return
        what = f"{side} handle {'broken' if broken else 'dragged'}"
        self._edit_key_tangents(
            targets, self.host.handle_drag_edit(vectors, side, broken), what
        )

    def _edit_key_tangents(self, targets: list, edit, what: str) -> None:
        """Apply a tangent *edit* to the selected keys, one undo step.

        *edit* is opaque here: built by the host (``SequencerHost.
        tangent_type_edit`` and its siblings) or by the host's own graph glue
        (``GraphSync``), and applied by ``SequencerHost.edit_key_tangents``.

        The rebuild that follows retires every key dot, so the selection is
        put back by object/attribute/time afterwards -- the user is looking
        at the handles they just changed, and they must stay selected to
        show them.
        """
        widget = self._get_sequencer_widget()
        if widget is None or not targets:
            return
        shot_id = next((sid for _o, _a, _t, sid in targets if sid is not None), None)
        was_syncing = self._syncing
        self._syncing = True  # own key edits must not arm the keyframe debounce
        try:
            n = self.host.edit_key_tangents(targets, edit)
        finally:
            self._syncing = was_syncing
        self._sub_row_cache.clear()
        self._sync_to_widget(shot_id=shot_id)
        widget.select_keys(
            [
                {"data": {"obj": obj, "attr_name": attr}, "times": list(times)}
                for obj, attr, times, _sid in targets
            ]
        )
        self._set_footer(f"Tangents {what} on {n} key{'s' if n != 1 else ''}")

    # -- key-selection edits (tentacle's Animation panel, per selection) -----

    #: The key edits offered under the key menu's Edit row, as
    #: ``(label, method name)`` -- one list for both hosts, unlike the tangent
    #: rows above them (the host's own types).
    _KEY_EDITS = (
        ("Simplify", "_simplify_selected_keys"),
        ("Remove Intermediate Keys", "_thin_selected_keys"),
        ("Snap Fractional Keys", "_snap_selected_keys"),
        ("Invert Keys", "_invert_selected_keys"),
        ("Align Keys", "_align_selected_keys"),
        ("Euler Filter", "_euler_filter_selected_keys"),
    )

    def _add_key_edit_actions(self, menu, targets, suffix) -> None:
        """Append the stash and Edit rows to the key menu.

        Everything here is scoped to the keys actually SELECTED -- the
        objects they belong to and the span they cover -- which is what
        makes them safe to offer at all: the same verbs applied to a whole
        shot silently reached every member's every attribute.

        Copy and Paste are NOT rows: they are the panel's ``Ctrl+C`` /
        ``Ctrl+V`` (see ``_copy_keys_shortcut``), because they are the one
        pair here that every editor already binds a key for.
        """
        menu.addSeparator()
        act_store = menu.addAction(f"Store Keys{suffix}")
        act_store.triggered.connect(lambda: self._stash_key_targets(targets))

        edit = QtWidgets.QMenu("Edit", menu)
        menu.addMenu(edit)
        for label, method in self._KEY_EDITS:
            act = edit.addAction(label)
            act.triggered.connect(
                lambda _checked=False, m=method: getattr(self, m)(targets)
            )

    @staticmethod
    def _target_objects(targets: list) -> list:
        """*targets*' objects, de-duplicated, in the order they appear."""
        return list(dict.fromkeys(obj for obj, _a, _t, _s in targets))

    @staticmethod
    def _target_span(targets: list) -> tuple:
        """The frame range *targets* covers, end to end."""
        times = [t for _o, _a, ts, _s in targets for t in ts]
        return (min(times), max(times))

    def _key_scene_edit(self, label: str, fn, shot_id=None):
        """Run *fn* as ONE undoable scene edit, reconcile, rebuild.

        The bracket every key edit needs and none of them should re-state:
        the store's ``scene_edit`` (a named undo step plus a boundary
        restore point), then ``reconcile_system_edits`` because an edit that
        adds, moves or removes keys may have touched a sample the shot
        system authored.  ``_syncing`` is held throughout so our own writes
        do not re-arm the keyframe debounce and rebuild underneath us.

        A raise keeps the restore point: ``scene_edit`` has tagged its step
        by then, so the keys *fn* wrote before raising undo with it, and the
        bounds and claims have to come back with them.

        Returns whatever *fn* returned, or ``None`` with no sequencer.
        """
        if self.sequencer is None:
            return None
        was_syncing = self._syncing
        self._syncing = True
        try:
            with self.sequencer.store.scene_edit(label):
                result = fn()
                self.sequencer.reconcile_system_edits()
        finally:
            self._syncing = was_syncing
        self._segment_cache.clear()
        self._sub_row_cache.clear()
        self._sync_to_widget(shot_id=shot_id)
        return result

    def _key_selection_edit(self, targets, label: str, fn):
        """Run ``fn(objects, span)`` over a key selection; ``(ran, result)``.

        Asserts the host's key selection first (:meth:`_select_target_keys`):
        several of Maya's edits read the Graph Editor selection rather than
        taking a range.

        Two return values because these edits disagree about what to report
        -- a count, a pair, a list -- so "it ran" cannot be read off the
        result.
        """
        if not targets or self.sequencer is None:
            return False, None
        self._select_target_keys(targets)
        objects = self._target_objects(targets)
        span = self._target_span(targets)
        shot_id = next((sid for _o, _a, _t, sid in targets if sid is not None), None)
        result = self._key_scene_edit(label, lambda: fn(objects, span), shot_id=shot_id)
        return True, result

    def _simplify_selected_keys(self, targets) -> None:
        """Drop the selected keys that carry neither a value nor a shape.

        What ``optimize_keys`` does, minus the part a context-menu edit must
        not do, aimed at a key SELECTION instead of a whole scene: the FLAT
        pass (the interior keys of a run that all hold one value -- the one
        that matters on real footage, since a hold is usually stepped and a
        stepped curve is exactly what the reducer will not touch) then the
        SHAPE pass, both over the selected attributes' curves and, within
        them, the selected keys (``SequencerHost.simplify_keys``).  Neither
        reaches the attributes beside the one the user highlighted.  A key
        either pass removes takes its claims with it, as a replaced one does
        (``ShotStore.release_replaced``).
        """
        ran, counts = self._key_selection_edit(
            targets,
            "Simplify",
            lambda objects, span: self.host.simplify_keys(
                targets, span, on_delete=self._claims_follow(objects)["on_replace"]
            ),
        )
        if not ran:
            return
        n_flat, n_shaped = counts or (0, 0)
        if n_flat or n_shaped:
            parts = []
            if n_flat:
                parts.append(f"{n_flat} flat key{'s' if n_flat != 1 else ''}")
            if n_shaped:
                parts.append(f"{n_shaped} curve{'s' if n_shaped != 1 else ''} reduced")
            self._set_footer("Simplified: " + ", ".join(parts))
        else:
            self._set_footer(
                "Nothing to simplify — every selected key carries value or shape"
            )

    def _thin_selected_keys(self, targets) -> None:
        """Keep only the first and last key of each selected attribute
        (``SequencerHost.thin_keys``), scoped to the attributes outright: the
        strip must narrow to the sub-rows the user selected.  A key it removes
        takes its claims with it, as a replaced one does."""
        ran, n = self._key_selection_edit(
            targets,
            "Remove Intermediate Keys",
            lambda objects, span: self.host.thin_keys(
                targets, span, on_delete=self._claims_follow(objects)["on_replace"]
            ),
        )
        if ran:
            self._set_footer(
                f"Removed {n or 0} intermediate key{'s' if n != 1 else ''}"
            )

    def _snap_selected_keys(self, targets) -> None:
        """Pull the selected keys off fractional frames onto whole ones."""
        ran, n = self._key_selection_edit(
            targets,
            "Snap Keys",
            # A snap never replaces a key (a taken target is skipped); the keys
            # it moves carry their claims along.
            lambda objects, span: self.host.snap_keys(
                targets, span, on_move=self._claims_follow(objects)["on_move"]
            ),
        )
        if ran:
            self._set_footer(
                f"Snapped {n or 0} key{'s' if n != 1 else ''} to whole frames"
            )

    def _euler_filter_selected_keys(self, targets) -> None:
        """Unflip the selected channels' rotation curves
        (``SequencerHost.euler_filter_keys``).

        Whole curves, as the Graph Editor's Euler Filter filters them:
        unwrapping a span alone would leave a new jump at its edge.  Values
        only -- no key moves, so no claim changes hands.
        """
        ran, done = self._key_selection_edit(
            targets,
            "Euler Filter",
            lambda _objects, _span: self.host.euler_filter_keys(targets),
        )
        if ran:
            n = len(done or ())
            self._set_footer(
                f"Euler filter: {n} rotation curve{'s' if n != 1 else ''}"
                if n
                else "Euler filter: no rotation curve among the selected keys"
            )

    def _claims_follow(self, objects) -> dict:
        """The ``on_replace`` / ``on_move`` a key edit over *objects* takes: a
        key it REPLACES takes its claims with it (``ShotStore.release_replaced``,
        as every key the system cuts does) and a key it MOVES carries them
        along (``ShotStore.remap_moved``, as the sequencer's own moves do) --
        both over ONE key resolution (``ShotStore.claim_hooks``)."""
        on_replace, on_move = self.sequencer.store.claim_hooks(objects)
        return {"on_replace": on_replace, "on_move": on_move}

    def _invert_selected_keys(self, targets) -> None:
        """Mirror the selected keys in time, in place, over their combined
        range (``SequencerHost.invert_keys``): the keys around them stay put.
        A key the mirror lands on is replaced and a key it moves carries its
        claims along (:meth:`_claims_follow`)."""
        ran, n = self._key_selection_edit(
            targets,
            "Invert Keys",
            lambda objects, _span: self.host.invert_keys(
                targets, **self._claims_follow(objects)
            ),
        )
        if ran:
            self._set_footer(
                f"Inverted {n} key{'s' if n != 1 else ''}" if n else "Nothing to invert"
            )

    def _align_selected_keys(self, targets) -> None:
        """Line the selected keys up on the earliest one's frame
        (``SequencerHost.align_keys``; claims follow as Invert's do)."""
        ran, n = self._key_selection_edit(
            targets,
            "Align Keys",
            lambda objects, _span: self.host.align_keys(
                targets, **self._claims_follow(objects)
            ),
        )
        if ran:
            self._set_footer(
                f"Aligned {n} key{'s' if n != 1 else ''}" if n else "Nothing to align"
            )

    #: ``{editor name: callable() -> targets}`` -- how a key shortcut finds
    #: the selection while a view other than the track rows shows
    #: (:meth:`register_key_targets`).  Replaced, never mutated in place:
    #: the class default is shared.
    _key_target_sources: dict = {}

    def register_key_targets(self, editor_name: str, source) -> None:
        """Resolve the key shortcuts' targets through *source* while the
        editor *editor_name* shows (``None`` drops it).

        *source* returns ``[(obj, attr, [times], shot_id), ...]``, the shape
        :meth:`_key_targets` reads from the track rows: the graph's
        ``GraphSync`` registers its curve-keyed selection here, so Ctrl+C /
        Ctrl+V act on what the graph has selected.
        """
        sources = dict(self._key_target_sources)
        if source is None:
            sources.pop(editor_name, None)
        else:
            sources[editor_name] = source
        self._key_target_sources = sources

    def _selected_key_targets(self) -> list:
        """The key menu's ``targets`` for whatever is selected right now.

        What a SHORTCUT has to resolve for itself: a menu is handed its
        groups, a key press is not.
        """
        widget = self._get_sequencer_widget()
        if widget is None:
            return []
        editor = getattr(widget, "active_editor", None)
        source = self._key_target_sources.get(getattr(editor, "name", None))
        if source is not None:
            return source()
        return self._key_targets(widget, widget.selected_keys())

    def _copy_keys_shortcut(self) -> None:
        """Ctrl+C over the sequencer: copy the selected keys."""
        self._copy_selected_keys(self._selected_key_targets())

    def _paste_keys_shortcut(self) -> None:
        """Ctrl+V over the sequencer: paste them at the playhead."""
        self._paste_selected_keys(self._selected_key_targets())

    #: The panel's key clipboard (:meth:`_copy_selected_keys`), as the host
    #: wrote it (``SequencerHost.copy_keys``): ``{"rows": [(obj, attr, [key
    #: record, ...]), ...], "start": frame, ...}`` -- the key records are the
    #: host's own.  On the class, so a slots re-init -- a fresh controller --
    #: keeps it; it outlives the scene (a row whose object is gone pastes
    #: nothing).
    _key_clipboard: dict = {}

    def _copy_selected_keys(self, targets) -> None:
        """Copy the selected keys onto the panel's own clipboard.

        Its own, not the host's (2026-10-10: "devise our own copy/paste
        system within the shot_sequencer"): a Graph Editor copy takes the shot
        system's gap holds -- the step it writes on the last key before a gap
        -- as if the animator had keyed them, and its paste writes over keys
        the system holds by frame.  Here each key is copied as the animator
        left it (``SequencerHost.copy_keys``: a held seam carries the tangent
        it had before the hold, ``ShotEditLedger.claimed_step``), and the
        system's bound samples are never selectable to begin with.  Copying
        changes no scene data and stays off the undo queue.
        """
        if not targets or self.sequencer is None:
            return
        clipboard = self.host.copy_keys(self.sequencer, targets)
        rows = clipboard.get("rows") if clipboard else None
        if not rows:
            self._set_footer("Nothing to copy")
            return
        type(self)._key_clipboard = clipboard
        n = sum(len(keys) for _o, _a, keys in rows)
        self._set_footer(f"Copied {n} key{'s' if n != 1 else ''}")

    def _paste_selected_keys(self, targets) -> None:
        """Paste the panel's clipboard at the playhead (:meth:`_copy_selected_keys`).

        The earliest copied key lands on the playhead and every other keeps
        its distance from it, across rows.  The destination is the rows the
        selected keys are on (``ShotSequencer.paste_pairs``: a lone row onto
        each, else each row onto its attribute's), or -- nothing selected --
        the rows the keys were copied from.  A pasted key replaces the one on
        its frame, which takes its claims with it; the rest of the curve
        stays.  One undo step, the gap holds re-derived after it, and the
        pasted keys selected.  The host's own key clipboard is never read.
        """
        clip = type(self)._key_clipboard
        if not clip:
            self._set_footer("Nothing copied here — Ctrl+C keys in the sequencer first")
            return
        if self.sequencer is None:
            return
        rows = clip["rows"]
        if targets:
            destinations = list(dict.fromkeys((o, a) for o, a, _t, _s in targets))
        else:
            destinations = [(o, a) for o, a, _k in rows]
        # Objects compared by their leaf: a copy and a paste may spell one
        # Maya node long and short.
        pairs = ptk.ShotSequencer.paste_pairs(
            rows, destinations, leaf=self.host.leaf_name
        )
        if not pairs:
            self._set_footer("Nothing copied for the selected rows' attributes")
            return
        now = self._current_time()
        if now is None:
            return
        shot_id = next((sid for _o, _a, _t, sid in targets if sid is not None), None)
        if shot_id is None:
            shot = self._find_shot_at_time(now)
            shot_id = shot.shot_id if shot is not None else None
        on_replace = self._claims_follow([o for o, _a, _k in pairs])["on_replace"]
        # The rows a paste keyed, with the frames they landed on: a row whose
        # object is gone since the copy (the clipboard outlives the scene)
        # keys nothing, and is neither counted nor selected.
        landed = []

        def _run():
            landed.extend(self.host.paste_keys(clip, pairs, now, on_replace=on_replace))
            return len(landed)

        n = self._key_scene_edit("Paste Keys", _run, shot_id=shot_id) or 0
        if not n:
            self._set_footer(
                "Nothing pasted: the copied rows' objects or attributes are gone"
            )
            return
        widget = self._get_sequencer_widget()
        if widget is not None:
            widget.select_keys(
                [
                    {"data": {"obj": obj, "attr_name": attr}, "times": list(frames)}
                    for obj, attr, frames in landed
                ]
            )
        keys_n = sum(len(frames) for _o, _a, frames in landed)
        self._set_footer(
            f"Pasted {keys_n} key{'s' if keys_n != 1 else ''} onto "
            f"{n} row{'s' if n != 1 else ''}"
        )

    def _stash_key_targets(self, targets: list) -> None:
        """Park the selected keys in the key stash.

        The key-selection twin of :meth:`_stash_clip_keys`: same store, same
        loop (:meth:`_run_stash`), scoped to the selected times of each
        attribute instead of a whole clip's span.  Each job is plain values,
        ``(obj, [attr], start, end, shot_id)``; the host resolves them and
        skips an object that is gone (``SequencerHost.stash_keys``).
        """
        jobs = [
            (obj, [attr], min(times), max(times), None if shot_id == -1 else shot_id)
            for obj, attr, times, shot_id in targets
            if times
        ]
        self._run_stash(jobs)
