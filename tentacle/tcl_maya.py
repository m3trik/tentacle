# !/usr/bin/python
# coding=utf-8
import sys
import mayatk as mtk
from tentacle.tcl import Tcl

instance = None


class TclMaya(Tcl):
    """Tcl class overridden for use with Autodesk Maya.

    Parameters:
        parent = Application top level window instance.
    """

    def __init__(self, parent=None, slot_location="slots/maya", *args, **kwargs):
        """ """
        if not parent:
            try:
                parent = mtk.get_main_window()

            except Exception as error:
                print(__file__, error)

        super().__init__(parent, slot_location=slot_location, *args, **kwargs)


def show(*args, **kwargs):
    """Create and show a TclMaya instance"""
    global instance
    if instance is None:
        instance = TclMaya(*args, **kwargs)
        instance.show()
    elif not instance.isVisible():
        instance.show()
    else:  # Bring the existing instance to the front
        instance.raise_()
        instance.activateWindow()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
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
