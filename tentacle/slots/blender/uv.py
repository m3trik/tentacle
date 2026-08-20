# !/usr/bin/python
# coding=utf-8
import math
import os

import bpy
import pythontk as ptk
import blendertk as btk
from tentacle import UvMixin, SlotsBlender


class Uv(UvMixin, SlotsBlender):
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
                if not self._uv_op(_pack):
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
        objects = self.selected_objects()  # _uv_op selected exactly the target meshes
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

    # ------------------------------------------------------------------
    # b000  Transfer UVs / Textures
    # ------------------------------------------------------------------
    def b000_init(self, widget):
        """Initialize the Transfer option box.

        One tool, two transfers that are ALTERNATIVES (see ``UvMixin``'s
        Transfer modes): the source's UV layout onto the targets
        (``btk.transfer_uvs`` -- exact for identical topology, sampled by
        proximity otherwise), or the source's textures re-mapped into each
        target's OWN layout (``btk.TextureTransfer`` over ``pythontk.UvTransfer``:
        exact texel correspondence, so it never bleeds the way a ray-cast bake
        does where a mesh touches itself). They do not compose -- the texture
        pass keeps the target's UV map, so a source layout copied alongside its
        maps would land in a UV map nothing references. The Auto mode defers
        the pick to run time: a source whose materials carry texture maps
        transfers them; an untextured source transfers its layout.
        """
        menu = widget.option_box.menu
        menu.setTitle("Transfer UVs / Textures")
        cmb024 = menu.add(
            "QComboBox",
            setObjectName="cmb024",
            setToolTip=self.sb.tooltip.fmt(
                title="Source",
                body="Where the UVs / textures come FROM. Everything else selected "
                "at run time is a <b>target</b>.",
                bullets=[
                    "<b>Active Mesh</b> — the active object is the source; the "
                    "Scope below picks the targets.",
                    "<b>Stored Source Meshes</b> — the meshes captured with "
                    "<i>Set Source From Selection</i>, paired to the selected "
                    "targets by matching name (then by order). Use for a "
                    "re-unwrapped / repacked copy, or a many-materials-to-one "
                    "consolidation.",
                    "<b>UV Map On Same Mesh</b> — textures only: read them through "
                    "the Source UV Map and write them for the Target UV Map, on "
                    "each selected mesh.",
                ],
                notes=[
                    "Textures need identical topology (same faces and vertex "
                    "order); UVs do not.",
                ],
            ),
        )
        for text, data in [
            ("Source: Active Mesh", "first"),
            ("Source: Stored Source Meshes", "stored"),
            ("Source: UV Map On Same Mesh", "uvset"),
        ]:
            cmb024.addItem(text, data)
        btn_src = menu.add(
            "QPushButton",
            setText="Set Source From Selection",
            setObjectName="btn_tt_set_source",
        )
        btn_src.clicked.connect(self._tt_set_source_from_selection)
        # Bound through the switchboard rather than ``btn_src.tooltip``:
        # ``Menu.add`` defers register_widget (which stamps the per-widget
        # namespace) to a timer, so the proxy does not exist yet here.
        self.sb.tooltip.bind(btn_src, self._tt_source_tooltip)
        # Clear rides the button's own option box. It greys (rather than
        # hides) while nothing is stored, so the row doubles as the panel's
        # only at-a-glance "is a source set?" readout -- a button that
        # vanishes reads as a layout change, not as a state.
        self._tt_clear_action = btn_src.option_box.set_action(
            callback=self._tt_clear_source,
            icon="clear",
            tooltip="Clear the stored source meshes. Enabled only while "
            "something is stored; the geometry itself is untouched.",
        )
        self._tt_src_button = btn_src
        cmb014 = menu.add(
            "QComboBox",
            setObjectName="cmb014",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                body="Which meshes receive the transfer when the source is the "
                "<b>Active Mesh</b>.",
                bullets=[
                    "<b>Selection Order</b> — every other selected object.",
                    "<b>Similar in Selection</b> — the selected objects that are "
                    "geometrically similar to the source.",
                    "<b>Similar in Scene</b> — every geometrically similar mesh "
                    "in the scene.",
                ],
                notes=[
                    "The Similar scopes find their targets by transferring UVs, "
                    "so they need <b>Transfer UV Set</b> on; they skip linked "
                    "duplicates of the source (one mesh datablock, UVs already match).",
                ],
            ),
        )
        for text, data in [
            ("Scope: Selection Order", "order"),
            ("Scope: Similar in Selection", "selection"),
            ("Scope: Similar in Scene", "scene"),
        ]:
            cmb014.addItem(text, data)
        d000 = menu.add(
            "QDoubleSpinBox",
            setObjectName="d000",
            setPrefix="Similarity: ",
            setValue=0.9,
            setMinimum=0.0,
            setMaximum=1.0,
            setSingleStep=0.05,
            setToolTip=self.sb.tooltip.fmt(
                title="Similarity",
                body="The minimum score (0–1) a mesh must reach to receive UVs, "
                "scored on bounding-box volume and vertex count.",
                notes=["Used by the <b>Similar</b> scopes only."],
            ),
        )
        cmb028 = menu.add(
            "QComboBox",
            setObjectName="cmb028",
            setToolTip=self.sb.tooltip.fmt(
                title="Transfer",
                body="What travels from the source to the targets — one or "
                "the other, since the texture pass deliberately keeps the "
                "target's own layout.",
                bullets=[
                    "<b>UV Map</b> — copy the source's active uv map onto each "
                    "target, replacing its active one. Exact for identical "
                    "topology, sampled by proximity otherwise.",
                    "<b>Textures</b> — re-map the source's textures into "
                    "each target's OWN layout by exact texel correspondence: a "
                    "repacked atlas, a material consolidation, or another "
                    "uv map on the same mesh. No rays, no cage, no bleed.",
                    "<b>Auto</b> — decided per run from the source's "
                    "materials: Textures when any of them carries a texture "
                    "map, UV Map when none do.",
                ],
                notes=[
                    "Textures need identical topology (same faces and vertex "
                    "order); uv maps do not.",
                ],
            ),
        )
        for text, data in [
            ("Transfer: UV Map", "uvs"),
            ("Transfer: Textures", "textures"),
            # Auto rides LAST, not first where an Auto usually sits: the
            # combo's state persists by index, so inserting above the existing
            # rows would silently remap every saved choice.
            ("Transfer: Auto", "auto"),
        ]:
            cmb028.addItem(text, data)
        t_tt_src_uvset = menu.add(
            "QLineEdit",
            setPlaceholderText="Source UV Map: Auto",
            setText="",
            setObjectName="t_tt_src_uvset",
            setToolTip=self.sb.tooltip.fmt(
                title="Source UV Map",
                body="The UV map the textures are READ through. Blank = <b>Auto</b>.",
                bullets=[
                    "<b>Mesh sources</b> — Auto is each source mesh's active UV map.",
                    "<b>UV Map On Same Mesh</b> — Auto is the UV map the mesh's "
                    "textures are actually bound to (the UV Map node feeding the "
                    "image, else the active-render map), i.e. the layout the maps "
                    "were painted for.",
                ],
            ),
        )
        t_tt_dst_uvset = menu.add(
            "QLineEdit",
            setPlaceholderText="Target UV Map: Auto",
            setText="",
            setObjectName="t_tt_dst_uvset",
            setToolTip=self.sb.tooltip.fmt(
                title="Target UV Map",
                body="The UV map the maps are WRITTEN for. Blank = <b>Auto</b>.",
                bullets=[
                    "<b>Mesh sources</b> — Auto is each target mesh's active UV map.",
                    "<b>UV Map On Same Mesh</b> — Auto is the first UV map other "
                    "than the source, so a two-map mesh needs neither named.",
                ],
            ),
        )
        cmb025 = menu.add(
            "QComboBox",
            setObjectName="cmb025",
            setToolTip=self.sb.tooltip.fmt(
                title="Resolution",
                body="Output size per target material.",
                bullets=["<b>Auto</b> — the largest source map feeding it."],
            ),
        )
        cmb025.addItem("Resolution: Auto", 0)
        for n in (512, 1024, 2048, 4096, 8192):
            cmb025.addItem(f"Resolution: {n}", n)
        cmb026 = menu.add(
            "QComboBox",
            setObjectName="cmb026",
            setToolTip=self.sb.tooltip.fmt(
                title="Quality",
                body="Sub-samples per texel axis.",
                bullets=[
                    "<b>Fast</b> (1) — point sampling; exact for 1:1 layouts.",
                    "<b>Standard</b> (2) — anti-aliased island edges and a box "
                    "filter for islands packed smaller than their source.",
                    "<b>High</b> (3) — for heavy downscaling.",
                ],
                notes=[
                    "Memory: 8 bytes x quality² x resolution². 4k Standard ≈ 540 MB."
                ],
            ),
        )
        for text, data in [
            ("Quality: Fast", 1),
            ("Quality: Standard", 2),
            ("Quality: High", 3),
        ]:
            cmb026.addItem(text, data)
        cmb026.setCurrentIndex(1)
        s025 = menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Padding: ",
            setObjectName="s025",
            set_limits=[-1, 256],
            setValue=-1,
            setCustomDisplayValues={-1: "Fill"},
            setToolTip=self.sb.tooltip.fmt(
                title="Padding",
                body="Gutter width in texels around each island.",
                bullets=[
                    "<b>Fill</b> (-1) — fill every empty texel (mip-safe, the "
                    "usual choice)."
                ],
            ),
        )
        cmb027 = menu.add(
            "QComboBox",
            setObjectName="cmb027",
            setToolTip=self.sb.tooltip.fmt(
                title="Normal Map Convention",
                body="Y axis of the SOURCE normal maps. Rotated islands mix X and Y, "
                "so this must be right.",
                bullets=[
                    "<b>Auto</b> — classify the filename's map-type suffix through "
                    "the shared map registry, which knows every handedness "
                    "spelling the pipeline emits (<i>_DX</i>, <i>DirectX</i>, "
                    "<i>NRMLDX</i>, <i>N-dx</i> …) and ignores a trailing UDIM or "
                    "duplicate token.",
                ],
                notes=[
                    "A map with no convention tag (plain <i>_Normal</i>) is read "
                    "as OpenGL: the convention is unknown, and flipping a guess "
                    "inverts a map that may already be right. Override here when "
                    "the filename does not say.",
                ],
            ),
        )
        for text, data in [
            ("Normals: Auto", None),
            ("Normals: OpenGL (Y+)", "opengl"),
            ("Normals: DirectX (Y-)", "directx"),
        ]:
            cmb027.addItem(text, data)
        # Required, and deliberately NOT persisted: it names ONE deliverable.
        # ``restore_state`` is set before ``Menu.add``'s deferred
        # ``register_widget`` runs, which is the only window in which the
        # opt-out is read (``MainWindow.register_widget`` defaults it to True
        # only when the attribute is absent).
        t_tt_name = menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText="Output name (required)",
            setObjectName="t_tt_name",
            setToolTip=self.sb.tooltip.fmt(
                title="Output Name",
                body="Names BOTH halves of the result: the material that gets "
                "assigned, and every map wired to it "
                "(<i>&lt;name&gt;_&lt;Channel&gt;.png</i>).",
                notes=[
                    "Required — there is no sensible default for a deliverable, "
                    "so the texture pass is refused without one.",
                    "Not remembered between sessions: it names one specific "
                    "result, and a name left over from the last scene would "
                    "overwrite that scene's material and maps without asking.",
                    "Re-running with the same name replaces that material and "
                    "its maps — which is what a second attempt wants.",
                    "A run that has to keep two UV layouts apart appends each "
                    "layout's label, so their maps cannot collide.",
                ],
            ),
        )
        t_tt_name.restore_state = False
        t_tt_name.option_box.clear_option = True
        # A uitk LineEdit for the option-box affordances: the clear icon
        # shows only while there is text (ClearOption auto-hides), and the
        # browse writes back the PORTABLE spelling — relative to
        # the .blend's textures folder when the pick is under it, which survives the project
        # being moved. The engine reads the entry the same way
        # (btk.TextureTransfer.resolve_output_dir), so "relative" is a real
        # contract rather than a UI convention.
        t_tt_output = menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText="Output folder (blank = //textures/uv_transfer)",
            setText="",
            setObjectName="t_tt_output",
            setToolTip=self.sb.tooltip.fmt(
                title="Output Folder",
                body="Where the maps are written, as "
                "<i>&lt;name&gt;_&lt;Channel&gt;.png</i>.",
                bullets=[
                    "<b>Blank</b> — <i>//textures/uv_transfer</i>.",
                    "<b>A relative entry</b> — a subdirectory of the .blend's textures folder; "
                    "the portable spelling, since it survives a project move.",
                    "<b>A full path</b> — used as-is.",
                ],
            ),
        )
        t_tt_output.option_box.clear_option = True
        t_tt_output.option_box.browse(
            mode="directory",
            title="Transfer output folder",
            tooltip="Browse for the output folder…",
            start_dir=lambda w=t_tt_output: btk.TextureTransfer.resolve_output_dir(
                w.text()
            ),
            callback=lambda picked, w=t_tt_output: w.setText(
                ptk.FileUtils.relativize_output_dir(
                    picked, btk.TextureTransfer.output_base_dir()
                )
            ),
        )
        chk050 = menu.add(
            "QCheckBox",
            setText="Assign Result",
            setObjectName="chk050",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Assign Result",
                body="Build one material per shared UV set — materials whose "
                "islands share a set and do not overlap merge into it — wired "
                "to the new maps and assigned to every transferred face.",
                notes=[
                    "Named after <b>Output Name</b>; a run that has to keep two "
                    "layouts apart appends each layout's label.",
                    "The original materials are never modified.",
                ],
            ),
        )
        self._tt_sources = []
        # Direct references: ``Menu.add`` registers the ``menu.<name>`` proxies
        # on a timer, so they are not addressable from inside this init.
        self._tt_ctl = {
            "source": cmb024,
            "scope": cmb014,
            "similarity": d000,
            "transfer": cmb028,
            "texture_controls": (
                t_tt_src_uvset,
                t_tt_dst_uvset,
                cmb025,
                cmb026,
                s025,
                cmb027,
                t_tt_name,
                t_tt_output,
                chk050,
            ),
        }
        for w in (cmb024, cmb014, cmb028):
            w.currentIndexChanged.connect(lambda *_: self._tt_sync_controls())
        self._tt_sync_controls()

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

    def _tt_source_tooltip(self):
        """Live tooltip for Set Source From Selection -- what is stored NOW.

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
            title="Set Source From Selection",
            body="Capture the current selection as the <b>Stored Source "
            "Meshes</b> (mesh objects; collections/empties contribute their "
            "mesh children). Read by the <i>Stored Source Meshes</i> source.",
            noun="stored source mesh(es)",
            empty_text="Nothing stored yet — the <i>Stored Source Meshes</i> "
            "source has nothing to read from.",
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

    @btk.undoable
    def b000(self, widget):
        """Transfer UVs OR textures -- one pass per run (mirror of Maya's ``b000``)."""
        menu = widget.option_box.menu
        mode = menu.cmb024.currentData() or "first"
        scope = menu.cmb014.currentData() or "order"
        selected = self.selected_objects()
        transfer_mode = menu.cmb028.currentData()
        auto = transfer_mode == self.TRANSFER_AUTO
        # Source candidates, resolved ONCE and reused by the mode branches
        # below: Auto's probe and the pass must read the SAME meshes, or the
        # probe could decide from meshes the run then doesn't use.
        active = self.active_object()
        stored_sources = [
            bpy.data.objects[n]
            for n in getattr(self, "_tt_sources", [])
            if n in bpy.data.objects
        ]
        if auto and mode != "uvset":
            # Resolved BEFORE the pass-dependent gates below (Output Name, the
            # Similar-scope check): what Auto decides is what they must ask
            # for. An empty probe resolves to the UV pass and falls through to
            # the same selection errors a manual mode would hit.
            if mode == "first":
                probe = [active] if active is not None and active.type == "MESH" else []
            else:
                probe = stored_sources
            transfer_mode = self._tt_resolve_auto(btk.TextureTransfer, probe)
        do_uvs, do_textures = self._tt_passes(mode, transfer_mode)
        auto_note = self._tt_auto_note(auto, do_textures, mode)
        if not (do_uvs or do_textures):
            return self.sb.message_box(
                "<b>Nothing to transfer.</b><br>The <i>UV Map On Same Mesh</i> "
                "source has no second mesh to read a layout from, so it "
                "transfers textures — pick a <b>Transfer</b> mode that "
                "includes them."
            )
        # Checked before anything is touched: the texture pass writes files and
        # builds a material, and finding out it had no name after the remap has
        # already run costs the whole run.
        out_name = menu.t_tt_name.text().strip()
        if do_textures and not out_name:
            return self.sb.message_box(
                "<b>Output Name required.</b><br>Open the option box and name "
                "the result — it names the new material and its maps." + auto_note
            )

        # ---- resolve source(s) and targets -------------------------------
        # pairs: [(source, target), ...] for the UV pass (None = found by scope)
        pairs = None
        source = None
        others = []
        if mode == "uvset":
            targets = self._tt_meshes(selected)
            if not targets:
                return self.sb.message_box(
                    "<b>Nothing selected.</b><br>Select the mesh(es) to transfer on."
                )
        elif mode == "first":
            if active is None or active.type != "MESH":
                return self.sb.message_box(
                    "<b>Make the source mesh active</b>"
                    + (
                        ", with the target mesh(es) selected."
                        if scope != "scene"
                        else "."
                    )
                )
            source = [active]
            others = [t for t in self._tt_meshes(selected) if t is not active]
            if scope != "scene" and not others:
                return self.sb.message_box(
                    "<b>Insufficient selection.</b><br>Select the target mesh(es) "
                    "with the source mesh active."
                )
            if scope == "order":
                targets = others
                pairs = [(active, t) for t in targets]
            else:
                if not do_uvs:
                    return self.sb.message_box(
                        "<b>The Similar scopes need a Transfer mode that "
                        "includes UV Map</b> -- the UV pass is what finds their "
                        "targets. Use Selection Order to transfer textures alone."
                        + auto_note
                    )
                targets = None  # found by transfer_uvs_to_similar below
        else:
            source = stored_sources
            if not source:
                return self.sb.message_box(
                    "<b>No stored source meshes.</b><br>Open the option box and use "
                    "<i>Set Source From Selection</i> first."
                )
            targets = [t for t in self._tt_meshes(selected) if t not in source]
            if not targets:
                return self.sb.message_box(
                    "<b>Nothing selected.</b><br>Select the target mesh(es)."
                )
            try:
                pairs = [
                    (s, t)
                    for t, s in btk.TextureTransfer.pair_by_name(
                        targets, source
                    ).items()
                ]
            except ValueError as e:
                return self.sb.message_box(f"<b>Transfer:</b><br>{e}")

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
                        candidates = others if scope == "selection" else None
                        targets = btk.transfer_uvs_to_similar(
                            source[0],
                            candidates,
                            tolerance=menu.d000.value(),
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
                try:
                    results = btk.TextureTransfer().transfer(
                        targets,
                        source,
                        source_uv_set=menu.t_tt_src_uvset.text().strip() or None,
                        target_uv_set=menu.t_tt_dst_uvset.text().strip() or None,
                        size=menu.cmb025.currentData() or None,
                        supersample=menu.cmb026.currentData() or 2,
                        padding=menu.s025.value(),
                        output_name=out_name,
                        output_dir=menu.t_tt_output.text().strip() or None,
                        normal_convention=menu.cmb027.currentData(),
                        assign=menu.chk050.isChecked(),
                    )
                except ValueError as e:
                    report.append(f"<b>Transfer Textures:</b> {e}")
                else:
                    n_maps = sum(len(v) for v in results.values())
                    folder = next(
                        (
                            os.path.dirname(p)
                            for v in results.values()
                            for p in v.values()
                        ),
                        "",
                    )
                    report.append(
                        f"Transferred <b>{n_maps}</b> map(s) for "
                        f"<b>{len(results)}</b> material(s)"
                        + (
                            f'<br><a href="action://open?path={folder}">{folder}</a>'
                            if folder
                            else ""
                        )
                    )
        self.sb.message_box("<br><br>".join(report))

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

    def cmb003(self, index, widget):
        """UV Map Size — passive input; the panel's one map size, read via
        get_map_size by Get/Set Texel Density, Auto Unwrap's engine modes, and
        Cut Cylinder's island gutter. Nothing to do on change."""

    def s003(self, value, widget):
        """Texel Density — passive input; read by Get/Set Texel Density (b003/b004).
        Nothing to do on change."""


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
