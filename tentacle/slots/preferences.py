# !/usr/bin/python
# coding=utf-8
"""Preferences: one Slots class for both hosts.

Two halves. Tentacle's own preferences -- the marking-menu and tool-window
themes (``cmb004`` / ``cmb005``), how tools whose external app is missing are
shown (``cmb006``) and the header's re-check -- are uitk state, reached through
the switchboard. The host's preferences -- working units, autosave, the app
style, the host's preference windows and the Macro Manager -- are the host
toolkit's (``self.tk``): Maya's own windows and settings, or Blender's.

Macros are keyable only: ``b011`` opens the Macro Manager to bind them, never to
run them.
"""

from tentacle import Slots


class PreferencesSlots(Slots):
    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.preferences
        self.submenu = self.sb.loaded_ui.preferences_submenu

        # The .ui pair is shared by both hosts, so each names its own preferences
        # over the ``<app>`` token.
        label = f"{self.tk.EnvUtils.APP_NAME} Preferences"
        self.ui.parent_app.setTitle(label)
        self.submenu.b010.setText(label)

    # ------------------------------------------------------------------ tentacle: themes
    @staticmethod
    def _token_label(token: str) -> str:
        """Display label for a setting token (``"dark-grey"`` -> ``"Dark Grey"``)."""
        return token.replace("-", " ").title()

    def _theme_items(self) -> dict:
        """``{display label: theme token}`` for every registered uitk theme
        (``sb.style``: the switchboard's lazy proxy for ``StyleSheet``)."""
        return {self._token_label(t): t for t in self.sb.style.themes}

    def _marking_menu(self):
        return self.sb.handlers.marking_menu

    def _apply_theme(self, kind: str, widget):
        """Write the combo's selected token to the ``{kind}_theme`` property; a change
        fired while the header row is current (no token) writes nothing."""
        theme = widget.currentData()
        if theme is not None:
            setattr(self._marking_menu(), f"{kind}_theme", theme)

    def cmb004_init(self, widget):
        """Marking-menu (radial startmenu / submenu) window theme."""
        if not widget.is_initialized:
            widget.add(self._theme_items(), header="Menu")
        widget.setCurrentText(self._token_label(self._marking_menu().menu_theme))

    def cmb004(self, index, widget):
        """Apply the marking-menu theme (persists + re-themes live windows)."""
        self._apply_theme("menu", widget)

    def cmb005_init(self, widget):
        """Standalone tool-window theme."""
        if not widget.is_initialized:
            widget.add(self._theme_items(), header="Window")
        widget.setCurrentText(self._token_label(self._marking_menu().window_theme))

    def cmb005(self, index, widget):
        """Apply the standalone-window theme (persists + re-themes live windows)."""
        self._apply_theme("window", widget)

    # ------------------------------------------------------------------ tentacle: unavailable tools
    #: Display label for an ``unmet_policy`` token where ``.title()`` is not enough.
    #: Only an override: the entries and their order come from
    #: ``Switchboard.UNMET_POLICIES``, so a policy added upstream appears here.
    _UNMET_LABEL_OVERRIDES = {"disable": "Show disabled"}

    def _unmet_label(self, token: str) -> str:
        """Display label for an ``unmet_policy`` token."""
        return self._UNMET_LABEL_OVERRIDES.get(token, self._token_label(token))

    def cmb006_init(self, widget):
        """Presentation for tools whose external app / plugin isn't installed:
        writes ``sb.unmet_policy``, which every ``sb.gate`` call reads."""
        if not widget.is_initialized:
            widget.add(
                {self._unmet_label(t): t for t in self.sb.UNMET_POLICIES},
                header="Unavailable tools",
            )
            widget.setToolTip(
                "How tools whose external app or plugin isn't installed are "
                "presented.\n\n"
                "Hide - leave them out entirely.\n"
                "Show disabled - greyed, with the missing app named in the tooltip.\n"
                "Show - leave them active (they report the missing app on use).\n\n"
                "Applies to open panels immediately."
            )
        widget.setCurrentText(self._unmet_label(self.sb.unmet_policy))

    def cmb006(self, index, widget):
        """Persist the chosen presentation policy and re-present the live gates
        (re-apply, not re-probe: only the presentation changed)."""
        policy = widget.currentData()
        if policy is None:
            return
        self.sb.unmet_policy = policy
        self.sb.recheck_gates()

    def header_init(self, widget):
        """Header menu: the manual re-probe that pairs with ``cmb006``. Built in code
        because the ``#submenu`` variant carries no header."""
        if not widget.is_initialized:
            widget.menu.hide_on_trigger = True  # a one-shot action
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Re-check Installed Tools",
                setObjectName="tb000",
                setToolTip=(
                    "Re-probe the external apps that gated tools need, and re-present "
                    "them.\n\nUse this after installing one without restarting: an "
                    "availability probe is cached (the gate re-runs on every panel "
                    "show and must not re-scan Program Files each time), so a "
                    "mid-session install stays invisible until the cache is dropped."
                ),
            )

    def tb000(self):
        """Re-check installed tools: drop the cached probes, then re-apply the gates."""
        updated = self.recheck_app_gates()
        self.sb.message_box(
            f"Re-checked installed tools — <hl>{updated}</hl> widget(s) re-presented."
        )

    # ------------------------------------------------------------------ host: working units
    def _sync_combo(self, widget, current):
        """Select *current* (an item's data) in *widget*, or nothing when the host's
        value is not listed; signals blocked: reading the host is not an edit."""
        was_blocked = widget.blockSignals(True)
        try:
            items = widget.items
            widget.setCurrentIndex(items.index(current) if current in items else -1)
        finally:
            widget.blockSignals(was_blocked)

    def _current_rate(self, rates):
        """The key of *rates* (``{name: fps}``) matching the scene's frame rate."""
        fps = self.tk.EnvUtils.scene_settings()["fps"]
        return next((name for name, rate in rates.items() if abs(rate - fps) < 1e-3), None)

    def cmb001_init(self, widget):
        """Working units: linear. Scene state, so mirrored, never restored
        (``mirror_app_state``); populated inside the seed because ``add`` emits
        ``currentIndexChanged``, which would write index 0's unit to the scene."""
        if not widget.is_initialized:
            jobs = self.tk.ScriptJobManager.instance()
            jobs.subscribe(
                "linearUnitChanged",
                lambda w=widget: self._sync_combo(w, self.tk.EnvUtils.get_linear_unit()),
                owner=widget,
            )
            jobs.connect_cleanup(widget, owner=widget)

        def seed():
            widget.add({unit.upper(): unit for unit in self.tk.EnvUtils.SCENE_UNIT_VALUES})
            self._sync_combo(widget, self.tk.EnvUtils.get_linear_unit())

        self.mirror_app_state(widget, seed)

    def cmb001(self, index, widget):
        """Set Working Units: Linear."""
        unit = widget.currentData()
        if unit:
            self.tk.EnvUtils.set_linear_unit(unit)

    def cmb002_init(self, widget):
        """Working units: time (the frame rate). Mirrored like ``cmb001``."""
        if not widget.is_initialized:
            jobs = self.tk.ScriptJobManager.instance()
            jobs.subscribe(
                "timeUnitChanged",
                lambda w=widget: self._sync_combo(
                    w, self._current_rate(self.tk.EnvUtils.frame_rates())
                ),
                owner=widget,
            )
            jobs.connect_cleanup(widget, owner=widget)

        def seed():
            rates = self.tk.EnvUtils.frame_rates()
            widget.add({f"{fps} fps {name.upper()}": name for name, fps in rates.items()})
            self._sync_combo(widget, self._current_rate(rates))

        self.mirror_app_state(widget, seed)

    def cmb002(self, index, widget):
        """Set Working Units: Time (the frame rate; Maya re-times the keys)."""
        fps = self.tk.EnvUtils.frame_rates().get(widget.currentData())
        if fps:
            self.tk.EnvUtils.apply_scene_settings({"fps": fps})

    # ------------------------------------------------------------------ host: autosave
    def s000_init(self, widget):
        """Autosave backups: the widget is the source of truth (its restored value
        reaches the host through ``valueChanged``). Maya: the autosave files kept, 0
        turning autosave off; Blender: the save versions kept."""
        if not widget.is_initialized:
            widget.setValue(int(self.tk.EnvUtils.autosave_settings()["max_backups"]))
            widget.valueChanged.connect(
                lambda value: self.tk.EnvUtils.set_autosave_settings(
                    max_backups=int(value)
                )
            )

    def s001_init(self, widget):
        """Autosave interval in minutes; 0 reads (Blender: and sets) autosave off."""
        if not widget.is_initialized:
            widget.setValue(int(round(self.tk.EnvUtils.autosave_settings()["interval"])))
            widget.valueChanged.connect(
                lambda value: self.tk.EnvUtils.set_autosave_settings(interval=value)
            )

    # ------------------------------------------------------------------ host: style + windows
    def cmb003_init(self, widget):
        """App style: the host's style list (Maya: the shipped color styles;
        Blender: its Themes presets, ours injected). Mirrored, never restored: a
        restored index would re-apply a stale pick on panel open, and the host keeps
        no "current" to select, so nothing is selected."""

        def seed():
            widget.add(self.tk.StyleSetter.list_templates())  # {display name: token}
            widget.setCurrentIndex(-1)

        self.mirror_app_state(widget, seed)

    def cmb003(self, index, widget):
        """Apply the picked style, as the host's own selector would."""
        token = widget.currentData()
        if token:
            self.tk.StyleSetter.apply_template(token)

    def _open_preferences(self, section):
        """Open the host's own preferences on *section*; say why when it could not."""
        try:
            self.tk.UiUtils.open_preferences(section)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Could not open the preferences: {error}")

    def b001(self):
        """Ui Color: the host's color settings (Blender: Preferences > Themes)."""
        self._open_preferences("colors")

    def b008(self):
        """Hotkeys: the host's hotkey editor (Blender: Preferences > Keymap)."""
        self._open_preferences("hotkeys")

    def b009(self):
        """Plug-ins: the host's plug-in manager (Blender: Preferences > Add-ons)."""
        self._open_preferences("plugins")

    def b010(self):
        """Preferences: the host's preferences window (Blender: Interface)."""
        self._open_preferences("general")

    def b011(self):
        """Macro Manager: the uitk shortcut editor over the host's macros."""
        self.tk.Macros.show_editor(parent=self.sb.handlers.marking_menu)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
