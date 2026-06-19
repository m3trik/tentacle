# !/usr/bin/python
# coding=utf-8
import html
import os
import sys

import mayatk as mtk
import pythontk as ptk

# From this package:
from tentacle.slots.maya._slots_maya import SlotsMaya


class Settings(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    def header_init(self, widget):
        """Initialize header"""
        if not widget.is_initialized:
            widget.menu.add(
                self.sb.registered_widgets.Separator,
                setTitle="Package",
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

        uitk_module = sys.modules.get("uitk.widgets.marking_menu")
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
            if pkg_mgr.is_outdated(this_pkg):
                user_choice = self.sb.message_box(
                    f"<b><hl>{latest_ver}</hl> is available. Do you want to update it?</b>",
                    "Yes",
                    "No",
                )
                if user_choice == "Yes":
                    pkg_mgr.update(this_pkg)
                    self.sb.message_box(
                        "<b>The package and it's dependencies have been <hl>updated</hl>.</b>"
                    )
                else:
                    self.sb.message_box("<b>The update was cancelled.</b>")
            else:
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

    def b020(self):
        """UI Style Editor"""
        self.sb.editors.show("style")

    def b021(self):
        """Hotkey Editor"""
        self.sb.editors.show("hotkey")

    def b022(self):
        """UI Browser"""
        self.sb.editors.show("browser")

    # -------------------------------------------------------------------------
    # Marking Menu Bindings
    # -------------------------------------------------------------------------

    def _get_startmenus(self) -> list:
        """Get available startmenu UIs from the registry."""
        filenames = self.sb.registry.ui_registry.get("filename") or []
        return sorted([f for f in filenames if "#startmenu" in f])

    def _get_bindings(self) -> dict:
        """Current marking-menu bindings — read from the SSoT (the menu's store).

        Goes through ``marking_menu`` rather than ``configurable.marking_menu_bindings``
        directly because that key is host-namespaced (Maya/Blender share one
        QSettings backend; see uitk ``MarkingMenu._binding_store_key``). Poking the
        bare key here would desync the editor from the live menu.
        """
        mm = self.sb.handlers.marking_menu
        return mm.bindings if mm is not None else {}

    def _set_bindings(self, bindings: dict) -> None:
        """Persist marking-menu bindings via the SSoT (auto-rebuilds + notifies)."""
        mm = self.sb.handlers.marking_menu
        if mm is not None:
            mm.bindings = bindings

    def _init_binding_combo(self, widget, binding_key: str):
        """Initialize a binding combo box."""
        # Disable auto-restore state for these widgets, as they are managed manually
        # via the marking-menu binding store.
        widget.restore_state = False

        available = self._get_startmenus()
        items = {ui.replace("#startmenu", ""): ui for ui in available}
        widget.clear()
        widget.add(items)

        marking_menu = self.sb.handlers.marking_menu
        if marking_menu is not None:
            marking_menu.on_bindings_changed(
                lambda v: self._sync_binding_combo(widget, binding_key, v)
            )

        bindings = self._get_bindings()
        if not bindings:
            bindings = (
                getattr(marking_menu, "default_bindings", {}) if marking_menu else {}
            )

        self._sync_binding_combo(widget, binding_key, bindings)

    def _sync_binding_combo(self, widget, key, bindings):
        """Sync combo box with settings value."""
        try:
            val = bindings.get(key, "")
            if val in widget.items:
                if widget.currentData() != val:
                    widget.setCurrentIndex(widget.items.index(val))
        except (RuntimeError, AttributeError):
            pass  # Widget likely deleted

    def _on_binding_change(self, binding_key: str, widget):
        """Handle binding combo change."""
        bindings = self._get_bindings()
        if bindings.get(binding_key) != widget.currentData():
            bindings[binding_key] = widget.currentData()
            self._set_bindings(bindings)

    def _get_activation_key(self) -> str:
        """Get activation key from bindings."""
        bindings = self._get_bindings()
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

    def kse_repeat_last_init(self, widget):
        """Initialize repeat last command key sequence editor."""
        if not widget.is_initialized:
            sequence = self.sb.configurable.repeat_last_shortcut.get("Ctrl+Shift+R")
            if sequence:
                widget.setKeySequence(self.sb.QtGui.QKeySequence(sequence))

            widget.keySequenceChanged.connect(
                lambda: self._on_repeat_last_change(widget)
            )

    def _on_repeat_last_change(self, widget):
        """Handle repeat last shortcut change."""
        try:
            sequence = widget.keySequence().toString()
        except AttributeError:
            return

        self.sb.configurable.repeat_last_shortcut.set(sequence)

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

        bindings = self._get_bindings()
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

        self._set_bindings(new_bindings)

    def b_reset_bindings(self):
        """Reset bindings to defaults."""
        marking_menu = self.sb.handlers.marking_menu
        defaults = getattr(marking_menu, "default_bindings", {}) if marking_menu else {}
        self._set_bindings(defaults)


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
