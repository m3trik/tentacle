# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Key(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.key

        from mayatk.ui_utils import maya_menu_handler

        handler = maya_menu_handler.MayaMenuHandler()
        menu = handler.get_menu("key")
        header = self.sb.Header()
        header.attach_to(menu)
        menu.header.setTitle(menu.objectName().upper())
        menu.header.configure_buttons(menu_button=True, pin_button=True)
        self.sb.add_ui(menu)
        self.sb.key.lock_style = True


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
