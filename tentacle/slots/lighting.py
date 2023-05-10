# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Lighting(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.lighting.draggableHeader.ctxMenu
        if not ctx.containsMenuItems:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")
