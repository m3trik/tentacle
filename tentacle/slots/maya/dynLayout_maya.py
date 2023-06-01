# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.dynLayout import DynLayout


class DynLayout_maya(DynLayout, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.dynLayout.draggableHeader.ctx_menu.cmb000
        items = []
        cmb.addItems_(items, "")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.dynLayout.draggableHeader.ctx_menu.cmb000

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
