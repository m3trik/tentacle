# !/usr/bin/python
# coding=utf-8

import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk

# From this package:
from tentacle import UvMixin, SlotsMaya


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
        self._b030_pin_weights = None

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
        # RizomUV is an optional third-party app. Present the entry per the user's
        # ``unmet_policy`` (Preferences > Unavailable tools) when it isn't installed,
        # rather than offering a button whose only outcome is a "not found" error.
        # The lambda defers the engine import into gate_on_app (see its docstring);
        # ``APP.available`` is cached, so this costs one dict lookup after the
        # first probe.
        self.gate_on_app(widget.menu.btn_rizom_bridge, lambda: mtk.RizomUVBridge.APP)

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
                    (
                        "Cost",
                        "2–15× slower (0.8s → 11s on 4 organic meshes at 1024); "
                        "grows steeply with shell count",
                    ),
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

    def _warn_non_manifold(self, objects):
        """Select what blocks Unfold on *objects* and explain it.

        Backs the 'Warn + Select' strategy and the fallback when a repair can't
        make the mesh unfoldable. ``mtk.Diagnostics.select_non_manifold`` picks
        the non-manifold vertices, else the non-manifold UVs (Unfold rejects
        those with the same error as bad geometry).
        """
        kind, comps = mtk.Diagnostics.select_non_manifold(objects)
        n = len(comps)
        if kind != "uvs":
            kind = "geometry"
            selected = (
                f"<b>{n}</b> problem {'vertex' if n == 1 else 'vertices'} "
                "selected in vertex mode.<br><br>"
                if n
                else ""
            )
            cause = (
                "Unfold can't flatten a mesh with <b>non-manifold vertices</b> — "
                "points where the surface branches or folds back on itself.<br><br>"
            )
            manual = "• run <b>Mesh &gt; Cleanup</b> / <b>Merge</b> doubled verts manually.<br><br>"
        else:
            kind = "UVs"
            selected = f"<b>{n}</b> problem {'UV' if n == 1 else 'UVs'} selected in UV mode.<br><br>"
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

    def tb000(self, widget):
        """Pack UVs with specified settings.

        Reads the option box and hands the selection to ``mtk.UvUtils.pack_uvs``
        -- engine ``"u3d"`` (Maya's u3dLayout) for Standard, ``"xatlas"`` for
        xatlas -- which owns the padding, tile box, grid and per-mesh failure
        isolation; this slot keeps the undo chunk, the progress marquee and the
        summary (texel density, map size, target UDIMs, skipped meshes).

        Scope — objects or components: both methods pack exactly what is
        selected. Select whole objects to pack their full maps, or select faces
        / UVs / UV shells to pack only that region and leave the rest of the map
        where it is (a component selection is widened to whole faces, since a
        packer's unit of input is a face).

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
                The engine deals shells to the tiles (area-balanced) and packs
                per tile (-tileAssignMode 1); u3dLayout's own Distribute mode
                stacks shells.
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
        UDIM = menu.s004.value()
        tiles_u = menu.s019.value()
        tiles_v = menu.s020.value()
        map_size = self.get_map_size()
        # The tile grid is u3dLayout-only (gated in the UI; force here too so
        # a persisted spinbox value can't leak into the engine path).
        if method != "standard":
            tiles_u = tiles_v = 1

        selection = self.require_selection()
        if selection is None:
            return

        # Instances share one shape + UV set, so packing every instance is
        # redundant and forces the packer to reserve tile space for each
        # identical copy. Keep one transform per instance group (object-level
        # selection only — component selections are packed exactly as given).
        if menu.chk016.isChecked() and not any("." in str(s) for s in selection):
            selection = mtk.NodeUtils.filter_duplicate_instances(selection)

        # The pack is one bulk engine call with nothing to tick from the
        # inside, so the marquee is painted BEFORE the blocking region and torn
        # down after it. Nothing ticks while the refresh is suspended and the
        # undo chunk is open: a tick pumps the event loop, and letting the user
        # reach another slot mid-chunk is how a half-open chunk gets made.
        # mtk.UvUtils.pack_uvs owns both engines (scope resolution, gutters,
        # tile grid, per-mesh failure isolation); an optional engine that is
        # not installed raises before the scene is touched, with its pip
        # command in the message, same pattern as Auto Unwrap's engines.
        error = None
        with self.sb.progress(text=f"Working: Pack UVs ({method})") as update:
            update()
            cmds.undoInfo(openChunk=True, chunkName="UV Pack")
            cmds.refresh(suspend=True)
            try:
                result = mtk.UvUtils.pack_uvs(
                    selection,
                    engine="xatlas" if method == "xatlas" else "u3d",
                    map_size=map_size,
                    udim=UDIM,
                    coverage=menu.cmb015.currentData(),
                    preserve_3d=menu.cmb009.currentData() == 1,  # Preserve 3D
                    rotate=menu.chk044.isChecked(),
                    brute_force=menu.chk043.isChecked(),
                    pre_rotate=menu.cmb010.currentData(),
                    rotate_step=menu.s011.value(),
                    rotate_min=menu.s012.value(),
                    rotate_max=menu.s013.value(),
                    mutations=menu.s014.value(),
                    scale_mode=menu.cmb018.currentData(),
                    tiles=(tiles_u, tiles_v),
                )
            except (RuntimeError, ValueError) as engine_error:
                error = engine_error
            finally:
                cmds.refresh(suspend=False)
                cmds.undoInfo(closeChunk=True)
        if error is not None:
            self.sb.message_box(
                f"<b>xatlas pack unavailable.</b><br><br>{error}"
                if method == "xatlas"
                else f"<b>{error}</b>"
            )
            return
        successful = list(result.succeeded)
        failed = list(result.failed)
        # The grid that actually ran: Tiles U is clamped so it stays inside
        # the UDIM row, and the summary says so.
        tiles_u_requested = tiles_u
        tiles_u, tiles_v = result.tiles
        grid = tiles_u > 1 or tiles_v > 1
        # What the resulting texel density is measured over: the components
        # the engine actually packed, so a faces/shell selection is not read
        # back as a whole-mesh density the run never produced.
        density_scope = list(result.targets)

        # Resulting texel density across the packed meshes — a single
        # representative value (with Preserve-3D pre-scale every shell shares
        # it; with Preserve-UV it's the aggregate of the kept relative scales).
        # Never let a texel-calc hiccup swallow the pack result, so guard it.
        density = 0.0
        if successful:
            try:
                density = mtk.get_texel_density(density_scope or successful, map_size)
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

        # Report summary. Distinct objects, not entries: a component pick
        # arrives as several face ranges per object.
        packed = len({str(m).split(".", 1)[0] for m in successful})
        if failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in failed
            )
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Packed: {packed} mesh(es)<br>"
                f"✗ Skipped: {len(failed)} mesh(es)<br><br>"
                f"{stats}<br><br>"
                f"<b>Skipped meshes:</b><br>{failed_list}<br><br>"
                f"<i>Tip: Use Mesh > Cleanup to fix non-manifold geometry.</i>"
            )
        elif successful:
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Successfully packed {packed} mesh(es).<br><br>"
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
        map_size = self.get_map_size()

        selection = self.require_selection()
        if selection is None:
            return

        if mode in self.AUTO_UNWRAP_ENGINE_MODES:
            # The engine handles its own per-object loop and error reporting.
            with self.sb.progress(text=f"Working: Auto Unwrap ({mode})") as update:
                update()
                return self._run_auto_unwrap(mtk, selection, mode, map_size)

        scale_mode = menu.cmb012.currentData()
        # Island gutter from the panel's map size, via the one ecosystem rule
        # (mtk.calculate_uv_padding) that also feeds the Pack tool's
        # shellSpacing and the RizomUV bridge — so a map auto-projected here
        # keeps its gutter when repacked. percentageSpace wants a percentage of
        # the texture area, hence the x100 (the normalized padding is
        # map-size-invariant by design: 1/256 -> 0.39%).
        percentage_space = mtk.calculate_uv_padding(map_size, normalize=True) * 100.0
        result = None
        failed = []
        progress = self.sb.progress(total=len(selection), text="Working: Auto Unwrap")
        with progress as update:
            for index, obj in enumerate(selection):
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
                        percentageSpace=percentage_space,  # gutter added around each UV piece, as a percentage of the texture area
                        worldSpace=0,
                    )  # 1=world reference. 0=object reference.
                except Exception as error:
                    failed.append((obj, str(error)))
                if not update(index + 1):
                    break  # Esc-hold: keep the projections already made

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
        # can locate non-manifold geometry on them. Guard first: u3dUnfold only
        # logs an error on an empty selection, but the orient pass below is MEL
        # (texOrientShells -> texCheckSelection) and raises outright.
        objects = self.require_selection(objectsOnly=True)
        if objects is None:
            return

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
                    f"<b>Unfold failed:</b> {mtk.UvUtils.classify_unfold3d_error(error)}."
                )
                return
            if nonmanifold_mode != "repair":
                self._warn_non_manifold(objects)
                return
            repair_summary = mtk.Diagnostics.repair_non_manifold(objects)
            try:
                cmds.u3dUnfold(**unfold_kwargs)
            except RuntimeError:
                # Repair couldn't make it unfoldable — fall back to warn + select.
                self._warn_non_manifold(objects)
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

        selection = self.require_selection()
        if selection is None:
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

        Seams cylinder / tube / turned meshes the way a texture artist does by
        hand — clean and minimal: every cylindrical wall, chamfer and flare
        becomes a strip with ONE lengthwise seam (all strips along the same
        edge loop, so the seams line up), washers / steps and caps stay closed
        rings and discs, and a ring is cut wherever a strip meets one of them
        or the profile kinks. Bent hoses and toruses are read locally, so
        there's nothing to choose. Then optionally unfolds so each strip lays
        out flat (a rectangle, a sector) and each ring / disc as its own shell.
        The knobs are the artist's preferences, not the algorithm's: *Taper
        Angle* is how far a band may tilt and still ride the cylinder's strip
        (and how much the profile may turn before a new piece starts); *Flat
        Angle* is the rings-vs-sectors call -- bands flatter than it stay
        closed rings, steeper bevels are cut open; *Fillet Size* is how small
        a bevel must be to ride its wall's strip instead of becoming a shell;
        *Crease Angle* only decides creases in geometry the tube reading
        doesn't cover; *Hide Seam From View* lands the lengthwise seam on the
        side facing away from the active viewport camera; *Invert Seam* flips
        it to the near side; *Keep Existing Seams* leaves hand-cut UV borders
        in place instead of sewing them shut first; *Unfold* flattens the cut
        sections (off = cut seams only).
        """
        menu = widget.option_box.menu
        menu.setTitle("Cut Cylinder")
        menu.add(
            "QSpinBox",
            setPrefix="Taper Angle: ",
            setObjectName="s021",
            set_limits=[1, 60],
            setValue=20,
            setSuffix="°",
            setToolTip="How far a band may tilt from the tube axis and still "
            "ride the cylinder's strip, and how much the profile may turn "
            "before a new piece starts. Raise it to let gentle chamfers and "
            "tapers stay part of the wall; lower it to split them off. Default 20.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Flat Angle: ",
            setObjectName="s022",
            set_limits=[20, 85],
            setValue=60,
            setSuffix="°",
            setToolTip="Rings vs. sectors. Bands tilted from the axis past this "
            "(steps, shallow bevels) stay closed rings; steeper ones (chamfers, "
            "flares, funnels) are cut open on the seam as exact sectors. Lower "
            "it to keep more bevels as rings (45 keeps a 45° chamfer closed at a "
            "41% stretch); raise it to cut more of them open. Default 60.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Fillet Size: ",
            setObjectName="s023",
            set_limits=[0, 50],
            setValue=12,
            setSuffix=" %",
            setToolTip="Bands shorter than this percentage of the tube radius "
            "are fillets / bevels / beads: they ride the strip of the wall they "
            "round off instead of becoming shells of their own. 0 = every band "
            "counts on its own. Default 12.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Crease Angle: ",
            setObjectName="s016",
            set_limits=[1, 179],
            setValue=45,
            setSuffix="°",
            setToolTip="Crease threshold in degrees for geometry that isn't a "
            "clean tube (edges sharper than this become seams there). The tube "
            "itself is read from its profile (see Taper / Flat Angle); set this "
            "below the Taper Angle to split gentler kinks too. Default 45.",
        )
        menu.add(
            "QCheckBox",
            setText="Hide Seam From View",
            setObjectName="chk045",
            setChecked=True,
            setToolTip="Place the lengthwise seam on the side facing away from "
            "the active viewport's camera, so it lands on the back. Off: a "
            "fixed side, away from Maya's default front-right perspective.",
        )
        menu.add(
            "QCheckBox",
            setText="Invert Seam",
            setObjectName="chk040",
            setChecked=False,
            setToolTip="Flip the lengthwise seam to the opposite side (facing "
            "the viewer).",
        )
        menu.add(
            "QCheckBox",
            setText="Keep Existing Seams",
            setObjectName="chk046",
            setChecked=False,
            setToolTip="Leave the mesh's current UV borders (hand-cut seams) in "
            "place and add the tube seams to them. Off: sew everything shut "
            "first so the shells come only from this operation.",
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
        menu = widget.option_box.menu
        angle = menu.s016.value()
        taper_angle = menu.s021.value()
        flat_angle = menu.s022.value()
        trim_ratio = menu.s023.value() / 100.0
        hide_from_view = menu.chk045.isChecked()
        invert_seam = menu.chk040.isChecked()
        keep_seams = menu.chk046.isChecked()
        unfold = menu.chk041.isChecked()
        orient = menu.chk042.isChecked()

        selection = self.require_selection(
            "<b>Nothing selected.</b><br>The operation requires at least one "
            "cylinder / tube mesh.",
            objectsOnly=True,
        )
        if selection is None:
            return

        camera = None
        if hide_from_view:
            try:  # no active 3D view (batch / undocked UI): fixed default side
                camera = mtk.CamUtils.get_current_cam() or None
            except Exception:
                camera = None

        seamed = mtk.UvUtils.unwrap_cylinder(
            selection,
            angle=angle,
            invert_seam=invert_seam,
            unfold=unfold,
            orient=orient,
            map_size=self.get_map_size(),
            sew=not keep_seams,
            taper_angle=taper_angle,
            camera=camera,
            flat_angle=flat_angle,
            trim_ratio=trim_ratio,
        )
        if not seamed:
            self.sb.message_box(
                "<b>No cylinder seams found.</b><br>Select polygon cylinder / "
                "tube / turned mesh(es)."
            )

    # ------------------------------------------------------------------
    # b000  Transfer UVs / Textures -- the option box, its wiring and the
    # texture pass are UvMixin's (``b000_init``, ``_tt_texture_pass``); this
    # fork supplies its engine, its words and the Maya-only Shader row.
    # ------------------------------------------------------------------
    _TT_TERMS = {
        "set": "set",
        "current": "current",
        "first": "First Selected Mesh",
        "first_who": "the first-selected object",
        "order": ", in selection order",
        "instances": "true instances of the source (one shape, UVs already match)",
        "bound": "uvLink",
        "name_note": "the assigned material's own settings — a <b>Material "
        "Affix</b> (a naming convention the maps deliberately do not follow) and "
        "its <b>Shader</b> type.",
        "output_dir": "sourceimages/uv_transfer",
        "output_rel": "a subdirectory of sourceimages",
    }

    def _tt_engine(self):
        """Maya's ``TextureTransfer`` (see ``UvMixin._tt_engine``)."""
        return mtk.TextureTransfer

    def _tt_add_assign_rows(self, name_menu):
        """The assigned material's TYPE, beside its name (Maya-only).

        The material is a copy of the target's, so left alone it lands on
        whatever that mesh wore -- for unassigned geometry, Maya's own default
        shader. Items come from the converter's TARGETS (its SSoT), so a target
        added there appears here; "Same as target" leads and the rest follow in
        TARGETS order, because combo state persists by INDEX.
        """
        cmb_tt_shader = name_menu.add(
            "QComboBox",
            setObjectName="cmb_tt_shader",
            setToolTip=self.sb.tooltip.fmt(
                title="Shader",
                body="The shader type of the material the run assigns.",
                bullets=[
                    "<b>Same as target</b> — a copy of the target's own "
                    "material, so every channel the transfer does not write "
                    "keeps its look. Right for a re-bake in place.",
                    "<b>A named type</b> — the result is rebuilt on that "
                    "shader (maps, constants and assignments carry across). "
                    "For a deliverable, where the target may be wearing "
                    "nothing but Maya's default shader.",
                ],
                notes=[
                    "Retyping a whole scene's materials is the <b>Material "
                    "Updater</b>'s Shader Type option — same engine.",
                ],
            ),
        )
        # addItem, not ``add(prefix=...)``: that helper rewrites a None data
        # value to the item's label (and title-cases the text), so the default
        # row would reach the engine as the string "Same As Target".
        cmb_tt_shader.addItem("Shader: Same as target", None)
        for name, node_type in mtk.ShaderConverter.TARGETS.items():
            cmb_tt_shader.addItem(
                f"Shader: {mtk.ShaderConverter.TARGET_LABELS.get(name, node_type)}",
                name,
            )
        # Held directly, like the affix: a row of the NAME field's option-box
        # menu, so the tool's own menu carries no proxy for ``b000`` to read.
        self._tt_shader_type = cmb_tt_shader
        return (cmb_tt_shader,)

    def _tt_assign_shader_type(self):
        """The Shader row's target type, or None for "same as target".

        Read off the slot rather than a menu proxy for the same reason as the
        affix (:meth:`UvMixin._tt_material_affix`): it is a row of the Output
        Name field's option-box menu. Maya-only -- Blender materials are one
        node graph, so that fork has no such row.
        """
        combo = getattr(self, "_tt_shader_type", None)
        return combo.currentData() if combo is not None else None

    @staticmethod
    def _tt_meshes(objects):
        """Mesh transforms under *objects* (groups expand; order kept)."""
        out = []
        for o in objects:
            shapes = (
                cmds.listRelatives(
                    o, allDescendents=True, type="mesh", fullPath=True, ni=True
                )
                or []
            )
            for shape in shapes:
                xf = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
                if xf not in out:
                    out.append(xf)
        return out

    def _tt_source_tooltip(self):
        """Live tooltip for Set Source From Selection -- what is stored NOW.

        The stored set is otherwise invisible until a transfer runs and
        either uses the wrong meshes or reports none, so the hover is the
        only place it can be checked. Nodes deleted since the capture are
        called out rather than silently listed: ``b000`` drops them, and a
        count that no longer matches what was selected needs a reason.
        """
        stored = getattr(self, "_tt_sources", [])
        missing = [s for s in stored if not cmds.objExists(s)]
        return self.sb.tooltip.stored_items(
            stored,
            title="Set Source From Selection",
            body="Capture the current selection as the <b>Stored Source "
            "Meshes</b> (mesh transforms, or groups — their mesh children "
            "are used). Read by the <i>Stored Source Meshes</i> source.",
            formatter=lambda n: n.rsplit("|", 1)[-1],
            noun="stored source mesh(es)",
            empty_text="Nothing stored yet — the <i>Stored Source Meshes</i> "
            "source has nothing to read from.",
            notes=(
                [f"{len(missing)} no longer in the scene; they are skipped."]
                if missing
                else None
            ),
        )

    def _tt_set_source_from_selection(self):
        sel = cmds.ls(selection=True, long=True, type="transform") or []
        self._tt_sources = self._tt_meshes(sel)
        self._tt_sync_controls()
        self.sb.message_box(
            f"Stored <b>{len(self._tt_sources)}</b> source mesh(es) for Transfer."
            if self._tt_sources
            else "<b>Nothing selected.</b><br>Select the source meshes (or their group)."
        )

    def _tt_select_source(self):
        """Select the stored source meshes -- the capture, made visible.

        The same survivor filter ``b000`` applies, so what gets selected is
        exactly what a run would read: a node deleted since the capture is
        reported rather than silently dropped, because a count that no longer
        matches what was picked needs a reason.
        """
        stored = getattr(self, "_tt_sources", [])
        alive = [s for s in stored if cmds.objExists(s)]
        if not alive:
            return self.sb.message_box(
                "<b>Nothing stored.</b><br>Use <i>Set Source From Selection</i> "
                "to capture the source meshes first."
                if not stored
                else "<b>None of the stored source meshes are still in the "
                "scene.</b><br>Re-capture them."
            )
        cmds.select(alive, replace=True)
        missing = len(stored) - len(alive)
        self.sb.message_box(
            f"Selected <b>{len(alive)}</b> stored source mesh(es)."
            + (f"<br>{missing} no longer in the scene; skipped." if missing else "")
        )

    @mtk.undoable
    def b000(self, widget):
        """Transfer UVs OR textures -- one pass per run (see ``b000_init``)."""
        menu = widget.option_box.menu
        mode = menu.cmb024.currentData() or "first"
        scope = menu.cmb014.currentData() or "order"
        ordered = cmds.ls(orderedSelection=True, long=True, type="transform") or []
        if not ordered:
            ordered = cmds.ls(selection=True, long=True, type="transform") or []
        transfer_mode = menu.cmb028.currentData()
        auto = transfer_mode == self.TRANSFER_AUTO
        # Source candidates, resolved ONCE and reused by the mode branches
        # below: Auto's probe and the pass must read the SAME meshes, or the
        # probe could decide from meshes the run then doesn't use.
        first_source = self._tt_meshes(ordered[:1])
        stored_sources = [
            s for s in getattr(self, "_tt_sources", []) if cmds.objExists(s)
        ]
        if auto and mode != "uvset":
            # Resolved BEFORE the pass-dependent gates below (Output Name, the
            # Similar-scope check): what Auto decides is what they must ask
            # for. An empty probe resolves to the UV pass and falls through to
            # the same selection errors a manual mode would hit.
            transfer_mode = self._tt_resolve_auto(
                mtk.TextureTransfer,
                first_source if mode == "first" else stored_sources,
            )
        do_uvs, do_textures = self._tt_passes(mode, transfer_mode)
        auto_note = self._tt_auto_note(auto, do_textures, mode)
        if not (do_uvs or do_textures):
            return self.sb.message_box(
                "<b>Nothing to transfer.</b><br>The <i>UV Set On Same Mesh</i> "
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
        if mode == "uvset":
            targets = self._tt_meshes(ordered)
            if not targets:
                return self.sb.message_box(
                    "<b>Nothing selected.</b><br>Select the mesh(es) to transfer on."
                )
        elif mode == "first":
            if not ordered or (scope != "scene" and len(ordered) < 2):
                return self.sb.message_box(
                    "<b>Select the source mesh first, then the target mesh(es).</b>"
                )
            source = first_source
            if scope == "order":
                targets = self._tt_meshes(ordered[1:])
                pairs = [(source[0], t) for t in targets]
            else:
                if not do_uvs:
                    return self.sb.message_box(
                        "<b>The Similar scopes need a Transfer mode that "
                        "includes UV Set</b> -- the UV pass is what finds their "
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
            targets = [t for t in self._tt_meshes(ordered) if t not in source]
            if not targets:
                return self.sb.message_box(
                    "<b>Nothing selected.</b><br>Select the target mesh(es)."
                )
            try:
                pairs = [
                    (s, t)
                    for t, s in mtk.TextureTransfer.pair_by_name(
                        targets, source
                    ).items()
                ]
            except ValueError as e:
                return self.sb.message_box(f"<b>Transfer:</b><br>{e}")

        report = []
        # Both passes are bulk engine calls with nothing to tick from the
        # inside, so ONE task indicator spans them and re-labels itself between
        # the two: the footer names whichever pass is currently freezing the
        # UI, which a bare wait cursor cannot. The texture pass is minutes of
        # numpy on a 4k atlas -- that is the one worth naming.
        first_label = (
            "Working: Transfer UV Set" if do_uvs else "Working: Transfer Textures"
        )
        with self.sb.progress(text=first_label) as tick:
            tick()
            # ---- UV pass ---------------------------------------------------
            if do_uvs:
                try:
                    if pairs is None:
                        candidates = (
                            self._tt_meshes(ordered[1:])
                            if scope == "selection"
                            else None
                        )
                        targets = mtk.transfer_uvs_to_similar(
                            source[0],
                            candidates,
                            tolerance=menu.d000.value(),
                        )
                        if not targets:
                            return self.sb.message_box(
                                "<b>No similar objects found.</b><br>Lower the "
                                "similarity threshold, or note that true instances "
                                "already share the source's UVs."
                            )
                        results = [(source[0], t, "topology") for t in targets]
                    else:
                        # match_by_similarity=False: the pairing is already decided
                        # (selection order / stored-by-name); re-vetting it by
                        # geometric similarity could only silently drop a pair the
                        # user named deliberately.
                        results = mtk.transfer_uvs(
                            [s for s, _ in pairs],
                            [t for _, t in pairs],
                            match_by_similarity=False,
                        )
                except ValueError as e:
                    return self.sb.message_box(f"<b>Transfer UV Set:</b><br>{e}")
                approximated = [r for r in results if r[2] != "topology"]
                report.append(
                    f"Transferred UVs to <b>{len(results)}</b> object(s)"
                    + "."
                    + (
                        f"<br><b>{len(approximated)}</b> did not match the source's "
                        "topology and were sampled by proximity — check the result."
                        if approximated
                        else ""
                    )
                )

            # ---- texture pass ----------------------------------------------
            if do_textures:
                tick(text="Working: Transfer Textures")
                report.append(
                    self._tt_texture_pass(
                        targets,
                        source,
                        menu,
                        out_name,
                        assign_shader_type=self._tt_assign_shader_type(),
                    )
                )
        self.sb.message_box("<br><br>".join(report))

    def b003(self):
        """Get texel density."""
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the object(s) to measure."
        )
        if selection is None:
            return
        density = mtk.get_texel_density(selection, self.get_map_size())
        self.ui.s003.setValue(density)

    @mtk.undoable
    def b004(self):
        """Set Texel Density"""
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the object(s) to set the texel density on."
        )
        if selection is None:
            return

        mtk.set_texel_density(selection, self.ui.s003.value(), self.get_map_size())

    @mtk.undoable
    def b005(self):
        """Cut UVs: split the UV shell along the selected edges."""
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select UV edge(s) to cut along, or mesh "
            "object(s) to cut every edge of."
        )
        if selection is None:
            return
        selected_edges = cmds.filterExpand(selection, selectionMask=32)

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
        selected = self.require_selection(
            "<b>Nothing selected.</b><br>Select UV edge(s) to sew, or mesh "
            "object(s) to sew every edge of.",
            flatten=True,
        )
        if selected is None:
            return

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
        # Guard here as well as in each step, so an empty selection reports once
        # instead of twice (unfold's box, then pack's).
        if self.require_selection() is None:
            return
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

        objects = self.require_selection(
            "<b>Nothing selected.</b><br>Select the mesh object(s) to cut.",
            objectsOnly=True,
        )
        if objects is None:
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

    @mtk.undoable
    def b029(self, widget):
        """Pin / Unpin selected UVs (dual-state toggle).

        First click on a fresh selection pins; the next click unpins; and so
        on. A selection change since the last click resets the toggle, so the
        next click always starts with Pin.
        """
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the UVs to pin."
        )
        if selection is None:
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

    @mtk.undoable
    def b030(self, widget):
        """Stack / Unstack shells (dual-state toggle).

        First click on a fresh selection captures each selected UV's position
        (and pin weight) and stacks the shells per the option box
        (:meth:`UvMixin.b030_init`): ``Similar`` =
        ``mtk.UvUtils.stack_similar_uv_shells`` (``polyUVStackSimilarShells``)
        — shells of the same topology + shape land on the first matching
        shell, rotated (and scaled) to overlap exactly, unmatched shells stay
        put; ``All shells`` = ``texStackShells`` — every shell translated onto
        the shared center. ``Pin after stack`` pins the selected shells' UVs.
        The next click restores the captured positions and pin weights,
        returning shells to exactly where they were before the stack. A
        selection change since the last click resets the toggle and drops
        the snapshot.

        Per-UV capture and restore avoid an ordering ambiguity in bulk
        ``polyEditUV(..., query=True)``.
        """
        mode, tolerance, pin = self._stack_options(widget)
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the shell(s) to stack."
        )
        if selection is None:
            return
        uv_ranges = cmds.polyListComponentConversion(selection, toUV=True) or []
        uvs = cmds.ls(uv_ranges, flatten=True) or []
        if not uvs:
            self.sb.message_box("<b>No UVs found in selection.</b>")
            return

        if self._b030_last_selection != selection:
            # Fresh selection — reset to "next click stacks" and drop any
            # snapshot from a previous selection.
            self._b030_stacked = False
            self._b030_uv_snapshot = None
            self._b030_pin_weights = None

        self._b030_stacked = not self._b030_stacked
        self._b030_last_selection = list(selection)

        if self._b030_stacked:
            # Prior pin weights, always: the stack commands ignore pins but
            # polyEditUV honours them, so Unstack has to lift every pin before
            # it can move a UV back -- and then put exactly these weights back
            # (pins the user set via b029 survive the cycle).
            #
            # Keyed by UV, then aligned to the snapshot: a UV whose position
            # query comes back empty is dropped from `snapshot`, so a list
            # captured over the full `uvs` would be LONGER than the list
            # Unstack pairs it against -- shifting every subsequent weight onto
            # a different UV, silently.
            weight_by_uv = dict(zip(uvs, mtk.UvUtils.get_uv_pin_weights(uvs)))
            snapshot = []
            for uv in uvs:
                pos = cmds.polyEditUV(uv, query=True)
                if pos and len(pos) >= 2:
                    snapshot.append((uv, pos[0], pos[1]))
            weights = [weight_by_uv[uv] for uv, _, _ in snapshot]
            if mode == self.STACK_MODE_SIMILAR:
                if not mtk.UvUtils.stack_similar_uv_shells(selection, tolerance):
                    self._b030_stacked = False
                    self._report_no_similar_shells()
                    return
            else:
                # texStackShells stacks the shells of the SELECTED UVs / faces
                # (a plain object selection is "No UVs selected" unless Maya's
                # auto-convert preference is on) -- select the UVs, stack, and
                # put the selection back so the toggle's compare still holds.
                cmds.select(uv_ranges)
                try:
                    mel.eval("texStackShells {}")
                finally:
                    cmds.select(selection)
            self._b030_uv_snapshot = snapshot
            self._b030_pin_weights = weights
            if pin:
                cmds.polyPinUV(uvs, value=1.0)
            return

        snapshot = self._b030_uv_snapshot or []
        weights = self._b030_pin_weights or []
        self._b030_uv_snapshot = None
        self._b030_pin_weights = None
        if not snapshot:
            self.sb.message_box(
                "<b>No snapshot available.</b><br>"
                "Stack a selection first; Unstack restores the pre-stack positions."
            )
            return
        cmds.refresh(suspend=True)
        try:
            live = [uv for uv, _, _ in snapshot if cmds.objExists(uv)]
            if live:
                cmds.polyPinUV(live, value=0.0)  # pins block polyEditUV
            for uv, u, v in snapshot:
                if cmds.objExists(uv):
                    cmds.polyEditUV(uv, uValue=u, vValue=v, relative=False)
            mtk.UvUtils.set_uv_pin_weights([uv for uv, _, _ in snapshot], weights)
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
