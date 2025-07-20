# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Animation(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb000_init(self, widget):
        """ """
        widget.menu.setTitle("Move To Frame")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits=[-999999, 999999],
            setValue=0,
            setToolTip="The desired frame number.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Update",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Change the current time, but do not update the world.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Move relative to the current position.",
        )
        widget.menu.add(
            self.sb.registered_widgets.Label,
            setText="Set To Current Frame",
            setObjectName="lbl020",
            setToolTip="Set frame to the current time.",
        )
        widget.menu.lbl020.clicked.connect(
            lambda: widget.menu.s000.setValue(pm.currentTime(q=True))
        )
        widget.menu.add(
            "QCheckBox",
            setText="Toggle Single frame",
            setObjectName="chk010",
            setChecked=False,
            setToolTip="Toggle single frame mode.",
        )
        widget._previous_frame_value = 1

        def toggle_single_frame(state):
            spinbox = widget.menu.s000
            if state:
                widget._previous_frame_value = spinbox.value() or 1
                spinbox.setValue(-1 if widget._previous_frame_value > 0 else 1)
            else:
                spinbox.setValue(widget._previous_frame_value)

        widget.menu.chk010.toggled.connect(toggle_single_frame)
        widget.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk011",
            setChecked=False,
            setToolTip="Toggle inverted mode.",
        )

        def toggle_inverted(state):
            spinbox = widget.menu.s000
            spinbox.setValue(-spinbox.value())

        widget.menu.chk011.toggled.connect(toggle_inverted)

        def update_invert_checkbox(value):
            block = widget.menu.chk011.blockSignals(True)
            widget.menu.chk011.setChecked(value < 0)
            widget.menu.chk011.blockSignals(block)

        widget.menu.s000.valueChanged.connect(update_invert_checkbox)

    def tb000(self, widget):
        """Move To Frame"""
        time = widget.menu.s000.value()
        update = widget.menu.chk001.isChecked()
        relative = widget.menu.chk000.isChecked()

        mtk.set_current_frame(time=time, update=update, relative=relative)

    def tb001_init(self, widget):
        """ """
        widget.menu.setTitle("Invert Selected Keys")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits=[-100000, 100000],
            setValue=0,
            setToolTip="The desired start time for the inverted keys.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Start time position as relative or absolute.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Delete Original",
            setObjectName="chk005",
            setChecked=False,
            setToolTip="Delete the original keyframes after inverting.",
        )

    def tb001(self, widget):
        """Invert Selected Keyframes"""
        time = widget.menu.s001.value()
        relative = widget.menu.chk002.isChecked()
        delete_original = widget.menu.chk005.isChecked()

        mtk.invert_selected_keys(
            time=time, relative=relative, delete_original=delete_original
        )

    def tb002_init(self, widget):
        """ """
        widget.menu.setTitle("Adjust Spacing")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s002",
            set_limits=[0, 100000],
            setValue=0,
            setToolTip="The time at which to start adding spacing.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[-100000, 100000],
            setValue=1,
            setToolTip="The amount of spacing to add or subtract.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Move relative to the current position.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Preserve Keys",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Preserves and adjusts a keyframe at the specified time if it exists.",
        )

    def tb002(self, widget):
        """Adjust spacing"""
        amount = widget.menu.s003.value()
        time = widget.menu.s002.value()
        relative = widget.menu.chk004.isChecked()
        preserve_keys = widget.menu.chk003.isChecked()

        objects = pm.ls(sl=True, type="transform", long=True)
        mtk.adjust_key_spacing(
            objects,
            spacing=amount,
            time=time,
            relative=relative,
            preserve_keys=preserve_keys,
        )

    def tb003_init(self, widget):
        """ """
        widget.menu.setTitle("Stagger Keys")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Offset: ",
            setObjectName="s004",
            set_limits=[-100000, 100000],
            setValue=1,
            setToolTip="The amount of spacing to add or subtract.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Invert the staggered keyframe order.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Smooth Tangents",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Adjust tangents for smooth transitions.",
        )

    def tb003(self, widget):
        """Stagger Keys"""
        offset = widget.menu.s004.value()
        invert = widget.menu.chk008.isChecked()
        smooth_tangents = widget.menu.chk009.isChecked()
        selected_objects = pm.selected()
        mtk.stagger_keyframes(
            selected_objects,
            offset=offset,
            invert=invert,
            smooth_tangents=smooth_tangents,
        )

    def tb004_init(self, widget):
        """ """
        widget.menu.setTitle("Transfer Keys")
        widget.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Values relative to the current position.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Tangents",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Transfer tangent values.",
        )

    def tb004(self, widget):
        """Tansfer Keys"""
        relative = widget.menu.chk006.isChecked()
        tangents = widget.menu.chk007.isChecked()

        selected_objects = pm.selected()
        mtk.transfer_keyframes(
            selected_objects, relative=relative, transfer_tangents=tangents
        )

    def tb005_init(self, widget):
        """ """
        widget.menu.setTitle("Set Key")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Start Time: ",
            setObjectName="s005",
            set_limits=[0, 100000],
            setValue=0,
            setToolTip="The time at which to start adding keys.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="End Time: ",
            setObjectName="s006",
            set_limits=[0, 100000],
            setValue=100,
            setToolTip="The time at which to end adding keys.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Percent: ",
            setObjectName="s007",
            set_limits=[0, 100],
            setValue=5,
            setToolTip="The percentage of the key to add.",
        )

    def tb005(self, widget):
        """Add Intermediate Keys"""
        start_time = widget.menu.s005.value()
        end_time = widget.menu.s006.value()
        percent = widget.menu.s007.value()

        objects = pm.selected(flatten=True)
        if not objects:
            self.sb.message_box("You must select at least one object.")
            return
        mtk.add_intermediate_keys(objects, start_time, end_time, percent)

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
