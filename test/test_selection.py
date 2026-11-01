#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.selection, the one Selection Slots class.

It reaches its host only through ``self.tk``: a fake toolkit (a MagicMock
switchboard's ``tk``) records what each slot asks of it (plain pytest), and in
Maya the same class drives the real ``mtk`` (``run_tests.py --in-maya``). Pinned
here: each slot's call and arguments; how it words an empty result or a
refusal; the Convert To rows and the constraint row following what the host
serves (Maya's persistent constraints, Blender's one-shots); the mirrored
widgets seeding from the host without firing; the static tables against the
``.ui``; and in Maya, Convert To, the constraint flags and Select Similar on real
geometry. The operations themselves are tested in mayatk and blendertk.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.selection import SelectionSlots

#: Maya's conversions, as mayatk's Selection lists them.
MAYA_CONVERSIONS = [
    "vertices", "vertex_faces", "vertex_perimeter", "edges", "edge_loop", "edge_ring",
    "contained_edges", "edge_perimeter", "border_edges", "faces", "face_path",
    "contained_faces", "face_perimeter", "uvs", "uv_shell", "uv_shell_border",
    "uv_perimeter", "uv_edge_loop", "shell", "shell_border",
]
#: Blender's: no vertex-face or UV component.
BLENDER_CONVERSIONS = [c for c in MAYA_CONVERSIONS if c not in ("vertex_faces", "uvs")]


def _value(v):
    """A widget answering isChecked(), value() and currentData()."""
    return SimpleNamespace(isChecked=lambda: v, value=lambda: v, currentData=lambda: v)


def _widget(**values):
    """An option-box widget whose menu holds *values* by objectName."""
    menu = SimpleNamespace(**{name: _value(v) for name, v in values.items()})
    return SimpleNamespace(option_box=SimpleNamespace(menu=menu))


class _Row:
    """A list row as the list handlers see it: label, objectName, optional sublist."""

    def __init__(self, label, name="", members=()):
        self._label, self._name = label, name
        items = list(members)
        self.sublist = SimpleNamespace(get_items=lambda: items) if items else None

    def item_text(self):
        return self._label

    def objectName(self):
        return self._name


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.slots = SelectionSlots(self.sb)
        self.tk = self.sb.tk
        self.tk.Selection.get_conversion_types.return_value = list(MAYA_CONVERSIONS)

    def messages(self):
        return [c.args[0] for c in self.sb.message_box.call_args_list]

    def set_scope(self, scope="all", mode="replace"):
        menu = SimpleNamespace(cmb_bytype_scope=_value(scope), cmb_bytype_mode=_value(mode))
        self.slots.submenu = SimpleNamespace(tb004=SimpleNamespace(menu=menu))


class TestSelectByType(_SlotsCase):
    def test_a_leaf_selects_by_type_in_the_scope_and_mode(self):
        self.set_scope("visible", "add")
        self.tk.Selection.select_by_type.return_value = ["cam"]
        self.slots.list000(_Row("Cameras"))
        self.tk.Selection.select_by_type.assert_called_once_with(
            "Cameras", None, mode="add", scope="visible"
        )
        self.assertEqual(self.messages(), [])

    def test_unset_combos_mean_all_and_replace(self):
        self.set_scope(None, None)
        self.slots.list000(_Row("Cameras"))
        self.tk.Selection.select_by_type.assert_called_once_with(
            "Cameras", None, mode="replace", scope="all"
        )

    def test_no_match_says_so(self):
        self.set_scope()
        self.tk.Selection.select_by_type.return_value = []
        self.slots.list000(_Row("Cameras"))
        self.assertIn("Cameras", self.messages()[0])

    def test_headers_are_navigation_only(self):
        self.set_scope()
        self.slots.list000(_Row("Geometry", members=["Polygon Meshes"]))
        self.tk.Selection.select_by_type.assert_not_called()

    def test_the_settings_row_opens_its_menu(self):
        self.set_scope()
        row = _Row("Settings", name="tb004")
        row.menu = mock.MagicMock()
        self.slots.list000(row)
        row.menu.show_as_popup.assert_called_once()
        self.tk.Selection.select_by_type.assert_not_called()


class TestReorderSelection(_SlotsCase):
    def _combo(self, reverse=False):
        widget = _widget(chk009=reverse)
        widget.items = [label for label, _ in SelectionSlots._REORDER_METHODS]
        return widget

    def test_every_row_has_its_own_method(self):
        widget = self._combo()
        methods = []
        for index in range(len(widget.items)):
            self.slots.cmb001(index, widget)
            methods.append(self.tk.Selection.reorder_selection.call_args.kwargs["method"])
        self.assertEqual(methods[0], "name")
        self.assertEqual(len(set(methods)), len(methods), "two rows share a method")

    def test_reverse_and_report(self):
        self.tk.Selection.reorder_selection.return_value = ["a", "b"]
        self.slots.cmb001(2, self._combo(reverse=True))
        self.tk.Selection.reorder_selection.assert_called_once_with(
            None, method="x", reverse=True
        )
        self.assertIn("(reversed)", self.messages()[0])

    def test_nothing_selected_says_so(self):
        self.tk.Selection.reorder_selection.return_value = []
        self.slots.cmb001(0, self._combo())
        self.assertIn("No objects selected", self.messages()[0])


class TestConvertTo(_SlotsCase):
    def test_the_table_and_the_groups_partition_the_rows(self):
        groups = SelectionSlots._CONVERT_TO_GROUPS
        rows = list(groups) + [m for members in groups.values() for m in members]
        self.assertEqual(sorted(rows), sorted(SelectionSlots._CONVERT_TO))
        self.assertEqual(len(rows), len(set(rows)), "a row appears in two places")
        self.assertEqual(list(SelectionSlots._CONVERT_TO.values()), MAYA_CONVERSIONS)

    def test_rows_follow_the_host_s_conversions(self):
        self.tk.Selection.get_conversion_types.return_value = list(BLENDER_CONVERSIONS)
        rows = self.slots._convert_to_rows()
        self.assertNotIn("Vertex Faces", rows)
        self.assertNotIn("UV's", rows)
        self.assertIn("UV Shell", rows)

    def test_a_category_row_with_a_sublist_still_converts(self):
        self.slots.list001(_Row("Verts", members=["Vertex Faces"]))
        self.tk.Selection.convert_selection.assert_called_once_with("vertices")

    def test_the_root_and_a_row_the_host_lacks_are_navigation_only(self):
        self.tk.Selection.get_conversion_types.return_value = list(BLENDER_CONVERSIONS)
        self.slots.list001(_Row("Convert To", members=["Verts"]))
        self.slots.list001(_Row("UV's", members=["UV Shell"]))
        self.tk.Selection.convert_selection.assert_not_called()

    def test_nothing_to_convert_says_so(self):
        self.tk.Selection.convert_selection.return_value = []
        self.slots.list001(_Row("Border Edges"))
        self.assertIn("Nothing to convert", self.messages()[0])


class TestConstraintRow(_SlotsCase):
    def _button(self, name, checked=False, checkable=True):
        button = mock.MagicMock()
        button.objectName.return_value = name
        button.isChecked.return_value = checked
        button.isCheckable.return_value = checkable
        button.blockSignals.return_value = False
        return button

    def test_a_persistent_host_makes_toggles_seeded_from_it(self):
        self.tk.Selection.get_selection_constraints.return_value = ["shell"]
        shell, angle = self._button("b006"), self._button("b002")
        self.slots.b006_init(shell)
        self.slots.b002_init(angle)
        shell.setCheckable.assert_called_once_with(True)
        shell.setChecked.assert_called_once_with(True)
        angle.setChecked.assert_called_once_with(False)
        self.assertFalse(shell.restore_state)
        self.assertIn("Toggle", shell.setToolTip.call_args.args[0])
        self.assertEqual(self.messages(), [])

    def test_a_one_shot_host_makes_plain_buttons(self):
        self.tk.Selection.get_selection_constraints.return_value = None
        loop = self._button("b004")
        self.slots.b004_init(loop)
        loop.setCheckable.assert_called_once_with(False)
        loop.setChecked.assert_not_called()
        self.assertIn("One-shot", loop.setToolTip.call_args.args[0])

    def test_a_toggle_sends_its_state_and_reports_what_is_on(self):
        self.tk.Selection.set_selection_constraint.return_value = ["angle", "edge_loop"]
        self.slots.b004(self._button("b004", checked=True))
        self.tk.Selection.set_selection_constraint.assert_called_once_with("edge_loop", True)
        self.assertEqual(
            self.messages(), ["Selection Constraints: <hl>Angle, Edge Loop</hl>"]
        )

    def test_all_off_reports_off(self):
        self.tk.Selection.set_selection_constraint.return_value = []
        self.slots.b002(self._button("b002", checked=False))
        self.assertIn("OFF", self.messages()[0])

    def test_a_one_shot_press_applies_and_says_nothing(self):
        self.tk.Selection.set_selection_constraint.return_value = None
        self.slots.b005(self._button("b005", checkable=False))
        self.tk.Selection.set_selection_constraint.assert_called_once_with("edge_ring", True)
        self.assertEqual(self.messages(), [])

    def test_a_refusal_is_shown(self):
        self.tk.Selection.set_selection_constraint.side_effect = ValueError("Select a mesh.")
        self.slots.b006(self._button("b006", checkable=False))
        self.assertEqual(self.messages(), ["Select a mesh."])

    def test_the_row_matches_the_ui(self):
        """Every declared constraint button has a slot entry and vice versa."""
        ui = Path(__file__).resolve().parent.parent / "tentacle" / "ui" / "selection.ui"
        names = [
            w.get("name")
            for w in ET.parse(ui).iter("widget")
            if w.get("class") == "PushButton"
            and w.get("name", "").startswith("b00")
            and w.get("name") != "b001"
        ]
        self.assertEqual(names, list(SelectionSlots._CONSTRAINT_BUTTONS))


class TestViewportPicking(_SlotsCase):
    def _box(self):
        box = mock.MagicMock()
        box.blockSignals.return_value = False
        return box

    def test_ignore_backfacing_seeds_from_the_host(self):
        for state in (True, False):
            with self.subTest(state=state):
                self.tk.Selection.get_ignore_backfacing.return_value = state
                box = self._box()
                self.slots.chk004_init(box)
                box.setChecked.assert_called_once_with(state)
                self.assertFalse(box.restore_state)

    def test_ignore_backfacing_without_state_keeps_the_default(self):
        self.tk.Selection.get_ignore_backfacing.return_value = None
        box = self._box()
        self.slots.chk004_init(box)
        box.setChecked.assert_not_called()
        self.assertFalse(box.restore_state)

    def test_ignore_backfacing_sets_the_host(self):
        self.slots.chk004(2, None)  # Qt.Checked
        self.tk.Selection.set_ignore_backfacing.assert_called_once_with(True)
        self.assertIn("ON", self.messages()[0])

    def test_select_style_seeds_only_the_active_tool_s_box(self):
        self.tk.UiUtils.current_tool.return_value = "Lasso Select"
        boxes = {n: self._box() for n in ("chk005", "chk006", "chk007")}
        for name, box in boxes.items():
            box.objectName.return_value = name
            getattr(self.slots, f"{name}_init")(box)
            self.assertFalse(box.restore_state, name)
        boxes["chk006"].setChecked.assert_called_once_with(True)
        boxes["chk005"].setChecked.assert_not_called()
        boxes["chk007"].setChecked.assert_not_called()
        self.tk.UiUtils.set_tool.assert_not_called()
        self.assertEqual(self.messages(), [])

    def test_select_style_activates_its_tool(self):
        for name, tool in SelectionSlots._SELECT_STYLES.items():
            with self.subTest(name=name):
                box = self._box()
                box.objectName.return_value = name
                getattr(self.slots, name)(True, box)
                self.tk.UiUtils.set_tool.assert_called_with(tool)
        self.tk.UiUtils.set_tool.reset_mock()
        box = self._box()
        box.objectName.return_value = "chk005"
        self.slots.chk005(False, box)  # unchecking sets nothing
        self.tk.UiUtils.set_tool.assert_not_called()


class TestButtons(_SlotsCase):
    def test_b001_toggle_selectability_reports(self):
        self.tk.Selection.toggle_selectability.return_value = (False, ["a", "b"])
        self.slots.b001()
        self.assertEqual(self.messages(), ["Selectability <hl>OFF</hl> (2 object(s))."])
        self.tk.Selection.toggle_selectability.return_value = []
        self.slots.b001()
        self.assertIn("needs a selection", self.messages()[1])

    def test_tb000_sends_the_checked_path_and_step(self):
        for name, path in (("chk000", "edge_ring"), ("chk021", "edge_loop_path"),
                           ("chk010", "border_edges")):
            with self.subTest(name=name):
                values = {n: n == name for n in ("chk000", "chk001", "chk002", "chk010", "chk021")}
                self.slots.tb000(_widget(s003=3, **values))
                self.tk.Selection.select_edge_path.assert_called_with(None, path=path, step=3)

    def test_tb002_island_sends_the_ranges_and_delimiters(self):
        self.slots.tb002(_widget(
            s002=0.1, s004=0.2, s005=0.3, chk022=True, chk_island_sharp=False,
            chk_island_normal=False, chk_island_material=True, chk_island_uv=False,
        ))
        self.tk.Selection.select_island.assert_called_once_with(
            None, range_x=0.1, range_y=0.2, range_z=0.3, delimit={"SEAM", "MATERIAL"}
        )

    def test_tb002_delimiters_are_blender_s(self):
        created = {}
        widget = mock.MagicMock()
        widget.option_box.menu.add.side_effect = lambda *a, **k: created.setdefault(
            k.get("setObjectName"), mock.MagicMock()
        )
        self.slots.tb002_init(widget)
        for name in SelectionSlots._ISLAND_DELIMIT:
            created[name].setProperty.assert_called_once_with("requires", "blender")
        for name in ("chk003", "s002", "s004", "s005"):
            created[name].setProperty.assert_not_called()

    def test_tb003_reports_no_edge_in_range(self):
        self.tk.EditUtils.select_edges_by_angle.return_value = 0
        self.slots.tb003(_widget(s006=70, s007=160))
        self.tk.EditUtils.select_edges_by_angle.assert_called_once_with(
            None, low_angle=70, high_angle=160
        )
        self.assertIn("No edges", self.messages()[0])

    def test_cmb002_seeds_the_rig_picking_mode_from_the_host(self):
        self.tk.Selection.get_rig_selection_mode.return_value = "meshes_only"
        combo = mock.MagicMock()
        combo.blockSignals.return_value = False
        self.slots.cmb002_init(combo)
        combo.setCurrentIndex.assert_called_once_with(2)
        self.assertFalse(combo.restore_state)


class TestSelectSimilar(_SlotsCase):
    def _run(self, result, **checked):
        self.tk.CoreUtils.selected_objects.return_value = ["ref"]
        self.tk.Selection.select_similar.return_value = result
        values = {name: checked.get(metric, default)
                  for name, _, metric, default, _ in SelectionSlots._SIMILAR_METRICS}
        self.slots.tb001(_widget(s000=0.5, chk020=False, **values))

    def test_no_reference_asks_for_one(self):
        self.tk.CoreUtils.selected_objects.return_value = []
        self.slots.tb001(_widget(s000=0.0))
        self.tk.Selection.select_similar.assert_not_called()
        self.assertIn("needs a reference", self.messages()[0])

    def test_sends_the_metrics_by_name(self):
        self._run(("objects", ["twin"]))
        kwargs = self.tk.Selection.select_similar.call_args.kwargs
        self.assertEqual(kwargs["tolerance"], 0.5)
        self.assertTrue(kwargs["world_area"])
        self.assertFalse(kwargs["bounding_box"])
        self.assertEqual(self.messages(), [])

    def test_no_object_match_names_the_compared_metrics(self):
        self._run(("objects", []), triangle=False)
        message = self.messages()[0]
        for label in ("Vertex", "Edge", "Face", "World Area"):
            self.assertIn(label, message)
        self.assertNotIn("Triangle", message)

    def test_no_uv_shell_match_says_so(self):
        self._run(("uv_shells", []))
        self.assertIn("no other UV shell", self.messages()[0])

    def test_an_unsupported_component_is_the_host_s_words(self):
        self.tk.CoreUtils.selected_objects.return_value = ["e"]
        self.tk.Selection.select_similar.side_effect = ValueError("not edges")
        self.slots.tb001(_widget(s000=0.0, chk020=False, **{
            name: False for name, *_ in SelectionSlots._SIMILAR_METRICS}))
        self.assertEqual(self.messages(), ["not edges"])


# --------------------------------------------------------------------------- in Maya
@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class _MayaCase(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.addCleanup(self.cmds.file, new=True, force=True)
        self.sb.tk = self.tk = maya_module("mayatk")


class TestConvertToInMaya(_MayaCase):
    def test_maya_serves_every_row(self):
        self.assertEqual(self.tk.Selection.get_conversion_types(), MAYA_CONVERSIONS)

    def test_border_edges_selects_the_naked_edges_of_an_open_plane(self):
        plane = self.cmds.polyPlane(sx=3, sy=3, w=2, h=2, ch=False)[0]
        self.cmds.select(f"{plane}.f[0:8]")
        self.slots.list001(_Row("Border Edges"))
        self.assertEqual(len(self.cmds.ls(sl=True, flatten=True) or []), 12)
        self.assertEqual(self.messages(), [])

    def test_border_edges_with_nothing_selected_warns(self):
        self.cmds.select(clear=True)
        self.slots.list001(_Row("Border Edges"))
        self.assertTrue(self.messages())

    def test_edge_loop_selects_the_full_border_loop(self):
        plane = self.cmds.polyPlane(sx=4, sy=4, w=4, h=4, ch=False)[0]
        self.cmds.select(f"{plane}.e[0]")
        self.slots.list001(_Row("Edge Loop"))
        self.assertEqual(len(self.cmds.ls(sl=True, flatten=True) or []), 16)


class TestConstraintsInMaya(_MayaCase):
    _ALL_OFF = dict(
        border=False, borderPropagation=False, shell=False, anglePropagation=False,
        loopPropagation=False, ringPropagation=False, uvEdgeLoopPropagation=False,
    )

    def setUp(self):
        super().setUp()
        self.cmds.polySelectConstraint(**self._ALL_OFF)
        self.addCleanup(self.cmds.polySelectConstraint, **self._ALL_OFF)

    def _flag(self, name):
        return bool(self.cmds.polySelectConstraint(q=True, **{name: True}))

    def _button(self, name, checked):
        button = mock.MagicMock()
        button.objectName.return_value = name
        button.isChecked.return_value = checked
        button.isCheckable.return_value = True
        button.blockSignals.return_value = False
        return button

    def test_two_constraints_can_be_on_at_once(self):
        self.slots.b002(self._button("b002", True))
        self.slots.b004(self._button("b004", True))
        self.assertTrue(self._flag("anglePropagation"))
        self.assertTrue(self._flag("loopPropagation"), "Edge Loop cleared Angle's flag")
        self.assertIn("Angle, Edge Loop", self.messages()[-1])

    def test_unchecking_clears_only_its_own_flags(self):
        self.slots.b002(self._button("b002", True))
        self.slots.b003(self._button("b003", True))
        self.slots.b003(self._button("b003", False))
        self.assertFalse(self._flag("border"))
        self.assertFalse(self._flag("borderPropagation"))
        self.assertTrue(self._flag("anglePropagation"), "unchecking Border cleared Angle")

    def test_the_row_seeds_from_the_live_flag(self):
        self.cmds.polySelectConstraint(shell=True)
        shell, angle = self._button("b006", False), self._button("b002", True)
        self.slots.b006_init(shell)
        self.slots.b002_init(angle)
        shell.setChecked.assert_called_once_with(True)
        angle.setChecked.assert_called_once_with(False)


class TestSelectSimilarInMaya(_MayaCase):
    """tb001 reports when it matches nothing: a no-match is invisible from the UI
    (with Include Original off it silently clears the selection, with it on it
    re-selects what was selected), which read as a dead button."""

    def _widget(self, tolerance=0.0, inc_orig=False, **checked):
        values = {name: checked.get(metric, default)
                  for name, _, metric, default, _ in SelectionSlots._SIMILAR_METRICS}
        return _widget(s000=tolerance, chk020=inc_orig, **values)

    def test_no_selection_asks_for_a_reference(self):
        self.cmds.polyCube(name="similar_lonely")
        self.cmds.select(clear=True)
        self.slots.tb001(self._widget())
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("reference", self.messages()[0])

    def test_no_match_names_the_compared_metrics(self):
        cube = self.cmds.polyCube(name="similar_cube", w=2, h=2, d=2)[0]
        self.cmds.polySphere(name="similar_sphere", r=9)
        self.cmds.select(cube)
        self.slots.tb001(self._widget(vertex=True, edge=True, face=True, world_area=True))
        self.assertEqual(len(self.messages()), 1)
        for label in ("Vertex", "Edge", "Face", "World Area"):
            self.assertIn(label, self.messages()[0])

    def test_no_match_reported_even_with_include_original(self):
        cube = self.cmds.polyCube(name="similar_solo", w=2, h=2, d=2)[0]
        self.cmds.polySphere(name="similar_other", r=9)
        self.cmds.select(cube)
        self.slots.tb001(self._widget(inc_orig=True))
        self.assertIn("no matches", self.messages()[0])

    def test_a_moved_and_rotated_duplicate_matches_silently(self):
        cube = self.cmds.polyCube(name="similar_src", w=2, h=2, d=2)[0]
        twin = self.cmds.duplicate(cube, name="similar_twin")[0]
        self.cmds.xform(twin, t=(25, 0, 0), ro=(0, 45, 0))
        self.cmds.select(cube)
        self.slots.tb001(self._widget(bounding_box=True))
        self.assertEqual(self.messages(), [], "a successful match reported an error")
        self.assertIn(twin, self.cmds.ls(sl=True))


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestSelectSimilarUvShellsInMaya(_MayaCase):
    """tb001 on a UV selection selects the shells that share the selected
    shell's topology and shape (the UV panel's Stack Similar oracle), without
    moving any UV; Include Original keeps the reference selected."""

    def setUp(self):
        super().setUp()
        cmds = self.cmds
        cmds.loadPlugin("Unfold3D.mll", quiet=True)
        self.a = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="uvsimA")[0]
        self.b = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="uvsimB")[0]
        self.c = cmds.polyPlane(w=1, h=1, sx=3, sy=1, ch=False, name="uvsimC")[0]
        for o, (du, dv, ang) in ((self.a, (0, 0, 0)), (self.b, (0.4, 0, 37)), (self.c, (0, 0.4, 0))):
            cmds.polyEditUV(f"{o}.map[*]", pu=0.5, pv=0.5, su=0.3, sv=0.3, r=True)
            cmds.polyEditUV(f"{o}.map[*]", pu=0.5, pv=0.5, a=ang, r=True)
            cmds.polyEditUV(f"{o}.map[*]", u=du, v=dv, r=True)
        cmds.hilite([self.a, self.b, self.c])
        cmds.selectMode(component=True)
        self.addCleanup(cmds.selectMode, object=True)

    def _widget(self, inc_orig=False):
        values = {name: default for name, _, _, default, _ in SelectionSlots._SIMILAR_METRICS}
        return _widget(s000=0.0, chk020=inc_orig, **values)

    def _uvs(self, o):
        cmds = self.cmds
        return [tuple(cmds.polyEditUV(f"{o}.map[{i}]", q=True)) for i in range(cmds.polyEvaluate(o, uv=True))]

    def test_a_uv_selection_selects_similar_shells_without_moving_uvs(self):
        before = {o: self._uvs(o) for o in (self.a, self.b, self.c)}
        self.cmds.select(f"{self.a}.map[0]")
        self.slots.tb001(self._widget())
        selected = self.cmds.ls(sl=True, flatten=True)
        self.assertTrue(selected and all(s.startswith(self.b + ".map[") for s in selected), selected)
        self.assertEqual(len(selected), self.cmds.polyEvaluate(self.b, uv=True))
        self.assertEqual(before, {o: self._uvs(o) for o in (self.a, self.b, self.c)})
        self.assertEqual(self.messages(), [])

    def test_include_original_keeps_the_reference_selected(self):
        self.cmds.select(f"{self.a}.map[0]")
        self.slots.tb001(self._widget(inc_orig=True))
        selected = self.cmds.ls(sl=True, flatten=True)
        self.assertIn(f"{self.a}.map[0]", selected)
        self.assertTrue(any(s.startswith(self.b + ".map[") for s in selected))

    def test_no_similar_shell_reports(self):
        self.cmds.select(f"{self.c}.map[0]")
        self.slots.tb001(self._widget())
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("no other UV shell", self.messages()[0])
        self.assertEqual(self.cmds.ls(sl=True, flatten=True), [f"{self.c}.map[0]"])


if __name__ == "__main__":
    unittest.main()
