# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import mayatk as mtk
from tentacle import AnimationMixin, SlotsMaya


class Animation(AnimationMixin, SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.animation
        self.ui_submenu = self.sb.loaded_ui.animation_submenu

    #: ``category -> [(label, objectName, tooltip)]`` for the header Tools list
    #: (was five separator sections of loose header buttons).
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
            ("Repair Corrupted Curves", "tb015", "Repair corrupted animation curves."),
            (
                "Repair Visibility Tangents",
                "b001",
                "Force 'step' tangents on visibility curves for selected objects (or all if none selected).",
            ),
        ],
        "Bake": [
            (
                "Smart Bake",
                "tb020",
                "Open the Smart Bake panel.\n"
                "Analyzes and bakes constraints, driven keys, expressions, IK,\n"
                "motion paths, and blend shapes — with a one-click Unbake to\n"
                "reverse the most recent bake, even after a scene reopen.",
            ),
        ],
        "Stash": [
            (
                "Key Stash",
                "b006",
                "Open the Key Stash: park selected keys out of the working animation\n"
                "(inert, not exported, kept across sessions), preview a stored range\n"
                "on demand, and retrieve it later.",
            ),
        ],
        "Playback": [
            (
                "Fit Playback Range",
                "b005",
                "Set the playback range to span every keyed object in the scene, "
                "from the earliest to the latest keyframe.",
            ),
        ],
        "Info": [
            (
                "Get Animation Info",
                "tb016",
                "Show segmented keyframe info in a formatted viewer.\n"
                "Use the option box to choose scope (Selected / All), "
                "dependency traversal, and output flags.",
            ),
        ],
    }

    def list000_init(self, widget):
        """Tools list: Sequencing / Repair / Bake / Stash / Playback / Info.

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

    @SlotsMaya.Signals("on_item_interacted")
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

    def b001(self):
        """Repair Visibility Tangents"""
        mtk.Diagnostics.repair_visibility_tangents(objects=cmds.ls(sl=True) or None)

    def tb000_init(self, widget):
        """Go To Frame Init"""
        widget.option_box.menu.setTitle("Go To Frame")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits=[-999999, 999999],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_FRAME),
        )
        # Mode ComboBox
        cmb000 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_MODE),
        )
        for text, data in [
            ("Mode: Absolute", "Absolute"),
            ("Mode: Relative", "Relative"),
        ]:
            cmb000.addItem(text, data)
        cmb000.setCurrentIndex(1)

        # Snap ComboBox. Nearest/Floor/Ceil are APPENDED, not inserted in
        # rounding order: the combo persists by index (cross-DCC QSettings
        # rule), so reordering would silently repoint a stored choice.
        cmb001 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb001",
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
                    "Only Floor and Ceil respond to <b>Invert</b> below — it "
                    "swaps the two."
                ],
            ),
        )
        snap_items = [
            ("Snap: None", "none"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive"),
            ("Snap: Nearest", "nearest"),
            ("Snap: Floor", "floor"),
            ("Snap: Ceil", "ceil"),
        ]
        for text, data in snap_items:
            cmb001.addItem(text, data)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Update",
            setObjectName="chk001",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Update",
                bullets=[
                    "<b>On</b> (default) — the scene re-evaluates at the new "
                    "time, so the viewport follows the playhead.",
                    "<b>Off</b> — only the time slider moves; the world is left "
                    "standing at the old time.",
                ],
                notes=[
                    "Off is the fast way to reposition the playhead in a heavy "
                    "scene without paying for a re-evaluation."
                ],
            ),
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.Label,
            setText="Set To Current Frame",
            setObjectName="lbl020",
            setToolTip=self.TIP_GOTO_SET_TO_CURRENT,
        )
        widget.option_box.menu.lbl020.clicked.connect(
            lambda: widget.option_box.menu.s000.setValue(cmds.currentTime(q=True))
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Toggle Single frame",
            setObjectName="chk010",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_SINGLE_FRAME),
        )
        widget._previous_frame_value = 1

        def toggle_single_frame(state):
            spinbox = widget.option_box.menu.s000
            if state:
                widget._previous_frame_value = spinbox.value() or 1
                spinbox.setValue(-1 if widget._previous_frame_value > 0 else 1)
            else:
                spinbox.setValue(widget._previous_frame_value)

        widget.option_box.menu.chk010.toggled.connect(toggle_single_frame)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk011",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_GOTO_INVERT),
        )

        def toggle_inverted(state):
            spinbox = widget.option_box.menu.s000
            spinbox.setValue(-spinbox.value())

        widget.option_box.menu.chk011.toggled.connect(toggle_inverted)

        def update_invert_checkbox(value):
            block = widget.option_box.menu.chk011.blockSignals(True)
            widget.option_box.menu.chk011.setChecked(value < 0)
            widget.option_box.menu.chk011.blockSignals(block)

        widget.option_box.menu.s000.valueChanged.connect(update_invert_checkbox)

        # Snapping re-rounds the CURRENT frame, so the frame-entry controls
        # have nothing to feed and grey out for every mode but None.
        self.sb.enable_when(
            widget.option_box.menu, "s000,cmb000,lbl020,chk010", "cmb001", "none"
        )
        # Invert needs a direction to reverse: the Frame field's sign, or a
        # directional snap. The clean-number modes have neither.
        self.sb.enable_when(
            widget.option_box.menu, "chk011", "cmb001", {"none", "floor", "ceil"}
        )

    def tb000(self, widget):
        """Go To Frame: jump the time slider to the next/previous key or a snap target."""
        update = widget.option_box.menu.chk001.isChecked()

        cmb001 = widget.option_box.menu.cmb001
        snap_mode = cmb001.itemData(cmb001.currentIndex())
        invert = widget.option_box.menu.chk011.isChecked()

        if snap_mode == "none":
            time_value = widget.option_box.menu.s000.value()
            cmb000 = widget.option_box.menu.cmb000
            mode = cmb000.itemData(cmb000.currentIndex())
            relative = mode == "Relative"
            time = time_value
        else:
            # Snap mode: use current time (time=None)
            time = None
            relative = False

        mtk.set_current_frame(
            time=time,
            update=update,
            relative=relative,
            snap_mode=snap_mode,
            invert_snap=invert,
        )

    def tb001_init(self, widget):
        """Invert Keyframes Init"""
        widget.option_box.menu.setTitle("Invert Keys")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb035",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INVERT_MODE),
        )
        for text, data in [
            ("Mode: X", "horizontal"),
            ("Mode: Y", "vertical"),
            ("Mode: X & Y", "both"),
        ]:
            cmb.addItem(text, data)

        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Time",
                bullets=[
                    "<b>Auto</b> (-1, default) — mirror the keys <b>in place</b>: "
                    "the animation reverses inside its own range. A move, not a "
                    "copy, so Relative and Delete Original do not apply.",
                    "<b>Any other value</b> — leave the source alone and place a "
                    "<b>reversed copy</b> starting here.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Pivot: ",
            setObjectName="d000",
            set_limits=[-100000, 100000],
            setValue=0.0,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INVERT_PIVOT),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk002",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INVERT_RELATIVE),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Original",
            setObjectName="chk005",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Delete Original",
                body="Remove the source keys once the reversed copy is placed, "
                "turning the copy into a move.",
                notes=[
                    "Already implied when Time is Auto — an in-place mirror is "
                    "a move by definition."
                ],
            ),
        )

        # Time controls apply to the X (horizontal) axis, the value pivot to Y.
        # Relative/Delete Original describe the reversed COPY, so they also go
        # dead at Time = Auto, where invert_keys mirrors in place and ignores
        # both (see mtk.AnimUtils.invert_keys).
        m = widget.option_box.menu
        self.sb.enable_when(m, "s001", "cmb035", {"horizontal", "both"})
        self.sb.enable_when(m, "d000", "cmb035", {"vertical", "both"})
        self.sb.enable_when(
            m,
            "chk002,chk005",
            ["cmb035", "s001"],
            lambda mode, time: mode in {"horizontal", "both"} and time != -1,
        )

    def tb001(self, widget):
        """Invert keyframes (selected keys preferred, fallback to all keys)."""
        cmb = widget.option_box.menu.cmb035
        mode = cmb.itemData(cmb.currentIndex())
        time_value = widget.option_box.menu.s001.value()
        value_pivot = widget.option_box.menu.d000.value()
        relative = widget.option_box.menu.chk002.isChecked()
        delete_original = widget.option_box.menu.chk005.isChecked()

        # Use None (auto) when time is -1 to let invert_keys use current time
        time = None if time_value == -1 else time_value

        try:
            mtk.invert_keys(
                time=time,
                relative=relative,
                delete_original=delete_original,
                mode=mode,
                value_pivot=value_pivot,
            )
        except RuntimeError as e:
            self.sb.message_box(
                "<strong>Nothing to invert</strong>.<br>"
                f"{e}<br><br>"
                "Select one or more objects with keyframes, "
                "or pick keys directly in the <hl>Graph Editor</hl>."
            )
            return

    def tb002_init(self, widget):
        """Adjust Spacing Init"""
        widget.option_box.menu.setTitle("Adjust Spacing")
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Frame: ",
            setObjectName="s002",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="Where the shift starts. Every key at or after this time "
                "moves; everything before it stays put.",
                notes=["<b>Auto</b> (-1) uses the current playhead time."],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[-100000, 100000],
            setValue=1,
            setToolTip=self.sb.tooltip.fmt(
                title="Amount",
                body="How far the affected keys move.",
                bullets=[
                    "<b>Positive</b> — pushes keys later, opening up time.",
                    "<b>Negative</b> — pulls keys earlier, compressing timing.",
                ],
                notes=[
                    "<b>Exact Gap</b> re-reads this as a target gap size and "
                    "requires a positive value — a zero or negative Amount is "
                    "refused with a warning."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk004",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Relative",
                body="How <b>Frame</b> above is read — this does not change how "
                "far the keys move.",
                bullets=[
                    "<b>On</b> (default) — Frame is an offset from the current "
                    "playhead time.",
                    "<b>Off</b> — Frame is an absolute frame number.",
                ],
                notes=["Ignored while Frame is Auto."],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Preserve Keys",
            setObjectName="chk003",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Preserve Keys",
                body="If a key already sits exactly on the start frame, re-anchor "
                "it at its own value instead of letting the shift drag it along.",
                notes=[
                    "Only keys the current scope can see count — under "
                    "<b>Scope: Selected Keys</b>, an unselected key on the start "
                    "frame is invisible to this."
                ],
            ),
        )
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb036",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                body="Which curves the shift reaches.",
                bullets=[
                    "<b>Selected Objects</b> — every curve on the selection.",
                    "<b>Selected Keys</b> — only the keys picked in the Graph "
                    "Editor; the object selection is ignored.",
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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Exact Gap",
            setObjectName="chk021",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Exact Gap",
                body="Re-reads <b>Amount</b> as the gap you want, not the "
                "distance to move: the shift is sized so the first key after the "
                "start frame lands exactly on "
                "<code>start&nbsp;+&nbsp;amount</code>.",
                notes=[
                    "Requires a positive Amount.",
                    "Use it to clear a precise window for new animation, "
                    "whatever the keys were doing before.",
                ],
            ),
        )

    def tb002(self, widget):
        """Adjust spacing"""
        amount = widget.option_box.menu.s003.value()
        time_value = widget.option_box.menu.s002.value()
        relative = widget.option_box.menu.chk004.isChecked()
        preserve_keys = widget.option_box.menu.chk003.isChecked()
        scope = widget.option_box.menu.cmb036.currentData()
        exact_gap = widget.option_box.menu.chk021.isChecked()

        selected_keys_only = scope == "keys"
        if scope == "scene":
            objects = None
        else:
            objects = cmds.ls(sl=True, type="transform", long=True) or []
            if not objects:
                self.sb.message_box("No objects selected.")
                return

        # Use None when -1 to use current playhead time
        time = None if time_value == -1 else time_value

        mtk.adjust_key_spacing(
            objects,
            spacing=amount,
            time=time,
            relative=relative,
            preserve_keys=preserve_keys,
            selected_keys_only=selected_keys_only,
            exact_gap=exact_gap,
        )

    def tb003_init(self, widget):
        """Stagger Keys Init"""
        # mtk.stagger_keys narrows to a Graph Editor key selection when there
        # is one; btk.stagger_keys has no such mode, so the shared .ui cannot
        # say it.
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Stagger Keys",
                body="Re-time the selected objects so their animations play one "
                "after another instead of on top of each other.",
                notes=[
                    "With keys selected in the Graph Editor, only those keys "
                    "are staggered; otherwise every key on the selection is.",
                    "Option box: the gap or fixed interval between blocks, "
                    "grouping for objects that overlap or touch, and the order.",
                ],
            )
        )
        widget.option_box.menu.setTitle("Stagger Keys")
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Start Frame: ",
            setObjectName="s005",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Start Frame",
                body="Where the first block's animation begins.",
                notes=["<b>Auto</b> (-1) starts from the earliest existing key."],
            ),
        )
        # QDoubleSpinBox, not QSpinBox: stagger_keys reads a value strictly
        # between -1.0 and 1.0 as a PERCENTAGE of each block's duration
        # (mtk.StaggerKeys.stagger_keys -> SegmentKeys.execute_stagger). An
        # integer spinbox made that documented mode unreachable.
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Spacing: ",
            setObjectName="s004",
            set_limits=[-100000, 100000],
            setDecimals=2,
            setSingleStep=1.0,
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Spacing",
                sections=[
                    (
                        "Sequential (Use Intervals off)",
                        [
                            "<b>0</b> (default) — blocks run end-to-start with no gap.",
                            "<b>Positive</b> — that many frames of gap.",
                            "<b>Negative</b> — that many frames of overlap.",
                            "<b>Strictly between -1 and 1</b> — read as a "
                            "<i>fraction of each block's own duration</i> "
                            "(<code>0.5</code> = a half-length gap, "
                            "<code>-0.3</code> = a 30% overlap).",
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
                notes=[
                    "The fraction range is exclusive: <code>1.0</code> and "
                    "<code>-1.0</code> mean one literal frame, not 100%."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Intervals",
            setObjectName="chk025",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Intervals",
                body="Place each block on a fixed grid instead of packing them "
                "end-to-start.",
                bullets=[
                    "<b>Off</b> (default) — each block starts where the previous "
                    "one ended, plus <b>Spacing</b>.",
                    "<b>On</b> — <b>Spacing</b> becomes the interval between "
                    "block starts (100 &#8594; frames 0, 100, 200…). A block too "
                    "long to fit is pushed on to the next interval.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Overlapping",
            setObjectName="chk014",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_STAGGER_GROUP_OVERLAPPING),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Touching",
            setObjectName="chk029",
            setChecked=False,
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
                notes=[
                    "Turns <b>Group Overlapping</b> on for you — checking this "
                    "alone is enough."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Attrs Only",
            setObjectName="chk024",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Channel Box Attrs Only",
                body="Restrict the stagger to the attributes highlighted in the "
                "Channel Box, leaving every other curve where it is.",
                notes=[
                    "With nothing highlighted the operation is refused rather "
                    "than silently widening to every attribute."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Smooth Tangents",
            setObjectName="chk009",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Smooth Tangents",
                body="Re-solve tangents to <b>auto</b> on the re-timed keys so "
                "the seams between staggered blocks do not pop.",
                notes=[
                    "Visibility curves are always forced back to stepped, "
                    "checked or not — a smoothed visibility curve would fade "
                    "objects in and out."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk008",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_STAGGER_INVERT),
        )

    def tb003(self, widget):
        """Stagger Keys"""
        spacing = widget.option_box.menu.s004.value()
        start_frame_value = widget.option_box.menu.s005.value()
        use_intervals = widget.option_box.menu.chk025.isChecked()
        invert = widget.option_box.menu.chk008.isChecked()
        smooth_tangents = widget.option_box.menu.chk009.isChecked()
        group_overlapping = widget.option_box.menu.chk014.isChecked()
        merge_touching = widget.option_box.menu.chk029.isChecked()
        channel_box_only = widget.option_box.menu.chk024.isChecked()

        # Only use start_frame if not -1
        start_frame = start_frame_value if start_frame_value != -1 else None

        selected_objects = cmds.ls(sl=True) or []
        mtk.stagger_keys(
            selected_objects,
            start_frame=start_frame,
            spacing=spacing,
            use_intervals=use_intervals,
            avoid_overlap=True,
            invert=invert,
            smooth_tangents=smooth_tangents,
            group_overlapping=group_overlapping,
            merge_touching=merge_touching,
            channel_box_attrs_only=channel_box_only,
            verbose=True,
        )

    def tb004_init(self, widget):
        """Transfer Keys Init"""
        # Maya picks the source by SELECTION ORDER (Blender uses the active
        # object), and narrows to a Graph Editor key selection when there is
        # one — neither is safe to state in the shared .ui.
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Transfer Keys",
                body="Copy the <b>first</b> selected object's keyframes onto "
                "every object selected after it.",
                notes=[
                    "With keys selected in the Graph Editor, only those keys "
                    "and their attributes are transferred.",
                    "Option box: offset the animation onto each target's own "
                    "current pose, carry tangents across, and clean up the "
                    "source before copying.",
                ],
            )
        )
        widget.option_box.menu.setTitle("Transfer Keys")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk006",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_TRANSFER_RELATIVE),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Tangents",
            setObjectName="chk007",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Tangents",
                body="Carry the source's tangent handles across as well, so the "
                "targets ease exactly like the source.",
                notes=["Off leaves the targets on Maya's default tangents."],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Optimize Before Transfer",
            setObjectName="chk035",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Optimize Before Transfer",
                body="Run <b>Optimize Keys</b> over the source first, so "
                "redundant keys are not copied onto every target.",
                notes=[
                    "This edits the source curves, not just the copy — the "
                    "cleanup stays behind after the transfer."
                ],
            ),
        )

    def tb004(self, widget):
        """Transfer Keys"""
        relative = widget.option_box.menu.chk006.isChecked()
        tangents = widget.option_box.menu.chk007.isChecked()
        optimize = widget.option_box.menu.chk035.isChecked()

        selected_objects = cmds.ls(sl=True) or []
        mtk.transfer_keyframes(
            selected_objects,
            relative=relative,
            transfer_tangents=tangents,
            optimize=optimize,
        )

    def tb005_init(self, widget):
        """Add/Remove Intermediate Keys Init"""
        widget.option_box.menu.setTitle("Intermediate Keys")
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Start Time: ",
            setObjectName="s021",
            set_limits=[-1, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Start Time",
                body="First frame of the window that gets sampled.",
                notes=["<b>Auto</b> (-1) uses each curve's own first key."],
            ),
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="End Time: ",
            setObjectName="s006",
            set_limits=[-1, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="End Time",
                body="Last frame of the window that gets sampled.",
                notes=["<b>Auto</b> (-1) uses each curve's own last key."],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Percent: ",
            setObjectName="s007",
            set_limits=[0, 100],
            setValue=5,
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
                    "so short and long curves stay proportionally keyed.",
                    "Frames whose value already matches both neighbours are "
                    "skipped, so even 100 fills only the parts of a curve that "
                    "are actually moving.",
                    "Never samples to nothing: below one frame's worth it "
                    "still places a single key.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Ignore Visibility",
            setObjectName="chk028",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Ignore Visibility",
                body="Leave <code>visibility</code> curves out of both the add "
                "and the remove pass.",
                notes=[
                    "Worth having on when baking: a sampled visibility curve "
                    "turns a clean on/off switch into a run of stepped keys."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Intermediate Keys",
            setObjectName="chk027",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_REMOVE_INTERMEDIATE),
        )
        # Percent only drives the add-keys branch.
        self.sb.enable_when(widget.option_box.menu, "s007", "chk027", invert=True)

    def tb005(self, widget):
        """Add/Remove Intermediate Keys.

        Note the add pass runs with ``include_flat=False`` (the mayatk
        default), so frames whose value matches both neighbours are skipped —
        "sample every frame" only fills the parts of a curve that are moving.
        """
        remove_mode = widget.option_box.menu.chk027.isChecked()
        ignore_visibility = widget.option_box.menu.chk028.isChecked()

        objects = cmds.ls(sl=True, flatten=True) or []
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        # Set ignore parameter based on checkbox
        ignore = "visibility" if ignore_visibility else None

        # Build time_range parameter based on UI values
        start_time_value = widget.option_box.menu.s021.value()
        end_time_value = widget.option_box.menu.s006.value()

        if start_time_value == -1 and end_time_value == -1:
            # Both auto-detect
            time_range = None
        elif start_time_value == -1:
            # Auto-detect start, explicit end
            time_range = end_time_value
        elif end_time_value == -1:
            # Explicit start, auto-detect end - need to get end from keyframes
            # This is an edge case; for simplicity use tuple
            time_range = (start_time_value, None)
        else:
            # Both explicit
            time_range = (start_time_value, end_time_value)

        if remove_mode:
            # Remove intermediate keys with time_range
            keys_removed = mtk.remove_intermediate_keys(
                objects, time_range, ignore=ignore
            )
            if keys_removed > 0:
                self.sb.message_box(f"Removed {keys_removed} intermediate keyframe(s).")
            else:
                self.sb.message_box("No intermediate keyframes found to remove.")
        else:
            # Add intermediate keys
            percent = widget.option_box.menu.s007.value()
            mtk.add_intermediate_keys(objects, time_range, percent, ignore=ignore)

    def tb006_init(self, widget):
        """Move Keys Init"""
        widget.option_box.menu.setTitle("Move Keys")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Move Selected Keys",
            setObjectName="chk031",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Move Selected Keys",
                bullets=[
                    "<b>On</b> (default) — move only the keys picked in the "
                    "Graph Editor.",
                    "<b>Off</b> — move every key on the selected objects.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Maintain Spacing",
            setObjectName="chk012",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Maintain Spacing",
                bullets=[
                    "<b>On</b> (default) — the selection moves as one rigid "
                    "block; the offsets between objects are preserved.",
                    "<b>Off</b> — every object is moved onto the target frame "
                    "independently, stacking them together.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Only",
            setObjectName="chk033",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Channel Box Only",
                body="Restrict the move to the attributes highlighted in the "
                "Channel Box.",
                notes=["Composes with <b>Move Selected Keys</b> either way."],
            ),
        )
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_align",
            setToolTip=self.sb.tooltip.fmt(
                title="Align",
                body="Which end of the moved key range lands on the current frame.",
                bullets=[
                    "<b>Start</b> — the earliest key lands there; the animation "
                    "runs forward from the playhead.",
                    "<b>End</b> — the latest key lands there; the animation "
                    "arrives at the playhead.",
                    "<b>Auto</b> — picks whichever end is nearer: End when the "
                    "range's midpoint sits before the playhead, Start otherwise.",
                ],
            ),
        )
        for text, data in [
            ("Align: Auto", "auto"),
            ("Align: Start", "start"),
            ("Align: End", "end"),
        ]:
            cmb.addItem(text, data)

    def tb006(self, widget):
        """Move Keys: move the selected keys in time, with optional spacing/alignment."""
        selected_keys_only = widget.option_box.menu.chk031.isChecked()
        retain_spacing = widget.option_box.menu.chk012.isChecked()
        channel_box_attrs_only = widget.option_box.menu.chk033.isChecked()
        align = widget.option_box.menu.cmb_align.currentData()

        objects = cmds.ls(sl=True, flatten=True) or []
        if not objects:
            self.sb.message_box("You must select at least one object or set of keys.")
            return
        mtk.move_keys_to_frame(
            objects,
            selected_keys_only=selected_keys_only,
            retain_spacing=retain_spacing,
            channel_box_attrs_only=channel_box_attrs_only,
            align=align,
        )

    def tb007_init(self, widget):
        """Align Selected Keyframes Init"""
        widget.option_box.menu.setTitle("Align Selected Keyframes")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Earliest Frame",
            setObjectName="chk013",
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
                    "Auto — an explicit target needs no election."
                ],
            ),
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Frame: ",
            setObjectName="spn000",
            setMinimum=-10000,
            setMaximum=10000,
            setValue=-1,
            setCustomDisplayValues={-1: "Auto"},
            setToolTip=self.sb.tooltip.fmt(
                title="Frame",
                body="Align every object's selected keys onto this exact frame.",
                notes=[
                    "<b>Auto</b> (-1) elects the target from the selection "
                    "instead, per <b>Use Earliest Frame</b> above."
                ],
            ),
        )
        # An explicit target frame makes the earliest/latest election moot
        # (mtk.AnimUtils.align_selected_keyframes ignores use_earliest then).
        self.sb.enable_when(widget.option_box.menu, "chk013", "spn000", -1)

    def tb007(self, widget):
        """Align Selected Keyframes"""
        use_earliest = widget.option_box.menu.chk013.isChecked()
        target_frame_value = widget.option_box.menu.spn000.value()

        # Only use target_frame if not -1, otherwise use None to auto-detect
        target_frame = target_frame_value if target_frame_value != -1 else None

        objects = cmds.ls(sl=True, flatten=True) or []
        if not objects:
            self.sb.message_box(
                "You must select at least one object with selected keyframes."
            )
            return

        result = mtk.align_selected_keyframes(
            objects,
            target_frame=target_frame,
            use_earliest=use_earliest,
        )

        if not result:
            self.sb.message_box(
                "No selected keyframes found. Select keyframes in the Graph Editor first."
            )

    def tb008_init(self, widget):
        """Set Visibility Keys Init"""
        widget.option_box.menu.setTitle("Set Visibility Keys")
        # Visible vs Hidden is a two-valued choice, not a modifier — name both states.
        vis = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_visibility",
            setToolTip=self.sb.tooltip.fmt(
                title="Visibility",
                body="The state written at the chosen frame(s) — "
                "<b>Visible</b> keys <code>visibility</code> on, <b>Hidden</b> "
                "keys it off.",
            ),
        )
        vis.addItems(["Visible", "Hidden"])
        vis.setCurrentText("Visible")  # preserve prior default (checkbox on = visible)
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb002",
            setToolTip=self.sb.tooltip.fmt(
                title="When",
                body="Where in each object's own keyed range the visibility key "
                "is written.",
                bullets=[
                    "<b>Start</b> / <b>End</b> — on the range's first / last frame.",
                    "<b>Both</b> — on each end.",
                    "<b>Before Start</b> / <b>After End</b> — one frame outside "
                    "the range, so the state is already settled when the "
                    "animation begins or ends.",
                ],
                notes=[
                    "The range is detected per object, so a mixed selection is "
                    "keyed at each object's own boundaries."
                ],
            ),
        )
        for text, data in [
            ("Start", "start"),
            ("End", "end"),
            ("Both", "both"),
            ("Before Start", "before_start"),
            ("After End", "after_end"),
        ]:
            cmb.addItem(text, data)
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Offset: ",
            setObjectName="s008",
            set_limits=[-10000, 10000],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_VISIBILITY_OFFSET),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Overlapping",
            setObjectName="chk016",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_VISIBILITY_GROUP_OVERLAPPING),
        )

    def tb008(self, widget):
        """Set Visibility Keys"""
        visible = widget.option_box.menu.cmb_visibility.currentText() == "Visible"
        when = widget.option_box.menu.cmb002.currentData()
        offset = widget.option_box.menu.s008.value()
        group_overlapping = widget.option_box.menu.chk016.isChecked()

        selected_objects = cmds.ls(sl=True) or []
        if not selected_objects:
            self.sb.message_box("You must select at least one object.")
            return

        result = mtk.set_visibility_keys(
            selected_objects,
            visible=visible,
            when=when,
            offset=offset,
            group_overlapping=group_overlapping,
        )

        if result == 0:
            self.sb.message_box(
                "No visibility keys created. Make sure selected objects have keyframes."
            )

    def tb009_init(self, widget):
        """Snap Keys to Frames Init"""
        widget.option_box.menu.setTitle("Snap Keys to Frames")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb003",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SNAP_METHOD),
        )
        for text, data in [
            ("Nearest", "nearest"),
            ("Floor", "floor"),
            ("Ceil", "ceil"),
            ("Half Up", "half_up"),
            ("Preferred", "preferred"),
            ("Aggressive Preferred", "aggressive_preferred"),
        ]:
            cmb.addItem(text, data)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Selected Keys Only",
            setObjectName="chk017",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Selected Keys Only",
                bullets=[
                    "<b>Off</b> (default) — snap every key on the selected objects.",
                    "<b>On</b> — snap only the keys picked in the Graph Editor.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Time Range",
            setObjectName="chk018",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Time Range",
                body="Limit the snap to keys inside the scene's <b>playback "
                "range</b> (the time slider's start/end, not the selected "
                "range highlight).",
                notes=["Keys outside the range keep their fractional times."],
            ),
        )

    def tb009(self, widget):
        """Snap Keys to Frames"""
        method = widget.option_box.menu.cmb003.currentData()
        selected_only = widget.option_box.menu.chk017.isChecked()
        use_time_range = widget.option_box.menu.chk018.isChecked()

        # Get time range if requested
        time_range = None
        if use_time_range:
            anim_start_time = cmds.playbackOptions(query=True, minTime=True)
            anim_end_time = cmds.playbackOptions(query=True, maxTime=True)
            time_range = (anim_start_time, anim_end_time)

        selected_objects = cmds.ls(sl=True) or []
        if not selected_objects:
            self.sb.message_box("You must select at least one object.")
            return

        result = mtk.snap_keys_to_frames(
            selected_objects,
            method=method,
            selected_only=selected_only,
            time_range=time_range,
        )

        if result == 0:
            self.sb.message_box(
                "No keyframes snapped. Make sure selected objects have keyframes with decimal values."
            )
        else:
            self.sb.message_box(f"Snapped {result} keyframe(s) to whole frames.")

    def tb010_init(self, widget):
        """Delete Keys Init"""
        widget.option_box.menu.setTitle("Delete Keys")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb004",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_DELETE_TIME_RANGE),
        )

        # Add items with display text and associated data
        items = [
            ("All Keyframes", "all"),
            ("Current Frame", "current"),
            ("Before Current", "before"),
            ("Before & Current", "before|current"),
            ("After Current", "after"),
            ("Current & After", "after|current"),
        ]

        for display_text, data_value in items:
            cmb.addItem(display_text)
            cmb.setItemData(cmb.count() - 1, data_value)

        cmb.setCurrentIndex(0)

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Only",
            setObjectName="chk020",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Channel Box Only",
                bullets=[
                    "<b>Off</b> (default) — delete keys on every keyable attribute.",
                    "<b>On</b> — delete only on the attributes highlighted in "
                    "the Channel Box.",
                ],
            ),
        )

    def tb010(self, widget):
        """Delete Keys: delete keys on the selection over a chosen time range."""
        cmb = widget.option_box.menu.cmb004
        time_param = cmb.itemData(cmb.currentIndex())
        channel_box_only = widget.option_box.menu.chk020.isChecked()

        objects = cmds.ls(sl=True) or []
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        kwargs = {}
        if time_param != "all":
            kwargs["time"] = time_param
        if channel_box_only:
            kwargs["channel_box_only"] = True
        mtk.delete_keys(objects, **kwargs)

    def tb011_init(self, widget):
        """Tie/Untie Keyframes Init"""
        widget.option_box.menu.setTitle("Tie/Untie Keyframes")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Absolute Range",
            setObjectName="chk023",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Use Absolute Range",
                body="Which range gets the bookend keys.",
                bullets=[
                    "<b>Off</b> (default) — the scene's playback range.",
                    "<b>On</b> — the true keyed extent, from the earliest to "
                    "the latest key across the objects.",
                ],
                notes=[
                    "Tie only. Untie removes exactly the bookends that were "
                    "recorded when tying, so it has no range to choose."
                ],
            ),
        )
        # Tie vs Untie is a two-valued choice, not a modifier — name both states.
        tie = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_tie",
            setToolTip=self.sb.tooltip.fmt(
                title="Tie / Untie",
                bullets=[
                    "<b>Tie</b> — insert bookend keys at the range boundaries "
                    "so every animated object is pinned at both ends.",
                    "<b>Untie</b> — remove exactly those bookends again. Each "
                    "tied curve records what was inserted, so genuine "
                    "animation is never cut.",
                ],
                notes=[
                    "Tie edits keys through the OpenMaya API to freeze adjacent "
                    "tangents, which bypasses the undo queue — "
                    "<b>Ctrl+Z will not remove the bookends</b>. Use Untie."
                ],
            ),
        )
        tie.addItems(["Tie", "Untie"])
        tie.setCurrentText("Tie")  # preserve prior default (checkbox off = tie)
        # Absolute range describes where bookends go IN, so it is dead in
        # Untie mode (tb011 only forwards it when tying).
        self.sb.enable_when(widget.option_box.menu, "chk023", "cmb_tie", 0)

    def tb011(self, widget):
        """Tie/Untie Keyframes"""
        untie_mode = widget.option_box.menu.cmb_tie.currentText() == "Untie"
        absolute = widget.option_box.menu.chk023.isChecked()

        objects = cmds.ls(sl=True) or []
        if not objects:
            # If no selection, operate on all keyed objects in scene
            objects = None

        if untie_mode:
            # untie removes exactly the recorded/detected bookends — the
            # absolute-range option only applies when tying.
            mtk.untie_keyframes(objects=objects)
        else:
            mtk.tie_keyframes(objects=objects, absolute=absolute)

    def tb013_init(self, widget):
        """Select Keys Init"""
        widget.option_box.menu.setTitle("Select Keys")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb041",
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
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Start Frame: ",
            setObjectName="s012",
            set_limits=[-10000, 10000],
            setValue=1,
            setToolTip=self.TIP_SELECT_RANGE_START,
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="End Frame: ",
            setObjectName="s013",
            set_limits=[-10000, 10000],
            setValue=100,
            setToolTip=self.TIP_SELECT_RANGE_END,
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Only",
            setObjectName="chk034",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Channel Box Only",
                body="Restrict the selection to the attributes highlighted in "
                "the Channel Box.",
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Add to Selection",
            setObjectName="chk039",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Add to Selection",
                body="Extend the current Graph Editor key selection instead of "
                "replacing it — run the button repeatedly to build a set out of "
                "several ranges.",
            ),
        )
        # Start/End only feed the explicit Range mode.
        self.sb.enable_when(widget.option_box.menu, "s012,s013", "cmb041", "range")

    def tb013(self, widget):
        """Select Keys: select keys on the selection within a frame range."""
        selection_type = widget.option_box.menu.cmb041.currentData()
        start_frame = widget.option_box.menu.s012.value()
        end_frame = widget.option_box.menu.s013.value()
        channel_box_only = widget.option_box.menu.chk034.isChecked()
        add_to_selection = widget.option_box.menu.chk039.isChecked()

        # Determine time parameter based on selection type
        if selection_type == "range":
            time = (start_frame, end_frame)
        elif selection_type == "all":
            time = None
        else:
            time = selection_type

        # Get objects to affect
        selected_objects = cmds.ls(sl=True) or []
        objects = selected_objects if selected_objects else None

        keys_selected = mtk.select_keys(
            objects=objects,
            time=time,
            channel_box_only=channel_box_only,
            add_to_selection=add_to_selection,
        )

        if keys_selected == 0:
            self.sb.message_box("No keyframes found to select.")
        else:
            self.sb.message_box(f"Selected {keys_selected} keyframe(s).")

    def tb014_init(self, widget):
        """Scale Keys Init"""
        widget.option_box.menu.setTitle("Scale Keys")
        # Re-applied by the mode switch below, so rendered once here.
        uniform_tooltip = self.sb.tooltip.fmt(**self.TIP_SCALE_FACTOR_UNIFORM)
        speed_tooltip = self.sb.tooltip.fmt(**self.TIP_SCALE_FACTOR_SPEED)
        cmb_mode = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb014",
            block_signals_on_restore=False,  # Allow signals during restore to trigger update_mode_ui
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
                    "normalise and is skipped.",
                    "A Graph Editor key selection narrows Uniform mode only; "
                    "Speed modes always retime the whole block.",
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
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Factor: ",
            setObjectName="d001",
            setMinimum=0.01,
            setMaximum=100000.0,
            setSingleStep=0.1,
            setValue=1.0,
            setDecimals=2,
            setToolTip=uniform_tooltip,
        )
        cmb_group = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb033",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_GROUPING),
        )
        for text, data in [
            ("Single Group", "single_group"),
            ("Per Object Pivots", "per_object"),
            ("Group Overlaps", "overlap_groups"),
        ]:
            cmb_group.addItem(text, data)

        cmb_snap = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb034",
            setToolTip=self.sb.tooltip.fmt(
                title="Snap",
                body="Scaling lands keys on fractional frames; this decides how "
                "they are rounded back afterwards. Applies to both modes.",
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

        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Samples: ",
            setObjectName="s014",
            setMinimum=8,
            setMaximum=512,
            setSingleStep=8,
            setValue=64,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_SAMPLES),
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Attrs Only",
            setObjectName="chk_channel_box",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Channel Box Attrs Only",
                body="Restrict the scale to the attributes highlighted in the "
                "Channel Box, leaving every other curve at its current timing.",
                notes=[
                    "With nothing highlighted the operation is refused rather "
                    "than silently widening to every attribute."
                ],
            ),
        )

        # Absolute vs Relative is a two-valued mode, not a modifier — name both states.
        scale_mode = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_scale_mode",
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_RELATIVE_ABSOLUTE),
        )
        scale_mode.addItems(["Relative", "Absolute"])
        scale_mode.setCurrentText(
            "Relative"
        )  # preserve prior default (checkbox off = relative)

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Split Static Segments",
            setObjectName="chk_split_static",
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
                notes=[
                    "Turn it off when an object's whole timeline is one "
                    "continuous performance you want retimed end to end."
                ],
            ),
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Touching",
            setObjectName="chk_merge_touching",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_SCALE_GROUP_TOUCHING),
        )
        # Nothing to merge unless the grouping pass is the one that looks at
        # ranges (mtk.ScaleKeys only consults merge_touching for
        # group_mode="overlap_groups").
        self.sb.enable_when(
            widget.option_box.menu, "chk_merge_touching", "cmb033", "overlap_groups"
        )

        # Auto-toggle UI elements based on mode
        def update_mode_ui(index):
            is_speed_mode = index > 0
            spinbox = widget.option_box.menu.d001
            samples_spinbox = widget.option_box.menu.s014
            scale_mode = widget.option_box.menu.cmb_scale_mode

            # Only samples spinbox is speed-mode specific
            # Snap mode now works for both uniform and speed modes
            samples_spinbox.setEnabled(is_speed_mode)

            # Update factor label/step/tooltip based on mode. The RANGE is
            # deliberately mode-independent (see d001 above): a per-mode
            # setRange silently clamped both an Absolute target duration and
            # whatever value QSettings restored.
            if is_speed_mode:
                spinbox.setPrefix("Speed: ")
                spinbox.setSingleStep(0.5)
                spinbox.setValue(5.0)
                spinbox.setToolTip(speed_tooltip)
                # Default to Absolute (Target Speed) for Speed Mode
                scale_mode.setCurrentText("Absolute")
            else:
                spinbox.setPrefix("Factor: ")
                spinbox.setSingleStep(0.1)
                spinbox.setValue(1.0)
                spinbox.setToolTip(uniform_tooltip)
                # Default to Relative (Multiplier) for Uniform Mode
                scale_mode.setCurrentText("Relative")

        widget.option_box.menu.cmb014.currentIndexChanged.connect(update_mode_ui)
        update_mode_ui(0)  # Initialize UI state

    def tb014(self, widget):
        """Scale Keys: scale the selected keys in time about a pivot."""
        mode_data = widget.option_box.menu.cmb014.currentData()
        factor = widget.option_box.menu.d001.value()
        channel_box_only = widget.option_box.menu.chk_channel_box.isChecked()
        absolute_mode = (
            widget.option_box.menu.cmb_scale_mode.currentText() == "Absolute"
        )
        split_static = widget.option_box.menu.chk_split_static.isChecked()
        merge_touching = widget.option_box.menu.chk_merge_touching.isChecked()
        group_mode = widget.option_box.menu.cmb033.currentData()
        snap_mode = widget.option_box.menu.cmb034.currentData()

        # Get objects to affect
        selected_objects = cmds.ls(sl=True) or []
        if not selected_objects:
            self.sb.message_box("You must select at least one object.")
            return

        # Determine mode and include_rotation from combo data
        if mode_data == "speed":
            mode, include_rotation = "speed", True
        elif mode_data == "speed_linear":
            mode, include_rotation = "speed", False
        elif mode_data == "speed_rotation":
            mode, include_rotation = "speed", "only"
        else:
            mode, include_rotation = "uniform", False

        # Determine keys parameter - check for selected keys in graph editor
        selected_keys_in_graph = cmds.keyframe(query=True, sl=True, tc=True)
        keys = "selected" if selected_keys_in_graph and mode == "uniform" else None

        # Get samples parameter for speed mode
        samples = widget.option_box.menu.s014.value() if mode == "speed" else None

        # Call the method with updated API (factor param serves both modes)
        keys_scaled = mtk.scale_keys(
            objects=selected_objects,
            factor=factor,
            mode=mode,
            pivot=None,  # Auto-detect pivot
            keys=keys,
            channel_box_attrs_only=channel_box_only,
            group_mode=group_mode,
            snap_mode=snap_mode,
            samples=samples,
            include_rotation=include_rotation,
            absolute=absolute_mode,
            split_static=split_static,
            merge_touching=merge_touching,
            prevent_overlap=True,
            verbose=True,
        )

        # Report results
        if keys_scaled > 0:
            if mode == "speed":
                # Speed mode
                if absolute_mode:
                    mode_str = f"{factor:.2f} units/frame"
                else:
                    mode_str = f"{factor:.2f}x speed"
            else:
                # Uniform mode
                if absolute_mode:
                    mode_str = f"to {factor:.2f} frames"
                else:
                    mode_str = f"{factor * 100:.0f}%"

            context = " (channel box)" if channel_box_only else ""
            self.sb.message_box(
                f"Scaled {keys_scaled} keyframe(s){context} {mode_str}."
            )
        else:
            self.sb.message_box("No keyframes found to scale.")

    def tb015_init(self, widget):
        """Repair Corrupted Curves - Initialize option box"""
        widget.option_box.menu.setTitle("Repair Corrupted Curves")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Unfixable Curves",
            setObjectName="chk036",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Delete Unfixable Curves",
                body="Remove curves left with no usable keys once the fixes "
                "below have run.",
                notes=[
                    "Off leaves a broken curve connected but empty, which keeps "
                    "the attribute animated and unkeyable by hand."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Fix Infinite Values",
            setObjectName="chk037",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Fix Infinite Values",
                body="Repair keys whose <i>value</i> is NaN, infinite, or past "
                "the <b>Value Threshold</b> below.",
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Fix Invalid Times",
            setObjectName="chk038",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Fix Invalid Times",
                body="Repair keys sitting at an absurd <i>frame</i> — the "
                "<code>-165916080</code>-style times a corrupted curve picks up "
                "and that stretch the Graph Editor to uselessness.",
            ),
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Time Threshold: ",
            setObjectName="d015",
            set_limits=[1000, 999999999],
            setValue=100000,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_REPAIR_TIME_THRESHOLD),
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Value Threshold: ",
            setObjectName="d016",
            set_limits=[1000, 999999999],
            setValue=1000000,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_REPAIR_VALUE_THRESHOLD),
        )

    def tb015(self, widget):
        """Repair Corrupted Curves

        Automatically detects scope based on selection:
        - Selected keys in graph editor: checks only those curves
        - Selected objects: checks all keys on those objects
        - Nothing selected: checks all keys in the scene
        """
        delete_corrupted = widget.option_box.menu.chk036.isChecked()
        fix_infinite = widget.option_box.menu.chk037.isChecked()
        fix_invalid_times = widget.option_box.menu.chk038.isChecked()
        time_threshold = widget.option_box.menu.d015.value()
        value_threshold = widget.option_box.menu.d016.value()

        # Determine objects to process based on selection context
        selected_objects = cmds.ls(sl=True, flatten=True) or []
        selected_curves = mtk.AnimUtils.get_anim_curves(
            objects=None, selected_keys_only=True, recursive=True
        )

        if selected_curves:
            objects = list(set(selected_curves))
            scope_label = "selected keys"
        elif selected_objects:
            objects = selected_objects
            scope_label = "selected objects"
        else:
            objects = None
            scope_label = "entire scene"

        # Call the repair method
        result = mtk.Diagnostics.repair_corrupted_curves(
            objects=objects,
            recursive=True,
            delete_corrupted=delete_corrupted,
            fix_infinite=fix_infinite,
            fix_invalid_times=fix_invalid_times,
            time_range_threshold=time_threshold,
            value_threshold=value_threshold,
            quiet=False,
        )

        # Format and display results
        corrupted = result["corrupted_found"]
        repaired = result["curves_repaired"]
        deleted = result["curves_deleted"]
        keys_fixed = result["keys_fixed"]

        if corrupted == 0:
            self.sb.message_box(
                f"No corrupted curves found on {scope_label}. All animation curves are clean!"
            )
            return

        message = f"Found {corrupted} corrupted curve(s):\n"
        message += f"  • Repaired: {repaired}\n"
        message += f"  • Deleted: {deleted}\n"
        message += f"  • Keys fixed: {keys_fixed}\n"

        if result["details"]:
            message += "\nFirst 3 issues:\n"
            for detail in result["details"][:3]:
                message += f"  • {detail}\n"
            if len(result["details"]) > 3:
                message += f"  ... and {len(result['details']) - 3} more"

        self.sb.message_box(message)

    _TB016_SCOPES = (
        ("Selected", "selected"),
        ("All Scene Objects", "all"),
    )
    _TB016_TRAVERSAL = (
        ("None", None),
        ("Upstream", "upstream"),
        ("Downstream", "downstream"),
        ("Both", "both"),
    )

    def tb016_init(self, widget):
        """Get Animation Info — option box."""
        widget.option_box.menu.setTitle("Get Animation Info")

        cmb_scope = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                bullets=[
                    "<b>Selected</b> — only the current viewport selection.",
                    "<b>All Scene Objects</b> — every transform in the scene.",
                ],
            ),
        )
        for label, data in self._TB016_SCOPES:
            cmb_scope.addItem(label, data)

        cmb_traversal = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_traversal",
            setToolTip=self.sb.tooltip.fmt(
                title="Traversal",
                body="Widen the report past the literal selection by walking the "
                "dependency graph, so animation that drives (or is driven by) "
                "the selection is included.",
                bullets=[
                    "<b>None</b> — the selection exactly as picked.",
                    "<b>Upstream</b> — also what feeds it (controls, "
                    "constraints, drivers).",
                    "<b>Downstream</b> — also what it feeds.",
                    "<b>Both</b> — either direction.",
                ],
                notes=[
                    "Greyed out under Scope = All Scene Objects, which already "
                    "covers everything."
                ],
            ),
        )
        for label, data in self._TB016_TRAVERSAL:
            cmb_traversal.addItem(label, data)

        # Disable traversal when scope is anything but Selected.
        def _sync_traversal(_idx=None):
            scope = cmb_scope.currentData()
            cmb_traversal.setEnabled(scope == "selected")

        cmb_scope.currentIndexChanged.connect(_sync_traversal)
        _sync_traversal()

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Sort by Time",
            setObjectName="chk_sort_time",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INFO_SORT_BY_TIME),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="CSV Output",
            setObjectName="chk_csv_output",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="CSV Output",
                body="Render the report as comma-separated rows, ready to paste "
                "into a spreadsheet.",
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Ignore Holds",
            setObjectName="chk_ignore_holds",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_INFO_IGNORE_HOLDS),
        )

    def tb016(self, widget):
        """Get Animation Info — render the report to the viewer dialog.

        Feedback while running is the application wait cursor (set by
        the slot dispatcher for every slot). The dialog itself opens
        when the report is ready, which is its own "done" signal.
        """
        menu = widget.option_box.menu
        scope = menu.cmb_scope.currentData() or "selected"
        traversal = menu.cmb_traversal.currentData() if scope == "selected" else None
        by_time = menu.chk_sort_time.isChecked()
        csv_output = menu.chk_csv_output.isChecked()
        ignore_holds = menu.chk_ignore_holds.isChecked()

        if scope == "selected":
            objects = cmds.ls(selection=True, type="transform") or []
            if not objects:
                self.sb.message_box(
                    "<hl>Nothing selected</hl><br>"
                    "Select object(s) or switch Scope to All Scene Objects."
                )
                return
        else:  # "all"
            objects = None  # let mayatk fall through to all-scene

        with self.sb.progress(text="Working: Get Animation Info") as update:
            html = mtk.SegmentKeys.format_scene_info_html(
                objects=objects,
                detailed=True,
                by_time=by_time,
                csv_output=csv_output,
                ignore_holds=ignore_holds,
                traversal=traversal,
                progress_callback=self.sb.progress_adapter(update),
            )
        if not html:
            self.sb.message_box("<hl>No animation</hl> found in the selected scope.")
            return

        # Non-modal viewer so Maya stays responsive while reading.
        self.sb.text_view_dialog(
            html,
            "Ok",
            title="Get Animation Info",
            size=(780, 520),
            monospace=False,
        )

    def tb017_init(self, widget):
        """Step Tangents Init"""
        # Maya's step_keys only ever sets STEPPED tangents (unlike Blender's tb017,
        # which can also set linear/smooth) — override the .ui's DCC-neutral default
        # with the accurate, Maya-specific description.
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Step Tangents",
                body="Set stepped (hold) tangents on animation keys, so values "
                "jump between keys instead of interpolating — the blocking / "
                "pose-to-pose look.",
                notes=[
                    "Option box: which keys to affect (auto, current time, "
                    "selected, all) and which tangent side (in, out, both)."
                ],
            )
        )
        widget.option_box.menu.setTitle("Step Tangents")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb037",
            setToolTip=self.sb.tooltip.fmt(
                title="Keys",
                body="Which keys get stepped tangents.",
                bullets=[
                    "<b>Auto</b> — the first of these that finds anything: "
                    "Graph Editor key selection, Channel Box attributes, keys "
                    "on the current frame, then everything.",
                    "<b>Current Time</b> — only keys sitting on the playhead.",
                    "<b>Selected</b> — only keys picked in the Graph Editor; "
                    "refuses to run if none are.",
                    "<b>All</b> — every key on the selected objects.",
                ],
            ),
        )
        for text, data in [
            ("Keys: Auto", "auto"),
            ("Keys: Current Time", "current_time"),
            ("Keys: Selected", "selected"),
            ("Keys: All", "all"),
        ]:
            cmb.addItem(text, data)

        cmb_tan = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb040",
            setToolTip=self.sb.tooltip.fmt(
                title="Tangent",
                body="Which side of the key is held flat.",
                bullets=[
                    "<b>Out</b> (default) — the key holds its value forward "
                    "until the next key, the usual blocking hold.",
                    "<b>In</b> — the key snaps to its value at the last moment "
                    "(<code>stepnext</code>).",
                    "<b>Both</b> — stepped on either side.",
                ],
            ),
        )
        for text, data in [
            ("Tangent: Out", "out"),
            ("Tangent: In", "in"),
            ("Tangent: Both", "both"),
        ]:
            cmb_tan.addItem(text, data)

    def tb017(self, widget):
        """Step Tangents — set stepped tangents on keys."""
        mode = widget.option_box.menu.cmb037.currentData()

        if mode == "auto":
            keys = "auto"
        elif mode == "selected":
            keys = mtk.AnimUtils.get_anim_curves(selected_keys_only=True)
            if not keys:
                self.sb.message_box("No keys selected in the Graph Editor.")
                return
        elif mode == "current_time":
            keys = cmds.currentTime(query=True)
        else:  # "all"
            keys = None

        tangent = widget.option_box.menu.cmb040.currentData()

        result = mtk.AnimUtils.step_keys(keys=keys, tangent=tangent)
        if result["curves"]:
            self.sb.message_box(f"Stepped {result['curves']} curve(s).")
        else:
            self.sb.message_box("No keys found. Select objects with keyframes.")

    def tb012_init(self, widget):
        """Copy Keys Init"""
        widget.option_box.menu.setTitle("Copy Keys")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb038",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="What gets captured from the selection.",
                bullets=[
                    "<b>Auto</b> — the first of these that finds anything: "
                    "Graph Editor key selection, Channel Box attributes, then "
                    "keyed values at the current frame.",
                    "<b>Current Frame</b> — a value snapshot of every keyed "
                    "attribute at the playhead.",
                    "<b>Selected Keys</b> — the picked keys with their times "
                    "and tangent types, so a whole passage can be replayed.",
                    "<b>Channel Box</b> — the values of the highlighted attributes.",
                    "<b>Copy + Paste</b> — capture in Auto mode and immediately "
                    "paste onto the same selection, in one click.",
                ],
                notes=[
                    "Everything but Copy + Paste only stores; use <b>Paste "
                    "Keys</b> to apply it."
                ],
            ),
        )
        for text, data in [
            ("Mode: Auto", "auto"),
            ("Mode: Current Frame", "current_frame"),
            ("Mode: Selected Keys", "selected"),
            ("Mode: Channel Box", "channel_box"),
            ("Mode: Copy + Paste", "copy_paste"),
        ]:
            cmb.addItem(text, data)

    def tb012(self, widget):
        """Copy Keys: copy the selected objects' keys for later paste."""
        mode = widget.option_box.menu.cmb038.currentData()

        copy_mode = "auto" if mode == "copy_paste" else mode
        self._stored_attributes = mtk.AnimUtils.copy_keys(mode=copy_mode)
        self._stored_frame = cmds.currentTime(query=True)

        if not self._stored_attributes:
            labels = {
                "auto": "Nothing to copy (no selected keys, channel box attributes, or keyed attributes at current frame).",
                "current_frame": "No keyed attributes found at current frame.",
                "selected": "No keys selected in the Graph Editor.",
                "channel_box": "No channel box attributes selected.",
                "copy_paste": "Nothing to copy from selection.",
            }
            self.sb.message_box(labels.get(mode, "Nothing to copy."))
            return

        if mode == "copy_paste":
            objects = cmds.ls(sl=True) or []
            if not objects:
                self.sb.message_box("You must select at least one object.")
                return
            keys_set = mtk.AnimUtils.paste_keys(
                objects, copied_data=self._stored_attributes
            )
            if keys_set > 0:
                self.sb.message_box(
                    f"Copied and pasted values to {keys_set} object(s)."
                )
            else:
                self.sb.message_box("No matching objects found.")
            return

        # Count total items: for multi-key data (list), count keys;
        # for scalar data (float), count 1 per attribute.
        total_keys = 0
        for obj_data in self._stored_attributes.values():
            for data in obj_data.values():
                if isinstance(data, list):
                    total_keys += len(data)
                else:
                    total_keys += 1
        total_attrs = sum(len(v) for v in self._stored_attributes.values())
        self.sb.message_box(
            f"Copied {total_keys} key(s) across {total_attrs} attribute(s) from "
            f"{len(self._stored_attributes)} object(s)."
        )

    def tb018_init(self, widget):
        """Paste Keys Init"""
        widget.option_box.menu.setTitle("Paste Keys")
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb039",
            setToolTip=self.sb.tooltip.fmt(
                title="Paste At",
                bullets=[
                    "<b>At Playhead</b> — shifted so the earliest copied key "
                    "lands on the current frame; later keys keep their "
                    "spacing.",
                    "<b>At Copy Frame</b> — back at the frame the copy was "
                    "taken from, wherever the playhead is now.",
                ],
            ),
        )
        for text, data in [
            ("At Playhead", "playhead"),
            ("At Copy Frame", "source"),
        ]:
            cmb.addItem(text, data)

    def tb018(self, widget):
        """Paste Keys: paste previously copied keys onto the selection."""
        if not hasattr(self, "_stored_attributes") or not self._stored_attributes:
            self.sb.message_box("No values stored. Use 'Copy Keys' first.")
            return

        objects = cmds.ls(sl=True) or []
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        paste_mode = widget.option_box.menu.cmb039.currentData()
        target_time = (
            getattr(self, "_stored_frame", None) if paste_mode == "source" else None
        )

        keys_set = mtk.AnimUtils.paste_keys(
            objects, copied_data=self._stored_attributes, target_time=target_time
        )

        if keys_set > 0:
            msg = f"Pasted values to {keys_set} object(s)."
            if keys_set < len(objects):
                msg += (
                    f"\n{len(objects) - keys_set} object(s) not found in copied data."
                )
            self.sb.message_box(msg)
        else:
            self.sb.message_box(
                "No matching objects found. Select the same objects you copied from."
            )

    def tb019_init(self, widget):
        """Optimize Keys Init"""
        widget.option_box.menu.setTitle("Optimize Keys")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Static Curves",
            setObjectName="chk000",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Remove Static Curves",
                body="Delete whole curves that never leave the attribute's "
                "default value — animation that exists but does nothing.",
                notes=[
                    "A curve sitting at a constant value that is NOT the "
                    "default is kept: it is holding a pose."
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Flat Keys",
            setObjectName="chk030",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(**self.TIP_OPTIMIZE_REMOVE_FLAT_KEYS),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Simplify Curves",
            setObjectName="chk032",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Simplify Curves",
                body="Run Maya's <code>keyReducer</code> filter, which drops any "
                "key whose absence changes the curve's shape by less than "
                "<b>Tolerance</b>.",
                notes=[
                    "The one lossy phase — it reshapes moving curves, not just "
                    "redundant ones. Off by default; reach for it on baked or "
                    "mocap data, not on hand-animated curves.",
                    "Ignored while <b>Reduce To Extremes</b> is on, which runs its own reduction.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reduce To Extremes",
            setObjectName="chk040",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Reduce To Extremes",
                body="Reduce baked curves to their endpoints, peaks, valleys and "
                "hold boundaries, with tangents refit to trace the baked motion "
                "— a bake thinned to its shape, not reversed (that is Smart Bake's Unbake).",
                notes=[
                    "Stepped curves get the flat-key pass instead. "
                    "<b>Simplify Curves</b> and <b>Tolerance</b> are ignored.",
                    "Lossy by nature: one tangent pair per half-wave, so a "
                    "sine-like motion drifts by a few percent of its amplitude "
                    "between keys; the report shows the largest deviation.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="d017",
            set_limits=[0.0001, 1.0],
            setValue=0.001,
            setDecimals=4,
            setSingleStep=0.001,
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
                    "It is measured in scene units, so the same number is "
                    "stricter on a rotation curve than on a translation one.",
                    "Ignored while <b>Reduce To Extremes</b> is on.",
                ],
            ),
        )
        # Reduce To Extremes replaces the simplify/tolerance pass outright (tb019 sends a
        # negative tolerance as its sentinel, and mtk.optimize_keys drops
        # simplify_keys in that mode), so both controls grey out.
        self.sb.enable_when(
            widget.option_box.menu, "chk032,d017", "chk040", invert=True
        )

    @SlotsMaya.Cancelable(120)
    def tb019(self, widget):
        """Optimize Keys — remove redundant animation data."""
        remove_static = widget.option_box.menu.chk000.isChecked()
        remove_flat = widget.option_box.menu.chk030.isChecked()
        simplify = widget.option_box.menu.chk032.isChecked()
        # A negative tolerance is optimize_keys' extremes sentinel.
        tolerance = (
            -1
            if widget.option_box.menu.chk040.isChecked()
            else widget.option_box.menu.d017.value()
        )

        selected = cmds.ls(sl=True, flatten=True) or []
        objects = selected if selected else (cmds.ls(type="transform") or [])
        if not objects:
            self.sb.message_box("No objects found to optimize.")
            return

        stats = {}
        with self.sb.progress(text="Working: Optimize Keys") as update:
            mtk.AnimUtils.optimize_keys(
                objects,
                value_tolerance=tolerance,
                remove_static_curves=remove_static,
                remove_flat_keys=remove_flat,
                simplify_keys=simplify,
                recursive=True,
                quiet=True,
                stats=stats,
                progress_callback=self.sb.progress_adapter(update),
            )

        kb = stats.get("keys_before", 0)
        ka = stats.get("keys_after", 0)
        cb = stats.get("curves_before", 0)
        ca = stats.get("curves_after", 0)

        scope = "selected objects" if selected else "scene"
        msg = f"Optimized {scope}:\n"
        msg += f"  \u2022 Curves: {cb} \u2192 {ca} ({cb - ca} removed)\n"
        msg += f"  \u2022 Keys: {kb:,} \u2192 {ka:,} ({kb - ka:,} removed)"
        if kb > 0:
            pct = (1 - ka / kb) * 100
            msg += f" ({pct:.1f}% reduction)"
        if "reduced" in stats:
            msg += (
                f"\n  \u2022 Reduced to extremes: {stats['reduced']} curves, "
                f"max deviation {stats['reduce_max_error']:.4f}"
            )
        self.sb.message_box(msg)

    def tb020(self, widget):
        """Smart Bake"""
        self.sb.handlers.marking_menu.show("smart_bake")

    def b000(self):
        """Open Shot Sequencer"""
        self.sb.handlers.marking_menu.show("shot_sequencer")

    def b004(self):
        """Open Shot Manifest"""
        self.sb.handlers.marking_menu.show("shot_manifest")

    def b005(self):
        """Fit Playback Range"""
        mtk.AnimUtils.fit_playback_range()

    def b006(self):
        """Open Key Stash"""
        self.sb.handlers.marking_menu.show("key_stash")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
