#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.pivot.

The substantive unit at this layer is tb001 (Center Pivot) — a three-way
radio dispatch between Component/Object/World that calls different
cmds.xform paths. If the radio handler order drifts, the wrong pivot
behavior would ship silently.

tb003 (World-Aligned Pivot) similarly routes by checkbox to manip vs
object pivot — pin the routing.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import pivot as pivot_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    pivot_module = None
    _MAYA_AVAILABLE = False


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeMenu:
    def __init__(self, **flags):
        for k, v in flags.items():
            setattr(self, k, _FakeChk(v))


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    def __init__(self, menu):
        self.option_box = _FakeOptionBox(menu)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001CenterPivot(unittest.TestCase):
    """tb001 Center Pivot routes on Component / Object / World radio."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = pivot_module.Pivot.__new__(pivot_module.Pivot)
        # Capture the real xform — install the stub later, after each test
        # has built its scene, so cmds.polyCube doesn't get intercepted.
        self._original_xform = cmds.xform
        self.xform_calls = []

    def tearDown(self):
        cmds.xform = self._original_xform
        cmds.file(new=True, force=True)

    def _install_xform_stub(self):
        cmds.xform = lambda *a, **kw: self.xform_calls.append((a, kw))

    def _widget(self, component=False, object_=False, world=False):
        return _FakeWidget(
            _FakeMenu(chk002=component, chk003=object_, chk004=world)
        )

    def test_no_selection_is_noop(self):
        """tb001 with no selection returns early — no xform call."""
        cmds.select(clear=True)
        self._install_xform_stub()
        self.instance.tb001(self._widget(object_=True))
        self.assertEqual(self.xform_calls, [])

    def test_object_mode_calls_center_pivots(self):
        """Object radio → cmds.xform(centerPivots=1)."""
        cube = cmds.polyCube(name="pv_obj")[0]
        cmds.select(cube)
        self._install_xform_stub()

        self.instance.tb001(self._widget(object_=True))

        self.assertEqual(len(self.xform_calls), 1)
        _, kw = self.xform_calls[0]
        self.assertTrue(kw.get("centerPivots"))

    def test_component_mode_calls_center_on_components(self):
        """Component radio → cmds.xform(centerPivotsOnComponents=1)."""
        cube = cmds.polyCube(name="pv_comp")[0]
        cmds.select(cube)
        self._install_xform_stub()

        self.instance.tb001(self._widget(component=True))

        self.assertEqual(len(self.xform_calls), 1)
        _, kw = self.xform_calls[0]
        self.assertTrue(kw.get("centerPivotsOnComponents"))

    def test_world_mode_sets_pivots_origin(self):
        """World radio → cmds.xform(worldSpace=1, pivots=[0,0,0])."""
        cube = cmds.polyCube(name="pv_world")[0]
        cmds.select(cube)
        self._install_xform_stub()

        self.instance.tb001(self._widget(world=True))

        self.assertEqual(len(self.xform_calls), 1)
        _, kw = self.xform_calls[0]
        self.assertTrue(kw.get("worldSpace"))
        self.assertEqual(kw.get("pivots"), [0, 0, 0])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb003WorldAlignedPivot(unittest.TestCase):
    """tb003 routes manip pivot vs object pivot based on chk010."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = pivot_module.Pivot.__new__(pivot_module.Pivot)

        # Capture mtk.world_align_pivot calls.
        import mayatk as mtk
        self._original = mtk.world_align_pivot
        self.captured = []

        def fake_align(mode, pivot_type):
            self.captured.append({"mode": mode, "pivot_type": pivot_type})
            return True

        mtk.world_align_pivot = fake_align

    def tearDown(self):
        import mayatk as mtk
        mtk.world_align_pivot = self._original
        cmds.file(new=True, force=True)

    def _widget(self, manip):
        return _FakeWidget(_FakeMenu(chk010=manip))

    def test_manip_checked_routes_to_manip_type(self):
        """chk010=True → mode='set', pivot_type='manip'."""
        self.instance.tb003(self._widget(manip=True))
        self.assertEqual(len(self.captured), 1)
        self.assertEqual(self.captured[0]["pivot_type"], "manip")
        self.assertEqual(self.captured[0]["mode"], "set")

    def test_manip_unchecked_routes_to_object_type(self):
        """chk010=False → mode='set', pivot_type='object'."""
        self.instance.tb003(self._widget(manip=False))
        self.assertEqual(len(self.captured), 1)
        self.assertEqual(self.captured[0]["pivot_type"], "object")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB004BakePivot(unittest.TestCase):
    """b004 (Bake Pivot) delegates to mtk.bake_pivot with the current selection."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = pivot_module.Pivot.__new__(pivot_module.Pivot)
        import mayatk as mtk
        self._original = mtk.bake_pivot
        self.captured = []

        def fake_bake(selection, **kwargs):
            self.captured.append((tuple(selection), kwargs))

        mtk.bake_pivot = fake_bake

    def tearDown(self):
        import mayatk as mtk
        mtk.bake_pivot = self._original
        cmds.file(new=True, force=True)

    def test_b004_forwards_selection_and_flags(self):
        """b004 forwards the selection with position=True, orientation=True."""
        a = cmds.polyCube(name="bake_a")[0]
        cmds.select(a)
        self.instance.b004()

        self.assertEqual(len(self.captured), 1)
        sel, kwargs = self.captured[0]
        self.assertIn(a, sel)
        self.assertTrue(kwargs["position"])
        self.assertTrue(kwargs["orientation"])

    def test_b004_empty_selection_still_dispatches(self):
        """b004 with empty selection passes [] (no message-box guard)."""
        cmds.select(clear=True)
        self.instance.b004()
        self.assertEqual(len(self.captured), 1)
        self.assertEqual(self.captured[0][0], ())


if __name__ == "__main__":
    unittest.main()
