#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.polygons.

The existing test_polygons_circularize covers b000. This file fills in
the rest of the slot's behavioral surface — the units worth pinning are
those with conditional routing or state-toggle logic:

- tb003 (Extrude): Maya's own Extrude on the real selection (any mask),
  with the option box's values -- and Maya's own settings left intact.
- tb007 (Divide Facet): mode/dv/u/v/subdMethod values driven by a 3-way
  U/V/Tris checkbox state, plus an "all U+V" special case.
- tb008 (Boolean): 3 ops × interactive matrix (6 dispatch paths).
- tb009 (Snap Closest Verts): exact-2-objects gate, ignores other counts.
- tb005 (Detach): chk020 negation (separate_each → not keep_faces_together).
- b005 (Set Distance): ValueError on != 2 vertices, falls back to default.
- b006 (Bridge): RuntimeError fallback to bridge_connected_edges.
- b038 (Assign Invisible): toggles based on current polyHole(q=True) state.
- b009 (Collapse Component): faces collapse each (per object, instances folded,
  any mask); edges/verts merge at one center; refusals named; one undo.
- b011 / b007 marking-menu key names (drift detector).
"""
import unittest

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
mel = maya_module("maya.mel")
polygons_module = maya_module("tentacle.slots.maya.polygons")


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeSpin:
    def __init__(self, val):
        self._v = val

    def value(self):
        return self._v


class _FakeCombo:
    def __init__(self, text):
        self._t = text

    def currentText(self):
        return self._t


class _FakeMenu:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    def __init__(self, menu):
        self.option_box = _FakeOptionBox(menu)


class _FakeMarkingMenu:
    def __init__(self):
        self.shown = []

    def show(self, name):
        self.shown.append(name)


class _FakeHandlers:
    def __init__(self):
        self.marking_menu = _FakeMarkingMenu()


class _RecordedSb:
    def __init__(self):
        self.messages = []
        self.handlers = _FakeHandlers()

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class _MaskNamesNoType(unittest.TestCase):
    """Selection-type mask cleared to how multi-component mode leaves it.

    Slots must route on the selection itself: with this mask no vertex / edge
    / facet query is true (under mayapy standalone every query answers None).
    The three flags are restored so the GUI suite run is left as found.
    """

    MASK = ("vertex", "edge", "facet")

    def setUp(self):
        self._mask = {m: cmds.selectType(q=True, **{m: True}) for m in self.MASK}

    def tearDown(self):
        for m, on in self._mask.items():
            if on is not None:  # None: standalone keeps no mask
                cmds.selectType(**{m: on})

    def clear_mask(self):
        cmds.selectType(**{m: False for m in self.MASK})


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb003Extrude(_MaskNamesNoType):
    """tb003 runs Maya's own Extrude on the real selection with the option
    box's values.

    Real geometry, no command mocks. The old mocks pinned a no-op
    ``polyExtrudeFacet(edit=1, ...)`` call: Maya's Extrude reads optionVars,
    so the option box was silently ignored, and a ``selectType`` mask gate
    dropped face selections made in multi-component mode.
    """

    OPTION_VARS = (
        "polyKeepFacetsGrouped",
        "polyExtrudeFaceDivisions",
        "polyExtrudeEdgeDivisions",
        "polyExtrudeVertexDivisions",
    )

    def setUp(self):
        super().setUp()
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()
        self._saved = {
            n: cmds.optionVar(q=n) if cmds.optionVar(exists=n) else None
            for n in self.OPTION_VARS
        }
        # Maya's own Extrude settings: the slot must neither obey nor clobber them.
        for n in self.OPTION_VARS:
            cmds.optionVar(intValue=(n, 1))

    def tearDown(self):
        for n, v in self._saved.items():
            if v is None:
                cmds.optionVar(remove=n)
            else:
                cmds.optionVar(intValue=(n, v))
        cmds.file(new=True, force=True)
        super().tearDown()

    def _extrude(self, *items, keep_together=False, divisions=3):
        cmds.select(items)
        self.clear_mask()
        menu = _FakeMenu(chk002=_FakeChk(keep_together), s004=_FakeSpin(divisions))
        self.instance.tb003(_FakeWidget(menu))

    def _node(self, node_type):
        nodes = cmds.ls(type=node_type) or []
        self.assertEqual(len(nodes), 1, f"expected one {node_type}, got {nodes}")
        return nodes[0]

    @staticmethod
    def _center(face):
        pts = cmds.xform(face, q=True, ws=True, t=True)
        n = len(pts) // 3
        return [sum(pts[i::3]) / n for i in range(3)]

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.tb003(
            _FakeWidget(_FakeMenu(chk002=_FakeChk(True), s004=_FakeSpin(1)))
        )
        self.assertTrue(self.instance.sb.messages)
        self.assertFalse(cmds.ls(type="polyExtrudeFace"))

    def test_single_face_plane_uses_option_box_values(self):
        plane = cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(f"{plane}.f[0]", keep_together=False, divisions=3)
        node = self._node("polyExtrudeFace")
        self.assertFalse(cmds.getAttr(f"{node}.keepFacesTogether"))
        self.assertEqual(cmds.getAttr(f"{node}.divisions"), 3)

    def test_edge_extrude_uses_option_box_values(self):
        cube = cmds.polyCube()[0]
        self._extrude(f"{cube}.e[0]", keep_together=False, divisions=2)
        node = self._node("polyExtrudeEdge")
        self.assertFalse(cmds.getAttr(f"{node}.keepFacesTogether"))
        self.assertEqual(cmds.getAttr(f"{node}.divisions"), 2)

    def test_vertex_extrude_uses_divisions(self):
        cube = cmds.polyCube()[0]
        self._extrude(f"{cube}.vtx[0]", divisions=2)
        node = self._node("polyExtrudeVertex")
        self.assertEqual(cmds.getAttr(f"{node}.divisions"), 2)

    def test_object_selection_extrudes_its_faces(self):
        plane = cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(plane)
        self._node("polyExtrudeFace")

    def test_faces_on_two_objects_extrude_each(self):
        a = cmds.polyPlane(sx=1, sy=1)[0]
        b = cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(f"{a}.f[0]", f"{b}.f[0]", keep_together=False)
        nodes = cmds.ls(type="polyExtrudeFace") or []
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            self.assertFalse(cmds.getAttr(f"{node}.keepFacesTogether"))

    def test_keep_together_off_pushes_each_face_along_its_own_normal(self):
        # Adjacent faces with different normals: welded (kept together) they
        # would share the corner verts and lean; apart, each rides its own.
        cube = cmds.polyCube()[0]
        faces = [f"{cube}.f[0]", f"{cube}.f[1]"]
        normals = []
        for f in faces:  # polyInfo's normals are unnormalized
            v = [
                float(c)
                for c in cmds.polyInfo(f, faceNormals=True)[0].split(":")[1].split()
            ]
            length = sum(c * c for c in v) ** 0.5
            normals.append([c / length for c in v])
        before = [self._center(f) for f in faces]
        self._extrude(*faces, keep_together=False, divisions=1)
        cmds.setAttr(f"{self._node('polyExtrudeFace')}.localTranslateZ", 1.0)
        for face, b, n in zip(faces, before, normals):
            moved = [a - c for a, c in zip(self._center(face), b)]
            for m, e in zip(moved, n):
                self.assertAlmostEqual(m, e, places=4, msg=face)

    def test_maya_extrude_settings_restored(self):
        cmds.optionVar(remove="polyExtrudeVertexDivisions")  # absent stays absent
        plane = cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(f"{plane}.f[0]", keep_together=False, divisions=3)
        for n in self.OPTION_VARS[:3]:
            self.assertEqual(cmds.optionVar(q=n), 1, n)
        self.assertFalse(cmds.optionVar(exists="polyExtrudeVertexDivisions"))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb007DivideFacet(unittest.TestCase):
    """tb007 sets dv/u/v/mode/subdMethod based on chk008/009/010."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

        self._orig = cmds.polySubdivideFacet
        self.calls = []
        cmds.polySubdivideFacet = lambda *a, **kw: self.calls.append((a, kw))

    def tearDown(self):
        cmds.polySubdivideFacet = self._orig
        cmds.file(new=True, force=True)

    def _widget(self, u, v, tris):
        return _FakeWidget(
            _FakeMenu(
                chk008=_FakeChk(u),
                chk009=_FakeChk(v),
                chk010=_FakeChk(tris),
            )
        )

    def _run_with_face_sel(self, widget):
        cube = cmds.polyCube(name="dv_facet")[0]
        cmds.select(f"{cube}.f[0]")
        self.instance.tb007(widget)

    def test_no_face_selection_warns(self):
        cmds.select(clear=True)
        self.instance.tb007(self._widget(True, True, False))
        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(self.calls, [])

    def test_u_and_v_subdivides_into_quads(self):
        """U+V (no tris): dv=1, subdMethod=0, u=v=0 — single quad subdivide."""
        self._run_with_face_sel(self._widget(True, True, False))
        self.assertEqual(len(self.calls), 1)
        kw = self.calls[0][1]
        self.assertEqual(kw["divisions"], 1)
        self.assertEqual(kw["subdMethod"], 0)
        self.assertEqual(kw["divisionsU"], 0)
        self.assertEqual(kw["divisionsV"], 0)
        self.assertEqual(kw["mode"], 0)

    def test_only_u_sets_divisionsU_2(self):
        """U only: divisionsU=2, divisionsV=0."""
        self._run_with_face_sel(self._widget(True, False, False))
        self.assertEqual(len(self.calls), 1)
        kw = self.calls[0][1]
        self.assertEqual(kw["divisionsU"], 2)
        self.assertEqual(kw["divisionsV"], 0)

    def test_only_v_sets_divisionsV_2(self):
        """V only: divisionsV=2, divisionsU=0."""
        self._run_with_face_sel(self._widget(False, True, False))
        kw = self.calls[0][1]
        self.assertEqual(kw["divisionsV"], 2)
        self.assertEqual(kw["divisionsU"], 0)

    def test_tris_mode_sets_mode_1_subd_method_0(self):
        """Tris: mode=1 (triangles), dv=1, subdMethod=0."""
        self._run_with_face_sel(self._widget(False, False, True))
        kw = self.calls[0][1]
        self.assertEqual(kw["mode"], 1)
        self.assertEqual(kw["divisions"], 1)
        self.assertEqual(kw["subdMethod"], 0)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb008Boolean(unittest.TestCase):
    """tb008 dispatches across (Union/Difference/Intersection) × (interactive)."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

        # Capture mtk.Macros.m_boolean and mel.eval.
        import mayatk as mtk
        self._orig_macro = mtk.Macros.m_boolean
        self._orig_mel = mel.eval
        self.macro_calls = []
        self.mel_calls = []
        mtk.Macros.m_boolean = lambda **kw: self.macro_calls.append(kw)
        mel.eval = lambda s: self.mel_calls.append(s)

    def tearDown(self):
        import mayatk as mtk
        mtk.Macros.m_boolean = self._orig_macro
        mel.eval = self._orig_mel
        cmds.file(new=True, force=True)

    def _widget(self, mode, interactive):
        return _FakeWidget(
            _FakeMenu(cmb011=_FakeCombo(mode), chk017=_FakeChk(interactive))
        )

    def _select_two_cubes(self):
        a = cmds.polyCube(name="bool_a")[0]
        b = cmds.polyCube(name="bool_b")[0]
        cmds.select([a, b])

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.tb008(self._widget("Union", False))
        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(self.macro_calls, [])

    def test_union_non_interactive_calls_macro(self):
        self._select_two_cubes()
        self.instance.tb008(self._widget("Union", False))
        self.assertEqual(self.macro_calls, [{"operation": "union"}])

    def test_difference_non_interactive_calls_macro(self):
        self._select_two_cubes()
        self.instance.tb008(self._widget("Difference", False))
        self.assertEqual(self.macro_calls, [{"operation": "difference"}])

    def test_intersection_non_interactive_calls_macro(self):
        self._select_two_cubes()
        self.instance.tb008(self._widget("Intersection", False))
        self.assertEqual(self.macro_calls, [{"operation": "intersection"}])

    def test_union_interactive_calls_mel(self):
        self._select_two_cubes()
        self.instance.tb008(self._widget("Union", True))
        self.assertEqual(self.macro_calls, [])
        self.assertIn("PolygonBooleanUnion", self.mel_calls)

    def test_difference_interactive_calls_mel(self):
        self._select_two_cubes()
        self.instance.tb008(self._widget("Difference", True))
        self.assertIn("PolygonBooleanDifference", self.mel_calls)

    def test_intersection_interactive_calls_mel(self):
        self._select_two_cubes()
        self.instance.tb008(self._widget("Intersection", True))
        self.assertIn("PolygonBooleanIntersection", self.mel_calls)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb009SnapClosestVerts(unittest.TestCase):
    """tb009 requires exactly 2 transforms; ignores 0, 1, 3+."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

        import mayatk as mtk
        self._orig = mtk.EditUtils.snap_closest_verts
        self.calls = []
        mtk.EditUtils.snap_closest_verts = (
            lambda *a, **kw: self.calls.append((a, kw))
        )

    def tearDown(self):
        import mayatk as mtk
        mtk.EditUtils.snap_closest_verts = self._orig
        cmds.file(new=True, force=True)

    def _widget(self):
        return _FakeWidget(_FakeMenu(s005=_FakeSpin(5.0), chk016=_FakeChk(True)))

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.tb009(self._widget())
        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(self.calls, [])

    def test_one_object_warns(self):
        a = cmds.polyCube(name="sn_a")[0]
        cmds.select(a)
        self.instance.tb009(self._widget())
        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(self.calls, [])

    def test_two_objects_dispatches(self):
        a = cmds.polyCube(name="sn_a2")[0]
        b = cmds.polyCube(name="sn_b2")[0]
        cmds.select([a, b])
        self.instance.tb009(self._widget())
        self.assertEqual(len(self.calls), 1)
        # Forwarded as (obj1, obj2, tolerance, freezetransforms).
        args, _ = self.calls[0]
        self.assertEqual(args[0], a)
        self.assertEqual(args[1], b)
        self.assertEqual(args[2], 5.0)
        self.assertTrue(args[3])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb005Detach(unittest.TestCase):
    """tb005 negates chk020 (separate_each → not keep_faces_together)."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

        import mayatk as mtk
        self._orig = mtk.EditUtils.detach_components
        self.calls = []

        def fake_detach(sel, **kwargs):
            self.calls.append(kwargs)
            return []

        mtk.EditUtils.detach_components = fake_detach

    def tearDown(self):
        import mayatk as mtk
        mtk.EditUtils.detach_components = self._orig
        cmds.file(new=True, force=True)

    def _widget(self, duplicate, separate, separate_each):
        return _FakeWidget(
            _FakeMenu(
                chk014=_FakeChk(duplicate),
                chk015=_FakeChk(separate),
                chk020=_FakeChk(separate_each),
            )
        )

    def test_separate_each_inverts_keep_faces_together(self):
        cube = cmds.polyCube(name="det_a")[0]
        cmds.select(f"{cube}.f[0]")

        # chk020=True (separate each) → keep_faces_together=False
        self.instance.tb005(self._widget(True, True, True))
        self.assertEqual(self.calls[-1]["keep_faces_together"], False)

        # chk020=False (keep together) → keep_faces_together=True
        cmds.select(f"{cube}.f[0]")
        self.instance.tb005(self._widget(True, True, False))
        self.assertEqual(self.calls[-1]["keep_faces_together"], True)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB005SetDistance(unittest.TestCase):
    """b005 catches ValueError when selection isn't exactly 2 verts."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )

        # Spin captures setValue; the slot reads it via ui.tb000.option_box.menu.s002.
        class _Spin:
            value_set = None

            def setValue(self, v):
                self.value_set = v

        self._spin = _Spin()
        from types import SimpleNamespace
        self.instance.ui = SimpleNamespace(
            tb000=SimpleNamespace(
                option_box=SimpleNamespace(
                    menu=SimpleNamespace(s002=self._spin)
                )
            )
        )

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_non_two_vertex_selection_uses_default(self):
        """0 verts (ValueError) → falls back to default 0.0005 baseline."""
        cmds.select(clear=True)
        self.instance.b005()
        # The default fallback distance is 0.0005 (with adjustment).
        # We just assert the spin got SOME value set (not crashed).
        self.assertIsNotNone(self._spin.value_set)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB006Bridge(unittest.TestCase):
    """b006 falls back to bridge_connected_edges on RuntimeError."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

        # Capture both paths.
        self._orig_bridge = cmds.polyBridgeEdge
        self._orig_close = cmds.polyCloseBorder
        self.bridge_calls = []
        self.close_calls = []
        cmds.polyBridgeEdge = lambda *a, **kw: (
            self.bridge_calls.append((a, kw)) or "bridgeNode1"
        )
        cmds.polyCloseBorder = lambda *a, **kw: self.close_calls.append((a, kw))

        import mayatk as mtk
        self._orig_fb = mtk.Components.bridge_connected_edges
        self.fallback_calls = []
        mtk.Components.bridge_connected_edges = lambda e: self.fallback_calls.append(e)

    def tearDown(self):
        cmds.polyBridgeEdge = self._orig_bridge
        cmds.polyCloseBorder = self._orig_close
        import mayatk as mtk
        mtk.Components.bridge_connected_edges = self._orig_fb
        cmds.file(new=True, force=True)

    def test_no_edge_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b006(widget=None)
        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(self.bridge_calls, [])

    def test_runtime_error_falls_back_to_connected(self):
        """When polyBridgeEdge raises, falls back to mtk.bridge_connected_edges."""
        cube = cmds.polyCube(name="brg_cube")[0]
        cmds.select(f"{cube}.e[0]")

        def raise_runtime(*a, **kw):
            raise RuntimeError("bridge failed")

        cmds.polyBridgeEdge = raise_runtime
        self.instance.b006(widget=None)
        self.assertEqual(len(self.fallback_calls), 1)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB038AssignInvisible(unittest.TestCase):
    """b038 toggles polyHole assignment based on current state."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

        self._orig = cmds.polyHole
        self.calls = []

        def fake_hole(*a, **kw):
            self.calls.append((a, kw))
            if kw.get("q"):
                return self._return_val
            return None

        cmds.polyHole = fake_hole
        self._return_val = False  # default: not currently a hole

    def tearDown(self):
        cmds.polyHole = self._orig
        cmds.file(new=True, force=True)

    def test_no_face_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b038()
        self.assertTrue(self.instance.sb.messages)
        # Only the filterExpand check — no polyHole calls.
        self.assertEqual(self.calls, [])

    def test_assigns_when_not_currently_hole(self):
        cube = cmds.polyCube(name="ah_cube")[0]
        cmds.select(f"{cube}.f[0]")
        self._return_val = False  # not currently a hole
        self.instance.b038()
        # First call: query. Second: assign True.
        # We can't strictly assert order if Maya's polyHole adds calls,
        # but the second polyHole call should have assignHole=True.
        assigns = [
            kw for _, kw in self.calls if "assignHole" in kw and not kw.get("q")
        ]
        self.assertEqual(len(assigns), 1)
        self.assertTrue(assigns[0]["assignHole"])

    def test_unassigns_when_currently_hole(self):
        cube = cmds.polyCube(name="ah_cube2")[0]
        cmds.select(f"{cube}.f[0]")
        self._return_val = True  # currently a hole
        self.instance.b038()
        assigns = [
            kw for _, kw in self.calls if "assignHole" in kw and not kw.get("q")
        ]
        self.assertEqual(len(assigns), 1)
        self.assertFalse(assigns[0]["assignHole"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB009CollapseComponent(_MaskNamesNoType):
    """b009 collapses each selected face to its own point; edges and vertices
    merge to their shared center. Routed on the selection, not the mask."""

    def setUp(self):
        super().setUp()
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()
        self.plane = cmds.polyPlane(sx=3, sy=3)[0]  # 16 verts
        self._history = cmds.constructionHistory(q=True, toggle=True)

    def tearDown(self):
        cmds.constructionHistory(toggle=self._history)
        cmds.file(new=True, force=True)
        super().tearDown()

    @staticmethod
    def _points(mesh):
        pts = cmds.xform(f"{mesh}.vtx[*]", q=True, os=True, t=True)
        return sorted(
            tuple(round(c, 4) for c in pts[i : i + 3]) for i in range(0, len(pts), 3)
        )

    def _collapse(self, *components):
        cmds.select([f"{self.plane}.{c}" for c in components])
        self.clear_mask()
        self.instance.b009()
        return cmds.polyEvaluate(self.plane, vertex=True)

    def test_faces_collapse_each_to_its_own_point(self):
        # Two corner faces: 3 verts lost each. MergeToCenter would weld all
        # 8 into ONE point (9 left).
        self.assertEqual(self._collapse("f[0]", "f[8]"), 10)

    def test_edges_merge_to_their_center(self):
        self.assertEqual(self._collapse("e[0]"), 15)

    def test_faces_on_two_instances_collapse_as_one_shape(self):
        # Every pick names a face of ONE shape -- f[0] through both paths. A call
        # per path collapsed f[0], then whatever face had renumbered into f[0].
        ref = cmds.polyPlane(sx=3, sy=3)[0]
        cmds.polyCollapseFacet([f"{ref}.f[0]", f"{ref}.f[8]"])
        twin = cmds.instance(self.plane)[0]
        cmds.select([f"{self.plane}.f[0]", f"{twin}.f[0]", f"{twin}.f[8]"])
        self.clear_mask()
        self.instance.b009()
        self.assertEqual(self._points(self.plane), self._points(ref))

    def test_object_selection_is_refused(self):
        # MergeToCenter converts an object pick to ALL its verts in the GUI.
        cmds.select(self.plane)
        self.instance.b009()
        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(cmds.polyEvaluate(self.plane, vertex=True), 16)

    def test_no_selection_is_refused(self):
        cmds.select(clear=True)
        self.instance.b009()
        self.assertTrue(self.instance.sb.messages)

    def test_edges_beside_faces_are_named_not_dropped_silently(self):
        self.assertEqual(self._collapse("f[0]", "e[20]"), 13)
        self.assertTrue(self.instance.sb.messages)

    def test_history_follows_the_toggle(self):
        cmds.delete(self.plane, constructionHistory=True)  # Maya ignores -ch off
        cmds.constructionHistory(toggle=False)  # on a mesh that has history
        self._collapse("f[0]")
        self.assertFalse(cmds.ls(type="polyCollapseF"))

    def test_one_undo_restores_every_object(self):
        other = cmds.polyPlane(sx=3, sy=3)[0]
        cmds.select([f"{self.plane}.f[0]", f"{other}.f[4]"])
        self.clear_mask()
        self.instance.b009()
        cmds.undo()
        self.assertEqual(cmds.polyEvaluate(self.plane, vertex=True), 16)
        self.assertEqual(cmds.polyEvaluate(other, vertex=True), 16)

    def test_faces_on_two_objects_collapse_per_object(self):
        other = cmds.polyPlane(sx=3, sy=3)[0]
        cmds.select([f"{self.plane}.f[0]", f"{self.plane}.f[8]", f"{other}.f[4]"])
        self.clear_mask()
        self.instance.b009()  # polyCollapseFacet refuses a multi-object list
        self.assertEqual(cmds.polyEvaluate(self.plane, vertex=True), 10)
        self.assertEqual(cmds.polyEvaluate(other, vertex=True), 13)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestMarkingMenuKeys(unittest.TestCase):
    """b007 (Bridge), b011 (Bevel) drive marking_menu.show with fragile keys."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = polygons_module.PolygonsSlots.__new__(
            polygons_module.PolygonsSlots
        )
        self.instance.sb = _RecordedSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_b007_shows_bridge_menu(self):
        self.instance.b007()
        self.assertEqual(self.instance.sb.handlers.marking_menu.shown, ["bridge"])

    def test_b011_shows_bevel_menu(self):
        self.instance.b011()
        self.assertEqual(self.instance.sb.handlers.marking_menu.shown, ["bevel"])


if __name__ == "__main__":
    unittest.main()
