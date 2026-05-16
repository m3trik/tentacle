#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.duplicate.

The mayatk duplicate_* engines (linear/radial/grid) are covered in
mayatk's test_edit_tools_duplicate. This file pins the *slot-layer*
gating logic:

- tb000 (Convert to Instances): requires ≥2 ordered-selected objects;
  warns and skips otherwise.
- tb001 (Select Instanced Objects): routes by 'All Instanced' checkbox
  — true → all-scene, false → selection-restricted.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import duplicate as duplicate_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    duplicate_module = None
    _MAYA_AVAILABLE = False


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeMenu:
    def __init__(self, chk000, chk001=None, chk002=None):
        self.chk000 = _FakeChk(chk000)
        if chk001 is not None:
            self.chk001 = _FakeChk(chk001)
        if chk002 is not None:
            self.chk002 = _FakeChk(chk002)


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    def __init__(self, menu):
        self.option_box = _FakeOptionBox(menu)


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb000ConvertToInstancesGate(unittest.TestCase):
    """tb000 (Convert to Instances) requires ≥2 ordered-selected transforms."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = duplicate_module.Duplicate.__new__(duplicate_module.Duplicate)
        self.instance.sb = _RecordedSb()

        # Capture mtk.replace_with_instances calls.
        import mayatk as mtk
        self._original = mtk.replace_with_instances
        self.captured = []

        def fake_replace(selection, **kwargs):
            self.captured.append((tuple(selection), kwargs))

        mtk.replace_with_instances = fake_replace

    def tearDown(self):
        import mayatk as mtk
        mtk.replace_with_instances = self._original
        cmds.file(new=True, force=True)

    def _widget(self):
        return _FakeWidget(_FakeMenu(chk000=False, chk001=True, chk002=True))

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.tb000(self._widget())
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_one_object_warns(self):
        a = cmds.polyCube(name="dup_tb000_one")[0]
        cmds.select(a)
        self.instance.tb000(self._widget())
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)

    def test_two_objects_dispatches(self):
        a = cmds.polyCube(name="dup_tb000_a")[0]
        b = cmds.polyCube(name="dup_tb000_b")[0]
        cmds.select([a, b])
        self.instance.tb000(self._widget())
        self.assertEqual(len(self.captured), 1)
        # Selection is forwarded as the first positional arg.
        self.assertEqual(set(self.captured[0][0]), {a, b})

    def test_checkbox_flags_forwarded(self):
        """The three checkboxes flow through as kwargs to replace_with_instances."""
        a = cmds.polyCube(name="dup_kw_a")[0]
        b = cmds.polyCube(name="dup_kw_b")[0]
        cmds.select([a, b])
        # chk000=Freeze, chk001=DeleteHistory, chk002=CenterPivot
        widget = _FakeWidget(_FakeMenu(chk000=True, chk001=False, chk002=True))
        self.instance.tb000(widget)

        self.assertEqual(len(self.captured), 1)
        kwargs = self.captured[0][1]
        self.assertTrue(kwargs["freeze_transforms"])
        self.assertFalse(kwargs["delete_history"])
        self.assertTrue(kwargs["center_pivot"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001SelectInstancedRouting(unittest.TestCase):
    """tb001 (Select Instanced Objects) routes by chk000 = All Instanced."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = duplicate_module.Duplicate.__new__(duplicate_module.Duplicate)
        self.instance.sb = _RecordedSb()

        # Capture mtk.get_instances calls.
        import mayatk as mtk
        self._original = mtk.get_instances
        self.captured = []

        def fake_get(objects=None):
            self.captured.append(objects)
            return []  # No instances found

        mtk.get_instances = fake_get

    def tearDown(self):
        import mayatk as mtk
        mtk.get_instances = self._original
        cmds.file(new=True, force=True)

    def test_all_instanced_passes_none(self):
        """chk000=True → mtk.get_instances(objects=None) (whole scene)."""
        widget = _FakeWidget(_FakeMenu(chk000=True))
        self.instance.tb001(widget)
        self.assertEqual(self.captured, [None])

    def test_selected_only_passes_selection(self):
        """chk000=False with a selection → mtk.get_instances(selection)."""
        a = cmds.polyCube(name="dup_tb001_a")[0]
        cmds.select(a)

        widget = _FakeWidget(_FakeMenu(chk000=False))
        self.instance.tb001(widget)

        self.assertEqual(len(self.captured), 1)
        # The forwarded selection should include our cube.
        self.assertIn(a, self.captured[0])

    def test_selected_only_with_no_selection_warns(self):
        """chk000=False AND no selection → warn, don't query."""
        cmds.select(clear=True)
        widget = _FakeWidget(_FakeMenu(chk000=False))
        self.instance.tb001(widget)
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)


if __name__ == "__main__":
    unittest.main()
