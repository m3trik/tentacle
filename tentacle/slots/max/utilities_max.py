# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.utilities import Utilities


class Utilities_max(Utilities, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.utilities.draggableHeader.ctx_menu.cmb000
        files = [""]
        cmb.addItems_(files, "")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.utilities.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def b000(self, *args, **kwargs):
        """Measure"""
        maxEval('macros.run "Tools" "two_point_dist"')

    def b001(self, *args, **kwargs):
        """Annotation"""
        mel.eval("CreateAnnotateNode;")

    def b002(self, *args, **kwargs):
        """Calculator"""
        mel.eval("calculator;")

    def b003(self, *args, **kwargs):
        """Grease Pencil"""
        mel.eval("greasePencilCtx;")


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
