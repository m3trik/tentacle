# !/usr/bin/python
# coding=utf-8
"""Image to Plane: batch-create textured planes from image files.

One Slots class for both hosts over the host toolkit's ``ImageToPlane``
(``self.tk``): one plane per image, sized to its aspect ratio, with the image
wired into a new material (Maya: Stingray PBS or Standard Surface; Blender:
Principled BSDF). Create and Remove are one undo step each, and Create leaves
the result selected.
"""

import pythontk as ptk

from tentacle import Slots


class ImageToPlaneSlots(Slots):
    IMAGE_FILTER = "Image Files (*.png *.jpg *.jpeg *.tga *.bmp *.tif *.tiff *.exr *.hdr);;All Files (*.*)"

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.image_to_plane

        # The host's material types, in the combo's saved order (it saves an
        # index): Maya's Stingray PBS / Standard Surface; Blender's one, the
        # Principled BSDF, shown disabled since there is nothing to choose.
        mat_types = self.tk.ImageToPlane.MAT_TYPES
        combo = self.ui.cmb_mat_type
        combo.clear()
        for label, value in mat_types:
            combo.addItem(label, value)
        combo.setEnabled(len(mat_types) > 1)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def header_init(self, widget):
        """Configure header menu."""
        widget.menu.add(
            "QCheckBox",
            setText="Group Result",
            setObjectName="chk_group_result",
            setChecked=False,
            setToolTip="Parent all created planes under a single group "
            "(an Empty in Blender).",
        )

        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Image to Plane",
                body="Creates textured planes from image files — one plane "
                "per image, sized to its aspect ratio, with the image as a new "
                "material's Base Color (and opacity when the image has alpha).",
                steps=[
                    "Press <b>Browse…</b> to queue one or more image files.",
                    "Pick a <b>Material Type</b> (Maya: Stingray PBS / Standard "
                    "Surface; Blender builds a Principled BSDF, so the choice is "
                    "disabled there).",
                    "Set the <b>Material Affix</b> (default <code>_MAT</code>). "
                    "The affix option box selects Suffix / Prefix / Auto, or "
                    "the shared naming convention.",
                    "Set the <b>Plane Height</b> in scene units (width is "
                    "derived from each image's aspect ratio).",
                    "Press <b>Create Planes</b>.",
                ],
                sections=[
                    (
                        "Menu options",
                        [
                            "<b>Group Result</b> — parent all created planes under "
                            "a single group (an Empty in Blender).",
                        ],
                    ),
                ],
                notes=[
                    "Use <b>Remove Selected</b> to delete planes and their "
                    "auto-created materials together.",
                ],
            )
        )

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def txt_suffix_init(self, widget):
        """Add a prefix/suffix/auto-mode picker to the affix field."""
        widget.option_box.clear_option = True
        widget.option_box.set_affix(
            default="auto",
            on_change=lambda _mode, w=widget: self._apply_affix_placeholder(w),
            convention_key="material",  # fourth state: the shared convention
        )
        self._apply_affix_placeholder(widget)

    @staticmethod
    def _apply_affix_placeholder(widget):
        mode = widget.option_box.affix_mode
        if mode == "prefix":
            widget.setPlaceholderText("Material Prefix")
            widget.setToolTip(
                "Prefix prepended to the image name for material naming.\n"
                'Example: image "brick" with prefix "MAT_" → material "MAT_brick".'
            )
        elif mode == "suffix":
            widget.setPlaceholderText("Material Suffix")
            widget.setToolTip(
                "Suffix appended to the image name for material naming.\n"
                'Example: image "brick" with suffix "_MAT" → material "brick_MAT".'
            )
        elif mode == "convention":
            widget.setPlaceholderText("Scene Convention")
            widget.setToolTip(
                "Following the shared naming convention for materials.\n"
                "Edit it in the Naming panel (Suffix By Type); every tool set "
                "to this mode follows.\n"
                "Click the button beside the field to type your own instead."
            )
        else:  # auto
            widget.setPlaceholderText("Material Affix")
            widget.setToolTip(
                "Material affix — placement inferred from '_' position.\n"
                "  '_MAT' → suffix (appended)\n"
                "  'MAT_' → prefix (prepended)"
            )

    def _material_affix(self):
        """The field's ``(prefix, suffix)``; empty, the shared convention's.

        An empty field falls back to the shared convention rather than a
        literal, so the one place that defines "what marks a material" governs
        here too. Mode-aware: a user who switched to Prefix and cleared the
        text still gets a sensible value on the right side."""
        option_box = self.ui.txt_suffix.option_box
        prefix, suffix = option_box.resolve_affix(default="suffix")
        if not prefix and not suffix:
            fallback = ptk.NamingConvention.affix("material").strip("_")
            if option_box.affix_mode == "prefix":
                prefix = f"{fallback}_"
            else:
                suffix = f"_{fallback}"
        return prefix, suffix

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def _queued(self) -> list:
        """The queued image paths, in list order."""
        files = self.ui.lst_files
        return [files.item(i).text() for i in range(files.count())]

    def b000(self):
        """Browse…: queue image files from a file dialog (no duplicates)."""
        from qtpy.QtWidgets import QFileDialog

        paths, _ = QFileDialog.getOpenFileNames(
            self.ui,
            "Select Images",
            "",
            self.IMAGE_FILTER,
        )
        if not paths:
            return
        queued = set(self._queued())
        for path in paths:
            if path not in queued:
                self.ui.lst_files.addItem(path)
                queued.add(path)
        self.ui.footer.setText(f"{self.ui.lst_files.count()} image(s) queued.")

    def b004(self):
        """Clear: empty the queue."""
        self.ui.lst_files.clear()
        self.ui.footer.setText("File list cleared.")

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def b001(self):
        """Create Planes: one textured plane per queued image."""
        image_paths = self._queued()
        if not image_paths:
            self.ui.footer.setText("No images queued. Use Browse to add files.")
            return
        prefix, suffix = self._material_affix()
        try:
            results = self.tk.ImageToPlane.create(
                image_paths,
                mat_type=self.ui.cmb_mat_type.currentData(),
                suffix=suffix,
                prefix=prefix,
                plane_height=self.ui.spn_height.value(),
                group=self.ui.header.menu.chk_group_result.isChecked(),
            )
        except Exception as e:
            self.ui.footer.setText(f"Error: {e}")
            return

        names = [name for name in results if name != "__group__"]
        if not names:
            self.ui.footer.setText("No planes created: no queued image could be read.")
            return
        label = ", ".join(names[:5])
        if len(names) > 5:
            label += f" … (+{len(names) - 5} more)"
        self.ui.footer.setText(f"Created {len(names)} plane(s): {label}")

    # ------------------------------------------------------------------
    # Manage
    # ------------------------------------------------------------------

    def b002(self):
        """Remove Selected: delete the selected planes and their materials."""
        objects = self.tk.CoreUtils.selected_objects()
        if not objects:
            self.ui.footer.setText("Select planes to remove.")
            return
        try:
            removed = self.tk.ImageToPlane.remove(objects)
        except Exception as e:
            self.ui.footer.setText(f"Error: {e}")
            return
        self.ui.footer.setText(f"Removed {removed} plane(s).")
