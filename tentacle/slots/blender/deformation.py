# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender._slots_blender import SlotsBlender


class Deformation(SlotsBlender):
    """Blender port of the shared ``deformation`` menu.

    The single shared widget launches mayatk's Curtain Generator tool — no blendertk
    counterpart yet; deferred with a message.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tb001(self, widget):
        """Curtain Generator — mayatk tool; not yet ported (use cloth sim + a plane)."""
        self.sb.message_box("Curtain Generator is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
