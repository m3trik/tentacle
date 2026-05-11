# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class PolygonsSlots(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.polygons
        self.submenu = self.sb.loaded_ui.polygons_submenu

    def header_init(self, widget):
        """Initialize Header"""
        widget.menu.add(
            "QPushButton",
            setText="Bridge Interactive",
            setObjectName="b007",
            setToolTip="Interactive bridge tool.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Bevel",
            setObjectName="b011",
            setToolTip="Open the bevel window.",
        )

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
        """Initialize Merge Vertices"""
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Distance: ",
            setObjectName="s002",
            set_limits=[0, 1000, 0.0001, 5],
            setValue=0.0005,
            set_fixed_height=20,
            setToolTip="Merge Distance.",
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Set Distance",
            setObjectName="b005",
            set_fixed_height=20,
            setToolTip="Set the distance using two selected vertices.\nElse; return the Distance to it's default value",
        )

    def tb000(self, widget):
        """Merge Vertices"""
        tolerance = widget.option_box.menu.s002.value()
        objects = cmds.ls(sl=True, objectsOnly=True, flatten=True) or []
        componentMode = cmds.selectMode(q=True, component=True)

        if not objects:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires an object or component selection."
            )
            return

        mtk.merge_vertices(objects, tolerance=tolerance, selected_only=componentMode)

    def tb002_init(self, widget):
        """Initialize Separate"""
        widget.option_box.menu.setTitle("Separate")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="By Material",
            setObjectName="chk021",
            setChecked=False,
            setToolTip=(
                "Split each mesh so every result has exactly one material, "
                "then parent the results under per-material groups (mirror of "
                "Combine → Group by Material). Children inherit the source "
                "object's name with a letter (A, B, …) or numeric suffix."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rename",
            setObjectName="chk022",
            setChecked=False,
            setToolTip=(
                "Rename resulting objects using the original name and a "
                "location-based suffix. Disabled while 'By Material' is on — "
                "the grouped path uses its own letter/number scheme."
            ),
        )

        # Rename is redundant whenever By Material drives the grouped naming.
        chk_by_material = widget.option_box.menu.chk021
        chk_rename = widget.option_box.menu.chk022
        chk_rename.setEnabled(not chk_by_material.isChecked())
        chk_by_material.toggled.connect(lambda on: chk_rename.setEnabled(not on))

    @mtk.undoable
    def tb002(self, widget):
        """Separate"""
        separate_by_material = widget.option_box.menu.chk021.isChecked()
        rename = widget.option_box.menu.chk022.isChecked()

        separated = mtk.separate_objects(
            by_material=separate_by_material,
            group_by_material=separate_by_material,
            center_pivots=True,
            rename=rename,
        )
        if separated:
            cmds.select(separated)

    def tb003_init(self, widget):
        """Initialize Extrude"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Keep Faces Together",
            setObjectName="chk002",
            setChecked=True,
            set_fixed_height=20,
            setToolTip="Keep edges/faces together.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Divisions: ",
            setObjectName="s004",
            set_limits=[0],
            setValue=1,
            set_fixed_height=20,
            setToolTip="Subdivision Amount.",
        )

    def tb003(self, widget):
        """Extrude"""
        keepFacesTogether = widget.option_box.menu.chk002.isChecked()
        divisions = widget.option_box.menu.s004.value()

        selection = cmds.ls(sl=1) or []
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection."
            )
        if cmds.selectType(q=True, facet=1):  # face selection
            cmds.polyExtrudeFacet(
                edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions
            )
            mel.eval("PolyExtrude")

        elif cmds.selectType(q=True, edge=1):  # edge selection
            cmds.polyExtrudeEdge(
                edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions
            )
            mel.eval("PolyExtrude")

        elif cmds.selectType(q=True, vertex=1):  # vertex selection
            cmds.polyExtrudeVertex(edit=1, width=0.5, length=1, divisions=divisions)
            mel.eval("PolyExtrude")

    def tb004_init(self, widget):
        """Initialize Combine"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Group by Material",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="Combine objects into groups based on their assigned materials.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Cluster by Distance",
            setObjectName="chk004",
            setChecked=False,
            setToolTip="Further subdivide material groups based on spatial proximity.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Threshold: ",
            setObjectName="s003",
            set_limits=[0, 100000, 1, 2],
            setValue=10000.0,
            setToolTip="Maximum distance between objects to be considered in the same cluster.",
        )

        # Connect signals
        chk_cluster = widget.option_box.menu.chk004
        spin_threshold = widget.option_box.menu.s003

        spin_threshold.setEnabled(chk_cluster.isChecked())
        chk_cluster.toggled.connect(spin_threshold.setEnabled)

    def tb004(self, widget):
        """Combine Selected Meshes."""
        group_by_material = widget.option_box.menu.chk003.isChecked()
        cluster_by_distance = widget.option_box.menu.chk004.isChecked()
        threshold = widget.option_box.menu.s003.value()

        selection = cmds.ls(sl=True) or []
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a selection."
            )

        mtk.EditUtils.combine_objects(
            selection,
            group_by_material=group_by_material,
            cluster_by_distance=cluster_by_distance,
            threshold=threshold,
        )

    def tb005_init(self, widget):
        """Initialize Detach"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Duplicate",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Duplicate the faces, leaving the original mesh unchanged.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Separate Extracted Faces",
            setObjectName="chk015",
            setChecked=True,
            setToolTip="Separate the extracted faces into new objects.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Separate Each Face",
            setObjectName="chk020",
            setChecked=False,
            setToolTip="If checked, each detached face becomes a separate object.",
        )

    def tb005(self, widget):
        """Detach."""
        duplicate = widget.option_box.menu.chk014.isChecked()
        separate = widget.option_box.menu.chk015.isChecked()
        separate_each = widget.option_box.menu.chk020.isChecked()

        selection = cmds.ls(sl=True) or []
        if not selection:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a component selection."
            )

        result = mtk.EditUtils.detach_components(
            selection,
            duplicate=duplicate,
            separate=separate,
            keep_faces_together=not separate_each,
        )
        cmds.selectMode(object=True)
        return result

    def tb006_init(self, widget):
        """Initialize Inset Face Region"""
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="s001",
            set_limits=[0, 100],
            setValue=2.00,
            set_fixed_height=20,
            setToolTip="Offset amount.",
        )

    def tb006(self, widget):
        """Inset Face Region"""
        selection = cmds.ls(sl=True) or []
        selected_faces = cmds.filterExpand(selection, selectionMask=34, expand=1)
        if not selected_faces:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection."
            )
            return

        offset = widget.option_box.menu.s001.value()
        return cmds.polyExtrudeFacet(
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
        """Initialize Divide Facet"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="U",
            setObjectName="chk008",
            setChecked=True,
            set_fixed_height=20,
            setToolTip="Divide facet: U coordinate.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="V",
            setObjectName="chk009",
            setChecked=True,
            set_fixed_height=20,
            setToolTip="Divide facet: V coordinate.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Tris",
            setObjectName="chk010",
            set_fixed_height=20,
            setToolTip="Divide facet: Tris.",
        )

    def tb007(self, widget):
        """Divide Facet"""
        dv = u = v = 0
        if widget.option_box.menu.chk008.isChecked():  # Split U
            u = 2
        if widget.option_box.menu.chk009.isChecked():  # Split V
            v = 2

        mode = 0  # The subdivision mode. 0=quads, 1=triangles
        subdMethod = 1  # subdivision type: 0=exponential(traditional subdivision) 1=linear(number of faces per edge grows linearly)
        if widget.option_box.menu.chk010.isChecked():  # tris
            mode = dv = 1
            subdMethod = 0
        if all(
            (
                widget.option_box.menu.chk008.isChecked(),
                widget.option_box.menu.chk009.isChecked(),
            )
        ):  # subdivide once into quads
            dv = 1
            subdMethod = 0
            u = v = 0
        # perform operation
        selectedFaces = cmds.filterExpand(cmds.ls(sl=1) or [], selectionMask=34, expand=1)
        if selectedFaces:
            for (
                face
            ) in (
                selectedFaces
            ):  # when performing polySubdivideFacet on multiple faces, adjacent subdivided faces will make the next face an n-gon and therefore not able to be subdivided.
                cmds.polySubdivideFacet(
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
        """Initialize Boolean Operation"""
        widget.option_box.menu.add(
            "QComboBox",
            addItems=["Union", "Difference", "Intersection"],
            setObjectName="cmb011",
            setCurrentText="Difference",
            set_fixed_height=20,
            setToolTip="Select the boolean operation to apply.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Interactive",
            setObjectName="chk017",
            set_fixed_height=20,
            setToolTip="Perform the operation using the interactive boolean tool.",
        )

    def tb008(self, widget):
        """Boolean Operation"""
        if not (cmds.ls(sl=True) or []):
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires the selection of at least two objects."
            )
        interactive = widget.option_box.menu.chk017.isChecked()
        mode = widget.option_box.menu.cmb011.currentText()

        if mode == "Union":
            if interactive:
                mel.eval("PolygonBooleanUnion")
            else:
                mtk.Macros.m_boolean(operation="union")
        elif mode == "Difference":
            if interactive:
                mel.eval("PolygonBooleanDifference")
            else:
                mtk.Macros.m_boolean(operation="difference")
        elif mode == "Intersection":
            if interactive:
                mel.eval("PolygonBooleanIntersection")
            else:
                mtk.Macros.m_boolean(operation="intersection")

    def tb009_init(self, widget):
        """Initialize Snap Closest Verts"""
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s005",
            set_limits=[0, 100, 0.05, 3],
            setValue=10,
            setToolTip="Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Freeze Transformations on the object that is being snapped to.",
        )

    def tb009(self, widget):
        """Snap Closest Verts"""
        tolerance = widget.option_box.menu.s005.value()
        freezetransforms = widget.option_box.menu.chk016.isChecked()

        selection = cmds.ls(sl=1, type="transform") or []
        if len(selection) > 1:
            obj1, obj2 = selection
            mtk.EditUtils.snap_closest_verts(
                obj1, obj2, tolerance, freezetransforms
            )
        else:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires at least two selected objects."
            )
            return

    def b000(self):
        """Circularize"""
        components = cmds.filterExpand(
            cmds.ls(sl=1) or [], selectionMask=(32, 34), expand=1
        )
        if not components:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face or border-edge selection."
            )
        if any(".e[" in c for c in components):
            return cmds.polyCircularizeEdge(components, ch=True)
        return cmds.polyCircularizeFace(components, ch=True)

    def b001(self):
        """Fill Holes"""
        mel.eval("FillHole")

    def b003(self):
        """Symmetrize"""
        mel.eval("Symmetrize")

    def b005(self):
        """Merge Vertices: Set Distance"""
        verts = cmds.ls(sl=1, flatten=1) or []
        try:
            p1, p2 = verts
        except ValueError:
            print(
                "Invalid selection: Operation requires exactly two vertices.\n\tUsing arbitrary points to set the distance to 0.0005"
            )
            p1, p2 = [(0.0005, 0, 0), (0, 0, 0)]

        dist = mtk.Components.adjusted_distance_between_vertices(
            p1, p2, adjust=0.1, as_percentage=True
        )
        spinbox = self.ui.tb000.option_box.menu.s002
        spinbox.setValue(dist)
        # Switch back to object mode
        cmds.selectMode(object=True)
        if verts:
            cmds.select(cmds.ls(verts, objectsOnly=True) or [])

    def b006(self, widget):
        """Bridge"""
        selection = cmds.ls(sl=1) or []
        edges = cmds.filterExpand(selection, selectionMask=32, expand=1)
        if not edges:
            return self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a edge selection."
            )
        try:  # Bridge the edges
            node = cmds.polyBridgeEdge(edges, curveType=0, divisions=0)
            if node:  # Fill edges if they lie on a border
                cmds.polyCloseBorder(edges)
        except RuntimeError:  # Bridge edges that share a vertex
            mtk.Components.bridge_connected_edges(edges)

    def b007(self):
        """Interactive Bridge"""
        self.sb.handlers.marking_menu.show("bridge")

    def b008(self):
        """Weld Center"""
        cmds.selectMode(component=True)
        cmds.selectType(vertex=True)
        cmds.select(deselect=True)
        cmds.targetWeldCtx("polyMergeVertexContext", edit=True, mergeToCenter=True)
        mel.eval("MergeVertexTool")

    def b009(self):
        """Collapse Component"""
        if cmds.selectType(q=True, facet=1):
            mel.eval("PolygonCollapse")
        else:
            was_edge_selected = cmds.selectType(q=True, edge=True)
            mel.eval("MergeToCenter")
            if was_edge_selected:
                cmds.selectType(edge=True)

    def b011(self):
        """Bevel"""
        self.sb.handlers.marking_menu.show("bevel")

    def b012(self):
        """Multi-Cut Tool"""
        mel.eval("dR_multiCutTool")

    def b022(self):
        """Attach"""
        mel.eval("dR_connectTool")

    def b032(self):
        """Poke"""
        mel.eval("PokePolygon")

    def b034(self):
        """Wedge"""
        try:
            mel.eval("WedgePolygon")
        except Exception:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Select faces and one or more edges from the selected faces to wedge about."
            )

    def b038(self):
        """Assign Invisible"""
        selection = cmds.ls(sl=True) or []
        selected_faces = cmds.filterExpand(selection, selectionMask=34, expand=1)
        if not selected_faces:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Operation requires a face selection."
            )
            return
        if not cmds.polyHole(selected_faces, q=True, assignHole=True):
            cmds.polyHole(selected_faces, assignHole=True)
        else:
            cmds.polyHole(selected_faces, assignHole=False)

    def b043(self):
        """Target Weld"""
        cmds.selectMode(component=True)
        cmds.selectType(vertex=True)
        cmds.select(deselect=True)
        cmds.targetWeldCtx("polyMergeVertexContext", edit=True, mergeToCenter=False)
        mel.eval("MergeVertexTool")

    def b047(self):
        """Insert Edgeloop"""
        mel.eval("SplitEdgeRingTool")

    def b049(self):
        """Slide Edge Tool"""
        mel.eval("SlideEdgeTool")

    def b051(self):
        """Offset Edgeloop"""
        mel.eval("performPolyDuplicateEdge 0")

    def b053(self):
        """Edit Edge Flow"""
        cmds.polyEditEdgeFlow(adjustEdgeFlow=1)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
