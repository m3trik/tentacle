# !/usr/bin/python
# coding=utf-8
import inspect
from qtpy import QtCore
import pythontk as ptk


# module = inspect.getmodule(inspect.currentframe())  # this module.
# path = ptk.get_object_path(module)  # this modules directory.


class Slots(QtCore.QObject):
    """Provides methods that can be triggered by widgets in the ui.
    Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

    If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
    @Slot(result=int, float)
    ex. def getFloatReturnInt(self, f):
                    return int(f)
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        """ """
        self.sb = kwargs.get("switchboard")
        try:
            self.sb.parent().left_mouse_double_click_ctrl.connect(
                self.repeat_last_command
            )
        except AttributeError:
            pass

    def repeat_last_command(self):
        """Repeat the last stored command."""
        method = self.sb.prev_slot

        if callable(method):
            widget = self.sb.get_widget_from_slot(method)
            widget.call_slot()
        else:
            print("No recent commands in history.")


# --------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
