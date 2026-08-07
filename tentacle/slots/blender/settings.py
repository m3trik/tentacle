# !/usr/bin/python
# coding=utf-8
import html
import sys

from tentacle import SettingsMixin, SlotsBlender


class Settings(SettingsMixin, SlotsBlender):
    """Blender fork of the shared ``settings`` menu.

    Everything DCC-agnostic (header Package menu, the ecosystem updater, editor
    launchers, marking-menu binding combos) lives on ``SettingsMixin``. This class
    supplies the pip interpreter (Blender's bundled python — ``sys.executable``)
    and Reload Scripts (``tcl_blender.reload()`` — guarded in-place reload;
    ``script.reload()`` would tear down the Qt host).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    def _update_python_path(self) -> str:
        """The interpreter whose environment the updater checks and upgrades."""
        return sys.executable

    def tb001(self):
        """Reload Scripts (tear down, reload the tentacle ecosystem in place, re-register)."""
        from tentacle import tcl_blender

        try:
            count = tcl_blender.reload()
        except Exception as error:
            print(f"Tentacle reload failed: {error}")
            self.sb.message_box(
                "<b>Reload failed.</b><br><small>{}</small>".format(
                    html.escape(str(error))
                )
            )
            return
        print(f"tentacle: reloaded {count} module(s); re-registering on the next tick.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
