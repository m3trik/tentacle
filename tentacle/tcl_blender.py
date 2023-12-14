# !/usr/bin/python
# coding=utf-8
import sys
from PySide2 import QtWidgets, QtCore
from tentacle.tcl import Tcl

instance = None


class TclBlender(Tcl):
    """Tcl class overridden for use with Blender.

    Parameters:
            parent = Application top level window instance.
    """

    def __init__(self, parent=None, slot_location="slots/blender", *args, **kwargs):
        """ """
        if not parent:
            try:
                parent = self.get_main_window()

            except Exception as error:
                print(__file__, error)

        super().__init__(parent, slot_location=slot_location, *args, **kwargs)

    @classmethod
    def get_main_window(cls):
        """Get blender's main window object.

        Returns:
                (QWidget)
        """
        main_window = QtWidgets.QApplication.instance().blender_widget

        return main_window

    def keyPressEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """
        if not event.isAutoRepeat():
            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()

            if event.key() == self.key_undo and modifiers == QtCore.Qt.ControlModifier:
                import bpy

                bpy.ops.ed.undo()

        super().keyPressEvent(event)


def show(*args, **kwargs):
    """Create and show a TclBlender instance"""
    global instance
    if instance is None:
        instance = TclBlender(*args, **kwargs)
        instance.show()
    elif not instance.isVisible():
        instance.show()
    else:  # Bring the existing instance to the front
        instance.raise_()
        instance.activateWindow()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclBlender()
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
