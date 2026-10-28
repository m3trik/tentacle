#!/usr/bin/python
# coding=utf-8
"""Tests for the host-free helpers on tentacle's shared ``Slots`` base.

``require_selection`` and ``activate_tool`` reach the host only through
``self.tk``: a fake toolkit stands in for it here and records the calls (plain
unittest, no DCC). What the toolkit answers -- ``CoreUtils.selected_objects``,
``UiUtils.set_tool`` -- is tested in mayatk and blendertk.
"""
import unittest
from unittest import mock

from tentacle.slots._slots import Slots


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = Slots(self.sb)
        self.tk = self.sb.tk


class TestRequireSelection(_SlotsCase):
    """The selection through the toolkit, or None after the message."""

    def test_the_selection_is_returned_and_nothing_said(self):
        self.tk.CoreUtils.selected_objects.return_value = ["pCube1", "pCube2"]
        self.assertEqual(self.slots.require_selection(), ["pCube1", "pCube2"])
        self.tk.CoreUtils.selected_objects.assert_called_once_with()
        self.sb.message_box.assert_not_called()

    def test_an_empty_selection_says_so_and_returns_none(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.assertIsNone(self.slots.require_selection())
        self.sb.message_box.assert_called_once_with(Slots.NOTHING_SELECTED)

    def test_the_callers_message_replaces_the_default(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.assertIsNone(self.slots.require_selection("Select the shells to stack."))
        self.sb.message_box.assert_called_once_with("Select the shells to stack.")


class TestActivateTool(_SlotsCase):
    """One toolkit call by the tool's shared name; a confirmation or the host's reason."""

    def test_a_set_tool_is_confirmed(self):
        self.assertTrue(self.slots.activate_tool("Multi-Cut"))
        self.tk.UiUtils.set_tool.assert_called_once_with("Multi-Cut")
        self.sb.message_box.assert_called_once_with("<hl>Multi-Cut</hl> tool active.")

    def test_a_refusal_shows_the_hosts_reason(self):
        for error in (
            ValueError("Multi-Cut needs an active or selected mesh object."),
            RuntimeError("No 3D viewport available."),
        ):
            with self.subTest(error=type(error).__name__):
                self.sb.message_box.reset_mock()
                self.tk.UiUtils.set_tool.side_effect = error
                self.assertFalse(self.slots.activate_tool("Multi-Cut"))
                self.sb.message_box.assert_called_once_with(str(error))

    def test_any_other_error_is_not_swallowed(self):
        self.tk.UiUtils.set_tool.side_effect = TypeError("a bug, not a refusal")
        with self.assertRaises(TypeError):
            self.slots.activate_tool("Multi-Cut")
        self.sb.message_box.assert_not_called()


if __name__ == "__main__":
    unittest.main()
