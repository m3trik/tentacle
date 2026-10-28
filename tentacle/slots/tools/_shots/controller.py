# !/usr/bin/python
# coding=utf-8
"""The Shots panel's controller: the scene's shot settings, the selected shot's
fields and edits, and the edits every shot takes.

One copy for both hosts. The store and the engine are the host library's,
reached through ``self.tk``: :meth:`ShotsController._sequencer_cls` is the
host's ``ShotSequencer`` and :meth:`ShotsController._store_cls` its
``STORE_CLASS`` (pythontk's ``ShotSequencer`` contract), so the panel names
neither ``ShotStore`` nor ``BlenderShotStore``. What the panel says about the
store -- the footer's summary, a trim's outcome, the Delete Shots scopes and
question -- is pythontk's ``ShotReport``, which the host's Shot Sequencer words
its own menus with.
"""

import pythontk as ptk
from pythontk import (
    ActiveShotChanged,
    BatchComplete,
    SettingsChanged,
    ShotDefined,
    ShotRemoved,
    ShotsEdited,
    ShotUpdated,
    StoreEvent,
    StoreInvalidated,
)
from qtpy import QtWidgets


class ShotsController(ptk.LoggingMixin):
    """Business logic for the Shots settings panel."""

    def __init__(self, slots_instance, log_level="WARNING"):
        super().__init__()
        self.set_log_level(log_level)
        self.sb = slots_instance.sb
        self.ui = slots_instance.ui
        #: The host library (``mtk`` / ``btk``): its ``ShotSequencer`` and store.
        self.tk = slots_instance.tk
        self._store_listener_bound = False
        self._refreshing_editor = False

        # Widgets the store owns get their values from it, not QSettings: a
        # restore lands after the store sync and goes through the slot that
        # writes the store, so a QSettings copy overwrote this scene's setting
        # with the last one set in any scene.
        for name in (
            "cmb_shot_select",
            "txt_shot_name",
            "spn_shot_start",
            "spn_shot_end",
            "txt_shot_desc",
            "spn_move_to",
            "spn_space",
            "spn_detection",
            "cmb_detection_mode",
            "spn_initial_length",
            "cmb_fit_mode",
            "chk_snap_whole_frames",
        ):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.restore_state = False

        # Debounce value-change signals so rapid spinner clicks / text
        # edits coalesce into a single store update.  spn_detection is
        # included because each change can trigger a full-scene
        # has_animation scan via refresh_state.
        for name in (
            "spn_shot_start",
            "spn_shot_end",
            "txt_shot_name",
            "txt_shot_desc",
            "spn_detection",
        ):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.debounce = 400

        # Disable keyboard tracking on frame spinners so valueChanged only
        # fires on commit (Enter / focus-loss / arrow-click), not on every
        # keystroke.  Without this, clearing the text to retype a value
        # emits valueChanged(0) mid-edit, which triggers a downstream
        # ripple with a bogus delta and corrupts all later shot ranges.
        for name in ("spn_shot_start", "spn_shot_end"):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.setKeyboardTracking(False)

        # The name IS the exported clip name: the field refuses what the
        # export would respell and says why -- the store's ``name_error``
        # through uitk's shared validator, red with the reason as its tooltip
        # -- and a refused name goes back to the shot's own on Enter /
        # focus-out, logged (_on_shot_name_refused), never silently.
        self._name_tooltip = (
            f"Shot name, exported as the clip name: {ptk.ShotStore.NAME_RULE}, "
            "unique ignoring case."
        )
        txt_name = getattr(self.ui, "txt_shot_name", None)
        if txt_name is not None:
            txt_name.setToolTip(self._name_tooltip)
            txt_name.set_validator(
                self._shot_name_error,
                reasons=True,
                debounce_ms=0,
                empty_is_valid=False,
                valid_tooltip=self._name_tooltip,
                revert_on_commit=self._active_shot_name,
            )
            txt_name.commit_refused.connect(self._on_shot_name_refused)

        # The option boxes before the first sync: the gap amount is one of
        # Apply Gap's options, and the sync fills it.
        self._setup_delete_menu()
        self._setup_move_menu()
        self._setup_swap_menu()
        self._setup_trim_menu()
        self._setup_space_menu()
        self._setup_gap_menu()
        self._setup_shift_menu()
        self._setup_delete_shots_menu()
        self._setup_shot_nav()
        self._sync_from_store()
        self._bind_store_listener()

        # Subscribe to class-level invalidation so the UI refreshes when
        # the persistence layer detects a scene change — no duplicate
        # scriptJobs needed.
        self._store_cls().add_invalidation_listener(self._on_store_invalidated)
        # Tear down on panel close: the invalidation registry is a class-level
        # list holding strong refs, so without this every reopen leaks a
        # controller whose stale listener then fires against destroyed widgets.
        self.ui.destroyed.connect(lambda *_: self.remove_callbacks())

        # Enable hide-on-mouse-leave so the window behaves like a quick-access panel.
        # WindowStaysOnTopHint prevents the panel from falling behind the
        # sequencer when focus shifts back to it.
        self._setup_hide_on_leave()

    # ---- hide on mouse leave ---------------------------------------------

    def _setup_hide_on_leave(self) -> None:
        """Hide the window once the cursor has visited and left it, unless
        pinned -- uitk's ``WindowAutoHide``, parented to the window."""
        self._auto_hide = self.sb.WindowAutoHide(self.ui)

    # ---- store access ----------------------------------------------------

    def _store_cls(self):
        """The host's store class: the ``STORE_CLASS`` of its ``ShotSequencer``
        (Maya's ``ShotStore``, Blender's ``BlenderShotStore``)."""
        return self._sequencer_cls().STORE_CLASS

    def _sequencer_cls(self):
        """The host's ``ShotSequencer``: every edit handler builds one over the
        active store."""
        return self.tk.ShotSequencer

    def _active_store(self):
        """Return the active ShotStore, or ``None``."""
        try:
            return self._store_cls().active()
        except Exception:
            return None

    def _bind_store_listener(self) -> None:
        """Listen for external store mutations to keep widgets in sync."""
        if self._store_listener_bound:
            return
        store = self._active_store()
        if store is not None:
            store.add_listener(self._on_store_event)
            self._bound_store = store
            self._store_listener_bound = True

    def _unbind_store_listener(self) -> None:
        """Detach from the current store so we can rebind after scene change."""
        if not self._store_listener_bound:
            return
        store = getattr(self, "_bound_store", None) or self._store_cls()._active
        if store is not None:
            store.remove_listener(self._on_store_event)
        self._bound_store = None
        self._store_listener_bound = False

    def remove_callbacks(self) -> None:
        """Remove store listeners and invalidation subscription (call on teardown)."""
        self._unbind_store_listener()
        self._store_cls().remove_invalidation_listener(self._on_store_invalidated)

    def _on_store_invalidated(self, event: StoreInvalidated) -> None:
        """Re-sync the UI after the active store is discarded (scene change)."""
        self._unbind_store_listener()
        self._sync_from_store()
        self._bind_store_listener()

    def _on_store_event(self, event: StoreEvent) -> None:
        """Re-sync widgets when the store changes externally.

        ``ShotsEdited`` included: a Shot Sequencer trim, resize or drag writes
        the bounds directly, and is the only word this panel gets of it.
        """
        if isinstance(
            event,
            (BatchComplete, ShotDefined, ShotRemoved, SettingsChanged, ShotsEdited),
        ):
            self._sync_from_store()
        elif isinstance(event, (ActiveShotChanged, ShotUpdated)):
            if isinstance(event, ShotUpdated):
                self._relabel_shot_row(event.shot)
            self._sync_shot_editor()
            self._sync_footer()

    # ---- index ↔ mode mapping ---------------------------------------------

    _DETECTION_MODES = ptk.ShotStore.DETECTION_MODES
    _FIT_MODES = ptk.ShotStore.FIT_MODES

    def _mode_to_index(self, mode: str) -> int:
        try:
            return self._DETECTION_MODES.index(mode)
        except ValueError:
            return 0

    def _index_to_mode(self, index: int) -> str:
        if 0 <= index < len(self._DETECTION_MODES):
            return self._DETECTION_MODES[index]
        return "auto"

    # ---- footer ----------------------------------------------------------

    def _set_footer(self, text: str) -> None:
        """Write *text* into the window footer."""
        footer = getattr(self.ui, "footer", None)
        if footer is None:
            return
        label = footer._status_label
        label.setStyleSheet("background: transparent; border: none;")
        footer.setText(text)

    def _sync_footer(self, store=None) -> None:
        """Update footer with aggregate shot statistics."""
        if store is None:
            store = self._active_store()
        if store is None or not store.shots:
            self._set_footer("")
            return
        self._set_footer(ptk.ShotReport.summary(store.sorted_shots()))

    # ---- state management -------------------------------------------------

    def refresh_state(self) -> None:
        """Central enable/disable refresh for all Shots UI widgets.

        Checks scene state (animation existence, shot existence) and
        sets the correct enabled state on every widget.  Call this
        after any operation that might change scene context — assess,
        build, scene open, etc.

        Dependent tools (manifest, sequencer) should call this instead
        of managing individual widget states themselves.
        """
        store = self._active_store()
        has_shots = bool(store.shots) if store else False
        mode = store.detection_mode if store else "auto"
        det_relevant = store.is_detection_relevant if store else True

        # Detection group — disabled when shots already exist OR
        # when auto mode finds no animation in the scene.
        # Only call has_animation() when it can actually affect the
        # result (auto mode + no shots) to avoid a scene-wide animation
        # scan on every store event.
        needs_anim_check = det_relevant and mode == "auto"
        has_anim = self._store_cls().has_animation() if needs_anim_check else True
        auto_no_anim = needs_anim_check and not has_anim

        cmb_mode = getattr(self.ui, "cmb_detection_mode", None)
        spn_det = getattr(self.ui, "spn_detection", None)

        if cmb_mode is not None:
            cmb_mode.setEnabled(det_relevant)
        if spn_det is not None:
            spn_det.setEnabled(
                det_relevant and mode != "zero_as_end" and not auto_no_anim
            )

        # All Shots group -- every control there needs at least one shot.
        # Delete Shots too, and the click decides whether its scope holds one
        # (on_delete_shots says "No stale shots"): deleting an object raises no
        # store event, so a state judged at the last one goes stale -- the
        # export log's Open Shots link opened the panel with the button greyed
        # out -- and judging it here looked every member and frame up in the
        # scene on every store event.
        for name in (
            "btn_apply_gap",
            "btn_shift_all",
            "btn_trim_all",
            "btn_delete_shots",
        ):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.setEnabled(has_shots)
        self.label_delete_shots()

    # ---- sync ------------------------------------------------------------

    def _sync_from_store(self) -> None:
        """Pull current values from ShotStore into UI widgets."""
        store = self._active_store()
        if store is None:
            return

        spn_det = getattr(self.ui, "spn_detection", None)
        if spn_det is not None:
            spn_det.blockSignals(True)
            spn_det.setValue(store.detection_threshold)
            spn_det.blockSignals(False)

        cmb_mode = getattr(self.ui, "cmb_detection_mode", None)
        if cmb_mode is not None:
            cmb_mode.blockSignals(True)
            cmb_mode.setCurrentIndex(self._mode_to_index(store.detection_mode))
            cmb_mode.blockSignals(False)

        spn_init = getattr(self.ui, "spn_initial_length", None)
        if spn_init is not None:
            spn_init.blockSignals(True)
            spn_init.setValue(float(store.initial_shot_length))
            spn_init.blockSignals(False)

        cmb_fit = getattr(self.ui, "cmb_fit_mode", None)
        if cmb_fit is not None:
            cmb_fit.blockSignals(True)
            try:
                cmb_fit.setCurrentIndex(self._FIT_MODES.index(store.fit_mode))
            except ValueError:
                cmb_fit.setCurrentIndex(0)
            cmb_fit.blockSignals(False)

        chk_snap = getattr(self.ui, "chk_snap_whole_frames", None)
        if chk_snap is not None:
            chk_snap.blockSignals(True)
            chk_snap.setChecked(bool(store.snap_whole_frames))
            chk_snap.blockSignals(False)
        self._apply_snap_to_spinboxes(bool(store.snap_whole_frames))

        chk_stale = getattr(self.ui, "chk_drop_stale_shots", None)
        if chk_stale is not None:
            chk_stale.blockSignals(True)
            chk_stale.setChecked(bool(store.drop_stale_shots))
            chk_stale.blockSignals(False)

        # ---- Editing group ----
        has_shots = bool(store.shots)

        # If shots exist but the persisted gap is zero, derive it from
        # actual shot positions so the spinner (and any op that reads
        # store.gap) reflects the scene state.  In-memory only: calling
        # mark_dirty here made a pure UI sync schedule a re-save of a
        # freshly-opened scene; the value persists with the next real
        # mutation instead.
        gap = store.gap
        if has_shots and gap == 0.0:
            gap = store.compute_gap()
            store.gap = gap

        spn_gap = getattr(self.ui, "spn_gap", None)
        if spn_gap is not None:
            spn_gap.blockSignals(True)
            spn_gap.setValue(int(gap))
            spn_gap.blockSignals(False)
            self.label_apply_gap()

        self._populate_shot_combobox(store)
        self._sync_footer(store)
        self.refresh_state()

    # ---- shot editor sync ------------------------------------------------

    def _populate_shot_combobox(self, store=None) -> None:
        """Rebuild the shot selector combobox from the store."""
        if store is None:
            store = self._active_store()

        cmb = getattr(self.ui, "cmb_shot_select", None)
        if cmb is None:
            return

        cmb.blockSignals(True)
        cmb.clear()
        if store is not None:
            for shot in store.sorted_shots():
                cmb.addItem(self.shot_label(shot), shot.shot_id)
            # Select the active shot, or auto-select the first one
            active_id = store.active_shot_id
            matched = False
            if active_id is not None:
                for i in range(cmb.count()):
                    if cmb.itemData(i) == active_id:
                        cmb.setCurrentIndex(i)
                        matched = True
                        break
            if not matched and cmb.count() > 0:
                cmb.setCurrentIndex(0)
                first_id = cmb.itemData(0)
                if first_id is not None:
                    store.set_active_shot(first_id)
        cmb.blockSignals(False)
        self._sync_shot_editor(store)

    def _sync_shot_editor(self, store=None) -> None:
        """Load the active shot's fields into the editor widgets."""
        if store is None:
            store = self._active_store()
        cmb = getattr(self.ui, "cmb_shot_select", None)
        active = (
            store.shot_by_id(store.active_shot_id)
            if store is not None and store.active_shot_id is not None
            else None
        )
        if (
            cmb is not None
            and active is not None
            and self._shot_row(cmb, active.shot_id) < 0
        ):
            # A shot the dropdown does not list yet: rebuilding it syncs this.
            self._populate_shot_combobox(store)
            return

        self._refreshing_editor = True
        try:
            self._enable_shot_editor(store, active, cmb)
            self._fill_shot_editor(store, active, cmb)
            self._update_shot_nav_state()
        finally:
            self._refreshing_editor = False

    def _enable_shot_editor(self, store, shot, cmb) -> None:
        """Enable the editor's fields and buttons for *shot* (``None``: no
        active shot), and bound Move To by the shots there are."""
        has_shot = shot is not None
        has_any_shots = cmb is not None and cmb.count() > 0
        if cmb is not None:
            cmb.setEnabled(has_any_shots)  # re-enables its option buttons
        for name in (
            "txt_shot_name",
            "spn_shot_start",
            "spn_shot_end",
            "txt_shot_desc",
            "b000",
            "btn_trim_empty",
            "spn_space",
        ):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.setEnabled(has_shot)
        btn_swap = getattr(self.ui, "btn_swap_shot", None)
        if btn_swap is not None:
            # Trading places needs a second shot.
            btn_swap.setEnabled(has_shot and cmb is not None and cmb.count() > 1)
        self._populate_swap_targets(store, shot)
        spn_move = getattr(self.ui, "spn_move_to", None)
        if spn_move is not None:
            spn_move.setEnabled(has_shot and has_any_shots)
            # The ceiling with or without an active shot: a stale maximum
            # silently refuses positions that became legal when shots were
            # added.
            n_shots = len(store.sorted_shots()) if store is not None else 0
            self._set_quietly(spn_move, "setMaximum", max(n_shots, 1))
            spn_move.setToolTip(
                "Move the selected shot to this position in the timeline "
                f"order (1\u2013{max(n_shots, 1)}; option box \u25b8 to apply)."
            )

    def _fill_shot_editor(self, store, shot, cmb) -> None:
        """Write *shot*'s fields into the editor (blank them for ``None``) and
        point the dropdown and Move To at it -- a sync, signals blocked."""
        txt_name = getattr(self.ui, "txt_shot_name", None)
        spn_start = getattr(self.ui, "spn_shot_start", None)
        spn_end = getattr(self.ui, "spn_shot_end", None)
        txt_desc = getattr(self.ui, "txt_shot_desc", None)
        if shot is None:
            self._set_quietly(txt_name, "setText", "")
            if txt_name is not None:
                # No shot to name: nothing is refused.
                txt_name.reset_action_color()
                txt_name.setToolTip(self._name_tooltip)
            self._set_quietly(spn_start, "setValue", 0)
            self._set_quietly(spn_end, "setValue", 0)
            self._set_quietly(txt_desc, "setText", "")
            return

        if txt_name is not None:
            if txt_name.text() != shot.name:
                self._set_quietly(txt_name, "setText", shot.name)
            # A name held from before names were validated shows as refused
            # right away -- the export would respell it (and says so). The
            # text went in with signals blocked, so the field checks it now.
            txt_name.validate_now()
        self._set_quietly(spn_start, "setValue", shot.start)
        self._set_quietly(spn_end, "setValue", shot.end)
        if txt_desc is not None and txt_desc.text() != shot.description:
            self._set_quietly(txt_desc, "setText", shot.description)

        # The dropdown follows the active shot, wherever it was picked.
        # It used to relabel its CURRENT row with the active shot -- after
        # a pick in the Shot Sequencer that row was another shot's, so one
        # shot was listed twice and the other was gone (2026-10-10: "the
        # shots combobox doesn't update properly and is often missing
        # shots during editing").
        if cmb is not None:
            row = self._shot_row(cmb, shot.shot_id)
            cmb.blockSignals(True)
            cmb.setCurrentIndex(row)
            cmb.setItemText(row, self.shot_label(shot))
            cmb.blockSignals(False)

        # Move To shows the shot's place in the timeline order.
        spn_move = getattr(self.ui, "spn_move_to", None)
        if spn_move is not None and store is not None:
            pos = next(
                (
                    i + 1
                    for i, s in enumerate(store.sorted_shots())
                    if s.shot_id == shot.shot_id
                ),
                1,
            )
            self._set_quietly(spn_move, "setValue", pos)

    @staticmethod
    def _set_quietly(widget, setter: str, value) -> None:
        """``widget.<setter>(value)`` with its signals blocked: a sync, not an
        edit.  No widget, nothing set."""
        if widget is None:
            return
        widget.blockSignals(True)
        getattr(widget, setter)(value)
        widget.blockSignals(False)

    @staticmethod
    def shot_label(shot) -> str:
        """A shot's row in the dropdown: ``"Shot_1  [1\u2013100]"``."""
        return f"{shot.name}  [{shot.start:.0f}\u2013{shot.end:.0f}]"

    @staticmethod
    def _shot_row(cmb, shot_id) -> int:
        """The dropdown row listing *shot_id*, or -1."""
        return next((i for i in range(cmb.count()) if cmb.itemData(i) == shot_id), -1)

    def _relabel_shot_row(self, shot) -> None:
        """Refresh the row of *shot* -- any shot, not only the active one."""
        cmb = getattr(self.ui, "cmb_shot_select", None)
        if cmb is None or shot is None:
            return
        row = self._shot_row(cmb, shot.shot_id)
        if row >= 0:
            cmb.blockSignals(True)
            cmb.setItemText(row, self.shot_label(shot))
            cmb.blockSignals(False)

    # ---- shot navigation (the dropdown's option box) ---------------------

    def _setup_shot_nav(self) -> None:
        """Previous / Next / New Shot buttons on the dropdown's option box --
        the Shot Sequencer dropdown's own (2026-10-10: "give the shot combobox
        an option_box previous and next icon buttons to match the shot
        sequencer's shot combobox ... a plus icon add shot icon button").

        Built once per widget and late-bound through ``cmb._nav_controller``,
        so a slots re-init over the same loaded UI repoints them rather than
        stacking a second set (the Sequencer's own contract).  New Shot stays
        clickable with no shot listed: the dropdown is disabled then, and the
        option box disables its buttons with it.
        """
        cmb = getattr(self.ui, "cmb_shot_select", None)
        if cmb is None or not hasattr(cmb, "option_box"):
            return
        cmb._nav_controller = self
        options = getattr(cmb, "_shots_nav_options", None)
        if options is None:
            ActionOption = self.sb.ActionOption
            options = {}
            for key, icon, tooltip, order, callback in (
                (
                    "prev",
                    "chevron_left",
                    "Previous Shot",
                    0,
                    lambda: cmb._nav_controller.on_navigate_shot(-1),
                ),
                (
                    "next",
                    "chevron_right",
                    "Next Shot",
                    1,
                    lambda: cmb._nav_controller.on_navigate_shot(1),
                ),
                (
                    "new",
                    "add",
                    "New Shot\nAfter the last shot, the gap on, Initial Length long.",
                    2,
                    lambda: cmb._nav_controller.on_new_shot(),
                ),
            ):
                options[key] = ActionOption(
                    wrapped_widget=cmb,
                    callback=callback,
                    icon=icon,
                    tooltip=tooltip,
                    order=order,
                )
            cmb.option_box.set_order(["action"])
            for option in options.values():
                cmb.option_box.add_option(option)
            options["new"].widget.setProperty("keepEnabledWhenWrappedDisabled", True)
            cmb._shots_nav_options = options
        self._nav_options = options

    def _update_shot_nav_state(self) -> None:
        """Previous / Next enabled where there is a shot to step to.

        Run after any change to the dropdown's own enabled state: the option
        box re-enables every one of its buttons with it.
        """
        options = getattr(self, "_nav_options", None)
        cmb = getattr(self.ui, "cmb_shot_select", None)
        if not options or cmb is None:
            return
        idx, count = cmb.currentIndex(), cmb.count()
        options["prev"].widget.setEnabled(cmb.isEnabled() and idx > 0)
        options["next"].widget.setEnabled(cmb.isEnabled() and 0 <= idx < count - 1)

    def on_navigate_shot(self, delta: int) -> None:
        """Make the previous (-1) or next (+1) shot the active one."""
        cmb = getattr(self.ui, "cmb_shot_select", None)
        store = self._active_store()
        if cmb is None or store is None:
            return
        idx = cmb.currentIndex() + delta
        if 0 <= idx < cmb.count() and cmb.itemData(idx) is not None:
            store.set_active_shot(cmb.itemData(idx))

    def on_new_shot(self) -> None:
        """Append a new shot and make it the active one.

        The Shot Sequencer's New Shot, through the same engine call
        (``ShotSequencer.new_shot``): ``Shot_<n>``, the gap after the last
        shot, Initial Length (Build) long -- one undoable edit.
        """
        store = self._active_store()
        if store is None:
            return
        seq = self._sequencer_cls()(store=store)
        made = []
        if not self._boundary_edit(
            store, "newshot", lambda: made.append(seq.new_shot())
        ):
            return
        shot = made[0]
        store.set_active_shot(shot.shot_id)
        self._set_footer(
            f"Created {shot.name} \u00b7 {shot.start:.0f}\u2013{shot.end:.0f}"
        )

    # ---- widget → store pushes -------------------------------------------

    def on_detection_changed(self, value: float) -> None:
        store = self._active_store()
        if store is not None:
            store.detection_threshold = float(value)
            store.mark_dirty()
            store._save_user_prefs()
            store.notify_settings_changed()

    def on_detection_mode_changed(self, index: int) -> None:
        store = self._active_store()
        mode = self._index_to_mode(index)
        if store is not None:
            store.detection_mode = mode
            store.mark_dirty()
            store._save_user_prefs()
            store.notify_settings_changed()
        self.refresh_state()

    def on_initial_length_changed(self, value: float) -> None:
        store = self._active_store()
        if store is not None:
            store.initial_shot_length = float(value)
            store.mark_dirty()
            store._save_user_prefs()
            store.notify_settings_changed()

    def on_snap_whole_frames_changed(self, checked: bool) -> None:
        store = self._active_store()
        if store is None:
            return
        store.snap_whole_frames = bool(checked)
        store.mark_dirty()
        store._save_user_prefs()
        self._apply_snap_to_spinboxes(bool(checked))
        # Re-snap existing shot bounds so the scene state reflects the
        # new policy.  No-op when turning snapping off.
        if checked:
            changed = False
            for shot in store.shots:
                ns, ne = store.snap(shot.start), store.snap(shot.end)
                if ns != shot.start or ne != shot.end:
                    shot.start, shot.end = ns, ne
                    changed = True
            if changed:
                store.mark_dirty()
        store.notify_settings_changed()

    def _apply_snap_to_spinboxes(self, snap: bool) -> None:
        """Mirror snap policy on frame spinboxes by toggling decimals."""
        decimals = 0 if snap else 1
        for name in ("spn_shot_start", "spn_shot_end", "spn_gap", "spn_initial_length"):
            w = getattr(self.ui, name, None)
            if w is not None:
                w.setDecimals(decimals)

    def on_drop_stale_shots_changed(self, checked: bool) -> None:
        """Whether this file's exports leave its stale shots out
        (``ShotStore.drop_stale_shots``): saved with the shots, read by every
        export's take list."""
        store = self._active_store()
        if store is None:
            return
        store.drop_stale_shots = bool(checked)
        store.mark_dirty()
        store.notify_settings_changed()

    def on_fit_mode_changed(self, index: int) -> None:
        store = self._active_store()
        if store is None:
            return
        if 0 <= index < len(self._FIT_MODES):
            store.fit_mode = self._FIT_MODES[index]
            store.mark_dirty()
            store._save_user_prefs()
            store.notify_settings_changed()

    def _boundary_edit(self, store, label: str, fn, *args, **kwargs) -> bool:
        """Run a boundary-mutating edit, reporting a refusal instead of raising.

        The edit runs in ``store.scene_edit(label)``: one named undo step whose
        restore point (the store's shared ledger: scene keys ride the native
        undo queue, shot bounds do not) is tagged with that step.

        :class:`ShotBoundaryConflict` means the edit was declined: the shots
        would have had to share a sample whose two poses disagree, which one
        frame cannot hold.  The restore point stays with the step
        ``scene_edit`` pushed: a multi-stage edit can write before it is
        declined (a "both" Add Space slides the head before the tail ripple
        refuses), and undoing that step must put the bounds and claims back
        with the keys.  An edit declined before it wrote anything strands
        nothing: Maya's ``scene_edit`` drops the point of an edit that changed
        nothing, and where Blender keeps it, restoring it changes nothing.
        (mayatk's twin discarded the point here, which left a step whose keys
        an undo took back without their bounds.)

        Returns ``True`` when the edit ran, ``False`` when it was refused.
        """
        try:
            with store.scene_edit(label):
                fn(*args, **kwargs)
        except ptk.ShotBoundaryConflict as exc:
            self.logger.warning(str(exc))
            self._set_footer(str(exc))
            return False
        return True

    def on_gap_changed(
        self, value, scope: str = "all", respect_locks: bool = True
    ) -> None:
        """Set the store gap and re-space per *scope*.

        *respect_locks* False spends the gap on locked gaps too (the option
        box's Override Locked Gaps); the locks themselves are left set.
        """
        store = self._active_store()
        if store is None:
            return
        previous_gap = store.gap
        store.gap = float(value)
        store.mark_dirty()

        seq = self._sequencer_cls()(store=store)
        if not self._boundary_edit(
            store,
            "gap",
            seq.apply_gap,
            store.gap,
            scope=scope,
            shot_id=store.active_shot_id,
            respect_locks=respect_locks,
        ):
            # Put the setting back so the panel keeps showing what the
            # scene actually is.
            store.gap = previous_gap
            return
        store.notify_settings_changed()

    # ---- shot editor actions ---------------------------------------------

    def on_shot_selected(self, index: int) -> None:
        """User picked a different shot from the combobox."""
        cmb = getattr(self.ui, "cmb_shot_select", None)
        if cmb is None:
            return
        shot_id = cmb.itemData(index)
        store = self._active_store()
        if store is not None and shot_id is not None:
            store.set_active_shot(shot_id)

    def _push_shot_field(self, **kwargs) -> None:
        """Push one or more field changes to the active shot."""
        if self._refreshing_editor:
            return
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        store.update_shot(store.active_shot_id, **kwargs)

    def on_shot_name_changed(self, text: str) -> None:
        """Push a name the store accepts; the field marks one it refuses, and
        why (its validator is :meth:`_shot_name_error`)."""
        if self._refreshing_editor:
            return
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        if self._shot_name_error(text) is None:
            self._push_shot_field(name=text)

    def _shot_name_error(self, text: str):
        """Why the store refuses *text* as the active shot's name, else
        ``None`` -- the name field's validator (``ShotStore.name_error``).  No
        active shot: nothing to refuse."""
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return None
        return store.name_error(text, store.active_shot_id)

    def _active_shot_name(self):
        """The active shot's own name -- what a refused commit puts back."""
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return None
        shot = store.shot_by_id(store.active_shot_id)
        return shot.name if shot is not None else None

    def _on_shot_name_refused(self, refused: str, reason: str) -> None:
        """Say what a refused commit did not apply: the field has put the
        shot's own name back."""
        self.logger.warning(f"Shot name {refused!r} not applied. {reason}")

    def on_shot_start_changed(self, value: float) -> None:
        if self._refreshing_editor:
            return
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        shot = store.shot_by_id(store.active_shot_id)
        if shot is None:
            return
        if abs(value - shot.start) < 1e-6:
            return

        seq = self._sequencer_cls()(store=store)
        if not self._boundary_edit(
            store, "shotstart", seq.move_shot, shot.shot_id, value
        ):
            return
        store.mark_dirty()

    def on_shot_end_changed(self, value: float) -> None:
        if self._refreshing_editor:
            return
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        shot = store.shot_by_id(store.active_shot_id)
        if shot is None:
            return
        delta = value - shot.end
        if abs(delta) < 1e-6:
            return

        seq = self._sequencer_cls()(store=store)

        def _run():
            old_end = shot.end
            store.update_shot(shot.shot_id, end=value)
            seq.ripple_downstream(shot.shot_id, old_end, delta)

        self._boundary_edit(store, "shotend", _run)

    def on_shot_desc_changed(self, text: str) -> None:
        self._push_shot_field(description=text)

    #: The three ends a trim can act on, as ``(label, edge, suffix)``.  One
    #: table drives both trim buttons so the per-shot and all-shots menus
    #: cannot offer different scopes.
    _TRIM_EDGES = (
        ("Trim Leading Space", "leading", "leading"),
        ("Trim Trailing Space", "trailing", "trailing"),
        ("Trim Both Ends", "both", "both"),
    )

    def _setup_delete_menu(self) -> None:
        """Attach the delete options to the delete button's option box.

        Both default ON, because "delete this shot" almost always means the
        shot AND its animation, with the timeline closing up behind it.  They
        are options rather than a hard-coded behaviour so removing just the
        record stays reachable.
        """
        btn = getattr(self.ui, "b000", None)
        if btn is None:
            return
        menu = btn.option_box.menu
        menu.add(
            "QCheckBox",
            setText="Delete Contents",
            setObjectName="chk_delete_contents",
            setChecked=True,
            setToolTip=(
                "Cut the keyframes the shot owns.\n"
                "Off: the shot record goes, its animation stays in the scene."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Close the Gap",
            setObjectName="chk_close_gap",
            setChecked=True,
            setToolTip=(
                "Slide the following shots back into the space the deleted\n"
                "shot occupied.  Off: the timeline keeps the hole."
            ),
        )

    def _setup_delete_shots_menu(self) -> None:
        """Attach the scope picker to Delete Shots' option box.

        One button for every multi-shot delete (2026-10-07: "consolidate to
        one global delete shots button ... delete stale, delete all, delete
        empty"), labelled with the scope it takes so a click never surprises.
        Stale leads: the narrowest, and the one an export's stale-shot note
        sends the user here for.
        """
        btn = getattr(self.ui, "btn_delete_shots", None)
        if btn is None:
            return
        cmb = btn.option_box.menu.add(
            self.sb.WidgetComboBox,
            setObjectName="cmb_delete_scope",
            setToolTip=(
                "Which shots Delete Shots takes:\n"
                "Stale -- every object they name is gone and nothing in their\n"
                "frames is keyed.\n"
                "Empty -- nothing they name is keyed in their frames (a shot\n"
                "naming nothing: nothing in the file is).\n"
                "All -- every shot.\n"
                "Records only, whichever: no keyframe is touched, no shot moves."
            ),
        )
        for label, scope in ptk.ShotReport.SCOPE_LABELS:
            cmb.addItem(label, scope)
        chk = btn.option_box.menu.add(
            "QCheckBox",
            setText="Leave Stale Shots Out of Exports",
            setObjectName="chk_drop_stale_shots",
            setToolTip=(
                "Off (default): an export ships every shot -- a stale one as a\n"
                "take that holds still -- and names the stale ones.\n"
                "On: an export leaves the stale shots out of the takes it\n"
                "declares.  This file's setting; the records stay either way."
            ),
        )
        # The file's setting, synced from the store (see __init__).
        chk.restore_state = False
        self.label_delete_shots()

    def delete_scope(self) -> str:
        """The scope Delete Shots takes (``"stale"`` until one is picked)."""
        cmb = getattr(self.ui, "cmb_delete_scope", None)
        scope = cmb.currentData() if cmb is not None else None
        return scope if scope in self._store_cls().DELETE_SCOPES else "stale"

    def label_delete_shots(self) -> None:
        """Name the picked scope on Delete Shots: "Delete Empty Shots"."""
        btn = getattr(self.ui, "btn_delete_shots", None)
        if btn is not None:
            label = ptk.ShotReport.scope_label(self.delete_scope())
            btn.setText(f"Delete {label} Shots")

    def _setup_move_menu(self) -> None:
        """Attach an option box action to the move-to spinbox."""
        spn = getattr(self.ui, "spn_move_to", None)
        if spn is None:
            return
        menu = spn.option_box.menu
        menu.add(
            "QPushButton",
            setText="Move Shot",
            setObjectName="btn_move_shot",
            setToolTip="Move the selected shot to the specified position.",
        )

    def _setup_swap_menu(self) -> None:
        """Fill Swap With's option box: the mode (:attr:`SWAP_MODES`), the
        other shot, then one Retain checkbox per field a swap can leave in
        place (``ShotSequencer.SWAP_FIELDS``).  The mode and the picked shot
        are named on the button (:meth:`label_swap_shot`)."""
        btn = getattr(self.ui, "btn_swap_shot", None)
        if btn is None:
            return
        menu = btn.option_box.menu
        cmb_mode = menu.add(
            self.sb.WidgetComboBox,
            setObjectName="cmb_swap_mode",
            setToolTip=(
                "Swap -- the two shots trade timeline places, each taking its\n"
                "keys along.\n"
                "Copy Over -- the picked shot's animation is replaced by a copy\n"
                "of the selected shot's (it takes the selected shot's length);\n"
                "its name, description, lock, metadata and the members it\n"
                "does not animate stay."
            ),
        )
        for label, mode, _verb in self.SWAP_MODES:
            cmb_mode.addItem(label, mode)
        cmb = menu.add(
            self.sb.WidgetComboBox,
            setObjectName="cmb_swap_with",
            setToolTip="The other shot: the one swapped with, or copied over.",
        )
        cmb.restore_state = False  # this scene's shots, filled by the sync
        for field, label, tip in self._SWAP_RETAIN:
            menu.add(
                "QCheckBox",
                setText=f"Retain {label}",
                setObjectName=f"chk_swap_retain_{field}",
                setChecked=False,
                setToolTip=tip,
            )
        self.label_swap_shot()

    #: Swap With's modes as ``(menu label, mode, button verb)``.
    SWAP_MODES = (("Swap", "swap", "Swap With"), ("Copy Over", "copy", "Copy To"))

    #: Swap With's Retain options as ``(field, label, tooltip)``, one per
    #: ``ShotSequencer.SWAP_FIELDS``.
    _SWAP_RETAIN = (
        (
            "name",
            "Name",
            "On: the names stay in timeline order -- each shot takes the\n"
            "name of the place it lands in.  Off: a shot keeps its name.",
        ),
        (
            "description",
            "Description",
            "On: the descriptions stay in place.  Off: they travel.",
        ),
        (
            "locked",
            "Lock",
            "On: each place keeps its lock (a locked shot is final for the\n"
            "Shot Manifest's Build).  Off: the lock travels with the shot.",
        ),
        (
            "metadata",
            "Metadata",
            "On: the manifest step each place pairs with -- its behaviors,\n"
            "assessment and the members its shot does not animate -- stays in\n"
            "place; animated members travel with their keys.  Off: it travels.",
        ),
    )

    def swap_mode(self) -> str:
        """Swap With's mode: ``"swap"`` (until one is picked) or ``"copy"``."""
        cmb = getattr(self.ui, "cmb_swap_mode", None)
        mode = cmb.currentData() if cmb is not None else None
        return mode if mode in {m for _l, m, _v in self.SWAP_MODES} else "swap"

    def swap_target(self):
        """The other shot's id -- swapped with, or copied over -- or ``None``."""
        cmb = getattr(self.ui, "cmb_swap_with", None)
        return cmb.currentData() if cmb is not None and cmb.count() else None

    def swap_retain(self) -> list:
        """The fields Swap With leaves in place: its checked Retain options."""
        return [
            field
            for field, _label, _tip in self._SWAP_RETAIN
            if self._option_checked(f"chk_swap_retain_{field}", False)
        ]

    def label_swap_shot(self, *_args) -> None:
        """Name the mode and the picked shot on Swap With: "Swap With: Shot_3",
        "Copy To: Shot_3".  Retain is a swap's: Copy Over keeps every field."""
        mode = self.swap_mode()
        for field, _label, _tip in self._SWAP_RETAIN:
            chk = getattr(self.ui, f"chk_swap_retain_{field}", None)
            if chk is not None:
                chk.setEnabled(mode == "swap")
        btn = getattr(self.ui, "btn_swap_shot", None)
        if btn is None:
            return
        verb = next(v for _l, m, v in self.SWAP_MODES if m == mode)
        target = self.swap_target()
        store = self._active_store() if target is not None else None
        shot = store.shot_by_id(target) if store is not None else None
        btn.setText(f"{verb}: {shot.name}" if shot is not None else verb)

    def _populate_swap_targets(self, store, active) -> None:
        """List every shot but *active* in Swap With's picker, keeping the
        pick while it is listed, else the shot after *active* (before it,
        for the last)."""
        cmb = getattr(self.ui, "cmb_swap_with", None)
        if cmb is None:
            return
        picked = self.swap_target()
        shots = store.sorted_shots() if store is not None else []
        ids = [s.shot_id for s in shots]
        cmb.blockSignals(True)
        cmb.clear()
        if active is not None and active.shot_id in ids and len(ids) > 1:
            for shot in shots:
                if shot.shot_id != active.shot_id:
                    cmb.addItem(self.shot_label(shot), shot.shot_id)
            if picked == active.shot_id or picked not in ids:
                at = ids.index(active.shot_id)
                picked = ids[at + 1] if at + 1 < len(ids) else ids[at - 1]
            cmb.setCurrentIndex(max(self._shot_row(cmb, picked), 0))
        cmb.blockSignals(False)
        self.label_swap_shot()

    def _setup_trim_menu(self) -> None:
        """Attach the per-edge trim actions to both trim buttons."""
        for name, prefix, what in (
            ("btn_trim_empty", "btn_trim", "the selected shot"),
            ("btn_trim_all", "btn_trim_all", "every shot"),
        ):
            btn = getattr(self.ui, name, None)
            if btn is None:
                continue
            menu = btn.option_box.menu
            for label, _edge, suffix in self._TRIM_EDGES:
                menu.add(
                    "QPushButton",
                    setText=label,
                    setObjectName=f"{prefix}_{suffix}",
                    setToolTip=f"{label} from {what}.",
                )

    def _setup_space_menu(self) -> None:
        """Attach the add-space actions to the padding spinbox."""
        spn = getattr(self.ui, "spn_space", None)
        if spn is None:
            return
        menu = spn.option_box.menu
        menu.add(
            "QPushButton",
            setText="Add Leading Space",
            setObjectName="btn_add_leading_space",
            setToolTip=(
                "Open this many empty frames at the shot's head.\n"
                "The start stays put; the shot's content, its end,\n"
                "and every downstream shot move later."
            ),
        )
        menu.add(
            "QPushButton",
            setText="Add Trailing Space",
            setObjectName="btn_add_trailing_space",
            setToolTip=(
                "Move the shot's end later by this many frames,\n"
                "pushing the downstream shots along."
            ),
        )

    def _setup_shift_menu(self) -> None:
        """Put Shift To's frame in its option box and name it on the button --
        Apply Gap's shape (2026-10-10: "shift to should be a pushbutton in
        the same style as gap and delete buttons").  A click shifts."""
        btn = getattr(self.ui, "btn_shift_all", None)
        if btn is None:
            return
        spn = btn.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="spn_shift_all",
            setPrefix="Start Frame: ",
            setDecimals=0,
            setMinimum=-100000,
            setMaximum=100000,
            setToolTip="Frame the first shot should start on.",
        )
        spn.restore_state = False
        spn.valueChanged.connect(self.label_shift_all)
        self.label_shift_all()

    def label_shift_all(self, *_args) -> None:
        """Name the frame on Shift To: "Shift To: 1"."""
        btn = getattr(self.ui, "btn_shift_all", None)
        spn = getattr(self.ui, "spn_shift_all", None)
        if btn is not None and spn is not None:
            btn.setText(f"Shift To: {spn.value():g}")

    def _setup_gap_menu(self) -> None:
        """Fill Apply Gap's option box: the amount, its scope, the lock override.

        The amount is the store's (``store.gap``, filled by
        :meth:`_sync_from_store`), so it never restores from QSettings -- that
        carried the last scene's gap into this one.  Out of sight in the option
        box, it is named on the button (:meth:`label_apply_gap`).
        """
        btn = getattr(self.ui, "btn_apply_gap", None)
        if btn is None:
            return
        menu = btn.option_box.menu
        spn = menu.add(
            "QDoubleSpinBox",
            setObjectName="spn_gap",
            setPrefix="Gap: ",
            setMaximum=100000,
            setToolTip="Frames between one shot's end and the next one's start.",
        )
        spn.restore_state = False
        spn.valueChanged.connect(self.label_apply_gap)
        cmb_scope = menu.add(
            self.sb.WidgetComboBox,
            setObjectName="cmb_gap_scope",
            setToolTip="Which shots to apply the gap value to.",
        )
        cmb_scope.addItem("All Shots", "all")
        cmb_scope.addItem("Start", "start")
        cmb_scope.addItem("End", "end")
        cmb_scope.addItem("Start & End", "start_end")
        menu.add(
            "QCheckBox",
            setText="Override Locked Gaps",
            setObjectName="chk_override_locks",
            setChecked=False,
            setToolTip=(
                "Off: a locked gap keeps its own width, and only the others\n"
                "take the gap value.  On: every gap takes it.\n"
                "The locks stay set either way, and only the All Shots scope\n"
                "consults them."
            ),
        )

    def label_apply_gap(self, *_args) -> None:
        """Name the amount on Apply Gap: "Apply Gap: 12"."""
        btn = getattr(self.ui, "btn_apply_gap", None)
        spn = getattr(self.ui, "spn_gap", None)
        if btn is not None and spn is not None:
            btn.setText(f"Apply Gap: {spn.value():g}")

    def _option_checked(self, name: str, default: bool = True) -> bool:
        """State of an option-box checkbox that may not have been built yet."""
        w = getattr(self.ui, name, None)
        return default if w is None else bool(w.isChecked())

    def on_delete_shot(self) -> None:
        """Delete the active shot after confirmation.

        The two option-box toggles decide how much of the shot goes: its keys
        (on by default) and the space it occupied (closed by default).  The
        confirmation spells out whichever combination is armed, because
        "delete" now reaches the animation and the user has to see that
        before it happens.
        """
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        shot = store.shot_by_id(store.active_shot_id)
        if shot is None:
            return

        drop_keys = self._option_checked("chk_delete_contents")
        close_gap = self._option_checked("chk_close_gap")
        detail = [
            "its keyframes" if drop_keys else "the shot record only",
            "closing the gap" if close_gap else "leaving the space",
        ]
        reply = QtWidgets.QMessageBox.question(
            self.ui,
            "Delete Shot",
            f'Delete "{shot.name}" [{shot.start:.0f}\u2013{shot.end:.0f}]\n'
            f"\u2014 {', '.join(detail)}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        seq = self._sequencer_cls()(store=store)
        result = {}

        def _run():
            result.update(
                seq.delete_shot(
                    shot.shot_id,
                    delete_contents=drop_keys,
                    close_gap=close_gap,
                )
            )

        # One undo step either way: cutting the contents lands on the queue,
        # and removing only the record lands scene_edit's own step.  The
        # store drops the active id with the shot.
        if not self._boundary_edit(store, "delshot", _run):
            return
        cut = result.get("curves_cut", 0)
        closed = result.get("closed", 0.0)
        parts = [f"Deleted {result.get('name', shot.name)}"]
        if cut:
            parts.append(f"{cut} curve(s) cleared")
        if closed:
            parts.append(f"closed {closed:.0f}f")
        self._set_footer(" \u00b7 ".join(parts))

    def confirm_removal(self, shots, scope: str = "stale") -> bool:
        """Ask before ``ShotStore.remove_shots_in_scope``, naming *shots*.

        The question is ``ShotReport.removal_question``, the one the Shot
        Sequencer's shot list asks too, so the two entry points cannot drift.
        """
        title, text = ptk.ShotReport.removal_question(shots, scope)
        reply = QtWidgets.QMessageBox.question(
            self.ui,
            title,
            text,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        )
        return reply == QtWidgets.QMessageBox.Yes

    def on_delete_shots(self, scope: str = "stale") -> None:
        """Delete the shots of *scope* after naming them (All Shots group).

        ``"stale"``: every object they name is gone and nothing in their frames
        is keyed -- what a file saved from another keeps of the shots whose
        animation it deleted, which an export ships as takes that hold
        still unless ``ShotStore.drop_stale_shots`` leaves them out.
        ``"empty"``: nothing they name is keyed in their frames.
        ``"all"``: every shot (``ShotStore.shots_in_scope``).  Records only, as
        one undoable edit: no key is touched and no shot moves, where Delete
        cuts the selected shot's keys and closes the gap behind it.
        """
        store = self._active_store()
        if store is None:
            return
        kind = "" if scope == "all" else f"{scope} "
        doomed = store.shots_in_scope(scope)
        if not doomed:
            self._set_footer(f"No {kind}shots")
            return
        if not self.confirm_removal(doomed, scope):
            return
        removed = []
        if self._boundary_edit(
            store,
            f"del{scope}",
            lambda: removed.extend(store.remove_shots_in_scope(scope)),
        ):
            self._set_footer(f"Deleted {len(removed)} {kind}shot(s)")

    def on_move_shot(self) -> None:
        """Move the active shot to the position specified by spn_move_to."""
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return

        spn = getattr(self.ui, "spn_move_to", None)
        if spn is None:
            return

        target_pos = int(spn.value())

        seq = self._sequencer_cls()(store=store)
        if not self._boundary_edit(
            store,
            "reorder",
            seq.move_shot_to_position,
            store.active_shot_id,
            target_pos,
        ):
            return

        # notify_settings_changed → _sync_from_store already rebuilds the
        # combobox; a direct _populate call here doubled the rebuild.
        store.notify_settings_changed()

    def on_swap_shot(self) -> None:
        """Swap With, in the mode its option box picks: trade the active
        shot's timeline place with the picked shot, leaving the checked Retain
        fields in place, or copy the active shot's animation over it."""
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        shot = store.shot_by_id(store.active_shot_id)
        target = self.swap_target()
        other = store.shot_by_id(target) if target is not None else None
        if shot is None or other is None or other is shot:
            return
        names = (shot.name, other.name)
        seq = self._sequencer_cls()(store=store)
        if self.swap_mode() == "copy":
            if not self._boundary_edit(
                store, "copyover", seq.copy_shot_content, shot.shot_id, target
            ):
                return
            self._set_footer(f"Copied {names[0]}'s animation over {names[1]}")
            store.notify_settings_changed()
            return

        retain = self.swap_retain()
        if not self._boundary_edit(
            store, "swapshots", seq.swap_shots, shot.shot_id, target, retain=retain
        ):
            return
        kept = f" \u00b7 kept in place: {', '.join(retain)}" if retain else ""
        self._set_footer(f"Swapped {names[0]} and {names[1]}{kept}")
        store.notify_settings_changed()

    def _report_deltas(self, label: str, deltas: list, store) -> None:
        """Footer + dead-restore-point handling shared by every trim / pad."""
        if not ptk.ShotReport.moved(deltas):
            # Nothing moved: a dead restore point would make the next undo
            # visibly do nothing.
            store.discard_boundary_snapshot()
        self._set_footer(ptk.ShotReport.delta_summary(label, deltas))
        store.notify_settings_changed()

    def on_trim_empty(self, edge: str = "both") -> None:
        """Trim empty space from the active shot, at *edge*.

        *edge* is ``"leading"``, ``"trailing"`` or ``"both"``. Trimming one
        end is the common case when hand-tuning a cut: the other end is
        usually already where the animator put it.
        """
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return

        seq = self._sequencer_cls()(store=store)
        deltas = []

        def _run():
            deltas.append(seq.trim_shot_to_content(store.active_shot_id, edge=edge))

        if not self._boundary_edit(store, "trim", _run):
            return
        self._report_deltas("Trimmed", deltas, store)

    def on_trim_all_shots(self, edge: str = "both") -> None:
        """Trim empty space from every shot, at *edge*."""
        store = self._active_store()
        if store is None or not store.shots:
            return

        seq = self._sequencer_cls()(store=store)
        deltas = []

        def _run():
            # List, not a generator: any() would short-circuit and skip
            # trimming the remaining shots after the first hit.
            deltas.extend(
                [
                    seq.trim_shot_to_content(shot.shot_id, edge=edge)
                    for shot in list(store.shots)
                ]
            )

        if not self._boundary_edit(store, "trimall", _run):
            return
        self._report_deltas("Trimmed", deltas, store)

    def on_shift_all_shots(self, start: float) -> None:
        """Shift every shot so the first one starts on *start*.

        One rigid move: the first shot goes to *start* and the downstream
        ripple carries the rest by the same delta, so the spacing between
        shots -- and the animation inside them -- is preserved.  This is how
        a sequence is re-based onto frame 0, or onto a slate offset, without
        re-timing anything.
        """
        store = self._active_store()
        if store is None or not store.shots:
            return

        seq = self._sequencer_cls()(store=store)
        first = seq.sorted_shots()[0]
        delta = float(start) - first.start
        if abs(delta) < 1e-6:
            self._set_footer(f"All shots already start at {first.start:.0f}")
            return
        if not self._boundary_edit(
            store, "shiftall", seq.move_shot, first.shot_id, float(start)
        ):
            return
        store.notify_settings_changed()
        self._set_footer(f"Shifted all shots by {delta:+.0f}f")

    def on_add_space(self, edge: str = "leading") -> None:
        """Pad the active shot with ``spn_space`` frames of room at *edge*."""
        store = self._active_store()
        if store is None or store.active_shot_id is None:
            return
        spn = getattr(self.ui, "spn_space", None)
        if spn is None:
            return
        frames = float(spn.value())
        if abs(frames) < 1e-6:
            self._set_footer("Add Space: set a frame count first")
            return

        seq = self._sequencer_cls()(store=store)
        deltas = []

        def _run():
            deltas.append(seq.add_shot_space(store.active_shot_id, frames, edge=edge))

        if not self._boundary_edit(store, "addspace", _run):
            return
        self._report_deltas(f"Added {edge} space", deltas, store)
