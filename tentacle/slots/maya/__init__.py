# !/usr/bin/python
# coding=utf-8
from mayatk.ui_utils import MayaMenuHandler
from tentacle.slots import Slots


class SlotsMaya(Slots):
    maya_menu_handler = MayaMenuHandler()

    """App specific methods inherited by all other app specific slot classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def embed_maya_menu(self, ui):
        """Set the Maya menu as the central widget of the UI MainWindow object.

        Parameters:
            ui (MainWindow): The UI MainWindow object to embed the Maya menu in.

        Returns:
            MainWindow: The wrapped UI MainWindow object.
        """
        menu = self.maya_menu_handler.get_menu(ui.name)
        # menu.scale_by_percentage(40)

        ui.setCentralWidget(menu)
        ui.setWindowFlags(self.sb.QtCore.Qt.FramelessWindowHint)
        ui.lock_style = True

        ui.header = self.sb.Header()
        ui.header.setTitle(ui.name.upper())
        ui.header.attach_to(ui)

        return ui


# --------------------------------------------------------------------------------------------


# module name
# print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
