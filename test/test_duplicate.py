#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.duplicate.

The mayatk duplicate_* engines (linear/radial/grid) are covered in
mayatk's test_edit_tools_duplicate; `mtk.auto_instance`/`AutoInstancer`
itself is covered in mayatk's own instancing test suite. This file pins
the *slot-layer* gating logic:

- tb000 (Convert to Instances): requires ≥2 ordered-selected objects;
  warns and skips otherwise.
- tb001 (Select Instanced Objects): routes by 'All Instanced' checkbox
  — true → all-scene, false → selection-restricted.
- tb002 (Auto Instance): forwards the option-box settings to
  `mtk.auto_instance`, selects the surviving result, and warns instead
  of silently no-op'ing when nothing matched.
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


class _FakeSpin:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _FakeMenu:
    """Fake option-box menu: chk* names become checkboxes, s* spinboxes."""

    def __init__(self, **widgets):
        for name, value in widgets.items():
            if value is None:
                continue
            fake = _FakeSpin(value) if name.startswith("s") else _FakeChk(value)
            setattr(self, name, fake)


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
    """tb001 (Select Instanced Objects) routes by chk003 = All Instanced."""

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
        """chk003=True → mtk.get_instances(objects=None) (whole scene)."""
        widget = _FakeWidget(_FakeMenu(chk003=True))
        self.instance.tb001(widget)
        self.assertEqual(self.captured, [None])

    def test_selected_only_passes_selection(self):
        """chk003=False with a selection → mtk.get_instances(selection)."""
        a = cmds.polyCube(name="dup_tb001_a")[0]
        cmds.select(a)

        widget = _FakeWidget(_FakeMenu(chk003=False))
        self.instance.tb001(widget)

        self.assertEqual(len(self.captured), 1)
        # The forwarded selection should include our cube.
        self.assertIn(a, self.captured[0])

    def test_selected_only_with_no_selection_warns(self):
        """chk003=False AND no selection → warn, don't query."""
        cmds.select(clear=True)
        widget = _FakeWidget(_FakeMenu(chk003=False))
        self.instance.tb001(widget)
        self.assertEqual(self.captured, [])
        self.assertTrue(self.instance.sb.messages)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb002AutoInstanceRouting(unittest.TestCase):
    """tb002 (Auto Instance) forwards option-box settings to mtk.auto_instance."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = duplicate_module.Duplicate.__new__(duplicate_module.Duplicate)
        self.instance.sb = _RecordedSb()

        import mayatk as mtk

        self._original = mtk.auto_instance
        self.captured = []
        self.result = []
        # Summary the slot now unpacks alongside the result list; tests may
        # mutate it to exercise the "matched but not instanced" branch.
        self.summary = mtk.AutoInstancer.default_summary()

        def fake_auto_instance(nodes, **kwargs):
            self.captured.append((nodes, kwargs))
            if kwargs.get("return_summary"):
                return self.result, self.summary
            return self.result

        mtk.auto_instance = fake_auto_instance

    def tearDown(self):
        import mayatk as mtk

        mtk.auto_instance = self._original
        cmds.file(new=True, force=True)

    def _widget(self, **overrides):
        defaults = dict(
            s000=0.001,
            chk004=True,
            chk005=False,
            chk006=False,
            chk007=False,
            chk008=False,
            chk009=True,
            chk010=True,
            chk011=True,
            s001=10000.0,
        )
        defaults.update(overrides)
        return _FakeWidget(_FakeMenu(**defaults))

    def test_passes_nodes_none_regardless_of_selection(self):
        """Scope is left to AutoInstancer's own selection→whole-scene
        fallback (mirrors tb001's 'All Instanced' whole-scene default)."""
        a = cmds.polyCube(name="dup_tb002_a")[0]
        cmds.select(a)
        self.instance.tb002(self._widget())
        self.assertEqual(len(self.captured), 1)
        self.assertIsNone(self.captured[0][0])

    def test_option_box_values_forwarded(self):
        widget = self._widget(
            s000=0.05,
            chk004=False,
            chk005=True,
            chk006=True,
            chk007=True,
            chk008=True,
            chk009=False,
            chk010=False,
            chk011=False,
            s001=250.0,
        )
        self.instance.tb002(widget)

        kwargs = self.captured[0][1]
        self.assertEqual(kwargs["tolerance"], 0.05)
        self.assertFalse(kwargs["require_same_material"])
        self.assertTrue(kwargs["check_uvs"])
        self.assertTrue(kwargs["check_hierarchy"])
        self.assertTrue(kwargs["separate_combined"])
        self.assertTrue(kwargs["combine_assemblies"])
        self.assertFalse(kwargs["combine_non_instanced"])
        self.assertFalse(kwargs["combine_by_material"])
        self.assertFalse(kwargs["combine_by_distance"])
        self.assertEqual(kwargs["combine_distance_threshold"], 250.0)

    def test_selects_surviving_result(self):
        a = cmds.polyCube(name="dup_tb002_survivor")[0]
        self.result = [a]
        self.instance.tb002(self._widget())
        self.assertEqual(cmds.ls(selection=True), [a])

    def test_no_matches_warns_instead_of_silent_noop(self):
        self.result = []
        self.instance.tb002(self._widget())
        self.assertTrue(self.instance.sb.messages)
        # No matches → generic no-match copy.
        body = self.instance.sb.messages[-1][0][0]
        self.assertIn("No matching geometry found", body)

    def test_matched_but_none_instanced_reports_reason(self):
        """Matches found but the strategy instanced none (too simple / count)
        → a distinct message explaining why, not the generic no-match copy."""
        self.result = []
        self.summary["matched_groups"] = 2
        self.summary["simple_groups"] = 2
        self.summary["details"] = [
            {"name": "Bolt", "reason": "too_simple", "count": 4, "tris": 12},
            {"name": "Nut", "reason": "too_simple", "count": 6, "tris": 8},
        ]
        self.instance.tb002(self._widget())
        self.assertTrue(self.instance.sb.messages)
        body = self.instance.sb.messages[-1][0][0]
        self.assertNotIn("No matching geometry found", body)
        self.assertIn("No objects were instanced", body)
        self.assertIn("too simple", body)


if __name__ == "__main__":
    unittest.main()
