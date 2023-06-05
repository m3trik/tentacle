# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Subdivision_maya(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def draggableHeader_init(self, widget):
        """ """
        cmb000 = widget.ctx_menu.add(
            self.sb.ComboBox,
            setObjectName="cmb000",
            setToolTip="Subdivision Editiors.",
        )
        items = ["Polygon Display Options"]
        cmb000.addItems_(items, "Subdivision Editiors")

        cmb001 = widget.ctx_menu.add(
            self.sb.ComboBox, setObjectName="cmb001", setToolTip="Smooth Proxy."
        )
        items = [
            "Create Subdiv Proxy",
            "Remove Subdiv Proxy Mirror",
            "Crease Tool",
            "Toggle Subdiv Proxy Display",
            "Both Proxy and Subdiv Display",
        ]
        cmb001.addItems_(items, "Smooth Proxy")

        cmb002 = widget.ctx_menu.add(
            self.sb.ComboBox,
            setObjectName="cmb002",
            setToolTip="Maya Subdivision Operations.",
        )
        items = ["Reduce Polygons", "Add Divisions", "Smooth"]
        cmb002.addItems_(items, "Maya Subdivision Operations")

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = kwargs.get('widget')
        index = kwargs.get('index')

        if index > 0:
            text = cmb.items[index]
            if text == "Polygon Display Options":
                pm.mel.CustomPolygonDisplayOptions()  # Polygon Display Options #pm.mel.eval("polysDisplaySetup 1;")
            cmb.setCurrentIndex(0)

    def cmb001(self, *args, **kwargs):
        """Smooth Proxy"""
        cmb = kwargs.get('widget')
        index = kwargs.get('index')

        if index > 0:
            text = cmb.items[index]
            if text == "Create Subdiv Proxy":
                pm.mel.SmoothProxyOptions()  #'Add polygons to the selected proxy objects.' #performSmoothProxy 1;
            elif text == "Remove Subdiv Proxy Mirror":
                pm.mel.UnmirrorSmoothProxyOptions()  #'Create a single low resolution mesh for a mirrored proxy setup.' #performUnmirrorSmoothProxy 1;
            elif text == "Crease Tool":
                pm.mel.polyCreaseProperties()  #'Harden or soften the edges of a smooth mesh preview.' #polyCreaseValues polyCreaseContext;
            elif text == "Toggle Subdiv Proxy Display":
                pm.mel.SmoothingDisplayToggle()  #'Toggle the display of smooth shapes.' #smoothingDisplayToggle 1;
            elif text == "Both Proxy and Subdiv Display":
                pm.mel.SmoothingDisplayShowBoth()  #'Display both smooth shapes' #smoothingDisplayToggle 0;
            cmb.setCurrentIndex(0)

    def cmb002(self, *args, **kwargs):
        """Maya Subdivision Operations"""
        cmb = kwargs.get('widget')
        index = kwargs.get('index')

        if index > 0:
            if index is cmb.items.index("Reduce Polygons"):
                pm.mel.ReducePolygonOptions()
            elif index is cmb.items.index("Add Divisions"):
                pm.mel.SubdividePolygonOptions()
            elif index is cmb.items.index("Smooth"):
                pm.mel.performPolySmooth(1)
            cmb.setCurrentIndex(0)

    def s000(self, *args, **kwargs):
        """Division Level"""
        value = kwargs.get('value')

        shapes = pm.ls(sl=1, dag=1, leaf=1)
        transforms = pm.listRelatives(shapes, p=True)
        for obj in transforms:
            if hasattr(obj, "smoothLevel"):
                mtk.Node.set_node_attributes(obj, {"smoothLevel": value})
                pm.optionVar(
                    intValue=["proxyDivisions", 1]
                )  # subDiv proxy options: 'divisions'
                print(obj + ": Division Level: <hl>" + str(value) + "</hl>")

    def s001(self, *args, **kwargs):
        """Tesselation Level"""
        value = kwargs.get('value')

        shapes = pm.ls(sl=1, dag=1, leaf=1)
        transforms = pm.listRelatives(shapes, p=True)
        for obj in transforms:
            if hasattr(obj, "smoothLevel"):
                mtk.Node.set_node_attributes(obj, {"smoothTessLevel": value})
                print(obj + ": Tesselation Level: <hl>" + str(value) + "</hl>")

    def b005(self, *args, **kwargs):
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

    def b008(self, *args, **kwargs):
        """Add Divisions - Subdivide Mesh"""
        pm.mel.SubdividePolygon()

    def b009(self, *args, **kwargs):
        """Smooth"""
        pm.mel.SmoothPolygon()

    def b011(self, *args, **kwargs):
        """Apply Smooth Preview"""
        pm.mel.performSmoothMeshPreviewToPolygon()  # convert smooth mesh preview to polygons

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


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
