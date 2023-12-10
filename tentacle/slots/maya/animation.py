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
        widget.menu.setTitle("Set Current Frame")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits=[0, 10000],
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

    def tb000(self, widget):
        """Set Current Frame"""
        time = widget.menu.s000.value()
        update = widget.menu.chk001.isChecked()
        relative = widget.menu.chk000.isChecked()

        mtk.setCurrentFrame(time=time, update=update, relative=relative)

    def tb001_init(self, widget):
        """ """
        widget.menu.setTitle("Invert Selected Keys")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits=[0, 10000],
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
            set_limits=[0, 10000],
            setValue=0,
            setToolTip="The time at which to start adding spacing.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[-10000, 10000],
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
        """Add Keyframe spacing"""
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
        widget.menu.add(
            "QSpinBox",
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits=[0, 10000],
            setValue=0,
            setToolTip="The desired start time for the inverted keys.",
        )

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
