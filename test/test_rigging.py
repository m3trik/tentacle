#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.rigging.

The dispatch units worth pinning at this layer:

- cmb001 (Create): 4-way dispatch on widget.itemText. Each branch
  invokes a different cmds/mel call. A typo or rename would silently
  break one tool.
- cmb002 (Quick Rig): 4 entries that drive marking_menu.show(<name>).
  The marking-menu key names must stay stable.
- tb000 (Toggle Display LRA): no-op when scene has no joints; warns.
- tb001 (Constraint Switch): forwards three field values to
  mtk.connect_switch_to_constraint as named kwargs.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import rigging as rigging_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    rigging_module = None
    _MAYA_AVAILABLE = False


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeLineEdit:
    def __init__(self, value):
        self._v = value

    def text(self):
        return self._v


class _FakeMenu:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    """Widget exposing both itemText() (for cmb dispatch) and items list."""

    def __init__(self, items, menu=None):
        self._items = list(items)
        self.items = list(items)
        if menu is not None:
            self.option_box = _FakeOptionBox(menu)

    def itemText(self, idx):
        return self._items[idx]


class _FakeMarkingMenu:
    def __init__(self):
        self.shown = []

    def show(self, name):
        self.shown.append(name)


class _FakeHandlers:
    def __init__(self):
        self.marking_menu = _FakeMarkingMenu()


class _FakeSb:
    def __init__(self):
        self.handlers = _FakeHandlers()
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb001Create(unittest.TestCase):
    """cmb001 dispatches to 4 different create-tool actions."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)

        # Capture cmds.setToolTo and cmds.lattice. mel.eval is harder to
        # capture without ruining other tests — leave it as a real call but
        # check via cmds afterwards.
        self._orig_setToolTo = cmds.setToolTo
        self._orig_lattice = cmds.lattice
        self.tool_calls = []
        self.lattice_calls = []
        cmds.setToolTo = lambda *a, **kw: self.tool_calls.append(a)
        cmds.lattice = lambda *a, **kw: self.lattice_calls.append((a, kw))

    def tearDown(self):
        cmds.setToolTo = self._orig_setToolTo
        cmds.lattice = self._orig_lattice
        cmds.file(new=True, force=True)

    def _w(self):
        return _FakeWidget(["Cluster", "IK Handle", "Joints", "Lattice"])

    def test_joints_sets_joint_tool(self):
        items = ["Cluster", "IK Handle", "Joints", "Lattice"]
        widget = _FakeWidget(items)
        idx = items.index("Joints")
        self.instance.cmb001(idx, widget)
        self.assertIn(("jointContext",), self.tool_calls)

    def test_ik_handle_sets_ik_tool(self):
        items = ["Cluster", "IK Handle", "Joints", "Lattice"]
        widget = _FakeWidget(items)
        idx = items.index("IK Handle")
        self.instance.cmb001(idx, widget)
        self.assertIn(("ikHandleContext",), self.tool_calls)

    def test_lattice_calls_cmds_lattice(self):
        items = ["Cluster", "IK Handle", "Joints", "Lattice"]
        widget = _FakeWidget(items)
        idx = items.index("Lattice")
        self.instance.cmb001(idx, widget)
        self.assertEqual(len(self.lattice_calls), 1)
        # Default lattice kwargs from the slot.
        _, kw = self.lattice_calls[0]
        self.assertEqual(kw.get("divisions"), [2, 5, 2])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb002QuickRigMarkingMenuNames(unittest.TestCase):
    """cmb002 routes to marking_menu.show(<key>). The 4 keys are part
    of a fragile string contract that we pin here."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)
        self.instance.sb = _FakeSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_each_quick_rig_routes_to_named_menu(self):
        items = ["Tube Rig", "Wheel Rig", "Shadow Rig", "Telescope Rig"]
        widget = _FakeWidget(items)

        for idx, _ in enumerate(items):
            self.instance.cmb002(idx, widget)

        expected = ["tube_rig", "wheel_rig", "shadow_rig", "telescope_rig"]
        self.assertEqual(self.instance.sb.handlers.marking_menu.shown, expected)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb000ToggleLocalAxes(unittest.TestCase):
    """tb000 warns when no joints exist."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)
        self.instance.sb = _FakeSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_no_joints_warns_and_skips(self):
        """Empty scene → message_box and early return; no toggle call."""
        widget = _FakeWidget(
            [],
            menu=_FakeMenu(
                chk000=_FakeChk(True),
                chk001=_FakeChk(False),
                chk002=_FakeChk(False),
            ),
        )
        # Capture cmds.toggle so we can assert it wasn't called.
        original = cmds.toggle
        called = []
        cmds.toggle = lambda *a, **kw: called.append((a, kw))
        try:
            self.instance.tb000(widget)
        finally:
            cmds.toggle = original

        self.assertTrue(self.instance.sb.messages)
        self.assertEqual(called, [])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001ConstraintSwitch(unittest.TestCase):
    """tb001 forwards 3 widget values to mtk.connect_switch_to_constraint."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)

        import mayatk as mtk
        self._original = mtk.connect_switch_to_constraint
        self.captured = []

        def fake_connect(**kwargs):
            self.captured.append(kwargs)

        mtk.connect_switch_to_constraint = fake_connect

    def tearDown(self):
        import mayatk as mtk
        mtk.connect_switch_to_constraint = self._original
        cmds.file(new=True, force=True)

    def test_values_forwarded_with_selection(self):
        cube = cmds.polyCube(name="cs_cube")[0]
        cmds.select(cube)
        widget = _FakeWidget(
            [],
            menu=_FakeMenu(
                t003=_FakeLineEdit("mySwitch"),
                t004=_FakeLineEdit("worldLoc"),
                chk003=_FakeChk(True),
            ),
        )
        self.instance.tb001(widget)

        self.assertEqual(len(self.captured), 1)
        kw = self.captured[0]
        self.assertEqual(kw["attr_name"], "mySwitch")
        self.assertEqual(kw["anchor"], "worldLoc")
        self.assertTrue(kw["weighted"])
        # Constraint node forwarded as first selection element.
        self.assertEqual(kw["constraint_node"], cube)

    def test_empty_selection_passes_none(self):
        """tb001 with no selection passes constraint_node=None."""
        cmds.select(clear=True)
        widget = _FakeWidget(
            [],
            menu=_FakeMenu(
                t003=_FakeLineEdit("sw"),
                t004=_FakeLineEdit(""),
                chk003=_FakeChk(False),
            ),
        )
        self.instance.tb001(widget)

        self.assertEqual(len(self.captured), 1)
        self.assertIsNone(self.captured[0]["constraint_node"])


if __name__ == "__main__":
    unittest.main()
