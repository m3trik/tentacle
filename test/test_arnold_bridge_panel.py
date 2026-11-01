#!/usr/bin/python
# coding=utf-8
"""The Arnold Preview Shader panel's Slots class (``slots/tools/arnold_bridge.py``).

It reaches its host only through ``self.tk``, so a fake toolkit stands in for
``mtk`` and records what the panel asks of its ``ArnoldBridge``: plain unittest,
no DCC, no widgets. A Maya tool (``tentacle.slots.tools.HOSTS``): in Maya the
same class drives the real ``mtk`` on real materials (needs MtoA). The bridge's
own behavior is mayatk's ``test_arnold_bridge.py``.
"""

import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools import HOSTS
from tentacle.slots.tools.arnold_bridge import ArnoldBridgeSlots


def _panel(values=None, tk=None):
    """An ``ArnoldBridgeSlots`` over a mock ui (*values*: the Scope index and the
    Force check) and a mock toolkit, or *tk* (handed over before the panel is
    built, as ``Slots.tk`` is)."""
    values = dict({"scope": 0, "force": False}, **(values or {}))
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    ui = sb.loaded_ui.arnold_bridge
    ui.cmb000.currentIndex.return_value = values["scope"]
    ui.chk000.isChecked.return_value = values["force"]
    return ArnoldBridgeSlots(sb), sb


def _footer(sb):
    """The footer's last text."""
    return sb.loaded_ui.arnold_bridge.footer.setText.call_args[0][0]


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)


class TestArnoldBridgePanel(_PanelCase):
    def test_a_maya_tool(self):
        """Blender has no Arnold: the launcher never registers it there."""
        self.assertEqual(HOSTS["arnold_bridge"], ("maya",))

    def test_builds_the_host_bridge(self):
        slots, sb = _panel()
        sb.tk.ArnoldBridge.assert_called_once_with()
        self.assertIs(slots._bridge, sb.tk.ArnoldBridge.return_value)

    def test_the_scope_combo_keeps_its_saved_order(self):
        """The combo saves an index: 0 is the selection, 1 every scene material."""
        slots, _sb = _panel()
        combo = mock.MagicMock()
        slots.cmb000_init(combo)
        combo.addItems.assert_called_once_with(("Selected Objects", "All Scene Materials"))
        combo.setCurrentIndex.assert_called_once_with(0)

    def test_the_header_offers_select_bridged(self):
        slots, _sb = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("menu", "collapse", "hide")
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        self.assertEqual(names, ["select_bridged"])
        header.set_help_text.assert_called_once()

    def test_add_bridges_the_selection_with_force(self):
        slots, sb = _panel({"scope": 0, "force": True})
        sb.tk.CoreUtils.selected_objects.return_value = ["cube"]
        slots._bridge.add.return_value = ["mat_ai"]
        slots.b000()
        slots._bridge.add.assert_called_once_with(objects=["cube"], force=True)
        self.assertEqual(_footer(sb), "Added 1 Arnold network (selection).")

    def test_an_empty_selection_names_the_fix(self):
        slots, sb = _panel({"scope": 0})
        sb.tk.CoreUtils.selected_objects.return_value = []
        slots.b000()
        slots._bridge.add.assert_not_called()
        self.assertIn("Select object(s)", _footer(sb))

    def test_remove_acts_on_every_scene_material(self):
        slots, sb = _panel({"scope": 1})
        slots._bridge.base_materials.return_value = ["matA", "matB"]
        slots._bridge.remove.return_value = ["matA", "matB"]
        slots.b001()
        slots._bridge.remove.assert_called_once_with(materials=["matA", "matB"])
        sb.tk.CoreUtils.selected_objects.assert_not_called()
        self.assertEqual(_footer(sb), "Removed 2 Arnold networks (2 scene material(s)).")

    def test_a_scene_without_materials_says_so(self):
        slots, sb = _panel({"scope": 1})
        slots._bridge.base_materials.return_value = []
        slots.b001()
        slots._bridge.remove.assert_not_called()
        self.assertEqual(_footer(sb), "No scene materials found.")

    def test_select_bridged_reports_what_it_selected(self):
        slots, sb = _panel()
        slots._bridge.select_bridged.return_value = ["matA"]
        slots.select_bridged()
        self.assertEqual(_footer(sb), "Selected 1 material(s) with an Arnold network.")
        slots._bridge.select_bridged.return_value = []
        slots.select_bridged()
        self.assertEqual(_footer(sb), "No materials have an Arnold network.")


def _mtoa_available(cmds) -> bool:
    try:
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa", quiet=True)
        return bool(cmds.pluginInfo("mtoa", query=True, loaded=True))
    except Exception:  # noqa: BLE001 -- no Arnold here
        return False


@unittest.skipUnless(MAYA_AVAILABLE, "needs a Maya runtime")
class TestArnoldBridgePanelInMaya(_PanelCase):
    """The panel over the real ``mtk`` on real materials (the panel cases mayatk's
    ``ArnoldBridgeSlotsTest`` held before the panel moved here)."""

    @classmethod
    def setUpClass(cls):
        cls.cmds = maya_module("maya.cmds")
        cls.mtk = maya_module("mayatk")
        if not _mtoa_available(cls.cmds):
            raise unittest.SkipTest("mtoa (Arnold) plugin not available")

    def setUp(self):
        super().setUp()
        self.cmds.file(new=True, force=True)

    def _slots(self, scope=0, force=False):
        return _panel({"scope": scope, "force": force}, tk=self.mtk)

    def _textured_cube(self, name):
        """A standardSurface (with one texture) assigned to a new cube."""
        cmds = self.cmds
        shader = cmds.shadingNode("standardSurface", asShader=True, name=name)
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{name}SG")
        cmds.connectAttr(f"{shader}.outColor", f"{sg}.surfaceShader", force=True)
        fn = cmds.shadingNode("file", asTexture=True, name=f"{name}_file")
        cmds.setAttr(f"{fn}.fileTextureName", f"{name}_BaseColor.png", type="string")
        cmds.connectAttr(f"{fn}.outColor", f"{shader}.baseColor", force=True)
        cube = cmds.polyCube(name=f"{name}_cube")[0]
        cmds.sets(cube, edit=True, forceElement=sg)
        return shader, cube

    def test_add_then_remove_on_the_selection(self):
        shader, cube = self._textured_cube("matSel")
        slots, sb = self._slots()
        self.cmds.select(cube, replace=True)
        slots.b000()
        self.assertTrue(slots._bridge.has_bridge(shader))
        self.assertIn("Added 1", _footer(sb))
        slots.b001()
        self.assertFalse(slots._bridge.has_bridge(shader))
        self.assertIn("Removed 1", _footer(sb))

    def test_an_empty_selection_adds_nothing(self):
        shader, _cube = self._textured_cube("matSel")
        slots, sb = self._slots()
        self.cmds.select(clear=True)
        slots.b000()
        self.assertFalse(slots._bridge.has_bridge(shader))
        self.assertIn("Select object", _footer(sb))

    def test_all_scene_materials_ignores_the_selection(self):
        shader_a, _ = self._textured_cube("matA")
        shader_b, _ = self._textured_cube("matB")
        slots, _sb = self._slots(scope=1)
        slots.b000()
        self.assertTrue(slots._bridge.has_bridge(shader_a))
        self.assertTrue(slots._bridge.has_bridge(shader_b))

    def test_force_rebuilds_the_network(self):
        shader, cube = self._textured_cube("matSel")
        self.cmds.select(cube, replace=True)
        self._slots()[0].b000()
        bridge = self.mtk.ArnoldBridge()
        first = self.cmds.ls(bridge.get_bridge(shader), uuid=True)[0]
        self._slots(force=True)[0].b000()
        second = self.cmds.ls(bridge.get_bridge(shader), uuid=True)[0]
        self.assertNotEqual(first, second)

    def test_select_bridged_selects_the_material_not_its_network(self):
        shader, cube = self._textured_cube("matSel")
        self.cmds.select(cube, replace=True)
        slots, _sb = self._slots()
        slots.b000()
        network = slots._bridge.get_bridge(shader)
        self.cmds.select(clear=True)
        slots.select_bridged()
        selection = self.cmds.ls(selection=True) or []
        self.assertIn(shader, selection)
        self.assertNotIn(network, selection)


if __name__ == "__main__":
    unittest.main()
