# !/usr/bin/python
# coding=utf-8
from qtpy import QtWidgets, QtCore
from uitk import MarkingMenu


class TclBlender(MarkingMenu):
    """Marking Menu class overridden for use with Blender."""

    def __init__(self, parent=None, slot_source="slots/blender", *args, **kwargs):
        if not parent:
            try:
                parent = self.get_main_window()
            except Exception as error:
                print(__file__, error)

        super().__init__(
            parent, ui_source="ui", slot_source=slot_source, *args, **kwargs
        )

    @classmethod
    def get_main_window(cls):
        """Get Blender's main window object."""
        return QtWidgets.QApplication.instance().blender_widget

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
            if event.key() == self.key_undo and modifiers == QtCore.Qt.ControlModifier:
                import bpy

                bpy.ops.ed.undo()

        super().keyPressEvent(event)


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclBlender()
    main.show()


# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
