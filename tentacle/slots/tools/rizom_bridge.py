# !/usr/bin/python
# coding=utf-8
"""RizomUV Bridge: unwrap or pack the selection in RizomUV with a Lua preset and
bring the UVs back, or open it in RizomUV one way.

One Slots class for both hosts, on the bridge panels' shared base
(:class:`HostBridge`: parameter rows, presets, log pane, Scope). The engine is the
host toolkit's ``RizomUVBridge`` (``self.tk.RizomUVBridge``), and everything a
preset means is the engine's: the preset folder (``SCRIPT_DIR``), the presets the
installed RizomUV can run (``list_template_modes``), the knobs a preset exposes
there (``referenced_keys``) and what Process runs for it (``run_preset``: the
round trip, the one-way ``send``, or ``pack_into_existing``). This module owns the
panel: the help, the header menu and the ``b000`` hand-off.

``REQUIRE_OUTPUT_DIR = False``: a round trip goes through a temp FBX the engine
manages, so there is no artifact to point the panel at.
"""

import traceback

from tentacle import Slots

from ._app_bridge.host_bridge import HostBridge


class _InstalledParams:
    """The engine's parameter registry as the installed RizomUV runs it.

    The rows a preset shows are the keys ``RizomUVBridge.referenced_keys`` keeps:
    a knob gated above the installed version is stripped from the send, so it gets
    no row to dial. ``PARAMS`` and the rest are the registry's own.
    """

    def __init__(self, panel):
        self._panel = panel

    def referenced_keys(self, script_text: str):
        return self._panel.bridge.referenced_keys(script_text)

    def __getattr__(self, name):
        return getattr(self._panel.bridge_class.params_registry(), name)


class RizomBridgeSlots(HostBridge):
    UI_NAME = "rizom_bridge"
    LOG_TAG = "rizom_bridge"

    # The presets are Lua (``scripts/*.lua``): what the base scans for each
    # preset's ``__KEY__`` placeholders and reads its description from. The
    # user's saved parameter presets are JSON under ``PRESETS_ROOT``, unaffected.
    TEMPLATE_EXTENSION = ".lua"

    # A round trip goes through a temp FBX the engine manages: no Output Dir row.
    REQUIRE_OUTPUT_DIR = False

    # Rizom's labels are short ("Spacing", "Mutations"): a tighter label column
    # than the bridges' default (90px) hugs the values on a 220px-wide panel.
    LABEL_MIN_WIDTH = 80

    # The header menu adds a UV Editor shortcut and calls the templates
    # "Scripts"; the base builds it from this data.
    HEADER_MENU_ITEMS = (
        (
            "Open UV Editor",
            "btn_open_uv_editor",
            "Open the UV Editor to inspect the result.",
            "open_uv_editor",
        ),
        (
            "Open Scripts Folder",
            "btn_open_scripts",
            "Reveal the bundled Lua preset folder in the file manager.",
            "open_templates_folder",
        ),
        (
            "Refresh Scripts",
            "btn_refresh_scripts",
            "Re-scan the scripts folder and rebuild the script combo.",
            "refresh_templates",
        ),
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
    )

    HELP_SPEC = {
        "title": "RizomUV Bridge",
        "body": "Round-trip the selected meshes through RizomUV with a Lua preset, "
        "or send them one way and keep working in RizomUV.",
        "steps": [
            "Select one or more mesh objects.",
            "Pick a <b>Lua preset</b> from the dropdown.",
            "Tweak the parameters that the preset exposes.",
            "Click <b>Process Selected</b>.",
        ],
        "sections": [
            (
                "Presets",
                [
                    "<b>pack / unwrap_hard / unwrap_organic / unwrap_hybrid "
                    "/ optimize</b> — round trip: copies of the selection export "
                    "with an <code>__RZTMP</code> suffix, RizomUV runs the script "
                    "headlessly, and the UVs are transferred back onto the "
                    "originals. (unwrap_hybrid needs RizomUV 2022+.)",
                    "<b>send</b> — one way: exports the selection directly (no "
                    "rename), optionally collects the materials' textures, then "
                    "launches RizomUV detached. Save inside RizomUV when done.",
                    "<b>pack_into_existing</b> — packs the selection's shells into "
                    "the empty space of the layout shared by every mesh using the "
                    "selection's material(s), at that layout's texel density "
                    "(shrunk only if they don't fit); the existing shells don't "
                    "move.",
                ],
            ),
            (
                "Header menu",
                [
                    "<b>Open UV Editor</b> — open the UV Editor (Blender: in a new "
                    "window) to inspect the result.",
                    "<b>Open Scripts Folder</b> — reveal the bundled Lua preset "
                    "folder in the file manager.",
                    "<b>Refresh Scripts</b> — re-scan the scripts folder and "
                    "rebuild the script combo.",
                    "<b>Clear Log</b> — clear the log panel below.",
                ],
            ),
        ],
        "notes": [
            "<b>pack</b> and <b>pack_into_existing</b> honour a shell selection "
            "(Maya: faces or UVs; Blender: Edit Mode faces): only the shells it "
            "touches move (any part of a shell picks all of it), and every other "
            "shell stays exactly where it is and is packed around. The other "
            "presets work on whole objects.",
            "A round trip runs RizomUV hidden: <b>hold Esc</b> to cancel one, or "
            "tick <b>Show App Window</b> to see (and answer) a dialog it stops on.",
            "Add custom presets by dropping new <code>.lua</code> files into the "
            "scripts folder (use <code>__KEY__</code> tokens from "
            "<i>parameters.py</i> for tunable values), then click "
            "<b>Refresh Scripts</b>.",
            "RizomUV must be installed: it is found on PATH or under "
            "<code>Program Files\\Rizom Lab</code>.",
        ],
    }

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        return self.tk.RizomUVBridge

    @property
    def params_module(self):
        """The registry, its rows gated by the installed RizomUV's version."""
        return _InstalledParams(self)

    @property
    def template_dir(self):
        """The Lua presets (``RizomUVBridge.SCRIPT_DIR``): the panel's templates.

        Not the engine's ``templates/`` folder, which holds what a preset is
        spliced into (the run wrappers and the shared includes)."""
        return self.bridge_class.SCRIPT_DIR

    def list_template_modes(self):
        """``[(preset, ""), ...]``: the presets the installed RizomUV can run
        (a preset gated above its version is left out). One mode per preset, so
        the combo shows the bare stem."""
        return self.bridge.list_template_modes()

    # ------------------------------------------------------------- b000: run
    # Inside the dispatcher's CancelScope: a round trip's hidden RizomUV polls
    # it, so holding Esc (or the long-run dialog's Cancel) ends a run stuck on a
    # dialog no one can see.
    @Slots.Cancelable(120, message="RizomUV run")
    def b000(self):
        """Run the chosen preset: a round trip, or the one-way ``send``."""
        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No preset chosen. Pick a Lua preset from the dropdown above."
            )
            return
        preset, _mode = pair

        # The base logs the scope-aware reason when the Scope is empty.
        params = self.collect_param_values()
        selection = self.scoped_objects(params)
        if not selection:
            return

        if not self.bridge.rizom_path:
            # The engine's sentence: its ``APP`` owns it, and the launcher gate
            # that greys this tool's entry shows the same one.
            self.bridge.logger.error(self.bridge.APP.not_found_message)
            return

        try:
            with self.sb.progress(text=f"Working: RizomUV {preset}"):
                self.bridge.run_preset(selection, preset, params=params)
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())

    # ------------------------------------------------------------- header menu
    def open_uv_editor(self):
        """Open the host's UV Editor (Blender: in a new window, since it has no
        floating editors)."""
        if self.tk.UiUtils.open_editor("UV Editor") is None:
            self.bridge.logger.error("Could not open the UV Editor.")
