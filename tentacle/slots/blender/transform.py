# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class TransformSlots(SlotsBlender):
    """Blender port of the shared ``transform`` menu.

    The object-transform ops (drop-to-grid, freeze, move-to, match-scale) are backed by
    ``blendertk.xform_utils`` (mirrors ``mtk.*``). Maya manipulator-context widgets — snap
    (``manip*Context``), xform constraints / make-live, the mel align tools — have no clean
    Blender analogue and are deferred with a message.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.transform
        self.submenu = self.sb.loaded_ui.transform_submenu

    def _selection_source_target(self):
        """(source_objects, target) using Blender's active object as the target (= Maya's
        last-ordered-selection)."""
        target = bpy.context.view_layer.objects.active
        source = [o for o in self.selected_objects() if o is not target]
        return source, target

    # ------------------------------------------------------------------ tb000  Drop To Grid
    def tb000_init(self, widget):
        widget.option_box.menu.add(
            "QComboBox", addItems=["Min", "Mid", "Max"], setObjectName="cmb004",
            setToolTip="Which bounding-box point to drop onto the grid (Z=0).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Move to Origin", setObjectName="chk014",
            setToolTip="Move to the world origin (0,0,0) first.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Center Pivot", setObjectName="chk016",
            setToolTip="Re-center the object origin on its bounding box.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Freeze Transforms", setObjectName="chk017", setChecked=True,
            setToolTip="Apply (bake) the transform after dropping.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Drop To Grid"""
        m = widget.option_box.menu
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Drop To Grid requires a selection.")
            return
        btk.drop_to_grid(
            objects, align=m.cmb004.currentText(),
            origin=m.chk014.isChecked(), center_pivot=m.chk016.isChecked(),
        )
        if m.chk017.isChecked():
            btk.freeze_transforms(objects, location=True, rotation=False, scale=False)
        for o in objects:
            o.select_set(True)

    # ------------------------------------------------------------------ tb002  Freeze Transforms
    def tb002_init(self, widget):
        widget.option_box.menu.setTitle("Freeze Transforms")
        widget.option_box.menu.add(
            "QCheckBox", setText="Translate", setObjectName="chk032", setChecked=True,
            setToolTip="Bake translation -> 0,0,0.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Rotate", setObjectName="chk033",
            setToolTip="Bake rotation -> 0,0,0.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Scale", setObjectName="chk034", setChecked=True,
            setToolTip="Bake scale -> 1,1,1.",
        )

    @btk.undoable
    def tb002(self, widget):
        """Freeze Transformations"""
        m = widget.option_box.menu
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Freeze Transforms requires a selection.")
            return
        btk.freeze_transforms(
            objects, location=m.chk032.isChecked(),
            rotation=m.chk033.isChecked(), scale=m.chk034.isChecked(),
        )

    # ------------------------------------------------------------------ tb005  Move To
    def tb005_init(self, widget):
        widget.option_box.menu.setTitle("Move To")
        widget.option_box.menu.add(
            "QComboBox", addItems=btk.XformUtils.get_pivot_options(), setObjectName="cmb005",
            setToolTip="Target pivot to align the source object(s) to.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Match Scale", setObjectName="chk_match_scale",
            setToolTip="Also rescale the moved object(s) to the target's bounding-box size.",
        )

    @btk.undoable
    def tb005(self, widget):
        """Move To (align source object(s) to the active/target object)."""
        pivot = widget.option_box.menu.cmb005.currentText() or "center"
        source, target = self._selection_source_target()
        if not source or not target:
            self.sb.message_box("Move To requires 2+ selected objects (active = target).")
            return
        if widget.option_box.menu.chk_match_scale.isChecked():
            btk.match_scale(source, target)
        btk.move_to(source, target, pivot=pivot)

    # ------------------------------------------------------------------ b001  Match Scale
    @btk.undoable
    def b001(self):
        """Match Scale (rescale source object(s) to the active/target object)."""
        source, target = self._selection_source_target()
        if not source or not target:
            self.sb.message_box("Match Scale requires 2+ selected objects (active = target).")
            return
        btk.match_scale(source, target)

    # ------------------------------------------------------------------ cmb002  Align To
    # Combo label -> object.align axis set (centers, relative to the active object).
    _ALIGN_AXES = {
        "Align X to Active": {"X"},
        "Align Y to Active": {"Y"},
        "Align Z to Active": {"Z"},
        "Align Centers to Active": {"X", "Y", "Z"},
    }

    def cmb002_init(self, widget):
        widget.add(list(self._ALIGN_AXES), header="Align To")

    @btk.undoable
    def cmb002(self, index, widget):
        """Align To (object centers onto the active object's, native ``object.align``)."""
        axis = self._ALIGN_AXES.get(widget.items[index])
        if axis is None:
            return
        if len(self.selected_objects()) < 2:
            self.sb.message_box("Align requires 2+ selected objects (active = target).")
            return
        try:
            bpy.ops.object.align(
                align_mode="OPT_2", relative_to="OPT_4", align_axis=axis
            )
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def tb001(self, widget):
        """Scale Connected Edges — component op, not yet ported."""
        self.sb.message_box("Scale Connected Edges is not yet implemented for Blender.")

    def b002(self):
        """Un-Freeze Transforms — needs stored original transforms; not yet ported."""
        self.sb.message_box("Un-Freeze Transforms is not yet implemented for Blender.")

    def tb003(self, widget):
        """Transform Constraints — Maya edge/surface/make-live constraints have no Blender analogue."""
        self.sb.message_box("Transform Constraints are not yet implemented for Blender.")

    def tb004(self, widget):
        """Transform Snap — Maya manipulator snap; Blender uses tool-settings snap (deferred)."""
        self.sb.message_box("Transform Snap is not yet implemented for Blender.")

    # The shared .ui snap/constraint toggles belong to the deferred tb003/tb004 Maya tools.
    # Hide them rather than stubbing: state restore fires checkbox signals by default
    # (block_signals_on_restore=False), so a message stub would pop at UI load.
    def chk023_init(self, widget):
        """Snap Rotate toggle (Maya manipulator snap) — hidden until tb004 is ported."""
        widget.setVisible(False)

    def chk024_init(self, widget):
        """Constraint: Edge toggle — hidden until tb003 is ported."""
        widget.setVisible(False)

    def chk025_init(self, widget):
        """Constraint: Surface toggle — hidden until tb003 is ported."""
        widget.setVisible(False)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
