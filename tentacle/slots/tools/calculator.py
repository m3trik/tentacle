# !/usr/bin/python
# coding=utf-8
"""Calculator: expressions, length units, and the scene's frame-rate helpers.

One Slots class for both hosts over the host toolkit's ``CalculatorController``
(``self.tk``): the math is pythontk's, the frame rate and current frame the
host's.

The display only ever holds what the user typed or a result: a failure keeps
the expression where it was, marks the field and says why in the footer, in the
shared status palette (``ptk.Palette.status()``). The footer is the tape: it
names what produced the value on display.
"""

import pythontk as ptk

from tentacle import Slots


class CalculatorSlots(Slots):
    #: The keypad: ``(label, row, column)``. A key types :attr:`_KEY_TEXT`'s
    #: entry for its label (the engine's operator for a typeset symbol), or
    #: its label itself; the keys in :attr:`_KEY_ACTIONS` run a method instead.
    _CALC_BUTTONS = [
        ("C", 0, 0),
        ("(", 0, 1),
        (")", 0, 2),
        ("÷", 0, 3),  # division sign
        ("7", 1, 0),
        ("8", 1, 1),
        ("9", 1, 2),
        ("×", 1, 3),  # multiplication sign
        ("4", 2, 0),
        ("5", 2, 1),
        ("6", 2, 2),
        ("−", 2, 3),  # minus sign
        ("1", 3, 0),
        ("2", 3, 1),
        ("3", 3, 2),
        ("+", 3, 3),
        ("0", 4, 0),
        (".", 4, 1),
        ("⌫", 4, 2),  # erase to the left
        ("=", 4, 3),
    ]
    _KEY_TEXT = {"÷": "/", "×": "*", "−": "-"}
    _KEY_ACTIONS = {"C": "on_clear", "⌫": "on_backspace", "=": "on_equal"}
    _KEY_TIPS = {
        "C": "Clear the display.",
        "⌫": "Delete the character left of the cursor.",
        "=": "Evaluate the expression (Enter).",
    }
    #: Keys that begin a new number: pressed right after a result, they start
    #: over instead of appending to it. An operator key continues from it.
    _STARTS_NUMBER = frozenset("0123456789.(")
    _UNITS = ["mm", "cm", "m", "km", "in", "ft", "yd", "mi"]
    #: The engine's answer for an expression it cannot evaluate.
    _ENGINE_ERROR = "Error"

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.calculator
        self.controller = self.tk.CalculatorController()
        self._result_shown = False  # the display holds a result, not typing
        self._failed = False  # the display is marked as an error

        self._init_calc_grid()
        self._init_time_grid()
        self._init_units()

        self.ui.txt_display.returnPressed.connect(self.on_equal)
        self.ui.txt_display.textEdited.connect(self._on_typed)

    def header_init(self, widget):
        """Configure header help text."""
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Calculator",
                body="Expression-based calculator with unit conversion and "
                "scene time helpers.",
                sections=[
                    (
                        "Expression entry",
                        [
                            "Type, or click the keys, to build an expression in "
                            "the display; keys insert at the cursor.",
                            f"Press <b>=</b> or {self.sb.tooltip.kbd('Enter')} "
                            "to evaluate. The footer keeps the expression that "
                            "gave the result.",
                            "After a result, a number key starts over and an "
                            "operator key continues from it.",
                            "Standard math operators plus functions: "
                            "<code>sin</code>, <code>cos</code>, <code>tan</code>, "
                            "<code>sqrt</code>, <code>pow</code>, <code>pi</code>, "
                            "etc.",
                            "An expression that can't be evaluated stays in the "
                            "display, marked, with the reason in the footer.",
                        ],
                    ),
                    (
                        "Unit conversion",
                        [
                            "Pick <b>From</b> and <b>To</b> units (mm, cm, m, km, "
                            "in, ft, yd, mi); the arrow swaps them.",
                            "Press <b>Convert</b> to convert the current display "
                            "value.",
                        ],
                    ),
                    (
                        "Animation helpers",
                        [
                            "<b>Get FPS</b> — read the scene's frame rate.",
                            "<b>Get Time</b> — read the current frame.",
                            "<b>Frames → Sec</b> / <b>Sec → Frames</b> — convert "
                            "the display value using the scene FPS.",
                        ],
                    ),
                ],
            )
        )

    # ------------------------------------------------------------------ grid builders
    def _init_calc_grid(self):
        from qtpy import QtCore, QtWidgets

        for text, r, c in self._CALC_BUTTONS:
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(35)
            # A key never takes focus: typing carries on in the display.
            btn.setFocusPolicy(QtCore.Qt.NoFocus)
            font = btn.font()
            font.setPointSize(10)
            btn.setFont(font)
            if text in self._KEY_TIPS:
                btn.setToolTip(self._KEY_TIPS[text])
            self.ui.calc_container.layout().addWidget(btn, r, c)

            action = self._KEY_ACTIONS.get(text)
            if action:
                btn.clicked.connect(getattr(self, action))
            else:
                key = self._KEY_TEXT.get(text, text)
                btn.clicked.connect(lambda checked=False, t=key: self.on_input(t))

    def _init_time_grid(self):
        # The animation-helper buttons (the .ui's ``maya_container``, a saved name).
        from qtpy import QtWidgets

        buttons = [
            ("Get FPS", self.get_fps, "Show the scene's frame rate."),
            ("Get Time", self.get_current_time, "Show the current frame."),
            (
                "Frames → Sec",
                self.frames_to_sec,
                "Convert the display from frames to seconds at the scene's rate.",
            ),
            (
                "Sec → Frames",
                self.sec_to_frames,
                "Convert the display from seconds to frames at the scene's rate.",
            ),
        ]
        cols = 2
        for i, (text, func, tip) in enumerate(buttons):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(30)
            btn.setToolTip(tip)
            btn.clicked.connect(func)
            self.ui.maya_container.layout().addWidget(btn, i // cols, i % cols)

    def _init_units(self):
        self.ui.cmb_unit_from.addItems(self._UNITS)
        self.ui.cmb_unit_to.addItems(self._UNITS)
        self.ui.cmb_unit_from.setCurrentText("cm")
        self.ui.cmb_unit_to.setCurrentText("m")
        self.ui.cmb_unit_from.setToolTip("Convert from this unit.")
        self.ui.cmb_unit_to.setToolTip("Convert to this unit.")
        self.ui.btn_swap_units.setIcon(
            self.sb.IconManager.get("arrow_right", size=(14, 14))
        )
        self.ui.btn_swap_units.clicked.connect(self.on_swap_units)
        self.ui.btn_convert.clicked.connect(self.on_convert_units)

    # ------------------------------------------------------------------ display state
    def _show(self, value, note=""):
        """Put a result on the display and its provenance on the footer."""
        self._clear_error()
        self.ui.txt_display.setText(value)
        self.ui.footer.setText(note)
        self._result_shown = True

    def _fail(self, message):
        """Mark the display as an error, keeping what the user typed, and say
        why on the footer in the shared status palette's error color."""
        self._failed = True
        self._result_shown = False
        self.ui.txt_display.set_action_color("invalid")
        self.ui.footer.setText(message, color=ptk.Palette.status()["error"][0])

    def _clear_error(self):
        if self._failed:
            self._failed = False
            self.ui.txt_display.reset_action_color()
            self.ui.footer.setText("")

    def _on_typed(self, _text=""):
        """The user edited the display: it is their expression again, so the
        footer's note about the previous value no longer applies."""
        if self._result_shown:
            self._result_shown = False
            self.ui.footer.setText("")
        self._clear_error()

    # ------------------------------------------------------------------ calculator actions
    def on_input(self, text):
        if self._result_shown and text in self._STARTS_NUMBER:
            self.ui.txt_display.clear()
        if self._result_shown:
            self.ui.txt_display.end(False)  # an operator continues the result
        self._on_typed()
        self.ui.txt_display.insert(text)

    def on_clear(self):
        self._on_typed()
        self.ui.txt_display.clear()
        self.ui.footer.setText("")

    def on_backspace(self):
        self._on_typed()
        self.ui.txt_display.backspace()

    def on_equal(self):
        expression = self.ui.txt_display.text().strip()
        if not expression or self._result_shown:
            return  # nothing to evaluate; a result keeps the tape that made it
        result = self.controller.calculate(expression)
        if result in ("", self._ENGINE_ERROR):
            self._fail(f"Can't evaluate: {expression}")
            return
        self._show(result, f"{expression} =")

    def _resolve_display_value(self):
        """Evaluate the display as an expression; return a float, or ``None`` when
        it is empty or can't be evaluated (the display is then marked)."""
        expression = self.ui.txt_display.text().strip()
        if not expression:
            self._fail("Enter a value first.")
            return None
        try:
            return float(self.controller.calculate(expression))
        except ValueError:  # the engine's "Error"
            self._fail(f"Can't evaluate: {expression}")
            return None

    def on_swap_units(self):
        source = self.ui.cmb_unit_from.currentText()
        self.ui.cmb_unit_from.setCurrentText(self.ui.cmb_unit_to.currentText())
        self.ui.cmb_unit_to.setCurrentText(source)

    def on_convert_units(self):
        value = self._resolve_display_value()
        if value is None:
            return
        source = self.ui.cmb_unit_from.currentText()
        target = self.ui.cmb_unit_to.currentText()
        result = self.controller.convert_unit(value, source, target)
        if result == self._ENGINE_ERROR:
            self._fail(f"Can't convert {source} to {target}.")
            return
        self._show(result, f"{self._fmt(value)} {source} = {result} {target}")

    # ------------------------------------------------------------------ animation helpers
    def get_fps(self):
        self._show(str(self.controller.get_fps_value()), "Scene frame rate (fps)")

    def get_current_time(self):
        self._show(self.controller.get_current_time(), "Current frame")

    def frames_to_sec(self):
        self._apply_time_helper(self.controller.frames_to_sec, "frames", "s")

    def sec_to_frames(self):
        self._apply_time_helper(self.controller.sec_to_frames, "s", "frames")

    def _apply_time_helper(self, convert, source, target):
        """Resolve the display (as an expression) then run ``convert(value)`` on it."""
        value = self._resolve_display_value()
        if value is None:
            return
        result = convert(value)
        if result == self._ENGINE_ERROR:
            self._fail("Can't read the scene's frame rate.")
            return
        fps = self.controller.get_fps_value()
        self._show(
            result,
            f"{self._fmt(value)} {source} = {result} {target} at {self._fmt(fps)} fps",
        )

    @staticmethod
    def _fmt(value):
        """*value* for the tape: every digit it was computed with, no ``.0``."""
        return f"{value:.15g}"
