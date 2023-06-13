# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Utilities_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def b000(self):
        """Measure"""
        pm.mel.DistanceTool()

    def b001(self):
        """Annotation"""
        pm.mel.CreateAnnotateNode()

    def b002(self):
        """Calculator"""
        pm.mel.calculator()

    def b003(self):
        """Grease Pencil"""
        pm.mel.greasePencilCtx()


# --------------------------------------------------------------------------------------------

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
