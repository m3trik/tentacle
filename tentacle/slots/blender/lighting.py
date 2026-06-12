# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender._slots_blender import SlotsBlender


class Lighting(SlotsBlender):
    """Blender port of the shared ``lighting`` menu.

    Both buttons launch mayatk tool panels (HDR Manager / Lightmap Baker) that have no
    blendertk counterparts yet — deferred with messages until those tools are ported.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def b000(self):
        """HDR Manager — mayatk panel; not yet ported (use World shader nodes for HDRIs)."""
        self.sb.message_box("HDR Manager is not yet implemented for Blender.")

    def b001(self):
        """Lightmap Baker — mayatk panel; not yet ported (use Cycles bake)."""
        self.sb.message_box("Lightmap Baker is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
