# !/usr/bin/python
# coding=utf-8
import mayatk as mtk
from tentacle.tcl import Tcl


class TclMaya(Tcl):
    """Tcl class overridden for use with Autodesk Maya."""

    def __init__(self, parent=None, slot_source="slots/maya", *args, **kwargs):
        if getattr(self, "_initialized", False):
            return

        if not parent:
            try:
                parent = mtk.get_main_window()
            except Exception as error:
                print(f"Error getting main window: {error}")

        super().__init__(parent, slot_source=slot_source, *args, **kwargs)
        self._initialized = True


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
    main.show()


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
