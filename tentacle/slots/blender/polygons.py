# !/usr/bin/python
# coding=utf-8
import bpy
import pythontk as ptk
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class PolygonsSlots(SlotsBlender):
    """Blender port of the shared ``polygons`` menu.

    Per the §5 capability map almost everything is a native edit-mode operator
    (merge/inset/subdivide/bridge/bevel/poke/symmetrize/fill-holes) run on the user's
    component selection via :meth:`_edit_op`; separate is an object op; combine routes
    through ``btk.combine_objects`` (object join, optionally grouped by material /
    clustered by distance); boolean routes through ``btk.boolean_op`` (Boolean modifier).
    Circularize / Edit Edge Flow are **extension-backed** (LoopTools / Edit Mesh Tools,
    wrap-if-present via :meth:`_addon_op`); Wedge rides ``btk.wedge`` (bmesh spin about the
    hinge edge) and Snap Closest Verts rides ``btk.snap_closest_verts`` (KD-tree). Modal
    Maya tools without a non-modal Blender analogue (slide, invisible faces) are deferred
    with messages.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.polygons
        self.submenu = self.sb.loaded_ui.polygons_submenu

    def _edit_op(self, op, *args, **kwargs):
        """Run an edit-mode mesh operator on the user's component selection.

        Requires an active mesh already in Edit Mode (component workflows are selection-
        based — silently entering edit mode and select-all would operate on the wrong
        thing). Returns True when the op ran.
        """
        active = bpy.context.view_layer.objects.active
        if not (active and active.type == "MESH" and active.mode == "EDIT"):
            self.sb.message_box("Select components in Edit Mode first.")
            return False
        try:
            op(*args, **kwargs)
            return True
        except RuntimeError as e:
            self.sb.message_box(str(e))
            return False

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        # b007 / b011 reuse the Maya header objectNames (Bridge Interactive / Bevel) — the same
        # two quick-access tools, also present as static buttons in polygons#component#submenu.ui.
        widget.menu.add(
            "QPushButton", setText="Bridge Interactive", setObjectName="b007",
            setToolTip="Bridge the selected edge loops (adjust cuts / twist / smoothness in the "
            "operator redo panel — Blender's interactive-bridge idiom).",
        )
        widget.menu.add(
            "QPushButton", setText="Bevel", setObjectName="b011",
            setToolTip="Open the bevel window.",
        )

    # ------------------------------------------------------------------ tb-slots
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Merge Vertices")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Distance: ", setObjectName="s002",
            set_limits=[0, 10, 0.0001, 4], setValue=0.0001,
            setToolTip="Vertices within this distance are merged.",
        )
        # b005 reuses the Maya name/label (Set Distance) — cross-DCC rule.
        widget.option_box.menu.add(
            "QPushButton", setText="Set Distance", setObjectName="b005",
            setToolTip="Set the merge distance from two selected vertices (their gap, +0.1% so a "
            "merge would collapse them).\nWith any other selection, reset to the default.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Merge Vertices"""
        self._edit_op(
            bpy.ops.mesh.remove_doubles,
            threshold=widget.option_box.menu.s002.value(),
        )

    def b005(self):
        """Merge Vertices: Set Distance — set the merge threshold from two selected verts
        (their local-space gap +0.1%, matching Maya's adjust); any other selection resets it."""
        import bmesh

        spinbox = self.ui.tb000.option_box.menu.s002
        active = bpy.context.view_layer.objects.active
        coords = []
        if active and active.type == "MESH" and active.mode == "EDIT":
            bm = bmesh.from_edit_mesh(active.data)
            coords = [tuple(v.co) for v in bm.verts if v.select]
        if len(coords) == 2:
            spinbox.setValue(ptk.distance_between_points(*coords) * 1.001)
        else:
            spinbox.setValue(0.0001)  # default
            self.sb.message_box("Select exactly two vertices in Edit Mode to set the distance.")

    def tb002_init(self, widget):
        # chk021 / chk022 reuse the Maya names for the SAME options (By Material / Rename).
        widget.option_box.menu.setTitle("Separate")
        widget.option_box.menu.add(
            "QCheckBox", setText="By Material", setObjectName="chk021",
            setToolTip="Split by material assignment (else by loose connected parts).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Rename", setObjectName="chk022",
            setToolTip="Rename the resulting parts after the source object (<name>, <name>_part01 …).",
        )

    @btk.undoable
    def tb002(self, widget):
        """Separate (split the mesh into loose parts, or by material)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Separate requires a mesh selection.")
            return
        m = widget.option_box.menu
        try:
            btk.separate_objects(
                objects, by_material=m.chk021.isChecked(), rename=m.chk022.isChecked()
            )
        except RuntimeError as e:  # residual failures (hidden/linked mesh) — no raw traceback
            self.sb.message_box(str(e))

    def tb003_init(self, widget):
        # chk002 / s004 reuse Maya names for the SAME options.
        widget.option_box.menu.setTitle("Extrude")
        widget.option_box.menu.add(
            "QCheckBox", setText="Keep Faces Together", setObjectName="chk002", setChecked=True,
            setToolTip="Extrude the region as one (off = extrude each face individually).",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Offset: ", setObjectName="s004",
            set_limits=[-100, 100, 0.01, 3], setValue=0.0,
            setToolTip="Push the extruded geometry along its normals by this amount.",
        )

    @btk.undoable
    def tb003(self, widget):
        """Extrude (region together or per-face), then offset along normals."""
        m = widget.option_box.menu
        op = bpy.ops.mesh.extrude_region if m.chk002.isChecked() else bpy.ops.mesh.extrude_faces_move
        if not self._edit_op(op):
            return
        offset = m.s004.value()
        if offset:  # offset == 0 stays an extrude-in-place (Maya parity)
            # shrink_fatten needs a VIEW_3D region (poll-fails from the Qt-pump context
            # where the active area isn't the viewport) — run it under a viewport
            # override, same pattern as the base ``set_viewport_tool``.
            ctx = btk.get_view3d_context()
            if not ctx:
                self.sb.message_box(
                    "No 3D viewport available — extruded, but the offset was skipped."
                )
                return
            ctx = {k: v for k, v in ctx.items() if v is not None}
            try:
                with bpy.context.temp_override(**ctx):
                    bpy.ops.transform.shrink_fatten(value=offset)
            except RuntimeError as e:
                self.sb.message_box(str(e))

    def tb004_init(self, widget):
        # chk003 / chk004 / s003 reuse the Maya names for the SAME options.
        widget.option_box.menu.setTitle("Combine")
        widget.option_box.menu.add(
            "QCheckBox", setText="Group by Material", setObjectName="chk003",
            setToolTip="Join into one mesh per material assignment instead of a single mesh.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Cluster by Distance", setObjectName="chk004",
            setToolTip="Further split each material group by spatial proximity — objects farther "
            "apart than the threshold stay in separate meshes.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Threshold: ", setObjectName="s003",
            set_limits=[0, 100000, 1, 2], setValue=10000.0,
            setToolTip="Maximum distance between objects to be considered part of the same cluster.",
        )
        # Threshold only matters while clustering (mirror of the Maya panel).
        chk_cluster = widget.option_box.menu.chk004
        spin = widget.option_box.menu.s003
        spin.setEnabled(chk_cluster.isChecked())
        chk_cluster.toggled.connect(spin.setEnabled)

    @btk.undoable
    def tb004(self, widget):
        """Combine Selected Meshes (optionally one mesh per material / clustered by distance)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if len(objects) < 2:
            self.sb.message_box("Combine requires 2+ selected meshes.")
            return
        m = widget.option_box.menu
        try:
            btk.combine_objects(
                objects,
                group_by_material=m.chk003.isChecked(),
                cluster_by_distance=m.chk004.isChecked(),
                threshold=m.s003.value(),
            )
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def tb005_init(self, widget):
        # chk014 / chk015 / chk020 reuse the Maya names for the SAME options.
        widget.option_box.menu.setTitle("Detach")
        widget.option_box.menu.add(
            "QCheckBox", setText="Duplicate", setObjectName="chk014", setChecked=True,
            setToolTip="Leave the original faces in place and detach a COPY of the selection.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Separate Extracted Faces", setObjectName="chk015", setChecked=True,
            setToolTip="Move the detached faces into a NEW object (off = split them off in place, "
            "staying within the same mesh).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Separate Each Face", setObjectName="chk020",
            setToolTip="Each detached face becomes its own separate object.",
        )

    @btk.undoable
    def tb005(self, widget):
        """Detach (separate selected components into a new object; optionally a copy / per-face)."""
        active = bpy.context.view_layer.objects.active
        if not (active and active.type == "MESH" and active.mode == "EDIT"):
            self.sb.message_box("Select faces in Edit Mode first.")
            return
        m = widget.option_box.menu
        btk.detach_components(
            duplicate=m.chk014.isChecked(),
            separate=m.chk015.isChecked(),
            separate_each=m.chk020.isChecked(),
        )

    def tb006_init(self, widget):
        # s001 mirrors Maya's inset "Offset" spinbox (same objectName/label) — it drives
        # Blender's inset thickness.
        widget.option_box.menu.setTitle("Inset Face Region")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Offset: ", setObjectName="s001",
            set_limits=[0, 100, 0.01, 3], setValue=0.1,
            setToolTip="Inset offset (thickness).",
        )
        # chk018 / s010: Blender-only options (free in maya/polygons.py — no state bleed).
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Depth: ", setObjectName="s010",
            set_limits=[-100, 100, 0.01, 3], setValue=0.0,
            setToolTip="Raise/lower the inset region along its normal.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Individual Faces", setObjectName="chk018",
            setToolTip="Inset each selected face separately (else as one region).",
        )

    @btk.undoable
    def tb006(self, widget):
        """Inset Face Region"""
        m = widget.option_box.menu
        self._edit_op(
            bpy.ops.mesh.inset,
            thickness=m.s001.value(),
            depth=m.s010.value(),
            use_individual=m.chk018.isChecked(),
        )

    def tb007_init(self, widget):
        # chk010 reuses the Maya name for the SAME option ("Tris").
        widget.option_box.menu.setTitle("Divide Facet")
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Cuts: ", setObjectName="s009",
            set_limits=[1, 10], setValue=1,
            setToolTip="Number of subdivision cuts.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Tris", setObjectName="chk010",
            setToolTip="Triangulate the result.",
        )

    @btk.undoable
    def tb007(self, widget):
        """Divide Facet (subdivide the selected components)."""
        m = widget.option_box.menu
        if not self._edit_op(bpy.ops.mesh.subdivide, number_cuts=m.s009.value()):
            return
        if m.chk010.isChecked():
            try:
                bpy.ops.mesh.quads_convert_to_tris()
            except RuntimeError as e:
                self.sb.message_box(str(e))

    def tb008_init(self, widget):
        # chk017 reuses the Maya name for the SAME option (Maya "Interactive" = a live/editable
        # boolean; the Blender analogue is keeping the Boolean modifier non-destructive).
        widget.option_box.menu.setTitle("Boolean Operation")
        widget.option_box.menu.add(
            "QComboBox", addItems=["Difference", "Union", "Intersection"],
            setObjectName="cmb011", setToolTip="Boolean operation (active = base).",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Interactive", setObjectName="chk017",
            setToolTip="Keep the Boolean modifier live (non-destructive) instead of baking it.",
        )

    @btk.undoable
    def tb008(self, widget):
        """Boolean Operation (active mesh = base, other selected = operands)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active in objects:  # base first (Maya's order-matters convention)
            objects = [active] + [o for o in objects if o is not active]
        if len(objects) < 2:
            self.sb.message_box("Boolean requires 2+ selected meshes (active = base).")
            return
        operation = {
            "Difference": "DIFFERENCE", "Union": "UNION", "Intersection": "INTERSECT"
        }[widget.option_box.menu.cmb011.currentText()]
        try:
            btk.boolean_op(
                objects, operation=operation,
                apply=not widget.option_box.menu.chk017.isChecked(),
            )
        except RuntimeError as e:  # residual failures (non-evaluable operand) — no raw traceback
            self.sb.message_box(str(e))

    def tb009_init(self, widget):
        widget.option_box.menu.setTitle("Snap Closest Verts")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Tolerance: ", setObjectName="s005",
            set_limits=[0, 100, 0.05, 3], setValue=10,
            setToolTip="Maximum snap distance — vertices farther than this are ignored.",
        )
        # Maya's "Freeze Transforms" option (chk016) is NOT mirrored: it was a cmds
        # world-query workaround, and ``btk.snap_closest_verts``'s world math is exact
        # under any transform — freezing here only zeroed both objects' channels.

    @btk.undoable
    def tb009(self, widget):
        """Snap Closest Verts (the other selected mesh's verts snap onto the ACTIVE mesh)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if len(objects) != 2 or active not in objects:
            self.sb.message_box(
                "<strong>Select two mesh objects</strong> — the active object is the "
                "snap target."
            )
            return
        source = next(o for o in objects if o is not active)
        moved = btk.snap_closest_verts(
            source, active, tolerance=widget.option_box.menu.s005.value()
        )
        if not moved:
            self.sb.message_box("No vertices within the snap tolerance.")

    # ------------------------------------------------------------------ b-slots (component ops)
    @btk.undoable
    def b001(self):
        """Fill Holes"""
        self._edit_op(bpy.ops.mesh.fill_holes, sides=0)

    @btk.undoable
    def b003(self):
        """Symmetrize"""
        self._edit_op(bpy.ops.mesh.symmetrize)

    @btk.undoable
    def b006(self):
        """Bridge (selected edge loops)."""
        self._edit_op(bpy.ops.mesh.bridge_edge_loops)

    def b007(self):
        """Bridge Interactive — open the Bridge panel (Divisions / Offset + live Preview),
        served from blendertk by the BlenderUiHandler, mirroring Maya's bridge window (b006
        stays the quick one-shot bridge)."""
        self.sb.handlers.marking_menu.show("bridge")

    def b008(self):
        """Weld Center: interactive target weld merging at the midpoint (mirror of Maya's
        MergeVertexTool with mergeToCenter=True; the one-shot merge-selected-at-center
        remains on b009 Collapse)."""
        self._target_weld(merge_to_center=True)

    @btk.undoable
    def b009(self):
        """Collapse Component (Maya-twin split: a face mask collapses per-region
        [PolygonCollapse]; verts/edges merge at one shared CENTER [MergeToCenter] —
        COLLAPSE alone left disconnected components unmerged)."""
        _, _, face = bpy.context.tool_settings.mesh_select_mode
        self._edit_op(bpy.ops.mesh.merge, type="COLLAPSE" if face else "CENTER")

    def b011(self):
        """Bevel — open the bevel panel (Width / Segments / Profile + live Preview),
        served from blendertk by the BlenderUiHandler, mirroring Maya's bevel window."""
        self.sb.handlers.marking_menu.show("bevel")

    def b012(self):
        """Multi-Cut Tool (Knife) — EDIT_MESH-only, so the mesh is put into component mode."""
        self.set_viewport_tool("builtin.knife", "Multi-Cut", edit_type="MESH")

    @btk.undoable
    def b022(self):
        """Attach — Maya's Connect-components tool (dR_connectTool; the shared tooltip says
        "Connect vertices edges and polygons"): connect the selected verts/edges with new
        edges, not an object join."""
        obj = self.ensure_edit_mode("MESH")
        if not obj:
            self.sb.message_box("Attach requires a mesh with components selected in Edit Mode.")
            return
        import bmesh

        # Headless-verified (Blender 5.1): vert_connect_path works from the interactive
        # pick-order history but raises "Invalid selection order" without it, and the
        # vert_connect fallback can FINISH while connecting nothing — so success is judged
        # by the edge count, not by the ops' return.
        edges_before = len(bmesh.from_edit_mesh(obj.data).edges)
        try:
            with btk.window_context_override():
                bpy.ops.mesh.vert_connect_path()
        except RuntimeError:
            try:  # unordered / cross-face selections that the path op rejects
                with btk.window_context_override():
                    bpy.ops.mesh.vert_connect()
            except RuntimeError:
                pass
        if len(bmesh.from_edit_mesh(obj.data).edges) == edges_before:
            self.sb.message_box(
                "<strong>Nothing connected.</strong><br>Click two or more vertices on the "
                "mesh (in order) to connect them across a face."
            )

    @btk.undoable
    def b032(self):
        """Poke"""
        self._edit_op(bpy.ops.mesh.poke)

    def b047(self):
        """Insert Edgeloop (Loop Cut tool) — EDIT_MESH-only, so the mesh is put into
        component mode."""
        self.set_viewport_tool("builtin.loop_cut", "Insert Edgeloop", edit_type="MESH")

    @btk.undoable
    def b051(self):
        """Offset Edgeloop"""
        self._edit_op(bpy.ops.mesh.offset_edge_loops)

    def b043(self):
        """Target Weld: interactively merge one vertex onto another by dragging."""
        self._target_weld(merge_to_center=False)

    def _target_weld(self, merge_to_center):
        """Launch blendertk's interactive Target Weld tool (the Blender build of Maya's
        MergeVertexTool — b043 welds at the target, b008 at the midpoint). The engine
        handles the Maya-slot activation prep (Edit mode, vertex mask, deselect)."""
        try:
            btk.target_weld(merge_to_center=merge_to_center)
        except RuntimeError as e:
            self.sb.message_box(str(e))

    def _addon_op(self, op_name, label, addon):
        """Run an extension-provided edit-mode operator if its add-on is installed,
        otherwise point the user at the extension (wrap-if-present — the add-on is the
        canonical implementation; don't rebuild it)."""
        op = getattr(bpy.ops.mesh, op_name)
        try:
            op.get_rna_type()  # raises when the operator isn't registered
        except Exception:
            self.sb.message_box(
                f"<strong>{label}</strong> requires the <b>{addon}</b> add-on — install "
                "it via Edit ▸ Preferences ▸ Get Extensions, then retry."
            )
            return
        self._edit_op(op)

    # ------------------------------------------------------------------ extension-backed
    @btk.undoable
    def b000(self):
        """Circularize (LoopTools Circle on the selected edge loop)."""
        self._addon_op("looptools_circle", "Circularize", "LoopTools")

    @btk.undoable
    def b053(self):
        """Edit Edge Flow (Set Flow on the selected edge loops)."""
        self._addon_op("set_edge_flow", "Edit Edge Flow", "Edit Mesh Tools (or Loop Flow)")

    # ------------------------------------------------------------------ deferred (modal / no analogue)

    @btk.undoable
    def b034(self):
        """Wedge (sweep the selected faces 90° around a selected hinge edge)."""
        wedged = btk.wedge(self.selected_objects(), angle=90.0, divisions=4)
        if not wedged:
            self.sb.message_box(
                "<strong>Wedge requires Edit Mode</strong> with face(s) selected plus one "
                "edge of those faces (the hinge — the active edge wins)."
            )

    def b038(self):
        """Assign Invisible — Maya invisible faces have no Blender analogue."""
        self.sb.message_box("Assign Invisible is not applicable in Blender.")

    def b049(self):
        """Slide Edge — modal in Blender (GG); no persistent tool."""
        self.sb.message_box("Slide Edge is modal in Blender — press GG on an edge selection.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
