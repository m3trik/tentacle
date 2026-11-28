# !/usr/bin/python
# coding=utf-8
"""Constants, column layout, and pure helper functions for the Shot Manifest UI.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

import html as _html
from typing import Iterable, Optional, Tuple

from pythontk import SHOT_PALETTE, SHOT_STATUS_LEVELS, Color, StepStatus
from pythontk.core_utils.engines.shots.manifest.behaviors import (
    Behaviors as _PyBehaviors,
)

# QSettings namespace
SETTINGS_NS = "ShotManifest"

# Column headers for the manifest tree widget
HEADERS = ["Step", "Section", "Description", "Behaviors", "Start", "End", "Status"]

# Fixed column indices for the unified layout
COL_STEP = 0
COL_SECTION = 1
COL_DESC = 2  # parent: description, child: object name
COL_BEHAVIORS = 3
COL_START = 4
COL_END = 5
#: The row's cause in a few words (``StepStatus.LABELS``), so it reads without
#: a hover. The last column by index, drawn second: beside the step it marks.
COL_STATUS = 6

#: A cell a Local Edit changed, drawn as a redline: the sheet's value is in
#: its tooltip.
EDIT_COLOR = "#E0A040"

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
        "success": "\u270e",  # edited by hand, kept: a pencil, never the lock
    }
    #: The icon of a row whose worst issue has that severity.
    LEVEL_ICONS = {
        "error": "error",
        "warn": "warning",
        "info": "info",
        "locked": "lock",
        "success": "edit",
    }
    #: The severities, mildest first.
    LEVELS = ("valid", "locked", "success", "info", "warn", "error")

    @staticmethod
    def label(status: Optional[str]) -> str:
        """*status* in a few words (``StepStatus.LABELS``); ``""`` for none."""
        return StepStatus.LABELS.get(status, "") if status else ""

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
        """``'highlight'`` → ``'Highlight'``, ``'show'`` → ``'Visibility · show'``
        (``Behaviors.label``: the marker
        notes a Build writes read the same)."""
        return _PyBehaviors.label(name)

    #: Before a behavior Build marks on the timeline instead of keying: the
    #: shape of the marker it places.
    MARKED_GLYPH = "\u25c6"

    #: The behavior states (``StepStatus.BEHAVIOR_STATES``) not in force on
    #: the row: drawn struck through, in the locked grey.
    STRUCK_STATES = ("taken", "off")

    @staticmethod
    def chip_look(state: str) -> Tuple[Optional[str], str, bool]:
        """A behavior chip's colour, glyph and strike for *state* (a
        ``StepStatus.BEHAVIOR_STATES`` key), in this panel's palette as it is
        now (the Colors... editor's): its status's colour and its severity's
        glyph (:attr:`LEVEL_GLYPHS`) -- in order (``valid``) the check's green
        and none; added by a Local Edit, the redline's :data:`EDIT_COLOR` and
        the pencil; not in force (:attr:`STRUCK_STATES`), struck in its grey
        and none; not assessed, the theme's text (``None``) and none."""
        status = StepStatus.BEHAVIOR_STATES.get(state, (None, ""))[0]
        if state in ManifestData.STRUCK_STATES:
            return ManifestData.status_color(status), "", True
        if state == "added":
            return EDIT_COLOR, ManifestData.LEVEL_GLYPHS["success"], False
        if status is None:
            return None, "", False
        if status == "valid":
            return ManifestData.status_color("success"), "", False
        glyph = ManifestData.LEVEL_GLYPHS.get(ManifestData.level(status), "")
        return ManifestData.status_color(status), glyph, False

    #: How much of its colour a chip's border shows, by its severity (an added
    #: one: ``"edit"``): the Unity manifest's lines (``EditorLook.uss``), the
    #: brightest hue the faintest.
    LINE_ALPHA = {"error": 0.65, "warn": 0.6, "info": 0.55, "valid": 0.45, "edit": 0.7}

    @staticmethod
    def chip_line(state: str) -> Optional[str]:
        """A behavior chip's border for *state*: its colour
        (:meth:`chip_look`) at its severity's :attr:`LINE_ALPHA`, as
        ``rgba()``; ``None`` -- the faint border every chip has -- where it
        has no colour or no severity of its own (not in force, locked)."""
        color, _mark, struck = ManifestData.chip_look(state)
        status = StepStatus.BEHAVIOR_STATES.get(state, (None, ""))[0]
        level = "edit" if state == "added" else ManifestData.level(status) if status else None
        alpha = ManifestData.LINE_ALPHA.get(level)
        if color is None or struck or alpha is None:
            return None
        r, g, b = Color.from_hex(color).rgb
        return f"rgba({r},{g},{b},{round(alpha * 255)})"
