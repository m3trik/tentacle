#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.utilities, the one Utilities Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- b000 activates the "Measure" tool both hosts register, and confirms it.
- b001 runs the host's own annotation, confirming a tool only when one was armed
  (Blender) and showing a refusal.
- b002 opens the calculator panel by its key name.
- b003 opens the host's pencil and shows a refusal.
The operations themselves are tested in mayatk and blendertk. Annotation and
Blue Pencil are not driven in Maya here: one opens a modal prompt, the other a
toolbar.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.utilities import UtilitiesSlots


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = UtilitiesSlots(self.sb)
        self.ui_utils = self.sb.tk.UiUtils


class TestUtilities(_SlotsCase):
    def test_b000_activates_measure_and_confirms(self):
        self.slots.b000()
        self.ui_utils.set_tool.assert_called_once_with("Measure")
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Measure", message)

    def test_b000_shows_a_refusal(self):
        self.ui_utils.set_tool.side_effect = RuntimeError("No 3D viewport")
        self.slots.b000()
        self.sb.message_box.assert_called_once_with("No 3D viewport")

    def test_b001_confirms_an_armed_tool(self):
        self.ui_utils.annotate.return_value = "Annotation"  # Blender
        self.slots.b001()
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Annotation", message)

    def test_b001_without_a_tool_says_nothing(self):
        self.ui_utils.annotate.return_value = None  # Maya: its prompt made the node
        self.slots.b001()
        self.sb.message_box.assert_not_called()

    def test_b001_shows_a_refusal(self):
        self.ui_utils.annotate.side_effect = RuntimeError("refused")
        self.slots.b001()
        self.sb.message_box.assert_called_once_with("refused")

    def test_b002_routes_to_the_calculator(self):
        self.slots.b002()
        self.sb.handlers.marking_menu.show.assert_called_once_with("calculator")

    def test_b003_opens_the_pencil_quietly(self):
        self.slots.b003()
        self.ui_utils.open_pencil.assert_called_once_with()
        self.sb.message_box.assert_not_called()

    def test_b003_shows_a_refusal(self):
        self.ui_utils.open_pencil.side_effect = RuntimeError("not available")
        self.slots.b003()
        self.sb.message_box.assert_called_once_with("not available")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestUtilitiesInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.sb.tk = maya_module("mayatk")
        prior = self.cmds.currentCtx()
        self.addCleanup(self.cmds.setToolTo, prior)

    def test_b000_arms_the_distance_tool(self):
        self.slots.b000()
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("Measure", message)
        self.assertNotEqual(self.cmds.currentCtx(), "selectSuperContext")

    def test_b002_routes_to_the_calculator(self):
        self.slots.b002()
        self.sb.handlers.marking_menu.show.assert_called_once_with("calculator")


if __name__ == "__main__":
    unittest.main()
