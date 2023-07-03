# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Pivot_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Reset Pivot Position",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Reset Pivot Orientation",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="",
        )

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Component",
            setObjectName="chk002",
            setToolTip="Center the pivot on the center of the selected component's bounding box",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Object",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Center the pivot on the center of the object's bounding box",
        )
        widget.menu.add(
            "QRadioButton",
            setText="World",
            setObjectName="chk004",
            setToolTip="Center the pivot on world origin.",
        )

    def tb000(self, widget):
        """Reset Pivot"""
        resetPivotPosition = (
            widget.menu.chk000.isChecked()
        )  # Reset Pivot Position
        resetPivotOrientation = (
            widget.menu.chk001.isChecked()
        )  # Reset Pivot Orientation

        pm.mel.manipPivotReset(int(resetPivotPosition), int(resetPivotOrientation))
        pm.inViewMessage(
            status_message="Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.".format(
                resetPivotPosition, resetPivotOrientation
            ),
            pos="topCenter",
            fade=True,
        )
        # self.sb.message_box('Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.'.format(resetPivotPosition, resetPivotOrientation))

    def tb001(self, widget):
        """Center Pivot"""
        component = widget.menu.chk002.isChecked()
        object_ = widget.menu.chk003.isChecked()
        world = widget.menu.chk004.isChecked()

        pm.mel.manipPivotReset(1, 1)  # reset Pivot Position and Orientation.

        if component:  # Set pivot points to the center of the component's bounding box.
            pm.xform(centerPivotsOnComponents=1)
        elif object_:  # Set pivot points to the center of the object's bounding box
            pm.xform(centerPivots=1)
        elif world:
            pm.xform(worldSpace=1, pivots=[0, 0, 0])

    def b000(self):
        """Center Pivot: Object"""
        self.sb.pivot.tb001.menu.chk003.setChecked(True)
        self.sb.pivot.tb001.call_slot()

    def b001(self):
        """Center Pivot: Component"""
        self.sb.pivot.tb001.menu.chk002.setChecked(True)
        self.sb.pivot.tb001.call_slot()

    def b002(self, widget):
        """Center Pivot: World"""
        self.sb.pivot.tb001.menu.chk004.setChecked(True)
        self.sb.pivot.tb001.call_slot()

    def b004(self):
        """Bake Pivot"""
        sel = pm.ls(sl=1)
        mtk.bake_custom_pivot(sel, position=1, orientation=1)


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
