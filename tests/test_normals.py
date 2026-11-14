#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.normals, the one Normals Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- tb001's -1 → None translation for the upper/lower hardness sentinels, and
  its warning when the host reports locked normals.
- b002's warning with too little selected, and every other operation's
  "Nothing selected" when the host ran it on an empty selection.
- b004's message for the state the toggle leaves.
- tb010's combo index → ``reverse_normals`` mode.
The operations themselves are tested in mayatk and blendertk.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.normals import NormalsSlots


def _widget(**values):
    """A widget whose option-box menu holds fakes reading *values*."""
    widget = mock.MagicMock()
    for name, value in values.items():
        child = getattr(widget.option_box.menu, name)
        child.value.return_value = value
        child.isChecked.return_value = value
        child.currentIndex.return_value = value
    return widget


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = NormalsSlots(self.sb)
        self.components = self.sb.tk.Components


class TestTb001HardnessTranslation(_SlotsCase):
    """tb001 reads three spinbox values; -1 must become None before dispatch."""

    def _run(self, threshold=90, upper=0, lower=180, unlock=False):
        self.components.set_edge_hardness.return_value = []
        self.slots.tb001(
            _widget(s002=threshold, s003=upper, s004=lower, chk_unlock_normals=unlock)
        )
        return self.components.set_edge_hardness.call_args

    def test_values_pass_through_on_the_selection(self):
        call = self._run(threshold=45)
        self.assertEqual(call.args, (None, 45, 0, 180))

    def test_unlock_checkbox_propagates(self):
        self.assertTrue(self._run(unlock=True).kwargs["unlock_normals"])
        self.assertFalse(self._run(unlock=False).kwargs["unlock_normals"])

    def test_minus_one_becomes_none(self):
        self.assertEqual(self._run(upper=-1).args[2:], (None, 180))
        self.assertEqual(self._run(lower=-1).args[2:], (0, None))
        self.assertEqual(self._run(upper=-1, lower=-1).args[2:], (None, None))


class TestTb001LockedNormalsGuard(_SlotsCase):
    """The host reports meshes it skipped for locked normals: tb001 names them."""

    def test_locked_objects_are_named_in_a_warning(self):
        self.components.set_edge_hardness.return_value = ["|grp|locked_cube"]
        self.slots.tb001(_widget(s002=90, s003=0, s004=180, chk_unlock_normals=False))
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("locked_cube", message)
        self.assertNotIn("|grp", message)

    def test_a_clean_run_says_nothing(self):
        self.components.set_edge_hardness.return_value = []
        self.slots.tb001(_widget(s002=90, s003=0, s004=180, chk_unlock_normals=True))
        self.sb.message_box.assert_not_called()


class TestOperations(_SlotsCase):
    def test_soften_and_harden_act_on_the_selection(self):
        self.slots.b000()
        self.components.set_edge_softness.assert_called_with(None, soft=True)
        self.slots.b001()
        self.components.set_edge_softness.assert_called_with(None, soft=False)

    def test_average_and_set_to_face(self):
        self.slots.tb004(_widget(chk003=True))
        self.components.average_normals.assert_called_once_with(None, by_uv_shell=True)
        self.slots.b006()
        self.components.set_to_face_normals.assert_called_once_with(None)

    def test_tb010_maps_the_combo_index_to_the_mode(self):
        for index in range(5):
            self.slots.tb010(_widget(cmb000=index))
            self.components.reverse_normals.assert_called_with(None, mode=index)

    def test_an_empty_selection_says_so_and_a_run_says_nothing(self):
        self.components.set_edge_softness.return_value = None
        self.slots.b000()
        self.sb.message_box.assert_not_called()
        self.components.set_edge_softness.return_value = []  # CoreUtils.selected
        self.slots.b000()
        self.sb.message_box.assert_called_once_with(NormalsSlots.NOTHING_SELECTED)


class TestB002SelectionGate(_SlotsCase):
    """b002 (Transfer Normals) needs a source and a target."""

    def test_nothing_selected_warns(self):
        self.components.transfer_normals.return_value = []  # CoreUtils.selected
        self.slots.b002()
        self.assertTrue(self.sb.message_box.called, "User must be warned")

    def test_too_few_meshes_warns_with_the_hosts_reason(self):
        self.components.transfer_normals.side_effect = ValueError("one mesh")
        self.slots.b002()
        self.sb.message_box.assert_called_once_with("one mesh")

    def test_a_transfer_says_nothing(self):
        self.components.transfer_normals.return_value = None
        self.slots.b002()
        self.sb.message_box.assert_not_called()


class TestB004LockToggle(_SlotsCase):
    def test_each_state_is_reported(self):
        for state, word in ((True, "Locked"), (False, "Unlocked"), ([], "requires")):
            with self.subTest(state=state):
                self.components.toggle_normal_lock.return_value = state
                self.slots.b004()
                (message,), _ = self.sb.message_box.call_args
                self.assertIn(word, message)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestNormalsInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.cube = self.cmds.polyCube(name="nrm_cube")[0]

    def _hard_edges(self):
        info = self.cmds.polyInfo(f"{self.cube}.e[*]", edgeToVertex=True) or []
        return sum("Hard" in line for line in info)

    def test_harden_then_soften_the_selection(self):
        self.cmds.select(self.cube)
        self.slots.b001()
        self.assertEqual(self._hard_edges(), 12)
        self.slots.b000()
        self.assertEqual(self._hard_edges(), 0)
        self.assertTrue(self.cmds.polyOptions(self.cube, q=True, se=True)[0])

    def test_soften_handles_a_leaf_name_collision(self):
        """Two objects sharing a leaf name must not crash b000 (the
        ``More than one object matches name`` regression)."""
        self.cmds.group(self.cmds.polyCube(name="pCube1")[0], name="grp1")
        self.cmds.group(self.cmds.polyCube(name="pCube1")[0], name="grp2")
        self.cmds.select(self.cmds.ls("grp1|pCube1.e[0:3]", flatten=True), replace=True)
        self.slots.b000()
        self.assertTrue(self.cmds.polyOptions("grp1|pCube1", q=True, se=True)[0])

    def test_transfer_with_one_mesh_warns(self):
        self.cmds.select(self.cube)
        self.slots.b002()
        self.assertTrue(self.sb.message_box.called)

    def test_nothing_selected_changes_nothing_and_says_so(self):
        before = self._hard_edges()  # a new polyCube's edges are all hard
        self.cmds.select(clear=True)
        self.slots.b000()
        self.slots.tb010(_widget(cmb000=0))
        self.assertEqual(self._hard_edges(), before)
        self.assertEqual(self.sb.message_box.call_count, 2)


if __name__ == "__main__":
    unittest.main()
