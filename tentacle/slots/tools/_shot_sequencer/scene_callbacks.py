# !/usr/bin/python
# coding=utf-8
"""Scene events for the shot sequencer: undo/redo, key edits, time changes.

Provides :class:`SceneCallbacksMixin` -- mixed into
:class:`~.controller.ShotSequencerController`. A redraw after the shot store
followed the host's undo/redo, and the host's scene watcher
(``SequencerHost.watch_scene``: Maya's OpenMaya anim-curve and DG time-change
callbacks, Blender's ``bpy.app.handlers``): new keys join the active shot (and
grow it, when that option is on) through a debounced refresh, the playhead
follows the scene's time, and a scene change that keys nothing (a rename, a
sound strip edited outside the panel) is a plain rebuild.
"""

from qtpy import QtCore


class SceneCallbacksMixin:
    """Scene event hooks: undo/redo, key edits and time changes refresh the widget."""

    #: Above this many banked edits the burst is a bake / import, not a keying
    #: gesture: probing each would cost more than the rebuild it feeds, and the
    #: refresh falls back to the selection instead.
    _EDITED_CAP = 400

    #: The host's scene watcher, made by :meth:`_register_scene_callbacks`.
    _scene_watch = None

    #: The single-shot plain rebuild (:meth:`_arm_rebuild_debounce`).
    _rebuild_debounce = None

    def _register_scene_callbacks(self) -> None:
        """(Re-)attach the undo/redo redraw and the host's scene watcher.

        Undo and redo are the STORE's to follow -- applying the restore point
        of the shot edit it took back -- with this panel open or not
        (``ShotStore.follow_native_step``, subscribed by ``ShotStore.active()``);
        when this listener applied it, an edit made with no Sequencer this
        session was undone in its keys and kept in its shots.  The panel only
        hears that the store did (:meth:`_on_native_step`).

        Idempotent: a second call re-attaches whatever hooks the host lost with
        the scene (``watch.refresh()``; Blender clears its non-persistent app
        handlers on File > New / Open) instead of stacking a second watcher.
        """
        self._store_cls().add_native_step_listener(self._on_native_step)
        if self._scene_watch is not None:
            self._scene_watch.refresh()
            return
        self._scene_watch = self.host.watch_scene(
            busy=lambda: self._syncing,
            on_keys_edited=self._on_keys_edited,
            on_time_changed=self._on_time_changed,
            on_scene_changed=self._on_scene_changed,
            cap=self._EDITED_CAP,
        )

    def remove_callbacks(self) -> None:
        """Detach every scene hook and store listener (call on teardown).

        Idempotent: a slots re-init tears the previous controller down and its
        ``ui.destroyed`` hook may still call this later.
        """
        self._unbind_store_listener()
        store_cls = self._store_cls()
        try:
            store_cls.remove_invalidation_listener(self._on_store_invalidated)
        except Exception:
            self.logger.debug("invalidation listener removal failed", exc_info=True)
        store_cls.remove_native_step_listener(self._on_native_step)
        if self._scene_watch is not None:
            self._scene_watch.remove()
            self._scene_watch = None
        self._edited_items.clear()
        for attr in ("_keyframe_debounce", "_rebuild_debounce"):
            timer = getattr(self, attr, None)
            if timer is not None:
                try:
                    timer.stop()
                except RuntimeError:
                    pass  # timer's C++ object died with the closing panel
                setattr(self, attr, None)

    # ---- undo/redo: the store follows, the panel redraws ------------------

    def _on_native_step(self, event) -> None:
        """The store followed a host undo or redo: redraw once.

        In Maya only when it put a shot edit's restore point back
        (``event.applied``): Maya fires its Undo/Redo for every undo in the
        session, and an unrelated one's keys reach the panel through the
        key-edit hook.  A host with no such per-key report (Blender) redraws
        after every step, which also carries the rename reconcile an undo can
        need (``SequencerHost.REDRAW_EVERY_NATIVE_STEP``).  The store's own
        events during the restore are skipped (:meth:`_on_store_event`), so a
        Ctrl+Z is one rebuild -- and this one also refreshes the dropdown,
        which lists the shots in order and paints their bounds: an undone
        reorder left it showing the order that had just been undone.  Only for
        the store this panel shows: a panel left behind by a scene swap or a
        module reload must not redraw for it.
        """
        if self._syncing:
            return
        if not event.applied and not self.host.REDRAW_EVERY_NATIVE_STEP:
            return
        if event.store is not getattr(self._sequencer, "store", None):
            return
        self._after_shot_change()

    # ---- key edits: a debounced refresh ------------------------------------

    def _on_keys_edited(self, items=()) -> None:
        """The host reported key edits: bank what it named and (re)arm the
        debounced refresh.

        *items* are the host's own handles of what changed (Maya's animCurve
        names, Blender's object names), resolved to new shot members by the
        host at refresh time (:meth:`_auto_add_keyed_objects`).  The host
        watcher already skipped playback, transient edits
        (``ShotStore.transient_edit``: an export or a bridge send, which puts
        the scene back) and this panel's own edits.  Past the cap nothing more
        is banked: the burst is a bake or an import.
        """
        if self._syncing:
            return
        if len(self._edited_items) <= self._EDITED_CAP:
            self._edited_items.update(items)
        self._arm_keyframe_debounce()

    def _arm_keyframe_debounce(self) -> None:
        """(Re)start the 200 ms single-shot refresh, built on first use.

        A debounce coalesces rapid bursts (e.g. keying 10 attributes at once)
        into a single refresh.
        """
        if self._keyframe_debounce is None:
            self._keyframe_debounce = QtCore.QTimer()
            self._keyframe_debounce.setSingleShot(True)
            self._keyframe_debounce.setInterval(200)
            self._keyframe_debounce.timeout.connect(self._on_keyframe_debounce_fire)
        self._keyframe_debounce.start()

    def _on_keyframe_debounce_fire(self) -> None:
        """Perform the actual refresh after the debounce window.

        Only evicts the active shot from the segment cache so that
        non-active shots (adjacent/all view modes) keep their cached
        segments.  The active shot is always re-queried by
        ``collect_segments`` anyway.

        If the keyframe was set on an object not yet in the active shot,
        the object is auto-added to the shot's object list.
        """
        if self._syncing:
            return
        # Only invalidate the active shot — collect_segments always
        # re-queries it, and non-active shots don't need re-collection.
        active_id = self.active_shot_id
        # Audio keys can be edited (e.g. dragging an audio clip) — the
        # cached segments must drop so the next rebuild re-discovers.
        # A keyframe edit can also reveal newly-keyed objects, requiring
        # DAG-path reconciliation on the next rebuild.
        self._audio_segments_cache = None
        self._reconcile_needed = True
        if active_id is not None:
            self._segment_cache.pop(active_id, None)
            self._sub_row_cache = {
                k: v for k, v in self._sub_row_cache.items() if k[0] != active_id
            }
            added = self._auto_add_keyed_objects(active_id)
            # Grow the shot over anything that landed outside it, if the
            # option is on.  After the membership pass: a freshly keyed object
            # has to be IN the shot before its keys count as the shot's.
            if self._auto_extend_to_new_keys(active_id):
                return  # it rebuilt already
        else:
            self._segment_cache.clear()
            self._sub_row_cache.clear()
            # Nothing to attribute the edits to — drop them rather than let
            # them join whichever shot is active next.
            self._edited_items.clear()
            added = False
        if not added:
            self._sync_to_widget()

    def _auto_add_keyed_objects(self, shot_id: int) -> bool:
        """Add newly-keyed objects to the active shot's object list.

        Candidates come from what the host reported as edited since the last
        refresh (:meth:`_on_keys_edited`), falling back to the current
        selection when it banked nothing -- keying through a path that reports
        no edit still gets picked up -- or when a bulk edit overran the cap.

        A candidate qualifies on "has a key in the shot's range on a content
        channel" (transforms, visibility, or a render-effect channel such as a
        highlight pulse), and deliberately NOT on its values varying: an
        object keyed on a hold inside the shot -- or keyed for the first time
        -- is still the shot's content, and leaving it out of
        ``shot.objects`` both hid it from the panel and stranded its keys when
        the shot moved.  The host decides (``SequencerHost.newly_keyed_members``).

        Returns ``True`` if objects were added (triggering a store event and
        widget sync), ``False`` otherwise.
        """
        if self.sequencer is None:
            return False
        shot = self.sequencer.shot_by_id(shot_id)
        if shot is None:
            return False
        banked = (
            set(self._edited_items)
            if len(self._edited_items) <= self._EDITED_CAP
            else set()
        )
        self._edited_items.clear()
        new_objects = self.host.newly_keyed_members(banked, shot, self.sequencer)
        if not new_objects:
            return False
        # The system's own addition, not a hand edit: the manifest's
        # edited_by_hand reads past it (ShotStore.SYSTEM_MEMBERS).
        self.sequencer.store.add_system_members(shot_id, new_objects)
        return True

    # ---- time changes: the playhead follows ----------------------------------

    def _on_time_changed(self, frame: float) -> None:
        """Move the widget playhead to the scene's new time.

        Not while the panel itself moves the scene's time
        (:meth:`on_playhead_moved`): the widget is already there.
        """
        if self._syncing_playhead:
            return
        widget = self._get_sequencer_widget()
        if widget is None:
            return
        widget.set_playhead(frame)

    # ---- scene changes that key nothing: a plain rebuild ------------------

    def _on_scene_changed(self) -> None:
        """The scene changed in a way the panel draws but that keys nothing --
        an object renamed, a sound strip moved, trimmed, added or removed
        outside the panel: re-point the shots and redraw on a plain
        (debounced) rebuild (:meth:`_arm_rebuild_debounce`).

        Not the keyframe debounce: its epilogue adds keyed objects to the
        active shot, falling back to the SELECTION when nothing was keyed --
        and these key nothing, so riding it put whatever was selected into the
        shot (and let Extend to Keys grow it), outside any undo step.
        """
        self._reconcile_needed = True
        self._audio_segments_cache = None
        try:
            self._arm_rebuild_debounce()
        except Exception:
            self.logger.debug("scene-change refresh not scheduled", exc_info=True)

    def _arm_rebuild_debounce(self) -> None:
        """(Re)start a 200 ms single-shot rebuild with NO keying epilogue,
        built on first use."""
        if self._rebuild_debounce is None:
            self._rebuild_debounce = QtCore.QTimer()
            self._rebuild_debounce.setSingleShot(True)
            self._rebuild_debounce.setInterval(200)
            self._rebuild_debounce.timeout.connect(self._on_rebuild_debounce_fire)
        self._rebuild_debounce.start()

    def _on_rebuild_debounce_fire(self) -> None:
        """Rebuild the widget from the scene -- membership is left as it is."""
        if self._syncing:
            return
        self._segment_cache.clear()
        self._sub_row_cache.clear()
        self._sync_to_widget()
