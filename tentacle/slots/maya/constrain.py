# !/usr/bin/python
# coding=utf-8

# From this package:
from tentacle import Slots


class ConstrainSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.handlers.ui.get("constrain", header=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
