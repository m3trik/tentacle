# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.nurbs import Nurbs


class Nurbs_max(Nurbs, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb000 = self.sb.nurbs.draggableHeader.ctx_menu.cmb000
        items = []
        cmb000.addItems_(items, "Curve Editors")

        cmb001 = self.sb.nurbs.cmb001
        items = []
        cmb001.addItems_(items, "Create Curve")

    def cmb000(self, *args, **kwargs):
        """Maya Curve Operations"""
        cmb = self.sb.nurbs.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "Project Curve":
                mel.eval("ProjectCurveOnSurfaceOptions;")
            elif text == "Duplicate Curve":
                mel.eval("DuplicateCurveOptions;")
            elif text == "Create Curve from Poly":
                mel.eval("CreateCurveFromPolyOptions")
            elif text == "Bend Curve":
                mel.eval("BendCurvesOptions;")
            elif text == "Curl Curve":
                mel.eval("CurlCurvesOptions;")
            elif text == "Modify Curve Curvature":
                mel.eval("ScaleCurvatureOptions;")
            elif text == "Smooth Curve":
                mel.eval("SmoothHairCurvesOptions;")
            elif text == "Straighten Curves":
                mel.eval("StraightenCurvesOptions;")
            elif text == "Extrude Curves":
                mel.eval("ExtrudeOptions;")
            elif text == "Revolve Curves":
                mel.eval("RevolveOptions;")
            elif text == "Loft Curves":
                mel.eval("LoftOptions;")
            elif text == "Planar Curves":
                mel.eval("PlanarOptions;")
            elif text == "Insert Isoparms":
                mel.eval("InsertIsoparmsOptions;")
            elif text == "Insert Knot":
                mel.eval("InsertKnotOptions;")
            elif text == "Rebuild Curve":
                mel.eval("RebuildCurveOptions;")
            elif text == "Extend Curve":
                mel.eval("ExtendCurveOptions;")
            elif text == "Extend Curve On Surface":
                mel.eval("ExtendCurveOnSurfaceOptions;")
            cmb.setCurrentIndex(0)

    def cmb001(self, *args, **kwargs):
        """Create: Curve"""
        cmb = self.sb.nurbs.cmb001

        if index > 0:
            text = cmb.items[index]
            if text == "Ep Curve Tool":
                mel.eval("EPCurveToolOptions;")  # mel.eval('EPCurveTool;')
            elif text == "CV Curve Tool":
                mel.eval("CVCurveToolOptions")  # mel.eval('CVCurveTool')
            elif text == "Bezier Curve Tool":
                mel.eval(
                    "CreateBezierCurveToolOptions"
                )  # mel.eval('CreateBezierCurveTool;')
            elif text == "Pencil Curve Tool":
                mel.eval("PencilCurveToolOptions;")  # mel.eval('PencilCurveTool;')
            elif text == "2 Point Circular Arc":
                mel.eval("TwoPointArcToolOptions;")  # mel.eval("TwoPointArcTool;")
            elif text == "3 Point Circular Arc":
                mel.eval("ThreePointArcToolOptions;")  # mel.eval("ThreePointArcTool;")
            cmb.setCurrentIndex(0)

    @SlotsMax.attr
    def tb000(self, *args, **kwargs):
        """Revolve"""
        tb = self.sb.nurbs.tb000

        degree = tb.option_menu.s002.value()
        startSweep = tb.option_menu.s003.value()
        endSweep = tb.option_menu.s004.value()
        sections = tb.option_menu.s005.value()
        range_ = tb.option_menu.chk006.isChecked()
        polygon = 1 if tb.option_menu.chk007.isChecked() else 0
        autoCorrectNormal = tb.option_menu.chk008.isChecked()
        useTolerance = tb.option_menu.chk009.isChecked()
        tolerance = tb.option_menu.s006.value()

        return pm.revolve(
            curves,
            po=polygon,
            rn=range_,
            ssw=startSweep,
            esw=endSweep,
            ut=useTolerance,
            tolerance=tolerance,
            degree=degree,
            s=sections,
            ulp=1,
            ax=[0, 1, 0],
        )

    @SlotsMax.attr
    def tb001(self, *args, **kwargs):
        """Loft"""
        tb = self.sb.nurbs.tb001

        uniform = tb.option_menu.chk000.isChecked()
        close = tb.option_menu.chk001.isChecked()
        degree = tb.option_menu.s000.value()
        autoReverse = tb.option_menu.chk002.isChecked()
        sectionSpans = tb.option_menu.s001.value()
        range_ = tb.option_menu.chk003.isChecked()
        polygon = 1 if tb.option_menu.chk004.isChecked() else 0
        reverseSurfaceNormals = tb.option_menu.chk005.isChecked()
        angleLoftBetweenTwoCurves = tb.option_menu.chk010.isChecked()
        angleLoftSpans = tb.option_menu.s007.value()

        if angleLoftBetweenTwoCurves:
            start, end = pm.ls(sl=1)[
                :2
            ]  # get the first two selected edge loops or curves.
            return SlotsMax.angleLoftBetweenTwoCurves(
                start,
                end,
                count=angleLoftSpans,
                cleanup=True,
                uniform=uniform,
                close=close,
                autoReverse=autoReverse,
                degree=degree,
                sectionSpans=sectionSpans,
                range=range_,
                polygon=polygon,
                reverseSurfaceNormals=reverseSurfaceNormals,
            )

        return pm.loft(
            curves,
            u=uniform,
            c=close,
            ar=autoReverse,
            d=degree,
            ss=sectionSpans,
            rn=range_,
            po=polygon,
            rsn=reverseSurfaceNormals,
        )

    def b012(self, *args, **kwargs):
        """Project Curve"""
        mel.eval("projectCurve;")  # ProjectCurveOnMesh;

    def b014(self, *args, **kwargs):
        """Duplicate Curve"""
        pm.mel.DuplicateCurve()

    def b016(self, *args, **kwargs):
        """Extract Curve"""
        pm.mel.CreateCurveFromPoly()

    def b018(self, *args, **kwargs):
        """Lock Curve"""
        pm.mel.LockCurveLength()

    def b019(self, *args, **kwargs):
        """Unlock Curve"""
        pm.mel.UnlockCurveLength()

    def b020(self, *args, **kwargs):
        """Bend Curve"""
        pm.mel.BendCurves()

    def b022(self, *args, **kwargs):
        """Curl Curve"""
        pm.mel.CurlCurves()

    def b024(self, *args, **kwargs):
        """Modify Curve Curvature"""
        pm.mel.ScaleCurvature()

    def b026(self, *args, **kwargs):
        """Smooth Curve"""
        pm.mel.SmoothHairCurves()

    def b028(self, *args, **kwargs):
        """Straighten Curve"""
        pm.mel.StraightenCurves()

    def b030(self, *args, **kwargs):
        """Extrude"""
        pm.mel.Extrude()

    def b036(self, *args, **kwargs):
        """Planar"""
        pm.mel.Planar()

    def b038(self, *args, **kwargs):
        """Insert Isoparm"""
        pm.mel.InsertIsoparms()

    def b040(self, *args, **kwargs):
        """Edit Curve Tool"""
        pm.mel.CurveEditTool()

    def b041(self, *args, **kwargs):
        """Attach Curve"""
        pm.mel.AttachCurveOptions()

    def b042(self, *args, **kwargs):
        """Detach Curve"""
        pm.mel.DetachCurve()

    def b043(self, *args, **kwargs):
        """Extend Curve"""
        pm.mel.ExtendCurveOptions()

    def b045(self, *args, **kwargs):
        """Cut Curve"""
        pm.mel.CutCurve()

    def b046(self, *args, **kwargs):
        """Open/Close Curve"""
        pm.mel.OpenCloseCurve()

    def b047(self, *args, **kwargs):
        """Insert Knot"""
        pm.mel.InsertKnot()

    def b049(self, *args, **kwargs):
        """Add Points Tool"""
        pm.mel.AddPointsTool()

    def b051(self, *args, **kwargs):
        """Reverse Curve"""
        mel.eval("reverse;")

    def b052(self, *args, **kwargs):
        """Extend Curve"""
        pm.mel.ExtendCurve()

    def b054(self, *args, **kwargs):
        """Extend On Surface"""
        pm.mel.ExtendCurveOnSurface()


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
