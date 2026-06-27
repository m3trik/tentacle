# !/usr/bin/python
# coding=utf-8
import math

import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Nurbs(SlotsBlender):
    """Blender port of the shared ``nurbs`` menu. Blender is mesh-centric (no Maya-grade parametric
    NURBS surfacing), so the **operations** map onto mesh equivalents — Revolve onto a Screw
    modifier, Loft onto ``btk.loft`` (a bmesh bridge of the profile curves/loops), Curve-to-Tube
    onto curve ``bevel_depth`` — while the NURBS-surface-specific *parameters* (degree, uniform
    parameterization, tolerance, NURBS range, angle-loft) have no mesh analogue and are excused.
    The mel-dispatcher curve-action list is hidden (Maya-MEL-only).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def _selected_curves(self):
        return [o for o in self.selected_objects() if o.type == "CURVE"]

    # ------------------------------------------------------------------ clean maps
    @btk.undoable
    def b058(self):
        """Curve to Tube (curve bevel)."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Curve to Tube requires selected curve(s).")
            return
        for c in curves:
            c.data.bevel_depth = c.data.bevel_depth or 0.1
            c.data.use_fill_caps = True

    # Revolve = Screw modifier. s003/s004/s005/chk008 reuse the Maya names + labels for the SAME
    # options (sweep range / sections / auto-correct-normal). The NURBS-surface params (degree /
    # range / polygon-output / tolerance) describe a parametric surface the Screw mesh doesn't have
    # and are excused. cmb_screw_axis is a Blender enhancement (Maya hardcodes the Y axis).
    def tb000_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Revolve")
        m.add(
            "QComboBox", addItems=["Y", "Z", "X"], setObjectName="cmb_screw_axis",
            setToolTip="Axis to revolve about (Maya revolves about Y).",
        )
        m.add(
            "QSpinBox", setPrefix="Start Sweep:", setObjectName="s003",
            set_limits=[0, 360], setValue=0,
            setToolTip="Start angle of the swept arc (degrees).",
        )
        m.add(
            "QSpinBox", setPrefix="End Sweep:", setObjectName="s004",
            set_limits=[0, 360], setValue=360,
            setToolTip="End angle of the swept arc (degrees). The Screw sweeps End − Start.",
        )
        m.add(
            "QSpinBox", setPrefix="Sections:", setObjectName="s005",
            set_limits=[1, 256], setValue=16,
            setToolTip="Number of revolution segments (Screw steps).",
        )
        m.add(
            "QCheckBox", setText="Auto Correct Normal", setObjectName="chk008", setChecked=True,
            setToolTip="Let the Screw modifier recalculate a consistent normal order.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Revolve (Screw modifier; reuses an existing Screw modifier instead of stacking)."""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Revolve requires a selection.")
            return
        m = widget.option_box.menu
        angle = math.radians(m.s004.value() - m.s003.value())
        for o in objects:
            if o.type not in ("MESH", "CURVE"):
                continue
            mod = next((x for x in o.modifiers if x.type == "SCREW"), None)
            if mod is None:
                mod = o.modifiers.new(name="Screw", type="SCREW")
            mod.axis = m.cmb_screw_axis.currentText()
            mod.angle = angle
            mod.steps = mod.render_steps = m.s005.value()
            mod.use_normal_calculate = m.chk008.isChecked()

    # Loft = btk.loft (bmesh bridge of profile curves/loops). chk001/chk005/s001 reuse the Maya
    # names for the SAME options (close / reverse normals / section spans). The NURBS-surface params
    # (uniform parameterization / degree / auto-reverse / range / polygon-output / angle-loft) are
    # excused — the result is a mesh, not a parametric NURBS surface.
    def tb001_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Loft")
        m.add(
            "QCheckBox", setText="Close", setObjectName="chk001", setChecked=False,
            setToolTip="Bridge the last profile back to the first (periodic in the loft direction).",
        )
        m.add(
            "QSpinBox", setPrefix="Section Spans:", setObjectName="s001",
            set_limits=[1, 100], setValue=1,
            setToolTip="Interpolated rings inserted between consecutive profiles.",
        )
        m.add(
            "QCheckBox", setText="Reverse Surface Normals", setObjectName="chk005", setChecked=False,
            setToolTip="Flip the winding (normals) of the lofted surface.",
        )

    @btk.undoable
    def tb001(self, widget):
        """Loft — bridge the selected profile curves / mesh loops into a surface (btk.loft)."""
        m = widget.option_box.menu
        result = btk.loft(
            self.selected_objects(),
            close=m.chk001.isChecked(),
            reverse_normals=m.chk005.isChecked(),
            section_spans=m.s001.value(),
        )
        if result is None:
            self.sb.message_box(
                "<strong>Loft needs 2+ profiles</strong>.<br>Select two or more curve objects "
                "(or meshes) to loft a surface across."
            )

    # ------------------------------------------------------------------ hidden / deferred
    def list000_init(self, widget):
        """Maya NURBS action list (mel dispatcher) — hidden; no Blender analogue."""
        widget.setVisible(False)

    def b030(self):
        """Extrude — use mesh/curve extrude in Edit Mode (E)."""
        self.sb.message_box("Use Extrude (E) in Edit Mode.")

    def b056(self):
        """Image Tracer (native wrap: trace the active image-empty to Grease Pencil,
        otherwise import an SVG as curves)."""
        obj = bpy.context.view_layer.objects.active
        if obj and obj.type == "EMPTY" and obj.empty_display_type == "IMAGE":
            # GPv3 renamed the op; resolve whichever this Blender ships.
            op_path = next(
                (
                    p
                    for p in ("grease_pencil.trace_image", "gpencil.trace_image")
                    if self.resolve_op(p)
                ),
                "grease_pencil.trace_image",
            )
            self.invoke_op(op_path)
        else:
            self.invoke_op("import_curve.svg")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
