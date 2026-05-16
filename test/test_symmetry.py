#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.symmetry.

The units worth pinning:

- chk000/1/2: each axis (x/y/z) maps to cmds.symmetricModelling(axis=...).
- chk005 (Topo symmetry): requires an edge selection; catches RuntimeError
  when activation fails and warns.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import symmetry as symmetry_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    symmetry_module = None
    _MAYA_AVAILABLE = False


class _RecordedSb:
    def __init__(self):
        self.messages = []
        self.toggle_calls = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))

    def toggle_multi(self, target, **kwargs):
        self.toggle_calls.append((target, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestChkAxes(unittest.TestCase):
    """chk000/1/2 each set a different axis on cmds.symmetricModelling."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = symmetry_module.Symmetry.__new__(symmetry_module.Symmetry)

        self._orig = cmds.symmetricModelling
        self.calls = []
        cmds.symmetricModelling = lambda **kw: self.calls.append(kw)

    def tearDown(self):
        cmds.symmetricModelling = self._orig
        cmds.file(new=True, force=True)

    def test_chk000_sets_x(self):
        self.instance.chk000(state=True, widget=None)
        self.assertEqual(self.calls[-1]["axis"], "x")
        self.assertTrue(self.calls[-1]["symmetry"])

    def test_chk001_sets_y(self):
        self.instance.chk001(state=True, widget=None)
        self.assertEqual(self.calls[-1]["axis"], "y")

    def test_chk002_sets_z(self):
        self.instance.chk002(state=True, widget=None)
        self.assertEqual(self.calls[-1]["axis"], "z")

    def test_unchecked_disables_symmetry(self):
        """state=False → symmetry=False (axis still set, but disabled)."""
        self.instance.chk000(state=False, widget=None)
        self.assertFalse(self.calls[-1]["symmetry"])


if __name__ == "__main__":
    unittest.main()
