#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.polygons b000 (Circularize).

Reproduces the bug where the slot rejected border-edge selections (asking for
faces) and did not exercise both component types polyCircularize supports.
"""
import unittest

try:
    import maya.standalone

    if not getattr(maya.standalone, "_tentacle_circ_initialized", False):
        try:
            maya.standalone.initialize()
            maya.standalone._tentacle_circ_initialized = True
        except RuntimeError:
            pass
    import maya.cmds as cmds
    from tentacle.slots.maya import polygons as polygons_mod

    _MAYA_AVAILABLE = True
except ImportError:
    _MAYA_AVAILABLE = False


class _StubSb:
    def __init__(self):
        self.messages = []

    def message_box(self, text):
        self.messages.append(text)


def _border_edges_of_hole(mesh):
    n_edges = cmds.polyEvaluate(mesh, edge=True)
    all_edges = cmds.ls("{}.e[0:{}]".format(mesh, n_edges - 1), fl=True)
    borders = []
    for e in all_edges:
        info = cmds.polyInfo(e, edgeToFace=True)[0]
        parts = info.split(":")[1].split()
        if len(parts) == 1:
            borders.append(e)
    return borders


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCircularize(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, force=True)
        self.slot = polygons_mod.PolygonsSlots.__new__(polygons_mod.PolygonsSlots)
        self.sb = _StubSb()
        self.slot.sb = self.sb

    def _node_count(self):
        return len(cmds.ls(type="polyCircularize") or [])

    def test_face_selection_creates_circularize_node(self):
        plane = cmds.polyPlane(sx=6, sy=6, ch=False)[0]
        faces = ["{}.f[{}]".format(plane, i) for i in (14, 15, 16, 21, 22, 23)]
        cmds.select(faces)
        before = self._node_count()
        result = self.slot.b000()
        self.assertEqual(self.sb.messages, [], "Should not warn on face selection")
        self.assertIsNotNone(result, "Expected polyCircularize result on faces")
        self.assertEqual(self._node_count(), before + 1)

    def test_border_edge_selection_creates_circularize_node(self):
        plane = cmds.polyPlane(sx=6, sy=6, ch=False)[0]
        cmds.delete("{}.f[18]".format(plane))
        borders = _border_edges_of_hole(plane)
        self.assertTrue(borders, "Test fixture must produce border edges")
        cmds.select(borders)
        before = self._node_count()
        result = self.slot.b000()
        self.assertEqual(
            self.sb.messages,
            [],
            "Border edges must be accepted — bug was rejecting them as non-faces",
        )
        self.assertIsNotNone(result, "Expected polyCircularize result on edges")
        self.assertEqual(self._node_count(), before + 1)

    def test_empty_selection_shows_message(self):
        cmds.select(clear=True)
        before = self._node_count()
        self.slot.b000()
        self.assertEqual(len(self.sb.messages), 1)
        self.assertEqual(self._node_count(), before, "No node should be created")

    def test_vertex_selection_creates_circularize_node(self):
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
        self.assertEqual(self.sb.messages, [], "Verts must be accepted")
        self.assertIsNotNone(result)
        self.assertEqual(self._node_count(), before + 1)


if __name__ == "__main__":
    unittest.main()
