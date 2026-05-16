# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class Crease(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.crease
        self.submenu = self.sb.loaded_ui.crease_submenu

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[0, 10],
            setValue=10,
            setToolTip="Sets the amount of creasing to apply to the selected edges. Range from 0 (no crease) to 10 (maximum crease).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Set Smoothing Angle",
            setObjectName="chk000",
            setToolTip="Enable this to set a custom smoothing angle for the edges. When checked, you can specify the angle in the adjacent spin box.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s004",
            set_limits=[0, 180],
            setValue=30,
            setDisabled=True,
            setToolTip="Sets the smoothing angle for the edges. Range from 0 degrees (hard edge) to 180 degrees (soft edge). Only active if 'Set Smoothing Angle' is checked.",
        )

        widget.option_box.menu.chk000.toggled.connect(
            widget.option_box.menu.s004.setEnabled
        )
        widget.setText(f"Crease {widget.option_box.menu.s003.value()}")
        widget.option_box.menu.s003.valueChanged.connect(
            lambda value: widget.setText(f"Crease {value}")
        )

    @mtk.undoable
    def tb000(self, widget):
        """Crease"""
        crease_amount = widget.option_box.menu.s003.value()
        smoothing_angle = widget.option_box.menu.s004.value()

        mtk.Components.crease_edges(amount=crease_amount, angle=smoothing_angle)

    @mtk.undoable
    def b002(self, widget):
        """Transfer Crease Edges"""
        try:
            source, *targets = cmds.ls(orderedSelection=True, objectsOnly=True) or []
            mtk.Components.transfer_creased_edges(source, targets)
        except ValueError:
            self.sb.message_box(
                "<hl>Incorrect object selection.</hl><br>Please select at least one source and one target object."
            )


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
