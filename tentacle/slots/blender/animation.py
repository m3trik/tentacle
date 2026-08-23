# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle import AnimationMixin, SlotsBlender


class Animation(AnimationMixin, SlotsBlender):
    """Blender port of the shared ``animation`` menu.

    Every key operation (invert/stagger/snap/scale/step/move/spacing/align/copy/paste/
    transfer/intermediate/select/visibility-keys) is plain math over
    ``fcurve.keyframe_points`` via ``blendertk.anim_utils`` — the §5 finding that animation
    is volume, not difficulty. The shot sequencer/manifest windows are native blendertk
    panels (``anim_utils/shots``, shipped 2026-07-11) launched from ``b000``/``b004``.
    Option-box widget names reused from Maya carry the same option (cross-DCC
    QSettings rule).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.animation
        self._copied_action = None

    #: ``category -> [(label, objectName, tooltip)]`` for the header Tools list
    #: (was five separator sections of loose header buttons). Mirror of the Maya
    #: animation Tools list; Sequencing (Shot Manifest / Shot Sequencer) launches
    #: the native blendertk shots panels (added 2026-07-12, after the Shots trio
    #: shipped — previously omitted as Maya-only). Only Maya's Repair Visibility
    #: Tangents stays omitted rather than shown as a dead entry. Reused
    #: objectNames carry the Maya label verbatim (cross-DCC QSettings rule).
    _TOOLS_ITEMS = {
        "Sequencing": [
            (
                "Shot Manifest",
                "b004",
                "Import a CSV sequence document and build scenes.",
            ),
            (
                "Shot Sequencer",
                "b000",
                "Open the sequencer for managing per-scene animation with ripple editing.",
            ),
        ],
        "Repair": [
            (
                "Repair Corrupted Curves",
                "tb015",
                "Remove corrupted keyframes (NaN/infinite values, absurd key times) and "
                "delete curves left with no valid keys.\nUse the option box to choose which fixes apply.",
            ),
        ],
        "Bake": [
            (
                "Smart Bake",
                "tb020",
                "Open the Smart Bake panel.\n"
                "Analyzes and bakes constraints, drivers/expressions, IK, and blend shapes\n"
                "— with a one-click Unbake to reverse the most recent bake, even after a "
                "scene reopen.",
            ),
        ],
        "Playback": [
            (
                "Fit Playback Range",
                "b005",
                "Set the playback range to the keyed extent of the selection, "
                "or of the whole scene when nothing is selected.",
            ),
        ],
        "Info": [
            (
                "Get Animation Info",
                "tb016",
                "Show a per-object keyframe summary (range / channels / keys) in a viewer.\n"
                "Use the option box to choose scope (Selected / All) and sort order.",
            ),
        ],
    }

    def list000_init(self, widget):
        """Tools list: Sequencing / Repair / Bake / Playback / Info.

        Rows are plain labels dispatched by ``list000``, EXCEPT entries whose
        slot defines an ``*_init``: that init builds the option box (tb015,
        tb016), which is lost on a plain label, so those are added as real
        slot-wired widgets carrying their original objectNames.

        The submenu hosts the same list where the Shot Sequencer / Shot
        Manifest buttons used to sit (upper-left of the radial overlay), so it
        opens upward over itself and fans left; the panel row fans right.
        Category order follows suit: the upward flyout is anchored at the
        trigger's bottom edge, so its LAST-added row is the one that lands
        under the cursor — populated in reverse there to put Sequencing (the
        two buttons this list replaced) where those buttons used to be. The
        panel's flyout fans right with its top row on the trigger, so it keeps
        natural order.
        """
        submenu = widget.ui.has_tags("submenu")
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay_up_left" if submenu else "hover_menu")
        root = widget.add(
            "Tools",
            setToolTip="Sequencing, repair, bake, playback and info tools.",
        )
        categories = list(self._TOOLS_ITEMS.items())
        if submenu:
            categories.reverse()
        for category, items in categories:
            cat = root.sublist.add(category)
            for label, slot_name, *rest in items:
                tooltip = rest[0] if rest else ""
                if slot_name and hasattr(self, f"{slot_name}_init"):
                    self.add_slot_widget(
                        cat.sublist,
                        setObjectName=slot_name,
                        setText=label,
                        setToolTip=tooltip,
                    )
                else:
                    cat.sublist.add(label, setToolTip=tooltip)

    @SlotsBlender.Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch a Tools leaf to its slot method."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        parent = item.parent_item_text() or ""
        for label, slot_name, *_ in self._TOOLS_ITEMS.get(parent, ()):
            if label == text:
                slot = getattr(self, slot_name, None)
                if not callable(slot):
                    return
                # Slots vary: some take the invoking widget, some take none.
                try:
                    slot(item)
                except TypeError:
                    slot()
                return

    # ------------------------------------------------------------------ tb000  Go To Frame
    def tb000_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Go To Frame")
        m.add(
            "QSpinBox", setPrefix="Frame: ", setObjectName="s000",
            set_limits=[-999999, 999999], setValue=0,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_FRAME),
        )
        cmb = m.add(
            "QComboBox", setObjectName="cmb000",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_MODE),
        )
        for text, data in [("Mode: Absolute", "Absolute"), ("Mode: Relative", "Relative")]:
            cmb.addItem(text, data)
        cmb.setCurrentIndex(1)  # default Relative (Maya parity — keeps chk010's ±1 a nudge, not a jump to frame ±1)
        cmb001 = m.add(
            "QComboBox", setObjectName="cmb001",
            setToolTip=self.sb.tooltip.fmt(
                title="Snap",
                body="Re-round the <b>current</b> frame to a clean number. Any "
                "mode but None overrides Frame/Mode above — nothing jumps, the "
                "playhead is snapped where it already stands.",
                bullets=[
                    "<b>None</b> — no snapping; Frame/Mode drive the move.",
                    "<b>Preferred</b> — snap to a clean number only when very "
                    "close (24 &#8594; 25, 99 &#8594; 100).",
                    "<b>Aggressive</b> — snap to a clean number even from "
                    "farther out (48 &#8594; 50, 73 &#8594; 75).",
                    "<b>Nearest / Floor / Ceil</b> — plain rounding of a "
                    "fractional playhead to a whole frame.",
                ],
                notes=[
                    "Blender reads the sub-frame playhead where it can, so "
                    "these are meaningful mid-scrub.",
                    "Only Floor and Ceil respond to <b>Invert</b> below — it "
                    "swaps the two.",
                ],
            ),
        )
        # Nearest/Floor/Ceil are APPENDED, not inserted in rounding order: the
        # combo persists by index, so reordering would repoint a stored choice.
        for text, data in [
            ("Snap: None", "none"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive"),
            ("Snap: Nearest", "nearest"),
            ("Snap: Floor", "floor"),
            ("Snap: Ceil", "ceil"),
        ]:
            cmb001.addItem(text, data)
        m.add(
            self.sb.registered_widgets.Label, setText="Set To Current Frame", setObjectName="lbl020",
            setToolTip=self.TIP_GOTO_SET_TO_CURRENT,
        )
        m.lbl020.clicked.connect(lambda: m.s000.setValue(bpy.context.scene.frame_current))
        m.add(
            "QCheckBox", setText="Toggle Single frame", setObjectName="chk010", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_SINGLE_FRAME),
        )
        widget._previous_frame_value = 1

        def toggle_single_frame(state):
            spinbox = m.s000
            if state:
                widget._previous_frame_value = spinbox.value() or 1
                spinbox.setValue(-1 if widget._previous_frame_value > 0 else 1)
            else:
                spinbox.setValue(widget._previous_frame_value)

        m.chk010.toggled.connect(toggle_single_frame)
        m.add(
            "QCheckBox", setText="Invert", setObjectName="chk011", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_INVERT),
        )

        def toggle_inverted(state):
            spinbox = m.s000
            spinbox.setValue(-spinbox.value())

        m.chk011.toggled.connect(toggle_inverted)

        def update_invert_checkbox(value):
            block = m.chk011.blockSignals(True)
            m.chk011.setChecked(value < 0)
            m.chk011.blockSignals(block)

        m.s000.valueChanged.connect(update_invert_checkbox)

        # Snapping re-rounds the CURRENT frame, so the frame-entry controls
        # have nothing to feed and grey out for every mode but None.
        self.sb.enable_when(m, "s000,cmb000,lbl020,chk010", "cmb001", "none")
        # Invert needs a direction to reverse: the Frame field's sign, or a
        # directional snap. The clean-number modes have neither.
        self.sb.enable_when(m, "chk011", "cmb001", {"none", "floor", "ceil"})

    def tb000(self, widget):
        """Go To Frame (absolute, or relative offset from the current frame); the Snap combo
        overrides both and re-rounds the CURRENT frame to a clean number instead."""
        m = widget.option_box.menu
        snap_mode = m.cmb001.currentData()
        invert = m.chk011.isChecked()
        if snap_mode and snap_mode != "none":
            btk.set_current_frame(time=None, snap_mode=snap_mode, invert_snap=invert)
            return
        btk.set_current_frame(
            time=m.s000.value(), relative=m.cmb000.currentData() == "Relative"
        )

    # ------------------------------------------------------------------ key-timing ops
    # Inversion mode (reuses Maya's cmb035 items + d000 pivot — cross-DCC QSettings rule).
    # Item DATA matches Maya's ("horizontal"/"vertical"/"both") so the shared
    # ``enable_when`` rules read the same values; the map converts to btk's mode.
    _INVERT_MODE_ITEMS = (
        ("Mode: X", "horizontal"),
        ("Mode: Y", "vertical"),
        ("Mode: X & Y", "both"),
    )
    _INVERT_MODES = {"horizontal": "time", "vertical": "value", "both": "both"}

    def tb001_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Invert Keys")
        cmb = m.add(
            "QComboBox", setObjectName="cmb035",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INVERT_MODE),
        )
        for text, data in self._INVERT_MODE_ITEMS:
            cmb.addItem(text, data)
        m.add(
            self.sb.registered_widgets.SpinBox, setPrefix="Time: ", setObjectName="s001",
            set_limits=[-100000, 100000], setValue=-1, setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Time",
                bullets=[
                    "<b>Auto</b> (-1, default) — mirror the keys <b>in place</b>: "
                    "the animation reverses inside its own range. A move, not a "
                    "copy, so Relative and Delete Original do not apply.",
                    "<b>Any other value</b> — leave the source alone and place a "
                    "<b>reversed copy</b> ending here.",
                ],
            ),
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Pivot: ", setObjectName="d000",
            set_limits=[-100000, 100000], setValue=0.0,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INVERT_PIVOT),
        )
        m.add(
            "QCheckBox", setText="Relative", setObjectName="chk002", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INVERT_RELATIVE),
        )
        m.add(
            "QCheckBox", setText="Delete Original", setObjectName="chk005", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Delete Original",
                body="Remove the source keys once the reversed copy is placed, "
                "turning the copy into a move.",
                notes=[
                    "Already implied when Time is Auto — an in-place mirror is "
                    "a move by definition.",
                    "A source key that lands on the same frame and value as a "
                    "copy key is kept; the copy already occupies that point.",
                ],
            ),
        )

        # Time controls apply to the X (horizontal) axis, the value pivot to Y.
        # Relative/Delete Original describe the reversed COPY, so they also go
        # dead at Time = Auto, where invert_keys mirrors in place and ignores
        # both (see btk.invert_keys).
        self.sb.enable_when(m, "s001", "cmb035", {"horizontal", "both"})
        self.sb.enable_when(m, "d000", "cmb035", {"vertical", "both"})
        self.sb.enable_when(
            m,
            "chk002,chk005",
            ["cmb035", "s001"],
            lambda mode, time: mode in {"horizontal", "both"} and time != -1,
        )

    @btk.undoable
    def tb001(self, widget):
        """Invert Keys (mirror key times and/or values — reverses timing / flips motion)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Invert Keys requires a selection.")
            return
        m = widget.option_box.menu
        mode = self._INVERT_MODES.get(m.cmb035.currentData(), "time")
        time_value = m.s001.value()
        btk.invert_keys(
            objects,
            mode=mode,
            value_pivot=m.d000.value(),
            start_frame=None if time_value == -1 else time_value,
            relative=m.chk002.isChecked(),
            delete_original=m.chk005.isChecked(),
        )

    def tb003_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Stagger Keys")
        m.add(
            "QSpinBox", setPrefix="Start Frame: ", setObjectName="s005",
            set_limits=[-100000, 100000], setValue=-1,
            setToolTip=self.sb.tooltip.fmt(
                title="Start Frame",
                body="Where the first block's animation begins.",
                notes=["<b>-1</b> leaves the first block exactly where it is."],
            ),
        )
        # Integer, unlike Maya's: btk.stagger_keys has no percentage-of-duration
        # mode, so a fractional value here would only produce off-grid keys.
        m.add(
            "QSpinBox", setPrefix="Spacing: ", setObjectName="s004",
            set_limits=[-100000, 100000], setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Spacing",
                sections=[
                    (
                        "Sequential (Use Intervals off)",
                        [
                            "<b>0</b> (default) — blocks run end-to-start with "
                            "no gap.",
                            "<b>Positive</b> — that many frames of gap.",
                            "<b>Negative</b> — that many frames of overlap.",
                        ],
                    ),
                    (
                        "Use Intervals on",
                        [
                            "The fixed interval between block starts — "
                            "<code>100</code> places blocks at 0, 100, 200…",
                        ],
                    ),
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Use Intervals", setObjectName="chk025", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Intervals",
                body="Place each block on a fixed grid instead of packing them "
                "end-to-start.",
                bullets=[
                    "<b>Off</b> (default) — each block starts where the previous "
                    "one ended, plus <b>Spacing</b>.",
                    "<b>On</b> — <b>Spacing</b> becomes the interval between "
                    "block starts (100 &#8594; frames 0, 100, 200…).",
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Invert", setObjectName="chk008", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_STAGGER_INVERT),
        )
        m.add(
            "QCheckBox", setText="Group Overlapping", setObjectName="chk014", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_STAGGER_GROUP_OVERLAPPING),
        )
        m.add(
            "QCheckBox", setText="Group Touching", setObjectName="chk029", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Group Touching",
                body="Widen grouping to blocks that merely <i>touch</i> — one "
                "ending on the exact frame the next begins — not just blocks "
                "that overlap.",
                bullets=[
                    "<b>Off</b> (default) — touching blocks stay separate and "
                    "are staggered apart.",
                    "<b>On</b> — they are merged and move as one.",
                ],
                notes=["Only bites alongside <b>Group Overlapping</b>."],
            ),
        )
        m.add(
            "QCheckBox", setText="Smooth Tangents", setObjectName="chk009", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Smooth Tangents",
                body="Set auto-clamped bezier handles on the re-timed keys so "
                "the seams between staggered blocks do not pop.",
            ),
        )
        # btk.stagger_keys only consults merge_touching when grouping runs.
        self.sb.enable_when(m, "chk029", "chk014")

    @btk.undoable
    def tb003(self, widget):
        """Stagger Keys (re-time selected objects sequentially)."""
        objects = self.selected_objects()
        if not objects:  # one object is valid — a re-time via the Start Frame override
            self.sb.message_box("Stagger Keys requires a selection.")
            return
        m = widget.option_box.menu
        start = m.s005.value()
        btk.stagger_keys(
            objects,
            start_frame=None if start == -1 else start,
            spacing=m.s004.value(),
            use_intervals=m.chk025.isChecked(),
            invert=m.chk008.isChecked(),
            group_overlapping=m.chk014.isChecked(),
            merge_touching=m.chk029.isChecked(),
            smooth_tangents=m.chk009.isChecked(),
        )

    # Rounding method combo shared with Scale Keys' cmb034 vocabulary (cross-DCC QSettings rule:
    # objectName cmb003 reused verbatim from Maya).
    _SNAP_METHODS = {
        "Nearest": "nearest",
        "Floor": "floor",
        "Ceil": "ceil",
        "Half Up": "half_up",
        "Preferred": "preferred",
        "Aggressive Preferred": "aggressive_preferred",
    }

    def tb009_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Snap Keys to Frames")
        cmb = m.add(
            "QComboBox", setObjectName="cmb003",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SNAP_METHOD),
        )
        for text, data in self._SNAP_METHODS.items():
            cmb.addItem(text, data)
        m.add(
            "QCheckBox", setText="Selected Keys Only", setObjectName="chk017", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Selected Keys Only",
                bullets=[
                    "<b>Off</b> (default) — snap every key on the selected "
                    "objects.",
                    "<b>On</b> — snap only the keys picked in the Dope Sheet / "
                    "Graph Editor.",
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Use Time Range", setObjectName="chk018", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Time Range",
                body="Limit the snap to keys inside the scene's frame range "
                "(Start/End on the timeline).",
                notes=["Keys outside the range keep their fractional times."],
            ),
        )

    @btk.undoable
    def tb009(self, widget):
        """Snap Keys to Frames"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Snap Keys requires a selection.")
            return
        m = widget.option_box.menu
        scene = bpy.context.scene
        time_range = (scene.frame_start, scene.frame_end) if m.chk018.isChecked() else None
        snapped = btk.snap_keys(
            objects,
            selected_only=m.chk017.isChecked(),
            time_range=time_range,
            method=m.cmb003.currentData(),
        )
        if not snapped:
            self.sb.message_box("No keys needed snapping (already on whole frames).")

    def tb010_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Delete Keys")
        cmb = m.add(
            "QComboBox", setObjectName="cmb004",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_DELETE_TIME_RANGE),
        )
        for text, data in [
            ("All Keyframes", "all"),
            ("Current Frame", "current"),
            ("Before Current", "before"),
            ("Before & Current", "before|current"),
            ("After Current", "after"),
            ("Current & After", "after|current"),
        ]:
            cmb.addItem(text, data)
        # Maya's chk020 "Channel Box Only" scopes to Channel Box attribute selection; Blender has
        # no Channel Box, so that option is na (channel scoping happens via Dope Sheet/Graph
        # Editor selection instead — see parity_map.py).

    @btk.undoable
    def tb010(self, widget):
        """Delete Keys (clear all animation on the selection, or only a time-scoped subset)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Delete Keys requires a selection.")
            return
        scope = widget.option_box.menu.cmb004.currentData()
        cleared = btk.delete_keys(objects, time=None if scope == "all" else scope)
        if not cleared:
            self.sb.message_box("Nothing keyed in the selection for the chosen scope.")

    def tb002_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Adjust Spacing")
        m.add(
            "QSpinBox", setPrefix="Frame: ", setObjectName="s002",
            set_limits=[-100000, 100000], setValue=-1,
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="Where the shift starts. Every key at or after this time "
                "moves; everything before it stays put.",
                notes=["<b>-1</b> uses the current playhead frame."],
            ),
        )
        m.add(
            "QSpinBox", setPrefix="Amount: ", setObjectName="s003",
            set_limits=[-100000, 100000], setValue=1,
            setToolTip=self.sb.tooltip.fmt(
                title="Amount",
                body="How far the affected keys move.",
                bullets=[
                    "<b>Positive</b> — pushes keys later, opening up time.",
                    "<b>Negative</b> — pulls keys earlier, compressing timing.",
                ],
                notes=[
                    "<b>Exact Gap</b> re-reads this as a target gap size, which "
                    "only makes sense as a positive value."
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Relative", setObjectName="chk004", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Relative",
                body="How <b>Frame</b> above is read — this does not change how "
                "far the keys move.",
                bullets=[
                    "<b>On</b> (default) — Frame is an offset from the current "
                    "playhead frame.",
                    "<b>Off</b> — Frame is an absolute frame number.",
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Preserve Keys", setObjectName="chk003", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Preserve Keys",
                body="If a key already sits exactly on the start frame, re-anchor "
                "it at its own value instead of letting the shift drag it along.",
            ),
        )
        cmb = m.add(
            "QComboBox",
            setObjectName="cmb036",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                body="Which curves the shift reaches.",
                bullets=[
                    "<b>Selected Objects</b> — every curve on the selection.",
                    "<b>Selected Keys</b> — only the keys picked in the Dope "
                    "Sheet / Graph Editor; the object selection is ignored.",
                    "<b>Entire Scene</b> — every animated curve in the scene.",
                ],
            ),
        )
        for text, data in [
            ("Scope: Selected Objects", "objects"),
            ("Scope: Selected Keys", "keys"),
            ("Scope: Entire Scene", "scene"),
        ]:
            cmb.addItem(text, data)
        m.add(
            "QCheckBox", setText="Exact Gap", setObjectName="chk021", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Exact Gap",
                body="Re-reads <b>Amount</b> as the gap you want, not the "
                "distance to move: the shift is sized so the first key after the "
                "start frame lands exactly on "
                "<code>frame&nbsp;+&nbsp;amount</code>.",
                notes=[
                    "Use it to clear a precise window for new animation, "
                    "whatever the keys were doing before."
                ],
            ),
        )

    @btk.undoable
    def tb002(self, widget):
        """Adjust Key Spacing (shift every key at/after the frame by the amount)."""
        m = widget.option_box.menu
        scope = m.cmb036.currentData()
        if scope == "scene":
            objects = None
        else:
            objects = self.selected_objects()
            if not objects:
                self.sb.message_box("Adjust Spacing requires a selection.")
                return
        frame_value = m.s002.value()
        moved = btk.adjust_key_spacing(
            objects,
            spacing=m.s003.value(),
            frame=None if frame_value == -1 else frame_value,
            relative=m.chk004.isChecked(),
            preserve_keys=m.chk003.isChecked(),
            selected_keys_only=scope == "keys",
            exact_gap=m.chk021.isChecked(),
        )
        if not moved:
            self.sb.message_box("No keys at or after the frame.")

    def tb004_init(self, widget):
        # Blender's source is the ACTIVE object, not "first selected" as in
        # Maya — override the .ui's DCC-neutral wording with the real rule.
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Transfer Keys",
                body="Copy the <b>active</b> object's animation onto every "
                "other selected object, as independent copies.",
                notes=[
                    "Option box: offset the animation onto each target's own "
                    "current pose, and clean up the source before copying."
                ],
            )
        )
        widget.option_box.menu.setTitle("Transfer Keys")
        widget.option_box.menu.add(
            "QCheckBox", setText="Relative", setObjectName="chk006",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_TRANSFER_RELATIVE),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Optimize Before Transfer", setObjectName="chk035",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Optimize Before Transfer",
                body="Run <b>Optimize Keys</b> over the source first, so "
                "redundant keys are not copied onto every target.",
                notes=[
                    "This edits the source's own curves — the cleanup stays "
                    "behind after the transfer."
                ],
            ),
        )

    @btk.undoable
    def tb004(self, widget):
        """Transfer Keys (active object → other selected, independent copies). Relative mode
        offsets the transferred values so each target keeps its own current pose as the base
        (mirrors Maya's chk006), instead of snapping every target to the source's literal
        values."""
        objects = self.selected_objects()
        active = self.active_object()
        targets = [o for o in objects if o is not active]
        if not (active and targets):
            self.sb.message_box("Select target object(s) with the source object active.")
            return
        pasted = btk.transfer_keyframes(
            [active] + targets,
            relative=widget.option_box.menu.chk006.isChecked(),
            optimize=widget.option_box.menu.chk035.isChecked(),
        )
        if not pasted:
            self.sb.message_box("The active object has no keys to transfer.")

    def tb005_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Intermediate Keys")
        m.add(
            "QSpinBox", setPrefix="Start Time: ", setObjectName="s021",
            set_limits=[-1, 100000], setValue=-1,
            setToolTip=self.sb.tooltip.fmt(
                title="Start Time",
                body="First frame of the window that gets sampled.",
                notes=["<b>-1</b> uses each curve's own first key."],
            ),
        )
        m.add(
            "QSpinBox", setPrefix="End Time: ", setObjectName="s006",
            set_limits=[-1, 100000], setValue=-1,
            setToolTip=self.sb.tooltip.fmt(
                title="End Time",
                body="Last frame of the window that gets sampled.",
                notes=["<b>-1</b> uses each curve's own last key."],
            ),
        )
        m.add(
            "QSpinBox", setPrefix="Percent: ", setObjectName="s007",
            set_limits=[0, 100], setValue=5,
            setToolTip=self.sb.tooltip.fmt(
                title="Percent",
                body="How densely the window is sampled — the share of the "
                "interior frames that get a key, spread evenly.",
                rows=[
                    ("100", "a key on every interior frame (a full bake)"),
                    ("50", "every other frame"),
                    ("5", "the default — a sparse scattering"),
                ],
                notes=[
                    "Density is measured against each curve's <i>own</i> span, "
                    "so short and long curves stay proportionally keyed."
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Ignore Visibility", setObjectName="chk028", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Ignore Visibility",
                body="Leave <code>hide_viewport</code> / <code>hide_render</code> "
                "curves out of both the add and the remove pass.",
                notes=[
                    "Worth having on when baking: a sampled visibility curve "
                    "turns a clean on/off switch into a run of stepped keys."
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Remove Intermediate Keys", setObjectName="chk027",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_REMOVE_INTERMEDIATE),
        )
        # Percent only drives the add-keys branch.
        self.sb.enable_when(m, "s007", "chk027", invert=True)

    @btk.undoable
    def tb005(self, widget):
        """Add/Remove Intermediate Keys"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Intermediate Keys requires a selection.")
            return
        m = widget.option_box.menu
        start, end = m.s021.value(), m.s006.value()
        # -1 on a bound = unbounded on that side (each curve's own first/last key).
        time_range = (
            None
            if start == -1 and end == -1
            else (start if start != -1 else -(10**9), end if end != -1 else 10**9)
        )
        ignore_visibility = m.chk028.isChecked()
        if m.chk027.isChecked():
            count = btk.remove_intermediate_keys(
                objects, time_range=time_range, ignore_visibility=ignore_visibility
            )
        else:
            count = btk.add_intermediate_keys(
                objects, time_range=time_range, ignore_visibility=ignore_visibility,
                percent=m.s007.value(),
            )
        if not count:
            self.sb.message_box("No intermediate keys to change in the selection.")

    def tb013_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Select Keys")
        cmb = m.add(
            "QComboBox", setObjectName="cmb041",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SELECT_TIME_RANGE),
        )
        for text, data in [
            ("All", "all"),
            ("Current", "current"),
            ("Before", "before"),
            ("After", "after"),
            ("Before|Current", "before|current"),
            ("After|Current", "after|current"),
            ("Range", "range"),
        ]:
            cmb.addItem(text, data)
        m.add(
            "QSpinBox", setPrefix="Start Frame: ", setObjectName="s012",
            set_limits=[-10000, 10000], setValue=1,
            setToolTip=self.TIP_SELECT_RANGE_START,
        )
        m.add(
            "QSpinBox", setPrefix="End Frame: ", setObjectName="s013",
            set_limits=[-10000, 10000], setValue=100,
            setToolTip=self.TIP_SELECT_RANGE_END,
        )
        m.add(
            "QCheckBox", setText="Add to Selection", setObjectName="chk039", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Add to Selection",
                body="Extend the current Dope Sheet / Graph Editor key selection "
                "instead of replacing it — run the button repeatedly to build a "
                "set out of several ranges.",
            ),
        )
        # Start/End only feed the explicit Range mode.
        self.sb.enable_when(m, "s012,s013", "cmb041", "range")
        # Maya's chk034 "Channel Box Only" scopes to Channel Box attribute selection; Blender has
        # no Channel Box, so that option is na (channel scoping happens via Dope Sheet/Graph
        # Editor selection instead — see parity_map.py).

    def tb013(self, widget):
        """Select Keys (``select_control_point`` — shows in the Dope Sheet / Graph Editor)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Select Keys requires a selection.")
            return
        m = widget.option_box.menu
        scope = m.cmb041.currentData()
        if scope == "range":
            time = (m.s012.value(), m.s013.value())
        elif scope == "all":
            time = None
        else:
            time = scope
        keys_selected = btk.select_keys(
            objects, time=time, add_to_selection=m.chk039.isChecked()
        )
        if not keys_selected:
            self.sb.message_box("No keyframes found to select.")
        else:
            self.sb.message_box(f"Selected {keys_selected} keyframe(s).")

    def tb007_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Align Selected Keyframes")
        m.add(
            "QCheckBox", setText="Use Earliest Frame", setObjectName="chk013",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Earliest Frame",
                body="Which selected key everything else is dragged onto.",
                bullets=[
                    "<b>On</b> (default) — the earliest selected key wins.",
                    "<b>Off</b> — the latest selected key wins.",
                ],
                notes=[
                    "Ignored once <b>Frame</b> below is set to anything but "
                    "-1 — an explicit target needs no election."
                ],
            ),
        )
        m.add(
            "QSpinBox", setPrefix="Frame: ", setObjectName="spn000",
            setMinimum=-10000, setMaximum=10000, setValue=-1,
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="Align every object's selected keys onto this exact frame.",
                notes=[
                    "<b>-1</b> elects the target from the selection instead, "
                    "per <b>Use Earliest Frame</b> above."
                ],
            ),
        )
        # An explicit target frame makes the earliest/latest election moot.
        self.sb.enable_when(m, "chk013", "spn000", -1)

    @btk.undoable
    def tb007(self, widget):
        """Align Selected Keyframes (keys picked in the Dope Sheet / Graph Editor)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Align Keys requires a selection.")
            return
        m = widget.option_box.menu
        frame = m.spn000.value()
        moved = btk.align_selected_keyframes(
            objects,
            target_frame=None if frame == -1 else frame,
            use_earliest=m.chk013.isChecked(),
        )
        if not moved:
            self.sb.message_box(
                "No selected keyframes found — select keys in the Dope Sheet first."
            )

    def tb008_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Set Visibility Keys")
        # Visible vs Hidden is a two-valued choice, not a modifier — name both states.
        vis = m.add(
            "QComboBox", setObjectName="cmb_visibility",
            setToolTip=self.sb.tooltip.fmt(
                title="Visibility",
                body="The state written at the chosen frame(s) — <b>Visible</b> "
                "keys <code>hide_viewport</code>/<code>hide_render</code> off, "
                "<b>Hidden</b> keys them on.",
            ),
        )
        vis.addItems(["Visible", "Hidden"])
        vis.setCurrentText("Visible")  # preserve prior default (checkbox on = visible)
        cmb = m.add(
            "QComboBox", setObjectName="cmb002",
            setToolTip=self.sb.tooltip.fmt(
                title="When",
                body="Where the visibility key is written.",
                bullets=[
                    "<b>Range Start</b> / <b>Range End</b> — on the first / "
                    "last frame of each object's own keyed range.",
                    "<b>Both Ends</b> — on each end.",
                    "<b>Before Start</b> / <b>After End</b> — one frame outside "
                    "the range, so the state is already settled when the "
                    "animation begins or ends.",
                    "<b>Current Frame</b> — on the playhead, ignoring the "
                    "keyed range entirely.",
                ],
            ),
        )
        # Maya's cmb002 items first, in Maya's order (cross-DCC QSettings rule: persisted
        # indices agree); the Blender-only Current Frame mode is appended last.
        for text, data in [
            ("When: Range Start", "start"),
            ("When: Range End", "end"),
            ("When: Both Ends", "both"),
            ("When: Before Start", "before_start"),
            ("When: After End", "after_end"),
            ("When: Current Frame", "current"),
        ]:
            cmb.addItem(text, data)
        m.add(
            "QSpinBox", setPrefix="Offset: ", setObjectName="s008",
            set_limits=[-10000, 10000], setValue=0,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_VISIBILITY_OFFSET),
        )
        m.add(
            "QCheckBox", setText="Group Overlapping", setObjectName="chk016", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_VISIBILITY_GROUP_OVERLAPPING),
        )

    @btk.undoable
    def tb008(self, widget):
        """Set Visibility Keys (key viewport + render visibility)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Visibility Keys requires a selection.")
            return
        m = widget.option_box.menu
        keyed = btk.set_visibility_keys(
            objects,
            visible=m.cmb_visibility.currentText() == "Visible",
            when=m.cmb002.currentData(),
            offset=m.s008.value(),
            group_overlapping=m.chk016.isChecked(),
        )
        if not keyed:
            self.sb.message_box(
                "No keyed range on the selection for the chosen When mode."
            )

    def tb006_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Move Keys")
        m.add(
            "QCheckBox", setText="Move Selected Keys", setObjectName="chk031", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Move Selected Keys",
                bullets=[
                    "<b>On</b> (default) — move only the keys picked in the "
                    "Dope Sheet / Graph Editor.",
                    "<b>Off</b> — move every key on the selected objects.",
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Maintain Spacing", setObjectName="chk012", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Maintain Spacing",
                bullets=[
                    "<b>On</b> (default) — the selection moves as one rigid "
                    "block; the offsets between objects are preserved.",
                    "<b>Off</b> — every object is moved onto the current frame "
                    "independently, stacking them together.",
                ],
            ),
        )
        cmb = m.add(
            "QComboBox", setObjectName="cmb_align",
            setToolTip=self.sb.tooltip.fmt(
                title="Align",
                body="Which end of the moved key range lands on the current frame.",
                bullets=[
                    "<b>Start</b> — the earliest key lands there; the animation "
                    "runs forward from the playhead.",
                    "<b>End</b> — the latest key lands there; the animation "
                    "arrives at the playhead.",
                    "<b>Auto</b> — picks whichever end is nearer.",
                ],
            ),
        )
        for text, data in [
            ("Align: Auto", "auto"),
            ("Align: Start", "start"),
            ("Align: End", "end"),
        ]:
            cmb.addItem(text, data)

    @btk.undoable
    def tb006(self, widget):
        """Move Keys (align the selection's keys to the current frame)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Move Keys requires a selection.")
            return
        m = widget.option_box.menu
        moved = btk.move_keys_to_frame(
            objects,
            retain_spacing=m.chk012.isChecked(),
            selected_keys_only=m.chk031.isChecked(),
            align=m.cmb_align.currentData(),
        )
        if not moved:
            self.sb.message_box("Nothing keyed in the selection.")

    # Copy mode -> btk.copy_keys mode ("copy_paste" is a Blender-side convenience that copies
    # AND immediately pastes onto the rest of the selection, handled entirely in tb012 below —
    # it never reaches btk.copy_keys as a mode string). Maya's "Mode: Channel Box" item is
    # dropped (Blender has no Channel Box) — see parity_map.py cmb038.
    _COPY_MODES = {
        "Mode: Auto": "action",
        "Mode: Current Frame": "current_frame",
        "Mode: Selected Keys": "selected",
        "Mode: Copy + Paste": "copy_paste",
    }

    def tb012_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Copy Keys")
        cmb = m.add(
            "QComboBox", setObjectName="cmb038",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="What gets captured from the <b>active</b> object.",
                bullets=[
                    "<b>Auto</b> — the whole action (Blender's native "
                    "full-animation copy).",
                    "<b>Current Frame</b> — a value snapshot of every animated "
                    "property at the playhead.",
                    "<b>Selected Keys</b> — only the keys picked in the Dope "
                    "Sheet / Graph Editor.",
                    "<b>Copy + Paste</b> — capture the whole action and "
                    "immediately paste it onto the rest of the selection, in "
                    "one click.",
                ],
                notes=[
                    "Everything but Copy + Paste only stores; use <b>Paste "
                    "Keys</b> to apply it."
                ],
            ),
        )
        for text, data in self._COPY_MODES.items():
            cmb.addItem(text, data)

    @btk.undoable
    def tb012(self, widget):
        """Copy Keys (from the active object; Copy + Paste mode also pastes onto the rest of
        the selection immediately)."""
        active = self.active_object()
        if active is None:
            self.sb.message_box("Copy Keys requires an active object.")
            return
        mode = widget.option_box.menu.cmb038.currentData() or "action"

        if mode == "copy_paste":
            targets = [o for o in self.selected_objects() if o is not active]
            action = btk.copy_keys(active)
            if action is None:
                self.sb.message_box("The active object has no keys to copy.")
                return
            if not targets:
                self.sb.message_box("Select target object(s) in addition to the active object.")
                return
            btk.paste_keys(targets, action)
            return

        self._copied_action = btk.copy_keys(active, mode=mode)
        if self._copied_action is None:
            self.sb.message_box("Nothing to copy for the chosen mode.")

    def tb018_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Paste Keys")
        cmb = m.add(
            "QComboBox", setObjectName="cmb039",
            setToolTip=self.sb.tooltip.fmt(
                title="Paste At",
                bullets=[
                    "<b>At Playhead</b> — shifted so the earliest copied key "
                    "lands on the current frame; later keys keep their spacing.",
                    "<b>At Copy Frame</b> — back at the frames they were "
                    "captured at, wherever the playhead is now.",
                ],
            ),
        )
        # Item order matches Maya's cmb039 (cross-DCC QSettings rule: persisted indices agree).
        for text, data in [("At Playhead", "playhead"), ("At Copy Frame", "source")]:
            cmb.addItem(text, data)

    @btk.undoable
    def tb018(self, widget):
        """Paste Keys (independent copies onto the selection)."""
        if self._copied_action is None:
            self.sb.message_box("Nothing copied — use Copy Keys first.")
            return
        paste_mode = widget.option_box.menu.cmb039.currentData()
        target_time = (
            bpy.context.scene.frame_current if paste_mode == "playhead" else None
        )
        try:
            pasted = btk.paste_keys(
                self.selected_objects(), self._copied_action, target_time=target_time
            )
        except ReferenceError:  # the copied action was deleted (e.g. file reload/purge)
            self._copied_action = None
            self.sb.message_box("The copied keys no longer exist — use Copy Keys again.")
            return
        if not pasted:
            self.sb.message_box("Nothing pasted — select target object(s) first.")

    def tb014_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Scale Keys")
        # Re-applied by the mode switch below, so rendered once here.
        uniform_tooltip = self.sb.tooltip.fmt(**self.TIP_SCALE_FACTOR_UNIFORM)
        speed_tooltip = self.sb.tooltip.fmt(**self.TIP_SCALE_FACTOR_SPEED)
        cmb_mode = m.add(
            "QComboBox", setObjectName="cmb014", block_signals_on_restore=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="What <b>Factor</b> is measured against.",
                bullets=[
                    "<b>Uniform</b> — plain time scaling about a pivot. Factor "
                    "is a multiplier, or a target duration in frames.",
                    "<b>Speed</b> — the block is retimed until its <i>motion</i> "
                    "hits the target speed; the duration falls out of "
                    "distance &#247; speed. Samples translation and rotation.",
                    "<b>Speed: Linear</b> — translation only.",
                    "<b>Speed: Rotation</b> — rotation only.",
                ],
                notes=[
                    "Speed modes need real world-space movement — an object "
                    "that only changes colour or visibility has no distance to "
                    "normalise and is skipped."
                ],
            ),
        )
        for text, data in [
            ("Uniform Mode", "uniform"),
            ("Speed Mode", "speed"),
            ("Speed Mode: Linear", "speed_linear"),
            ("Speed Mode: Rotation", "speed_rotation"),
        ]:
            cmb_mode.addItem(text, data)

        m.add(
            "QDoubleSpinBox", setPrefix="Factor: ", setObjectName="d001",
            setMinimum=0.01, setMaximum=100000.0, setSingleStep=0.1, setValue=1.0,
            setDecimals=2,
            setToolTip=uniform_tooltip,
        )
        cmb_group = m.add(
            "QComboBox", setObjectName="cmb033",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_GROUPING),
        )
        for text, data in [
            ("Single Group", "single_group"),
            ("Per Object Pivots", "per_object"),
            ("Group Overlaps", "overlap_groups"),
        ]:
            cmb_group.addItem(text, data)
        cmb_snap = m.add(
            "QComboBox", setObjectName="cmb034",
            setToolTip=self.sb.tooltip.fmt(
                title="Snap",
                body="Scaling lands keys on fractional frames; this decides how "
                "they are rounded back afterwards.",
                bullets=[
                    "<b>Nearest</b> (default) — to the closest whole frame.",
                    "<b>Preferred</b> — snap to a clean number when close "
                    "(24 &#8594; 25, 99 &#8594; 100).",
                    "<b>Aggressive</b> — snap to a clean number from farther "
                    "out (48 &#8594; 50, 73 &#8594; 75).",
                    "<b>None</b> — keep the exact decimal times.",
                ],
                notes=[
                    "Pick None when the scale is an intermediate step and the "
                    "rounding error would compound."
                ],
            ),
        )
        for text, data in [
            ("Snap: Nearest", "nearest"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive_preferred"),
            ("Snap: None", "none"),
        ]:
            cmb_snap.addItem(text, data)
        m.add(
            "QSpinBox", setPrefix="Samples: ", setObjectName="s014",
            setMinimum=8, setMaximum=512, setSingleStep=8, setValue=64,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_SAMPLES),
        )
        # Absolute vs Relative is a two-valued mode, not a modifier — name both states.
        scale_mode = m.add(
            "QComboBox", setObjectName="cmb_scale_mode",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_RELATIVE_ABSOLUTE),
        )
        scale_mode.addItems(["Relative", "Absolute"])
        scale_mode.setCurrentText("Relative")  # preserve prior default (checkbox off = relative)
        m.add(
            "QCheckBox", setText="Split Static Segments", setObjectName="chk_split_static",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Split Static Segments",
                body="Treat an object's separate bursts of animation as "
                "independent blocks, using the flat holds between them as the "
                "cut points.",
                bullets=[
                    "<b>On</b> (default) — each burst is scaled on its own, so "
                    "the holds between them absorb the change.",
                    "<b>Off</b> — every key on the object scales as one block, "
                    "stretching the holds along with the motion.",
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Group Touching", setObjectName="chk_merge_touching",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_GROUP_TOUCHING),
        )
        # btk.scale_keys only consults merge_touching for "overlap_groups".
        self.sb.enable_when(m, "chk_merge_touching", "cmb033", "overlap_groups")
        # cmb_scale_pivot is Blender-specific (Maya's scale option box always auto-detects the
        # block's own start; it has no pivot picker).
        m.add(
            "QComboBox", addItems=["First Key", "Current Frame"], setObjectName="cmb_scale_pivot",
            setToolTip=self.sb.tooltip.fmt(
                title="Pivot",
                body="The frame the scale is anchored to — the one point that "
                "does not move.",
                bullets=[
                    "<b>First Key</b> (default) — each group's own start frame, "
                    "so a block grows or shrinks forward from where it began.",
                    "<b>Current Frame</b> — the playhead, for every group. Keys "
                    "before it move the other way.",
                ],
                notes=[
                    "Blender-only; Maya's Scale Keys always anchors to the "
                    "block's own start."
                ],
            ),
        )

        def update_mode_ui(index):
            is_speed_mode = index > 0
            m.s014.setEnabled(is_speed_mode)
            if is_speed_mode:
                m.d001.setPrefix("Speed: ")
                m.d001.setSingleStep(0.5)
                m.d001.setValue(5.0)
                m.d001.setToolTip(speed_tooltip)
                m.cmb_scale_mode.setCurrentText("Absolute")
            else:
                m.d001.setPrefix("Factor: ")
                m.d001.setSingleStep(0.1)
                m.d001.setValue(1.0)
                m.d001.setToolTip(uniform_tooltip)
                m.cmb_scale_mode.setCurrentText("Relative")

        cmb_mode.currentIndexChanged.connect(update_mode_ui)
        update_mode_ui(0)

    @btk.undoable
    def tb014(self, widget):
        """Scale Keys"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Scale Keys requires a selection.")
            return
        m = widget.option_box.menu
        mode_data = m.cmb014.currentData()
        if mode_data == "speed":
            mode, include_rotation = "speed", True
        elif mode_data == "speed_linear":
            mode, include_rotation = "speed", False
        elif mode_data == "speed_rotation":
            mode, include_rotation = "speed", "only"
        else:
            mode, include_rotation = "uniform", False

        pivot = (
            bpy.context.scene.frame_current
            if m.cmb_scale_pivot.currentText() == "Current Frame"
            else None
        )
        keys_scaled = btk.scale_keys(
            objects,
            factor=m.d001.value(),
            pivot=pivot,
            mode=mode,
            absolute=m.cmb_scale_mode.currentText() == "Absolute",
            group_mode=m.cmb033.currentData(),
            snap_mode=m.cmb034.currentData(),
            samples=m.s014.value(),
            include_rotation=include_rotation,
            split_static=m.chk_split_static.isChecked(),
            merge_touching=m.chk_merge_touching.isChecked(),
        )
        if not keys_scaled:
            self.sb.message_box("No keyframes found to scale.")

    # interp label -> fcurve interpolation enum (Maya's "Step Tangents" generalized to a tangent-
    # type picker). cmb_interp is Blender-specific (Maya used cmb037/cmb040 for in/out tangent).
    _INTERP_TYPES = {"Stepped": "CONSTANT", "Linear": "LINEAR", "Smooth (Bezier)": "BEZIER"}

    def tb017_init(self, widget):
        # Blender's fcurve interpolation can be set to any of the three types below
        # (unlike Maya's tb017, which only ever sets stepped/hold tangents) — override
        # the .ui's DCC-neutral default with the accurate, Blender-specific description.
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Set Tangents",
                body="Set the interpolation type on <b>every</b> key of the "
                "selected object(s) — Blender sets whole-key interpolation, so "
                "there is no separate in/out side to pick.",
                notes=["Option box: which interpolation type to apply."],
            )
        )
        widget.option_box.menu.setTitle("Set Tangents")
        widget.option_box.menu.add(
            "QComboBox", addItems=list(self._INTERP_TYPES), setObjectName="cmb_interp",
            setToolTip=self.sb.tooltip.fmt(
                title="Interpolation",
                body="Applied to every key on the selection.",
                bullets=[
                    "<b>Stepped</b> — values hold and jump; the blocking / "
                    "pose-to-pose look.",
                    "<b>Linear</b> — straight ramps between keys, constant "
                    "speed and hard corners.",
                    "<b>Smooth (Bezier)</b> — eased handles; Blender's default.",
                ],
            ),
        )

    @btk.undoable
    def tb017(self, widget):
        """Set Tangents (key interpolation type — stepped / linear / smooth)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Set Tangents requires a selection.")
            return
        interp = self._INTERP_TYPES[widget.option_box.menu.cmb_interp.currentText()]
        btk.set_interpolation(objects, interp)

    # ------------------------------------------------------------------ b-slots
    def b005(self):
        """Fit Playback Range (to the keyed extent of the selection, or the whole scene)."""
        objects = self.selected_objects() or None
        applied = btk.fit_playback_range(objects)
        if applied is None:
            self.sb.message_box("Nothing keyed to fit the range to.")
        else:
            self.sb.message_box(f"Playback range set to <hl>{applied[0]}-{applied[1]}</hl>.")

    # ------------------------------------------------------------------ tb011  Tie Keyframes
    def tb011_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Tie Keyframes")
        # Tie vs Untie is a two-valued choice, not a modifier — name both states.
        tie = m.add(
            "QComboBox", setObjectName="cmb_tie",
            setToolTip=self.sb.tooltip.fmt(
                title="Tie / Untie",
                bullets=[
                    "<b>Tie</b> — insert bookend keys at the range boundaries "
                    "so every animated object is pinned at both ends.",
                    "<b>Untie</b> — remove those bookends again, leaving "
                    "genuine animation intact.",
                ],
            ),
        )
        tie.addItems(["Tie", "Untie"])
        tie.setCurrentText("Tie")  # preserve prior default (checkbox off = tie)
        m.add(
            "QCheckBox", setText="Use Absolute Range", setObjectName="chk023", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Absolute Range",
                body="Which range gets the bookend keys.",
                bullets=[
                    "<b>Off</b> (default) — the scene's frame range.",
                    "<b>On</b> — the true keyed extent, from the earliest to "
                    "the latest key across the objects.",
                ],
                notes=[
                    "Tie only. On an untie it would target genuine first/last "
                    "keys, so tb011 drops it there."
                ],
            ),
        )
        # ...and the control says so rather than sitting live and ignored.
        self.sb.enable_when(m, "chk023", "cmb_tie", 0)

    @btk.undoable
    def tb011(self, widget):
        """Tie/Untie Keyframes"""
        objects = self.selected_objects() or None
        m = widget.option_box.menu
        untie = m.cmb_tie.currentText() == "Untie"
        # Absolute range = the keyed extent (every curve's genuine first/last keys), so
        # untie+absolute would delete real animation endpoints — absolute applies only when tying.
        changed = btk.tie_keyframes(
            objects, untie=untie, absolute=not untie and m.chk023.isChecked()
        )
        verb = "Untied" if untie else "Tied"
        self.sb.message_box(f"{verb} <hl>{changed}</hl> bookend key(s).")

    # ------------------------------------------------------------------ tb016  Get Animation Info
    def tb016_init(self, widget):
        widget.option_box.menu.setTitle("Get Animation Info")
        cmb = widget.option_box.menu.add(
            "QComboBox", setObjectName="cmb_scope",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                bullets=[
                    "<b>Selected</b> — only the current selection.",
                    "<b>All Scene Objects</b> — every object in the scene.",
                ],
            ),
        )
        for label, data in [("Scope: Selected", "selected"), ("Scope: All Scene Objects", "all")]:
            cmb.addItem(label, data)
        widget.option_box.menu.add(
            "QCheckBox", setText="Sort by Time", setObjectName="chk_sort_time", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INFO_SORT_BY_TIME),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="CSV Output", setObjectName="chk_csv_output", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="CSV Output",
                body="Render the report as comma-separated rows, ready to paste "
                "into a spreadsheet.",
                notes=["The viewer switches to a monospace font for CSV."],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Ignore Holds", setObjectName="chk_ignore_holds",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INFO_IGNORE_HOLDS),
        )

    def tb016(self, widget):
        """Get Animation Info — render a per-object keyframe summary to the viewer dialog."""
        m = widget.option_box.menu
        scope = m.cmb_scope.currentData() or "selected"
        objects = self.selected_objects() if scope == "selected" else None
        if scope == "selected" and not objects:
            self.sb.message_box(
                "<hl>Nothing selected</hl><br>"
                "Select object(s) or switch Scope to All Scene Objects."
            )
            return
        records = btk.get_animation_info(
            objects, by_time=m.chk_sort_time.isChecked(),
            ignore_holds=m.chk_ignore_holds.isChecked(),
        )
        if not records:
            self.sb.message_box("<hl>No animation</hl> found in the selected scope.")
            return
        csv_output = m.chk_csv_output.isChecked()
        text = (
            btk.format_animation_info_csv(records)
            if csv_output
            else btk.format_animation_info_html(records)
        )
        self.sb.text_view_dialog(
            text, "Ok", title="Get Animation Info", size=(780, 520), monospace=csv_output
        )

    # ------------------------------------------------------------------ tb019  Optimize Keys
    def tb019_init(self, widget):
        widget.option_box.menu.setTitle("Optimize Keys")
        widget.option_box.menu.add(
            "QCheckBox", setText="Remove Static Curves", setObjectName="chk000", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Remove Static Curves",
                body="Delete whole curves that never change value — animation "
                "that exists but does nothing.",
                notes=[
                    "Lossless: the held value is written back to the property "
                    "before the curve goes, so the pose is unchanged."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Remove Flat Keys", setObjectName="chk030", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_OPTIMIZE_REMOVE_FLAT_KEYS),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Simplify Curves", setObjectName="chk032", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Simplify Curves",
                body="Also drop keys that sit on the line between their "
                "neighbours, within <b>Tolerance</b>.",
                notes=[
                    "The one lossy phase — it can reshape a moving curve, not "
                    "just remove redundancy.",
                    "Ignored while <b>Unbake</b> is on, which runs its own "
                    "reduction.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Unbake (keep extrema)", setObjectName="chk040", setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Unbake (keep extrema)",
                body="The inverse of a per-frame bake: reduce a dense curve to "
                "its endpoints, peaks, valleys and hold boundaries, then refit "
                "the handles so the reduced curve still traces the baked motion.",
                notes=[
                    "Stepped curves get the flat-key pass instead — there is no "
                    "smooth motion to refit.",
                    "<b>Simplify Curves</b> and <b>Tolerance</b> are ignored "
                    "while this is on.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Tolerance: ", setObjectName="d017",
            set_limits=[0.0001, 1.0], setValue=0.001, setDecimals=4, setSingleStep=0.001,
            setToolTip=self.sb.tooltip.fmt(
                title="Tolerance",
                body="How far a value may drift before a key is considered "
                "worth keeping. Drives both <b>Remove Flat Keys</b> (how equal "
                "counts as flat) and <b>Simplify Curves</b>.",
                bullets=[
                    "<b>Smaller</b> — more faithful, fewer keys removed.",
                    "<b>Larger</b> — leaner curves, more visible drift.",
                ],
                notes=[
                    "Measured in scene units, so the same number is stricter on "
                    "a rotation curve than on a location one.",
                    "Ignored while <b>Unbake</b> is on.",
                ],
            ),
        )
        # Unbake replaces the simplify/tolerance pass outright (tb019 sends a
        # negative tolerance as its sentinel), so both controls grey out.
        self.sb.enable_when(
            widget.option_box.menu, "chk032,d017", "chk040", invert=True
        )

    @btk.undoable
    def tb019(self, widget):
        """Optimize Keys — remove redundant animation data."""
        m = widget.option_box.menu
        selected = self.selected_objects()
        stats = {}
        btk.optimize_keys(
            selected or None,
            # A negative tolerance is optimize_keys' unbake sentinel.
            value_tolerance=-1 if m.chk040.isChecked() else m.d017.value(),
            remove_static_curves=m.chk000.isChecked(),
            remove_flat_keys=m.chk030.isChecked(),
            simplify_keys=m.chk032.isChecked(),
            stats=stats,
        )
        cb, ca = stats["curves_before"], stats["curves_after"]
        kb, ka = stats["keys_before"], stats["keys_after"]
        scope = "selected objects" if selected else "scene"
        msg = (
            f"Optimized {scope}:\n"
            f"  • Curves: {cb} → {ca} ({cb - ca} removed)\n"
            f"  • Keys: {kb:,} → {ka:,} ({kb - ka:,} removed)"
        )
        if kb:
            msg += f" ({(1 - ka / kb) * 100:.1f}% reduction)"
        if "unbaked" in stats:
            msg += (
                f"\n  • Unbaked: {stats['unbaked']} curves, "
                f"max deviation {stats['unbake_max_error']:.4f}"
            )
        self.sb.message_box(msg)

    # ------------------------------------------------------------------ tb015  Repair Corrupted Curves
    def tb015_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Repair Corrupted Curves")
        m.add(
            "QCheckBox", setText="Delete Unfixable Curves", setObjectName="chk036", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Delete Unfixable Curves",
                body="Remove curves left with no usable keys once the fixes "
                "below have run.",
                notes=[
                    "Off leaves the curve in place but empty, which keeps the "
                    "property driven and unkeyable by hand."
                ],
            ),
        )
        m.add(
            "QCheckBox", setText="Fix Infinite Values", setObjectName="chk037", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Fix Infinite Values",
                body="Remove keys whose <i>value</i> is NaN, infinite, or past "
                "the <b>Value Threshold</b> below.",
            ),
        )
        m.add(
            "QCheckBox", setText="Fix Invalid Times", setObjectName="chk038", setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Fix Invalid Times",
                body="Remove keys sitting at a NaN, infinite, or absurd "
                "<i>frame</i> — the times a corrupted curve picks up that "
                "stretch the Graph Editor to uselessness.",
            ),
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Time Threshold: ", setObjectName="d015",
            set_limits=[1000, 999999999], setValue=100000,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_REPAIR_TIME_THRESHOLD),
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Value Threshold: ", setObjectName="d016",
            set_limits=[1000, 999999999], setValue=1000000,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_REPAIR_VALUE_THRESHOLD),
        )

    @btk.undoable
    def tb015(self, widget):
        """Repair Corrupted Curves — strip NaN/infinite or out-of-range keys; delete unfixable curves."""
        m = widget.option_box.menu
        selected = self.selected_objects()
        r = btk.repair_corrupted_curves(
            selected or None,
            delete_unfixable=m.chk036.isChecked(),
            fix_infinite=m.chk037.isChecked(),
            fix_invalid_times=m.chk038.isChecked(),
            time_threshold=m.d015.value(),
            value_threshold=m.d016.value(),
        )
        scope = "selected objects" if selected else "scene"
        if not r["corrupted_found"]:
            self.sb.message_box(f"No corrupted curves found on the {scope}. Animation is clean.")
            return
        msg = (
            f"Repaired {scope}:\n"
            f"  • Corrupted curves: {r['corrupted_found']}\n"
            f"  • Repaired: {r['curves_repaired']}\n"
            f"  • Deleted: {r['curves_deleted']}\n"
            f"  • Keys fixed: {r['keys_fixed']}"
        )
        if r["details"]:
            msg += "\n\n" + "\n".join(f"  • {d}" for d in r["details"][:3])
            if len(r["details"]) > 3:
                msg += f"\n  … and {len(r['details']) - 3} more"
        self.sb.message_box(msg)

    # ------------------------------------------------------------------ tb020  Smart Bake
    def tb020(self, widget):
        """Smart Bake"""
        self.sb.handlers.marking_menu.show("smart_bake")

    # ------------------------------------------------------------------ Shots pipeline (blendertk)
    def b000(self):
        """Open Shot Sequencer — native blendertk panel (anim_utils/shots/shot_sequencer), 1:1
        with mayatk's: shots realized on timeline markers + ``marker.camera_bind`` behind the
        shared pythontk shots core. (Replaced the pre-2026-07-11 "Maya-shot-pipeline specific"
        message box — the panel shipped in blendertk.)"""
        self.sb.handlers.marking_menu.show("shot_sequencer")

    def b004(self):
        """Open Shot Manifest — native blendertk panel (anim_utils/shots/shot_manifest), 1:1 with
        mayatk's CSV-driven scene assembly over linked Scenes/Collections behind the shared
        pythontk shots core. (Replaced the pre-2026-07-11 "Maya-shot-pipeline specific" message
        box — the panel shipped in blendertk.)"""
        self.sb.handlers.marking_menu.show("shot_manifest")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
