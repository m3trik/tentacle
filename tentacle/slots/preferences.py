# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Preferences(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        ctx = self.sb.preferences.draggableHeader.ctx_menu
        if not ctx.containsMenuItems:
            ctx.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.preferences.draggableHeader

    def cmb003(self, index=-1):
        """Ui Style: Set main ui style using QStyleFactory"""
        cmb = self.sb.preferences.cmb003

        if index > 0:
            from Pyside2.QtWidgets import QApplication

            QApplication.instance().setStyle(cmb.items[index])
