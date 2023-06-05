# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.animation import Animation


class Animation_blender(Animation, SlotsBlender):
    def __init__(self, *args, **kwargs):
        SlotsBlender.__init__(self, *args, **kwargs)
        Animation.__init__(self, *args, **kwargs)

        cmb = self.sb.animation.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.animation.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass

            cmb.setCurrentIndex(0)

    def b000(self, *args, **kwargs):
        """Delete Keys on Selected"""
        rt.deleteKeys(rt.selection)

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

    @SlotsBlender.undoChunk
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
