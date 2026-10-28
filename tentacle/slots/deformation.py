# !/usr/bin/python
# coding=utf-8
"""Deformation: one Slots class for both hosts.

The category's one control opens the shared Curtain tool
(``slots/tools/curtain.py``), which reaches its host through ``self.tk``
itself. Distinct from Maya's native *Deform* menu
(``slots/maya/deform.py``).
"""

from tentacle import Slots


class DeformationSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)

    def tb001_init(self, widget):
        """Initialize the Curtain Generator launcher."""
        widget.setText("Curtain Generator")
        widget.setToolTip(
            "Drape a procedural pleated, gravity-draped (catenary) curtain from "
            "a selected rail curve, edges or a row of objects, or a generated arc."
        )

    def tb001(self, widget):
        """Curtain Generator: open the shared Curtain tool."""
        self.sb.handlers.marking_menu.show("curtain")
