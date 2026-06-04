# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya._slots_maya import SlotsMaya


class DeformationSlots(SlotsMaya):
    """Slots for the Deformation panel (``deformation.ui``).

    Distinct from :class:`~tentacle.slots.maya.deform.DeformSlots`, which wraps
    Maya's native *Deform* menu; this backs the tentacle Deformation panel.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb001_init(self, widget):
        """Init Curtain Generator launcher."""
        widget.setText("Curtain Generator")
        widget.setToolTip(
            "Drape a procedural pleated, gravity-draped (catenary) curtain from "
            "a selected rail curve / edges / locators — or a generated arc."
        )

    def tb001(self, widget):
        """Curtain Generator — open the mayatk Curtain tool."""
        self.sb.handlers.marking_menu.show("curtain")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
