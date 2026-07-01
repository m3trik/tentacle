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
        """Shortcut Editor"""
        self.sb.editors.show("shortcut")

    def b022(self):
        """UI Browser: open the tentacle UI browser (search, show/hide registered UIs)."""
        self.sb.editors.show("browser")

    def b023(self):
        """Global Shortcuts: open the shortcut editor focused on the global
        triggers — the marking-menu activation key, repeat-last, and reopen-last
        UI. Replaces the inline activation-key / repeat-last key-sequence editors;
        the marking-menu chord→menu targets stay in the Menu Bindings combos."""
        self.sb.editors.show("global_shortcuts")

    # -------------------------------------------------------------------------
    # Marking Menu Bindings
    # -------------------------------------------------------------------------

    def _get_startmenus(self) -> list:
        """Available startmenu UIs — via the marking menu's SSoT helper."""
        mm = self.sb.handlers.marking_menu
        return mm.start_menu_names(short=False) if mm is not None else []

    def _init_binding_combo(self, widget, buttons):
        """Initialize a route combo for the activation-key + *buttons* gesture.

        Binds by *gesture* (a button tuple like ``("LeftButton",)``), not a
        captured key string, so the combo stays correct when the activation key is
        changed in the shortcut editor. Target get/set delegate to the marking
        menu (the SSoT), which resolves the gesture against the current key.
        """
        widget.restore_state = False  # managed via the marking-menu store, not QSettings

        items = {ui.replace("#startmenu", ""): ui for ui in self._get_startmenus()}
        widget.clear()
        widget.add(items)

        mm = self.sb.handlers.marking_menu
        if mm is not None:
            mm.on_bindings_changed(lambda _v: self._sync_binding_combo(widget, buttons))
        self._sync_binding_combo(widget, buttons)

    def _sync_binding_combo(self, widget, buttons):
        """Reflect the gesture's current target menu in the combo."""
        mm = self.sb.handlers.marking_menu
        if mm is None:
            return
        try:
            val = mm.get_route_target(buttons)
            if val in widget.items and widget.currentData() != val:
                widget.setCurrentIndex(widget.items.index(val))
        except (RuntimeError, AttributeError):
            pass  # widget likely deleted

    def _on_binding_change(self, buttons, widget):
        """Persist a route combo change via the marking menu (the SSoT)."""
        mm = self.sb.handlers.marking_menu
        if mm is not None and mm.get_route_target(buttons) != widget.currentData():
            mm.set_route_target(buttons, widget.currentData())

    def cmb_bind_default_init(self, widget):
        """Default menu (activation key only)."""
        self._init_binding_combo(widget, ())
        widget.currentIndexChanged.connect(lambda: self._on_binding_change((), widget))

    def cmb_bind_left_init(self, widget):
        """Left mouse button."""
        self._init_binding_combo(widget, ("LeftButton",))
        widget.currentIndexChanged.connect(
            lambda: self._on_binding_change(("LeftButton",), widget)
        )

    def cmb_bind_middle_init(self, widget):
        """Middle mouse button."""
        self._init_binding_combo(widget, ("MiddleButton",))
        widget.currentIndexChanged.connect(
            lambda: self._on_binding_change(("MiddleButton",), widget)
        )

    def cmb_bind_right_init(self, widget):
        """Right mouse button."""
        self._init_binding_combo(widget, ("RightButton",))
        widget.currentIndexChanged.connect(
            lambda: self._on_binding_change(("RightButton",), widget)
        )

    def cmb_bind_left_right_init(self, widget):
        """Left + Right mouse buttons."""
        self._init_binding_combo(widget, ("LeftButton", "RightButton"))
        widget.currentIndexChanged.connect(
            lambda: self._on_binding_change(("LeftButton", "RightButton"), widget)
        )

    def b_reset_bindings(self):
        """Reset marking-menu bindings (routes + activation key) to defaults."""
        mm = self.sb.handlers.marking_menu
        if mm is not None:
            mm.bindings = getattr(mm, "default_bindings", {})


# -------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
