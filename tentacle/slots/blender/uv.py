# !/usr/bin/python
# coding=utf-8
import math

import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Uv(SlotsBlender):
    """Blender port of the shared ``uv`` menu.

    Core UV operators (unwrap, the cmb011 Smart/Cube/Cylinder/Sphere projections, pack, seam,
    angle-band hard-edge cut) run as ``bpy.ops.uv.*`` in edit mode via :meth:`_uv_op` (verified to
    work headless). Data-level UV work (pin/stack/texel density/UV-set cleanup) is backed by
    ``blendertk.uv_utils`` (bmesh — headless); move/transform/mirror/straighten/distribute live in
    the blendertk ``shell_xform`` panel (launched via b033); UV transfer rides the native
    Data-Transfer operator; RizomUV is a one-way bridge. The deferred Maya-only depth is in the
    parity overrides (RizomUV/u3dLayout packing params + the unwrap_cylinder crease algorithm).
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
        """Run a UV/seam operator on the selected meshes in edit mode (all selected), then
        restore the caller's active object and mode. Returns False (with a message) if there's
        no mesh selection."""
        meshes = [o for o in self.selected_objects() if o.type == "MESH"]
        if not meshes:
            self.sb.message_box("UV operation requires a mesh selection.")
            return False
        active = bpy.context.view_layer.objects.active
        prior = getattr(active, "mode", "OBJECT")
        # window override: mode_set / mesh.select_all / the uv op itself all poll the active
        # object from *screen* context — dead in the Qt-pump state (no-op when a window exists).
        with btk.window_context_override():
            if prior != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            # view-layer deselect, not object.select_all: the op polls Object Mode and reads
            # screen context; select_set is mode-independent and pump-safe.
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            for o in meshes:
                o.select_set(True)
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            try:
                op()
            finally:
                # ``prior`` belongs to the ORIGINAL active object — meshes[0] is active here,
                # so leave Edit Mode first, then re-activate and re-mode the original (if it
                # still exists). Never let a restore failure mask the op's own result.
                try:
                    bpy.ops.object.mode_set(mode="OBJECT")
                    if active and active.name in bpy.context.view_layer.objects:
                        bpy.context.view_layer.objects.active = active
                        if prior != "OBJECT":
                            bpy.ops.object.mode_set(mode=prior)
                except (RuntimeError, ReferenceError):
                    pass  # e.g. the op removed the original active
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

    @staticmethod
    def _selection_fingerprint(objects):
        """Toggle key for the b029/b030 dual-state toggles: object names PLUS a per-object
        fingerprint of the Edit-Mode component selection (the vert scope ``btk.pin_uvs`` /
        ``btk.stack_uv_shells`` act on). Names alone invert the intent when only the
        component selection changes on the same objects — the second click would "un-do"
        onto the wrong components; a changed selection now starts a fresh toggle cycle.
        Object mode contributes a whole-map marker (no component scope)."""
        import bmesh

        parts = []
        for o in sorted(objects, key=lambda o: o.name):
            if o.mode == "EDIT":
                bm = bmesh.from_edit_mesh(o.data)
                sel = tuple(v.index for v in bm.verts if v.select)
                parts.append((o.name, len(sel), hash(sel)))
            else:
                parts.append((o.name, -1, 0))  # whole map — no component scope
        return tuple(parts)

    # ------------------------------------------------------------------ UV operators (edit mode)
    # Option-box names are Blender-specific (Maya's UV option boxes carry RizomUV-style packing
    # params with no Blender analogue): they expose the native operator's own parameters.
    def tb000_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Pack UVs")
        # cmb009 reuses the Maya objectName + labels (same Pre-Scale-Mode option, cross-DCC rule):
        # "Preserve 3D" runs a native average-islands-scale pass (equal texel density) before
        # packing; "Preserve UV" skips it and keeps each shell's current relative proportions.
        cmb009 = m.add(
            "QComboBox", setObjectName="cmb009",
            setToolTip="How shells are scaled before packing.\n"
            "Preserve UV: keep each shell's current relative UV proportions.\n"
            "Preserve 3D: rescale every shell to equal texel density "
            "(bpy.ops.uv.average_islands_scale).",
        )
        for text, data in (("Pre-Scale: Preserve UV", 0), ("Pre-Scale: Preserve 3D", 1)):
            cmb009.addItem(text, data)
        cmb009.setCurrentIndex(1)  # matches Maya's default (Preserve 3D)
        m.add(
            "QDoubleSpinBox", setPrefix="Margin: ", setObjectName="s_pack_margin",
            set_limits=[0, 1, 0.001, 3], setValue=0.001,
            setToolTip="Spacing left between packed islands.",
        )
        m.add(
            "QCheckBox", setText="Rotate Islands", setObjectName="chk_pack_rotate", setChecked=True,
            setToolTip="Allow islands to rotate for a tighter pack.",
        )
        # s004 reuses the Maya objectName + label (same target-UDIM-tile option, cross-DCC
        # rule): Blender's pack_islands has no target-tile parameter (no packBox analogue) —
        # and on 4.x+ it defaults udim_source='CLOSEST_UDIM', packing islands into whichever
        # tile they already occupy, NOT 0-1 — so tb000 reads the tile actually packed into
        # afterward and moves the map by the delta into this tile.
        m.add(
            "QSpinBox", setPrefix="UDIM: ", setObjectName="s004",
            set_limits=[1001, 1200], setValue=1001,
            setToolTip="Target UDIM tile (1001-1200). After packing, the map is moved into "
            "this tile (1001 = the first 0-1 tile).",
        )

    @btk.undoable
    def tb000(self, widget):
        """Pack UVs (optionally equal-texel-density pre-scaled), then moved into the target
        UDIM tile by the delta from the tile actually packed into."""
        m = widget.option_box.menu
        preserve_3d = m.cmb009.currentData() == 1  # Pre-Scale Mode: 1 = Preserve 3D

        def _pack():
            if preserve_3d:
                # Preserve 3D: rescale islands to equal texel density before packing.
                bpy.ops.uv.average_islands_scale()
            bpy.ops.uv.pack_islands(
                margin=m.s_pack_margin.value(), rotate=m.chk_pack_rotate.isChecked()
            )

        try:
            if not self._uv_op(_pack):
                return
        except RuntimeError:  # average_islands_scale/pack_islands poll-fail without a UV layer
            self.sb.message_box("No UVs found on the selection.")
            return
        # 4.x+ pack_islands defaults udim_source='CLOSEST_UDIM' — islands already in another
        # tile pack into THAT tile, not 0-1, so a blind fixed shift would land the map in the
        # wrong tile. Read the tile actually packed into (floor of the achieved min u/v) and
        # move by the DELTA to the requested one.
        udim = m.s004.value()
        u_tile, v_tile = (udim - 1001) % 10, (udim - 1001) // 10
        objects = self.selected_objects()  # _uv_op selected exactly the target meshes
        snapshot = btk.get_uv_coords(objects)
        if not snapshot:
            return
        u_min = min(u for coords in snapshot.values() for u, _ in coords)
        v_min = min(v for coords in snapshot.values() for _, v in coords)
        du, dv = u_tile - math.floor(u_min), v_tile - math.floor(v_min)
        if du or dv:
            btk.move_uvs(objects, du=float(du), dv=float(dv))

    # cmb011 projection method -> the native Blender projection op (Maya's projection-method
    # selector; reuses the Maya objectName, cross-DCC rule). Smart uses the angle/margin below;
    # Cube/Cylinder/Sphere project from the object bounds (no per-mode options, like Maya gates).
    _PROJECTION_OPS = {
        "Cube": "cube_project", "Cylinder": "cylinder_project", "Sphere": "sphere_project",
    }
    _PROJECTIONS = ("Smart", *_PROJECTION_OPS)  # Smart needs args; the rest map 1:1 to an op

    def tb001_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Auto Unwrap")
        m.add(
            "QComboBox", addItems=list(self._PROJECTIONS), setObjectName="cmb011",
            setToolTip="Projection method used to generate UVs (Blender native projections).\n"
            "Smart: best-fit from multiple planar projections.\n"
            "Cube / Cylinder / Sphere: project from the object's bounds.",
        )
        m.add(
            "QSpinBox", setPrefix="Angle Limit: ", setObjectName="s_smart_angle",
            set_limits=[1, 89], setValue=66,
            setToolTip="Lower = more islands (Smart UV Project angle limit, degrees). Smart only.",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Island Margin: ", setObjectName="s_smart_margin",
            set_limits=[0, 1, 0.001, 3], setValue=0.0,
            setToolTip="Spacing between the generated islands. Smart only.",
        )

        def _sync():  # Smart-only params disable for the single-shape projections
            smart = m.cmb011.currentText() == "Smart"
            m.s_smart_angle.setEnabled(smart)
            m.s_smart_margin.setEnabled(smart)

        m.cmb011.currentIndexChanged.connect(_sync)
        _sync()

    @btk.undoable
    def tb001(self, widget):
        """Auto Unwrap (Smart UV Project / Cube / Cylinder / Sphere projection)."""
        m = widget.option_box.menu
        method = m.cmb011.currentText()
        if method == "Smart":
            self._uv_op(
                lambda: bpy.ops.uv.smart_project(
                    angle_limit=math.radians(m.s_smart_angle.value()),
                    island_margin=m.s_smart_margin.value(),
                )
            )
        else:
            op = getattr(bpy.ops.uv, self._PROJECTION_OPS[method])
            # scale_to_bounds: fit the projection into the 0-1 square (the option-box tooltip
            # promises bounds projection; Maya's smartFit default) — at the default False
            # these ops project at absolute unit scale.
            self._uv_op(lambda: op(scale_to_bounds=True))

    # method enum -> friendly label (Minimum Stretch only exists on newer Blender; guarded).
    _UNWRAP_METHODS = {"Angle Based": "ANGLE_BASED", "Conformal": "CONFORMAL"}

    def tb004_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Unfold")
        m.add(
            "QComboBox", addItems=list(self._UNWRAP_METHODS), setObjectName="cmb_unfold_method",
            setToolTip="Unwrap algorithm.",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Margin: ", setObjectName="s_unfold_margin",
            set_limits=[0, 1, 0.001, 3], setValue=0.0,
            setToolTip="Spacing between islands after unwrap.",
        )
        # Maya parity: post-unwrap relax (Optimize) + axis-align (Orient). Reuses Maya's
        # chk017/chk007 names + labels (same options, cross-DCC QSettings rule).
        m.add(
            "QCheckBox", setText="Optimize", setObjectName="chk017", setChecked=True,
            setToolTip="Relax the unwrap to even out UV spacing (Minimize Stretch).",
        )
        m.add(
            "QCheckBox", setText="Orient", setObjectName="chk007", setChecked=True,
            setToolTip="Rotate each shell parallel to the nearest U/V axis (Align Rotation).",
        )
        # chk022/s000 reuse the Maya objectNames + labels (same options, cross-DCC rule):
        # post-unfold similarity-gated stacking (btk.stack_uv_shells(tolerance=...)).
        m.add(
            "QCheckBox", setText="Stack Similar", setObjectName="chk022", setChecked=True,
            setToolTip="Stack only shells that fall within the set tolerance.",
        )
        m.add(
            "QDoubleSpinBox", setPrefix="Tolerance: ", setObjectName="s000",
            set_limits=[0, 10, 0.1, 1], setValue=1.0,
            setToolTip="Stack shells with uv's within the given range.",
        )

    @btk.undoable
    def tb004(self, widget):
        """Unfold (unwrap, then optionally relax, axis-align, and stack similar shells)."""
        m = widget.option_box.menu
        method = self._UNWRAP_METHODS.get(m.cmb_unfold_method.currentText(), "ANGLE_BASED")
        optimize = m.chk017.isChecked()
        orient = m.chk007.isChecked()
        stack_similar = m.chk022.isChecked()
        tolerance = m.s000.value()

        def _run():
            bpy.ops.uv.unwrap(method=method, margin=m.s_unfold_margin.value())
            if optimize:
                bpy.ops.uv.minimize_stretch(iterations=10)
            if orient:
                bpy.ops.uv.align_rotation(method="AUTO")
            if stack_similar:
                btk.stack_uv_shells(self.selected_objects(), tolerance=tolerance)

        try:
            self._uv_op(_run)
        except RuntimeError:  # uv.* poll failure without a UV layer
            self.sb.message_box("No UVs found on the selection.")

    def tb009_init(self, widget):
        # s016/chk041/chk042 reuse the Maya names + labels for the SAME options. chk040 (Invert
        # Seam) has no Blender analogue — the auto-seam path places the lengthwise cut itself.
        m = widget.option_box.menu
        m.setTitle("Cut Cylinder")
        m.add(
            "QDoubleSpinBox", setPrefix="Crease Angle: ", setObjectName="s016",
            set_limits=[1, 179], setValue=45.0, setSuffix="°",
            setToolTip="Edges sharper than this angle (degrees) become UV seams — cuts ~90° steps "
            "and cap rings while keeping shallow chamfers merged.",
        )
        m.add(
            "QCheckBox", setText="Unfold", setObjectName="chk041", setChecked=True,
            setToolTip="Unwrap (flatten) after seaming. Off = only cut the crease seams.",
        )
        m.add(
            "QCheckBox", setText="Orient", setObjectName="chk042", setChecked=True,
            setToolTip="Rotate each shell parallel to the nearest U/V axis when packing.",
        )

    @btk.undoable
    def tb009(self, widget):
        """Cut Cylinder — seam by crease angle, then unfold. The Blender equivalent of Maya's
        unwrap_cylinder: Smart UV Project auto-seams a tube/turned mesh by angle (cap rings + one
        lengthwise cut) and unwraps it to clean strips; Unfold off only marks the crease seams."""
        m = widget.option_box.menu
        angle = math.radians(m.s016.value())
        unfold = m.chk041.isChecked()
        orient = m.chk042.isChecked()

        def _run():
            if unfold:
                bpy.ops.uv.smart_project(angle_limit=angle, island_margin=0.003)
                try:
                    bpy.ops.uv.pack_islands(rotate=orient, margin=0.003)
                except TypeError:  # older Blender pack_islands signature
                    bpy.ops.uv.pack_islands(margin=0.003)
            else:  # cut crease seams only (no unwrap)
                bpy.ops.mesh.select_all(action="DESELECT")
                bpy.ops.mesh.edges_select_sharp(sharpness=angle)
                bpy.ops.mesh.mark_seam(clear=False)

        self._uv_op(_run)

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
        try:
            self._uv_op(
                lambda: (bpy.ops.uv.unwrap(method="ANGLE_BASED"), bpy.ops.uv.pack_islands())
            )
        except RuntimeError:  # uv.* poll failure without a UV layer
            self.sb.message_box("No UVs found on the selection.")

    # ------------------------------------------------------------------ tb007  Cleanup UV Sets
    def tb007_init(self, widget):
        """Cleanup UV Sets option box (reuses the Maya objectNames + labels — same options,
        cross-DCC QSettings rule)."""
        m = widget.option_box.menu
        m.setTitle("Cleanup UV Sets")
        m.add(
            "QCheckBox", setText="Prefer Best Layout", setObjectName="chk029", setChecked=True,
            setToolTip="Keep the UV set with the largest UV footprint, not just the first one.",
        )
        m.add(
            "QCheckBox", setText="Remove Empty Sets", setObjectName="chk035", setChecked=True,
            setToolTip="Delete UV sets whose UVs are all at the origin (never unwrapped).",
        )
        m.add(
            "QCheckBox", setText="Delete Secondary Sets", setObjectName="chk036",
            setToolTip="Delete ALL other UV sets, leaving only the kept one.",
        )
        m.add(
            "QCheckBox", setText="Rename to 'map1'", setObjectName="chk037", setChecked=True,
            setToolTip="Rename the kept UV set to 'map1' (Maya's default — export pipeline parity).",
        )
        m.add(
            "QCheckBox", setText="Force Rename", setObjectName="chk038",
            setToolTip="If another set is already named 'map1', overwrite it instead of skipping.",
        )
        m.add(
            "QCheckBox", setText="Dry Run", setObjectName="chk030",
            setToolTip="Report what would change without modifying anything.",
        )

    @btk.undoable
    def tb007(self, widget):
        """Cleanup UV Sets (standardize/clean the UV layers — mirror of Maya's cleanup_uv_sets)."""
        m = widget.option_box.menu
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("<b>Nothing selected.</b><br>Select mesh object(s) with UV sets.")
            return
        dry_run = m.chk030.isChecked()
        results = btk.cleanup_uv_sets(
            objects,
            remove_empty=m.chk035.isChecked(),
            keep_only_primary=m.chk036.isChecked(),
            rename_to_map1=m.chk037.isChecked(),
            force_rename=m.chk038.isChecked(),
            prefer_largest_area=m.chk029.isChecked(),
            dry_run=dry_run,
        )
        verb, del_verb = ("Would keep", "would delete") if dry_run else ("Kept", "deleted")
        lines = []
        for r in results:
            if r.error:
                lines.append(f"❌ <b>{r.object}</b>: {r.error}")
                continue
            detail = f"{verb} '<b>{r.primary_set}</b>'"
            if r.final_name != r.primary_set:
                detail += f" → '<b>{r.final_name}</b>'"
            if r.deleted:
                detail += f", {del_verb} {len(r.deleted)} other(s)"
            lines.append(f"• <b>{r.object}</b>: {detail}")
        header = "<b>Dry Run</b>" if dry_run else "<b>Cleanup Complete</b>"
        self.sb.message_box(f"{header}<br><br>" + "<br>".join(lines))

    def header_init(self, widget):
        """Header menu — Create UV Snapshot + RizomUV Bridge (reuse the Maya objectNames + labels,
        cross-DCC QSettings rule). Open UV Editor is already on ``b031``; Shell Xform is the
        ``More..`` button in the Transform group (``b033``)."""
        widget.menu.add(
            "QPushButton", setText="Create UV Snapshot", setObjectName="uv_snapshot",
            setToolTip="Export the active mesh's UV layout to an image (native Export UV Layout) "
            "as a texture-painting reference.",
        )
        widget.menu.add(
            "QPushButton", setText="RizomUV Bridge", setObjectName="btn_rizom_bridge",
            setToolTip="Export the selected meshes and open them in a fresh RizomUV session "
            "(one-way send via a Lua load-script).",
            clicked=lambda: self.b032(),
        )

    def uv_snapshot(self):
        """Create UV Snapshot — export the active mesh's UV layout to an image."""
        obj = self.active_object()
        if not (obj and obj.type == "MESH" and obj.data.uv_layers):
            self.sb.message_box("Create UV Snapshot requires a mesh with a UV map.")
            return
        self.invoke_op("uv.export_layout")

    # ------------------------------------------------------------------ b031  Open UV Editor
    def b031(self):
        """Open UV Editor"""
        btk.open_editor("UV Editor")

    # ------------------------------------------------------------------ b000  Transfer UVs
    @btk.undoable
    def b000(self, widget):
        """Transfer UVs (active mesh → other selected, native Data-Transfer)."""
        self.transfer_from_active(
            "UV", layers_select_src="ACTIVE", layers_select_dst="ACTIVE"
        )

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
    def b029_init(self, widget):
        """Initialize Pin/Unpin button — non-checkable text button.

        Defensively clears any `checkable` property a Qt Designer round-trip
        may have re-added (the button's "Pin" label lives in the .ui).
        """
        widget.setCheckable(False)

    def b029(self, widget):
        """Pin / Unpin UVs (dual-state toggle, Maya parity: first click on a fresh selection
        pins, the next unpins; selection change resets. Edit mode pins the selected verts'
        UVs, object mode the whole map)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Nothing selected.")
            return
        signature = self._selection_fingerprint(objects)
        if self._b029_last_selection != signature:
            self._b029_pinned = False  # fresh selection — start with Pin
        self._b029_pinned = not self._b029_pinned
        btk.pin_uvs(
            objects, pin=self._b029_pinned,
            selected_only=any(o.mode == "EDIT" for o in objects),
        )
        self._b029_last_selection = signature

    # ------------------------------------------------------------------ tb022  Cut Hard Edges
    def tb022_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Cut Hard Edges")
        m.add(
            "QDoubleSpinBox", setPrefix="Angle Low:  ", setObjectName="s017",
            set_limits=[0, 180], setValue=70,
            setToolTip="Lower bound: edges whose dihedral angle is at least this are seam-cut.",
        )
        # s018 / chk025 reuse the Maya objectNames + labels (same options, cross-DCC rule).
        m.add(
            "QDoubleSpinBox", setPrefix="Angle High: ", setObjectName="s018",
            set_limits=[0, 180], setValue=180,
            setToolTip="Upper bound of the seam-cut angle band (180 = no upper limit).",
        )
        m.add(
            "QCheckBox", setText="Include UV Borders", setObjectName="chk025",
            setToolTip="Also mark seams at the current UV island borders (Seams From Islands).",
        )
        # chk026 reuses the Maya objectName + label (same option, cross-DCC rule): a temporary
        # Smart UV Project decomposition stands in for u3dAutoSeam (btk.derive_auto_seams).
        m.add(
            "QCheckBox", setText="Include Auto Seams", setObjectName="chk026",
            setToolTip="Also cut seams auto-detected via a temporary Smart UV Project pass.",
        )

    @btk.undoable
    def tb022(self, widget):
        """Cut UV Hard Edges (mark seams on edges whose dihedral angle is in the [low, high]
        band, optionally also at existing UV island borders and/or Smart-Project-derived auto
        seams)."""
        m = widget.option_box.menu
        low, high = m.s017.value(), m.s018.value()
        include_borders = m.chk025.isChecked()
        include_auto_seams = m.chk026.isChecked()
        objects = [o for o in self.selected_objects() if o.type == "MESH"]

        def _run():
            if include_borders:
                try:
                    bpy.ops.uv.seams_from_islands()
                except RuntimeError:
                    pass  # a mesh without a UV layer has no islands to seam — skip
            if include_auto_seams:
                btk.derive_auto_seams(objects)
            # btk.select_edges_by_angle gives the [low, high] band (mesh.edges_select_sharp is a
            # single lower threshold); then seam the selection.
            if btk.select_edges_by_angle(objects, low_angle=low, high_angle=high):
                bpy.ops.mesh.mark_seam(clear=False)

        self._uv_op(_run)

    # ------------------------------------------------------------------ shell ops (btk islands)
    def b030_init(self, widget):
        """Initialize Stack button — non-checkable text button.

        Defensively clears any `checkable` property a Qt Designer round-trip
        may have re-added (the button's "Stack" label lives in the .ui).
        """
        widget.setCheckable(False)

    @btk.undoable
    def b030(self, widget):
        """Stack / Unstack shells (dual-state toggle: first click stacks the targeted
        shells at a shared center and captures their positions; the next click restores
        them. A selection change resets the toggle)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("<b>Nothing selected.</b>")
            return
        signature = self._selection_fingerprint(objects)
        if getattr(self, "_b030_snapshot", None) and self._b030_signature == signature:
            btk.set_uv_coords(objects, self._b030_snapshot)
            self._b030_snapshot = None
            return
        snapshot = btk.get_uv_coords(objects)
        moved = btk.stack_uv_shells(objects)
        if moved:
            self._b030_snapshot = snapshot
            self._b030_signature = signature
        else:
            self._b030_snapshot = None
            self.sb.message_box(
                "<strong>No UV shells stacked.</strong><br>Needs at least two islands "
                "(in Edit Mode, shells touched by the selection)."
            )

    # ------------------------------------------------------------------ deferred (Maya / UV-editor)
    def b032(self):
        """RizomUV Bridge — co-located blendertk panel (export selection → launch RizomUV with a
        Lua load-script). Mirrors Maya's b032 → ``marking_menu.show("rizom_bridge")``."""
        self.sb.handlers.marking_menu.show("rizom_bridge")

    def b033(self):
        """Open the Shell Xform panel — the ``More..`` button in the Transform group.

        Co-located blendertk tool in ``blendertk.uv_utils.shell_xform``
        (``ShellXformSlots``), discovered by ``BlenderUiHandler``. Mirrors Maya's b033;
        Pin (b029) and Stack (b030) sit beside it in the same group."""
        self.sb.handlers.marking_menu.show("shell_xform")

    def cmb003(self, index, widget):
        """UV Map Size — passive input; read by get_map_size for the texel-density tools.
        Nothing to do on change."""

    def s003(self, value, widget):
        """Texel Density — passive input; read by Get/Set Texel Density (b003/b004).
        Nothing to do on change."""


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
