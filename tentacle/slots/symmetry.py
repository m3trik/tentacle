# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Symmetry(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        dh = self.sb.symmetry.draggableHeader
        dh.ctx_menu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.symmetry.draggableHeader

    def chk000(self, state=None):
        """Symmetry X"""
        self.sb.toggle_widgets(setUnChecked="chk001,chk002")
        self.setSymmetry(state, "x")

    def chk001(self, state=None):
        """Symmetry Y"""
        self.sb.toggle_widgets(setUnChecked="chk000,chk002")
        self.setSymmetry(state, "y")

    def chk002(self, state=None):
        """Symmetry Z"""
        self.sb.toggle_widgets(setUnChecked="chk000,chk001")
        self.setSymmetry(state, "z")

    def chk004(self, state=None):
        """Symmetry: Object"""
        self.sb.symmetry.chk005.setChecked(False)  # uncheck symmetry:topological


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:
# sync widgets
# self.sb.sync_widgets(self.sb.transform.option_menu.chk000, self.sb.transform_submenu.chk000, attributes='setChecked')
# self.sb.sync_widgets(self.sb.transform.option_menu.chk001, self.sb.transform_submenu.chk001, attributes='setChecked')
# self.sb.sync_widgets(self.sb.transform.option_menu.chk002, self.sb.transform_submenu.chk002, attributes='setChecked')
