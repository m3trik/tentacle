# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Rigging(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """
        dh = self.sb.rigging.draggableHeader
        dh.ctxMenu.add(
            self.sb.ComboBox, setObjectName="cmb000", setToolTip="Rigging Editors"
        )

        tb000 = self.sb.rigging.tb000
        tb000.ctxMenu.add(
            "QCheckBox",
            setText="Joints",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Display Joints.",
        )
        tb000.ctxMenu.add(
            "QCheckBox",
            setText="IK",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Display IK.",
        )
        tb000.ctxMenu.add(
            "QCheckBox",
            setText="IK\\FK",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Display IK\\FK.",
        )
        tb000.ctxMenu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            setMinMax_="0.00-10 step.5",
            setValue=1.0,
            setToolTip="Global Display Scale for the selected type.",
        )
        self.chk000()  # init scale joint value

        tb001 = self.sb.rigging.tb001
        tb001.ctxMenu.add(
            "QCheckBox",
            setText="Align world",
            setObjectName="chk003",
            setToolTip="Align joints with the worlds transform.",
        )

        tb002 = self.sb.rigging.tb002
        tb002.ctxMenu.add(
            "QCheckBox",
            setText="Template Child",
            setObjectName="chk004",
            setChecked=False,
            setToolTip="Template child object(s) after parenting.",
        )

        tb003 = self.sb.rigging.tb003
        tb003.ctxMenu.add(
            "QDoubleSpinBox",
            setPrefix="Locator Scale: ",
            setObjectName="s001",
            setMinMax_=".000-1000 step1",
            setValue=1,
            setToolTip="The scale of the locator.",
        )
        tb003.ctxMenu.add(
            "QLineEdit",
            setPlaceholderText="Group Suffix:",
            setText="_GRP",
            setObjectName="t002",
            setToolTip="A string appended to the end of the created group's name.",
        )
        tb003.ctxMenu.add(
            "QLineEdit",
            setPlaceholderText="Locator Suffix:",
            setText="",
            setObjectName="t000",
            setToolTip="A string appended to the end of the created locator's name.",
        )
        tb003.ctxMenu.add(
            "QLineEdit",
            setPlaceholderText="Geometry Suffix:",
            setText="",
            setObjectName="t001",
            setToolTip="A string appended to the end of the existing geometry's name.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Strip Suffix",
            setObjectName="chk016",
            setToolTip="Strip any of preexisting suffixes from the group name before appending the new ones.\nA suffix is defined as anything trailing an underscore.\nAny user-defined suffixes are stripped by default.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Strip Digits",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Strip any trailing numeric characters from the name.\nIf the resulting name is not unique, maya will append a trailing digit.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Parent",
            setObjectName="chk006",
            setChecked=True,
            setToolTip="Parent to object to the locator.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Freeze transforms on the locator.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Bake Child Pivot",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="Bake pivot positions on the child object.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Lock Child Translate",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Lock the translate values of the child object.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Lock Child Rotation",
            setObjectName="chk008",
            setChecked=True,
            setToolTip="Lock the rotation values of the child object.",
        )
        tb003.ctxMenu.add(
            "QCheckBox",
            setText="Lock Child Scale",
            setObjectName="chk009",
            setToolTip="Lock the scale values of the child object.",
        )

        tb004 = self.sb.rigging.tb004
        tb004.ctxMenu.add(
            "QCheckBox",
            setText="Translate",
            setObjectName="chk012",
            setChecked=False,
            setToolTip="",
        )
        tb004.ctxMenu.add(
            "QCheckBox",
            setText="Rotate",
            setObjectName="chk013",
            setChecked=False,
            setToolTip="",
        )
        tb004.ctxMenu.add(
            "QCheckBox",
            setText="Scale",
            setObjectName="chk014",
            setChecked=False,
            setToolTip="",
        )
        self.sb.connect_multi(
            (tb004.ctxMenu.chk012, tb004.ctxMenu.chk013, tb004.ctxMenu.chk014),
            "toggled",
            [
                lambda state: self.sb.rigging.tb004.setText(
                    "Lock Attributes"
                    if any(
                        (
                            tb004.ctxMenu.chk012.isChecked(),
                            tb004.ctxMenu.chk013.isChecked(),
                            tb004.ctxMenu.chk014.isChecked(),
                        )
                    )
                    else "Unlock Attributes"
                ),
                lambda state: self.sb.rigging_submenu.tb004.setText(
                    "Lock Transforms"
                    if any(
                        (
                            tb004.ctxMenu.chk012.isChecked(),
                            tb004.ctxMenu.chk013.isChecked(),
                            tb004.ctxMenu.chk014.isChecked(),
                        )
                    )
                    else "Unlock Attributes"
                ),
            ],
        )

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.rigging.draggableHeader
