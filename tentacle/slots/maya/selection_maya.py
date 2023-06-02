# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Selection(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draggableHeader_init(self, w):
        w.option_menu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")
        w.option_menu.add(
            self.sb.ComboBox,
            setObjectName="cmb006",
            setToolTip="A list of currently selected objects.",
        )
        items = ["Polygon Selection Constraints"]
        w.option_menu.cmb000.addItems_(items, "Selection Editors:")

        w.option_menu.add(
            "QCheckBox",
            setText="Ignore Backfacing",
            setObjectName="chk004",
            setToolTip="Ignore backfacing components during selection.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Soft Selection",
            setObjectName="chk008",
            setToolTip="Toggle soft selection mode.",
        )
        w.option_menu.add(
            self.sb.Label,
            setText="Grow Selection",
            setObjectName="lbl003",
            setToolTip="Grow the current selection.",
        )
        w.option_menu.add(
            self.sb.Label,
            setText="Shrink Selection",
            setObjectName="lbl004",
            setToolTip="Shrink the current selection.",
        )
        w.option_menu.cmb006.setCurrentText("Current Selection")
        w.option_menu.cmb006.popupStyle = "qmenu"
        w.option_menu.cmb006.beforePopupShown.connect(self.cmb006)

    def cmb001_init(self, w):
        w.option_menu.add(
            self.sb.Label,
            setText="Select",
            setObjectName="lbl005",
            setToolTip="Select the current set elements.",
        )
        w.option_menu.add(
            self.sb.Label,
            setText="New",
            setObjectName="lbl000",
            setToolTip="Create a new selection set.",
        )
        w.option_menu.add(
            self.sb.Label,
            setText="Modify",
            setObjectName="lbl001",
            setToolTip="Modify the current set by renaming and/or changing the selection.",
        )
        w.option_menu.add(
            self.sb.Label,
            setText="Delete",
            setObjectName="lbl002",
            setToolTip="Delete the current set.",
        )
        # w.returnPressed.connect(
        #     lambda m=w.option_menu.lastActiveChild: getattr(self, m(name=1))()
        # )
        w.currentIndexChanged.connect(self.lbl005)
        w.beforePopupShown.connect(self.cmb001)

    def tb000_init(self, w):
        w.option_menu.add(
            "QRadioButton",
            setText="Component Ring",
            setObjectName="chk000",
            setToolTip="Select component ring.",
        )
        w.option_menu.add(
            "QRadioButton",
            setText="Component Loop",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Select all contiguous components that form a loop with the current selection.",
        )
        w.option_menu.add(
            "QRadioButton",
            setText="Path Along Loop",
            setObjectName="chk009",
            setToolTip="The path along loop between two selected edges, vertices or UV's.",
        )
        w.option_menu.add(
            "QRadioButton",
            setText="Shortest Path",
            setObjectName="chk002",
            setToolTip="The shortest component path between two selected edges, vertices or UV's.",
        )
        w.option_menu.add(
            "QRadioButton",
            setText="Border Edges",
            setObjectName="chk010",
            setToolTip="Select the object(s) border edges.",
        )
        w.option_menu.add(
            "QSpinBox",
            setPrefix="Step: ",
            setObjectName="s003",
            set_limits="1-100 step1",
            setValue=1,
            setToolTip="Step Amount.",
        )

    def tb001_init(self, w):
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits="0.000-9999 step1.0",
            setValue=0.0,
            setToolTip="The allowed difference in any of the compared results.\nie. A tolerance of 4 allows for a difference of 4 components.\nie. A tolerance of 0.05 allows for that amount of variance between any of the bounding box values.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Vertex",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="The number of vertices.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Edge",
            setObjectName="chk012",
            setChecked=True,
            setToolTip="The number of edges.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Face",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="The number of faces.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Triangle",
            setObjectName="chk014",
            setToolTip="The number of triangles.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Shell",
            setObjectName="chk015",
            setToolTip="The number of shells shells (disconnected pieces).",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Uv Coord",
            setObjectName="chk016",
            setToolTip="The number of uv coordinates (for the current map).",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Area",
            setObjectName="chk017",
            setToolTip="The surface area of the object's faces in local space.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="World Area",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="The surface area of the object's faces in world space.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Bounding Box",
            setObjectName="chk019",
            setToolTip="The object's bounding box in 3d space.\nCannot be used with the topological flags.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Include Original",
            setObjectName="chk020",
            setToolTip="Include the original selected object(s) in the final selection.",
        )
        w.option_menu.chk018.stateChanged.connect(
            lambda state: self.sb.toggle_widgets(w.option_menu, setDisabled="chk011-18")
            if state
            else self.sb.toggle_widgets(w.option_menu, setEnabled="chk011-18")
        )

    def tb002_init(self, w):
        w.option_menu.add(
            "QCheckBox",
            setText="Lock Values",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Keep values in sync.",
        )
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="x: ",
            setObjectName="s002",
            set_limits="0.00-1 step.01",
            setValue=0.05,
            setToolTip="Normal X range.",
        )
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="y: ",
            setObjectName="s004",
            set_limits="0.00-1 step.01",
            setValue=0.05,
            setToolTip="Normal Y range.",
        )
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="z: ",
            setObjectName="s005",
            set_limits="0.00-1 step.01",
            setValue=0.05,
            setToolTip="Normal Z range.",
        )

    def tb003_init(self, w):
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s006",
            set_limits="0.0-180 step1",
            setValue=70,
            setToolTip="Normal angle low range.",
        )
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s007",
            set_limits="0.0-180 step1",
            setValue=160,
            setToolTip="Normal angle high range.",
        )

    def cmb002_init(self, w):
        items = [
            "IK Handles",
            "Joints",
            "Clusters",
            "Lattices",
            "Sculpt Objects",
            "Wires",
            "Transforms",
            "Geometry",
            "NURBS Curves",
            "NURBS Surfaces",
            "Polygon Geometry",
            "Cameras",
            "Lights",
            "Image Planes",
            "Assets",
            "Fluids",
            "Particles",
            "Rigid Bodies",
            "Rigid Constraints",
            "Brushes",
            "Strokes",
            "Dynamic Constraints",
            "Follicles",
            "nCloths",
            "nParticles",
            "nRigids",
        ]
        w.addItems_(items, "By Type:")

    def cmb003_init(self, w):
        items = [
            "Verts",
            "Vertex Faces",
            "Vertex Perimeter",
            "Edges",
            "Edge Loop",
            "Edge Ring",
            "Contained Edges",
            "Edge Perimeter",
            "Border Edges",
            "Faces",
            "Face Path",
            "Contained Faces",
            "Face Perimeter",
            "UV's",
            "UV Shell",
            "UV Shell Border",
            "UV Perimeter",
            "UV Edge Loop",
            "Shell",
            "Shell Border",
        ]
        w.addItems_(items, "Convert To:")

    def cmb005_init(self, widget):
        items = ["Angle", "Border", "Edge Loop", "Edge Ring", "Shell", "UV Edge Loop"]
        widget.addItems_(items, "Off")

    def s002(self, value=None):
        """Select Island: tolerance x"""
        tb = self.sb.selection.tb002
        if tb.option_menu.chk003.isChecked():
            text = tb.option_menu.s002.value()
            tb.option_menu.s004.setValue(text)
            tb.option_menu.s005.setValue(text)

    def s004(self, value=None):
        """Select Island: tolerance y"""
        tb = self.sb.selection.tb002
        if tb.option_menu.chk003.isChecked():
            text = tb.option_menu.s004.value()
            tb.option_menu.s002.setValue(text)
            tb.option_menu.s005.setValue(text)

    def s005(self, value=None):
        """Select Island: tolerance z"""
        tb = self.sb.selection.tb002
        if tb.option_menu.chk003.isChecked():
            text = tb.option_menu.s005.value()
            tb.option_menu.s002.setValue(text)
            tb.option_menu.s004.setValue(text)

    def chk000(self, state=None):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_widgets(setUnChecked="chk001-2")

    def chk001(self, state=None):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_widgets(setUnChecked="chk000,chk002")

    def chk002(self, state=None):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_widgets(setUnChecked="chk000-1")

    def chk005(self, state=None):
        """Select Style: Marquee"""
        self.sb.toggle_widgets(setChecked="chk005", setUnChecked="chk006-7")
        Selection.setSelectionStyle("marquee")
        self.sb.message_box("Select Style: <hl>Marquee</hl>")

    def chk006(self, state=None):
        """Select Style: Lasso"""
        self.sb.toggle_widgets(setChecked="chk006", setUnChecked="chk005,chk007")
        Selection.setSelectionStyle("lasso")
        self.sb.message_box("Select Style: <hl>Lasso</hl>")

    def chk007(self, state=None):
        """Select Style: Paint"""
        self.sb.toggle_widgets(setChecked="chk007", setUnChecked="chk005-6")
        Selection.setSelectionStyle("paint")
        self.sb.message_box("Select Style: <hl>Paint</hl>")

    def txt001(self):
        """Select By Name"""
        searchStr = str(
            self.sb.selection.txt001.text()
        )  # asterisk denotes startswith*, *endswith, *contains*
        if searchStr:
            selection = pm.select(pm.ls(searchStr))

    def lbl000(self):
        """Selection Sets: Create New"""
        cmb = self.sb.selection.cmb001
        if not cmb.isEditable():
            cmb.addItems_("", ascending=True)
            cmb.setEditable(True)
            cmb.lineEdit().setPlaceholderText("New Set:")
        else:
            name = cmb.currentText()
            self.creatNewSelectionSet(name)
            self.cmb001()  # refresh the sets comboBox
            cmb.setCurrentIndex(0)

    def lbl001(self):
        """Selection Sets: Modify Current"""
        cmb = self.sb.selection.cmb001
        if not cmb.isEditable():
            name = cmb.currentText()
            self._oldSetName = name
            cmb.setEditable(True)
            cmb.lineEdit().setPlaceholderText(name)
        else:
            name = cmb.currentText()
            self.modifySet(self._oldSetName)
            cmb.setItemText(cmb.currentIndex(), name)
            # self.cmb001() #refresh the sets comboBox

    def lbl002(self):
        """Selection Sets: Delete Current"""
        cmb = self.sb.selection.cmb001
        name = cmb.currentText()

        pm.delete(name)

        self.cmb001()  # refresh the sets comboBox

    def lbl003(self):
        """Grow Selection"""
        pm.mel.GrowPolygonSelectionRegion()

    def lbl004(self):
        """Shrink Selection"""
        pm.mel.ShrinkPolygonSelectionRegion()

    def lbl005(self):
        """Selection Sets: Select Current"""
        cmb = self.sb.selection.cmb001
        name = cmb.currentText()

        if cmb.currentIndex() > 0:
            # Select The Selection Set Itself (Not Members Of) (noExpand=select set)
            pm.select(name)  # pm.select(name, noExpand=1)

    @SlotsMaya.hideMain
    def chk004(self, state=None):
        """Ignore Backfacing (Camera Based Selection)"""
        if self.selection_submenu_ui.chk004.isChecked():
            pm.selectPref(useDepth=True)
            self.sb.message_box(
                "Camera-based selection <hl>On</hl>.", message_type="Result"
            )
        else:
            pm.selectPref(useDepth=False)
            self.sb.message_box(
                "Camera-based selection <hl>Off</hl>.", message_type="Result"
            )

    def chk008(self, state=None):
        """Toggle Soft Selection"""
        if self.selection_submenu_ui.chk008.isChecked():
            pm.softSelect(edit=1, softSelectEnabled=True)
            self.sb.message_box("Soft Select <hl>On</hl>.", message_type="Result")
        else:
            pm.softSelect(edit=1, softSelectEnabled=False)
            self.sb.message_box("Soft Select <hl>Off</hl>.", message_type="Result")

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.selection.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "Polygon Selection Constraints":
                pm.mel.PolygonSelectionConstraints()
            cmb.setCurrentIndex(0)

    def cmb001(self, index=-1):
        """Selection Sets"""
        cmb = self.sb.selection.cmb001

        items = [str(s) for s in pm.ls(et="objectSet", flatten=1)]
        cmb.addItems_(items, clear=True)

    def cmb002(self, index=-1):
        """Select by Type"""
        cmb = self.sb.selection.cmb002

        if index > 0:
            text = cmb.items[index]
            if text == "IK Handles":  #
                type_ = pm.ls(type=["ikHandle", "hikEffector"])
            elif text == "Joints":  #
                type_ = pm.ls(type="joint")
            elif text == "Clusters":  #
                type_ = pm.listTransforms(type="clusterHandle")
            elif text == "Lattices":  #
                type_ = pm.listTransforms(type="lattice")
            elif text == "Sculpt Objects":  #
                type_ = pm.listTransforms(type=["implicitSphere", "sculpt"])
            elif text == "Wires":  #
                type_ = pm.ls(type="wire")
            elif text == "Transforms":  #
                type_ = pm.ls(type="transform")
            elif text == "Geometry":  # Select all Geometry
                geometry = pm.ls(geometry=True)
                type_ = pm.listRelatives(
                    geometry, p=True, path=True
                )  # pm.listTransforms(type='nRigid')
            elif text == "NURBS Curves":  #
                type_ = pm.listTransforms(type="nurbsCurve")
            elif text == "NURBS Surfaces":  #
                type_ = pm.ls(type="nurbsSurface")
            elif text == "Polygon Geometry":  #
                type_ = pm.listTransforms(type="mesh")
            elif text == "Cameras":  #
                type_ = pm.listTransforms(cameras=1)
            elif text == "Lights":  #
                type_ = pm.listTransforms(lights=1)
            elif text == "Image Planes":  #
                type_ = pm.ls(type="imagePlane")
            elif text == "Assets":  #
                type_ = pm.ls(type=["container", "dagContainer"])
            elif text == "Fluids":  #
                type_ = pm.listTransforms(type="fluidShape")
            elif text == "Particles":  #
                type_ = pm.listTransforms(type="particle")
            elif text == "Rigid Bodies":  #
                type_ = pm.listTransforms(type="rigidBody")
            elif text == "Rigid Constraints":  #
                type_ = pm.ls(type="rigidConstraint")
            elif text == "Brushes":  #
                type_ = pm.ls(type="brush")
            elif text == "Strokes":  #
                type_ = pm.listTransforms(type="stroke")
            elif text == "Dynamic Constraints":  #
                type_ = pm.listTransforms(type="dynamicConstraint")
            elif text == "Follicles":  #
                type_ = pm.listTransforms(type="follicle")
            elif text == "nCloths":  #
                type_ = pm.listTransforms(type="nCloth")
            elif text == "nParticles":  #
                type_ = pm.listTransforms(type="nParticle")
            elif text == "nRigids":  #
                type_ = pm.listTransforms(type="nRigid")

            pm.select(type_)
            cmb.setCurrentIndex(0)

    def cmb003(self, index=-1):
        """Convert To"""
        cmb = self.sb.selection.cmb003

        if index > 0:
            text = cmb.items[index]
            if text == "Verts":  # Convert Selection To Vertices
                pm.mel.PolySelectConvert(3)
            elif text == "Vertex Faces":  #
                pm.mel.PolySelectConvert(5)
            elif text == "Vertex Perimeter":  #
                pm.mel.ConvertSelectionToVertexPerimeter()
            elif text == "Edges":  # Convert Selection To Edges
                pm.mel.PolySelectConvert(2)
            elif text == "Edge Loop":  #
                pm.mel.polySelectSp(loop=1)
            elif text == "Edge Ring":  # Convert Selection To Edge Ring
                pm.mel.SelectEdgeRingSp()
            elif text == "Contained Edges":  #
                pm.mel.PolySelectConvert(20)
            elif text == "Edge Perimeter":  #
                pm.mel.ConvertSelectionToEdgePerimeter()
            elif text == "Border Edges":  #
                pm.select(self.getBorderEdgeFromFace())
            elif text == "Faces":  # Convert Selection To Faces
                pm.mel.PolySelectConvert(1)
            elif text == "Face Path":  #
                pm.mel.polySelectEdges("edgeRing")
            elif text == "Contained Faces":  #
                pm.mel.PolySelectConvert(10)
            elif text == "Face Perimeter":  #
                pm.mel.polySelectFacePerimeter()
            elif text == "UV's":  #
                pm.mel.PolySelectConvert(4)
            elif text == "UV Shell":  #
                pm.mel.polySelectBorderShell(0)
            elif text == "UV Shell Border":  #
                pm.mel.polySelectBorderShell(1)
            elif text == "UV Perimeter":  #
                pm.mel.ConvertSelectionToUVPerimeter()
            elif text == "UV Edge Loop":  #
                pm.mel.polySelectEdges("edgeUVLoopOrBorder")
            elif text == "Shell":  #
                pm.mel.polyConvertToShell()
            elif text == "Shell Border":  #
                pm.mel.polyConvertToShellBorder()
            cmb.setCurrentIndex(0)

    def cmb005(self, index=-1):
        """Selection Contraints"""
        cmb = self.sb.selection.cmb005

        if index > 0:
            text = cmb.items[index]
            if text == "Angle":
                pm.mel.dR_selConstraintAngle()  # dR_DoCmd("selConstraintAngle");
            elif text == "Border":
                pm.mel.dR_selConstraintBorder()  # dR_DoCmd("selConstraintBorder");
            elif text == "Edge Loop":
                pm.mel.dR_selConstraintEdgeLoop()  # dR_DoCmd("selConstraintEdgeLoop");
            elif text == "Edge Ring":
                pm.mel.dR_selConstraintEdgeRing()  # dR_DoCmd("selConstraintEdgeRing");
            elif text == "Shell":
                pm.mel.dR_selConstraintElement()  # dR_DoCmd("selConstraintElement");
            elif text == "UV Edge Loop":
                pm.mel.dR_selConstraintUVEdgeLoop()  # dR_DoCmd("selConstraintUVEdgeLoop");
        else:
            pm.mel.dR_selConstraintOff()  # dR_DoCmd("selConstraintOff");

    def cmb006(self, index=-1):
        """Currently Selected Objects"""
        cmb = self.sb.selection.draggableHeader.ctx_menu.cmb006

        cmb.clear()
        items = [str(i) for i in pm.ls(sl=1, flatten=1)]
        widgets = [
            cmb.option_menu.add("QCheckBox", setText=t, setChecked=1)
            for t in items[:50]
        ]  # selection list is capped with a slice at 50 elements.

        for w in widgets:
            try:
                w.disconnect()  # disconnect all previous connections.

            except TypeError:
                pass  # if no connections are present; pass
            w.toggled.connect(
                lambda state, widget=w: self.chkxxx(state=state, widget=widget)
            )

    def chkxxx(self, **kwargs):
        """Transform Constraints: Constraint CheckBoxes"""
        try:
            pm.select(kwargs["widget"].text(), deselect=(not kwargs["state"]))
        except KeyError:
            pass

    def tb000(self, state=None):
        """Select Nth"""
        tb = self.sb.selection.tb000

        edgeRing = tb.option_menu.chk000.isChecked()
        edgeLoop = tb.option_menu.chk001.isChecked()
        pathAlongLoop = tb.option_menu.chk009.isChecked()
        shortestPath = tb.option_menu.chk002.isChecked()
        borderEdges = tb.option_menu.chk010.isChecked()
        step = tb.option_menu.s003.value()

        selection = pm.ls(sl=1)
        if not selection:
            self.sb.message_box("Operation requires a valid selection.")
            return

        result = []
        if edgeRing:
            result = mtk.Cmpt.get_edge_path(selection, "edgeRing")

        elif edgeLoop:
            result = mtk.Cmpt.get_edge_path(selection, "edgeLoop")

        elif pathAlongLoop:
            result = mtk.Cmpt.get_edge_path(selection, "edgeLoopPath")

        elif shortestPath:
            result = mtk.Cmpt.get_shortest_path(selection)

        elif borderEdges:
            result = mtk.Cmpt.get_border_components(selection, "edges")

        pm.select(result[::step])

    def tb001(self, state=None):
        """Select Similar"""
        tb = self.sb.selection.tb001

        tolerance = tb.option_menu.s000.value()  # tolerance
        v = tb.option_menu.chk011.isChecked()  # vertex
        e = tb.option_menu.chk012.isChecked()  # edge
        f = tb.option_menu.chk013.isChecked()  # face
        t = tb.option_menu.chk014.isChecked()  # triangle
        s = tb.option_menu.chk015.isChecked()  # shell
        uv = tb.option_menu.chk016.isChecked()  # uvcoord
        a = tb.option_menu.chk017.isChecked()  # area
        wa = tb.option_menu.chk018.isChecked()  # world area
        b = tb.option_menu.chk019.isChecked()  # bounding box
        inc = tb.option_menu.chk020.isChecked()  # select the original objects

        objMode = pm.selectMode(query=1, object=1)
        if objMode:
            selection = pm.ls(sl=1, objectsOnly=1, type="transform")
            pm.select(clear=1)
            for obj in selection:
                similar = self.sb.edit.slots.get_similar_mesh(
                    obj,
                    tolerance=tolerance,
                    inc_orig=inc,
                    vertex=v,
                    edge=e,
                    face=f,
                    uvcoord=uv,
                    triangle=t,
                    shell=s,
                    boundingBox=b,
                    area=a,
                    worldArea=wa,
                )
                pm.select(similar, add=True)
        else:
            pm.mel.doSelectSimilar(1, {tolerance})

    def tb002(self, state=None):
        """Select Island: Select Polygon Face Island"""
        tb = self.sb.selection.tb002

        rangeX = float(tb.option_menu.s002.value())
        rangeY = float(tb.option_menu.s004.value())
        rangeZ = float(tb.option_menu.s005.value())

        sel = pm.ls(sl=1)
        selectedFaces = mtk.Cmpt.get_components(sel, component_type="faces")
        if not selectedFaces:
            self.sb.message_box("The operation requires a face selection.")
            return

        similarFaces = self.sb.normals.slots.getFacesWithSimilarNormals(
            selectedFaces, rangeX=rangeX, rangeY=rangeY, rangeZ=rangeZ
        )
        islands = mtk.Cmpt.get_contigious_islands(similarFaces)
        island = [i for i in islands if bool(set(i) & set(selectedFaces))]
        pm.select(island)

    def tb003(self, state=None):
        """Select Edges By Angle"""
        tb = self.sb.selection.tb003

        angleLow = tb.option_menu.s006.value()
        angleHigh = tb.option_menu.s007.value()

        objects = pm.ls(sl=1, objectsOnly=1)
        edges = mtk.get_edges_by_normal_angle(
            objects, low_angle=angleLow, high_angle=angleHigh
        )
        pm.select(edges)

        pm.selectMode(component=1)
        pm.selectType(edge=1)

    def b016(self):
        """Convert Selection To Vertices"""
        pm.mel.PolySelectConvert(3)

    def b017(self):
        """Convert Selection To Edges"""
        pm.mel.PolySelectConvert(2)

    def b018(self):
        """Convert Selection To Faces"""
        pm.mel.PolySelectConvert(1)

    def b019(self):
        """Convert Selection To Edge Ring"""
        pm.mel.SelectEdgeRingSp()

    @staticmethod
    def setSelectionStyle(ctx):
        """Set the selection style context.

        Parameters:
                ctx (str): Selection style context. valid: 'marquee', 'lasso', 'paint'.
        """
        ctx = ctx + "Context"
        if pm.contextInfo(ctx, exists=True):
            pm.deleteUI(ctx)

        if ctx == "marqueeContext":
            ctx = pm.selectContext(ctx)
        elif ctx == "lassoContext":
            ctx = pm.lassoContext(ctx)
        elif ctx == "paintContext":
            ctx = pm.artSelectCtx(ctx)

        pm.setToolTo(ctx)

    def generateUniqueSetName(self, obj=None):
        """Generate a generic name based on the object's name.

        Parameters:
                obj (str/obj/list): The maya scene object to derive a unique name from.

        <objectName>_Set<int>
        """
        if obj is None:
            obj = pm.ls(sl=1)
        num = ptk.cycle(list(range(99)), "selectionSetNum")
        name = "{0}_Set{1}".format(
            pm.ls(obj, objectsOnly=1, flatten=1)[0].name, num
        )  # ie. pCube1_Set0

        return name

    def creatNewSelectionSet(self, name=None):
        """Selection Sets: Create a new selection set."""
        if pm.objExists(name):
            self.sb.message_box(
                "Set with name <hl>{}</hl> already exists.".format(name)
            )
            return

        else:  # create set
            if not name:  # name=='set#Set': #generate a generic name based on obj.name
                name = self.generateUniqueSetName()

            pm.sets(name=name, text="gCharacterSet")

    def modifySet(self, name):
        """Selection Sets: Modify Current by renaming or changing the set members."""
        newName = self.sb.selection.cmb001.currentText()
        if not newName:
            newName = self.generateUniqueSetName()
        name = pm.rename(name, newName)

        if pm.objExists(name):
            pm.sets(name, clear=1)
            pm.sets(name, add=1)  # if set exists; clear set and add current selection


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
