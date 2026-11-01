# !/usr/bin/python
# coding=utf-8
"""The Texture Combine panel's Transfer mode: UVs or textures, source -> targets.

One tool, two transfers that are ALTERNATIVES -- the source's UV layout onto
the targets, or its textures re-mapped into each target's own layout; *Auto*
defers the pick to run time. The run and every decision in it are the
library's: the host's ``TextureTransfer.run`` (``ptk.TransferRun`` over the
host) takes the rows as plain values and returns a ``ptk.TransferResult``,
which this mode words. Which selected mesh is the source is the host's
convention (Maya: the selection order; Blender: the active object), worded by
its ``TextureTransfer.TERMS``.

:class:`TransferMode` is composed by
:class:`~tentacle.slots.tools.texture_combine.TextureCombineSlots` (which owns
the widgets' slot names and the shared Output / Material rows) -- a
controller, not a mixin.
"""

import html
import os

import pythontk as ptk


class TransferMode:
    """Transfer mode's widgets, and the words for its run's result."""

    TRANSFER_AUTO = ptk.TransferRun.AUTO
    TRANSFER_TEXTURES = ptk.TransferRun.TEXTURES
    TRANSFER_UVS = ptk.TransferRun.UVS
    SOURCE_AUTO = ptk.TransferRun.AUTO
    #: Overwrite target's report lists this many of what it left alone; the
    #: host's log has the rest.
    NOTE_LIMIT = 6
    #: Each pass's progress label (``{uv}``: the host's word for a UV channel).
    STAGES = {
        "uvs": "Working: Transfer {uv}",
        "textures": "Working: Transfer Textures",
    }

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
        uvs, textures = ptk.TransferRun.passes(mode, transfer.currentData())
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
        """Transfer UVs OR textures: the host's ``TextureTransfer.run`` (one
        pass per run, one undo step) over the rows, its result worded here."""
        ui = self.ui
        slots = self.slots
        prefix, suffix = slots.material_affix()
        uv = self.terms["uv"]
        with self.sb.progress(text="Working: Transfer") as tick:
            result = self.tk.TextureTransfer.run(
                source=ui.cmb_tt_source.currentData() or self.SOURCE_AUTO,
                transfer=ui.cmb_tt_transfer.currentData(),
                scope=ui.cmb_tt_targets.currentData() or "order",
                stored=list(self.sources),
                similarity=self.similarity.value() if self.similarity else 0.9,
                lightmaps=ui.chk_tt_lightmaps.isChecked(),
                output_name=ui.t_name.text().strip(),
                output_dir=ui.t_output.text().strip() or None,
                source_uv_set=ui.t_tt_src_uvset.text().strip() or None,
                target_uv_set=ui.t_tt_dst_uvset.text().strip() or None,
                size=ui.cmb_tt_resolution.currentData() or None,
                supersample=ui.cmb_quality.currentData() or 2,
                padding=ui.s_padding.value(),
                assign=ui.chk_assign.isChecked(),
                assign_prefix=prefix,
                assign_suffix=suffix,
                progress=lambda stage: tick(text=self.STAGES[stage].format(uv=uv)),
                **slots.assign_options(),
            )
        if result.produced and result.typed:
            slots.record_name(result.output_name)
        self.sb.message_box(self.report(result))

    # ------------------------------------------------------------ the result, worded
    def report(self, result) -> str:
        """What a run's *result* (``ptk.TransferResult``) says: why it
        stopped, or what each pass did -- with how Auto read the selection."""
        source_note = self.source_note(result.mode) if result.source_auto else ""
        if result.refusal:
            auto_note = self.auto_note(
                result.transfer_auto,
                result.do_textures,
                result.mode,
                lightmaps=result.lightmaps,
            )
            return self.refusal_text(result, auto_note, source_note)
        lines = []
        if result.do_uvs:
            lines.append(self.uv_note(result))
        if result.do_textures:
            lines.append(self.texture_note(result))
        return "<br><br>".join(lines) + source_note

    def refusal_text(self, result, auto_note="", source_note="") -> str:
        """Why the run stopped (``result.refusal``), in the host's words."""
        t = self.terms
        uv = t["uv"]
        pick_first = f"<b>{t['pick_first']}</b>"
        pick_last = f"<b>{t['pick_last']}</b>"
        both = auto_note + source_note
        text, note = {
            "nothing_to_transfer": (
                f"<b>Nothing to transfer.</b><br>The <i>{uv}s On Same Mesh</i> "
                "source transfers textures -- pick a <b>Transfer</b> mode that "
                "includes them.",
                source_note,
            ),
            "nothing_selected": (
                "<b>Nothing selected.</b><br>Select the mesh(es) to transfer on.",
                source_note,
            ),
            "no_targets": (
                "<b>Nothing selected.</b><br>Select the target mesh(es).",
                source_note,
            ),
            "pick_first": (pick_first, source_note),
            "pick_last": (pick_last, source_note),
            "similar_needs_uvs": (
                "<b>The Similar scopes need a Transfer mode that includes "
                f"{uv}</b> -- the UV pass is what finds their targets. Use Rest "
                "of Selection to transfer textures alone.",
                both,
            ),
            "no_stored": (
                "<b>No stored source meshes.</b><br>Store them with the <b>+</b> "
                "icon on the Source row first.",
                "",
            ),
            "pair_error": (f"<b>Transfer:</b><br>{result.error}", both),
            "one_source_per_target": (
                "<b>The UV pass copies one source per target.</b><br>The target "
                "was combined from several sources, so only their textures can "
                "travel -- pick <b>Transfer: Textures</b>.",
                both,
            ),
            "no_similar": (
                "<b>No similar meshes found</b> within the similarity threshold "
                f"-- lower it, or note that the source's {t['instances']} "
                "already share its UVs.",
                "",
            ),
            "uv_error": (f"<b>Transfer {uv}:</b><br>{result.error}", ""),
        }[result.refusal]
        return text + note

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

    @staticmethod
    def uv_note(result) -> str:
        """The UV pass: how many it reached, and the ones sampled by proximity."""
        approximated = [r for r in result.uvs if r[2] != "topology"]
        return f"Transferred UVs to <b>{len(result.uvs)}</b> object(s)." + (
            f"<br><b>{len(approximated)}</b> did not match the source's topology "
            "and were sampled by proximity -- check the result."
            if approximated
            else ""
        )

    @staticmethod
    def _folder_link(folder: str) -> str:
        return (
            f'<br><a href="action://open?path={folder}">{folder}</a>' if folder else ""
        )

    def texture_note(self, result) -> str:
        """The texture pass (and, with Include Lightmaps, the lightmap pass)."""
        lines = []
        if result.texture_error:
            lines.append(f"<b>Transfer Textures:</b> {result.texture_error}")
        if result.maps is not None:
            lines.append(
                f"Transferred <b>{result.map_count}</b> map(s) for "
                f"<b>{len(result.maps)}</b> material(s)"
                + self._folder_link(result.maps_folder)
            )
            if result.in_place:
                lines.append(self.overwrite_note(result))
        if result.lightmap_results is not None or result.lightmap_error:
            lines.append(self.lightmap_note(result))
        named, out_name = result.named, result.output_name
        if result.produced and not result.typed and not result.in_place:
            lines.append(
                f"Named <b>{named}</b> after the source -- type an <b>Output Name</b> "
                "to choose another."
            )
        elif result.produced and named != out_name and not result.in_place:
            lines.append(
                f"Named <b>{named}</b>: <b>{out_name}</b> is held outside this run "
                "(another object's material, or a map one reads)."
            )
        return "<br><br>".join(lines)

    @classmethod
    def overwrite_note(cls, result) -> str:
        """Overwrite target's report: the files rewritten where they are (the
        targets' materials read them before the run), the new ones they read
        now, and the run's warnings (what was left alone, and why)."""
        over, added, warnings = result.overwritten, result.added, result.warnings
        text = (
            f"Overwrote <b>{len(over)}</b> file(s) in place: "
            + ", ".join(os.path.basename(p) for p in over)
            if over
            else "No file was overwritten in place."
        )
        if added:
            text += (
                f"<br>Wrote <b>{len(added)}</b> new file(s) the targets' own "
                "materials now read."
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

    def lightmap_note(self, result) -> str:
        """The lightmap pass: bound to the source's map, or resampled (and
        where the resampled maps go once the scene is saved)."""
        if result.lightmap_error:
            return f"<b>Transfer Lightmaps:</b> {result.lightmap_error}"
        transferred = result.lightmap_results
        if not transferred:
            return (
                "<b>No lightmaps transferred</b> -- no source carries a committed "
                "lightmap, or its map or lightmap UVs are gone (see the log)."
            )
        resampled = result.resampled
        rebound = len(transferred) - len(resampled)
        parts = []
        if rebound:
            parts.append(f"<b>{rebound}</b> bound to the source's own map")
        if resampled:
            parts.append(f"<b>{len(resampled)}</b> resampled into the target's layout")
        return (
            f"Transferred lightmaps to <b>{len(transferred)}</b> object(s): "
            + ", ".join(parts)
            + "."
            + self._folder_link(result.lightmap_folder)
        )
