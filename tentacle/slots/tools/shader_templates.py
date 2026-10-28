# !/usr/bin/python
# coding=utf-8
"""Shader Templates: save a material's shader network as a reusable template
and rebuild it, its texture maps rebound by map type.

One Slots class for both hosts over the host toolkit's ``ShaderTemplates``
(``self.tk``): its ``store()`` holds the templates (Maya ships some, read-only;
the user's live in the user config), ``save_template`` captures the selection's
material and ``restore_template`` rebuilds one and reports what it built (Maya:
a shading network; Blender: a material, assigned to the selected meshes). A
thin driver: the panel picks, names and logs.
"""

import logging
import os

import pythontk as ptk

from tentacle import Slots


class ShaderTemplatesSlots(Slots, ptk.LoggingMixin):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.shader_templates

        self.image_files = None
        self.last_restored_nodes = None
        self._store = self.tk.ShaderTemplates.store()

        # INFO, not WARNING: the logger is redirected into txt001, so the info
        # lines ARE the user feedback (the run banners, saved paths).
        self.logger.setLevel("INFO")
        self.logger.hide_logger_name(True)
        self.logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        self.logger.setup_logging_redirect(self.ui.txt001)

        # Dispatch the action:// links the run summaries emit (the created
        # shader, the saved template).
        if hasattr(self.ui.txt001, "anchorClicked"):
            self.ui.txt001.anchorClicked.connect(self._on_log_link_clicked)

    @property
    def source_images_dir(self) -> str:
        """Where Load Texture Maps opens: the scene project's texture folder,
        resolved when asked (the scene can change while the panel is open)."""
        return self.tk.DataNodes.scene_source_images_dir()

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the log panel."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    def header_init(self, widget):
        """Initialize the header widget."""
        widget.setTitle("Shader Templates")
        widget.menu.add(
            self.sb.registered_widgets.Label,
            setObjectName="lbl_open_templates_dir",
            setText="Open Templates Directory",
            setToolTip="Open the directory holding your shader templates.",
        )
        widget.menu.add(
            self.sb.registered_widgets.Label,
            setObjectName="lbl_graph_material",
            setText="Graph Material",
            setToolTip="Open the last restored material in the shader editor.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Shader Templates",
                body="Save and restore shader networks as reusable templates. "
                "Your templates live in your user settings folder (Maya also "
                "ships a few, read-only).",
                steps=[
                    "Select a material (Blender: an object carrying one) to "
                    "capture its network.",
                    "Press <b>Save Template</b> and name it.",
                    "To restore, pick a template from the combo, optionally "
                    "<b>Load Texture Maps</b> to rebind by map type, and press "
                    "<b>Create Network</b> (Blender assigns the new material "
                    "to the selected meshes).",
                ],
                sections=[
                    (
                        "Combo menu",
                        [
                            "<b>Rename</b> / <b>Delete</b> a template of yours; "
                            "a shipped one is read-only.",
                            "<b>Open Template File</b> in the default editor.",
                        ],
                    ),
                    (
                        "Header menu",
                        [
                            "<b>Open Templates Directory</b>: reveal your "
                            "templates folder in the file manager.",
                            "<b>Graph Material</b>: open the most recently "
                            "restored material in the shader editor (Maya: the "
                            "Hypershade; Blender: the Shader Editor).",
                        ],
                    ),
                ],
            )
        )

    def lbl_graph_material(self):
        """Graph the last restored material in the host's shader editor."""
        if self.last_restored_nodes:
            self.tk.MatUtils.graph_materials(self.last_restored_nodes)
        else:
            self.logger.warning("No material has been restored yet.")

    def lbl_open_templates_dir(self):
        """Open the user's shader templates directory in the file manager."""
        ptk.open_explorer(str(self._store.user_dir), create_dir=True)

    def cmb002_init(self, widget):
        """Initialize the ComboBox for shader templates."""
        if not widget.is_initialized:
            widget.restore_state = True
            # Persist the pick by TEXT, not index: the list is rebuilt from
            # disk each show, so a stored index selects whichever template
            # occupies that row next session.
            widget.restore_by = "text"
            widget.refresh_on_show = True
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setObjectName="lbl000",
                setText="Rename",
                setToolTip="Rename the current template.",
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setObjectName="lbl001",
                setText="Delete",
                setToolTip="Delete the current template.",
            )
            widget.on_editing_finished.connect(
                lambda text: self.rename_template_safe(widget, text)
            )
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setObjectName="lbl002",
                setText="Open Template File",
                setToolTip="Open the selected template file in the default editor.",
            )
        self.refresh_templates(widget)

    def refresh_templates(self, widget):
        """List the templates, each carrying its file: shipped and the user's
        (a user template shadows a shipped one of the same name)."""
        widget.clear()
        for name in self._store.list():
            widget.addItem(name, str(self._store.path(name, self._store.source(name))))

    def _user_template(self, widget) -> str:
        """The selected template's name when it is the user's, else ``""``
        (logged): the shipped templates are read-only."""
        name = widget.currentText()
        if not name or widget.currentData() is None:
            self.logger.error("No template selected or data is missing.")
            return ""
        if self._store.source(name) != "user":
            self.logger.error(
                f"'{name}' is a shipped template and read-only; save a copy "
                "under another name to change it."
            )
            return ""
        return name

    @staticmethod
    def _sanitize_name(name) -> str:
        """Strip and drop filesystem-invalid characters from a template name."""
        return "".join(c for c in (name or "").strip() if c not in '\\/:*?"<>|')

    def rename_template_safe(self, widget, new_name):
        """Rename the selected (user) template to *new_name*, through the
        store: its sidecar and active pointer follow."""
        current = self._user_template(widget)
        if not current:
            return

        new_name = self._sanitize_name(new_name)
        if not new_name:
            self.logger.error("Invalid template name.")
            return
        if new_name == current:
            return  # unchanged: a no-op
        if self._store.exists(new_name):
            self.logger.error("A template with that name already exists.")
            return

        if not self._store.rename(current, new_name):
            self.logger.error(f"Template '{current}' could not be renamed.")
            return
        self.logger.info(f"Template renamed to: {self._store.path(new_name, 'user')}")
        widget.init_slot()

    def lbl000(self):
        """Make the ComboBox editable, to rename the template."""
        self.ui.cmb002.setEditable(True)
        self.ui.cmb002.menu.hide()

    def lbl001(self):
        """Delete the selected (user) template."""
        name = self._user_template(self.ui.cmb002)
        if not name:
            return
        template_path = self._store.path(name, "user")
        if self._store.delete(name):
            self.logger.info(f"Template deleted: {template_path}")
        self.ui.cmb002.init_slot()

    def lbl002(self):
        """Open the selected template in the default editor."""
        template_path = self.ui.cmb002.currentData()
        if not template_path:
            self.logger.error("No template selected.")
            return
        ptk.open_explorer(template_path)

    def b000(self):
        """Create Network: rebuild the selected template, rebinding the loaded
        texture maps by map type."""
        self.ui.txt001.clear()

        template_path = self.ui.cmb002.currentData()
        if not template_path:
            self.logger.error("No template selected.")
            return

        # The run banner as ONE record: each record renders as its own
        # paragraph in the output panel.
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.log_box(
                "CREATE SHADER NETWORK",
                [
                    f"Template : {self.ui.cmb002.currentText()}",
                    f"Textures : {len(self.image_files or [])}",
                ],
            )

        # The library reports what it built (its NETWORK CREATED summary, with
        # a link to the result), as it announces a save.
        restored = self.tk.ShaderTemplates.restore_template(
            template_path, self.image_files or [], logger=self.logger
        )
        self.last_restored_nodes = list(restored.values())

    def b001(self):
        """Load Texture Maps: pick the maps Create Network rebinds by type."""
        image_files = self.sb.file_dialog(
            file_types=[f"*.{ext}" for ext in ptk.ImgUtils.texture_file_types],
            title="Select one or more image files to open.",
            start_dir=self.source_images_dir,
        )

        if image_files:
            self.image_files = image_files
            self.ui.txt001.clear()
            # ONE record for the whole list: a line per file puts a paragraph
            # break between every texture.
            if self.logger.isEnabledFor(logging.INFO):
                self.logger.log_group(
                    f"Textures loaded ({len(image_files)})",
                    [ptk.truncate(img, 60) for img in image_files],
                )

    def b002(self):
        """Save Template: capture the selection's material network under a
        name the user gives."""
        templates = self.tk.ShaderTemplates
        selected = self.tk.CoreUtils.selected_objects()
        if not selected:
            self.logger.error(
                "Select a material (Blender: an object carrying one) to save "
                "its network."
            )
            return

        # The panel has no name field: prompt, offering the material's name.
        QtWidgets = self.sb.QtWidgets
        name, ok = QtWidgets.QInputDialog.getText(
            self.ui,
            "Save Template",
            "Template name:",
            text=templates.suggested_name(selected),
        )
        name = self._sanitize_name(name)
        if not ok or not name:
            self.logger.info("Save cancelled.")
            return

        if self._store.exists(name):
            self.logger.error(
                f"Template '{name}' already exists — pick another name, or "
                "rename/delete the existing one from the template dropdown's menu."
            )
            return
        file_path = str(self._store.path(name, "user"))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # The library announces the save (node count + a clickable path); the
        # panel adds nothing on top.
        templates.save_template(
            selected,
            file_path,
            exclude_types=list(templates.EXCLUDE_TYPES),
            logger=self.logger,
        )
        self.ui.cmb002.init_slot()
