# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Scripting(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.scripting.draggableHeader.ctx_menu
        if not ctx.containsMenuItems:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.scripting.draggableHeader

    def chk000(self, state=None):
        """Toggle Mel/Python"""
        if self.sb.scripting.chk000.isChecked():
            self.sb.scripting.chk000.setText("python")
        else:
            self.sb.scripting.chk000.setText("MEL")
