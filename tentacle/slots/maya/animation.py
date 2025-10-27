# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Animation(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.animation
        self.ui_submenu = self.sb.loaded_ui.animation_submenu

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Move To Frame")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits=[-999999, 999999],
            setValue=0,
            setToolTip="The desired frame number.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Update",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Change the current time, but do not update the world.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Move relative to the current position.",
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

    def tb000(self, widget):
        """Move To Frame"""
        time = widget.option_box.menu.s000.value()
        update = widget.option_box.menu.chk001.isChecked()
        relative = widget.option_box.menu.chk000.isChecked()

        mtk.set_current_frame(time=time, update=update, relative=relative)

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Invert Selected Keys")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits=[-100000, 100000],
            setValue=0,
            setToolTip="The desired start time for the inverted keys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Start time position as relative or absolute.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Original",
            setObjectName="chk005",
            setChecked=False,
            setToolTip="Delete the original keyframes after inverting.",
        )

    def tb001(self, widget):
        """Invert Selected Keyframes"""
        time = widget.option_box.menu.s001.value()
        relative = widget.option_box.menu.chk002.isChecked()
        delete_original = widget.option_box.menu.chk005.isChecked()

        mtk.invert_selected_keys(
            time=time, relative=relative, delete_original=delete_original
        )

    def tb002_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Adjust Spacing")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s002",
            set_limits=[0, 100000],
            setValue=0,
            setToolTip="The time at which to start adding spacing.",
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
        time = widget.option_box.menu.s002.value()
        relative = widget.option_box.menu.chk004.isChecked()
        preserve_keys = widget.option_box.menu.chk003.isChecked()

        objects = pm.ls(sl=True, type="transform", long=True)
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
            "QSpinBox",
            setPrefix="Offset: ",
            setObjectName="s004",
            set_limits=[-100000, 100000],
            setValue=0,
            setToolTip="Offset/spacing between animations. Positive = gap, Negative = overlap, 0 = end-to-start.\nFloat between -1.0 and 1.0 = percentage of duration.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Start Frame: ",
            setObjectName="s005",
            set_limits=[-100000, 100000],
            setValue=0,
            setToolTip="Override starting frame. 0 = use earliest keyframe.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Interval: ",
            setObjectName="s006",
            set_limits=[0, 100000],
            setValue=0,
            setToolTip="Place animations at regular frame intervals (e.g., 100 = frames 0, 100, 200...).\n0 = disabled, uses offset instead.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Overlap Interval: ",
            setObjectName="s007",
            set_limits=[0, 100000],
            setValue=0,
            setToolTip="Additional interval to use when overlap detected.\nIf non-zero, animations skip to next interval position to avoid overlap.\n0 = disabled.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Invert the staggered keyframe order.",
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
            setText="Group Overlapping",
            setObjectName="chk014",
            setChecked=False,
            setToolTip="Treat objects with overlapping keyframes as a single block.\nObjects in the same time range will move together.",
        )

    def tb003(self, widget):
        """Stagger Keys"""
        offset = widget.option_box.menu.s004.value()
        start_frame_value = widget.option_box.menu.s005.value()
        interval_value = widget.option_box.menu.s006.value()
        overlap_interval_value = widget.option_box.menu.s007.value()
        invert = widget.option_box.menu.chk008.isChecked()
        smooth_tangents = widget.option_box.menu.chk009.isChecked()
        group_overlapping = widget.option_box.menu.chk014.isChecked()

        # Only use start_frame/interval if non-zero
        start_frame = start_frame_value if start_frame_value != 0 else None

        # Handle interval as tuple if overlap_interval is specified
        if interval_value != 0:
            if overlap_interval_value != 0:
                interval = (interval_value, overlap_interval_value)
            else:
                interval = interval_value
        else:
            interval = None

        selected_objects = pm.selected()
        mtk.stagger_keyframes(
            selected_objects,
            start_frame=start_frame,
            interval=interval,
            offset=offset,
            invert=invert,
            smooth_tangents=smooth_tangents,
            group_overlapping=group_overlapping,
        )

    def tb004_init(self, widget):
        """ """
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
        """ """
        widget.option_box.menu.setTitle("Set Key")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Start Time: ",
            setObjectName="s005",
            set_limits=[0, 100000],
            setValue=0,
            setToolTip="The time at which to start adding keys.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="End Time: ",
            setObjectName="s006",
            set_limits=[0, 100000],
            setValue=100,
            setToolTip="The time at which to end adding keys.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Percent: ",
            setObjectName="s007",
            set_limits=[0, 100],
            setValue=5,
            setToolTip="The percentage of the key to add.",
        )

    def tb005(self, widget):
        """Add Intermediate Keys"""
        start_time = widget.option_box.menu.s005.value()
        end_time = widget.option_box.menu.s006.value()
        percent = widget.option_box.menu.s007.value()

        objects = pm.selected(flatten=True)
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return
        mtk.add_intermediate_keys(objects, start_time, end_time, percent)

    def tb006_init(self, widget):
        """Move Keys Init"""
        widget.option_box.menu.setTitle("Move Keys")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Move Selected Keys",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Move selected keys to current frame.\nElse move all keys on selected objects.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Maintain Spacing",
            setObjectName="chk012",
            setChecked=True,
            setToolTip="Maintain relative spacing between objects.\nElse move each object's first key to target frame.",
        )

    def tb006(self, widget):
        """Move Keys"""
        only_move_selected = widget.option_box.menu.chk010.isChecked()
        retain_spacing = widget.option_box.menu.chk012.isChecked()

        objects = pm.selected(flatten=True)
        if not objects:
            self.sb.message_box("You must select at least one object or set of keys.")
            return
        mtk.move_keys_to_frame(
            objects,
            only_move_selected=only_move_selected,
            retain_spacing=retain_spacing,
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
            "QSpinBox",
            setText="Target Frame:",
            setPrefix="Frame: ",
            setObjectName="spn000",
            setMinimum=-10000,
            setMaximum=10000,
            setValue=0,
            setToolTip="Specific frame to align to. Leave at 0 to use earliest/latest from selection.",
        )

    def tb007(self, widget):
        """Align Selected Keyframes"""
        use_earliest = widget.option_box.menu.chk013.isChecked()
        target_frame_value = widget.option_box.menu.spn000.value()

        # Only use target_frame if it's non-zero, otherwise use None to auto-detect
        target_frame = target_frame_value if target_frame_value != 0 else None

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

    def b000(self):
        """Delete Keys"""
        try:
            objects = pm.selected()
            attributes = mtk.get_channel_box_attributes(objects)
            mtk.delete_keys(objects, *attributes.keys())
        except AttributeError:
            self.sb.message_box("No channel box values stored.")

    def b001(self):
        """Store Channel Box Attributes"""
        objects = pm.selected()
        if objects:
            self._stored_attributes = mtk.get_channel_box_attributes(objects)
        else:
            self.sb.message_box("You must select at least one channel box attribute.")

    def b002(self):
        """Key Stored Attributes"""
        try:
            objects = pm.selected()  # Get the currently selected objects
            mtk.set_keys_for_attributes(objects, **self._stored_attributes)
        except AttributeError:
            self.sb.message_box("No channel box values stored.")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
