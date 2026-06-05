# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import pythontk as ptk
import mayatk as mtk
from uitk import Signals
from tentacle.slots.maya._slots_maya import SlotsMaya


class Nurbs(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.nurbs
        self.submenu = self.sb.loaded_ui.nurbs_submenu

    # --- Nurbs Expandable List ------------------------------------------

    # (category, label) -> MEL command. Each leaf click runs the MEL via
    # mel.eval so Maya's own configured tool/option settings are used.
    # Extrude / Revolve / Loft are intentionally excluded — those have
    # dedicated option-box buttons in the main window.
    _LIST000_COMMANDS = {
        "Create": [
            ("Project", "ProjectCurveOnMesh"),
            ("Extract", "CreateCurveFromPoly"),
            ("Duplicate", "DuplicateCurve"),
        ],
        "Modify": [
            ("Lock", "LockCurveLength"),
            ("Unlock", "UnlockCurveLength"),
            ("Bend", "BendCurves"),
            ("Curl", "CurlCurves"),
            ("Curvature", "ScaleCurvature"),
            ("Smooth", "SmoothHairCurves"),
            ("Straighten", "StraightenCurves"),
        ],
        "Surfaces": [
            ("Planar", "Planar"),
            ("Insert Isoparm", "InsertIsoparms"),
        ],
        "Edit": [
            ("Edit Curve Tool", "CurveEditTool"),
            ("Attach", "AttachCurveOptions"),
            ("Detach", "DetachCurve"),
            ("Cut", "CutCurve"),
            ("Open/Close", "OpenCloseCurve"),
            ("Insert Knot", "InsertKnot"),
            ("Add Points Tool", "AddPointsTool"),
            ("Rebuild", "RebuildCurveOptions"),
            ("Reverse", "ReverseCurve"),
            ("Extend (Options)", "ExtendCurveOptions"),
            ("Extend", "ExtendCurve"),
            ("Extend on Surface", "ExtendCurveOnSurface"),
        ],
    }

    def list000_init(self, widget):
        """Initialize Nurbs expandable list (categories → curve actions)."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay")

        root = widget.add("Nurbs")
        root.sublist.setMinimumWidth(widget.width() or 120)

        for category, items in self._LIST000_COMMANDS.items():
            cat = root.sublist.add(category)
            cat.sublist.add([label for label, _ in items])

    @Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch a Nurbs leaf action via mel.eval (uses Maya's stored settings)."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        parent = item.parent_item_text() or ""

        for label, command in self._LIST000_COMMANDS.get(parent, ()):
            if label == text:
                try:
                    mel.eval(command)
                except Exception as e:
                    cmds.warning(f"Nurbs '{text}' ({command}) failed: {e}")
                return

    def b056(self):
        """Image Tracer"""
        self.sb.handlers.marking_menu.show("image_tracer")

    def b058(self):
        """Curve to Tube"""
        self.sb.handlers.marking_menu.show("curve_to_tube")

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Degree:",
            setObjectName="s002",
            setValue=3,
            set_limits=[0],
            setToolTip="The degree of the resulting surface.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Start Sweep:",
            setObjectName="s003",
            setValue=3,
            set_limits=[0, 360],
            setToolTip="    The value for the start sweep angle.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="End Sweep:",
            setObjectName="s004",
            setValue=3,
            set_limits=[0, 360],
            setToolTip="The value for the end sweep angle.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Sections:",
            setObjectName="s005",
            setValue=8,
            set_limits=[0],
            setToolTip="The number of surface spans between consecutive curves in the loft.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Range",
            setObjectName="chk006",
            setChecked=False,
            setToolTip="Force a curve range on complete input curve.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Polygon",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="The object created by this operation.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Auto Correct Normal",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Attempt to reverse the direction of the axis in case it is necessary to do so for the surface normals to end up pointing to the outside of the object.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Use Tolerance",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Use the tolerance, or the number of sections to control the sections.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance:",
            setObjectName="s006",
            setValue=0.001,
            set_limits=[0],
            setToolTip="Tolerance to build to (if useTolerance attribute is set).",
        )

    def tb000(self, widget):
        """Revolve"""
        degree = widget.option_box.menu.s002.value()
        startSweep = widget.option_box.menu.s003.value()
        endSweep = widget.option_box.menu.s004.value()
        sections = widget.option_box.menu.s005.value()
        range_ = widget.option_box.menu.chk006.isChecked()
        polygon = 1 if widget.option_box.menu.chk007.isChecked() else 0
        # autoCorrectNormal = widget.option_box.menu.chk008.isChecked()
        useTolerance = widget.option_box.menu.chk009.isChecked()
        tolerance = widget.option_box.menu.s006.value()

        curves = cmds.ls(sl=True) or []
        return cmds.revolve(
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

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Uniform",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="The resulting surface will have uniform parameterization in the loft direction. If set to false, the parameterization will be chord length.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Close",
            setObjectName="chk001",
            setChecked=False,
            setToolTip="The resulting surface will be closed (periodic) with the start (end) at the first curve. If set to false, the surface will remain open.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Degree:",
            setObjectName="s000",
            setValue=3,
            set_limits=[0],
            setToolTip="The degree of the resulting surface.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Auto Reverse",
            setObjectName="chk002",
            setChecked=False,
            setToolTip="The direction of the curves for the loft is computed automatically. If set to false, the values of the multi-use reverse flag are used instead.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Section Spans:",
            setObjectName="s001",
            setValue=1,
            set_limits=[0],
            setToolTip="The number of surface spans between consecutive curves in the loft.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Range",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="Force a curve range on complete input curve.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Polygon",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="The object created by this operation.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reverse Surface Normals",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="The surface normals on the output NURBS surface will be reversed. This is accomplished by swapping the U and V parametric directions.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Angle Loft Between Two Curves",
            setObjectName="chk010",
            setChecked=False,
            setToolTip="Perform a loft at an angle between two selected curves or polygon edges (that will be extracted as curves).",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Angle Loft: Spans:",
            setObjectName="s007",
            setValue=6,
            set_limits=[2],
            setToolTip="Angle loft: Number of duplicated points (spans).",
        )

    def tb001(self, widget):
        """Loft"""
        uniform = widget.option_box.menu.chk000.isChecked()
        close = widget.option_box.menu.chk001.isChecked()
        degree = widget.option_box.menu.s000.value()
        autoReverse = widget.option_box.menu.chk002.isChecked()
        sectionSpans = widget.option_box.menu.s001.value()
        range_ = widget.option_box.menu.chk003.isChecked()
        polygon = 1 if widget.option_box.menu.chk004.isChecked() else 0
        reverseSurfaceNormals = widget.option_box.menu.chk005.isChecked()
        angle_loft_between_two_curves = widget.option_box.menu.chk010.isChecked()
        angleLoftSpans = widget.option_box.menu.s007.value()

        mtk.loft(
            uniform=uniform,
            close=close,
            degree=degree,
            autoReverse=autoReverse,
            sectionSpans=sectionSpans,
            range_=range_,
            polygon=polygon,
            reverseSurfaceNormals=reverseSurfaceNormals,
            angle_loft_between_two_curves=angle_loft_between_two_curves,
            angleLoftSpans=angleLoftSpans,
        )

    def b012(self):
        """Project Curve"""
        mel.eval("ProjectCurveOnMesh")

    def b014(self):
        """Duplicate Curve"""
        mel.eval("DuplicateCurve")

    def b016(self):
        """Extract Curve"""
        try:
            mel.eval("CreateCurveFromPoly")
        except Exception:
            mtk.create_curve_from_edges()

    def b018(self):
        """Lock Curve"""
        mel.eval("LockCurveLength")

    def b019(self):
        """Unlock Curve"""
        mel.eval("UnlockCurveLength")

    def b020(self):
        """Bend Curve"""
        mel.eval("BendCurves")

    def b022(self):
        """Curl Curve"""
        mel.eval("CurlCurves")

    def b024(self):
        """Modify Curve Curvature"""
        mel.eval("ScaleCurvature")

    def b026(self):
        """Smooth Curve"""
        mel.eval("SmoothHairCurves")

    def b028(self):
        """Straighten Curve"""
        mel.eval("StraightenCurves")

    def b030(self):
        """Extrude"""
        mel.eval("Extrude")

    def b036(self):
        """Planar"""
        mel.eval("Planar")

    def b038(self):
        """Insert Isoparm"""
        mel.eval("InsertIsoparms")

    def b040(self):
        """Edit Curve Tool"""
        mel.eval("CurveEditTool")

    def b041(self):
        """Attach Curve"""
        mel.eval("AttachCurveOptions")

    def b042(self):
        """Detach Curve"""
        mel.eval("DetachCurve")

    def b043(self):
        """Extend Curve"""
        mel.eval("ExtendCurveOptions")

    def b045(self):
        """Cut Curve"""
        mel.eval("CutCurve")

    def b046(self):
        """Open/Close Curve"""
        mel.eval("OpenCloseCurve")

    def b047(self):
        """Insert Knot"""
        mel.eval("InsertKnot")

    def b049(self):
        """Add Points Tool"""
        mel.eval("AddPointsTool")

    def b051(self):
        """Reverse Curve"""
        mel.eval("ReverseCurve")

    def b052(self):
        """Extend Curve"""
        mel.eval("ExtendCurve")

    def b054(self):
        """Extend On Surface"""
        mel.eval("ExtendCurveOnSurface")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
