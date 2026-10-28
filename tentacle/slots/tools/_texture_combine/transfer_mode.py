# !/usr/bin/python
# coding=utf-8
"""The Texture Combine panel's Transfer mode: UVs or textures, source -> targets.

One tool, two transfers that are ALTERNATIVES: the source's UV layout onto the
targets (the host's ``UvUtils.transfer_uvs`` -- exact for identical topology,
sampled by proximity otherwise), or the source's textures re-mapped into each
target's OWN layout (the host's ``TextureTransfer``: exact texel
correspondence, no rays, no bleed). They do not compose -- the texture pass
keeps the target's UV channel, so a source layout copied alongside its maps
would land in one nothing references. *Auto* defers the pick to run time.

Which selected mesh is the source is the host's convention, read by
``TextureTransfer.selection_sides`` (Maya: the selection order; Blender: the
active object), and worded by its ``TextureTransfer.TERMS``.

:class:`TransferMode` is composed by
:class:`~tentacle.slots.tools.texture_combine.TextureCombineSlots` (which owns
the widgets' slot names and the shared Output / Material rows) -- a
controller, not a mixin.
"""

import html
import os
from typing import Tuple

import pythontk as ptk


class TransferMode:
    """Transfer mode's decisions and its run, over the panel's widgets."""

    TRANSFER_AUTO = "auto"
    TRANSFER_TEXTURES = "textures"
    TRANSFER_UVS = "uvs"
    SOURCE_AUTO = "auto"
    #: Overwrite target's report lists this many of what it left alone; the
    #: host's log has the rest.
    NOTE_LIMIT = 6

    def __init__(self, slots):
        self.slots = slots
        self.sb = slots.sb
        #: The stored source meshes, by name (``TextureTransfer.capture_sources``).
        self.sources = []
        self.similarity = None
        self.select_action = self.clear_action = None

    @property
    def ui(self):
        return self.slots.ui

    @property
    def tk(self):
        """The host toolkit (the panel's ``Slots.tk``)."""
        return self.slots.tk

    @property
    def terms(self):
        """The host's words for its selection convention and UV channels."""
        return self.tk.TextureTransfer.TERMS

    # ------------------------------------------------------------ widgets
    def init_transfer(self, widget) -> None:
        uv = self.terms["uv"]
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Transfer",
                body="What travels from the source to the targets -- one or the "
                "other, since the texture pass deliberately keeps the target's "
                "own layout.",
                bullets=[
                    "<b>Auto</b> -- decided per run: Textures when any source "
                    "material carries a texture map (or, with <b>Include "
                    "Lightmaps</b> on, the source carries a committed lightmap), "
                    f"{uv} when none do.",
                    "<b>Textures</b> -- re-map the source's textures into each "
                    "target's OWN layout by exact texel correspondence: a "
                    "repacked atlas, a material consolidation, or another "
                    f"{uv} on the same mesh. No rays, no cage, no bleed.",
                    f"<b>{uv}</b> -- copy the source's {self.terms['uv_current']} "
                    f"{uv} onto each target. Exact for identical topology, sampled "
                    "by proximity otherwise.",
                ],
                notes=[f"Textures need identical topology; {uv}s do not."],
            )
        )
        for label, data in (
            ("Transfer: Auto", self.TRANSFER_AUTO),
            ("Transfer: Textures", self.TRANSFER_TEXTURES),
            (f"Transfer: {uv}", self.TRANSFER_UVS),
        ):
            widget.addItem(label, data)
        widget.currentIndexChanged.connect(lambda *_: self.sync())

    def init_source(self, widget) -> None:
        t = self.terms
        uv = t["uv"]
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Source",
                body="Which selected meshes the UVs / textures come FROM; the rest "
                "are <b>targets</b>.",
                bullets=[
                    "<b>Auto</b> -- read from the selection: a mesh combined from "
                    "all the others is the target; a selection the stored meshes "
                    "match is their target; one mesh moves between its own "
                    f"{uv}s; otherwise {t['first_who']} is the source.",
                    f"<b>{t['first']}</b> -- {t['first_who']} is the source (a "
                    f"{t['group']}: its meshes, paired by name); <b>Targets</b> "
                    "picks the rest.",
                    f"<b>{t['last']}</b> -- {t['last_who']} is the target and "
                    "every other selected mesh a source.",
                    "<b>Stored Meshes</b> -- the meshes captured with the <b>+</b> "
                    "icon, paired to the selected targets by name (then order).",
                    f"<b>{uv}s On Same Mesh</b> -- textures only: read through "
                    f"the Source {uv}, written for the Target {uv}.",
                ],
            )
        )
        for label, data in (
            ("Source: Auto", self.SOURCE_AUTO),
            (f"Source: {t['first']}", "first"),
            (f"Source: {t['last']}", "last"),
            ("Source: Stored Meshes", "stored"),
            (f"Source: {uv}s On Same Mesh", "uvset"),
        ):
            widget.addItem(label, data)
        box = widget.option_box
        capture = box.add_action(
            callback=self.capture_source,
            icon="add",
            tooltip="Store the selected meshes as the source meshes.",
        )
        self.sb.tooltip.bind(capture.widget, self.source_tooltip)
        self.select_action = box.add_action(
            callback=self.select_source,
            icon="select",
            tooltip="Select the stored source meshes. Enabled while something is stored.",
        )
        self.clear_action = box.add_action(
            callback=self.clear_source,
            icon="clear",
            tooltip="Clear the stored source meshes (the geometry is untouched).",
        )
        widget.currentIndexChanged.connect(lambda *_: self.sync())

    def init_targets(self, widget) -> None:
        t = self.terms
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Targets",
                body="Which meshes receive the transfer when the source is the "
                f"<b>{t['first']}</b>.",
                bullets=[
                    "<b>Rest of Selection</b> -- every other selected object.",
                    "<b>Similar in Selection</b> -- the selected objects "
                    "geometrically similar to the source.",
                    "<b>Similar in Scene</b> -- every similar mesh in the scene.",
                ],
                notes=[
                    "The Similar scopes find their targets by transferring UVs, "
                    f"so they need <b>Transfer: {t['uv']}</b>; they skip the "
                    f"source's {t['instances']} (those share its UVs already). "
                    "Their threshold is this row's option box."
                ],
            )
        )
        for label, data in (
            ("Targets: Rest of Selection", "order"),
            ("Targets: Similar in Selection", "selection"),
            ("Targets: Similar in Scene", "scene"),
        ):
            widget.addItem(label, data)
        menu = widget.option_box.menu
        menu.setTitle("Similar Targets")
        self.similarity = menu.add(
            "QDoubleSpinBox",
            setObjectName="d_tt_similarity",
            setPrefix="Similarity: ",
            setValue=0.9,
            setMinimum=0.0,
            setMaximum=1.0,
            setSingleStep=0.05,
            setToolTip=self.sb.tooltip.fmt(
                title="Similarity",
                body="The minimum score (0-1) a mesh must reach to receive UVs, "
                "scored on bounding-box volume and vertex count.",
            ),
        )
        widget.currentIndexChanged.connect(lambda *_: self.sync())

    def init_resolution(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Resolution",
                body="Output size per target material.",
                bullets=["<b>Auto</b> -- the largest source map feeding it."],
            )
        )
        widget.addItem("Resolution: Auto", 0)
        for n in (512, 1024, 2048, 4096, 8192):
            widget.addItem(f"Resolution: {n}", n)

    def init_uv_sets(self, src, dst) -> None:
        t = self.terms
        uv = t["uv"]
        # The host's word on the fields themselves (the .ui says "UVs").
        src.setPlaceholderText(f"Source {uv}: Auto")
        dst.setPlaceholderText(f"Target {uv}: Auto")
        src.setToolTip(
            self.sb.tooltip.fmt(
                title=f"Source {uv}",
                body=f"The {uv} the textures are READ through. Blank = <b>Auto</b>.",
                bullets=[
                    f"<b>Mesh sources</b> -- each source mesh's {t['uv_current']} "
                    f"{uv}.",
                    f"<b>{uv}s On Same Mesh</b> -- {t['uv_linked']}: the layout the "
                    "maps were painted for.",
                ],
            )
        )
        dst.setToolTip(
            self.sb.tooltip.fmt(
                title=f"Target {uv}",
                body=f"The {uv} the maps are WRITTEN for. Blank = <b>Auto</b>.",
                bullets=[
                    f"<b>Mesh sources</b> -- each target mesh's {t['uv_current']} "
                    f"{uv}.",
                    f"<b>{uv}s On Same Mesh</b> -- the first {uv} other than the "
                    f"source, so a mesh with two needs neither named.",
                ],
            )
        )

    def init_lightmaps(self, widget) -> None:
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Include Lightmaps",
                body="Also carry each source mesh's committed lightmap (the "
                "Lightmap Baker's) onto its target, bound per object.",
                bullets=[
                    "<b>Same lightmap layout</b> -- bound to the source's own map "
                    "and atlas rect; nothing is written.",
                    "<b>Different layout</b> -- resampled into the target's "
                    f"lightmap {self.terms['uv']} and written as "
                    "<i>&lt;name&gt;_Lightmap.exr</i>.",
                ],
                notes=["Mesh sources only: on one mesh the lightmap is untouched."],
            )
        )
        widget.toggled.connect(lambda *_: self.sync())

    # ------------------------------------------------------------ sources
    def source_tooltip(self) -> str:
        """Live tooltip for the Store Source Meshes icon -- what is stored NOW.

        Names are stored (not node references), so a mesh renamed or removed
        since the capture is called out rather than silently listed.
        """
        stored = self.sources
        missing = len(stored) - len(self.tk.TextureTransfer.live_sources(stored))
        return self.sb.tooltip.stored_items(
            stored,
            title="Store Source Meshes",
            body="Store the current selection as the source meshes "
            f"({self.terms['group']}s contribute their meshes) and switch to "
            "<i>Stored Meshes</i>. <i>Source: Auto</i> reads them too, when they "
            "match the selection.",
            formatter=lambda n: n.rsplit("|", 1)[-1],
            noun="stored source mesh(es)",
            empty_text="Nothing stored yet.",
            notes=[f"{missing} no longer in the scene; skipped."] if missing else None,
        )

    def capture_source(self) -> None:
        self.sources = list(self.tk.TextureTransfer.capture_sources())
        if self.sources:
            index = self.ui.cmb_tt_source.findData("stored")
            if index >= 0:
                self.ui.cmb_tt_source.setCurrentIndex(index)
        self.sync()
        self.slots.status(
            f"Stored {len(self.sources)} source mesh(es)."
            if self.sources
            else "Nothing selected -- select the source meshes (or their "
            f"{self.terms['group']})."
        )

    def select_source(self) -> None:
        """Select the stored source meshes -- the capture, made visible.

        The same survivor filter the run applies, so what is selected is
        exactly what a run would read; a mesh deleted since the capture is
        reported rather than silently dropped, and one the host declines to
        select (Blender: an excluded collection, selection disabled) is
        reported, never forced -- a transfer reads it either way.
        """
        stored = self.sources
        alive = self.tk.TextureTransfer.live_sources(stored)
        if not alive:
            return self.slots.status(
                "Nothing stored -- store the source meshes with the + icon first."
                if not stored
                else "None of the stored source meshes are in the scene -- re-capture them."
            )
        selected = self.tk.TextureCombine.select(alive)
        missing = len(stored) - len(alive)
        unreachable = len(alive) - selected
        self.slots.status(
            f"Selected {selected} stored source mesh(es)."
            + (f" {missing} no longer in the scene; skipped." if missing else "")
            + (
                f" {unreachable} not selectable (excluded collection, or selection "
                "disabled)."
                if unreachable
                else ""
            )
        )

    def clear_source(self) -> None:
        self.sources = []
        self.sync()

    # ------------------------------------------------------------ decisions
    @classmethod
    def passes(cls, source_mode, transfer_mode) -> Tuple[bool, bool]:
        """``(do_uvs, do_textures)`` for a Source / Transfer pair (Auto unresolved
        = both possible; the same-mesh source has no second mesh for UVs)."""
        mode = transfer_mode or cls.TRANSFER_UVS
        if mode == cls.TRANSFER_AUTO:
            return source_mode != "uvset", True
        textures = mode == cls.TRANSFER_TEXTURES
        return not textures and source_mode != "uvset", textures

    def resolve_auto(self, source_meshes, has_lightmap=None) -> str:
        """Auto's run-time pick: Textures once any source material carries a map
        (or a committed lightmap, with *has_lightmap*), else UVs."""
        transfers = self.tk.TextureTransfer
        for mesh in source_meshes:
            if has_lightmap is not None:
                try:
                    if has_lightmap(mesh):
                        return self.TRANSFER_TEXTURES
                except Exception:  # noqa: BLE001 - unreadable marker = none
                    pass
            try:
                materials, _ = transfers.face_materials(mesh)
            except Exception:  # noqa: BLE001
                continue
            for material in materials:
                try:
                    if transfers.material_maps(material):
                        return self.TRANSFER_TEXTURES
                except Exception:  # noqa: BLE001
                    continue
        return self.TRANSFER_UVS

    def source_note(self, mode) -> str:
        t = self.terms
        reading = {
            "uvset": f"one mesh, so its textures move between its {t['uv']}s",
            "last": "a mesh combined from all the others, so it is the target",
            "stored": "the stored source meshes, which match the selection",
            "first": f"{t['first_who']} as the source and the rest as targets",
        }[mode]
        return f"<br><br><i>Source: Auto</i> read {reading}."

    def auto_note(self, auto, do_textures, source_mode=None, lightmaps=False) -> str:
        if not (auto and do_textures):
            return ""
        if source_mode == "uvset":
            return (
                f"<br><br><i>Transfer: Auto</i> chose Textures -- a second "
                f"{self.terms['uv']} of the same mesh carries no layout to transfer."
            )
        if lightmaps:
            return (
                "<br><br><i>Transfer: Auto</i> chose Textures -- the source carries "
                "texture maps or a committed lightmap."
            )
        return (
            "<br><br><i>Transfer: Auto</i> chose Textures -- the source's materials "
            "carry texture maps."
        )

    def pair(self, targets, sources, do_uvs):
        """``(pairs, error)`` for mesh sources (Stored / Last)."""
        try:
            grouped = self.tk.TextureTransfer.pair_sources(targets, sources)
        except ValueError as e:
            return None, f"<b>Transfer:</b><br>{e}"
        if do_uvs and any(isinstance(s, tuple) for s in grouped.values()):
            return None, (
                "<b>The UV pass copies one source per target.</b><br>The target was "
                "combined from several sources, so only their textures can travel "
                "-- pick <b>Transfer: Textures</b>."
            )
        return [(s, t) for t, s in grouped.items()], None

    def gate(self, mode, scope, source, targets, do_uvs, do_textures, notes=("", "")):
        """``(pairs, targets, others, refusal)`` -- the run's refusals and pairs."""
        t = self.terms
        auto_note, source_note = notes
        pick_first = f"<b>{t['pick_first']}</b>"
        pick_last = f"<b>{t['pick_last']}</b>"
        if not (do_uvs or do_textures):
            return (
                None,
                targets,
                None,
                (
                    f"<b>Nothing to transfer.</b><br>The <i>{t['uv']}s On Same "
                    "Mesh</i> source transfers textures -- pick a <b>Transfer</b> "
                    "mode that includes them." + source_note
                ),
            )
        if mode == "uvset":
            if not targets:
                return (
                    None,
                    targets,
                    None,
                    (
                        "<b>Nothing selected.</b><br>Select the mesh(es) to transfer on."
                        + source_note
                    ),
                )
            return None, targets, None, None
        if mode == "first" and scope != "order":
            if not source or (scope == "selection" and not targets):
                return None, None, None, pick_first + source_note
            if not do_uvs:
                return (
                    None,
                    None,
                    None,
                    (
                        "<b>The Similar scopes need a Transfer mode that includes "
                        f"{t['uv']}</b> -- the UV pass is what finds their targets. "
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
            hint = {"first": pick_first, "last": pick_last}.get(
                mode, "<b>Nothing selected.</b><br>Select the target mesh(es)."
            )
            return None, targets, None, hint + source_note
        pairs, error = self.pair(targets, source, do_uvs)
        return pairs, targets, None, (error + auto_note if error else None)

    def lightmap_probe(self):
        if not self.ui.chk_tt_lightmaps.isChecked():
            return None
        records = self.tk.LightmapRecords
        return lambda mesh: records.baked_objects([mesh])

    # ------------------------------------------------------------ enablement
    def sync(self) -> None:
        """Grey every row the current Source / Transfer pair makes meaningless."""
        ui = self.ui
        source, transfer = (
            getattr(ui, "cmb_tt_source", None),
            getattr(ui, "cmb_tt_transfer", None),
        )
        if source is None or transfer is None:
            return
        mode = source.currentData() or self.SOURCE_AUTO
        same_mesh = mode == "uvset"
        index = transfer.findData(self.TRANSFER_TEXTURES)
        if same_mesh and index >= 0 and transfer.currentIndex() != index:
            transfer.setCurrentIndex(index)  # re-enters sync; harmless
        transfer.setEnabled(not same_mesh)
        uvs, textures = self.passes(mode, transfer.currentData())
        stored = bool(self.sources)
        for action in (self.select_action, self.clear_action):
            if action is not None:
                action.widget.setEnabled(stored)
        scope = ui.cmb_tt_targets
        scope.setEnabled(mode == "first")
        if self.similarity is not None:
            self.similarity.setEnabled(
                mode == "first" and uvs and (scope.currentData() or "order") != "order"
            )
        for name in (
            "t_tt_src_uvset",
            "t_tt_dst_uvset",
            "cmb_tt_resolution",
            "chk_assign",
        ):
            getattr(ui, name).setEnabled(textures)
        ui.chk_tt_lightmaps.setEnabled(textures and not same_mesh)
        self.slots.sync_shared(textures=textures)

    # ------------------------------------------------------------ run
    def run(self) -> None:
        """Transfer UVs OR textures -- one pass per run, one undo step."""
        with self.tk.CoreUtils.undo_chunk("Texture Transfer"):
            self._run()

    def _run(self) -> None:
        ui = self.ui
        transfers = self.tk.TextureTransfer
        requested = ui.cmb_tt_source.currentData() or self.SOURCE_AUTO
        scope = ui.cmb_tt_targets.currentData() or "order"
        # The host's reading of the selection: Maya's order, Blender's active
        # object; Auto resolved there too.
        mode, source, targets = transfers.selection_sides(requested, self.sources)
        source_note = ""
        if requested == self.SOURCE_AUTO:
            scope = "order"  # Auto's First reads Rest of Selection
            source_note = self.source_note(mode)

        transfer_mode = ui.cmb_tt_transfer.currentData()
        auto = transfer_mode == self.TRANSFER_AUTO
        probe = self.lightmap_probe()
        if auto and mode != "uvset":
            transfer_mode = self.resolve_auto(source or [], has_lightmap=probe)
        do_uvs, do_textures = self.passes(mode, transfer_mode)
        auto_note = self.auto_note(auto, do_textures, mode, lightmaps=probe is not None)
        pairs, targets, others, refusal = self.gate(
            mode,
            scope,
            source,
            targets,
            do_uvs,
            do_textures,
            notes=(auto_note + source_note, source_note),
        )
        if refusal:
            return self.sb.message_box(refusal)

        uv = self.terms["uv"]
        uv_utils = self.tk.UvUtils
        report = []
        label = f"Working: Transfer {uv}" if do_uvs else "Working: Transfer Textures"
        with self.sb.progress(text=label) as tick:
            tick()
            if do_uvs:
                try:
                    if pairs is None:
                        targets = uv_utils.transfer_uvs_to_similar(
                            source[0],
                            others if scope == "selection" else None,
                            tolerance=self.similarity.value()
                            if self.similarity
                            else 0.9,
                        )
                        if not targets:
                            return self.sb.message_box(
                                "<b>No similar meshes found</b> within the "
                                "similarity threshold -- lower it, or note that "
                                f"the source's {self.terms['instances']} already "
                                "share its UVs."
                            )
                        results = [(source[0], t, "topology") for t in targets]
                    else:
                        # The pairing is already decided (selection / stored by
                        # name): re-vetting it by similarity could only drop a
                        # pair the user named.
                        results = (
                            uv_utils.transfer_uvs(
                                [s for s, _ in pairs],
                                [t for _, t in pairs],
                                match_by_similarity=False,
                            )
                            or []
                        )
                except ValueError as e:
                    return self.sb.message_box(f"<b>Transfer {uv}:</b><br>{e}")
                approximated = [r for r in results if r[2] != "topology"]
                report.append(
                    f"Transferred UVs to <b>{len(results)}</b> object(s)."
                    + (
                        f"<br><b>{len(approximated)}</b> did not match the source's "
                        "topology and were sampled by proximity -- check the result."
                        if approximated
                        else ""
                    )
                )
            if do_textures:
                tick(text="Working: Transfer Textures")
                report.append(self.texture_pass(targets, source))
        self.sb.message_box("<br><br>".join(report) + source_note)

    def derived_name(self, source, targets) -> str:
        """A blank Output Name: the source's common name (else the targets')."""
        nodes = list(source) if source else list(targets or [])
        return self.slots.engine.default_name(nodes, fallback="transfer")

    def texture_pass(self, targets, source) -> str:
        """The texture pass (and, with Include Lightmaps, the lightmap pass)."""
        ui = self.ui
        lines = []
        produced = False
        out_name = ui.t_name.text().strip()
        typed = bool(out_name)
        if not typed:
            out_name = self.derived_name(source, targets)
        named = out_name
        prefix, suffix = self.slots.material_affix()
        in_place = ui.chk_assign.isChecked() and self.slots.overwrites_target()
        before = self.read_files(targets) if in_place else set()
        engine = self.tk.TextureTransfer()
        # What Overwrite target leaves alone is said as a warning; the report
        # repeats it (the class's own ring buffer, read before it is dropped).
        left = engine.logger.enable_log_buffer(level="WARNING") if in_place else None
        try:
            results = engine.transfer(
                targets,
                source,
                source_uv_set=ui.t_tt_src_uvset.text().strip() or None,
                target_uv_set=ui.t_tt_dst_uvset.text().strip() or None,
                size=ui.cmb_tt_resolution.currentData() or None,
                supersample=ui.cmb_quality.currentData() or 2,
                padding=ui.s_padding.value(),
                output_name=out_name,
                output_dir=ui.t_output.text().strip() or None,
                assign=ui.chk_assign.isChecked(),
                assign_prefix=prefix,
                assign_suffix=suffix,
                **self.slots.assign_options(),
            )
        except ValueError as e:
            lines.append(f"<b>Transfer Textures:</b> {e}")
            results = None
        finally:
            warnings = [r.getMessage() for r in left.buffer] if left else []
            if left is not None:
                engine.logger.disable_log_buffer()
        if results is not None:
            n_maps = sum(len(v) for v in results.values())
            produced = bool(n_maps)
            folder = next(
                (os.path.dirname(p) for v in results.values() for p in v.values()), ""
            )
            lines.append(
                f"Transferred <b>{n_maps}</b> map(s) for <b>{len(results)}</b> "
                "material(s)"
                + (
                    f'<br><a href="action://open?path={folder}">{folder}</a>'
                    if folder
                    else ""
                )
            )
            if in_place:
                lines.append(self.overwrite_note(before, results, warnings))
            stems = {
                os.path.basename(p).rsplit("_", 1)[0]
                for v in results.values()
                for p in v.values()
            }
            # In place, a map keeps the name it had: no stem is the output's.
            if len(results) == 1 and len(stems) == 1 and not in_place:
                named = stems.pop()
        if source is not None and ui.chk_tt_lightmaps.isChecked():
            text, wrote = self.lightmap_pass(targets, source, named)
            lines.append(text)
            produced = produced or wrote
        if produced and not typed and not in_place:
            lines.append(
                f"Named <b>{named}</b> after the source -- type an <b>Output Name</b> "
                "to choose another."
            )
        elif produced and named != out_name and not in_place:
            lines.append(
                f"Named <b>{named}</b>: <b>{out_name}</b> is held outside this run "
                "(another object's material, or a map one reads)."
            )
        if produced and typed:
            self.slots.record_name(out_name)
        return "<br><br>".join(lines)

    @staticmethod
    def _path_key(path: str) -> str:
        """*path* as the filesystem compares it."""
        return os.path.normcase(os.path.abspath(path))

    def read_files(self, targets) -> set:
        """Path keys of the maps the materials *targets* wear read now."""
        transfers = self.tk.TextureTransfer
        return {
            self._path_key(path)
            for target in targets or ()
            for mat in transfers.face_materials(target)[0]
            for path in transfers.material_maps(mat).values()
        }

    @classmethod
    def overwrite_note(cls, before, results, warnings) -> str:
        """Overwrite target's report: the files rewritten where they are (the
        targets' materials read them before the run), the new ones they read
        now, and the run's warnings (what was left alone, and why)."""
        written = [p for maps in results.values() for p in maps.values()]
        over = [p for p in written if cls._path_key(p) in before]
        text = (
            f"Overwrote <b>{len(over)}</b> file(s) in place: "
            + ", ".join(os.path.basename(p) for p in over)
            if over
            else "No file was overwritten in place."
        )
        if len(written) > len(over):
            text += (
                f"<br>Wrote <b>{len(written) - len(over)}</b> new file(s) the "
                "targets' own materials now read."
            )
        if warnings:
            shown = warnings[: cls.NOTE_LIMIT]
            more = len(warnings) - len(shown)
            text += "<br>Warnings:<br>" + "<br>".join(
                f"&bull; {html.escape(w)}" for w in shown
            )
            if more:
                text += f"<br>... and {more} more (the log)."
        return text

    def lightmap_pass(self, targets, source, out_name) -> Tuple[str, bool]:
        ui = self.ui
        try:
            results = self.tk.LightmapRecords.transfer_lightmaps(
                targets,
                source,
                output_dir=ui.t_output.text().strip() or None,
                output_name=out_name,
                supersample=ui.cmb_quality.currentData() or 2,
                padding=ui.s_padding.value(),
            )
        except ValueError as e:
            return f"<b>Transfer Lightmaps:</b> {e}", False
        if not results:
            return (
                "<b>No lightmaps transferred</b> -- no source carries a committed "
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
        # The maps' home: a resampled map waits in the session until the scene
        # is saved (``ptk.PendingFiles``); the folder it goes to is the link.
        folder = (
            ptk.FileUtils.format_path(
                os.path.dirname(ptk.PendingFiles.session().home(resampled[0]))
            )
            if resampled
            else ""
        )
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
