# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)

import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Polygons_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draggableHeader_init(self, w):
        """ """
        w.ctx_menu.add(self.sb.ComboBox, setObjectName="cmb000", setToolTip="")

        cmb000 = w.ctx_menu.cmb000
        items = [
            "Extrude",
            "Bevel",
            "Bridge",
            "Combine",
            "Merge Vertex",
            "Offset Edgeloop",
            "Edit Edgeflow",
            "Extract Curve",
            "Poke",
            "Wedge",
            "Assign Invisible",
        ]
        cmb000.addItems_(items, "Polygon Editors")

    def tb000_init(self, w):
        """ """
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Distance: ",
            setObjectName="s002",
            set_limits="0.0000-10 step.0005",
            setValue=0.0005,
            set_height=20,
            setToolTip="Merge Distance.",
        )
        w.option_menu.add(
            "QPushButton",
            setText="Set Distance",
            setObjectName="b005",
            set_height=20,
            setToolTip="Set the distance using two selected vertices.\nElse; return the Distance to it's default value",
        )

    def tb001_init(self, w):
        """ """
        w.option_menu.add(
            "QSpinBox",
            setPrefix="Divisions: ",
            setObjectName="s003",
            set_limits="0-10000 step1",
            setValue=0,
            set_height=20,
            setToolTip="Subdivision Amount.",
        )

    def tb002_init(self, w):
        """ """
        w.option_menu.add(
            "QCheckBox",
            setText="Merge",
            setObjectName="chk000",
            setChecked=True,
            set_height=20,
            setToolTip="Combine selected meshes and merge any coincident verts/edges.",
        )

    def tb003_init(self, w):
        """ """
        w.option_menu.add(
            "QCheckBox",
            setText="Keep Faces Together",
            setObjectName="chk002",
            setChecked=True,
            set_height=20,
            setToolTip="Keep edges/faces together.",
        )
        w.option_menu.add(
            "QSpinBox",
            setPrefix="Divisions: ",
            setObjectName="s004",
            set_limits="1-10000 step1",
            setValue=1,
            set_height=20,
            setToolTip="Subdivision Amount.",
        )

    def tb004_init(self, w):
        """ """
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Width: ",
            setObjectName="s000",
            set_limits="0.00-100 step.05",
            setValue=0.25,
            set_height=20,
            setToolTip="Bevel Width.",
        )
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Segments: ",
            setObjectName="s006",
            set_limits="1-100 step1",
            setValue=1,
            set_height=20,
            setToolTip="Bevel Segments.",
        )

    def tb005_init(self, w):
        """ """
        w.option_menu.add(
            "QCheckBox",
            setText="Duplicate",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Duplicate any selected faces, leaving the originals.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Separate",
            setObjectName="chk015",
            setChecked=True,
            setToolTip="Separate mesh objects after detaching faces.",
        )
        # tb005.option_menu.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')

    def tb006_init(self, w):
        """ """
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="s001",
            set_limits="0.00-100 step.01",
            setValue=2.00,
            set_height=20,
            setToolTip="Offset amount.",
        )

    def tb007_init(self, w):
        """ """
        w.option_menu.add(
            "QCheckBox",
            setText="U",
            setObjectName="chk008",
            setChecked=True,
            set_height=20,
            setToolTip="Divide facet: U coordinate.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="V",
            setObjectName="chk009",
            setChecked=True,
            set_height=20,
            setToolTip="Divide facet: V coordinate.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Tris",
            setObjectName="chk010",
            set_height=20,
            setToolTip="Divide facet: Tris.",
        )

    def tb008_init(self, w):
        """ """
        w.option_menu.add(
            "QRadioButton",
            setText="Union",
            setObjectName="chk011",
            set_height=20,
            setToolTip="Fuse two objects together.",
        )
        w.option_menu.add(
            "QRadioButton",
            setText="Difference",
            setObjectName="chk012",
            setChecked=True,
            set_height=20,
            setToolTip="Indents one object with the shape of another at the point of their intersection.",
        )
        w.option_menu.add(
            "QRadioButton",
            setText="Intersection",
            setObjectName="chk013",
            set_height=20,
            setToolTip="Keep only the interaction point of two objects.",
        )

    def tb009_init(self, w):
        """ """
        w.option_menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s005",
            set_limits=".000-100 step.05",
            setValue=10,
            setToolTip="Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.",
        )
        w.option_menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Freeze Transformations on the object that is being snapped to.",
        )

    def chk008(self, state=None):
        """Divide Facet: Split U"""
        self.sb.toggle_widgets(setUnChecked="chk010")

    def chk009(self, state=None):
        """Divide Facet: Split V"""
        self.sb.toggle_widgets(setUnChecked="chk010")

    def chk010(self, state=None):
        """Divide Facet: Tris"""
        self.sb.toggle_widgets(setUnChecked="chk008,chk009")

    def setMergeVertexDistance(self, p1, p2):
        """Merge Vertices: Set Distance"""
        from pythontk import get_distance

        s = self.sb.polygons.tb000.option_menu.s002
        dist = get_distance(p1, p2)
        s.setValue(dist)

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.sb.polygons.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "Extrude":
                pm.mel.PolyExtrudeOptions()
            elif text == "Bevel":
                pm.mel.BevelPolygonOptions()
            elif text == "Bridge":
                pm.mel.BridgeEdgeOptions()
            elif text == "Combine":
                pm.mel.CombinePolygonsOptions()
            elif text == "Merge Vertex":
                pm.mel.PolyMergeOptions()
            elif text == "Offset Edgeloop":
                pm.mel.DuplicateEdgesOptions()
            elif text == "Edit Edgeflow":
                pm.mel.PolyEditEdgeFlowOptions()
            elif text == "Extract Curve":
                pm.mel.CreateCurveFromPolyOptions()
            elif text == "Poke":
                pm.mel.PokePolygonOptions()
            elif text == "Wedge":
                pm.mel.WedgePolygonOptions()
            elif text == "Assign Invisible":
                pm.mel.PolyAssignSubdivHoleOptions()
            cmb.setCurrentIndex(0)

    def tb000(self, state=None):
        """Merge Vertices"""
        tb = self.sb.polygons.tb000

        tolerance = float(tb.option_menu.s002.value())
        objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
        componentMode = pm.selectMode(query=1, component=1)

        if not objects:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object or vertex selection.",
                message_type="Error",
            )
            return

        mtk.Edit.merge_vertices(objects, selected=componentMode, tolerance=tolerance)

    @SlotsMaya.attr
    def tb001(self, state=None):
        """Bridge"""
        tb = self.sb.polygons.tb001

        divisions = tb.option_menu.s003.value()

        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection.",
                message_type="Error",
            )
        edges = pm.filterExpand(
            selection, selectionMask=32, expand=1
        )  # get edges from selection

        node = pm.polyBridgeEdge(edges, divisions=divisions)  # bridge edges
        pm.polyCloseBorder(edges)  # fill edges if they lie on a border
        return node

    def tb002(self, state=None):
        """Combine"""
        tb = self.sb.polygons.tb002

        if tb.option_menu.chk000.isChecked():
            sel = pm.ls(sl=1, objectsOnly=1)
            if not sel:
                return self.sb.message_box(
                    "<strong>Nothing selected</strong>.<br>Operation requires the selection of at least two objects.",
                    message_type="Error",
                )

            objName = sel[0].name()
            objParent = pm.listRelatives(objName, parent=1)
            # combine
            newObj = pm.polyUnite(ch=1, mergeUVSets=1, centerPivot=1)
            # rename using the first selected object
            pm.bakePartialHistory(objName, all=True)
            objName_ = pm.rename(newObj[0], objName)
            # reparent
            pm.parent(objName_, objParent)
        else:
            pm.mel.CombinePolygons()

    @SlotsMaya.attr
    def tb003(self, state=None):
        """Extrude"""
        tb = self.sb.polygons.tb003

        keepFacesTogether = (
            tb.option_menu.chk002.isChecked()
        )  # keep faces/edges together.
        divisions = tb.option_menu.s004.value()

        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection.",
                message_type="Error",
            )
        if pm.selectType(query=1, facet=1):  # face selection
            pm.polyExtrudeFacet(
                edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions
            )
            pm.mel.PolyExtrude()  # return pm.polyExtrudeFacet(selection, ch=1, keepFacesTogether=keepFacesTogether, divisions=divisions)

        elif pm.selectType(query=1, edge=1):  # edge selection
            pm.polyExtrudeEdge(
                edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions
            )
            pm.mel.PolyExtrude()  # return pm.polyExtrudeEdge(selection, ch=1, keepFacesTogether=keepFacesTogether, divisions=divisions)

        elif pm.selectType(query=1, vertex=1):  # vertex selection
            pm.polyExtrudeVertex(edit=1, width=0.5, length=1, divisions=divisions)
            pm.mel.PolyExtrude()  # return polyExtrudeVertex(selection, ch=1, width=0.5, length=1, divisions=divisions)

    @SlotsMaya.attr
    def tb004(self, state=None):
        """Bevel (Chamfer)"""
        tb = self.sb.polygons.tb004

        width = tb.option_menu.s000.value()
        chamfer = True
        segments = tb.option_menu.s006.value()

        selection = pm.ls(sl=1, objectsOnly=1, type="shape")
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection.",
                message_type="Error",
            )

        for obj in selection:
            edges = pm.ls(obj, sl=1)
            node = pm.polyBevel3(
                edges,
                fraction=width,
                offsetAsFraction=1,
                autoFit=1,
                depth=1,
                mitering=0,
                miterAlong=0,
                chamfer=chamfer,
                segments=segments,
                worldSpace=1,
                smoothingAngle=30,
                subdivideNgons=1,
                mergeVertices=1,
                mergeVertexTolerance=0.0001,
                miteringAngle=180,
                angleTolerance=180,
                ch=0,
            )
            if len(selection) == 1:
                return node

    def tb005(self, state=None):
        """Detach"""
        tb = self.sb.polygons.tb005

        duplicate = tb.option_menu.chk014.isChecked()
        separate = tb.option_menu.chk015.isChecked()

        vertexMask = pm.selectType(query=True, vertex=True)
        edgeMask = pm.selectType(query=True, edge=True)
        facetMask = pm.selectType(query=True, facet=True)

        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection.",
                message_type="Error",
            )

        if vertexMask:
            pm.mel.polySplitVertex()

        elif facetMask:
            extract = pm.polyChipOff(
                selection, ch=1, keepFacesTogether=1, dup=duplicate, off=0
            )
            if separate:
                try:
                    splitObjects = pm.polySeparate(selection)
                except Exception:
                    splitObjects = pm.polySeparate(pm.ls(selection, objectsOnly=1))
            pm.select(splitObjects[-1])
            return extract

        else:
            pm.mel.DetachComponent()

    @SlotsMaya.attr
    def tb006(self, state=None):
        """Inset Face Region"""
        tb = self.sb.polygons.tb006

        selected_faces = pm.polyEvaluate(faceComponent=1)
        # 'Nothing counted : no polygonal object is selected.'
        if isinstance(selected_faces, str):
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection.",
                message_type="Error",
            )
            return

        offset = float(tb.option_menu.s001.value())
        return pm.polyExtrudeFacet(
            selected_faces,
            keepFacesTogether=1,
            pvx=0,
            pvy=40.55638003,
            pvz=33.53797107,
            divisions=1,
            twist=0,
            taper=1,
            offset=offset,
            thickness=0,
            smoothingAngle=30,
        )

    def tb007(self, state=None):
        """Divide Facet"""
        tb = self.sb.polygons.tb007

        dv = u = v = 0
        if tb.option_menu.chk008.isChecked():  # Split U
            u = 2
        if tb.option_menu.chk009.isChecked():  # Split V
            v = 2

        mode = 0  # The subdivision mode. 0=quads, 1=triangles
        subdMethod = 1  # subdivision type: 0=exponential(traditional subdivision) 1=linear(number of faces per edge grows linearly)
        if tb.option_menu.chk010.isChecked():  # tris
            mode = dv = 1
            subdMethod = 0
        if all(
            [tb.option_menu.chk008.isChecked(), tb.option_menu.chk009.isChecked()]
        ):  # subdivide once into quads
            dv = 1
            subdMethod = 0
            u = v = 0
        # perform operation
        selectedFaces = pm.filterExpand(pm.ls(sl=1), selectionMask=34, expand=1)
        if selectedFaces:
            for (
                face
            ) in (
                selectedFaces
            ):  # when performing polySubdivideFacet on multiple faces, adjacent subdivided faces will make the next face an n-gon and therefore not able to be subdivided.
                pm.polySubdivideFacet(
                    face, divisions=0, divisionsU=2, divisionsV=2, mode=0, subdMethod=1
                )
        else:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection.",
                message_type="Error",
            )
            return

    def tb008(self, state=None):
        """Boolean Operation"""
        tb = self.sb.polygons.tb008

        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires the selection of at least two objects.",
                message_type="Error",
            )
        if tb.option_menu.chk011.isChecked():  # union
            pm.mel.PolygonBooleanIntersection()

        if tb.option_menu.chk012.isChecked():  # difference
            pm.mel.PolygonBooleanDifference()

        if tb.option_menu.chk013.isChecked():  # intersection
            pm.mel.PolygonBooleanIntersection()

    def tb009(self, state=None):
        """Snap Closest Verts"""
        tb = self.sb.polygons.tb009

        tolerance = tb.option_menu.s005.value()
        freezetransforms = tb.option_menu.chk016.isChecked()

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        if len(selection) > 1:
            obj1, obj2 = selection
            mtk.Edit.snap_closest_verts(obj1, obj2, tolerance, freezetransforms)
        else:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires at least two selected objects.",
                message_type="Error",
            )
            return

    @SlotsMaya.attr
    def b000(self):
        """Circularize"""
        circularize = pm.polyCircularize(
            constructionHistory=1,
            alignment=0,
            radialOffset=0,
            normalOffset=0,
            normalOrientation=0,
            smoothingAngle=30,
            evenlyDistribute=1,
            divisions=0,
            supportingEdges=0,
            twist=0,
            relaxInterior=1,
        )
        return circularize

    def b001(self):
        """Fill Holes"""
        pm.mel.FillHole()

    def b002(self):
        """Separate"""
        pm.mel.SeparatePolygon()
        sel = pm.ls(sl=1, objectsOnly=True)
        for obj in sel:
            pm.xform(obj, centerPivots=1)

    def b003(self):
        """Symmetrize"""
        pm.mel.Symmetrize()

    @SlotsMaya.attr
    def b004(self):
        """Slice"""
        cuttingDirection = "Y"  # valid values: 'x','y','z' A value of 'x' will cut the object along the YZ plane cutting through the center of the bounding box. 'y':ZX. 'z':XY.

        component_sel = pm.ls(sl=1)
        return pm.polyCut(component_sel, cuttingDirection=cuttingDirection, ch=1)

    def b005(self):
        """Merge Vertices: Set Distance"""
        verts = pm.ls(sl=1, flatten=1)

        try:
            p1 = pm.pointPosition(verts[0], world=True)
            p2 = pm.pointPosition(verts[1], world=True)
        except IndexError:
            p1, p2 = [
                (0.0005, 0, 0),
                (0, 0, 0),
            ]  # arbitrary points that will return the spinbox to it's default value of 0.0005.

        self.setMergeVertexDistance(p1, p2)

    def b006(self):
        """Merge Vertices: Merge All"""
        sel = pm.ls(sl=True, objectsOnly=True)
        mtk.Edit.merge_vertices(sel)

    def b009(self):
        """Collapse Component"""
        if pm.selectType(query=1, facet=1):
            pm.mel.PolygonCollapse()
        else:
            pm.mel.MergeToCenter()

    def b012(self):
        """Multi-Cut Tool"""
        pm.mel.dR_multiCutTool()

    def b021(self):
        """Connect Border Edges"""
        pm.mel.performPolyConnectBorders(0)

    def b022(self):
        """Attach"""
        # pm.mel.AttachComponent()
        pm.mel.dR_connectTool()

    def b028(self):
        """Quad Draw"""
        pm.mel.dR_quadDrawTool()

    def b032(self):
        """Poke"""
        pm.mel.PokePolygon()

    def b034(self):
        """Wedge"""
        pm.mel.WedgePolygon()

    def b038(self):
        """Assign Invisible"""
        pm.polyHole(assignHole=1)

    def b043(self):
        """Target Weld"""
        pm.mel.ConvertSelectionToVertices()
        pm.select(deselect=True)
        pm.mel.dR_targetWeldTool()

    def b045(self):
        """Re-Order Vertices"""
        symmetryOn = pm.symmetricModelling(
            query=True, symmetry=True
        )  # query symmetry state
        if symmetryOn:
            pm.symmetricModelling(symmetry=False)
        pm.mel.setPolygonDisplaySettings("vertIDs")  # set vertex id on
        pm.mel.doBakeNonDefHistory(1, "pre")  # history must be deleted
        pm.mel.performPolyReorderVertex()  # start vertex reorder ctx

    def b046(self):
        """Split"""
        vertexMask = pm.selectType(query=True, vertex=True)
        edgeMask = pm.selectType(query=True, edge=True)
        facetMask = pm.selectType(query=True, facet=True)

        if facetMask:
            pm.mel.performPolyPoke(1)

        elif edgeMask:
            pm.polySubdivideEdge(ws=0, s=0, dv=1, ch=0)

        elif vertexMask:
            pm.mel.polyChamferVtx(0, 0.25, 0)

    def b047(self):
        """Insert Edgeloop"""
        pm.mel.SplitEdgeRingTool()

    def b048(self):
        """Collapse Edgering"""
        pm.mel.bt_polyCollapseEdgeRingTool()

    def b049(self):
        """Slide Edge Tool"""
        pm.mel.SlideEdgeTool()

    def b050(self):
        """Spin Edge"""
        pm.mel.bt_polySpinEdgeTool()

    def b051(self):
        """Offset Edgeloop"""
        pm.mel.performPolyDuplicateEdge(0)

    def b053(self):
        """Edit Edge Flow"""
        pm.polyEditEdgeFlow(adjustEdgeFlow=1)


# --------------------------------------------------------------------------------------------


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated:

#   def tb005(self, state=None):
#       '''
#       Detach
#       '''
#       tb = self.sb.polygons.tb005
#       if state=='setMenu':
#           # tb.option_menu.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')
#           return

#       vertexMask = pm.selectType (query=True, vertex=True)
#       edgeMask = pm.selectType (query=True, edge=True)
#       facetMask = pm.selectType (query=True, facet=True)

#       if vertexMask:
#           pm.mel.eval("polySplitVertex()")

#       if facetMask:
#           maskVertex = pm.selectType (query=True, vertex=True)
#           if maskVertex:
#               pm.mel.eval("DetachComponent;")
#           else:
#               selFace = pm.ls(ni=1, sl=1)
#               selObj = pm.ls(objectsOnly=1, noIntermediate=1, sl=1) #to errorcheck if more than 1 obj selected

#               if len(selFace) < 1:
#                   return 'Error: Nothing selected.'

#               # if len(selObj) > 1:
#               #   return 'Error: Only components from a single object can be extracted.'

#               else:
#                   pm.mel.eval("DetachComponent;")
#                   # pm.undoInfo (openChunk=1)
#                   # sel = str(selFace[0]).split(".") #creates ex. ['polyShape', 'f[553]']
#                   # print(sel)
#                   # extractedObject = "extracted_"+sel[0]
#                   # pm.duplicate (sel[0], name=extractedObject)
#                   # if tb.option_menu.chk007.isChecked(): #delete original
#                   #   pm.delete (selFace)

#                   # allFace = [] #populate a list of all faces in the duplicated object
#                   # numFaces = pm.polyEvaluate(extractedObject, face=1)
#                   # num=0
#                   # for _ in range(numFaces):
#                   #   allFace.append(extractedObject+".f["+str(num)+"]")
#                   #   num+=1

#                   # extFace = [] #faces to keep
#                   # for face in selFace:
#                   #   fNum = str(face.split(".")[0]) #ex. f[4]
#                   #   extFace.append(extractedObject+"."+fNum)

#                   # delFace = [x for x in allFace if x not in extFace] #all faces not in extFace
#                   # pm.delete (delFace)

#                   # pm.select (extractedObject)
#                   # pm.xform (cpc=1) #center pivot
#                   # pm.undoInfo (closeChunk=1)
#                   # return extractedObject
