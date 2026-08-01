# !/usr/bin/python
# coding=utf-8
import mayatk as mtk

# From this package:
from tentacle import SlotsMaya


class ArnoldSlots(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.handlers.ui.get("arnold", header=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
