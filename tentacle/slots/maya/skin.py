# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Skin(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.skin
        self.submenu = self.sb.skin_submenu
        print("Skin constructor:", self.ui, self.submenu)
        print(self.ui, repr(self.ui))

    def i025(self):
        from mayatk.ui_utils import maya_menu_handler

        handler = maya_menu_handler.MayaMenuHandler()
        menu = handler.create_tool_menu("edit_mesh")
        menu.show()
        cursor_pos = self.sb.QtGui.QCursor.pos()
        menu.move(
            cursor_pos - self.sb.QtCore.QPoint(menu.width() / 2, menu.height() / 2)
        )


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
