# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Nurbs(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.nurbs
        self.submenu = self.sb.loaded_ui.nurbs_submenu

    def cmb001_init(self, widget):
        """ """
        items = [
            "Ep Curve Tool",
            "CV Curve Tool",
            "Bezier Curve Tool",
            "Pencil Curve Tool",
            "2 Point Circular Arc",
            "3 Point Circular Arc",
        ]
        widget.add(items, header="Create Curve")

    def tb000_init(self, widget):
        """ """
        widget.menu.add(
            "QSpinBox",
            setPrefix="Degree:",
            setObjectName="s002",
            setValue=3,
            set_limits=[0],
            setToolTip="The degree of the resulting surface.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Start Sweep:",
            setObjectName="s003",
            setValue=3,
            set_limits=[0, 360],
            setToolTip="    The value for the start sweep angle.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="End Sweep:",
            setObjectName="s004",
            setValue=3,
            set_limits=[0, 360],
            setToolTip="The value for the end sweep angle.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Sections:",
            setObjectName="s005",
            setValue=8,
            set_limits=[0],
            setToolTip="The number of surface spans between consecutive curves in the loft.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Range",
            setObjectName="chk006",
            setChecked=False,
            setToolTip="Force a curve range on complete input curve.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Polygon",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="The object created by this operation.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Auto Correct Normal",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Attempt to reverse the direction of the axis in case it is necessary to do so for the surface normals to end up pointing to the outside of the object.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Use Tolerance",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Use the tolerance, or the number of sections to control the sections.",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance:",
            setObjectName="s006",
            setValue=0.001,
            set_limits=[0],
            setToolTip="Tolerance to build to (if useTolerance attribute is set).",
        )

    def tb001_init(self, widget):
        """ """
        widget.menu.add(
            "QCheckBox",
            setText="Uniform",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="The resulting surface will have uniform parameterization in the loft direction. If set to false, the parameterization will be chord length.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Close",
            setObjectName="chk001",
            setChecked=False,
            setToolTip="The resulting surface will be closed (periodic) with the start (end) at the first curve. If set to false, the surface will remain open.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Degree:",
            setObjectName="s000",
            setValue=3,
            set_limits=[0],
            setToolTip="The degree of the resulting surface.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Auto Reverse",
            setObjectName="chk002",
            setChecked=False,
            setToolTip="The direction of the curves for the loft is computed automatically. If set to false, the values of the multi-use reverse flag are used instead.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Section Spans:",
            setObjectName="s001",
            setValue=1,
            set_limits=[0],
            setToolTip="The number of surface spans between consecutive curves in the loft.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Range",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="Force a curve range on complete input curve.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Polygon",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="The object created by this operation.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Reverse Surface Normals",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="The surface normals on the output NURBS surface will be reversed. This is accomplished by swapping the U and V parametric directions.",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Angle Loft Between Two Curves",
            setObjectName="chk010",
            setChecked=False,
            setToolTip="Perform a loft at an angle between two selected curves or polygon edges (that will be extracted as curves).",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Angle Loft: Spans:",
            setObjectName="s007",
            setValue=6,
            set_limits=[2],
            setToolTip="Angle loft: Number of duplicated points (spans).",
        )

    def cmb001(self, index, widget):
        """Create: Curve"""
        text = widget.items[index]
        if text == "Ep Curve Tool":
            pm.mel.eval("EPCurveToolOptions;")  # pm.mel.eval('EPCurveTool;')
        elif text == "CV Curve Tool":
            pm.mel.eval("CVCurveToolOptions")  # pm.mel.eval('CVCurveTool')
        elif text == "Bezier Curve Tool":
            pm.mel.eval(
                "CreateBezierCurveToolOptions"
            )  # pm.mel.eval('CreateBezierCurveTool;')
        elif text == "Pencil Curve Tool":
            pm.mel.eval("PencilCurveToolOptions;")  # pm.mel.eval('PencilCurveTool;')
        elif text == "2 Point Circular Arc":
            pm.mel.eval("TwoPointArcToolOptions;")  # pm.mel.eval("TwoPointArcTool;")
        elif text == "3 Point Circular Arc":
            pm.mel.eval(
                "ThreePointArcToolOptions;"
            )  # pm.mel.eval("ThreePointArcTool;")

    def tb000(self, widget):
        """Revolve"""
        degree = widget.menu.s002.value()
        startSweep = widget.menu.s003.value()
        endSweep = widget.menu.s004.value()
        sections = widget.menu.s005.value()
        range_ = widget.menu.chk006.isChecked()
        polygon = 1 if widget.menu.chk007.isChecked() else 0
        # autoCorrectNormal = widget.menu.chk008.isChecked()
        useTolerance = widget.menu.chk009.isChecked()
        tolerance = widget.menu.s006.value()

        curves = pm.ls(sl=True)
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

    def tb001(self, widget):
        """Loft"""
        uniform = widget.menu.chk000.isChecked()
        close = widget.menu.chk001.isChecked()
        degree = widget.menu.s000.value()
        autoReverse = widget.menu.chk002.isChecked()
        sectionSpans = widget.menu.s001.value()
        range_ = widget.menu.chk003.isChecked()
        polygon = 1 if widget.menu.chk004.isChecked() else 0
        reverseSurfaceNormals = widget.menu.chk005.isChecked()
        angleLoftBetweenTwoCurves = widget.menu.chk010.isChecked()
        angleLoftSpans = widget.menu.s007.value()

        self.loft(
            uniform=uniform,
            close=close,
            degree=degree,
            autoReverse=autoReverse,
            sectionSpans=sectionSpans,
            range_=range_,
            polygon=polygon,
            reverseSurfaceNormals=reverseSurfaceNormals,
            angleLoftBetweenTwoCurves=angleLoftBetweenTwoCurves,
            angleLoftSpans=angleLoftSpans,
        )

    def b012(self):
        """Project Curve"""
        pm.mel.ProjectCurveOnMesh()

    def b014(self):
        """Duplicate Curve"""
        pm.mel.DuplicateCurve()

    def b016(self):
        """Extract Curve"""
        try:
            pm.mel.CreateCurveFromPoly()
        except Exception:
            mtk.create_curve_from_edges()

    def b018(self):
        """Lock Curve"""
        pm.mel.LockCurveLength()

    def b019(self):
        """Unlock Curve"""
        pm.mel.UnlockCurveLength()

    def b020(self):
        """Bend Curve"""
        pm.mel.BendCurves()

    def b022(self):
        """Curl Curve"""
        pm.mel.CurlCurves()

    def b024(self):
        """Modify Curve Curvature"""
        pm.mel.ScaleCurvature()

    def b026(self):
        """Smooth Curve"""
        pm.mel.SmoothHairCurves()

    def b028(self):
        """Straighten Curve"""
        pm.mel.StraightenCurves()

    def b030(self):
        """Extrude"""
        pm.mel.Extrude()

    def b036(self):
        """Planar"""
        pm.mel.Planar()

    def b038(self):
        """Insert Isoparm"""
        pm.mel.InsertIsoparms()

    def b040(self):
        """Edit Curve Tool"""
        pm.mel.CurveEditTool()

    def b041(self):
        """Attach Curve"""
        pm.mel.AttachCurveOptions()

    def b042(self):
        """Detach Curve"""
        pm.mel.DetachCurve()

    def b043(self):
        """Extend Curve"""
        pm.mel.ExtendCurveOptions()

    def b045(self):
        """Cut Curve"""
        pm.mel.CutCurve()

    def b046(self):
        """Open/Close Curve"""
        pm.mel.OpenCloseCurve()

    def b047(self):
        """Insert Knot"""
        pm.mel.InsertKnot()

    def b049(self):
        """Add Points Tool"""
        pm.mel.AddPointsTool()

    def b051(self):
        """Reverse Curve"""
        pm.mel.ReverseCurve()

    def b052(self):
        """Extend Curve"""
        pm.mel.ExtendCurve()

    def b054(self):
        """Extend On Surface"""
        pm.mel.ExtendCurveOnSurface()


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
