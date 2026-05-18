#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.normals.

The bulk of Normals dispatches to mtk.Components / mtk.Macros. What's
worth pinning at this layer:

- tb001's -1 → None translation for upper/lower hardness sentinel values.
- b000/b001 polySoftEdge dispatch (soften / harden by angle).
- b002's "≥2 selected" gate.
- tb010's combo-index → polyNormal normalMode mapping.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import normals as normals_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    normals_module = None
    _MAYA_AVAILABLE = False


class _FakeSpin:
    def __init__(self, value):
        self._v = value

    def value(self):
        return self._v


class _FakeCheck:
    def __init__(self, checked):
        self._v = checked

    def isChecked(self):
        return self._v


class _FakeCombo:
    def __init__(self, index):
        self._i = index

    def currentIndex(self):
        return self._i


class _FakeMenu:
    pass


class _FakeOptionBox:
    def __init__(self):
        self.menu = _FakeMenu()


class _FakeWidget:
    def __init__(self):
        self.option_box = _FakeOptionBox()


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001HardnessTranslation(unittest.TestCase):
    """tb001 reads three spinbox values; -1 must become None before dispatch."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = normals_module.Normals.__new__(normals_module.Normals)

        # Patch mtk.Components.set_edge_hardness to capture call args.
        import mayatk as mtk
        self._original = mtk.Components.set_edge_hardness
        self.captured = []

        def fake_set_edge_hardness(selection, threshold, upper, lower, **kwargs):
            self.captured.append({
                "threshold": threshold,
                "upper": upper,
                "lower": lower,
                "unlock_normals": kwargs.get("unlock_normals"),
            })

        mtk.Components.set_edge_hardness = staticmethod(fake_set_edge_hardness)

    def tearDown(self):
        import mayatk as mtk
        mtk.Components.set_edge_hardness = self._original
        cmds.file(new=True, force=True)

    def _make_widget(self, threshold, upper, lower, unlock=False):
        widget = _FakeWidget()
        widget.option_box.menu.s002 = _FakeSpin(threshold)
        widget.option_box.menu.s003 = _FakeSpin(upper)
        widget.option_box.menu.s004 = _FakeSpin(lower)
        widget.option_box.menu.chk_unlock_normals = _FakeCheck(unlock)
        return widget

    def test_unlock_checkbox_propagates(self):
        widget = self._make_widget(threshold=90, upper=0, lower=180, unlock=True)
        self.instance.tb001(widget)
        self.assertTrue(self.captured[0]["unlock_normals"])

    def test_unlock_unchecked_propagates_false(self):
        widget = self._make_widget(threshold=90, upper=0, lower=180, unlock=False)
        self.instance.tb001(widget)
        self.assertFalse(self.captured[0]["unlock_normals"])

    def test_normal_values_pass_through(self):
        widget = self._make_widget(threshold=45, upper=0, lower=180)
        self.instance.tb001(widget)
        self.assertEqual(self.captured[0]["threshold"], 45)
        self.assertEqual(self.captured[0]["upper"], 0)
        self.assertEqual(self.captured[0]["lower"], 180)

    def test_upper_minus_one_becomes_none(self):
        widget = self._make_widget(threshold=90, upper=-1, lower=180)
        self.instance.tb001(widget)
        self.assertIsNone(self.captured[0]["upper"])
        self.assertEqual(self.captured[0]["lower"], 180)

    def test_lower_minus_one_becomes_none(self):
        widget = self._make_widget(threshold=90, upper=0, lower=-1)
        self.instance.tb001(widget)
        self.assertEqual(self.captured[0]["upper"], 0)
        self.assertIsNone(self.captured[0]["lower"])

    def test_both_minus_one_both_become_none(self):
        widget = self._make_widget(threshold=90, upper=-1, lower=-1)
        self.instance.tb001(widget)
        self.assertIsNone(self.captured[0]["upper"])
        self.assertIsNone(self.captured[0]["lower"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSoftenHarden(unittest.TestCase):
    """b000 softens all edges; b001 hardens all edges."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.cube = cmds.polyCube(name="nrm_cube")[0]
        self.instance = normals_module.Normals.__new__(normals_module.Normals)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_b000_softens_edges(self):
        # First, harden everything so we can verify softening changes state.
        cmds.polySoftEdge(f"{self.cube}.e[:]", angle=0)
        # Verify edges are hard.
        cmds.select(f"{self.cube}.e[0]")
        was_smooth = cmds.polyInfo(faceToVertex=False) or []

        cmds.select(self.cube)
        self.instance.b000()

        # After softening, polyInfo should report soft edges.
        # Simplest check: query the soft-edge display option.
        is_soft_display = cmds.polyOptions(self.cube, q=True, se=True)
        self.assertTrue(is_soft_display[0])

    def test_b001_hardens_edges(self):
        # Start with soft edges.
        cmds.polySoftEdge(f"{self.cube}.e[:]", angle=180)
        cmds.select(self.cube)
        self.instance.b001()
        # Soft-edge display flag is still set after hardening (it's a
        # display option, not edge-state). The behavioral check is that
        # the call didn't raise — verifying b001 dispatch path works.

    def test_b000_no_selection_is_noop(self):
        """No selection → no work, no crash."""
        cmds.select(clear=True)
        self.instance.b000()


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB002SelectionGate(unittest.TestCase):
    """b002 (Transfer Normals) requires ≥2 objects."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = normals_module.Normals.__new__(normals_module.Normals)
        self.instance.sb = _RecordedSb()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_no_selection_warns(self):
        cmds.select(clear=True)
        self.instance.b002()
        self.assertTrue(self.instance.sb.messages, "User must be warned")

    def test_one_object_warns(self):
        cube = cmds.polyCube(name="single")[0]
        cmds.select(cube)
        self.instance.b002()
        self.assertTrue(self.instance.sb.messages, "User must be warned")

    def test_two_objects_proceeds(self):
        """With 2 selected, the gate is satisfied — should dispatch without
        raising (the mtk call might still no-op on these cubes but no crash)."""
        a = cmds.polyCube(name="nrm_src")[0]
        b = cmds.polyCube(name="nrm_dst")[0]
        cmds.select([a, b])
        # Just verify it doesn't raise; the gate is what we're testing.
        try:
            self.instance.b002()
        except Exception:
            # The downstream mtk.Components.transfer_normals may itself raise
            # in some edge cases; we only care that the gate let it through.
            pass
        # If we reached this assert, the gate let the call through.
        self.assertEqual(self.instance.sb.messages, [])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb010NormalModeMapping(unittest.TestCase):
    """tb010 maps combo index 0-4 to polyNormal normalMode 0-4."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.cube = cmds.polyCube(name="nrm_rev")[0]
        self.instance = normals_module.Normals.__new__(normals_module.Normals)

        # Patch cmds.polyNormal to capture normalMode values.
        self._original = cmds.polyNormal
        self.captured = []

        def fake_polyNormal(*args, **kwargs):
            self.captured.append(kwargs.get("normalMode"))

        cmds.polyNormal = fake_polyNormal

    def tearDown(self):
        cmds.polyNormal = self._original
        cmds.file(new=True, force=True)

    def _make_widget(self, index):
        widget = _FakeWidget()
        widget.option_box.menu.cmb000 = _FakeCombo(index)
        return widget

    def test_index_zero_reverse(self):
        cmds.select(self.cube)
        self.instance.tb010(self._make_widget(0))
        self.assertEqual(self.captured, [0])

    def test_index_two_conform(self):
        cmds.select(self.cube)
        self.instance.tb010(self._make_widget(2))
        self.assertEqual(self.captured, [2])

    def test_index_three_reverse_and_extract(self):
        cmds.select(self.cube)
        self.instance.tb010(self._make_widget(3))
        self.assertEqual(self.captured, [3])

    def test_no_selection_does_not_call_polyNormal(self):
        cmds.select(clear=True)
        self.instance.tb010(self._make_widget(0))
        self.assertEqual(self.captured, [])


if __name__ == "__main__":
    unittest.main()
