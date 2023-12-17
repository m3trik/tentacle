# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Crease(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.crease
        self.submenu = self.sb.crease_submenu

    def tb000_init(self, widget):
        """ """
        widget.menu.setTitle("Crease")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[0, 10],
            setValue=10,
            setToolTip="Sets the amount of creasing to apply to the selected edges. Range from 0 (no crease) to 10 (maximum crease).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Set Smoothing Angle",
            setObjectName="chk000",
            setToolTip="Enable this to set a custom smoothing angle for the edges. When checked, you can specify the angle in the adjacent spin box.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s004",
            set_limits=[0, 180],
            setValue=30,
            setDisabled=True,
            setToolTip="Sets the smoothing angle for the edges. Range from 0 degrees (hard edge) to 180 degrees (soft edge). Only active if 'Set Smoothing Angle' is checked.",
        )

        widget.menu.chk000.toggled.connect(widget.menu.s004.setEnabled)
        #  Suffix the widget text with the current crease value.
        widget.setText(f"Crease {widget.menu.s003.value()}")
        # Update the widget text when the spinbox value changes.
        widget.menu.s003.valueChanged.connect(
            lambda value: widget.setText(f"Crease {value}")
        )

    @mtk.undo
    def tb000(self, widget):
        """Crease"""
        crease_amount = widget.menu.s003.value()
        smoothing_angle = widget.menu.s004.value()

        mtk.crease_edges(amount=crease_amount, angle=smoothing_angle)

    @mtk.undo
    def b002(self, widget):
        """Transfer Crease Edges"""
        try:
            source, *targets = pm.ls(orderedSelection=True, objectsOnly=True)
            mtk.transfer_creased_edges(source, targets)
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
