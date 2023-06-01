# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Display(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.display.draggableHeader.ctx_menu
        if not ctx.containsMenuItems:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.display.draggableHeader
