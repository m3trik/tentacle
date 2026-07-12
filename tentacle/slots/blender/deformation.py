# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender._slots_blender import SlotsBlender


class Deformation(SlotsBlender):
    """Blender port of the shared ``deformation`` menu.

    The single shared widget launches the Curtain Generator panel
    (``blender_menus/curtain`` — the ``CurtainDrape`` engine vendored in
    blendertk over a bmesh build, same parameters as the Maya tool).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb001_init(self, widget):
        """Init Curtain Generator launcher."""
        widget.setText("Curtain Generator")
        widget.setToolTip(
            "Drape a procedural pleated, gravity-draped (catenary) curtain from "
            "a selected rail curve / edges / objects — or a generated arc."
        )

    def tb001(self, widget):
        """Curtain Generator — open the curtain panel."""
        self.sb.handlers.marking_menu.show("curtain")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
