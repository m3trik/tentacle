# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.lighting import Lighting


class Lighting_blender(Lighting, Slots_blender):
    def __init__(self, *args, **kwargs):
        Slots_blender.__init__(self, *args, **kwargs)
        Lighting.__init__(self, *args, **kwargs)

        cmb = self.sb.lighting.draggableHeader.ctxMenu.cmb000
        items = [""]
        cmb.addItems_(items, "")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.lighting.draggableHeader

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.lighting.draggableHeader.ctxMenu.cmb000

        # if index>0:
        # 	if index==cmd.items.index(''):
        # 		pass
        # 	cmb.setCurrentIndex(0)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
