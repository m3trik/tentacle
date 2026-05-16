#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.uv.

uv.py is the largest tentacle slot (~1200 lines) and almost entirely UI
orchestration over mayatk and cmds. The testable units worth pinning
at this layer:

- get_map_size: the cmb003 value-carrier read (not a click handler).
- b000 (Transfer UVs): the ≥2-ordered-selection gate.
- b005 (Cut UVs): the "selected edges vs whole mesh" routing.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import uv as uv_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    uv_module = None
    _MAYA_AVAILABLE = False


class _FakeCmb:
    def __init__(self, text):
        self._t = text

    def currentText(self):
        return self._t


class _FakeUi:
    pass


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestGetMapSize(unittest.TestCase):
    """get_map_size casts cmb003 text to int. Used throughout the file
    by texel-density operations.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.ui = _FakeUi()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_returns_int_from_combo_text(self):
        self.instance.ui.cmb003 = _FakeCmb("2048")
        self.assertEqual(self.instance.get_map_size(), 2048)

    def test_returns_correct_int_for_common_sizes(self):
        for size in (256, 512, 1024, 2048, 4096):
            self.instance.ui.cmb003 = _FakeCmb(str(size))
            self.assertEqual(self.instance.get_map_size(), size)

    def test_non_numeric_text_raises(self):
        """Contract: garbage in cmb003 raises ValueError (no silent fallback)."""
        self.instance.ui.cmb003 = _FakeCmb("not_a_number")
        with self.assertRaises(ValueError):
            self.instance.get_map_size()


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB000TransferUVsGate(unittest.TestCase):
    """b000 (Transfer UVs) requires ≥2 ordered-selected objects."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()

        # Capture mtk.transfer_uvs calls.
        import mayatk as mtk
        self._original = mtk.transfer_uvs
        self.captured = []

        def fake_transfer(frm, to):
            self.captured.append((frm, to))

        mtk.transfer_uvs = fake_transfer

    def tearDown(self):
        import mayatk as mtk
        mtk.transfer_uvs = self._original
        cmds.file(new=True, force=True)

    def test_no_selection_warns_and_skips(self):
        cmds.select(clear=True)
        self.instance.b000(widget=None)
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_one_object_warns_and_skips(self):
        a = cmds.polyCube(name="uv_b000_one")[0]
        cmds.select(a)
        self.instance.b000(widget=None)
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_two_objects_dispatches_once(self):
        a = cmds.polyCube(name="uv_b000_a")[0]
        b = cmds.polyCube(name="uv_b000_b")[0]
        cmds.select([a, b])

        self.instance.b000(widget=None)

        # frm=a, to=[b] → one transfer call
        self.assertEqual(len(self.captured), 1)
        self.assertEqual(self.captured[0][0], a)
        self.assertEqual(self.captured[0][1], b)

    def test_three_objects_dispatches_twice(self):
        a = cmds.polyCube(name="uv_b000_a3")[0]
        b = cmds.polyCube(name="uv_b000_b3")[0]
        c = cmds.polyCube(name="uv_b000_c3")[0]
        cmds.select([a, b, c])

        self.instance.b000(widget=None)

        # frm=a, to=[b, c] → two transfer calls
        self.assertEqual(len(self.captured), 2)
        self.assertEqual(self.captured[0][0], a)
        self.assertEqual(self.captured[1][0], a)
        self.assertEqual({self.captured[0][1], self.captured[1][1]}, {b, c})


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB005CutUVsRouting(unittest.TestCase):
    """b005 (Cut UVs) routes to polyMapCut differently for edges vs transforms."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = uv_module.UvSlots.__new__(uv_module.UvSlots)
        self.instance.sb = _RecordedSb()

        # Capture polyMapCut calls.
        self._original = cmds.polyMapCut
        self.captured = []
        cmds.polyMapCut = lambda edges: self.captured.append(edges)

    def tearDown(self):
        cmds.polyMapCut = self._original
        cmds.file(new=True, force=True)

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b005()
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_edge_selection_routes_polyMapCut(self):
        cube = cmds.polyCube(name="uv_cut_cube")[0]
        cmds.select(f"{cube}.e[0:3]")
        self.instance.b005()
        self.assertGreater(len(self.captured), 0)

    def test_transform_selection_cuts_all_mesh_edges(self):
        """When a transform is selected (no edge components), Cut UVs targets all edges."""
        cube = cmds.polyCube(name="uv_cut_all")[0]
        cmds.select(cube)
        self.instance.b005()
        # Should have made at least one polyMapCut call on the cube's edges.
        self.assertGreater(len(self.captured), 0)
        # The argument should be a glob-like edge spec.
        joined = " ".join(str(c) for c in self.captured)
        self.assertIn(".e[", joined)


if __name__ == "__main__":
    unittest.main()
