# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``pivot`` panels.

The Center Pivot shortcuts (Object / Component / World), which drive the fork's own
``tb001``.
"""


class PivotMixin:
    """Shared ``pivot`` panel behavior. Mixed in ahead of the DCC Slots base."""

    def b000(self):
        """Center Pivot: Object"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk003.setChecked(True)
        self.ui.tb001.call_slot()

    def b001(self):
        """Center Pivot: Component"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk002.setChecked(True)
        self.ui.tb001.call_slot()

    def b002(self, widget):
        """Center Pivot: World"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk004.setChecked(True)
        self.ui.tb001.call_slot()
