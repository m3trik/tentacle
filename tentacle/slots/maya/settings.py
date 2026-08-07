# !/usr/bin/python
# coding=utf-8
import html
import os
import sys

import mayatk as mtk

# From this package:
from tentacle import SettingsMixin, SlotsMaya


class Settings(SettingsMixin, SlotsMaya):
    """Maya fork of the shared ``settings`` menu.

    Everything DCC-agnostic (header Package menu, the ecosystem updater, editor
    launchers, marking-menu binding combos) lives on ``SettingsMixin``. This class
    supplies the pip interpreter (mayapy) and Reload Scripts.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    def _update_python_path(self) -> str:
        """The interpreter whose environment the updater checks and upgrades."""
        return os.path.join(mtk.get_env_info("install_path"), "bin", "mayapy.exe")

    def tb001(self):
        """Reload Tentacle package with its dependencies."""
        state = self._teardown_tentacle_instance()

        # Reload dependencies first, then tentacle
        modules = [m for m in ("pythontk", "mayatk", "uitk") if m in sys.modules]
        modules.append("tentacle")

        try:
            reloaded = mtk.MayaConnection.reload_modules(modules)
        except Exception as error:
            print(f"Tentacle reload failed: {error}")
            self.sb.message_box(
                "<b>Reload failed.</b><br><small>{}</small>".format(
                    html.escape(str(error))
                )
            )
            return

        self._restore_tentacle_instance(state)

        self.sb.message_box(
            f"<b>Reload complete.</b><br><small>{len(reloaded)} module(s) refreshed.</small>"
        )

    def _teardown_tentacle_instance(self):
        state = {"was_visible": False, "ui_name": None}

        uitk_module = sys.modules.get("uitk.widgets.marking_menu")
        if not uitk_module:
            return state

        MarkingMenu = getattr(uitk_module, "MarkingMenu", None)
        if MarkingMenu is None:
            return state

        instance = getattr(MarkingMenu, "_instances", {}).get(MarkingMenu)
        if instance is None:
            return state

        try:
            state["was_visible"] = instance.isVisible()
            instance.hide()
        except Exception:
            pass

        try:
            current_ui = getattr(getattr(instance, "sb", None), "current_ui", None)
            if current_ui is not None:
                state["ui_name"] = getattr(current_ui, "objectName", lambda: None)()
        except Exception:
            pass

        try:
            instance.deleteLater()
        except Exception:
            pass

        if hasattr(MarkingMenu, "_submenu_cache"):
            try:
                MarkingMenu._submenu_cache.clear()
            except Exception:
                pass

        if hasattr(MarkingMenu, "reset_instance"):
            try:
                MarkingMenu.reset_instance()
            except Exception:
                pass

        try:
            MarkingMenu._instances.pop(MarkingMenu, None)
        except Exception:
            pass

        return state

    def _restore_tentacle_instance(self, state):
        if not state.get("was_visible"):
            return

        try:
            from tentacle import TclMaya
        except Exception as error:
            print(f"Tentacle restore skipped: {error}")
            return

        try:
            new_instance = TclMaya()
            target_ui = state.get("ui_name") or "hud#startmenu"
            try:
                new_instance.show(target_ui)
            except Exception:
                new_instance.show()
        except Exception as error:
            print(f"Tentacle restore failed: {error}")


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
