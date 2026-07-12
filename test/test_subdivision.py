#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.subdivision.

subdivision.py is dominated by thin mel.eval dispatchers. The units worth
pinning at this layer:

- The one-click buttons (b000/b001/b008/b011/b028) each dispatch one exact
  MEL command — silent drift in those strings would ship broken menu
  entries with no error.
- s000 (Division Level): only acts on transforms with a smoothLevel
  attribute, set via mtk.Attributes.set_attributes. Guards against
  applying smooth attrs to non-subdivision meshes.

(TestCmb001SmoothProxyDispatch / TestCmb002MayaSubdivisionDispatch removed
2026-07-12: the cmb001/cmb002 combo dispatchers they drove were redesigned
out of the slot — their ops now ship as the direct buttons pinned below
(Add Divisions=b008, Smooth=b011 apply-preview, Reduce=b005/tb000 Decimate)
plus the smoothProxy() static — so both classes raised AttributeError under
mayapy.)
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


class _FakeSb:
    """Minimal switchboard stub recording message_box calls."""

    def __init__(self):
        self.messages = []

    def message_box(self, string, *args, **kwargs):
        self.messages.append(string)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestMelDispatchButtons(unittest.TestCase):
    """Each one-click button is a thin mel.eval dispatcher — pin the exact
    MEL command per button so dispatch-string drift can't ship silently."""

    EXPECTED = {
        "b000": "performPolyQuadrangulate 0",
        "b001": "polyTriangulate",
        "b008": "SubdividePolygon",
        "b011": "performSmoothMeshPreviewToPolygon",
        "b028": "dR_quadDrawTool",
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

    def test_each_button_routes_to_expected_mel(self):
        for slot_name, command in self.EXPECTED.items():
            self.mel_calls.clear()
            getattr(self.instance, slot_name)()
            self.assertEqual(
                self.mel_calls,
                [command],
                f"{slot_name} did not dispatch `{command}`",
            )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestS000DivisionLevel(unittest.TestCase):
    """s000 only writes smoothLevel to objects that have it (subdivision
    proxies). Plain cubes have no smoothLevel attr → skipped."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = subdivision_module.Subdivision.__new__(
            subdivision_module.Subdivision
        )
        # s000 posts per-object message_box feedback (added post-redesign) —
        # stub sb so the bare __new__ instance can run it headlessly.
        self.instance.sb = _FakeSb()

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
        self.assertEqual(self.instance.sb.messages, [])

    def test_object_with_smoothlevel_is_updated(self):
        """An object with smoothLevel attr gets the new value (and posts the
        per-object Division Level feedback message)."""
        cube = cmds.polyCube(name="sub_smooth")[0]
        cmds.addAttr(cube, longName="smoothLevel", attributeType="long")
        cmds.select(cube)
        self.instance.s000(5, widget=None)
        self.assertEqual(len(self.set_calls), 1)
        obj, kw = self.set_calls[0]
        self.assertEqual(kw["smoothLevel"], 5)
        self.assertEqual(len(self.instance.sb.messages), 1)
        self.assertIn("Division Level", self.instance.sb.messages[0])


if __name__ == "__main__":
    unittest.main()
