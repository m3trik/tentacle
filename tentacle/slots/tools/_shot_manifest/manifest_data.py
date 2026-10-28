# !/usr/bin/python
# coding=utf-8
"""Constants, column layout, and pure helper functions for the Shot Manifest UI.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

import html as _html
from typing import Iterable, Optional, Tuple

from pythontk import SHOT_PALETTE, SHOT_STATUS_LEVELS
from pythontk.core_utils.engines.shots.manifest.behaviors import (
    Behaviors as _PyBehaviors,
)

# QSettings namespace
SETTINGS_NS = "ShotManifest"

# Column headers for the manifest tree widget
HEADERS = ["Step", "Section", "Description", "Behaviors", "Start", "End"]

# Fixed column indices for the unified 6-column layout
COL_STEP = 0
COL_SECTION = 1
COL_DESC = 2  # parent: description, child: object name
COL_BEHAVIORS = 3
COL_START = 4
COL_END = 5

STEP_ICON_COLOR = "#8E8E8E"  # neutral dark grey for parent step rows

# Assessment status colours: the pythontk engine's palette, copied -- the
# Colors... editor recolours this panel, never the Shot Sequencer's.
PASTEL_STATUS = SHOT_PALETTE.copy()

# Derived from the palette — used for footer error labels
ERROR_COLOR = PASTEL_STATUS["error"][0]


class ManifestData:
    """ManifestData — module namespace."""

    #: The glyph a status line leads with, by its severity
    #: (``SHOT_STATUS_LEVELS``): its shape says what its colour does.
    LEVEL_GLYPHS = {
        "error": "\u2716",
        "warn": "\u25b2",
        "info": "\u25cf",
        "locked": "\u25a0",
    }
    #: The icon of a row whose worst issue has that severity.
    LEVEL_ICONS = {
        "error": "error",
        "warn": "warning",
        "info": "info",
        "locked": "lock",
    }
    #: The severities, mildest first.
    LEVELS = ("valid", "locked", "info", "warn", "error")

    @staticmethod
    def level(status: str) -> str:
        """*status*'s severity (``SHOT_STATUS_LEVELS``); a severity is its own."""
        if status in ManifestData.LEVELS:
            return status
        return SHOT_STATUS_LEVELS.get(status, "valid")

    @staticmethod
    def status_color(status: str) -> Optional[str]:
        """*status*'s colour in this panel's palette, or ``None`` for none."""
        fg = PASTEL_STATUS.get(status, (None, None))[0]
        return str(fg) if fg else None

    @staticmethod
    def worst(statuses: Iterable[str]) -> Optional[str]:
        """The status of *statuses* at the worst severity (the first of
        equals), or ``None`` when none has one."""
        order = ManifestData.LEVELS.index
        best, rank = None, 0
        for status in statuses:
            r = order(ManifestData.level(status))
            if r > rank:
                best, rank = status, r
        return best

    @staticmethod
    def glyph_html(status: str) -> str:
        """*status*'s glyph in its colour, as rich text (``""``: no severity)."""
        glyph = ManifestData.LEVEL_GLYPHS.get(ManifestData.level(status))
        if not glyph:
            return ""
        color = ManifestData.status_color(status)
        return f'<span style="color:{color}">{glyph}</span>' if color else glyph

    @staticmethod
    def issues_html(issues: Iterable[Tuple[str, str]]) -> str:
        """``(status, text)`` *issues* as rich text, a line each: its glyph,
        in its colour, before the text (escaped; a newline stays one)."""
        lines = []
        for status, text in issues:
            body = _html.escape(text, quote=False).replace("\n", "<br>")
            glyph = ManifestData.glyph_html(status)
            lines.append(f"{glyph}&nbsp;{body}" if glyph else body)
        return "<br>".join(lines)

    @staticmethod
    def fmt_behavior(name: str) -> str:
        """``'fade_in'`` → ``'Fade In'`` (``Behaviors.label``: the marker
        notes a Build writes read the same)."""
        return _PyBehaviors.label(name)

    #: Before a behavior Build marks on the timeline instead of keying: the
    #: shape of the marker it places.
    MARKED_GLYPH = "\u25c6"

    @staticmethod
    def format_behavior_html(
        behaviors, broken=(), status_color=None, stale=(), disabled=(), marked=()
    ) -> str:
        """Return rich-text HTML for a list of behavior names.

        A behavior with an issue is led by its glyph, in its colour
        (:meth:`glyph_html`); the name itself is never coloured.

        Parameters:
            behaviors: Sequence of raw behavior names to display.
            broken: Subset of *behaviors* that failed verification: led by the
                ``missing_behavior`` glyph.
            status_color: Optional colour every behaviour is shown in instead.
            stale: Subset of *behaviors* keyed under an older effect recipe
                (Build re-keys them): led by the ``stale_behavior`` glyph.
            disabled: Behavior types turned off (header menu): struck through
                in the ``locked`` grey, whatever else applies.
            marked: Behavior types set to Marker (header menu): shown after
                :attr:`MARKED_GLYPH`; *broken* then means its marker is missing.
        """
        if not behaviors:
            return ""
        spans = []
        off = set(disabled)
        if off:
            grey = PASTEL_STATUS["locked"][0]
            on = [b for b in behaviors if b not in off]
            html = ManifestData.format_behavior_html(
                on, broken, status_color, stale, marked=marked
            )
            struck = [
                f'<span style="color:{grey};text-decoration:line-through">'
                f"{ManifestData.fmt_behavior(b)}</span>"
                for b in behaviors
                if b in off
            ]
            return "  ".join(([html] if html else []) + struck)
        marked = set(marked)

        def _display(b):
            text = ManifestData.fmt_behavior(b)
            return f"{ManifestData.MARKED_GLYPH} {text}" if b in marked else text

        if status_color:
            for b in behaviors:
                display = _display(b)
                spans.append(f'<span style="color:{status_color}">{display}</span>')
        else:
            broken_set, stale_set = set(broken), set(stale)
            for b in behaviors:
                display = _display(b)
                if b in broken_set:
                    display = f"{ManifestData.glyph_html('missing_behavior')} {display}"
                elif b in stale_set:
                    display = f"{ManifestData.glyph_html('stale_behavior')} {display}"
                spans.append(display)
        return "  ".join(spans)
