# !/usr/bin/python
# coding=utf-8
"""The Shot Sequencer panel's controller: :class:`ShotSequencerController`.

Bridges uitk's generic ``SequencerWidget`` to the host's ``ShotSequencer``
engine. One copy for both hosts: every host call goes through :attr:`host`, the
host library's ``SequencerHost`` (from ``Slots.tk``), and the engine and store
classes are the host's ``ShotSequencer`` and its ``STORE_CLASS``. This module
holds the controller's own state -- construction, the footer, the active-store
binding and the active shot -- and composes the interaction handlers from the
concept mixins beside it:

- ``scene_callbacks`` -- the host's undo/redo, key-edit and time-change events.
- ``undo_ledger`` -- the shot-boundary snapshots undo/redo step through.
- ``shot_lane`` -- the shot lane's context menu and shot structure edits.
- ``shot_layer`` -- the shots ON the widget: the lane, the gaps (a layer).
- ``clip_menu`` -- clip context menus, Move / Copy to Shot, clip-key delete / stash.
- ``key_menu`` -- key context menus, tangent edits and drags, key edits.
- ``widget_sync`` -- rebuilding the widget: tracks, clips, sub-rows, colours.
- ``scene_selection`` -- tracks and the scene selection / Graph Editor sync.
- ``transport`` -- playhead, audio scrub and the transport row.
- ``gap_manager`` / ``clip_motion`` / ``shot_nav`` / ``marker_manager`` --
  gaps, clip drags, shot navigation and markers.

The panel's Switchboard slots (:class:`~tentacle.slots.tools.shot_sequencer.ShotSequencerSlots`)
build this class.
"""

from typing import Optional

import pythontk as ptk
from pythontk import ActiveShotChanged, ShotsEdited, StoreEvent

from .clip_menu import ClipMenuMixin
from .clip_motion import ClipMotionMixin
from .gap_manager import GapManagerMixin
from .key_menu import KeyMenuMixin
from .marker_manager import MarkerManagerMixin
from .scene_callbacks import SceneCallbacksMixin
from .scene_selection import SceneSelectionMixin
from .shot_lane import ShotLaneMixin
from .shot_layer import ShotLayer
from .shot_nav import ShotNavMixin
from .transport import TransportMixin
from .undo_ledger import UndoLedgerMixin
from .widget_sync import WidgetSyncMixin


class ShotSequencerController(
    SceneCallbacksMixin,
    UndoLedgerMixin,
    ShotLaneMixin,
    ClipMenuMixin,
    KeyMenuMixin,
    WidgetSyncMixin,
    SceneSelectionMixin,
    TransportMixin,
    GapManagerMixin,
    ClipMotionMixin,
    ShotNavMixin,
    MarkerManagerMixin,
    ptk.LoggingMixin,
):
    """Business logic controller bridging SequencerWidget ↔ ShotSequencer."""

    #: The host library (``mtk`` / ``btk``) the panel reaches the scene
    #: through; set from the slots in ``__init__``.  A class default so a
    #: controller built bare (``__new__``, as tests do) reads ``None`` until
    #: one is given.
    tk = None

    #: Frames the context-menu padding prompt opens on.  A beat of room is
    #: what the gesture is usually for; the prompt then remembers whatever
    #: the user actually typed for the rest of the session.
    CONTEXT_SPACE_FRAMES = 15.0

    #: How far past a bound the "Extend to Keys" option reaches, in frames.
    #: ``ANY_REACH`` (-1) means any distance -- a key set anywhere outside
    #: the shot is claimed, as long as it is not inside a neighbouring one.
    EXTEND_REACH_FRAMES = 24.0

    ANY_REACH = -1.0

    #: The shot combobox's cells (``uitk.ComboBox.set_cells``): one row per
    #: shot reads name / start / end / description, and double-clicking it
    #: edits those in place -- the Shots window's fields without the window.
    SHOT_CELLS = (
        {"key": "name", "label": "Name"},
        {"key": "start", "label": "Start", "kind": "int", "format": "{:.0f}"},
        {"key": "end", "label": "End", "kind": "int", "format": "{:.0f}"},
        {"key": "description", "label": "Description"},
    )

    SHOT_CELL_FORMAT = "{name}  [{start:.0f}-{end:.0f}]  {description}"

    def __init__(self, slots_instance, log_level="WARNING"):
        super().__init__()
        self.set_log_level(log_level)
        self.sb = slots_instance.sb
        self.ui = slots_instance.ui
        self.tk = slots_instance.tk
        self._sequencer = None
        # The host's scene watcher (``SequencerHost.watch_scene``): key edits,
        # time changes and the scene changes a rebuild follows.
        self._scene_watch = None
        self._keyframe_debounce = None
        # A plain rebuild with no keying epilogue (a rename, a sound strip
        # edited outside the panel).
        self._rebuild_debounce = None
        # What the host reported as keyed since the last refresh (Maya's
        # animCurve names, Blender's object names): lets the debounced
        # refresh add exactly the objects the user just keyed -- scripted or
        # channel-pinned keying on UNSELECTED objects included -- instead of
        # guessing from the current selection.  Opaque to the panel; the host
        # resolves them (``SequencerHost.newly_keyed_members``).
        self._edited_items: set = set()
        self._syncing = False
        self._syncing_playhead = False
        self._store_listener_bound = False
        self._shot_display_mode: str = "current"  # "current" | "adjacent" | "all"
        self._segment_cache: dict = {}  # shot_id → segments list
        self._sub_row_cache: dict = {}  # (shot_id, track_name) → sub-row data
        self._color_map_cache: Optional[dict] = None  # persisted attribute color map
        self._audio_segments_cache: Optional[tuple] = None  # (range_key, segments)
        self._reconcile_needed: bool = True  # gated by DAG/store events
        self._shifted_out_keys: dict = {}  # obj_name → {time, …} shift-moved out
        # Last amount the padding prompt was answered with — padding a run of
        # shots by the same beat is the common case, so the field opens on it.
        self._context_space_frames: float = self.CONTEXT_SPACE_FRAMES
        # Global "grow the current shot over keys set just outside it".  Off
        # by default: it moves a bound the user did not touch, so it is opted
        # into, and _extend_reach caps how far out a new key may sit and
        # still count (ANY_REACH = no cap).
        self._extend_to_keys: bool = False
        # Global "a shot change puts the playhead on the shot's first frame"
        # (header menu; on by default -- the shot changed to is the one about
        # to be worked in).
        self._playhead_to_shot_start: bool = True
        # Move / Copy to Shot's toggle: a pick copies while it is on.  Held
        # for the session, so a run of copies is one toggle.
        self._copy_to_shot: bool = False
        self._extend_reach: float = self.EXTEND_REACH_FRAMES
        self._prev_action = None  # OptionBox action for prev shot
        self._next_action = None  # OptionBox action for next shot
        self._view_mode_action = None  # OptionBox action for view mode cycle
        self._cmb_mode_widget = None  # mode selector combobox (Shots/Markers)
        self._playback_range_mode: str = (
            "follows_view"  # "off" | "follows_view" | "locked"
        )
        self._track_order_scope: str = "visible"  # "visible" | "global"
        self._show_internal_holds: bool = (
            False  # show flat-key spans in attribute sub-rows
        )
        self._cmb_mode: str = "shots"  # "shots" or "markers"
        self._transport_controls = None

        self._register_scene_callbacks()
        self._bind_store_listener()
        self._bind_invalidation_listener()
        # Tear down on panel close.  Without this every hook above outlives
        # the panel -- the time-change hook fires on every frame of playback
        # against destroyed widgets -- and they accumulate across reopens.
        # remove_callbacks also unbinds the store listener and stops the
        # debounce timers.
        self.ui.destroyed.connect(lambda *_: self.remove_callbacks())
        self.logger.debug("ShotSequencerController initialized.")

    # ---- the host ----------------------------------------------------------

    @property
    def host(self):
        """The host library's ``SequencerHost``: every scene call the panel
        makes goes through it."""
        return self.tk.SequencerHost

    def _sequencer_cls(self):
        """The host's ``ShotSequencer`` (Maya's, Blender's)."""
        return self.tk.ShotSequencer

    def _store_cls(self):
        """The host's store class: the ``STORE_CLASS`` of its ``ShotSequencer``
        (Maya's ``ShotStore``, Blender's ``BlenderShotStore``)."""
        return self._sequencer_cls().STORE_CLASS

    # ---- footer helpers --------------------------------------------------

    def _set_footer(self, text: str, *, color: str = "") -> None:
        """Set the window footer text with an optional foreground color."""
        footer = getattr(self.ui, "footer", None)
        if footer is None:
            return
        label = footer._status_label
        if color:
            label.setStyleSheet(
                f"background: transparent; border: none; color: {color};"
            )
        else:
            label.setStyleSheet("background: transparent; border: none;")
        footer.setText(text)

    def _update_footer_shot_summary(self) -> None:
        """Update the footer with a summary of the active shot."""
        if self.sequencer is None:
            self._set_footer("No shots defined.")
            return
        shot_id = self.active_shot_id
        shot = self.sequencer.shot_by_id(shot_id) if shot_id is not None else None
        if shot is None:
            self._set_footer("No shot selected.")
            return
        dur = int(shot.end - shot.start)
        n_obj = len(shot.objects)
        n_shots = len(self.sequencer.shots)
        idx = next(
            (
                i
                for i, s in enumerate(self.sequencer.sorted_shots())
                if s.shot_id == shot_id
            ),
            0,
        )
        parts = [
            f"[{idx + 1}/{n_shots}]",
            f"{dur}f",
            f"{n_obj} object{'s' if n_obj != 1 else ''}",
        ]
        self._set_footer(" · ".join(parts))

    # ---- sequencer property (lazy init from the active store) -------------

    @property
    def sequencer(self):
        """Return the host's ShotSequencer, lazily created over the active store."""
        if self._sequencer is None:
            store = self._store_cls().active()
            self._sequencer = self._sequencer_cls()(store=store)
            self.logger.debug("Lazy-initialized ShotSequencer from the active store.")
        return self._sequencer

    @sequencer.setter
    def sequencer(self, value) -> None:
        self._sequencer = value

    # ---- store observers -------------------------------------------------

    def _bind_store_listener(self) -> None:
        """Register as a listener on the active store."""
        if self._store_listener_bound:
            return
        try:
            store = self._store_cls().active()
            store.add_listener(self._on_store_event)
            self._bound_store = store
            self._store_listener_bound = True
        except Exception:
            # A failed bind means the panel silently stops reacting to
            # external shot changes — leave a trace.
            self.logger.warning("store listener bind failed", exc_info=True)

    def _unbind_store_listener(self) -> None:
        """Remove the store listener."""
        if not self._store_listener_bound:
            return
        try:
            store = getattr(self, "_bound_store", None)
            if store is not None:
                store.remove_listener(self._on_store_event)
                self._bound_store = None
        except Exception:
            self.logger.debug("store listener unbind failed", exc_info=True)
        self._store_listener_bound = False

    def _bind_invalidation_listener(self) -> None:
        """Track active-store swaps (scene new/open).

        Without this the controller keeps its lazily-cached sequencer
        and event listener bound to the store of the *previous* scene —
        edits go to a dead store and external changes stop refreshing
        the panel.
        """
        self._store_cls().add_invalidation_listener(self._on_store_invalidated)

    def _on_store_invalidated(self, event=None) -> None:
        """Rebind to the new active store after a scene swap."""
        self._unbind_store_listener()
        self._sequencer = None
        self._drop_caches()
        # Cross-scene state must not survive the swap.  The boundary
        # ledger needs no clearing here — it lives on the STORE, so the new
        # scene's store starts with a fresh one and the old scene's dies
        # with its store.
        self._shifted_out_keys.clear()
        self._edited_items.clear()
        self._bind_store_listener()
        # A host that drops its scene hooks with the scene (Blender clears its
        # non-persistent app handlers on File > New / Open) gets them back
        # here; otherwise the live playhead / keyframe refresh would be dead
        # for the rest of the session.  Idempotent.
        self._register_scene_callbacks()
        # Combobox first: _sync_to_widget resolves active_shot_id through
        # the combobox, which still holds the PREVIOUS scene's shot ids
        # until repopulated.
        self._sync_combobox()
        self._sync_to_widget()
        if self._cmb_mode == "markers":
            # Markers mode populates the combobox from the WIDGET's
            # marker items, which only _sync_to_widget rebuilds — re-sync
            # so the list shows the new scene's markers, not the old.
            self._sync_combobox()

    def _on_store_event(self, event: StoreEvent) -> None:
        """React to store mutations from any source (e.g. manifest build)."""
        if self._syncing or self.sequencer is None:
            return
        if isinstance(event, ShotsEdited):
            # An edit's own announcement (``scene_edit``), for the panels that
            # did not make it.  This one redraws after each of its own edits,
            # and another panel's reaches it through the events that edit
            # raises: rebuilding here too drew every sequencer edit twice.
            return
        if getattr(self.sequencer.store, "following_native_step", False) is True:
            # The store putting back a restore point for the host's own undo:
            # _on_native_step redraws once when it is done.
            return
        self._drop_caches()
        if (
            isinstance(event, ActiveShotChanged)
            and event.shot_id is not None
            and event.previous is not None
        ):
            # A shot picked in another panel -- the Shots window, the
            # manifest's Open in Shot Sequencer -- is a shot change too.  One
            # that only fills an empty slot is not: the Shots window selects
            # the first shot once the active one is deleted.
            shot = self.sequencer.shot_by_id(event.shot_id)
            if shot is not None:
                self._land_on_shot(shot)
        # Refresh combobox and widget when shots change externally
        self._sync_combobox()
        self._sync_to_widget()
        # The store's event, through the widget's generic bridge
        widget = self._get_sequencer_widget()
        if widget is not None and hasattr(widget, "app_event"):
            widget.app_event.emit(event.name, event)

    # ---- widget ↔ engine sync -------------------------------------------

    @property
    def active_shot_id(self) -> Optional[int]:
        """Return the shot_id currently selected, or the first shot's id."""
        # In markers mode the combobox itemData holds marker TIMES
        # (floats), not shot ids — reading it would return a bogus id
        # and silently break shot resolution downstream.
        cmb = getattr(self.ui, "cmb_shot", None)
        if self._cmb_mode != "markers" and cmb is not None and cmb.currentIndex() >= 0:
            sid = cmb.itemData(cmb.currentIndex())
            if sid is not None:
                return sid
        if self.sequencer and self.sequencer.shots:
            # The store's active shot (set by shot selection here or in
            # the Shots settings panel) wins over the first-shot
            # fallback — in markers mode the combobox can't provide it,
            # and defaulting to the first shot retargets the view away
            # from the shot being worked on after every store event.
            store_active = self.sequencer.store.active_shot_id
            if store_active is not None and self.sequencer.shot_by_id(store_active):
                return store_active
            # Nothing selected yet (the panel just opened, or markers mode):
            # the shot under the playhead is the one being worked on, and the
            # one the first framing should show.  The first shot stands in
            # only when the playhead sits outside every shot.
            under_playhead = self._shot_at_current_time()
            if under_playhead is not None:
                return under_playhead.shot_id
            return self.sequencer.sorted_shots()[0].shot_id
        return None

    def _current_time(self) -> Optional[float]:
        """The playhead's frame, or ``None`` when there is no scene to ask."""
        try:
            return self.host.current_time()
        except Exception:
            return None

    def _shot_at_current_time(self):
        """The shot the playhead is in, or ``None``."""
        now = self._current_time()
        if now is None or self.sequencer is None:
            return None
        return self._find_shot_at_time(now)

    def _get_sequencer_widget(self):
        """Return the promoted SequencerWidget, or ``None``.

        ``None`` too while the ``.ui`` still holds the placeholder (a load
        outside the panel's own handler, before promotion): only the real
        widget has ``add_track``.
        """
        w = getattr(self.ui, "sequencer_widget", None)
        if w is not None and hasattr(w, "add_track"):
            return w
        return None

    def _shot_layer(self, widget=None):
        """The shots on the sequencer widget -- the lane, the gaps
        (:class:`~.shot_layer.ShotLayer`) -- added on first use; ``None``
        without a widget."""
        if widget is None:
            widget = self._get_sequencer_widget()
        if widget is None:
            return None
        return ShotLayer.of(widget, getattr(self, "sb", None))
