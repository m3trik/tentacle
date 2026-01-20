# !/usr/bin/python
# coding=utf-8
import mayatk as mtk
from uitk import MarkingMenu


class TclMaya(MarkingMenu):
    """Marking Menu class overridden for use with Autodesk Maya."""

    def __init__(self, parent=None, slot_source="slots/maya", **kwargs):
        if not parent:
            try:
                parent = mtk.get_main_window()
            except Exception as error:
                print(f"Error getting main window: {error}")

        key_show = kwargs.pop("key_show", "Key_F12")

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
            log_level="WARNING",
            **kwargs,
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
