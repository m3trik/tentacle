# !/usr/bin/python
# coding=utf-8
"""Shared HUD framework (DCC-agnostic): warnings + the prev-command line.

Lightweight pre-build checks shown as colored icons (immediately) and formatted detail
lines (after the regular HUD-build delay). The framework — preference gating, evaluation,
icon/detail rendering — is pure Qt/HTML logic; only the *checks* are DCC-specific, so each
DCC's hud slot subclasses this and supplies its own ``WARNING_DEFS`` (+ ``_scene_is_unsaved``).

Each WARNING_DEFS spec defines:
    key       - QCheckBox objectName in the preferences UI gating the check.
    icon      - Unicode glyph used in the early icon row.
    color     - HTML color for both icon and detail line.
    label     - Short tag rendered next to the icon.
    check     - Callable(self) -> bool. True means "trigger this warning".
    describe  - Callable(self) -> str. Detail line shown post-delay.

Adding a new check is a one-line tuple addition in the DCC subclass — no other edits needed.

The trailing "Prev Command" line lives here too — it reads ``sb.prev_slot``, which is
DCC-agnostic, so both DCC hud slots share one implementation (and one length cap).
"""

import pythontk as ptk


class HudWarningsMixin:
    WARNING_DEFS: tuple = ()
    SKIP_ON_UNSAVED_KEY = "chk_warn_skip_unsaved"
    #: Max characters of a slot summary shown on the "Prev Command" line.
    PREV_COMMAND_MAX_CHARS = 120

    def _scene_is_unsaved(self) -> bool:
        """True if no saved scene file exists on disk — DCC subclasses override."""
        return False

    def _warn_is_enabled(self, key: str) -> bool:
        """Return True if the user has opted-in to the warning in preferences.

        Triggers lazy load of the preferences UI on first call so checkbox
        state restoration is available even before the user opens prefs.
        """
        try:
            prefs = self.sb.loaded_ui.preferences
        except AttributeError:
            return False
        widget = getattr(prefs, key, None)
        if widget is None:
            return False
        try:
            return bool(widget.isChecked())
        except AttributeError:
            return False

    def evaluate_warnings(self) -> list:
        """Return the subset of WARNING_DEFS whose check fires and is enabled."""
        if self._warn_is_enabled(self.SKIP_ON_UNSAVED_KEY) and self._scene_is_unsaved():
            return []
        active = []
        for spec in self.WARNING_DEFS:
            if not self._warn_is_enabled(spec["key"]):
                continue
            try:
                triggered = bool(spec["check"](self))
            except Exception as error:
                print(f"{__file__}: warning check {spec['key']} failed: {error}")
                continue
            if triggered:
                active.append(spec)
        return active

    def insert_warning_icons(self, hud, warnings) -> None:
        """Insert a single-line row of colored badges; one per active warning."""
        if not warnings:
            return
        badges = "&nbsp;&nbsp;".join(
            f'<font style="color: {w["color"]};">{w["icon"]} {w["label"]}</font>'
            for w in warnings
        )
        hud.insertText(f'<span style="font-size: 150%;">{badges}</span>')

    def insert_warning_details(self, hud, warnings) -> None:
        """Insert a formatted detail line per active warning."""
        for w in warnings:
            try:
                msg = w["describe"](self)
            except Exception as error:
                print(f"{__file__}: warning describe {w['key']} failed: {error}")
                continue
            if msg:
                hud.insertText(msg)

    def insert_prev_command(self, hud, method) -> None:
        """Insert the last-used command as a single, length-capped line.

        Slot docstrings range from a one-line summary to a full ``Parameters:``
        block, so only the leading summary is shown, and that is truncated at
        ``PREV_COMMAND_MAX_CHARS`` — an undocumented or verbose slot must not be
        able to push the rest of the HUD off-screen.

        Parameters:
            hud (obj): The uitk TextEdit the HUD is composed into.
            method (obj): The previously run slot (``sb.prev_slot``), or None.
        """
        if not method:
            return
        doc = (getattr(method, "__doc__", None) or "").strip()
        summary = next((ln.strip() for ln in doc.splitlines() if ln.strip()), "")
        if not summary:  # undocumented slot: fall back to its name.
            summary = getattr(method, "__name__", "") or str(method)
        summary = ptk.StrUtils.truncate(summary, self.PREV_COMMAND_MAX_CHARS, "end")
        hud.insertText(f'Prev Command: <font style="color: Yellow;">{summary}</font>')
