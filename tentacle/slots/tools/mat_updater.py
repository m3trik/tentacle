# !/usr/bin/python
# coding=utf-8
"""Material Updater: rework scene materials for a target workflow preset,
packing or unpacking their texture maps and rewiring them to the result.

One Slots class for both hosts over the host toolkit's ``MatUpdater``
(``self.tk``), composed, never inherited. The engine resolves the run's scope
(the selection's materials, or those using picked textures) and owns what each
host can do: Maya can retype a material first and copy or move its source maps
to the Output Folder; Blender has one surface shader and writes processed maps
straight to the Output Folder, so those two options are Maya's.
"""

from functools import partial

import pythontk as ptk
from qtpy import QtCore

from tentacle import Slots


class MatUpdaterSlots(Slots):
    msg_intro = "Reconfigure existing materials for a target workflow preset."

    #: The selection-mode combo's entries, in order (the combo saves its index).
    SELECTION_MODES = ("Selected Objects", "All Scene Materials", "Browse...")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.mat_updater
        self.engine = self.tk.MatUpdater()
        self._pending = None  # the live call an armed Apply button would make
        self._committing = None  # that call, handed to b001 for one dispatch
        # Built here rather than at the end of init: ``_disarm_apply`` is a
        # signal handler (the selection-mode combo restores its state during
        # header init) and reads this, so it must already be bound.
        self._apply_btn = self._add_apply_button()

        # Stream the engine's log into txt001. ``update_materials`` is a
        # classmethod logging through MatUpdater's class logger, so that is the
        # one mirrored (it sets its own level each run: INFO for this panel's
        # verbose runs).
        self.logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        self.logger.setup_logging_redirect(self.ui.txt001)

        # Connect clickable log links (action:// URIs in QTextBrowser)
        if hasattr(self.ui.txt001, "anchorClicked"):
            self.ui.txt001.anchorClicked.connect(self._on_log_link_clicked)

        # Where the run resolves an Output Folder and discovers maps.
        try:
            root = self.engine.texture_root()
        except Exception:  # a scene state the host cannot answer for
            root = ""
        info = (
            "<br><font color='#888'>Texture folder: "
            f"{ptk.truncate(root, mode='middle')}</font><br>"
            if root
            else ""
        )
        self.ui.txt001.setText(self.msg_intro + info)

    @property
    def logger(self):
        """The engine's logger: the run report and this panel's notes share it."""
        return self.engine.logger

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the log panel."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    # ------------------------------------------------------------------
    # Dry run / Apply
    # ------------------------------------------------------------------

    def _add_apply_button(self):
        """The footer button that commits the last dry run; hidden until one is armed."""
        footer = getattr(self.ui, "footer", None)
        if footer is None or not hasattr(footer, "add_action_button"):
            return None
        button = footer.add_action_button(
            text="Apply",
            icon_name="check",
            tooltip="Apply the update the last dry run previewed.",
            callback=self._apply_dry_run,
        )
        button.setVisible(False)
        return button

    def _arm_apply(self, commit) -> None:
        """Hold *commit* -- the identical live call -- for the Apply button."""
        self._pending = commit
        if self._apply_btn is not None:
            self._apply_btn.setVisible(True)
            self.ui.footer.setText("Dry run — Apply to commit", level="warning")

    def _disarm_apply(self, *_args) -> None:
        """Drop any armed preview and hide the Apply button.

        Gated on having been armed, not on ``isVisible()`` -- a child of an
        unshown window reads as invisible however it was set, which would leave
        the footer note behind.
        """
        was_armed = self._pending is not None
        self._pending = None
        if was_armed and self._apply_btn is not None:
            self._apply_btn.setVisible(False)
            self.ui.footer.setText("")

    def _apply_dry_run(self) -> None:
        """Commit the plan the last dry run previewed.

        Routed back through the Update button rather than called straight,
        because the commit is the run that actually writes: going through the
        dispatcher is what gives it the same ``@Cancelable`` treatment the
        preview got -- an activated cancel scope (so ``sb.progress``'s Esc and
        the stall dialog's Cancel are the same cancel), the "still running"
        dialog and the spinner. ``b001`` consumes ``_committing`` and calls
        ``_begin``, which is what disarms this button.
        """
        commit = self._pending
        if commit is None:
            return
        self._committing = commit
        try:
            self.ui.b001.click()
        finally:
            # Never leave the carrier set: a dispatch that did not reach b001
            # would otherwise make the NEXT Update press commit a stale plan.
            self._committing = None

    def _report_failure(self, error) -> None:
        """Report a failed run -- shared by the preview and the commit.

        Through the logger, not txt001.append: the handler is already pointed
        at txt001, so this lands in the same place *and* picks up ERROR
        colouring plus any file/ring sink the session attached. Message and
        traceback go out as ONE record -- a formatted traceback is already a
        single multi-line string, and the widget handler renders it with
        ``white-space:pre-wrap``, so it needs no ``log_group`` to avoid
        per-frame paragraphs. Plain ``error`` also keeps the whole thing
        level-filtered, which ``log_group`` (via ``log_raw``) would not be.
        """
        import traceback

        self.logger.error(f"Material update failed: {error}\n{traceback.format_exc()}")

    def _begin(self) -> None:
        """Start a new run: clear the report and drop any pending preview.

        One rule in one place -- a new run always supersedes the last dry run's
        plan, including when it goes on to abort with nothing in scope.
        """
        self.ui.txt001.clear()
        self._disarm_apply()

    def header_init(self, widget):
        """Format global options in the header menu."""
        # Selection Mode
        cmb_mode = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_selection_mode",
            addItems=list(self.SELECTION_MODES),
            setToolTip=(
                "Choose the texture/material source:\n"
                "• Selected Objects — materials on the current selection (in "
                "Maya, material nodes selected in the Hypershade or Outliner "
                "count too).\n"
                "• All Scene Materials — every supported material in the scene.\n"
                "• Browse… — pick texture files; updates materials that reference them."
            ),
        )
        # A new mode stales any armed preview: the plan on screen was built
        # over the old mode's material set, and committing it under a mode the
        # panel no longer shows is exactly the surprise Apply exists to avoid.
        cmb_mode.currentTextChanged.connect(self._disarm_apply)
        # Dry Run — kept at the top so it's the first thing reached under the
        # selection mode; simulate the run without writing files or editing nodes.
        widget.menu.add(
            "QCheckBox",
            setObjectName="chk_dry_run",
            setText="Dry Run",
            setToolTip=(
                "Simulate the process without making changes.\n"
                "A preview arms Apply in the footer: it commits the exact plan "
                "you are looking at, even if the options or the selection have "
                "moved on since."
            ),
        )
        # Shader Type — the material's NODE type, retyped before the textures
        # are wired (``update_materials(shader_type=...)``). The engine names
        # its targets, so one added there appears here without a second list
        # to keep in step; the labels' prefix is this panel's business. "Keep
        # Current Type" leads and the targets follow in the engine's order —
        # combo state persists by INDEX, so new targets land at the END.
        # Blender has one surface shader (Principled BSDF): no targets, so no
        # combo there.
        shader_types = self.engine.shader_type_choices()
        if shader_types:
            cmb_shader = widget.menu.add(
                "QComboBox",
                setObjectName="cmb_shader_type",
                setToolTip=(
                    "Retype the materials before their textures are wired.\n"
                    "Keep Current Type (default): only the textures change.\n"
                    "A target type: each material is rebuilt on that shader — its "
                    "textures, constants and geometry assignments carry across — "
                    "then updated as usual. This is also what brings a legacy "
                    "blinn/lambert/phong into the run at all: those have no "
                    "connector, so without a retype they are skipped."
                ),
            )
            # addItem, not ``add(prefix=...)``: that helper rewrites a None data
            # value to the item's label (and title-cases the text), which would
            # hand "Keep Current Type" to the engine as a shader-type name.
            cmb_shader.addItem("Shader: Keep Current Type", None)
            for label, shader_type in shader_types:
                cmb_shader.addItem(f"Shader: {label}", shader_type)
        # Reconfiguration only — file format, max size, mask/secondary scale
        # and bit depth are NOT offered here. They duplicate the Map Converter's
        # Optimize tool, which owns image optimization for the whole pipeline;
        # this panel decides *which* maps a material gets and wires them up.
        widget.menu.add("Separator", setTitle="Processing")
        # Missing Maps — the policy for a packed map (ORM / MSAO) the preset
        # calls for whose source channels aren't all resolvable. Same three
        # rules, wording and prefixed-combo presentation as the Map Packer's
        # control, so one vocabulary covers both ends of the pipeline.
        cmb_missing = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_missing_maps",
            setToolTip=(
                "What to do when a packed map (ORM, MSAO) the preset calls for "
                "is missing one or more of its source maps (and it can't be "
                "derived from the maps that are present).\n"
                "Skip Map (default): the packed map isn't written. A gap whose "
                "fill is harmless still packs - an absent AO fills white - so "
                "this is about the ones that would bake in a wrong value, like "
                "black roughness or white (mirror) smoothness.\n"
                "Pack If 2+ Maps: pack once at least two source channels "
                "resolved - enough that the result is still a useful packed map "
                "rather than a single map wearing a packed name.\n"
                "Pack Anyway: always pack; missing channels are filled with "
                "their default value.\n"
                "In Blender, packed maps are written for engine export but never "
                "wired into the Principled BSDF, which keeps separate Roughness / "
                "Metallic / AO inputs."
            ),
        )
        cmb_missing.add(
            [
                ("Skip Map", ptk.MapRegistry.MISSING_SKIP),
                ("Pack If 2+ Maps", ptk.MapRegistry.MISSING_MULTI),
                ("Pack Anyway", ptk.MapRegistry.MISSING_FORCE),
            ],
            prefix="Missing Maps:",
        )
        # Use Input Fallbacks
        widget.menu.add(
            "QCheckBox",
            setObjectName="chk_input_fallbacks",
            setText="Use Input Fallbacks",
            setChecked=True,
            setToolTip="Allow generating maps from alternative inputs (e.g. create Base Color from Existing Diffuse).",
        )
        # Use Output Fallbacks
        widget.menu.add(
            "QCheckBox",
            setObjectName="chk_output_fallbacks",
            setText="Use Output Fallbacks",
            setChecked=True,
            setToolTip="Allow substituting missing output maps with alternatives (e.g. use AO map alone if Mask Map cannot be generated). Ignored when Missing Maps is set to Pack Anyway.",
        )

        # Output fallbacks only have something to do while a packed map can
        # still fail to be written: 'Pack Anyway' always emits one, so there is
        # never a missing output left to substitute for.
        def _update_output_fallbacks_state():
            widget.menu.chk_output_fallbacks.setDisabled(
                cmb_missing.currentData() == ptk.MapRegistry.MISSING_FORCE
            )

        cmb_missing.currentIndexChanged.connect(
            lambda *_: _update_output_fallbacks_state()
        )
        _update_output_fallbacks_state()
        # Discover Maps in the texture folder (the engine's ``texture_root``).
        widget.menu.add(
            "QCheckBox",
            setObjectName="chk_discover_sourceimages",
            setText="Discover Maps in Texture Folder",
            setChecked=True,
            setToolTip=(
                "Pull in same-base-name textures found in the texture folder "
                "(Maya: the project's sourceimages; Blender: the workspace "
                "folder) that aren't wired into the material (e.g. a Normal "
                "sitting on disk but never connected).\n"
                "Only map types missing from the material are added; "
                "connected textures are never replaced."
            ),
        )
        widget.menu.add("Separator", setTitle="File Management")
        # File Transfer Mode: what becomes of the SOURCE maps once an Output
        # Folder is set. Blender's engine has no such step (the factory writes
        # processed maps straight to the Output Folder), so it offers no mode
        # and the combo shows disabled there, its items kept so the saved
        # index means the same on both hosts.
        transfer_modes = self.engine.TRANSFER_MODES
        cmb_transfer = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_transfer_mode",
            setToolTip=(
                "How to handle the source files when an Output Folder is "
                "specified (Maya only: Blender writes processed textures "
                "straight to the Output Folder)."
            ),
        )
        cmb_transfer.addItem("Copy All to Output", "copy")
        cmb_transfer.addItem("Move All to Output", "move")
        cmb_transfer.addItem("Use Existing Folders", "none")
        cmb_transfer.setEnabled(bool(transfer_modes))

        # Output Folder
        widget.menu.add(
            "QLineEdit",
            setObjectName="txt_move_to",
            setPlaceholderText="Output Folder (Optional)",
            setToolTip=(
                "Folder to write the processed textures to; the materials are "
                "repathed to them. A relative path resolves against the texture "
                "folder. Blank: process each texture in place."
            ),
        )

        # Use Existing Folders writes nowhere new: no Output Folder to type.
        def _update_move_to_state():
            mode = cmb_transfer.currentData()
            widget.menu.txt_move_to.setEnabled(mode != "none")

        if transfer_modes:
            cmb_transfer.currentIndexChanged.connect(_update_move_to_state)
            _update_move_to_state()

        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Material Updater",
                body="Reconfigure scene materials for a target workflow — "
                "resolve each material's texture set, generate the packed maps "
                "the preset calls for (ORM / MSAO), and rewire the shading "
                "network to the result.<br>"
                "A preset that wants LOOSE maps goes the other way too: a packed map it does not call for is unpacked into the channels it carries and retired — a loose map already on disk (or discovered in the texture folder) always wins over an extracted one, and a packing whose channels cannot be recovered is kept rather than lost.<br>"
                "Image <i>optimization</i> — file format, resolution clamp, "
                "secondary scale, bit depth, archiving originals — is not done "
                "here: run the <b>Map Converter</b>'s <b>Optimize</b> tool for that.",
                steps=[
                    "Pick a <b>Selection Mode</b> (Selected Objects / All "
                    "Scene Materials / Browse... for texture files).",
                    "Open the header menu (▸) and configure the processing "
                    "and file-management options below.",
                    "Press <b>Update Materials</b> to run.",
                ],
                sections=[
                    (
                        "Processing options",
                        [
                            "<b>Missing Maps</b> — what an ORM / MSAO does when a "
                            "source channel can't be resolved: <i>Skip Map</i> "
                            "writes nothing unless the gap is harmless (an absent "
                            "AO fills white), <i>Pack If 2+ Maps</i> packs once at "
                            "least two channels resolved, <i>Pack Anyway</i> packs "
                            "regardless (absent channels take their default fill). "
                            "In Blender, written for engine export; never wired "
                            "into the Principled BSDF.",
                            "<b>Use Input Fallbacks</b> — generate missing inputs "
                            "from related ones (e.g. Base Color from Diffuse).",
                            "<b>Use Output Fallbacks</b> — substitute missing "
                            "outputs (e.g. AO alone for Mask Map). Disabled when "
                            "Missing Maps is set to Pack Anyway.",
                            "<b>Discover Maps in Texture Folder</b> — gap-fill each "
                            "material with same-base-name textures sitting in "
                            "the texture folder (Maya: sourceimages; Blender: the "
                            "workspace folder) that were never connected. Only "
                            "missing map types are added; connected textures are kept.",
                            "<b>Shader Type</b> (Maya) — retype each material "
                            "before its textures are wired (textures, constants and "
                            "geometry assignments carry across). Leave on "
                            "<i>Keep Current Type</i> to change textures only; "
                            "pick a target to bring legacy blinn / lambert / "
                            "phong materials into the run, which are otherwise "
                            "skipped for having no connector.",
                            "<b>Dry Run</b> — preview the plan without writing "
                            "files. <b>Apply</b> then appears in the footer to "
                            "commit the preview.",
                        ],
                    ),
                    (
                        "File management",
                        [
                            "<b>Transfer Mode</b> (Maya) — Copy / Move / Use "
                            "Existing. Blender writes processed textures straight "
                            "to the Output Folder.",
                            "<b>Output Folder</b> — destination for processed "
                            "textures (disabled when Use Existing is selected).",
                        ],
                    ),
                    (
                        "Notes",
                        [
                            "In Blender, needs Pillow — installed into Blender's "
                            "Python on first run.",
                        ],
                    ),
                ],
            )
        )

    # The header menu's widgets, reached through it: they are no part of the .ui.
    @property
    def selection_mode(self):
        return self.ui.header.menu.cmb_selection_mode.currentText()

    @property
    def move_to_folder(self):
        return self.ui.header.menu.txt_move_to.text() or None

    @property
    def shader_type(self):
        """The selected retype target, or None for "keep the current type"
        (always None on a host with nothing to retype to)."""
        if not self.engine.shader_type_choices():
            return None
        return self.ui.header.menu.cmb_shader_type.currentData()

    def cmb001_init(self, widget):
        """Initialize Presets.

        Names and tooltips both come from the ``OutputTemplates`` SSoT (shared
        with game_shader / the converter / compositor / scene exporter). The
        tooltip is the profile's full outline rather than its one-paragraph
        description: "which preset is right for me" is answered by the target
        engine, but the question a preset combo is actually asked here is *what
        will I get* — so each item names the files the profile writes and what
        each one carries.

        ``delivery=False`` because this panel does not hand the profile to the
        writer as ``output_profile``: it reconfigures and rewires, leaving each
        map in the container it was authored in (the Map Converter's Optimize
        tool owns format changes). Naming TGA under Unreal here would be a
        promise the run does not keep.
        """
        if not widget.is_initialized:
            widget.restore_state = True
            widget.clear()
            for name, outline in ptk.OutputTemplates.profile_outlines(delivery=False):
                widget.addItem(name)
                widget.setItemData(
                    widget.count() - 1,
                    self.sb.tooltip.fmt(**outline),
                    QtCore.Qt.ToolTipRole,
                )

    def _scope(self, mode, shader_type):
        """The materials the run acts on for *mode*: ``None`` for every scene
        material, ``[]`` when there are none (the engine or this said why)."""
        if mode == "Selected Objects":
            # The selection's materials the run can act on; the engine warns
            # why when there are none (nothing selected, or no supported type).
            return self.engine.selected_materials(shader_type=shader_type)
        if mode == "Browse...":
            try:
                start_dir = self.engine.texture_root()
            except Exception:
                start_dir = ""
            paths = self.sb.file_dialog(
                file_types=[f"*.{ext}" for ext in ptk.ImgUtils.texture_file_types],
                title="Select textures whose materials should be updated:",
                start_dir=start_dir,
                allow_multiple=True,
            )
            if not paths:
                return []
            materials = self.engine.materials_using_textures(
                paths, shader_type=shader_type
            )
            if not materials:
                self.logger.warning(
                    "No supported materials reference the selected textures."
                )
            return materials
        return None  # All Scene Materials: update_materials' own default

    @Slots.Cancelable(300)
    def b001(self):
        """Update Materials"""
        # An armed plan, handed over by the footer's Apply button, IS the run:
        # it is the preview's own call with dry_run off, over the material set
        # and options as they were previewed.
        # Consumed on READ, not just in ``_apply_dry_run``'s finally: the
        # commit pumps the event loop (the progress bar, the stall dialog), so
        # a second press during it re-enters here -- and a carrier still set
        # would commit the same plan again instead of running a fresh update.
        commit, self._committing = self._committing, None
        # Before the scope resolves: an abort ("Nothing selected.") is a new
        # run too, so it must not land under the previous run's report, and it
        # must supersede any plan the Apply button still holds.
        self._begin()
        if commit is not None:
            try:
                commit()
            except Exception as e:
                self._report_failure(e)
            return

        config_name = self.ui.cmb001.currentText()

        menu = self.ui.header.menu
        dry_run = menu.chk_dry_run.isChecked()
        shader_type = self.shader_type

        # `None` means "let update_materials default to all scene materials".
        materials = self._scope(self.selection_mode, shader_type)
        if materials is not None and not materials:
            return

        try:
            # Reconfiguration keys only. Image-optimization keys (max_size,
            # mask_map_scale, output_extension, old_files_folder) are
            # deliberately absent — the factory then leaves resolution, format
            # and bit depth alone, and the Map Converter's Optimize tool owns
            # that pass. ``update_materials`` still accepts them, so a script
            # can drive both in one call; the panel does not offer them.
            config = {
                "preset": config_name,
                "move_to_folder": self.move_to_folder,
                "missing_map_rule": menu.cmb_missing_maps.currentData(),
                "use_input_fallbacks": menu.chk_input_fallbacks.isChecked(),
                "use_output_fallbacks": menu.chk_output_fallbacks.isChecked(),
                "discover_sourceimages": menu.chk_discover_sourceimages.isChecked(),
            }
            # The source-file transfer, where the host has one (Maya; Blender
            # writes straight to the Output Folder): Use Existing Folders
            # ("none") writes nowhere new.
            if self.engine.TRANSFER_MODES:
                transfer_mode = menu.cmb_transfer_mode.currentData()
                config["transfer_mode"] = transfer_mode
                if transfer_mode == "none":
                    config["move_to_folder"] = None

            # The run as a closure over the frozen plan, so Apply commits
            # what the report on screen describes even if the preset, the
            # header options or the selection have moved on since. Only
            # ``dry_run`` differs between the two calls.
            #
            # No ``total=`` needed — :meth:`Switchboard.progress_adapter`
            # auto-syncs the bar from ``update_materials``'s callback total
            # on the first tick. Also avoids ``len(None)`` when materials
            # defaults to "all scene materials".
            def run(plan, mats):
                with self.sb.progress(text="Updating Materials") as update:
                    return self.engine.update_materials(
                        materials=mats,
                        config=dict(config, dry_run=plan),
                        verbose=True,
                        progress_callback=self.sb.progress_adapter(update),
                        shader_type=shader_type,
                    )

            run(dry_run, materials)
            # No completion line appended here — update_materials closes the
            # run with its own summary box (mirrors the scene exporter).

            # Arm only once the preview has actually reported: a run that
            # raised must not leave a button offering to commit it. ``None``
            # is frozen as-is — "All Scene Materials" is a standing query, and
            # re-resolving it at Apply is what that mode means; a resolved
            # list is copied so a later selection change cannot rewrite it.
            if dry_run:
                self._arm_apply(
                    partial(run, False, None if materials is None else list(materials))
                )
        except Exception as e:
            self._report_failure(e)
