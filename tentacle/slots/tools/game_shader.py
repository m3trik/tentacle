# !/usr/bin/python
# coding=utf-8
"""Game Shader: build a PBR material from a set of texture maps, packed for a
target engine.

One Slots class for both hosts over the host toolkit's ``GameShader``
(``self.tk``), composed, never inherited: Maya builds a Stingray PBS, Standard
Surface or OpenPBR Surface network, Blender a Principled BSDF material (already
the OpenPBR model, so Blender offers no Shader Type).
"""

from typing import Optional

import pythontk as ptk
from qtpy import QtCore

from tentacle import Slots


class GameShaderSlots(Slots, ptk.LoggingMixin):
    msg_intro = """<u>To set up the material:</u>
        <br>• Click <b>Create Network</b> to pick texture maps and build their shading network; OpenGL and DirectX normal maps are converted as needed.

        <p><b>Note (Maya):</b> opacity and transmission render in Maya only with the shape node's
        Opaque setting disabled. With Opaque on, opacity does not work at all; transmission does,
        but any shadow the object casts stays solid, ignoring the shader's Transparent Color and density.</p>
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.game_shader
        # The engine logs through this panel's own logger, as the panel's
        # subclass did: GameShader's class logger is shared with every other
        # caller (bridges, the material updater), which this panel must neither
        # stream into its log nor have its level set by.
        self.engine = self.tk.GameShader()
        self.engine.use_logger(self.logger)

        # Don't keep this window glued above other tools; the pin button
        # toggles stay-on-top when needed.
        if hasattr(self.ui, "set_flags"):
            self.ui.set_flags(WindowStaysOnTopHint=False)

        self.image_files = None
        self.last_created = []  # what the last Create Network built (non-empty)

        self.ui.txt001.setText(self.msg_intro)

        # Stream the log into txt001 with HTML colorization; the redirect is
        # what makes the log's clickable action:// links work.
        self.logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        self.logger.setup_logging_redirect(self.ui.txt001)

        # Dispatch action:// links (e.g. select or graph the created material).
        if hasattr(self.ui.txt001, "anchorClicked"):
            self.ui.txt001.anchorClicked.connect(self._on_log_link_clicked)

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the log panel."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    def header_init(self, widget):
        """Initialize the header widget."""
        widget.menu.add(
            self.sb.registered_widgets.Label,
            setObjectName="lbl_graph_material",
            setText="Open in Editor",
            setToolTip="Graph the material in the shader editor "
            "(Maya: the Hypershade; Blender: the Shader Editor).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Assign to Selection",
            setObjectName="chk_assign_to_selection",
            setChecked=False,
            setToolTip="Assign the created material to the objects (in Maya, "
            "faces too) selected when Create Network is pressed.\n"
            "Skipped when the textures build several materials: set a "
            "Material Name to merge them into one.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Game Shader",
                body="Build a complete PBR material from a set of texture "
                "maps. Each map's type (Base Color, Normal, Roughness, "
                "Metallic, AO, Emissive, Opacity, ORM, MSAO ...) is detected "
                "from its file name and wired into the right input, with the "
                "conversion nodes it needs.",
                steps=[
                    "Set <b>Material Name</b> and an optional <b>Prefix / "
                    "Suffix</b> (the field's option box picks placement).",
                    "Pick an <b>Output Template</b>: its tooltip names the "
                    "target workflow and the platforms it ships to (UE / Unity "
                    "/ Godot / film, or glTF 2.0 for WebXR).",
                    "Pick the <b>Normal Map</b> convention (OpenGL / DirectX) "
                    "and the output <b>Ext</b> ('Profile default' leaves each "
                    "map's format to the template).",
                    "In Maya, pick a <b>Shader Type</b>: Stingray PBS / "
                    "Standard Surface / Open PBR. Blender builds a "
                    "Principled BSDF, already the OpenPBR model.",
                    "Press <b>Create Network</b> and select the texture files; "
                    "results stream into the log panel.",
                ],
                notes=[
                    "Several texture sets in one selection build <b>one "
                    "material per set</b>; set a <b>Material Name</b> to merge "
                    "them into one.",
                    "The template can <i>write new maps</i> (packing / format "
                    "conversion). In Blender that step needs Pillow, installed "
                    "into Blender's Python on first use.",
                    "<b>Open in Editor</b> in the header menu graphs the "
                    "resulting material; <b>Assign to Selection</b> assigns it "
                    "to the selection.",
                ],
            )
        )

    def lbl_graph_material(self):
        """Open in Editor: graph the material last built here, else the one the
        Material Name field names."""
        built = self.last_created
        if not built and self.mat_name:
            built = self.tk.MatUtils.get_scene_mats(inc=self.mat_name)
        if built:
            self.tk.MatUtils.graph_materials(built)
        elif self.mat_name:
            self.logger.warning(f"Material '{self.mat_name}' not found.")
        else:
            self.logger.warning("No material has been created yet.")

    @property
    def mat_name(self) -> str:
        """The Material Name field's text ('' derives the name from the textures)."""
        return self.ui.txt000.text().strip()

    @property
    def mat_prefix(self) -> str:
        """Return the affix text when it resolves as a prefix, else empty string."""
        if not hasattr(self.ui, "txt002"):
            return ""
        prefix, _ = self.ui.txt002.option_box.resolve_affix(default="prefix")
        return prefix

    @property
    def mat_suffix(self) -> str:
        """Return the affix text when it resolves as a suffix, else empty string."""
        if not hasattr(self.ui, "txt002"):
            return ""
        _, suffix = self.ui.txt002.option_box.resolve_affix(default="prefix")
        return suffix

    @property
    def normal_map_type(self) -> str:
        """The Normal Map combo's convention: 'OpenGL' or 'DirectX'."""
        return self.ui.cmb001.currentText() or "OpenGL"

    @property
    def output_extension(self) -> str:
        """Selected output extension, or '' when 'Profile default' is chosen.

        An empty string signals the caller to defer per-map format to the selected
        workflow profile's template rather than forcing one container for all maps.

        Returns:
            (str) The file extension in lowercase (e.g., 'png', 'jpg'), or ''.
        """
        text = self.ui.cmb003.currentText().lower()
        return "" if text.startswith("profile") else text

    @property
    def shader_type(self) -> Optional[str]:
        """The Shader Type combo's ``shader_type`` (Maya: 'stingray',
        'standard_surface' or 'open_pbr'); None on a host with one surface
        shader, which takes none."""
        if not self.engine.shader_type_choices():
            return None
        return self.ui.cmb004.currentData()

    @property
    def opacity_mode(self) -> Optional[str]:
        """The opacity graph the panel asks for.

        Returns:
            str | None: ``"transparent"`` (alpha blend), ``"masked"`` (alpha
            cutout), or ``"none"`` -- opacity ruled out, which retires the
            set's opacity sources instead of letting them pick the graph.
            None for Auto: a usable opacity source then builds as transparent,
            as it always has.
        """
        if hasattr(self.ui, "cmb005"):
            text = self.ui.cmb005.currentText().lower()
            if "masked" in text:
                return "masked"
            if "transparent" in text:
                return "transparent"
            if "none" in text:
                return "none"
        return None

    def cmb002_init(self, widget):
        """Initialize Presets"""
        if not widget.is_initialized:
            # Names + tooltips come from the OutputTemplates SSoT, shared with the
            # converter / compositor / mat_updater / scene exporter, so none of
            # them depends on the preset dict's internal shape.
            widget.clear()
            for name, description in ptk.OutputTemplates.profile_choices():
                widget.addItem(name)
                if description:
                    widget.setItemData(
                        widget.count() - 1, description, QtCore.Qt.ToolTipRole
                    )

    def cmb003_init(self, widget):
        """Initialize Output Format.

        Selecting 'Profile default' defers each map's container/bit-depth to the
        selected workflow profile's output template; a concrete format forces that
        container for all maps.
        """
        if not widget.is_initialized:
            # format_choices appends the sentinel LAST, preserving the existing
            # format indices — combobox state is persisted by index, so moving it
            # to the front would silently shift every saved selection by one.
            widget.add(
                ptk.OutputTemplates.format_choices(
                    sentinel=ptk.OutputTemplates.PROFILE_DEFAULT_LABEL
                )
            )

    def cmb004_init(self, widget):
        """Initialize Shader Type from the host's surface shaders.

        Blender has one, the Principled BSDF (already the OpenPBR model), so
        its engine offers no choice and the combo hides: a control picking
        between Maya shader nodes Blender never creates would be a fake one.
        """
        choices = self.engine.shader_type_choices()
        if not choices:
            widget.setVisible(False)
            return
        if not widget.is_initialized:
            # The engine's order: the combo saves its index.
            widget.clear()
            for label, shader_type in choices:
                widget.addItem(label, shader_type)

    def txt000_init(self, widget):
        """Material-name field — clearable back to the auto-derived name."""
        widget.option_box.clear_option = True

    def txt002_init(self, widget):
        """Add a prefix/suffix/auto-mode picker to the affix field."""
        widget.option_box.set_affix(
            default="prefix",
            on_change=lambda _mode, w=widget: self._apply_affix_placeholder(w),
            settings_key="game_shader_affix",  # ``txt002`` alone is too generic
            convention_key="material",  # fourth state: the shared convention
        )
        self._apply_affix_placeholder(widget)

    @staticmethod
    def _apply_affix_placeholder(widget):
        mode = widget.option_box.affix_mode
        if mode == "prefix":
            widget.setPlaceholderText("Prefix")
            widget.setToolTip(
                "Prefix prepended to the material name.\n"
                'Example: "MAT_" + "brick" → "MAT_brick".'
            )
        elif mode == "suffix":
            widget.setPlaceholderText("Suffix")
            widget.setToolTip(
                "Suffix appended to the material name.\n"
                'Example: "brick" + "_MAT" → "brick_MAT".'
            )
        elif mode == "convention":
            # The field is showing (and locked to) the shared convention, so
            # the placeholder would never be seen — name the source instead, so
            # a user wondering why they cannot type has the answer in the tip.
            widget.setPlaceholderText("Scene Convention")
            widget.setToolTip(
                "Following the shared naming convention for materials.\n"
                "Edit it in the Naming panel (Suffix By Type); every tool set "
                "to this mode follows.\n"
                "Click the button beside the field to type your own instead."
            )
        else:  # auto
            widget.setPlaceholderText("Affix")
            widget.setToolTip(
                "Affix — placement inferred from '_' position.\n"
                "  '_MAT' → suffix (appended)\n"
                "  'MAT_' → prefix (prepended)"
            )

    def b000(self):
        """Create Network: pick texture files and build their material(s)."""
        # Snapshot before the file dialog, so the assignment targets what was
        # selected when the button was pressed.
        selection = (
            list(self.tk.CoreUtils.selected_objects())
            if self.ui.header.menu.chk_assign_to_selection.isChecked()
            else None
        )

        # The scene project's texture folder, resolved when asked: the scene
        # can change while the panel stays open.
        image_files = self.sb.file_dialog(
            file_types=[f"*.{ext}" for ext in ptk.ImgUtils.texture_file_types],
            title="Select one or more image files to open.",
            start_dir=self.tk.DataNodes.scene_source_images_dir(),
        )
        if not image_files:
            return

        self.image_files = image_files
        self.ui.txt001.clear()

        template_name = self.ui.cmb002.currentText()
        # 'Profile default' (empty ext) → let the workflow profile drive per-map
        # format; a concrete ext overrides it for all maps.
        ext = self.output_extension
        options = dict(
            config=template_name,
            normal_type=self.normal_map_type,
            opacity_mode=self.opacity_mode,
            cleanup_base_color=False,  # Can be exposed in UI later if needed
            output_extension=ext or None,
            output_profile=template_name if not ext else None,
        )
        shader_type = self.shader_type
        if shader_type:  # a host with one surface shader takes none
            options["shader_type"] = shader_type

        def progress_adapter(p, m):
            # Surface progress in the footer and keep the UI responsive during
            # the long network build.
            self.ui.footer.setText(f"{m} ({int(p)}%)" if m else f"{int(p)}%")
            self.sb.QtWidgets.QApplication.instance().processEvents()

        result = self.engine.create_network(
            self.image_files,
            self.mat_name,
            prefix=self.mat_prefix,
            suffix=self.mat_suffix,
            progress_callback=progress_adapter,
            **options,
        )
        # One network, or one per texture set (a failed set is None).
        self.last_created = [m for m in ptk.make_iterable(result) if m]

        if selection is not None:
            self.engine.assign_network(self.last_created, selection)

        if not self.last_created:
            self.sb.message_box(
                "<hl>No PBR textures recognized</hl><br>Filenames must carry map "
                "types (BaseColor, Normal, Roughness, Metallic…)."
            )
