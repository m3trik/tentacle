#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.polygons b000 (Circularize).

Reproduces the bug where the slot rejected border-edge selections (asking for
faces) and did not exercise both component types polyCircularize supports. The
composed class asks the toolkit for ``Components.circularize(None)``; in Maya
that is the real ``mtk`` on real geometry.
"""
import unittest
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.polygons import PolygonsSlots

if MAYA_AVAILABLE:
    import maya.standalone

    if not getattr(maya.standalone, "_tentacle_circ_initialized", False):
        try:
            maya.standalone.initialize()
            maya.standalone._tentacle_circ_initialized = True
        except RuntimeError:
            pass


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slot = PolygonsSlots(self.sb)

    def messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]


class TestCircularizeAsks(_SlotsCase):
    def test_b000_circularizes_the_selection(self):
        self.sb.tk.Components.circularize.return_value = ["node"]
        self.assertEqual(self.slot.b000(), ["node"])
        self.sb.tk.Components.circularize.assert_called_once_with(None)
        self.assertEqual(self.messages(), [])

    def test_b000_with_no_component_says_so(self):
        self.sb.tk.Components.circularize.return_value = []
        self.slot.b000()
        self.assertEqual(len(self.messages()), 1)


def _border_edges_of_hole(cmds, mesh):
    n_edges = cmds.polyEvaluate(mesh, edge=True)
    all_edges = cmds.ls("{}.e[0:{}]".format(mesh, n_edges - 1), fl=True)
    borders = []
    for e in all_edges:
        info = cmds.polyInfo(e, edgeToFace=True)[0]
        parts = info.split(":")[1].split()
        if len(parts) == 1:
            borders.append(e)
    return borders


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestCircularize(_SlotsCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        self.sb.tk = maya_module("mayatk")

    def _node_count(self):
        return len(self.cmds.ls(type="polyCircularize") or [])

    def test_face_selection_creates_circularize_node(self):
        cmds = self.cmds
        plane = cmds.polyPlane(sx=6, sy=6, ch=False)[0]
        cmds.select(["{}.f[{}]".format(plane, i) for i in (14, 15, 16, 21, 22, 23)])
        before = self._node_count()
        result = self.slot.b000()
        self.assertEqual(self.messages(), [], "Should not warn on face selection")
        self.assertTrue(result, "Expected polyCircularize result on faces")
        self.assertEqual(self._node_count(), before + 1)

    def test_border_edge_selection_creates_circularize_node(self):
        cmds = self.cmds
        plane = cmds.polyPlane(sx=6, sy=6, ch=False)[0]
        cmds.delete("{}.f[18]".format(plane))
        borders = _border_edges_of_hole(cmds, plane)
        self.assertTrue(borders, "Test fixture must produce border edges")
        cmds.select(borders)
        before = self._node_count()
        result = self.slot.b000()
        self.assertEqual(
            self.messages(), [], "Border edges must be accepted, not rejected as non-faces"
        )
        self.assertTrue(result, "Expected polyCircularize result on edges")
        self.assertEqual(self._node_count(), before + 1)

    def test_empty_selection_shows_message(self):
        self.cmds.select(clear=True)
        before = self._node_count()
        self.slot.b000()
        self.assertEqual(len(self.messages()), 1)
        self.assertEqual(self._node_count(), before, "No node should be created")

    def test_vertex_selection_creates_circularize_node(self):
        cmds = self.cmds
        plane = cmds.polyPlane(sx=6, sy=6, ch=False)[0]
        cmds.delete("{}.f[18]".format(plane))
        # border verts: vertices whose connected-face count < connected-edge count
        border_verts = []
        for i in range(cmds.polyEvaluate(plane, vertex=True)):
            v = "{}.vtx[{}]".format(plane, i)
            fs = cmds.ls(
                cmds.polyListComponentConversion(v, fromVertex=True, toFace=True),
                fl=True,
            )
            es = cmds.ls(
                cmds.polyListComponentConversion(v, fromVertex=True, toEdge=True),
                fl=True,
            )
            if len(fs) < len(es):
                border_verts.append(v)
        self.assertTrue(border_verts)
        cmds.select(border_verts)
        before = self._node_count()
        result = self.slot.b000()
        self.assertEqual(self.messages(), [], "Verts must be accepted")
        self.assertTrue(result)
        self.assertEqual(self._node_count(), before + 1)


if __name__ == "__main__":
    unittest.main()
