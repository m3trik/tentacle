#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.symmetry, the one Symmetry Slots class.

It reaches its host only through ``self.tk`` (``EditUtils.get_symmetry`` /
``set_symmetry``): a fake toolkit stands in for it here and records the calls
(plain pytest), and in Maya the same class drives the real ``mtk``. What's worth
pinning at this layer:

- chk000/1/2 send their axis and state; the report is worded from the state the
  host answers (``Symmetry: <space> <hl>AXES</hl>``), silent when off; a refusal
  is shown and the boxes re-seeded from the host.
- chk004 (object space) acts only when selected: a deselect means Topo took over.
- chk005 (topology) reverts the radio to object space WITHOUT running either slot
  when the host refuses, and disables the axes only where the host's symmetry
  uses none (Maya's topological symmetry).
- the inits seed from the host with signals blocked and opt out of restore.
The operations themselves are tested in mayatk and blendertk.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.symmetry import SymmetrySlots


def _state(enabled=True, axes=("x",), space="object", by_axis=True):
    return {"enabled": enabled, "axes": list(axes), "space": space, "by_axis": by_axis}


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = SymmetrySlots(self.sb)
        self.edit = self.sb.tk.EditUtils

    def _last_message(self):
        (message,), _ = self.sb.message_box.call_args
        return message


class TestAxes(_SlotsCase):
    def test_each_box_sends_its_axis(self):
        self.edit.set_symmetry.return_value = _state()
        for name, axis in (("chk000", "x"), ("chk001", "y"), ("chk002", "z")):
            getattr(self.slots, name)(2, mock.MagicMock())  # Qt.Checked
            self.edit.set_symmetry.assert_called_with(axis=axis, state=True)

    def test_unchecked_sends_off(self):
        self.edit.set_symmetry.return_value = _state(enabled=False, axes=())
        self.slots.chk000(0, mock.MagicMock())
        self.edit.set_symmetry.assert_called_with(axis="x", state=False)

    def test_the_report_is_worded_from_the_hosts_state(self):
        self.edit.set_symmetry.return_value = _state(axes=("x", "y"), space="world")
        self.slots.chk000(True, mock.MagicMock())
        self.assertEqual(self._last_message(), "Symmetry: World <hl>X+Y</hl>")

    def test_off_is_silent(self):
        self.edit.set_symmetry.return_value = _state(enabled=False, axes=())
        self.slots.chk000(False, mock.MagicMock())
        self.sb.message_box.assert_not_called()

    def test_a_radio_switch_reports_once(self):
        """X off and Y on, in either order: one toast, for the axis turned on."""
        self.edit.set_symmetry.return_value = _state(axes=("y",))
        self.slots.chk001(True, mock.MagicMock())
        self.slots.chk000(False, mock.MagicMock())  # Maya: not the current axis, a no-op
        self.sb.message_box.assert_called_once_with("Symmetry: Object <hl>Y</hl>")

    def test_a_refusal_is_shown_and_the_boxes_reseeded(self):
        self.edit.set_symmetry.side_effect = ValueError("Select a mesh")
        self.edit.get_symmetry.return_value = _state(axes=("y",))
        widget = mock.MagicMock()
        self.slots.chk000(True, widget)
        self.sb.message_box.assert_called_once_with("Select a mesh")
        widget.ui.chk000.setChecked.assert_called_with(False)
        widget.ui.chk001.setChecked.assert_called_with(True)
        self.assertFalse(widget.ui.chk000.restore_state)


class TestSpace(_SlotsCase):
    def test_chk004_selected_sets_object_space_and_reports(self):
        self.edit.set_symmetry.return_value = _state(space="object")
        self.slots.chk004(True, None)
        self.edit.set_symmetry.assert_called_once_with(space="object")
        self.assertEqual(self._last_message(), "Symmetry: Object <hl>X</hl>")

    def test_chk004_deselected_is_a_no_op(self):
        """Deselection happens when Topo takes over; it must not clobber it."""
        self.slots.chk004(False, None)
        self.edit.set_symmetry.assert_not_called()

    def test_topology_without_an_axis_disables_the_axes(self):
        """Maya: topological symmetry uses no axis."""
        self.edit.set_symmetry.return_value = _state(axes=(), space="topo", by_axis=False)
        self.slots.chk005(True, None)
        self.edit.set_symmetry.assert_called_once_with(space="topo")
        self.sb.toggle_multi.assert_called_once_with(self.slots.ui, setDisabled="chk000-2")
        self.assertEqual(self._last_message(), "Symmetry: <hl>Topological</hl>")

    def test_topology_by_axis_keeps_the_axes(self):
        """Blender: topology matching still mirrors across the axes."""
        self.edit.set_symmetry.return_value = _state(space="topo")
        self.slots.chk005(True, None)
        self.sb.toggle_multi.assert_not_called()
        self.assertEqual(self._last_message(), "Symmetry: Topological <hl>X</hl>")

    def test_a_refused_topology_reverts_to_object_space_silently(self):
        self.edit.set_symmetry.side_effect = ValueError("Select an edge first")
        chk004, chk005 = self.slots.ui.chk004, self.slots.ui.chk005
        chk004.blockSignals.return_value = False
        chk005.blockSignals.return_value = False
        self.slots.chk005(True, None)
        chk004.setChecked.assert_called_once_with(True)
        chk005.setChecked.assert_called_once_with(False)
        # signals blocked around each, so neither slot re-runs the host
        self.assertEqual(chk004.blockSignals.call_args_list[0], mock.call(True))
        self.assertEqual(chk005.blockSignals.call_args_list[0], mock.call(True))
        self.sb.message_box.assert_called_once_with("Select an edge first")

    def test_leaving_topology_reenables_the_axes(self):
        self.slots.chk005(False, None)
        self.sb.toggle_multi.assert_called_once_with(self.slots.ui, setEnabled="chk000-2")
        self.edit.set_symmetry.assert_not_called()


class TestInits(_SlotsCase):
    def _ui(self):
        ui = mock.MagicMock()
        for name in ("chk000", "chk001", "chk002", "chk004", "chk005"):
            getattr(ui, name).blockSignals.return_value = False
        return ui

    def test_the_first_mirrored_axis_lights_alone(self):
        self.edit.get_symmetry.return_value = _state(axes=("y", "z"))
        ui = self._ui()
        self.slots.chk000_init(mock.MagicMock(ui=ui))
        ui.chk000.setChecked.assert_called_once_with(False)
        ui.chk001.setChecked.assert_called_once_with(True)
        ui.chk002.setChecked.assert_called_once_with(False)
        for name in ("chk000", "chk001", "chk002"):
            self.assertFalse(getattr(ui, name).restore_state, name)
        self.sb.message_box.assert_not_called()

    def test_each_sibling_opts_itself_out(self):
        for name in ("chk001", "chk002", "chk004"):
            widget = mock.MagicMock()
            getattr(self.slots, f"{name}_init")(widget)
            self.assertFalse(widget.restore_state, name)

    def test_the_space_radio_seeds_from_the_host(self):
        for space, expect004, expect005 in (
            ("object", True, False),
            ("topo", False, True),
            (None, False, False),  # Blender, no active mesh
        ):
            with self.subTest(space=space):
                self.edit.get_symmetry.return_value = _state(space=space)
                ui = self._ui()
                self.slots.chk005_init(mock.MagicMock(ui=ui))
                ui.chk004.setChecked.assert_called_once_with(expect004)
                ui.chk005.setChecked.assert_called_once_with(expect005)

    def test_a_maya_topology_session_opens_with_the_axes_disabled(self):
        self.edit.get_symmetry.return_value = _state(axes=(), space="topo", by_axis=False)
        ui = self._ui()
        self.slots.chk005_init(mock.MagicMock(ui=ui))
        self.sb.toggle_multi.assert_called_once_with(ui, setDisabled="chk000-2")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestSymmetryInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self._off()
        self.addCleanup(self._off)

    def _off(self):
        self.cmds.symmetricModelling(edit=True, symmetry=False, about="world", axis="x")

    def test_an_axis_turns_maya_symmetry_on_and_says_so(self):
        self.slots.chk001(True, mock.MagicMock())
        self.assertTrue(self.cmds.symmetricModelling(query=True, symmetry=True))
        self.assertEqual(self.cmds.symmetricModelling(query=True, axis=True), "y")
        self.assertIn("<hl>Y</hl>", self._last_message())

    def test_object_space(self):
        self.slots.chk000(True, mock.MagicMock())
        self.slots.chk004(True, None)
        self.assertEqual(self.cmds.symmetricModelling(query=True, about=True), "object")

    def test_topology_without_an_edge_reverts_and_warns(self):
        self.cmds.select(clear=True)
        self.slots.chk005(True, None)
        self.slots.ui.chk004.setChecked.assert_called_with(True)
        self.assertIn("edge", self._last_message())
        self.assertNotEqual(self.cmds.symmetricModelling(query=True, about=True), "topo")


if __name__ == "__main__":
    unittest.main()
