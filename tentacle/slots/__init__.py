# !/usr/bin/python
# coding=utf-8
import inspect
from PySide2 import QtCore
import pythontk as ptk


module = inspect.getmodule(inspect.currentframe())  # this module.
path = ptk.get_object_path(module)  # this modules directory.


class Slots(QtCore.QObject):
    """Provides methods that can be triggered by widgets in the ui.
    Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

    If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
    @Slot(result=int, float)
    ex. def getFloatReturnInt(self, f):
                    return int(f)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        """
        """
        self.sb = self.switchboard()

    def hide_main(fn):
        """A decorator that hides the stacked widget main window."""

        def wrapper(self, *args, **kwargs):
            fn(self, *args, **kwargs)  # execute the method normally.
            self.sb.parent().hide()  # Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.

        return wrapper


# --------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
