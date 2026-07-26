# !/usr/bin/python
# coding=utf-8
"""Marking-menu + standalone window theme selectors (DCC-agnostic).

Exposes the two previously hard-pinned uitk window themes so the user can pick
light / dark / high-contrast per window style. Both selectors read and write the
live MarkingMenu theme properties, which persist per host and re-theme any
already-open windows. Shared by every DCC's Preferences slot — the logic is pure
uitk, so nothing is DCC-specific to fork.
"""
from uitk.themes.style_sheet import StyleSheet


class PreferencesThemeMixin:
    """``cmb004`` / ``cmb005`` — themes for the two uitk hosted window styles."""

    @staticmethod
    def _theme_label(token: str) -> str:
        return token.replace("-", " ").title()

    def _theme_items(self) -> dict:
        """``{display label: theme token}`` for every registered uitk theme."""
        return {self._theme_label(t): t for t in StyleSheet.themes}

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
        widget.setCurrentText(self._theme_label(self._marking_menu().menu_theme))

    def cmb004(self, index, widget):
        """Apply the marking-menu theme (persists + re-themes live windows)."""
        self._apply_theme("menu", widget)

    def cmb005_init(self, widget):
        """Standalone tool-window theme."""
        if not widget.is_initialized:
            widget.add(self._theme_items(), header="Window")
        widget.setCurrentText(self._theme_label(self._marking_menu().window_theme))

    def cmb005(self, index, widget):
        """Apply the standalone-window theme (persists + re-themes live windows)."""
        self._apply_theme("window", widget)
