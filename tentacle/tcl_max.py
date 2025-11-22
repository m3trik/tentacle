# !/usr/bin/python
# coding=utf-8
import sys

try:
    from pymxs import runtime as rt
except ImportError as error:
    print(error)
from tentacle.tcl import Tcl


class TclMax(Tcl):
    """Tcl class overridden for use with Autodesk 3ds Max."""

    def __init__(self, parent=None, slot_source="slots/max", *args, **kwargs):
        if not parent:
            try:
                parent = self.get_main_window()
            except Exception as error:
                print(__file__, error)

        super().__init__(parent, slot_source=slot_source, *args, **kwargs)

    @classmethod
    def get_main_window(cls):
        """Get the 3DS MAX main window."""
        main_window = next(
            (
                w.window()
                for w in cls.app.topLevelWidgets()
                if w.inherits("QMainWindow")
                and w.metaObject().className() == "QmaxApplicationWindow"
            ),
            lambda: (_ for _ in ()).throw(
                RuntimeError("Could not find QmaxApplicationWindow instance.")
            ),
        )

        if not main_window.objectName():
            main_window.setObjectName("MaxWindow")

        return main_window

    def showEvent(self, event):
        try:
            rt.enableAccelerators = False
        except Exception as error:
            print(error)

        super().showEvent(event)

    def hideEvent(self, event):
        try:
            rt.enableAccelerators = True
        except Exception as error:
            print(error)

        super().hideEvent(event)


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMax()
    main.show()


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
