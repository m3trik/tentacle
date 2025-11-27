# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Pivot(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.pivot
        self.submenu = self.sb.loaded_ui.pivot_submenu

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reset Pivot Position",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reset Pivot Orientation",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="",
        )

    def tb000(self, widget):
        """Reset Pivot"""
        resetPivotPosition = (
            widget.option_box.menu.chk000.isChecked()
        )  # Reset Pivot Position
        resetPivotOrientation = (
            widget.option_box.menu.chk001.isChecked()
        )  # Reset Pivot Orientation

        pm.mel.manipPivotReset(int(resetPivotPosition), int(resetPivotOrientation))
        pm.inViewMessage(
            status_message="Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.".format(
                resetPivotPosition, resetPivotOrientation
            ),
            pos="topCenter",
            fade=True,
        )

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Component",
            setObjectName="chk002",
            setToolTip="Center the pivot on the center of the selected component's bounding box",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Object",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Center the pivot on the center of the object's bounding box",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="World",
            setObjectName="chk004",
            setToolTip="Center the pivot on world origin.",
        )

    def tb001(self, widget):
        """Center Pivot"""
        component = widget.option_box.menu.chk002.isChecked()
        object_ = widget.option_box.menu.chk003.isChecked()
        world = widget.option_box.menu.chk004.isChecked()

        pm.mel.manipPivotReset(1, 1)  # reset Pivot Position and Orientation.

        if component:  # Set pivot points to the center of the component's bounding box.
            pm.xform(centerPivotsOnComponents=1)
        elif object_:  # Set pivot points to the center of the object's bounding box
            pm.xform(centerPivots=1)
        elif world:
            pm.xform(worldSpace=1, pivots=[0, 0, 0])

    def tb002_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Transfer Pivot")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Transfer the translation pivot.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Transfer the pivot orientation.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Transfer the scale pivot.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Bake",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Bake the pivot values into the transform node.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="World Space",
            setObjectName="chk009",
            setChecked=True,
            setToolTip="Whether to use world space for transformations.",
        )

    def tb002(self, widget):
        """Transfer Pivot"""
        translate = widget.option_box.menu.chk005.isChecked()
        rotate = widget.option_box.menu.chk006.isChecked()
        scale = widget.option_box.menu.chk007.isChecked()
        bake = widget.option_box.menu.chk008.isChecked()
        world_space = widget.option_box.menu.chk009.isChecked()

        mtk.transfer_pivot(
            pm.selected(),
            translate=translate,
            rotate=rotate,
            scale=scale,
            bake=bake,
            world_space=world_space,
            select_targets_after_transfer=True,
        )

    def tb003_init(self, widget):
        """Initialize World-Aligned Pivot options"""
        widget.option_box.menu.setTitle("World-Aligned Pivot")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Manip Pivot",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Set temporary manipulator pivot. If unchecked, sets permanent object pivot.",
        )

    def tb003(self, widget):
        """World-Aligned Pivot"""
        manip_pivot = widget.option_box.menu.chk010.isChecked()

        # Set pivot
        pivot_type = "manip" if manip_pivot else "object"
        result = mtk.world_align_pivot(mode="set", pivot_type=pivot_type)

        if result:
            if pivot_type == "manip":
                pm.inViewMessage(
                    status_message="World-aligned <hl>manipulator</hl> pivot set (temporary).",
                    pos="topCenter",
                    fade=True,
                )
            else:
                pm.inViewMessage(
                    status_message="World-aligned <hl>object</hl> pivot set (permanent).",
                    pos="topCenter",
                    fade=True,
                )

    def b000(self):
        """Center Pivot: Object"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk003.setChecked(True)
        self.ui.tb001.call_slot()

    def b001(self):
        """Center Pivot: Component"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk002.setChecked(True)
        self.ui.tb001.call_slot()

    def b002(self, widget):
        """Center Pivot: World"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk004.setChecked(True)
        self.ui.tb001.call_slot()

    def b004(self):
        """Bake Pivot"""
        mtk.bake_pivot(pm.selected(), position=True, orientation=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
