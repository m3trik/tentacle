# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.lighting import Lighting


class Lighting_max(Lighting, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.lighting.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.lighting.draggableHeader

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.lighting.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
