# !/usr/bin/python
# coding=utf-8
"""Marmoset Bridge: send the selection to Marmoset Toolbag through a template.

One Slots class for both hosts, on the bridge panels' shared base
(:class:`HostBridge`: parameter rows, presets, log pane, Output Dir row, Scope and
the Bake Source row). The engine is the host toolkit's ``MarmosetBridge``
(``self.tk.MarmosetBridge``): it exports the selection with a material manifest
and a bake-pairs sidecar, renders the chosen Toolbag template and launches or
round-trips Toolbag. Its parameter registry, template folder and
``(template, mode)`` list are the engine's. This module owns the help text, the
preferred template, the suffix rows' live greying and the ``b000`` send.
"""

import traceback

import pythontk as ptk

from tentacle import Slots

from ._app_bridge.host_bridge import HostBridge


class MarmosetBridgeSlots(HostBridge):
    UI_NAME = "marmoset_bridge"
    LOG_TAG = "marmoset_bridge"
    # A blank field is never filled in by the panel: every mode's hand-off
    # artifacts (FBX, manifests, rendered script) are intermediates, so the
    # bridge stages them in a fresh temp folder per send -- removed when a
    # roundtrip succeeds, aged out after a send_to's detached Toolbag has read
    # them -- and puts what is kept in the scene's project (the maps in
    # sourceimages/baked, a roundtrip's .tbscene in data/marmoset). A folder
    # named here still wins -- and is still kept.
    TRANSIENT_OUTPUT_MODES = (ptk.SEND_TO, ptk.ROUND_TRIP)

    # The base tooltip promises the baked maps land in this folder too. For a
    # bake roundtrip they deliberately do not: they are production textures and
    # go to the project's own texture folder (``MarmosetBridge.baked_texture_dir``),
    # so a later export never has to copy them in and rename each one around a
    # collision with the source maps that fed the bake.
    OUTPUT_DIR_TOOLTIP = (
        "Directory where the hand-off artifacts (FBX, material manifest,\n"
        "rendered script, saved .tbscene) land.\n\n"
        "Leave blank and they go to a temp folder per send: removed when a\n"
        "bake ROUNDTRIP succeeds, aged out after a Send To's Toolbag has\n"
        "read them. A roundtrip's saved .tbscene goes to the scene project's\n"
        "data/marmoset. Name a folder here and every artifact stays in it.\n\n"
        "A bake roundtrip's TEXTURE MAPS do NOT land here — they go to a\n"
        "baked/ folder in the project's texture folder (sourceimages/baked),\n"
        "where the scene references its textures from, so no later pass\n"
        "copies or renames them."
    )

    HELP_SPEC = {
        "title": "Marmoset Bridge",
        "body": "Send the selected objects to Marmoset Toolbag. The selection is "
        "exported (FBX, or USD per <b>Format</b>) with a <i>MatManifest</i> JSON "
        "sidecar; Toolbag runs the rendered template with your parameter values "
        "substituted in.",
        "steps": [
            "Set the <b>Output Dir</b> (or leave it blank: the hand-off "
            "goes to a temp folder per send).",
            "Select one or more mesh objects.",
            "Pick a <b>Template + Mode</b> from the dropdown.",
            "Tweak the template's exposed parameters.",
            "Click <b>Send to Marmoset</b>.",
        ],
        "sections": [
            (
                "Modes",
                [
                    "<b>send_to</b> — opens Toolbag for interactive work.",
                    "<b>roundtrip</b> — runs Toolbag headless, then "
                    "re-surfaces generated maps as clickable links in the "
                    "log panel below. Only a bake with <b>Assign Material</b> "
                    "on changes the scene (see below).",
                    "A roundtrip runs Toolbag hidden: <b>hold Esc</b> to "
                    "cancel one, or tick <b>Show App Window</b> to see (and "
                    "answer) a dialog it stops on.",
                ],
            ),
        ],
        "notes": [
            "For the <b>bake</b> template: select the bake <i>source</i> "
            "geometry once and use the <b>Bake Source</b> row's <b>Set From "
            "Selection</b> (the set saves with the scene and is shared "
            "with the Substance bridge). Then select the bake <i>target</i> "
            "meshes and Send -- the source rides along automatically, hidden "
            "or not, and pairs explicitly, no name suffixes required. The "
            "Suffix rows grey out while the set exists; clear it to fall back "
            "to naming (with <b>Include Children</b> on, one suffixed group "
            "tags every mesh under it).",
            "A <b>bake (roundtrip)</b> with <b>Assign Material</b> on wires "
            "the baked maps into one material per texture set — restoring the "
            "source's packed-map layout — and assigns it to the bake-target "
            "meshes where the source material was (Maya keeps the shader type "
            "the meshes wore). Re-baking <i>replaces</i> that material and its "
            "maps rather than stacking a new one beside it.",
            "Edge padding and bit depth are managed automatically: padding "
            "derives from the map size, bit depth from the per-map output "
            "templates.",
            "Add custom templates by dropping new files into the "
            "templates folder (use <code>__KEY__</code> tokens from "
            "<i>parameters.py</i> for tunable values), then use <b>Refresh "
            "Templates</b> on the template dropdown's menu.",
        ],
    }

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        return self.tk.MarmosetBridge

    def select_initial_template_index(self, pairs):
        """Prefer 'bake (roundtrip)' then 'bake (send_to)', else the first entry."""
        for pref in (("bake", ptk.ROUND_TRIP), ("bake", ptk.SEND_TO)):
            if pref in pairs:
                return pairs.index(pref)
        return 0

    # ------------------------------------------------------------- bake source
    # The Bake Source row's actions are the base's; this bridge says what the
    # set means for ITS send: only a bake reads it, and it retires the suffix
    # fallback while it exists.
    BAKE_SOURCE_DEFINED_NOTE = (
        "Bake sends now export it as the bake source "
        "(the Source/Target Suffix fallback is inactive while it exists)."
    )
    BAKE_SOURCE_CLEARED_NOTE = (
        "Pairing falls back to the Source/Target Suffix convention."
    )

    #: Rows that apply only while the scene has NO Bake Source set -- the
    #: name-suffix pairing fallback. An explicit set classifies both sides
    #: outright, so these grey while one exists rather than sitting there
    #: implying they still steer the bake.
    SUFFIX_FALLBACK_KEYS = ("HIGH_SUFFIX", "LOW_SUFFIX", "SUFFIX_INCLUDE_CHILDREN")

    _SUFFIX_DISABLED_REASON = (
        "Inactive: this scene has a Bake Source set, which pairs the two "
        "sides explicitly.\nThe name-suffix fallback applies only without "
        "one -- use the Bake Source row's Clear to fall back to it."
    )

    def _refresh_param_enablement(self) -> None:
        """Grey the suffix-fallback rows while a Bake Source set exists.

        The registry's own supersessions (Auto Maps / Auto cage) are applied by
        the base; this adds the one that keys off LIVE scene state.
        """
        super()._refresh_param_enablement()
        has_set = self._bake_source_defined()
        for key in self.SUFFIX_FALLBACK_KEYS:
            self.set_param_enabled(
                key, not has_set, self._SUFFIX_DISABLED_REASON if has_set else ""
            )

    def _bake_source_defined(self) -> bool:
        """Whether the scene has a Bake Source set.

        Runs while the panel is built (and on every show), so a host library
        loaded without its host -- blendertk outside Blender, no ``bpy`` -- reads
        as no set rather than taking the panel down.
        """
        try:
            return bool(self.tk.BakeSourceSet.exists())
        except ImportError:
            return False

    # ------------------------------------------------------------- b000: send
    # Inside the dispatcher's CancelScope: a roundtrip's hidden Toolbag polls
    # it, so holding Esc (or the long-run dialog's Cancel) ends a bake stuck on
    # a dialog no one can see.
    @Slots.Cancelable(300, message="Marmoset Toolbag run")
    def b000(self):
        """Send the Scope's objects with the chosen template + mode."""
        # Scope (Selected / Entire Scene / Visible Only) resolves via the
        # bridge base; it logs the scope-aware reason when empty.
        params = self.collect_param_values()
        selection = self.scoped_objects(params)
        if not selection:
            return

        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No template chosen. Pick one from the dropdown above."
            )
            return
        template, mode = pair

        if not self.bridge.toolbag_path:
            # The spec's sentence, not a panel-local copy: the engine's ``APP``
            # owns it, and the menu gate that greys this tool's entry shows
            # the same one.
            self.bridge.logger.error(self.bridge.APP.not_found_message)
            return

        output_dir = self.require_output_dir(mode)
        if output_dir is None:
            return

        # The log accumulates across runs (the header menu's Clear Log resets
        # it); this line separates one operation from the next.
        self.bridge.logger.info(
            f"--- {template} ({mode}) on {len(selection)} object(s) ---"
        )
        try:
            with self.sb.progress(text=f"Working: Marmoset {template} ({mode})"):
                self.bridge.send(
                    objects=selection,
                    template=template,
                    mode=mode,
                    output_dir=output_dir,
                    params=params,
                )
        except Exception:
            # The whole traceback in the log pane, so diagnosing needs no
            # trip to the host's script console.
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
