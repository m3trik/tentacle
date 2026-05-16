#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.display.

Most DisplaySlots methods are thin wrappers over cmds.hide/show or MEL
macros. The state-mutation chain worth pinning is the xRay trio
(b005/b006/b007) — they read+write the displaySurface xRay flag across
sets of meshes, which is the kind of logic where set arithmetic bugs
slip through.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import display as display_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    display_module = None
    _MAYA_AVAILABLE = False


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestHideShow(unittest.TestCase):
    """b002 hides selection; b003 reveals it. No-op when nothing is selected."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.cube = cmds.polyCube(name="ds_cube")[0]
        self.instance = display_module.DisplaySlots.__new__(display_module.DisplaySlots)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_b002_hides_selection(self):
        cmds.select(self.cube)
        self.assertEqual(cmds.getAttr(f"{self.cube}.visibility"), True)
        self.instance.b002()
        self.assertEqual(cmds.getAttr(f"{self.cube}.visibility"), False)

    def test_b002_no_selection_is_noop(self):
        cmds.select(clear=True)
        # Should not raise — just no work.
        self.instance.b002()
        # Cube was never selected, visibility unchanged.
        self.assertEqual(cmds.getAttr(f"{self.cube}.visibility"), True)

    def test_b003_reveals_hidden_selection(self):
        cmds.hide(self.cube)
        cmds.select(self.cube)
        self.assertEqual(cmds.getAttr(f"{self.cube}.visibility"), False)
        self.instance.b003()
        self.assertEqual(cmds.getAttr(f"{self.cube}.visibility"), True)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestXrayChain(unittest.TestCase):
    """b005/b006/b007 manage the xRay flag across selected vs all meshes.

    This is the highest-risk chain in display.py — set arithmetic bugs
    (operating on the wrong subset, mishandling instances/duplicates)
    would silently affect the wrong objects.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.cube_a = cmds.polyCube(name="xr_a")[0]
        self.cube_b = cmds.polyCube(name="xr_b")[0]
        self.cube_c = cmds.polyCube(name="xr_c")[0]
        self.instance = display_module.DisplaySlots.__new__(display_module.DisplaySlots)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _xray(self, node):
        """Query xRay state on a transform."""
        result = cmds.displaySurface(node, xRay=True, query=True)
        return bool(result[0]) if result else False

    def test_b005_toggles_xray_on_selected_only(self):
        cmds.select([self.cube_a, self.cube_b])

        self.instance.b005()

        self.assertTrue(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))
        # cube_c was NOT selected — must remain non-xray.
        self.assertFalse(self._xray(self.cube_c))

    def test_b005_second_call_toggles_back(self):
        cmds.select([self.cube_a])
        self.instance.b005()
        self.assertTrue(self._xray(self.cube_a))

        self.instance.b005()
        self.assertFalse(self._xray(self.cube_a))

    def test_b006_clears_xray_on_all_meshes(self):
        # Enable xray on cube_a + cube_b, leave cube_c untouched.
        cmds.displaySurface(self.cube_a, xRay=True)
        cmds.displaySurface(self.cube_b, xRay=True)
        self.assertTrue(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))

        self.instance.b006()

        # All meshes must be cleared, regardless of prior state.
        self.assertFalse(self._xray(self.cube_a))
        self.assertFalse(self._xray(self.cube_b))
        self.assertFalse(self._xray(self.cube_c))

    def test_b007_toggles_xray_on_non_selected(self):
        """Xray Other — apply to everything EXCEPT the selection."""
        cmds.select([self.cube_a])

        self.instance.b007()

        # cube_a was selected → must NOT be x-rayed.
        self.assertFalse(self._xray(self.cube_a))
        # cube_b and cube_c were not selected → toggled on.
        self.assertTrue(self._xray(self.cube_b))
        self.assertTrue(self._xray(self.cube_c))

    def test_b007_with_nothing_selected_toggles_everything(self):
        """When selection is empty, all meshes are "other" → all get toggled."""
        cmds.select(clear=True)
        self.instance.b007()
        self.assertTrue(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))
        self.assertTrue(self._xray(self.cube_c))


if __name__ == "__main__":
    unittest.main()
