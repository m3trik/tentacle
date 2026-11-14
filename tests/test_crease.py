#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.crease, the one Crease Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- tb000 forwards the amount, and the angle only while "Set Smoothing Angle" is
  checked; an empty result (nothing to crease) is reported.
- b002 transfers on the selection, shows the host's reason when it refuses and
  says so when nothing is selected.
The operations themselves are tested in mayatk and blendertk.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.crease import CreaseSlots


def _widget(amount=10, set_angle=False, angle=30):
    """A Crease button whose option-box menu reads the given values."""
    widget = mock.MagicMock()
    menu = widget.option_box.menu
    menu.s003.value.return_value = amount
    menu.chk000.isChecked.return_value = set_angle
    menu.s004.value.return_value = angle
    return widget


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = CreaseSlots(self.sb)
        self.components = self.sb.tk.Components


class TestTb000Crease(_SlotsCase):
    def test_the_amount_reaches_the_selection_without_an_angle(self):
        self.components.crease_edges.return_value = ["e"]
        self.slots.tb000(_widget(amount=8, set_angle=False, angle=45))
        self.components.crease_edges.assert_called_once_with(None, amount=8, angle=None)
        self.sb.message_box.assert_not_called()

    def test_the_angle_rides_only_while_checked(self):
        self.components.crease_edges.return_value = ["e"]
        self.slots.tb000(_widget(amount=8, set_angle=True, angle=45))
        self.components.crease_edges.assert_called_once_with(None, amount=8, angle=45)

    def test_zero_amount_is_passed_through(self):
        """Amount 0 (no crease) still calls through, it is not a warning."""
        self.components.crease_edges.return_value = ["e"]
        self.slots.tb000(_widget(amount=0))
        self.assertEqual(self.components.crease_edges.call_args.kwargs["amount"], 0)

    def test_nothing_to_crease_says_so(self):
        self.components.crease_edges.return_value = []
        self.slots.tb000(_widget())
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("selection", message)


class TestB002TransferCreases(_SlotsCase):
    def test_transfers_on_the_selection(self):
        self.components.transfer_creased_edges.return_value = ["target"]
        self.slots.b002(None)
        self.components.transfer_creased_edges.assert_called_once_with(None)
        self.sb.message_box.assert_not_called()

    def test_nothing_selected_asks_for_a_source_and_a_target(self):
        self.components.transfer_creased_edges.return_value = []
        self.slots.b002(None)
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("source", message)

    def test_a_refusal_shows_the_hosts_reason(self):
        self.components.transfer_creased_edges.side_effect = ValueError("one mesh")
        self.slots.b002(None)
        self.sb.message_box.assert_called_once_with("one mesh")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestCreaseInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.src = self.cmds.polyCube(name="cr_src")[0]

    def _creases(self, node):
        return self.cmds.polyCrease(f"{node}.e[*]", query=True, value=True) or []

    def test_crease_the_selected_object(self):
        self.cmds.select(self.src)
        self.slots.tb000(_widget(amount=5))
        self.assertEqual(self._creases(self.src), [5.0] * 12)
        self.sb.message_box.assert_not_called()

    def test_nothing_selected_creases_nothing_and_says_so(self):
        self.cmds.select(clear=True)
        self.slots.tb000(_widget(amount=5))
        self.assertTrue(all(v <= 0 for v in self._creases(self.src)))
        self.assertTrue(self.sb.message_box.called)

    def test_transfer_from_the_first_selected(self):
        tgt = self.cmds.polyCube(name="cr_tgt")[0]
        self.cmds.polyCrease(f"{self.src}.e[0]", value=5.0)
        self.cmds.select([self.src, tgt])
        self.slots.b002(None)
        self.assertEqual(self._creases(tgt)[0], 5.0)
        self.sb.message_box.assert_not_called()

    def test_transfer_with_one_object_warns(self):
        self.cmds.select(self.src)
        self.slots.b002(None)
        self.assertTrue(self.sb.message_box.called)

    def test_transfer_with_nothing_selected_warns(self):
        self.cmds.select(clear=True)
        self.slots.b002(None)
        self.assertTrue(self.sb.message_box.called)


if __name__ == "__main__":
    unittest.main()
