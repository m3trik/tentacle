#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.subdivision.

subdivision.py is dominated by thin mel.eval dispatchers. The units worth
pinning at this layer:

- The one-click buttons (b000/b001/b008/b011/b028) each dispatch one exact
  MEL command — silent drift in those strings would ship broken menu
  entries with no error.
- s000 (Division Level) / s001 (Adaptive Level): write the smooth-preview
  attrs to the mesh SHAPES under the selection. These used to guard with
  ``attributeQuery(node=<transform>)``, which is always False for a shape
  attribute — so both spinboxes were silently inert on every mesh.

(TestCmb001SmoothProxyDispatch / TestCmb002MayaSubdivisionDispatch removed
2026-07-12: the cmb001/cmb002 combo dispatchers they drove were redesigned
out of the slot — their ops now ship as the direct buttons pinned below
(Add Divisions=b008, Smooth=b011 apply-preview, Reduce=b005/tb000 Decimate)
plus the smoothProxy() static — so both classes raised AttributeError under
mayapy.)
"""
import unittest

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
mel = maya_module("maya.mel")
subdivision_module = maya_module("tentacle.slots.maya.subdivision")


class _FakeSb:
    """Minimal switchboard stub recording message_box calls."""

    def __init__(self):
        self.messages = []

    def message_box(self, string, *args, **kwargs):
        self.messages.append(string)


class _FakeSpinBox:
    """Minimal QSpinBox stand-in: records whether the seed ran signal-blocked."""

    def __init__(self):
        self._value = None
        self._blocked = False
        self.blocked_during_seed = False
        self.restore_state = True

    def blockSignals(self, block):
        was, self._blocked = self._blocked, block
        return was

    def setValue(self, value):
        self._value = value
        self.blocked_during_seed = self._blocked

    def value(self):
        return self._value


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
class TestSmoothPreviewSpinBoxes(unittest.TestCase):
    """s000/s001 drive the smooth-preview attrs on the selection's mesh shapes.

    ``smoothLevel`` / ``smoothTessLevel`` live on the MESH SHAPE. The old
    implementation walked the selection up to its transforms and guarded on
    ``cmds.attributeQuery(..., node=<transform>, exists=True)`` — always False
    for a shape attribute — so nothing was ever written, on any mesh.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = subdivision_module.Subdivision.__new__(
            subdivision_module.Subdivision
        )
        # stub sb so the bare __new__ instance can post feedback headlessly.
        self.instance.sb = _FakeSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    @staticmethod
    def _shape(transform):
        return cmds.listRelatives(transform, shapes=True, fullPath=True)[0]

    def test_plain_cube_gets_the_division_level(self):
        cube = cmds.polyCube(name="sub_plain")[0]
        cmds.select(cube)

        self.instance.s000(5, widget=None)

        shape = self._shape(cube)
        self.assertEqual(cmds.getAttr(f"{shape}.smoothLevel"), 5)
        # The level is unobservable unless the preview itself is on.
        self.assertEqual(cmds.getAttr(f"{shape}.displaySmoothMesh"), 2)
        self.assertEqual(len(self.instance.sb.messages), 1)
        self.assertIn("Division Level", self.instance.sb.messages[0])

    def test_division_level_reaches_meshes_under_a_group(self):
        cube = cmds.polyCube(name="sub_grp_cube")[0]
        grp = cmds.group(cube, name="sub_grp")
        cmds.select(grp)

        self.instance.s000(4, widget=None)

        self.assertEqual(cmds.getAttr(f"{self._shape(grp + '|sub_grp_cube')}.smoothLevel"), 4)

    def test_adaptive_level_switches_to_the_adaptive_draw_type(self):
        """``smoothTessLevel`` is inert unless the shape draws with OpenSubdiv
        Adaptive, and a mesh follows the GLOBAL draw type by default."""
        cube = cmds.polyCube(name="sub_adaptive")[0]
        cmds.select(cube)

        self.instance.s001(4, widget=None)

        shape = self._shape(cube)
        self.assertEqual(cmds.getAttr(f"{shape}.smoothTessLevel"), 4)
        self.assertEqual(cmds.getAttr(f"{shape}.smoothDrawType"), 3)
        self.assertFalse(cmds.getAttr(f"{shape}.useGlobalSmoothDrawType"))
        self.assertIn("Adaptive Level", self.instance.sb.messages[0])

    def test_non_mesh_selection_is_a_silent_no_op(self):
        curve = cmds.curve(name="sub_curve", degree=1, point=[(0, 0, 0), (1, 0, 0)])
        cmds.select(curve)

        self.instance.s000(3, widget=None)
        self.instance.s001(3, widget=None)

        self.assertEqual(self.instance.sb.messages, [])

    def test_init_seeds_from_the_selection_and_opts_out_of_persistence(self):
        """A persisted spinbox value re-fires its slot on panel open — which
        would smooth whatever happened to be selected. ``mirror_app_state``
        seeds from the mesh with signals blocked and clears ``restore_state``."""
        cube = cmds.polyCube(name="sub_init_cube")[0]
        cmds.setAttr(f"{self._shape(cube)}.smoothLevel", 4)
        cmds.select(cube)
        widget = _FakeSpinBox()

        self.instance.s000_init(widget)

        self.assertEqual(widget.value(), 4)
        self.assertFalse(widget.restore_state)
        self.assertTrue(widget.blocked_during_seed)

    def test_init_without_a_mesh_leaves_the_ui_default(self):
        cmds.select(clear=True)
        widget = _FakeSpinBox()

        self.instance.s000_init(widget)

        self.assertIsNone(widget.value())
        self.assertFalse(widget.restore_state)

    def test_mixed_selection_still_reaches_the_mesh(self):
        cube = cmds.polyCube(name="sub_mixed_cube")[0]
        curve = cmds.curve(name="sub_mixed_curve", degree=1, point=[(0, 0, 0), (1, 0, 0)])
        cmds.select([cube, curve])

        self.instance.s000(2, widget=None)

        self.assertEqual(cmds.getAttr(f"{self._shape(cube)}.smoothLevel"), 2)


if __name__ == "__main__":
    unittest.main()
