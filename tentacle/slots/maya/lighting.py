# !/usr/bin/python
# coding=utf-8
import mayatk as mtk

# From this Package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class Lighting(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb = kwargs.get("switchboard")
        self.ui = self.sb.loaded_ui.lighting
        self.submenu = self.sb.loaded_ui.lighting_submenu

    def b000(self):
        """Launch the HDR Manager."""
        self.sb.handlers.marking_menu.show("hdr_manager")

    def b001(self):
        """Launch the Lightmap Baker."""
        self.sb.handlers.marking_menu.show("lightmap_baker")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
