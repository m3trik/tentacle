# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.dynLayout import DynLayout


class DynLayout_blender(DynLayout, Slots_blender):
    def __init__(self, *args, **kwargs):
        Slots_blender.__init__(self, *args, **kwargs)
        DynLayout.__init__(self, *args, **kwargs)

        cmb = self.sb.dynLayout.draggableHeader.ctxMenu.cmb000
        items = []
        cmb.addItems_(items, "")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.dynLayout.draggableHeader.ctxMenu.cmb000

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
