# !/usr/bin/python
# coding=utf-8
import maya.mel as mel
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class Utilities(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def b000(self):
        """Measure: create a distance-measure tool between two points."""
        mel.eval("DistanceTool")

    def b001(self):
        """Annotation: create an annotation (text label) node."""
        mel.eval("CreateAnnotateNode")

    def b002(self):
        """Calculator: open the calculator tool."""
        self.sb.handlers.marking_menu.show("calculator")

    def b003(self):
        """Grease Pencil"""
        mel.eval("OpenBluePencil")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
