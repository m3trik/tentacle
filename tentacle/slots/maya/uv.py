# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya
from tentacle.slots._uv import UvMixin


class UvSlots(UvMixin, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu

        # Assure the maya UV plugin is loaded
        mtk.load_plugin("Unfold3D.mll")

        # Dual-state toggle state for b029 (Pin) and b030 (Stack).
        # Each button tracks the selection captured at its last successful
        # action; on the next click we compare to the live selection and reset
        # the toggle if it changed. This is more robust than a SelectionChanged
        # scriptJob — Maya can fire SelectionChanged as a side effect of UV
        # commands (e.g. texStackShells), which would silently reset our flag
        # mid-operation.
        self._b029_pinned = False
        self._b029_last_selection = None
        self._b030_stacked = False
        self._b030_last_selection = None
        self._b030_uv_snapshot = None

    def get_map_size(self):
        """Get the map size from the combobox as an int. ie. 2048"""
        return int(self.ui.cmb003.currentText())

    def header_init(self, widget):
        """Initialize UV Menu Header"""
        # Every entry is a one-shot action — dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Create UV Snapshot",
            setObjectName="uv_snapshot",
            setToolTip="Save an image file of the current UV layout.",
        )
        widget.menu.uv_snapshot.clicked.connect(lambda: mel.eval("UVCreateSnapshot"))
        widget.menu.add(
            "QPushButton",
            setText="Open UV Editor",
            setObjectName="uv_editor",
            setToolTip="Open the texture coordinate mapping window.",
        )
        widget.menu.uv_editor.clicked.connect(lambda: self.b031())
        widget.menu.add(
            "QPushButton",
            setText="RizomUV Bridge",
            setObjectName="btn_rizom_bridge",
            setToolTip="Round-trip selected meshes through RizomUV using a Lua preset.",
        )
        widget.menu.btn_rizom_bridge.clicked.connect(lambda: self.b032())

    def tb000_init(self, widget):
        """Initialize UV packing tool interface.

        Sets up the UV packing options menu with controls for:
        - Method: Which packer runs — Maya's u3dLayout, or the optional
          external xatlas engine (pip-installable; the slot reports the
          install command when it's missing)
        - Brute Force / Rotate Shells: xatlas-only quality/orientation toggles
        - Pre-Scale Mode: How shells are scaled before packing (both methods)
        - Pre-Rotate Mode: One-shot shell orientation before packing
        - Rotate Step/Min/Max: Packing-time rotation search (active when Max > Min)
        - Mutations: Optimization passes (higher = better pack, slower)
        - UDIM: Target UDIM tile space for the packed UVs (both methods)
        - Tile Coverage: Fraction of the target tile to pack into (both methods)
        - Scale Mode: Post-pack scale-to-fit (fill / keep density / stretch)
        - Tiles U/V: Distribute shells across a grid of UDIM tiles
        - Skip Instances: Pack one representative per instance group (both)

        Gates (mirroring tb001's per-mode pattern): the u3dLayout-only
        controls disable under xatlas and vice versa; Rotate Step is
        auto-disabled when Rotate Max <= Rotate Min (no range to step
        through); Tile Coverage disables while a tile grid is active — the
        pack uses Full then (grid cells are copies of the pack region).

        Parameters:
            widget: The parent widget to add menu items to
        """
        widget.option_box.menu.setTitle("Pack UVs")
        # Method selector. Item data is the dispatch key consumed by tb000 --
        # "standard" for Maya's u3dLayout, "xatlas" for the external engine
        # (mtk.UvUtils.pack_uvs -> ptk.UvPack; same optional-engine pattern
        # as Auto Unwrap's cmb011).
        cmb019 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb019",
            setToolTip=self.sb.tooltip.fmt(
                title="Pack Method",
                body="Which packing engine runs.",
                bullets=[
                    "<b>Standard</b> — Maya's <code>u3dLayout</code> (Unfold3D). "
                    "Drives the full option set below.",
                    "<b>xatlas</b> — open-source external engine "
                    "(<code>pip install xatlas</code>). Scale-searches the "
                    "shells to fill the target region edge-to-edge; adds shell "
                    "rotation and a brute-force placement search.",
                ],
                notes=["Options that apply to only one method disable for the other."],
            ),
        )
        for text, data in [
            ("Method: Standard (u3dLayout)", "standard"),
            ("Method: xatlas", "xatlas"),
        ]:
            cmb019.addItem(text, data)
        cmb019.setCurrentIndex(0)  # Standard — needs no external engine
        # xatlas-only toggles (grouped with the method that owns them).
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rotate Shells (xatlas)",
            setObjectName="chk044",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Shells (xatlas)",
                body="Let xatlas re-orient shells wherever that packs tighter.",
                bullets=[
                    "<b>On</b> — 90° steps, plus an arbitrary-angle turn onto "
                    "each shell's own axis where that helps. Which of the two "
                    "wins depends on the mesh, so both are tried and the "
                    "tighter result is kept.",
                    "<b>Off</b> — shells keep their orientation exactly.",
                ],
                notes=[
                    "The xatlas counterpart of the Rotate Min / Max search below.",
                    "Like u3dLayout, the engine may still mirror shells "
                    "regardless of this setting.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Brute Force (xatlas)",
            setObjectName="chk043",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Brute Force (xatlas)",
                body="Exhaustive placement search — xatlas' main density lever. "
                "It competes with normal placement rather than replacing it, so "
                "turning it on can only hold or improve the result.",
                rows=[
                    ("Density", "cube 0.62 → 0.64; 4 hard-surface meshes 0.63 → 0.67"),
                    ("Cost", "2–15× slower (0.8s → 11s on 4 organic meshes at 1024); "
                     "grows steeply with shell count"),
                ],
                notes=[
                    "Measured at 1024 into a full tile; Standard packs the same "
                    "cube to 0.65.",
                    "A cube cut into 6 equal squares cannot exceed 0.67 in a "
                    "square tile no matter the packer — low fill there is the "
                    "shape of the shells, not the engine.",
                ],
            ),
        )
        # Pre-Scale Mode. Empirically, u3dLayout has only two distinct -preScaleMode
        # behaviors in Maya 2025 (re-verified: values 1-4 give identical results):
        # omitted/0 keeps input UV proportions; any non-zero value rescales shells
        # by 3D area. Stock Maya's "Preserve UV" UI option actually emits -scl 3,
        # which behaves as Preserve 3D — so don't expose the broken intermediates.
        cmb009 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb009",
            setToolTip=self.sb.tooltip.fmt(
                title="Pre-Scale Mode",
                body="How shells are sized relative to each other before packing.",
                bullets=[
                    "<b>Preserve UV</b> — keep each shell's current UV size "
                    "relative to the others.",
                    "<b>Preserve 3D</b> — rescale so UV area follows 3D surface "
                    "area, giving every packed shell the same texel density.",
                ],
            ),
        )
        for text, data in [
            ("Pre-Scale: Preserve UV", 0),
            ("Pre-Scale: Preserve 3D", 1),
        ]:
            cmb009.addItem(text, data)
        cmb009.setCurrentIndex(1)  # matches prior default (preScaleMode=1)

        # Pre-Rotate Mode. Mirrors Maya's stock dialog
        # (performPolyLayoutUV.mel:662-670). Values are passed through directly;
        # 0 = omit the flag.
        cmb010 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb010",
            setToolTip=self.sb.tooltip.fmt(
                title="Pre-Rotate Mode",
                body="One-shot re-orient applied to every shell before packing "
                "(<code>u3dLayout -preRotateMode</code>).",
                notes=[
                    "The axis modes (X / Y / Z to V) orient by the underlying "
                    "3D mesh, not by the shell's UV bounds.",
                ],
            ),
        )
        for text, data in [
            ("Pre-Rotate: Off", 0),
            ("Pre-Rotate: Horizontal (long axis to U)", 1),
            ("Pre-Rotate: Vertical (long axis to V)", 2),
            ("Pre-Rotate: Axis X to V", 3),
            ("Pre-Rotate: Axis Y to V", 4),
            ("Pre-Rotate: Axis Z to V", 5),
        ]:
            cmb010.addItem(text, data)
        cmb010.setCurrentIndex(0)  # Off (matches prior default of 0)
        # Packing-time rotation search: active when Rotate Max > Rotate Min.
        # Independent of Pre-Rotate Mode. Verified: the search only re-orients
        # a shell when that tightens the pack (single shells stay put), and a
        # degenerate equal Min/Max range breaks packing — the > gate below
        # keeps that range from ever being emitted.
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Step: ",
            setObjectName="s011",
            set_limits=[1, 360],
            setValue=90,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Step",
                body="Increment, in degrees, between the shell orientations tried "
                "while packing.",
                bullets=[
                    "<b>90</b> — keeps every shell axis-aligned.",
                    "<b>Smaller</b> — tries more orientations, at more cost.",
                ],
                notes=["Active only while Rotate Max &gt; Rotate Min."],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Min: ",
            setObjectName="s012",
            set_limits=[0, 360],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Min",
                body="Lower bound, in degrees, of the packing-time rotation search.",
                notes=["The search only runs while Rotate Max &gt; Rotate Min."],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Rotate Max: ",
            setObjectName="s013",
            set_limits=[0, 360],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Max",
                body="Upper bound, in degrees, of the packing-time rotation search. "
                "<b>0</b> (the default) disables rotation — raise it above Rotate "
                "Min to opt in.",
                notes=[
                    "A shell is only re-oriented where that tightens the pack.",
                    "0–180 with a 90° step is the usual choice.",
                    "Measurably helps fractional Tile Coverage regions — a "
                    "half-tile box packed 0.55 → 0.71 fill on test content.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Mutations: ",
            setObjectName="s014",
            set_limits=[1, 50],
            setValue=1,
            setToolTip=self.sb.tooltip.fmt(
                title="Mutations",
                body="How many packing attempts to iterate on "
                "(<code>u3dLayout -mutations</code>). Higher values pack tighter "
                "at the cost of CPU time.",
                notes=[
                    "Maya's own dialog allows 1–50.",
                    "The flag is only emitted above 1.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="UDIM: ",
            setObjectName="s004",
            set_limits=[1001, 1200],
            setValue=1001,
            setToolTip=self.sb.tooltip.fmt(
                title="UDIM",
                body="The tile the shells are packed into (1001–1200).",
                rows=[
                    ("1001", "first tile — UV 0–1, 0–1"),
                    ("1002", "second tile — UV 1–2, 0–1"),
                    ("1011", "start of the next row — UV 0–1, 1–2"),
                ],
            ),
        )
        # Fractional-tile packing: u3dLayout's -packBox accepts fractional
        # extents, so packing into half / a quarter of the target tile is
        # a plain box shrink (anchored at the tile's bottom-left corner).
        cmb015 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb015",
            setToolTip=self.sb.tooltip.fmt(
                title="Tile Coverage",
                body="Which fraction of the target UDIM tile to pack into, "
                "anchored at the tile's bottom-left corner. Use it to reserve "
                "the rest of the tile for other shells.",
                notes=["Locked to Full while a Tiles U / V grid is active."],
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
        # Post-pack scale-to-fit (u3dLayout -layoutScaleMode). Verified: flag
        # omitted behaves as Uniform (2); 1 disables the fit — shells keep
        # their exact input UV scale and overflow spills into the neighboring
        # tile instead of overlapping; 3 scales U/V independently to fill.
        cmb018 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb018",
            setToolTip=self.sb.tooltip.fmt(
                title="Scale Mode",
                body="How shells are scaled to the pack region once they are placed.",
                bullets=[
                    "<b>Fill (uniform)</b> — scale all shells together to fill "
                    "the region. Maya's default.",
                    "<b>Off (keep density)</b> — shells keep their exact UV scale. "
                    "Anything that doesn't fit spills into the neighboring tile "
                    "rather than overlapping.",
                    "<b>Stretch (non-uniform)</b> — scale U and V independently "
                    "to fill the region. Distorts.",
                ],
                notes=[
                    "Pair <b>Off</b> with <b>Pre-Scale: Preserve UV</b> to re-arrange "
                    "shells without touching texel density.",
                ],
            ),
        )
        for text, data in [
            ("Scale Mode: Fill (uniform)", 2),
            ("Scale Mode: Off (keep density)", 1),
            ("Scale Mode: Stretch (non-uniform)", 3),
        ]:
            cmb018.addItem(text, data)
        cmb018.setCurrentIndex(0)
        # Multi-tile distribution (u3dLayout -tileU/-tileV). Verified: the grid
        # anchors at the pack box and extends right/up in box-sized cells, so
        # it composes with the UDIM spinbox — but fractional Tile Coverage
        # would make the cells sub-tile sized, so the gate below locks
        # coverage to Full while a grid is active.
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Tiles U: ",
            setObjectName="s019",
            set_limits=[1, 10],
            setValue=1,
            setToolTip=self.sb.tooltip.fmt(
                title="Tiles U",
                body="Spread the shells across a grid this many UDIM tiles wide. "
                "<b>1</b> (the default) packs into the single target tile.",
                rows=[("UDIM 1001, Tiles 2 × 2", "fills 1001–1002 and 1011–1012")],
                notes=[
                    "The grid anchors at the target UDIM and extends right / up.",
                    "Clamped so it never runs past the end of the UDIM row "
                    "(a row is 10 tiles wide) — the completion message says when.",
                ],
            ),
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Tiles V: ",
            setObjectName="s020",
            set_limits=[1, 10],
            setValue=1,
            setToolTip=self.sb.tooltip.fmt(
                title="Tiles V",
                body="Spread the shells across a grid this many UDIM tiles tall. "
                "<b>1</b> (the default) packs into the single target tile.",
                notes=["See <b>Tiles U</b> for how the grid is anchored."],
            ),
        )
        # Instances share a single shape + UV set, so packing every instance is
        # redundant and forces the packer to reserve tile space for each
        # identical copy (lowering density). When on, only one representative
        # per instance group is packed; the shared UVs apply to all of them.
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Skip Instances",
            setObjectName="chk016",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Skip Instances",
                body="Pack one representative transform per instance group.",
                notes=[
                    "Instances share a single shape and UV set, so packing every "
                    "copy just reserves tile space for identical shells — the "
                    "result already applies to all of them.",
                    "Ignored for component (face / UV) selections.",
                ],
            ),
        )
        # Gates. Per-method: the u3dLayout-only controls disable under xatlas
        # (pre-rotate, rotation search, mutations, scale mode, tile grid) and
        # the xatlas toggles disable under Standard; Pre-Scale, UDIM, Tile
        # Coverage and Skip Instances apply to both. Within Standard: Rotate
        # Step is meaningless when Rotate Max <= Rotate Min, and Tile Coverage
        # disables while a tile grid is active — the slot packs Full then
        # (grid cells are copies of the pack region; a fractional region would
        # carve sub-tile cells instead of real UDIM tiles). Disable-only:
        # resetting a combo would destroy the user's persisted choice.
        menu = widget.option_box.menu

        def _sync_gates():
            standard = menu.cmb019.currentData() == "standard"
            menu.chk043.setEnabled(not standard)
            menu.chk044.setEnabled(not standard)
            menu.cmb010.setEnabled(standard)
            menu.s011.setEnabled(standard and menu.s013.value() > menu.s012.value())
            menu.s012.setEnabled(standard)
            menu.s013.setEnabled(standard)
            menu.s014.setEnabled(standard)
            menu.cmb018.setEnabled(standard)
            menu.s019.setEnabled(standard)
            menu.s020.setEnabled(standard)
            grid = standard and (menu.s019.value() > 1 or menu.s020.value() > 1)
            menu.cmb015.setEnabled(not grid)

        menu.cmb019.currentIndexChanged.connect(_sync_gates)
        menu.s012.valueChanged.connect(_sync_gates)
        menu.s013.valueChanged.connect(_sync_gates)
        menu.s019.valueChanged.connect(_sync_gates)
        menu.s020.valueChanged.connect(_sync_gates)
        _sync_gates()

    def _pack_u3d(self, all_uvs, meshes, pack_kwargs, successful, failed) -> None:
        """Native u3dLayout pack with per-mesh failure isolation.

        Batches all meshes into one call; on failure with several meshes,
        probes each to isolate the bad one(s) and re-packs the survivors
        together so they share the tile. A single mesh reports its failure
        directly — a probe pass would just re-run the same failing call.
        Appends to *successful* / *failed* in place.
        """
        try:
            cmds.u3dLayout(all_uvs, **pack_kwargs)
            successful.extend(str(m) for m in meshes)
            return
        except RuntimeError as batch_error:
            if len(meshes) == 1:
                failed.append((str(meshes[0]), self._classify_u3d_error(batch_error)))
                return

        good = []
        for mesh in meshes:
            uvs = cmds.polyListComponentConversion(mesh, fromFace=True, toUV=True) or []
            if not uvs:
                continue
            try:
                cmds.u3dLayout(uvs, **pack_kwargs)
                good.extend(uvs)
                successful.append(str(mesh))
            except RuntimeError as mesh_error:
                failed.append((str(mesh), self._classify_u3d_error(mesh_error)))
        if good:
            try:
                cmds.u3dLayout(good, **pack_kwargs)
            except RuntimeError as combine_error:
                # Survivors packed individually (each filling the tile);
                # combine failed, so leave them as-is and surface the cause.
                failed.append(
                    ("<combined re-pack>", self._classify_u3d_error(combine_error))
                )

    @staticmethod
    def _classify_u3d_error(error) -> str:
        """Condense an Unfold3D RuntimeError (u3dLayout / u3dUnfold / u3dOptimize)
        into a short, human-readable reason for display in a message box.
        """
        msg = str(error)
        low = msg.lower()
        if "non-manifold" in low:
            return "non-manifold vertices"
        if "overlapping" in low:
            return "overlapping UVs"
        return msg.split("\n")[0][:50]

    @staticmethod
    def _non_manifold_vertices(objects):
        """Map each mesh in *objects* to its non-manifold vertices, via polyInfo.

        Native ``polyInfo`` is instant, unlike ``EditUtils.find_non_manifold_vertex``
        whose per-vertex Python scan is too slow for the heavy meshes that trip
        Unfold. Returns ``{mesh_shape: [vertex_components]}`` (only meshes that
        have any; empty dict when there are none).
        """
        by_mesh = {}
        if not objects:
            return by_mesh
        for shape in cmds.ls(objects, dag=True, type="mesh", noIntermediate=True) or []:
            verts = cmds.polyInfo(shape, nonManifoldVertices=True) or []
            if verts:
                by_mesh[shape] = cmds.ls(verts, flatten=True)
        return by_mesh

    def _warn_and_select_non_manifold(self, objects):
        """Select the non-manifold vertices (or UVs) on *objects* and explain.

        Backs the 'Warn + Select' strategy and the fallback when a repair can't
        make the mesh unfoldable. Unfold rejects non-manifold *UVs* with the
        same error as bad geometry, so when no vertices are flagged the UV scan
        is what locates the problem.
        """
        verts = [v for vs in self._non_manifold_vertices(objects).values() for v in vs]
        uvs = [
            uv
            for us in mtk.Diagnostics.find_non_manifold_uvs(objects).values()
            for uv in us
        ]
        if verts:
            cmds.selectMode(component=True)
            cmds.selectType(vertex=True)
            cmds.select(verts, replace=True)
        elif uvs:
            cmds.selectMode(component=True)
            cmds.selectType(polymeshUV=True)
            cmds.select(uvs, replace=True)
        if verts or not uvs:
            kind = "geometry"
            n = len(verts)
            selected = (
                f"<b>{n}</b> problem {'vertex' if n == 1 else 'vertices'} "
                "selected in vertex mode.<br><br>"
                if verts
                else ""
            )
            cause = (
                "Unfold can't flatten a mesh with <b>non-manifold vertices</b> — "
                "points where the surface branches or folds back on itself.<br><br>"
            )
            manual = "• run <b>Mesh &gt; Cleanup</b> / <b>Merge</b> doubled verts manually.<br><br>"
        else:
            kind = "UVs"
            n = len(uvs)
            selected = (
                f"<b>{n}</b> problem {'UV' if n == 1 else 'UVs'} selected in UV mode.<br><br>"
            )
            cause = (
                "Unfold can't flatten a mesh with <b>non-manifold UVs</b> — "
                "corrupt UV topology (usually from an import) that Maya's own "
                "tools can't author.<br><br>"
            )
            manual = "• delete the UVs on the affected faces and re-project them manually.<br><br>"
        self.sb.message_box(
            f"<b>⚠ Unfold stopped — non-manifold {kind}</b><br><br>"
            f"{cause}"
            f"{selected}"
            "<b>To fix:</b><br>"
            "• Set the Unfold option to <b>Repair + Retry</b> to auto-clean, or<br>"
            f"{manual}"
            "<i>Then run Unfold again.</i>"
        )

    def _repair_non_manifold(self, objects):
        """Auto-repair non-manifold geometry and UVs on *objects*.

        Geometry goes through Mesh Cleanup; non-manifold *UVs* (which block
        Unfold with the same error but which Cleanup can't touch) are repaired
        by re-mapping the affected faces. Logs a per-mesh breakdown to the
        console and returns a summary ``{"total", "fixed", "remaining"}`` of
        non-manifold components, so the caller can briefly mention the repair
        in its result message.
        """
        before_verts = self._non_manifold_vertices(objects)
        before_uvs = mtk.Diagnostics.find_non_manifold_uvs(objects)
        total = sum(len(v) for v in before_verts.values()) + sum(
            len(v) for v in before_uvs.values()
        )

        print("# Unfold: auto-repairing non-manifold geometry #")
        for shape, verts in before_verts.items():
            print(f"#   {shape}: {len(verts)} non-manifold vertex(es) #")
        for shape, uvs in before_uvs.items():
            print(f"#   {shape}: {len(uvs)} non-manifold UV(s) #")

        try:
            mtk.Diagnostics.clean_geometry(objects, repair=True, nonmanifold=True)
        except (RuntimeError, ValueError) as exc:
            # Cleanup itself failed — the retry will fall back to Warn + Select.
            print(f"# Unfold: cleanup failed: {exc} #")

        # Unconditional: it re-scans internally (no-op on clean meshes), and the
        # pre-scan above can't see UV corruption the Cleanup pass just exposed.
        try:
            mtk.Diagnostics.repair_non_manifold_uvs(objects)
        except (RuntimeError, ValueError) as exc:
            print(f"# Unfold: UV repair failed: {exc} #")

        remaining = sum(
            len(v) for v in self._non_manifold_vertices(objects).values()
        ) + sum(len(v) for v in mtk.Diagnostics.find_non_manifold_uvs(objects).values())
        fixed = total - remaining
        print(
            f"# Unfold: repaired {fixed} non-manifold component(s), {remaining} remaining #"
        )
        return {"total": total, "fixed": fixed, "remaining": remaining}

    def tb000(self, widget):
        """Pack UVs with specified settings.

        Performs UV packing operation on selected objects using Maya's u3dLayout command
        with user-specified scaling, rotation, and UDIM settings.

        The packing operation:
        1. Gets UV packing parameters from UI controls
        2. Calculates appropriate padding based on texture resolution
        3. Packs UVs from all selected meshes together into the target UDIM tile
           (if the batched call fails with several meshes, probes each to
           isolate the offending one and re-packs the survivors together;
           a single mesh reports its failure directly)

        Parameters:
            widget: The widget containing the menu controls with packing options

        UI Parameters used:
            method (str): cmb019. "standard" — Maya u3dLayout (default) —
                or "xatlas" — the optional external engine, dispatched to
                mtk.UvUtils.pack_uvs. Under xatlas, Pre-Scale, UDIM, Tile
                Coverage and Skip Instances still apply; the u3dLayout-only
                options are gated off, and chk043 (Brute Force) / chk044
                (Rotate Shells) apply instead. A missing engine surfaces as
                a message box carrying the pip install command.
            scale (int): Pre-scale mode from cmb009 (Maya -preScaleMode)
                - 0: Preserve UV (no rescaling), 1: Preserve 3D (uniform by 3D area)
            rotate (int): Pre-rotate mode from cmb010 (Maya -preRotateMode)
                - 0: Off, 1: Horizontal, 2: Vertical, 3-5: Axis X/Y/Z to V
            rotate_step/min/max (int): Packing-time rotation search.
                Active only when max > min; independent of pre-rotate mode.
            mutations (int): s014 spinbox (Maya -mutations). Optimization passes;
                only emitted when > 1.
            UDIM (int): Target UDIM tile number (s004), e.g., 1001
            coverage (tuple): cmb015. (u, v) fraction of the target tile the
                pack fills, anchored bottom-left (fractional -packBox).
            scale_mode (int): cmb018 (Maya -layoutScaleMode). 2: uniform
                scale-to-fill (command default; flag omitted), 1: no scaling
                (keep texel density; overflow spills to the next tile),
                3: non-uniform stretch-to-fill. Only emitted when != 2.
            tiles_u/tiles_v (int): s019/s020 (Maya -tileU/-tileV). When either
                > 1, shells distribute across a grid of UDIM tiles anchored at
                the target tile, extending right/up. Coverage is forced Full,
                and Tiles U is clamped so the grid stays inside the UDIM row.
            skip_instances (bool): chk016. When on (default), pack one
                representative per instance group instead of every instance.
                Object-level selection only; ignored for component selections.

        Note:
            - Requires at least one object to be selected
            - Automatically calculates shell and tile padding based on map size
            - Meshes with errors (e.g., non-manifold vertices) are skipped with a summary
            - The completion message reports the resulting texel density
              (px/unit) for the packed meshes, plus the map size and target UDIM
        """
        menu = widget.option_box.menu
        method = menu.cmb019.currentData()
        scale = menu.cmb009.currentData()
        rotate = menu.cmb010.currentData()
        UDIM = menu.s004.value()
        rotate_step = menu.s011.value()
        rotate_min = menu.s012.value()
        rotate_max = menu.s013.value()
        mutations = menu.s014.value()
        scale_mode = menu.cmb018.currentData()
        tiles_u = menu.s019.value()
        tiles_v = menu.s020.value()
        map_size = self.get_map_size()
        # The tile grid is u3dLayout-only (gated in the UI; force here too so
        # a persisted spinbox value can't leak into the engine path).
        if method != "standard":
            tiles_u = tiles_v = 1

        # packBox is [umin, umax, vmin, vmax], anchored at the UDIM's tile corner.
        u_tile, v_tile = mtk.udim_to_tile(UDIM)
        # A UDIM row is 10 tiles wide and u wraps to the next row at 10 — the
        # tile at u=10 is NOT the next UDIM — so shells packed past the row
        # end would be unaddressable by any UDIM texture. Clamp the grid to
        # the columns remaining from the anchor and say so in the summary.
        tiles_u_requested = tiles_u
        tiles_u = min(tiles_u, 10 - u_tile)
        # Gutters (verified): -shellSpacing is per-shell padding in UV units —
        # adjacent shells land 2x spacing apart — and it rescales with the
        # post-pack fit; -tileMargin is an absolute inset from the region edges.
        shellPadding = mtk.calculate_uv_padding(map_size, normalize=True)
        tilePadding = shellPadding / 2

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least one selected object."
            )
            return

        # Instances share one shape + UV set, so packing every instance is
        # redundant and forces the packer to reserve tile space for each
        # identical copy. Keep one transform per instance group (object-level
        # selection only — component selections are packed exactly as given).
        if menu.chk016.isChecked() and not any("." in str(s) for s in selection):
            selection = mtk.NodeUtils.filter_duplicate_instances(selection)

        # Get unique meshes from selection (handles both object and component selection)
        meshes = mtk.Components.get_components(selection, "mesh", flatten=False)
        if not meshes:
            meshes = cmds.ls(selection, type="transform", dag=True) or selection

        # Bulk-resolve UVs in one call; keep ranges unflattened ("pCube1.map[0:23]")
        # so we don't pay to expand millions of indices into individual strings.
        all_uvs = (
            cmds.polyListComponentConversion(meshes, fromFace=True, toUV=True) or []
        )
        if not all_uvs:
            self.sb.message_box("<b>No UVs found on selection.</b>")
            return

        # Fractional tile coverage shrinks the pack box from the tile's
        # bottom-left corner; u3dLayout accepts fractional -packBox extents.
        # A tile grid repurposes the box as its cell template (verified), so
        # coverage is forced Full then — the UI gate mirrors this.
        grid = tiles_u > 1 or tiles_v > 1
        cov_u, cov_v = (1.0, 1.0) if grid else menu.cmb015.currentData()

        pack_kwargs = dict(
            resolution=map_size,
            shellSpacing=shellPadding,
            tileMargin=tilePadding,
            preScaleMode=scale,
            preRotateMode=rotate,
            packBox=[u_tile, u_tile + cov_u, v_tile, v_tile + cov_v],
            multiObject=True,  # -m off causes all shells to stack at the tile center
        )
        # Rotate flags only when the user opts in (max > min). Maya's stock dialog
        # follows the same pattern: it omits these unless the "Rotate" checkbox is on.
        # Passing them with the default range (0..180) silently rotates shells even
        # when Pre-Rotate is set to Off.
        if rotate_max > rotate_min:
            pack_kwargs["rotateStep"] = rotate_step
            pack_kwargs["rotateMin"] = rotate_min
            pack_kwargs["rotateMax"] = rotate_max
        if mutations > 1:
            pack_kwargs["mutations"] = mutations
        # Omitted -layoutScaleMode == Uniform (verified), so only emit overrides.
        if scale_mode != 2:
            pack_kwargs["layoutScaleMode"] = scale_mode
        if grid:
            pack_kwargs["tileU"] = tiles_u
            pack_kwargs["tileV"] = tiles_v

        successful = []
        failed = []
        cmds.undoInfo(openChunk=True, chunkName="UV Pack")
        cmds.refresh(suspend=True)
        try:
            if method == "xatlas":
                # External engine path: mtk.UvUtils.pack_uvs owns the whole
                # round-trip (density pre-pass, xatlas, per-shell undoable
                # write-back, per-mesh failure isolation). The engine check
                # runs before the scene is touched, so a missing package
                # surfaces as a message with the pip command, same pattern as
                # Auto Unwrap's engines.
                try:
                    result = mtk.UvUtils.pack_uvs(
                        meshes,
                        map_size=map_size,
                        udim=UDIM,
                        coverage=(cov_u, cov_v),
                        rotate=menu.chk044.isChecked(),
                        brute_force=menu.chk043.isChecked(),
                        preserve_3d=scale == 1,  # cmb009: Preserve 3D
                    )
                    successful = list(result.succeeded)
                    failed = list(result.failed)
                except (RuntimeError, ValueError) as engine_error:
                    self.sb.message_box(
                        f"<b>xatlas pack unavailable.</b><br><br>{engine_error}"
                    )
                    return
            else:
                self._pack_u3d(all_uvs, meshes, pack_kwargs, successful, failed)
        finally:
            cmds.refresh(suspend=False)
            cmds.undoInfo(closeChunk=True)

        # Resulting texel density across the packed meshes — a single
        # representative value (with Preserve-3D pre-scale every shell shares
        # it; with Preserve-UV it's the aggregate of the kept relative scales).
        # Never let a texel-calc hiccup swallow the pack result, so guard it.
        density = 0.0
        if successful:
            try:
                density = mtk.get_texel_density(successful, map_size)
            except Exception as error:
                print(f"# Texel density unavailable: {error}")

        # Shared, easy-to-scan stats block appended to both summaries.
        if grid:
            # Grid extends right/up from the anchor tile (UDIM + 10 per V row).
            last_udim = UDIM + (tiles_u - 1) + 10 * (tiles_v - 1)
            target = f"<b>Target UDIMs:</b> {UDIM}-{last_udim} ({tiles_u} × {tiles_v})"
        else:
            target = f"<b>Target UDIM:</b> {UDIM}"
        stats = (
            (f"<b>Texel Density:</b> {density:,.1f} px/unit<br>" if density else "")
            + f"<b>Map Size:</b> {map_size} × {map_size} px<br>"
            + target
        )
        if tiles_u < tiles_u_requested:
            stats += (
                f"<br><i>Tiles U clamped to {tiles_u} — the grid can't extend "
                f"past the end of the UDIM row.</i>"
            )

        # Report summary
        if failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in failed
            )
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Packed: {len(successful)} mesh(es)<br>"
                f"✗ Skipped: {len(failed)} mesh(es)<br><br>"
                f"{stats}<br><br>"
                f"<b>Skipped meshes:</b><br>{failed_list}<br><br>"
                f"<i>Tip: Use Mesh > Cleanup to fix non-manifold geometry.</i>"
            )
        elif successful:
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Successfully packed {len(successful)} mesh(es).<br><br>"
                f"{stats}"
            )

    def tb001_init(self, widget):
        """Initialize Auto Unwrap.

        The mode combobox (cmb011) picks which algorithm generates the UVs:
        Maya's own auto projection, or one of two external unwrapping engines
        chosen by the kind of model. Scale Mode (cmb012) applies to Standard
        only, so it disables for the engine modes.

        Parameters:
            widget: The parent widget to add menu items to
        """
        menu = widget.option_box.menu
        menu.setTitle("Auto Unwrap")

        # Mode selector. Item data is the key consumed by tb001 -- "standard"
        # for Maya's own projection, else a UvUtils.auto_unwrap method name.
        cmb011 = menu.add(
            "QComboBox",
            setObjectName="cmb011",
            setToolTip=self.sb.tooltip.fmt(
                title="Unwrap Method",
                body="Which algorithm generates the UVs.",
                bullets=[
                    "<b>Standard</b> — Maya's auto projection: the best fit from "
                    "several simultaneous planar projections.",
                    "<b>Hard Surface</b> — Ministry of Flat, an external unwrapper "
                    "that classifies topology and places seams the way an artist "
                    "would. Best for mechanical / architectural models.",
                    "<b>Organic</b> — Boundary First Flattening, an external "
                    "unwrapper using conformal flattening with automatic cone "
                    "singularities. Best for sculpted, scanned and character models.",
                ],
                notes=["Scale Mode below applies to <b>Standard</b> only."],
            ),
        )
        for text, data in [
            ("Standard", "standard"),
            ("Hard Surface (Ministry of Flat)", "hard"),
            ("Organic (BFF)", "organic"),
        ]:
            cmb011.addItem(text, data)
        cmb011.setCurrentIndex(0)  # Standard — needs no external engine

        # Scale Mode (Standard only). Explicit data values fix the old tristate
        # checkbox, whose isChecked() collapsed to a bool and could never emit 2.
        cmb012 = menu.add(
            "QComboBox",
            setObjectName="cmb012",
            setToolTip=self.sb.tooltip.fmt(
                title="Scale Mode",
                body="How the projected shells are scaled afterwards "
                "(<code>polyAutoProjection -scaleMode</code>).",
                bullets=[
                    "<b>None</b> — keep the projected scale.",
                    "<b>Uniform</b> — scale uniformly to fit the unit square.",
                    "<b>Stretch to Square</b> — scale U and V independently to "
                    "fill the unit square. Distorts.",
                ],
                notes=["<b>Standard</b> method only."],
            ),
        )
        for text, data in [
            ("Scale: None", 0),
            ("Scale: Uniform", 1),
            ("Scale: Stretch to Square", 2),
        ]:
            cmb012.addItem(text, data)
        cmb012.setCurrentIndex(1)  # Uniform (matches prior default of scaleMode=1)

        # Gate: enable only the options relevant to the selected mode.
        def _sync_options():
            menu.cmb012.setEnabled(cmb011.currentData() == "standard")

        cmb011.currentIndexChanged.connect(_sync_options)
        _sync_options()

    @mtk.undoable
    def tb001(self, widget):
        """Auto Unwrap: automatically unwrap UVs for the selected objects."""
        menu = widget.option_box.menu
        mode = menu.cmb011.currentData()

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least one selected object."
            )
            return

        if mode in self.AUTO_UNWRAP_ENGINE_MODES:
            # The engine handles its own per-object loop and error reporting.
            return self._run_auto_unwrap(mtk, selection, mode, self.get_map_size())

        scale_mode = menu.cmb012.currentData()
        result = None
        failed = []
        for obj in selection:
            try:
                result = cmds.polyAutoProjection(
                    obj,
                    layoutMethod=0,
                    optimize=1,
                    insertBeforeDeformers=1,
                    scaleMode=scale_mode,  # 0 none, 1 uniform, 2 stretch to square
                    createNewMap=False,  # Create a new UV set, as opposed to editing the current one, or the one given by the -uvSetName flag.
                    projectBothDirections=0,  # If "on" : projections are mirrored on directly opposite faces. If "off" : projections are not mirrored on opposite faces.
                    layout=2,  # 0 UV pieces are set to no layout. 1 UV pieces are aligned along the U axis. 2 UV pieces are moved in a square shape.
                    planes=6,  # intermediate projections used. Valid numbers are 4, 5, 6, 8, and 12
                    percentageSpace=0.2,  # percentage of the texture area which is added around each UV piece.
                    worldSpace=0,
                )  # 1=world reference. 0=object reference.
            except Exception as error:
                failed.append((obj, str(error)))

        if failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in failed
            )
            self.sb.message_box(
                f"<b>Auto Unwrap</b><br><br>"
                f"✗ Failed: {len(failed)} of {len(selection)} mesh(es)<br><br>"
                f"{failed_list}"
            )

        if len(selection) == 1:
            return result

    def tb004_init(self, widget):
        """Initialize Unfold UV"""
        widget.option_box.menu.setTitle("Unfold UV")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Optimize",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Orient selected UV shells to run parallel with the most adjacent U or V axis.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Stack Similar",
            setObjectName="chk022",
            setChecked=True,
            setToolTip="Stack only shells that fall within the set tolerance.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip="Stack shells with uv's within the given range.",
        )
        cmb013 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb013",
            setToolTip=(
                "What to do when non-manifold geometry blocks Unfold:\n"
                "Warn + Select: stop, select the offending vertices, and explain.\n"
                "Repair + Retry: auto-clean the non-manifold geometry (Mesh Cleanup;\n"
                "non-manifold UVs are re-mapped) first, then unfold. The repair is\n"
                "noted in the result and the console."
            ),
        )
        for text, data in [
            ("Non-Manifold: Warn + Select", "select"),
            ("Non-Manifold: Repair + Retry", "repair"),
        ]:
            cmb013.addItem(text, data)
        cmb013.setCurrentIndex(0)  # Warn + Select (matches the prior default)

    def tb004(self, widget):
        """Unfold: relax/unfold the selected UVs to reduce stretch and distortion."""
        optimize = widget.option_box.menu.chk017.isChecked()
        orient = widget.option_box.menu.chk007.isChecked()
        stackSimilar = widget.option_box.menu.chk022.isChecked()
        nonmanifold_mode = widget.option_box.menu.cmb013.currentData()
        tolerance = widget.option_box.menu.s000.value()
        map_size = self.get_map_size()

        # Capture the operands before any mode switch, so the repair / warn paths
        # can locate non-manifold geometry on them.
        objects = cmds.ls(sl=True, objectsOnly=True) or []

        # u3dUnfold flattens the whole object; make sure we're in object mode so a
        # leftover component selection (common mid-UV-edit) can't scope it to a
        # partial sub-shell. Switching modes keeps the parent objects selected.
        if not cmds.selectMode(query=True, object=True):
            cmds.selectMode(object=True)

        # Unfold only relaxes the existing UVs — it never cuts new seams. A mesh
        # with no seams to open simply stays as-is; seaming a cylinder/tube is the
        # job of the dedicated Cut Cylinder tool (tb009), kept separate on purpose.
        unfold_kwargs = dict(
            iterations=1,
            pack=0,
            borderintersection=1,
            triangleflip=1,
            mapsize=map_size,
            roomspace=0,
        )

        # Let u3dUnfold itself decide whether the mesh is unfoldable — its
        # non-manifold rejection is narrower than polyInfo's topological flag, so
        # we must NOT pre-empt the unfold on a polyInfo scan (that aborted clean,
        # unfoldable meshes). Only on an actual non-manifold RuntimeError do we
        # act on the chosen strategy: warn + select, or repair (Mesh Cleanup) and
        # retry once. The object-mode switch above is what lets the single repair
        # retry land in one click.
        repair_summary = None
        try:
            cmds.u3dUnfold(**unfold_kwargs)
        except RuntimeError as error:
            if "non-manifold" not in str(error).lower():
                self.sb.message_box(
                    f"<b>Unfold failed:</b> {self._classify_u3d_error(error)}."
                )
                return
            if nonmanifold_mode != "repair":
                self._warn_and_select_non_manifold(objects)
                return
            repair_summary = self._repair_non_manifold(objects)
            try:
                cmds.u3dUnfold(**unfold_kwargs)
            except RuntimeError:
                # Repair couldn't make it unfoldable — fall back to warn + select.
                self._warn_and_select_non_manifold(objects)
                return

        if optimize:
            cmds.u3dOptimize(
                iterations=10,
                power=1,
                surfangle=1,
                borderintersection=0,
                triangleflip=1,
                mapsize=map_size,
                roomspace=0,
            )

        if orient:
            mel.eval("texOrientShells")

        if stackSimilar:
            cmds.polyUVStackSimilarShells(tolerance=tolerance)

        if repair_summary:
            fixed = repair_summary["fixed"]
            detail = (
                f" — <b>{fixed}</b> {'component' if fixed == 1 else 'components'} fixed"
                if fixed
                else ""
            )
            self.sb.message_box(
                "<b>Unfold complete.</b><br><br>"
                f"⚠ Non-manifold geometry was auto-repaired first{detail}.<br>"
                "<i>See the Script Editor for the per-mesh breakdown.</i>"
            )

    def tb007_init(self, widget):
        """Initialize Cleanup UV Sets"""
        widget.option_box.menu.setTitle("Cleanup UV Sets")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Prefer Best Layout",
            setObjectName="chk029",
            setChecked=True,
            setToolTip="<b>Best Information Strategy</b><br>If checked: Analyzes all valid UV sets and picks the one with the best layout density (Fill Rate).<br>Ignores global scaling, prioritizing actual texture usage and validity.<br>If unchecked: Uses the currently active UV set.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Remove Empty Sets",
            setObjectName="chk035",
            setChecked=True,
            setToolTip="<b>Safe Cleanup</b><br>Deletes any UV sets that have no UV coordinates.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Secondary Sets",
            setObjectName="chk036",
            setChecked=False,
            setToolTip="<b>Aggressive Cleanup</b><br>If checked: Deletes ALL other UV sets, leaving only the primary one.<br>If unchecked: Only deletes empty sets (if enabled). Secondary sets with data are preserved.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Rename to 'map1'",
            setObjectName="chk037",
            setChecked=True,
            setToolTip="<b>Standardization</b><br>Renames the primary UV set to the default 'map1'.<br>This also moves it to the first index (canonical position).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Force Rename",
            setObjectName="chk038",
            setChecked=False,
            setToolTip="<b>Destructive Rename</b><br>If 'map1' already exists but isn't the primary set:<br>Checked: Overwrite/merge 'map1' with the primary set.<br>Unchecked: Skip renaming if 'map1' exists and has content.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Dry Run",
            setObjectName="chk030",
            setChecked=False,
            setToolTip="Preview changes in the Script Editor without modifying anything.",
        )

    def tb007(self, widget):
        """Cleanup UV Sets"""
        prefer_largest_area = widget.option_box.menu.chk029.isChecked()
        remove_empty = widget.option_box.menu.chk035.isChecked()
        keep_only_primary = widget.option_box.menu.chk036.isChecked()
        rename_to_map1 = widget.option_box.menu.chk037.isChecked()
        force_rename = widget.option_box.menu.chk038.isChecked()
        dry_run = widget.option_box.menu.chk030.isChecked()

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least one selected object."
            )
            return

        results = mtk.Diagnostics.cleanup_uv_sets(
            selection,
            remove_empty=remove_empty,
            keep_only_primary=keep_only_primary,
            rename_to_map1=rename_to_map1,
            force_rename=force_rename,
            prefer_largest_area=prefer_largest_area,
            dry_run=dry_run,
        )

        # Generate summary report
        if not results:
            return

        report_lines = []
        for r in results:
            if r.error:
                report_lines.append(f"❌ <b>{r.shape}</b>: {r.error}")
                continue

            # Format specific details
            details = []
            if r.initial_sets:
                deleted_count = len(r.sets_to_delete)
                kept = r.primary_set

                if dry_run:
                    action = "Would keep"
                    del_action = "would delete"
                else:
                    action = "Kept"
                    del_action = "deleted"

                details.append(f"{action} '<b>{kept}</b>'")
                if r.final_name != kept and (rename_to_map1 or force_rename):
                    details.append(f" → renamed to '<b>{r.final_name}</b>'")

                if deleted_count > 0:
                    details.append(f", {del_action} {deleted_count} others")

            report_lines.append(f"• <b>{r.shape}</b>: {''.join(details)}")

        header = "<b>Dry Run Report</b>" if dry_run else "<b>Cleanup Complete</b>"
        self.sb.message_box(f"{header}<br><br>" + "<br>".join(report_lines))

    def tb009_init(self, widget):
        """Initialize Cut Cylinder.

        Cuts the hard creases (cap rims + step rings) plus one lengthwise seam
        on cylinder / tube / turned meshes, then optionally unfolds so each
        smooth section lays out as a clean strip and each flat step / cap as its
        own shell. The seam strategy is detected per mesh — a straight revolved
        axis for upright cylinders and turned columns, surface topology for
        bent / swept tubes and toruses — so there's nothing to choose.
        *Crease Angle* sets how sharp a bend must be to start a new shell;
        *Invert Seam* moves the lengthwise seam to the opposite side; *Unfold*
        flattens the cut sections (off = cut seams only).
        """
        menu = widget.option_box.menu
        menu.setTitle("Cut Cylinder")
        menu.add(
            "QSpinBox",
            setPrefix="Crease Angle: ",
            setObjectName="s016",
            set_limits=[1, 179],
            setValue=45,
            setSuffix="°",
            setToolTip="Crease threshold in degrees. An edge whose two faces "
            "meet at this angle or sharper starts a new shell, so a smaller "
            "value splits at gentler bevels and a larger value keeps only the "
            "hardest (~90°) steps. Default 45.",
        )
        menu.add(
            "QCheckBox",
            setText="Invert Seam",
            setObjectName="chk040",
            setChecked=False,
            setToolTip="Place the lengthwise seam on the opposite side of the "
            "cylinder, so it lands on the back / hidden side.",
        )
        menu.add(
            "QCheckBox",
            setText="Unfold",
            setObjectName="chk041",
            setChecked=True,
            setToolTip="Unfold (flatten) the UVs after seaming so the body lays "
            "out as a rectangular strip. Uncheck to cut the seams only.",
        )
        menu.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk042",
            setChecked=True,
            setToolTip="Orient each shell to its nearest U/V axis after the unfold.",
        )

    @mtk.undoable
    def tb009(self, widget):
        """Cut Cylinder"""
        angle = widget.option_box.menu.s016.value()
        invert_seam = widget.option_box.menu.chk040.isChecked()
        unfold = widget.option_box.menu.chk041.isChecked()
        orient = widget.option_box.menu.chk042.isChecked()

        selection = cmds.ls(sl=True, objectsOnly=True) or []
        if not selection:
            self.sb.message_box(
                "<b>Nothing selected.</b><br>The operation requires at least one "
                "cylinder / tube mesh."
            )
            return

        seamed = mtk.UvUtils.unwrap_cylinder(
            selection,
            angle=angle,
            invert_seam=invert_seam,
            unfold=unfold,
            orient=orient,
            map_size=self.get_map_size(),
        )
        if not seamed:
            self.sb.message_box(
                "<b>No cylinder seams found.</b><br>Select polygon cylinder / "
                "tube / turned mesh(es)."
            )

    def cmb003(self, index, widget):
        """UV Map Size — passive input; read by get_map_size for the texel-density
        and layout tools. Nothing to do on change."""

    def s003(self, value, widget):
        """Texel Density — passive input; read by Get/Set Texel Density (b003/b004).
        Nothing to do on change."""

    def b000_init(self, widget):
        """Initialize Transfer UVs option box — scope + similarity tolerance."""
        widget.option_box.menu.setTitle("Transfer UVs")
        cmb014 = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb014",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                body="Where the transfer targets come from. The "
                "<b>first-selected</b> object is always the source.",
                bullets=[
                    "<b>Selection Order</b> — transfer to each additionally "
                    "selected object, in selection order.",
                    "<b>Similar in Selection</b> — transfer to the selected "
                    "objects that are geometrically similar to the source.",
                    "<b>Similar in Scene</b> — transfer to every geometrically "
                    "similar mesh in the scene.",
                ],
                notes=[
                    "The Similar scopes skip true instances of the source: "
                    "instances share one shape, so their UVs already match.",
                ],
            ),
        )
        for text, data in [
            ("Scope: Selection Order", "order"),
            ("Scope: Similar in Selection", "selection"),
            ("Scope: Similar in Scene", "scene"),
        ]:
            cmb014.addItem(text, data)
        widget.option_box.menu.add(
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

    @mtk.undoable
    def b000(self, widget):
        """Transfer UV's"""
        scope = widget.option_box.menu.cmb014.currentData() or "order"
        tolerance = widget.option_box.menu.d000.value()
        ordered = cmds.ls(orderedSelection=1, flatten=1) or []

        if scope == "order":
            if len(ordered) < 2:
                return self.sb.message_box(
                    "<b>Nothing selected.</b><br>The operation requires the selection of at least two polygon objects."
                )
            frm, *to = ordered
            for t in to:
                mtk.transfer_uvs(frm, t)
            return

        # Similar scopes: first-selected is the source; targets are found by
        # geometric similarity within the chosen pool.
        if not ordered:
            return self.sb.message_box(
                "<b>Nothing selected.</b><br>Select the source object first"
                + (", then the candidate objects." if scope == "selection" else ".")
            )
        if scope == "selection" and len(ordered) < 2:
            return self.sb.message_box(
                "<b>Insufficient selection.</b><br>Select the source object, then the candidate objects."
            )
        candidates = ordered[1:] if scope == "selection" else None
        try:
            targets = mtk.transfer_uvs_to_similar(
                ordered[0], candidates, tolerance=tolerance
            )
        except ValueError as e:
            return self.sb.message_box(f"<b>Transfer UVs:</b><br>{e}")

        if targets:
            self.sb.message_box(
                f"Transferred UVs to <b>{len(targets)}</b> similar object(s)."
            )
        else:
            self.sb.message_box(
                "<b>No similar objects found.</b><br>Lower the similarity "
                "threshold, or note that true instances already share the "
                "source's UVs."
            )

    def b003(self):
        """Get texel density."""
        density = mtk.get_texel_density(cmds.ls(sl=True) or [], self.get_map_size())
        self.ui.s003.setValue(density)

    @mtk.undoable
    def b004(self):
        """Set Texel Density"""
        density = self.ui.s003.value()
        map_size = self.get_map_size()

        mtk.set_texel_density(cmds.ls(sl=True) or [], density, map_size)

    @mtk.undoable
    def b005(self):
        """Cut UVs: split the UV shell along the selected edges."""
        selection = cmds.ls(sl=True) or []
        selected_edges = cmds.filterExpand(selection, selectionMask=32)

        if not selection:
            self.sb.message_box("Nothing selected")
            return

        if selected_edges:
            # cut_uv_edges groups per object (polyMapCut refuses multi-object lists).
            mtk.UvUtils.cut_uv_edges(selected_edges)
            # Re-select the edges after the operation
            cmds.select(selected_edges)
        else:
            # No edges selected — cut along all edges of each selected mesh.
            # Resolve shapes with a type filter and full paths (same rationale
            # as b011): a short shape name is ambiguous when two transforms
            # share a leaf name, and objectType then raises.
            transforms = cmds.ls(selection, type="transform") or []
            shapes = (
                cmds.listRelatives(
                    transforms,
                    shapes=True,
                    noIntermediate=True,
                    type="mesh",
                    fullPath=True,
                )
                or []
            )
            for shape in shapes:
                cmds.polyMapCut(f"{shape}.e[*]")

    @mtk.undoable
    def b011(self):
        """Sew UVs: stitch the selected UV edges back together."""
        selected = cmds.ls(sl=True, flatten=True) or []

        # Edges (component selection) — sew directly
        edges = cmds.filterExpand(selected, selectionMask=32) or []
        for edge in edges:
            cmds.polyMapSew(edge)

        # Transforms — sew all edges of each mesh shape. Resolve shapes with a
        # type filter and full paths, not a per-shape objectType call: a short
        # shape name is ambiguous when two transforms share a leaf name under
        # different parents, and objectType then raises "No object matches name".
        transforms = cmds.ls(selected, type="transform") or []
        shapes = (
            cmds.listRelatives(
                transforms, shapes=True, noIntermediate=True, type="mesh", fullPath=True
            )
            or []
        )
        for shape in shapes:
            cmds.polyMapSew(f"{shape}.e[*]")

    def b021(self, widget):
        """Unfold and Pack UVs"""
        self.ui.tb004.call_slot()  # perform unfold
        self.ui.tb000.call_slot()  # perform pack

    def tb022_init(self, widget):
        """Initialize Cut Hard Edges option menu."""
        widget.option_box.menu.setTitle("Cut Hard Edges")
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s017",  # NOT s014 — collides with tb000's "Mutations"
            set_limits=[0, 180],
            setValue=70,
            setToolTip="Normal angle low range for hard-edge detection.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s018",
            set_limits=[0, 180],
            setValue=180,
            setToolTip="Normal angle high range for hard-edge detection.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include UV Borders",
            setObjectName="chk025",
            setChecked=False,
            setToolTip="Also cut along edges that are existing UV shell borders.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include Auto Seams",
            setObjectName="chk026",
            setChecked=False,
            setToolTip="Also cut along seams auto-detected by u3dAutoSeam.",
        )

    @mtk.undoable
    def tb022(self, widget):
        """Cut UV hard edges (always), optionally also UV borders and auto-detected seams."""
        angle_low = widget.option_box.menu.s017.value()
        angle_high = widget.option_box.menu.s018.value()
        include_uv_borders = widget.option_box.menu.chk025.isChecked()
        include_auto_seams = widget.option_box.menu.chk026.isChecked()

        objects = cmds.ls(sl=True, objectsOnly=True) or []
        if not objects:
            self.sb.message_box("Nothing selected")
            return

        # Hard edges (always on) — cut along edges within the angle range.
        # cut_uv_edges groups per object: polyMapCut refuses a component list
        # spanning multiple objects.
        hard_edges = mtk.Components.get_edges_by_normal_angle(
            objects, low_angle=angle_low, high_angle=angle_high
        )
        if hard_edges:
            mtk.UvUtils.cut_uv_edges(hard_edges)

        # Optional: cut along existing UV shell border edges.
        if include_uv_borders:
            border_edges = mtk.UvUtils.get_uv_shell_border_edges(objects)
            if border_edges:
                mtk.UvUtils.cut_uv_edges(border_edges)

        # Optional: auto-detected seams via Unfold3D.
        if include_auto_seams:
            for obj in objects:
                try:
                    cmds.u3dAutoSeam(obj, s=0, p=1)
                except Exception as error:
                    print(error)

    def b029_init(self, widget):
        """Initialize Pin/Unpin button — non-checkable text button.

        Defensively clears any `checkable` property a Qt Designer round-trip
        may have re-added (the button's "Pin" label lives in the .ui).
        """
        widget.setCheckable(False)

    @mtk.undoable
    def b029(self, widget):
        """Pin / Unpin selected UVs (dual-state toggle).

        First click on a fresh selection pins; the next click unpins; and so
        on. A selection change since the last click resets the toggle, so the
        next click always starts with Pin.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box("<b>Nothing selected.</b>")
            return
        uvs = cmds.polyListComponentConversion(selection, toUV=True) or []
        if not uvs:
            self.sb.message_box("<b>No UVs found in selection.</b>")
            return

        if self._b029_last_selection != selection:
            self._b029_pinned = False  # fresh selection — start with Pin
        self._b029_pinned = not self._b029_pinned
        cmds.polyPinUV(uvs, value=1.0 if self._b029_pinned else 0.0)
        self._b029_last_selection = list(selection)

    def b030_init(self, widget):
        """Initialize Stack button — non-checkable text button.

        Defensively clears any `checkable` property a Qt Designer round-trip
        may have re-added (the button's "Stack" label lives in the .ui).
        """
        widget.setCheckable(False)

    @mtk.undoable
    def b030(self, widget):
        """Stack / Unstack similar shells (dual-state toggle).

        First click on a fresh selection captures each selected UV's position
        and stacks similar shells (texStackShells). The next click restores
        those positions, returning shells to exactly where they were before
        the stack. A selection change since the last click resets the toggle
        and drops the snapshot.

        Per-UV capture and restore avoid an ordering ambiguity in bulk
        ``polyEditUV(..., query=True)``.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box("<b>Nothing selected.</b>")
            return
        uvs = cmds.polyListComponentConversion(selection, toUV=True) or []
        uvs = cmds.ls(uvs, flatten=True) or []
        if not uvs:
            self.sb.message_box("<b>No UVs found in selection.</b>")
            return

        if self._b030_last_selection != selection:
            # Fresh selection — reset to "next click stacks" and drop any
            # snapshot from a previous selection.
            self._b030_stacked = False
            self._b030_uv_snapshot = None

        self._b030_stacked = not self._b030_stacked
        self._b030_last_selection = list(selection)

        if self._b030_stacked:
            snapshot = []
            for uv in uvs:
                pos = cmds.polyEditUV(uv, query=True)
                if pos and len(pos) >= 2:
                    snapshot.append((uv, pos[0], pos[1]))
            self._b030_uv_snapshot = snapshot
            mel.eval("texStackShells {}")
            return

        snapshot = self._b030_uv_snapshot or []
        self._b030_uv_snapshot = None
        if not snapshot:
            self.sb.message_box(
                "<b>No snapshot available.</b><br>"
                "Stack a selection first; Unstack restores the pre-stack positions."
            )
            return
        cmds.refresh(suspend=True)
        try:
            for uv, u, v in snapshot:
                if cmds.objExists(uv):
                    cmds.polyEditUV(uv, uValue=u, vValue=v, relative=False)
        finally:
            cmds.refresh(suspend=False)

    def b031(self):
        """Open UV Editor"""
        mel.eval("TextureViewWindow")

    def b032(self):
        """RizomUV Bridge"""
        self.sb.handlers.marking_menu.show("rizom_bridge")

    def b033(self):
        """Open the Shell Xform panel (move / flip / rotate / align / orient / distribute).

        The ``More..`` button in the Transform group. The dedicated tool is
        co-located with its engine in ``mayatk.uv_utils.shell_xform``
        (``ShellXformSlots``) and auto-discovered by ``MayaUiHandler``; Pin
        (b029) and Stack (b030) sit beside it in the same group.
        """
        self.sb.handlers.marking_menu.show("shell_xform")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
