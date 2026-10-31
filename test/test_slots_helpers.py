#!/usr/bin/python
# coding=utf-8
"""Tests for the host-free helpers on tentacle's shared ``Slots`` base.

``require_selection``, ``activate_tool`` and ``run_operation`` reach the host only through
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


class TestHostVisibilityOnRealWidgets(unittest.TestCase):
    """``Slots.requires`` and ``Slots.hide_unless`` over a real (offscreen)
    switchboard and widgets: what stays hidden, and what a gate or a group
    can no longer bring back."""

    @classmethod
    def setUpClass(cls):
        from qtpy import QtWidgets
        from uitk import Switchboard

        cls.QtWidgets = QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.sb = Switchboard(context_tags={"blender"})

    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.slots = Slots(self.sb)
        self.window = self.QtWidgets.QWidget()
        self.addCleanup(self.window.deleteLater)

    def _in_group(self):
        from uitk.widgets.collapsableGroup import CollapsableGroup

        group = CollapsableGroup("Advanced", self.window)
        group.setLayout(self.QtWidgets.QVBoxLayout())
        widget = self.QtWidgets.QPushButton()
        group.layout().addWidget(widget)
        self.window.show()
        return group, widget

    def test_a_capability_hide_survives_a_group_expand_and_a_gate(self):
        group, widget = self._in_group()
        self.assertFalse(self.slots.hide_unless(widget, False))
        group.setChecked(False)
        group.setChecked(True)
        self.assertTrue(widget.isHidden(), "the expand re-showed it")
        self.assertTrue(self.sb.gate(widget, True))  # the app is there...
        self.assertTrue(widget.isHidden(), "...but the host still cannot serve it")
        self.assertFalse(self.sb.gate(widget, False))
        self.assertTrue(widget.isHidden())

    def test_a_served_control_is_left_alone(self):
        _group, widget = self._in_group()
        self.assertTrue(self.slots.hide_unless(widget, True))
        self.assertFalse(widget.isHidden())
        self.assertIsNone(getattr(widget, "hidden_by_policy", None))

    def test_requires_hides_the_other_hosts_widget_for_good(self):
        group, widget = self._in_group()
        self.assertFalse(self.slots.requires(widget, "maya"))
        group.setChecked(False)
        group.setChecked(True)
        self.assertTrue(widget.isHidden())
        self.assertEqual(widget.hidden_by_policy, "requires")

    def test_requires_with_no_host_tags_nothing(self):
        _group, widget = self._in_group()
        self.assertTrue(self.slots.requires(widget, None))
        self.assertIsNone(widget.property("requires"))
        self.assertFalse(widget.isHidden())
        self.assertTrue(self.slots.requires(widget, "blender"))
        self.assertFalse(widget.isHidden())


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



class TestRunOperation(_SlotsCase):
    """A host operation called and reported: its refusal, its empty answer, its result."""

    def test_the_result_is_returned_and_nothing_said(self):
        op = mock.Mock(return_value=["pCube1"])
        self.assertEqual(self.slots.run_operation(op, None, cuts=2, empty="Nothing."), ["pCube1"])
        op.assert_called_once_with(None, cuts=2)
        self.sb.message_box.assert_not_called()

    def test_an_empty_answer_says_the_callers_message(self):
        self.assertEqual(self.slots.run_operation(mock.Mock(return_value=[]), empty="Select faces."), [])
        self.sb.message_box.assert_called_once_with("Select faces.")

    def test_an_empty_answer_with_no_message_is_silent(self):
        self.slots.run_operation(mock.Mock(return_value=[]))
        self.sb.message_box.assert_not_called()

    def test_a_refusal_shows_the_hosts_reason_and_returns_none(self):
        for error in (ValueError("Select two vertices."), RuntimeError("Maya refused.")):
            with self.subTest(error=type(error).__name__):
                self.sb.message_box.reset_mock()
                self.assertIsNone(self.slots.run_operation(mock.Mock(side_effect=error)))
                self.sb.message_box.assert_called_once_with(str(error))

    def test_any_other_error_is_not_swallowed(self):
        with self.assertRaises(TypeError):
            self.slots.run_operation(mock.Mock(side_effect=TypeError("a bug")))


if __name__ == "__main__":
    unittest.main()
