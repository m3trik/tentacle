# !/usr/bin/python
# coding=utf-8
"""Scene Exporter: batch-export the scene through its task/check pipeline.

One Slots class for both hosts over the host toolkit's ``SceneExporter``
(``self.tk``), built once per panel with this panel's logger and its two
dialogs (:meth:`SceneExporterSlots.confirm`,
:meth:`SceneExporterSlots.decide_check_failure`), so everything the run says
lands in the panel's log. The Settings / Tasks / Checks rows are registry
driven: each is a widget the host's task and check definitions describe
(``task_manager.task_definitions`` / ``check_definitions``), read back into
the run's configuration by ``pythontk.ExportProfile``. What a host does its own
way is its engine's: the object scope (``objects_to_export``), the FBX presets
(``presets``, ``fbx_preset_dir``, ``edit_fbx_preset``, their embedding in an
export preset) and the store export presets are saved in
(``EXPORT_PRESET_DIR``).
"""

import html
import os
from typing import Dict, List

import pythontk as ptk

from tentacle import Slots


class SceneExporterSlots(Slots, ptk.LoggingMixin):
    # Rows of the Settings combo (cmb008), by group. Names resolve to a UI-only
    # widget spec (``_SETTINGS_WIDGETS``) or to a ``task_definitions`` entry
    # tagged ``"panel": "settings"`` — a task the engine dispatches (or a flag
    # ``perform_export`` pops) that the USER experiences as a write/scope
    # setting rather than scene prep. Order here is display order; a name a
    # host's definitions lack (blendertk has no set_workspace) is skipped.
    _SETTINGS_LAYOUT = (
        (
            "Output",
            (
                "cmb000",
                "cmb004",
                "set_linear_unit",
                "set_workspace",
            ),
        ),
        (
            "Scope",
            (
                "export_visible_objects",
                "ignore_groups",
                "exclude_hdr",
                "drop_rig_apparatus",
                "export_data_node",
            ),
        ),
        # No Textures section: every texture dial — Texture Output included —
        # lives in the Tasks combo's Textures group, the gate row directly
        # above the three rows it governs (see task_definitions).
    )

    #: Settings rows with no task/check definition behind them. Each keeps the
    #: objectName it had as a main-layout / option-box widget so its ``_init``
    #: slot, ``b000``'s reads and every saved export preset stay valid.
    _SETTINGS_WIDGETS = {
        "cmb000": {
            "widget_type": "ComboBox",
            "set_row_label": "FBX Preset",
            "setToolTip": (
                "FBX export preset applied to the write — the FBX exporter's "
                "own options (units, axis, geometry, animation).\n"
                "It governs a GLB output too: the GLB is converted from this "
                "FBX write, so the preset's geometry/animation choices carry "
                "through.\n"
                "'None' writes without a preset (Maya: its current FBX "
                "settings; Blender: the game-ready baseline its 'game_asset' "
                "preset holds).\n"
                "The option box beside this row opens the preset folder "
                "or the selected preset for editing."
            ),
        },
        "cmb004": {
            "widget_type": "ComboBox",
            "set_row_label": "Format",
            "setToolTip": "Output file format: FBX, GLB, FBX + GLB, or USD.",
        },
    }

    #: The rows this panel builds at runtime and registers by objectName, and
    #: reads or initializes by name: the two UI-only Settings rows
    #: (``_SETTINGS_WIDGETS``), the Tasks row the Texture Template rides
    #: (``convert_textures``, saved as ``cmb005``) and the two Settings rows whose
    #: option boxes this panel fills. No ``.ui`` declares them; saved settings
    #: and export presets key on these names, so they never change.
    RUNTIME_WIDGETS = (
        "cmb000",
        "cmb004",
        "cmb005",
        "ignore_groups",
        "export_data_node",
    )

    #: Definition keys that describe the row, not the widget — stripped before
    #: the remainder is applied as widget attributes.
    _DEFINITION_META_KEYS = (
        "widget_type",
        "panel",
        "group",
        "object_name",
        "value_method",
    )

    #: Preset keys of the retired rows the Output Filename took over, with the
    #: spelling that replaces each: ``version`` the Version pattern, ``chk004``
    #: the Timestamp checkbox.
    _RETIRED_NAMING_KEYS: Dict[str, str] = {
        "version": "*_v{n:03d}",
        "chk004": "*_{date}_{time}",
    }

    #: The Ignore row's case toggle, set by :meth:`ignore_groups_init`. Held on
    #: the slots instance rather than re-resolved off the row each export: it
    #: is a plain Python object, so unlike a Qt wrapper it cannot be
    #: invalidated by the option box's reparent. ``None`` until that slot runs
    #: — :meth:`_ignore_groups_case_sensitive` then reports the task's own
    #: ``case_sensitive=False`` default.
    _case_toggle = None
    #: The Output Directory / Output Filename history options
    #: (:meth:`txt000_init` / :meth:`txt001_init`); ``None`` until they run.
    _recent_dirs_option = None
    _recent_names_option = None

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("INFO")
        self.ui = self.sb.loaded_ui.scene_exporter

        #: The host's engine. It logs through THIS panel's logger (its task
        #: manager is built with it, so every task's line reaches the log
        #: panel) and asks through this panel's dialogs; ``log_level=None``
        #: leaves the panel's level alone.
        self.exporter = self.tk.SceneExporter(
            log_level=None,
            logger=self.logger,
            confirm=self.confirm,
            decide_check_failure=self.decide_check_failure,
        )

        self.ui.txt001.setText("")  # Output Name
        self.ui.txt003.setText("")  # Log Output

        self._wire_dependencies()

        self._init_override_button(self.ui.b009)

        self.logger.hide_logger_name(True)  # Hide the logger name in output
        self.logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        self.logger.setup_logging_redirect(self.ui.txt003)

        # Connect clickable log links (action:// URIs in QTextBrowser)
        if hasattr(self.ui.txt003, "anchorClicked"):
            self.ui.txt003.anchorClicked.connect(self._on_log_link_clicked)

        # What the saved state asked of a row since retired, said once (the
        # restore skips a key no widget takes; a preset pick says the same
        # through _warn_retired_naming_keys).
        self.exporter.note_retired_panel_state(self.ui.settings)
        # A saved RegEx field (retired) folds into the Output Filename's SAVED
        # pattern here, before the switchboard restores the field over it.
        out_name = self.ui.txt001
        self.exporter.migrate_legacy_regex(
            self.ui.settings,
            out_name.objectName(),
            lambda pattern: self.ui.state.save(out_name, pattern),
        )

    @staticmethod
    def _init_override_button(widget) -> None:
        """Arm-once styling for the Override Checks toggle.

        ``restore_state = False`` is the load-bearing line: a registered widget
        persists through QSettings by default and its restore runs AFTER the
        slots ``__init__``, so the toggle used to come back armed in the next
        session -- right over the ``setChecked(False)`` here. A per-run escape
        hatch that survives a restart is a validation pass silently disabled.
        """
        widget.restore_state = False
        widget.setEnabled(True)
        widget.setChecked(False)
        widget.setStyleSheet("QPushButton:checked {background-color: #FF9999;}")

    def _wire_dependencies(self) -> None:
        """Hide a setting while a lower-level choice makes it irrelevant.

        One ``sb.show_when`` rule per dependency — declared once here, order-
        independent (the rows register later; the rule picks them up), and
        re-applied by the trigger's own change signal, so there is no per-
        trigger slot and no ``_sync_*`` helper to keep in step. A preset load
        applies with signals unblocked (``cmb007_init``), so these follow it
        too. Hidden rather than greyed (2026-09-14): a row that cannot apply
        to what was chosen is not a setting of this export, and the option
        menus read shorter and truer without it. A hidden row keeps its value
        (it still saves and restores); every one gated here is a mode the run
        resolves as off or ignores when its trigger says so.
        """
        sb, ui = self.sb, self.ui
        glb = {"glb", "fbx_glb"}
        # Texture File Type is the container dial for every texture the export
        # ships, so it is NOT gated on Optimize Textures: a GLB deliverable is
        # re-encoded to it whether or not the scene pass runs. The pass's size
        # ceiling needs no rule at all any more — it rides the Optimize
        # Textures combo itself ("Optimize + Max …"), so a ceiling with
        # nothing to apply it is unrepresentable rather than hidden.
        # Texture Output only matters once a texture-processing task runs —
        # Optimize Textures, or the conversion a Texture Template arms.
        sb.show_when(
            ui,
            "texture_write_back",
            ["texture_optimize", "cmb005"],
            lambda optimize, template: bool(optimize) or bool(template),
        )
        # Exclude HDR under the Visible scope: hidden where that scope can
        # hold nothing the exclusion strips (Maya's visible geometry is
        # surface shapes, never a skydome); kept where it can (Blender's
        # exclusion also strips a visible mesh dome). The engine says which.
        if not self.exporter.EXCLUDE_HDR_IN_VISIBLE_SCOPE:
            sb.show_when(
                ui,
                "exclude_hdr",
                "export_visible_objects",
                lambda scope: scope != "visible",
            )
        # A USD deliverable: the FBX preset, the takes and the bake range set
        # FBX flags only (the engine reports them inert), the verifier has no
        # FBX/GLB to open, and the rig-helper pass edits a written FBX (or sets
        # the deform-only write). A row a host lacks is simply never matched.
        sb.show_when(
            ui,
            "cmb000,animation_clips,bake_range,verify_deliverables,drop_rig_apparatus",
            "cmb004",
            lambda fmt: fmt != "usd",
        )
        # The GLB-only dials: nothing to apply them to without a GLB. KTX2 RDO
        # further needs the KTX2 container (ETC1S/UASTC are its encodes), and
        # the key tolerance is the GLB half of Optimize Keys.
        sb.show_when(ui, "secondary_max_size", "cmb004", glb)
        sb.show_when(
            ui,
            "uastc_rdo",
            ["cmb004", "texture_file_type"],
            lambda fmt, container: (
                fmt in glb and str(container or "").startswith("ktx2")
            ),
        )
        sb.show_when(
            ui,
            "glb_key_tolerance",
            ["cmb004", "optimize_level"],
            lambda fmt, level: fmt in glb and bool(level),
        )

    def confirm(self, question: str) -> bool:
        """The engine's consent seam as the panel's modal Yes/No.

        ``message_box`` takes HTML and hands it to Qt's rich-text engine, which
        collapses a newline to a space -- so the seam's plain text (documented
        as "newlines allowed") arrived as one run-on paragraph. Translate here,
        at the one place that knows the destination is a rich-text widget,
        rather than making every caller author HTML.
        """
        body = html.escape(question).replace("\n", "<br>")
        return self.sb.message_box(body, "Yes", "No") == "Yes"

    def decide_check_failure(
        self, check: str, messages: List[str], remaining: List[str]
    ) -> str:
        """The engine's check-failure seam as the panel's three-button dialog.

        Asked the moment *check* fails: the failure, what it reported and the
        checks still to run (the engine's ``check_failure_html``), over
        Override All / Override / Cancel. Enter is Cancel -- the answer that
        cannot ship a file past a check -- and so is Esc.
        """
        choices = self.exporter.CHECK_FAILURE_CHOICES
        answer = self.sb.message_box(
            self.exporter.check_failure_html(check, messages, remaining),
            *choices,
            default="Cancel",
            timeout=None,
        )
        return choices.get(answer, ptk.TaskFactory.CHECK_ABORT)

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the log panel.

        ``show?ui=<panel>`` opens a panel -- a note's remedy, such as the
        Shots window a stale-shot warning links (``TaskManager.NOTE_PANELS``);
        opening one takes the switchboard, which this panel holds and the
        shared dispatcher does not. Everything else goes to the host's
        ``UiUtils.dispatch_log_link``.
        """
        if url.scheme() == "action" and url.host() == "show":
            from urllib.parse import parse_qs

            panel = parse_qs(url.query()).get("ui", [""])[0]
            if panel:
                self.sb.handlers.marking_menu.show(panel)
            return
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    @property
    def workspace(self) -> str:
        """The current workspace's root (the dialogs' start folder); ``""``,
        said in the log, when there is none."""
        workspace_path = self.tk.EnvUtils.workspace_root()
        if not workspace_path:
            self.logger.error("No workspace directory found (save the scene first).")
        return workspace_path

    def header_init(self, widget):
        """Initialize the header widget (its help; the export preset lives in
        the panel as ``cmb007``). Logging takes no option: the panel shows the
        run at INFO and every export appends its full detail, down to DEBUG,
        to the scene's run log (``SceneExporter.log_file_path``), linked on
        the run's last line."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Scene Exporter",
                body="Batch-export scene objects to FBX, GLB or USD through "
                "configurable task pipelines and saved presets.",
                steps=[
                    "Pick an export <b>Preset</b> — the whole panel's "
                    "configuration under a name (Save / Rename / Delete from "
                    "its toolbar).",
                    "Adjust <b>Settings</b> (FBX preset, format, units, scope, "
                    "texture template), <b>Tasks</b> (scene prep) and "
                    "<b>Checks</b> (validation gates), and set the output path.",
                    "Press <b>Export</b> to run.",
                ],
                sections=[
                    (
                        "Log",
                        [
                            "The panel shows each run's progress; every export "
                            "also appends its full detail to the scene's own "
                            "log file (in your user cache, never beside the "
                            "FBX), linked at the run's end -- and a run that "
                            "ships a GLB ends with a link that opens it in the "
                            "WebXR preview.",
                        ],
                    ),
                ],
            )
        )

    def cmb000_init(self, widget) -> None:
        """Init FBX Preset — a Settings row (``cmb008``), created by
        :meth:`cmb008_init` and registered by objectName.

        Preset management (open the directory, edit the selection) lives in
        this row's own option box — the ☐ beside the combo — so it sits on the
        widget it configures, alongside a refresh button that re-scans the
        presets. The directory is fixed by the host (its engine's
        ``fbx_preset_dir``). The option-box wrap swaps the combo for its
        container in the row layout (``replaceWidget``); the row's
        bookkeeping keys off the widget itself, so the swap is invisible to it.
        """
        if not widget.is_initialized:
            widget.restore_state = True  # Enable state restore
            widget.refresh_on_show = True  # Call this method on show
            # Persist the selection by preset NAME, not combo index: the item
            # list is rebuilt from a scan each show, so an index saved one
            # session points at a different preset (or out of range -> "None")
            # the next. See StateManager.restore_by / _RESTORE_MODES.
            widget.restore_by = "text"

            widget.option_box.menu.setTitle("FBX Preset:")
            widget.option_box.menu.add_defaults_button = False
            widget.option_box.menu.add(
                "QPushButton",
                setText="Open FBX Preset Directory",
                setObjectName="b007",
                setToolTip=(
                    "Open the FBX preset directory in the file browser: "
                    "presets are added, renamed and deleted there."
                ),
            )
            widget.option_box.menu.add(
                "QPushButton",
                setText="Edit FBX Preset",
                setObjectName="b008",
                setToolTip=(
                    "Edit the selected preset (Maya: in the FBX preset editor; "
                    "Blender: its JSON file, a built-in one copied to your "
                    "presets first)."
                ),
            )

            # Sorts ahead of the option-box menu button (DEFAULT_OPTION_ORDER:
            # "action" before "menu"). ``refresh_on_show`` already re-scans when
            # the panel opens; this is for a preset added, renamed or deleted
            # while it is sitting open (Maya's own preset editor, a file
            # dropped into the directory b007 opens), which the panel has no
            # way to hear about.
            widget.option_box.add_action(
                callback=self._refresh_presets,
                icon="refresh",
                tooltip="Re-scan the FBX preset directory for presets added, renamed or removed since the panel opened.",
            )

        # Store current selection before refresh
        current_data = widget.currentData() if widget.count() > 0 else None
        current_text = widget.currentText() if widget.count() > 0 else ""

        # Refresh the preset data. Read the scan ONCE — the warning and the
        # selection-restore below must agree with the list actually shown.
        presets = self.exporter.presets
        widget.add(presets, clear=True)

        # Warn if no presets or directory issues
        if hasattr(self.ui, "txt003"):
            if not self.exporter.fbx_preset_dir():
                self.ui.txt003.setHtml(
                    "<span style='color:orange'>Warning: the FBX preset directory was not found.</span>"
                )
            elif len(presets) <= 1:  # Only "None"
                self.ui.txt003.setHtml(
                    "<span style='color:orange'>Warning: No presets found in the preset directory.<br>"
                    "Drop preset files into it (FBX Preset ▸ option box ▸ Open FBX Preset Directory).</span>"
                )

        # Restore previous selection if it still exists
        if current_data and current_data in presets.values():
            # Find the text key for the preset
            for text, value in presets.items():
                if value == current_data:
                    widget.setCurrentText(text)
                    self.logger.debug(f"Restored preset selection: {text}")
                    break
        elif current_text and current_text in presets:
            widget.setCurrentText(current_text)
            self.logger.debug(f"Restored preset selection by text: {current_text}")

    def txt000_init(self, widget) -> None:
        """Init Output Directory"""
        widget.option_box.menu.setTitle("Output Directory:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.menu.add(
            "QPushButton",
            setToolTip="Set the output directory.",
            setText="Set Output Directory",
            setObjectName="b010",
        )
        widget.option_box.menu.add(
            "QPushButton",
            setToolTip="Open the output directory.",
            setText="Open Output Directory",
            setObjectName="b006",
        )

        # Recent output directories — option box button with history popup
        self._recent_dirs_option = self.sb.RecentValuesOption(
            wrapped_widget=widget,
            settings_key="scene_exporter_output_dirs",
            max_recent=10,
            display_format=lambda p: (
                "\u2026/" + "/".join(ptk.format_path(p).split("/")[-3:])
                if len(ptk.format_path(p).split("/")) > 3
                else str(p)
            ),
            text_align="left",
        )
        widget.option_box.add_option(self._recent_dirs_option)

        # Seed from legacy QSettings if the plugin's store is empty
        if not self._recent_dirs_option.recent_values:
            for d in self._get_legacy_output_dirs():
                self._recent_dirs_option.add_recent_value(d)

    def output_name_preview(self) -> str:
        """Live tooltip for the Output Filename field.

        Teaches the vocabulary (every token, its meaning, its value right now)
        and names the file(s) the next export writes -- resolved through the
        very call the export makes (the engine's ``resolve_export_path``),
        RegEx, counter and Format included, so the two cannot disagree.
        """
        exporter = self.exporter
        resolved = exporter.resolve_export_path(
            self.ui.txt001.text(),
            exporter.resolve_export_dir(self.ui.txt000.text()),
            output_format=self.ui.cmb004.currentData() or "fbx",
            report=False,
        )
        # The counter has no value until a name uses it: say so in its row
        # rather than flag a supported token as unknown.
        n = resolved["n"]
        context = dict(
            resolved["context"],
            **{exporter.VERSION_TOKEN: "next free" if n is None else n},
        )
        first, *rest = resolved["paths"]
        final = first + "".join(" + " + os.path.splitext(p)[1] for p in rest)
        return self.sb.tooltip.placeholder_preview(
            resolved["expanded"],
            context,
            title="Output Filename",
            body=f"Name of the exported file &mdash; empty is "
            f"<b>{exporter.NAME_WILDCARD}</b>, the scene's own name.",
            descriptions=exporter.NAME_TOKENS,
            wildcards={exporter.NAME_WILDCARD: ptk.ExportProfile.NAME_KEY},
            final=final,
            final_label="writes →",
            notes=[
                "Anything else is literal — <b>WIP_*_export</b> wraps the "
                "default name, <b>asset</b> replaces it.",
                "<b>*_v{n:03d}</b> versions every export and "
                "<b>*_{date}_{time}</b> stamps it; the extension follows Format.",
                "Any token can reshape its own value with a regex — "
                "<b>{scene:PATTERN-&gt;REPLACEMENT}</b>. "
                "<b>{scene:_bar.*-&gt;}</b> drops <b>_bar</b> and everything "
                "after it; <b>{scene:(foo|bar)-&gt;baz}</b> rewrites either to "
                "<b>baz</b>. Leave the replacement empty to delete the match.",
            ],
        )

    def txt001_init(self, widget) -> None:
        """Init Output Name"""
        widget.tooltip.bind(self.output_name_preview)
        widget.option_box.menu.setTitle("Output Name:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.clear_option = True
        widget.option_box.menu.add(
            "QPushButton",
            setToolTip=(
                "Name the export after an existing file.\n\n"
                "Opens a file browser at the current output directory. The chosen "
                "file's name (without extension) becomes the output name, and the "
                "output directory follows the file if it lives elsewhere."
            ),
            setText="Browse for File",
            setObjectName="b012",
        )
        # No RegEx lineedit: the regex is part of the name now
        # (``{scene:PATTERN->REPLACEMENT}``), so the whole naming rule is ONE
        # string -- which is also what lets the recent-filenames history below
        # recall it intact. A saved one folds in at ``__init__``
        # (``migrate_legacy_regex``), before this field's restore.

        # Recent output filenames — option box button with history popup
        self._recent_names_option = self.sb.RecentValuesOption(
            wrapped_widget=widget,
            settings_key="scene_exporter_output_filenames",
            max_recent=10,
            display_format="basename",
            text_align="left",
        )
        widget.option_box.add_option(self._recent_names_option)

    def _make_definition_widget(self, name, params, object_name=None):
        """Instantiate the widget a task/check/settings definition describes."""
        params = dict(params)
        widget_type = params.get("widget_type", "QCheckBox")
        object_name = object_name or params.get(
            "object_name", self.sb.convert_to_legal_name(name)
        )
        widget_class = getattr(self.sb.QtWidgets, widget_type, None)
        if widget_class is None:
            widget_class = getattr(self.sb.registered_widgets, widget_type, None)
            if widget_class is None:
                raise ValueError(f"Unknown widget type: {widget_type}")
        for key in self._DEFINITION_META_KEYS:
            params.pop(key, None)
        widget = widget_class()
        self.ui.set_attributes(widget, setObjectName=object_name, **params)
        return widget

    def _definition_rows(self, definitions, panel=None):
        """``[(widget, label)]`` for a WidgetComboBox: one row per definition
        whose ``panel`` tag matches, with a titled Separator wherever the
        ``group`` tag changes — the group sequence IS the section order, so no
        hand-placed separator entries."""
        rows = []
        current_group = None
        for name, params in definitions.items():
            if params.get("panel") != panel:
                continue
            group = params.get("group")
            if group and group != current_group:
                rows.append((self.sb.registered_widgets.Separator(title=group), group))
                current_group = group
            rows.append((self._make_definition_widget(name, params), name))
        return rows

    def cmb001_init(self, widget) -> None:
        """Tasks — scene-prep steps the engine dispatches (``TASK_ORDER``),
        grouped by their ``group`` tag; entries tagged ``panel: settings``
        render in ``cmb008`` instead."""
        widget.add(
            self._definition_rows(self.exporter.task_manager.task_definitions),
            header="Tasks",
            clear=True,
        )

    def cmb002_init(self, widget) -> None:
        """Validation Checks — the gates that abort the write, grouped by tag."""
        widget.add(
            self._definition_rows(self.exporter.task_manager.check_definitions),
            header="Validation Checks",
            clear=True,
        )

    def cmb007_init(self, widget) -> None:
        """Export Preset — the whole panel's run configuration under a name.

        The window's ``PresetManager`` wired onto this main-layout combo (the
        canonical Refresh / Save / ⋯ toolbar comes from ``wire_combo``).
        ``scope="window"`` captures every registered value-bearing widget —
        the Settings / Tasks / Checks rows (they register by objectName like
        any main-layout widget) — minus the machine/scene-specific fields:
        output dir (txt000), output filename (txt001), log output (txt003).
        The preset combo itself is always excluded internally. Each host keeps
        its own presets (``EXPORT_PRESET_DIR``), and the selected FBX preset
        rides along as embedded metadata so a preset shared to another machine
        restores it (the engine's ``fbx_preset_metadata`` /
        ``restore_fbx_preset``).
        """
        mgr = self.ui.presets
        # Adopt this panel's logger (instance-scoped) so the manager's
        # user-facing lines -- notably the schema-drift "preset doesn't cover
        # N new panel settings" warning -- reach the txt003 log sink instead
        # of only the console. Must precede wire_combo: the active-preset
        # restore it triggers is exactly the load that warns.
        mgr.use_logger(self.logger)
        mgr.setup(
            preset_dir=self.exporter.EXPORT_PRESET_DIR,
            metadata_provider=self._fbx_preset_metadata_provider,
            on_metadata_loaded=self._on_fbx_preset_metadata_loaded,
        )
        mgr.scope = "window"
        mgr.exclude("txt000", "txt001", "txt003")
        # No on_loaded: a preset then applies with signals UNBLOCKED, so the
        # show_when dependencies (see _wire_dependencies) follow the loaded
        # values on their own.
        mgr.wire_combo(widget, placeholder="Preset…")
        # A pick loads through the combo's ``activated`` (wire_combo connected it
        # first), so this reads what the loaded preset stores, after the load.
        widget.activated.connect(
            lambda index: self._warn_retired_naming_keys(widget.itemText(index))
        )

    def _warn_retired_naming_keys(self, name: str) -> None:
        """Warn when preset *name* still asks for a retired naming row.

        The manager skips a key no widget takes, and the Output Filename is not
        part of a preset, so a preset that versioned or stamped its exports
        would load and stop doing so without a word. The rows retired
        2026-10-19 (a check its fix now arms, Baked Reflections) are said by
        the engine's ``note_retired_preset_rows``.
        """
        stored = (self.ui.presets.read(name) if name else None) or {}
        spellings = [
            spelling
            for key, spelling in self._RETIRED_NAMING_KEYS.items()
            if stored.get(key)
        ]
        if spellings:
            self.logger.warning(
                f"Preset '{name}' carries the retired Version / Timestamp "
                "settings, which no longer apply: write them into the Output "
                f"Filename instead ({', '.join(spellings)})."
            )
        self.exporter.note_retired_preset_rows(name, stored)

    def cmb008_init(self, widget) -> None:
        """Settings — what is written and from what (the scene-prep steps are
        Tasks). Rows come from :attr:`_SETTINGS_LAYOUT`; the FBX-preset
        management lives on the ``cmb000`` row's own option box
        (``cmb000_init``)."""
        definitions = self.exporter.task_manager.task_definitions
        rows = []
        for group, names in self._SETTINGS_LAYOUT:
            rows.append((self.sb.registered_widgets.Separator(title=group), group))
            for name in names:
                spec = self._SETTINGS_WIDGETS.get(name)
                if spec is not None:
                    rows.append(
                        (
                            self._make_definition_widget(name, spec, object_name=name),
                            name,
                        )
                    )
                elif name in definitions:
                    rows.append(
                        (self._make_definition_widget(name, definitions[name]), name)
                    )
        widget.add(rows, header="Settings", clear=True)

    def _refresh_presets(self) -> None:
        """Re-scan the FBX presets (the ``cmb000`` refresh button), then re-run
        :meth:`cmb000_init`, which restores the current selection if it
        survived. The button has to mean "re-scan", unconditionally -- the
        engine's ``refresh_fbx_presets`` drops any cache its scan keeps."""
        self.exporter.refresh_fbx_presets()
        self.ui.cmb000.init_slot()
        self.logger.debug("Refreshed the FBX preset list.")

    def ignore_groups_init(self, widget) -> None:
        """Init Ignore Groups — a Settings row (``cmb008``), created by
        :meth:`cmb008_init` and registered by objectName.

        The row's own option box carries an "Aa" toggle for the match mode, so
        the case switch sits on the field it governs instead of costing a
        second row. Off (case-insensitive) is the default and the behavior the
        task has always had; :meth:`b000` reads the toggle back when it builds
        the task payload.
        """
        if widget.is_initialized:
            return
        widget.option_box.set_toggle(
            icon="font",  # an "Aa" glyph — the conventional match-case mark
            tooltip_on="Case-sensitive: names must match exactly. Click to ignore case.",
            tooltip_off="Ignoring case. Click to match case exactly.",
            initial=False,
            # ToggleOption tints its off state the project error red, which suits
            # a toggle whose off state STOPS something; here "off" is the
            # ordinary, default match mode, so it takes the neutral "locked"
            # token. The on state keeps the auto theme colour, so the button
            # reads like every sibling in the option box.
            disabled_color=ptk.Palette.status()["locked"][0],
            # Explicit namespace, and the toggle's ONLY persistence: its button
            # is registered by objectName (``register_children`` sweeps the
            # option box) but carries ``restore_state=False``, so the preset
            # manager's value-only window scope skips it — the export preset
            # stores the Ignore field's text, never the match mode. uitk
            # host-namespaces the key, so each host keeps its own state.
            settings_key="scene_exporter_ignore_groups_case_sensitive",
        )
        self._case_toggle = widget.option_box.find_option(self.sb.ToggleOption)

    def _ignore_groups_case_sensitive(self) -> bool:
        """Whether the Ignore row's case toggle is on.

        ``False`` when :meth:`ignore_groups_init` never ran (no row, or an
        option box that never got wrapped) — the task's own default, so the
        panel still exports.
        """
        return bool(self._case_toggle and self._case_toggle.is_on)

    def export_data_node_init(self, widget) -> None:
        """Init Export Scene Data Node — a Settings row (``cmb008``).

        Its option box carries a viewer button: what the checkbox would ship,
        without exporting to find out.
        """
        if widget.is_initialized:
            return
        widget.option_box.add_action(
            callback=self._show_data_node,
            icon="shell",
            tooltip="Show what this ships: the scene's data_export node contents.",
        )

    def _show_data_node(self):
        """Open every ``data_export`` carrier the export ships in the shared data
        viewer (``sb.data_view_dialog``, the one tentacle's Scene Metadata uses):
        the host's ``DataNodes.dump_export_nodes`` (Maya: a referenced module's
        ``NS:data_export`` included), JSON decoded, keyed by node.

        The nodes as they stand: the export refreshes them from the live scene
        before writing, so a producer that has not run yet is not shown.
        """
        data_nodes = self.tk.DataNodes
        return self.sb.data_view_dialog(
            data_nodes.dump_export_nodes(),
            title="Scene Data Node",
            save_path=self.tk.EnvUtils.scene_artifact_path(
                f"_{data_nodes.EXPORT}.json"
            ),
            empty_message=f"<hl>No {data_nodes.EXPORT} channels</hl> -- "
            "the export has no scene metadata to ship.",
        )

    def cmb004_init(self, widget) -> None:
        """Init Output Format — FBX (default), GLB, FBX + GLB, or USD.

        A Settings row (``cmb008``). ``currentData()`` yields the
        ``output_format`` token ``b000`` forwards to ``perform_export``.
        GLB-only writes the FBX to a temp dir and keeps only the converted
        ``.glb``; FBX + GLB keeps both side by side. The container its embedded
        textures are written in is the general ``texture_file_type`` row (a
        GLB carries what glTF accepts — see ``ptk.ExportRun.glb_texture_params``).
        USD writes a ``.usd`` layer through the host's USD exporter
        (UsdPreviewSurface materials; the FBX preset / takes / GLB rows do not
        apply and say so). Items are APPEND-ONLY: the combo persists by index.
        """
        if not widget.is_initialized:
            widget.restore_state = True
        widget.add(dict(self.exporter.OUTPUT_FORMATS), clear=True)

    def cmb005_init(self, widget) -> None:
        """Init Texture Template — optionally convert textures to a registry workflow.

        The ``convert_textures`` row of the Tasks combo (``cmb001``, Textures
        group), which is where it acts: it arms a pipeline task rather than
        describing the write. The run configuration collects it as
        ``convert_textures`` (task phase) and mirrors it onto
        ``check_material_compatibility`` (check phase), so there are no separate
        rows to keep in sync. "As Authored" (the default) sends textures exactly
        as the scene references them and arms neither.

        Names and tooltips from ``ptk.OutputTemplates.profile_choices()`` -- the
        workflow profiles the Map Updater, game shader and converter panels
        render, in the registry's order (the combo persists by index).
        """
        if not widget.is_initialized:
            widget.restore_state = True
        choices = ptk.OutputTemplates.profile_choices()
        widget.add(
            {"As Authored": None, **{name: name for name, _ in choices}},
            clear=True,
        )
        tooltips = dict(choices)
        for index in range(widget.count()):
            description = tooltips.get(widget.itemData(index))
            if description:
                widget.setItemData(index, description, self.sb.QtCore.Qt.ToolTipRole)

    def b000(self) -> None:
        """Export: run the scene export with the configured tasks and settings.

        The panel's widgets are read into values and turned into the run
        configuration by the engine's ``run_config_from_values`` -- the
        button's contract written once (:class:`pythontk.ExportProfile`).
        """
        exporter = self.exporter
        self.ui.txt003.clear()
        tasks_def, checks_def = exporter.definition_tables()
        values = ptk.ExportProfile.read_values(self.ui, tasks_def, checks_def)
        values["cmb004"] = self.ui.cmb004.currentData()
        config = exporter.run_config_from_values(
            values,
            override_checks=self.ui.b009.isChecked(),
            ignore_groups_case_sensitive=self._ignore_groups_case_sensitive(),
        )
        export_mode = config["export_mode"]
        self.logger.debug(f"Run configuration: {config}")

        # The footer's bar (determinate -- the run's own step count arrives
        # with the first tick) plus its busy spinner, because single steps
        # (the FBX write, a GLB conversion) hold the event loop for seconds
        # and a parked bar reads as hung. Esc held over the panel cancels
        # through the same ``update``: perform_export stops before its next
        # step while nothing has been written. ``sb.progress`` is a no-op on
        # a UI without a footer, so the run itself never depends on one.
        # The scope resolves inside the run (a callable), as it always has.
        with self.sb.progress(
            ui=self.ui, text="Export: preparing…", busy=True
        ) as update:
            exported = exporter.perform_export(
                objects=lambda: exporter.objects_to_export(export_mode),
                export_dir=self.ui.txt000.text(),
                preset_file=self.ui.cmb000.currentData(),
                export_visible=config["export_visible"],
                output_name=self.ui.txt001.text(),
                create_log_file=True,
                tasks=config["tasks"],
                progress_callback=self.sb.progress_adapter(update),
            )
        footer = getattr(self.ui, "footer", None)
        if footer is not None:
            if exported:
                footer.setText("Export complete", level="success")
            elif exporter.export_cancelled:
                footer.setText("Export cancelled", level="warning")
            else:
                footer.setText("Export aborted — see the log", level="warning")

        self.save_output_dir(self.ui.txt000.text())
        self.save_output_name(self.ui.txt001.text())

        # Override Checks is a per-run escape hatch, not a mode: a successful
        # export disarms it so the next run is validated again. Left armed on a
        # failed export -- the user is still mid-troubleshooting and would
        # otherwise have to re-arm it for every retry.
        if exported:
            self.ui.b009.setChecked(False)

    def b010(self) -> None:
        """Set Output Directory"""
        output_dir = self.sb.dir_dialog(
            title="Select an output directory:", start_dir=self.workspace
        )
        if output_dir:
            self.ui.txt000.setText(output_dir)

    def b012(self) -> None:
        """Browse for Output File -- name the export after an existing file.

        Opens at the currently specified output directory (falling back to the
        workspace when it is unset or gone) and filters to the extensions the
        selected output format (``cmb004``) writes. The pick sets the output
        name to the file's basename and, when the file was chosen from another
        directory, retargets the output directory to match -- so the file the
        user pointed at is the file the next export overwrites.
        """
        start_dir = self.ui.txt000.text()
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = self.workspace or ""

        file_types = {
            "fbx": ["*.fbx"],
            "glb": ["*.glb"],
            "fbx_glb": ["*.fbx", "*.glb"],
            "usd": ["*.usd", "*.usda", "*.usdc"],
        }.get(self.ui.cmb004.currentData(), ["*.fbx", "*.glb", "*.usd"])

        file_path = self.sb.file_dialog(
            file_types=file_types,
            title="Select a file to name the export after:",
            start_dir=start_dir,
            filter_description="Export Files",
            allow_multiple=False,
        )
        if not file_path:
            return

        self.ui.txt001.setText(ptk.format_path(file_path, "name"))

        # Second pass restores the trailing slash on a drive root ("O:" -> "O:/",
        # which Windows resolves to that drive's CWD rather than its root).
        file_dir = ptk.format_path(ptk.format_path(file_path, "path"))
        if file_dir and file_dir != ptk.format_path(self.ui.txt000.text()):
            self.ui.txt000.setText(file_dir)
            self.logger.info(f"Output directory set to: {file_dir}")

    def b006(self) -> None:
        """Open Output Directory"""
        # The shared opener, not os.startfile (Windows-only); it says so when
        # the directory does not exist.
        ptk.FileUtils.open_explorer(self.ui.txt000.text(), logger=self.logger)

    def b007(self) -> None:
        """Open FBX Preset Directory -- the host's own FBX preset folder, where
        a dropped-in preset belongs (Maya: ``FBX/Presets`` under its user app
        directory, which the scan reaches; Blender: the user preset tier)."""
        preset_dir = self.exporter.fbx_preset_dir()
        if not preset_dir:
            self.logger.error("The FBX preset directory was not found.")
            return
        ptk.FileUtils.open_explorer(preset_dir, create_dir=True, logger=self.logger)

    def b008(self) -> None:
        """Edit FBX Preset -- the host's edit surface for the selected preset
        (the engine's ``edit_fbx_preset``)."""
        self.exporter.edit_fbx_preset(self.ui.cmb000.currentData())

    def _get_legacy_output_dirs(self) -> List[str]:
        """Load recent output directories from legacy QSettings.

        Used only for one-time migration into ``RecentValuesOption``.
        """
        prev_output_dirs = self.ui.settings.value("prev_output_dirs", [])
        return [i for i in prev_output_dirs if not i == "/"][-10:]

    def save_output_dir(self, output_dir: str) -> None:
        """Record the output directory into the recent values plugin."""
        if output_dir and self._recent_dirs_option is not None:
            self._recent_dirs_option.record(ptk.format_path(output_dir))

    def save_output_name(self, output_name: str) -> None:
        """Record the output filename into the recent values plugin."""
        if output_name and self._recent_names_option is not None:
            self._recent_names_option.record(output_name)

    def _fbx_preset_metadata_provider(self) -> dict:
        """The selected FBX preset as metadata an export preset embeds."""
        return self.exporter.fbx_preset_metadata(self.ui.cmb000.currentData())

    def _on_fbx_preset_metadata_loaded(self, meta: dict) -> None:
        """Restore an embedded FBX preset no copy of which exists here, then
        show it in the FBX Preset combo."""
        if self.exporter.restore_fbx_preset(meta):
            self.ui.cmb000.init_slot()
