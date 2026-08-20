# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``settings`` panel.

The per-panel home for logic the Maya and Blender ``Settings`` forks share (mixed in
ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this class rather than adding a
new module per feature — see the convention in ``tentacle/CLAUDE.md``.

Currently: the header Package menu (Update / Reload entries), the ecosystem-wide
in-app updater, the uitk editor launchers, and the marking-menu binding combos.
Only ``tb001`` (Reload Scripts) and the pip interpreter stay DCC-specific.
"""
import html

import pythontk as ptk


class SettingsMixin:
    """DCC-agnostic ``settings`` slot behavior.

    ``tb000`` — ecosystem update check; ``b020``–``b023`` — uitk editors;
    ``cmb_bind_*`` / ``b_reset_bindings`` — marking-menu route combos.

    Concrete slots provide ``_update_python_path()`` (the interpreter whose
    environment pip checks and upgrades) and ``tb001`` (Reload Scripts).
    """

    # The distributions the updater checks and upgrades together. A fix routinely
    # ships as a dependency patch with no tentacletk bump (push.ps1 releases each
    # package independently), and pip's only-if-needed upgrade strategy would leave
    # an already-satisfied pin untouched — so checking tentacletk alone reports
    # "up to date" while e.g. uitk stays stale.
    #
    # Fallback only. The live list is DERIVED per host by :meth:`ecosystem_dists`
    # from the installed metadata, because the DCC engines are extras: hardcoding
    # both here made a Maya install report the engine it cannot use as
    # "blendertk not installed -> X.Y.Z" and pip-install it on the next update.
    ECOSYSTEM_DISTS = ("pythontk", "uitk", "tentacletk")

    @classmethod
    def ecosystem_dists(cls, installed=None):
        """The distributions to check for updates in THIS host.

        Base dependencies + the running host's engine extra + ``tentacletk``, straight
        from the installed metadata (see :meth:`tentacle.Tcl.declared_dists`), so the
        set tracks ``pyproject.toml`` and never reports the other DCC's engine as
        missing. Falls back to :attr:`ECOSYSTEM_DISTS` when metadata is unreadable — a
        source checkout, or a vendored copy — where reporting the engine-free base beats
        reporting nothing.

        Parameters:
            installed (dict): ``{dist: version}`` as returned by
                    ``PackageManager.list_packages``. Any OTHER host's engine that is
                    already present is added, so it keeps being maintained. This is not
                    a corner case: every install made before the engines became extras
                    hard-pinned BOTH, so the whole existing user base has the other
                    DCC's engine sitting in its environment — and dropping it from the
                    check would silently freeze it at its installed version forever.
                    Present-only, so a missing engine is still never installed (that
                    reinstall-the-wrong-engine behavior is the bug this method fixes).
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
            # Every entry is a one-shot action — dismiss the menu once one is triggered.
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

    def check_for_update(self):
        """Check the whole ecosystem for updates and upgrade what's outdated."""
        pkg_mgr = ptk.PackageManager(python_path=self._update_python_path())
        try:
            installed_all = pkg_mgr.list_packages()  # one pip call for every version
            # Concurrent, and failure-isolating: a lookup that could not reach
            # the index comes back None. Comparing against None would read as
            # "outdated", so an unknown is skipped rather than reported — but if
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
            # message_box buttons must be Qt StandardButton NAMES — anything
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
        # Write through the menu so it lands in the host-namespaced store (Maya and
        # Blender share one QSettings backend; the bare key would collide). See uitk
        # MarkingMenu._binding_store_key.
        if mm is not None:
            mm.bindings = getattr(mm, "default_bindings", {})


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
