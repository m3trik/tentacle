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
    while the Maya-only concepts — Transfer Pivot's channel granularity, World-Aligned manip
    pivot, Bake Pivot — are deferred with an honest message.
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

    # ------------------------------------------------------------------ deferred (Maya-specific)

    def tb003(self, widget):
        """World-Aligned Pivot — Maya manipulator-pivot orientation; Blender has no separate
        manip pivot (the origin is a single point), so this is not applicable."""
        self.sb.message_box(
            "World-Aligned Pivot is not applicable in Blender (the origin is a single "
            "point, with no separate manipulator-pivot orientation)."
        )

    def b004(self):
        """Bake Pivot — Blender object origins are always baked into the transform (no-op)."""
        self.sb.message_box("Bake Pivot is not applicable in Blender (origins are always baked).")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
