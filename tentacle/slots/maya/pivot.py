# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


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
            setToolTip=self.sb.tooltip.fmt(
                title="Reset Pivot Position",
                body="Move the manipulator pivot back to the object's own pivot "
                "point, discarding any temporary offset "
                "(<code>manipPivotReset</code>).",
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reset Pivot Orientation",
            setObjectName="chk001",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Reset Pivot Orientation",
                body="Return the manipulator to the object's own orientation, "
                "discarding any temporary re-orientation "
                "(<code>manipPivotReset</code>).",
            ),
        )

    def tb000(self, widget):
        """Reset Pivot: reset the selected objects' pivot position and/or orientation."""
        resetPivotPosition = (
            widget.option_box.menu.chk000.isChecked()
        )  # Reset Pivot Position
        resetPivotOrientation = (
            widget.option_box.menu.chk001.isChecked()
        )  # Reset Pivot Orientation

        mel.eval(
            f"manipPivotReset {int(resetPivotPosition)} {int(resetPivotOrientation)}"
        )
        self.sb.message_box(
            "Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.".format(
                resetPivotPosition, resetPivotOrientation
            )
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

        mel.eval("manipPivotReset 1 1")  # reset Pivot Position and Orientation.

        selection = cmds.ls(sl=True) or []
        if not selection:
            return

        if component:  # Set pivot points to the center of the component's bounding box.
            cmds.xform(selection, centerPivotsOnComponents=1)
        elif object_:  # Set pivot points to the center of the object's bounding box
            cmds.xform(selection, centerPivots=1)
        elif world:
            cmds.xform(selection, worldSpace=1, pivots=[0, 0, 0])

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
        cmb000 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=self.sb.tooltip.fmt(
                title="Mirror",
                body="Reflect the transferred pivot across the chosen world "
                "axis-plane through the origin.",
                notes=[
                    "Use it when the target is a mirrored copy of the source.",
                    "<b>None</b> transfers the pivot unreflected.",
                ],
            ),
        )
        for text, data in [
            ("Mirror: None", ""),
            ("Mirror: X", "x"),
            ("Mirror: Y", "y"),
            ("Mirror: Z", "z"),
        ]:
            cmb000.addItem(text, data)

    def tb002(self, widget):
        """Transfer Pivot"""
        translate = widget.option_box.menu.chk005.isChecked()
        rotate = widget.option_box.menu.chk006.isChecked()
        scale = widget.option_box.menu.chk007.isChecked()
        bake = widget.option_box.menu.chk008.isChecked()
        world_space = widget.option_box.menu.chk009.isChecked()
        mirror = widget.option_box.menu.cmb000.currentData()

        mtk.transfer_pivot(
            cmds.ls(sl=True) or [],
            translate=translate,
            rotate=rotate,
            scale=scale,
            bake=bake,
            world_space=world_space,
            mirror=mirror,
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
            setToolTip=self.sb.tooltip.fmt(
                title="Manip Pivot",
                body="Set a temporary manipulator pivot.",
                notes=[
                    "Off: the permanent object pivot is set instead.",
                    "Works on a component selection too — the pivot lands on the "
                    "selected components' bounding-box center, and the selection "
                    "is left in component mode.",
                ],
            ),
        )

    def tb003(self, widget):
        """World-Aligned Pivot: world-align the pivot of the selected objects or components."""
        manip_pivot = widget.option_box.menu.chk010.isChecked()

        # Set pivot
        pivot_type = "manip" if manip_pivot else "object"
        result = mtk.world_align_pivot(mode="set", pivot_type=pivot_type)

        if result:
            if pivot_type == "manip":
                self.sb.message_box(
                    "World-aligned <hl>manipulator</hl> pivot set (temporary)."
                )
            else:
                self.sb.message_box(
                    "World-aligned <hl>object</hl> pivot set (permanent)."
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
        """Bake Pivot: bake the manipulator pivot's position and orientation into the transform."""
        mtk.bake_pivot(cmds.ls(sl=True) or [], position=True, orientation=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
