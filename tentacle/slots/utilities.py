# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Utilities(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.utilities.draggableHeader.ctx_menu
        if not ctx.contains_items:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.utilities.draggableHeader
