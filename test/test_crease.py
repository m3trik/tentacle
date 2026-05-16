#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.crease.

crease.py has two slot methods worth pinning:

- tb000 (Crease): forwards widget s003 (amount) + s004 (angle) to
  mtk.Components.crease_edges.
- b002 (Transfer Crease Edges): uses ``source, *targets = cmds.ls(...)``
  unpacking. Empty selection raises ValueError; the handler catches it
  and shows a message.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import crease as crease_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    crease_module = None
    _MAYA_AVAILABLE = False


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


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb000Crease(unittest.TestCase):
    """tb000 forwards crease amount + angle to mtk.Components.crease_edges."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = crease_module.Crease.__new__(crease_module.Crease)

        import mayatk as mtk
        self._orig = mtk.Components.crease_edges
        self.calls = []
        mtk.Components.crease_edges = lambda **kw: self.calls.append(kw)

    def tearDown(self):
        import mayatk as mtk
        mtk.Components.crease_edges = self._orig
        cmds.file(new=True, force=True)

    def _widget(self, amount, angle):
        return _FakeWidget(
            _FakeMenu(s003=_FakeSpin(amount), s004=_FakeSpin(angle))
        )

    def test_amount_and_angle_forwarded(self):
        self.instance.tb000(self._widget(amount=8, angle=45))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["amount"], 8)
        self.assertEqual(self.calls[0]["angle"], 45)

    def test_zero_amount_is_passed_through(self):
        """Amount=0 (no crease) should still call through, not warn."""
        self.instance.tb000(self._widget(amount=0, angle=30))
        self.assertEqual(self.calls[0]["amount"], 0)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB002TransferCreaseEdges(unittest.TestCase):
    """b002 catches ValueError from ``source, *targets = selection`` when
    selection is empty, and shows a message."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = crease_module.Crease.__new__(crease_module.Crease)
        self.instance.sb = _RecordedSb()

        import mayatk as mtk
        self._orig = mtk.Components.transfer_creased_edges
        self.calls = []
        mtk.Components.transfer_creased_edges = lambda src, tgts: self.calls.append(
            (src, list(tgts))
        )

    def tearDown(self):
        import mayatk as mtk
        mtk.Components.transfer_creased_edges = self._orig
        cmds.file(new=True, force=True)

    def test_empty_selection_warns_and_skips(self):
        cmds.select(clear=True)
        self.instance.b002(widget=None)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.instance.sb.messages)

    def test_one_object_dispatches_with_empty_targets(self):
        """Single selection: source, *targets = [a] → source=a, targets=[]."""
        a = cmds.polyCube(name="cr_a")[0]
        cmds.select(a)
        self.instance.b002(widget=None)
        self.assertEqual(len(self.calls), 1)
        src, tgts = self.calls[0]
        self.assertEqual(src, a)
        self.assertEqual(tgts, [])

    def test_two_objects_dispatches_source_and_targets(self):
        a = cmds.polyCube(name="cr_src")[0]
        b = cmds.polyCube(name="cr_tgt")[0]
        cmds.select([a, b])
        self.instance.b002(widget=None)
        self.assertEqual(len(self.calls), 1)
        src, tgts = self.calls[0]
        self.assertEqual(src, a)
        self.assertEqual(tgts, [b])


if __name__ == "__main__":
    unittest.main()
