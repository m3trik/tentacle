# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest panel following the scene's store: its events (a shot
added, edited, removed or re-ranged anywhere), a swapped store (scene new /
open), the settings detection reads, and the re-assessment owed after edits.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

import pythontk as ptk
from pythontk import (
    BatchComplete,
    BuilderStep,
    MarkersChanged,
    SettingsChanged,
    ShotDefined,
    ShotRemoved,
    ShotsEdited,
    ShotUpdated,
    StoreEvent,
)

from .manifest_data import COL_END, COL_START


class StoreFollowMixin:
    """Store events and scene swaps, mixed into ``ShotManifestController``.

    Uses the controller's ``_store_cls()``, ``_active_store()``, ``_pairing()``,
    ``_orphan_shots()``, ``_redraw()``, ``_populate_table()``,
    ``_load_scene_shots()``, ``_open_scene_source()``, ``_refresh_ranges()``,
    ``detect()``, ``assess()`` and the panel state they read.
    """

    def _bind_store_listener(self) -> None:
        """Register as a listener on the active ShotStore."""
        if self._store_listener_bound:
            return
        try:
            store = self._store_cls().active()
            store.add_listener(self._on_store_event)
            self._bound_store = store
            self._store_listener_bound = True
            self._detection_snapshot = self._detection_inputs()
        except Exception:
            pass

    def _detection_inputs(self) -> tuple:
        """The store settings the steps' detection, auto-filled ranges and
        build layout read -- detection mode and threshold, gap, new-shot
        length, fit mode -- with the store itself (``()`` without one)."""
        store = self._active_store()
        if store is None:
            return ()
        return (
            store,
            store.detection_mode,
            store.detection_threshold,
            store.gap,
            store.initial_shot_length,
            store.fit_mode,
        )

    def _unbind_store_listener(self) -> None:
        """Remove the ShotStore listener."""
        if not self._store_listener_bound:
            return
        try:
            store = getattr(self, "_bound_store", None)
            if store is not None:
                store.remove_listener(self._on_store_event)
                self._bound_store = None
        except Exception:
            pass
        self._store_listener_bound = False

    def remove_callbacks(self) -> None:
        """Remove the ShotStore listener and the invalidation subscription,
        and stop a pending re-assessment."""
        self._unbind_store_listener()
        self._store_cls().remove_invalidation_listener(self._on_store_invalidated)
        self._store_cls().remove_native_step_listener(self._on_native_step_followed)
        if self._reassess_timer is not None:
            self._reassess_timer.stop()

    def _on_native_step_followed(self, event) -> None:
        """The DCC's own undo or redo ran (``NativeStepFollowed``): when it
        undid the last Build -- every shot it made gone again -- the typed
        ranges it re-based come back as they were, and a redo of it brings
        its own back (``_build_undo``, kept by ``_rebase_typed_ranges``)."""
        undo = self._build_undo
        if undo is None or event.store is not undo["store"] or not event.applied:
            return
        ids = {shot.shot_id for shot in undo["store"].shots}
        if event.redo and undo["made"] <= ids:
            ranges = undo["after"]
        elif not event.redo and not undo["made"] & ids:
            ranges = undo["before"]
        else:
            return
        self._user_ranges, self._seeded_ranges = (dict(r) for r in ranges)
        if self._first_shown and self._steps and not self._building:
            self._redraw()

    def _on_store_invalidated(self, event=None) -> None:
        """The active store was swapped (:meth:`_on_scene_changed`)."""
        self._on_scene_changed()

    def _on_scene_changed(self) -> None:
        """Handle a scene open / new-scene event.

        Re-binds the store listener (the old store is stale) and
        re-populates the table from CSV or detection, mirroring the
        logic in ``_on_first_show``.
        """
        # The old store is invalidated by ShotStore._on_scene_changed.
        self._unbind_store_listener()
        self._store = None
        self._bind_store_listener()
        # Another scene: its manifest opens unassessed (_load_data runs a
        # showing assessment again, and this one judged the old scene) -- a
        # re-assessment the old one was owed is dropped with it.
        self._last_results = []
        self._reassess_on_show = False
        self._reassess_note = ""
        if self._reassess_timer is not None:
            self._reassess_timer.stop()

        if not self._first_shown:
            return

        self._open_scene_source()

    def _on_store_event(self, event: StoreEvent) -> None:
        """React to ShotStore mutations — refresh tree timing if steps are loaded."""

        if self._building:
            return
        if isinstance(event, SettingsChanged):
            # One event for every store setting, but only the detection inputs
            # move the steps and ranges: re-detecting for another -- a Render
            # Effects recipe spinbox, a snap toggle, a Shots-panel trim --
            # regenerated the steps (typed ranges, renamed steps gone) per
            # tick.  It does stale the last Assess, which judged the old keys.
            inputs = self._detection_inputs()
            if inputs == self._detection_snapshot:
                if self._last_results:
                    # Dropped (Build waits for a fresh judgement) and run
                    # again once the change settles.
                    self._last_results = []
                    self._reassess_soon()
                self._update_build_button()
                return
            self._detection_snapshot = inputs
            # Detection settings changed — invalidate cache and re-detect.
            # Guard on _first_shown to avoid triggering detection (and
            # message boxes) before the widget is visible.
            self._cached_gaps = None
            self._cached_gap_ends = None
            if self._first_shown:
                if self._csv_path:
                    # CSV defines steps — don't replace them with detected
                    # steps.  Just refresh auto-filled ranges so the new
                    # detection mode takes effect.
                    if self._steps:
                        self._refresh_ranges()
                elif self._source != "scene":
                    # The scene's own shots don't depend on detection settings.
                    self.detect()
            return
        if isinstance(event, MarkersChanged):
            # The rows stand, but a marked behavior is judged by its marker
            # (an undo takes a build's out): a showing Assess is run again.
            if self._first_shown and self._last_results:
                self._reassess_soon()
            return
        if isinstance(event, self._SHOT_EVENTS):
            self._follow_store()

    #: The store events that change what the table shows: the shots, their
    #: bounds, names and members.  ``ShotsEdited`` is the only word of an
    #: edit that writes bounds directly (a trim, resize, ripple or respace in
    #: the Shot Sequencer or the Shots window).
    _SHOT_EVENTS = (ShotDefined, ShotUpdated, ShotRemoved, BatchComplete, ShotsEdited)

    #: How long a burst of edits must settle before a showing assessment is
    #: re-run (one drag can land several events).
    REASSESS_DELAY_MS = 300

    def _follow_store(self) -> None:
        """Bring the table up to the store after a shot edit made anywhere
        (2026-10-07: "the manifest doesn't refresh properly on many actions").

        The scene's own shots ARE the steps, so they are read again (keeping
        the user's expansion); a sheet's or a detection's built rows take
        their shots' live Start / End, and on a built timeline the unbuilt
        rows' preview is worked out again (:meth:`_refresh_ranges`: the
        shots' bounds, no animation scan) -- an edited shot moves where Build
        inserts the next.  A showing assessment judged the scene before the
        edit, so it is re-run once the edits settle (:meth:`_reassess_soon`);
        with none showing nothing is assessed.
        """
        if not self._first_shown:
            return
        assessed = bool(self._last_results)
        if self._source == "scene":
            # One edit can raise several events (its batch's, then its
            # scene_edit's); a reload costs ~60 ms on a 38-shot production
            # scene, so the shots the table already shows are not re-read.
            shown = self._shots_record()
            if shown != self._shown_record:
                state = self._save_tree_state()
                self._load_scene_shots(detect_when_empty=False)
                self._restore_tree_state(state)
                self._shown_record = shown
        elif self._steps:
            # A shot added, removed, renamed, reordered or given members
            # elsewhere changes the rows: the table is drawn again.
            # Otherwise only the live ranges change.
            if self._pairing_key() != self._shown_pairing:
                self._redraw()
            else:
                self._refresh_timing()
                if self._is_built and not self._use_selected_keys:
                    self._refresh_ranges()
        else:
            return
        if assessed:
            self._reassess_soon()
        self._update_build_button()

    def _shots_record(self) -> tuple:
        """Everything the scene's shots give the table (``from_shots``): what
        tells :meth:`_follow_store` the shots changed since it last read them."""
        store = self._active_store()
        return tuple(
            (
                s.shot_id,
                s.name,
                s.start,
                s.end,
                s.description,
                tuple(s.objects),
                repr(s.metadata),
            )
            for s in (store.sorted_shots() if store is not None else ())
        )

    def _pairing_key(self, pairing=None) -> tuple:
        """Which shot each step has and which shots no step has, the shots'
        timeline order, members and locks: what the table's rows hang on
        (:meth:`_follow_store`) -- a shot moved past another moves its "not in
        doc" row, a member added in the Shot Sequencer is a row."""
        pairing = pairing if pairing is not None else self._pairing()
        return (
            tuple(sorted((sid, s.shot_id) for sid, s in pairing.shots.items())),
            tuple(s.shot_id for s in self._orphan_shots(pairing)),
            tuple((s.shot_id, tuple(s.objects), s.locked) for s in pairing.timeline),
        )

    def _reassess_soon(self, note: str = "") -> None:
        """Re-run Assess once a burst of edits settles: one timer, restarted
        by every edit.  A hidden panel re-assesses when it is next shown.
        *note* (the edit's own word, e.g. ``"Hid 2 step(s)."``) leads the
        footer the assessment writes; the last edit's wins."""
        self._reassess_note = note
        timer = self._reassess_timer
        if timer is None:
            from qtpy import QtCore

            timer = self._reassess_timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.setInterval(self.REASSESS_DELAY_MS)
            timer.timeout.connect(self._reassess)
        timer.start()

    def _reassess(self) -> None:
        """The deferred re-assessment (:meth:`_reassess_soon`)."""
        if self._building or not self._steps:
            return
        if not self.ui.isVisible():
            self._reassess_on_show = True
            return
        self._reassess_on_show = False
        note, self._reassess_note = self._reassess_note, ""
        self.assess(skip_key_check=True, note=note)

    def _on_show(self) -> None:
        """A re-assessment owed while the panel was hidden runs now."""
        if self._reassess_on_show:
            self._reassess()

    def _refresh_timing(self) -> None:
        """Write each built row's Start / End from its shot (the active
        store's, through the pairing), and each "not in doc" row's from its
        own: the store is the truth for every row that has a shot."""
        from qtpy.QtCore import Qt

        store = self._active_store()
        timing_map = self._pairing().shots
        tree = self.ui.tbl_steps
        tree.blockSignals(True)
        try:
            for i in range(tree.topLevelItemCount()):
                parent = tree.topLevelItem(i)
                step_data = parent.data(0, Qt.UserRole)
                if isinstance(step_data, BuilderStep):
                    shot = timing_map.get(step_data.step_id)
                elif isinstance(step_data, ptk.ShotBlock) and store is not None:
                    # By id: an undo restores a removed shot as a new record.
                    shot = store.shot_by_id(step_data.shot_id)
                else:
                    shot = None
                if shot is None:
                    continue
                parent.setText(COL_START, f"{shot.start:.0f}")
                parent.setText(COL_END, f"{shot.end:.0f}")
                parent.setToolTip(COL_START, f"{shot.end - shot.start:.0f}f")
                parent.setToolTip(COL_END, f"{shot.end - shot.start:.0f}f")
        finally:
            tree.blockSignals(False)
        self._refresh_export_preview()  # an open one shows these frames
