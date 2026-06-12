# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots.blender._slots_blender import SlotsBlender


class Edit(SlotsBlender):
    """Blender port of the shared ``edit`` menu.

    Mesh Cleanup is backed by ``blendertk.edit_utils.clean_geometry`` (bmesh merge/degenerate/loose/
    recalc). Delete-Selected is mode-aware (objects in object mode, components by select mode in
    edit mode). Create-Primitive / Convert map onto ``bpy.ops.mesh.primitive_*`` /
    ``bpy.ops.object.convert``. Maya construction-history, node-locking, attribute/map/vertex-order
    transfers, shading sets and the axis-cut tool have no clean Blender analogue (or need a
    Data-Transfer setup) and are deferred.
    """

    # (category -> {label: bpy.ops.mesh operator}) for the Create Primitive list.
    _PRIMITIVES = {
        "Polygon": {
            "Cube": "primitive_cube_add",
            "Sphere": "primitive_uv_sphere_add",
            "Ico Sphere": "primitive_ico_sphere_add",
            "Cylinder": "primitive_cylinder_add",
            "Plane": "primitive_plane_add",
            "Circle": "primitive_circle_add",
            "Cone": "primitive_cone_add",
            "Torus": "primitive_torus_add",
            "Grid": "primitive_grid_add",
            "Monkey": "primitive_monkey_add",
        },
    }

    # (label -> bpy.ops.object.convert target) for the Convert list.
    _CONVERT_TARGETS = {
        "Mesh": "MESH",
        "Curve": "CURVE",
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.edit
        self.submenu = self.sb.loaded_ui.edit_submenu

    def header_init(self, widget):
        widget.menu.add(
            "QPushButton", setText="Cut On Axis", setObjectName="b000",
            setToolTip="Cut selected objects on an axis.",
        )

    # ------------------------------------------------------------------ tb000  Mesh Cleanup
    def tb000_init(self, widget):
        # chk032/chk033: first numbers free in BOTH this file and maya/edit.py — the QSettings
        # store is shared across DCCs, so reusing a Maya name for a different option bleeds state
        # (maya chk025 = Overlapping Faces, chk027 = Toggle Lock/UnLock).
        menu = widget.option_box.menu
        menu.setTitle("Mesh Cleanup")
        menu.add("QCheckBox", setText="Merge Vertices", setObjectName="chk024", setChecked=True,
                 setToolTip="Merge overlapping vertices (remove doubles).")
        menu.add("QDoubleSpinBox", setPrefix="Merge Distance: ", setObjectName="s000",
                 set_limits=[0, 1, 0.0001, 4], setValue=0.0001, set_fixed_height=20,
                 setToolTip="Distance under which vertices are merged / treated as degenerate.")
        menu.add("QCheckBox", setText="Delete Loose", setObjectName="chk032", setChecked=True,
                 setToolTip="Remove loose (wire) edges and unconnected vertices.")
        menu.add("QCheckBox", setText="Dissolve Degenerate", setObjectName="chk033", setChecked=True,
                 setToolTip="Dissolve zero-area faces / zero-length edges.")
        menu.add("QCheckBox", setText="Recalculate Normals", setObjectName="chk028", setChecked=True,
                 setToolTip="Make face normals consistent (outward).")
        menu.add("QCheckBox", setText="Fill Holes", setObjectName="chk029",
                 setToolTip="Fill open boundary holes.")

    @btk.undoable
    def tb000(self, widget):
        """Mesh Cleanup"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Mesh Cleanup requires a selection.")
            return
        m = widget.option_box.menu
        btk.clean_geometry(
            objects,
            merge=m.chk024.isChecked(),
            merge_distance=m.s000.value(),
            delete_loose=m.chk032.isChecked(),
            degenerate=m.chk033.isChecked(),
            recalculate=m.chk028.isChecked(),
            fill_holes=m.chk029.isChecked(),
        )

    # ------------------------------------------------------------------ tb002  Delete Selected
    @btk.undoable
    def tb002(self, widget):
        """Delete Selected (objects in object mode, components by select mode in edit mode)."""
        active = bpy.context.view_layer.objects.active
        if active and active.mode == "EDIT":
            # Deleting by VERT in edge/face mode would also remove neighboring faces that
            # share those verts — match the type to the active component select mode.
            vert, edge, face = bpy.context.tool_settings.mesh_select_mode
            bpy.ops.mesh.delete(type="FACE" if face else "EDGE" if edge else "VERT")
            return
        if self.selected_objects():
            bpy.ops.object.delete()

    # ------------------------------------------------------------------ list000  Create Primitive
    def list000_init(self, widget):
        """Initialize Create Primitives list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_left")
        root = widget.add("Create")
        root.sublist.setMinimumWidth(widget.width() or 120)
        for category, items in self._PRIMITIVES.items():
            cat = root.sublist.add(category)
            cat.sublist.add(list(items))

    # The undoable wrap sits on the action helpers, not the list handlers — the handlers also
    # fire for category/expand clicks, which would otherwise push no-op undo steps.
    @Signals("on_item_interacted")
    def list000(self, item):
        """Create Primitive"""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        op_name = self._PRIMITIVES.get(item.parent_item_text() or "", {}).get(item.item_text())
        if op_name:
            self._create_primitive(op_name)

    @btk.undoable
    def _create_primitive(self, op_name):
        getattr(bpy.ops.mesh, op_name)()

    # ------------------------------------------------------------------ list001  Convert
    def list001_init(self, widget):
        """Initialize Convert list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_down")
        root = widget.add("Convert")
        root.sublist.setMinimumWidth(180)
        root.sublist.add(list(self._CONVERT_TARGETS))

    @Signals("on_item_interacted")
    def list001(self, item):
        """Convert the selected object(s) to another type."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        target = self._CONVERT_TARGETS.get(item.item_text())
        if not target:
            return
        if not self.selected_objects():
            self.sb.message_box("Convert requires a selection.")
            return
        self._convert_selected(target)

    @btk.undoable
    def _convert_selected(self, target):
        try:
            bpy.ops.object.convert(target=target)
        except RuntimeError as e:  # e.g. poll failure outside object mode
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def tb001(self, widget):
        """Delete History — Blender has no construction history (modifier stack is non-destructive)."""
        self.sb.message_box("Delete History is not applicable in Blender (no construction history).")

    def tb004(self, widget):
        """Node Locking — Maya node locking has no Blender analogue."""
        self.sb.message_box("Node Locking is not applicable in Blender.")

    def b000(self):
        """Cut On Axis — mesh bisect; not yet ported."""
        self.sb.message_box("Cut On Axis is not yet implemented for Blender.")

    def b021(self, widget):
        """Transfer Maps — needs a bake/Data-Transfer setup; not yet ported."""
        self.sb.message_box("Transfer Maps is not yet implemented for Blender.")

    def b022(self, widget):
        """Transfer Vertex Order — Maya-specific; not yet ported."""
        self.sb.message_box("Transfer Vertex Order is not yet implemented for Blender.")

    def b023(self, widget):
        """Transfer Attribute Values — needs a Data-Transfer setup; not yet ported."""
        self.sb.message_box("Transfer Attribute Values is not yet implemented for Blender.")

    def b027(self, widget):
        """Shading Sets — Maya shading groups; Blender uses material slots."""
        self.sb.message_box("Shading Sets is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
