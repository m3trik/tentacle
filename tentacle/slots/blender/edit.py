# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from uitk import Signals
from tentacle.slots._mesh_cleanup import (
    cleanup_popup_html,
    cleanup_console_report,
    report_cleanup_failure,
)
from tentacle.slots.blender._slots_blender import SlotsBlender


class Edit(SlotsBlender):
    """Blender port of the shared ``edit`` menu.

    Mesh Cleanup is backed by ``blendertk.edit_utils.clean_geometry`` (bmesh merge/degenerate/loose/
    recalc). Delete-Selected is mode-aware (objects in object mode, components by select mode in
    edit mode). Create-Primitive (list000) mirrors Maya's 6 categories (Polygon / NURBS / Curve /
    Helper / Light / Control) over ``bpy.ops.mesh``/``bpy.ops.surface``/``bpy.ops.curve``/
    ``bpy.ops.object.empty_add``/``bpy.ops.object.light_add``/``blendertk.Controls``. Convert
    (list001) maps onto ``bpy.ops.object.convert`` plus one non-convert "Instance to Object" entry.
    The Transfer menu (cmb000) rides native Data-Transfer / material slot copy — see the ``cmb000``
    section below. Maya construction-history and node-locking have no Blender analogue (no
    construction history, no DG node locking) and stay documented stubs.
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

    # (label -> bpy.ops.curve primitive-add operator) for the Create > Curve category. Maya's
    # freehand EP/CV/Pencil Curve *tools* have no one-click equivalent here (they're modal
    # click-to-place tools, not a single creation call) — bpy.ops.curve.draw is the interactive
    # analogue but activating a modal drawing tool from a menu click doesn't fit this list's
    # "click -> object appears" contract, so it's left out; these 5 non-interactive primitives
    # cover the actual "Curve" capability gap the audit found (verified live: dir(bpy.ops.curve)).
    _CURVE_PRIMITIVES = {
        "Bezier Curve": "primitive_bezier_curve_add",
        "Bezier Circle": "primitive_bezier_circle_add",
        "Nurbs Curve": "primitive_nurbs_curve_add",
        "Nurbs Circle": "primitive_nurbs_circle_add",
        "Path": "primitive_nurbs_path_add",
    }

    # (label -> bpy.ops.surface primitive-add operator) for the Create > NURBS category. Maya's
    # "NURBS" category is specifically NURBS *surfaces*, so this mirrors bpy.ops.surface (a
    # distinct namespace from bpy.ops.curve's NURBS *curves* above) — verified live via
    # dir(bpy.ops.surface).
    _NURBS_SURFACES = {
        "Sphere": "primitive_nurbs_surface_sphere_add",
        "Cylinder": "primitive_nurbs_surface_cylinder_add",
        "Torus": "primitive_nurbs_surface_torus_add",
        "Circle": "primitive_nurbs_surface_circle_add",
        "Curve": "primitive_nurbs_surface_curve_add",
        "Patch": "primitive_nurbs_surface_surface_add",
    }

    # (label -> callable) for the Create > Helper category. "Locator" reuses the exact
    # empty_add(type="PLAIN_AXES") precedent already established in rigging.py; "Null Group" uses
    # the "ARROWS" empty type RigUtils.create_group uses for its offset-group buffer (Blender has
    # no separate invisible-group node like Maya's ``cmds.group(empty=True)`` — an Empty stands in
    # for both). "Set" mirrors ``cmds.sets()`` — a non-visual logical-grouping container — with a
    # linked, empty Collection (Blender's closest structural analogue), linked under
    # ``scene.collection``: ``bpy.context.collection`` is a *screen-context* member that is None
    # in the Qt-pump state (AttributeError).
    _HELPERS = {
        "Locator": lambda: bpy.ops.object.empty_add(type="PLAIN_AXES"),
        "Null Group": lambda: bpy.ops.object.empty_add(type="ARROWS"),
        "Set": lambda: bpy.context.scene.collection.children.link(
            bpy.data.collections.new("set1")
        ),
    }

    # (label -> bpy.ops.object.light_add type) for the Create > Light category. Verified live
    # (bpy.ops.object.light_add.get_rna_type().properties["type"].enum_items) that Blender's light
    # object supports exactly POINT/SUN/SPOT/AREA — Maya's Ambient and Volume lights have no
    # Blender light-object counterpart and are dropped; Directional maps onto Sun (the equivalent
    # parallel-ray light type).
    _LIGHTS = {
        "Point": "POINT",
        "Directional": "SUN",
        "Spot": "SPOT",
        "Area": "AREA",
    }

    # (label -> blendertk.Controls preset name) for the Create > Control category — wires up
    # blendertk's rig-control factory (``blendertk.rig_utils.controls.Controls``), previously built
    # but unreachable from any menu. Only the shapes actually registered in Controls._PRESETS are
    # offered (6, vs Maya's 14 control_map presets); add more shapes there to grow this list.
    _CONTROLS = {
        "Circle": "circle",
        "Square": "square",
        "Diamond": "diamond",
        "Box": "box",
        "Ball": "ball",
        "Arrow": "arrow",
    }

    # (label -> bpy.ops.object.convert target) for the Convert list. Verified live
    # (bpy.ops.object.convert.get_rna_type().properties["target"].enum_items) that Blender's
    # convert operator supports exactly these 5 targets — all now offered. Blender's own
    # Object > Convert To menu (space_view3d.py's VIEW3D_MT_object_convert) lists all 5
    # unconditionally too (`layout.operator_enum("object.convert", "target")` — no per-source-type
    # graying), so this matches native behavior exactly: "Curve" on a solid mesh, and "Hair Curves"
    # on anything but an existing Curve/hair-particle source, legitimately no-op (FINISHED, object
    # unchanged) rather than erroring — verified live, not a bug to work around.
    _CONVERT_TARGETS = {
        "Mesh": "MESH",
        "Curve": "CURVE",
        "Point Cloud": "POINTCLOUD",
        "Hair Curves": "CURVES",
        "Grease Pencil": "GREASEPENCIL",
    }

    # Convert-list item(s) that aren't a bpy.ops.object.convert() target — dispatched to a
    # dedicated method (label -> method name), same pattern as cmb000's _TRANSFER_OPS below.
    # "Instance to Object" mirrors Maya's convertInstanceToObject: cmds.instance() shares one
    # shape node across transforms, and Blender's linked duplicate (Alt+D) shares one object-data
    # block across objects the same way, so make_single_user(...) — giving the selection its own
    # unique data — is the precise analogue. (NOT duplicates_make_real, verified live to be a
    # different kind of instancing — particle/array/collection-instance duplis becoming real
    # objects — that no Maya Convert item maps onto.)
    _CONVERT_EXTRA = {
        "Instance to Object": "_convert_instance_to_object",
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

    # (criterion -> human label) for the Select-path feedback (popup + console). Keys mirror
    # _DIAGNOSTIC_CRITERIA / find_problem_geometry's returned counts.
    _CRITERION_LABELS = {
        "ngons": "N-Gons",
        "concave": "Concave",
        "nonplanar": "Non-Planar",
        "nonmanifold": "Non-Manifold edges",
        "quads": "Quads",
        "zero_area_faces": "Zero-Area Faces",
        "zero_length_edges": "Zero-Length Edges",
        "zero_uv_area": "Zero-UV-Area Faces",
    }

    def tb000_init(self, widget):
        # chk032/chk033: first numbers free in BOTH this file and maya/edit.py — the QSettings
        # store is shared across DCCs, so reusing a Maya name for a different option bleeds state
        # (maya chk025 = Overlapping Faces, chk027 = Toggle Lock/UnLock).
        menu = widget.option_box.menu
        menu.setTitle("Mesh Cleanup")
        # Scope (cmb_scope) replaces the old "All Geometry" checkbox: which meshes to act on. Data
        # values (selected / visible / all) drive _cleanup_pool below; items are identical to the
        # Maya panel (shared QSettings namespace + parity sweep both key off objectName).
        cmb = menu.add("QComboBox", setObjectName="cmb_scope",
                       setToolTip="Which meshes Mesh Cleanup acts on:\n"
                       "• Selected: only the current selection.\n"
                       "• Visible: every visible mesh in the scene.\n"
                       "• All Geometry: every mesh in the scene.")
        for label, data in [("Selected", "selected"), ("Visible", "visible"), ("All Geometry", "all")]:
            cmb.addItem(label, data)
        # Mode (cmb_mode) replaces the old "Repair" checkbox: same two states, now self-labeling.
        cmb = menu.add("QComboBox", setObjectName="cmb_mode",
                       setToolTip="What Mesh Cleanup does with the matches:\n"
                       "• Select (diagnose): just select the problem components so you can inspect them.\n"
                       "• Repair (fix): fix the geometry in place.")
        for label, data in [("Select (diagnose)", "select"), ("Repair (fix)", "repair")]:
            cmb.addItem(label, data)
        menu.add("Separator", setTitle="Repair")
        menu.add("QCheckBox", setText="Merge vertices", setObjectName="chk024", setChecked=False,
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
        menu.add("QCheckBox", setText="N-Gons", setObjectName="chk002", setChecked=True,
                 setToolTip="Find faces with more than 4 sides.")
        menu.add("QCheckBox", setText="Concave", setObjectName="chk011",
                 setToolTip="Find non-convex faces.")
        menu.add("QCheckBox", setText="Non-Planar", setObjectName="chk003",
                 setToolTip="Find faces whose vertices don't lie in a single plane.")
        menu.add("QCheckBox", setText="Non-Manifold Geometry", setObjectName="chk017", setChecked=True,
                 setToolTip="Find edges bordering anything other than 2 faces.")
        menu.add("QCheckBox", setText="Quads", setObjectName="chk010",
                 setToolTip="Find faces with exactly 4 sides.")
        menu.add("QCheckBox", setText="Zero Face Area", setObjectName="chk013", setChecked=True,
                 setToolTip="Find faces whose area is at or below the tolerance below (degenerate).")
        menu.add("QDoubleSpinBox", setPrefix="Face Area Tolerance:   ", setObjectName="s006",
                 set_limits=[0, 10, 0.00001, 6], setValue=0.000010, set_fixed_height=20,
                 setToolTip="Faces at or below this area count as zero-area.")
        menu.add("QCheckBox", setText="Zero Length Edges", setObjectName="chk014", setChecked=True,
                 setToolTip="Find edges at or below the length tolerance below (degenerate).")
        menu.add("QDoubleSpinBox", setPrefix="Edge Length Tolerance: ", setObjectName="s007",
                 set_limits=[0, 10, 0.00001, 6], setValue=0.000010, set_fixed_height=20,
                 setToolTip="Edges at or below this length count as zero-length.")
        menu.add("Separator", setTitle="UVs")
        menu.add("QCheckBox", setText="Zero UV Face Area", setObjectName="chk015",
                 setToolTip="Find faces whose area in the active UV map is at or below the tolerance "
                 "below (select-only; no automatic repair).")
        menu.add("QDoubleSpinBox", setPrefix="UV Face Area Tolerance:", setObjectName="s008",
                 set_limits=[0, 10, 0.00001, 6], setValue=0.000010, set_fixed_height=20,
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
        """Mesh Cleanup — Repair (fix) or, in Select mode, select the matched problem geometry.

        Two-channel feedback (see ``tentacle.slots._mesh_cleanup``): a minimal HTML popup summary
        plus a detailed console breakdown. The whole operational body is wrapped so any bpy
        ``RuntimeError`` surfaces as a message box instead of an unhandled traceback."""
        m = widget.option_box.menu
        scope = m.cmb_scope.currentData() or "selected"
        repair = m.cmb_mode.currentData() == "repair"
        mode_label = "Repair" if repair else "Select"
        try:
            self._mesh_cleanup(m, scope, repair, mode_label)
        except RuntimeError as exc:
            report_cleanup_failure(self.sb.message_box, scope, mode_label, exc)

    def _cleanup_pool(self, scope):
        """Mesh objects for the Cleanup ``scope``: 'selected' -> the current selection; 'visible' ->
        every visible mesh in the active view layer; 'all' -> every mesh in the view layer. Pools
        from ``view_layer.objects`` (not ``bpy.data.objects``) — the data pool spans the whole file
        (other scenes, excluded collections, linked libraries: activating one raises, and cleaning
        linked data errors)."""
        if scope == "selected":
            return [o for o in self.selected_objects() if o.type == "MESH"]
        meshes = [o for o in bpy.context.view_layer.objects if o.type == "MESH"]
        if scope == "visible":
            return [o for o in meshes if o.visible_get()]
        return meshes

    @staticmethod
    def _geo_counts(objects):
        """``(total verts, total faces)`` across ``objects`` — before/after feedback for the Repair
        path. Reads mesh data (accurate in Object Mode, where cleanup runs); guarded so a stray
        state can't crash the report."""
        verts = faces = 0
        for o in objects:
            data = getattr(o, "data", None)
            if data is None:
                continue
            try:
                verts += len(data.vertices)
                faces += len(data.polygons)
            except (AttributeError, ReferenceError):
                pass
        return verts, faces

    def _mesh_cleanup(self, m, scope, repair, mode_label):
        """Mesh Cleanup body (see :meth:`tb000`) — resolves the scope pool, routes duplicates /
        select / repair, and reports through both feedback channels."""
        objects = self._cleanup_pool(scope)

        # Object-level duplicates are a distinct domain — handle and return (Maya parity).
        if m.chk022.isChecked():
            retain = self.selected_objects() if m.chk023.isChecked() else None
            dupes = btk.get_overlapping_duplicates(retain=retain, select=not repair, delete=repair)
            n = len(dupes)
            verb = "deleted" if repair else "selected"
            cleanup_console_report(
                f"{mode_label} · Overlapping Duplicate Objects",
                [f"scope: {scope}", f"{n} overlapping duplicate object(s) ({verb})"],
            )
            self.sb.message_box(cleanup_popup_html(
                f"<hl>Mesh Cleanup — {mode_label}</hl>",
                [(n, f"overlapping duplicate objects {verb}")],
            ))
            return

        if not objects:
            self.sb.message_box(
                f"<hl>Mesh Cleanup — {mode_label}</hl><br>"
                f"No mesh found for scope '<hl>{scope}</hl>'.<br>Select a mesh or change Scope."
            )
            return

        criteria = {
            name: getattr(m, oname).isChecked()
            for name, oname in self._DIAGNOSTIC_CRITERIA.items()
        }

        # Overlapping faces — Repair deletes them; in Select mode the selected dupes are captured
        # and re-applied after the topology pass below (which rewrites the mesh select flags
        # wholesale — the union mirrors Maya's additive ``select -add``).
        overlap_n = 0
        overlap_faces = {}
        if m.chk025.isChecked():
            overlap_n = btk.get_overlapping_faces(objects, delete=repair, select=not repair)
            if not repair and any(criteria.values()):
                overlap_faces = {
                    o: [p.index for p in o.data.polygons if p.select] for o in objects
                }

        if not repair:
            self._mesh_cleanup_select(m, scope, objects, criteria, overlap_n, overlap_faces)
            return

        # -------- Repair / fix path
        before_v, before_f = self._geo_counts(objects)
        btk.clean_geometry(
            objects,
            merge=m.chk024.isChecked(),
            merge_distance=m.s000.value(),
            delete_loose=m.chk032.isChecked(),
            degenerate=m.chk033.isChecked(),
            recalculate=m.chk028.isChecked(),
            fill_holes=m.chk029.isChecked(),
        )
        after_v, after_f = self._geo_counts(objects)
        removed_v, removed_f = before_v - after_v, before_f - after_f
        ops = [
            label
            for on, label in (
                (m.chk024.isChecked(), "merge doubles"),
                (m.chk032.isChecked(), "delete loose"),
                (m.chk033.isChecked(), "dissolve degenerate"),
                (m.chk028.isChecked(), "recalc normals"),
                (m.chk029.isChecked(), "fill holes"),
            )
            if on
        ]
        cleanup_console_report(
            "Repair",
            [
                f"scope: {scope} · {len(objects)} mesh(es)",
                f"operations: {', '.join(ops) or 'none'}",
                f"verts: {before_v} -> {after_v} (removed {removed_v})",
                f"faces: {before_f} -> {after_f} (removed {removed_f})",
                *([f"overlapping faces deleted: {overlap_n}"] if m.chk025.isChecked() else []),
            ],
        )
        self.sb.message_box(cleanup_popup_html(
            f"<hl>Mesh Cleanup — Repair</hl> · <hl>{len(objects)}</hl> mesh(es)",
            [
                (removed_v, "verts removed"),
                (removed_f, "faces removed"),
                (overlap_n, "overlapping faces deleted"),
            ],
        ))

    def _mesh_cleanup_select(self, m, scope, objects, criteria, overlap_n, overlap_faces):
        """Select / diagnose path: flag the matched problem geometry, reveal it in Edit Mode, and
        report per-criterion counts through both feedback channels."""
        if not any(criteria.values()):
            if not m.chk025.isChecked():
                self.sb.message_box(
                    "<hl>Mesh Cleanup — Select</hl><br>"
                    "Enable a topology check (N-Gons, Concave, …) or Overlapping Faces to select."
                )
                return
            self._show_problem_components(objects, "FACE")
            cleanup_console_report(
                "Select · Overlapping Faces",
                [f"scope: {scope} · {len(objects)} mesh(es)", f"overlapping faces: {overlap_n}"],
            )
            self.sb.message_box(cleanup_popup_html(
                "<hl>Mesh Cleanup — Select</hl>", [(overlap_n, "overlapping faces")]
            ))
            return

        counts = btk.find_problem_geometry(
            objects, select=True,
            area_tolerance=m.s006.value(),
            edge_length_tolerance=m.s007.value(),
            uv_area_tolerance=m.s008.value(),
            **criteria,
        )
        for o, indices in overlap_faces.items():  # union the dupes back in
            self._reselect_faces(o, indices)
        self._show_problem_components(objects, counts.get("_mode", "VERT"))

        rows = [
            (counts.get(k, 0), self._CRITERION_LABELS[k])
            for k in self._DIAGNOSTIC_CRITERIA
            if counts.get(k)
        ]
        if overlap_n:
            rows.append((overlap_n, "Overlapping Faces"))
        total = sum(c for c, _ in rows)
        cleanup_console_report(
            "Select",
            [
                f"scope: {scope} · {len(objects)} mesh(es)",
                *[f"{label}: {c}" for c, label in rows],
                f"total problem components: {total}",
            ],
        )
        self.sb.message_box(cleanup_popup_html(
            f"<hl>Mesh Cleanup — Select</hl> · <hl>{total}</hl> total", rows
        ))

    @staticmethod
    def _show_problem_components(objects, mode):
        """Enter Edit Mode on a problem mesh and set the component select mode so the flags stamped
        by ``find_problem_geometry`` are visible. Defensive: a no-op when there's no mesh to show,
        and the ``mode_set`` / ``select_mode`` ops run under ``window_context_override`` — they poll
        their target from the *window* context, which is ``None`` in the Qt event-pump state the
        slots run in (the "Context missing active object" crash), so the override supplies a window
        for the poll (the same trap ``tb002`` and the fbx exporter handle). A poll failure is
        swallowed: the components are already flagged on the mesh data."""
        meshes = [o for o in objects if o and getattr(o, "type", None) == "MESH"]
        if not meshes:
            return
        active = btk.active_object()
        if active not in meshes:
            active = meshes[0]
            bpy.context.view_layer.objects.active = active
        with btk.window_context_override():
            try:
                if active.mode != "EDIT":
                    bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_mode(type=mode)
            except RuntimeError:
                pass

    @staticmethod
    def _reselect_faces(obj, indices):
        """Additively re-select faces by index, with the down-flush to verts/edges that keeps
        them selected across ``mesh.select_mode``'s selection flush — used by tb000 to union
        the overlapping-face dupes with the topology-diagnostic selection (both engine passes
        rewrite the select flags wholesale)."""
        import bmesh

        if not indices:
            return
        if obj.mode == "EDIT":  # mesh-data writes wouldn't reach the live edit-bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            for i in indices:
                bm.faces[i].select_set(True)  # select_set flushes down to verts/edges
            bm.select_flush(True)
            bmesh.update_edit_mesh(obj.data)
            return
        mesh = obj.data
        for i in indices:
            p = mesh.polygons[i]
            p.select = True
            for vi in p.vertices:
                mesh.vertices[vi].select = True
            for li in p.loop_indices:
                mesh.edges[mesh.loops[li].edge_index].select = True
        mesh.update()

    # ------------------------------------------------------------------ tb002  Delete Selected
    @btk.undoable
    def tb002(self, widget):
        """Delete Selected (objects in object mode, components by select mode in edit mode)."""
        active = bpy.context.view_layer.objects.active
        # window override: mesh.delete / object.delete / mode_set poll their targets from
        # *screen* context — dead in the Qt-pump state (no-op when a window exists).
        with btk.window_context_override():
            if active and active.mode == "EDIT":
                # Deleting by VERT in edge/face mode would also remove neighboring faces that
                # share those verts — match the type to the active component select mode.
                vert, edge, face = bpy.context.tool_settings.mesh_select_mode
                bpy.ops.mesh.delete(type="FACE" if face else "EDGE" if edge else "VERT")
                return
            if active and active.mode != "OBJECT":
                # SCULPT / WEIGHT_PAINT / etc. fall into this object branch, where
                # object.delete's poll fails outside Object Mode — switch first.
                try:
                    bpy.ops.object.mode_set(mode="OBJECT")
                except RuntimeError as e:
                    self.sb.message_box(str(e))
                    return
            if self.selected_objects():
                bpy.ops.object.delete()

    # ------------------------------------------------------------------ list000  Create Primitive
    def list000_init(self, widget):
        """Initialize Create Primitives list — 6 categories, mirroring Maya's Polygon/NURBS/
        Curve/Helper/Light/Control (name+capability, not item-count) parity."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_left")
        root = widget.add("Create")

        categories = {
            "Polygon": list(self._PRIMITIVES["Polygon"]),
            "NURBS": list(self._NURBS_SURFACES),
            "Curve": list(self._CURVE_PRIMITIVES),
            "Helper": list(self._HELPERS),
            "Light": list(self._LIGHTS),
            "Control": list(self._CONTROLS),
        }
        for category, items in categories.items():
            cat = root.sublist.add(category)
            cat.sublist.add(items)

    # The undoable wrap sits on the action helpers, not the list handlers — the handlers also
    # fire for category/expand clicks, which would otherwise push no-op undo steps.
    @Signals("on_item_interacted")
    def list000(self, item):
        """Create Primitive — branch per category the way Maya's list000 does (Control/Curve/
        Helper/Light get their own creation path; Polygon/NURBS stay a flat op-name lookup).

        Forces Object Mode first. Maya's primitive commands always create a brand-new DAG node
        regardless of component-select mode (that's *why* Maya's own list000 only bothers to
        restore ``cmds.selectMode(object=True)`` — a post-creation convenience, not a safety
        requirement). Blender has no such guarantee: verified live that ``mesh``/``curve``/
        ``surface`` primitive-add operators called from Edit Mode silently MERGE the new geometry
        into whichever mesh is currently being edited (no new object, no error) instead of making
        one, and that ``object.empty_add``/``object.light_add`` instead raise (poll fails outside
        Object Mode) — so this guard is what makes "click Create -> get a new object" true here
        the way it always is in Maya."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        active = bpy.context.view_layer.objects.active
        if active and active.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        text = item.item_text()
        parent_text = item.parent_item_text() or ""

        try:
            if parent_text == "Control":
                shape = self._CONTROLS.get(text)
                if shape:
                    self._create_control(shape, text)
            elif parent_text == "Light":
                light_type = self._LIGHTS.get(text)
                if light_type:
                    self._create_light(light_type)
            elif parent_text == "Helper":
                fn = self._HELPERS.get(text)
                if fn:
                    self._create_helper(fn)
            elif parent_text == "Curve":
                op_name = self._CURVE_PRIMITIVES.get(text)
                if op_name:
                    self._create_curve_primitive(op_name)
            elif parent_text == "NURBS":
                op_name = self._NURBS_SURFACES.get(text)
                if op_name:
                    self._create_nurbs_surface(op_name)
            else:  # Polygon
                op_name = self._PRIMITIVES.get(parent_text, {}).get(text)
                if op_name:
                    self._create_primitive(op_name)
        except RuntimeError as e:  # e.g. a poll failure the Object Mode guard above didn't cover
            self.sb.message_box(str(e))

    @btk.undoable
    def _create_primitive(self, op_name):
        getattr(bpy.ops.mesh, op_name)()

    @btk.undoable
    def _create_curve_primitive(self, op_name):
        getattr(bpy.ops.curve, op_name)()

    @btk.undoable
    def _create_nurbs_surface(self, op_name):
        getattr(bpy.ops.surface, op_name)()

    @btk.undoable
    def _create_light(self, light_type):
        bpy.ops.object.light_add(type=light_type)

    @btk.undoable
    def _create_helper(self, fn):
        fn()

    @btk.undoable
    def _create_control(self, shape, label):
        ctrl = btk.Controls.create(shape, name=label.replace(" ", ""))
        # view-layer deselect, not object.select_all: the op polls Object Mode and reads
        # screen context (dead under the Qt pump); select_set is mode-independent.
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ctrl.select_set(True)
        bpy.context.view_layer.objects.active = ctrl

    # ------------------------------------------------------------------ list001  Convert
    def list001_init(self, widget):
        """Initialize Convert list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_down")
        root = widget.add("Convert")
        root.sublist.setMinimumWidth(180)
        root.sublist.add(list(self._CONVERT_TARGETS) + list(self._CONVERT_EXTRA))

    @Signals("on_item_interacted")
    def list001(self, item):
        """Convert the selected object(s) to another type (or run a Convert-list action that
        isn't itself a ``bpy.ops.object.convert`` target — see ``_CONVERT_EXTRA``)."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()

        method_name = self._CONVERT_EXTRA.get(text)
        target = None if method_name else self._CONVERT_TARGETS.get(text)
        if not method_name and not target:
            return

        if not self.selected_objects():
            self.sb.message_box("Convert requires a selection.")
            return

        if method_name:
            getattr(self, method_name)()
        else:
            self._convert_selected(target)

    @btk.undoable
    def _convert_selected(self, target):
        # window override: convert's poll reads ``context.active_base`` and its exec reads the
        # context selection — both *screen*-context members, dead in the Qt-pump state. Force
        # Object Mode first (same guard list000 uses): convert poll-fails outside it.
        active = bpy.context.view_layer.objects.active
        with btk.window_context_override():
            try:
                if active and active.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.convert(target=target)
            except RuntimeError as e:  # e.g. a poll failure the guard didn't cover
                self.sb.message_box(str(e))

    @btk.undoable
    def _convert_instance_to_object(self):
        """Instance to Object — give the selection its own unique object-data, breaking the
        shared-data link a linked duplicate/instance has (Blender's analogue of Maya's
        ``convertInstanceToObject``)."""
        try:
            # window override: make_single_user's exec iterates
            # context.selected_editable_objects (screen context — empty in the Qt-pump
            # state), silently no-opping bare.
            with btk.window_context_override():
                bpy.ops.object.make_single_user(object=True, obdata=True)
        except RuntimeError as e:  # e.g. poll failure outside object mode
            self.sb.message_box(str(e))

    # ------------------------------------------------------------------ tool panels (blender_menus)
    def b000(self):
        """Cut On Axis"""
        self.sb.handlers.marking_menu.show("cut_on_axis")

    # ------------------------------------------------------------------ cmb000  Transfer
    # (combo label -> handler method) for the Transfer menu. Maya's single "Attribute Values"
    # op opens one dialog that can transfer vertex positions/normals/UVs/vertex colors all at
    # once; Blender's Data-Transfer operator works one data-layer at a time, so it's broken out
    # here into its natural granular items instead (Blender-idiomatic, per the cross-DCC naming
    # rule). "Shading Sets" maps 1:1 onto material-slot copying, renamed to Blender's own term.
    # Maya's other two Transfer items are intentionally NOT mirrored:
    #   - "Maps" is a Cycles selected-to-active bake (render engine + UV + image-target setup) —
    #     a separate, much larger feature; use Render Properties -> Bake directly meanwhile.
    #   - "Vertex Order" (interactive click-to-match reindexing) has no bpy operator or mesh-index
    #     remap primitive at all — there is nothing to wrap.
    _TRANSFER_OPS = {
        "UVs": "_transfer_uvs",
        "Vertex Colors": "_transfer_vertex_colors",
        "Vertex Group Weights": "_transfer_vertex_weights",
        "Custom Normals": "_transfer_custom_normals",
        "Material Slots": "_transfer_material_slots",
    }

    def cmb000_init(self, widget):
        """Initialize the Transfer operations menu."""
        widget.add(list(self._TRANSFER_OPS), header="Transfer:")

    def cmb000(self, index, widget):
        """Transfer — dispatch the selected transfer operation.

        Active object = source, other selected mesh object(s) = target(s) — Blender's native
        Data-Transfer/material-slot-copy convention, matching Maya's source-then-target(s)
        selection order for ``TransferAttributeValues``/``performTransferShadingSets``."""
        if index < 0:  # header / reset emission
            return
        label = widget.items[index]
        method = self._TRANSFER_OPS.get(label)
        if method:
            getattr(self, method)()

    @btk.undoable
    def _transfer_uvs(self):
        """UVs — native Data-Transfer of the active UV map (part of Maya's Attribute Values)."""
        if self.transfer_from_active(
            "UV", layers_select_src="ACTIVE", layers_select_dst="ACTIVE"
        ):
            self._report_transfer("UVs")

    @btk.undoable
    def _transfer_vertex_colors(self):
        """Vertex Colors — native Data-Transfer of the active color attribute, matched to its
        domain (point vs. face-corner) so both painted-per-vertex and painted-per-corner sets
        transfer correctly (part of Maya's Attribute Values)."""
        active = bpy.context.view_layer.objects.active
        data_type = self._color_attribute_data_type(active) if active else "COLOR_VERTEX"
        if self.transfer_from_active(
            data_type,
            vert_mapping="NEAREST",
            layers_select_src="ACTIVE",
            layers_select_dst="ACTIVE",
        ):
            self._report_transfer("Vertex Colors")

    @btk.undoable
    def _transfer_vertex_weights(self):
        """Vertex Group Weights — native Data-Transfer of every named vertex group, matched by
        name (Blender's counterpart to Maya's skin-weight transfer, itself part of Attribute
        Values)."""
        if self.transfer_from_active(
            "VGROUP_WEIGHTS",
            vert_mapping="NEAREST",
            layers_select_src="ALL",
            layers_select_dst="NAME",
        ):
            self._report_transfer("Vertex Group Weights")

    @btk.undoable
    def _transfer_custom_normals(self):
        """Custom Normals — native Data-Transfer of custom split normals (part of Maya's
        Attribute Values; same op as ``normals.py``'s b002)."""
        if self.transfer_from_active("CUSTOM_NORMAL"):
            self._report_transfer("Custom Normals")

    @btk.undoable
    def _transfer_material_slots(self):
        """Material Slots — copy the active object's material slots (and thus its shading) onto
        the other selected objects; Blender's counterpart to Maya's Shading Sets transfer
        (shading-group assignment)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active not in objects or len(objects) < 2:
            self.sb.message_box("Select target mesh(es) with the source (shaded) mesh active.")
            return
        try:
            # window override: material_slot_copy's exec iterates the context selection
            # (screen context — empty in the Qt-pump state), silently no-opping bare.
            with btk.window_context_override():
                bpy.ops.object.material_slot_copy()
        except RuntimeError as e:
            self.sb.message_box(str(e))
            return
        self._report_transfer("Material Slots")

    @staticmethod
    def _color_attribute_data_type(obj):
        """The Data-Transfer ``data_type`` matching ``obj``'s active color attribute's domain
        (point vs. face-corner) — defaults to the point domain when the mesh has no color
        attribute yet (matches ``geometry.color_attribute_add``'s own default)."""
        attrs = getattr(getattr(obj, "data", None), "color_attributes", None)
        active = attrs.active_color if attrs else None
        return "COLOR_CORNER" if active and active.domain == "CORNER" else "COLOR_VERTEX"

    def _report_transfer(self, label):
        """Message-box + console summary shared by every Transfer op (mirrors Maya's
        ``_run_transfer`` feedback: quick popup + full source/target breakdown on the console)."""
        active = bpy.context.view_layer.objects.active
        targets = [
            o.name for o in self.selected_objects() if o is not active and o.type == "MESH"
        ]
        print(f"# Transfer '{label}': source=<{active.name}> target(s)={targets}")
        plural = "" if len(targets) == 1 else "s"
        self.sb.message_box(
            f"<b>Transferred {label}</b><br><hl>{active.name}</hl> → {len(targets)} "
            f"target{plural}"
        )

    # ------------------------------------------------------------------ deferred (Maya-specific)
    def tb001(self, widget):
        """Delete History — Blender has no construction history (modifier stack is non-destructive)."""
        self.sb.message_box("Delete History is not applicable in Blender (no construction history).")

    def tb004(self, widget):
        """Node Locking — Maya node locking has no Blender analogue."""
        self.sb.message_box("Node Locking is not applicable in Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
