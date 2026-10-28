# !/usr/bin/python
# coding=utf-8
"""Shot Sequencer: the scene's shots on a timeline -- objects as tracks, keys as
clips, rows or curves -- with ripple edits.

One Slots class for both hosts: the ``.ui``'s widgets and the header menu routed
to the controller (:class:`~tentacle.slots.tools._shot_sequencer.controller.ShotSequencerController`),
which reaches the scene through the host library's ``SequencerHost``
(``self.tk``). The shots on uitk's generic timeline -- the shot lane, the gaps
-- are the panel's own layer on it
(:class:`~tentacle.slots.tools._shot_sequencer.shot_layer.ShotLayer`). The
shots engine is pythontk's; each host's ``ShotSequencer``, store and
graph-editor half (``GraphSync``) are its library's.
"""

import pythontk as ptk
from qtpy import QtCore

from tentacle import Slots
from ._shot_sequencer.controller import ShotSequencerController
from ._shot_sequencer.shot_edit_dialog import ShotEditDialog
from ._shot_sequencer.shot_layer import ShotLayer

# Arrow-key labels for the help's key list, kept out of the f-strings that use
# them (a backslash inside an f-string expression is a SyntaxError before 3.12).
_KB_LEFT = "←"
_KB_RIGHT = "→"

#: Where the window keeps its live controller, so a slots re-init over the same
#: loaded window tears the previous one down first.
_CONTROLLER_ATTR = "_shot_seq_controller"


class ShotSequencerSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for the ``shot_sequencer.ui`` panel."""

    #: The header-menu rows this panel builds at runtime (``header_init``) and
    #: the slots below answer to. No ``.ui`` declares them; saved settings key on
    #: these names, so they never change.
    RUNTIME_WIDGETS = (
        "spn_snap",
        "chk_snap_to_keys",
        "chk_extend_to_keys",
        "spn_extend_reach",
        "cmb_shortcut_overlay",
        "cmb_playback_range",
        "cmb_track_order",
        "chk_select_on_load",
        "chk_frame_on_shot_change",
        "chk_playhead_to_shot_start",
        "btn_colors",
        "btn_shortcuts",
        "btn_shot_settings",
    )

    #: (widget signal, controller slot) -- the sequencer widget's signals and the
    #: controller methods that answer them.
    _WIRING = (
        ("clip_resized", "on_clip_resized"),
        ("clips_batch_resized", "on_clips_batch_resized"),
        ("clip_moved", "on_clip_moved"),
        ("clips_batch_moved", "on_clips_batch_moved"),
        ("clip_renamed", "on_clip_renamed"),
        ("playhead_moved", "on_playhead_moved"),
        ("track_hidden", "hide_track"),
        ("track_shown", "show_track"),
        ("track_deleted", "delete_track"),
        ("selection_changed", "on_selection_changed"),
        ("track_selected", "on_track_selected"),
        ("sub_track_selected", "on_sub_track_selected"),
        ("track_menu_requested", "on_track_menu"),
        ("clip_locked", "on_clip_locked"),
        ("undo_requested", "on_undo"),
        ("redo_requested", "on_redo"),
        ("marker_added", "on_marker_added"),
        ("marker_moved", "on_marker_moved"),
        ("marker_changed", "on_marker_changed"),
        ("marker_removed", "on_marker_removed"),
        ("clip_menu_requested", "on_clip_menu"),
        ("range_highlight_changed", "on_range_highlight_changed"),
        ("zone_context_menu_requested", "on_zone_context_menu"),
        ("header_menu_requested", "on_header_menu"),
        ("keys_moved", "on_keys_moved"),
        ("keys_batch_moved", "on_keys_batch_moved"),
        ("keys_deleted", "on_keys_deleted"),
        ("key_selection_changed", "on_key_selection_changed"),
        ("key_menu_requested", "on_key_menu"),
        ("keys_tangent_dragged", "on_keys_tangent_dragged"),
        ("editor_changed", "_on_editor_changed"),
    )

    #: (layer signal, controller slot) -- the shot layer's
    #: (:class:`~tentacle.slots.tools._shot_sequencer.shot_layer.ShotLayer`):
    #: the gaps' drags, locks and menu, and Ctrl+Shift+Click's shot switch.
    _LAYER_WIRING = (
        ("gap_resized", "on_gap_resized"),
        ("gap_left_resized", "on_gap_left_resized"),
        ("gap_moved", "on_gap_moved"),
        ("gap_lock_changed", "on_gap_lock_changed"),
        ("gap_lock_all_requested", "on_gap_lock_all"),
        ("gap_unlock_all_requested", "on_gap_unlock_all"),
        ("gap_menu_requested", "on_gap_menu"),
        ("shot_switch_requested", "_on_shot_switch_requested"),
    )

    #: The scope button's states (``cmb_shot``'s option box) -> display mode.
    _VIEW_MODE_MAP = {0: "current", 1: "adjacent", 2: "all"}

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.shot_sequencer

        # The shot dropdown mirrors the scene's shots (repopulated by
        # _sync_combobox each sync), never a persisted UI value -- opt out of
        # cross-session index restore, or a stale index auto-selects (and
        # fires cmb_shot on) the wrong shot next session. Mirrors the Shots
        # panel's cmb_shot_select opt-out.
        cmb_shot = getattr(self.ui, "cmb_shot", None)
        if cmb_shot is not None:
            cmb_shot.restore_state = False

        # A slots re-init over the same still-alive loaded UI does NOT destroy
        # self.ui, so the previous controller's remove_callbacks() (wired only
        # to ui.destroyed) never runs -- its scene hooks, store listener and
        # the class-global invalidation listener would accumulate one per
        # reopen (bound methods of distinct instances never dedupe), leaving
        # orphaned controllers that rebuild the widget N times per event.
        # remove_callbacks() is idempotent, so the old controller's
        # still-connected ui.destroyed hook stays harmless.
        prev_controller = getattr(self.ui, _CONTROLLER_ATTR, None)
        if prev_controller is not None:
            try:
                prev_controller.remove_callbacks()
            except Exception:
                self.logger.debug("prev controller teardown failed", exc_info=True)
        self.controller = ShotSequencerController(self)
        setattr(self.ui, _CONTROLLER_ATTR, self.controller)

        # The SequencerWidget is promoted in the .ui; loaded outside the
        # panel's own handler (deferred promotion) it may still be the
        # placeholder, and the controller reports no widget.
        sequencer = self.controller._get_sequencer_widget()
        if sequencer is not None:
            sequencer.window_shortcuts = True
            self._wire(sequencer)
            # The shots on the timeline: the lane and the gaps, a layer of the
            # panel's own on uitk's generic widget.  Added before the graph
            # half is built, so the graph's page opens below the lane.
            self._wire(ShotLayer.of(sequencer, self.sb), self._LAYER_WIRING)
            # Right-clicks reach on_zone_context_menu (the shot-lane menu)
            # instead of the widget's built-in default menu.
            sequencer.zone_menu_enabled = True
            self._bind_shortcuts(sequencer)
            # The graph editor's feed and commits (the host's GraphSync),
            # rebuilt with the controller; the previous one is detached first,
            # as the wiring is.
            prev_graph = getattr(sequencer, "_graph_sync", None)
            if prev_graph is not None:
                prev_graph.detach()
            self.graph_sync = self.tk.SequencerHost.graph_sync_cls()(
                self.controller, sequencer
            )
            sequencer._graph_sync = self.graph_sync
            self._register_track_options(sequencer)
        self._setup_shot_nav()
        self.controller._setup_transport_controls()

        # Initial population so gaps and clips are visible immediately.
        self.controller._sync_combobox()
        self.controller._sync_to_widget()

    def _wire(self, source, wiring=None) -> None:
        """Connect *source*'s signals to the controller (*wiring*: the
        widget's :attr:`_WIRING` by default, the shot layer's
        :attr:`_LAYER_WIRING`).

        The live connections are recorded on the source, so a slots re-init
        over the same loaded UI disconnects the PREVIOUS controller first --
        without this both controllers stay connected and every signal
        double-fires (two undos per Ctrl+Z, duplicate markers, ...).
        """
        for sig_name, slot in getattr(source, "_slots_connections", []):
            try:
                getattr(source, sig_name).disconnect(slot)
            except (RuntimeError, TypeError):
                pass  # the connection died with the old controller
        connections = []
        for sig_name, slot_name in self._WIRING if wiring is None else wiring:
            # Guarded on both sides: a uitk that predates a signal degrades
            # that one connection, not the whole panel -- but never silently.
            signal = getattr(source, sig_name, None)
            slot = getattr(self.controller, slot_name, None)
            if signal is None or slot is None:
                self.logger.warning(
                    "sequencer wiring skipped: %s -> %s (signal or slot "
                    "missing - uitk version mismatch?)",
                    sig_name,
                    slot_name,
                )
                continue
            signal.connect(slot)
            connections.append((sig_name, slot))
        source._slots_connections = connections

    def _bind_shortcuts(self, sequencer) -> None:
        """The panel's own key bindings.

        ``add_shortcut`` disposes and replaces a same-sequence binding, so a
        slots re-init re-points them at the new controller instead of stacking
        a second one. Window context: Qt claims the key at the window level
        and the host never sees it -- which is also why the panel binds these
        itself, the host's own hotkeys never reaching a focused Qt tool window.
        """
        context = (
            QtCore.Qt.WindowShortcut
            if sequencer.window_shortcuts
            else QtCore.Qt.WidgetWithChildrenShortcut
        )
        for key, action, desc in (
            (
                "Delete",
                self.controller._delete_selected_clip_keys,
                "Delete keys for selected clips",
            ),
            ("Ctrl+C", self.controller._copy_keys_shortcut, "Copy the selected keys"),
            (
                "Ctrl+V",
                self.controller._paste_keys_shortcut,
                "Paste copied keys at the playhead",
            ),
        ):
            sequencer.shortcut_manager.add_shortcut(key, action, desc, context)

    def _setup_shot_nav(self) -> None:
        """The shot dropdown's option box: previous / next, New Shot, the
        scope and view buttons, its context menu and the Shots / Markers mode.

        Every callback is late-bound through ``cmb._nav_controller`` /
        ``cmb._nav_slots``, so a slots re-init over the same loaded UI only
        re-points those attributes -- the option-box actions and menu connects
        are created exactly once and never duplicated.
        """
        cmb = getattr(self.ui, "cmb_shot", None)
        if cmb is None or not hasattr(cmb, "option_box"):
            return

        cmb._nav_controller = self.controller
        cmb._nav_slots = self
        # Before the re-init early return: the cells are the controller's
        # (a fresh one on every re-init), the option boxes are the widget's.
        self.controller._configure_shot_combobox(cmb)

        ctl = self.controller
        existing = getattr(cmb, "_shot_nav_options", None)
        if existing is not None:
            # Re-init: adopt the already-built options for this controller.
            ctl._prev_action = existing["prev"]
            ctl._next_action = existing["next"]
            ctl._view_mode_action = existing["view"]
            views_opt = existing.get("views")
            if views_opt is not None:
                ctl._view = ctl.VIEWS[views_opt.current_state][0]
            ctl._shot_display_mode = self._VIEW_MODE_MAP.get(
                existing["view"].current_state, "current"
            )
            ctl._cmb_mode_widget = getattr(self.ui, "cmb_mode", None)
            return

        ActionOption = self.sb.ActionOption
        prev_opt = ActionOption(
            wrapped_widget=cmb,
            callback=lambda: cmb._nav_controller._navigate_shot(-1),
            icon="chevron_left",
            tooltip="Previous Shot",
            order=0,
        )
        next_opt = ActionOption(
            wrapped_widget=cmb,
            callback=lambda: cmb._nav_controller._navigate_shot(1),
            icon="chevron_right",
            tooltip="Next Shot",
            order=1,
        )
        # "+": one-click shot creation.
        add_opt = ActionOption(
            wrapped_widget=cmb,
            callback=lambda: cmb._nav_controller._create_shot_one_click(),
            icon="add",
            tooltip="New Shot",
            order=2,
        )
        # The scope cycle: Current -> Adjacent -> All.
        view_opt = ActionOption(
            wrapped_widget=cmb,
            states=[
                {
                    "icon": "target",
                    "tooltip": "Scope: Current Shot (click for adjacent)",
                    "callback": lambda: cmb._nav_controller._set_view_mode("adjacent"),
                },
                {
                    "icon": "columns",
                    "tooltip": "Scope: Adjacent Shots (click for all)",
                    "callback": lambda: cmb._nav_controller._set_view_mode("all"),
                },
                {
                    "icon": "grid",
                    "tooltip": "Scope: All Shots (click for current)",
                    "callback": lambda: cmb._nav_controller._set_view_mode("current"),
                },
            ],
            order=4,
        )
        # The view cycle beside the scope: Standard -> Compact -> Graph.
        views_opt = self._view_option(cmb)

        cmb.option_box.set_order(["action"])
        for opt in (prev_opt, next_opt, add_opt, view_opt, views_opt):
            cmb.option_box.add_option(opt)
        # Shown once, here: the button's persisted state is the view.
        ctl._set_view(ctl.VIEWS[views_opt.current_state][0])

        ctl._prev_action = prev_opt
        ctl._next_action = next_opt
        ctl._view_mode_action = view_opt
        # The display mode follows the scope button's persisted state.
        ctl._shot_display_mode = self._VIEW_MODE_MAP.get(
            view_opt.current_state, "current"
        )
        cmb._shot_nav_options = {
            "prev": prev_opt,
            "next": next_opt,
            "add": add_opt,
            "view": view_opt,
            "views": views_opt,
        }

        cmb.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        cmb.customContextMenuRequested.connect(
            lambda pos: cmb._nav_slots._cmb_context_menu(pos)
        )

        # The mode selector (Shots / Markers): connected once, late-bound
        # through ``cmb._nav_slots`` like every other nav callback, so a slots
        # re-init re-points it instead of leaving it driving the retired
        # controller.
        cmb_mode = getattr(self.ui, "cmb_mode", None)
        if cmb_mode is not None:
            cmb_mode.blockSignals(True)
            cmb_mode.clear()
            cmb_mode.addItem("Shots:", "shots")
            cmb_mode.addItem("Markers:", "markers")
            cmb_mode.setCurrentIndex(0)
            cmb_mode.blockSignals(False)
            cmb_mode.currentIndexChanged.connect(
                lambda i: cmb._nav_slots._on_cmb_mode_changed(i)
            )
        ctl._cmb_mode_widget = cmb_mode

    def _view_option(self, cmb):
        """The view button beside the scope: Standard, Compact, Graph.

        Each state shows the view on screen; a click shows the next one
        (``_set_view``), and the choice persists like the scope's.
        """
        views = self.controller.VIEWS
        states = []
        for i, (_name, label, icon) in enumerate(views):
            nxt = views[(i + 1) % len(views)]
            states.append(
                {
                    "icon": icon,
                    "tooltip": f"View: {label} (click for {nxt[1]})",
                    "callback": lambda n=nxt[0]: cmb._nav_controller._set_view(n),
                }
            )
        return self.sb.ActionOption(
            wrapped_widget=cmb,
            states=states,
            order=5,
            settings_key="shot_sequencer_view",
        )

    #: Where the track view's Options rows keep their state.
    _OPTIONS_NAMESPACE = "shot_sequencer/options"

    def _register_track_options(self, sequencer) -> None:
        """The track view's rows of the header pane's Options menu: Show
        Internal Holds (a track-row matter), remembered across sessions."""
        settings = self.sb.SettingsManager(namespace=self._OPTIONS_NAMESPACE)
        saved = settings.value("show_internal_holds", False)
        self.controller._show_internal_holds = saved in (True, 1, "1", "true", "True")

        def set_holds(on):
            settings.setValue("show_internal_holds", bool(on))
            self.controller._set_show_internal_holds(bool(on))

        sequencer.editor("tracks").add_option(
            "holds",
            "Show Internal Holds",
            lambda: self.controller._show_internal_holds,
            set_holds,
            "Draw the flat-key spans inside the attribute rows",
            section="Display",
        )

    # ---- header-menu option handlers -------------------------------------

    def _on_shortcut_overlay_changed(self, index: int) -> None:
        """Off / On / On Modifier for the corner legend of gestures and keys."""
        cmb = getattr(self.ui, "cmb_shortcut_overlay", None)
        widget = self.controller._get_sequencer_widget()
        if cmb is None or widget is None:
            return
        mode = cmb.itemData(index)
        if mode in widget.SHORTCUT_OVERLAY_MODES:
            widget.shortcut_overlay_mode = mode

    def _on_snap_to_keys_toggled(self, checked: bool) -> None:
        """Turn the opt-in pull onto existing key frames on or off.

        The alignment guides are unconditional -- this only decides whether
        the drag is also captured by the frames they mark.
        """
        widget = self.controller._get_sequencer_widget()
        if widget is not None:
            widget.snap_to_keys = bool(checked)

    def _on_playback_range_changed(self, index: int) -> None:
        """Handle the playback-range combobox selection."""
        cmb_pb = getattr(self.ui, "cmb_playback_range", None)
        if cmb_pb is None:
            return
        mode = cmb_pb.itemData(index)
        if mode:
            self.controller._set_playback_range_mode(mode)

    def _on_cmb_mode_changed(self, index: int) -> None:
        """Handle the Shots / Markers mode selector."""
        cmb_mode = getattr(self.ui, "cmb_mode", None)
        if cmb_mode is None:
            return
        mode = cmb_mode.itemData(index)
        if mode:
            self.controller._set_cmb_mode(mode)

    def _on_track_order_changed(self, index: int) -> None:
        """Handle the track-order scope combobox selection."""
        cmb = getattr(self.ui, "cmb_track_order", None)
        if cmb is None:
            return
        scope = cmb.itemData(index)
        if scope and scope != self.controller._track_order_scope:
            self.controller._track_order_scope = scope
            self.controller._sync_to_widget()

    # ---- shot CRUD (the dropdown's menu) ----------------------------------

    def _edit_shot_in_settings(self) -> None:
        """Open the Shots panel with the active shot pre-selected."""
        if self.controller.sequencer is not None:
            sid = self.controller.active_shot_id
            if sid is not None:
                self.controller.sequencer.store.set_active_shot(sid)
        self.controller._show_shots_window()

    def _delete_shot(self) -> None:
        """Delete the selected shot (dropdown menu / nav bar).

        One implementation for every entry point: the controller owns the
        confirmation and the engine call, so the dropdown menu, the shot-lane
        menu and the Delete key cannot drift into three different ideas of
        what deleting a shot does.
        """
        sid = self.controller.active_shot_id
        if self.controller.sequencer is None or sid is None:
            return
        self.controller.delete_shot(sid)

    def _detect_next_shot(self) -> None:
        """Generate a shot from the next unregistered animation cluster."""
        seq = self.controller.sequencer
        if seq is None:
            return
        store = seq.store  # never None: a sequencer builds one when not given
        cand = seq.detect_next_shot(gap_threshold=store.detection_threshold)
        if cand is None:
            self.controller._set_footer("No additional animation clusters found.")
            return
        result = ShotEditDialog.show(
            parent=self.ui,
            # Detection numbers its clusters from 1; the scene may hold those,
            # and the next free Shot_<n> beats a Shot_1_2.
            name=store.default_name(cand["name"]),
            start=cand["start"],
            end=cand["end"],
            title="Generated Shot",
            validate=store.name_error,
        )
        if result is None:
            return
        name, s, e, desc = result
        if e <= s:
            return
        # Through scene_edit like every other shot edit: without its restore
        # point a detected shot could not be undone at all.
        with store.scene_edit("Generate Shot"):
            shot = seq.define_shot(
                name=name, start=s, end=e, objects=cand["objects"], description=desc
            )
        self.controller._take_new_shot(shot)

    def _cmb_context_menu(self, pos) -> None:
        """Right-click menu on the shot dropdown."""
        if self.controller._cmb_mode != "shots":
            return
        cmb = getattr(self.ui, "cmb_shot", None)
        if cmb is None:
            return

        has_shot = self.controller.active_shot_id is not None
        menu = self.sb.ContextMenu(parent=cmb)
        # Editing the shot you just picked is what this menu is reached for
        # most often, so it leads; creation and the structural edits follow.
        menu.add(
            "Edit Shot…", callback=self._edit_shot_in_settings, setEnabled=has_shot
        )
        menu.add_separator()
        # New Shot (with Insert Before / After), Split at Playhead and Merge
        # live on the shot body's own menu, over the shot they act on.
        # Generate Next Shot has no twin there, so it stays here.
        menu.add("Generate Next Shot…", callback=self._detect_next_shot)
        menu.add_separator()
        menu.add("Delete Shot…", callback=self._delete_shot, setEnabled=has_shot)
        # The Shots panel's Delete Shots, scope by scope (``ShotReport`` words
        # both): each row names how many shots it would take, and is off when
        # that is none.
        seq = self.controller.sequencer
        store = seq.store if seq is not None else None
        scoped = menu.add("Delete Shots", setEnabled=bool(store and store.shots))
        for label, scope in ptk.ShotReport.SCOPE_LABELS:
            doomed = store.shots_in_scope(scope) if store is not None else []
            menu.add(
                f"{label}…",
                parent=scoped,
                callback=lambda s=scope: self.controller.delete_shots(s),
                setEnabled=bool(doomed),
                setToolTip=(
                    f"Delete {ptk.ShotReport.scope_count(doomed, scope)}.\n"
                    "Their records only: no keyframe is touched, no shot moves."
                    if doomed
                    else f"No {'' if scope == 'all' else label.lower() + ' '}shots."
                ),
            )
        menu.exec_(cmb.mapToGlobal(pos))

    # ---- header ------------------------------------------------------------

    def header_init(self, widget):
        """Build the header menu."""
        # Refresh is a window verb: the header's own button, beside the menu.
        # A tool panel stays open (sticky): hide, not pin -- a header carries
        # one dismissal button, and the user's persistence choice swaps it.
        widget.config_buttons("refresh", "menu", "collapse", "hide")
        widget.refresh_requested.connect(lambda: self.controller.refresh())
        widget.menu.add(
            "QSpinBox",
            setMinimum=0,
            setMaximum=1000,
            setValue=1,
            setObjectName="spn_snap",
            setPrefix="Snap: ",
            setToolTip="Snap interval for clip edges when dragging or resizing (0 = free movement).",
        )
        chk_snap_keys = widget.menu.add(
            "QCheckBox",
            setText="Snap to Keys",
            setObjectName="chk_snap_to_keys",
            setToolTip="Pull clip and key drags onto frames that already carry keys.\nAlignment guides are shown either way.",
        )
        chk_snap_keys.toggled.connect(self._on_snap_to_keys_toggled)
        # Extend to Keys: one global switch, not a per-shot action.  Keys set
        # (or pasted) outside the current shot pull its bound out to cover
        # them, capped by the reach below -- which is the whole question the
        # option asks, so it sits right under it and greys out with it.
        chk_extend = widget.menu.add(
            "QCheckBox",
            setText="Extend to Keys",
            setObjectName="chk_extend_to_keys",
            setToolTip=(
                "Grow the current shot to cover keys created outside it.\n"
                "Keys inside a neighbouring shot are never claimed."
            ),
        )
        spn_reach = widget.menu.add(
            "QSpinBox",
            setObjectName="spn_extend_reach",
            setPrefix="Extend Distance: ",
            setSuffix=" frames",
            setMinimum=int(self.controller.ANY_REACH),
            setMaximum=100000,
            setSpecialValueText="Extend Distance: any",
            setValue=int(self.controller.EXTEND_REACH_FRAMES),
            setToolTip=(
                "How far outside a bound a new key may sit and still be "
                "reached for.\nAt the minimum (-1) the distance is not "
                "capped at all."
            ),
        )
        spn_reach.setEnabled(False)
        chk_extend.toggled.connect(self.controller._set_extend_to_keys)
        chk_extend.toggled.connect(spn_reach.setEnabled)
        spn_reach.valueChanged.connect(self.controller._set_extend_reach)

        WidgetComboBox = self.sb.WidgetComboBox
        cmb_overlay = widget.menu.add(
            WidgetComboBox,
            setObjectName="cmb_shortcut_overlay",
            setToolTip="Keep a legend of the drag grammar and keys in the timeline's corner;\nthe group under the pointer is lit.\n\nOn Modifier shows it only while Ctrl, Shift or Alt is held.",
        )
        cmb_overlay.addItem("Shortcut Overlay: Off", "off")
        cmb_overlay.addItem("Shortcut Overlay: On", "on")
        cmb_overlay.addItem("Shortcut Overlay: On Modifier", "modifier")
        cmb_overlay.setCurrentIndex(0)
        cmb_overlay.currentIndexChanged.connect(self._on_shortcut_overlay_changed)

        cmb_pb = widget.menu.add(
            WidgetComboBox,
            setObjectName="cmb_playback_range",
            setToolTip="Control how the scene's playback range tracks the visible shots.",
        )
        cmb_pb.addItem("Playback Range: Off", "off")
        cmb_pb.addItem("Playback Range: Follows Scope", "follows_view")
        cmb_pb.addItem("Playback Range: Locked to Shot", "locked")
        cmb_pb.setCurrentIndex(1)
        cmb_pb.currentIndexChanged.connect(self._on_playback_range_changed)

        cmb_scope = widget.menu.add(
            WidgetComboBox,
            setObjectName="cmb_track_order",
            setToolTip=self.sb.tooltip.fmt(
                title="Track Order",
                bullets=[
                    "<b>Visible:</b> Show objects from visible shots only.",
                    "<b>Global:</b> Show all objects from every shot so tracks never reorder when switching shots.",
                ],
            ),
        )
        cmb_scope.addItem("Track Order: Visible", "visible")
        cmb_scope.addItem("Track Order: Global", "global")
        cmb_scope.setCurrentIndex(
            0 if self.controller._track_order_scope == "visible" else 1
        )
        cmb_scope.currentIndexChanged.connect(self._on_track_order_changed)

        seq = getattr(self.controller, "sequencer", None)
        chk_select = widget.menu.add(
            "QCheckBox",
            setText="Select Members on Load",
            setObjectName="chk_select_on_load",
            setToolTip=(
                "Select all objects belonging to the shot\n"
                "when navigating to it in the sequencer."
            ),
        )
        chk_select.restore_state = False  # the store owns this setting
        if seq is not None and hasattr(seq, "store"):
            chk_select.setChecked(seq.store.select_on_load)
        chk_select.toggled.connect(self.controller._on_select_on_load_toggled)

        chk_frame = widget.menu.add(
            "QCheckBox",
            setText="Frame on Shot Change",
            setObjectName="chk_frame_on_shot_change",
            setToolTip=(
                "Automatically frame the view on the shot's objects\n"
                "when navigating to a different shot."
            ),
        )
        chk_frame.restore_state = False  # the store owns this setting
        if seq is not None and hasattr(seq, "store"):
            chk_frame.setChecked(seq.store.frame_on_shot_change)
        chk_frame.toggled.connect(self.controller._on_frame_on_shot_change_toggled)

        # One global option for every shot change (dropdown, prev / next, a
        # shot block, another panel's pick) and every new shot; remembered per
        # user, like the playback range.
        chk_playhead = widget.menu.add(
            "QCheckBox",
            setText="Playhead to Shot Start",
            setObjectName="chk_playhead_to_shot_start",
            setChecked=True,
            setToolTip=(
                "Move the playhead to a shot's first frame\n"
                "when changing to it or creating it."
            ),
        )
        chk_playhead.toggled.connect(self.controller._set_playhead_to_shot_start)

        widget.menu.add("Separator", setTitle="Actions")
        widget.menu.add(
            "QPushButton",
            setText="Attribute Colors",
            setObjectName="btn_colors",
            setToolTip="Customize the colors used to display each animated attribute in the sequencer.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Shortcuts…",
            setObjectName="btn_shortcuts",
            setToolTip="View and customise sequencer keyboard shortcuts.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Shots…",
            setObjectName="btn_shot_settings",
            setToolTip="Open shared shot generation, gap, and editing settings.",
        )
        self._set_help(widget)

    #: The full guide; the header's help is its short form.
    HELP_URL = "https://github.com/m3trik/mayatk/blob/main/docs/shot_sequencer.md"

    def _set_help(self, header) -> None:
        """The header's help: the essentials at a glance, and the full guide
        a click away (:attr:`HELP_URL`)."""
        kbd = self.sb.tooltip.kbd
        dot = " &nbsp;·&nbsp; "
        header.set_help_text(
            self.sb.tooltip.fmt(
                title="Shot Sequencer",
                body="Shots on the ruler, objects as tracks, keys as clips, rows or curves.",
                sections=[
                    (
                        "Shots",
                        [
                            "<b>+</b> adds a shot; the dropdown and <b>◄ / ►</b> change shots.",
                            "<b>Scope</b> shows the current, adjacent or all shots; <b>View</b> switches Standard, Compact and Graph.",
                        ],
                    ),
                    (
                        "Editing",
                        [
                            "Drag a clip to move its keys; drag its edge to scale them.",
                            "Drag a shot's edge to resize it as neighbours ripple; Ctrl moves the bound only, Shift retimes its keys, Alt resizes about the centre.",
                            "Right-click anything for its menu; Ctrl+Z undoes every edit.",
                        ],
                    ),
                    (
                        "Keys",
                        [
                            dot.join(
                                (
                                    f"{kbd(_KB_LEFT)} / {kbd(_KB_RIGHT)} prev / next key",
                                    f"{kbd('F')} frame",
                                    f"{kbd('M')} marker",
                                    f"{kbd('Del')} delete",
                                )
                            ),
                            f"{kbd('Ctrl', 'C')} / {kbd('Ctrl', 'V')} copy / paste keys",
                        ],
                    ),
                ],
            ),
            url=self.HELP_URL,
        )

    # ---- widget slots (objectName -> method) -------------------------------

    def cmb_shot(self, index):
        """A shot (or, in Markers mode, a marker) picked in the dropdown."""
        cmb = getattr(self.ui, "cmb_shot", None)
        if cmb is None or index < 0:
            return
        if self.controller._cmb_mode == "markers":
            # Markers mode: the playhead goes to the marker's time.
            marker_time = cmb.itemData(index)
            if marker_time is not None:
                widget = self.controller._get_sequencer_widget()
                if widget:
                    widget.set_playhead(marker_time)
                    widget.playhead_moved.emit(marker_time)
            return
        shot_id = cmb.itemData(index)
        if shot_id is not None:
            self.controller._go_to_shot(shot_id)

    def spn_snap(self, value):
        """Set the snap interval on the sequencer widget."""
        widget = self.controller._get_sequencer_widget()
        if widget is not None:
            widget.snap_interval = float(value)

    def btn_colors(self):
        """Open the attribute color configuration dialog."""
        widget = self.controller._get_sequencer_widget()
        dlg = self.sb.AttributeColorDialog(
            defaults=ptk.Palette.channels(),
            common_attrs=list(ptk.TRANSFORM_CHANNELS),
            active_attrs=widget.clip_attributes() if widget else [],
            parent=widget or self.ui,
        )

        def _apply(cmap):
            if widget:
                widget.attribute_colors = cmap
            # Invalidate the cached map so the next rebuild reloads it.
            self.controller._color_map_cache = None

        dlg.colors_changed.connect(_apply)
        dlg.exec_()

    def btn_shortcuts(self):
        """Open the sequencer shortcut editor."""
        widget = self.controller._get_sequencer_widget()
        if widget is not None:
            widget.shortcut_manager.show_editor(
                parent=widget, title="Sequencer Shortcuts"
            )

    def btn_shot_settings(self):
        """Open the shared Shots panel (pinned, as Edit Shot does)."""
        self.controller._show_shots_window()
