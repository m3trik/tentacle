# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class CacheSlots(SlotsMaya):

    def __init__(self, switchboard):
        super().__init__(switchboard=switchboard)

        self.sb = switchboard
        self.ui = self.sb.handlers.ui.get("cache", header=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
