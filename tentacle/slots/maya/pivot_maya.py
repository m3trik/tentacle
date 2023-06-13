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
        widget.option_menu.add(
            "QCheckBox",
            setText="Reset Pivot Position",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="",
        )
        widget.option_menu.add(
            "QCheckBox",
            setText="Reset Pivot Orientation",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="",
        )

    def tb001_init(self, widget):
        """ """
        widget.option_menu.add(
            "QRadioButton",
            setText="Component",
            setObjectName="chk002",
            setToolTip="Center the pivot on the center of the selected component's bounding box",
        )
        widget.option_menu.add(
            "QRadioButton",
            setText="Object",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Center the pivot on the center of the object's bounding box",
        )
        widget.option_menu.add(
            "QRadioButton",
            setText="World",
            setObjectName="chk004",
            setToolTip="Center the pivot on world origin.",
        )

    @SlotsMaya.hideMain
    def tb000(self, widget):
        """Reset Pivot"""
        resetPivotPosition = (
            widget.option_menu.chk000.isChecked()
        )  # Reset Pivot Position
        resetPivotOrientation = (
            widget.option_menu.chk001.isChecked()
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
        component = widget.option_menu.chk002.isChecked()
        object_ = widget.option_menu.chk003.isChecked()
        world = widget.option_menu.chk004.isChecked()

        pm.mel.manipPivotReset(1, 1)  # reset Pivot Position and Orientation.

        if component:  # Set pivot points to the center of the component's bounding box.
            pm.xform(centerPivotsOnComponents=1)
        elif object_:  # Set pivot points to the center of the object's bounding box
            pm.xform(centerPivots=1)
        elif world:
            pm.xform(worldSpace=1, pivots=[0, 0, 0])

    def b000(self):
        """Center Pivot: Object"""
        tb = self.sb.pivot.tb001
        tb.option_menu.chk003.setChecked(True)
        self.tb001()

    def b001(self):
        """Center Pivot: Component"""
        tb = self.sb.pivot.tb001
        tb.option_menu.chk002.setChecked(True)
        self.tb001()

    def b002(self):
        """Center Pivot: World"""
        tb = self.sb.pivot.tb001
        tb.option_menu.chk004.setChecked(True)
        self.tb001()

    def b004(self):
        """Bake Pivot"""
        sel = pm.ls(sl=1)
        mtk.bake_custom_pivot(
            sel, position=1, orientation=1
        )  # pm.mel.BakeCustomPivot()


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
