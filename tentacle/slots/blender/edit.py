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
            "QPushButton", setText="Channels", setObjectName="b_channels",
            setToolTip="Open the Channels panel — inspect / edit / lock / key the selected "
            "object's transform channels and custom properties (mirror of Maya's Channels).",
        )
        widget.menu.add(
            "QPushButton", setText="Cut On Axis", setObjectName="b000",
            setToolTip="Cut selected objects on an axis.",
        )

    def b_channels(self):
        """Channels — open the spreadsheet-style channel editor (btk.Channels panel).

        Faithful mirror of Maya's Channels tool, co-located in blendertk
        (``node_utils/attributes/channels``): a table of the object's transform channels +
        custom properties with value editing, lock/key toggles, and create/delete/freeze actions.
        Replaces the earlier native-substitute that just popped Blender's Properties editor."""
        self.sb.handlers.marking_menu.show("channels")

    # ------------------------------------------------------------------ tb000  Mesh Cleanup
    # (criterion -> shared objectName) for the topology-diagnostic checkboxes. The numbers reuse
    # the Maya objectNames FOR THE SAME OPTION (N-Gons / Concave / Non-Planar / Non-Manifold /
    # Quads / Zero Face Area / Zero Length Edges) per the cross-DCC objectName rule. Maya's
    # Holed / Lamina / Shared-UV / Overlapping / Zero-UV-Area / Invalid-Components checks have no
    # bmesh primitive (see find_problem_geometry) and are not mirrored.
    _DIAGNOSTIC_CRITERIA = {
        "ngons": "chk002",
        "concave": "chk011",
        "nonplanar": "chk003",
        "nonmanifold": "chk017",
        "quads": "chk010",
        "zero_area_faces": "chk013",
        "zero_length_edges": "chk014",
        "zero_uv_area": "chk015",
    }

    def tb000_init(self, widget):
        # chk032/chk033: first numbers free in BOTH this file and maya/edit.py — the QSettings
        # store is shared across DCCs, so reusing a Maya name for a different option bleeds state
        # (maya chk025 = Overlapping Faces, chk027 = Toggle Lock/UnLock).
        menu = widget.option_box.menu
        menu.setTitle("Mesh Cleanup")
        menu.add("QCheckBox", setText="All Geometry", setObjectName="chk005",
                 setToolTip="Act on every mesh in the scene instead of just the selection.")
        # Repair (chk004): same meaning as Maya — ON fixes geometry, OFF selects problem geometry.
        menu.add("QCheckBox", setText="Repair", setObjectName="chk004", setChecked=True,
                 setToolTip="ON: fix the geometry. OFF: just select the problem components so you "
                 "can inspect them (the topology checks below).")
        menu.add("Separator", setTitle="Repair")
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
        menu.add("Separator", setTitle="Topology (select / diagnose)")
        menu.add("QCheckBox", setText="N-Gons", setObjectName="chk002",
                 setToolTip="Find faces with more than 4 sides.")
        menu.add("QCheckBox", setText="Concave", setObjectName="chk011",
                 setToolTip="Find non-convex faces.")
        menu.add("QCheckBox", setText="Non-Planar", setObjectName="chk003",
                 setToolTip="Find faces whose vertices don't lie in a single plane.")
        menu.add("QCheckBox", setText="Non-Manifold Geometry", setObjectName="chk017",
                 setToolTip="Find edges bordering anything other than 2 faces.")
        menu.add("QCheckBox", setText="Quads", setObjectName="chk010",
                 setToolTip="Find faces with exactly 4 sides.")
        menu.add("QCheckBox", setText="Zero Face Area", setObjectName="chk013",
                 setToolTip="Find faces whose area is at or below the tolerance below (degenerate).")
        menu.add("QDoubleSpinBox", setPrefix="Face Area Tolerance: ", setObjectName="s006",
                 set_limits=[0, 1, 0.000001, 6], setValue=0.000001, set_fixed_height=20,
                 setToolTip="Faces at or below this area count as zero-area.")
        menu.add("QCheckBox", setText="Zero Length Edges", setObjectName="chk014",
                 setToolTip="Find edges at or below the length tolerance below (degenerate).")
        menu.add("QDoubleSpinBox", setPrefix="Edge Length Tolerance: ", setObjectName="s007",
                 set_limits=[0, 1, 0.000001, 6], setValue=0.000001, set_fixed_height=20,
                 setToolTip="Edges at or below this length count as zero-length.")
        menu.add("Separator", setTitle="UVs")
        menu.add("QCheckBox", setText="Zero UV Face Area", setObjectName="chk015",
                 setToolTip="Find faces whose area in the active UV map is at or below the tolerance "
                 "below (select-only; no automatic repair).")
        menu.add("QDoubleSpinBox", setPrefix="UV Face Area Tolerance: ", setObjectName="s008",
                 set_limits=[0, 1, 0.000001, 6], setValue=0.000001, set_fixed_height=20,
                 setToolTip="Faces at or below this UV area count as zero-UV-area.")
        menu.add("Separator", setTitle="Overlapping (select / delete)")
        menu.add("QCheckBox", setText="Overlapping Faces", setObjectName="chk025",
                 setToolTip="Find faces coincident with another (doubled geometry). "
                 "Repair ON deletes them; OFF selects them.")
        menu.add("QCheckBox", setText="Overlapping Duplicate Objects", setObjectName="chk022",
                 setToolTip="Find duplicate mesh OBJECTS overlapping in world space. "
                 "Repair ON deletes them; OFF selects them.")
        menu.add("QCheckBox", setText="Omit Selected Objects", setObjectName="chk023",
                 setToolTip="With Overlapping Duplicate Objects: find duplicates OF the selected "
                 "objects while keeping the selected ones.")

    @btk.undoable
    def tb000(self, widget):
        """Mesh Cleanup — Repair (fix) or, with Repair OFF, select the matched problem geometry."""
        m = widget.option_box.menu
        repair = m.chk004.isChecked()
        objects = (
            [o for o in bpy.data.objects if o.type == "MESH"]
            if m.chk005.isChecked()
            else [o for o in self.selected_objects() if o.type == "MESH"]
        )

        # Object-level duplicates are a distinct domain — handle and return (Maya parity).
        if m.chk022.isChecked():
            retain = self.selected_objects() if m.chk023.isChecked() else None
            dupes = btk.get_overlapping_duplicates(
                retain=retain, select=not repair, delete=repair
            )
            verb = "deleted" if repair else "selected"
            self.sb.message_box(
                f"Found <hl>{len(dupes)}</hl> overlapping duplicate object(s)"
                f"{f' ({verb})' if dupes else ''}."
            )
            return

        if not objects:
            self.sb.message_box("Mesh Cleanup requires a mesh selection.")
            return

        # Overlapping faces — its own select/delete pass (the topology select path below would
        # clear the selection it makes, so in select mode it stands alone).
        if m.chk025.isChecked():
            n = btk.get_overlapping_faces(objects, delete=repair, select=not repair)
            if not repair:
                self._show_problem_components(objects, "FACE")
                self.sb.message_box(f"Found <hl>{n}</hl> overlapping face(s) (selected).")
                return
            if n:
                self.sb.message_box(f"Deleted <hl>{n}</hl> overlapping face(s).")

        criteria = {
            name: getattr(m, oname).isChecked()
            for name, oname in self._DIAGNOSTIC_CRITERIA.items()
        }

        if not repair:  # select-only diagnostic path
            if not any(criteria.values()):
                self.sb.message_box("Enable a topology check (N-Gons, Concave, …) to select.")
                return
            counts = btk.find_problem_geometry(
                objects, select=True,
                area_tolerance=m.s006.value(),
                edge_length_tolerance=m.s007.value(),
                uv_area_tolerance=m.s008.value(),
                **criteria,
            )
            self._show_problem_components(objects, counts.get("_mode", "VERT"))
            found = {k: v for k, v in counts.items() if k != "_mode" and v}
            summary = ", ".join(f"{v} {k}" for k, v in found.items()) or "none"
            self.sb.message_box(f"Problem geometry selected: <hl>{summary}</hl>.")
            return

        btk.clean_geometry(
            objects,
            merge=m.chk024.isChecked(),
            merge_distance=m.s000.value(),
            delete_loose=m.chk032.isChecked(),
            degenerate=m.chk033.isChecked(),
            recalculate=m.chk028.isChecked(),
            fill_holes=m.chk029.isChecked(),
        )

    @staticmethod
    def _show_problem_components(objects, mode):
        """Enter Edit Mode on the active mesh and set the component select mode so the
        flags stamped by ``find_problem_geometry`` are visible."""
        active = bpy.context.view_layer.objects.active
        if active not in objects:
            bpy.context.view_layer.objects.active = objects[0]
        if bpy.context.view_layer.objects.active.mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type=mode)

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

    # ------------------------------------------------------------------ tool panels (blender_menus)
    def b000(self):
        """Cut On Axis"""
        self.sb.handlers.marking_menu.show("cut_on_axis")

    # ------------------------------------------------------------------ transfers
    def b023(self):
        """Transfer Attribute Values — Blender's native **Data Transfer** (active → selected).

        Maya's ``TransferAttributeValues`` maps onto ``object.data_transfer``, which transfers
        any mesh layer (vertex positions/normals, UVs, vertex colors, weights, custom split
        normals…) from the active mesh to the other selected ones. Invoked interactively so its
        redo panel exposes the per-layer choice, mirroring the Maya options dialog."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active not in objects or len(objects) < 2:
            self.sb.message_box("Select target mesh(es) with the source mesh active.")
            return
        self.invoke_op("object.data_transfer")

    def b027(self):
        """Shading Sets — copy the active mesh's material slots/assignments to the selected ones.

        Maya transfers shading-group membership; the Blender analogue is
        ``object.material_slot_copy`` (copies the active object's material slots — and thus its
        shading — onto every other selected object)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active not in objects or len(objects) < 2:
            self.sb.message_box("Select target mesh(es) with the source (shaded) mesh active.")
            return
        try:
            bpy.ops.object.material_slot_copy()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def tb001(self, widget):
        """Delete History — Blender has no construction history (modifier stack is non-destructive)."""
        self.sb.message_box("Delete History is not applicable in Blender (no construction history).")

    def tb004(self, widget):
        """Node Locking — Maya node locking has no Blender analogue."""
        self.sb.message_box("Node Locking is not applicable in Blender.")

    def b021(self):
        """Transfer Maps — Maya's surface-sampling bake (high→low normals/AO/etc.). The Blender
        analogue is Cycles selected-to-active baking (render-engine + UV + image-target setup);
        deferred as its own task — use Blender's Render Properties ▸ Bake directly meanwhile."""
        self.sb.message_box(
            "Transfer Maps (bake) isn't wired yet — use Render Properties ▸ Bake "
            "(Cycles, Selected to Active) for now."
        )

    def b022(self):
        """Transfer Vertex Order — Maya reindexes a target's verts to match a source. Blender has
        no native vertex-order transfer (and no in-place reindex), so this is deferred."""
        self.sb.message_box("Transfer Vertex Order has no Blender built-in (deferred).")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
