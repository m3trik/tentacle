# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Lighting_maya(SlotsMaya):
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

        # if index>0:
        #   if index==cmb.items.index(''):
        #       pass
        #   cmb.setCurrentIndex(0)


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
