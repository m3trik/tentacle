# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender._slots_blender import SlotsBlender


class Lighting(SlotsBlender):
    """Blender port of the shared ``lighting`` menu.

    HDR Manager opens the world-environment panel; the Lightmap Baker opens the
    Cycles-bake panel (``btk.LightmapBaker`` engine + co-located ``LightmapBakerSlots``,
    discovered by ``BlenderUiHandler``). Both panels live in blendertk.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def b000(self):
        """Launch the HDR Manager (world-environment HDRI panel)."""
        self.sb.handlers.marking_menu.show("hdr_manager")

    def b001(self):
        """Launch the Lightmap Baker (Cycles-bake → game-engine lightmaps)."""
        self.sb.handlers.marking_menu.show("lightmap_baker")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
