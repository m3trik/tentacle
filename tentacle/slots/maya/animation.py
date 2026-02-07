# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
import pythontk as ptk
from tentacle.slots.maya import SlotsMaya


class Animation(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.animation
        self.ui_submenu = self.sb.loaded_ui.animation_submenu

    def header_init(self, widget):
        """Header Init"""
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Smart Bake",
            setObjectName="tb017",
            setToolTip="Intelligently bake constraints, driven keys, expressions, IK, motion paths, and blend shapes.",
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Print Animation Info",
            setObjectName="tb016",
            setToolTip="Print segmented keyframe info for selected objects (or all if none selected).",
        )
        widget.menu.add(
            "QPushButton",
            setText="Repair Visibility Tangents",
            setToolTip="Force 'step' tangents on visibility curves for selected objects (or all if none selected).",
            clicked=lambda: mtk.Diagnostics.repair_visibility_tangents(
                objects=pm.selected() or None
            ),
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Repair Corrupted Curves",
            setObjectName="tb015",
            setToolTip="Repair corrupted animation curves.",
        )

    def tb000_init(self, widget):
        """Go To Frame Init"""
        widget.option_box.menu.setTitle("Go To Frame")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits=[-999999, 999999],
            setValue=0,
            setToolTip="The desired frame number.",
        )
        # Mode ComboBox
        cmb000 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip="Set the mode to Absolute or Relative.",
        )
        for text, data in [
            ("Mode: Absolute", "Absolute"),
            ("Mode: Relative", "Relative"),
        ]:
            cmb000.addItem(text, data)
        cmb000.setCurrentIndex(1)

        # Snap ComboBox
        cmb001 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb001",
            setToolTip="Snap the resulting frame number.",
        )
        snap_items = [
            ("Snap: None", "none"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive"),
        ]
        for text, data in snap_items:
            cmb001.addItem(text, data)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Update",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Change the current time, but do not update the world.",
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.Label,
            setText="Set To Current Frame",
            setObjectName="lbl020",
            setToolTip="Set frame to the current time.",
        )
        widget.option_box.menu.lbl020.clicked.connect(
            lambda: widget.option_box.menu.s000.setValue(pm.currentTime(q=True))
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Toggle Single frame",
            setObjectName="chk010",
            setChecked=False,
            setToolTip="Toggle single frame mode.",
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
            setToolTip="Toggle inverted mode.",
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

        self.sb.toggle_multi(
            widget.option_box.menu,
            trigger="cmb001",
            signal="currentIndexChanged",
            on_0={"setEnabled": "s000,cmb000,lbl020,chk010"},
            on_1={"setDisabled": "s000,cmb000,lbl020,chk010"},
            on_2={"setDisabled": "s000,cmb000,lbl020,chk010"},
        )

    def tb000(self, widget):
        """Go To Frame"""
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
            setObjectName="cmb000",
            setToolTip="Inversion mode.",
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
            setCustomDisplayValues={-1: "Time: Auto"},
            setToolTip="Start time for inverted keys.\nSet to -1 to auto-detect from keys (selected or all).",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Pivot: ",
            setObjectName="d000",
            set_limits=[-100000, 100000],
            setValue=0.0,
            setToolTip="Value pivot for vertical inversion.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Treat time as relative offset (checked) or absolute frame (unchecked).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Original",
            setObjectName="chk005",
            setChecked=False,
            setToolTip="Delete the original keyframes after inverting.",
        )

        self.sb.toggle_multi(
            widget.option_box.menu,
            trigger="cmb000",
            signal="currentIndexChanged",
            on_0={"setEnabled": "s001,chk002", "setDisabled": "d000"},
            on_1={"setDisabled": "s001,chk002", "setEnabled": "d000"},
            on_2={"setEnabled": "s001,chk002,d000"},
        )
        widget.option_box.menu.d000.setDisabled(True)

    def tb001(self, widget):
        """Invert keyframes (selected keys preferred, fallback to all keys)."""
        cmb = widget.option_box.menu.cmb000
        mode = cmb.itemData(cmb.currentIndex())
        time_value = widget.option_box.menu.s001.value()
        value_pivot = widget.option_box.menu.d000.value()
        relative = widget.option_box.menu.chk002.isChecked()
        delete_original = widget.option_box.menu.chk005.isChecked()

        # Use current time when time is -1
        time = pm.currentTime(q=True) if time_value == -1 else time_value

        mtk.invert_keys(
            time=time,
            relative=relative,
            delete_original=delete_original,
            mode=mode,
            value_pivot=value_pivot,
        )

    def tb002_init(self, widget):
        """Adjust Spacing Init"""
        widget.option_box.menu.setTitle("Adjust Spacing")
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Frame: ",
            setObjectName="s002",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Frame: Auto"},
            setToolTip="The time at which to start adding spacing.\nSet to -1 to use earliest keyframe on selected objects.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[-100000, 100000],
            setValue=1,
            setToolTip="The amount of spacing to add or subtract.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Move relative to the current position.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Preserve Keys",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Preserves and adjusts a keyframe at the specified time if it exists.",
        )

    def tb002(self, widget):
        """Adjust spacing"""
        amount = widget.option_box.menu.s003.value()
        time_value = widget.option_box.menu.s002.value()
        relative = widget.option_box.menu.chk004.isChecked()
        preserve_keys = widget.option_box.menu.chk003.isChecked()

        objects = pm.ls(sl=True, type="transform", long=True)

        # Use None when -1 to auto-detect earliest keyframe
        time = None if time_value == -1 else time_value

        mtk.adjust_key_spacing(
            objects,
            spacing=amount,
            time=time,
            relative=relative,
            preserve_keys=preserve_keys,
        )

    def tb003_init(self, widget):
        """Stagger Keys Init"""
        widget.option_box.menu.setTitle("Stagger Keys")
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Start Frame: ",
            setObjectName="s005",
            set_limits=[-100000, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Start Frame: Auto"},
            setToolTip="Override starting frame. -1 = use earliest keyframe.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Spacing: ",
            setObjectName="s004",
            set_limits=[-100000, 100000],
            setValue=0,
            setToolTip="Sequential mode: Offset/spacing between animations.\n"
            "  • Positive = gap in frames\n"
            "  • Zero = end-to-start (default)\n"
            "  • Negative = overlap in frames\n"
            "  • Float -1.0 to 1.0 = % of duration\n\n"
            "Interval mode: Fixed frame interval for placement\n"
            "  • e.g., 100 = animations at frames 0, 100, 200...",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Intervals",
            setObjectName="chk025",
            setChecked=False,
            setToolTip="Place animations at fixed frame intervals instead of sequential spacing.\n"
            "When enabled, Spacing defines the interval (e.g., 100 = frames 0, 100, 200...).",
        )
        # widget.option_box.menu.add(
        #     "QCheckBox",
        #     setText="Avoid Overlap",
        #     setObjectName="chk026",
        #     setChecked=False,
        #     setToolTip="Skip to next interval if animation would overlap with previous one.\n"
        #     "Only applies when 'Use Intervals' is enabled.",
        # )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Overlapping",
            setObjectName="chk014",
            setChecked=False,
            setToolTip="Treat objects with overlapping keyframes as a single block.\nObjects in the same time range will move together.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Touching",
            setObjectName="chk029",
            setChecked=False,
            setToolTip="Merge touching animation segments:\n\n"
            "• Checked: Segments that touch (end frame == start frame)\n"
            "  are merged into a single group when using 'Group Overlapping'.\n"
            "• Unchecked (default): Touching segments remain separate,\n"
            "  preserving the gap between them.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Attrs Only",
            setObjectName="chk024",
            setChecked=False,
            setToolTip="Only affect attributes currently selected in the Channel Box.\n\n"
            "• Unchecked (default): All animated attributes are staggered.\n"
            "• Checked: Only attributes selected in Channel Box are staggered.\n\n"
            "This allows precise control over which channels are affected.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Smooth Tangents",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Adjust tangents for smooth transitions.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Invert the staggered keyframe order.",
        )

    def tb003(self, widget):
        """Stagger Keys"""
        spacing = widget.option_box.menu.s004.value()
        start_frame_value = widget.option_box.menu.s005.value()
        use_intervals = widget.option_box.menu.chk025.isChecked()
        # avoid_overlap = widget.option_box.menu.chk026.isChecked()
        invert = widget.option_box.menu.chk008.isChecked()
        smooth_tangents = widget.option_box.menu.chk009.isChecked()
        group_overlapping = widget.option_box.menu.chk014.isChecked()
        merge_touching = widget.option_box.menu.chk029.isChecked()
        channel_box_only = widget.option_box.menu.chk024.isChecked()

        # Only use start_frame if not -1
        start_frame = start_frame_value if start_frame_value != -1 else None

        selected_objects = pm.selected()
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
        widget.option_box.menu.setTitle("Transfer Keys")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Values relative to the current position.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Tangents",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Transfer tangent values.",
        )

    def tb004(self, widget):
        """Tansfer Keys"""
        relative = widget.option_box.menu.chk006.isChecked()
        tangents = widget.option_box.menu.chk007.isChecked()

        selected_objects = pm.selected()
        mtk.transfer_keyframes(
            selected_objects, relative=relative, transfer_tangents=tangents
        )

    def tb005_init(self, widget):
        """Add/Remove Intermediate Keys Init"""
        widget.option_box.menu.setTitle("Intermediate Keys")
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Start Time: ",
            setObjectName="s005",
            set_limits=[-1, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "Start Time: Auto"},
            setToolTip="The time at which to start adding keys. Set to -1 to auto-detect from first keyframe.",
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="End Time: ",
            setObjectName="s006",
            set_limits=[-1, 100000],
            setValue=-1,
            setCustomDisplayValues={-1: "End Time: Auto"},
            setToolTip="The time at which to end adding keys. Set to -1 to auto-detect from last keyframe.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Percent: ",
            setObjectName="s007",
            set_limits=[0, 100],
            setValue=5,
            setToolTip="The percentage of the key to add.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Ignore Visibility",
            setObjectName="chk028",
            setChecked=False,
            setToolTip="Ignore visibility keyframes when adding/removing intermediate keys.\nVisibility keys will remain unchanged.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Intermediate Keys",
            setObjectName="chk027",
            setChecked=False,
            setToolTip="If checked, removes all intermediate keys (keeps only first and last).\nIf unchecked, adds intermediate keys within the range.",
        )
        # Auto-connect toggle behavior using state mapping
        self.sb.toggle_multi(
            widget.option_box.menu,
            trigger="chk027",
            signal="toggled",
            on_True={"setDisabled": "s007"},
            on_False={"setEnabled": "s007"},
        )

    def tb005(self, widget):
        """Add/Remove Intermediate Keys"""
        remove_mode = widget.option_box.menu.chk027.isChecked()
        ignore_visibility = widget.option_box.menu.chk028.isChecked()

        objects = pm.selected(flatten=True)
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        # Set ignore parameter based on checkbox
        ignore = "visibility" if ignore_visibility else None

        # Build time_range parameter based on UI values
        start_time_value = widget.option_box.menu.s005.value()
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
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Move selected keys from graph editor to current frame.\nElse move all keys on selected objects.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Maintain Spacing",
            setObjectName="chk012",
            setChecked=True,
            setToolTip="Maintain relative spacing between objects.\nElse move each object's first key to target frame.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Only",
            setObjectName="chk021",
            setChecked=False,
            setToolTip="Only move keys for attributes selected in the channel box.\nWorks with both 'Move Selected Keys' and all keys modes.",
        )

    def tb006(self, widget):
        """Move Keys"""
        selected_keys_only = widget.option_box.menu.chk010.isChecked()
        retain_spacing = widget.option_box.menu.chk012.isChecked()
        channel_box_attrs_only = widget.option_box.menu.chk021.isChecked()

        objects = pm.selected(flatten=True)
        if not objects:
            self.sb.message_box("You must select at least one object or set of keys.")
            return
        mtk.move_keys_to_frame(
            objects,
            selected_keys_only=selected_keys_only,
            retain_spacing=retain_spacing,
            channel_box_attrs_only=channel_box_attrs_only,
        )

    def tb007_init(self, widget):
        """Align Selected Keyframes Init"""
        widget.option_box.menu.setTitle("Align Selected Keyframes")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Earliest Frame",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Align to the earliest selected keyframe.\nElse align to the latest selected keyframe.",
        )
        widget.option_box.menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Frame: ",
            setObjectName="spn000",
            setMinimum=-10000,
            setMaximum=10000,
            setValue=-1,
            setCustomDisplayValues={-1: "Frame: Auto"},
            setToolTip="Specific frame to align to.\nSet to -1 to auto-detect from selected keyframes.",
        )

    def tb007(self, widget):
        """Align Selected Keyframes"""
        use_earliest = widget.option_box.menu.chk013.isChecked()
        target_frame_value = widget.option_box.menu.spn000.value()

        # Only use target_frame if not -1, otherwise use None to auto-detect
        target_frame = target_frame_value if target_frame_value != -1 else None

        objects = pm.selected(flatten=True)
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
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Visible",
            setObjectName="chk015",
            setChecked=True,
            setToolTip="Set visibility to on (visible) or off (hidden).",
        )
        widget.option_box.menu.add(
            "QComboBox",
            addItems=["Start", "End", "Both", "Before Start", "After End"],
            setObjectName="cmb002",
            setCurrentIndex=0,
            setToolTip="When to set the visibility keyframe:\n• Start: At animation start\n• End: At animation end\n• Both: At start and end\n• Before Start: One frame before start\n• After End: One frame after end",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Offset: ",
            setObjectName="s008",
            set_limits=[-10000, 10000],
            setValue=0,
            setToolTip="Frame offset to apply. Positive = later, Negative = earlier.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Overlapping",
            setObjectName="chk016",
            setChecked=False,
            setToolTip="Treat objects with overlapping keyframes as a single group.\nGroup visibility keys will be set at the combined range.",
        )

    def tb008(self, widget):
        """Set Visibility Keys"""
        visible = widget.option_box.menu.chk015.isChecked()
        when_index = widget.option_box.menu.cmb002.currentIndex()
        offset = widget.option_box.menu.s008.value()
        group_overlapping = widget.option_box.menu.chk016.isChecked()

        # Map combobox index to 'when' parameter
        when_options = ["start", "end", "both", "before_start", "after_end"]
        when = when_options[when_index]

        selected_objects = pm.selected()
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
        widget.option_box.menu.add(
            "QComboBox",
            addItems=[
                "Nearest",
                "Floor",
                "Ceil",
                "Half Up",
                "Preferred",
                "Aggressive Preferred",
            ],
            setObjectName="cmb003",
            setCurrentIndex=0,
            setToolTip="Rounding method:\n"
            "• Nearest: Round to nearest whole number\n"
            "• Floor: Always round down\n"
            "• Ceil: Always round up\n"
            "• Half Up: Standard rounding (.5 rounds up)\n"
            "• Preferred: Round to clean numbers when very close (24→25, 99→100)\n"
            "• Aggressive Preferred: Round to clean numbers even when farther (48→50, 73→75)",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Selected Keys Only",
            setObjectName="chk017",
            setChecked=False,
            setToolTip="If checked, only snap selected keyframes.\nIf unchecked, snap all keyframes on selected objects.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Time Range",
            setObjectName="chk018",
            setChecked=False,
            setToolTip="If checked, only snap keyframes within the current time range.",
        )

    def tb009(self, widget):
        """Snap Keys to Frames"""
        method_index = widget.option_box.menu.cmb003.currentIndex()
        selected_only = widget.option_box.menu.chk017.isChecked()
        use_time_range = widget.option_box.menu.chk018.isChecked()

        # Map combobox index to method parameter
        method_options = [
            "nearest",
            "floor",
            "ceil",
            "half_up",
            "preferred",
            "aggressive_preferred",
        ]
        method = method_options[method_index]

        # Get time range if requested
        time_range = None
        if use_time_range:
            anim_start_time = pm.playbackOptions(query=True, minTime=True)
            anim_end_time = pm.playbackOptions(query=True, maxTime=True)
            time_range = (anim_start_time, anim_end_time)

        selected_objects = pm.selected()
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
            setToolTip="Time range for keyframe deletion:\n"
            "• All Keyframes: Delete all keyframes on selected attributes\n"
            "• Current Frame: Delete keyframes at current frame only\n"
            "• Before Current: Delete all keyframes before current frame (excluding current)\n"
            "• Before & Current: Delete all keyframes before and including current frame\n"
            "• After Current: Delete all keyframes after current frame (excluding current)\n"
            "• Current & After: Delete all keyframes at and after current frame (including current)",
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
            setToolTip="If checked, only delete keys for attributes selected in the channel box.\nIf unchecked, delete keys for all keyable attributes.",
        )

    def tb010(self, widget):
        """Delete Keys"""
        cmb = widget.option_box.menu.cmb004
        time_param = cmb.itemData(cmb.currentIndex())
        channel_box_only = widget.option_box.menu.chk020.isChecked()

        objects = pm.selected()
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        if channel_box_only:
            # Use channel box filtering
            if time_param == "all":
                mtk.delete_keys(objects, channel_box_only=True)
            else:
                mtk.delete_keys(objects, time=time_param, channel_box_only=True)
        else:
            # Delete all keyable attributes (no filtering)
            if time_param == "all":
                mtk.delete_keys(objects)
            else:
                mtk.delete_keys(objects, time=time_param)

    def tb011_init(self, widget):
        """Tie/Untie Keyframes Init"""
        widget.option_box.menu.setTitle("Tie/Untie Keyframes")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Absolute Range",
            setObjectName="chk023",
            setChecked=False,
            setToolTip="If checked, uses the absolute start/end keyframes across all objects.\nIf unchecked, uses the scene's playback range.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Untie Keyframes",
            setObjectName="chk022",
            setChecked=False,
            setToolTip="If checked, removes bookend keyframes (preserves genuine animation).\nIf unchecked, adds keyframes at start/end of animation range.",
        )

    def tb011(self, widget):
        """Tie/Untie Keyframes"""
        untie_mode = widget.option_box.menu.chk022.isChecked()
        absolute = widget.option_box.menu.chk023.isChecked()

        objects = pm.selected()
        if not objects:
            # If no selection, operate on all keyed objects in scene
            objects = None

        if untie_mode:
            mtk.untie_keyframes(objects=objects, absolute=absolute)
        else:
            mtk.tie_keyframes(objects=objects, absolute=absolute)

    def tb012_init(self, widget):
        """Insert Keyframe Gap Init"""
        widget.option_box.menu.setTitle("Insert Keyframe Gap")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Start Frame: ",
            setObjectName="s009",
            set_limits=[-1000000, 1000000],
            setValue=0,
            setToolTip="Gap start frame. Set to 0 to use current time as start.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="End Frame: ",
            setObjectName="s010",
            set_limits=[-1000000, 1000000],
            setValue=10,
            setToolTip="When Start=0: Gap duration in frames.\nWhen Start≠0: Gap size in frames (gap ends at Start+End).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Selected Keys Only",
            setObjectName="chk020",
            setChecked=False,
            setToolTip="Only affect selected keyframes in graph editor.\nWhen unchecked, affects all keys on selected objects (or all scene objects if nothing selected).",
        )

    def tb012(self, widget):
        """Insert Keyframe Gap"""
        start_frame = widget.option_box.menu.s009.value()
        end_frame = widget.option_box.menu.s010.value()
        selected_keys_only = widget.option_box.menu.chk020.isChecked()

        # Determine duration parameter
        if start_frame == 0:
            # Use current time + duration (end_frame as duration)
            duration = end_frame
        else:
            # Use explicit start and end
            duration = (start_frame, start_frame + end_frame)

        # Get objects to affect
        selected_objects = pm.selected()
        objects = selected_objects if selected_objects else None

        result = mtk.insert_keyframe_gap(
            duration=duration,
            objects=objects,
            selected_keys_only=selected_keys_only,
        )

        if result["keys_moved"] == 0:
            self.sb.message_box("No keyframes found to move.")

    def tb013_init(self, widget):
        """Select Keys Init"""
        widget.option_box.menu.setTitle("Select Keys")
        widget.option_box.menu.add(
            "QComboBox",
            addItems=[
                "All",
                "Current",
                "Before",
                "After",
                "Before|Current",
                "After|Current",
                "Range",
            ],
            setObjectName="cmb003",
            setCurrentIndex=0,
            setToolTip="Type of time selection to make.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Start Frame: ",
            setObjectName="s012",
            set_limits=[-10000, 10000],
            setValue=1,
            setToolTip="Start frame for Range selection mode.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="End Frame: ",
            setObjectName="s013",
            set_limits=[-10000, 10000],
            setValue=100,
            setToolTip="End frame for Range selection mode.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Only",
            setObjectName="chk021",
            setChecked=False,
            setToolTip="Only select keys for attributes selected in the channel box.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Add to Selection",
            setObjectName="chk022",
            setChecked=False,
            setToolTip="Add to existing keyframe selection instead of replacing it.",
        )

    def tb013(self, widget):
        """Select Keys"""
        selection_type = widget.option_box.menu.cmb003.currentText()
        start_frame = widget.option_box.menu.s012.value()
        end_frame = widget.option_box.menu.s013.value()
        channel_box_only = widget.option_box.menu.chk021.isChecked()
        add_to_selection = widget.option_box.menu.chk022.isChecked()

        # Determine time parameter based on selection type
        if selection_type == "All":
            time = None
        elif selection_type == "Current":
            time = "current"
        elif selection_type == "Before":
            time = "before"
        elif selection_type == "After":
            time = "after"
        elif selection_type == "Before|Current":
            time = "before|current"
        elif selection_type == "After|Current":
            time = "after|current"
        elif selection_type == "Range":
            time = (start_frame, end_frame)
        else:
            time = None

        # Get objects to affect
        selected_objects = pm.selected()
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
            pm.displayInfo(f"Selected {keys_selected} keyframe(s)")

    def tb014_init(self, widget):
        """Scale Keys Init"""
        widget.option_box.menu.setTitle("Scale Keys")
        widget.option_box.menu.add(
            "QComboBox",
            addItems=[
                "Uniform Mode",
                "Speed Mode",
                "Speed Mode: Linear",
                "Speed Mode: Rotation",
            ],
            setObjectName="cmb014",
            setCurrentIndex=0,
            block_signals_on_restore=False,  # Allow signals during restore to trigger update_mode_ui
            setToolTip="Scaling mode:\n"
            "• Uniform: Traditional time scaling around pivot\n"
            "• Speed: Motion-based speed normalization (Translation + Rotation)\n"
            "• Speed (Linear): Translation only\n"
            "• Speed (Rotation): Rotation only",
        )
        uniform_tooltip = (
            "Time scaling factor:\n\n"
            "UNIFORM MODE:\n"
            "• 1.0 = no change (100%)\n"
            "• 0.5 = compress to 50% (2x faster)\n"
            "• 2.0 = expand to 200% (2x slower)\n"
        )

        speed_tooltip = (
            "Target speed in units per frame:\n\n"
            "SPEED MODE:\n"
            "• All objects retimed to this exact speed\n"
            "• Example: 5.0 = all objects move at 5 units/frame\n"
            "• Duration automatically calculated: distance / speed\n"
        )

        grouping_tooltip = (
            "Grouping strategy for pivots and time ranges:\n\n"
            "• Group All Objects: Share a single pivot/range across the selection.\n"
            "• Per Object Pivots: Each object uses its own pivot and auto-detected range.\n"
            "• Group Overlaps: Objects with overlapping key ranges share a group pivot."
        )

        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Factor: ",
            setObjectName="d001",
            setMinimum=0.01,
            setMaximum=100.0,
            setSingleStep=0.1,
            setValue=1.0,
            setDecimals=2,
            setToolTip=uniform_tooltip,
        )
        widget.option_box.menu.add(
            "QComboBox",
            addItems=[
                "Single Group",
                "Per Object Pivots",
                "Group Overlaps",
            ],
            setObjectName="cmb033",
            setCurrentIndex=0,
            setToolTip=grouping_tooltip,
        )

        widget.option_box.menu.add(
            "QComboBox",
            addItems=[
                "Snap: Nearest",
                "Snap: Preferred",
                "Snap: Aggressive",
                "Snap: None",
            ],
            setObjectName="cmb034",
            setCurrentIndex=0,
            setToolTip="Keyframe snapping after scaling (both modes):\n\n"
            "• Nearest: Round to nearest whole number (default)\n"
            "• Preferred: Round to clean numbers when close (24→25, 99→100)\n"
            "• Aggressive Preferred: Round to clean numbers aggressively (48→50, 73→75)\n"
            "• None: No snapping, preserve precise decimal times\n\n"
            "Applies after keyframe scaling to snap decimal frame times to whole frames.",
        )

        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Samples: ",
            setObjectName="s014",
            setMinimum=8,
            setMaximum=512,
            setSingleStep=8,
            setValue=64,
            setToolTip="Motion sampling resolution for speed mode:\n\n"
            "• Higher values = more accurate motion detection but slower\n"
            "• Lower values = faster processing but less precise\n"
            "• Default: 64 samples (good balance)\n"
            "• Recommended range: 32-128\n\n"
            "Note: Only applies in speed mode, ignored in uniform mode.",
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Channel Box Attrs Only",
            setObjectName="chk_channel_box",
            setChecked=False,
            setToolTip="Only affect attributes currently selected in the Channel Box.\n\n"
            "• Unchecked (default): All animated attributes are scaled.\n"
            "• Checked: Only attributes selected in Channel Box are scaled.\n\n"
            "This allows precise control over which channels are affected.",
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Absolute Mode",
            setObjectName="chk_absolute",
            setChecked=False,
            setToolTip="Toggle between Absolute and Relative scaling:\n\n"
            "Uniform Mode:\n"
            "• Unchecked (Relative): Factor is a multiplier (2.0 = 2x longer)\n"
            "• Checked (Absolute): Factor is target duration in frames\n\n"
            "Speed Mode:\n"
            "• Unchecked (Relative): Factor is speed multiplier (2.0 = 2x faster)\n"
            "• Checked (Absolute): Factor is target speed (units/frame)",
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Split Static Segments",
            setObjectName="chk_split_static",
            setChecked=True,
            setToolTip="Split animation by static segments:\n\n"
            "• Checked (default): Animation segments separated by flat keys\n"
            "  are treated as independent groups and scaled separately.\n"
            "• Unchecked: All keys on an object are scaled as a single block.\n\n"
            "Use this when objects have multiple animation 'clips' separated\n"
            "by static holds that should be scaled independently.",
        )

        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group Touching",
            setObjectName="chk_merge_touching",
            setChecked=False,
            setToolTip="Merge touching animation segments:\n\n"
            "• Checked: Segments that touch (end frame == start frame)\n"
            "  are merged into a single group when using 'Group Overlaps'.\n"
            "• Unchecked (default): Touching segments remain separate,\n"
            "  preserving the gap between them during scaling.",
        )

        # Auto-toggle UI elements based on mode
        def update_mode_ui(index):
            is_speed_mode = index > 0
            spinbox = widget.option_box.menu.d001
            samples_spinbox = widget.option_box.menu.s014
            absolute_chk = widget.option_box.menu.chk_absolute

            # Only samples spinbox is speed-mode specific
            # Snap mode now works for both uniform and speed modes
            samples_spinbox.setEnabled(is_speed_mode)

            # Update factor label and ranges/tooltips based on mode
            if is_speed_mode:
                spinbox.setPrefix("Speed: ")
                spinbox.setRange(0.01, 1000.0)
                spinbox.setSingleStep(0.5)
                spinbox.setValue(5.0)
                spinbox.setToolTip(speed_tooltip)
                # Default to Absolute (Target Speed) for Speed Mode
                absolute_chk.setChecked(True)
            else:
                spinbox.setPrefix("Factor: ")
                spinbox.setRange(0.01, 100.0)
                spinbox.setSingleStep(0.1)
                spinbox.setValue(1.0)
                spinbox.setToolTip(uniform_tooltip)
                # Default to Relative (Multiplier) for Uniform Mode
                absolute_chk.setChecked(False)

        widget.option_box.menu.cmb014.currentIndexChanged.connect(update_mode_ui)
        update_mode_ui(0)  # Initialize UI state

    def tb014(self, widget):
        """Scale Keys"""
        mode_index = widget.option_box.menu.cmb014.currentIndex()
        factor = widget.option_box.menu.d001.value()
        channel_box_only_checked = widget.option_box.menu.chk_channel_box.isChecked()
        absolute_mode = widget.option_box.menu.chk_absolute.isChecked()
        split_static = widget.option_box.menu.chk_split_static.isChecked()
        merge_touching = widget.option_box.menu.chk_merge_touching.isChecked()
        group_mode_index = widget.option_box.menu.cmb033.currentIndex()

        # Get objects to affect
        selected_objects = pm.selected()
        if not selected_objects:
            self.sb.message_box("You must select at least one object.")
            return

        # Determine mode and include_rotation
        mode = "uniform"
        include_rotation = False

        if mode_index == 1:  # Speed Mode (Combined)
            mode = "speed"
            include_rotation = True
        elif mode_index == 2:  # Speed Mode: Linear
            mode = "speed"
            include_rotation = False
        elif mode_index == 3:  # Speed Mode: Rotation
            mode = "speed"
            include_rotation = "only"

        # Determine keys parameter - check for selected keys in graph editor
        selected_keys_in_graph = pm.keyframe(query=True, sl=True, tc=True)
        keys = "selected" if selected_keys_in_graph and mode == "uniform" else None

        # Determine parameters - use explicit checkbox instead of auto-detection
        channel_box_only = channel_box_only_checked
        group_mode_values = ["single_group", "per_object", "overlap_groups"]
        group_mode = group_mode_values[group_mode_index]

        # Map snap mode combo index to parameter value
        snap_mode_values = [
            "nearest",  # 0: Nearest (default)
            "preferred",  # 1: Preferred
            "aggressive_preferred",  # 2: Aggressive Preferred
            "none",  # 3: None (Precise)
        ]
        # Get snap mode index safely
        try:
            snap_mode_index = widget.option_box.menu.cmb034.currentIndex()
            snap_mode = snap_mode_values[snap_mode_index]
        except (AttributeError, IndexError):
            # Fallback to default if combo doesn't exist or index is invalid
            snap_mode = "nearest"

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

            context = f" (channel box)" if channel_box_only else ""
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
            setObjectName="chk015",
            setChecked=True,
            setToolTip="Delete curves that cannot be repaired.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Fix Infinite Values",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Fix infinite and NaN keyframe values.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Fix Invalid Times",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Fix invalid time ranges (e.g., -165916080).",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Time Threshold: ",
            setObjectName="d015",
            set_limits=[1000, 999999999],
            setValue=100000,
            setToolTip="Maximum reasonable time value (frames). Keys beyond this are flagged as corrupted.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Value Threshold: ",
            setObjectName="d016",
            set_limits=[1000, 999999999],
            setValue=1000000,
            setToolTip="Maximum reasonable keyframe value. Values beyond this are flagged as corrupted.",
        )

    def tb015(self, widget):
        """Repair Corrupted Curves

        Automatically detects scope based on selection:
        - Selected keys in graph editor: checks only those curves
        - Selected objects: checks all keys on those objects
        - Nothing selected: checks all keys in the scene
        """
        delete_corrupted = widget.option_box.menu.chk015.isChecked()
        fix_infinite = widget.option_box.menu.chk016.isChecked()
        fix_invalid_times = widget.option_box.menu.chk017.isChecked()
        time_threshold = widget.option_box.menu.d015.value()
        value_threshold = widget.option_box.menu.d016.value()

        # Determine objects to process based on selection context
        selected_objects = pm.selected(flatten=True)
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
            message += f"\nFirst 3 issues:\n"
            for detail in result["details"][:3]:
                message += f"  • {detail}\n"
            if len(result["details"]) > 3:
                message += f"  ... and {len(result['details']) - 3} more"

        self.sb.message_box(message)

    def tb016_init(self, widget):
        """Print Animation Info - Initialize option box"""
        widget.option_box.menu.setTitle("Print Animation Info")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Sort by Time",
            setObjectName="chk_sort_time",
            setChecked=False,
            setToolTip="Sort output by start time instead of object name.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="CSV Output",
            setObjectName="chk_csv_output",
            setChecked=False,
            setToolTip="Print output in CSV format for easy spreadsheet import.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Ignore Holds",
            setObjectName="chk_ignore_holds",
            setChecked=True,
            setToolTip="Exclude static hold keys from the reported ranges.\nUncheck to include leading/trailing holds.",
        )

    def tb016(self, widget):
        """Print Animation Info"""
        by_time = widget.option_box.menu.chk_sort_time.isChecked()
        csv_output = widget.option_box.menu.chk_csv_output.isChecked()
        ignore_holds = widget.option_box.menu.chk_ignore_holds.isChecked()

        mtk.SegmentKeys.print_scene_info(
            detailed=True,
            by_time=by_time,
            csv_output=csv_output,
            ignore_holds=ignore_holds,
        )

    def b001(self, widget=None):
        """Copy Keys"""
        objects = pm.selected()
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        # Copy each object's unique values (default behavior)
        self._stored_attributes = mtk.get_channel_box_attributes(objects)

        if not self._stored_attributes:
            self.sb.message_box("No channel box attributes selected.")
        else:
            self.sb.message_box(
                f"Copied values from {len(self._stored_attributes)} object(s)."
            )

    def b002(self, widget=None):
        """Paste Keys"""
        if not hasattr(self, "_stored_attributes") or not self._stored_attributes:
            self.sb.message_box("No values stored. Use 'Copy Keys' first.")
            return

        objects = pm.selected()
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return

        # Paste - auto-detects per-object mode from dict structure
        mtk.set_keys_for_attributes(
            objects, refresh_channel_box=True, **self._stored_attributes
        )

        # Count how many objects were actually matched
        keys_set = 0
        for obj in objects:
            obj_name = str(obj)
            if obj_name in self._stored_attributes:
                keys_set += 1
            elif obj.nodeName() in self._stored_attributes:
                keys_set += 1
            else:
                # Check for short name matches
                for stored_name in self._stored_attributes.keys():
                    if stored_name.split("|")[-1] == obj.nodeName():
                        keys_set += 1
                        break

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


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
