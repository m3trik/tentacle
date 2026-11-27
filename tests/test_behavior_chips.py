#!/usr/bin/python
# coding=utf-8
"""The Shot Manifest's Behaviors cell, ``_shot_manifest/behavior_chips.py``:
a chip per behavior and a ``+``, pure Qt (offscreen, plain Python).

Pinned here: the chips are updated in place (an Assess re-colours a table of
them, and making each anew with a style sheet of its own cost about a second
at 212 rows); their look is one style sheet keyed on each chip's state; a chip
too wide for its cell is elided, never clipped; the ``+`` shows only where it
offers something. The cell's states and words are the panel's
(``test_shot_manifest_panel.py``) and pythontk's (``StepStatus.behavior_states``).
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qtpy import QtWidgets

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from tentacle.slots.tools._shot_manifest.behavior_chips import BehaviorChips, Chip


def _chip(raw="fade_in", state="", text=None, line="", struck=False):
    text = text or raw.replace("_", " ").title()
    return Chip(raw, text, state, line or text, f"{text}\n\nClick: ...", struck)


class TestBehaviorChips(unittest.TestCase):
    def setUp(self):
        # In a parent, as in the tree (a top-level window's layout holds it
        # to its minimum size; a cell is sized by its column).
        self.holder = QtWidgets.QWidget()
        self.addCleanup(self.holder.deleteLater)
        self.cell = BehaviorChips(self.holder)

    def _order(self):
        layout = self.cell.layout()
        return [layout.itemAt(i).widget() for i in range(layout.count()) if layout.itemAt(i).widget()]

    def test_a_redraw_updates_the_chips_in_place(self):
        """Every draw and every Assess deleted and remade each chip.
        Fixed: 2026-11-23"""
        self.cell.set_chips([_chip("fade_in"), _chip("fade_out")])
        first = list(self.cell.chips)
        plus = self.cell.plus
        self.cell.set_chips([_chip("fade_in", "built"), _chip("fade_out")])
        self.assertEqual(self.cell.chips, first, "the same buttons")
        self.assertIs(self.cell.plus, plus)
        self.assertEqual(first[0].property(BehaviorChips.STATE_PROPERTY), "built")
        self.assertEqual(first[1].property(BehaviorChips.STATE_PROPERTY), "")
        self.assertEqual([c.styleSheet() for c in first], ["", ""], "no style sheet per chip")

    def test_more_or_fewer_chips_reuse_the_rest_and_keep_the_plus_last(self):
        self.cell.set_chips([_chip("fade_in")])
        kept = self.cell.chips[0]
        self.cell.set_chips([_chip("fade_in"), _chip("fade_out"), _chip("highlight")])
        self.assertIs(self.cell.chips[0], kept)
        self.assertEqual(self._order(), [*self.cell.chips, self.cell.plus])
        self.cell.set_chips([_chip("highlight")])
        self.assertIs(self.cell.chips[0], kept)
        self.assertEqual(self._order(), [kept, self.cell.plus])

    def test_a_reused_chip_reports_its_new_behavior(self):
        seen = []
        self.cell.chip_clicked.connect(lambda raw, _pos: seen.append(raw))
        self.cell.set_chips([_chip("fade_in")])
        self.cell.set_chips([_chip("highlight")])
        self.cell.chips[0].click()
        self.assertEqual(seen, ["highlight"])

    def test_the_plus_shows_only_where_asked(self):
        """A control with nothing to do is hidden (CODE_STANDARD section 15)."""
        self.cell.set_chips([_chip()], plus=False)
        self.assertIsNone(self.cell.plus)
        self.cell.set_chips([_chip()], plus=True, plus_tip="Give it one.")
        self.assertEqual(self.cell.plus.toolTip(), "Give it one.")
        self.cell.set_chips([_chip()], plus=False)
        self.assertIsNone(self.cell.plus)
        self.assertEqual(self._order(), self.cell.chips)

    def test_the_cell_keeps_what_each_chip_says_as_data(self):
        """The detail pane read a chip's state back off its tooltip text."""
        chips = [_chip("fade_in", "built", line="Fade In  (built)")]
        self.cell.set_chips(chips)
        self.assertEqual(self.cell.shown, chips)

    def test_one_style_sheet_colours_every_state(self):
        """The Unity manifest's look: a state's colour on its text, its line on
        its border; a state with neither keeps the faint chrome; the + is quiet
        until hovered."""
        sheet = BehaviorChips.style_sheet(
            {"built": "#9CC69B", "locked": "#888888", "": None},
            lines={"built": "rgba(156,198,155,115)"},
            quiet="rgb(1,2,3)",
            text="rgb(4,5,6)",
        )
        self.assertIn(
            '[chipState="built"] { color: #9CC69B; border-color: rgba(156,198,155,115); }', sheet
        )
        self.assertIn('[chipState="locked"] { color: #888888; }', sheet, "no line: the faint one")
        self.assertNotIn('[chipState=""]', sheet, "no colour: the theme's text")
        self.assertIn(BehaviorChips.CHROME["line"], sheet)
        self.assertIn("color: rgb(1,2,3)", sheet)
        self.assertIn('[chipState="plus"]:hover { color: rgb(4,5,6); }', sheet)
        bare = BehaviorChips.style_sheet({"built": "#9CC69B"})
        self.assertNotIn(":hover { color", bare, "no token: the + keeps the theme's text")

    def test_the_hover_ground_beats_the_bare_ones(self):
        """Equal selectors: the later rule wins. A struck chip and the + have
        no ground, yet show the hover's."""
        sheet = BehaviorChips.style_sheet({"built": "#9CC69B"})
        hover = sheet.index(f":hover {{ background: {BehaviorChips.CHROME['hover']}")
        self.assertGreater(hover, sheet.index(f'[{BehaviorChips.STRUCK_PROPERTY}="true"]'))
        self.assertGreater(hover, sheet.index(f'[chipState="{BehaviorChips.PLUS_STATE}"]'))

    def test_a_struck_chip_is_marked_for_its_bare_look(self):
        """A behavior not in force here has no ground (the Unity manifest's Off)."""
        self.cell.set_chips([_chip("fade_in", "off", struck=True)])
        button = self.cell.chips[0]
        self.assertTrue(button.property(BehaviorChips.STRUCK_PROPERTY))
        self.assertTrue(button.font().strikeOut())
        self.cell.set_chips([_chip("fade_in", "built")])
        self.assertFalse(button.property(BehaviorChips.STRUCK_PROPERTY))
        self.assertFalse(button.font().strikeOut())

    def test_a_chip_too_wide_for_its_cell_is_elided(self):
        """The cell clipped chips past its 110 px. Fixed: 2026-11-23"""
        short = "Fade In"
        long = "A Very Long Behavior Name Indeed"
        self.cell.set_chips([_chip("x", text=long), _chip("y", text=short)])
        self.holder.show()
        self.cell.resize(self.cell.preferred_width(), 20)
        _app.processEvents()
        self.assertEqual(self.cell.chips[0].text(), long)
        self.cell.resize(self.cell.preferred_width() // 2, 20)
        _app.processEvents()
        shown = self.cell.chips[0].text()
        self.assertTrue(shown.endswith("…") and len(shown) < len(long), shown)
        self.assertEqual(self.cell.chips[1].text(), short, "the widest narrowed first")
        self.cell.resize(self.cell.preferred_width(), 20)
        _app.processEvents()
        self.assertEqual(self.cell.chips[0].text(), long, "its whole text again")

    def test_the_plus_is_as_narrow_as_the_unity_manifests(self):
        """The + was 32 px wide against a glyph of 8: a tool button pads its
        text by two spaces of its own. Fixed: 2026-11-24 -- a chip is its
        text, the Unity manifest's padding (5 px the +, 7 px a chip), its 1 px
        border and the 3 px Qt's style sheets add to any tool button."""
        self.holder.setStyleSheet(BehaviorChips.style_sheet({}))
        self.cell.set_chips([_chip("fade_in")])
        for button, unity_padding in ((self.cell.plus, 5), (self.cell.chips[0], 7)):
            button.ensurePolished()
            chrome = button.sizeHint().width() - button.fontMetrics().horizontalAdvance(button.text())
            self.assertEqual(chrome, 2 * unity_padding + 2 + 3, button.text())

    def test_the_preferred_width_holds_every_whole_chip(self):
        self.cell.set_chips([_chip("fade_in"), _chip("fade_out")])
        narrow = self.cell.preferred_width()
        self.cell.set_chips([_chip("fade_in", text="Fade In and a good deal more"), _chip("fade_out")])
        self.assertGreater(self.cell.preferred_width(), narrow)


if __name__ == "__main__":
    unittest.main()
