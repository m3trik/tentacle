# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.pivot import Pivot


class Pivot_maya(Pivot, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.pivot.draggableHeader.ctxMenu.cmb000
        items = [""]
        cmb.addItems_(items, "")

        ctx = self.sb.pivot.tb000.ctxMenu
        if not ctx.containsMenuItems:
            ctx.add(
                "QCheckBox",
                setText="Reset Pivot Position",
                setObjectName="chk000",
                setChecked=True,
                setToolTip="",
            )
            ctx.add(
                "QCheckBox",
                setText="Reset Pivot Orientation",
                setObjectName="chk001",
                setChecked=True,
                setToolTip="",
            )

        ctx = self.sb.pivot.tb001.ctxMenu
        if not ctx.containsMenuItems:
            ctx.add(
                "QRadioButton",
                setText="Component",
                setObjectName="chk002",
                setToolTip="Center the pivot on the center of the selected component's bounding box",
            )
            ctx.add(
                "QRadioButton",
                setText="Object",
                setObjectName="chk003",
                setChecked=True,
                setToolTip="Center the pivot on the center of the object's bounding box",
            )
            ctx.add(
                "QRadioButton",
                setText="World",
                setObjectName="chk004",
                setToolTip="Center the pivot on world origin.",
            )

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.pivot.draggableHeader.ctxMenu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    @Slots.hideMain
    def tb000(self, state=None):
        """Reset Pivot"""
        tb = self.sb.pivot.tb000

        resetPivotPosition = tb.ctxMenu.chk000.isChecked()  # Reset Pivot Position
        resetPivotOrientation = tb.ctxMenu.chk001.isChecked()  # Reset Pivot Orientation

        pm.mel.manipPivotReset(int(resetPivotPosition), int(resetPivotOrientation))
        pm.inViewMessage(
            statusMessage="Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.".format(
                resetPivotPosition, resetPivotOrientation
            ),
            pos="topCenter",
            fade=True,
        )
        # self.sb.message_box('Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.'.format(resetPivotPosition, resetPivotOrientation))

    def tb001(self, state=None):
        """Center Pivot"""
        tb = self.sb.pivot.tb001

        component = tb.ctxMenu.chk002.isChecked()
        object_ = tb.ctxMenu.chk003.isChecked()
        world = tb.ctxMenu.chk004.isChecked()

        pm.mel.manipPivotReset(1, 1)  # reset Pivot Position and Orientation.

        if component:  # Set pivot points to the center of the component's bounding box.
            pm.xform(centerPivotsOnComponents=1)
        elif object_:  ##Set pivot points to the center of the object's bounding box
            pm.xform(centerPivots=1)
        elif world:
            pm.xform(worldSpace=1, pivots=[0, 0, 0])

    def b004(self):
        """Bake Pivot"""
        sel = pm.ls(sl=1)
        Rig.bakeCustomPivot(sel, position=1, orientation=1)  # pm.mel.BakeCustomPivot()


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
