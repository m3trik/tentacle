# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots.maya import SlotsMaya


class Preferences(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb.preferences.b010.setText("Maya Preferences")

    def cmb001_init(self, widget):
        """ """
        items = [
            "millimeter",
            "centimeter",
            "meter",
            "kilometer",
            "inch",
            "foot",
            "yard",
            "mile",
        ]
        widget.add(items)
        # get/set current linear value.
        index = widget.items.index(pm.currentUnit(q=True, fullName=1, linear=1))
        widget.setCurrentIndex(index)

    def cmb002_init(self, widget):
        """ """
        items = {
            "15 fps (game)": "game",
            "24 fps (film)": "film",
            "25 fps (pal)": "pal",
            "30 fps (ntsc)": "ntsc",
            "48 fps (show)": "show",
            "50 fps (palf)": "palf",
            "60 fps (ntscf)": "ntscf",
        }
        widget.add(items)
        index = widget.items.index(
            pm.currentUnit(q=True, fullName=1, time=1)
        )  # get/set current time value.
        widget.setCurrentIndex(index)

    def cmb003_init(self, widget):
        """ """
        from PySide2 import QtWidgets, QtCore

        items = QtWidgets.QStyleFactory.keys()  # get styles from QStyleFactory
        widget.add(items)
        index = widget.findText(
            QtWidgets.QApplication.style().objectName(), QtCore.Qt.MatchFixedString
        )  # get/set current value
        widget.setCurrentIndex(index)

    def cmb001(self, index, widget):
        """Set Working Units: Linear"""
        if index > 0:
            # millimeter | centimeter | meter | kilometer | inch | foot | yard | mile
            pm.currentUnit(linear=widget.items[index])

    def cmb002(self, index, widget):
        """Set Working Units: Time"""
        if index > 0:
            # game | film | pal | ntsc | show | palf | ntscf
            pm.currentUnit(time=widget.items[index].split()[-1])

    def b001(self):
        """Color Settings"""
        pm.mel.colorPrefWnd()

    def b008(self):
        """Hotkeys"""
        pm.mel.HotkeyPreferencesWindow()

    def b009(self):
        """Plug-In Manager"""
        pm.mel.PluginManager()

    def b010(self):
        """Settings/Preferences"""
        pm.mel.PreferencesWindow()

    @staticmethod
    def loadPlugin(plugin):
        """Loads A Plugin.

        Parameters:
                plugin (str): The desired plugin to load.

        ex. loadPlugin('nearestPointOnMesh')
        """
        not pm.pluginInfo(plugin, query=True, loaded=True) and pm.loadPlugin(plugin)


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
