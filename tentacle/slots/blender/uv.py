# !/usr/bin/python
# coding=utf-8
import math

import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Uv(SlotsBlender):
    """Blender port of the shared ``uv`` menu.

    Core UV operators (unwrap, smart-project, pack, cylinder-project, seam) run as ``bpy.ops.uv.*``
    in edit mode via :meth:`_uv_op` (verified to work headless). Data-level UV work (move/transform/
    pin/texel density/UV-set cleanup) is backed by ``blendertk.uv_utils`` (bmesh — headless); UV
    transfer rides the native Data-Transfer operator. Maya-/UV-editor-bound features (straighten,
    distribute, mirror, stack, RizomUV) stay deferred.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu
        # b029 dual-state pin toggle (Maya parity): reset when the selection changes.
        self._b029_pinned = False
        self._b029_last_selection = None

    def get_map_size(self):
        """Get the map size from the combobox as an int. ie. 2048"""
        return int(self.ui.cmb003.currentText())

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

    # ------------------------------------------------------------------ b031  Open UV Editor
    def b031(self):
        """Open UV Editor"""
        btk.open_editor("UV Editor")

    # ------------------------------------------------------------------ cmb002  Transform
    def cmb002_init(self, widget):
        widget.add(["Flip U", "Flip V", "Rotate 45"], header="Transform:")

    @btk.undoable
    def cmb002(self, index, widget):
        """Transform (flip/rotate the selection's UV maps about their shared bbox center —
        whole-map, unlike Maya's selected-UV transform)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Nothing selected.")
            return
        text = widget.items[index]
        if text == "Flip U":
            btk.transform_uvs(objects, flip_u=True)
        elif text == "Flip V":
            btk.transform_uvs(objects, flip_v=True)
        elif text == "Rotate 45":
            btk.transform_uvs(objects, angle=-45.0)

    # ------------------------------------------------------------------ b000  Transfer UVs
    @btk.undoable
    def b000(self, widget):
        """Transfer UVs (active mesh → other selected, native Data-Transfer)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active not in objects or len(objects) < 2:
            self.sb.message_box("Select target mesh(es) with the source mesh active.")
            return
        try:
            bpy.ops.object.data_transfer(
                data_type="UV", loop_mapping="POLYINTERP_NEAREST",
                layers_select_src="ACTIVE", layers_select_dst="ACTIVE",
            )
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ b003/b004  Texel density
    def b003(self):
        """Get Texel Density (into the s003 readout, against the cmb003 map size)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Nothing selected.")
            return
        self.ui.s003.setValue(btk.get_texel_density(objects, self.get_map_size()))

    @btk.undoable
    def b004(self):
        """Set Texel Density (from the s003 value, against the cmb003 map size)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Nothing selected.")
            return
        btk.set_texel_density(objects, self.ui.s003.value(), self.get_map_size())

    # ------------------------------------------------------------------ b029  Pin / Unpin
    def b029(self, widget):
        """Pin / Unpin UVs (dual-state toggle, Maya parity: first click on a fresh selection
        pins, the next unpins; selection change resets. Edit mode pins the selected verts'
        UVs, object mode the whole map)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Nothing selected.")
            return
        names = sorted(o.name for o in objects)
        if self._b029_last_selection != names:
            self._b029_pinned = False  # fresh selection — start with Pin
        self._b029_pinned = not self._b029_pinned
        btk.pin_uvs(
            objects, pin=self._b029_pinned,
            selected_only=any(o.mode == "EDIT" for o in objects),
        )
        self._b029_last_selection = names

    # ------------------------------------------------------------------ tb022  Cut Hard Edges
    def tb022_init(self, widget):
        widget.option_box.menu.setTitle("Cut Hard Edges")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Angle: ", setObjectName="s017",
            set_limits=[0, 180], setValue=70,
            setToolTip="Edges sharper than this angle are seam-cut.",
        )

    @btk.undoable
    def tb022(self, widget):
        """Cut UV Hard Edges (mark seams on edges sharper than the angle)."""
        angle = widget.option_box.menu.s017.value()
        self._uv_op(
            lambda: (
                bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(angle)),
                bpy.ops.mesh.mark_seam(clear=False),
            )
        )

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

    def b030(self, widget):
        """Stack / Unstack shells — not yet ported."""
        self.sb.message_box("Stack/Unstack is not yet implemented for Blender.")

    def b032(self):
        """RizomUV Bridge — external tool; not ported."""
        self.sb.message_box("RizomUV Bridge is not applicable in Blender.")

    def cmb003(self, index, widget):
        """UV Map Size — passive input; read by get_map_size for the texel-density tools.
        Nothing to do on change."""

    def s003(self, value, widget):
        """Texel Density — passive input; read by Get/Set Texel Density (b003/b004).
        Nothing to do on change."""


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
