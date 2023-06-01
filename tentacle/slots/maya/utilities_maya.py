# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.utilities import Utilities


class Utilities_maya(Utilities, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.utilities.draggableHeader.ctx_menu.cmb000
        files = [""]
        cmb.addItems_(files, "")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.utilities.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def b000(self):
        """Measure"""
        pm.mel.eval("DistanceTool;")

    def b001(self):
        """Annotation"""
        pm.mel.eval("CreateAnnotateNode;")

    def b002(self):
        """Calculator"""
        pm.mel.eval("calculator;")

    def b003(self):
        """Grease Pencil"""
        pm.mel.eval("greasePencilCtx;")


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
