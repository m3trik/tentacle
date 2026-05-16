#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.materials.

materials.py is a 740-line slot module dominated by UI plumbing. The
unit worth pinning is `_strip_material_names` — it does real work
(collision resolution, alphabetical suffixing, rename dispatch) over
ptk.StrUtils.resolve_name_collisions and returns a structured result.
A bug here would silently mis-rename materials across asset pipelines.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import materials as materials_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    materials_module = None
    _MAYA_AVAILABLE = False


class _FakeAlphaOption:
    """Stand-in for the lbl007 alpha-mode option box state."""

    def __init__(self, alpha_on):
        # 1 = alphabetical suffix mode; 0 = skip-on-collision
        self.current_state = 1 if alpha_on else 0


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCollisionModeIsAlpha(unittest.TestCase):
    """_collision_mode_is_alpha reads the persistent toggle."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = materials_module.MaterialsSlots.__new__(
            materials_module.MaterialsSlots
        )

    def test_no_option_set_returns_false(self):
        # Attribute not set → bool(None) is False.
        self.assertFalse(self.instance._collision_mode_is_alpha())

    def test_state_1_returns_true(self):
        self.instance._strip_alpha_option = _FakeAlphaOption(alpha_on=True)
        self.assertTrue(self.instance._collision_mode_is_alpha())

    def test_state_0_returns_false(self):
        self.instance._strip_alpha_option = _FakeAlphaOption(alpha_on=False)
        self.assertFalse(self.instance._collision_mode_is_alpha())


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestStripMaterialNames(unittest.TestCase):
    """_strip_material_names renames materials by stripping trailing ints/underscores.

    Delegates to ptk.StrUtils.resolve_name_collisions; the slot's job is
    to wire candidates in, drive cmds.rename, and classify the result
    into renamed/no_change/conflicts/failed buckets.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = materials_module.MaterialsSlots.__new__(
            materials_module.MaterialsSlots
        )
        # Default: alpha mode OFF (the safer default).
        self.instance._strip_alpha_option = _FakeAlphaOption(alpha_on=False)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _make_mat(self, name):
        """Create a lambert with the given name."""
        return cmds.shadingNode("lambert", asShader=True, name=name)

    def test_returns_dict_with_four_keys(self):
        mat = self._make_mat("foo_1")
        result = self.instance._strip_material_names([mat])
        self.assertEqual(
            set(result.keys()),
            {"renamed", "no_change", "conflicts", "failed"},
        )

    def test_strips_trailing_int_on_singleton(self):
        """A single material with a bare trailing int strips to its base.

        Note: ``_<int>`` numbering is deliberately preserved (intentional
        index), so we use ``mymat1`` not ``mymat_1`` here.
        """
        mat = self._make_mat("mymat1")
        result = self.instance._strip_material_names([mat])
        # Should produce exactly one rename mymat1 -> mymat.
        self.assertEqual(len(result["renamed"]), 1)
        old, new = result["renamed"][0]
        self.assertEqual(old, "mymat1")
        self.assertEqual(new, "mymat")
        # The renamed node exists in the scene.
        self.assertTrue(cmds.objExists("mymat"))

    def test_no_trailing_int_means_no_change(self):
        """A material already at its base name has nothing to strip."""
        mat = self._make_mat("plain")
        result = self.instance._strip_material_names([mat])
        self.assertEqual(result["renamed"], [])
        self.assertIn("plain", result["no_change"])

    def test_alpha_mode_off_skips_collisions(self):
        """Two materials sharing a base name: alpha mode off → skip both.

        Bare trailing ints get stripped to the same base, causing
        collision: ``mat1`` and ``mat2`` both reduce to ``mat``.
        """
        a = self._make_mat("mat1")
        b = self._make_mat("mat2")

        self.instance._strip_alpha_option = _FakeAlphaOption(alpha_on=False)
        result = self.instance._strip_material_names([a, b])

        # With alpha mode off, both stay put — no renames.
        self.assertEqual(result["renamed"], [])

    def test_alpha_mode_on_resolves_collisions_with_letters(self):
        """Two materials with same base get _A, _B alphabetical suffixes."""
        a = self._make_mat("mat1")
        b = self._make_mat("mat2")

        self.instance._strip_alpha_option = _FakeAlphaOption(alpha_on=True)
        result = self.instance._strip_material_names([a, b])

        # Should produce two renames, with names ending in distinct alpha
        # suffixes (e.g. mat_A, mat_B).
        self.assertEqual(len(result["renamed"]), 2)
        new_names = sorted(n for _, n in result["renamed"])
        # Both new names should be distinct and end with different alpha letters.
        self.assertNotEqual(new_names[0], new_names[1])

    def test_external_collision_reported(self):
        """If the stripped name collides with an unrelated existing node,
        the rename should be skipped and reported in `conflicts`."""
        # Create an unrelated transform that occupies the target name.
        cmds.createNode("transform", name="blocked")
        mat = self._make_mat("blocked1")  # bare trailing int strips to 'blocked'

        result = self.instance._strip_material_names([mat])

        # The unrelated node must survive.
        self.assertTrue(cmds.objExists("blocked"))
        # The mat should be reported as a conflict (stripped target exists).
        self.assertIn("blocked1", result["conflicts"])

    def test_empty_input_returns_empty_result(self):
        result = self.instance._strip_material_names([])
        self.assertEqual(result["renamed"], [])
        self.assertEqual(result["no_change"], [])
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(result["failed"], [])


if __name__ == "__main__":
    unittest.main()
