# !/usr/bin/python
# coding=utf-8
import os

import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
import pythontk as ptk
from mayatk.core_utils.script_job_manager import ScriptJobManager

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class Preferences(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.preferences
        self.submenu = self.sb.loaded_ui.preferences_submenu

    def cmb001_init(self, widget):
        """Initializes the combo box with unit options."""
        if not widget.is_initialized:
            mgr = ScriptJobManager.instance()
            mgr.subscribe(
                "linearUnitChanged",
                lambda w=widget: w.setCurrentIndex(
                    w.items.index(
                        cmds.currentUnit(q=True, fullName=True, linear=True)
                    )
                ),
                owner=widget,
            )
            mgr.connect_cleanup(widget, owner=widget)

        items = {i.upper(): i for i in mtk.EnvUtils.SCENE_UNIT_VALUES}
        widget.add(items)
        widget.setCurrentIndex(
            widget.items.index(cmds.currentUnit(q=True, fullName=True, linear=True))
        )

    def cmb001(self, index, widget):
        """Set Working Units: Linear"""
        # Valid Units: millimeter | centimeter | meter | kilometer | inch | foot | yard | mile
        unit = widget.currentData()
        cmds.currentUnit(linear=unit.lower())

    def cmb002_init(self, widget):
        """Initializes the combo box with frame rate options."""
        if not widget.is_initialized:
            mgr = ScriptJobManager.instance()
            mgr.subscribe(
                "timeUnitChanged",
                lambda w=widget: w.setCurrentIndex(
                    w.items.index(
                        cmds.currentUnit(q=True, fullName=True, time=True)
                    )
                ),
                owner=widget,
            )
            mgr.connect_cleanup(widget, owner=widget)

        frame_rates = ptk.VidUtils.FRAME_RATES
        items = {
            f"{frame_rates.get(key)} fps {key.upper()}": key for key in frame_rates
        }
        widget.add(items)
        widget.setCurrentIndex(
            widget.items.index(cmds.currentUnit(q=True, fullName=True, time=True))
        )

    def cmb002(self, index, widget):
        """Set Working Units: Time"""
        # game | film | pal | ntsc | show | palf | ntscf
        cmds.currentUnit(time=widget.currentData())

    def s000_init(self, widget):
        """Initialize autosave max backups spinbox (widget is source of truth)."""
        if not widget.is_initialized:
            # Set initial value from Maya
            autoSaveState = cmds.autoSave(q=True, enable=True)
            if autoSaveState:
                autoSaveAmount = cmds.autoSave(q=True, maxBackups=True)
                widget.setValue(autoSaveAmount)
            else:
                widget.setValue(0)

            def update_autosave(value):
                """Update Maya autosave settings from widget value."""
                if value == 0:
                    cmds.autoSave(enable=False)
                else:
                    cmds.autoSave(enable=True, maxBackups=value, limitBackups=True)

            widget.valueChanged.connect(update_autosave)

            # Enforce widget as source of truth on show
            current_value = widget.value()
            update_autosave(current_value)

    def s001_init(self, widget):
        """Initialize autosave interval spinbox (widget is source of truth)."""
        if not widget.is_initialized:
            # Set initial value from Maya
            autoSaveInterval = cmds.autoSave(q=True, int=True)
            widget.setValue(autoSaveInterval / 60)

            def update_interval(value):
                """Update Maya autosave interval from widget value."""
                cmds.autoSave(int=int(value * 60))

            widget.valueChanged.connect(update_interval)

            # Enforce widget as source of truth on show
            current_value = widget.value()
            update_interval(current_value)

    def b001(self):
        """Color Settings"""
        mel.eval("colorPrefWnd")

    def b002(self):
        """Autosave: Delete All"""
        files = mtk.get_recent_autosave()
        for file, _ in files:
            try:
                os.remove(file)

            except Exception as error:
                print(error)

    def b008(self):
        """Hotkeys"""
        mel.eval("HotkeyPreferencesWindow")

    def b011(self):
        """Macro Manager"""
        self.sb.handlers.marking_menu.show("macro_manager")

    def b009(self):
        """Plug-In Manager"""
        mel.eval("PluginManager")

    def b010(self):
        """Settings/Preferences"""
        mel.eval("PreferencesWindow")


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
