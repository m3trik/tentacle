# !/usr/bin/python
# coding=utf-8
import bpy
from tentacle.slots.blender._slots_blender import SlotsBlender


class Preferences(SlotsBlender):
    """Blender port of the shared ``preferences`` menu.

    Working units (length) and frame rate map onto ``scene.unit_settings`` / ``scene.render.fps``;
    autosave maps onto Blender's user filepaths prefs. The Maya preference windows (color, hotkeys,
    plug-ins) open Blender's Preferences editor instead.
    """

    # Blender metric length units (combo label -> length_unit enum).
    _LENGTH_UNITS = {
        "Millimeter": "MILLIMETERS",
        "Centimeter": "CENTIMETERS",
        "Meter": "METERS",
        "Kilometer": "KILOMETERS",
    }
    _FPS_OPTIONS = [24, 25, 30, 48, 60]

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.preferences
        self.submenu = self.sb.loaded_ui.preferences_submenu

    @staticmethod
    def _open_preferences(section=None):
        """Open Blender's Preferences editor, optionally on a specific section."""
        if section:
            try:
                bpy.context.preferences.active_section = section
            except (TypeError, AttributeError):
                pass
        try:
            bpy.ops.screen.userpref_show()
        except Exception:
            pass

    # ------------------------------------------------------------------ cmb001  Linear units
    def cmb001_init(self, widget):
        widget.add(self._LENGTH_UNITS)
        current = bpy.context.scene.unit_settings.length_unit
        labels = list(self._LENGTH_UNITS)
        match = next((l for l, u in self._LENGTH_UNITS.items() if u == current), None)
        if match:
            widget.setCurrentIndex(labels.index(match))

    def cmb001(self, index, widget):
        """Set Working Units: Linear"""
        unit = widget.currentData()
        us = bpy.context.scene.unit_settings
        us.system = "METRIC"
        us.length_unit = unit

    # ------------------------------------------------------------------ cmb002  Frame rate
    def cmb002_init(self, widget):
        widget.add({f"{f} fps": f for f in self._FPS_OPTIONS})
        fps = bpy.context.scene.render.fps
        if fps in self._FPS_OPTIONS:
            widget.setCurrentIndex(self._FPS_OPTIONS.index(fps))

    def cmb002(self, index, widget):
        """Set Working Units: Time (frame rate)"""
        bpy.context.scene.render.fps = int(widget.currentData())

    # ------------------------------------------------------------------ s000/s001  Autosave
    def s000_init(self, widget):
        if not widget.is_initialized:
            widget.setValue(bpy.context.preferences.filepaths.save_version)
            widget.valueChanged.connect(
                lambda v: setattr(bpy.context.preferences.filepaths, "save_version", int(v))
            )

    def s001_init(self, widget):
        if not widget.is_initialized:
            fp = bpy.context.preferences.filepaths
            widget.setValue(fp.auto_save_time)

            def _update(value):
                fp.use_auto_save_temporary_files = value > 0
                if value > 0:
                    fp.auto_save_time = int(value)

            widget.valueChanged.connect(_update)

    # ------------------------------------------------------------------ b-slots (open prefs)
    def b001(self):
        """Color Settings → Blender Preferences (Themes)."""
        self._open_preferences("THEMES")

    def b008(self):
        """Hotkeys → Blender Preferences (Keymap)."""
        self._open_preferences("KEYMAP")

    def b009(self):
        """Plug-In Manager → Blender Preferences (Add-ons)."""
        self._open_preferences("ADDONS")

    def b010(self):
        """Settings/Preferences → Blender Preferences (Interface)."""
        self._open_preferences("INTERFACE")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
