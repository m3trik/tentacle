# !/usr/bin/python
# coding=utf-8

# From this package:
from tentacle import Slots


class MeshToolsSlots(Slots):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb = kwargs.get("switchboard")
        self.ui = self.sb.handlers.ui.get("mesh_tools", header=True)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
