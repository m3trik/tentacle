# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Uv(SlotsBlender):
    """Blender port of the shared ``uv`` menu.

    Core UV operators (unwrap, smart-project, pack, cylinder-project, seam) run as ``bpy.ops.uv.*``
    in edit mode via :meth:`_uv_op` (verified to work headless). Move-to-UV-space and UV-set cleanup
    are data ops backed by ``blendertk.uv_utils``. Maya-specific / UV-editor-bound features
    (straighten, distribute, mirror, transfer, texel density, pin, stack, RizomUV) are deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu

    def _uv_op(self, op):
        """Run a UV/seam operator on the selected meshes in edit mode (all selected), then restore
        the caller's mode. Returns False (with a message) if there's no mesh selection."""
        meshes = [o for o in self.selected_objects() if o.type == "MESH"]
        if not meshes:
            self.sb.message_box("UV operation requires a mesh selection.")
            return False
        active = bpy.context.view_layer.objects.active
        prior = getattr(active, "mode", "OBJECT")
        if prior != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        try:
            op()
        finally:
            bpy.ops.object.mode_set(mode=prior)
        return True

    def _seam_op(self, clear):
        """Mark/clear UV seams on the user's **selected** edges (selection-based, unlike the
        whole-mesh unwrap ops — so it does not force select-all). Requires edit mode."""
        active = bpy.context.view_layer.objects.active
        if not (active and active.type == "MESH"):
            self.sb.message_box("Cut/Sew UVs requires an active mesh.")
            return
        if active.mode != "EDIT":
            self.sb.message_box("Select edges in Edit Mode to cut/sew UV seams.")
            return
        bpy.ops.mesh.mark_seam(clear=clear)

    # ------------------------------------------------------------------ UV operators (edit mode)
    @btk.undoable
    def tb000(self, widget):
        """Pack UVs"""
        self._uv_op(lambda: bpy.ops.uv.pack_islands())

    @btk.undoable
    def tb001(self, widget):
        """Auto Unwrap (Smart UV Project)"""
        self._uv_op(lambda: bpy.ops.uv.smart_project())

    @btk.undoable
    def tb004(self, widget):
        """Unfold (angle-based unwrap)"""
        self._uv_op(lambda: bpy.ops.uv.unwrap(method="ANGLE_BASED"))

    @btk.undoable
    def tb009(self, widget):
        """Cut Cylinder (cylinder project)"""
        self._uv_op(lambda: bpy.ops.uv.cylinder_project())

    @btk.undoable
    def b005(self):
        """Cut UVs (mark seam on selected edges)"""
        self._seam_op(clear=False)

    @btk.undoable
    def b011(self):
        """Sew UVs (clear seam on selected edges)"""
        self._seam_op(clear=True)

    @btk.undoable
    def b021(self, widget):
        """Unfold and Pack UVs"""
        self._uv_op(lambda: (bpy.ops.uv.unwrap(method="ANGLE_BASED"), bpy.ops.uv.pack_islands()))

    # ------------------------------------------------------------------ move to UV space (data op)
    @btk.undoable
    def b023(self):
        """Move To UV Space: Left"""
        btk.move_uvs(self.selected_objects(), du=-1.0)

    @btk.undoable
    def b024(self):
        """Move To UV Space: Down"""
        btk.move_uvs(self.selected_objects(), dv=-1.0)

    @btk.undoable
    def b025(self):
        """Move To UV Space: Up"""
        btk.move_uvs(self.selected_objects(), dv=1.0)

    @btk.undoable
    def b026(self):
        """Move To UV Space: Right"""
        btk.move_uvs(self.selected_objects(), du=1.0)

    # ------------------------------------------------------------------ tb007  Cleanup UV Sets
    @btk.undoable
    def tb007(self, widget):
        """Cleanup UV Sets (keep only the first UV map)."""
        btk.delete_extra_uv_sets(self.selected_objects())

    # ------------------------------------------------------------------ deferred (Maya / UV-editor)
    def tb005(self, widget):
        """Straighten UV — UV-editor align op; not yet ported."""
        self.sb.message_box("Straighten UV is not yet implemented for Blender.")

    def tb006(self, widget):
        """Distribute — UV-editor align/distribute op; not yet ported."""
        self.sb.message_box("Distribute is not yet implemented for Blender.")

    def tb008(self, widget):
        """Mirror UVs — UV-editor mirror op; not yet ported."""
        self.sb.message_box("Mirror UVs is not yet implemented for Blender.")

    def tb022(self, widget):
        """Cut UV hard edges — seam-from-sharp; not yet ported."""
        self.sb.message_box("Cut UV Hard Edges is not yet implemented for Blender.")

    def b000(self, widget):
        """Transfer UVs — needs a Data-Transfer UV setup; not yet ported."""
        self.sb.message_box("Transfer UVs is not yet implemented for Blender.")

    def b003(self):
        """Get Texel Density — needs a texel-density helper; not yet ported."""
        self.sb.message_box("Get Texel Density is not yet implemented for Blender.")

    def b004(self):
        """Set Texel Density — needs a texel-density helper; not yet ported."""
        self.sb.message_box("Set Texel Density is not yet implemented for Blender.")

    def b029(self, widget):
        """Pin / Unpin UVs — UV-editor pin; not yet ported."""
        self.sb.message_box("Pin/Unpin UVs is not yet implemented for Blender.")

    def b030(self, widget):
        """Stack / Unstack shells — not yet ported."""
        self.sb.message_box("Stack/Unstack is not yet implemented for Blender.")

    def b031(self):
        """Open UV Editor — switch an area to the UV editor; not yet ported."""
        self.sb.message_box("Open UV Editor is not yet implemented for Blender.")

    def b032(self):
        """RizomUV Bridge — external tool; not ported."""
        self.sb.message_box("RizomUV Bridge is not applicable in Blender.")

    def cmb002(self, index, widget):
        """Transform — UV transform options; not yet ported."""
        self.sb.message_box("UV Transform is not yet implemented for Blender.")

    def cmb003(self, index, widget):
        """UV set options — not yet ported."""
        self.sb.message_box("UV set options are not yet implemented for Blender.")

    def s003(self, value, widget):
        """UV spin option — not yet wired."""


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
