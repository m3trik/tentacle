# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Polygons(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.polygons
        self.submenu = self.sb.polygons_submenu

    def chk008(self, state, widget):
        """Divide Facet: Split U"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk010")

    def chk009(self, state, widget):
        """Divide Facet: Split V"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk010")

    def chk010(self, state, widget):
        """Divide Facet: Tris"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk008,chk009")

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Distance: ",
            setObjectName="s002",
            set_limits=[0, 1000, 0.0001, 5],
            setValue=0.0005,
            set_height=20,
            setToolTip="Merge Distance.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Set Distance",
            setObjectName="b005",
            set_height=20,
            setToolTip="Set the distance using two selected vertices.\nElse; return the Distance to it's default value",
        )

    def tb000(self, widget):
        """Merge Vertices"""
        tolerance = widget.menu.s002.value()
        objects = pm.ls(sl=True, objectsOnly=1, flatten=1)
        componentMode = pm.selectMode(q=True, component=1)

        if not objects:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object or component selection."
            )
            return

        mtk.merge_vertices(objects, tolerance=tolerance, selected_only=componentMode)

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Linear",
            setObjectName="chk003",
            setChecked=True,
            set_height=20,
            setToolTip="Curve Type: Linear.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Blend",
            setObjectName="chk004",
            set_height=20,
            setToolTip="Curve Type: Blend.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Curve",
            setObjectName="chk005",
            set_height=20,
            setToolTip="Curve Type: Curve.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Divisions: ",
            setObjectName="s003",
            set_limits=[0],
            setValue=0,
            set_height=20,
            setToolTip="Subdivision Amount.",
        )

    def tb001(self, widget):
        """Bridge"""
        curve_type = (
            0
            if widget.menu.chk003.isChecked()
            else 1
            if widget.menu.chk004.isChecked()
            else 2
        )
        divisions = widget.menu.s003.value()

        selection = pm.ls(sl=1)
        edges = pm.filterExpand(selection, selectionMask=32, expand=1)
        if not edges:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a edge selection."
            )
        # Bridge the edges
        node = pm.polyBridgeEdge(edges, curveType=curve_type, divisions=divisions)
        # Fill edges if they lie on a border
        pm.polyCloseBorder(edges)
        return node

    def tb002_init(self, widget):
        # Remove 'Merge' and add 'Bake Partial History' option
        widget.menu.setTitle("COMBINE")
        widget.menu.add(
            "QCheckBox",
            setText="Bake Partial History",
            setObjectName="chk_bake_history",
            setChecked=True,
            set_height=20,
            setToolTip="Bake the construction history of the base mesh into its current state.",
        )
        # Add 'Center Pivot' option
        widget.menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk_center_pivot",
            setChecked=True,
            set_height=20,
            setToolTip="Center the pivot point of the combined mesh.",
        )

    def tb002(self, widget):
        """Combine"""
        # Get options from UI
        bake_history = widget.menu.chk_bake_history.isChecked()
        center_pivot = widget.menu.chk_center_pivot.isChecked()

        # Get ordered selection of objects
        sel = pm.ls(orderedSelection=True, objectsOnly=True)

        # Check if selection is valid
        if not sel or len(sel) < 2:
            return self.sb.message_box(
                "<strong>Insufficient selection</strong>.<br>Operation requires the selection of at least two objects."
            )

        # Get the name and parent of the first selected object
        base_mesh = sel[0]
        objName = base_mesh.name()
        objParent = pm.listRelatives(base_mesh, parent=True)

        # Combine meshes
        newObj = pm.polyUnite(sel, ch=True, mergeUVSets=True, centerPivot=center_pivot)

        # Optionally bake history
        if bake_history:
            pm.bakePartialHistory(base_mesh, all=True)

        # Rename the new object
        newObjRenamed = pm.rename(newObj[0], objName)

        # Reparent to the original parent of the first selected object
        if objParent:
            pm.parent(newObjRenamed, objParent[0])

        # Check for an existing isolation set and add the new object if one exists
        mtk.add_to_isolation_set(newObjRenamed)

    def tb003_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Keep Faces Together",
            setObjectName="chk002",
            setChecked=True,
            set_height=20,
            setToolTip="Keep edges/faces together.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Divisions: ",
            setObjectName="s004",
            set_limits=[0],
            setValue=1,
            set_height=20,
            setToolTip="Subdivision Amount.",
        )

    def tb003(self, widget):
        """Extrude"""
        keepFacesTogether = widget.menu.chk002.isChecked()
        divisions = widget.menu.s004.value()

        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection."
            )
        if pm.selectType(q=True, facet=1):  # face selection
            pm.polyExtrudeFacet(
                edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions
            )
            pm.mel.PolyExtrude()  # return pm.polyExtrudeFacet(selection, ch=1, keepFacesTogether=keepFacesTogether, divisions=divisions)

        elif pm.selectType(q=True, edge=1):  # edge selection
            pm.polyExtrudeEdge(
                edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions
            )
            pm.mel.PolyExtrude()  # return pm.polyExtrudeEdge(selection, ch=1, keepFacesTogether=keepFacesTogether, divisions=divisions)

        elif pm.selectType(q=True, vertex=1):  # vertex selection
            pm.polyExtrudeVertex(edit=1, width=0.5, length=1, divisions=divisions)
            pm.mel.PolyExtrude()  # return polyExtrudeVertex(selection, ch=1, width=0.5, length=1, divisions=divisions)

    def tb004(self, widget):
        """Bevel"""
        module = mtk.edit_utils.bevel_edges
        slot_class = module.BevelEdgesSlots

        self.sb.register("bevel_edges.ui", slot_class, base_dir=module)
        self.sb.bevel_edges.slots.preview.enable_on_show = True
        self.sb.parent().set_ui("bevel_edges")

    def tb005_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Duplicate Faces",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Duplicate any selected faces, leaving the originals.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Separate Objects",
            setObjectName="chk015",
            setChecked=True,
            setToolTip="Separate mesh objects after detaching faces.",
        )

    def tb005(self, widget):
        """Detach."""
        duplicate_faces = widget.menu.chk014.isChecked()
        separate_objects = widget.menu.chk015.isChecked()

        vertexMask = pm.selectType(q=True, vertex=True)
        facetMask = pm.selectType(q=True, facet=True)

        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection."
            )

        if vertexMask:
            pm.mel.polySplitVertex()
        elif facetMask:
            extract = pm.polyChipOff(
                selection,
                ch=True,
                keepFacesTogether=True,
                dup=duplicate_faces,
                off=True,
            )
            if separate_objects:
                try:
                    splitObjects = pm.polySeparate(selection)
                except Exception:
                    splitObjects = pm.polySeparate(pm.ls(selection, objectsOnly=True))
            pm.select(splitObjects[-1])
            return extract
        else:
            pm.mel.DetachComponent()

    def tb006_init(self, widget):
        """ """
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="s001",
            set_limits=[0, 100],
            setValue=2.00,
            set_height=20,
            setToolTip="Offset amount.",
        )

    def tb006(self, widget):
        """Inset Face Region"""
        selection = pm.ls(sl=True)
        selected_faces = pm.filterExpand(selection, selectionMask=34, expand=1)
        if not selected_faces:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection."
            )
            return

        offset = widget.menu.s001.value()
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

    def tb007_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="U",
            setObjectName="chk008",
            setChecked=True,
            set_height=20,
            setToolTip="Divide facet: U coordinate.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="V",
            setObjectName="chk009",
            setChecked=True,
            set_height=20,
            setToolTip="Divide facet: V coordinate.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Tris",
            setObjectName="chk010",
            set_height=20,
            setToolTip="Divide facet: Tris.",
        )

    def tb007(self, widget):
        """Divide Facet"""
        dv = u = v = 0
        if widget.menu.chk008.isChecked():  # Split U
            u = 2
        if widget.menu.chk009.isChecked():  # Split V
            v = 2

        mode = 0  # The subdivision mode. 0=quads, 1=triangles
        subdMethod = 1  # subdivision type: 0=exponential(traditional subdivision) 1=linear(number of faces per edge grows linearly)
        if widget.menu.chk010.isChecked():  # tris
            mode = dv = 1
            subdMethod = 0
        if all(
            (
                widget.menu.chk008.isChecked(),
                widget.menu.chk009.isChecked(),
            )
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
                    face,
                    divisions=dv,
                    divisionsU=u,
                    divisionsV=v,
                    mode=mode,
                    subdMethod=subdMethod,
                )
        else:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection."
            )
            return

    def tb008_init(self, widget):
        """ """
        widget.menu.add(
            "QRadioButton",
            setText="Union",
            setObjectName="chk011",
            set_height=20,
            setToolTip="Fuse two objects together.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Difference",
            setObjectName="chk012",
            setChecked=True,
            set_height=20,
            setToolTip="Indents one object with the shape of another at the point of their intersection.",
        )
        widget.menu.add(
            "QRadioButton",
            setText="Intersection",
            setObjectName="chk013",
            set_height=20,
            setToolTip="Keep only the interaction point of two objects.",
        )

    def tb008(self, widget):
        """Boolean Operation"""
        selection = pm.ls(sl=1)
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires the selection of at least two objects."
            )
        if widget.menu.chk011.isChecked():  # union
            pm.mel.PolygonBooleanIntersection()

        if widget.menu.chk012.isChecked():  # difference
            pm.mel.PolygonBooleanDifference()

        if widget.menu.chk013.isChecked():  # intersection
            pm.mel.PolygonBooleanIntersection()

    def tb009_init(self, widget):
        """ """
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s005",
            set_limits=[0, 100, 0.05, 3],
            setValue=10,
            setToolTip="Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Freeze Transformations on the object that is being snapped to.",
        )

    def tb009(self, widget):
        """Snap Closest Verts"""
        tolerance = widget.menu.s005.value()
        freezetransforms = widget.menu.chk016.isChecked()

        selection = pm.ls(sl=1, objectsOnly=1, type="transform")
        if len(selection) > 1:
            obj1, obj2 = selection
            mtk.snap_closest_verts(obj1, obj2, tolerance, freezetransforms)
        else:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires at least two selected objects."
            )
            return

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
            # Use Arbitrary points that will return the spinbox to it's default value of 0.0005
            p1, p2 = [(0.0005, 0, 0), (0, 0, 0)]

        self.setMergeVertexDistance(p1, p2)

    def b009(self):
        """Collapse Component"""
        if pm.selectType(q=True, facet=1):
            pm.mel.PolygonCollapse()
        else:
            was_edge_selected = pm.selectType(q=True, edge=True)
            pm.mel.MergeToCenter()
            if was_edge_selected:
                pm.selectType(edge=True)

    def b012(self):
        """Multi-Cut Tool"""
        pm.mel.dR_multiCutTool()

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
        try:
            pm.mel.WedgePolygon()
        except Exception:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Select faces and one or more edges from the selected faces to wedge about."
            )

    def b038(self):
        """Assign Invisible"""
        selection = pm.ls(sl=True)
        selected_faces = pm.filterExpand(selection, selectionMask=34, expand=1)
        if not selected_faces:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection."
            )
            return
        if not pm.polyHole(selected_faces, q=True, assignHole=True):
            pm.polyHole(selected_faces, assignHole=True)
        else:
            pm.polyHole(selected_faces, assignHole=False)

    def b043(self):
        """Target Weld"""
        pm.selectType(vertex=True)
        pm.select(deselect=True)
        pm.mel.dR_targetWeldTool()

    def b046(self):
        """Split"""
        vertexMask = pm.selectType(q=True, vertex=True)
        edgeMask = pm.selectType(q=True, edge=True)
        facetMask = pm.selectType(q=True, facet=True)

        if facetMask:
            pm.mel.performPolyPoke(1)

        elif edgeMask:
            pm.polySubdivideEdge(ws=0, s=0, dv=1, ch=0)

        elif vertexMask:
            pm.mel.polyChamferVtx(0, 0.25, 0)

    def b047(self):
        """Insert Edgeloop"""
        pm.mel.SplitEdgeRingTool()

    def b049(self):
        """Slide Edge Tool"""
        pm.mel.SlideEdgeTool()

    def b051(self):
        """Offset Edgeloop"""
        pm.mel.performPolyDuplicateEdge(0)

    def b053(self):
        """Edit Edge Flow"""
        pm.polyEditEdgeFlow(adjustEdgeFlow=1)

    def setMergeVertexDistance(self, p1, p2):
        """Merge Vertices: Set Distance"""
        spinbox = self.ui.tb000.menu.s002
        dist = ptk.get_distance(p1, p2)
        adjustment_factor = 1.01  # Add 1% to the distance
        dist *= adjustment_factor
        spinbox.setValue(dist)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
