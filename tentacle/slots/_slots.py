# !/usr/bin/python
# coding=utf-8
from qtpy import QtCore, QtWidgets, QtGui


class Slots(QtCore.QObject):
    """Provides methods that can be triggered by widgets in the ui.
    Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

    If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
    @Slot(result=int, float)
    ex. def getFloatReturnInt(self, f):
                    return int(f)
    """

    _repeat_last_shortcut: QtWidgets.QShortcut = None

    def __init__(self, switchboard):
        super().__init__()
        """ """
        self.sb = switchboard

        # Connect to configurable change signal to update shortcut dynamically
        self.sb.configurable.repeat_last_shortcut.changed.connect(
            self._update_repeat_last_shortcut
        )
        # Initialize shortcut with current value (or default)
        self._update_repeat_last_shortcut()

    def _update_repeat_last_shortcut(self, _value=None):
        """Update the repeat last shortcut based on configurable value."""
        # Get the configured sequence (default to Ctrl+Shift+R)
        sequence = self.sb.configurable.repeat_last_shortcut.get("Ctrl+Shift+R")

        # Clean up existing shortcut
        if self._repeat_last_shortcut is not None:
            self._repeat_last_shortcut.activated.disconnect()
            self._repeat_last_shortcut.deleteLater()
            self._repeat_last_shortcut = None

        if not sequence:
            return  # Disabled if empty

        # Find appropriate parent widget for the shortcut
        parent = self.sb.parent()
        if parent is None:
            return

        # Create new shortcut
        self._repeat_last_shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(sequence), parent
        )
        self._repeat_last_shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        self._repeat_last_shortcut.activated.connect(self.repeat_last_command)

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
