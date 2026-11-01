#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.lighting, the one Lighting Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here and records the calls (plain pytest), and in Maya the same class drives
the real ``mtk``. What's worth pinning at this layer:

- the three launchers' panel names (drift would silently break the buttons);
- Lights From Geometry's option box reaching ``LightUtils.lights_from_geometry``
  in mayatk's call: the selection, the host's intensity, Kelvin 0 as "off",
  the offset converted from centimetres to the scene's units, the cluster
  mode (Maya's: the combo is hidden elsewhere).
The operation itself is tested in mayatk and blendertk.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.lighting import LightingSlots


def _widget(kelvin=5000, intensity=100.0, offset=1.0, cluster="shell"):
    """A widget whose option-box menu reads the given values."""
    widget = mock.MagicMock()
    menu = widget.option_box.menu
    menu.s000.value.return_value = kelvin
    menu.d000.value.return_value = intensity
    menu.d001.value.return_value = offset
    menu.cmb000.currentData.return_value = cluster
    return widget


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = LightingSlots(self.sb)
        self.tk = self.sb.tk
        # cm -> the scene's units: a stand-in for a metre-unit scene.
        self.tk.Units.convert.side_effect = lambda value, source, target: value / 100.0


class TestLaunchers(_SlotsCase):
    def test_each_launcher_opens_its_panel(self):
        for slot, panel in (
            (self.slots.b000, "hdr_manager"),
            (self.slots.b001, "lightmap_baker"),
            (self.slots.b002, "light_rig"),
        ):
            with self.subTest(panel=panel):
                slot()
                self.sb.handlers.marking_menu.show.assert_called_with(panel)


class TestLightsFromGeometry(_SlotsCase):
    def test_the_option_box_reaches_the_host_in_mayatks_call(self):
        self.tk.LightUtils.lights_from_geometry.return_value = ["l1", "l2"]
        self.slots.tb000(
            _widget(kelvin=4000, intensity=250.0, offset=2.0, cluster="face")
        )
        self.tk.Units.convert.assert_called_once_with(2.0, "cm", "working")
        self.tk.LightUtils.lights_from_geometry.assert_called_once_with(
            None, intensity=250.0, kelvin=4000, offset=0.02, cluster="face"
        )
        self.assertIn("Created 2 light(s)", self.sb.message_box.call_args.args[0])

    def test_kelvin_zero_is_off(self):
        self.tk.LightUtils.lights_from_geometry.return_value = ["l1"]
        self.slots.tb000(_widget(kelvin=0))
        kwargs = self.tk.LightUtils.lights_from_geometry.call_args.kwargs
        self.assertIsNone(kwargs["kelvin"])

    def test_nothing_made_asks_for_the_fixtures(self):
        self.tk.LightUtils.lights_from_geometry.return_value = []
        self.slots.tb000(_widget())
        self.assertIn(
            "Select the fixture geometry", self.sb.message_box.call_args.args[0]
        )

    def test_the_cluster_combo_is_mayas(self):
        menu = mock.MagicMock()
        made = {}

        def add(_kind, **kwargs):
            made[kwargs["setObjectName"]] = mock.MagicMock()
            return made[kwargs["setObjectName"]]

        menu.add.side_effect = add
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        self.slots.tb000_init(widget)
        self.assertEqual(sorted(made), ["cmb000", "d000", "d001", "s000"])
        made["cmb000"].setProperty.assert_called_once_with("requires", "maya")
        self.sb.apply_visibility_policy.assert_called_once_with(made["cmb000"])
        data = [c.args[1] for c in made["cmb000"].addItem.call_args_list]
        self.assertEqual(data, ["shell", "object", "face"])  # saved index order
        for name in ("s000", "d000", "d001"):
            made[name].setProperty.assert_not_called()

    def test_the_offset_field_is_in_centimetres(self):
        menu = mock.MagicMock()
        widget = mock.MagicMock()
        widget.option_box.menu = menu
        self.slots.tb000_init(widget)
        offset = next(
            c.kwargs
            for c in menu.add.call_args_list
            if c.kwargs.get("setObjectName") == "d001"
        )
        self.assertEqual(offset["setSuffix"], " cm")
        self.assertEqual(offset["setValue"], 1.0)


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestLightingInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")

    def tearDown(self):
        self.cmds.file(new=True, force=True)

    def test_a_selected_fixture_gets_a_light(self):
        self.cmds.polyPlane(name="floor", width=800, height=800)
        plate = self.cmds.polyCube(name="troffer", width=372, height=10, depth=72)[0]
        self.cmds.xform(plate, translation=(0, 390, 0), worldSpace=True)
        self.cmds.select(plate)
        self.slots.tb000(_widget(offset=1.0))
        self.assertIn("Created 1 light(s)", self.sb.message_box.call_args.args[0])

    def test_nothing_selected_creates_nothing(self):
        self.cmds.select(clear=True)
        self.slots.tb000(_widget())
        self.assertIn(
            "Select the fixture geometry", self.sb.message_box.call_args.args[0]
        )
        self.assertEqual(self.cmds.ls(type="light") or [], [])


if __name__ == "__main__":
    unittest.main()
