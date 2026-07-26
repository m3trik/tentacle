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
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import selection as selection_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    selection_module = None
    _MAYA_AVAILABLE = False


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
class TestCmb003ConvertToBorderEdges(unittest.TestCase):
    """Regression pin for a real bug: cmb003's "Border Edges" used to call
    ``self.getBorderEdgeFromFace()``, a method that doesn't exist anywhere in the
    codebase — every selection raised AttributeError. Fixed 2026-07-06 to reuse the
    same ``mtk.Components`` pipeline ``tb000``'s own Border-Edges option already used
    correctly a few methods above. Pins both "doesn't crash" and "selects the right
    edges" against a real open mesh (a closed mesh has zero border edges either way)."""

    def test_border_edges_selects_naked_edges_of_an_open_plane(self):
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        cmds.file(new=True, force=True)
        plane = cmds.polyPlane(sx=3, sy=3, w=2, h=2, ch=False)[0]
        cmds.select(f"{plane}.f[0:8]")  # all 9 faces of the 3x3 plane

        try:
            instance.cmb003(8, _Widget_ConvertTo())  # index 8 == "Border Edges"
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
        components given.") by design as an API-boundary guard, but cmb003
        called it with an empty selection unguarded, crashing the slot.
        Fixed 2026-07-06 to warn via message_box and return early instead."""
        instance = selection_module.Selection.__new__(selection_module.Selection)
        instance.sb = _RecordedSb()

        cmds.file(new=True, force=True)
        cmds.select(clear=True)
        instance.cmb003(8, _Widget_ConvertTo())  # index 8 == "Border Edges"

        self.assertTrue(instance.sb.messages, "should warn on an empty selection")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb003EdgeLoop(unittest.TestCase):
    """Regression pin for a real bug: cmb003's "Edge Loop" case called
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
            instance.cmb003(4, _Widget_ConvertTo())  # index 4 == "Edge Loop"
        finally:
            result = cmds.ls(sl=True, flatten=True) or []
            cmds.file(new=True, force=True)

        # A border edge's loop on a 4x4 grid traces the full 16-edge perimeter.
        self.assertEqual(len(result), 16, f"got {result}")


class _Widget_ConvertTo:
    """cmb003's dispatch only reads ``widget.items`` (by index)."""

    items = [
        "Verts", "Vertex Faces", "Vertex Perimeter", "Edges", "Edge Loop", "Edge Ring",
        "Contained Edges", "Edge Perimeter", "Border Edges", "Faces", "Face Path",
        "Contained Faces", "Face Perimeter", "UV's", "UV Shell", "UV Shell Border",
        "UV Perimeter", "UV Edge Loop", "Shell", "Shell Border",
    ]


if __name__ == "__main__":
    unittest.main()
