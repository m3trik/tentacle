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

        # Change generic button text to Maya specific
        self.ui.parent_app.setTitle("Maya")
        self.ui.b010.setText("Maya Preferences")
        self.submenu.b010.setText("Maya Preferences")

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
        """Initializes the combo box with frame rate options."""
        items = {  # Generate formatted frame rate items from the FRAME_RATE_VALUES
            mtk.AnimUtils.format_frame_rate_str(key): key
            for key in mtk.AnimUtils.FRAME_RATE_VALUES
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
        self.check_for_update()

    def check_for_update(self):
        """ """
        mayapy = os.path.join(mtk.get_maya_info("install_path"), "bin", "mayapy.exe")
        pkg_mgr = ptk.PkgManager(python_path=mayapy)
        this_pkg = "tentacletk"
        latest_ver = pkg_mgr.latest_version(this_pkg)
        # Check if the package is outdated
        if pkg_mgr.is_outdated(this_pkg):  # Prompt user whether to update
            user_choice = self.sb.message_box(
                f"<b><hl>{latest_ver}</hl> is available. Do you want to update it?</b>",
                "Yes",
                "No",
            )
            if user_choice == "Yes":  # User chose to update
                pkg_mgr.update("pythontk")
                pkg_mgr.update("uitk")
                pkg_mgr.update("mayatk")
                pkg_mgr.update(this_pkg)
                self.sb.message_box(
                    "<b>The package and it's dependencies have been <hl>updated</hl>.</b>"
                )
            else:  # User chose not to update or closed the dialog
                self.sb.message_box("<b>The update was cancelled.</b>")
        else:  # Package is up to date
            self.sb.message_box(
                f"<b><hl>{latest_ver}</hl> is already the latest version.</b>"
            )

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
