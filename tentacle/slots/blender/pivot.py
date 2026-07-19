# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Pivot(SlotsBlender):
    """Blender port of the shared ``pivot`` menu.

    Blender has a single object **origin** (no separate manipulator pivot, no per-channel
    translate/rotate/scale pivots, and origins are always baked into the transform). So the
    Center-Pivot family maps cleanly onto ``blendertk.center_pivot`` (``bpy.ops.object.origin_set``),
    while Transfer Pivot's per-channel (rotate/scale) granularity has no analogue. Both halves
    of World-Aligned Pivot (tb003) map for full Maya parity: the *temporary manipulator* default
    onto Blender's Global transform orientation (a gizmo-orientation switch, non-destructive),
    the *permanent object* option onto baking the object's rotation into its data
    (``object.transform_apply``). Bake Pivot (b004) bakes Blender's temporary pivot — the 3D
    cursor — into the origin (``origin_set(ORIGIN_CURSOR)``, geometry unmoved), mirroring Maya's
    "make the pivot you placed permanent" intent.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.pivot
        self.submenu = self.sb.loaded_ui.pivot_submenu

    # ------------------------------------------------------------------ tb000  Reset Pivot
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Reset Pivot")
        widget.option_box.menu.add(
            "QCheckBox", setText="Reset Pivot Position", setObjectName="chk000",
            setChecked=True,
            setToolTip="Move the object origin to its geometry bounding-box center.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Reset Pivot"""
        if not widget.option_box.menu.chk000.isChecked():
            return
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Reset Pivot requires a selection.")
            return
        btk.center_pivot(objects, mode="object")
        self.sb.message_box(
            f"Reset Pivot Position for <hl>{len(objects)}</hl> object(s)."
        )

    # ------------------------------------------------------------------ tb001  Center Pivot
    def tb001_init(self, widget):
        widget.option_box.menu.setTitle("Center Pivot")
        widget.option_box.menu.add(
            "QRadioButton", setText="Component", setObjectName="chk002",
            setToolTip="Origin to the geometry median of the selected objects.",
        )
        widget.option_box.menu.add(
            "QRadioButton", setText="Object", setObjectName="chk003", setChecked=True,
            setToolTip="Origin to the object's bounding-box center.",
        )
        widget.option_box.menu.add(
            "QRadioButton", setText="World", setObjectName="chk004",
            setToolTip="Origin to the world origin (0,0,0).",
        )

    @btk.undoable
    def tb001(self, widget):
        """Center Pivot"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Center Pivot requires a selection.")
            return
        m = widget.option_box.menu
        mode = (
            "median" if m.chk002.isChecked()
            else "world" if m.chk004.isChecked()
            else "object"
        )
        btk.center_pivot(objects, mode=mode)

    # ------------------------------------------------------------------ b000/b001/b002 shortcuts
    def b000(self):
        """Center Pivot: Object"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk003.setChecked(True)
        self.ui.tb001.call_slot()

    def b001(self):
        """Center Pivot: Component"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk002.setChecked(True)
        self.ui.tb001.call_slot()

    def b002(self, widget):
        """Center Pivot: World"""
        self.ui.tb001.init_slot()
        self.ui.tb001.option_box.menu.chk004.setChecked(True)
        self.ui.tb001.call_slot()

    # ------------------------------------------------------------------ tb002  Transfer Pivot
    @btk.undoable
    def tb002(self, widget):
        """Transfer Pivot — move the selected objects' origins onto the **active** object's origin.

        Blender has a single object origin (a point), so only Maya's translate-pivot maps: the
        active object is the source and every other selected object's origin moves onto it without
        moving geometry (``btk.transfer_pivot`` — 3D-cursor → ORIGIN_CURSOR). Maya's rotate/scale
        pivot channels and Bake have no Blender analogue (a single, always-baked origin)."""
        objects = self.selected_objects()
        active = bpy.context.view_layer.objects.active
        if active is None or len(objects) < 2:
            self.sb.message_box("Select target object(s) with the source object active.")
            return
        # Order active-first so it's the source (mtk convention is source = objects[0]).
        ordered = [active] + [o for o in objects if o != active]
        btk.transfer_pivot(ordered, translate=True, select_targets_after_transfer=True)

    # ------------------------------------------------------------------ apply-rotation helper
    # transform_apply-able object types: data that can counter-offset the applied rotation so
    # the geometry stays put. An EMPTY / CAMERA / LIGHT has no such data — excluded rather than
    # risk the op erroring or losing their orientation outright.
    # (GP is "GREASEPENCIL" on Blender 4.3+/5.x — the identifier the rest of the package uses.)
    _APPLYABLE = ("MESH", "CURVE", "SURFACE", "FONT", "GREASEPENCIL", "LATTICE")

    def _apply_rotation(self, label):
        """Apply (bake) the selected objects' rotation into their data via
        ``object.transform_apply``: the geometry doesn't move, but the rotation channel resets
        so the local axes end up world-aligned — tb003's permanent World-Aligned Pivot.

        Runs under ``btk.window_context_override``: ``transform_apply`` gathers its targets and
        reads the active object from *screen* context, dead in the Qt-pump state (the same
        reason ``tb002``'s transfer and the nurbs Attach/Join calls override). Object Mode is
        ensured first (the op poll-fails in Edit Mode); multi-user data can't be applied and
        surfaces the operator's own message rather than a raw traceback.
        """
        prior_selection = self.selected_objects()
        objects = [o for o in prior_selection if o.type in self._APPLYABLE]
        if not objects:
            self.sb.message_box(
                f"{label} requires selected object(s) with geometry data "
                "(mesh / curve / text / lattice)."
            )
            return
        if not self.ensure_object_mode():
            return
        view_layer = bpy.context.view_layer
        prior_active = view_layer.objects.active
        with btk.window_context_override():
            # select ONLY the applyable objects (objects is a subset of prior_selection,
            # so this both selects them and deselects the rest in one pass)
            for o in prior_selection:
                o.select_set(o in objects)
            view_layer.objects.active = objects[0]
            try:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            except RuntimeError as e:
                self.sb.message_box(str(e))
            for o in prior_selection:  # restore the user's prior selection / active
                o.select_set(True)
            if prior_active is not None:
                view_layer.objects.active = prior_active

    def tb003_init(self, widget):
        # chk010 reuses Maya's objectName + label + default for the SAME option (the two
        # halves of Maya's World-Aligned Pivot), so the option persists in the shared namespace.
        widget.option_box.menu.setTitle("World-Aligned Pivot")
        widget.option_box.menu.add(
            "QCheckBox", setText="Manip Pivot", setObjectName="chk010", setChecked=True,
            setToolTip="On (Maya default): set a temporary world-aligned manipulator orientation "
            "(Blender's Global transform orientation) — non-destructive. Off: permanently "
            "world-align the object pivot by baking its rotation into the data.",
        )

    @btk.undoable
    def tb003(self, widget):
        """World-Aligned Pivot — a faithful mirror of Maya's ``tb003`` *including its
        Manip-Pivot option* (``chk010``), so a Maya user's muscle memory carries over:

          - **Manip Pivot on** (Maya's default) — set a *temporary* world-aligned manipulator
            orientation. Maya reorients the manip gizmo to world; the Blender parity is switching
            the scene's transform orientation to **Global** (a plain scene-property write, so the
            move/rotate gizmo now uses world axes exactly as in Maya — and, crucially, it's
            non-destructive, matching what a Maya user expects from the *default* click).
          - **Manip Pivot off** — Maya's *permanent object* pivot: apply the object's rotation so
            its local axes world-align, geometry unmoved (``_apply_rotation``).
        """
        if widget.option_box.menu.chk010.isChecked():
            bpy.context.scene.transform_orientation_slots[0].type = "GLOBAL"
            self.sb.message_box(
                "Manipulator orientation set to <hl>Global</hl> (world-aligned)."
            )
        else:
            self._apply_rotation("World-Aligned Pivot")

    @btk.undoable
    def b004(self):
        """Bake Pivot — bake Blender's *temporary* pivot, the 3D cursor, into the selected
        objects' origins (``origin_set(type="ORIGIN_CURSOR")``, geometry unmoved). The faithful
        intent-mirror of Maya's ``mtk.bake_pivot`` ("make the pivot you placed permanent"):
        Maya's repositionable manipulator pivot maps onto the cursor-as-pivot workflow
        (``pivot_point=CURSOR`` — the same analogy ``tb002``/``btk.transfer_pivot`` ride), so
        baking it = adopting the cursor as the origin. Maya's *orientation* half doesn't carry —
        a Blender origin has no orientation of its own (the object's rotation defines the axes;
        World-Aligned Pivot's permanent option covers world-aligning them). Verified live:
        non-geometry objects (EMPTY/CAMERA) in the selection are skipped untouched and armatures
        re-origin correctly, so the selection needs no type filter."""
        if not self.selected_objects():
            self.sb.message_box("Bake Pivot requires selected object(s).")
            return
        if not self.ensure_object_mode():
            return
        with btk.window_context_override():
            try:
                bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            except RuntimeError as e:
                self.sb.message_box(str(e))


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
