# !/usr/bin/python
# coding=utf-8
import sys
from PySide2 import QtWidgets, QtCore
from tentacle.tcl import Tcl


INSTANCES = {}


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

    def showEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """
        super().showEvent(event)  # super().showEvent(event)

    def hideEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """
        super().hideEvent(event)  # super().hideEvent(event)


# --------------------------------------------------------------------------------------------


def getInstance(instanceID=None, *args, **kwargs):
    """Get an instance of this class using a given instanceID.
    The instanceID is either the object or the object's id.

    Parameters:
            instanceID () = The instanceID can be any immutable type.
            args/kwargs () = The args to be passed to the class instance when it is created.

    Returns:
            (obj) An instance of this class.

    Example: tentacle = getInstance(id(0), key_show='Key_F12') #returns the class instance with an instance ID of the value of `id(0)`.
    """
    import inspect

    if instanceID is None:
        instanceID = inspect.stack()[1][3]
    try:
        return INSTANCES[instanceID]

    except KeyError:
        INSTANCES[instanceID] = TclBlender(*args, **kwargs)
        return INSTANCES[instanceID]


def show(instanceID=None, *args, **kwargs):
    """Expands `getInstance` to get and then show an instance in a single command."""
    inst = getInstance(instanceID=instanceID, *args, **kwargs)
    inst.show()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclBlender()
    main.show("init#startmenu")

    # run app, show window, wait for input, then terminate program with a status code returned from app.
    exit_code = main.app.exec_()
    if exit_code != -1:
        sys.exit(exit_code)

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
