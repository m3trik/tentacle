# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.pivot import Pivot


class Pivot_blender(Pivot, SlotsBlender):
    def __init__(self, *args, **kwargs):
        SlotsBlender.__init__(self, *args, **kwargs)
        Pivot.__init__(self, *args, **kwargs)

        cmb = self.sb.pivot.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

        ctx = self.sb.pivot.tb000.option_menu
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

        ctx = self.sb.pivot.tb001.option_menu
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
        cmb = self.sb.pivot.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def tb000(self, state=None):
        """Reset Pivot"""
        tb = self.sb.pivot.tb000

        resetPivotPosition = tb.option_menu.chk000.isChecked()  # Reset Pivot Position
        resetPivotOrientation = tb.option_menu.chk001.isChecked()  # Reset Pivot Orientation

        mel.eval(
            "manipPivotReset({0},{1})".format(
                int(resetPivotPosition), int(resetPivotOrientation)
            )
        )
        return "Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.".format(
            resetPivotPosition, resetPivotOrientation
        )

    def tb001(self, state=None):
        """Center Pivot"""
        tb = self.sb.pivot.tb001

        component = tb.option_menu.chk002.isChecked()
        object_ = tb.option_menu.chk003.isChecked()
        world = tb.option_menu.chk004.isChecked()

        if component:  # Set pivot points to the center of the component's bounding box.
            pm.xform(centerPivotsOnComponents=1)
        elif object_:  ##Set pivot points to the center of the object's bounding box
            pm.xform(centerPivots=1)
        elif world:
            pm.xform(worldSpace=1, pivots=[0, 0, 0])

    def b004(self):
        """Bake Pivot"""
        pm.mel.BakeCustomPivot()

    @staticmethod
    def reset_pivot_transforms(objects):
        """Reset Pivot Transforms"""
        objs = pm.ls(type=["transform", "geometryShape"], sl=1)

        if len(objs) > 0:
            pm.xform(cp=1)

        pm.manipPivot(ro=1, rp=1)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
