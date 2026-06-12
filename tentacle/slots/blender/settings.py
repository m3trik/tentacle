# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender._slots_blender import SlotsBlender


class Settings(SlotsBlender):
    """Blender port of the shared ``settings`` menu.

    The package/editor controls (Update, UI Style / Hotkey / Browser editors, reset marking-menu
    bindings) are DCC-agnostic uitk switchboard features and port directly. Live package reload
    uses a Maya-specific mechanism upstream and is deferred for Blender.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    def header_init(self, widget):
        if not widget.is_initialized:
            widget.menu.add(self.sb.registered_widgets.Separator, setTitle="Package")
            widget.menu.add(
                self.sb.registered_widgets.PushButton, setText="Update Package",
                setObjectName="tb000", setToolTip="Check for Tentacle package updates.",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton, setText="Reload Scripts",
                setObjectName="tb001",
                setToolTip="Reload Tentacle and its dependencies (not yet wired for Blender).",
            )

    def tb000(self):
        """Update Package — Maya's updater shells out to mayapy; needs Blender's bundled
        python wired into ptk.PackageManager. Deferred."""
        self.sb.message_box("Package update check is not yet implemented for Blender.")

    def tb001(self):
        """Reload Scripts — live reload uses a Maya-specific mechanism; not yet ported to Blender."""
        self.sb.message_box("Reload Scripts is not yet implemented for Blender.")

    def b020(self):
        """UI Style Editor"""
        self.sb.editors.show("style")

    def b021(self):
        """Hotkey Editor"""
        self.sb.editors.show("hotkey")

    def b022(self):
        """UI Browser"""
        self.sb.editors.show("browser")

    def b_reset_bindings(self):
        """Reset marking-menu bindings to defaults."""
        marking_menu = self.sb.handlers.marking_menu
        defaults = getattr(marking_menu, "default_bindings", {}) if marking_menu else {}
        self.sb.configurable.marking_menu_bindings.set(defaults)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
