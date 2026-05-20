#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.nurbs.

Most of nurbs.py is a flat mel.eval dispatch table for NURBS edit
operations. The units worth pinning at this layer:

- tb000 (Revolve): widget values → cmds.revolve kwargs.
- b056 (Image Tracer): marking-menu key name.
- b016 (Extract Curve): Exception fallback to mtk.create_curve_from_edges.
- tb001 (Loft): forwards 10 widget values to mtk.loft. Pins the
  contract after the 2026-05-16 fix that replaced a 2-year-old
  ``self.loft`` typo (no such method existed) with ``mtk.loft``.
"""
import unittest

try:
    import maya.cmds as cmds
    import maya.mel as mel
    from tentacle.slots.maya import nurbs as nurbs_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    mel = None
    nurbs_module = None
    _MAYA_AVAILABLE = False


class _FakeChk:
    def __init__(self, state):
        self._state = state

    def isChecked(self):
        return self._state


class _FakeSpin:
    def __init__(self, val):
        self._v = val

    def value(self):
        return self._v


class _FakeMenu:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeOptionBox:
    def __init__(self, menu):
        self.menu = menu


class _FakeWidget:
    def __init__(self, menu):
        self.option_box = _FakeOptionBox(menu)


class _FakeMarkingMenu:
    def __init__(self):
        self.shown = []

    def show(self, name):
        self.shown.append(name)


class _FakeHandlers:
    def __init__(self):
        self.marking_menu = _FakeMarkingMenu()


class _RecordedSb:
    def __init__(self):
        self.messages = []
        self.handlers = _FakeHandlers()

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb000Revolve(unittest.TestCase):
    """tb000 forwards widget values to cmds.revolve as kwargs."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = nurbs_module.Nurbs.__new__(nurbs_module.Nurbs)

        self._orig = cmds.revolve
        self.captured = []
        cmds.revolve = lambda *a, **kw: self.captured.append((a, kw)) or "rev1"

    def tearDown(self):
        cmds.revolve = self._orig
        cmds.file(new=True, force=True)

    def _widget(
        self,
        degree=3,
        startSweep=0,
        endSweep=360,
        sections=8,
        range_=False,
        polygon=True,
        useTolerance=False,
        tolerance=0.001,
    ):
        return _FakeWidget(
            _FakeMenu(
                s002=_FakeSpin(degree),
                s003=_FakeSpin(startSweep),
                s004=_FakeSpin(endSweep),
                s005=_FakeSpin(sections),
                chk006=_FakeChk(range_),
                chk007=_FakeChk(polygon),
                chk009=_FakeChk(useTolerance),
                s006=_FakeSpin(tolerance),
            )
        )

    def test_forwards_widget_values_to_revolve(self):
        cmds.select(clear=True)  # cmds.revolve is mocked; selection doesn't matter
        self.instance.tb000(
            self._widget(degree=5, startSweep=10, endSweep=350, sections=16)
        )

        self.assertEqual(len(self.captured), 1)
        kw = self.captured[0][1]
        self.assertEqual(kw["degree"], 5)
        self.assertEqual(kw["ssw"], 10)
        self.assertEqual(kw["esw"], 350)
        self.assertEqual(kw["s"], 16)

    def test_polygon_checkbox_forwarded_as_int(self):
        """chk007 (Polygon) is forwarded as 1/0, not bool."""
        self.instance.tb000(self._widget(polygon=True))
        self.assertEqual(self.captured[-1][1]["po"], 1)

        self.instance.tb000(self._widget(polygon=False))
        self.assertEqual(self.captured[-1][1]["po"], 0)

    def test_revolve_axis_is_y(self):
        """The axis stays pinned to Y (= [0, 1, 0]) by the slot."""
        self.instance.tb000(self._widget())
        self.assertEqual(self.captured[-1][1]["ax"], [0, 1, 0])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB056ImageTracer(unittest.TestCase):
    """b056 shows the 'image_tracer' marking menu."""

    def test_b056_routes_to_image_tracer(self):
        instance = nurbs_module.Nurbs.__new__(nurbs_module.Nurbs)
        instance.sb = _RecordedSb()
        instance.b056()
        self.assertEqual(instance.sb.handlers.marking_menu.shown, ["image_tracer"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB016ExtractCurveFallback(unittest.TestCase):
    """b016 falls back to mtk.create_curve_from_edges on any Exception."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = nurbs_module.Nurbs.__new__(nurbs_module.Nurbs)

        self._orig_mel = mel.eval

        import mayatk as mtk
        self._orig_create = mtk.create_curve_from_edges
        self.fallback_calls = []
        mtk.create_curve_from_edges = lambda: self.fallback_calls.append("called")

    def tearDown(self):
        mel.eval = self._orig_mel
        import mayatk as mtk
        mtk.create_curve_from_edges = self._orig_create
        cmds.file(new=True, force=True)

    def test_mel_success_skips_fallback(self):
        """When CreateCurveFromPoly succeeds, fallback is not invoked."""
        mel.eval = lambda s: None
        self.instance.b016()
        self.assertEqual(self.fallback_calls, [])

    def test_mel_failure_invokes_fallback(self):
        """When CreateCurveFromPoly raises, fallback is invoked."""
        def raise_(s):
            raise RuntimeError("no faces selected")

        mel.eval = raise_
        self.instance.b016()
        self.assertEqual(self.fallback_calls, ["called"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb001LoftForwardsToMtk(unittest.TestCase):
    """tb001 forwards 10 widget values as kwargs to mtk.loft.

    Pins the contract after fixing a 2-year-old typo (``self.loft``
    referenced a method that never existed on Nurbs or its base; the
    fix is ``mtk.loft``). If the call signature drifts again, this test
    catches it.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = nurbs_module.Nurbs.__new__(nurbs_module.Nurbs)

        import mayatk as mtk
        self._orig = mtk.loft
        self.captured = []
        mtk.loft = lambda **kw: self.captured.append(kw)

    def tearDown(self):
        import mayatk as mtk
        mtk.loft = self._orig
        cmds.file(new=True, force=True)

    def _widget(
        self,
        uniform=True,
        close=False,
        degree=3,
        autoReverse=False,
        sectionSpans=1,
        range_=False,
        polygon=True,
        reverseSurfaceNormals=True,
        angle_loft=False,
        angle_loft_spans=6,
    ):
        return _FakeWidget(
            _FakeMenu(
                chk000=_FakeChk(uniform),
                chk001=_FakeChk(close),
                s000=_FakeSpin(degree),
                chk002=_FakeChk(autoReverse),
                s001=_FakeSpin(sectionSpans),
                chk003=_FakeChk(range_),
                chk004=_FakeChk(polygon),
                chk005=_FakeChk(reverseSurfaceNormals),
                chk010=_FakeChk(angle_loft),
                s007=_FakeSpin(angle_loft_spans),
            )
        )

    def test_forwards_all_ten_kwargs(self):
        self.instance.tb001(
            self._widget(
                uniform=True,
                close=True,
                degree=5,
                autoReverse=True,
                sectionSpans=4,
                range_=False,
                polygon=True,
                reverseSurfaceNormals=False,
                angle_loft=True,
                angle_loft_spans=8,
            )
        )
        self.assertEqual(len(self.captured), 1)
        kw = self.captured[0]
        self.assertTrue(kw["uniform"])
        self.assertTrue(kw["close"])
        self.assertEqual(kw["degree"], 5)
        self.assertTrue(kw["autoReverse"])
        self.assertEqual(kw["sectionSpans"], 4)
        self.assertFalse(kw["range_"])
        self.assertEqual(kw["polygon"], 1)  # bool→int conversion in the slot
        self.assertFalse(kw["reverseSurfaceNormals"])
        self.assertTrue(kw["angle_loft_between_two_curves"])
        self.assertEqual(kw["angleLoftSpans"], 8)

    def test_polygon_unchecked_forwards_zero(self):
        """Polygon checkbox is bool but forwarded as 1/0, not True/False."""
        self.instance.tb001(self._widget(polygon=False))
        self.assertEqual(self.captured[0]["polygon"], 0)


if __name__ == "__main__":
    unittest.main()
