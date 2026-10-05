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
    # Contract with ``b000_init``: it sets ``_tt_ctl`` -- the ``{role:
    # widget}`` map named below -- plus ``_tt_select_action`` /
    # ``_tt_clear_action`` (the Source combo's icons), ``_tt_sources`` for the
    # captured meshes, and the rows ``b000`` reads off the slot rather than a
    # menu proxy: ``_tt_affix`` (Material Affix) and ``_tt_similarity`` (a row
    # of the Targets combo's own option box). Every lookup is defensive so a
    # panel that has not built
    # its option box yet (or a fork that grows a row later) is a no-op, not an
    # AttributeError from inside a signal handler.

    # Modes of the Transfer combo (option-box combo data), and the one place
    # that turns the chosen mode into the passes ``b000`` runs. One combo
    # rather than two toggles because the two are alternatives, not options
    # that compose: the texture pass writes the maps FOR THE TARGET'S OWN
    # layout, so a source layout copied alongside them would land in a UV set
    # nothing references. (The combined operation that IS useful reads the
    # TARGET's own textures -- "adopt a new layout on a textured mesh"; see
    # .claude/BACKLOG.archive.md, 2026-08-19.)
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
    def _tt_resolve_auto(cls, texture_transfer, source_meshes, has_lightmap=None):
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
            has_lightmap: With *Include Lightmaps* on, ``callable(mesh)``
                that is truthy for a mesh carrying a committed lightmap (see
                :meth:`_tt_lightmap_probe`): a lightmap is then a map the
                Textures pass moves too, so it picks Textures as well.
                ``None`` -- material maps only.
        """
        for mesh in source_meshes:
            if has_lightmap is not None:
                try:
                    if has_lightmap(mesh):
                        return cls.TRANSFER_TEXTURES
                except Exception:  # noqa: BLE001 - an unreadable marker = none
                    pass
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
    def _tt_auto_note(auto, do_textures, source_mode=None, lightmaps=False):
        """The gate suffix naming Auto's pick, or ``""`` when there is none.

        Auto's choice is invisible state: a gate it trips ("the Similar
        scopes need a Transfer mode that includes UV Set", "the UV pass
        copies one source per target") reads as a broken combo unless the
        message says Auto made the pick.

        The *reason* has to match how the pick was actually made. With a
        ``uvset`` source nothing is probed at all -- there is no second mesh
        to read a layout from, so Textures is the only pass the mode leaves
        available -- and claiming the materials decided it would send the
        user hunting through maps that were never consulted. With
        *lightmaps* (Include Lightmaps on) a committed lightmap could have
        decided it as well, so the note names both.
        """
        if not (auto and do_textures):
            return ""
        if source_mode == "uvset":
            return (
                "<br><br><i>Transfer: Auto</i> chose Textures — a second UV "
                "set of the same mesh carries no layout to transfer."
            )
        if lightmaps:
            return (
                "<br><br><i>Transfer: Auto</i> chose Textures — the source "
                "carries texture maps or a committed lightmap."
            )
        return (
            "<br><br><i>Transfer: Auto</i> chose Textures — the source's "
            "materials carry texture maps."
        )

    @staticmethod
    def _tt_lightmaps_checked(menu):
        """Whether the option box's *Include Lightmaps* row is checked."""
        box = getattr(menu, "chk051", None)
        return bool(box is not None and box.isChecked())

    def _tt_lightmap_probe(self, menu):
        """Auto's lightmap test while *Include Lightmaps* is checked, else
        ``None`` -- the ``has_lightmap`` argument of :meth:`_tt_resolve_auto`.

        A marker check (``LightmapRecords.baked_objects``), not
        ``lightmap_info``: Auto only asks whether a lightmap is committed,
        and resolving its file can walk the whole texture tree."""
        if not self._tt_lightmaps_checked(menu):
            return None
        records = self._tt_records()
        return lambda mesh: records.baked_objects([mesh])

    def _tt_material_affix(self):
        """``(assign_prefix, assign_suffix)`` from the Material Affix field.

        The field is ``_tt_affix``, the Material section's affix row
        (:meth:`b000_init` builds it and holds the reference: ``Menu.add``
        registers the ``menu.<name>`` proxies on a timer, so ``b000`` reads it
        off the slot).

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

    #: Source combo data for Source: Auto -- resolved per run by
    #: :meth:`_tt_auto_source` into one of the concrete modes.
    SOURCE_AUTO = "auto"

    def _tt_auto_source(self, meshes, stored=()):
        """Source: Auto's reading of the selected *meshes*: ``(mode, target)``.

        First match wins, strongest evidence first:

        * One mesh combined from ALL the others -- ``"last"``, *target* that
          mesh, wherever it sits in the selection (the engine's
          ``find_combined``; three meshes or more).
        * The *stored* source meshes, when the selection holds none of them
          and they pair with it by topology (:meth:`_tt_stored_fits`) --
          ``"stored"``: the capture was made for exactly these targets.
        * One mesh -- ``"uvset"``: there is nothing else to read from.
        * Otherwise -- ``"first"``: the first pick (a mesh, or a group of
          them) is the source. Never a Similar scope: ``b000`` runs Auto's
          First as Rest of Selection.

        A mesh the engine cannot read raises ``ValueError``, which reads as
        "not combined" -- it then falls through to that mode's own errors.
        """
        if len(meshes) >= 3:
            try:
                found = self._tt_engine().find_combined(meshes)
            except ValueError:
                found = None
            if found:
                return "last", found[0]
        if stored and meshes and not set(stored) & set(meshes):
            if self._tt_stored_fits(meshes, stored):
                return "stored", None
        if len(meshes) == 1:
            return "uvset", None
        return "first", None

    def _tt_stored_fits(self, targets, stored):
        """Whether the *stored* sources pair with *targets* by TOPOLOGY.

        Names and order are only how ``pair_sources`` lines them up; a stale
        capture made for other meshes fails the topology check here, so Auto
        does not quietly read it.
        """
        engine = self._tt_engine()
        try:
            pairs = engine.pair_sources(list(targets), list(stored))
            return all(engine.topology_matches(t, s)[0] for t, s in pairs.items())
        except ValueError:
            return False

    def _tt_source_note(self, mode):
        """The report suffix naming what Source: Auto resolved *mode* to."""
        t = self._TT_TERMS
        reading = {
            "uvset": f"one mesh, so its textures move between its UV {t['set']}s",
            "last": "a mesh combined from all the others, so it is the target",
            "stored": "the stored source meshes, which match the selection",
            "first": f"{t['first_who']} as the source and the rest as targets",
        }[mode]
        return f"<br><br><i>Source: Auto</i> read {reading}."

    def _tt_plan(self, menu, mode, scope, source, targets, source_note):
        """``b000``'s run, decided -- one body for both forks.

        Each fork resolves *mode* (Source: Auto included), *source* and
        *targets* its own way, then hands them here: *Transfer: Auto* is
        resolved against the same *source* the passes will read, through the
        fork's engine (:meth:`_tt_engine`), the Output Name is read, and
        :meth:`_tt_gate` pairs the meshes or refuses. *source_note* is what
        Source: Auto read (``""`` when it was not used).

        Returns:
            ``(do_uvs, do_textures, out_name, pairs, targets, others,
            refusal)`` -- the passes to run, the Output Name as typed (blank:
            the texture pass names the result after the source), then
            :meth:`_tt_gate`'s four.
        """
        transfer_mode = menu.cmb_tt_transfer.currentData()
        auto = transfer_mode == self.TRANSFER_AUTO
        lightmap_probe = self._tt_lightmap_probe(menu)
        if auto and mode != "uvset":
            # Resolved BEFORE the pass-dependent gates below (the Similar-scope
            # check): what Auto decides is what they must ask for. An empty
            # probe resolves to the UV pass and falls through to the same
            # selection errors a manual mode would hit.
            transfer_mode = self._tt_resolve_auto(
                self._tt_engine(), source, has_lightmap=lightmap_probe
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
        return do_uvs, do_textures, out_name, pairs, targets, others, refusal

    def _tt_gate(
        self, mode, scope, source, targets, do_uvs, do_textures, notes=("", "")
    ):
        """``b000``'s refusals and the UV pass's pairs -- one body for both forks.

        Each fork resolves *source* / *targets* its own way (Maya: the picks in
        selection order; Blender: the active object); :meth:`_tt_plan` hands
        them here. *notes* is ``(auto_note, source_note)``: what Auto chose,
        appended to the refusals it could have caused.

        Returns:
            ``(pairs, targets, others, refusal)`` -- *pairs* ``[(source,
            target), ...]`` for the UV pass, ``None`` when a Similar scope finds
            the targets (they come back ``None`` too, and *others* holds the
            selected candidates Similar in Selection searches); *refusal* is the
            message to show instead of running, ``None`` to run.
        """
        t = self._TT_TERMS
        cap = t["set"].title()
        auto_note, source_note = notes
        if not (do_uvs or do_textures):
            return (
                None,
                targets,
                None,
                (
                    f"<b>Nothing to transfer.</b><br>The <i>UV {cap}s On Same Mesh</i> "
                    "source has no second mesh to read a layout from, so it "
                    "transfers textures — pick a <b>Transfer</b> mode that "
                    "includes them." + source_note
                ),
            )
        if mode == "uvset":
            if not targets:
                return (
                    None,
                    targets,
                    None,
                    (
                        "<b>Nothing selected.</b><br>Select the mesh(es) to transfer "
                        "on." + source_note
                    ),
                )
            return None, targets, None, None
        if mode == "first" and scope != "order":
            if not source or (scope == "selection" and not targets):
                return None, None, None, t["pick_first"] + source_note
            if not do_uvs:
                return (
                    None,
                    None,
                    None,
                    (
                        "<b>The Similar scopes need a Transfer mode that includes "
                        f"UV {cap}</b> -- the UV pass is what finds their targets. "
                        "Use Rest of Selection to transfer textures alone." + auto_note
                    ),
                )
            return None, None, targets, None
        if mode == "stored" and not source:
            return (
                None,
                targets,
                None,
                (
                    "<b>No stored source meshes.</b><br>Store them with the <b>+</b> "
                    "icon on the Source row first."
                ),
            )
        if not (source and targets):
            hint = {"first": t["pick_first"], "last": t["pick_last"]}.get(
                mode, "<b>Nothing selected.</b><br>Select the target mesh(es)."
            )
            return None, targets, None, hint + source_note
        pairs, error = self._tt_pair(targets, source, do_uvs)
        return pairs, targets, None, (error + auto_note if error else None)

    def _tt_capture_source(self):
        """The Source combo's capture icon: store the selection, then switch
        the combo to Stored Meshes -- capturing is how the mode is entered."""
        self._tt_set_source_from_selection()
        source = (getattr(self, "_tt_ctl", None) or {}).get("source")
        if source is not None and getattr(self, "_tt_sources", None):
            index = source.findData("stored")
            if index >= 0:
                source.setCurrentIndex(index)

    def _tt_similarity_value(self):
        """The Similar scopes' threshold -- a row of the Targets combo's own
        option box, so it is read off the slot (0.9 before it is built)."""
        spin = getattr(self, "_tt_similarity", None)
        return spin.value() if spin is not None else 0.9

    def _tt_node_path(self, node):
        """Hook: *node*'s ``|``-separated hierarchy path, for the derived
        Output Name (Maya's long name as given; Blender builds one)."""
        return str(node)

    def _tt_derived_name(self, source, targets):
        """The Output Name a blank field stands for: named after the source.

        ``ptk.StrUtils.common_name`` over the source meshes' paths (the
        targets' when the source is the mesh itself), dropping the naming
        convention's type markers so ``SOLDERING_TABLE_LOC`` reads
        ``SOLDERING_TABLE``.
        """
        import pythontk as ptk

        nodes = list(source) if source else list(targets or [])
        name = ptk.StrUtils.common_name(
            [self._tt_node_path(n) for n in nodes],
            strip=ptk.NamingConvention.all_affixes(),
        )
        return name or "transfer"

    def _tt_pair(self, targets, sources, do_uvs):
        """``(pairs, error)`` for mesh sources -- the Stored and Last modes.

        Pairs through the engine's ``pair_sources``: one to one by name, or,
        with more sources than targets, each target with the sources it was
        combined from. *pairs* is ``[(source, target), ...]`` for the UV pass;
        *error* is the message to show instead (``None`` when pairing worked).
        A combined target refuses the UV pass up front -- a layout cannot be
        copied from several meshes onto one -- rather than after the run.
        """
        try:
            grouped = self._tt_engine().pair_sources(targets, sources)
        except ValueError as e:
            return None, f"<b>Transfer:</b><br>{e}"
        if do_uvs and any(isinstance(s, tuple) for s in grouped.values()):
            return None, (
                "<b>The UV pass copies one source per target.</b><br>The target "
                "was combined from several sources, so only their textures can "
                "travel — pick <b>Transfer: Textures</b>."
            )
        return [(s, t) for t, s in grouped.items()], None

    def _tt_clear_source(self):
        """Forget the stored source meshes (the geometry is untouched)."""
        self._tt_sources = []
        self._tt_sync_controls()

    def _tt_sync_controls(self):
        """Grey every option that the current mode makes meaningless.

        Greying (not hiding) keeps the panel's shape stable, so each row is its
        own readout: the Source combo's Select/Clear icons follow the capture
        (lit only once something is stored -- Stored and Auto both read it),
        Targets + Similarity follow the *first selected* mode (the Similar
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
        mode = source.currentData() or self.SOURCE_AUTO
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
        # Select + Clear both only mean something once a capture exists, and a
        # fork that has not built one of them yet is a no-op here (same
        # defensive contract as ``ctl.get`` above).
        has_stored = bool(getattr(self, "_tt_sources", None))
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
        # A lightmap travels between MESHES: on one mesh the texture move
        # leaves the lightmap's own UV set -- and so the lightmap -- untouched.
        lightmaps = ctl.get("lightmaps")
        if lightmaps is not None:
            lightmaps.setEnabled(textures and not same_mesh)
        # Rows that additionally need the material the texture pass builds:
        # nothing is assigned with Assign Result off, so an affix for its name
        # has nothing to affix.
        assign = ctl.get("assign")
        for w in ctl.get("assign_controls") or ():
            w.setEnabled(textures and (assign is None or assign.isChecked()))

    # Fork hooks for the Transfer tool (b000_init / b000). Each fork supplies
    # its engine (``_tt_engine``, ``_tt_records``) and its words; the option
    # box, its wiring, the run's plan (``_tt_plan``) and the texture +
    # lightmap passes are this mixin's.
    #
    # ``_TT_TERMS`` -- the host's vocabulary for the same controls (Maya's "UV
    # Set" is Blender's "UV Map"): ``set`` ("set" / "map"), ``current`` (the
    # set a mesh reads by default), ``first`` / ``first_who`` (the single
    # source pick), ``last`` / ``last_who`` (the single TARGET pick, every
    # other mesh a source), ``order`` (the Selection Order bullet's tail),
    # ``instances`` (what the Similar scopes skip), ``bound`` (how a mesh's
    # textures name their UV set), ``output_dir`` / ``output_rel`` (the default and
    # relative output locations). These are the panel's labels -- what
    # ``docs/parity_map.py`` ledgers -- not logic.
    _TT_TERMS = {}

    def _tt_engine(self):
        """The host toolkit's ``TextureTransfer`` class (each fork overrides)."""
        raise NotImplementedError

    def _tt_records(self):
        """The host toolkit's ``LightmapRecords`` class (each fork overrides):
        Auto's lightmap probe asks it (:meth:`_tt_lightmap_probe`)."""
        raise NotImplementedError

    def _tt_shader_items(self):
        """Hook: ``(label, data)`` shader types the Material row can rebuild
        the result on (Maya: ``ShaderConverter.TARGETS``). The default offers
        none -- a Blender material is one node graph, nothing to retype."""
        return ()

    def _tt_add_assign_rows(self, menu):
        """The Material row, below the affix: what the assigned material is.

        "Same as source" leads (and so is the default): the result is a copy
        of the SOURCE's material pointed at the new maps, so it keeps the look
        being transferred. "Same as target" copied whatever the target wore --
        an import placeholder, typically -- and a StingrayPBS source's maps on
        a standardSurface rendered visibly darker. A fork's shader types
        (:meth:`_tt_shader_items`) follow. Combo state persists by INDEX, so
        the row is new under a fresh objectName. Returns the added widgets;
        they grey with the affix (they only mean something with Assign Result
        on).
        """
        t = self._TT_TERMS
        shaders = tuple(self._tt_shader_items())
        bullets = [
            "<b>Same as source</b> — a copy of the source's material (the one "
            "covering most of the layout), pointed at the new maps: the result "
            "looks like what was transferred.",
            "<b>Same as target</b> — a copy of the target's own material. For a "
            "re-bake in place, where the two are one.",
        ]
        notes = []
        if shaders:
            bullets.append(
                "<b>A named type</b> — the result is rebuilt on that shader "
                "(maps, constants and assignments carry across)."
            )
            notes.append(
                "Retyping a whole scene's materials is the <b>Material "
                "Updater</b>'s Shader Type option — same engine."
            )
        combo = menu.add(
            "QComboBox",
            setObjectName="cmb_tt_assign_from",
            setToolTip=self.sb.tooltip.fmt(
                title=t["assign_row"],
                body="What the material the run assigns is a copy of.",
                bullets=bullets,
                notes=notes,
            ),
        )
        # addItem, not ``add(prefix=...)``: that helper rewrites the data to
        # the item's label (and title-cases the text).
        combo.addItem(f"{t['assign_row']}: Same as source", "source")
        combo.addItem(f"{t['assign_row']}: Same as target", "target")
        for label, data in shaders:
            combo.addItem(f"{t['assign_row']}: {label}", data)
        # Held directly, like the affix: ``b000`` reads it through the slot
        # (:meth:`_tt_assign_options`), which covers an unbuilt box.
        self._tt_assign_from = combo
        return (combo,)

    def _tt_assign_options(self):
        """The Material row as engine keywords.

        ``assign_from`` always (an unbuilt box reads "source", the row's
        default); a named shader type adds ``assign_shader_type`` and keeps
        the source's material as what is retyped.
        """
        combo = getattr(self, "_tt_assign_from", None)
        data = combo.currentData() if combo is not None else "source"
        if data in ("source", "target"):
            return {"assign_from": data}
        return {"assign_from": "source", "assign_shader_type": data}

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
        transfers them; an untextured source transfers its layout. *Include
        Lightmaps* rides the texture pass: each source mesh's committed
        lightmap follows it to the target (:meth:`_tt_lightmap_pass`).

        Laid out in three groups, the decisions first: WHAT travels and
        between WHICH meshes (Transfer, Source, Targets -- Auto leads both mode
        combos), then the Textures rows (greyed for a UV pass), then the
        assigned Material. Settings only one mode reads ride that row's own
        option box instead of a row of their own: the Stored source's capture
        verbs on the Source combo, the Similarity threshold on the Targets
        combo.
        """
        import pythontk as ptk

        t = self._TT_TERMS
        word = t["set"]
        cap = word.title()
        engine = self._tt_engine()
        menu = widget.option_box.menu
        menu.setTitle("Transfer UVs / Textures")
        # Both mode combos persist by INDEX, and Auto now leads each. New
        # objectNames (they were cmb028 / cmb024) start them fresh rather
        # than re-reading a saved index against the reordered list.
        cmb_tt_transfer = menu.add(
            "QComboBox",
            setObjectName="cmb_tt_transfer",
            setToolTip=self.sb.tooltip.fmt(
                title="Transfer",
                body="What travels from the source to the targets — one or "
                "the other, since the texture pass deliberately keeps the "
                "target's own layout.",
                bullets=[
                    "<b>Auto</b> — decided per run from the source's "
                    "materials: Textures when any of them carries a texture "
                    "map (or, with <b>Include Lightmaps</b> on, the source "
                    f"carries a committed lightmap), UV {cap} when none do.",
                    "<b>Textures</b> — re-map the source's textures into "
                    "each target's OWN layout by exact texel correspondence: a "
                    "repacked atlas, a material consolidation, or another "
                    f"uv {word} on the same mesh. No rays, no cage, no bleed.",
                    f"<b>UV {cap}</b> — copy the source's {t['current']} uv "
                    f"{word} onto each target, replacing its {t['current']} "
                    "one. Exact for identical topology, sampled by proximity "
                    "otherwise.",
                ],
                notes=[
                    "Textures need identical topology (same faces and vertex "
                    f"order); uv {word}s do not.",
                    "Every map is resampled the same way — a normal map's XY "
                    "also turn with any island the target rotates, read off "
                    "the two layouts alone. Never a bake: where a target stands "
                    "does not enter it.",
                ],
            ),
        )
        for text, data in [
            ("Transfer: Auto", self.TRANSFER_AUTO),
            ("Transfer: Textures", self.TRANSFER_TEXTURES),
            (f"Transfer: UV {cap}", self.TRANSFER_UVS),
        ]:
            cmb_tt_transfer.addItem(text, data)
        cmb_tt_source = menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb_tt_source",
            setToolTip=self.sb.tooltip.fmt(
                title="Source",
                body="Which selected meshes the UVs / textures come FROM; the "
                "rest are <b>targets</b>.",
                bullets=[
                    "<b>Auto</b> — read from the selection: a mesh combined from "
                    "all the others is the target (whatever order they were "
                    "picked in); a selection the stored source meshes match is "
                    f"their target; one mesh moves between its own UV {word}s; "
                    f"otherwise {t['first_who']} — mesh or group — is the "
                    "source.",
                    f"<b>{t['first']}</b> — {t['first_who']} is the source (a "
                    "group: its meshes, paired to the targets by name); the "
                    "<b>Targets</b> row picks the rest.",
                    f"<b>{t['last']}</b> — {t['last_who']} is the target and "
                    "every other selected mesh a source: a mesh combined from "
                    "the others and re-unwrapped takes all their textures.",
                    "<b>Stored Meshes</b> — the meshes captured with the "
                    "<b>+</b> icon, paired to the selected targets by name "
                    "(then by order).",
                    f"<b>UV {cap}s On Same Mesh</b> — textures only: read "
                    f"through the Source UV {cap}, written for the Target UV "
                    f"{cap}, on each selected mesh.",
                ],
                notes=[
                    "One source feeds every target; several sources can feed "
                    "ONE target combined from them, faces unedited (textures "
                    "only).",
                    "The icons store the selection as the source meshes (and "
                    "switch to Stored Meshes), select what is stored, and clear "
                    "it.",
                ],
            ),
        )
        for text, data in [
            ("Source: Auto", self.SOURCE_AUTO),
            (f"Source: {t['first']}", "first"),
            (f"Source: {t['last']}", "last"),
            ("Source: Stored Meshes", "stored"),
            (f"Source: UV {cap}s On Same Mesh", "uvset"),
        ]:
            cmb_tt_source.addItem(text, data)
        # The Stored mode's verbs ride its picker: capture leads (it is the
        # way INTO the mode), then Select -- inspecting the capture is the
        # common follow-up -- with the destructive Clear last. Select and Clear
        # grey (rather than hide) while nothing is stored, so the icons double
        # as the panel's "is a source stored?" readout.
        src_box = cmb_tt_source.option_box
        self._tt_capture_action = src_box.add_action(
            callback=self._tt_capture_source,
            icon="add",
            tooltip="Store the selected meshes as the source meshes.",
        )
        # The live hover lists what is stored NOW (each fork's
        # ``_tt_source_tooltip``) -- otherwise invisible until a run uses it.
        self.sb.tooltip.bind(self._tt_capture_action.widget, self._tt_source_tooltip)
        self._tt_select_action = src_box.add_action(
            callback=self._tt_select_source,
            icon="select",
            tooltip="Select the stored source meshes, so you can see what the "
            "capture actually holds. Enabled only while something is stored.",
        )
        self._tt_clear_action = src_box.add_action(
            callback=self._tt_clear_source,
            icon="clear",
            tooltip="Clear the stored source meshes. Enabled only while "
            "something is stored; the geometry itself is untouched.",
        )
        cmb014 = menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb014",
            setToolTip=self.sb.tooltip.fmt(
                title="Targets",
                body="Which meshes receive the transfer when the source is the "
                f"<b>{t['first']}</b>.",
                bullets=[
                    "<b>Rest of Selection</b> — every other selected object"
                    f"{t['order']}.",
                    "<b>Similar in Selection</b> — the selected objects that are "
                    "geometrically similar to the source.",
                    "<b>Similar in Scene</b> — every geometrically similar mesh "
                    "in the scene.",
                ],
                notes=[
                    "The Similar scopes find their targets by transferring UVs, "
                    f"so they need <b>Transfer: UV {cap}</b>; they skip "
                    f"{t['instances']}. Their threshold is this row's option "
                    "box.",
                ],
            ),
        )
        for text, data in [
            ("Targets: Rest of Selection", "order"),
            ("Targets: Similar in Selection", "selection"),
            ("Targets: Similar in Scene", "scene"),
        ]:
            cmb014.addItem(text, data)
        sim_menu = cmb014.option_box.menu
        sim_menu.setTitle("Similar Targets")
        d000 = sim_menu.add(
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
        # Held directly: a row of the Targets combo's own option-box menu, so
        # the tool's menu carries no ``menu.d000`` proxy for ``b000`` to read.
        self._tt_similarity = d000

        # ---- Textures ------------------------------------------------------
        menu.add("Separator", setTitle="Textures")
        # Optional, and deliberately NOT persisted: it names ONE deliverable.
        # ``restore_state`` is set before ``Menu.add``'s deferred
        # ``register_widget`` runs, which is the only window in which the
        # opt-out is read (``MainWindow.register_widget`` defaults it to True
        # only when the attribute is absent).
        t_tt_name = menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText="Output name: from the source",
            setObjectName="t_tt_name",
            setToolTip=self.sb.tooltip.fmt(
                title="Output Name",
                body="Names BOTH halves of the result: the material that gets "
                "assigned, and every map wired to it "
                "(<i>&lt;name&gt;_&lt;Channel&gt;.png</i>).",
                bullets=[
                    "<b>Blank</b> — named after the source: one source's own "
                    "name; several share their leading name tokens, else the "
                    "group that holds them all. Type markers (<i>_GRP</i>, "
                    "<i>_LOC</i>, <i>_GEO</i> … the naming convention's) are "
                    "dropped.",
                ],
                notes=[
                    "Never pre-filled from the last session: a name left over "
                    "from another scene would overwrite that scene's material "
                    "and maps without asking. The clock button recalls names "
                    "you typed — a pick, never a default.",
                    "Re-running with the same name replaces that material and "
                    "its maps — which is what a second attempt wants.",
                    "A run that has to keep two UV layouts apart appends each "
                    "layout's label, so their maps cannot collide.",
                ],
            ),
        )
        t_tt_name.restore_state = False
        t_tt_name.option_box.clear_option = True
        # History is opt-in recall, so it does not contradict the opt-out
        # above: nothing is restored until the user picks it. Recorded by
        # ``_tt_texture_pass`` for a TYPED name that produced a file -- a
        # derived one is rebuilt from the source every run anyway.
        t_tt_name.option_box.recent(
            settings_key="uv_transfer_output_names", text_align="left"
        )
        self._tt_name_recent = t_tt_name.option_box.find_option(
            self.sb.RecentValuesOption
        )
        # A uitk LineEdit for the option-box affordances: the clear icon shows
        # only while there is text (ClearOption auto-hides), and the browse
        # writes back the PORTABLE spelling -- relative to the project's
        # texture root when the pick is under it, which survives the project
        # being moved. The engine reads the entry the same way
        # (``TextureTransfer.resolve_output_dir``), so "relative" is a real
        # contract rather than a UI convention.
        t_tt_output = menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText=f"Output folder: {t['output_dir']}",
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
        # Paired settings share a row: the pair is read together (size and
        # its sampling), and each has a sane Auto that most runs never change.
        cmb025, cmb026 = menu.add_row(
            [
                (
                    "QComboBox",
                    dict(
                        setObjectName="cmb025",
                        setToolTip=self.sb.tooltip.fmt(
                            title="Resolution",
                            body="Output size per target material.",
                            bullets=[
                                "<b>Auto</b> — the largest source map feeding it."
                            ],
                        ),
                    ),
                ),
                (
                    "QComboBox",
                    dict(
                        setObjectName="cmb026",
                        setToolTip=self.sb.tooltip.fmt(
                            title="Quality",
                            body="Sub-samples per texel axis.",
                            bullets=[
                                "<b>Fast</b> (1) — point sampling; exact for 1:1 "
                                "layouts.",
                                "<b>Standard</b> (2) — anti-aliased island edges "
                                "and a box filter for islands packed smaller than "
                                "their source.",
                                "<b>High</b> (3) — for heavy downscaling.",
                            ],
                            notes=[
                                "Memory: 8 bytes x quality² x resolution². 4k "
                                "Standard ≈ 540 MB."
                            ],
                        ),
                    ),
                ),
            ],
            justify="expand",
        )
        cmb025.addItem("Resolution: Auto", 0)
        for n in (512, 1024, 2048, 4096, 8192):
            cmb025.addItem(f"Resolution: {n}", n)
        for text, data in [
            ("Quality: Fast", 1),
            ("Quality: Standard", 2),
            ("Quality: High", 3),
        ]:
            cmb026.addItem(text, data)
        cmb026.setCurrentIndex(1)
        # The normal maps' convention is no row of its own: each map's is read
        # off its content, then its filename (ptk.UvTransfer.normal_convention).
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
                    "<b>Fill</b> (-1) — fill every empty texel "
                    "(mip-safe, the usual choice)."
                ],
            ),
        )
        t_tt_src_uvset, t_tt_dst_uvset = menu.add_row(
            [
                (
                    "QLineEdit",
                    dict(
                        setPlaceholderText=f"Source UV {cap}: Auto",
                        setText="",
                        setObjectName="t_tt_src_uvset",
                        setToolTip=self.sb.tooltip.fmt(
                            title=f"Source UV {cap}",
                            body=f"The UV {word} the textures are READ through. "
                            "Blank = <b>Auto</b>.",
                            bullets=[
                                "<b>Mesh sources</b> — Auto is each source mesh's "
                                f"{t['current']} UV {word}.",
                                f"<b>UV {cap}s On Same Mesh</b> — Auto is the UV "
                                f"{word} the mesh's textures are actually bound "
                                f"to ({t['bound']}), i.e. the layout the maps "
                                "were painted for.",
                            ],
                        ),
                    ),
                ),
                (
                    "QLineEdit",
                    dict(
                        setPlaceholderText=f"Target UV {cap}: Auto",
                        setText="",
                        setObjectName="t_tt_dst_uvset",
                        setToolTip=self.sb.tooltip.fmt(
                            title=f"Target UV {cap}",
                            body=f"The UV {word} the maps are WRITTEN for. "
                            "Blank = <b>Auto</b>.",
                            bullets=[
                                "<b>Mesh sources</b> — Auto is each target mesh's "
                                f"{t['current']} UV {word}.",
                                f"<b>UV {cap}s On Same Mesh</b> — Auto is the "
                                f"first UV {word} other than the source, so a "
                                f"two-{word} mesh needs neither named.",
                            ],
                        ),
                    ),
                ),
            ],
            justify="expand",
        )
        # Off by default: a lightmap is the scene's lighting, not part of the
        # material, and carrying it is a choice. Persisted like every other
        # option row (unlike the Output Name, it names nothing).
        chk051 = menu.add(
            "QCheckBox",
            setText="Include Lightmaps",
            setObjectName="chk051",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Include Lightmaps",
                body="Also carry each source mesh's committed lightmap (the "
                "Lightmap Baker's) onto its target. A lightmap is not a "
                "material map: it travels on its own pass, bound per object.",
                bullets=[
                    f"<b>Same lightmap layout</b> — the target's lightmap UV "
                    f"{word} matches the source's: it is bound to the source's "
                    "own map and atlas rect. Nothing is written.",
                    f"<b>Different layout</b> — the lightmap is resampled into "
                    f"the target's lightmap UV {word} and written (HDR) as "
                    "<i>&lt;name&gt;_Lightmap.exr</i> in the Output Folder, at "
                    "the texel share it had in its source map.",
                ],
                notes=[
                    "The lighting is the source's: meant for a copy that stands "
                    "where the source stands (re-unwrapped, consolidated). A "
                    "target elsewhere is carried too, with a warning.",
                    f"A target without a lightmap UV {word} is given the "
                    "source's (the topology is the same), so its lightmap is "
                    f"bound, not resampled. No other UV {word} is written.",
                    "One mesh to one mesh: a target combined from several "
                    "sources needs its own bake.",
                    "Mesh sources only: on the same mesh, moving textures "
                    f"between UV {word}s leaves the lightmap untouched.",
                    "<b>Transfer: Auto</b> counts a committed lightmap as "
                    "something to transfer while this is on.",
                ],
            ),
        )

        # ---- Material -------------------------------------------------------
        menu.add("Separator", setTitle="Material")
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
                    "Named after <b>Output Name</b> (or the source); a run that "
                    "has to keep two layouts apart appends each layout's label.",
                    "The original materials are never modified.",
                ],
            ),
        )
        # The material's naming convention, kept off the maps deliberately:
        # the files are the deliverable's, the affix is the scene's. Its
        # picker is the shared uitk affix control -- one tri-state icon
        # (Auto -> Suffix -> Prefix) over ptk.StrUtils.split_affix, the same
        # one the mat_utils panels wear.
        t_tt_affix = menu.add(
            self.sb.registered_widgets.LineEdit,
            setPlaceholderText="Material affix: none",
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
        # Held directly, like the similarity: ``Menu.add`` registers the
        # ``menu.<name>`` proxies on a timer, and ``b000`` reads these through
        # the slot (:meth:`_tt_material_affix`), which also covers a panel
        # whose option box was never built.
        self._tt_affix = t_tt_affix
        assign_rows = tuple(self._tt_add_assign_rows(menu))
        self._tt_sources = []
        # Direct references: ``Menu.add`` registers the ``menu.<name>`` proxies
        # on a timer, so they are not addressable from inside this init.
        self._tt_ctl = {
            "source": cmb_tt_source,
            "scope": cmb014,
            "similarity": d000,
            "transfer": cmb_tt_transfer,
            "texture_controls": (
                t_tt_name,
                t_tt_output,
                cmb025,
                cmb026,
                s025,
                t_tt_src_uvset,
                t_tt_dst_uvset,
                chk050,
            ),
            "assign": chk050,
            "assign_controls": (t_tt_affix, *assign_rows),
            "lightmaps": chk051,
        }
        for w in (cmb_tt_source, cmb014, cmb_tt_transfer):
            w.currentIndexChanged.connect(lambda *_: self._tt_sync_controls())
        chk050.toggled.connect(lambda *_: self._tt_sync_controls())
        self._tt_sync_controls()

    def _tt_texture_pass(self, targets, source, menu, out_name, **engine_kwargs):
        """Run ``b000``'s texture pass and return its report.

        The same call in both forks: the host's ``TextureTransfer`` reads every
        texture row of the option box, and the Material row through
        :meth:`_tt_assign_options`; *engine_kwargs* carries a fork's extra
        options. With *Include Lightmaps* on
        and mesh sources, the lightmap pass (:meth:`_tt_lightmap_pass`) runs
        after it -- whatever the material pass found, since a lit but
        untextured source has a lightmap and no maps. A ``ValueError`` from
        the engine is reported, not raised -- the UV pass may already have run.
        A blank *out_name* is derived from the source
        (:meth:`_tt_derived_name`) and said so; a TYPED one is recorded in the
        field's history once the run produced a file. The engine names an
        output beside a name held outside the run (``seat_1`` while another
        object wears ``seat``), so the name it used is read back off its maps:
        the report and the lightmap pass follow that, not *out_name*.
        """
        import os

        lines = []
        produced = False
        typed = bool(out_name)
        if not typed:
            out_name = self._tt_derived_name(source, targets)
        named = out_name
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
                assign=menu.chk050.isChecked(),
                assign_prefix=assign_prefix,
                assign_suffix=assign_suffix,
                **{**self._tt_assign_options(), **engine_kwargs},
            )
        except ValueError as e:
            lines.append(f"<b>Transfer Textures:</b> {e}")
        else:
            n_maps = sum(len(v) for v in results.values())
            produced = bool(n_maps)
            folder = next(
                (os.path.dirname(p) for v in results.values() for p in v.values()),
                "",
            )
            lines.append(
                f"Transferred <b>{n_maps}</b> map(s) for "
                f"<b>{len(results)}</b> material(s)"
                + (
                    f'<br><a href="action://open?path={folder}">{folder}</a>'
                    if folder
                    else ""
                )
            )
            # One layout's maps are `<name>_<Channel>.png`; several layouts are
            # `<name>_<layout>` each, and the stem stands.
            stems = {
                os.path.basename(p).rsplit("_", 1)[0]
                for v in results.values()
                for p in v.values()
            }
            if len(results) == 1 and len(stems) == 1:
                named = stems.pop()
        if source is not None and self._tt_lightmaps_checked(menu):
            text, wrote = self._tt_lightmap_pass(targets, source, menu, named)
            lines.append(text)
            produced = produced or wrote
        if produced and not typed:
            lines.append(
                f"Named <b>{named}</b> after the source — type an "
                "<b>Output Name</b> to choose another."
            )
        elif produced and named != out_name:
            lines.append(
                f"Named <b>{named}</b>: <b>{out_name}</b> is held outside this "
                "run (another object's material, or a map one reads)."
            )
        recent = getattr(self, "_tt_name_recent", None)
        if produced and typed and recent is not None:
            recent.record(out_name)
        return "<br><br>".join(lines)

    def _tt_lightmap_pass(self, targets, source, menu, out_name):
        """The *Include Lightmaps* pass: ``(report line, wrote a file)``.

        The host's ``LightmapRecords.transfer_lightmaps`` over the same pairs
        as the material pass, writing any resampled map beside its maps (the
        Output Folder, named after the Output Name). Resolution is NOT the
        option box's: that sizes material maps, while a resampled lightmap
        keeps the texel share it had in its source map.
        """
        import os

        try:
            results = self._tt_records().transfer_lightmaps(
                targets,
                source,
                output_dir=menu.t_tt_output.text().strip() or None,
                output_name=out_name,
                supersample=menu.cmb026.currentData() or 2,
                padding=menu.s025.value(),
            )
        except ValueError as e:
            return f"<b>Transfer Lightmaps:</b> {e}", False
        if not results:
            # A target without a lightmap UV set is given the source's, so
            # only the source side can come up empty.
            return (
                "<b>No lightmaps transferred</b> — no source carries a committed "
                "lightmap, or its map or lightmap UVs are gone (see the log).",
                False,
            )
        resampled = [r["path"] for r in results.values() if r["how"] == "resampled"]
        rebound = len(results) - len(resampled)
        parts = []
        if rebound:
            parts.append(f"<b>{rebound}</b> bound to the source's own map")
        if resampled:
            parts.append(f"<b>{len(resampled)}</b> resampled into the target's layout")
        folder = os.path.dirname(resampled[0]) if resampled else ""
        return (
            f"Transferred lightmaps to <b>{len(results)}</b> object(s): "
            + ", ".join(parts)
            + "."
            + (
                f'<br><a href="action://open?path={folder}">{folder}</a>'
                if folder
                else ""
            ),
            bool(resampled),
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
