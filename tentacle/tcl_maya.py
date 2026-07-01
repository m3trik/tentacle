# !/usr/bin/python
# coding=utf-8
import mayatk as mtk

# From this package:
from uitk.widgets.marking_menu._marking_menu import MarkingMenu
from uitk.handlers.external_app_handler import ExternalAppHandler
from mayatk.ui_utils.maya_ui_handler import MayaUiHandler


class TclMaya(MarkingMenu):
    """Marking Menu class overridden for use with Autodesk Maya."""

    def __init__(
        self, parent=None, slot_source="slots/maya", log_level="WARNING", **kwargs
    ):
        if not parent:
            try:
                parent = mtk.get_main_window()
            except Exception as error:
                print(f"Error getting main window: {error}")

        key_show = kwargs.pop("key_show", "F12")
        key_show = f"Key_{key_show}" if not key_show.startswith("Key_") else key_show

        # Default bindings for Maya (fully qualified)
        bindings = kwargs.pop("bindings", None) or {
            key_show: "hud#startmenu",  # Activation key + default UI
            f"{key_show}|LeftButton": "cameras#startmenu",
            f"{key_show}|MiddleButton": "editors#startmenu",
            f"{key_show}|RightButton": "main#startmenu",
            f"{key_show}|LeftButton|RightButton": "maya#startmenu",
        }

        super().__init__(
            parent,
            ui_source=("ui", "ui/maya_menus"),
            slot_source=slot_source,
            bindings=bindings,
            handlers={"ui": MayaUiHandler, "external_app": ExternalAppHandler},
            log_level=log_level,
            suppress_default_on_reentry=True,
            precompile=True,
            context_tags={"maya"},  # `requires` widget filtering (Phase-5 visibility)
            **kwargs,
        )

        # Register the Maya hotkey-collision checker on the bundled
        # ShortcutEditor whenever it's built. Lazily wired so the editor
        # module stays unimported until the user opens it.
        for _editor_name in ("shortcut", "global_shortcuts"):
            self.sb.editors.add_post_build_hook(
                _editor_name,
                lambda editor: editor.add_collision_checker(mtk.maya_collision_checker),
            )

        # External apps (compositor, photogrammetry, texture/mesh tools)
        # self-describe via ``extapps``'s ``uitk.external_apps.in_process``
        # entry points and are auto-registered by ExternalAppHandler on
        # construction — no per-app list here. ``context_tags={"maya"}``
        # (above) hides apps gated ``hide_maya`` (Substance/Marmoset, which
        # Maya serves through native mayatk bridges). ``extapps`` is an
        # optional, discovered provider (not a hard dep — it's off the
        # ecosystem release chain); its panels appear whenever it's installed
        # in the host env, and the provider entry in tentacle's pyproject lets
        # the handler install it on first launch where the interpreter allows.


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
    main.show()


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
