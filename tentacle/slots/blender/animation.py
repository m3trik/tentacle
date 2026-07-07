# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Animation(SlotsBlender):
    """Blender port of the shared ``animation`` menu.

    Every key operation (invert/stagger/snap/scale/step/move/spacing/align/copy/paste/
    transfer/intermediate/select/visibility-keys) is plain math over
    ``fcurve.keyframe_points`` via ``blendertk.anim_utils`` — the §5 finding that animation
    is volume, not difficulty. Only the mayatk shot sequencer/manifest windows remain
    deferred. Option-box widget names reused from Maya carry the same option (cross-DCC
    QSettings rule).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.animation
        self._copied_action = None

    def header_init(self, widget):
        """Header menu — mirror of the Maya animation header (the portable subset). The
        Maya-only Sequencing (shot manifest/sequencer) and the Repair Visibility Tangents tool are
        omitted rather than shown as dead entries. Reused objectNames carry the Maya label verbatim
        (cross-DCC QSettings rule)."""
        Btn = self.sb.registered_widgets.PushButton
        widget.menu.add("Separator", setTitle="Repair")
        widget.menu.add(
            Btn, setText="Repair Corrupted Curves", setObjectName="tb015",
            setToolTip="Remove corrupted keyframes (NaN/infinite values, absurd key times) and "
            "delete curves left with no valid keys.\nUse the option box to choose which fixes apply.",
        )
        widget.menu.add("Separator", setTitle="Bake")
        widget.menu.add(
            Btn, setText="Smart Bake", setObjectName="tb020",
            setToolTip="Open the Smart Bake panel.\n"
            "Analyzes and bakes constraints, drivers/expressions, IK, and blend shapes\n"
            "— with a one-click Unbake to reverse the most recent bake, even after a "
            "scene reopen.",
        )
        widget.menu.add("Separator", setTitle="Playback")
        widget.menu.add(
            "QPushButton", setText="Fit Playback Range", setObjectName="b005",
            setToolTip="Set the playback range to the keyed extent of the selection (or scene).",
        )
        widget.menu.add("Separator", setTitle="Info")
        widget.menu.add(
            Btn, setText="Get Animation Info", setObjectName="tb016",
            setToolTip="Show a per-object keyframe summary (range / channels / keys) in a viewer.\n"
            "Use the option box to choose scope (Selected / All) and sort order.",
        )

    # ------------------------------------------------------------------ tb000  Go To Frame
    def tb000_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Go To Frame")
        m.add(
            "QSpinBox", setPrefix="Frame: ", setObjectName="s000",
            set_limits=[-999999, 999999], setValue=0,
            setToolTip="The frame to jump to (or the offset, in Relative mode).",
        )
        cmb = m.add(
            "QComboBox", setObjectName="cmb000",
            setToolTip="Absolute: jump to the frame.\nRelative: offset from the current frame.",
        )
        for text, data in [("Mode: Absolute", "Absolute"), ("Mode: Relative", "Relative")]:
            cmb.addItem(text, data)
        cmb001 = m.add(
            "QComboBox", setObjectName="cmb001",
            setToolTip="Snap the resulting frame to a clean number:\n"
            "• None: no snapping\n"
            "• Preferred: round to clean numbers when very close (24→25, 99→100)\n"
            "• Aggressive: round to clean numbers even when farther (48→50, 73→75)\n"
            "Snapping re-rounds the CURRENT frame; Frame/Mode are ignored.",
        )
        for text, data in [
            ("Snap: None", "none"),
            ("Snap: Preferred", "preferred"),
            ("Snap: Aggressive", "aggressive"),
        ]:
            cmb001.addItem(text, data)
        m.add(
            self.sb.registered_widgets.Label, setText="Set To Current Frame", setObjectName="lbl020",
            setToolTip="Write the current frame into Frame.",
        )
        m.lbl020.clicked.connect(lambda: m.s000.setValue(bpy.context.scene.frame_current))
        m.add(
            "QCheckBox", setText="Toggle Single frame", setObjectName="chk010", setChecked=False,
            setToolTip="Snap Frame to a single-frame nudge (+1/-1) and back.",
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
            setToolTip="Flip the sign of Frame; also feeds the Snap direction below.",
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

        self.sb.toggle_multi(
            m, trigger="cmb001", signal="currentIndexChanged",
            on_0={"setEnabled": "s000,cmb000,lbl020,chk010"},
            on_1={"setDisabled": "s000,cmb000,lbl020,chk010"},
            on_2={"setDisabled": "s000,cmb000,lbl020,chk010"},
        )

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
    _INVERT_MODES = {"Mode: X": "time", "Mode: Y": "value", "Mode: X & Y": "both"}

    def tb001_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Invert Keys")
        m.add(
            "QComboBox", addItems=list(self._INVERT_MODES), setObjectName="cmb035",
            setToolTip="Mode: X mirrors key times (reverse timing); Y mirrors values about the "
            "pivot (flip motion); X & Y does both.",
        )
        m.add(
            self.sb.registered_widgets.SpinBox, setPrefix="Time: ", setObjectName="s001",
            set_limits=[-100000, 100000], setValue=-1, setCustomDisplayValues={-1: "Auto"},
            setToolTip="Start time for the reversed copy.\nSet to -1 (Auto) to mirror the keys "
            "in place (reverses the animation within its own range; no copy).",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Pivot: ", setObjectName="d000",
            set_limits=[-100000, 100000], setValue=0.0,
            setToolTip="Value pivot for Y (value) inversion.",
        )
        m.add(
            "QCheckBox", setText="Relative", setObjectName="chk002", setChecked=True,
            setToolTip="Treat Time as an offset from the last key (checked) or an absolute "
            "frame (unchecked). Ignored when Time is Auto.",
        )
        m.add(
            "QCheckBox", setText="Delete Original", setObjectName="chk005", setChecked=False,
            setToolTip="Delete the original keyframes after inverting.\nImplied when Time is "
            "Auto (in-place mirror).",
        )

        self.sb.toggle_multi(
            m, trigger="cmb035", signal="currentIndexChanged",
            on_0={"setEnabled": "s001,chk002", "setDisabled": "d000"},
            on_1={"setDisabled": "s001,chk002", "setEnabled": "d000"},
            on_2={"setEnabled": "s001,chk002,d000"},
        )
        m.d000.setDisabled(True)

    @btk.undoable
    def tb001(self, widget):
        """Invert Keys (mirror key times and/or values — reverses timing / flips motion)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Invert Keys requires a selection.")
            return
        m = widget.option_box.menu
        mode = self._INVERT_MODES.get(m.cmb035.currentText(), "time")
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
            setToolTip="Where the first object's animation starts. -1 = leave it where it is.",
        )
        m.add(
            "QSpinBox", setPrefix="Spacing: ", setObjectName="s004",
            set_limits=[-100000, 100000], setValue=0,
            setToolTip="Frames between one block's end and the next block's start\n"
            "(or the fixed interval between block starts, with Use Intervals).",
        )
        m.add(
            "QCheckBox", setText="Use Intervals", setObjectName="chk025", setChecked=False,
            setToolTip="Place each block at a fixed frame interval (Spacing) instead of "
            "sequentially end-to-start.",
        )
        m.add(
            "QCheckBox", setText="Invert", setObjectName="chk008", setChecked=False,
            setToolTip="Reverse the order in which objects are staggered.",
        )
        m.add(
            "QCheckBox", setText="Group Overlapping", setObjectName="chk014", setChecked=False,
            setToolTip="Objects with overlapping key ranges re-time together as a single block "
            "(relative timing within the block is preserved).",
        )
        m.add(
            "QCheckBox", setText="Group Touching", setObjectName="chk029", setChecked=False,
            setToolTip="Also merge blocks whose ranges merely touch (end frame == start frame).\n"
            "Applies with Group Overlapping.",
        )
        m.add(
            "QCheckBox", setText="Smooth Tangents", setObjectName="chk009", setChecked=False,
            setToolTip="Set auto-clamped bezier handles on the re-timed keys for smooth "
            "transitions.",
        )

    @btk.undoable
    def tb003(self, widget):
        """Stagger Keys (re-time selected objects sequentially)."""
        objects = self.selected_objects()
        if len(objects) < 2:
            self.sb.message_box("Stagger Keys requires 2+ selected objects.")
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
            setToolTip="Rounding method:\n"
            "• Nearest: round to the nearest whole frame\n"
            "• Floor: always round down\n"
            "• Ceil: always round up\n"
            "• Half Up: standard rounding (.5 rounds up)\n"
            "• Preferred: round to clean numbers when very close (24→25, 99→100)\n"
            "• Aggressive Preferred: round to clean numbers even when farther (48→50, 73→75)",
        )
        for text, data in self._SNAP_METHODS.items():
            cmb.addItem(text, data)
        m.add(
            "QCheckBox", setText="Selected Keys Only", setObjectName="chk017", setChecked=False,
            setToolTip="Only snap keys selected in the Dope Sheet / Graph Editor.\n"
            "Else snap all keys on the selected objects.",
        )
        m.add(
            "QCheckBox", setText="Use Time Range", setObjectName="chk018", setChecked=False,
            setToolTip="Only snap keys within the scene's frame range.",
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
            setToolTip="Time range for keyframe deletion:\n"
            "• All Keyframes: delete all keyframes on the selection\n"
            "• Current Frame: delete keyframes at the current frame only\n"
            "• Before Current: delete all keyframes before the current frame (excluding it)\n"
            "• Before & Current: delete all keyframes before and including the current frame\n"
            "• After Current: delete all keyframes after the current frame (excluding it)\n"
            "• Current & After: delete all keyframes at and after the current frame (including it)",
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
            setToolTip="Starting frame for the shift. -1 = current frame.",
        )
        m.add(
            "QSpinBox", setPrefix="Amount: ", setObjectName="s003",
            set_limits=[-100000, 100000], setValue=1,
            setToolTip="Frames to add (+) or remove (−) between keys.",
        )
        m.add(
            "QCheckBox", setText="Relative", setObjectName="chk004", setChecked=True,
            setToolTip="Treat Frame as an offset from the current frame (checked) or an "
            "absolute frame number (unchecked).",
        )
        m.add(
            "QCheckBox", setText="Preserve Keys", setObjectName="chk003", setChecked=True,
            setToolTip="Preserve a keyframe at Frame if one exists there: it's re-anchored at "
            "the same value after the shift moves the rest of the keys away.",
        )
        cmb = m.add("QComboBox", setObjectName="cmb036", setToolTip="Which keys to shift.")
        for text, data in [
            ("Scope: Selected Objects", "objects"),
            ("Scope: Selected Keys", "keys"),
            ("Scope: Entire Scene", "scene"),
        ]:
            cmb.addItem(text, data)
        m.add(
            "QCheckBox", setText="Exact Gap", setObjectName="chk021", setChecked=False,
            setToolTip="Treat Amount as a target gap: shift so the first key at/after the frame "
            "lands exactly at (frame + amount).",
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
        widget.option_box.menu.setTitle("Transfer Keys")
        widget.option_box.menu.add(
            "QCheckBox", setText="Relative", setObjectName="chk006",
            setChecked=True,
            setToolTip="Values relative to the current position.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Optimize Before Transfer", setObjectName="chk035",
            setChecked=False,
            setToolTip="Run Optimize Keys on the source object before transferring, to remove "
            "redundant keys.",
        )

    @btk.undoable
    def tb004(self, widget):
        """Transfer Keys (active object → other selected, independent copies). Relative mode
        offsets the transferred values so each target keeps its own current pose as the base
        (mirrors Maya's chk006), instead of snapping every target to the source's literal
        values."""
        objects = self.selected_objects()
        active = bpy.context.view_layer.objects.active
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
            setToolTip="First frame of the window to add/remove keys in. -1 = each curve's first key.",
        )
        m.add(
            "QSpinBox", setPrefix="End Time: ", setObjectName="s006",
            set_limits=[-1, 100000], setValue=-1,
            setToolTip="Last frame of the window. -1 = each curve's last key.",
        )
        m.add(
            "QSpinBox", setPrefix="Percent: ", setObjectName="s007",
            set_limits=[0, 100], setValue=5,
            setToolTip="Percentage of each curve's OWN interior frames to key, evenly "
            "distributed (mirror of Maya's density control — density scales with the curve's "
            "own span, not a fixed frame count).",
        )
        m.add(
            "QCheckBox", setText="Ignore Visibility", setObjectName="chk028", setChecked=False,
            setToolTip="Leave visibility (hide_viewport/hide_render) keys untouched.",
        )
        m.add(
            "QCheckBox", setText="Remove Intermediate Keys", setObjectName="chk027",
            setChecked=False,
            setToolTip="If checked, removes intermediate keys (keeps the endpoints).\n"
            "If unchecked, adds sampled keys within the range (density set by Percent).",
        )
        self.sb.toggle_multi(
            m, trigger="chk027", signal="toggled",
            on_True={"setDisabled": "s007"},
            on_False={"setEnabled": "s007"},
        )

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
            setToolTip="Type of time selection to make.",
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
            setToolTip="Start frame for Range selection mode.",
        )
        m.add(
            "QSpinBox", setPrefix="End Frame: ", setObjectName="s013",
            set_limits=[-10000, 10000], setValue=100,
            setToolTip="End frame for Range selection mode.",
        )
        m.add(
            "QCheckBox", setText="Add to Selection", setObjectName="chk039", setChecked=False,
            setToolTip="Add to the existing keyframe selection instead of replacing it.",
        )
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
            setToolTip="Align to the earliest selected keyframe.\n"
            "Else align to the latest. Ignored when Frame is set.",
        )
        m.add(
            "QSpinBox", setPrefix="Frame: ", setObjectName="spn000",
            setMinimum=-10000, setMaximum=10000, setValue=-1,
            setToolTip="Specific frame to align the selected keys to.\n"
            "-1 = auto (the earliest / latest selected key).",
        )

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
        m.add(
            "QCheckBox", setText="Visible", setObjectName="chk015", setChecked=True,
            setToolTip="Set visibility to on (visible) or off (hidden).",
        )
        cmb = m.add(
            "QComboBox", setObjectName="cmb002",
            setToolTip="When to key visibility: at the current frame, or relative to each "
            "object's keyed range.",
        )
        for text, data in [
            ("When: Current Frame", "current"),
            ("When: Range Start", "start"),
            ("When: Range End", "end"),
            ("When: Both Ends", "both"),
            ("When: Before Start", "before_start"),
            ("When: After End", "after_end"),
        ]:
            cmb.addItem(text, data)
        m.add(
            "QSpinBox", setPrefix="Offset: ", setObjectName="s008",
            set_limits=[-10000, 10000], setValue=0,
            setToolTip="Frame offset applied to the chosen frame(s). + later, − earlier.",
        )
        m.add(
            "QCheckBox", setText="Group Overlapping", setObjectName="chk016", setChecked=False,
            setToolTip="Treat objects with overlapping keyframe ranges as a single group.\n"
            "Group visibility keys are set at the combined range.",
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
            visible=m.chk015.isChecked(),
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
            setToolTip="Move only the keys selected in the Dope Sheet / Graph Editor to the "
            "current frame.\nElse move all keys on the selected objects.",
        )
        m.add(
            "QCheckBox", setText="Maintain Spacing", setObjectName="chk012", setChecked=True,
            setToolTip="Maintain relative spacing between objects.\n"
            "Else move each object's own keys to the current frame.",
        )
        cmb = m.add(
            "QComboBox", setObjectName="cmb_align",
            setToolTip="Which end of the key range aligns to the current frame.",
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
            setToolTip="Which keys to copy from the active object:\n"
            "• Auto: the active object's whole action (Blender's native full-animation copy)\n"
            "• Current Frame: a snapshot of every animated property's value at the current frame\n"
            "• Selected Keys: only the keyframes selected in the Dope Sheet / Graph Editor\n"
            "• Copy + Paste: copy the active object's whole action and immediately paste it onto "
            "the rest of the selection, in one click",
        )
        for text, data in self._COPY_MODES.items():
            cmb.addItem(text, data)

    @btk.undoable
    def tb012(self, widget):
        """Copy Keys (from the active object; Copy + Paste mode also pastes onto the rest of
        the selection immediately)."""
        active = bpy.context.view_layer.objects.active
        if active is None:
            self.sb.message_box("Copy Keys requires an active object.")
            return
        mode = self._COPY_MODES.get(widget.option_box.menu.cmb038.currentText(), "action")

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
            setToolTip="Where to paste the copied keys:\n"
            "• At Copy Frame: at the frame(s) they were originally captured at (unshifted)\n"
            "• At Playhead: shifted so the earliest copied key lands on the current frame",
        )
        for text, data in [("At Copy Frame", "source"), ("At Playhead", "playhead")]:
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

    _SCALE_UNIFORM_TOOLTIP = (
        "Time scaling factor:\n\n"
        "UNIFORM MODE:\n"
        "• 1.0 = no change (100%)\n"
        "• 0.5 = compress to 50% (2x faster)\n"
        "• 2.0 = expand to 200% (2x slower)"
    )
    _SCALE_SPEED_TOOLTIP = (
        "Target speed in units per frame:\n\n"
        "SPEED MODE:\n"
        "• The block is retimed so its overall speed matches this value\n"
        "• Duration is derived from sampled world-space motion distance / speed"
    )

    def tb014_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Scale Keys")
        cmb_mode = m.add(
            "QComboBox", setObjectName="cmb014", block_signals_on_restore=False,
            setToolTip="Scaling mode:\n"
            "• Uniform: plain time scaling around a pivot\n"
            "• Speed: retime so the block's overall speed matches the target "
            "(Translation + Rotation)\n"
            "• Speed (Linear): translation only\n"
            "• Speed (Rotation): rotation only",
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
            setMinimum=0.01, setMaximum=100.0, setSingleStep=0.1, setValue=1.0, setDecimals=2,
            setToolTip=self._SCALE_UNIFORM_TOOLTIP,
        )
        cmb_group = m.add(
            "QComboBox", setObjectName="cmb033",
            setToolTip="Grouping strategy for pivots and time ranges:\n\n"
            "• Single Group: share one pivot/range across the whole selection.\n"
            "• Per Object Pivots: each object (or segment) uses its own pivot/range.\n"
            "• Group Overlaps: objects with overlapping key ranges share a group pivot.",
        )
        for text, data in [
            ("Single Group", "single_group"),
            ("Per Object Pivots", "per_object"),
            ("Group Overlaps", "overlap_groups"),
        ]:
            cmb_group.addItem(text, data)
        cmb_snap = m.add(
            "QComboBox", setObjectName="cmb034",
            setToolTip="Keyframe snapping after scaling:\n\n"
            "• Nearest: round to the nearest whole frame (default)\n"
            "• Preferred / Aggressive Preferred: round to clean numbers when close\n"
            "• None: keep precise decimal times",
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
            setToolTip="Motion sampling resolution for speed mode:\n\n"
            "• Higher values = more accurate motion detection but slower\n"
            "• Lower values = faster processing but less precise\n"
            "• Only applies in speed mode, ignored in uniform mode.",
        )
        m.add(
            "QCheckBox", setText="Absolute Mode", setObjectName="chk_absolute", setChecked=False,
            setToolTip="Toggle between Absolute and Relative scaling:\n\n"
            "Uniform Mode:\n"
            "• Unchecked (Relative): Factor is a multiplier (2.0 = 2x longer)\n"
            "• Checked (Absolute): Factor is target duration in frames\n\n"
            "Speed Mode:\n"
            "• Unchecked (Relative): Factor is a speed multiplier (2.0 = 2x faster)\n"
            "• Checked (Absolute): Factor is target speed (units/frame)",
        )
        m.add(
            "QCheckBox", setText="Split Static Segments", setObjectName="chk_split_static",
            setChecked=True,
            setToolTip="Split animation by static segments:\n\n"
            "• Checked (default): segments separated by static holds are treated as "
            "independent blocks and scaled separately.\n"
            "• Unchecked: the whole object is scaled as a single block.",
        )
        m.add(
            "QCheckBox", setText="Group Touching", setObjectName="chk_merge_touching",
            setChecked=False,
            setToolTip="Merge touching animation segments:\n\n"
            "• Checked: segments that touch (end frame == start frame) are merged into a "
            "single group when using Group Overlaps.\n"
            "• Unchecked (default): touching segments remain separate.",
        )
        # cmb_scale_pivot is Blender-specific (Maya's scale option box always auto-detects the
        # block's own start; it has no pivot picker).
        m.add(
            "QComboBox", addItems=["First Key", "Current Frame"], setObjectName="cmb_scale_pivot",
            setToolTip="Time the scaling pivots about (Single Group / Per Object Pivots only).",
        )

        def update_mode_ui(index):
            is_speed_mode = index > 0
            m.s014.setEnabled(is_speed_mode)
            if is_speed_mode:
                m.d001.setPrefix("Speed: ")
                m.d001.setRange(0.01, 1000.0)
                m.d001.setSingleStep(0.5)
                m.d001.setValue(5.0)
                m.d001.setToolTip(self._SCALE_SPEED_TOOLTIP)
                m.chk_absolute.setChecked(True)
            else:
                m.d001.setPrefix("Factor: ")
                m.d001.setRange(0.01, 100.0)
                m.d001.setSingleStep(0.1)
                m.d001.setValue(1.0)
                m.d001.setToolTip(self._SCALE_UNIFORM_TOOLTIP)
                m.chk_absolute.setChecked(False)

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
            absolute=m.chk_absolute.isChecked(),
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
        widget.option_box.menu.setTitle("Set Tangents")
        widget.option_box.menu.add(
            "QComboBox", addItems=list(self._INTERP_TYPES), setObjectName="cmb_interp",
            setToolTip="Interpolation/tangent type to apply to every key on the selection.",
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
        m.add(
            "QCheckBox", setText="Untie", setObjectName="chk_untie", setChecked=False,
            setToolTip="Remove the bookend keys at the range boundaries instead of adding them.",
        )
        m.add(
            "QCheckBox", setText="Use Absolute Range", setObjectName="chk023", setChecked=False,
            setToolTip="Bookend at the actual keyed extent across the objects instead of the "
            "scene's frame range.",
        )

    @btk.undoable
    def tb011(self, widget):
        """Tie/Untie Keyframes"""
        objects = self.selected_objects() or None
        m = widget.option_box.menu
        untie = m.chk_untie.isChecked()
        changed = btk.tie_keyframes(objects, untie=untie, absolute=m.chk023.isChecked())
        verb = "Untied" if untie else "Tied"
        self.sb.message_box(f"{verb} <hl>{changed}</hl> bookend key(s).")

    # ------------------------------------------------------------------ tb016  Get Animation Info
    def tb016_init(self, widget):
        widget.option_box.menu.setTitle("Get Animation Info")
        cmb = widget.option_box.menu.add(
            "QComboBox", setObjectName="cmb_scope",
            setToolTip="Selected: only the current selection.\nAll Scene Objects: every object.",
        )
        for label, data in [("Scope: Selected", "selected"), ("Scope: All Scene Objects", "all")]:
            cmb.addItem(label, data)
        widget.option_box.menu.add(
            "QCheckBox", setText="Sort by Time", setObjectName="chk_sort_time", setChecked=False,
            setToolTip="Sort output by start frame instead of object name.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="CSV Output", setObjectName="chk_csv_output", setChecked=False,
            setToolTip="Format the report as CSV (copy/paste into a spreadsheet).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Ignore Holds", setObjectName="chk_ignore_holds",
            setChecked=True,
            setToolTip="Exclude static hold keys from the reported ranges.\n"
            "Uncheck to include leading/trailing holds.",
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
            setToolTip="Drop curves that hold a constant value (the held value is written back "
            "to the property — lossless).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Remove Flat Keys", setObjectName="chk030", setChecked=True,
            setToolTip="Remove interior keys on constant-value segments (boundary keys kept).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Simplify Curves", setObjectName="chk032", setChecked=False,
            setToolTip="Additionally drop keys that lie on the line between their neighbours.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Tolerance: ", setObjectName="d017",
            set_limits=[0.0001, 1.0], setValue=0.001, setDecimals=4, setSingleStep=0.001,
            setToolTip="Maximum allowed value deviation when removing keys.",
        )

    @btk.undoable
    def tb019(self, widget):
        """Optimize Keys — remove redundant animation data."""
        m = widget.option_box.menu
        selected = self.selected_objects()
        stats = {}
        btk.optimize_keys(
            selected or None,
            value_tolerance=m.d017.value(),
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
        self.sb.message_box(msg)

    # ------------------------------------------------------------------ tb015  Repair Corrupted Curves
    def tb015_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Repair Corrupted Curves")
        m.add(
            "QCheckBox", setText="Delete Unfixable Curves", setObjectName="chk036", setChecked=True,
            setToolTip="Delete curves left with no valid keys after repair (else they're emptied).",
        )
        m.add(
            "QCheckBox", setText="Fix Infinite Values", setObjectName="chk037", setChecked=True,
            setToolTip="Remove keys with NaN/infinite (or beyond-threshold) values.",
        )
        m.add(
            "QCheckBox", setText="Fix Invalid Times", setObjectName="chk038", setChecked=True,
            setToolTip="Remove keys at NaN/infinite (or beyond-threshold) frame times.",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Time Threshold: ", setObjectName="d015",
            set_limits=[1000, 999999999], setValue=100000,
            setToolTip="Key frames beyond this magnitude are treated as corrupt.",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Value Threshold: ", setObjectName="d016",
            set_limits=[1000, 999999999], setValue=1000000,
            setToolTip="Key values beyond this magnitude are treated as corrupt.",
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

    # ------------------------------------------------------------------ divergent (Maya shot pipeline)
    def b000(self):
        """Shot Sequencer — Maya's shot-node / scene-per-shot ripple editor. Blender's sequencing
        model (the VSE, linked scenes, and timeline-marker cameras) is structurally different, so
        there is no faithful port; pointing the user at the native equivalent."""
        self.sb.message_box(
            "Shot Sequencer is Maya-shot-pipeline specific. In Blender, sequence shots via the "
            "<hl>Video Sequencer</hl> and bind cameras with timeline markers (Marker ▸ Bind Camera)."
        )

    def b004(self):
        """Shot Manifest — Maya's CSV-driven scene-assembly tool (built on Maya's shot nodes). No
        Blender analogue; Blender assembles shots via linked scenes / collections, a different model."""
        self.sb.message_box(
            "Shot Manifest is Maya-shot-pipeline specific (CSV-driven scene assembly). Blender "
            "assembles shots via linked <hl>Scenes</hl> / <hl>Collections</hl> instead."
        )


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
