# !/usr/bin/python
# coding=utf-8
import html
import os
import sys

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
import pythontk as ptk

# From this package:
from tentacle.slots.maya import SlotsMaya


class Preferences(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.preferences
        self.submenu = self.sb.loaded_ui.preferences_submenu

    def header_init(self, widget):
        """Initialize header"""
        if not widget.is_initialized:
            widget.menu.add(
                self.sb.registered_widgets.Label,
                setText="UI Style Editor",
                setObjectName="lbl000",
                setToolTip="Customize the UI colors used by Tentacle.",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Update Package",
                setObjectName="tb000",
                setToolTip="Check for Tentacle package updates.",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Reload Scripts",
                setObjectName="tb001",
                setToolTip="Reload Tentacle and its core dependencies in the current session.",
            )

    def cmb001_init(self, widget):
        """Initializes the combo box with unit options."""
        if not widget.is_initialized:
            # Set up a script job to update the index when the unit changes
            widget.unitChangeJob = pm.scriptJob(
                event=[
                    "linearUnitChanged",
                    lambda: widget.setCurrentIndex(
                        widget.items.index(
                            pm.currentUnit(q=True, fullName=True, linear=True)
                        )
                    ),
                ],
                runOnce=False,
            )

        items = {i.upper(): i for i in mtk.EnvUtils.SCENE_UNIT_VALUES}
        widget.add(items)
        widget.setCurrentIndex(
            widget.items.index(pm.currentUnit(q=True, fullName=True, linear=True))
        )

    def cmb001(self, index, widget):
        """Set Working Units: Linear"""
        # Valid Units: millimeter | centimeter | meter | kilometer | inch | foot | yard | mile
        unit = widget.currentData()
        pm.currentUnit(linear=unit.lower())

    def cmb002_init(self, widget):
        """Initializes the combo box with frame rate options."""
        if not widget.is_initialized:
            # Set up a script job to update the index when the frame rate changes
            widget.timeChangeJob = pm.scriptJob(
                event=[
                    "timeChanged",
                    lambda: widget.setCurrentIndex(
                        widget.items.index(
                            pm.currentUnit(q=True, fullName=True, time=True)
                        )
                    ),
                ],
                runOnce=False,
            )

        frame_rates = ptk.VidUtils.FRAME_RATES
        items = {
            f"{frame_rates.get(key)} fps {key.upper()}": key for key in frame_rates
        }
        widget.add(items)
        widget.setCurrentIndex(
            widget.items.index(pm.currentUnit(q=True, fullName=True, time=True))
        )

    def cmb002(self, index, widget):
        """Set Working Units: Time"""
        # game | film | pal | ntsc | show | palf | ntscf
        pm.currentUnit(time=widget.currentData())

    def s000_init(self, widget):
        """Initialize autosave max backups spinbox (widget is source of truth)."""
        if not widget.is_initialized:
            # Set initial value from Maya
            autoSaveState = pm.autoSave(q=True, enable=True)
            if autoSaveState:
                autoSaveAmount = pm.autoSave(q=True, maxBackups=True)
                widget.setValue(autoSaveAmount)
            else:
                widget.setValue(0)

            def update_autosave(value):
                """Update Maya autosave settings from widget value."""
                if value == 0:
                    pm.autoSave(enable=False)
                else:
                    pm.autoSave(enable=True, maxBackups=value, limitBackups=True)

            widget.valueChanged.connect(update_autosave)

            # Enforce widget as source of truth on show
            current_value = widget.value()
            update_autosave(current_value)

    def s001_init(self, widget):
        """Initialize autosave interval spinbox (widget is source of truth)."""
        if not widget.is_initialized:
            # Set initial value from Maya
            autoSaveInterval = pm.autoSave(q=True, int=True)
            widget.setValue(autoSaveInterval / 60)

            def update_interval(value):
                """Update Maya autosave interval from widget value."""
                pm.autoSave(int=int(value * 60))

            widget.valueChanged.connect(update_interval)

            # Enforce widget as source of truth on show
            current_value = widget.value()
            update_interval(current_value)

    def tb000(self):
        """Update Package"""
        self.check_for_update()

    def tb001(self):
        """Reload Tentacle package with its dependencies."""
        state = self._teardown_tentacle_instance()

        # Reload dependencies first, then tentacle
        modules = [m for m in ("pythontk", "mayatk", "uitk") if m in sys.modules]
        modules.append("tentacle")

        try:
            reloaded = mtk.MayaConnection.reload_modules(modules)
        except Exception as error:
            print(f"Tentacle reload failed: {error}")
            self.sb.message_box(
                "<b>Reload failed.</b><br><small>{}</small>".format(
                    html.escape(str(error))
                )
            )
            return

        self._restore_tentacle_instance(state)

        self.sb.message_box(
            f"<b>Reload complete.</b><br><small>{len(reloaded)} module(s) refreshed.</small>"
        )

    def _teardown_tentacle_instance(self):
        state = {"was_visible": False, "ui_name": None}

        uitk_module = sys.modules.get("uitk.menus.marking_menu")
        if not uitk_module:
            return state

        MarkingMenu = getattr(uitk_module, "MarkingMenu", None)
        if MarkingMenu is None:
            return state

        instance = getattr(MarkingMenu, "_instances", {}).get(MarkingMenu)
        if instance is None:
            return state

        try:
            state["was_visible"] = instance.isVisible()
            instance.hide()
        except Exception:
            pass

        try:
            current_ui = getattr(getattr(instance, "sb", None), "current_ui", None)
            if current_ui is not None:
                state["ui_name"] = getattr(current_ui, "objectName", lambda: None)()
        except Exception:
            pass

        try:
            instance.deleteLater()
        except Exception:
            pass

        if hasattr(MarkingMenu, "_submenu_cache"):
            try:
                MarkingMenu._submenu_cache.clear()
            except Exception:
                pass

        if hasattr(MarkingMenu, "reset_instance"):
            try:
                MarkingMenu.reset_instance()
            except Exception:
                pass

        # Ensure the singleton registry is cleared for safety.
        try:
            MarkingMenu._instances.pop(MarkingMenu, None)
        except Exception:
            pass

        return state

    def _restore_tentacle_instance(self, state):
        if not state.get("was_visible"):
            return

        try:
            from tentacle.tcl_maya import TclMaya
        except Exception as error:
            print(f"Tentacle restore skipped: {error}")
            return

        try:
            new_instance = TclMaya()
            target_ui = state.get("ui_name") or "hud#startmenu"
            try:
                new_instance.show(target_ui)
            except Exception:
                new_instance.show()
        except Exception as error:
            print(f"Tentacle restore failed: {error}")

    def check_for_update(self):
        """Check for Tentacle package updates"""
        mayapy = os.path.join(mtk.get_env_info("install_path"), "bin", "mayapy.exe")
        pkg_mgr = ptk.PackageManager(python_path=mayapy)
        this_pkg = "tentacletk"

        try:
            latest_ver = pkg_mgr.latest_version(this_pkg)
            # Check if the package is outdated
            if pkg_mgr.is_outdated(this_pkg):  # Prompt user whether to update
                user_choice = self.sb.message_box(
                    f"<b><hl>{latest_ver}</hl> is available. Do you want to update it?</b>",
                    "Yes",
                    "No",
                )
                if user_choice == "Yes":  # User chose to update
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

        except Exception as error:
            print(f"Update check failed: {error}")
            self.sb.message_box(
                "<b>Update check failed.</b><br><small>{}</small>".format(
                    html.escape(str(error))
                )
            )

    def lbl000(self):
        """UI Style Editor"""
        from uitk.widgets.style_editor import StyleEditor

        # Create if not exists or if the C++ object has been deleted
        if not hasattr(self, "_style_editor"):
            self._style_editor = StyleEditor(parent=self.sb.parent())
        else:
            try:
                # Check if underlying C++ object is valid
                if not self._style_editor.isVisible():
                    self._style_editor.show()  # Just show if hidden
            except RuntimeError:
                # Re-create if deleted
                self._style_editor = StyleEditor(parent=self.sb.parent())
        print("Opening Style Editor:", self._style_editor)
        self._style_editor.show()
        self._style_editor.raise_()

    def b001(self):
        """Color Settings"""
        pm.mel.colorPrefWnd()

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
        pm.mel.HotkeyPreferencesWindow()

    def b009(self):
        """Plug-In Manager"""
        pm.mel.PluginManager()

    def b010(self):
        """Settings/Preferences"""
        pm.mel.PreferencesWindow()

    # -------------------------------------------------------------------------
    # Menu Bindings Configuration
    # -------------------------------------------------------------------------

    def _get_startmenus(self) -> list:
        """Get available startmenu UIs from the registry."""
        # Access registry through the parent switchboard (tentacle's sb)
        filenames = self.sb.registry.ui_registry.get("filename") or []
        return sorted([f for f in filenames if "#startmenu" in f])

    def _init_binding_combo(self, widget, binding_key: str):
        """Initialize a binding combo box."""
        # Disable auto-restore state for these widgets, as they are managed manually
        # via the marking_menu_bindings setting.
        widget.restore_state = False

        available = self._get_startmenus()
        items = {ui.replace("#startmenu", ""): ui for ui in available}
        widget.clear()
        widget.add(items)

        # Connect to settings change for reactive updates
        self.sb.configurable.marking_menu_bindings.changed.connect(
            lambda v: self._sync_binding_combo(widget, binding_key, v)
        )

        # Initial sync
        self._sync_binding_combo(
            widget, binding_key, self.sb.configurable.marking_menu_bindings.get({})
        )

    def _sync_binding_combo(self, widget, key, bindings):
        """Sync combo box with settings value."""
        try:
            val = bindings.get(key, "")
            if val in widget.items:
                # Only update if different to avoid signal loops
                if widget.currentData() != val:
                    widget.setCurrentIndex(widget.items.index(val))
        except (RuntimeError, AttributeError):
            pass  # Widget likely deleted

    def _on_binding_change(self, binding_key: str, widget):
        """Handle binding combo change."""
        bindings = self.sb.configurable.marking_menu_bindings.get({})
        # Only update if value changed (avoids unnecessary writes)
        if bindings.get(binding_key) != widget.currentData():
            bindings[binding_key] = widget.currentData()
            self.sb.configurable.marking_menu_bindings.set(bindings)

    def _get_activation_key(self) -> str:
        """Get activation key from bindings."""
        bindings = self.sb.configurable.marking_menu_bindings.get({})
        for key in bindings:
            for part in key.split("|"):
                if part.startswith("Key_"):
                    return part
        return "Key_F12"

    def cmb_bind_default_init(self, widget):
        """Default binding (key only)."""
        key = self._get_activation_key()
        self._init_binding_combo(widget, key)
        widget.currentIndexChanged.connect(lambda: self._on_binding_change(key, widget))

    def cmb_bind_left_init(self, widget):
        """Left button binding."""
        key = f"{self._get_activation_key()}|LeftButton"
        self._init_binding_combo(widget, key)
        widget.currentIndexChanged.connect(lambda: self._on_binding_change(key, widget))

    def cmb_bind_middle_init(self, widget):
        """Middle button binding."""
        key = f"{self._get_activation_key()}|MiddleButton"
        self._init_binding_combo(widget, key)
        widget.currentIndexChanged.connect(lambda: self._on_binding_change(key, widget))

    def cmb_bind_right_init(self, widget):
        """Right button binding."""
        key = f"{self._get_activation_key()}|RightButton"
        self._init_binding_combo(widget, key)
        widget.currentIndexChanged.connect(lambda: self._on_binding_change(key, widget))

    def cmb_bind_left_right_init(self, widget):
        """Left+Right button binding."""
        key = f"{self._get_activation_key()}|LeftButton|RightButton"
        self._init_binding_combo(widget, key)
        widget.currentIndexChanged.connect(lambda: self._on_binding_change(key, widget))

    def kse_activation_key_init(self, widget):
        """Initialize activation key sequence editor."""
        if not widget.is_initialized:
            val = self._get_activation_key()
            try:
                seq_str = val.replace("Key_", "")
                widget.setKeySequence(self.sb.QtGui.QKeySequence(seq_str))
            except Exception:
                pass

            widget.keySequenceChanged.connect(
                lambda: self._on_activation_key_change(widget)
            )

    def _on_activation_key_change(self, widget):
        """Handle activation key change."""
        try:
            val = widget.keySequence().toString()
        except AttributeError:
            return

        if not val:
            return

        new_key_part = f"Key_{val}"
        old_key_part = self._get_activation_key()

        if new_key_part == old_key_part:
            return

        bindings = self.sb.configurable.marking_menu_bindings.get({})
        new_bindings = {}

        for key, menu in bindings.items():
            parts = key.split("|")
            new_parts = []
            for part in parts:
                if part == old_key_part:
                    new_parts.append(new_key_part)
                else:
                    new_parts.append(part)
            new_key = "|".join(new_parts)
            new_bindings[new_key] = menu

        self.sb.configurable.marking_menu_bindings.set(new_bindings)

    def b_reset_bindings(self):
        """Reset bindings to defaults."""
        parent = self.sb.parent()
        defaults = getattr(parent, "_initial_bindings", {}) if parent else {}
        self.sb.configurable.marking_menu_bindings.set(defaults)


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
