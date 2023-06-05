# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Animation_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Frame: ",
            setObjectName="s000",
            set_limits="0-10000 step1",
            setValue=1,
            setToolTip="",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Update",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="",
        )

    def tb001_init(self, widget):
        """ """
        widget.option_menu.add(
            "QSpinBox",
            setPrefix="Time: ",
            setObjectName="s001",
            set_limits="0-10000 step1",
            setValue=1,
            setToolTip="The desired start time for the inverted keys.",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk002",
            setChecked=False,
            setToolTip="Start time position as relative or absolute.",
        )

    def tb000(self, *args, **kwargs):
        """Set Current Frame"""
        tb = kwargs.get("widget")

        frame = self.sb.invert_on_modifier(tb.option_menu.s000.value())
        relative = tb.option_menu.chk000.isChecked()
        update = tb.option_menu.chk001.isChecked()

        self.setCurrentFrame(frame, relative=relative, update=update)

    def tb001(self, *args, **kwargs):
        """Invert Selected Keyframes"""
        tb = kwargs.get("widget")

        time = tb.option_menu.s001.value()
        relative = tb.option_menu.chk002.isChecked()

        self.invertSelectedKeyframes(time=time, relative=relative)

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = kwargs.get("widget")
        index = kwargs.get("index")

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass

            cmb.setCurrentIndex(0)

    def b000(self, *args, **kwargs):
        """Delete Keys on Selected"""
        selected_objects = pm.selected()
        for obj in selected_objects:
            pm.cutKey(obj, clear=True)

    def setCurrentFrame(self, frame=1, relative=False, update=True):
        """Set the current frame on the timeslider.

        Parameters:
        frame (int): Desired from number.
        relative (bool): If True; the frame will be moved relative to
                it's current position using the frame value as a move amount.
        update (bool): Change the current time, but do not update the world. (default=True)

        Example:
                setCurrentFrame(24, relative=True, update=1)
        """
        currentTime = 0
        if relative:
            currentTime = pm.currentTime(query=True)

        pm.currentTime(currentTime + frame, edit=True, update=update)

    @mtk.undo
    def invertSelectedKeyframes(self, time=1, relative=True):
        """Duplicate any selected keyframes and paste them inverted at the given time.

        Parameters:
                time (int): The desired start time for the inverted keys.
                relative (bool): Start time position as relative or absolute.

        Example: invertSelectedKeyframes(time=48, relative=0)
        """
        # pm.undoInfo(openChunk=1)
        allActiveKeyTimes = pm.keyframe(
            query=True, sl=True, tc=True
        )  # get times from all selected keys.
        if not allActiveKeyTimes:
            error = "# Error: No keys selected. #"
            print(error)
            return error

        range_ = max(allActiveKeyTimes) - min(allActiveKeyTimes)
        time = time - max(allActiveKeyTimes) if not relative else time

        selection = pm.ls(sl=1, transforms=1)
        for obj in selection:
            keys = pm.keyframe(obj, query=True, name=True, sl=True)
            for node in keys:
                activeKeyTimes = pm.keyframe(node, query=True, sl=True, tc=True)
                for t, rt in zip(activeKeyTimes, reversed(activeKeyTimes)):
                    pm.copyKey(node, time=t)
                    pm.pasteKey(node, time=rt + range_ + time)

                    inAngle = pm.keyTangent(node, query=True, time=t, inAngle=True)
                    pm.keyTangent(
                        node, edit=True, time=rt + range_ + time, inAngle=-inAngle[0]
                    )
        # pm.undoInfo(closeChunk=1)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
