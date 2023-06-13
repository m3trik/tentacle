# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Materials_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.randomMat = None

    def draggableHeader_init(self, widget):
        """ """
        widget.ctx_menu.add(
            self.sb.Label,
            setText="Material Attributes",
            setObjectName="lbl004",
            setToolTip="Show the material attributes in the attribute editor.",
        )
        self.sb.materials_submenu.b003.setVisible(False)

    def cmb002_init(self, widget):
        """ """
        widget.refresh = True
        widget.option_menu.clear()
        widget.option_menu.add(
            "QComboBox",
            setObjectName="cmb001",
            addItems=["Scene Materials", "ID Map Materials", "Favorite Materials"],
            setToolTip="Filter materials list based on type.",
        )
        widget.option_menu.add(
            self.sb.Label,
            setText="Open in Editor",
            setObjectName="lbl000",
            setToolTip="Open material in editor.",
        )
        widget.option_menu.add(
            self.sb.Label,
            setText="Rename",
            setObjectName="lbl001",
            setToolTip="Rename the current material.",
        )
        widget.option_menu.add(
            self.sb.Label,
            setText="Delete",
            setObjectName="lbl002",
            setToolTip="Delete the current material.",
        )
        widget.option_menu.add(
            self.sb.Label,
            setText="Delete All Unused Materials",
            setObjectName="lbl003",
            setToolTip="Delete All unused materials.",
        )
        widget.returnPressed.connect(lambda: self.lbl001(setEditable=False))
        # set the popup title to be the current materials name.
        widget.currentIndexChanged.connect(
            lambda: widget.option_menu.setTitle(widget.currentText())
        )
        # set the groupbox title to reflect the current filter.
        widget.option_menu.cmb001.currentIndexChanged.connect(
            lambda: self.sb.materials.group000.setTitle(
                widget.option_menu.cmb001.currentText()
            )
        )
        # refresh cmb002 contents.
        widget.option_menu.cmb001.currentIndexChanged.connect(
            lambda v, w=widget: self.cmb002_init(w)
        )
        # initialize the materials list
        b = self.sb.materials_submenu.b003

        mode = widget.option_menu.cmb001.currentText()
        if mode == "Scene Materials":
            materials = mtk.get_scene_mats(exc="standardSurface")

        elif mode == "ID Map Materials":
            materials = mtk.get_scene_mats(inc="ID_*")

        if mode == "Favorite Materials":
            fav_materials = mtk.get_fav_mats()
            currentMats = {
                matName: matName for matName in sorted(list(set(fav_materials)))
            }
        else:
            currentMats = {
                mat.name(): mat
                for mat in sorted(list(set(materials)))
                if hasattr(mat, "name")
            }

        widget.addItems_(currentMats, clear=True)

        # create and set icons with color swatch
        for i, mat in enumerate(widget.items):
            icon = self.getColorSwatchIcon(mat)
            widget.setItemIcon(i, icon) if icon else None

        # set submenu assign material button attributes
        b.setText("Assign " + widget.currentText())
        icon = self.getColorSwatchIcon(widget.currentText(), [15, 15])
        b.setIcon(icon) if icon else None
        b.setMinimumWidth(b.minimumSizeHint().width() + 25)
        b.setVisible(True if widget.currentText() else False)

    def tb000_init(self, widget):
        """ """
        widget.option_menu.add(
            "QCheckBox",
            setText="Shell",
            setObjectName="chk005",
            setToolTip="Select entire shell.",
        )

    def tb002_init(self, widget):
        """ """
        widget.option_menu.add(
            "QRadioButton",
            setText="Current Material",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Re-Assign the current stored material.",
        )
        widget.option_menu.add(
            "QRadioButton",
            setText="New Material",
            setObjectName="chk009",
            setToolTip="Assign a new material.",
        )
        widget.option_menu.add(
            "QRadioButton",
            setText="New Random Material",
            setObjectName="chk008",
            setToolTip="Assign a new random ID material.",
        )
        widget.option_menu.chk007.clicked.connect(
            lambda state: widget.setText("Assign Current")
        )
        widget.option_menu.chk009.clicked.connect(
            lambda state: widget.setText("Assign New")
        )
        widget.option_menu.chk008.clicked.connect(
            lambda state: widget.setText("Assign Random")
        )
        # Refresh the materials list
        widget.released.connect(lambda w=widget: self.cmb002_init(w))

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

        shell = widget.option_menu.chk005.isChecked()  # Select by material: shell

        selection = pm.ls(sl=1, objectsOnly=1)
        faces_with_mat = mtk.find_by_mat_id(mat, selection, shell=shell)

        pm.select(faces_with_mat)

    def tb002(self, widget):
        """Assign Material"""
        selection = pm.ls(sl=True, flatten=1)
        if not selection:
            self.sb.message_box("No renderable object is selected for assignment.")
            return

        assignCurrent = widget.option_menu.chk007.isChecked()
        assignRandom = widget.option_menu.chk008.isChecked()
        assignNew = widget.option_menu.chk009.isChecked()

        if assignCurrent:  # Assign current mat
            mat = self.sb.materials.cmb002.currentData()
            if isinstance(mat, str):  # new mat type as a string:
                mtk.assign_mat(selection, pm.createNode(mat))
            else:  # existing mat object:
                mtk.assign_mat(selection, mat)

        elif assignRandom:  # Assign New random mat ID
            mat = mtk.create_random_mat(prefix="ID_")
            mtk.assign_mat(selection, mat)

            self.randomMat = mat

            # set the combobox index to the new mat #self.cmb002.setCurrentIndex(self.cmb002.findText(name))
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

    def lbl001(self, setEditable=True):
        """Rename Material: Set cmb002 as editable and disable wgts."""
        cmb = self.sb.materials.cmb002

        if setEditable:
            self._mat = self.sb.materials.cmb002.currentData()
            cmb.setEditable(True)
            self.sb.toggle_widgets(
                self.sb.materials, setDisabled="b002,lbl000,tb000,tb002"
            )
        else:
            mat = self._mat
            newMatName = cmb.currentText()
            self.renameMaterial(mat, newMatName)
            cmb.setEditable(False)
            self.sb.toggle_widgets(
                self.sb.materials, setEnabled="b002,lbl000,tb000,tb002"
            )

    def lbl002(self):
        """Delete Material"""
        mat = self.sb.materials.cmb002.currentData()
        mat = pm.delete(mat)

        index = self.sb.materials.cmb002.currentIndex()
        self.sb.materials.cmb002.setItemText(
            index, "None"
        )  # self.sb.materials.cmb002.removeItem(index)

    def lbl003(self, widget):
        """Delete Unused Materials"""
        pm.mel.hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes")
        self.cmb002_init(widget.ui.cmb002)  # refresh the materials list comboBox

    def lbl004(self):
        """Material Attributes: Show Material Attributes in the Attribute Editor."""
        mat = self.sb.materials.cmb002.currentData()
        try:
            pm.mel.showSG(mat.name())
        except Exception as error:
            print(error)

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
        self.sb.materials.cmb002.option_menu.cmb001.setCurrentIndex(0)
        self.cmb002_init(widget.ui.cmb002)  # refresh the materials list comboBox
        self.sb.materials.cmb002.setCurrentItem(mat.pop().name())

    def b003(self, widget):
        """Assign: Assign Current"""
        self.sb.materials.tb002.option_menu.chk007.setChecked(True)
        self.sb.materials.tb002.setText("Assign Current")
        self.tb002_init(widget.ui.tb002)

    def b004(self, widget):
        """Assign: Assign Random"""
        self.sb.materials.tb002.option_menu.chk008.setChecked(True)
        self.sb.materials.tb002.setText("Assign Random")
        self.tb002_init(widget.ui.tb002)

    def b005(self, widget):
        """Assign: Assign New"""
        self.sb.materials.tb002.option_menu.chk009.setChecked(True)
        self.sb.materials.tb002.setText("Assign New")
        self.tb002_init(widget.ui.tb002)

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

    def renameMaterial(self, mat, newMatName):
        """Rename material"""
        cmb = self.sb.materials.cmb002  # scene materials

        curMatName = mat.name()
        if curMatName != newMatName:
            cmb.setItemText(cmb.currentIndex(), newMatName)
            try:
                print(curMatName, newMatName)
                pm.rename(curMatName, newMatName)

            except RuntimeError as error:
                cmb.setItemText(cmb.currentIndex(), str(error).strip("\n"))


# --------------------------------------------------------------------------------------------

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# depricated


# @property
# def currentMat(self):
#   '''Get the current material using the current index of the materials combobox.
#   '''
#   text = self.sb.materials.cmb002.currentText()

#   try:
#       result = self.currentMats[text]
#   except:
#       result = None

#   return result

# elif storedMaterial:
#   mat = self.currentMat
#   if not mat:
#       cmb.addItems_(['Stored Material: None'])
#       return

#   matName = mat.name()

#   if pm.nodeType(mat)=='VRayMultiSubTex':
#       subMaterials = pm.hyperShade(mat, listUpstreamShaderNodes=1) #get any connected submaterials
#       subMatNames = [s.name() for s in subMaterials if s is not None]
#   else:
#       subMatNames=[]

#   contents = cmb.addItems_(subMatNames, matName)

#   if index is None:
#       index = cmb.currentIndex()
#   if index!=0:
#       self.currentMat = subMaterials[index-1]
#   else:
#       self.currentMat = mat

# def cmb000(self, *args, **kwargs):
#   '''
#   Existing Materials

#   '''
#   cmb = self.sb.materials.draggableHeader.ctx_menu.cmb000

#   mats = [m for m in pm.ls(materials=1)]
#   matNames = [m.name() for m in mats]

#   contents = cmb.addItems_(matNames, "Scene Materials")

#   if index is None:
#       index = cmb.currentIndex()
#   if index!=0:
#       print contents[index]

#       self.currentMat = mats[index-1] #store material
#       self.cmb002() #refresh combobox

#       cmb.setCurrentIndex(0)


# assign random
# pm.mel.eval('''
#       string $selection[] = `ls -selection`;

#       int $d = 2; //decimal places to round to
#       $r = rand (0,1);
#       $r = trunc($r*`pow 10 $d`+0.5)/`pow 10 $d`;
#       $g = rand (0,1);
#       $g = trunc($g*`pow 10 $d`+0.5)/`pow 10 $d`;
#       $b = rand (0,1);
#       $b = trunc($b*`pow 10 $d`+0.5)/`pow 10 $d`;

#       string $rgb = ("_"+$r+"_"+$g+"_"+$b);
#       $rgb = substituteAllString($rgb, "0.", "");

#       $name = ("ID_"+$rgb);

#       string $ID_ = `shadingNode -asShader lambert -name $name`;
#       setAttr ($name + ".colorR") $r;
#       setAttr ($name + ".colorG") $g;
#       setAttr ($name + ".colorB") $b;

#       for ($object in $selection)
#           {
#           select $object;
#           hyperShade -assign $ID_;
#           }
#        ''')

# re-assign random
# pm.mel.eval('''
# string $objList[] = `ls -selection -flatten`;
# $material = `hyperShade -shaderNetworksSelectMaterialNodes ""`;
# string $matList[] = `ls -selection -flatten`;

# hyperShade -objects $material;
# string $selection[] = `ls -selection`;
# //delete the old material and shader group nodes
# for($i=0; $i<size($matList); $i++)
#   {
#   string $matSGplug[] = `connectionInfo -dfs ($matList[$i] + ".outColor")`;
#   $SGList[$i] = `match "^[^\.]*" $matSGplug[0]`;
#   print $matList; print $SGList;
#   delete $matList[$i];
#   delete $SGList[$i];
#   }
# //create new random material
# int $d = 2; //decimal places to round to
# $r = rand (0,1);
# $r = trunc($r*`pow 10 $d`+0.5)/`pow 10 $d`;
# $g = rand (0,1);
# $g = trunc($g*`pow 10 $d`+0.5)/`pow 10 $d`;
# $b = rand (0,1);
# $b = trunc($b*`pow 10 $d`+0.5)/`pow 10 $d`;

# string $rgb = ("_"+$r+"_"+$g+"_"+$b+"");
# $rgb = substituteAllString($rgb, "0.", "");

# $name = ("ID_"+$rgb);

# string $ID_ = `shadingNode -asShader lambert -name $name`;
# setAttr ($name + ".colorR") $r;
# setAttr ($name + ".colorG") $g;
# setAttr ($name + ".colorB") $b;

# for ($object in $selection)
#   {
#   select $object;
#   hyperShade -assign $ID_;
#   }
# ''')
