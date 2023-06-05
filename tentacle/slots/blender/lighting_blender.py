# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.lighting import Lighting


class Lighting_blender(Lighting, SlotsBlender):
    def __init__(self, *args, **kwargs):
        SlotsBlender.__init__(self, *args, **kwargs)
        Lighting.__init__(self, *args, **kwargs)

        cmb = self.sb.lighting.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.lighting.draggableHeader

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.lighting.draggableHeader.ctx_menu.cmb000

        # if index>0:
        # 	if index==cmb.items.index(''):
        # 		pass
        # 	cmb.setCurrentIndex(0)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
