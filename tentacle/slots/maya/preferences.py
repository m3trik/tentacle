# !/usr/bin/python
# coding=utf-8
import os

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Preferences(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.preferences
        self.submenu = self.sb.preferences_submenu

        self.ui.parent_app.setTitle("Maya")
        self.ui.b010.setText("Maya Preferences")

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

    def s000_init(self, widget):
        """ """
        # Get the current autosave state
        autoSaveState = pm.autoSave(q=True, enable=True)
        if autoSaveState:
            autoSaveAmount = pm.autoSave(q=True, maxBackups=True)
            widget.setValue(autoSaveAmount)
        else:
            widget.setValue(0)

        widget.valueChanged.connect(
            lambda v: pm.autoSave(enable=v, maxBackups=v, limitBackups=True)
        )

    def s001_init(self, widget):
        """ """
        autoSaveInterval = pm.autoSave(q=True, int=True)
        widget.setValue(autoSaveInterval / 60)

        widget.valueChanged.connect(lambda v: pm.autoSave(int=v * 60))

    def b002(self):
        """Autosave: Delete All"""
        files = mtk.get_recent_autosave()
        for file in files:
            try:
                os.remove(file)

            except Exception as error:
                print(error)

    def b000(self):
        """Update Package"""
        mayapy = os.path.join(mtk.get_maya_info("install_path"), "bin", "mayapy.exe")
        pkg_mgr = ptk.PkgManager(python_path=mayapy)

        package_name = "tentacletk"
        # Check if the package is outdated
        if pkg_mgr.is_outdated(package_name):
            # Ask user whether to update
            user_choice = self.prompt_update_decision(package_name)
            if user_choice == self.sb.QMessageBox.Yes:
                # User chose to update
                pkg_mgr.update(package_name)
                self.sb.message_box(
                    f"Updated {package_name} to the latest version.", location="center"
                )
            else:  # User chose not to update
                self.sb.message_box(
                    f"Update for {package_name} was cancelled.", location="center"
                )
        else:
            self.sb.message_box(f"{package_name} is already up to date.")

    def prompt_update_decision(self, package_name):
        """Prompt user to decide on updating the package."""
        msg_box = self.sb.QMessageBox()
        msg_box.setWindowTitle("Update Package")
        msg_box.setText(f"{package_name} is outdated. Do you want to update it?")
        msg_box.setStandardButtons(self.sb.QMessageBox.Yes | self.sb.QMessageBox.No)
        return msg_box.exec_()

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
