# !/usr/bin/python
# coding=utf-8
"""The Behaviors cell as chips, the same design as the Unity manifest's: one
small pill per behavior, coloured by its state, with its own tooltip and its own
menu on a click, and a ``+`` that adds one.

Pure Qt over plain values: the presenter hands each chip (:class:`Chip`: its
text, its state and what it says) to :meth:`BehaviorChips.set_chips` and answers
its clicks (:attr:`BehaviorChips.chip_clicked`, :attr:`BehaviorChips.plus_clicked`).
A redraw updates the chips in place, touching only those that changed, and
their look is one style sheet keyed on each chip's state
(:meth:`BehaviorChips.style_sheet`), set once on a parent of every row's cell:
no chip has a style sheet of its own.
"""

from __future__ import annotations

from typing import List, Mapping, NamedTuple, Optional, Sequence

from qtpy import QtCore, QtWidgets

__all__ = ["BehaviorChips", "Chip"]


class Chip(NamedTuple):
    """One chip of a Behaviors cell."""

    #: The behavior's raw name (what a click reports).
    behavior: str
    #: What the chip says: its glyphs and the behavior's label.
    text: str
    #: Its look, a key of the style sheet's states (:meth:`BehaviorChips.style_sheet`).
    state: str
    #: Its state in words, as the detail pane lists it.
    line: str
    tooltip: str
    #: Struck through: not in force here.
    struck: bool = False


class _ChipButton(QtWidgets.QToolButton):
    """A chip: a tool button as wide as its text's advance and the style
    sheet's box. ``QToolButton.sizeHint`` measures the text by its bounding
    size and pads it by two spaces of its own, which made the ``+`` four
    times its glyph's width."""

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802 -- Qt's name
        hint = super().sizeHint()
        metrics = self.fontMetrics()
        measured = metrics.size(QtCore.Qt.TextShowMnemonic, self.text()).width()
        padded = measured + 2 * metrics.horizontalAdvance(" ")
        return QtCore.QSize(
            hint.width() - padded + metrics.horizontalAdvance(self.text()), hint.height()
        )


class BehaviorChips(QtWidgets.QWidget):
    """A row of behavior chips and a ``+``.

    Signals:
        chip_clicked(str, QPoint): a chip's behavior (its raw name) and where to
            open its menu (global).
        plus_clicked(QPoint): where to open the add menu (global).
    """

    chip_clicked = QtCore.Signal(str, QtCore.QPoint)
    plus_clicked = QtCore.Signal(QtCore.QPoint)

    #: The dynamic property a chip's look is keyed on (:meth:`style_sheet`).
    STATE_PROPERTY = "chipState"
    #: The dynamic property set on a chip not in force (:attr:`Chip.struck`):
    #: it has no ground.
    STRUCK_PROPERTY = "chipStruck"
    #: The ``+``'s state: the quiet look.
    PLUS_STATE = "plus"
    #: The Unity manifest's chip chrome (``ManifestWindow.uss``), white over
    #: any ground: every chip's faint border and ground, a hovered one's
    #: ground, and the ``+``'s fainter border.
    CHROME = {
        "line": "rgba(255,255,255,36)",
        "ground": "rgba(255,255,255,13)",
        "hover": "rgba(255,255,255,33)",
        "plus_line": "rgba(255,255,255,20)",
    }

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(3)
        layout.addStretch(1)
        self._layout = layout
        self.chips: List[QtWidgets.QToolButton] = []
        self.plus: Optional[QtWidgets.QToolButton] = None
        #: The chips as last set (:meth:`set_chips`), each one's whole text.
        self.shown: List[Chip] = []
        self._fitted: Optional[tuple] = None  # (room, texts) _fit last fitted

    def set_chips(
        self, chips: Sequence[Chip], plus: bool = True, plus_tip: str = ""
    ) -> None:
        """Show *chips*, then a ``+`` where *plus*, in place: a button per
        chip is reused, one whose chip is unchanged is not touched, and only
        those past the new count are deleted."""
        chips = list(chips)
        for index, chip in enumerate(chips):
            if index < len(self.chips):
                if self.shown[index] == chip:
                    continue
                self._show(self.chips[index], chip, self.shown[index])
            else:
                button = self._button()
                button.clicked.connect(
                    lambda _c=False, b=button: self._on_chip_clicked(b)
                )
                self._layout.insertWidget(index, button)
                self.chips.append(button)
                self._show(button, chip, None)
        for button in self.chips[len(chips) :]:
            self._layout.removeWidget(button)
            button.deleteLater()
        del self.chips[len(chips) :]
        self.shown = chips
        self._set_plus(plus, plus_tip)
        if self.isVisible():  # else when it is sized and shown
            self._fit()

    def preferred_width(self) -> int:
        """The width that shows every chip whole, and the ``+``."""
        margins = self._layout.contentsMargins()
        buttons = self.chips + ([self.plus] if self.plus is not None else [])
        width = margins.left() + margins.right()
        width += self._layout.spacing() * max(len(buttons) - 1, 0)
        width += sum(self._widths()) if self.chips else 0
        if self.plus is not None:
            width += self.plus.sizeHint().width()
        return width

    @classmethod
    def style_sheet(
        cls,
        colors: Mapping[str, Optional[str]],
        lines: Optional[Mapping[str, Optional[str]]] = None,
        quiet: str = "",
        text: str = "",
    ) -> str:
        """The chips' look as one style sheet, for a parent of every cell:
        the Unity manifest's. Every chip has :attr:`CHROME`'s faint border and
        ground (none while struck), a state its colour on its text and its
        line on its border; the ``+`` is quiet, its border fainter still,
        until hovered.

        Parameters:
            colors: Each state's text colour; a state with none keeps the
                theme's text.
            lines: Each state's border; a state with none keeps the faint one.
            quiet: The ``+``'s text until hovered (empty: the theme's text).
            text: The hovered ``+``'s text (empty: unchanged).
        """
        button = "BehaviorChips > QToolButton"
        plus = f'{button}[{cls.STATE_PROPERTY}="{cls.PLUS_STATE}"]'
        chrome = cls.CHROME
        # The Unity manifest's box: 16 px high, 7 px padding a chip, 5 px the +.
        # Equal selectors: the later rule wins, so the hover's ground comes last.
        rules = [
            f"{button} {{ border: 1px solid {chrome['line']}; border-radius: 8px;"
            " padding: 0px 7px; margin: 0px; min-height: 14px; max-height: 14px;"
            f" font-size: 11px; background: {chrome['ground']}; }}",
            f'{button}[{cls.STRUCK_PROPERTY}="true"] {{ background: transparent; }}',
            f"{plus} {{ padding: 0px 5px; background: transparent;"
            f" border-color: {chrome['plus_line']};"
            + (f" color: {quiet};" if quiet else "")
            + " }",
        ]
        lines = lines or {}
        for state, color in colors.items():
            line = lines.get(state)
            body = (f" color: {color};" if color else "") + (
                f" border-color: {line};" if line else ""
            )
            if state and body:
                rules.append(f'{button}[{cls.STATE_PROPERTY}="{state}"] {{{body} }}')
        rules.append(f"{button}:hover {{ background: {chrome['hover']}; }}")
        if text:
            rules.append(f"{plus}:hover {{ color: {text}; }}")
        return "\n".join(rules)

    # ---- internals ----------------------------------------------------------

    def _button(self) -> QtWidgets.QToolButton:
        button = _ChipButton(self)
        button.setAutoRaise(True)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        return button

    def _show(
        self, button: QtWidgets.QToolButton, chip: Chip, old: Optional[Chip]
    ) -> None:
        """Make *button* show *chip*, setting only what differs from *old*."""
        button.setProperty("behavior_raw", chip.behavior)
        if old is None or old.text != chip.text:
            button.setText(chip.text)
        if old is None or old.tooltip != chip.tooltip:
            button.setToolTip(chip.tooltip)
        restyle = False
        if chip.struck != (old.struck if old is not None else False):
            font = button.font()
            font.setStrikeOut(chip.struck)
            button.setFont(font)
            button.setProperty(self.STRUCK_PROPERTY, chip.struck)
            restyle = True
        if old is None or old.state != chip.state:
            button.setProperty(self.STATE_PROPERTY, chip.state)
            restyle = True
        if restyle and old is not None:  # a property selector reads it at polish
            button.style().unpolish(button)
            button.style().polish(button)

    def _set_plus(self, plus: bool, tip: str) -> None:
        if plus and self.plus is None:
            self.plus = self._button()
            self.plus.setText("+")
            self.plus.setProperty(self.STATE_PROPERTY, self.PLUS_STATE)
            self.plus.clicked.connect(self._on_plus_clicked)
            self._layout.insertWidget(len(self.chips), self.plus)
        elif not plus and self.plus is not None:
            self._layout.removeWidget(self.plus)
            self.plus.deleteLater()
            self.plus = None
        if self.plus is not None and self.plus.toolTip() != tip:
            self.plus.setToolTip(tip)

    def _on_chip_clicked(self, button: QtWidgets.QToolButton) -> None:
        where = button.mapToGlobal(QtCore.QPoint(0, button.height()))
        self.chip_clicked.emit(button.property("behavior_raw"), where)

    def _on_plus_clicked(self, _checked: bool = False) -> None:
        self.plus_clicked.emit(
            self.plus.mapToGlobal(QtCore.QPoint(0, self.plus.height()))
        )

    def _widths(self) -> List[int]:
        """Each chip's width showing its whole text: the chips' chrome (one
        style sheet: the same for every chip, measured off the first) and its
        text's advance."""
        first = self.chips[0]
        first.ensurePolished()  # its chrome is the style sheet's
        metrics = first.fontMetrics()
        chrome = first.sizeHint().width() - metrics.horizontalAdvance(first.text())
        return [chrome + metrics.horizontalAdvance(c.text) for c in self.shown]

    def _fit(self) -> None:
        """Elide the chips' texts to the cell's width (never clip them): the
        room left beside the ``+`` is shared out, the widest chips narrowed
        first; at its preferred width each says its whole text."""
        if not self.chips:
            return
        margins = self._layout.contentsMargins()
        room = self.width() - margins.left() - margins.right()
        room -= self._layout.spacing() * (len(self.chips) - (0 if self.plus else 1))
        if self.plus is not None:
            room -= self.plus.sizeHint().width()
        key = (room, tuple(c.text for c in self.shown))
        if key == self._fitted:
            return  # nothing it is fitted to changed
        self._fitted = key
        widths = self._widths()
        cap = max(widths)
        if sum(widths) > room:  # the widest share the room: one cap for all
            rest, narrowed = room, sorted(widths)
            for i, w in enumerate(narrowed):
                share = rest // (len(narrowed) - i)
                if w > share:
                    cap = share
                    break
                rest -= w
        metrics = self.chips[0].fontMetrics()
        least = metrics.horizontalAdvance("…")  # an ellipsis at least
        for button, chip, width in zip(self.chips, self.shown, widths):
            shown = chip.text
            if width > cap:
                chrome = width - metrics.horizontalAdvance(chip.text)
                shown = metrics.elidedText(
                    chip.text, QtCore.Qt.ElideRight, max(cap - chrome, least)
                )
            if button.text() != shown:
                button.setText(shown)

    def resizeEvent(self, event) -> None:  # noqa: N802 -- Qt's name
        super().resizeEvent(event)
        self._fit()

    def showEvent(self, event) -> None:  # noqa: N802 -- Qt's name
        super().showEvent(event)
        self._fit()  # set while hidden (a collapsed row): fit now
