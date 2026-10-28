# !/usr/bin/python
# coding=utf-8
"""Smart Bake: bake what drives the scene's animation to keys, reversibly.

One Slots class for both hosts over the host toolkit's ``SmartBake``
(``self.tk``), instantiated fresh per bake from the panel's current options:
Maya bakes onto an override or the base animation layer, Blender into a fresh
action over the muted rig. What a bake did is the host's own account
(``BakeResult.describe``); Unbake is ``SmartBake.restore``.
"""

from typing import List, Optional

import pythontk as ptk

from tentacle import Slots


class SmartBakeSlots(Slots, ptk.LoggingMixin):
    # Combo index -> SmartBake(backup_file=...) value. Index is the source of
    # truth so reordering the combo labels can't silently remap the value.
    _BACKUP_MODES = (("Auto", None), ("Always", True), ("Never", False))
    #: The Bake Layer combo's entries, in order (it saves its index): the
    #: first is SmartBake(use_override_layer=True).
    BAKE_LAYERS = ("Override Layer", "Base Layer")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("INFO")
        self.ui = self.sb.loaded_ui.smart_bake

        self.logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        # setup_logging_redirect() defaults its *own* level to INFO, which
        # would silently override the level just set -- pass the resolved
        # level through explicitly so it actually governs verbosity.
        self.logger.setup_logging_redirect(self.ui.txt000, level=self.logger.level)
        self.logger.hide_logger_name(True)
        self.logger.log_timestamp = "%H:%M:%S"

        # Deferred: child widgets (footer, checkboxes, combos) aren't wired
        # onto self.ui until register_children runs after __init__ returns.
        self.sb.QtCore.QTimer.singleShot(0, self._initialize_ui)

    def _initialize_ui(self) -> None:
        """Wire cross-widget behavior and sync the Unbake button to scene state.

        Deferred from __init__ (see there) so the full UI is registered
        before any ``self.ui.<widget>`` access.
        """
        self.sb.add_reset_buttons(self.ui)
        # Bake target is a choice between two named layers, not a modifier.
        self.ui.cmb_bake_layer.add(list(self.BAKE_LAYERS))
        self.ui.cmb_bake_layer.setAsCurrent(self.BAKE_LAYERS[0])  # nondestructive
        self.ui.cmb_bake_layer.currentTextChanged.connect(self._on_bake_layer_changed)
        self._on_bake_layer_changed(self.ui.cmb_bake_layer.currentText())
        self._log_getting_started()
        self._refresh_session_state()

    def _log_getting_started(self) -> None:
        """Print a one-time orientation block to the output panel."""
        self.logger.log_box(
            "Smart Bake",
            [
                "1. Pick Scope — Auto (whole scene, default) or Selected.",
                "2. Adjust the options above, then click Bake.",
                "3. Click Unbake anytime — even after saving and",
                "   reopening the scene — to reverse the last bake.",
            ],
        )

    def _log_run_header(self, title: str) -> None:
        """Blank line + colored section title + divider, opening a new
        bake/unbake report so consecutive runs stay visually distinct."""
        self.logger.log_raw("")
        self.logger.notice(title)
        self.logger.log_divider()

    def _warn(self, msg: str) -> None:
        """Write *msg* to the footer (transient) and the output panel
        (persistent) — every warning in this panel needs both."""
        self.ui.footer.setText(msg, level="warning")
        self.logger.warning(msg)

    def _succeed(
        self,
        msg: str,
        details: Optional[List[str]] = None,
        item_color: Optional[str] = None,
    ) -> None:
        """Write *msg* to the footer (transient) and the output panel
        (persistent). With *details*, renders a colored group; otherwise a
        plain success line."""
        self.ui.footer.setText(msg, level="success")
        if details:
            kwargs = {"item_color": item_color} if item_color else {}
            self.logger.log_group(msg, details, level="SUCCESS", **kwargs)
        else:
            self.logger.success(msg)

    def cmb_scope_init(self, widget) -> None:
        # Auto is index 0 (the default): analyze() + bake() already restrict
        # a whole-scene scope to driven objects, so Auto costs nothing extra
        # over a scan of everything -- it just names what already happens.
        widget.add(["Auto (Whole Scene)", "Selected"])

    def cmb_backup_init(self, widget) -> None:
        widget.add([label for label, _ in self._BACKUP_MODES])

    def header_init(self, widget) -> None:
        """Configure header menu, refresh button, and help text."""
        widget.config_buttons("refresh", "menu", "collapse", "hide")
        widget.refresh_requested.connect(self._refresh_session_state)
        reset = widget.menu.add(
            "QPushButton",
            setText="Reset to Defaults",
            setObjectName="reset_defaults",
        )
        # Every field back to its default, on uitk's shared reset grammar: its
        # tooltip teaches Shift+Click (save as defaults) and Ctrl+Shift+Click.
        self._reset_gesture = self.sb.ResetGesture(reset)
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Smart Bake",
                body="Analyzes the scene for what drives its animation — "
                "constraints, IK, driven keys, expressions, motion paths and "
                "driven blend shapes (in Blender: constraints, IK, drivers and "
                "driven shape keys) — then bakes only what is actually driven; "
                "already-keyed channels are untouched.",
                steps=[
                    "Pick <b>Scope</b> — <b>Auto</b> (default) scans the whole "
                    "scene and bakes only what's actually driven; "
                    "<b>Selected</b> restricts the scan to your selection.",
                    "Adjust the options below and click <b>Bake</b>.",
                    "Click <b>Unbake</b> at any time — even after saving and "
                    "reopening the scene — to reverse the most recent bake.",
                ],
                sections=[
                    (
                        "Safety",
                        [
                            "<b>Override Layer</b> (default) bakes over the "
                            "original animation, which stays connected "
                            "underneath — fully reversible. <b>Base Layer</b> "
                            "bakes into the base animation and disconnects the "
                            "drivers — still reversed by Unbake. (Blender bakes "
                            "into a fresh action and mutes the rig either way.)",
                            "<b>Delete Inputs</b> (Base Layer only) permanently "
                            "removes the drivers. Not reversible by Unbake; a "
                            "scene backup is saved automatically unless Backup "
                            "is set to Never. <b>Mute Drivers</b> mutes them "
                            "instead.",
                        ],
                    )
                ],
            )
        )

    def _on_bake_layer_changed(self, text: str) -> None:
        # delete_inputs is a base-layer-only behavior — ignored (and visibly
        # disabled) whenever the nondestructive override layer is active.
        self.ui.chk_delete_inputs.setDisabled(text == self.BAKE_LAYERS[0])

    def _scope_objects(self) -> Optional[list]:
        """Selected scope -> the selection (possibly empty); Auto -> None
        (SmartBake then scans every candidate in the scene and bakes only the
        ones analyze() finds actually driven)."""
        if self.ui.cmb_scope.currentIndex() == 1:  # Selected
            return list(self.tk.CoreUtils.selected_objects())
        return None

    def _backup_value(self):
        return self._BACKUP_MODES[self.ui.cmb_backup.currentIndex()][1]

    @Slots.Cancelable(180)
    def b000(self, widget) -> None:
        """Bake."""
        objects = self._scope_objects()
        if objects == []:
            # Selected scope with nothing selected must NOT silently
            # escalate to a whole-scene bake (objects=None would).
            self._warn(
                "Nothing selected — select objects, or set Scope to Auto (Whole Scene)."
            )
            return

        self._log_run_header("Bake")

        baker = self.tk.SmartBake(
            objects=objects,
            sample_by=self.ui.spn_sample_by.value(),
            preserve_outside_keys=self.ui.chk_preserve_outside.isChecked(),
            delete_inputs=self.ui.chk_delete_inputs.isChecked(),
            optimize_keys=self.ui.chk_optimize.isChecked(),
            bake_blend_shapes=self.ui.chk_bake_blendshapes.isChecked(),
            # bake_inherited_visibility is deliberately NOT exposed here (Maya
            # only; see the CAUTION on mayatk's SmartBake.__init__): the FBX
            # exporter already resolves inherited visibility, and the one case
            # it fixes is also the shape a RenderOpacity fade has, where baking
            # splits the fade window. The panel cannot tell those apart, so it
            # does not offer the choice.
            use_override_layer=self.ui.cmb_bake_layer.currentText()
            == self.BAKE_LAYERS[0],
            mute_drivers=self.ui.chk_mute_drivers.isChecked(),
            backup_file=self._backup_value(),
        )

        # All footer messaging happens AFTER the progress context: its
        # __exit__ synchronously writes "Complete" to the status label, so
        # text set inside the block would be clobbered on exit.
        result = None
        with self.ui.footer.progress(text="Analyzing scene…") as update:
            self.logger.info("Analyzing scene…")
            analysis = baker.analyze()
            if any(a.requires_bake for a in analysis.values()):
                update(None, "Baking…")
                self.logger.info("Baking…")
                result = baker.bake(analysis)

        if result is None:
            self._warn(
                "Nothing to bake — no constraints, drivers, expressions, IK, or "
                "motion paths detected."
            )
        else:
            self._report_bake_result(result)
        self._refresh_session_state()

    def _report_bake_result(self, result) -> None:
        if not result.success:
            self._warn("Bake produced no output.")
            return

        summary = (
            f"Baked {result.baked_count} object(s), "
            f"range {result.time_range[0]}-{result.time_range[1]}."
        )
        # The host's account of what it baked, declined, muted, deleted and
        # backed up; the session line is this panel's (it names Unbake).
        details = list(result.describe())
        if result.session_id and result.restorable:
            details.append(
                f"Restorable — session '{result.session_id}'. Click Unbake to reverse."
            )
        elif result.session_id:
            details.append(
                f"Session '{result.session_id}' recorded, but a Delete Inputs bake "
                "cannot be fully reversed — Unbake reports what it can't rebuild."
            )
        else:
            details.append("Not restorable.")

        self._succeed(summary, details)

    @Slots.Cancelable(60)
    def b001(self, widget) -> None:
        """Unbake."""
        self._log_run_header("Unbake")
        restore = self.tk.SmartBake.restore()
        if not restore.success:
            self._warn(
                restore.warnings[0] if restore.warnings else "Nothing to restore."
            )
        else:
            summary = f"Restored session '{restore.session_id}'."
            self._succeed(
                summary, restore.warnings, item_color=self.LOG_COLORS["WARNING"]
            )
        self._refresh_session_state()

    def _refresh_session_state(self) -> None:
        # Non-restorable (Delete Inputs) sessions stay clickable on purpose:
        # the click reports what can't be rebuilt and pops the dead entry so
        # any older restorable session becomes reachable on the next click.
        pending = self.tk.SmartBake.list_sessions()
        self.ui.b001.setEnabled(bool(pending))
        self.ui.b001.setToolTip(
            f"Restore the most recent of {len(pending)} pending bake(s)."
            if pending
            else "No bakes pending restore."
        )
