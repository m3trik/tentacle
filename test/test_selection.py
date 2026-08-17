#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.selection.

selection.py is mostly UI plumbing over mtk.Selection and Maya cmds. The
units worth pinning at this layer:

- cmb001 (Reorder Selection): the display-name → method-name map. If a
  new item is added to the combo without a method_map entry, it would
  silently fall back to ``name``. The test asserts every combo item
  resolves to an mtk-reorder method.
- get_selection_tool / set_selection_tool: static methods with explicit
  validation — set_selection_tool() rejects unknown tool names.
- tb000 step slicing: the Select-Nth result is sliced by step. If step
  drifts to 0, this would raise ValueError — pin the contract.
- list001 (Convert To) / b002-b007 (Selection Constraints): the two forks'
  tables against the shared SelectionMixin (static, no DCC needed) plus the
  Maya dispatch against real geometry / real polySelectConstraint state.
"""
import ast
import unittest
from pathlib import Path

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
selection_module = maya_module("tentacle.slots.maya.selection")


class _FakeOptionMenu:
    """Simulates widget.option_box.menu attribute access (chk000.isChecked, s003.value)."""

    def __init__(self, **flags):
        for k, v in flags.items():
            setattr(self, k, _FakeChk(v) if isinstance(v, bool) else _FakeSpin(v))


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeSpin:
    def __init__(self, val):
        self._val = val

    def value(self):
        return self._val


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    def __init__(self, menu):
        # tb004's settings menu is now the button's own MenuMixin menu
        # (no option box), so the scope/mode reads go through ``.menu``.
        self.menu = menu


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestReorderSelectionMap(unittest.TestCase):
    """cmb001 maps a display-name to a method-name keyword. Drift here is
    silent (unknown key falls through to ``name``), so we pin the items list
    against the mapping directly."""

    EXPECTED_DISPLAY_ITEMS = [
        "Name",
        "Hierarchy",
        "X Position",
        "Y Position",
        "Z Position",
        "Distance from Origin",
        "Volume",
        "Vertex Count",
        "Random",
        "Creation Time",
    ]

    def test_method_map_covers_every_display_item(self):
        """Probe by running cmb001 with each item index → captured method."""
        import mayatk as mtk

        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        original = mtk.reorder_objects
        captured = []
        mtk.reorder_objects = lambda objs, method, reverse: captured.append(method) or []

        try:
            # Build a fake widget that exposes .items + .option_box.menu.chk009
            class _Widget:
                items = list(self.EXPECTED_DISPLAY_ITEMS)
                option_box = _FakeOptionBox(_FakeOptionMenu(chk009=False))

            # Need a selection so cmb001 doesn't bail out at the front.
            cmds.file(new=True, force=True)
            cube = cmds.polyCube(name="reorder_probe")[0]
            cmds.select(cube)

            for i, _ in enumerate(self.EXPECTED_DISPLAY_ITEMS):
                instance.cmb001(i, _Widget())
        finally:
            mtk.reorder_objects = original
            cmds.file(new=True, force=True)

        # Every display item should produce a *distinct* mtk method name.
        # The bug we're catching: a typo in method_map silently falls back to "name".
        # We assert every item produces a non-"name" mapping EXCEPT "Name" itself.
        self.assertEqual(captured[0], "name")  # 'Name' → 'name'
        # All later items must NOT fall through to 'name' (drift detector).
        for display, method in zip(self.EXPECTED_DISPLAY_ITEMS[1:], captured[1:]):
            self.assertNotEqual(
                method,
                "name",
                f"'{display}' silently falls through to 'name' — broken method_map",
            )

    def test_empty_selection_warns_and_skips(self):
        """cmb001 with no selection should message-box and not call mtk."""
        import mayatk as mtk

        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        original = mtk.reorder_objects
        captured = []
        mtk.reorder_objects = lambda *a, **kw: captured.append((a, kw))

        try:
            class _Widget:
                items = ["Name"]
                option_box = _FakeOptionBox(_FakeOptionMenu(chk009=False))

            cmds.file(new=True, force=True)
            cmds.select(clear=True)
            instance.cmb001(0, _Widget())
        finally:
            mtk.reorder_objects = original
            cmds.file(new=True, force=True)

        self.assertEqual(captured, [])
        self.assertTrue(instance.sb.messages)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSelectionToolStatic(unittest.TestCase):
    """get_selection_tool / set_selection_tool are static utility methods
    with validation."""

    def test_set_selection_tool_rejects_unknown(self):
        """An unknown tool name must NOT call cmds.setToolTo."""
        original = cmds.setToolTo
        captured = []
        cmds.setToolTo = lambda *a, **kw: captured.append((a, kw))

        try:
            selection_module.Selection.set_selection_tool("bogusContext")
        finally:
            cmds.setToolTo = original

        self.assertEqual(captured, [])

    def test_set_selection_tool_accepts_valid(self):
        """A valid tool name should be forwarded to cmds.setToolTo."""
        original = cmds.setToolTo
        captured = []
        cmds.setToolTo = lambda *a, **kw: captured.append((a, kw))

        try:
            selection_module.Selection.set_selection_tool("selectSuperContext")
        finally:
            cmds.setToolTo = original

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0][0], "selectSuperContext")

    def test_get_selection_tool_returns_str(self):
        """get_selection_tool wraps cmds.currentCtx and returns a str."""
        result = selection_module.Selection.get_selection_tool()
        # Maya 2025 startup default is 'selectSuperContext'. Just assert string
        # (or None on failure path).
        self.assertTrue(result is None or isinstance(result, str))


class _FakeCombo:
    """Simulates a data-carrying settings combo (cmb_bytype_scope / _mode)."""

    def __init__(self, data):
        self._data = data

    def currentData(self):
        return self._data


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestByTypeScopeAndMode(unittest.TestCase):
    """tb004's scope/mode combos → the pool list000 filters from and the
    selection mode it applies.

    Pins the currentData → ls-flag / mode-kwarg dispatch so a relabeled
    combo can't silently fall back to the All-Objects / Replace defaults."""

    def _instance_with(self, scope="all", mode="replace"):
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        menu = _FakeOptionMenu()
        menu.cmb_bytype_scope = _FakeCombo(scope)
        menu.cmb_bytype_mode = _FakeCombo(mode)

        class _Submenu:
            tb004 = _FakeWidget(menu)

        instance.submenu = _Submenu()
        return instance

    def test_selected_scope_uses_selection(self):
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="scope_sel_probe")[0]
        cmds.select(cube)
        inst = self._instance_with(scope="selected")
        self.assertEqual(inst._by_type_scope_objects(), [cube])

    def test_visible_scope_excludes_hidden(self):
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="scope_vis_probe")[0]
        cmds.setAttr(f"{cube}.visibility", 0)
        inst = self._instance_with(scope="visible")
        self.assertNotIn(cube, inst._by_type_scope_objects())

    def test_default_scope_is_all(self):
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="scope_all_probe")[0]
        cmds.select(clear=True)
        inst = self._instance_with(scope=None)  # unset combo → "all"
        self.assertIn(cube, inst._by_type_scope_objects())

    def test_settings_row_opens_menu_not_type_select(self):
        """The tb004 Settings row dispatches to its scope/mode menu (via
        ``tb004``), never to ``select_by_type`` — regression for the reported
        'settings menu does not open' after the option box was removed."""
        import mayatk as mtk

        inst = self._instance_with()
        opened = {}

        class _Menu:
            def show_as_popup(self, **kwargs):
                opened.update(kwargs)

        class _SettingsRow:
            sublist = None
            menu = _Menu()

            def objectName(self):
                return "tb004"

            def item_text(self):
                return "Settings"

        ran_select = {"v": False}
        original = mtk.Selection.select_by_type
        mtk.Selection.select_by_type = (
            lambda *a, **k: ran_select.__setitem__("v", True) or []
        )
        try:
            inst.list000(_SettingsRow())
        finally:
            mtk.Selection.select_by_type = original

        self.assertTrue(opened, "the Settings row did not open its menu")
        self.assertFalse(
            ran_select["v"], "the Settings row wrongly ran select_by_type"
        )

    def test_mode_passes_through_to_select_by_type(self):
        import mayatk as mtk

        cmds.file(new=True, force=True)
        inst = self._instance_with(scope="all", mode="add")

        class _Leaf:
            sublist = None

            def objectName(self):  # a real leaf row is an unnamed list item
                return ""

            def item_text(self):
                return "Cameras"

        captured = {}
        original = mtk.Selection.select_by_type
        mtk.Selection.select_by_type = (
            lambda st, objs, mode: captured.update(mode=mode) or []
        )
        try:
            inst.list000(_Leaf())
        finally:
            mtk.Selection.select_by_type = original

        self.assertEqual(captured.get("mode"), "add")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList001ConvertToBorderEdges(unittest.TestCase):
    """Regression pin for a real bug: Convert To's "Border Edges" used to call
    ``self.getBorderEdgeFromFace()``, a method that doesn't exist anywhere in the
    codebase — every selection raised AttributeError. Fixed 2026-07-06 to reuse the
    same ``mtk.Components`` pipeline ``tb000``'s own Border-Edges option already used
    correctly a few methods above. Pins both "doesn't crash" and "selects the right
    edges" against a real open mesh (a closed mesh has zero border edges either way).

    Driven through ``list001`` (the Convert To ExpandableList that replaced the
    ``cmb003`` combo on 2026-08-16), i.e. the SelectionMixin dispatch + the fork's
    ``_CONVERT_TO_OPS`` table, not the helper directly."""

    def test_border_edges_selects_naked_edges_of_an_open_plane(self):
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        cmds.file(new=True, force=True)
        plane = cmds.polyPlane(sx=3, sy=3, w=2, h=2, ch=False)[0]
        cmds.select(f"{plane}.f[0:8]")  # all 9 faces of the 3x3 plane

        try:
            instance.list001(_ConvertToLeaf("Border Edges"))
        finally:
            border_result = cmds.ls(sl=True, flatten=True) or []
            cmds.file(new=True, force=True)

        # A 3x3 open plane has a perimeter of 4*3=12 border edges.
        self.assertEqual(len(border_result), 12, f"got {border_result}")
        self.assertFalse(instance.sb.messages, "should not warn on a valid selection")

    def test_getBorderEdgeFromFace_is_truly_gone(self):
        """Confirms the ORIGINAL bug's method reference doesn't silently reappear."""
        self.assertFalse(hasattr(selection_module.Selection, "getBorderEdgeFromFace"))

    def test_border_edges_empty_selection_warns_and_does_not_raise(self):
        """Regression: get_border_components() raises ValueError("No valid
        components given.") by design as an API-boundary guard, but the slot
        called it with an empty selection unguarded, crashing. Fixed 2026-07-06
        to warn via message_box and return early instead."""
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        cmds.file(new=True, force=True)
        cmds.select(clear=True)
        instance.list001(_ConvertToLeaf("Border Edges"))

        self.assertTrue(instance.sb.messages, "should warn on an empty selection")

    def test_root_row_is_navigation_only(self):
        """The list root ("Convert To") carries a populated sublist; interacting
        with it must not run any conversion (a stray op on the root would fire
        on every hover-open)."""
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()
        ran = []
        original = selection_module.Selection._CONVERT_TO_OPS
        selection_module.Selection._CONVERT_TO_OPS = {
            k: (lambda self, k=k: ran.append(k)) for k in original
        }
        try:
            instance.list001(_ConvertToRoot())
        finally:
            selection_module.Selection._CONVERT_TO_OPS = original
        self.assertEqual(ran, [])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList001EdgeLoop(unittest.TestCase):
    """Regression pin for a real bug: Convert To's "Edge Loop" case called
    ``mel.eval("polySelectSp -loop 1")`` — a nonexistent MEL command — which
    raised RuntimeError("Invalid object or value: 1") on every use. Fixed
    2026-07-06 to call ``SelectEdgeLoopSp``, the same global proc Maya's own
    Polygons > Select menu wires "Convert Selection to Edge Loop" to (see
    PolygonsSelectMenu.mel, sibling of "Edge Ring"'s SelectEdgeRingSp used a
    few lines below)."""

    def test_edge_loop_selects_the_full_border_loop(self):
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        cmds.file(new=True, force=True)
        plane = cmds.polyPlane(sx=4, sy=4, w=4, h=4, ch=False)[0]
        cmds.select(f"{plane}.e[0]")

        try:
            instance.list001(_ConvertToLeaf("Edge Loop"))
        finally:
            result = cmds.ls(sl=True, flatten=True) or []
            cmds.file(new=True, force=True)

        # A border edge's loop on a 4x4 grid traces the full 16-edge perimeter.
        self.assertEqual(len(result), 16, f"got {result}")


class _ConstraintButton:
    """A constraint-row button as the slot sees it: name, checked state, and
    the panel (``ui``) its siblings hang off, for the "what's on now" report."""

    def __init__(self, name, checked, ui=None):
        self._name = name
        self._checked = checked
        self.ui = ui if ui is not None else _ConstraintRow()
        setattr(self.ui, name, self)

    def objectName(self):
        return self._name

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        self._checked = bool(state)


class _ConstraintRow:
    """Stand-in for ``widget.ui``: buttons attach themselves by objectName."""


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestConstraintButtons(unittest.TestCase):
    """b002-b007 (the icon row that replaced the one-at-a-time ``cmb005`` combo,
    2026-08-16) write their button state straight to Maya's per-constraint
    ``polySelectConstraint`` flags. The whole point of the row is that the flags
    are INDEPENDENT — enabling one must not clear another — so that is pinned
    against the real command, not a fake."""

    _ALL_OFF = dict(
        border=False, borderPropagation=False, shell=False, anglePropagation=False,
        loopPropagation=False, ringPropagation=False, uvEdgeLoopPropagation=False,
    )

    def setUp(self):
        cmds.polySelectConstraint(**self._ALL_OFF)
        self.instance = selection_module.Selection.__new__(selection_module.Selection)
        self.instance.sb = _RecordedSb()

    def tearDown(self):
        cmds.polySelectConstraint(**self._ALL_OFF)

    def _flag(self, name):
        return bool(cmds.polySelectConstraint(q=True, **{name: True}))

    def test_two_constraints_can_be_on_at_once(self):
        row = _ConstraintRow()
        angle = _ConstraintButton("b002", True, row)
        loop = _ConstraintButton("b004", True, row)
        self.instance._toggle_constraint(angle)
        self.instance._toggle_constraint(loop)
        self.assertTrue(self._flag("anglePropagation"))
        self.assertTrue(self._flag("loopPropagation"), "Edge Loop cleared Angle's sibling flag")
        # the report names every constraint that is on
        (args, _), = self.instance.sb.messages[-1:]
        self.assertIn("Angle", args[0])
        self.assertIn("Edge Loop", args[0])

    def test_unchecking_clears_only_its_own_flags(self):
        row = _ConstraintRow()
        angle = _ConstraintButton("b002", True, row)
        border = _ConstraintButton("b003", True, row)
        self.instance._toggle_constraint(angle)
        self.instance._toggle_constraint(border)
        border.setChecked(False)
        self.instance._toggle_constraint(border)
        self.assertFalse(self._flag("border"))
        self.assertFalse(self._flag("borderPropagation"))
        self.assertTrue(self._flag("anglePropagation"), "unchecking Border cleared Angle")

    def test_all_off_reports_off(self):
        angle = _ConstraintButton("b002", False)
        self.instance._toggle_constraint(angle)
        (args, _), = self.instance.sb.messages[-1:]
        self.assertIn("OFF", args[0])

    def test_seed_reads_the_live_flag(self):
        """``_constraint_is_on`` is what ``mirror_app_state`` seeds from — it must
        read Maya, not the widget."""
        cmds.polySelectConstraint(shell=True)
        self.assertTrue(self.instance._constraint_is_on(_ConstraintButton("b006", False)))
        self.assertFalse(self.instance._constraint_is_on(_ConstraintButton("b002", True)))


class TestSelectionForksAgreeWithMixin(unittest.TestCase):
    """Static (no DCC) parity pins for the two shared-table surfaces the parity
    sweep does NOT track (ExpandableList leaves and per-button tables): both
    forks' ``_CONVERT_TO_OPS`` / constraint tables against ``SelectionMixin``.
    Read via AST so this runs without maya.cmds or bpy."""

    ROOT = Path(__file__).resolve().parent.parent / "tentacle" / "slots"

    @classmethod
    def _class_dict_keys(cls, path, attr):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == attr for t in node.targets
            ):
                assert isinstance(node.value, ast.Dict), f"{attr} in {path.name} is not a dict literal"
                return [ast.literal_eval(k) for k in node.value.keys]
        raise AssertionError(f"{attr} not found in {path}")

    def test_convert_to_tables_mirror_minus_ledgered_items(self):
        maya = self._class_dict_keys(self.ROOT / "maya" / "selection.py", "_CONVERT_TO_OPS")
        blender = self._class_dict_keys(self.ROOT / "blender" / "selection.py", "_CONVERT_TO_OPS")
        # ledgered na in docs/parity_map.py (no Blender component analogue)
        ledgered = {"Vertex Faces", "UV's"}
        self.assertEqual(len(maya), 20)
        self.assertEqual([m for m in maya if m not in ledgered], blender)

    def test_constraint_tables_cover_the_shared_button_row(self):
        mixin = self._class_dict_keys(self.ROOT / "_selection.py", "_CONSTRAINT_BUTTONS")
        maya = self._class_dict_keys(self.ROOT / "maya" / "selection.py", "_CONSTRAINT_FLAGS")
        blender = self._class_dict_keys(self.ROOT / "blender" / "selection.py", "_CONSTRAINT_OPS")
        self.assertEqual(mixin, ["b002", "b003", "b004", "b005", "b006", "b007"])
        self.assertEqual(maya, mixin)
        self.assertEqual(blender, mixin)

    def test_constraint_row_matches_the_ui(self):
        """The .ui declares the row; every declared button must have a slot
        (else the widget is inert) and vice versa (else the slot is dead)."""
        import xml.etree.ElementTree as ET

        ui = self.ROOT.parent / "ui" / "selection.ui"
        names = [
            w.get("name")
            for w in ET.parse(ui).iter("widget")
            if w.get("class") == "PushButton" and w.get("name", "").startswith("b00")
            and w.get("name") != "b001"
        ]
        mixin = self._class_dict_keys(self.ROOT / "_selection.py", "_CONSTRAINT_BUTTONS")
        self.assertEqual(names, mixin)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001SelectSimilarReporting(unittest.TestCase):
    """tb001 (Select Similar) reports when it matches nothing.

    Regression for a real report ("Select Similar selects nothing"): a no-match
    is invisible from the UI — with Include Original off it silently clears the
    selection, with it on it re-selects what was already selected. Both read as
    a dead button, which is why a genuine engine bug went undiagnosed.
    """

    def setUp(self):
        # cmds.selectMode is inert under maya.standalone — it answers False to
        # every query even right after being set — so tb001's object-mode branch
        # is unreachable headless and every case would fall through to the
        # component path. Pin the query; a leaked mock would reroute every later
        # cmds.selectMode call, hence addCleanup rather than a tearDown body.
        real_select_mode = cmds.selectMode
        self.addCleanup(setattr, cmds, "selectMode", real_select_mode)
        cmds.selectMode = lambda *a, **kw: True

    def _instance(self, tolerance=0.0, inc_orig=False, **checked):
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        menu = _FakeOptionMenu()
        menu.s000 = _FakeSpin(tolerance)
        menu.chk020 = _FakeChk(inc_orig)
        for name, _, kwarg, default, _tip in instance._SIMILAR_METRICS:
            setattr(menu, name, _FakeChk(checked.get(kwarg, default)))

        self.widget = _FakeWidget(menu)
        self.widget.option_box = _FakeOptionBox(menu)
        return instance

    def test_no_selection_asks_for_a_reference_object(self):
        """An empty selection is a different failure from an empty result and
        must not advise raising the tolerance."""
        cmds.file(new=True, force=True)
        cmds.polyCube(name="similar_lonely")
        cmds.select(clear=True)

        inst = self._instance()
        inst.tb001(self.widget)

        self.assertEqual(len(inst.sb.messages), 1)
        self.assertIn("reference object", inst.sb.messages[0][0][0])

    def test_no_match_names_the_compared_metrics(self):
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="similar_cube", w=2, h=2, d=2)[0]
        cmds.polySphere(name="similar_sphere", r=9)
        cmds.select(cube)

        inst = self._instance(vertex=True, edge=True, face=True, worldArea=True)
        inst.tb001(self.widget)

        self.assertEqual(len(inst.sb.messages), 1)
        message = inst.sb.messages[0][0][0]
        for label in ("Vertex", "Edge", "Face", "World Area"):
            self.assertIn(label, message)
        self.assertNotIn("Triangle", message)  # unchecked metrics aren't named

    def test_no_match_reported_even_with_include_original(self):
        """With Include Original on, the result is non-empty (it's the original)
        — the report has to compare against the originals, not the raw return."""
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="similar_solo", w=2, h=2, d=2)[0]
        cmds.polySphere(name="similar_other", r=9)
        cmds.select(cube)

        inst = self._instance(inc_orig=True)
        inst.tb001(self.widget)

        self.assertEqual(len(inst.sb.messages), 1)
        self.assertIn("no matches", inst.sb.messages[0][0][0])

    def test_match_selects_silently(self):
        """A duplicate moved AND rotated is the reported scenario; it must match
        at tolerance 0 with the default metrics, and say nothing."""
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="similar_src", w=2, h=2, d=2)[0]
        twin = cmds.duplicate(cube, name="similar_twin")[0]
        cmds.xform(twin, t=(25, 0, 0), ro=(0, 45, 0))
        cmds.select(cube)

        inst = self._instance(boundingBox=True)
        inst.tb001(self.widget)

        self.assertEqual(inst.sb.messages, [], "a successful match reported an error")
        self.assertIn(twin, cmds.ls(sl=True))

    def test_metric_table_kwargs_are_valid_polyevaluate_flags(self):
        """The table's third field is passed straight to polyEvaluate as a
        keyword — a typo there would silently widen the comparison."""
        cmds.file(new=True, force=True)
        cube = cmds.polyCube(name="similar_flags")[0]
        inst = selection_module.Selection
        for _, label, kwarg, _, _ in inst._SIMILAR_METRICS:
            with self.subTest(metric=label):
                self.assertIsNotNone(cmds.polyEvaluate(cube, **{kwarg: True}))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001SelectSimilarUvShells(unittest.TestCase):
    """tb001 on a UV selection selects the shells that share the selected shell's
    topology and shape (the UV panel's Stack Similar oracle), without moving any
    UV; Include Original keeps the reference selected."""

    def setUp(self):
        cmds.file(new=True, force=True)
        cmds.loadPlugin("Unfold3D.mll", quiet=True)
        # standalone's selectMode answers False -> the object-mode branch is
        # skipped, which is what a component selection needs here.
        self.a = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="uvsimA")[0]
        self.b = cmds.polyPlane(w=1, h=1, sx=2, sy=2, ch=False, name="uvsimB")[0]
        self.c = cmds.polyPlane(w=1, h=1, sx=3, sy=1, ch=False, name="uvsimC")[0]
        for o, (du, dv, ang) in ((self.a, (0, 0, 0)), (self.b, (0.4, 0, 37)), (self.c, (0, 0.4, 0))):
            cmds.polyEditUV(f"{o}.map[*]", pu=0.5, pv=0.5, su=0.3, sv=0.3, r=True)
            cmds.polyEditUV(f"{o}.map[*]", pu=0.5, pv=0.5, a=ang, r=True)
            cmds.polyEditUV(f"{o}.map[*]", u=du, v=dv, r=True)
        cmds.hilite([self.a, self.b, self.c])

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _instance(self, tolerance=0.0, inc_orig=False):
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()
        menu = _FakeOptionMenu()
        menu.s000 = _FakeSpin(tolerance)
        menu.chk020 = _FakeChk(inc_orig)
        for name, _, _kwarg, default, _tip in instance._SIMILAR_METRICS:
            setattr(menu, name, _FakeChk(default))
        widget = _FakeWidget(menu)
        widget.option_box = _FakeOptionBox(menu)
        return instance, widget

    def _uvs(self, o):
        return [tuple(cmds.polyEditUV(f"{o}.map[{i}]", q=True)) for i in range(cmds.polyEvaluate(o, uv=True))]

    def test_uv_selection_selects_similar_shells_without_moving_uvs(self):
        before = {o: self._uvs(o) for o in (self.a, self.b, self.c)}
        cmds.select(f"{self.a}.map[0]")
        inst, widget = self._instance()
        inst.tb001(widget)
        selected = cmds.ls(sl=True, flatten=True)
        self.assertTrue(selected and all(s.startswith(self.b + ".map[") for s in selected), selected)
        self.assertEqual(len(selected), cmds.polyEvaluate(self.b, uv=True))
        self.assertEqual(before, {o: self._uvs(o) for o in (self.a, self.b, self.c)})
        self.assertEqual(inst.sb.messages, [])

    def test_include_original_keeps_the_reference_selected(self):
        cmds.select(f"{self.a}.map[0]")
        inst, widget = self._instance(inc_orig=True)
        inst.tb001(widget)
        selected = cmds.ls(sl=True, flatten=True)
        self.assertIn(f"{self.a}.map[0]", selected)
        self.assertTrue(any(s.startswith(self.b + ".map[") for s in selected))

    def test_no_similar_shell_reports(self):
        cmds.select(f"{self.c}.map[0]")
        inst, widget = self._instance()
        inst.tb001(widget)
        self.assertEqual(len(inst.sb.messages), 1)
        self.assertIn("no other UV shell", inst.sb.messages[0][0][0])
        self.assertEqual(cmds.ls(sl=True, flatten=True), [f"{self.c}.map[0]"])  # untouched


class _ConvertToLeaf:
    """A Convert To list leaf as ``_dispatch_convert_to`` sees it: no sublist,
    and ``item_text()`` is the table key."""

    sublist = None

    def __init__(self, label):
        self._label = label

    def item_text(self):
        return self._label


class _ConvertToRoot:
    """The list root: a populated sublist marks it navigation-only."""

    class sublist:  # noqa: N801 — attribute stand-in
        @staticmethod
        def get_items():
            return ["Verts"]

    @staticmethod
    def item_text():
        return "Convert To"


if __name__ == "__main__":
    unittest.main()
