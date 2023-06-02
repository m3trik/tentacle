# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Deformation(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.deformation.draggableHeader.ctx_menu
        if not ctx.contains_items:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.deformation.draggableHeader
