# !/usr/bin/python
# coding=utf-8
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

        # The preferences .ui pair is shared with every other DCC, so the app name
        # can't live in Designer — each host writes its own over the `<app>` token.
        self.ui.parent_app.setTitle("Maya Preferences")
        self.submenu.b010.setText("Maya Preferences")

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

        # Working units are scene state — Maya owns the truth, not QSettings
        # (Slots.mirror_app_state; same sweep as the Blender twin). Populating
        # happens inside the seed because `add` itself emits currentIndexChanged
        # (and re-arms restore_state for a headerless combo), which on the
        # deferred init path would write index 0's unit to the scene before the
        # real one was seeded.
        def seed():
            widget.add({i.upper(): i for i in mtk.EnvUtils.SCENE_UNIT_VALUES})
            widget.setCurrentIndex(
                widget.items.index(cmds.currentUnit(q=True, fullName=True, linear=True))
            )

        self.mirror_app_state(widget, seed)

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

        # Scene state, populated inside the seed — same reasons as cmb001_init.
        def seed():
            frame_rates = ptk.VidUtils.FRAME_RATES
            widget.add(
                {f"{frame_rates.get(key)} fps {key.upper()}": key for key in frame_rates}
            )
            widget.setCurrentIndex(
                widget.items.index(cmds.currentUnit(q=True, fullName=True, time=True))
            )

        self.mirror_app_state(widget, seed)

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

    def cmb003_init(self, widget):
        """App-style / color selector — the Maya-side counterpart to the Blender slot's ``cmb003``.
        Maya has no *native* color-preset dropdown to mirror (its Colors editor offers no named
        templates), so this just lists our own shipped styles (e.g. ``Blender``). See
        ``mayatk.ui_utils.style_setter``."""
        if not widget.is_initialized:
            widget.add(mtk.StyleSetter.list_templates())  # {display_name: token}

    def cmb003(self, index, widget):
        """Apply the selected shipped style (e.g. ``Blender``), recoloring Maya's viewport toward
        that look. Scoped to what Maya exposes scriptably (displayRGBColor/colorIndex/displayColor)
        — Maya's Qt chrome itself has no scriptable equivalent, unlike Blender's full theme."""
        mtk.StyleSetter.apply_template(widget.currentData())

    def b008(self):
        """Hotkeys: open Maya's native Hotkey Preferences window."""
        mel.eval("HotkeyPreferencesWindow")

    def b011(self):
        """Macro Manager — the unified shortcut editor over the mayatk macros
        (``mtk.Macros.show_editor``; the bespoke panel was retired)."""
        mtk.Macros.show_editor(parent=self.sb.handlers.marking_menu)

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
