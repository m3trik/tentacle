# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya._slots_maya import SlotsMaya


class Convert(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.get_ui("convert")
        self.submenu = self.sb.get_ui("convert#submenu")

    def cmb001_init(self, widget):
        """ """
        items = [
            "NURBS to Polygons",
            "NURBS to Subdiv",
            "Polygons to Subdiv",
            "Smooth Mesh Preview to Polygons",
            "Polygon Edges to Curve",
            "Type to Curves",
            "Subdiv to Polygons",
            "Subdiv to NURBS",
            "NURBS Curve to Bezier",
            "Bezier Curve to NURBS",
            "Paint Effects to NURBS",
            "Paint Effects to Curves",
            "Texture to Geometry",
            "Displacement to Polygons",
            "Displacement to Polygons with History",
            "Fluid to Polygons",
            "nParticle to Polygons",
            "Instance to Object",
            "Geometry to Bounding Box",
            "Convert XGen Primitives to Polygons",
        ]
        widget.add(items, header="Convert To")

    def cmb001(self, index, widget):
        """Convert To"""
        text = widget.items[index]
        if text == "NURBS to Polygons":  # index 1
            pm.mel.eval("performnurbsToPoly 0;")
        elif text == "NURBS to Subdiv":  # index 2
            pm.mel.eval("performSubdivCreate 0;")
        elif text == "Polygons to Subdiv":  # index 3
            pm.mel.eval("performSubdivCreate 0;")
        elif text == "Smooth Mesh Preview to Polygons":  # index 4
            pm.mel.eval("performSmoothMeshPreviewToPolygon;")
        elif text == "Polygon Edges to Curve":  # index 5
            pm.mel.eval("polyToCurve -form 2 -degree 3 -conformToSmoothMeshPreview 1;")
        elif text == "Type to Curves":  # index 6
            pm.mel.eval("convertTypeCapsToCurves;")
        elif text == "Subdiv to Polygons":  # index 7
            pm.mel.eval("performSubdivTessellate  false;")
        elif text == "Subdiv to NURBS":  # index 8
            pm.mel.eval("performSubdToNurbs 0;")
        elif text == "NURBS Curve to Bezier":  # index 9
            pm.mel.eval("nurbsCurveToBezier;")
        elif text == "Bezier Curve to NURBS":  # index 10
            pm.mel.eval("bezierCurveToNurbs;")
        elif text == "Paint Effects to NURBS":  # index 11
            pm.mel.eval("performPaintEffectsToNurbs  false;")
        elif text == "Paint Effects to Curves":  # index 12
            pm.mel.eval("performPaintEffectsToCurve  false;")
        elif text == "Texture to Geometry":  # index 13
            pm.mel.eval("performTextureToGeom 0;")
        elif text == "Displacement to Polygons":  # index 14
            pm.mel.eval("displacementToPoly;")
        elif text == "Displacement to Polygons with History":  # index 15
            pm.mel.eval("setupAnimatedDisplacement;")
        elif text == "Fluid to Polygons":  # index 16
            pm.mel.eval("fluidToPoly;")
        elif text == "nParticle to Polygons":  # index 17
            pm.mel.eval("particleToPoly;")
        elif text == "Instance to Object":  # index 18
            pm.mel.eval("convertInstanceToObject;")
        elif text == "Geometry to Bounding Box":  # index 19
            pm.mel.eval("performGeomToBBox 0;")
        elif text == "Convert XGen Primitives to Polygons":  # index 20
            import xgenm.xmaya.xgmConvertPrimToPolygon as cpp

            cpp.convertPrimToPolygon(False)

    def b000(self):
        """Polygon Edges to Curve"""
        self.sb.convert.cmb001.call_slot(4)

    def b001(self):
        """Instance to Object"""
        self.sb.convert.cmb001.call_slot(17)

    def b002(self):
        """NURBS to Polygons"""
        self.sb.convert.cmb001.call_slot(0)

    def b003(self):
        """Smooth Mesh Preview to Polygons"""
        self.sb.convert.cmb001.call_slot(3)


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
