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
        # Get/Set current linear value.
        index = widget.items.index(pm.currentUnit(q=True, fullName=1, linear=1))
        widget.setCurrentIndex(index)

    def cmb001(self, index, widget):
        """Set Working Units: Linear"""
        # millimeter | centimeter | meter | kilometer | inch | foot | yard | mile
        pm.currentUnit(linear=widget.items[index])

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
        # Get/Set current time value.
        index = widget.items.index(pm.currentUnit(q=True, fullName=1, time=1))
        widget.setCurrentIndex(index)

    def cmb002(self, index, widget):
        """Set Working Units: Time"""
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


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
