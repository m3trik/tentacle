# !/usr/bin/python
# coding=utf-8
"""Settings: one Slots class for both hosts.

Tentacle's own settings: the header's Package menu (Update Package, Reload
Scripts), the uitk editor launchers and the marking-menu binding combos. The
updater drives pip through the host's own interpreter
(``self.tk.EnvUtils.python_executable``: mayapy, or Blender's bundled Python);
Reload Scripts is the launcher's (``Tcl.reload``), which tears tentacle down and
rebuilds it the way its host requires.
"""

import html

import pythontk as ptk

from tentacle import Slots


class SettingsSlots(Slots):
    # The distributions the updater checks and upgrades together. A fix routinely
    # ships as a dependency patch with no tentacletk bump (push.ps1 releases each
    # package independently), and pip's only-if-needed upgrade strategy would leave
    # an already-satisfied pin untouched -- so checking tentacletk alone reports
    # "up to date" while e.g. uitk stays stale.
    #
    # Fallback only. The live list is DERIVED per host by :meth:`ecosystem_dists`
    # from the installed metadata, because the DCC engines are extras: hardcoding
    # both here made a Maya install report the engine it cannot use as
    # "blendertk not installed -> X.Y.Z" and pip-install it on the next update.
    ECOSYSTEM_DISTS = ("pythontk", "uitk", "tentacletk")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.settings
        self.submenu = self.sb.loaded_ui.settings_submenu

    @classmethod
    def ecosystem_dists(cls, installed=None):
        """The distributions to check for updates in THIS host.

        Base dependencies + the running host's engine extra + ``tentacletk``, straight
        from the installed metadata (see :meth:`tentacle.Tcl.declared_dists`), so the
        set tracks ``pyproject.toml`` and never reports the other DCC's engine as
        missing. Falls back to :attr:`ECOSYSTEM_DISTS` when metadata is unreadable -- a
        source checkout, or a vendored copy -- where reporting the engine-free base beats
        reporting nothing.

        Parameters:
            installed (dict): ``{dist: version}`` as returned by
                    ``PackageManager.list_packages``. Any OTHER host's engine that is
                    already present is added, so it keeps being maintained: every
                    install made before the engines became extras hard-pinned BOTH,
                    and dropping the other one would freeze it at its installed
                    version forever. Present-only, so a missing engine is still
                    never installed.
        """
        try:
            from tentacle import Tcl

            dists = list(Tcl.declared_dists())
            if not dists:
                return cls.ECOSYSTEM_DISTS
            for host in Tcl.HOSTS:
                for dist in Tcl.engine_dists(host):
                    if dist in (installed or ()) and dist not in dists:
                        dists.append(dist)
            return tuple(dists)
        except Exception:
            return cls.ECOSYSTEM_DISTS

    def header_init(self, widget):
        """Initialize header"""
        if not widget.is_initialized:
            # Every entry is a one-shot action -- dismiss the menu once one is triggered.
            widget.menu.hide_on_trigger = True
            widget.menu.add(
                self.sb.registered_widgets.Separator,
                setTitle="Package",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Update Package",
                setObjectName="tb000",
                setToolTip="Check the Tentacle packages for updates.",
            )
            widget.menu.add(
                self.sb.registered_widgets.PushButton,
                setText="Reload Scripts",
                setObjectName="tb001",
                setToolTip="Reload Tentacle and its dependencies in the current session.",
            )

    def tb000(self):
        """Update Package"""
        self.check_for_update()

    def tb001(self):
        """Reload Scripts: tear tentacle down, reload the ecosystem in place, and
        rebuild it on the host's next idle tick (``Tcl.reload``). Maya reports
        through Maya itself, never this panel, which the reload retires."""
        from tentacle import Tcl

        try:
            Tcl.reload()
        except Exception as error:
            print(f"Tentacle reload failed: {error}")
            self.sb.message_box(
                "<b>Reload failed.</b><br><small>{}</small>".format(
                    html.escape(str(error))
                )
            )

    def check_for_update(self):
        """Check the whole ecosystem for updates and upgrade what's outdated."""
        pkg_mgr = ptk.PackageManager(
            python_path=self.tk.EnvUtils.python_executable()
        )
        try:
            installed_all = pkg_mgr.list_packages()  # one pip call for every version
            # Concurrent, and failure-isolating: a lookup that could not reach
            # the index comes back None. Comparing against None would read as
            # "outdated", so an unknown is skipped rather than reported -- but if
            # NONE of them resolved, the check itself failed and must say so
            # instead of quietly claiming everything is current.
            dists = self.ecosystem_dists(installed_all)
            latest_all = pkg_mgr.latest_versions(dists)
            if not any(latest_all.values()):
                raise RuntimeError("could not reach the package index")

            outdated = []
            for dist in dists:
                latest = latest_all.get(dist)
                if not latest:
                    continue
                installed = installed_all.get(dist)
                if installed != latest:
                    outdated.append((dist, installed or "not installed", latest))

            if not outdated:
                this_ver = installed_all.get("tentacletk", "")
                self.sb.message_box(
                    f"<b><hl>{this_ver}</hl> is already the latest version.</b>"
                )
                return

            rows = "<br>".join(
                f"<small>{dist} {installed} → <hl>{latest}</hl></small>"
                for dist, installed, latest in outdated
            )
            # message_box buttons must be Qt StandardButton NAMES -- anything
            # else is dropped and leaves the dialog without its affirmative.
            user_choice = self.sb.message_box(
                f"<b>Update available. Install now?</b><br>{rows}", "Yes", "No"
            )
            if user_choice != "Yes":
                self.sb.message_box("<b>The update was cancelled.</b>")
                return

            # One resolver run for the whole set (update() splits on whitespace).
            pkg_mgr.update(" ".join(dist for dist, _installed, _latest in outdated))
            self.sb.message_box(
                "<b>Update <hl>complete</hl>.</b><br>"
                "<small>Run Reload Scripts (or restart) to apply.</small>"
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
        self.sb.editors.show("style_editor")

    def b021(self):
        """Shortcut Editor"""
        self.sb.editors.show("shortcut_editor")

    def b022(self):
        """UI Browser: open the tentacle UI browser (search, show/hide registered UIs)."""
        self.sb.editors.show("ui_browser")

    def b023(self):
        """Global Shortcuts: the shortcut editor focused on the global triggers --
        the marking-menu activation key, repeat-last, and reopen-last UI. The
        marking-menu chord->menu targets stay in the Menu Bindings combos."""
        self.sb.editors.show("global_shortcuts")

    def b024(self):
        """Preset Editor: every tool's presets in one window -- lock, group into
        collections, back up, and import/share (uitk ``PresetEditor``)."""
        self.sb.editors.show("preset_editor")

    # -------------------------------------------------------------------------
    # Marking Menu Bindings
    # -------------------------------------------------------------------------

    def _get_startmenus(self) -> list:
        """Available startmenu UIs -- via the marking menu's SSoT helper."""
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
        # Write through the menu so it lands in the host-namespaced store (Maya and
        # Blender share one QSettings backend; the bare key would collide). See uitk
        # MarkingMenu._binding_store_key.
        if mm is not None:
            mm.bindings = getattr(mm, "default_bindings", {})


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
