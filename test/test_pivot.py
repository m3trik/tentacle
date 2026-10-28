#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.pivot, the one Pivot Slots class.

It reaches its host only through ``self.tk``: a fake toolkit records what each
slot asks of ``XformUtils`` (plain pytest), and in Maya the same class drives the
real ``mtk``. What's worth pinning at this layer:

- each option box's values reach the operation (Center Pivot's radio as its
  mode, Transfer Pivot's channels and mirror, World-Aligned's manip/object);
- every operation acts on the selection (``None``) and says so when it was empty;
- the options only Maya's pivots serve are tagged ``requires="maya"``.

The operations themselves are tested in mayatk and blendertk.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.pivot import PivotSlots


def _widget(**values):
    """A widget whose option-box menu holds fakes reading *values*."""
    widget = mock.MagicMock()
    for name, value in values.items():
        child = getattr(widget.option_box.menu, name)
        child.isChecked.return_value = value
        child.currentData.return_value = value
    return widget


class _RecordingMenu:
    """Records the widgets a ``*_init`` builds on the option box."""

    def __init__(self):
        self.added = {}

    def setTitle(self, title):
        self.title = title

    def add(self, widget_type, **kwargs):
        widget = mock.MagicMock()
        self.added[kwargs.get("setObjectName")] = (kwargs, widget)
        return widget


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = PivotSlots(self.sb)
        self.xform = self.sb.tk.XformUtils

    def _message(self):
        (message,), _ = self.sb.message_box.call_args
        return message

    def _init(self, name):
        widget = mock.MagicMock()
        widget.option_box.menu = _RecordingMenu()
        getattr(self.slots, f"{name}_init")(widget)
        return widget.option_box.menu.added


class TestResetPivot(_SlotsCase):
    def test_the_options_reach_the_operation(self):
        self.xform.reset_pivot.return_value = ["a", "b"]
        self.slots.tb000(_widget(chk000=True, chk001=False))
        self.xform.reset_pivot.assert_called_once_with(
            None, position=True, orientation=False
        )
        self.assertIn("<hl>2</hl>", self._message())

    def test_nothing_selected_says_so(self):
        self.xform.reset_pivot.return_value = []
        self.slots.tb000(_widget(chk000=True, chk001=True))
        self.assertEqual(self._message(), PivotSlots.NOTHING_SELECTED)


class TestCenterPivot(_SlotsCase):
    def test_the_radio_is_the_mode(self):
        for flags, mode in (
            (dict(chk002=True, chk003=False, chk004=False), "component"),
            (dict(chk002=False, chk003=True, chk004=False), "object"),
            (dict(chk002=False, chk003=False, chk004=True), "world"),
        ):
            with self.subTest(mode=mode):
                self.slots.tb001(_widget(**flags))
                self.xform.center_pivot.assert_called_with(None, mode=mode)

    def test_nothing_selected_says_so(self):
        self.xform.center_pivot.return_value = []
        self.slots.tb001(_widget(chk002=False, chk003=True, chk004=False))
        self.assertIn("requires a selection", self._message())

    def test_the_shortcuts_drive_center_pivot(self):
        for button, radio in (("b000", "chk003"), ("b001", "chk002"), ("b002", "chk004")):
            with self.subTest(button=button):
                tb001 = mock.MagicMock()
                self.slots.ui = mock.MagicMock(tb001=tb001)
                method = getattr(self.slots, button)
                method(None) if button == "b002" else method()
                getattr(tb001.option_box.menu, radio).setChecked.assert_called_once_with(True)
                tb001.call_slot.assert_called_once_with()


class TestTransferPivot(_SlotsCase):
    def _run(self, **overrides):
        values = dict(
            chk005=True, chk006=False, chk007=True, chk008=True, chk009=True, cmb000="x"
        )
        values.update(overrides)
        self.slots.tb002(_widget(**values))
        return self.xform.transfer_pivot.call_args

    def test_every_option_reaches_the_operation(self):
        call = self._run()
        self.assertEqual(call.args, (None,))
        self.assertEqual(
            call.kwargs,
            dict(
                translate=True,
                rotate=False,
                scale=True,
                bake=True,
                world_space=True,
                mirror="x",
                select_targets_after_transfer=True,
            ),
        )

    def test_too_few_objects_says_which_is_the_source(self):
        self.xform.transfer_pivot.return_value = []
        self._run()
        self.assertIn("source", self._message())

    def test_the_hosts_reason_is_shown(self):
        self.xform.transfer_pivot.side_effect = ValueError("make the source active")
        self._run()
        self.assertEqual(self._message(), "make the source active")

    def test_option_defaults(self):
        """Bake defaults ON (the button does something that sticks); Rotate OFF
        (most transfers want the pivot point only)."""
        added = self._init("tb002")
        self.assertTrue(added["chk008"][0]["setChecked"])
        self.assertFalse(added["chk006"][0]["setChecked"])
        self.assertTrue(added["chk005"][0]["setChecked"])
        self.assertTrue(added["chk007"][0]["setChecked"])
        self.assertTrue(added["chk009"][0]["setChecked"])


class TestMayaOnlyOptions(_SlotsCase):
    """Blender's one origin is always baked, world-space and orientation-free: the
    options it cannot serve are hidden there (``requires``), never stubs."""

    def _tagged(self, added):
        return {
            name
            for name, (_, widget) in added.items()
            if mock.call("requires", "maya") in widget.setProperty.call_args_list
        }

    def test_transfer_pivot(self):
        tagged = self._tagged(self._init("tb002"))
        self.assertEqual(tagged, {"chk005", "chk006", "chk007", "chk008", "chk009"})

    def test_reset_pivot(self):
        self.assertEqual(self._tagged(self._init("tb000")), {"chk001"})

    def test_the_rest_serve_both_hosts(self):
        for name in ("tb001", "tb003"):
            with self.subTest(name=name):
                self.assertEqual(self._tagged(self._init(name)), set())


class TestWorldAlignedPivot(_SlotsCase):
    def test_the_option_picks_the_pivot(self):
        self.xform.world_align_pivot.return_value = True
        self.slots.tb003(_widget(chk010=True))
        self.xform.world_align_pivot.assert_called_with(None, pivot_type="manip", mode="set")
        self.assertIn("manipulator", self._message())
        self.slots.tb003(_widget(chk010=False))
        self.xform.world_align_pivot.assert_called_with(None, pivot_type="object", mode="set")
        self.assertIn("object", self._message())

    def test_a_failure_says_why(self):
        self.xform.world_align_pivot.return_value = False
        self.slots.tb003(_widget(chk010=False))
        self.assertIn("requires a selection", self._message())
        self.xform.world_align_pivot.side_effect = ValueError("linked data")
        self.slots.tb003(_widget(chk010=False))
        self.assertEqual(self._message(), "linked data")


class TestBakePivot(_SlotsCase):
    def test_the_selection_bakes_position_and_orientation(self):
        self.slots.b004()
        self.xform.bake_pivot.assert_called_once_with(
            None, position=True, orientation=True
        )
        self.sb.message_box.assert_not_called()

    def test_nothing_selected_or_a_refusal_says_so(self):
        self.xform.bake_pivot.return_value = []
        self.slots.b004()
        self.assertIn("requires a selection", self._message())
        self.xform.bake_pivot.side_effect = RuntimeError("edit mode")
        self.slots.b004()
        self.assertEqual(self._message(), "edit mode")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestPivotInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self.cube = self.cmds.polyCube(name="pv_cube")[0]
        self.cmds.move(5, 0, 0, self.cube)

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def _rp(self):
        return [round(v, 4) for v in self.cmds.xform(self.cube, q=True, ws=True, rp=True)]

    def test_center_pivot_object_and_world(self):
        self.cmds.xform(self.cube, worldSpace=True, pivots=(9, 9, 9))
        self.cmds.select(self.cube)
        self.slots.tb001(_widget(chk002=False, chk003=True, chk004=False))
        self.assertEqual(self._rp(), [5.0, 0.0, 0.0])
        self.slots.tb001(_widget(chk002=False, chk003=False, chk004=True))
        self.assertEqual(self._rp(), [0.0, 0.0, 0.0])

    def test_nothing_selected_changes_nothing_and_says_so(self):
        self.cmds.select(clear=True)
        self.slots.tb001(_widget(chk002=False, chk003=True, chk004=False))
        self.slots.b004()
        self.assertEqual(self.sb.message_box.call_count, 2)

    def test_bake_pivot_makes_the_pivot_the_objects_own(self):
        self.cmds.xform(self.cube, worldSpace=True, pivots=(6, 1, 0))
        self.cmds.select(self.cube)
        self.slots.b004()
        self.assertEqual(
            [round(v, 4) for v in self.cmds.getAttr(f"{self.cube}.translate")[0]],
            [6.0, 1.0, 0.0],
        )


if __name__ == "__main__":
    unittest.main()
