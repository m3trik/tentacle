#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.polygons, the one Polygons Slots class.

It reaches its host only through ``self.tk``: a fake toolkit (a MagicMock
switchboard's ``tk``) records what each slot asks of it (plain pytest), and in
Maya the same class drives the real ``mtk`` (``run_tests.py --in-maya``). Pinned
here: each slot's call and arguments, how it words an empty result or a refusal,
the option boxes' host tags, and in Maya the behaviors worth a real scene --
Extrude's settings swap, Divide Facet's subdivision values, Collapse routing on
the selection, Boolean's dispatch, Assign Hole's toggle, Set Distance, Bridge's
fallback. The operations themselves are tested in mayatk and blendertk.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.polygons import PolygonsSlots


def _value(v):
    """A widget answering both isChecked() and value()/currentText()."""
    return SimpleNamespace(
        isChecked=lambda: v, value=lambda: v, currentText=lambda: v
    )


def _widget(**values):
    """An option-box widget whose menu holds *values* by objectName."""
    menu = SimpleNamespace(**{name: _value(v) for name, v in values.items()})
    return SimpleNamespace(option_box=SimpleNamespace(menu=menu))


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = PolygonsSlots(self.sb)
        self.tk = self.sb.tk

    def messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]


class TestMergeVertices(_SlotsCase):
    def test_tb000_merges_at_the_distance(self):
        self.tk.EditUtils.merge_vertices.return_value = None
        self.slots.tb000(_widget(s002=0.01))
        self.tk.EditUtils.merge_vertices.assert_called_once_with(None, tolerance=0.01)
        self.assertEqual(self.messages(), [])

    def test_tb000_with_nothing_selected_says_so(self):
        self.tk.EditUtils.merge_vertices.return_value = []
        self.slots.tb000(_widget(s002=0.01))
        self.assertIn("Merge Vertices", self.messages()[0])

    def _spin(self):
        spin = mock.MagicMock()
        self.slots.ui = SimpleNamespace(
            tb000=SimpleNamespace(option_box=SimpleNamespace(menu=SimpleNamespace(s002=spin)))
        )
        return spin

    def test_b005_sets_the_measured_distance_and_leaves_component_mode(self):
        spin = self._spin()
        self.tk.Components.adjusted_distance_between_vertices.return_value = 0.5
        self.slots.b005()
        self.tk.Components.adjusted_distance_between_vertices.assert_called_once_with(
            None, None, adjust=0.1, as_percentage=True
        )
        spin.setValue.assert_called_once_with(0.5)
        self.tk.CoreUtils.ensure_object_mode.assert_called_once_with()
        self.assertEqual(self.messages(), [])

    def test_b005_without_two_vertices_resets_and_says_so(self):
        spin = self._spin()
        self.tk.Components.adjusted_distance_between_vertices.return_value = None
        self.slots.b005()
        spin.setValue.assert_called_once_with(PolygonsSlots.MERGE_DISTANCE)
        self.tk.CoreUtils.ensure_object_mode.assert_not_called()
        self.assertIn("two vertices", self.messages()[0])


class TestObjectOperations(_SlotsCase):
    def test_tb002_separate_by_material_groups_and_selects(self):
        self.slots.tb002(_widget(chk021=True, chk022=False, chk024=True))
        self.tk.EditUtils.separate_objects.assert_called_once_with(
            None,
            by_material=True,
            group_by_material=True,
            rename=False,
            uninstance=True,
            select=True,
        )

    def test_tb004_combine_needs_a_selection(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb004(_widget(chk003=False, chk004=False, s003=1.0, chk023=True))
        self.tk.EditUtils.combine_objects.assert_not_called()
        self.assertEqual(self.messages(), [Slots.NOTHING_SELECTED])

    def test_tb004_combine_passes_its_options(self):
        self.tk.CoreUtils.selected_objects.return_value = ["a", "b"]
        self.tk.EditUtils.combine_objects.return_value = "a"
        self.slots.tb004(_widget(chk003=True, chk004=True, s003=5.0, chk023=False))
        self.tk.EditUtils.combine_objects.assert_called_once_with(
            None, group_by_material=True, cluster_by_distance=True, threshold=5.0,
            uninstance=False,
        )
        self.assertEqual(self.messages(), [])

    def test_tb004_one_mesh_is_not_enough(self):
        self.tk.CoreUtils.selected_objects.return_value = ["a"]
        self.tk.EditUtils.combine_objects.return_value = None
        self.slots.tb004(_widget(chk003=False, chk004=False, s003=1.0, chk023=True))
        self.assertIn("two or more", self.messages()[0])

    def test_tb005_one_object_per_face_turns_keep_faces_together_off(self):
        self.tk.CoreUtils.selected_objects.return_value = ["f"]
        self.tk.EditUtils.detach_components.return_value = ["piece"]
        self.slots.tb005(_widget(chk014=True, chk015=True, chk020=True))
        self.tk.EditUtils.detach_components.assert_called_once_with(
            None, duplicate=True, separate=True, keep_faces_together=False
        )
        # the new object(s) read as objects
        self.tk.CoreUtils.ensure_object_mode.assert_called_once_with()

    def test_tb005_in_place_stays_in_component_mode(self):
        self.tk.CoreUtils.selected_objects.return_value = ["f"]
        self.tk.EditUtils.detach_components.return_value = []
        self.slots.tb005(_widget(chk014=False, chk015=False, chk020=False))
        self.tk.CoreUtils.ensure_object_mode.assert_not_called()
        self.assertEqual(self.messages(), [])

    def test_tb005_nothing_detached_says_so(self):
        self.tk.CoreUtils.selected_objects.return_value = ["obj"]
        self.tk.EditUtils.detach_components.return_value = []
        self.slots.tb005(_widget(chk014=True, chk015=True, chk020=False))
        self.assertIn("Detach", self.messages()[0])

    def test_tb008_boolean_passes_the_operation_in_lowercase(self):
        self.tk.EditUtils.boolean_objects.return_value = ["result"]
        self.slots.tb008(_widget(cmb011="Intersection", chk017=True))
        self.tk.EditUtils.boolean_objects.assert_called_once_with(
            None, operation="intersection", interactive=True
        )

    def test_tb008_needs_two_meshes(self):
        self.tk.EditUtils.boolean_objects.return_value = []
        self.slots.tb008(_widget(cmb011="Union", chk017=False))
        self.assertIn("two or more", self.messages()[0])

    def test_tb009_snaps_the_source_onto_the_target(self):
        self.tk.Snap.source_and_target.return_value = (["a"], "b")
        self.tk.Snap.snap_to_closest_vertex.return_value = 8
        self.slots.tb009(_widget(s005=5.0, chk016=True))
        self.tk.Snap.snap_to_closest_vertex.assert_called_once_with(
            "a", "b", tolerance=5.0, freeze_transforms=True
        )
        self.assertEqual(self.messages(), [])

    def test_tb009_needs_exactly_two_meshes(self):
        for pair in (([], None), (["a", "c"], "b")):
            with self.subTest(pair=pair):
                self.sb.message_box.reset_mock()
                self.tk.Snap.source_and_target.return_value = pair
                self.slots.tb009(_widget(s005=5.0, chk016=True))
                self.assertIn("Select two meshes", self.messages()[0])
        self.tk.Snap.snap_to_closest_vertex.assert_not_called()

    def test_tb009_nothing_within_tolerance_says_so(self):
        self.tk.Snap.source_and_target.return_value = (["a"], "b")
        self.tk.Snap.snap_to_closest_vertex.return_value = 0
        self.slots.tb009(_widget(s005=5.0, chk016=False))
        self.assertIn("No vertices", self.messages()[0])


class TestComponentOperations(_SlotsCase):
    def test_tb003_extrude_passes_its_options(self):
        self.slots.tb003(_widget(chk002=False, s004=3, s011=0.25))
        self.tk.Components.extrude.assert_called_once_with(
            None, keep_faces_together=False, divisions=3, thickness=0.25
        )

    def test_tb006_inset_passes_its_options(self):
        self.slots.tb006(_widget(s001=0.2, s010=-0.1, chk018=True))
        self.tk.Components.inset_faces.assert_called_once_with(
            None, offset=0.2, depth=-0.1, individual=True
        )

    def test_tb007_divide_passes_its_options(self):
        self.slots.tb007(_widget(chk008=True, chk009=False, chk010=False, s009=2))
        self.tk.Components.divide_faces.assert_called_once_with(
            None, u=True, v=False, cuts=2, tris=False
        )

    BUTTONS = {
        "b000": "circularize",
        "b001": "fill_holes",
        "b003": "symmetrize",
        "b006": "bridge_edges",
        "b022": "connect_components",
        "b032": "poke_faces",
        "b051": "offset_edge_loops",
        "b053": "edit_edge_flow",
    }

    def test_each_button_runs_its_operation_on_the_selection(self):
        for slot, op in self.BUTTONS.items():
            with self.subTest(slot=slot):
                getattr(self.tk.Components, op).return_value = ["mesh"]
                getattr(self.slots, slot)()
                getattr(self.tk.Components, op).assert_called_once_with(None)
        self.assertEqual(self.messages(), [])

    def test_each_button_says_when_there_is_nothing_to_act_on(self):
        for slot, op in self.BUTTONS.items():
            with self.subTest(slot=slot):
                self.sb.message_box.reset_mock()
                getattr(self.tk.Components, op).return_value = []
                getattr(self.slots, slot)()
                self.assertEqual(len(self.messages()), 1)

    def test_a_refusal_is_shown_as_the_host_words_it(self):
        self.tk.Components.circularize.side_effect = RuntimeError(
            "Circularize needs the LoopTools add-on"
        )
        self.slots.b000()
        self.assertEqual(self.messages(), ["Circularize needs the LoopTools add-on"])

    def test_b009_collapse_reports(self):
        cases = (
            (([], []), "Nothing to collapse"),
            ((["f"], ["e"]), "left as they are"),
            ((["f"], []), None),
        )
        for result, expected in cases:
            with self.subTest(result=result):
                self.sb.message_box.reset_mock()
                self.tk.Components.collapse_components.return_value = result
                self.slots.b009()
                if expected:
                    self.assertIn(expected, self.messages()[0])
                else:
                    self.assertEqual(self.messages(), [])

    def test_b034_wedge_says_when_nothing_wedged(self):
        for result, says in ((0, True), ([], True), (1, False)):
            with self.subTest(result=result):
                self.sb.message_box.reset_mock()
                self.tk.EditUtils.wedge.return_value = result
                self.slots.b034()
                self.assertEqual(bool(self.messages()), says)
        self.tk.EditUtils.wedge.assert_called_with(None)

    def test_b038_reports_the_new_hole_state(self):
        self.tk.Components.toggle_face_holes.return_value = (True, ["f1", "f2"])
        self.slots.b038()
        self.assertIn("assigned as holes", self.messages()[0])
        self.tk.Components.toggle_face_holes.return_value = []
        self.slots.b038()
        self.assertIn("face selection", self.messages()[1])

    def test_b049_slide_shows_a_refusal(self):
        self.tk.Components.slide_edges.side_effect = ValueError("Slide needs a mesh.")
        self.slots.b049()
        self.tk.Components.slide_edges.assert_called_once_with(None)
        self.assertEqual(self.messages(), ["Slide needs a mesh."])

    def test_target_weld_at_the_target_or_the_center(self):
        self.slots.b043()
        self.tk.TargetWeld.activate.assert_called_with(merge_to_center=False)
        self.slots.b008()
        self.tk.TargetWeld.activate.assert_called_with(merge_to_center=True)
        self.tk.TargetWeld.activate.side_effect = RuntimeError("No 3D viewport")
        self.slots.b043()
        self.assertEqual(self.messages(), ["No 3D viewport"])


class TestToolsAndWindows(_SlotsCase):
    def test_viewport_tools_by_their_shared_names(self):
        for slot, tool in (("b012", "Multi-Cut"), ("b047", "Insert Edgeloop")):
            with self.subTest(slot=slot):
                getattr(self.slots, slot)()
                self.tk.UiUtils.set_tool.assert_called_with(tool)
                self.assertIn(tool, self.messages()[-1])

    def test_b007_b011_open_the_tool_windows(self):
        self.slots.b007()
        self.slots.b011()
        self.assertEqual(
            self.sb.handlers.marking_menu.show.call_args_list,
            [mock.call("bridge"), mock.call("bevel")],
        )


class TestOptionBoxes(_SlotsCase):
    def _init(self, name):
        created = {}
        widget = mock.MagicMock()
        widget.option_box.menu.add.side_effect = lambda *a, **k: created.setdefault(
            k.get("setObjectName"), mock.MagicMock()
        )
        getattr(self.slots, f"{name}_init")(widget)
        return created

    def test_freeze_transforms_is_maya_s(self):
        created = self._init("tb009")
        created["chk016"].setProperty.assert_called_once_with("requires", "maya")
        self.sb.apply_visibility_policy.assert_any_call(created["chk016"])
        created["s005"].setProperty.assert_not_called()

    def test_divide_s_one_way_splits_are_maya_s(self):
        created = self._init("tb007")
        for name in ("chk008", "chk009"):
            created[name].setProperty.assert_called_once_with("requires", "maya")
        for name in ("chk010", "s009"):
            created[name].setProperty.assert_not_called()

    def test_inset_default_is_two_centimetres_in_working_units(self):
        self.tk.Units.convert.return_value = 0.02
        self._init("tb006")
        self.tk.Units.convert.assert_called_once_with(2.0, "cm", "working")

    def test_boolean_keeps_maya_s_item_order(self):
        widget = mock.MagicMock()
        self.slots.tb008_init(widget)
        first = widget.option_box.menu.add.call_args_list[0]
        self.assertEqual(first.kwargs["addItems"], ["Union", "Difference", "Intersection"])
        self.assertEqual(first.kwargs["setCurrentText"], "Difference")


# --------------------------------------------------------------------------- in Maya
@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class _MayaCase(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.mtk = maya_module("mayatk")
        self.cmds.file(new=True, force=True)
        self.sb.tk = self.mtk
        self.tk = self.mtk
        self.addCleanup(self.cmds.file, new=True, force=True)

    def clear_mask(self):
        """The selection-type mask as multi-component mode leaves it (no type):
        the operations must route on the selection itself. Restored after."""
        mask = ("vertex", "edge", "facet")
        saved = {m: self.cmds.selectType(q=True, **{m: True}) for m in mask}
        self.addCleanup(
            lambda: [
                self.cmds.selectType(**{m: on}) for m, on in saved.items() if on is not None
            ]
        )
        self.cmds.selectType(**{m: False for m in mask})


class TestExtrudeInMaya(_MayaCase):
    OPTION_VARS = (
        "polyKeepFacetsGrouped",
        "polyExtrudeFaceDivisions",
        "polyExtrudeEdgeDivisions",
        "polyExtrudeVertexDivisions",
        "polyExtrudeFaceThickness",
        "polyExtrudeEdgeThickness",
    )

    def setUp(self):
        super().setUp()
        cmds = self.cmds
        saved = {n: cmds.optionVar(q=n) if cmds.optionVar(exists=n) else None for n in self.OPTION_VARS}

        def restore():
            for n, v in saved.items():
                if v is None:
                    cmds.optionVar(remove=n)
                elif isinstance(v, float):
                    cmds.optionVar(floatValue=(n, v))
                else:
                    cmds.optionVar(intValue=(n, v))

        self.addCleanup(restore)
        # Maya's own Extrude settings: the slot must neither obey nor clobber them.
        for n in self.OPTION_VARS[:4]:
            cmds.optionVar(intValue=(n, 1))

    def _extrude(self, *items, keep_together=False, divisions=3, thickness=0.0):
        self.cmds.select(items)
        self.clear_mask()
        self.slots.tb003(_widget(chk002=keep_together, s004=divisions, s011=thickness))

    def _node(self, node_type):
        nodes = self.cmds.ls(type=node_type) or []
        self.assertEqual(len(nodes), 1, f"expected one {node_type}, got {nodes}")
        return nodes[0]

    def test_no_selection_warns(self):
        self.cmds.select(clear=True)
        self.slots.tb003(_widget(chk002=True, s004=1, s011=0.0))
        self.assertTrue(self.messages())
        self.assertFalse(self.cmds.ls(type="polyExtrudeFace"))

    def test_a_face_uses_the_option_box_values(self):
        plane = self.cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(f"{plane}.f[0]", keep_together=False, divisions=3, thickness=0.5)
        node = self._node("polyExtrudeFace")
        self.assertFalse(self.cmds.getAttr(f"{node}.keepFacesTogether"))
        self.assertEqual(self.cmds.getAttr(f"{node}.divisions"), 3)
        self.assertAlmostEqual(self.cmds.getAttr(f"{node}.thickness"), 0.5, places=4)

    def test_an_edge_and_a_vertex_extrude_under_any_mask(self):
        cube = self.cmds.polyCube()[0]
        self._extrude(f"{cube}.e[0]", divisions=2)
        self.assertEqual(self.cmds.getAttr(f"{self._node('polyExtrudeEdge')}.divisions"), 2)
        self._extrude(f"{cube}.vtx[0]", divisions=2)
        self.assertEqual(self.cmds.getAttr(f"{self._node('polyExtrudeVertex')}.divisions"), 2)

    def test_an_object_extrudes_its_faces(self):
        plane = self.cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(plane)
        self._node("polyExtrudeFace")

    def test_faces_on_two_objects_extrude_each(self):
        a = self.cmds.polyPlane(sx=1, sy=1)[0]
        b = self.cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(f"{a}.f[0]", f"{b}.f[0]", keep_together=False)
        self.assertEqual(len(self.cmds.ls(type="polyExtrudeFace") or []), 2)

    def test_maya_s_extrude_settings_are_restored(self):
        self.cmds.optionVar(remove="polyExtrudeVertexDivisions")  # absent stays absent
        plane = self.cmds.polyPlane(sx=1, sy=1)[0]
        self._extrude(f"{plane}.f[0]", keep_together=False, divisions=3)
        for n in self.OPTION_VARS[:3]:
            self.assertEqual(self.cmds.optionVar(q=n), 1, n)
        self.assertFalse(self.cmds.optionVar(exists="polyExtrudeVertexDivisions"))


class TestDivideFacetInMaya(_MayaCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        patcher = mock.patch.object(
            self.cmds, "polySubdivideFacet", lambda *a, **kw: self.calls.append(kw)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cube = self.cmds.polyCube(name="dv_facet")[0]

    def _divide(self, u, v, tris, cuts=1):
        self.cmds.select(f"{self.cube}.f[0]")
        self.slots.tb007(_widget(chk008=u, chk009=v, chk010=tris, s009=cuts))
        self.assertEqual(len(self.calls), 1)
        return self.calls[0]

    def test_no_face_selection_warns(self):
        self.cmds.select(clear=True)
        self.slots.tb007(_widget(chk008=True, chk009=True, chk010=False, s009=1))
        self.assertTrue(self.messages())
        self.assertEqual(self.calls, [])

    def test_u_and_v_subdivide_once_into_quads(self):
        kw = self._divide(True, True, False)
        self.assertEqual(
            (kw["divisions"], kw["subdMethod"], kw["divisionsU"], kw["divisionsV"], kw["mode"]),
            (1, 0, 0, 0, 0),
        )

    def test_one_way_splits_in_two(self):
        kw = self._divide(True, False, False)
        self.assertEqual((kw["divisionsU"], kw["divisionsV"]), (2, 0))
        self.calls.clear()
        kw = self._divide(False, True, False)
        self.assertEqual((kw["divisionsU"], kw["divisionsV"]), (0, 2))

    def test_tris(self):
        kw = self._divide(False, False, True)
        self.assertEqual((kw["mode"], kw["divisions"], kw["subdMethod"]), (1, 1, 0))

    def test_cuts_divide_linearly(self):
        kw = self._divide(True, True, False, cuts=2)
        self.assertEqual(
            (kw["subdMethod"], kw["divisionsU"], kw["divisionsV"]), (1, 3, 3)
        )


class TestBooleanInMaya(_MayaCase):
    def setUp(self):
        super().setUp()
        macro = mock.patch.object(self.mtk.Macros, "m_boolean", return_value="result")
        self.macro = macro.start()
        self.addCleanup(macro.stop)
        mel = maya_module("maya.mel")
        self.mel_calls = []
        evaluate = mock.patch.object(mel, "eval", lambda s: self.mel_calls.append(s))
        evaluate.start()
        self.addCleanup(evaluate.stop)

    def _two_cubes(self):
        a = self.cmds.polyCube(name="bool_a")[0]
        b = self.cmds.polyCube(name="bool_b")[0]
        self.cmds.select([a, b])
        return a, b

    def test_no_selection_warns(self):
        self.cmds.select(clear=True)
        self.slots.tb008(_widget(cmb011="Union", chk017=False))
        self.assertTrue(self.messages())
        self.macro.assert_not_called()

    def test_baked_operations_run_the_macro(self):
        for label in ("Union", "Difference", "Intersection"):
            with self.subTest(label=label):
                self.macro.reset_mock()
                a, b = self._two_cubes()
                self.slots.tb008(_widget(cmb011=label, chk017=False))
                self.macro.assert_called_once()
                self.assertEqual(self.macro.call_args.kwargs, {"operation": label.lower()})
                self.assertEqual(set(self.macro.call_args.args[0]), {a, b})

    def test_interactive_runs_maya_s_boolean_tool(self):
        for label in ("Union", "Difference", "Intersection"):
            with self.subTest(label=label):
                self._two_cubes()
                self.slots.tb008(_widget(cmb011=label, chk017=True))
                self.assertIn(f"PolygonBoolean{label}", self.mel_calls)
        self.macro.assert_not_called()


class TestSnapInMaya(_MayaCase):
    def setUp(self):
        super().setUp()
        snap = mock.patch.object(self.mtk.Snap, "snap_to_closest_vertex", return_value=8)
        self.snap = snap.start()
        self.addCleanup(snap.stop)

    def test_the_first_selected_snaps_onto_the_second(self):
        a = self.cmds.polyCube(name="sn_a")[0]
        b = self.cmds.polyCube(name="sn_b")[0]
        self.cmds.select([a, b])
        self.slots.tb009(_widget(s005=5.0, chk016=True))
        self.snap.assert_called_once_with(a, b, tolerance=5.0, freeze_transforms=True)

    def test_one_object_warns(self):
        self.cmds.select(self.cmds.polyCube(name="sn_one")[0])
        self.slots.tb009(_widget(s005=5.0, chk016=True))
        self.assertTrue(self.messages())
        self.snap.assert_not_called()


class TestSetDistanceInMaya(_MayaCase):
    def setUp(self):
        super().setUp()
        self.spin = mock.MagicMock()
        self.slots.ui = SimpleNamespace(
            tb000=SimpleNamespace(option_box=SimpleNamespace(menu=SimpleNamespace(s002=self.spin)))
        )

    def test_two_vertices_set_their_gap_plus_a_tenth_percent(self):
        plane = self.cmds.polyPlane(sx=1, sy=1, w=2, h=2)[0]
        self.cmds.select([f"{plane}.vtx[0]", f"{plane}.vtx[1]"])
        self.slots.b005()
        (value,), _ = self.spin.setValue.call_args
        self.assertAlmostEqual(value, 2.0 * 1.001, places=4)

    def test_anything_else_resets_to_the_default(self):
        self.cmds.select(clear=True)
        self.slots.b005()
        self.spin.setValue.assert_called_once_with(PolygonsSlots.MERGE_DISTANCE)
        self.assertTrue(self.messages())


class TestBridgeInMaya(_MayaCase):
    def test_no_edge_selection_warns(self):
        self.cmds.select(clear=True)
        self.slots.b006()
        self.assertTrue(self.messages())

    def test_edges_sharing_a_vertex_fall_back_to_the_connected_bridge(self):
        cube = self.cmds.polyCube(name="brg_cube")[0]
        self.cmds.select(f"{cube}.e[0]")
        fallback = mock.patch.object(self.mtk.Components, "bridge_connected_edges")
        connected = fallback.start()
        self.addCleanup(fallback.stop)

        def refuse(*a, **kw):
            raise RuntimeError("bridge failed")

        with mock.patch.object(self.cmds, "polyBridgeEdge", refuse):
            self.slots.b006()
        connected.assert_called_once()


class TestAssignHoleInMaya(_MayaCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        self.current = False

        def fake_hole(*a, **kw):
            self.calls.append(kw)
            return self.current if kw.get("q") else None

        patcher = mock.patch.object(self.cmds, "polyHole", fake_hole)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _assigned(self):
        return [kw["assignHole"] for kw in self.calls if not kw.get("q")]

    def test_no_face_selection_warns(self):
        self.cmds.select(clear=True)
        self.slots.b038()
        self.assertTrue(self.messages())
        self.assertEqual(self.calls, [])

    def test_assigns_when_not_a_hole_and_restores_when_it_is(self):
        cube = self.cmds.polyCube(name="ah_cube")[0]
        self.cmds.select(f"{cube}.f[0]")
        self.slots.b038()
        self.current = True
        self.cmds.select(f"{cube}.f[0]")
        self.slots.b038()
        self.assertEqual(self._assigned(), [True, False])


class TestCollapseInMaya(_MayaCase):
    """b009 collapses each selected face to its own point; edges and vertices
    merge to their shared center. Routed on the selection, not the mask."""

    def setUp(self):
        super().setUp()
        self.plane = self.cmds.polyPlane(sx=3, sy=3)[0]  # 16 verts
        history = self.cmds.constructionHistory(q=True, toggle=True)
        self.addCleanup(self.cmds.constructionHistory, toggle=history)

    def _points(self, mesh):
        pts = self.cmds.xform(f"{mesh}.vtx[*]", q=True, os=True, t=True)
        return sorted(
            tuple(round(c, 4) for c in pts[i : i + 3]) for i in range(0, len(pts), 3)
        )

    def _collapse(self, *components):
        self.cmds.select([f"{self.plane}.{c}" for c in components])
        self.clear_mask()
        self.slots.b009()
        return self.cmds.polyEvaluate(self.plane, vertex=True)

    def test_faces_collapse_each_to_their_own_point(self):
        self.assertEqual(self._collapse("f[0]", "f[8]"), 10)

    def test_edges_merge_to_their_center(self):
        self.assertEqual(self._collapse("e[0]"), 15)

    def test_faces_on_two_instances_collapse_as_one_shape(self):
        ref = self.cmds.polyPlane(sx=3, sy=3)[0]
        self.cmds.polyCollapseFacet([f"{ref}.f[0]", f"{ref}.f[8]"])
        twin = self.cmds.instance(self.plane)[0]
        self.cmds.select([f"{self.plane}.f[0]", f"{twin}.f[0]", f"{twin}.f[8]"])
        self.clear_mask()
        self.slots.b009()
        self.assertEqual(self._points(self.plane), self._points(ref))

    def test_an_object_selection_is_refused(self):
        self.cmds.select(self.plane)
        self.slots.b009()
        self.assertTrue(self.messages())
        self.assertEqual(self.cmds.polyEvaluate(self.plane, vertex=True), 16)

    def test_edges_beside_faces_are_named_not_dropped_silently(self):
        self.assertEqual(self._collapse("f[0]", "e[20]"), 13)
        self.assertTrue(self.messages())

    def test_one_undo_restores_every_object(self):
        other = self.cmds.polyPlane(sx=3, sy=3)[0]
        self.cmds.select([f"{self.plane}.f[0]", f"{other}.f[4]"])
        self.clear_mask()
        self.slots.b009()
        self.cmds.undo()
        self.assertEqual(self.cmds.polyEvaluate(self.plane, vertex=True), 16)
        self.assertEqual(self.cmds.polyEvaluate(other, vertex=True), 16)


if __name__ == "__main__":
    unittest.main()
