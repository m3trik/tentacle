# !/usr/bin/python
# coding=utf-8
"""UV: one Slots class for both hosts.

Every operation is the host toolkit's ``UvUtils`` (``self.tk``; Cleanup UV Sets
is ``Diagnostics``), each one undo step in its host. Maya acts on the selection
as ``cmds.ls`` names it (components scope an operation); Blender on the
selected meshes, an Edit-Mode mesh's selected components scoping the shell
tools. An operation with nothing to act on returns ``[]`` and the slot says so;
a state the user can fix raises ``ValueError`` and a host refusal
``RuntimeError``, both shown as the host words them (:meth:`Slots.run_operation`).
An option only one host serves carries a ``requires`` tag (hidden on the other).
Texture Combine, Shell Xform and the RizomUV Bridge are tentacle's shared tools.
"""

from tentacle import Slots


class UvSlots(Slots):
    #: Auto Unwrap modes an external unwrapping engine runs (``UvUtils.auto_unwrap``
    #: in both hosts); ``"standard"`` is the host's own projection
    #: (``UvUtils.auto_project``).
    AUTO_UNWRAP_ENGINE_MODES = ("hard", "organic")

    #: Stack's modes (the option box's cmb020 data): ``similar`` stacks shells of
    #: the same topology and shape onto the first matching one, rotated (and
    #: scaled) to overlap exactly, leaving unmatched shells where they are;
    #: ``center`` ("All shells") translates every targeted shell onto one shared
    #: center regardless of shape -- the plain Stack.
    STACK_MODE_SIMILAR = "similar"
    STACK_MODE_CENTER = "center"

    #: Pack option-box controls, by the ``UvUtils.pack_uvs`` option each feeds:
    #: a control is enabled, and its value sent, only while the chosen packer
    #: honors that option (``UvUtils.PACK_ENGINES``, each host's own table).
    PACK_CONTROLS = {
        "chk044": "rotate",
        "chk043": "brute_force",
        "s_pack_margin": "margin",
        "cmb010": "pre_rotate",
        "s011": "rotate_step",
        "s012": "rotate_min",
        "s013": "rotate_max",
        "s014": "mutations",
        "cmb018": "scale_mode",
        "s019": "tiles",
        "s020": "tiles",
        "chk016": "skip_instances",
    }

    # Pin (b029) and Stack (b030) are dual-state toggles keyed on the UV scope
    # they last acted on (``UvUtils.uv_scope_key``): the next click on the same
    # scope undoes the last one, a new scope starts a fresh cycle. Compared on
    # each click rather than reset by a selection-changed callback: Maya fires
    # SelectionChanged from inside its own UV commands (texStackShells).
    _b029_pinned = False
    _b029_key = None
    _b030_snapshot = None
    _b030_key = None

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.uv
        self.submenu = self.sb.loaded_ui.uv_submenu

    def _host_only(self, host, *widgets):
        """Tag option-box controls only *host* serves; uitk hides them on the other."""
        for widget in widgets:
            widget.setProperty("requires", host)
            self.sb.apply_visibility_policy(widget)

    def get_map_size(self):
        """Get the map size from the combobox as an int. ie. 2048"""
        return int(self.ui.cmb003.currentText())

    def cmb003(self, index, widget):
        """UV Map Size -- passive input; the panel's one map size, read via
        get_map_size by Pack, Auto Unwrap, Unfold, Cut Cylinder and Get/Set
        Texel Density. Nothing to do on change."""

    def s003(self, value, widget):
        """Texel Density -- passive input; read by Get/Set Texel Density (b003/b004).
        Nothing to do on change."""

    # ------------------------------------------------------------------ header
    def header_init(self, widget):
        """Header menu: Create UV Snapshot, Open UV Editor, RizomUV Bridge."""
        # Every entry is a one-shot action: dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Create UV Snapshot",
            setObjectName="uv_snapshot",
            setToolTip="Save an image of the UV layout (Maya: UV Snapshot; "
            "Blender: Export UV Layout, of the active mesh).",
        )
        widget.menu.add(
            "QPushButton",
            setText="Open UV Editor",
            setObjectName="uv_editor",
            setToolTip="Open the texture coordinate mapping window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="RizomUV Bridge",
            setObjectName="btn_rizom_bridge",
            setToolTip="Round-trip selected meshes through RizomUV using a Lua preset.",
            clicked=lambda: self.b032(),
        )
        # RizomUV is an optional third-party app: the entry follows the user's
        # ``unmet_policy`` (Preferences > Unavailable tools) when it isn't
        # installed, rather than offering a button whose only outcome is a "not
        # found" error. The lambda defers the engine import into gate_on_app;
        # ``APP.available`` is cached, so this costs one lookup after the first.
        self.gate_on_app(widget.menu.btn_rizom_bridge, lambda: self.tk.RizomUVBridge.APP)

    def uv_snapshot(self):
        """Create UV Snapshot: the host's UV layout image export, through its own dialog."""
        self.run_operation(self.tk.UvUtils.export_uv_image)

    def uv_editor(self):
        """Open UV Editor (the header's entry)."""
        self.b031()

    # ------------------------------------------------------------------ tb000  Pack
    def tb000_init(self, widget):
        """Initialize Pack UVs.

        One option box for both hosts: the packer (cmb019, Maya's Standard
        u3dLayout or the optional xatlas engine; Blender has one), then the
        options. Each packer honors its own set (``UvUtils.PACK_ENGINES``): the
        others disable while it is chosen, and an option no packer of the host
        honors is hidden there. Rotate Step also needs Rotate Max > Rotate Min,
        and Tile Coverage locks while a Tiles U / V grid is active (the grid's
        cells are copies of the pack region). Disable-only: resetting a combo
        would destroy the user's persisted choice.
        """
        menu = widget.option_box.menu
        menu.setTitle("Pack UVs")
        cmb019 = menu.add(
            "QComboBox",
            setObjectName="cmb019",
            setToolTip=self.sb.tooltip.fmt(
                title="Pack Method",
                body="Which packing engine runs.",
                bullets=[
                    "<b>Standard</b> -- Maya's <code>u3dLayout</code> (Unfold3D). "
                    "Drives the full option set below.",
                    "<b>xatlas</b> -- open-source external engine "
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
        cmb019.setCurrentIndex(0)  # Standard -- needs no external engine
        menu.add(
            "QCheckBox",
            setText="Rotate Shells",
            setObjectName="chk044",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Shells",
                body="Let the packer re-orient shells wherever that packs tighter.",
                bullets=[
                    "<b>On</b> -- xatlas tries 90° steps plus an arbitrary-angle "
                    "turn onto each shell's own axis and keeps the tighter result; "
                    "Blender's packer turns islands as it fits them.",
                    "<b>Off</b> -- shells keep their orientation.",
                ],
                notes=[
                    "Maya: the xatlas method's; Standard searches with Rotate "
                    "Min / Max instead.",
                    "A packer may still mirror shells regardless of this setting.",
                ],
            ),
        )
        chk043 = menu.add(
            "QCheckBox",
            setText="Brute Force (xatlas)",
            setObjectName="chk043",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Brute Force (xatlas)",
                body="Exhaustive placement search -- xatlas' main density lever. "
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
                    "square tile no matter the packer -- low fill there is the "
                    "shape of the shells, not the engine.",
                ],
            ),
        )
        # u3dLayout has only two distinct -preScaleMode behaviors in Maya 2025
        # (values 1-4 give identical results): 0 keeps input UV proportions, any
        # other value rescales shells by 3D area. Blender's Preserve 3D is an
        # average-islands-scale pass before the pack.
        cmb009 = menu.add(
            "QComboBox",
            setObjectName="cmb009",
            setToolTip=self.sb.tooltip.fmt(
                title="Pre-Scale Mode",
                body="How shells are sized relative to each other before packing.",
                bullets=[
                    "<b>Preserve UV</b> -- keep each shell's current UV size "
                    "relative to the others.",
                    "<b>Preserve 3D</b> -- rescale so UV area follows 3D surface "
                    "area, giving every packed shell the same texel density.",
                ],
            ),
        )
        for text, data in [
            ("Pre-Scale: Preserve UV", 0),
            ("Pre-Scale: Preserve 3D", 1),
        ]:
            cmb009.addItem(text, data)
        cmb009.setCurrentIndex(1)  # Preserve 3D
        s_pack_margin = menu.add(
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
        # Pre-Rotate Mode: mirrors Maya's stock dialog (performPolyLayoutUV.mel);
        # values pass straight through, 0 omits the flag.
        cmb010 = menu.add(
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
        cmb010.setCurrentIndex(0)
        # Packing-time rotation search, active when Rotate Max > Rotate Min. It
        # only re-orients a shell when that tightens the pack, and a degenerate
        # equal Min/Max range breaks packing -- the gate keeps it from being sent.
        s011 = menu.add(
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
                    "<b>90</b> -- keeps every shell axis-aligned.",
                    "<b>Smaller</b> -- tries more orientations, at more cost.",
                ],
                notes=["Active only while Rotate Max &gt; Rotate Min."],
            ),
        )
        s012 = menu.add(
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
        s013 = menu.add(
            "QSpinBox",
            setPrefix="Rotate Max: ",
            setObjectName="s013",
            set_limits=[0, 360],
            setValue=0,
            setToolTip=self.sb.tooltip.fmt(
                title="Rotate Max",
                body="Upper bound, in degrees, of the packing-time rotation search. "
                "<b>0</b> (the default) disables rotation -- raise it above Rotate "
                "Min to opt in.",
                notes=[
                    "A shell is only re-oriented where that tightens the pack.",
                    "0–180 with a 90° step is the usual choice.",
                    "Measurably helps fractional Tile Coverage regions -- a "
                    "half-tile box packed 0.55 → 0.71 fill on test content.",
                ],
            ),
        )
        s014 = menu.add(
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
        menu.add(
            "QSpinBox",
            setPrefix="UDIM: ",
            setObjectName="s004",
            set_limits=[1001, 1200],
            setValue=1001,
            setToolTip=self.sb.tooltip.fmt(
                title="UDIM",
                body="The tile the shells are packed into (1001–1200).",
                rows=[
                    ("1001", "first tile -- UV 0–1, 0–1"),
                    ("1002", "second tile -- UV 1–2, 0–1"),
                    ("1011", "start of the next row -- UV 0–1, 1–2"),
                ],
                notes=[
                    "Blender's packer has no target tile: the map is moved into "
                    "this one after the pack.",
                ],
            ),
        )
        # Fractional-tile packing: a box anchored at the target tile's bottom-left
        # corner (u3dLayout's fractional -packBox; Blender scales the packed map
        # about that corner).
        cmb015 = menu.add(
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
        # Post-pack scale-to-fit (u3dLayout -layoutScaleMode): omitted behaves as
        # Uniform (2); 1 keeps the exact input UV scale (overflow spills into the
        # neighboring tile instead of overlapping); 3 scales U and V apart.
        cmb018 = menu.add(
            "QComboBox",
            setObjectName="cmb018",
            setToolTip=self.sb.tooltip.fmt(
                title="Scale Mode",
                body="How shells are scaled to the pack region once they are placed.",
                bullets=[
                    "<b>Fill (uniform)</b> -- scale all shells together to fill "
                    "the region. Maya's default.",
                    "<b>Off (keep density)</b> -- shells keep their exact UV scale. "
                    "Anything that doesn't fit spills into the neighboring tile "
                    "rather than overlapping.",
                    "<b>Stretch (non-uniform)</b> -- scale U and V independently "
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
        # Multi-tile distribution (u3dLayout -tileU/-tileV): the grid anchors at
        # the pack box and extends right/up in box-sized cells, so it composes
        # with the UDIM spinbox; fractional coverage would carve sub-tile cells,
        # hence the coverage lock.
        s019 = menu.add(
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
                    "(a row is 10 tiles wide) -- the completion message says when.",
                ],
            ),
        )
        s020 = menu.add(
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
        # Instances share one shape and UV set: packing every one reserves tile
        # space for identical shells. Blender's linked duplicates share one mesh,
        # which its packer edits once anyway.
        chk016 = menu.add(
            "QCheckBox",
            setText="Skip Instances",
            setObjectName="chk016",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Skip Instances",
                body="Pack one representative transform per instance group.",
                notes=[
                    "Instances share a single shape and UV set, so packing every "
                    "copy just reserves tile space for identical shells -- the "
                    "result already applies to all of them.",
                    "Ignored for component (face / UV) selections.",
                ],
            ),
        )
        self._host_only(
            "maya", cmb019, chk043, cmb010, s011, s012, s013, s014, cmb018, s019,
            s020, chk016,
        )
        self._host_only("blender", s_pack_margin)

        def _sync_gates():
            _engine, honored = self._pack_engine(menu)
            for name, option in self.PACK_CONTROLS.items():
                getattr(menu, name).setEnabled(option in honored)
            menu.s011.setEnabled(
                "rotate_step" in honored and menu.s013.value() > menu.s012.value()
            )
            grid = "tiles" in honored and (menu.s019.value() > 1 or menu.s020.value() > 1)
            menu.cmb015.setEnabled(not grid)

        menu.cmb019.currentIndexChanged.connect(_sync_gates)
        for spinbox in (menu.s012, menu.s013, menu.s019, menu.s020):
            spinbox.valueChanged.connect(_sync_gates)
        _sync_gates()

    def _pack_engine(self, menu):
        """``(engine, options)``: the chosen packer and the ``pack_uvs`` options
        it honors. A host with one packer (Blender) hides the method combo; any
        value it holds there resolves to that packer."""
        engines = self.tk.UvUtils.PACK_ENGINES
        engine = menu.cmb019.currentData()
        if engine not in engines:
            engine = "standard"
        return engine, engines[engine]

    @staticmethod
    def _pack_options(menu, honored):
        """The option-box values of the ``pack_uvs`` options in *honored*."""
        readers = {
            "rotate": lambda: menu.chk044.isChecked(),
            "brute_force": lambda: menu.chk043.isChecked(),
            "margin": lambda: menu.s_pack_margin.value(),
            "pre_rotate": lambda: menu.cmb010.currentData(),
            "rotate_step": lambda: menu.s011.value(),
            "rotate_min": lambda: menu.s012.value(),
            "rotate_max": lambda: menu.s013.value(),
            "mutations": lambda: menu.s014.value(),
            "scale_mode": lambda: menu.cmb018.currentData(),
            "tiles": lambda: (menu.s019.value(), menu.s020.value()),
            "skip_instances": lambda: menu.chk016.isChecked(),
        }
        return {name: read() for name, read in readers.items() if name in honored}

    def tb000(self, widget):
        """Pack UVs: hand the selection to ``UvUtils.pack_uvs`` (scope, gutters,
        tile grid and per-mesh failure isolation are its; one undo step) and
        summarize the result: texel density, map size, target UDIM(s), skipped
        meshes. Select objects to pack their whole maps; in Maya, faces / UVs /
        UV shells pack only that region and leave the rest of the map where it
        is (a component selection widens to whole faces).
        """
        menu = widget.option_box.menu
        engine, honored = self._pack_engine(menu)
        options = self._pack_options(menu, honored)
        udim = menu.s004.value()
        map_size = self.get_map_size()
        selection = self.require_selection()
        if selection is None:
            return
        # One bulk engine call with nothing to tick from the inside: the marquee
        # is painted before it and torn down after.
        with self.sb.progress(text=f"Working: Pack UVs ({engine})") as update:
            update()
            try:
                result = self.tk.UvUtils.pack_uvs(
                    selection,
                    engine=engine,
                    map_size=map_size,
                    udim=udim,
                    coverage=menu.cmb015.currentData(),
                    preserve_3d=menu.cmb009.currentData() == 1,  # Preserve 3D
                    **options,
                )
            except (RuntimeError, ValueError) as error:
                # A missing optional engine raises before the scene is touched,
                # its pip command in the message.
                prefix = "xatlas pack unavailable." if engine == "xatlas" else ""
                self.sb.message_box(
                    f"<b>{prefix}</b><br><br>{error}" if prefix else f"<b>{error}</b>"
                )
                return
        self._report_pack(result, udim, map_size, options.get("tiles", (1, 1))[0])

    def _report_pack(self, result, udim, map_size, tiles_u_requested):
        """Summarize a ``pack_uvs`` result: what packed and what was skipped, the
        resulting texel density, the map size and the target UDIM(s)."""
        tiles_u, tiles_v = result.tiles  # the grid that ran (Tiles U is clamped)
        density = 0.0
        if result.succeeded:
            # Over what actually packed: a faces-only pack read back as a
            # whole-mesh density would report a number the run never produced.
            # Never let a measuring hiccup swallow the pack result: the summary
            # then leaves the density out.
            try:
                density = self.tk.UvUtils.get_texel_density(
                    list(result.targets) or list(result.succeeded), map_size
                )
            except Exception:  # noqa: BLE001 - the pack itself succeeded
                density = 0.0
        if tiles_u > 1 or tiles_v > 1:
            last_udim = udim + (tiles_u - 1) + 10 * (tiles_v - 1)
            target = f"<b>Target UDIMs:</b> {udim}-{last_udim} ({tiles_u} × {tiles_v})"
        else:
            target = f"<b>Target UDIM:</b> {udim}"
        stats = (
            (f"<b>Texel Density:</b> {density:,.1f} px/unit<br>" if density else "")
            + f"<b>Map Size:</b> {map_size} × {map_size} px<br>"
            + target
        )
        if tiles_u < tiles_u_requested:
            stats += (
                f"<br><i>Tiles U clamped to {tiles_u} -- the grid can't extend "
                f"past the end of the UDIM row.</i>"
            )
        packed = len(result.objects)
        if result.failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in result.failed
            )
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Packed: {packed} mesh(es)<br>"
                f"✗ Skipped: {len(result.failed)} mesh(es)<br><br>"
                f"{stats}<br><br>"
                f"<b>Skipped meshes:</b><br>{failed_list}<br><br>"
                f"<i>Tip: Use Mesh > Cleanup to fix non-manifold geometry.</i>"
            )
        elif result.succeeded:
            self.sb.message_box(
                f"<b>UV Pack Complete</b><br><br>"
                f"✓ Successfully packed {packed} mesh(es).<br><br>"
                f"{stats}"
            )

    # ------------------------------------------------------------------ tb001  Auto Unwrap
    def tb001_init(self, widget):
        """Initialize Auto Unwrap: the method (cmb011) picks the host's own
        projection or one of two external unwrapping engines; the projection's
        settings (Maya's Scale Mode, Blender's Angle Limit / Island Margin) apply
        to Standard only, so they disable for the engine modes."""
        menu = widget.option_box.menu
        menu.setTitle("Auto Unwrap")
        cmb011 = menu.add(
            "QComboBox",
            setObjectName="cmb011",
            setToolTip=self.sb.tooltip.fmt(
                title="Unwrap Method",
                body="Which algorithm generates the UVs.",
                bullets=[
                    "<b>Standard</b> -- the host's own auto projection: Maya's best "
                    "fit from several planar projections, Blender's Smart UV Project.",
                    "<b>Hard Surface</b> -- Ministry of Flat, an external unwrapper "
                    "that classifies topology and places seams the way an artist "
                    "would. Best for mechanical / architectural models.",
                    "<b>Organic</b> -- Boundary First Flattening, an external "
                    "unwrapper using conformal flattening with automatic cone "
                    "singularities. Best for sculpted, scanned and character models.",
                ],
                notes=["The settings below apply to <b>Standard</b> only."],
            ),
        )
        for text, data in [
            ("Standard", "standard"),
            ("Hard Surface (Ministry of Flat)", "hard"),
            ("Organic (BFF)", "organic"),
        ]:
            cmb011.addItem(text, data)
        cmb011.setCurrentIndex(0)  # Standard -- needs no external engine
        cmb012 = menu.add(
            "QComboBox",
            setObjectName="cmb012",
            setToolTip=self.sb.tooltip.fmt(
                title="Scale Mode",
                body="How the projected shells are scaled afterwards "
                "(<code>polyAutoProjection -scaleMode</code>).",
                bullets=[
                    "<b>None</b> -- keep the projected scale.",
                    "<b>Uniform</b> -- scale uniformly to fit the unit square.",
                    "<b>Stretch to Square</b> -- scale U and V independently to "
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
        cmb012.setCurrentIndex(1)  # Uniform
        s_smart_angle = menu.add(
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
        s_smart_margin = menu.add(
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
        self._host_only("maya", cmb012)
        self._host_only("blender", s_smart_angle, s_smart_margin)

        def _sync_options():
            standard = menu.cmb011.currentData() == "standard"
            for control in (menu.cmb012, menu.s_smart_angle, menu.s_smart_margin):
                control.setEnabled(standard)

        cmb011.currentIndexChanged.connect(_sync_options)
        _sync_options()

    def tb001(self, widget):
        """Auto Unwrap: the selected meshes, by the host's own projection
        (``UvUtils.auto_project``) or an external engine (``auto_unwrap``)."""
        menu = widget.option_box.menu
        mode = menu.cmb011.currentData()
        map_size = self.get_map_size()
        selection = self.require_selection()
        if selection is None:
            return None
        if mode in self.AUTO_UNWRAP_ENGINE_MODES:
            # The engine runs its own per-object loop and error isolation.
            with self.sb.progress(text=f"Working: Auto Unwrap ({mode})") as update:
                update()
                result = self._run_auto_unwrap(selection, mode, map_size)
            if result is not None:
                self._report_auto_unwrap(result)
            return result
        with self.sb.progress(
            total=len(selection), text="Working: Auto Unwrap"
        ) as update:
            result = self.run_operation(
                self.tk.UvUtils.auto_project,
                selection,
                map_size=map_size,
                scale_mode=menu.cmb012.currentData(),
                angle_limit=menu.s_smart_angle.value(),
                margin=menu.s_smart_margin.value(),
                # Esc-hold stops the run; the projections already made stay.
                progress_callback=lambda done, _total, _text: update(done),
                empty="<b>No meshes in the selection.</b>",
            )
        if result and result.failed:
            self._report_auto_unwrap(result)
        return result

    def _run_auto_unwrap(self, objects, method, map_size):
        """``UvUtils.auto_unwrap``, its refusal shown: a missing engine reports
        its download URL in the message."""
        try:
            return self.tk.UvUtils.auto_unwrap(
                objects, method=method, map_size=map_size
            )
        except Exception as error:  # noqa: BLE001 - surfaced to the user, not swallowed
            self.sb.message_box(f"<b>Auto Unwrap failed.</b><br><br>{error}")
            return None

    @staticmethod
    def _engine_label(engine):
        """The engine's display name, read from its own spec (not a second copy);
        the host's own projection is "Standard"."""
        import pythontk as ptk

        spec = ptk.UvUnwrap.ENGINES.get(engine)
        return spec.label if spec is not None else str(engine).title()

    def _report_auto_unwrap(self, result):
        """Summarize an ``AutoUnwrapResult``; stay quiet on a clean single run."""
        label = self._engine_label(result.engine)
        if result.failed:
            failed_list = "<br>".join(
                f"• <b>{name}</b>: {reason}" for name, reason in result.failed
            )
            self.sb.message_box(
                f"<b>Auto Unwrap Complete</b><br><br>"
                f"<b>Engine:</b> {label}<br>"
                f"✓ Unwrapped: {len(result.succeeded)} mesh(es)<br>"
                f"✗ Failed: {len(result.failed)} mesh(es)<br><br>"
                f"<b>Failed meshes:</b><br>{failed_list}"
            )
        elif len(result.succeeded) > 1:
            self.sb.message_box(
                f"<b>Auto Unwrap Complete</b><br><br>"
                f"<b>Engine:</b> {label}<br>"
                f"✓ Unwrapped {len(result.succeeded)} mesh(es)."
            )

    # ------------------------------------------------------------------ tb004  Unfold
    def tb004_init(self, widget):
        """Initialize Unfold: flatten the existing UVs along their seams (never
        cutting new ones; Cut Cylinder does that), then optionally relax,
        axis-align and stack similar shells."""
        menu = widget.option_box.menu
        menu.setTitle("Unfold UV")
        menu.add(
            "QCheckBox",
            setText="Optimize",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Even out the spacing between UVs after unfolding, fixing "
            "areas of distortion (Maya: Optimize; Blender: Minimize Stretch).",
        )
        menu.add(
            "QCheckBox",
            setText="Orient",
            setObjectName="chk007",
            setChecked=True,
            setToolTip="Orient the UV shells to run parallel with the nearest U or V axis.",
        )
        menu.add(
            "QCheckBox",
            setText="Stack Similar",
            setObjectName="chk022",
            setChecked=True,
            setToolTip="Stack only shells that fall within the set tolerance.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip="Stack shells with uv's within the given range.",
        )
        cmb013 = menu.add(
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
        cmb013.setCurrentIndex(0)  # Warn + Select
        cmb_unfold_method = menu.add(
            "QComboBox",
            addItems=["Angle Based", "Conformal"],
            setObjectName="cmb_unfold_method",
            setToolTip="Unwrap algorithm.",
        )
        s_unfold_margin = menu.add(
            "QDoubleSpinBox",
            setPrefix="Margin: ",
            setObjectName="s_unfold_margin",
            set_limits=[0, 1, 0.001, 3],
            setValue=0.0,
            setToolTip="Spacing between islands after unwrap.",
        )
        # Blender's unwrap never rejects a non-manifold mesh: no strategy to pick.
        self._host_only("maya", cmb013)
        self._host_only("blender", cmb_unfold_method, s_unfold_margin)

    def tb004(self, widget):
        """Unfold: relax / unfold the selected meshes' UVs (``UvUtils.unfold_uvs``)."""
        menu = widget.option_box.menu
        objects = self.require_selection()
        if objects is None:
            return
        result = self.run_operation(
            self.tk.UvUtils.unfold_uvs,
            objects,
            optimize=menu.chk017.isChecked(),
            orient=menu.chk007.isChecked(),
            stack_similar=menu.chk022.isChecked(),
            tolerance=menu.s000.value(),
            map_size=self.get_map_size(),
            repair=menu.cmb013.currentData() == "repair",
            method=menu.cmb_unfold_method.currentText().lower().replace(" ", "_"),
            margin=menu.s_unfold_margin.value(),
            empty="<b>No meshes in the selection.</b>",
        )
        if result is None or isinstance(result, list):
            return  # refused, or nothing to unfold: said so
        if result.blocked:
            self._warn_non_manifold(result.blocked, len(result.components))
        elif result.repaired:
            fixed = result.repaired["fixed"]
            detail = (
                f" -- <b>{fixed}</b> {'component' if fixed == 1 else 'components'} fixed"
                if fixed
                else ""
            )
            self.sb.message_box(
                "<b>Unfold complete.</b><br><br>"
                f"⚠ Non-manifold geometry was auto-repaired first{detail}.<br>"
                "<i>See the Script Editor for the per-mesh breakdown.</i>"
            )

    def _warn_non_manifold(self, kind, count):
        """Explain what blocked Unfold: ``kind`` ``"uvs"`` or ``"geometry"``, the
        *count* problem components the operation selected."""
        if kind == "uvs":
            kind = "UVs"
            selected = (
                f"<b>{count}</b> problem {'UV' if count == 1 else 'UVs'} selected "
                "in UV mode.<br><br>"
            )
            cause = (
                "Unfold can't flatten a mesh with <b>non-manifold UVs</b> -- "
                "corrupt UV topology (usually from an import) that Maya's own "
                "tools can't author.<br><br>"
            )
            manual = "• delete the UVs on the affected faces and re-project them manually.<br><br>"
        else:
            kind = "geometry"
            selected = (
                f"<b>{count}</b> problem {'vertex' if count == 1 else 'vertices'} "
                "selected in vertex mode.<br><br>"
                if count
                else ""
            )
            cause = (
                "Unfold can't flatten a mesh with <b>non-manifold vertices</b> -- "
                "points where the surface branches or folds back on itself.<br><br>"
            )
            manual = "• run <b>Mesh &gt; Cleanup</b> / <b>Merge</b> doubled verts manually.<br><br>"
        self.sb.message_box(
            f"<b>⚠ Unfold stopped -- non-manifold {kind}</b><br><br>"
            f"{cause}"
            f"{selected}"
            "<b>To fix:</b><br>"
            "• Set the Unfold option to <b>Repair + Retry</b> to auto-clean, or<br>"
            f"{manual}"
            "<i>Then run Unfold again.</i>"
        )

    # ------------------------------------------------------------------ tb007  Cleanup UV Sets
    def tb007_init(self, widget):
        """Initialize Cleanup UV Sets"""
        menu = widget.option_box.menu
        menu.setTitle("Cleanup UV Sets")
        menu.add(
            "QCheckBox",
            setText="Prefer Best Layout",
            setObjectName="chk029",
            setChecked=True,
            setToolTip="<b>Best Information Strategy</b><br>If checked: keep the UV "
            "set with the best layout (the largest UV footprint) of the valid "
            "sets.<br>If unchecked: keep the active / first UV set.",
        )
        menu.add(
            "QCheckBox",
            setText="Remove Empty Sets",
            setObjectName="chk035",
            setChecked=True,
            setToolTip="<b>Safe Cleanup</b><br>Delete the UV sets that hold no UV "
            "layout (never unwrapped).",
        )
        menu.add(
            "QCheckBox",
            setText="Delete Secondary Sets",
            setObjectName="chk036",
            setChecked=False,
            setToolTip="<b>Aggressive Cleanup</b><br>If checked: delete ALL other UV "
            "sets, leaving only the kept one.<br>If unchecked: only empty sets are "
            "deleted (when enabled); secondary sets with data are preserved.",
        )
        menu.add(
            "QCheckBox",
            setText="Rename to 'map1'",
            setObjectName="chk037",
            setChecked=True,
            setToolTip="<b>Standardization</b><br>Rename the kept UV set to the "
            "default 'map1' (Maya also moves it to the first index).",
        )
        menu.add(
            "QCheckBox",
            setText="Force Rename",
            setObjectName="chk038",
            setChecked=False,
            setToolTip="<b>Destructive Rename</b><br>If another set is already named "
            "'map1':<br>Checked: overwrite it with the kept set.<br>Unchecked: skip "
            "the rename.",
        )
        menu.add(
            "QCheckBox",
            setText="Dry Run",
            setObjectName="chk030",
            setChecked=False,
            setToolTip="Report what would change without modifying anything.",
        )

    def tb007(self, widget):
        """Cleanup UV Sets: keep each mesh's best (or active) UV set, remove the
        empty / extra ones and optionally rename the survivor to map1."""
        menu = widget.option_box.menu
        dry_run = menu.chk030.isChecked()
        rename = menu.chk037.isChecked() or menu.chk038.isChecked()
        selection = self.require_selection()
        if selection is None:
            return
        results = self.run_operation(
            self.tk.Diagnostics.cleanup_uv_sets,
            selection,
            remove_empty=menu.chk035.isChecked(),
            keep_only_primary=menu.chk036.isChecked(),
            rename_to_map1=menu.chk037.isChecked(),
            force_rename=menu.chk038.isChecked(),
            prefer_largest_area=menu.chk029.isChecked(),
            dry_run=dry_run,
        )
        if not results:
            return
        verb, del_verb = ("Would keep", "would delete") if dry_run else ("Kept", "deleted")
        lines = []
        for r in results:
            if r.error:
                lines.append(f"❌ <b>{r.shape}</b>: {r.error}")
                continue
            details = ""
            if r.initial_sets:
                details = f"{verb} '<b>{r.primary_set}</b>'"
                if r.final_name != r.primary_set and rename:
                    details += f" → renamed to '<b>{r.final_name}</b>'"
                if r.sets_to_delete:
                    details += f", {del_verb} {len(r.sets_to_delete)} others"
            lines.append(f"• <b>{r.shape}</b>: {details}")
        header = "<b>Dry Run Report</b>" if dry_run else "<b>Cleanup Complete</b>"
        self.sb.message_box(f"{header}<br><br>" + "<br>".join(lines))

    # ------------------------------------------------------------------ tb009  Cut Cylinder
    def tb009_init(self, widget):
        """Initialize Cut Cylinder.

        Seams cylinder / tube / turned meshes the way a texture artist does by
        hand, then optionally unfolds each section flat. Maya reads the tube
        from its profile: every wall, chamfer and flare becomes a strip with ONE
        lengthwise seam, washers / steps and caps stay rings and discs, and the
        knobs are the artist's preferences (*Taper Angle* how far a band may
        tilt and still ride the strip; *Flat Angle* rings vs. sectors; *Fillet
        Size* how small a bevel rides its wall's strip; *Hide Seam From View* /
        *Invert Seam* where the lengthwise seam lands; *Keep Existing Seams*).
        Blender's Smart UV Project seams by *Crease Angle* alone, so those knobs
        are Maya's.
        """
        menu = widget.option_box.menu
        menu.setTitle("Cut Cylinder")
        s021 = menu.add(
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
        s022 = menu.add(
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
        s023 = menu.add(
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
            setToolTip="Edges sharper than this angle become seams. Maya reads "
            "the tube itself from its profile (Taper / Flat Angle) and applies "
            "this to geometry that isn't a clean tube; Blender's Smart UV Project "
            "seams by it everywhere. Default 45.",
        )
        chk045 = menu.add(
            "QCheckBox",
            setText="Hide Seam From View",
            setObjectName="chk045",
            setChecked=True,
            setToolTip="Place the lengthwise seam on the side facing away from "
            "the active viewport's camera, so it lands on the back. Off: a "
            "fixed side, away from Maya's default front-right perspective.",
        )
        chk040 = menu.add(
            "QCheckBox",
            setText="Invert Seam",
            setObjectName="chk040",
            setChecked=False,
            setToolTip="Flip the lengthwise seam to the opposite side (facing "
            "the viewer).",
        )
        chk046 = menu.add(
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
            setToolTip="Orient each shell to its nearest U/V axis when packing "
            "after the unfold.",
        )
        self._host_only("maya", s021, s022, s023, chk045, chk040, chk046)

    def tb009(self, widget):
        """Cut Cylinder (``UvUtils.unwrap_cylinder``)."""
        menu = widget.option_box.menu
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>The operation requires at least one "
            "cylinder / tube mesh."
        )
        if selection is None:
            return
        self.run_operation(
            self.tk.UvUtils.unwrap_cylinder,
            selection,
            angle=menu.s016.value(),
            invert_seam=menu.chk040.isChecked(),
            unfold=menu.chk041.isChecked(),
            orient=menu.chk042.isChecked(),
            map_size=self.get_map_size(),
            sew=not menu.chk046.isChecked(),
            taper_angle=menu.s021.value(),
            # True: the active viewport's camera (none open: a fixed default side).
            camera=True if menu.chk045.isChecked() else None,
            flat_angle=menu.s022.value(),
            trim_ratio=menu.s023.value() / 100.0,
            empty="<b>No cylinder seams found.</b><br>Select polygon cylinder / "
            "tube / turned mesh(es).",
        )

    # ------------------------------------------------------------------ texel density
    def b003(self):
        """Get Texel Density (into the s003 readout, against the cmb003 map size)."""
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the object(s) to measure."
        )
        if selection is None:
            return
        self.ui.s003.setValue(
            self.tk.UvUtils.get_texel_density(selection, self.get_map_size())
        )

    def b004(self):
        """Set Texel Density (from the s003 value, against the cmb003 map size)."""
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the object(s) to set the texel density on."
        )
        if selection is None:
            return
        self.run_operation(
            self.tk.UvUtils.set_texel_density,
            selection,
            density=self.ui.s003.value(),
            map_size=self.get_map_size(),
        )

    # ------------------------------------------------------------------ cut / sew
    def b005(self):
        """Cut UVs: split the UV shells along the selected edges (Maya: a mesh
        object, along all of its edges)."""
        self.run_operation(
            self.tk.UvUtils.cut_uvs,
            None,
            empty="<b>Nothing selected.</b><br>Select the edges to cut along "
            "(Maya: or mesh objects, to cut all of their edges).",
        )

    def b011(self):
        """Sew UVs: stitch the selected UV edges back together (Maya: a mesh
        object, along all of its edges)."""
        self.run_operation(
            self.tk.UvUtils.sew_uvs,
            None,
            empty="<b>Nothing selected.</b><br>Select the edges to sew "
            "(Maya: or mesh objects, to sew all of their edges).",
        )

    def b021(self, widget):
        """Unfold + Pack: the panel's Unfold, then its Pack, as one undo step."""
        # Guarded here as well as in each step, so an empty selection reports once
        # instead of twice (Unfold's box, then Pack's).
        if self.require_selection() is None:
            return
        with self.tk.CoreUtils.undo_chunk("Unfold + Pack"):
            self.ui.tb004.call_slot()
            self.ui.tb000.call_slot()

    # ------------------------------------------------------------------ tb022  Cut Hard Edges
    def tb022_init(self, widget):
        """Initialize Cut Hard Edges"""
        menu = widget.option_box.menu
        menu.setTitle("Cut Hard Edges")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s017",  # NOT s014 -- collides with tb000's "Mutations"
            set_limits=[0, 180],
            setValue=70,
            setToolTip="Lower bound: edges whose normal angle is at least this are cut.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s018",
            set_limits=[0, 180],
            setValue=180,
            setToolTip="Upper bound of the cut angle band (180 = no upper limit).",
        )
        menu.add(
            "QCheckBox",
            setText="Include UV Borders",
            setObjectName="chk025",
            setChecked=False,
            setToolTip="Also cut along edges that are existing UV shell borders.",
        )
        menu.add(
            "QCheckBox",
            setText="Include Auto Seams",
            setObjectName="chk026",
            setChecked=False,
            setToolTip="Also cut along auto-detected seams (Maya: u3dAutoSeam; "
            "Blender: a temporary Smart UV Project pass).",
        )

    def tb022(self, widget):
        """Cut Hard Edges: cut the UVs along the hard edges (always), optionally
        also along the UV borders and the auto-detected seams."""
        menu = widget.option_box.menu
        self.run_operation(
            self.tk.UvUtils.cut_hard_edges,
            None,
            low_angle=menu.s017.value(),
            high_angle=menu.s018.value(),
            uv_borders=menu.chk025.isChecked(),
            auto_seams=menu.chk026.isChecked(),
            empty="<b>Nothing selected.</b><br>Select the mesh object(s) to cut.",
        )

    # ------------------------------------------------------------------ b029  Pin
    def b029_init(self, widget):
        """Pin / Unpin: a plain text button. Defensively clears any ``checkable``
        a Qt Designer round-trip may have re-added (its "Pin" label is the .ui's)."""
        widget.setCheckable(False)

    def b029(self, widget):
        """Pin / Unpin the selected UVs (toggle: the first click on a fresh scope
        pins, the next unpins). An Edit-Mode mesh pins its selected vertices'
        UVs (Blender), an object its whole map."""
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the UVs to pin."
        )
        if selection is None:
            return
        key = self.tk.UvUtils.uv_scope_key(selection)
        pin = not self._b029_pinned if key == self._b029_key else True
        pinned = self.run_operation(
            self.tk.UvUtils.pin_uvs,
            selection,
            pin=pin,
            empty="<b>No UVs found in selection.</b>",
        )
        if pinned:
            self._b029_pinned, self._b029_key = pin, key

    # ------------------------------------------------------------------ b030  Stack
    def b030_init(self, widget):
        """Stack: a plain text button with the stack option box (Mode, Tolerance,
        Pin after stack), read back by :meth:`_stack_options`."""
        widget.setCheckable(False)
        menu = widget.option_box.menu
        menu.setTitle("Stack Shells")
        cmb020 = menu.add(
            "QComboBox",
            setObjectName="cmb020",
            setToolTip=self.sb.tooltip.fmt(
                title="Mode",
                body="How the selected shells are stacked. Click again to "
                "Unstack (restore the pre-stack positions).",
                bullets=[
                    "<b>Similar</b> -- shells with the same topology and shape "
                    "stack onto the first matching shell, rotated (and scaled) "
                    "to overlap exactly. Shells with no match stay put. Use "
                    "this to share texture space between identical parts.",
                    "<b>All shells</b> -- the basic stack: every selected shell "
                    "is translated onto one shared center regardless of shape "
                    "(no rotation).",
                ],
            ),
        )
        for text, data in [
            ("Mode: Similar (rotate to match)", self.STACK_MODE_SIMILAR),
            ("Mode: All shells (center, no rotation)", self.STACK_MODE_CENTER),
        ]:
            cmb020.addItem(text, data)
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s024",
            set_limits=[0, 10, 0.1, 1],
            setValue=1.0,
            setToolTip=self.sb.tooltip.fmt(
                title="Tolerance",
                body="Similar mode only: how much two shells' shapes may differ "
                "and still count as the same shell.",
                notes=[
                    "0 = practically identical; higher = looser. Identical "
                    "duplicates match at any value; 1.0 also tolerates the "
                    "small drift two separately unfolded copies pick up.",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Pin after stack",
            setObjectName="chk047",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Pin after stack",
                body="Pin the selected shells' UVs once stacked so a later "
                "Unfold / Optimize / Layout leaves them in place. Unstack "
                "puts the pins back as they were.",
                notes=[
                    "Pins are DCC-side only -- they do not travel through the "
                    "RizomUV bridge. To keep a stack together in a Rizom pack, "
                    "turn on <b>Keep Stacked</b> in the bridge's pack options "
                    "instead (it detects the overlapping shells itself).",
                ],
            ),
        )

    def _stack_options(self, widget):
        """``(mode, tolerance, pin)`` from the Stack option box (see :meth:`b030_init`)."""
        menu = widget.option_box.menu
        return (
            menu.cmb020.currentData() or self.STACK_MODE_SIMILAR,
            float(menu.s024.value()),
            bool(menu.chk047.isChecked()),
        )

    def b030(self, widget):
        """Stack / Unstack shells (toggle). The first click on a fresh scope
        captures the targeted UVs' positions and pins and stacks the shells per
        the option box (``UvUtils.stack_uv_shells``: Similar rotates matching
        shells into exact overlap, All shells translates every shell onto one
        center; Pin after stack pins them); the next click puts the positions
        and pins back (``UvUtils.set_uv_coords``)."""
        mode, tolerance, pin = self._stack_options(widget)
        selection = self.require_selection(
            "<b>Nothing selected.</b><br>Select the shell(s) to stack."
        )
        if selection is None:
            return
        key = self.tk.UvUtils.uv_scope_key(selection)
        if self._b030_snapshot is not None and key == self._b030_key:
            snapshot, self._b030_snapshot = self._b030_snapshot, None
            self.run_operation(self.tk.UvUtils.set_uv_coords, selection, snapshot)
            return
        self._b030_snapshot = None
        snapshot = self.tk.UvUtils.get_uv_coords(selection, pins=True)
        if not snapshot:
            self.sb.message_box("<b>No UVs found in selection.</b>")
            return
        similar = mode == self.STACK_MODE_SIMILAR
        stacked = self.run_operation(
            self.tk.UvUtils.stack_uv_shells,
            selection,
            tolerance=tolerance if similar else None,
            pin=pin,
        )
        if stacked is None:  # refused, and said so
            return
        if not stacked:
            if similar:
                self._report_no_similar_shells()
            else:
                self.sb.message_box(
                    "<b>No UV shells stacked.</b><br>Stacking needs at least two "
                    "shells (Blender, in Edit Mode: the shells the selection touches)."
                )
            return
        self._b030_snapshot, self._b030_key = snapshot, key

    def _report_no_similar_shells(self):
        """Similar mode found nothing to stack: say so."""
        self.sb.message_box(
            "<b>No similar shells found.</b><br>"
            "Similar mode stacks shells that share topology and shape (within "
            "the tolerance) -- raise the tolerance, or switch to <b>All shells</b> to "
            "stack regardless of shape."
        )

    # ------------------------------------------------------------------ windows and tools
    def b031(self):
        """Open UV Editor"""
        if self.tk.UiUtils.open_editor("UV Editor") is None:
            self.sb.message_box("The UV Editor could not be opened.")

    def b032(self):
        """RizomUV Bridge: the shared tool (round-trip Lua presets + one-way send)."""
        self.sb.handlers.marking_menu.show("rizom_bridge")

    def b033(self):
        """Open the Shell Xform panel (move / flip / rotate / align / orient /
        distribute) -- the ``More..`` button in the Transform group, beside Pin
        (b029) and Stack (b030); the shared ``slots/tools/shell_xform.py``."""
        self.sb.handlers.marking_menu.show("shell_xform")

    # ------------------------------------------------------------------ b000  Texture Combine
    # The shared Texture Combine tool (``slots/tools/texture_combine.py``): its
    # Combine mode merges materials into one atlas in place; its Transfer mode is
    # what this button's option box was.
    def b000_init(self, widget):
        """The Texture Combine launcher: a plain button, the panel is the UI."""
        widget.setText("Texture Combine...")
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Texture Combine",
                body="Open the Texture Combine panel.",
                bullets=[
                    "<b>Combine</b> -- merge the selected meshes' materials into "
                    "one atlas and one material, in place: nothing duplicated, "
                    "the originals recorded so they can be restored or "
                    "re-combined when a source map is revised.",
                    "<b>Transfer</b> -- UVs or textures from a source mesh onto "
                    "targets (exact texel correspondence, no rays).",
                ],
            )
        )

    def b000(self):
        """Open the Texture Combine panel (Combine / Transfer modes)."""
        self.sb.handlers.marking_menu.show("texture_combine")
