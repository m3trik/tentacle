# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Materials(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.random_mat = None

    def cmb002_init(self, widget):
        """ """
        widget.refresh = True
        if not widget.is_initialized:
            widget.editable = True
            widget.menu.add(
                "QComboBox",
                setObjectName="cmb001",
                addItems=["Scene Materials", "ID Map Materials", "Favorite Materials"],
                setToolTip="Filter materials list based on type.",
            )
            widget.menu.add(
                self.sb.Label,
                setText="Open in Editor",
                setObjectName="lbl000",
                setToolTip="Open material in editor.",
            )
            widget.menu.add(
                self.sb.Label,
                setText="Delete",
                setObjectName="lbl002",
                setToolTip="Delete the current material.",
            )
            widget.menu.add(
                self.sb.Label,
                setText="Delete All Unused Materials",
                setObjectName="lbl003",
                setToolTip="Delete All unused materials.",
            )
            widget.menu.add(
                self.sb.Label,
                setText="Material Attributes",
                setObjectName="lbl004",
                setToolTip="Show the material attributes in the attribute editor.",
            )
            widget.on_editing_finished.connect(
                lambda text: pm.rename(widget.currentData(), text)
            )
            # Refresh contents each index change.
            widget.menu.cmb001.currentIndexChanged.connect(widget.init_slot)
            # Set the groupbox title to reflect the current filter.
            widget.menu.cmb001.currentIndexChanged.connect(
                lambda: self.sb.materials.group000.setTitle(
                    widget.menu.cmb001.currentText()
                )
            )

        mode = widget.menu.cmb001.currentText()
        if mode == "Scene Materials":
            materials = mtk.get_scene_mats(exc="standardSurface")
        elif mode == "ID Map Materials":
            materials = mtk.get_scene_mats(inc="ID_*")
        elif mode == "Favorite Materials":
            materials = mtk.get_fav_mats()

        materials_dict = {m.name(): m for m in materials}
        widget.add(materials_dict, clear=True)

        # create and set icons with color swatch
        for i, mat in enumerate(widget.items):
            icon = self.getColorSwatchIcon(mat)
            widget.setItemIcon(i, icon) if icon else None

        # initialize the materials list
        b = self.sb.materials_submenu.b003
        # set submenu assign material button attributes
        b.setText("Assign " + widget.currentText())
        icon = self.getColorSwatchIcon(widget.currentText(), [15, 15])
        b.setIcon(icon) if icon else None
        b.setMinimumWidth(b.minimumSizeHint().width() + 25)
        b.setVisible(True if widget.currentText() else False)

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Shell",
            setObjectName="chk005",
            setToolTip="Select entire shell.",
        )

    def tb002_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Current Material",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Re-Assign the current stored material.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="New Material",
            setObjectName="chk009",
            setToolTip="Assign a new material.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="New Random Material",
            setObjectName="chk008",
            setToolTip="Assign a new random ID material.",
        )
        widget.menu.chk007.clicked.connect(
            lambda state: widget.setText("Assign Current")
        )
        widget.menu.chk009.clicked.connect(lambda state: widget.setText("Assign New"))
        widget.menu.chk008.clicked.connect(
            lambda state: widget.setText("Assign Random")
        )
        # Refresh the materials list
        widget.released.connect(widget.ui.cmb002.init_slot)

    def tb000(self, widget):
        """Select By Material ID"""
        mat = self.sb.materials.cmb002.currentData()
        if not mat:
            self.sb.message_box(
                amg="<hl>Nothing selected</hl><br>Select an object face, or choose the option: current material.",
                pos="midCenterTop",
                fade=True,
            )
            return

        shell = widget.menu.chk005.isChecked()  # Select by material: shell

        selection = pm.ls(sl=1, objectsOnly=1)
        faces_with_mat = mtk.find_by_mat_id(mat, selection, shell=shell)

        pm.select(faces_with_mat)

    def tb002(self, widget):
        """Assign Material"""
        selection = pm.ls(sl=True, flatten=1)
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return

        assignCurrent = widget.menu.chk007.isChecked()
        assignRandom = widget.menu.chk008.isChecked()
        assignNew = widget.menu.chk009.isChecked()

        if assignCurrent:  # Assign current mat
            mat = self.sb.materials.cmb002.currentData()
            if isinstance(mat, str):  # new mat type as a string:
                mtk.assign_mat(selection, pm.createNode(mat))
            else:  # existing mat object:
                mtk.assign_mat(selection, mat)

        elif assignRandom:  # Assign New random mat ID
            mat = mtk.create_random_mat(prefix="ID_")
            mtk.assign_mat(selection, mat)

            self.random_mat = mat

            # set the combobox index to the new mat
            self.sb.materials.cmb002.setCurrentItem(mat.name())

        elif assignNew:  # Assign New Material
            pm.mel.buildObjectMenuItemsNow(
                "MainPane|viewPanes|modelPanel4|modelPanel4|modelPanel4|modelPanel4ObjectPop"
            )
            pm.mel.createAssignNewMaterialTreeLister("")

    def lbl000(self):
        """Open material in editor"""
        try:
            mat = self.sb.materials.cmb002.currentData()  # get the mat obj from cmb002
            pm.select(mat)
        except Exception:
            self.sb.message_box("No stored material or no valid object selected.")
            return

        pm.mel.HypershadeWindow()  # open the hypershade editor

    def lbl002(self):
        """Delete Material"""
        mat = self.sb.materials.cmb002.currentData()
        mat = pm.delete(mat)

        index = self.sb.materials.cmb002.currentIndex()
        self.sb.materials.cmb002.setItemText(index, "None")

    def lbl003(self, widget):
        """Delete Unused Materials"""
        pm.mel.hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes")
        widget.ui.cmb002.init_slot  # refresh the materials list comboBox

    def lbl004(self):
        """Material Attributes: Show Material Attributes in the Attribute Editor."""
        mat = self.sb.materials.cmb002.currentData()
        try:
            pm.mel.showSG(mat.name())
        except Exception as e:
            print(e)

    def b000(self):
        """Material List: Delete"""
        self.lbl002()

    def b001(self):
        """Material List: Edit"""
        self.lbl000()

    def b002(self, widget):
        """Set Material: Set the currently selected material as the current material."""
        selection = pm.ls(sl=True)
        if not selection:
            self.sb.message_box(
                "<hl>Nothing selected</hl><br>Select mesh object(s) or face(s)."
            )
            return

        mat = mtk.get_mats(selection[0])
        if len(mat) != 1:
            self.sb.message_box(
                "<hl>Invalid selection</hl><br>Selection must have exactly one material assigned."
            )
            return

        # set the combobox to show all scene materials
        self.sb.materials.cmb002.menu.cmb001.setCurrentIndex(0)
        widget.ui.cmb002.init_slot()  # refresh the materials list comboBox
        self.sb.materials.cmb002.setCurrentItem(mat.pop().name())

    def b003(self, widget):
        """Assign: Assign Current"""
        self.sb.materials.tb002.menu.chk007.setChecked(True)
        self.sb.materials.tb002.setText("Assign Current")
        widget.ui.tb002.init_slot()

    def b004(self, widget):
        """Assign: Assign Random"""
        self.sb.materials.tb002.menu.chk008.setChecked(True)
        self.sb.materials.tb002.setText("Assign Random")
        widget.ui.tb002.init_slot()

    def b005(self, widget):
        """Assign: Assign New"""
        self.sb.materials.tb002.menu.chk009.setChecked(True)
        self.sb.materials.tb002.setText("Assign New")
        widget.ui.tb002.init_slot()

    def getColorSwatchIcon(self, mat, size=[20, 20]):
        """Get an icon with a color fill matching the given materials RBG value.

        Parameters:
            mat (obj)(str): The material or the material's name.
            size (list): Desired icon size.

        Returns:
            (obj) pixmap icon.
        """
        from PySide2.QtGui import QPixmap, QColor, QIcon

        try:
            # get the string name if a mat object is given.
            matName = mat.name() if not isinstance(mat, (str)) else mat
            # convert from 0-1 to 0-255 value and then to an integer
            r = int(pm.getAttr(matName + ".colorR") * 255)
            g = int(pm.getAttr(matName + ".colorG") * 255)
            b = int(pm.getAttr(matName + ".colorB") * 255)
            pixmap = QPixmap(size[0], size[1])
            pixmap.fill(QColor.fromRgb(r, g, b))

            return QIcon(pixmap)

        except Exception:
            pass


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
