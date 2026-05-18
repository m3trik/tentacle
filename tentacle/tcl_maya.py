# !/usr/bin/python
# coding=utf-8
import mayatk as mtk

# From this package:
from uitk.widgets.marking_menu._marking_menu import MarkingMenu
from uitk.handlers.external_tool_handler import ExternalToolHandler
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
            handlers={"ui": MayaUiHandler, "external_tool": ExternalToolHandler},
            log_level=log_level,
            suppress_default_on_reentry=True,
            precompile=True,
            **kwargs,
        )

        # Register the Maya hotkey-collision checker on the bundled
        # HotkeyEditor whenever it's built. Lazily wired so the editor
        # module stays unimported until the user opens it.
        self.sb.editors.add_post_build_hook(
            "hotkey",
            lambda editor: editor.add_collision_checker(mtk.maya_collision_checker),
        )

        # External tools — two paths:
        #
        # 1. Auto-discovery via ``importlib.metadata.entry_points`` runs
        #    inside ExternalToolHandler.__init__. Tools whose installed
        #    metadata advertises ``uitk.external_tools[.in_process]``
        #    are picked up with zero changes here. Once map_compositor
        #    and metashape_workflow ship with their entry-point metadata
        #    on PyPI / git, the manual block below collapses to nothing.
        #
        # 2. Manual registration — for tools that may not be installed
        #    yet. ``install_spec`` lets the handler pip-install them
        #    on first launch. Re-registration of a name discovered in
        #    pass 1 is intentional and idempotent (the manual call
        #    wins, carrying ``install_spec`` for the on-demand install).
        self.sb.handlers.external_tool.register(
            "map_compositor",
            module="map_compositor",
            entry="MapCompositorUI",
            install_spec="map_compositor",
            mode="in_process",
        )
        self.sb.handlers.external_tool.register(
            "metashape_workflow",
            module="metashape_workflow",
            entry="MetashapeWorkflowUI",
            install_spec="git+https://github.com/m3trik/metashape_workflow",
            mode="in_process",
        )


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
    main.show()


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
