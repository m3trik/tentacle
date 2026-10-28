# !/usr/bin/python
# coding=utf-8
"""Tube Rig: rig a tube-shaped mesh (hose, cable, piston, tail) with joints,
controls and a skin bind, in one click or step by step.

One Slots class for both hosts over the host toolkit's ``TubeRig``
(``self.tk``). The library owns the rig modes (``TubeRig.MODES``), what each
button reads from the selection, the steps themselves and their undo
(``TubeRig.undo_step`` scopes a batch as one step); the panel reads its
widgets, runs the batches with the footer's progress and cancel, and reports.
"""

from tentacle import Slots


class TubeRigSlots(Slots):
    #: Utility buttons -> the ``TubeRig`` method each one needs. Blender's
    #: ``TubeRig`` keeps no rig registry or scene record yet, so it has no
    #: teardown, rename or rebind to find a built rig by; those buttons are
    #: disabled there (``getattr`` gate in ``__init__``) until it does.
    HOST_ONLY = {"b005": "teardown", "b006": "rename", "b007": "rebind_skin"}

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.tube_rig
        # The Mode combo's entries, in order (the combo saves its index).
        self.modes = list(self.tk.TubeRig.MODES)

        # -1 is "Auto": the joint count from the tube's rings, the joint size
        # from the measured tube radius.
        self.ui.s000.setCustomDisplayValues(-1, "Auto")
        self.ui.s002.setCustomDisplayValues(-1, "Auto")

        # The mode names are self-describing under the "Global Options" group,
        # so the combo carries no extra label: a setTextOverlay("Mode:") floated
        # a translucent label ON TOP of the item text, and the two overlapped
        # into an unreadable smear (a themed combo paints its label from its own
        # currentText, so a display-only prefix can't stand in either).
        self.ui.cmb_preset.clear()
        for mode in self.modes:
            self.ui.cmb_preset.addItem(mode.name, mode.strategy)
        self.ui.cmb_preset.currentIndexChanged.connect(self.apply_mode)
        if self.modes:
            self.apply_mode(0)

        # Auto-Bend needs the 3-control spline layout: keep the checkbox gated
        # as the control count changes (apply_mode syncs it per mode).
        self.ui.s001.valueChanged.connect(self._sync_auto_bend_gate)

        for button, method in self.HOST_ONLY.items():
            if getattr(self.tk.TubeRig, method, None) is None:  # Blender, for now
                getattr(self.ui, button).setEnabled(False)

        self._init_tooltips()

        # Keep the window tall enough for the selected step. QToolBox wraps each
        # page in a QScrollArea whose minimum under-reports its content height,
        # so the window's show-time fit leaves a taller step clipped behind a
        # scrollbar. Re-fit the height on page change to sizeHint, which DOES
        # reflect the current page.
        self.ui.toolbox_steps.currentChanged.connect(self._fit_window_to_step)

    def _fit_window_to_step(self, *_) -> None:
        """Fit the window's height to the newly selected toolbox page.

        Resizes the height to ``sizeHint`` (which reflects the current page,
        unlike the ``minimumSizeHint`` the show-time fit targets) and keeps the
        width, so a user-widened panel stays wide. Deferred one event-loop tick
        so the page switch has settled before the window re-measures.
        """
        win = self.ui.window()
        self.sb.QtCore.QTimer.singleShot(
            0, lambda: win.resize(win.width(), win.sizeHint().height())
        )

    def txt000_init(self, widget):
        """Rig-name field — optional, so clearing back to auto-naming is a state."""
        widget.option_box.clear_option = True

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Tube Rig",
                body="Generate joint rigs along tube-shaped meshes (Blender: "
                "an armature's bones). The tool finds the tube's centerline and "
                "sizes the controls to the measured tube radius.",
                sections=[
                    (
                        "Quick start (One-Click)",
                        [
                            "Select a tube mesh.",
                            "Pick a <b>Mode</b> preset — irrelevant options "
                            "disable per mode.",
                            "Press <b>Full Rig</b> — it runs Steps 1 → 2 → 3 "
                            "with the parameter values set in each step page.",
                        ],
                    ),
                    (
                        "Step-by-step",
                        [
                            "<b>Step 1</b> creates the joints, <b>Step 2</b> "
                            "the controls, <b>Step 3</b> the skin bind — the "
                            "same operations One-Click runs, one at a time.",
                            "Each step's tooltip states exactly what to "
                            "select, and in what order.",
                        ],
                    ),
                    (
                        "Utility",
                        [
                            "<b>Add End Constraints</b> pins the tube ends to "
                            "anchor objects.",
                            "<b>Remove Rig</b> / <b>Rename Rig</b> / <b>Rebind "
                            "Skin</b> act on whatever rig the selection touches, "
                            "also on rigs built in an earlier session (Maya "
                            "only for now).",
                        ],
                    ),
                ],
                notes=[
                    "Every button is a <b>single undo</b> — one <b>Ctrl+Z</b> "
                    "reverts a whole build, bind or removal, batch runs "
                    "included. The footer shows what a run is doing; hold "
                    "<b>Esc</b> to cancel a batch.",
                    "<b>Joints = Auto</b> places one joint per edge loop "
                    "(Blender: a default count along the centerline).",
                    "Select several tubes to rig them in one go; a typed "
                    "name is suffixed <b>_01</b>, <b>_02</b>, …",
                ],
            )
        )

    def _init_tooltips(self):
        """Set the polished (uitk ``fmt``) tooltips for every option and step."""
        ui = self.ui
        fmt = self.sb.tooltip.fmt

        ui.cmb_preset.setToolTip(
            fmt(
                title="Rig Mode",
                body="Selects the build strategy and presets the step "
                "parameters below. Options a mode doesn't support are "
                "disabled while it is active.",
                sections=[
                    (
                        "Spline (Hose/Cable)",
                        [
                            "IK-spline chain with start / mid / end controls.",
                            "Good for: hoses, cables, organic tubes.",
                            "Supports: stretch, squash, volume, twist, auto-bend.",
                        ],
                    ),
                    (
                        "Anchor (Piston)",
                        [
                            "Two end controls with distance-driven stretch.",
                            "Good for: pistons, hydraulics, struts.",
                            "Stretch only.",
                        ],
                    ),
                    (
                        "FK Chain (Tail/Tentacle)",
                        [
                            "A few FK controls, each bending its span of "
                            "joints in a smooth arc (Blender: every bone is "
                            "a control).",
                            "Good for: tails, tentacles, cables, hand-keyed tubes.",
                        ],
                    ),
                ],
            )
        )
        ui.txt000.setToolTip(
            fmt(
                title="Rig Name",
                body="Base name for every node the rig creates (group, "
                "joints, controls, skin bind).",
                notes=["Empty = derived from the mesh name."],
            )
        )
        ui.s000.setToolTip(
            fmt(
                title="Number of Joints",
                body="Joint count along the tube centerline.",
                rows=[
                    (
                        "Auto",
                        "one joint per edge loop (Blender: a default count)",
                    ),
                    ("N", "evenly resampled along the centerline"),
                ],
                notes=["Anchor rigs always use their two ends."],
            )
        )
        ui.s001.setToolTip(
            fmt(
                title="Number of Controls",
                body="Driver control count for the Spline and FK rigs. Increase "
                "for complex shapes.",
                notes=[
                    "<b>Auto-Bend</b> requires exactly 3 controls.",
                    "FK: each control bends its span of joints; a count at or "
                    "above the joint count gives one control per joint "
                    "(Blender's FK makes every bone a control).",
                ],
            )
        )
        ui.s002.setToolTip(
            fmt(
                title="Joint Size",
                body="Joint display radius in the viewport (Blender: the bone radius).",
                rows=[("Auto", "half the measured tube radius")],
                notes=[
                    "Display only — control sizes always scale to the "
                    "measured tube radius."
                ],
            )
        )
        ui.chk000.setToolTip(
            fmt(
                title="Reverse Direction",
                body="Builds the chain from the tube's other end: the ROOT (the "
                "end that stays put; FK rotation carries toward the tip) and the "
                "TIP swap ends.",
                notes=[
                    "Applies to every build: Step 1 and <b>One-Click</b>.",
                    "Rigged the wrong way round? Toggle it and rebuild — a "
                    "plug pulled out of its top wants its root at the bottom.",
                ],
            )
        )
        ui.chk_stretch.setToolTip(
            fmt(
                title="Stretch",
                bullets=[
                    "<b>Spline:</b> joints scale along the tube to follow "
                    "the curve length.",
                    "<b>Anchor:</b> the start joint stretches toward the end control.",
                ],
            )
        )
        ui.chk_twist.setToolTip(
            fmt(
                title="Twist",
                body="Spline twist driven by a roll control at the tube's end.",
                notes=[
                    "Spline only. Maya: a <b>roll</b> attribute on the end "
                    "control; Blender: a roll-control bone at the tip."
                ],
            )
        )
        ui.chk_squash.setToolTip(
            fmt(
                title="Squash",
                body="Joints compress when the curve shortens.",
                notes=["Spline only."],
            )
        )
        ui.chk_volume.setToolTip(
            fmt(
                title="Volume Preservation",
                body="Bulges when squashed, thins when stretched.",
                notes=["Spline only."],
            )
        )
        ui.chk_auto_bend.setToolTip(
            fmt(
                title="Auto-Bend (Mid)",
                body="The mid control bows outward automatically as the ends "
                "compress toward each other.",
                notes=["Spline only — requires exactly <b>3</b> controls."],
            )
        )
        ui.b001.setToolTip(
            fmt(
                title="Step 1 — Create Joints",
                body="Places this rig's joints along the tube's centerline.",
                steps=[
                    "Select the tube mesh <i>(Maya: or an edge loop running "
                    "down it; Blender: or its edges in Edit Mode)</i>.",
                    "Press <b>Create Joints</b>.",
                ],
                notes=[
                    "Anchor mode creates its two end joints instead of a chain.",
                    "Maya: re-running replaces this rig's previous joints.",
                ],
            )
        )
        ui.b002.setToolTip(
            fmt(
                title="Step 2 — Create Controls",
                body="Builds the active mode's control rig on the joints from Step 1.",
                steps=[
                    "Select the root joint <i>(Anchor: either or both end "
                    "joints)</i>; in Blender, the armature.",
                    "Press <b>Create IK / Controls</b>.",
                ],
                sections=[
                    (
                        "Creates",
                        [
                            "<b>Spline:</b> IK spline, start/mid/end controls, "
                            "twist, stretch, auto-bend.",
                            "<b>Anchor:</b> two end controls with distance stretch.",
                            "<b>FK:</b> FK controls, each bending its span of joints.",
                        ],
                    ),
                ],
                notes=[
                    "Control size is proportional to the tube's radius.",
                    "A chain that already has controls is refused: remove "
                    "them first, or rebuild with One-Click Rig.",
                ],
            )
        )
        ui.b003.setToolTip(
            fmt(
                title="Step 3 — Bind Skin",
                body="Binds the tube mesh to the joints (Maya: ring-uniform "
                "parametric weights, the solver the One-Click build uses; "
                "Blender: an Armature modifier with automatic weights).",
                steps=[
                    "Select the root joint, then <b>Shift</b>-select the tube "
                    "mesh <i>last</i>; in Blender, the armature and the mesh.",
                    "Press <b>Bind Joints to Mesh</b>.",
                ],
                notes=["Maya: re-running replaces the mesh's existing skinCluster."],
            )
        )
        ui.b004.setToolTip(
            fmt(
                title="Constrain Ends to Anchors",
                body="Constrains one or both tube ends to external anchor "
                "objects (each end's control follows its anchor) with "
                "distance-falloff skin weighting at the contact points.",
                steps=[
                    "Select the root joint (Blender: the armature).",
                    "<b>Shift</b>-select the anchor object(s) — one per end to "
                    "constrain.",
                    "Press <b>Add End Constraints</b>.",
                ],
                notes=[
                    "Requires a bound tube — run <b>Step 3</b> first.",
                    "Each anchor constrains its nearest tube end — selection "
                    "order doesn't matter. A single anchor leaves the other end "
                    "free (a plugged-in loom whose base is part of the module).",
                    "Re-anchoring an end replaces its previous anchor.",
                    "Falloff spans ≈2× the tube radius.",
                ],
            )
        )
        ui.b005.setToolTip(
            fmt(
                title="Remove Rig",
                body="Deletes the rig — joints, controls, IK, utility nodes and "
                "the skin bind — and restores the mesh's viewport display. The "
                "tube mesh itself is kept.",
                steps=[
                    "Select the tube mesh, or any joint / control of the rig(s).",
                    "Press <b>Remove Rig</b>.",
                ],
                notes=[
                    "Works on rigs built in an earlier session — the rig is "
                    "read back from the scene.",
                    "Several rigs selected are removed together, in one undo step.",
                    "Maya only for now.",
                ],
            )
        )
        ui.b006.setToolTip(
            fmt(
                title="Rename Rig",
                body="Renames every node of the rig — group, joints, controls, "
                "sets and utility nodes — to the name in the <b>Rig Name</b> "
                "field.",
                steps=[
                    "Type the new name in <b>Rig Name</b>.",
                    "Select the tube mesh, or any joint / control of the rig.",
                    "Press <b>Rename Rig</b>.",
                ],
                notes=[
                    "One rig at a time.",
                    "Referenced rigs can't be renamed — rename them in their "
                    "source scene.",
                    "Maya only for now.",
                ],
            )
        )
        ui.b007.setToolTip(
            fmt(
                title="Rebind Skin",
                body="Re-solves the tube's bind from the rig already in the "
                "scene. Use it when the mesh stopped following the controls "
                "but the joints and controls are still there — a UV unwrap, "
                "<b>Delete History</b> or <b>Bake Non-Deformer History</b> on "
                "the tube removes the skinCluster and leaves everything else "
                "standing.",
                steps=[
                    "Select the tube mesh, or any joint / control of the rig.",
                    "Press <b>Rebind Skin</b>.",
                ],
                sections=[
                    (
                        "Older rigs",
                        [
                            "A rig built before the scene record existed is "
                            "linked to its tube only THROUGH the bind, so once "
                            "the bind is gone the tube looks like plain "
                            "geometry.",
                            "Select the tube <b>and</b> one of the rig's joints "
                            "or controls together — one rig, one tube at a time.",
                            "Only needed once: the rebind stamps the record.",
                        ],
                    ),
                ],
                notes=[
                    "Joints, controls and their animation are untouched "
                    "(unlike <b>One-Click Rig</b>, which rebuilds from "
                    "scratch).",
                    "Rebind at the rig's DEFAULT pose: a bind destroyed while "
                    "the rig was posed has already baked that pose into the "
                    "mesh, and no rebind can undo that.",
                    "Maya only for now.",
                ],
            )
        )
        ui.b000.setToolTip(
            fmt(
                title="One-Click Rig",
                body="Runs <b>Step 1 → Step 2 → Step 3</b> in order, using "
                "the parameter values set in each step's page.",
                steps=[
                    "Select the tube mesh <i>(or several, to rig each)</i>.",
                    "Press <b>Full Rig</b>.",
                ],
                notes=[
                    "Maya: rebuilding on an already-rigged mesh tears the old "
                    "rig down first. Blender builds a second rig beside it, so "
                    "delete the old one first.",
                    "<b>Ctrl+Z</b> reverts the whole run in one step.",
                ],
            )
        )

    # ------------------------------------------------------------------ modes
    def _sync_auto_bend_gate(self, *_):
        """Gate Auto-Bend on the 3-control spline layout."""
        mode = self.get_mode()
        allowed = bool(
            mode and mode.auto_bend_editable and int(self.ui.s001.value()) == 3
        )
        self.ui.chk_auto_bend.setEnabled(allowed)
        if not allowed:
            self.ui.chk_auto_bend.setChecked(False)

    def _mode_at(self, index: int):
        """The mode at *index* (the first for an unset or stale index)."""
        if 0 <= index < len(self.modes):
            return self.modes[index]
        return self.modes[0] if self.modes else None

    def apply_mode(self, index: int):
        """Apply a mode's values and constraints to the option widgets."""
        mode = self._mode_at(index)
        if mode is None:
            return
        ui = self.ui
        ui.s000.setValue(mode.num_joints)
        ui.s000.setEnabled(mode.num_joints_editable)
        ui.s001.setValue(mode.num_controls)
        ui.s001.setEnabled(mode.num_controls_editable)
        for widget, value, editable in (
            (ui.chk_stretch, mode.enable_stretch, mode.stretch_editable),
            (ui.chk_squash, mode.enable_squash, mode.squash_editable),
            (ui.chk_volume, mode.enable_volume, mode.volume_editable),
            (ui.chk_auto_bend, mode.enable_auto_bend, mode.auto_bend_editable),
            (ui.chk_twist, mode.enable_twist, mode.twist_editable),
        ):
            widget.setChecked(value)
            widget.setEnabled(editable)
        self._sync_auto_bend_gate()

    def get_mode(self):
        """The current rig mode (a ``TubeRig.MODES`` entry)."""
        return self._mode_at(self.ui.cmb_preset.currentIndex())

    def get_strategy(self) -> str:
        """The current mode's strategy name (``spline`` / ``anchor`` / ``fk``)."""
        return self.get_mode().strategy

    # ------------------------------------------------------------------ helpers
    def _rig_name(self) -> str:
        """The Rig Name field's text ("" when left to the default)."""
        return (self.ui.txt000.text() or "").strip()

    def _batch_names(self, count: int) -> list:
        """Per-tube rig names for a batch: the typed name suffixed ``_01``,
        ``_02``, ... when several tubes share it; None (the per-mesh auto name)
        when the field is empty."""
        typed = self._rig_name()
        if not typed or count == 1:
            return [typed or None] * count
        return [f"{typed}_{i + 1:02d}" for i in range(count)]

    def _deform_options(self) -> dict:
        """The Step 2 page's toggles, as the engine's keywords."""
        ui = self.ui
        return dict(
            enable_stretch=ui.chk_stretch.isChecked(),
            enable_squash=ui.chk_squash.isChecked(),
            enable_volume=ui.chk_volume.isChecked(),
            enable_twist=ui.chk_twist.isChecked(),
            enable_auto_bend=ui.chk_auto_bend.isChecked(),
        )

    @staticmethod
    def _batch_summary(what: str, done: list, failed: list) -> str:
        lines = []
        if done:
            lines.append(f"{what}: {', '.join(done)}")
        if failed:
            lines.append(
                "Failed:\n  "
                + "\n  ".join(f"{label}: {error}" for label, error in failed)
            )
        return "\n".join(lines)

    @staticmethod
    def _cancel_note(remaining: int) -> str:
        """Say so when the user cancelled a batch — and that undo is still one step.

        The whole run is one undo step, so a half-finished batch is not a mess
        to clean up by hand; saying that is the difference between a cancel the
        user trusts and one they don't. ``0`` (a completed run) says nothing.
        """
        if remaining <= 0:
            return ""
        return (
            f"<br><br>Cancelled with {remaining} left — Ctrl+Z reverts the "
            "whole run in one step."
        )

    @staticmethod
    def _label(item) -> str:
        """A batch item's name for the footer and the report: a rig's name, an
        object's name, or a node path's last segment."""
        name = (
            getattr(item, "rig_name", None) or getattr(item, "name", None) or str(item)
        )
        return str(name).rsplit("|", 1)[-1]

    @staticmethod
    def _prefixed(hook, prefix: str):
        """*hook* with *prefix* (a batch's ``[2/5]`` counter, which the engine
        cannot know about) prepended to every phase message it carries."""
        if not prefix:
            return hook

        def prefixed(current=None, total=0, message=None):
            return hook(current, total, f"{prefix}{message}" if message else message)

        return prefixed

    def _run_batch(self, items, operation, verb: str, undo_name: str, text: str):
        """Run ``operation(item, progress)`` over *items* as ONE undo step.

        ``TubeRig.undo_step`` scopes the step (Maya also holds the viewport
        still; Blender recompiles the rig drivers after its push). Each item is
        announced on the footer with a ``[2/5]`` counter that the operation's own
        phase reports inherit, because the viewport shows nothing while a rig
        builds. An item that raises is recorded and the batch goes on; the
        footer's Esc cancel stops it before the next item, and what already ran
        stays in the same undo step.

        Returns:
            tuple: ``(done, failed, skipped)`` -- ``[(label, result)]`` for the
            items that ran, ``[(label, error)]`` for those that raised, and the
            count never reached. Counted from the loop index, so an item that
            FAILED is not also counted as skipped.
        """
        done, failed, skipped = [], [], 0
        total = len(items)
        with self.tk.TubeRig.undo_step(undo_name):
            with self.ui.footer.progress(text=text) as update:
                hook = self.sb.progress_adapter(update)
                for i, item in enumerate(items):
                    prefix = f"[{i + 1}/{total}] " if total > 1 else ""
                    label = self._label(item)
                    if not update(None, f"{prefix}{verb} {label}…"):
                        skipped = total - i
                        break
                    try:
                        done.append(
                            (label, operation(item, self._prefixed(hook, prefix)))
                        )
                    except Exception as error:
                        failed.append((label, str(error)))
                        self.sb.logger.error(
                            f"{verb} {label} failed: {error}", exc_info=True
                        )
        return done, failed, skipped

    def _unsupported(self, button: str) -> bool:
        """True (and says so) when this host's ``TubeRig`` lacks *button*'s
        operation: its widget is disabled, but a repeat-last can still call it."""
        if getattr(self.tk.TubeRig, self.HOST_ONLY[button], None) is not None:
            return False
        self.sb.message_box("Not available in this application yet.")
        return True

    # ------------------------------------------------------------------ steps
    def b000(self):
        """One-Click Rig — runs Steps 1 → 2 → 3 with the step parameters,
        once per selected tube."""
        tubes = self.tk.TubeRig.selected_tubes()
        if not tubes:
            self.sb.message_box("Select one or more polygon tube meshes to rig.")
            return
        strategy = self.get_strategy()
        names = dict(zip(tubes, self._batch_names(len(tubes))))
        options = dict(
            num_joints=int(self.ui.s000.value()),
            num_controls=int(self.ui.s001.value()),
            radius=self.ui.s002.value(),
            reverse=self.ui.chk000.isChecked(),
            edges=self.tk.TubeRig.selected_edges(),
            **self._deform_options(),
        )

        def build(tube, progress):
            rig = self.tk.TubeRig.for_build(tube, rig_name=names[tube])
            rig.build(strategy=strategy, progress=progress, **options)
            return rig.rig_name

        done, failed, skipped = self._run_batch(
            tubes, build, "Rigging", "Tube Rig: Full Rig", "Tube Rig: building…"
        )
        self.sb.message_box(
            self._batch_summary(
                f"Tube rig ({strategy}) created", [name for _, name in done], failed
            )
            + self._cancel_note(skipped)
        )

    def b001(self):
        """Step 1: Create Joints from Tube — once per selected tube."""
        tubes = self.tk.TubeRig.selected_tubes()
        if not tubes:
            self.sb.message_box(
                "Select the tube mesh (or an edge loop on it) to create joints."
            )
            return
        strategy = self.get_strategy()
        names = dict(zip(tubes, self._batch_names(len(tubes))))
        options = dict(
            num_joints=int(self.ui.s000.value()),
            radius=self.ui.s002.value(),
            reverse=self.ui.chk000.isChecked(),
            edges=self.tk.TubeRig.selected_edges(),
        )

        def create(tube, progress):
            rig = self.tk.TubeRig.for_build(tube, rig_name=names[tube])
            return rig.create_joints(strategy, **options)

        done, failed, skipped = self._run_batch(
            tubes,
            create,
            "Creating joints on",
            "Tube Rig: Create Joints",
            "Tube Rig: creating joints…",
        )
        counts = [
            f"{len(joints)} ({label})" if len(tubes) > 1 else str(len(joints))
            for label, joints in done
        ]
        if counts or failed:
            self.sb.message_box(
                self._batch_summary("Joints created", counts, failed)
                + self._cancel_note(skipped)
            )
        elif skipped:  # cancelled before the first tube: silence reads as broken
            self.sb.message_box(f"No joints created.{self._cancel_note(skipped)}")

    def b002(self):
        """Step 2: Create IK / Controls (mode dependent) on the selected chain."""
        try:
            with self.ui.footer.progress(text="Tube Rig: creating controls…") as update:
                update()
                kind, joints, controls = self.tk.TubeRig.create_controls_from_selection(
                    self.get_strategy(),
                    num_controls=int(self.ui.s001.value()),
                    rig_name=self._rig_name() or None,
                    **self._deform_options(),
                )
        except ValueError as error:  # the selection, refused with the fix
            self.sb.message_box(str(error))
            return
        self.sb.message_box(
            f"{kind} controls created on {len(joints)} joints.\n"
            f"Controls: {', '.join(controls)}"
        )

    def b003(self):
        """Step 3: Bind the joint chain to the tube."""
        try:
            with self.ui.footer.progress(text="Tube Rig: binding skin…") as update:
                update()
                mesh, count, skin = self.tk.TubeRig.bind_from_selection(
                    self.get_strategy(), rig_name=self._rig_name() or None
                )
        except (ValueError, RuntimeError) as error:
            self.sb.message_box(str(error))
            return
        self.sb.message_box(f"Skinned '{mesh}' to {count} joints ({skin}).")

    def b004(self):
        """Utility: Constrain Ends to Anchors — one anchor or both, each to its
        nearest tube end."""
        try:
            with self.ui.footer.progress(text="Tube Rig: constraining ends…") as update:
                results = self.tk.TubeRig.constrain_ends_from_selection(
                    self.get_strategy(),
                    rig_name=self._rig_name() or None,
                    progress=self.sb.progress_adapter(update),
                )
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        lines = [
            f"  {end} <- {anchor}: {result or 'failed'}"
            for end, anchor, result in results
        ]
        self.sb.message_box("End constraints added:\n" + "\n".join(lines))

    def b005(self):
        """Utility: Remove Rig — tear down every rig the selection touches."""
        if self._unsupported("b005"):
            return
        rigs = self.tk.TubeRig.selected_rigs()
        if not rigs:
            self.sb.message_box(
                "Select the tube mesh, or any joint / control of the rig(s) to remove."
            )
            return
        done, failed, skipped = self._run_batch(
            rigs,
            lambda rig, progress: rig.teardown(progress=progress),
            "Removing",
            "Tube Rig: Remove",
            "Tube Rig: removing…",
        )
        self.sb.message_box(
            self._batch_summary("Rig removed", [label for label, _ in done], failed)
            + self._cancel_note(skipped)
        )

    def b006(self):
        """Utility: Rename Rig — to the Rig Name field, every node included."""
        if self._unsupported("b006"):
            return
        new_name = self._rig_name()
        if not new_name:
            self.sb.message_box("Type the new name in the Rig Name field first.")
            return
        rigs = self.tk.TubeRig.selected_rigs()
        if len(rigs) != 1:
            self.sb.message_box(
                "Select the tube mesh, or any joint / control of ONE rig to rename."
                if not rigs
                else f"Select one rig at a time (got {len(rigs)})."
            )
            return
        old = rigs[0].rig_name
        try:
            with self.ui.footer.progress(
                text=f"Tube Rig: renaming {old} → {new_name}…"
            ) as update:
                update()
                renamed = rigs[0].rename(new_name)
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        if renamed == old:
            self.sb.message_box(f"Rig name unchanged: {old}")
            return
        self.sb.message_box(f"Rig renamed: {old} -> {renamed}")

    def b007(self):
        """Utility: Rebind Skin — re-solve the bind for every rig the selection
        touches (a lone unlinked mesh pairs with a lone rig)."""
        if self._unsupported("b007"):
            return
        try:
            rigs, mesh = self.tk.TubeRig.selected_rebind_targets()
        except ValueError as error:
            self.sb.message_box(str(error))
            return
        done, failed, skipped = self._run_batch(
            rigs,
            lambda rig, progress: rig.rebind_skin(mesh=mesh),
            "Rebinding",
            "Tube Rig: Rebind Skin",
            "Tube Rig: rebinding skin…",
        )
        self.sb.message_box(
            self._batch_summary("Skin rebound", [label for label, _ in done], failed)
            + self._cancel_note(skipped)
        )
