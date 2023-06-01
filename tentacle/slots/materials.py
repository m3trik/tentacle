# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots


class Materials(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
		"""
        self.sb.materials_submenu.b003.setVisible(
            False
        )  # hide the current material submenu button until a material is available.

        cmb002 = self.sb.materials.cmb002
        cmb002.option_menu.add(
            "QComboBox",
            setObjectName="cmb001",
            addItems=["Scene Materials", "ID Map Materials", "Favorite Materials"],
            setToolTip="Filter materials list based on type.",
        )
        cmb002.option_menu.add(
            self.sb.Label,
            setText="Open in Editor",
            setObjectName="lbl000",
            setToolTip="Open material in editor.",
        )
        cmb002.option_menu.add(
            self.sb.Label,
            setText="Rename",
            setObjectName="lbl001",
            setToolTip="Rename the current material.",
        )
        cmb002.option_menu.add(
            self.sb.Label,
            setText="Delete",
            setObjectName="lbl002",
            setToolTip="Delete the current material.",
        )
        cmb002.option_menu.add(
            self.sb.Label,
            setText="Delete All Unused Materials",
            setObjectName="lbl003",
            setToolTip="Delete All unused materials.",
        )
        cmb002.beforePopupShown.connect(
            self.cmb002
        )  # refresh comboBox contents before showing it's menu.
        cmb002.returnPressed.connect(lambda: self.lbl001(setEditable=False))
        cmb002.currentIndexChanged.connect(
            lambda: cmb002.option_menu.setTitle(cmb002.currentText())
        )  # set the popup title to be the current materials name.
        cmb002.option_menu.cmb001.currentIndexChanged.connect(
            lambda: self.sb.materials.group000.setTitle(
                cmb002.option_menu.cmb001.currentText()
            )
        )  # set the groupbox title to reflect the current filter.
        cmb002.option_menu.cmb001.currentIndexChanged.connect(
            self.cmb002
        )  # refresh cmb002 contents.
        self.cmb002()  # initialize the materials list

        tb000 = self.sb.materials.tb000
        tb000.option_menu.add(
            "QCheckBox",
            setText="All Objects",
            setObjectName="chk003",
            setToolTip="Search all scene objects, or only those currently selected.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Shell",
            setObjectName="chk005",
            setToolTip="Select entire shell.",
        )
        tb000.option_menu.add(
            "QCheckBox",
            setText="Invert",
            setObjectName="chk006",
            setToolTip="Invert Selection.",
        )

        tb002 = self.sb.materials.tb002
        tb002.option_menu.add(
            "QRadioButton",
            setText="Current Material",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Re-Assign the current stored material.",
        )
        tb002.option_menu.add(
            "QRadioButton",
            setText="New Material",
            setObjectName="chk009",
            setToolTip="Assign a new material.",
        )
        tb002.option_menu.add(
            "QRadioButton",
            setText="New Random Material",
            setObjectName="chk008",
            setToolTip="Assign a new random ID material.",
        )
        tb002.option_menu.chk007.clicked.connect(
            lambda state: tb002.setText("Assign Current")
        )
        tb002.option_menu.chk009.clicked.connect(lambda state: tb002.setText("Assign New"))
        tb002.option_menu.chk008.clicked.connect(
            lambda state: tb002.setText("Assign Random")
        )

    def draggableHeader(self, state=None):
        """Context menu"""
        dh = self.sb.materials.draggableHeader

    def b000(self):
        """Material List: Delete"""
        self.lbl002()

    def b001(self):
        """Material List: Edit"""
        self.lbl000()

    def b003(self):
        """Assign: Assign Current"""
        self.sb.materials.tb002.option_menu.chk007.setChecked(True)
        self.sb.materials.tb002.setText("Assign Current")
        self.tb002()

    def b004(self):
        """Assign: Assign Random"""
        self.sb.materials.tb002.option_menu.chk008.setChecked(True)
        self.sb.materials.tb002.setText("Assign Random")
        self.tb002()

    def b005(self):
        """Assign: Assign New"""
        self.sb.materials.tb002.option_menu.chk009.setChecked(True)
        self.sb.materials.tb002.setText("Assign New")
        self.tb002()
