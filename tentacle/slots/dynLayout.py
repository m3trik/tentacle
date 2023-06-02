# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class DynLayout(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.dynLayout.draggableHeader.ctx_menu
        if not ctx.contains_items:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")
            ctx.add(
                "QPushButton",
                setText="Delete History",
                setObjectName="b000",
                setToolTip="",
            )

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.dynLayout.draggableHeader

    def b000(self):
        """ """
        self.sb.get_method("edit", "tb001")()
