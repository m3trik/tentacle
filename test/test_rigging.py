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


class _FakeCombo:
    """Stand-in for the option_box QComboBox: currentText()/currentData()."""

    def __init__(self, text="", data=None):
        self._text = text
        self._data = data

    def currentText(self):
        return self._text

    def currentData(self):
        return self._data


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
    """tb001 validates the selection up front, then forwards field values to
    mtk.connect_switch_to_constraint. Empty / non-constraint selections are
    rejected with a message box instead of calling the engine with junk."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)
        self.instance.sb = _FakeSb()

        import mayatk as mtk
        self._original = mtk.connect_switch_to_constraint
        self.captured = []

        def fake_connect(**kwargs):
            self.captured.append(kwargs)
            # Mimic the real engine's success return (see the switch_attr
            # success-signal contract the slot relies on).
            return {"switch_attr": f"{kwargs['constraint_node']}.{kwargs['attr_name']}"}

        mtk.connect_switch_to_constraint = fake_connect

    def tearDown(self):
        import mayatk as mtk
        mtk.connect_switch_to_constraint = self._original
        cmds.file(new=True, force=True)

    def _menu(self, switch="sw", anchor="", weighted=False):
        return _FakeMenu(
            t003=_FakeLineEdit(switch),
            t004=_FakeLineEdit(anchor),
            chk003=_FakeChk(weighted),
        )

    def _make_constraint(self):
        src = cmds.spaceLocator(name="cs_src")[0]
        driven = cmds.polyCube(name="cs_cube")[0]
        return cmds.parentConstraint(src, driven)[0]

    def test_values_forwarded_with_constraint_selection(self):
        con = self._make_constraint()
        cmds.select(con)
        widget = _FakeWidget([], menu=self._menu("mySwitch", "worldLoc", True))
        self.instance.tb001(widget)

        self.assertEqual(len(self.captured), 1)
        kw = self.captured[0]
        self.assertEqual(kw["attr_name"], "mySwitch")
        self.assertEqual(kw["anchor"], "worldLoc")
        self.assertTrue(kw["weighted"])
        self.assertEqual(kw["constraint_node"], con)

    def test_empty_selection_warns_and_skips_engine(self):
        cmds.select(clear=True)
        self.instance.tb001(_FakeWidget([], menu=self._menu()))
        self.assertEqual(self.captured, [])  # engine not called
        self.assertIn("Nothing selected", self.instance.sb.messages[-1][0][0])

    def test_non_constraint_selection_warns_and_skips_engine(self):
        cmds.select(cmds.polyCube(name="plain_cube")[0])
        self.instance.tb001(_FakeWidget([], menu=self._menu()))
        self.assertEqual(self.captured, [])  # engine not called
        self.assertIn("not a constraint", self.instance.sb.messages[-1][0][0])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB020RebindSkinClusters(unittest.TestCase):
    """b020 turns the engine summary into a simple message-box line and
    defers the detailed breakdown to the console."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)
        self.instance.sb = _FakeSb()

        import mayatk as mtk

        self._mtk = mtk
        self._original = mtk.rebind_skin_clusters
        self._summary = {
            "rebound": [],
            "no_skin_cluster": [],
            "wrong_type": [],
            "failed": [],
        }
        self.passed = []

        def fake_rebind(meshes=None, *a, **kw):
            self.passed.append(meshes)
            return self._summary

        mtk.rebind_skin_clusters = fake_rebind

    def tearDown(self):
        self._mtk.rebind_skin_clusters = self._original
        cmds.file(new=True, force=True)

    def _last_message(self):
        self.assertTrue(self.instance.sb.messages, "expected a message box")
        return self.instance.sb.messages[-1][0][0]

    def test_nothing_selected_warns_and_skips_engine(self):
        cmds.select(clear=True)
        self.instance.b020()
        self.assertEqual(self.passed, [])  # engine not called
        self.assertIn("Nothing selected", self._last_message())

    def test_success_reports_count(self):
        cube = cmds.polyCube(name="rb_cube")[0]
        cmds.select(cube)
        self._summary["rebound"] = ["rb_cube"]
        self.instance.b020()
        self.assertEqual(self.passed, [[cube]])  # forwards the selection
        self.assertIn("Rebound", self._last_message())

    def test_no_skin_cluster_message(self):
        cube = cmds.polyCube(name="rb_cube")[0]
        cmds.select(cube)
        self._summary["no_skin_cluster"] = ["rb_cube"]
        self.instance.b020()
        self.assertIn("no skinClusters", self._last_message())

    def test_wrong_type_message(self):
        loc = cmds.spaceLocator(name="rb_loc")[0]
        cmds.select(loc)
        self._summary["wrong_type"] = ["rb_loc"]
        self.instance.b020()
        self.assertIn("Incorrect object type", self._last_message())

    def test_partial_success_tallies_each_bucket(self):
        cube = cmds.polyCube(name="rb_cube")[0]
        cmds.select(cube)
        self._summary["rebound"] = ["a"]
        self._summary["no_skin_cluster"] = ["b"]
        self._summary["wrong_type"] = ["c"]
        self.instance.b020()
        msg = self._last_message()
        self.assertIn("Rebound", msg)
        self.assertIn("w/o skinCluster", msg)
        self.assertIn("wrong type", msg)
        self.assertIn("See console", msg)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb004LockUnlockAttributes(unittest.TestCase):
    """tb004 reads the Lock/Unlock combobox (cmb_lock, replacing the old
    chk010 checkbox) and the attr-scope combobox (cmb010), then locks or
    unlocks the resolved attributes. Pins the combobox-driven dispatch so a
    label/reader rename can't silently invert the action."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rigging_module.Rigging.__new__(rigging_module.Rigging)
        self.instance.sb = _FakeSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _widget(self, action, scope="all"):
        menu = _FakeMenu(
            cmb_lock=_FakeCombo(text=action),
            cmb010=_FakeCombo(text=f"Attrs: {scope}", data=scope),
        )
        return _FakeWidget([], menu=menu)

    def test_lock_locks_all_transform_attrs(self):
        cube = cmds.polyCube(name="lk_cube")[0]
        cmds.select(cube)
        self.instance.tb004(self._widget("Lock", "all"))
        self.assertTrue(cmds.getAttr(f"{cube}.tx", lock=True))
        self.assertTrue(cmds.getAttr(f"{cube}.sz", lock=True))

    def test_unlock_clears_the_lock(self):
        cube = cmds.polyCube(name="lk_cube")[0]
        for attr in ("tx", "sz"):
            cmds.setAttr(f"{cube}.{attr}", lock=True)
        cmds.select(cube)
        self.instance.tb004(self._widget("Unlock", "all"))
        self.assertFalse(cmds.getAttr(f"{cube}.tx", lock=True))
        self.assertFalse(cmds.getAttr(f"{cube}.sz", lock=True))

    def test_nothing_selected_warns_and_skips(self):
        cmds.select(clear=True)
        self.instance.tb004(self._widget("Lock", "all"))
        self.assertTrue(self.instance.sb.messages)


if __name__ == "__main__":
    unittest.main()
