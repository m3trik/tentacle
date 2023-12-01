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

        self.setCurrentFrame(time=time, update=update, relative=relative)

    def tb001_init(self, widget):
        """ """
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

    def tb001(self, widget):
        """Invert Selected Keyframes"""
        time = widget.menu.s001.value()
        relative = widget.menu.chk002.isChecked()

        self.invertSelectedKeyframes(time=time, relative=relative)

    def tb002_init(self, widget):
        """ """
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
            set_limits=[0, 10000],
            setValue=1,
            setToolTip="The amount of spacing to add.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Relative",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Move relative to the current position.",
        )

    def tb002(self, widget):
        """Add Keyframe spacing"""
        amount = widget.menu.s003.value()
        time = widget.menu.s002.value()
        relative = widget.menu.chk004.isChecked()

        self.add_key_spacing(spacing_amount=amount, time=time, relative=relative)

    def b000(self):
        """Delete Keys on Selected"""
        selected_objects = pm.selected()
        for obj in selected_objects:
            pm.cutKey(obj, clear=True)

    def setCurrentFrame(self, time=1, update=True, relative=False):
        """Set the current frame on the timeslider.

        Parameters:
        time (int): The desired frame number.
        update (bool): Change the current time, but do not update the world. (default=True)
        relative (bool): If True; the frame will be moved relative to
                    it's current position using the frame value as a move amount.
        Example:
            setCurrentFrame(24, relative=True, update=1)
        """
        currentTime = 0
        if relative:
            currentTime = pm.currentTime(query=True)

        pm.currentTime(currentTime + time, edit=True, update=update)

    @mtk.undo
    def add_key_spacing(self, spacing_amount=1, time=1, relative=True):
        """Adds spacing between all keys at a given time.

        Parameters:
            spacing_amount (int): The amount of spacing to add.
            time (int): The time at which to start adding spacing.
            relative (bool): If True, the time is relative to the current frame.
        """
        # Adjust time if relative to the current frame
        if relative:
            time += pm.currentTime(query=True)

        # Process each object with keyframes
        for obj in pm.ls(type="transform", long=True):
            # Iterate over animatable attributes
            for attr in pm.listAnimatable(obj):
                # Format the attribute name properly
                attr_name = "{}.{}".format(obj, attr.split(".")[-1])

                # Get keyframes for this attribute
                keyframes = pm.keyframe(attr_name, query=True)

                if keyframes:
                    # Shift keyframes occurring after specified time
                    for key in sorted(keyframes, reverse=True):
                        if key >= time:
                            new_time = key + spacing_amount
                            # Get the value of the current keyframe
                            value = pm.getAttr(attr_name, time=key)
                            # Set a new keyframe at the new time with the same value
                            pm.setKeyframe(attr_name, time=(new_time,), value=value)
                            # Remove the old keyframe
                            pm.cutKey(attr_name, time=(key, key))

    @mtk.undo
    def invertSelectedKeyframes(self, time=1, relative=True):
        """Duplicate any selected keyframes and paste them inverted at the given time.

        Parameters:
            time (int): The desired start time for the inverted keys.
            relative (bool): Start time position as relative or absolute.

        Example: invertSelectedKeyframes(time=48, relative=0)
        """
        # Get times from all selected keys.
        allActiveKeyTimes = pm.keyframe(query=True, sl=True, tc=True)
        if not allActiveKeyTimes:
            error = "# Error: No keys selected. #"
            print(error)
            return

        maxTime = max(allActiveKeyTimes)
        if relative:
            inversionPoint = maxTime + time
        else:
            inversionPoint = time

        selection = pm.ls(sl=1, transforms=1)
        for obj in selection:
            keys = pm.keyframe(obj, query=True, name=True, sl=True)
            for node in keys:
                activeKeyTimes = pm.keyframe(node, query=True, sl=True, tc=True)
                for t in activeKeyTimes:
                    # Calculate the inverted time
                    timeDiff = t - maxTime
                    invertedTime = inversionPoint - timeDiff

                    pm.copyKey(node, time=t)
                    pm.pasteKey(node, time=invertedTime)

                    # Invert tangent angles
                    inAngle, outAngle = pm.keyTangent(
                        node, query=True, time=t, inAngle=True, outAngle=True
                    )
                    inAngleVal = (
                        -outAngle[0] if isinstance(outAngle, list) else -outAngle
                    )
                    outAngleVal = -inAngle[0] if isinstance(inAngle, list) else -inAngle
                    pm.keyTangent(
                        node,
                        edit=True,
                        time=invertedTime,
                        inAngle=inAngleVal,
                        outAngle=outAngleVal,
                    )


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
