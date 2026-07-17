# !/usr/bin/python
# coding=utf-8
import math

import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Nurbs(SlotsBlender):
    """Blender port of the shared ``nurbs`` menu. Blender is mesh-centric (no Maya-grade parametric
    NURBS surfacing), so the **operations** map onto mesh equivalents — Revolve onto a Screw
    modifier, Loft onto ``btk.loft`` (a bmesh bridge of the profile curves/loops), Curve-to-Tube
    onto curve ``bevel_depth`` — while the NURBS-surface-specific *parameters* (degree, uniform
    parameterization, tolerance, NURBS range, angle-loft) have no mesh analogue and are excused.
    ``list000`` (the Maya MEL curve-action dispatcher) is ported the same way: real Blender
    ops/props back every leaf that has a genuine equivalent (see ``_LIST000_COMMANDS``); only the
    parametric-NURBS-only leaves are excused, not the whole list.
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
            set_limits=[1, 256], setValue=8,
            setToolTip="Number of revolution segments (Screw steps).",
        )
        m.add(
            "QCheckBox", setText="Auto Correct Normal", setObjectName="chk008", setChecked=False,
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
            set_limits=[0], setValue=1,
            setToolTip="Interpolated rings inserted between consecutive profiles.",
        )
        m.add(
            "QCheckBox", setText="Reverse Surface Normals", setObjectName="chk005", setChecked=True,
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

    # ------------------------------------------------------------------ list000  Nurbs actions
    # (category, label) -> bound-method name; each leaf click resolves ``getattr(self, name)``
    # and calls it. Mirrors the shape of Maya's ``_LIST000_COMMANDS`` (category -> [(label, MEL
    # command)]), keyed to a Python method instead of a MEL string.
    #
    # Only leaves with a genuine Blender/mesh-curve equivalent are listed — the rest are omitted
    # from the tree (not silently: see the per-category note below) rather than hiding list000
    # wholesale:
    #   Create:   Project is ``_project_curve_on_mesh`` (Shrinkwrap-modifier wrap, added+applied —
    #             same reuse-a-modifier idiom as this file's own Revolve/tb000).
    #   Modify:   Lock / Unlock Curve Length have no Blender concept (a control point has no
    #             independent "locked arc length" constraint to toggle) — excused. Bend / Curl /
    #             Curvature / Straighten are parametric deformations Maya drives from its own
    #             option-box magnitude; Blender's nearest analogues (Simple Deform / lattice) are
    #             persistent modifiers needing that same kind of dedicated option UI as this
    #             file's tb000/tb001, not a parameterless one-click list action — excused
    #             (reviewer's call, same as the auditor flagged).
    #   Surfaces: Insert Isoparm is a parametric NURBS-surface-only concept — excused.
    #   Edit:     Insert Knot / Rebuild are parametric NURBS-curve re-parameterization — excused.
    #             Extend (Options) / Extend / Extend on Surface are tolerance-based parametric
    #             curve extension; no Blender op extends a curve by a tolerance/surface target —
    #             excused.
    _LIST000_COMMANDS = {
        "Create": [
            ("Project", "_project_curve_on_mesh"),
            ("Extract", "_extract_curve"),
            ("Duplicate", "_duplicate_curves"),
        ],
        "Modify": [
            ("Smooth", "_smooth_curve"),
        ],
        "Surfaces": [
            ("Planar", "_planar_fill"),
        ],
        "Edit": [
            ("Edit Curve Tool", "_edit_curve_tool"),
            ("Attach", "_attach_curves"),
            ("Detach", "_detach_curve"),
            ("Cut", "_cut_curve"),
            ("Open/Close", "_toggle_open_close"),
            ("Add Points Tool", "_add_points_tool"),
            ("Reverse", "_reverse_curve"),
        ],
    }

    def list000_init(self, widget):
        """Initialize the Nurbs expandable list (categories -> curve actions) — same
        root -> category -> leaf structure as Maya's ``list000_init``, backed by
        ``_LIST000_COMMANDS`` (bpy ops/props instead of MEL strings)."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_overlay")

        root = widget.add("Nurbs")

        for category, items in self._LIST000_COMMANDS.items():
            cat = root.sublist.add(category)
            cat.sublist.add([label for label, _ in items])

    # The undoable wrap sits on the leaf handlers below, not on this dispatcher, matching
    # edit.py's list000 (Create Primitive): the dispatcher also fires for category/expand
    # clicks, which would otherwise push no-op undo steps.
    @Signals("on_item_interacted")
    def list000(self, item):
        """Dispatch a Nurbs leaf action (mirrors Maya's list000: no-op on a node that still
        has its own populated sublist — i.e. a category, not a leaf — else resolve
        ``item_text()``/``parent_item_text()`` and call the mapped handler)."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        parent = item.parent_item_text() or ""

        for label, method_name in self._LIST000_COMMANDS.get(parent, ()):
            if label == text:
                try:
                    getattr(self, method_name)()
                except RuntimeError as e:
                    self.sb.message_box(f"Nurbs '{text}' failed: {e}")
                return

    # -- list000 leaf handlers (each @btk.undoable so its bpy.data + bpy.ops mix collapses
    # into a single Ctrl+Z step, same convention as this file's tb000/tb001/b058) ------------
    def _run_curve_edit_op(self, op, curves):
        """Run a curve-domain Edit-Mode operator (``switch_direction`` / ``cyclic_toggle`` /
        ``smooth``) against every control point of each of ``curves`` in turn, then restore
        Object Mode. Maya's MEL curve verbs act directly on the object; Blender's curve-domain
        ops only poll inside Edit Mode, so each curve is switched into Edit Mode with all its
        points selected for the call. Returns the number of curves the op ran on."""
        prior_active = bpy.context.view_layer.objects.active
        ran = 0
        for curve in curves:
            bpy.context.view_layer.objects.active = curve
            try:
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.curve.select_all(action="SELECT")
                op()
                ran += 1
            except RuntimeError as e:
                self.sb.message_box(str(e))
            finally:
                bpy.ops.object.mode_set(mode="OBJECT")
        if prior_active is not None:
            bpy.context.view_layer.objects.active = prior_active
        return ran

    @btk.undoable
    def _project_curve_on_mesh(self):
        """Project (Create): conform the selected curve(s) onto the first selected mesh by
        adding a Shrinkwrap modifier and immediately applying it (bakes the projected
        positions into the curve's own control points, verified live)."""
        curves = self._selected_curves()
        meshes = [o for o in self.selected_objects() if o.type == "MESH"]
        if not curves or not meshes:
            self.sb.message_box("Project requires curve(s) and a target mesh selected.")
            return
        target = meshes[0]
        for curve in curves:
            mod = curve.modifiers.new(name="Shrinkwrap", type="SHRINKWRAP")
            mod.target = target
            mod.wrap_method = "PROJECT"
            mod.use_project_z = True
            mod.use_negative_direction = True
            mod.use_positive_direction = True
            bpy.context.view_layer.objects.active = curve
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError as e:
                self.sb.message_box(str(e))

    @btk.undoable
    def _extract_curve(self):
        """Extract (Create): a curve built from the selected mesh's edges — duplicates the
        mesh(es) first (``object.convert`` replaces data in place) so the source poly is left
        intact, mirroring Maya's non-destructive ``CreateCurveFromPoly``."""
        meshes = [o for o in self.selected_objects() if o.type == "MESH"]
        if not meshes:
            self.sb.message_box("Extract requires selected mesh(es).")
            return
        for o in self.selected_objects():
            o.select_set(False)
        for m in meshes:
            dup = m.copy()
            dup.data = m.data.copy()
            for c in m.users_collection or [bpy.context.collection]:
                c.objects.link(dup)
            dup.select_set(True)
            bpy.context.view_layer.objects.active = dup
        try:
            bpy.ops.object.convert(target="CURVE")
        except RuntimeError as e:
            self.sb.message_box(str(e))

    @btk.undoable
    def _duplicate_curves(self):
        """Duplicate (Create): via ``btk.NurbsUtils.duplicate_curve`` (already shared by the
        curve tools in this package) rather than re-deriving an ``object.duplicate`` call."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Duplicate requires selected curve(s).")
            return
        dups = [btk.NurbsUtils.duplicate_curve(c) for c in curves]
        for o in self.selected_objects():
            o.select_set(False)
        for d in dups:
            d.select_set(True)
        bpy.context.view_layer.objects.active = dups[-1]

    @btk.undoable
    def _smooth_curve(self):
        """Smooth (Modify): ``curve.smooth`` over every selected curve's control points."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Smooth requires selected curve(s).")
            return
        self._run_curve_edit_op(bpy.ops.curve.smooth, curves)

    @btk.undoable
    def _planar_fill(self):
        """Planar (Surfaces): fill the selected curve(s) — Blender's ``fill_mode`` is a curve
        data property (2D dimensions required), not an operator (``bpy.ops.curve.fill`` does
        not exist — verified live), so this sets the property directly."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Planar requires selected curve(s).")
            return
        for c in curves:
            c.data.dimensions = "2D"
            c.data.fill_mode = "BOTH"

    @btk.undoable
    def _edit_curve_tool(self):
        """Edit Curve Tool (Edit): enter Edit Mode on the selected curve and activate the
        viewport Curve Pen tool (add/insert/move control points interactively) — the closest
        analogue of Maya's ``CurveEditTool``. Pen is EDIT_CURVE-only, so ``edit_type`` puts the
        curve into component mode first (bare, the tool fails to resolve)."""
        self.set_viewport_tool("builtin.pen", "Edit Curve Tool", edit_type="CURVE")

    @btk.undoable
    def _add_points_tool(self):
        """Add Points Tool (Edit): enter Edit Mode on the selected curve and activate the
        viewport Draw tool (extend a curve by drawing new points) — the closest analogue of
        Maya's ``AddPointsTool``. Draw is EDIT_CURVE-only (see :meth:`_edit_curve_tool`)."""
        self.set_viewport_tool("builtin.draw", "Add Points Tool", edit_type="CURVE")

    @btk.undoable
    def _attach_curves(self):
        """Attach (Edit): ``object.join`` the selected curves into the active one."""
        curves = self._selected_curves()
        if len(curves) < 2:
            self.sb.message_box("Attach requires 2+ selected curves.")
            return
        for o in self.selected_objects():
            o.select_set(o in curves)
        bpy.context.view_layer.objects.active = curves[0]
        try:
            bpy.ops.object.join()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    @btk.undoable
    def _detach_curve(self):
        """Detach (Edit): ``curve.separate`` the selected control point(s) into a new object.
        Unlike Reverse/Open-Close/Smooth this needs a specific point sub-selection (not "every
        point"), so it requires the curve already be in Edit Mode with points selected —
        checked first and explained via message_box rather than letting the operator's own
        poll() failure surface (same pattern this file already uses elsewhere)."""
        obj = bpy.context.view_layer.objects.active
        if not obj or obj.type != "CURVE" or obj.mode != "EDIT":
            self.sb.message_box(
                "Detach requires the curve in Edit Mode with the split point(s) selected."
            )
            return
        try:
            bpy.ops.curve.separate()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    @btk.undoable
    def _cut_curve(self):
        """Cut (Edit): ``curve.split`` at the selected control point(s) — same Edit-Mode
        precondition as Detach (a specific point selection, not "every point")."""
        obj = bpy.context.view_layer.objects.active
        if not obj or obj.type != "CURVE" or obj.mode != "EDIT":
            self.sb.message_box(
                "Cut requires the curve in Edit Mode with the cut point(s) selected."
            )
            return
        try:
            bpy.ops.curve.split()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    @btk.undoable
    def _toggle_open_close(self):
        """Open/Close (Edit): ``curve.cyclic_toggle`` over every selected curve."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Open/Close requires selected curve(s).")
            return
        self._run_curve_edit_op(bpy.ops.curve.cyclic_toggle, curves)

    @btk.undoable
    def _reverse_curve(self):
        """Reverse (Edit): ``curve.switch_direction`` over every selected curve."""
        curves = self._selected_curves()
        if not curves:
            self.sb.message_box("Reverse requires selected curve(s).")
            return
        self._run_curve_edit_op(bpy.ops.curve.switch_direction, curves)

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
