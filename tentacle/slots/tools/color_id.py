# !/usr/bin/python
# coding=utf-8
"""Color ID: color-code objects across channels from a swatch palette.

One Slots class for both hosts over the host toolkit's ``ColorId``
(``self.tk``), which applies, selects by, reads and resets the colors (Set
Color and Reset are one undo step each). The channel checkboxes name the same
channels in both hosts; how each is stored is the library's: Maya's wireframe
override and objectSets, Blender's object color and collections.
"""

from tentacle import Slots


class ColorIdSlots(Slots):
    _DEFAULT_PRESET = "default"

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.color_id

        self.button_grp = self.sb.create_button_groups(self.ui, "chk000-11")
        buttons = self.button_grp.buttons()
        palette = self.tk.ColorId.DEFAULT_SWATCH_COLORS

        for i, button in enumerate(buttons):
            button._initialColor = self.sb.QtGui.QColor(*palette[i % len(palette)])
            button.keep_square = True  # square swatches that track column width
            button.settings = self.ui.settings
        self.ui.chk000.setChecked(True)

    # ── Preset I/O ─────────────────────────────────────────────────────────

    def _export_swatch_colors(self) -> dict:
        """``PresetManager.metadata_provider`` — capture current swatch colors."""
        return {"swatches": [btn.color.name() for btn in self.button_grp.buttons()]}

    def _import_swatch_colors(self, meta: dict) -> None:
        """``PresetManager.on_metadata_loaded`` — apply colors from a preset."""
        colors = (meta or {}).get("swatches") or []
        for btn, hex_color in zip(self.button_grp.buttons(), colors):
            btn.color = self.sb.QtGui.QColor(hex_color)

    @staticmethod
    def _hex_from_rgb(rgb) -> str:
        r, g, b = rgb
        return f"#{int(r):02X}{int(g):02X}{int(b):02X}"

    def _ensure_default_preset(self, presets) -> None:
        """Write the factory-default preset on first use if it's missing."""
        if presets.exists(self._DEFAULT_PRESET):
            return
        palette = self.tk.ColorId.DEFAULT_SWATCH_COLORS
        original = presets.metadata_provider
        presets.metadata_provider = lambda: {
            "swatches": [self._hex_from_rgb(rgb) for rgb in palette]
        }
        try:
            presets.save(self._DEFAULT_PRESET)
        finally:
            presets.metadata_provider = original

    def header_init(self, widget):
        """Configure header help text and preset combobox."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Color ID",
                body="Color-code objects through any combination of four "
                "channels: the outliner text color, a wireframe tint, vertex "
                "colors and an ID material.",
                steps=[
                    "Click a palette swatch to pick the active color (right-"
                    "click a swatch to change its color).",
                    "Check the channels to act on: <b>Outliner</b>, "
                    "<b>Wireframe</b>, <b>Vertex</b>, <b>Material</b>, and "
                    "<b>Set Per Color</b> to also group each color's objects. "
                    "They scope <i>every</i> action below.",
                    "Select objects and press <b>Set Color</b>.",
                    "<b>Select By Color</b> selects the objects carrying the "
                    "active color on the checked channels.",
                ],
                sections=[
                    (
                        "Other actions",
                        [
                            "<b>Get Color</b> — read the selected object's color "
                            "from the checked channels into the active swatch "
                            "(Maya: the last selected; Blender: the active object).",
                            "<b>Reset</b> — clear the checked channels on the "
                            "selection (every object in the scene with "
                            f"{self.sb.tooltip.kbd('Ctrl')}-click); unchecked "
                            "channels are left untouched.",
                        ],
                    ),
                    (
                        "Per host",
                        [
                            "<b>Material</b> assigns one flat ID material per "
                            "color in place of the object's materials.",
                            "In Blender, <b>Wireframe</b> is the object's viewport "
                            "color, and Set Color points the viewport shading at "
                            "the channels it wrote so the color shows.",
                            "<b>Set Per Color</b> groups into an objectSet in "
                            "Maya, a color-tagged collection in Blender.",
                        ],
                    ),
                    (
                        "Presets",
                        [
                            "The header menu's preset combo saves / restores "
                            "swatch palettes. Use <b>Save</b> to capture the "
                            "current colors; pick a preset to restore them.",
                        ],
                    ),
                ],
            )
        )
        # Preset combobox — swatches aren't standard widgets, so colors
        # are carried in metadata rather than per-widget value reads. Each
        # host keeps its own palettes, in the store its library names.
        widget.menu.add_presets = True
        widget.menu.presets.preset_dir = self.tk.ColorId.SWATCH_PRESET_DIR
        widget.menu.presets.metadata_provider = self._export_swatch_colors
        widget.menu.presets.on_metadata_loaded = self._import_swatch_colors
        self._ensure_default_preset(widget.menu.presets)

    # ── helpers ────────────────────────────────────────────────────────────

    def _selected_objects(self) -> list:
        """The current selection, or ``[]`` (and why, said) when it is empty."""
        objects = self.tk.CoreUtils.selected_objects()
        if not objects:
            self.sb.message_box("No objects selected.")
        return objects

    @property
    def selected_button(self):
        """The checked swatch in the palette group, or None."""
        for button in self.button_grp.buttons():
            if button.isChecked():
                return button
        return None

    @property
    def target_color(self):
        """The active swatch's color as 0-1 ``(r, g, b)``, or None without one."""
        button = self.selected_button
        if button is None:
            return None
        color = button.color
        if hasattr(color, "redF"):  # a QColor
            return (color.redF(), color.greenF(), color.blueF())
        return tuple(color[:3])  # already an (r, g, b) 0-1 tuple

    @staticmethod
    def _rgb255(color) -> tuple:
        """A 0-1 ``(r, g, b)`` as 0-255 ints, clamped."""
        return tuple(max(0, min(255, int(c * 255 + 0.5))) for c in color[:3])

    def _channels(self) -> dict:
        """Current channel checkbox states — the scope EVERY action honors.

        ``chk012`` Wireframe · ``chk013`` Outliner · ``chk014`` Material ·
        ``chk015`` Vertex · ``chk016`` Set Per Color."""
        return {
            "wireframe": self.ui.chk012.isChecked(),
            "outliner": self.ui.chk013.isChecked(),
            "material": self.ui.chk014.isChecked(),
            "vertex": self.ui.chk015.isChecked(),
            "set": self.ui.chk016.isChecked(),
        }

    def _channels_or_warn(self):
        """:meth:`_channels`, or None (with a prompt) when the user has enabled none.

        Every action is channel-scoped, so with nothing checked there is nothing to do —
        and Select By Color would answer "no matches" by clearing the selection."""
        channels = self._channels()
        if not any(channels.values()):
            self.sb.message_box("No channels enabled.")
            return None
        return channels

    @staticmethod
    def _checks(channels: dict) -> dict:
        """The channels as the engine's read keywords (Select By / Get Color)."""
        return {
            "check_wireframe_color": channels["wireframe"],
            "check_outliner_color": channels["outliner"],
            "check_material_color": channels["material"],
            "check_vertex_color": channels["vertex"],
            "check_set": channels["set"],
        }

    # ── buttons ────────────────────────────────────────────────────────────

    def b000(self) -> None:
        """Reset: clear the ENABLED channels on the selection (Ctrl+click: every
        object in the scene). An unchecked channel is never touched."""
        channels = self._channels_or_warn()
        if channels is None:
            return
        if self.sb.app.keyboardModifiers() == self.sb.QtCore.Qt.ControlModifier:
            objects = self.tk.ColorId.scene_objects()
        else:
            objects = self._selected_objects()
        if not objects:
            return
        self.tk.ColorId.reset_colors(
            objects,
            reset_wireframe=channels["wireframe"],
            reset_outliner=channels["outliner"],
            reset_material=channels["material"],
            reset_vertex=channels["vertex"],
            reset_sets=channels["set"],
        )

    def b001(self) -> None:
        """Set Color: apply the active color to the selection on the enabled channels."""
        channels = self._channels_or_warn()
        if channels is None:
            return
        objects = self._selected_objects()
        color = self.target_color
        if not objects or color is None:
            return
        self.tk.ColorId.apply_color(
            objects,
            color=color,
            apply_to_wireframe=channels["wireframe"],
            apply_to_vertex=channels["vertex"],
            apply_to_outliner=channels["outliner"],
            apply_to_material=channels["material"],
            set_per_color=channels["set"],
        )

    def b002(self) -> None:
        """Select By Color: select the objects carrying the active color on the
        enabled channels (none found clears the selection)."""
        channels = self._channels_or_warn()
        if channels is None:
            return
        color = self.target_color
        if color is None:
            return
        self.tk.ColorId.select_by_color(color, **self._checks(channels))

    def b003(self) -> None:
        """Get Color: read the selected object's color on the enabled channels into
        the active swatch (the host's lead object: Maya's last selected, Blender's
        active)."""
        channels = self._channels_or_warn()
        if channels is None:
            return
        button = self.selected_button
        obj = self.tk.ColorId.lead_object()
        if obj is None or button is None:
            self.sb.message_box("Select an object and a swatch first.")
            return
        color = self.tk.ColorId.get_color(obj, **self._checks(channels))
        if color is None:
            self.sb.message_box(
                "No color found on the selected object's enabled channels."
            )
            return
        button.color = self.sb.QtGui.QColor(*self._rgb255(color))
