# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender UV panels."""


class UvMixin:
    """Shared UV-panel behavior (see ``slots/maya/uv.py``, ``slots/blender/uv.py``)."""

    # Auto Unwrap modes handled by an external unwrapping engine rather than the
    # DCC's own projection. Values are the ``method`` names understood by both
    # engines' ``UvUtils.auto_unwrap``.
    AUTO_UNWRAP_ENGINE_MODES = ("hard", "organic")

    @staticmethod
    def _engine_label(engine):
        """The engine's display name, read from its own spec (not a second copy)."""
        try:
            import pythontk as ptk

            return ptk.UvUnwrap.ENGINES[engine].label
        except (ImportError, KeyError):
            return engine

    def _run_auto_unwrap(self, engine, objects, method, map_size):
        """Run ``UvUtils.auto_unwrap`` and report the outcome.

        Parameters:
            engine: The DCC toolkit module (``mayatk`` / ``blendertk``).
            objects: Meshes to unwrap.
            method (str): ``"hard"`` or ``"organic"``.
            map_size (int): Texture size driving island spacing.
        """
        try:
            result = engine.UvUtils.auto_unwrap(
                objects, method=method, map_size=map_size
            )
        except Exception as error:  # noqa: BLE001 - surfaced to the user, not swallowed
            # A missing engine reports its download URL in the message.
            self.sb.message_box(f"<b>Auto Unwrap failed.</b><br><br>{error}")
            return None
        self._report_auto_unwrap(result)
        return result

    # ------------------------------------------------------------------ b030  Stack
    # Modes of the Stack button (option-box combo data). Both DCC engines
    # implement the pair with the same semantics: ``similar`` stacks shells of
    # the same topology + shape onto the first matching one, rotated (and
    # scaled) to overlap exactly, leaving unmatched shells where they are;
    # ``center`` (labelled "All shells") translates every targeted shell onto
    # one shared center regardless of shape -- the plain Stack.
    STACK_MODE_SIMILAR = "similar"
    STACK_MODE_CENTER = "center"

    # ------------------------------------------------------------------
    # Transfer tool: enablement of the option box's mode-dependent rows
    # ------------------------------------------------------------------
    # Both forks build the same option box and drive it from the same state, so
    # this pair lives here rather than twice: the bodies were byte-identical and
    # only the fork-specific *labels* differ, which are the panel's business
    # (they are what `docs/parity_map.py` ledgers), not this logic's.
    #
    # Contract with each fork's ``b000_init``: it sets ``_tt_ctl`` -- the
    # ``{role: widget}`` map named below -- plus ``_tt_src_button`` /
    # ``_tt_clear_action`` for the Set Source row, ``_tt_sources`` for the
    # captured meshes, and ``_tt_affix`` for the Material Affix field (a row of
    # the Output Name field's own option-box menu, so the tool's menu carries no
    # proxy for it). Every lookup is defensive so a panel that has not built
    # its option box yet (or a fork that grows a row later) is a no-op, not an
    # AttributeError from inside a signal handler.

    # Modes of the Transfer combo (option-box combo data), and the one place
    # that turns the chosen mode into the passes ``b000`` runs. One combo
    # rather than two toggles because the two are alternatives, not options
    # that compose: the texture pass writes the maps FOR THE TARGET'S OWN
    # layout, so a source layout copied alongside them would land in a UV set
    # nothing references. (The combined operation that IS useful reads the
    # TARGET's own textures -- "adopt a new layout on a textured mesh"; see
    # .claude/BACKLOG.md.)
    # ``auto`` defers the pick to run time: the source's materials decide
    # (any mapped texture slot -> Textures, none -> UV Set). Still one pass
    # per run -- Auto chooses between the alternatives, it never composes them.
    TRANSFER_UVS = "uvs"
    TRANSFER_TEXTURES = "textures"
    TRANSFER_AUTO = "auto"

    @classmethod
    def _tt_passes(cls, source_mode, transfer_mode):
        """``(do_uvs, do_textures)`` for a Source / Transfer mode pair.

        The UV pass is dropped for the *same mesh, other UV set* source: there
        is no second mesh to read a layout from, only two layouts of one mesh.

        ``TRANSFER_AUTO`` here is the UNRESOLVED mode (the option box asking
        which rows may matter): either pass could run, so both flags are on.
        ``b000`` resolves Auto to a concrete mode via :meth:`_tt_resolve_auto`
        before acting on the flags.
        """
        mode = transfer_mode or cls.TRANSFER_UVS
        if mode == cls.TRANSFER_AUTO:
            return source_mode != "uvset", True
        textures = mode == cls.TRANSFER_TEXTURES
        return not textures and source_mode != "uvset", textures

    @classmethod
    def _tt_resolve_auto(cls, texture_transfer, source_meshes):
        """Auto's run-time decision: the concrete Transfer mode for the sources.

        Textures as soon as any source material carries a mapped texture slot
        -- read through the engine's own material lookup, so Auto agrees
        exactly with what the texture pass would find. UV Set when none do:
        an untextured source has no maps to move, so its layout is the thing
        worth transferring.

        Parameters:
            texture_transfer: The engine's ``TextureTransfer`` class
                (``mtk`` / ``btk`` -- same names, same behavior).
            source_meshes: The resolved source mesh(es). Empty resolves to
                the UV pass and falls through to ``b000``'s selection errors.
        """
        for mesh in source_meshes:
            try:
                materials, _ = texture_transfer.face_materials(mesh)
            except Exception:  # noqa: BLE001 - an unreadable mesh has no maps
                continue
            for material in materials:
                try:
                    maps = texture_transfer.material_maps(material)
                except Exception:  # noqa: BLE001 - unreadable shader = no maps
                    continue
                if maps:
                    return cls.TRANSFER_TEXTURES
        return cls.TRANSFER_UVS

    @staticmethod
    def _tt_auto_note(auto, do_textures, source_mode=None):
        """The gate suffix naming Auto's pick, or ``""`` when there is none.

        Auto's choice is invisible state: a gate it trips ("pick a Transfer
        mode that includes X", "Output Name required") reads as a broken
        combo unless the message says Auto made the pick.

        The *reason* has to match how the pick was actually made. With a
        ``uvset`` source nothing is probed at all -- there is no second mesh
        to read a layout from, so Textures is the only pass the mode leaves
        available -- and claiming the materials decided it would send the
        user hunting through maps that were never consulted.
        """
        if not (auto and do_textures):
            return ""
        if source_mode == "uvset":
            return (
                "<br><br><i>Transfer: Auto</i> chose Textures — a second UV "
                "set of the same mesh carries no layout to transfer."
            )
        return (
            "<br><br><i>Transfer: Auto</i> chose Textures — the source's "
            "materials carry texture maps."
        )

    def _tt_material_affix(self):
        """``(assign_prefix, assign_suffix)`` from the Material Affix field.

        The field is ``_tt_affix``, a row of the Output Name field's own
        option-box menu (each fork's ``b000_init`` builds it and holds the
        reference -- the tool's menu has no proxy for a nested row).

        Blank -> ``("", None)``: ``None`` is the engine's Auto, which names the
        material exactly the Output Name (the tag it would otherwise append
        exists to keep a LAYOUT-derived name apart from the material it came
        from, and an explicit name already does that). A panel whose option box
        has not been built yet reads the same, per this mixin's defensive
        contract.

        A typed affix is split by the field's own tri-state picker
        (``uitk``'s ``AffixOption`` over ``ptk.StrUtils.split_affix``).
        ``default="suffix"``: the affix on a texture-set material reads
        ``<name>_MAT`` far more often than ``MAT_<name>``, and only a spelling
        that declares neither side (``MAT``, no underscore) ever reaches the
        fallback.
        """
        field = getattr(self, "_tt_affix", None)
        text = (field.text() or "").strip() if field is not None else ""
        if not text:
            return ("", None)
        return field.option_box.resolve_affix(text, default="suffix")

    def _tt_clear_source(self):
        """Forget the stored source meshes (the geometry is untouched)."""
        self._tt_sources = []
        self._tt_sync_controls()

    def _tt_sync_controls(self):
        """Grey every option that the current mode makes meaningless.

        Greying (not hiding) keeps the panel's shape stable, so each row is its
        own readout: the Set Source row follows the Source combo (capture only
        feeds the *stored sources* mode; its Select/Clear icons only once
        something is stored),
        Scope + Similarity follow the *single source mesh* mode (the Similar
        scopes additionally need the UV pass, which is what finds their
        targets), and the texture rows follow the Transfer combo -- which the
        *same mesh, other UV set* source pins to Textures, having no second
        mesh for a UV pass to read from.
        """
        ctl = getattr(self, "_tt_ctl", None)
        if ctl is None:
            return
        # ``.get``, per the contract above: a fork that has not built every
        # row yet must be a no-op here, not an AttributeError raised from
        # inside a signal handler.
        source, transfer = ctl.get("source"), ctl.get("transfer")
        if source is None:
            return
        mode = source.currentData() or "first"
        # The same-mesh source moves textures between two of ONE mesh's
        # layouts, so a UV pass has no second mesh to read from: the combo is
        # pinned to Textures rather than left offering a mode that cannot run.
        # Pinned BEFORE the passes are read -- ``setCurrentIndex`` re-enters
        # this method through the combo's signal, and computing first would
        # leave the outer call finishing with the pre-pin flags, re-greying
        # every texture row the re-entrant call had just enabled.
        same_mesh = mode == "uvset"
        if transfer is not None:
            index = transfer.findData(self.TRANSFER_TEXTURES)
            if same_mesh and index >= 0 and transfer.currentIndex() != index:
                transfer.setCurrentIndex(index)
            transfer.setEnabled(not same_mesh)
        uvs, textures = self._tt_passes(
            mode, transfer.currentData() if transfer is not None else None
        )
        stored_mode = mode == "stored"
        button = getattr(self, "_tt_src_button", None)
        if button is not None:
            button.setEnabled(stored_mode)
        # Select + Clear both only mean something once a capture exists, and a
        # fork that has not built one of them yet is a no-op here (same
        # defensive contract as ``ctl.get`` above).
        has_stored = stored_mode and bool(self._tt_sources)
        for name in ("_tt_select_action", "_tt_clear_action"):
            action = getattr(self, name, None)
            if action is not None:
                action.widget.setEnabled(has_stored)
        scope = ctl.get("scope")
        if scope is not None:
            scope.setEnabled(mode == "first")
        similarity = ctl.get("similarity")
        if similarity is not None:
            in_scope = (
                (scope.currentData() or "order") if scope is not None else "order"
            )
            similarity.setEnabled(mode == "first" and uvs and in_scope != "order")
        for w in ctl.get("texture_controls") or ():
            w.setEnabled(textures)
        # Rows that additionally need the material the texture pass builds:
        # nothing is assigned with Assign Result off, so an affix for its name
        # has nothing to affix.
        assign = ctl.get("assign")
        for w in ctl.get("assign_controls") or ():
            w.setEnabled(textures and (assign is None or assign.isChecked()))

    # Fork hooks for the Transfer tool (b000_init / b000). Each fork supplies
    # its engine and its words; the option box, its wiring and the texture
    # pass are this mixin's.
    #
    # ``_TT_TERMS`` -- the host's vocabulary for the same controls (Maya's "UV
    # Set" is Blender's "UV Map"): ``set`` ("set" / "map"), ``current`` (the
    # set a mesh reads by default), ``first`` / ``first_who`` (the single
    # source pick), ``order`` (the Selection Order bullet's tail),
    # ``instances`` (what the Similar scopes skip), ``bound`` (how a mesh's
    # textures name their UV set), ``name_note`` (what the Output Name's own
    # option box carries), ``output_dir`` / ``output_rel`` (the default and
    # relative output locations). These are the panel's labels -- what
    # ``docs/parity_map.py`` ledgers -- not logic.
    _TT_TERMS = {}

    def _tt_engine(self):
        """The host toolkit's ``TextureTransfer`` class (each fork overrides)."""
        raise NotImplementedError

    def _tt_add_assign_rows(self, name_menu):
        """Hook: extra rows for the Output Name field's option box.

        Returns the added widgets; they grey with the affix (they only mean
        something with Assign Result on). The default adds none.
        """
        return ()

    def b000_init(self, widget):
        """Initialize the Transfer option box.

        One tool, two transfers that are ALTERNATIVES (see the Transfer modes
        above): the source's UV layout onto the targets (the host toolkit's
        ``transfer_uvs`` -- exact for identical topology, sampled by proximity
        otherwise), or the source's textures re-mapped into each target's OWN
        layout (the host's ``TextureTransfer`` over ``pythontk.UvTransfer``:
        exact texel correspondence, so it never bleeds the way a ray-cast bake
        does where a mesh touches itself). They do not compose -- the texture
        pass keeps the target's UV set, so a source layout copied alongside its
        maps would land in a UV set nothing references. The Auto mode defers
        the pick to run time: a source whose materials carry texture maps
        transfers them; an untextured source transfers its layout.
        """
        import pythontk as ptk

        t = self._TT_TERMS
        word = t["set"]
        cap = word.title()
        engine = self._tt_engine()
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
                    f"<b>{t['first']}</b> — {t['first_who']} is the source; the "
                    "Scope below picks the targets.",
                    "<b>Stored Source Meshes</b> — the meshes captured with "
                    "<i>Set Source From Selection</i>, paired to the selected "
                    "targets by matching name (then by order). Use for a "
                    "re-unwrapped / repacked copy, or a many-materials-to-one "
                    "consolidation.",
                    f"<b>UV {cap} On Same Mesh</b> — textures only: read them through "
                    f"the Source UV {cap} and write them for the Target UV {cap}, on "
                    "each selected mesh.",
                ],
                notes=[
                    "Textures need identical topology (same faces and vertex "
                    "order); UVs do not.",
                ],
            ),
        )
        for text, data in [
            (f"Source: {t['first']}", "first"),
            ("Source: Stored Source Meshes", "stored"),
            (f"Source: UV {cap} On Same Mesh", "uvset"),
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
        # Select + Clear ride the button's own option box as icons. They grey
        # (rather than hide) while nothing is stored, so the row doubles as the
        # panel's only at-a-glance "is a source set?" readout -- a button that
        # vanishes reads as a layout change, not as a state. Select leads:
        # inspecting what you captured is the common follow-up, and the
        # destructive verb reads better last.
        self._tt_select_action = btn_src.option_box.set_action(
            callback=self._tt_select_source,
            icon="select",
            tooltip="Select the stored source meshes, so you can see what the "
            "capture actually holds. Enabled only while something is stored.",
        )
        self._tt_clear_action = btn_src.option_box.add_action(
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
                f"<b>{t['first']}</b>.",
                bullets=[
                    "<b>Selection Order</b> — every other selected object"
                    f"{t['order']}.",
                    "<b>Similar in Selection</b> — the selected objects that are "
                    "geometrically similar to the source.",
                    "<b>Similar in Scene</b> — every geometrically similar mesh "
                    "in the scene.",
                ],
                notes=[
                    "The Similar scopes find their targets by transferring UVs, "
                    f"so they need <b>Transfer UV {cap}</b> on; they skip "
                    f"{t['instances']}.",
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
                    f"<b>UV {cap}</b> — copy the source's {t['current']} uv {word} onto "
                    f"each target, replacing its {t['current']} one. Exact for "
                    "identical topology, sampled by proximity otherwise.",
                    "<b>Textures</b> — re-map the source's textures into "
                    "each target's OWN layout by exact texel correspondence: a "
                    "repacked atlas, a material consolidation, or another "
                    f"uv {word} on the same mesh. No rays, no cage, no bleed.",
                    "<b>Auto</b> — decided per run from the source's "
                    "materials: Textures when any of them carries a texture "
                    f"map, UV {cap} when none do.",
                ],
                notes=[
                    "Textures need identical topology (same faces and vertex "
                    f"order); uv {word}s do not.",
                ],
            ),
        )
        for text, data in [
            (f"Transfer: UV {cap}", "uvs"),
            ("Transfer: Textures", "textures"),
            # Auto rides LAST, not first where an Auto usually sits: the
            # combo's state persists by index, so inserting above the existing
            # rows would silently remap every saved choice.
            ("Transfer: Auto", "auto"),
        ]:
            cmb028.addItem(text, data)
        t_tt_src_uvset = menu.add(
            "QLineEdit",
            setPlaceholderText=f"Source UV {cap}: Auto",
            setText="",
            setObjectName="t_tt_src_uvset",
            setToolTip=self.sb.tooltip.fmt(
                title=f"Source UV {cap}",
                body=f"The UV {word} the textures are READ through. Blank = <b>Auto</b>.",
                bullets=[
                    "<b>Mesh sources</b> — Auto is each source mesh's "
                    f"{t['current']} UV {word}.",
                    f"<b>UV {cap} On Same Mesh</b> — Auto is the UV {word} the mesh's "
                    f"textures are actually bound to ({t['bound']}), i.e. the "
                    "layout the maps were painted for.",
                ],
            ),
        )
        t_tt_dst_uvset = menu.add(
            "QLineEdit",
            setPlaceholderText=f"Target UV {cap}: Auto",
            setText="",
            setObjectName="t_tt_dst_uvset",
            setToolTip=self.sb.tooltip.fmt(
                title=f"Target UV {cap}",
                body=f"The UV {word} the maps are WRITTEN for. Blank = <b>Auto</b>.",
                bullets=[
                    "<b>Mesh sources</b> — Auto is each target mesh's "
                    f"{t['current']} UV {word}.",
                    f"<b>UV {cap} On Same Mesh</b> — Auto is the first UV {word} other "
                    f"than the source, so a two-{word} mesh needs neither named.",
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
                    f"Its own option box carries {t['name_note']}",
                ],
            ),
        )
        t_tt_name.restore_state = False
        t_tt_name.option_box.clear_option = True
        # The material's naming convention, kept off the maps deliberately:
        # the files are the deliverable's, the affix is the scene's. It rides
        # the Output Name field's OWN option box rather than a row of its own:
        # it modifies that name and nothing else, and the tool's option box is
        # already long. Its picker is the shared uitk affix control -- one
        # tri-state icon (Auto -> Suffix -> Prefix) over
        # ptk.StrUtils.split_affix, the same one the mat_utils panels wear.
        name_menu = t_tt_name.option_box.menu
        name_menu.setTitle("Assigned Material")
        t_tt_affix = name_menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText="Material affix (blank = none)",
            setText="",
            setObjectName="t_tt_affix",
            setToolTip=self.sb.tooltip.fmt(
                title="Material Affix",
                body="Affixes the ASSIGNED MATERIAL's name. The maps keep "
                "<b>Output Name</b> as they are, so a material naming "
                "convention never leaks into the filenames.",
                bullets=[
                    "<b>_MAT</b> — <i>hero_MAT</i>: a leading underscore reads "
                    "as a suffix.",
                    "<b>MAT_</b> — <i>MAT_hero</i>: a trailing underscore reads "
                    "as a prefix.",
                    "The icon button pins the side outright when the spelling "
                    "does not say: <b>Auto</b> → <b>Suffix</b> → <b>Prefix</b>.",
                ],
                notes=[
                    "Blank — the material is named exactly <b>Output Name</b>.",
                    "Re-applied idempotently: a second run over the same result "
                    "does not stack a second copy of the affix.",
                    "Only meaningful with <b>Assign Result</b> on.",
                ],
            ),
        )
        t_tt_affix.option_box.clear_option = True
        # Fourth, custom state: the shared material naming convention.
        t_tt_affix.option_box.set_affix(default="auto", convention_key="material")
        assign_rows = tuple(self._tt_add_assign_rows(name_menu))
        # Held directly: it is a row of the NAME field's option-box menu, so the
        # tool's own menu carries no ``menu.t_tt_affix`` proxy for ``b000`` to
        # read (the same reason ``_tt_src_button`` is held).
        self._tt_affix = t_tt_affix
        # A uitk LineEdit for the option-box affordances: the clear icon shows
        # only while there is text (ClearOption auto-hides), and the browse
        # writes back the PORTABLE spelling -- relative to the project's
        # texture root when the pick is under it, which survives the project
        # being moved. The engine reads the entry the same way
        # (``TextureTransfer.resolve_output_dir``), so "relative" is a real
        # contract rather than a UI convention.
        t_tt_output = menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText=f"Output folder (blank = {t['output_dir']})",
            setText="",
            setObjectName="t_tt_output",
            setToolTip=self.sb.tooltip.fmt(
                title="Output Folder",
                body="Where the maps are written, as "
                "<i>&lt;name&gt;_&lt;Channel&gt;.png</i>.",
                bullets=[
                    f"<b>Blank</b> — <i>{t['output_dir']}</i>.",
                    f"<b>A relative entry</b> — {t['output_rel']}; "
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
            start_dir=lambda w=t_tt_output: engine.resolve_output_dir(w.text()),
            callback=lambda picked, w=t_tt_output: w.setText(
                ptk.FileUtils.relativize_output_dir(picked, engine.output_base_dir())
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
            "assign": chk050,
            "assign_controls": (t_tt_affix, *assign_rows),
        }
        for w in (cmb024, cmb014, cmb028):
            w.currentIndexChanged.connect(lambda *_: self._tt_sync_controls())
        chk050.toggled.connect(lambda *_: self._tt_sync_controls())
        self._tt_sync_controls()

    def _tt_texture_pass(self, targets, source, menu, out_name, **engine_kwargs):
        """Run ``b000``'s texture pass and return its report line.

        The same call in both forks: the host's ``TextureTransfer`` reads every
        texture row of the option box; *engine_kwargs* carries a fork's extra
        options (Maya's ``assign_shader_type``). A ``ValueError`` from the
        engine is reported, not raised -- the UV pass may already have run.
        """
        import os

        assign_prefix, assign_suffix = self._tt_material_affix()
        try:
            results = self._tt_engine()().transfer(
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
                assign_prefix=assign_prefix,
                assign_suffix=assign_suffix,
                **engine_kwargs,
            )
        except ValueError as e:
            return f"<b>Transfer Textures:</b> {e}"
        n_maps = sum(len(v) for v in results.values())
        folder = next(
            (os.path.dirname(p) for v in results.values() for p in v.values()),
            "",
        )
        return (
            f"Transferred <b>{n_maps}</b> map(s) for "
            f"<b>{len(results)}</b> material(s)"
            + (
                f'<br><a href="action://open?path={folder}">{folder}</a>'
                if folder
                else ""
            )
        )

    def b030_init(self, widget):
        """Stack button — non-checkable text button with the stack option box.

        Defensively clears any ``checkable`` property a Qt Designer round-trip
        may have re-added (the button's "Stack" label lives in the .ui). The
        option box (Mode / Tolerance / Pin) is one shared surface: each DCC
        fork's ``b030`` reads it through :meth:`_stack_options`.
        """
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
                    "<b>Similar</b> — shells with the same topology and shape "
                    "stack onto the first matching shell, rotated (and scaled) "
                    "to overlap exactly. Shells with no match stay put. Use "
                    "this to share texture space between identical parts.",
                    "<b>All shells</b> — the basic stack: every selected shell "
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
                    "Pins are DCC-side only — they do not travel through the "
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

    def _report_no_similar_shells(self):
        """Similar mode found nothing to stack — say so (both DCC forks)."""
        self.sb.message_box(
            "<b>No similar shells found.</b><br>"
            "Similar mode stacks shells that share topology and shape (within "
            "the tolerance) — raise the tolerance, or switch to <b>All shells</b> to "
            "stack regardless of shape."
        )

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

    def get_map_size(self):
        """Get the map size from the combobox as an int. ie. 2048"""
        return int(self.ui.cmb003.currentText())

    def cmb003(self, index, widget):
        """UV Map Size — passive input; the panel's one map size, read via
        get_map_size by Pack, Auto Unwrap, Unfold, Cut Cylinder and Get/Set
        Texel Density. Nothing to do on change."""

    def s003(self, value, widget):
        """Texel Density — passive input; read by Get/Set Texel Density (b003/b004).
        Nothing to do on change."""

    def b029_init(self, widget):
        """Initialize Pin/Unpin button — non-checkable text button.

        Defensively clears any `checkable` property a Qt Designer round-trip
        may have re-added (the button's "Pin" label lives in the .ui).
        """
        widget.setCheckable(False)
