# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Edit(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """
        dh = self.sb.edit.draggableHeader
        dh.ctxMenu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="Editors")

        cmb001 = self.sb.edit.cmb001
        cmb001.beforePopupShown.connect(
            self.cmb001
        )  # refresh comboBox contents before showing it's popup.

        tb001 = self.sb.edit.tb001
        tb001.ctxMenu.add(
            "QCheckBox",
            setText="For All Objects",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Delete history on All objects or just those selected.",
        )
        tb001.ctxMenu.add(
            "QCheckBox",
            setText="Delete Unused Nodes",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Delete unused nodes.",
        )
        tb001.ctxMenu.add(
            "QCheckBox",
            setText="Delete Deformers",
            setObjectName="chk020",
            setToolTip="Delete deformers.",
        )
        tb001.ctxMenu.add(
            "QCheckBox",
            setText="Optimize Scene",
            setObjectName="chk030",
            setToolTip="Remove unused scene objects.",
        )

        tb002 = self.sb.edit.tb002
        tb002.ctxMenu.add(
            "QCheckBox",
            setText="Delete Edge Loop",
            setObjectName="chk001",
            setToolTip="Delete the edge loops of any edges selected.",
        )
        tb002.ctxMenu.add(
            "QCheckBox",
            setText="Delete Edge Ring",
            setObjectName="chk000",
            setToolTip="Delete the edge rings of any edges selected.",
        )

        tb003 = self.sb.edit.tb003
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="-",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Perform delete along negative axis.",
        )
        tb003.ctxMenu.add(
            "QRadioButton",
            setText="X",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Perform delete along X axis.",
        )
        tb003.ctxMenu.add(
            "QRadioButton",
            setText="Y",
            setObjectName="chk008",
            setToolTip="Perform delete along Y axis.",
        )
        tb003.ctxMenu.add(
            "QRadioButton",
            setText="Z",
            setObjectName="chk009",
            setToolTip="Perform delete along Z axis.",
        )
        self.sb.connect_multi("chk006-9", "toggled", self.chk006_9, tb003.ctxMenu)

        tb004 = self.sb.edit.tb004
        tb004.ctxMenu.add(
            "QCheckBox",
            setText="All Nodes",
            setObjectName="chk026",
            setToolTip="Effect all nodes or only those currently selected.",
        )
        tb004.ctxMenu.add(
            "QCheckBox",
            setText="UnLock",
            setObjectName="chk027",
            setChecked=True,
            setToolTip="Unlock nodes (else lock).",
        )
        tb004.ctxMenu.chk027.toggled.connect(
            lambda state: tb004.setText("Unlock Nodes" if state else "Lock Nodes")
        )

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.edit.draggableHeader

    def chk006_9(self):
        """Set the toolbutton's text according to the checkstates."""
        tb = self.sb.edit.tb003
        axis = self.sb.get_axis_from_checkboxes("chk006-9", tb.ctxMenu)
        tb.setText("Delete " + axis)
