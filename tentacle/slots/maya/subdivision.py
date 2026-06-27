# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from tentacle.slots.maya._slots_maya import SlotsMaya


class Subdivision(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.subdivision
        self.submenu = self.sb.loaded_ui.subdivision_submenu

    def cmb001(self, index, widget):
        """Smooth Proxy"""
        text = widget.items[index]
        if text == "Create Subdiv Proxy":
            mel.eval("SmoothProxyOptions")
        elif text == "Remove Subdiv Proxy Mirror":
            mel.eval("UnmirrorSmoothProxyOptions")
        elif text == "Crease Tool":
            mel.eval("polyCreaseProperties")
        elif text == "Toggle Subdiv Proxy Display":
            mel.eval("SmoothingDisplayToggle")
        elif text == "Both Proxy and Subdiv Display":
            mel.eval("SmoothingDisplayShowBoth")

    def cmb002(self, index, widget):
        """Maya Subdivision Operations"""
        if index is widget.items.index("Reduce Polygons"):
            mel.eval("ReducePolygonOptions")
        elif index is widget.items.index("Add Divisions"):
            mel.eval("SubdividePolygonOptions")
        elif index is widget.items.index("Smooth"):
            mel.eval("performPolySmooth 1")

    def s000(self, value: int, widget: object) -> None:
        """Division Level"""
        shapes = cmds.ls(selection=True, dag=True, leaf=True) or []
        transforms = cmds.listRelatives(shapes, parent=True) or []
        for obj in transforms:
            if cmds.attributeQuery("smoothLevel", node=obj, exists=True):
                # Correctly pass attributes as keyword arguments
                mtk.Attributes.set_attributes(obj, smoothLevel=value)
                # SubDivision proxy options: 'divisions'
                cmds.optionVar(intValue=("proxyDivisions", value))
                cmds.inViewMessage(
                    statusMessage=f"{obj}: Division Level: <hl>{value}</hl>",
                    pos="topCenter",
                    fade=True,
                )

    def s001(self, value: int, widget: object) -> None:
        """Tesselation Level"""
        shapes = cmds.ls(selection=True, dag=True, leaf=True) or []
        transforms = cmds.listRelatives(shapes, parent=True) or []
        for obj in transforms:
            if cmds.attributeQuery("smoothLevel", node=obj, exists=True):
                # Correctly pass attributes as keyword arguments
                mtk.Attributes.set_attributes(obj, smoothTessLevel=value)
                cmds.inViewMessage(
                    statusMessage=f"{obj}: Tesselation Level: <hl>{value}</hl>",
                    pos="topCenter",
                    fade=True,
                )

    def b000(self):
        """Quadrangulate"""
        mel.eval("performPolyQuadrangulate 0")

    def b001(self):
        """Triangulate: split the selected faces into triangles."""
        mel.eval("polyTriangulate")

    def b005(self):
        """Reduce: lower the polygon count while preserving border, hard, crease, and UV edges."""
        selection = cmds.ls(sl=1, objectsOnly=1, type="transform") or []
        if not selection:
            return

        cmds.polyReduce(
            selection,
            ver=1,
            trm=0,
            shp=0,
            keepBorder=1,
            keepMapBorder=1,
            keepColorBorder=1,
            keepFaceGroupBorder=1,
            keepHardEdge=1,
            keepCreaseEdge=1,
            keepBorderWeight=0.5,
            keepMapBorderWeight=0.5,
            keepColorBorderWeight=0.5,
            keepFaceGroupBorderWeight=0.5,
            keepHardEdgeWeight=0.5,
            keepCreaseEdgeWeight=0.5,
            useVirtualSymmetry=0,
            symmetryTolerance=0.01,
            sx=0,
            sy=1,
            sz=0,
            sw=0,
            preserveTopology=1,
            keepQuadsWeight=1,
            vertexMapName="",
            cachingReduce=1,
            ch=1,
            p=50,
            vct=0,
            tct=0,
            replaceOriginal=1,
        )

    def tb000_init(self, widget):
        """Initialize Decimate"""
        menu = widget.option_box.menu
        menu.setTitle("Decimate")

        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip="Decimation algorithm.",
        )
        for text, data in [
            ("Reduce (Quadric Error %)", "qem"),
            ("Planar (Coplanar Dissolve)", "planar"),
        ]:
            cmb.addItem(text, data)

        # Reduce (quadric error metric) options.
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Reduce %: ",
            setObjectName="s010",
            set_limits=[0, 99, 1, 1],
            setValue=50.0,
            set_fixed_height=20,
            setToolTip="Percent of faces to remove (quadric-error polyReduce).",
        )
        menu.add("QCheckBox", setText="Preserve Borders", setObjectName="chk010",
                 setChecked=True, setToolTip="Hold open mesh and face-group borders fixed.")
        menu.add("QCheckBox", setText="Preserve Hard/Crease Edges", setObjectName="chk011",
                 setChecked=True, setToolTip="Hold hard and crease edges.")
        menu.add("QCheckBox", setText="Preserve UV Borders", setObjectName="chk012",
                 setChecked=True, setToolTip="Hold UV (map) and color borders.")
        menu.add("QCheckBox", setText="Preserve Quads", setObjectName="chk013",
                 setChecked=True, setToolTip="Bias the reduction toward keeping quads.")
        menu.add("QCheckBox", setText="Symmetry (X)", setObjectName="chk014",
                 setChecked=False, setToolTip="Reduce symmetrically about X (virtual symmetry).")

        # Planar (coplanar dissolve) options.
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Tolerance: ",
            setObjectName="s011",
            set_limits=[0, 180, 0.5, 1],
            setValue=1.0,
            set_fixed_height=20,
            setToolTip="Max dihedral angle (degrees) treated as coplanar. ~0 is lossless on hard-surface.",
        )

        # Grey out the options that don't apply to the chosen algorithm.
        qem_widgets = [menu.s010, menu.chk010, menu.chk011, menu.chk012, menu.chk013, menu.chk014]

        def _sync(*_):
            planar = menu.cmb000.currentData() == "planar"
            for w in qem_widgets:
                w.setEnabled(not planar)
            menu.s011.setEnabled(planar)

        menu.cmb000.currentIndexChanged.connect(_sync)
        _sync()

    def tb000(self, widget):
        """Decimate: reduce face count by quadric-error percentage or coplanar-face dissolve."""
        objects = cmds.ls(sl=True, objectsOnly=True, type="transform") or []
        if not objects:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Select one or more "
                "meshes to decimate."
            )
            return

        menu = widget.option_box.menu
        if menu.cmb000.currentData() == "planar":
            mtk.EditUtils.dissolve_coplanar(objects, angle_tolerance=menu.s011.value())
        else:
            mtk.EditUtils.decimate(
                objects,
                percentage=menu.s010.value(),
                preserve_borders=menu.chk010.isChecked(),
                preserve_hard_edges=menu.chk011.isChecked(),
                preserve_uv_borders=menu.chk012.isChecked(),
                preserve_quads=menu.chk013.isChecked(),
                symmetry=menu.chk014.isChecked(),
            )

    def b008(self):
        """Add Divisions - Subdivide Mesh"""
        mel.eval("SubdividePolygon")

    def b009(self):
        """Smooth"""
        mel.eval("SmoothPolygon")

    def b011(self):
        """Apply Smooth Preview"""
        mel.eval("performSmoothMeshPreviewToPolygon")

    def b028(self):
        """Quad Draw: enter Maya's Quad Draw retopology tool."""
        mel.eval("dR_quadDrawTool")

    @staticmethod
    def smoothProxy():
        """Subdiv Proxy"""
        global polySmoothBaseMesh
        polySmoothBaseMesh = []
        # disable creating seperate layers for subdiv proxy
        cmds.optionVar(intValue=("polySmoothLoInLayer", 0))
        cmds.optionVar(intValue=("polySmoothHiInLayer", 0))
        # query smooth proxy state.
        sel = mel.eval('polyCheckSelection "polySmoothProxy" "o" 0') or []

        if len(sel) == 0 and len(polySmoothBaseMesh) == 0:
            return "Error: Nothing selected."

        if len(sel) != 0:
            del polySmoothBaseMesh[:]
            for object_ in sel:
                polySmoothBaseMesh.append(object_)
        elif len(polySmoothBaseMesh) != 0:
            sel = polySmoothBaseMesh

        transform = cmds.listRelatives(sel[0], fullPath=1, parent=1) or []
        if not transform:
            return
        shape = cmds.listRelatives(transform[0], pa=1, shapes=1) or []
        if not shape:
            return

        # check shape for an existing output to a smoothProxy
        attachedSmoothProxies = cmds.listConnections(
            shape[0], type="polySmoothProxy", s=0, d=1
        ) or []
        if len(attachedSmoothProxies) != 0:  # subdiv off
            mel.eval("smoothingDisplayToggle 0")

        # toggle performSmoothProxy
        mel.eval("performSmoothProxy 0")  # toggle SubDiv Proxy


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
