# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
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
            pm.mel.SmoothProxyOptions()  # Add polygons to the selected proxy objects #performSmoothProxy 1;
        elif text == "Remove Subdiv Proxy Mirror":
            pm.mel.UnmirrorSmoothProxyOptions()  # Create a single low resolution mesh for a mirrored proxy setup #performUnmirrorSmoothProxy 1;
        elif text == "Crease Tool":
            pm.mel.polyCreaseProperties()  # Harden or soften the edges of a smooth mesh preview #polyCreaseValues polyCreaseContext;
        elif text == "Toggle Subdiv Proxy Display":
            pm.mel.SmoothingDisplayToggle()  # Toggle the display of smooth shapes #smoothingDisplayToggle 1;
        elif text == "Both Proxy and Subdiv Display":
            pm.mel.SmoothingDisplayShowBoth()  # Display both smooth shapes #smoothingDisplayToggle 0;

    def cmb002(self, index, widget):
        """Maya Subdivision Operations"""
        if index is widget.items.index("Reduce Polygons"):
            pm.mel.ReducePolygonOptions()
        elif index is widget.items.index("Add Divisions"):
            pm.mel.SubdividePolygonOptions()
        elif index is widget.items.index("Smooth"):
            pm.mel.performPolySmooth(1)

    def s000(self, value: int, widget: object) -> None:
        """Division Level"""
        shapes = pm.ls(selection=True, dag=True, leaf=True)
        transforms = pm.listRelatives(shapes, parent=True)
        for obj in transforms:
            if hasattr(obj, "smoothLevel"):
                # Correctly pass attributes as keyword arguments
                mtk.Attributes.set_attributes(obj, smoothLevel=value)
                # SubDivision proxy options: 'divisions'
                pm.optionVar(intValue=["proxyDivisions", value])
                pm.inViewMessage(
                    statusMessage=f"{obj}: Division Level: <hl>{value}</hl>",
                    pos="topCenter",
                    fade=True,
                )

    def s001(self, value: int, widget: object) -> None:
        """Tesselation Level"""
        shapes = pm.ls(selection=True, dag=True, leaf=True)
        transforms = pm.listRelatives(shapes, parent=True)
        for obj in transforms:
            if hasattr(obj, "smoothLevel"):
                # Correctly pass attributes as keyword arguments
                mtk.Attributes.set_attributes(obj, smoothTessLevel=value)
                pm.inViewMessage(
                    statusMessage=f"{obj}: Tesselation Level: <hl>{value}</hl>",
                    pos="topCenter",
                    fade=True,
                )

    def b000(self):
        """Quadrangulate"""
        pm.mel.performPolyQuadrangulate(0)

    def b001(self):
        """Triangulate"""
        pm.mel.polyTriangulate()

    def b005(self):
        """Reduce"""
        selection = pm.ls(sl=1, objectsOnly=1, type="transform")

        pm.polyReduce(
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

    def b008(self):
        """Add Divisions - Subdivide Mesh"""
        pm.mel.SubdividePolygon()

    def b009(self):
        """Smooth"""
        pm.mel.SmoothPolygon()

    def b011(self):
        """Apply Smooth Preview"""
        pm.mel.performSmoothMeshPreviewToPolygon()  # convert smooth mesh preview to polygons

    def b028(self):
        """Quad Draw"""
        pm.mel.dR_quadDrawTool()

    @staticmethod
    def smoothProxy():
        """Subdiv Proxy"""
        global polySmoothBaseMesh
        polySmoothBaseMesh = []
        # disable creating seperate layers for subdiv proxy
        pm.optionVar(intValue=["polySmoothLoInLayer", 0])
        pm.optionVar(intValue=["polySmoothHiInLayer", 0])
        # query smooth proxy state.
        sel = pm.mel.polyCheckSelection(
            "polySmoothProxy", "o", 0
        )  # pm.mel.eval("polyCheckSelection \"polySmoothProxy\" \"o\" 0")

        if len(sel) == 0 and len(polySmoothBaseMesh) == 0:
            return "Error: Nothing selected."

        if len(sel) != 0:
            del polySmoothBaseMesh[:]
            for object_ in sel:
                polySmoothBaseMesh.append(object_)
        elif len(polySmoothBaseMesh) != 0:
            sel = polySmoothBaseMesh

        transform = pm.listRelatives(sel[0], fullPath=1, parent=1)
        shape = pm.listRelatives(transform[0], pa=1, shapes=1)

        # check shape for an existing output to a smoothProxy
        attachedSmoothProxies = pm.listConnections(
            shape[0], type="polySmoothProxy", s=0, d=1
        )
        if len(attachedSmoothProxies) != 0:  # subdiv off
            pm.mel.smoothingDisplayToggle(0)

        # toggle performSmoothProxy
        pm.mel.performSmoothProxy(0)  # toggle SubDiv Proxy;


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
