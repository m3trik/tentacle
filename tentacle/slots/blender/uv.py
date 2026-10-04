# !/usr/bin/python
# coding=utf-8
import math

import bpy
import blendertk as btk
from tentacle import UvMixin, SlotsBlender


class UvSlots(UvMixin, SlotsBlender):
    """Blender port of the shared ``uv`` menu.

    Core UV operators (unwrap, the cmb011 Standard projection, pack, seam,
    angle-band hard-edge cut) run as ``bpy.ops.uv.*`` in edit mode via :meth:`_uv_op` (verified to
    work headless). Auto Unwrap's Hard Surface / Organic modes instead round-trip the mesh through
    an external unwrapping engine via ``btk.UvUtils.auto_unwrap`` (shared dispatch in
    :class:`~tentacle.slots._uv.UvMixin`). Data-level UV work (pin/stack/texel density/UV-set
    cleanup) is backed by ``blendertk.uv_utils`` (bmesh — headless);
    move/transform/mirror/straighten/distribute live in the blendertk ``shell_xform`` panel
    (launched via b033); UV transfer rides the native Data-Transfer operator; RizomUV rides the
    blendertk bridge panel (round-trip presets + one-way send). The deferred Maya-only depth is in
    the parity overrides (u3dLayout packing params + the unwrap_cylinder crease algorithm).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu
        # b029 dual-state pin toggle (Maya parity): reset when the selection changes.
        self._b029_pinned = False
        self._b029_last_selection = None

    def _uv_op(self, op):
        """Run a UV/seam operator across the selected meshes in Edit Mode (all faces
        selected) inside ``btk.edit_mode``, which restores the caller's selection, active
        object and mode afterward. Returns the meshes it ran on -- empty (with a message)
        when there's no mesh selection."""
        meshes = [o for o in self.selected_objects() if o.type == "MESH"]
        if not meshes:
            self.sb.message_box("UV operation requires a mesh selection.")
            return []
        with btk.edit_mode(meshes):
            bpy.ops.mesh.select_all(action="SELECT")
            op()
        return meshes

    def _seam_op(self, clear):
        """Mark/clear UV seams on the user's **selected** edges (selection-based, unlike the
        whole-mesh unwrap ops — so it does not force select-all). Requires edit mode."""
        active = self.active_object()
        if not (active and active.type == "MESH"):
            self.sb.message_box("Cut/Sew UVs requires an active mesh.")
            return
        if active.mode != "EDIT":
            self.sb.message_box("Select edges in Edit Mode to cut/sew UV seams.")
            return
        # window override: edit-mesh ops poll ``edit_object`` from screen context
        with btk.window_context_override():
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
    # Option-box names are Blender-specific (Maya's UV option boxes carry u3dLayout packing
    # params with no Blender analogue): they expose the native operator's own parameters.
    def tb000_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Pack UVs")
        # cmb009 reuses the Maya objectName + labels (same Pre-Scale-Mode option, cross-DCC rule):
        # "Preserve 3D" runs a native average-islands-scale pass (equal texel density) before
        # packing; "Preserve UV" skips it and keeps each shell's current relative proportions.
        cmb009 = m.add(
            "QComboBox",
            setObjectName="cmb009",
            setToolTip=self.sb.tooltip.fmt(
                title="Pre-Scale Mode",
                body="How shells are sized relative to each other before packing.",
                bullets=[
                    "<b>Preserve UV</b> — keep each shell's current UV size "
                    "relative to the others.",
                    "<b>Preserve 3D</b> — rescale so every shell carries the same "
                    "texel density (<code>uv.average_islands_scale</code>).",
                ],
            ),
        )
        for text, data in (
            ("Pre-Scale: Preserve UV", 0),
            ("Pre-Scale: Preserve 3D", 1),
        ):
            cmb009.addItem(text, data)
        cmb009.setCurrentIndex(1)  # matches Maya's default (Preserve 3D)
        m.add(
            "QDoubleSpinBox",
            setPrefix="Margin: ",
            setObjectName="s_pack_margin",
            set_limits=[0, 1, 0.001, 3],
            setValue=0.001,
            setToolTip=self.sb.tooltip.fmt(
                title="Margin",
                body="Spacing left between packed islands, in UV units.",
            ),
        )
        m.add(
            "QCheckBox",
            setText="Rotate Islands",
            setObjectName="chk_pack_rotate",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Islands",
                body="Let the packer re-orient an island wherever that packs tighter.",
            ),
        )
        # s004 reuses the Maya objectName + label (same target-UDIM-tile option, cross-DCC
        # rule): Blender's pack_islands has no target-tile parameter (no packBox analogue) —
        # and on 4.x+ it defaults udim_source='CLOSEST_UDIM', packing islands into whichever
        # tile they already occupy, NOT 0-1 — so tb000 reads the tile actually packed into
        # afterward and moves the map by the delta into this tile.
        m.add(
            "QSpinBox",
            setPrefix="UDIM: ",
            setObjectName="s004",
            set_limits=[1001, 1200],
            setValue=1001,
            setToolTip=self.sb.tooltip.fmt(
                title="UDIM",
                body="The tile the shells end up in (1001–1200). "
                "<b>1001</b> is the first 0–1 tile.",
                notes=[
                    "Blender's packer has no target-tile parameter, so the map is "
                    "moved into this tile after the pack.",
                ],
            ),
        )
        # cmb015 reuses the Maya objectName + labels (same tile-coverage option, cross-DCC
        # rule): pack_islands has no packBox analogue, so coverage is a post-pack whole-map
        # scale about the target tile's bottom-left corner (same math as Maya's fractional
        # -packBox / the rizom bridge's UV_AREA token).
        cmb015 = m.add(
            "QComboBox",
            setObjectName="cmb015",
            setToolTip=self.sb.tooltip.fmt(
                title="Tile Coverage",
                body="Which fraction of the target UDIM tile to pack into, "
                "anchored at the tile's bottom-left corner. Use it to reserve "
                "the rest of the tile for other shells.",
            ),
        )
        for text, data in [
            ("Tile Coverage: Full", (1.0, 1.0)),
            ("Tile Coverage: Half (U)", (0.5, 1.0)),
            ("Tile Coverage: Half (V)", (1.0, 0.5)),
            ("Tile Coverage: Quarter", (0.5, 0.5)),
        ]:
            cmb015.addItem(text, data)
        cmb015.setCurrentIndex(0)

    @btk.undoable
    def tb000(self, widget):
        """Pack UVs (optionally equal-texel-density pre-scaled), then moved into the target
        UDIM tile by the delta from the tile actually packed into — and shrunk to the chosen
        tile coverage about the tile's bottom-left corner."""
        m = widget.option_box.menu
        preserve_3d = m.cmb009.currentData() == 1  # Pre-Scale Mode: 1 = Preserve 3D

        def _pack():
            if preserve_3d:
                # Preserve 3D: rescale islands to equal texel density before packing.
                bpy.ops.uv.average_islands_scale()
            bpy.ops.uv.pack_islands(
                margin=m.s_pack_margin.value(), rotate=m.chk_pack_rotate.isChecked()
            )

        # One bulk operator call with nothing to tick from the inside, so the
        # marquee is painted before it and torn down after (mirror of Maya's).
        with self.sb.progress(text="Working: Pack UVs") as update:
            update()
            try:
                objects = self._uv_op(_pack)
                if not objects:
                    return
            except (
                RuntimeError
            ):  # average_islands_scale/pack_islands poll-fail without a UV layer
                self.sb.message_box("No UVs found on the selection.")
                return
        # 4.x+ pack_islands defaults udim_source='CLOSEST_UDIM' — islands already in another
        # tile pack into THAT tile, not 0-1, so a blind fixed shift would land the map in the
        # wrong tile. Read the tile actually packed into (floor of the achieved min u/v) and
        # move by the DELTA to the requested one.
        udim = m.s004.value()
        u_tile, v_tile = (udim - 1001) % 10, (udim - 1001) // 10
        snapshot = btk.get_uv_coords(objects)
        if not snapshot:
            return
        u_min = min(u for coords in snapshot.values() for u, _ in coords)
        v_min = min(v for coords in snapshot.values() for _, v in coords)
        du, dv = u_tile - math.floor(u_min), v_tile - math.floor(v_min)
        if du or dv:
            btk.move_uvs(objects, du=float(du), dv=float(dv))
        cu, cv = m.cmb015.currentData()  # Tile Coverage — shrink about the tile corner
        if cu != 1.0 or cv != 1.0:
            btk.scale_uvs(objects, su=cu, sv=cv, pivot=(float(u_tile), float(v_tile)))

    def tb001_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Auto Unwrap")
        # Item data is the key consumed by tb001 -- "standard" for Blender's own
        # Smart UV Project, else a UvUtils.auto_unwrap method name. Labels match
        # the Maya panel's exactly (cross-DCC parity).
        cmb011 = m.add(
            "QComboBox",
            setObjectName="cmb011",
            setToolTip=self.sb.tooltip.fmt(
                title="Unwrap Method",
                body="Which algorithm generates the UVs.",
                bullets=[
                    "<b>Standard</b> — Blender's Smart UV Project: the best fit "
                    "from several planar projections.",
                    "<b>Hard Surface</b> — Ministry of Flat, an external unwrapper "
                    "that classifies topology and places seams the way an artist "
                    "would. Best for mechanical / architectural models.",
                    "<b>Organic</b> — Boundary First Flattening, an external "
                    "unwrapper using conformal flattening with automatic cone "
                    "singularities. Best for sculpted, scanned and character models.",
                ],
                notes=[
                    "Angle Limit and Island Margin below apply to "
                    "<b>Standard</b> only.",
                ],
            ),
        )
        for text, data in [
            ("Standard", "standard"),
            ("Hard Surface (Ministry of Flat)", "hard"),
            ("Organic (BFF)", "organic"),
        ]:
            cmb011.addItem(text, data)
        cmb011.setCurrentIndex(0)  # Standard — needs no external engine
        m.add(
            "QSpinBox",
            setPrefix="Angle Limit: ",
            setObjectName="s_smart_angle",
            set_limits=[1, 89],
            setValue=66,
            setToolTip=self.sb.tooltip.fmt(
                title="Angle Limit",
                body="Smart UV Project's projection angle limit, in degrees. "
                "Lower values cut more islands.",
                notes=["<b>Standard</b> method only."],
            ),
        )
        m.add(
            "QDoubleSpinBox",
            setPrefix="Island Margin: ",
            setObjectName="s_smart_margin",
            set_limits=[0, 1, 0.001, 3],
            setValue=0.0,
            setToolTip=self.sb.tooltip.fmt(
                title="Island Margin",
                body="Spacing left between the generated islands, in UV units.",
                notes=["<b>Standard</b> method only."],
            ),
        )

        def _sync():  # Smart-project params disable for the engine modes
            standard = m.cmb011.currentData() == "standard"
            m.s_smart_angle.setEnabled(standard)
            m.s_smart_margin.setEnabled(standard)

        m.cmb011.currentIndexChanged.connect(_sync)
        _sync()

    @btk.undoable
    def tb001(self, widget):
        """Auto Unwrap (Smart UV Project, or an external unwrapping engine)."""
        m = widget.option_box.menu
        mode = m.cmb011.currentData()

        if mode in self.AUTO_UNWRAP_ENGINE_MODES:
            objects = [o for o in self.selected_objects() if o.type == "MESH"]
            if not objects:
                self.sb.message_box(
                    "<b>Nothing selected.</b><br>The operation requires at least "
                    "one selected mesh."
                )
                return
            # Not via _uv_op: auto_unwrap manages its own object-mode context.
            with self.sb.progress(text=f"Working: Auto Unwrap ({mode})") as update:
                update()
                return self._run_auto_unwrap(btk, objects, mode, self.get_map_size())

        with self.sb.progress(text="Working: Auto Unwrap") as update:
            update()
            self._uv_op(
                lambda: bpy.ops.uv.smart_project(
                    angle_limit=math.radians(m.s_smart_angle.value()),
                    island_margin=m.s_smart_margin.value(),
                )
            )

    # method enum -> friendly label (Minimum Stretch only exists on newer Blender; guarded).
    _UNWRAP_METHODS = {"Angle Based": "ANGLE_BASED", "Conformal": "CONFORMAL"}

    def tb004_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Unfold")
        m.add(
            "QComboBox",
            addItems=list(self._UNWRAP_METHODS),
            setObjectName="cmb_unfold_method",
            setToolTip="Unwrap algorithm.",
        )
        m.add(
            "QDoubleSpinBox",
            setPrefix="Margin: ",
            setObjectName="s_unfold_margin",
            set_limits=[0, 1, 0.001, 3],
            setValue=0.0,
            setToolTip="Spacing between islands after unwrap.",
        )
        # Maya parity: post-unwrap relax (Optimize) + axis-align (Orient). Reuses Maya's
        # chk017/chk007 names + labels (same options, cross-DCC QSettings rule).
        m.add(
            "QCheckBox",
            setText="Optimize",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Relax the unwrap to even out UV spacing (Minimize Stretch).",
        )
        m.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Rotate each shell parallel to the nearest U/V axis (Align Rotation).",
        )
        # chk022/s000 reuse the Maya objectNames + labels (same options, cross-DCC rule):
        # post-unfold similarity-gated stacking (btk.stack_uv_shells(tolerance=...)).
        m.add(
            "QCheckBox",
            setText="Stack Similar",
            setObjectName="chk022",
            setChecked=True,
            setToolTip="Stack only shells that fall within the set tolerance.",
        )
        m.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip="Stack shells with uv's within the given range.",
        )

    @btk.undoable
    def tb004(self, widget):
        """Unfold (unwrap, then optionally relax, axis-align, and stack similar shells)."""
        m = widget.option_box.menu
        method = self._UNWRAP_METHODS.get(
            m.cmb_unfold_method.currentText(), "ANGLE_BASED"
        )
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
        # Seam) and chk045 (Hide Seam From View) have no Blender analogue — the auto-seam path
        # places the lengthwise cut itself (parity_map.py "uv").
        m = widget.option_box.menu
        m.setTitle("Cut Cylinder")
        m.add(
            "QDoubleSpinBox",
            setPrefix="Crease Angle: ",
            setObjectName="s016",
            set_limits=[1, 179],
            setValue=45.0,
            setSuffix="°",
            setToolTip="Edges sharper than this angle (degrees) become UV seams — cuts ~90° steps "
            "and cap rings while keeping shallow chamfers merged.",
        )
        m.add(
            "QCheckBox",
            setText="Unfold",
            setObjectName="chk041",
            setChecked=True,
            setToolTip="Unwrap (flatten) after seaming. Off = only cut the crease seams.",
        )
        m.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk042",
            setChecked=True,
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
        # Island gutter from the panel's map size, via the one ecosystem rule
        # (btk.calculate_uv_padding, mirror of mtk's) rather than a bespoke
        # literal — the Maya twin passes map_size into unwrap_cylinder for the
        # same reason, so a mesh seamed in either DCC gets the same gutter.
        margin = btk.calculate_uv_padding(self.get_map_size(), normalize=True)

        def _run():
            if unfold:
                bpy.ops.uv.smart_project(angle_limit=angle, island_margin=margin)
                try:
                    bpy.ops.uv.pack_islands(rotate=orient, margin=margin)
                except TypeError:  # older Blender pack_islands signature
                    bpy.ops.uv.pack_islands(margin=margin)
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
                lambda: (
                    bpy.ops.uv.unwrap(method="ANGLE_BASED"),
                    bpy.ops.uv.pack_islands(),
                )
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
            "QCheckBox",
            setText="Prefer Best Layout",
            setObjectName="chk029",
            setChecked=True,
            setToolTip="Keep the UV set with the largest UV footprint, not just the first one.",
        )
        m.add(
            "QCheckBox",
            setText="Remove Empty Sets",
            setObjectName="chk035",
            setChecked=True,
            setToolTip="Delete UV sets whose UVs are all at the origin (never unwrapped).",
        )
        m.add(
            "QCheckBox",
            setText="Delete Secondary Sets",
            setObjectName="chk036",
            setToolTip="Delete ALL other UV sets, leaving only the kept one.",
        )
        m.add(
            "QCheckBox",
            setText="Rename to 'map1'",
            setObjectName="chk037",
            setChecked=True,
            setToolTip="Rename the kept UV set to 'map1' (Maya's default — export pipeline parity).",
        )
        m.add(
            "QCheckBox",
            setText="Force Rename",
            setObjectName="chk038",
            setToolTip="If another set is already named 'map1', overwrite it instead of skipping.",
        )
        m.add(
            "QCheckBox",
            setText="Dry Run",
            setObjectName="chk030",
            setToolTip="Report what would change without modifying anything.",
        )

    @btk.undoable
    def tb007(self, widget):
        """Cleanup UV Sets (standardize/clean the UV layers — mirror of Maya's cleanup_uv_sets)."""
        m = widget.option_box.menu
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>Select mesh object(s) with UV sets."
            )
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
        verb, del_verb = (
            ("Would keep", "would delete") if dry_run else ("Kept", "deleted")
        )
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
        # Every entry is a one-shot action — dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Create UV Snapshot",
            setObjectName="uv_snapshot",
            setToolTip="Export the active mesh's UV layout to an image (native Export UV Layout) "
            "as a texture-painting reference.",
        )
        widget.menu.add(
            "QPushButton",
            setText="RizomUV Bridge",
            setObjectName="btn_rizom_bridge",
            setToolTip="Round-trip selected meshes through RizomUV using a Lua preset.",
            clicked=lambda: self.b032(),
        )
        # RizomUV is an optional third-party app. Present the entry per the user's
        # ``unmet_policy`` (Preferences > Unavailable tools) when it isn't installed,
        # rather than offering a button whose only outcome is a "not found" error.
        # The lambda defers the engine import into gate_on_app (see its docstring);
        # ``APP.available`` is cached, so this costs one dict lookup after the
        # first probe.
        self.gate_on_app(widget.menu.btn_rizom_bridge, lambda: btk.RizomUVBridge.APP)

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

    # ------------------------------------------------------------------ b000  Transfer
    # The option box, its wiring and the texture pass are UvMixin's (``b000_init``,
    # ``_tt_texture_pass``); this fork supplies its engine and its words.
    _TT_TERMS = {
        "set": "map",
        "current": "active",
        "first": "Active Mesh",
        "first_who": "the active object",
        "pick_first": "<b>Make the source active</b> (a mesh, or the parent of several), with the target(s) selected.",
        "pick_last": "<b>Make the target mesh active</b>, with the source mesh(es) selected.",
        "assign_row": "Material",
        "last": "All But Active",
        "last_who": "the active object",
        "order": "",
        "instances": "linked duplicates of the source (one mesh datablock, UVs "
        "already match)",
        "bound": "the UV Map node feeding the image, else the active-render map",
        "output_dir": "//textures/uv_transfer",
        "output_rel": "a subdirectory of the .blend's textures folder",
    }

    def _tt_engine(self):
        """Blender's ``TextureTransfer`` (see ``UvMixin._tt_engine``)."""
        return btk.TextureTransfer

    def _tt_records(self):
        """Blender's ``LightmapRecords`` (see ``UvMixin._tt_records``)."""
        return btk.LightmapRecords

    @staticmethod
    def _tt_meshes(objects):
        """Mesh objects among *objects* and their children (order kept)."""
        out = []

        def visit(o):
            if o.type == "MESH" and o not in out:
                out.append(o)
            for c in o.children:
                visit(c)

        for o in objects:
            visit(o)
        return out

    def _tt_node_path(self, node):
        """``|``-joined parent chain of *node*, for the derived Output Name.

        Blender has no DAG path, so it is built from ``parent`` links; a
        ``.001``-style duplicate counter is dropped from each name, since it
        is Blender's collision suffix, not part of what the object is called.
        """
        import re

        chain = []
        while node is not None:
            chain.append(re.sub(r"\.\d+$", "", node.name))
            node = node.parent
        return "|" + "|".join(reversed(chain))

    def _tt_source_tooltip(self):
        """Live tooltip for the Store Source Meshes icon -- what is stored NOW.

        Mirror of the Maya slot's. The stored set is otherwise invisible
        until a transfer runs and either uses the wrong meshes or reports
        none, so the hover is the only place it can be checked. Names are
        stored (not object references), so an object renamed or removed
        since the capture is called out rather than silently listed.
        """
        stored = getattr(self, "_tt_sources", [])
        missing = [n for n in stored if n not in bpy.data.objects]
        return self.sb.tooltip.stored_items(
            stored,
            title="Store Source Meshes",
            body="Store the current selection as the source meshes (mesh "
            "objects; empties / parents contribute their mesh children) and "
            "switch to <i>Stored Meshes</i>. <i>Source: Auto</i> reads them "
            "too, when they match the selection.",
            noun="stored source mesh(es)",
            empty_text="Nothing stored yet.",
            notes=(
                [f"{len(missing)} no longer in the file; they are skipped."]
                if missing
                else None
            ),
        )

    def _tt_set_source_from_selection(self):
        self._tt_sources = [o.name for o in self._tt_meshes(self.selected_objects())]
        self._tt_sync_controls()
        self.sb.message_box(
            f"Stored <b>{len(self._tt_sources)}</b> source mesh(es) for Transfer."
            if self._tt_sources
            else "<b>Nothing selected.</b><br>Select the source meshes."
        )

    def _tt_select_source(self):
        """Select the stored source meshes -- the capture, made visible.

        Mirror of the Maya slot's, with Blender's two extra refusals reported
        rather than forced: an object outside the active view layer (an
        excluded collection) raises from ``select_set``, and one with
        ``hide_select`` on silently declines. Unhiding geometry behind the
        user's back to satisfy a *select* is the one thing this must not do --
        and a transfer reads the objects either way.
        """
        stored = getattr(self, "_tt_sources", [])
        alive = [bpy.data.objects[n] for n in stored if n in bpy.data.objects]
        if not alive:
            return self.sb.message_box(
                "<b>Nothing stored.</b><br>Store the source meshes with the "
                "<b>+</b> icon on the Source row first."
                if not stored
                else "<b>None of the stored source meshes are still in the "
                "file.</b><br>Re-capture them."
            )
        # window override: windowless, select_all / select_set / the active write
        # address the scene's default layer, not the one the window shows
        with btk.window_context_override():
            bpy.ops.object.select_all(action="DESELECT")
            selected = []
            for obj in alive:
                try:
                    obj.select_set(True)
                except RuntimeError:  # not in the active view layer
                    continue
                if obj.select_get():
                    selected.append(obj)
            if selected:
                bpy.context.view_layer.objects.active = selected[0]
        unreachable = len(alive) - len(selected)
        missing = len(stored) - len(alive)
        self.sb.message_box(
            f"Selected <b>{len(selected)}</b> stored source mesh(es)."
            + (f"<br>{missing} no longer in the file; skipped." if missing else "")
            + (
                f"<br>{unreachable} not selectable (excluded collection, or "
                f"Disable Selection is on)."
                if unreachable
                else ""
            )
        )

    @btk.undoable
    def b000(self, widget):
        """Transfer UVs OR textures -- one pass per run (mirror of Maya's ``b000``)."""
        menu = widget.option_box.menu
        mode = menu.cmb_tt_source.currentData() or self.SOURCE_AUTO
        scope = menu.cmb014.currentData() or "order"
        selected = self.selected_objects()
        active = self.active_object()
        stored_sources = [
            bpy.data.objects[n]
            for n in getattr(self, "_tt_sources", [])
            if n in bpy.data.objects
        ]
        source_note = ""
        if mode == self.SOURCE_AUTO:
            # Resolved first: every gate below asks about a concrete mode.
            # First and Last both key off the ACTIVE object, so Auto's
            # combined target stands in for it; Auto's First is Rest of
            # Selection.
            mode, target = self._tt_auto_source(
                self._tt_meshes(selected), stored_sources
            )
            if target is not None:
                active = target
            scope = "order"
            source_note = self._tt_source_note(mode)

        # ---- source(s) and targets, per mode, ONCE ------------------------
        # Auto's probe and the passes must read the SAME meshes. The active
        # object is one side of the transfer -- a mesh, or an empty / parent
        # whose mesh children pair with the targets by name, else order.
        picked = self._tt_meshes([active]) if active is not None else []
        if mode == "first":
            source = picked
            targets = [m for m in self._tt_meshes(selected) if m not in source]
        elif mode == "last":
            targets = picked
            source = [m for m in self._tt_meshes(selected) if m not in targets]
        elif mode == "stored":
            source = stored_sources
            targets = [m for m in self._tt_meshes(selected) if m not in source]
        else:  # uvset: every selected mesh moves between its own maps
            source, targets = None, self._tt_meshes(selected)

        transfer_mode = menu.cmb_tt_transfer.currentData()
        auto = transfer_mode == self.TRANSFER_AUTO
        lightmap_probe = self._tt_lightmap_probe(menu)
        if auto and mode != "uvset":
            # Resolved BEFORE the pass-dependent gates below (the Similar-scope
            # check): what Auto decides is what they must ask for. An empty
            # probe resolves to the UV pass and falls through to the same
            # selection errors a manual mode would hit.
            transfer_mode = self._tt_resolve_auto(
                btk.TextureTransfer, source, has_lightmap=lightmap_probe
            )
        do_uvs, do_textures = self._tt_passes(mode, transfer_mode)
        auto_note = (
            self._tt_auto_note(
                auto, do_textures, mode, lightmaps=lightmap_probe is not None
            )
            + source_note
        )
        # Blank = named after the source by the texture pass.
        out_name = menu.t_tt_name.text().strip()
        pairs, targets, others, refusal = self._tt_gate(
            mode,
            scope,
            source,
            targets,
            do_uvs,
            do_textures,
            notes=(auto_note, source_note),
        )
        if refusal:
            return self.sb.message_box(refusal)

        report = []
        # Mirror of Maya's: both passes are bulk engine calls with nothing to
        # tick from the inside, so ONE task indicator spans them and re-labels
        # itself between the two -- the footer names whichever pass is
        # currently freezing the UI, which a bare wait cursor cannot.
        first_label = (
            "Working: Transfer UV Set" if do_uvs else "Working: Transfer Textures"
        )
        with self.sb.progress(text=first_label) as tick:
            tick()
            # ---- UV pass ---------------------------------------------------
            if do_uvs:
                try:
                    if pairs is None:
                        targets = btk.transfer_uvs_to_similar(
                            source[0],
                            others if scope == "selection" else None,
                            tolerance=self._tt_similarity_value(),
                        )
                        if not targets:
                            return self.sb.message_box(
                                "<b>No similar meshes found</b> within the tolerance "
                                "(linked duplicates already share the source's UVs)."
                            )
                    else:
                        # match_by_similarity=False: the pairing is already decided
                        # (selection / stored-by-name); re-vetting it by geometric
                        # similarity could only silently drop a pair the user named.
                        btk.transfer_uvs(
                            [s for s, _ in pairs],
                            [t for _, t in pairs],
                            match_by_similarity=False,
                        )
                except ValueError as e:
                    return self.sb.message_box(f"<b>Transfer UV Set:</b><br>{e}")
                report.append(
                    f"Transferred UVs to <b>{len(targets)}</b> mesh(es)" + "."
                )

            # ---- texture pass ----------------------------------------------
            if do_textures:
                tick(text="Working: Transfer Textures")
                report.append(self._tt_texture_pass(targets, source, menu, out_name))
        self.sb.message_box("<br><br>".join(report) + source_note)

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
        signature = self._selection_fingerprint(objects)
        if self._b029_last_selection != signature:
            self._b029_pinned = False  # fresh selection — start with Pin
        self._b029_pinned = not self._b029_pinned
        btk.pin_uvs(
            objects,
            pin=self._b029_pinned,
            selected_only=any(o.mode == "EDIT" for o in objects),
        )
        self._b029_last_selection = signature

    # ------------------------------------------------------------------ tb022  Cut Hard Edges
    def tb022_init(self, widget):
        m = widget.option_box.menu
        m.setTitle("Cut Hard Edges")
        m.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s017",
            set_limits=[0, 180],
            setValue=70,
            setToolTip="Lower bound: edges whose dihedral angle is at least this are seam-cut.",
        )
        # s018 / chk025 reuse the Maya objectNames + labels (same options, cross-DCC rule).
        m.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s018",
            set_limits=[0, 180],
            setValue=180,
            setToolTip="Upper bound of the seam-cut angle band (180 = no upper limit).",
        )
        m.add(
            "QCheckBox",
            setText="Include UV Borders",
            setObjectName="chk025",
            setToolTip="Also mark seams at the current UV island borders (Seams From Islands).",
        )
        # chk026 reuses the Maya objectName + label (same option, cross-DCC rule): a temporary
        # Smart UV Project decomposition stands in for u3dAutoSeam (btk.derive_auto_seams).
        m.add(
            "QCheckBox",
            setText="Include Auto Seams",
            setObjectName="chk026",
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
    @btk.undoable
    def b030(self, widget):
        """Stack / Unstack shells (dual-state toggle: first click stacks the targeted
        shells per the option box — :meth:`UvMixin.b030_init` — and captures their positions
        (and pins); the next click restores them. A selection change resets the toggle).

        ``Similar`` = ``btk.stack_uv_shells(tolerance=...)`` — shells of the same topology +
        shape land on the first matching shell, rotated / scaled to overlap exactly, unmatched
        shells stay put (Maya's ``polyUVStackSimilarShells``); ``Center`` =
        ``btk.stack_uv_shells()`` — every shell onto the shared center (``texStackShells``).
        ``Pin after stack`` pins the targeted shells' UVs; Unstack restores the pins as they
        were (the snapshot carries them)."""
        mode, tolerance, pin = self._stack_options(widget)
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("<b>Nothing selected.</b>")
            return
        signature = self._selection_fingerprint(objects)
        if getattr(self, "_b030_snapshot", None) and self._b030_signature == signature:
            btk.set_uv_coords(objects, self._b030_snapshot)
            self._b030_snapshot = None
            return
        snapshot = btk.get_uv_coords(objects, pins=pin)
        similar = mode == self.STACK_MODE_SIMILAR
        moved = btk.stack_uv_shells(objects, tolerance=tolerance if similar else None)
        if not moved:
            self._b030_snapshot = None
            if similar:
                self._report_no_similar_shells()
            else:
                self.sb.message_box(
                    "<strong>No UV shells stacked.</strong><br>Needs at least two islands "
                    "(in Edit Mode, shells touched by the selection)."
                )
            return
        self._b030_snapshot = snapshot
        self._b030_signature = signature
        if pin:
            btk.pin_uvs(
                objects,
                pin=True,
                selected_only=any(o.mode == "EDIT" for o in objects),
                whole_shells=True,
            )

    # ------------------------------------------------------------------ deferred (Maya / UV-editor)
    def b032(self):
        """RizomUV Bridge — co-located blendertk panel (round-trip Lua presets + one-way send).
        Mirrors Maya's b032 → ``marking_menu.show("rizom_bridge")``."""
        self.sb.handlers.marking_menu.show("rizom_bridge")

    def b033(self):
        """Open the Shell Xform panel — the ``More..`` button in the Transform group.

        Co-located blendertk tool in ``blendertk.uv_utils.shell_xform``
        (``ShellXformSlots``), discovered by ``BlenderUiHandler``. Mirrors Maya's b033;
        Pin (b029) and Stack (b030) sit beside it in the same group."""
        self.sb.handlers.marking_menu.show("shell_xform")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
