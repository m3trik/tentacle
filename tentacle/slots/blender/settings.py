# !/usr/bin/python
# coding=utf-8
import sys
import html

import pythontk as ptk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Settings(SlotsBlender):
    """Blender port of the shared ``settings`` menu.

    The package/editor controls (Update, UI Style / Shortcut / Browser editors, reset marking-menu
    bindings) are DCC-agnostic uitk switchboard features and port directly. Update Package
    drives ``ptk.PackageManager`` with Blender's bundled python (``sys.executable``); Reload
    Scripts rides ``tcl_blender.reload()`` (guarded in-place reload — ``script.reload()``
    would tear down the Qt host).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    def header_init(self, widget):
        if not widget.is_initialized:
            widget.menu.add(self.sb.registered_widgets.Separator, setTitle="Package")
            widget.menu.add(
                self.sb.registered_widgets.PushButton, setText="Update Package",
                setObjectName="tb000", setToolTip="Check for Tentacle package updates.",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton, setText="Reload Scripts",
                setObjectName="tb001",
                setToolTip="Reload Tentacle and its dependencies in place, then re-register.",
            )

    def tb000(self):
        """Update Package (PyPI check via Blender's bundled python — sys.executable)."""
        pkg_mgr = ptk.PackageManager(python_path=sys.executable)
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

    def tb001(self):
        """Reload Scripts (tear down, reload the tentacle ecosystem in place, re-register)."""
        from tentacle import tcl_blender

        try:
            count = tcl_blender.reload()
        except Exception as error:
            print(f"Tentacle reload failed: {error}")
            self.sb.message_box(
                "<b>Reload failed.</b><br><small>{}</small>".format(
                    html.escape(str(error))
                )
            )
            return
        print(f"tentacle: reloaded {count} module(s); re-registering on the next tick.")

    def b020(self):
        """UI Style Editor"""
        self.sb.editors.show("style")

    def b021(self):
        """Shortcut Editor"""
        self.sb.editors.show("shortcut")

    def b022(self):
        """UI Browser"""
        self.sb.editors.show("browser")

    def b023(self):
        """Global Shortcuts: focused shortcut editor for the global triggers
        (marking-menu activation key, repeat-last, reopen-last UI)."""
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
        """Reset marking-menu bindings to defaults."""
        marking_menu = self.sb.handlers.marking_menu
        defaults = getattr(marking_menu, "default_bindings", {}) if marking_menu else {}
        # Write through the menu so it lands in the host-namespaced store (Maya and
        # Blender share one QSettings backend; the bare key would collide). See uitk
        # MarkingMenu._binding_store_key.
        if marking_menu is not None:
            marking_menu.bindings = defaults


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
