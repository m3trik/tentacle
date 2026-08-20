# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``preferences`` panel.

The per-panel home for logic the Maya and Blender ``Preferences`` forks share (mixed in
ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this class rather than adding a
new module per feature — see the convention in ``tentacle/CLAUDE.md``.

Currently: the marking-menu + standalone-window theme selectors, and the presentation
policy for tools whose external app isn't installed. The theme selectors expose the two
previously hard-pinned uitk window themes so the user can pick light / dark / high-contrast
per window style; both read and write the live MarkingMenu theme properties, which persist
per host and re-theme any already-open windows. The logic is pure uitk, so nothing is
DCC-specific to fork.
"""


class PreferencesMixin:
    """DCC-agnostic ``preferences`` slot behavior.

    ``cmb004`` / ``cmb005`` — themes for the two uitk hosted window styles.
    ``cmb006`` — how tools whose external app / plugin isn't installed are shown
    (``sb.unmet_policy``, read by every ``sb.gate`` call).
    ``header`` > ``tb000`` — re-probe those apps (``Slots.recheck_app_gates``), so a
    mid-session install is picked up without restarting the host.
    """

    @staticmethod
    def _token_label(token: str) -> str:
        """Display label for a setting token (``"dark-grey"`` -> ``"Dark Grey"``).

        Shared by the theme combos and the unavailable-tools combo -- both turn a
        stored lowercase token into a menu entry by the same rule.
        """
        return token.replace("-", " ").title()

    def _theme_items(self) -> dict:
        """``{display label: theme token}`` for every registered uitk theme.

        ``sb.style`` is the Switchboard's lazy proxy for the ``StyleSheet`` class —
        the slots layer reaches uitk through the Switchboard, never by importing
        ``uitk.themes.style_sheet`` directly.
        """
        return {self._token_label(t): t for t in self.sb.style.themes}

    def _marking_menu(self):
        return self.sb.handlers.marking_menu

    def _apply_theme(self, kind: str, widget):
        """Write the combo's selected token to the ``{kind}_theme`` property.

        A change fired while the header row is current yields
        ``currentData() is None`` — no real selection, so this is a no-op rather
        than a crash (the setter rejects unknown/None tokens by design).
        """
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

    #: Display label for an ``unmet_policy`` token, where ``.title()`` isn't the
    #: whole story. Only an OVERRIDE map: the combo's entries and their ORDER come
    #: from ``Switchboard.UNMET_POLICIES``, so a policy added upstream appears here
    #: automatically (labelled from its token) instead of silently going missing —
    #: which is what a hand-maintained token->label dict would have done.
    _UNMET_LABEL_OVERRIDES = {"disable": "Show disabled"}

    def _unmet_label(self, token: str) -> str:
        """Display label for an ``unmet_policy`` token."""
        return self._UNMET_LABEL_OVERRIDES.get(token, self._token_label(token))

    def cmb006_init(self, widget):
        """Presentation for tools whose external app / plugin isn't installed.

        Writes ``sb.unmet_policy``, which every ``sb.gate`` call reads. Applied
        immediately via ``sb.recheck_gates()`` -- the switchboard keeps a registry
        of live gates precisely so a preference the user just changed does not have
        to wait for the next panel build to become visible.
        """
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
        """Persist the chosen presentation policy and re-present the live gates."""
        policy = widget.currentData()
        if policy is None:
            return
        self.sb.unmet_policy = policy
        # Re-apply, don't re-probe: the requirement has not changed, only how an
        # unmet one is shown. (`tb000` below is the other direction -- the app
        # itself may have appeared -- and costs a filesystem scan per app.)
        self.sb.recheck_gates()

    def header_init(self, widget):
        """Header menu — the manual re-probe that pairs with ``cmb006``.

        Built in code rather than in Designer because the panel's ``.ui`` pair is
        shared by every DCC and this entry is DCC-agnostic; the ``#submenu``
        variant carries no header, so it is the panel's alone.
        """
        if not widget.is_initialized:
            # A one-shot action — dismiss the menu once it is triggered.
            widget.menu.hide_on_trigger = True
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
