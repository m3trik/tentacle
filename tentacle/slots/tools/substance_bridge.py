# !/usr/bin/python
# coding=utf-8
"""Substance Bridge: send the selection to Substance Painter through a template.

One Slots class for both hosts, on the bridge panels' shared base
(:class:`HostBridge`: parameter rows, presets, log pane, Output Dir row, Scope and
the Bake Source row). The engine is the host toolkit's ``SubstanceBridge``
(``self.tk.SubstanceBridge``): it exports the selection, stages its textures and
hands off to Painter (a launch line, plus RPC ops over the ``substance_rpc``
plugin). Its parameter registry, template folder, ``(template, mode)`` list and
template metadata are the engine's. This module owns the help text, the
preferred template, the Output Dir row's clear button, the Texture Affix row's
greying and the ``b000`` send.
"""

import traceback

import pythontk as ptk

from ._app_bridge.host_bridge import HostBridge


class SubstanceBridgeSlots(HostBridge):
    UI_NAME = "substance_bridge"
    LOG_TAG = "substance_bridge"
    # A blank field is never filled in by the panel, in either mode: the
    # bridge puts the mesh Painter's project is built from (and a reimport
    # overwrites) in the scene project's cache/substance, and the manifest +
    # staged texture copies in a fresh temp folder per send. A panel-made
    # session temp folder was deleted when the host exited, while the Painter
    # project still pointed into it.
    TRANSIENT_OUTPUT_MODES = (ptk.SEND_TO, ptk.ROUND_TRIP)

    # The Output Dir is a per-run hand-off location, not durable config: leaving
    # it blank leaves the destinations to the bridge (above), which is right
    # far more often than whatever was typed in some earlier session. A
    # restored path silently outranks that per-run default, so the field starts
    # blank each session -- the recent-values button still holds the history.
    OUTPUT_DIR_PERSISTS = False

    HELP_SPEC = {
        "title": "Substance Bridge",
        "body": "Send the selected objects to Substance Painter. The selection "
        "is exported (FBX, or USD per <b>Format</b>); the template's metadata "
        "constants (<i>BRIDGE_MODES</i>, <i>LAUNCH_ARGS</i>, <i>RPC_SCRIPT</i>, "
        "<i>BUILD_MANIFEST</i>, <i>FBX_OPTIONS</i>) drive the launch "
        "line and optional RPC step.",
        "steps": [
            "Set the <b>Output Dir</b> (or leave it blank: the mesh goes to "
            "the scene project's cache/substance, the rest to a temp folder "
            "per send).",
            "Select one or more mesh objects.",
            "Pick a <b>Template + Mode</b> from the dropdown.",
            "Tweak the template's exposed parameters.",
            "Click <b>Send to Painter</b>.",
        ],
        "sections": [
            (
                "Modes",
                [
                    "<b>send_to</b> — launches Painter for interactive work.",
                    "<b>roundtrip</b> — launches Painter with remote "
                    "scripting, sends the template's JS body via "
                    "JSON-RPC, and waits for completion.",
                ],
            ),
        ],
        "notes": [
            "<b>reimport</b> overwrites the FBX from the last send and "
            "reloads it in the already-running Painter (never launches a "
            "new one). Needs the <i>substance_rpc</i> Painter plugin, "
            "installed automatically on send. <b>First-run:</b> activate "
            "it once in Painter — <i>Python > Reload Plugins Folder</i> "
            "(or relaunch Painter), then tick <i>substance_rpc</i> in the "
            "<i>Python</i> menu (Painter remembers it). Without a reachable "
            "Painter the log shows the manual reload steps.",
            "<b>Bake Source</b> — define the set once with <b>Set From "
            "Selection</b> and every send ships it as a companion "
            "<i>&lt;name&gt;_source.fbx</i>, set as Painter's <i>Hipoly "
            "Mesh</i> in the baking options. The set's contents ARE the "
            "switch: no set, nothing shipped. It lives in the scene (Maya: an "
            "objectSet; Blender: a collection), so it survives saves and "
            "restarts and is independent of the <b>Scope</b>. Hidden geometry "
            "needs no preparation: FBX carries it verbatim, so the export "
            "never touches your scene. The row's icon buttons <i>select</i> "
            "the set's members or <i>clear</i> it.",
            "<b>Map Resolution</b> and the bake source have no Painter "
            "command line any more, so they travel over the "
            "<i>substance_rpc</i> plugin. On a project that is already open "
            "they apply at once; on a fresh launch the plugin holds them "
            "and applies them the moment the New Project wizard finishes — "
            "so the first send after Painter starts waits briefly for the "
            "plugin's endpoint.",
            "Add custom templates by dropping new files into the "
            "templates folder (use <code>__KEY__</code> tokens from "
            "<i>parameters.py</i> for tunable values), then use <b>Refresh "
            "Templates</b> on the template dropdown's menu.",
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self._wire_texture_affix_dependency()

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        return self.tk.SubstanceBridge

    def select_initial_template_index(self, pairs):
        """Default the panel to ``import (send_to)`` when it is available."""
        pref = ("import", ptk.SEND_TO)
        return pairs.index(pref) if pref in pairs else 0

    # -------------------------------------------------------------- output dir
    def _configure_output_dir_options(self, edit) -> None:
        """Base buttons (recent history + browse) plus a clear button.

        Blank is a *meaningful* state for this field -- ``require_output_dir``
        reads it as "the bridge decides" (the project cache for the mesh, temp
        for the rest) -- so unlike a browse-only path field the clear button
        reaches a real setting rather than just breaking the value. Pairs with
        ``OUTPUT_DIR_PERSISTS = False``: clearing it is how the user gets back
        to the per-run default within a session, and the next session starts
        there anyway.
        """
        super()._configure_output_dir_options(edit)
        edit.option_box.clear_option = True

    # ----------------------------------------------------------- texture affix
    #: Why ``Texture Affix`` greys out: one string, not one per call site.
    _AFFIX_DISABLED_REASON = (
        "Only applies to textures the send stages — turn <b>Include Textures</b> on."
    )

    def _wire_texture_affix_dependency(self) -> None:
        """Grey out ``Texture Affix`` while ``Include Textures`` is off.

        The affix only renames files the staging step copies, so it means
        nothing with staging off. Routed through ``set_param_enabled`` rather
        than the widget's own ``setEnabled``: the affix row is a text field
        WRAPPED in an option box, so disabling the field alone leaves its two
        icon buttons (the mode cycle, the clear) live beside a greyed-out
        value -- and gives the row no reason for the state. The base walks the
        row instead, which covers the whole cell.

        Either row is skipped when the registry does not build it, so a panel
        over a registry without them stays usable.
        """
        include_widget = self._param_widgets.get("PAINTER_INCLUDE_TEXTURES")
        if include_widget is None or "PAINTER_TEXTURE_AFFIX" not in self._param_widgets:
            return
        kinds = self.sb.KindFactory

        def _sync(_value=None):
            enabled = bool(kinds.read_value(include_widget))
            self.set_param_enabled(
                "PAINTER_TEXTURE_AFFIX",
                enabled,
                "" if enabled else self._AFFIX_DISABLED_REASON,
            )

        kinds.connect_changed(include_widget, _sync)
        _sync()

    # ------------------------------------------------------------- b000: send
    def b000(self):
        """Send the Scope's objects with the chosen template + mode."""
        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No template chosen. Pick one from the dropdown above."
            )
            return
        template, mode = pair

        # A template that exports no FBX (``render``) works on the project
        # already open in Painter: no selection needed, and no warning for its
        # absence.
        meta = self.bridge_class.parse_template(self.template_dir / f"{template}.py")
        needs_selection = meta.get("EXPORT_FBX", True)
        params = self.collect_param_values()
        selection = self.scoped_objects(params, warn=needs_selection)
        if needs_selection and not selection:
            return

        if not self.bridge.painter_path:
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
            with self.sb.progress(text=f"Working: Substance {template} ({mode})"):
                self.bridge.send(
                    objects=selection,
                    template=template,
                    mode=mode,
                    output_dir=output_dir,
                    params=params,
                )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
