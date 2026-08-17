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

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
display_module = maya_module("tentacle.slots.maya.display")


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

    def test_b005_mixed_selection_unifies_on(self):
        """A mesh that lost its xray among xray'd others: ONE press turns all on.

        Regression: topology ops (polyUnite/Separate/boolean/duplicate/reload)
        silently drop the xRay flag. The old per-object blind invert then
        toggled the still-on meshes OFF while turning the lost one on,
        forcing a second press. The toggle must unify: any-off -> all on.
        """
        cmds.displaySurface(self.cube_a, xRay=True)
        cmds.select([self.cube_a, self.cube_b])

        self.instance.b005()

        self.assertTrue(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))

    def test_b005_operates_on_group_selection(self):
        """displaySurface query returns None on a group — the old code
        silently skipped it, making the button a no-op on group selections."""
        cmds.group(self.cube_a, self.cube_b, name="xr_grp")
        cmds.select("xr_grp")

        self.instance.b005()

        self.assertTrue(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))
        self.assertFalse(self._xray(self.cube_c))

    def test_b005_component_selection(self):
        """Component-mode selection (faces) must resolve to the owning mesh
        (the old ls(transforms=True) filter dropped components -> no-op)."""
        cmds.select(f"{self.cube_a}.f[0]")

        self.instance.b005()

        self.assertTrue(self._xray(self.cube_a))
        self.assertFalse(self._xray(self.cube_b))

    def test_b007_mixed_others_unify_on(self):
        """Xray Other with mixed non-selected states: one press -> all on."""
        cmds.displaySurface(self.cube_b, xRay=True)
        cmds.select(self.cube_a)

        self.instance.b007()

        self.assertFalse(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))
        self.assertTrue(self._xray(self.cube_c))

    def test_list_xray_selected_reports_resulting_state(self):
        """The list wrapper rides b005's (state, count) return."""
        cmds.select(self.cube_a)
        self.assertIn("On", self.instance._list_xray_selected())
        self.assertIn("Off", self.instance._list_xray_selected())
        cmds.select(clear=True)
        self.assertIn("nothing selected", self.instance._list_xray_selected())

    def test_b007_with_nothing_selected_toggles_everything(self):
        """When selection is empty, all meshes are "other" → all get toggled."""
        cmds.select(clear=True)
        self.instance.b007()
        self.assertTrue(self._xray(self.cube_a))
        self.assertTrue(self._xray(self.cube_b))
        self.assertTrue(self._xray(self.cube_c))


if __name__ == "__main__":
    unittest.main()
