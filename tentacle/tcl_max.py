# !/usr/bin/python
# coding=utf-8
import sys

try:
    from pymxs import runtime as rt
except ImportError as error:
    print(error)
from tentacle.tcl import Tcl

instance = None


class TclMax(Tcl):
    """Tcl class overridden for use with Autodesk 3ds max.

    Parameters:
            parent = main application top level window object.
    """

    def __init__(self, parent=None, slot_source="slots/max", *args, **kwargs):
        """ """
        if not parent:
            try:
                parent = self.get_main_window()

            except Exception as error:
                print(__file__, error)

        super().__init__(parent, slot_source=slot_source, *args, **kwargs)

    @classmethod
    def get_main_window(cls):
        """Get the 3DS MAX main window.

        Returns:
                qtpy.QtWidgets.QMainWindow: 'QMainWindow' 3DS MAX main window.
        """
        # import qtmax
        # main_window = qtmax.GetQMaxMainWindow()

        main_window = next(
            (
                w.window()
                for w in cls.app.topLevelWidgets()
                if w.inherits("QMainWindow")
                and w.metaObject().className() == "QmaxApplicationWindow"
            ),
            lambda: (_ for _ in ()).throw(
                RuntimeError("Count not find QmaxApplicationWindow instance.")
            ),
        )

        if not main_window.objectName():
            main_window.setObjectName("MaxWindow")

        return main_window

    def showEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """
        try:
            rt.enableAccelerators = False

        except Exception as error:
            print(error)

        super().showEvent(event)  # super().showEvent(event)

    def hideEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """
        try:
            rt.enableAccelerators = True

        except Exception as error:
            print(error)

        super().hideEvent(event)  # super().hideEvent(event)


def show(*args, **kwargs):
    """Create and show a TclMax instance"""
    global instance
    if instance is None:
        instance = TclMax(*args, **kwargs)
        instance.show()
    elif not instance.isVisible():
        instance.show()
    else:  # Bring the existing instance to the front
        instance.raise_()
        instance.activateWindow()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMax()
    main.show("init#startmenu")
    # run app, show window, wait for input, then terminate program with a status code returned from app.
    exit_code = main.app.exec_()
    if exit_code != -1:
        sys.exit(exit_code)

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
