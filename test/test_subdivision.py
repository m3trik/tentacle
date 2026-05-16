#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.subdivision.

subdivision.py is dominated by mel.eval dispatch tables. The units worth
pinning at this layer:

- cmb001: 5-way dispatch by text — drift between init items and branches
  would silently break menu options.
- cmb002: 3-way dispatch by widget.items.index() lookup — different
  fragility (relies on list order, not text comparison).
- s000 (Division Level): only acts on transforms with a smoothLevel
  attribute, set via mtk.Attributes.set_attributes. Guards against
  applying smooth attrs to non-subdivision meshes.
"""
import unittest

try:
    import maya.cmds as cmds
    import maya.mel as mel
    from tentacle.slots.maya import subdivision as subdivision_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    mel = None
    subdivision_module = None
    _MAYA_AVAILABLE = False


class _FakeWidget:
    def __init__(self, items):
        self.items = list(items)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb001SmoothProxyDispatch(unittest.TestCase):
    """cmb001 dispatches 5 options by text comparison; each routes to a
    different mel command."""

    EXPECTED = {
        "Create Subdiv Proxy": "SmoothProxyOptions",
        "Remove Subdiv Proxy Mirror": "UnmirrorSmoothProxyOptions",
        "Crease Tool": "polyCreaseProperties",
        "Toggle Subdiv Proxy Display": "SmoothingDisplayToggle",
        "Both Proxy and Subdiv Display": "SmoothingDisplayShowBoth",
    }

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = subdivision_module.Subdivision.__new__(
            subdivision_module.Subdivision
        )
        self._orig = mel.eval
        self.mel_calls = []
        mel.eval = lambda s: self.mel_calls.append(s)

    def tearDown(self):
        mel.eval = self._orig
        cmds.file(new=True, force=True)

    def test_each_item_routes_to_expected_mel(self):
        items = list(self.EXPECTED.keys())
        widget = _FakeWidget(items)
        for idx, label in enumerate(items):
            self.mel_calls.clear()
            self.instance.cmb001(idx, widget)
            self.assertEqual(
                self.mel_calls,
                [self.EXPECTED[label]],
                f"'{label}' (index {idx}) did not route correctly",
            )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb002MayaSubdivisionDispatch(unittest.TestCase):
    """cmb002 uses widget.items.index() — order-sensitive, distinct from
    cmb001's text-based dispatch."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = subdivision_module.Subdivision.__new__(
            subdivision_module.Subdivision
        )
        self._orig = mel.eval
        self.mel_calls = []
        mel.eval = lambda s: self.mel_calls.append(s)

    def tearDown(self):
        mel.eval = self._orig
        cmds.file(new=True, force=True)

    def test_reduce_polygons_routes_to_options(self):
        items = ["Reduce Polygons", "Add Divisions", "Smooth"]
        widget = _FakeWidget(items)
        idx = items.index("Reduce Polygons")
        self.instance.cmb002(idx, widget)
        self.assertIn("ReducePolygonOptions", self.mel_calls)

    def test_add_divisions_routes_to_subdivide(self):
        items = ["Reduce Polygons", "Add Divisions", "Smooth"]
        widget = _FakeWidget(items)
        idx = items.index("Add Divisions")
        self.instance.cmb002(idx, widget)
        self.assertIn("SubdividePolygonOptions", self.mel_calls)

    def test_smooth_routes_to_perform_polysmooth(self):
        items = ["Reduce Polygons", "Add Divisions", "Smooth"]
        widget = _FakeWidget(items)
        idx = items.index("Smooth")
        self.instance.cmb002(idx, widget)
        self.assertIn("performPolySmooth 1", self.mel_calls)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestS000DivisionLevel(unittest.TestCase):
    """s000 only writes smoothLevel to objects that have it (subdivision
    proxies). Plain cubes have no smoothLevel attr → skipped."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = subdivision_module.Subdivision.__new__(
            subdivision_module.Subdivision
        )

        import mayatk as mtk
        self._orig = mtk.Attributes.set_attributes
        self.set_calls = []
        mtk.Attributes.set_attributes = lambda obj, **kw: self.set_calls.append(
            (obj, kw)
        )

    def tearDown(self):
        import mayatk as mtk
        mtk.Attributes.set_attributes = self._orig
        cmds.file(new=True, force=True)

    def test_plain_cube_is_skipped(self):
        """Plain polyCube has no smoothLevel → set_attributes never called."""
        cube = cmds.polyCube(name="sub_plain")[0]
        cmds.select(cube)
        self.instance.s000(3, widget=None)
        self.assertEqual(self.set_calls, [])

    def test_object_with_smoothlevel_is_updated(self):
        """An object with smoothLevel attr gets the new value."""
        cube = cmds.polyCube(name="sub_smooth")[0]
        cmds.addAttr(cube, longName="smoothLevel", attributeType="long")
        cmds.select(cube)
        self.instance.s000(5, widget=None)
        self.assertEqual(len(self.set_calls), 1)
        obj, kw = self.set_calls[0]
        self.assertEqual(kw["smoothLevel"], 5)


if __name__ == "__main__":
    unittest.main()
