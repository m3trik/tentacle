#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.symmetry.

The units worth pinning:

- chk000/1/2: each axis (x/y/z) maps to cmds.symmetricModelling(axis=...).
- chk004 (Object space): selecting the radio restores about="object" (after a Topo
  session `about` would otherwise stay "topo"); deselection must be a no-op (radio
  signal ordering — Topo sets about="topo" itself).
- chk005 (Topo symmetry): requires an edge selection; catches RuntimeError
  when activation fails and warns.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import symmetry as symmetry_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    symmetry_module = None
    _MAYA_AVAILABLE = False


class _RecordedSb:
    def __init__(self):
        self.messages = []
        self.toggle_calls = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))

    def toggle_multi(self, target, **kwargs):
        self.toggle_calls.append((target, kwargs))


class _FakeCheckbox:
    def __init__(self):
        self.checked = None

    def setChecked(self, value):
        self.checked = value


class _FakeUi:
    def __init__(self):
        self.chk004 = _FakeCheckbox()


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestChkAxes(unittest.TestCase):
    """chk000/1/2 each set a different axis on cmds.symmetricModelling."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = symmetry_module.Symmetry.__new__(symmetry_module.Symmetry)
        self.instance.sb = _RecordedSb()

        # Stateful stub: edits mutate state, queries read it — so the feedback popup
        # (which queries the scene back) sees the same result a real toggle would.
        self._orig = cmds.symmetricModelling
        self.calls = []
        self.state = {"symmetry": 0, "axis": "x", "about": "object"}

        def fake_symmetric_modelling(**kw):
            self.calls.append(kw)
            if kw.get("edit"):
                for key in ("symmetry", "axis", "about"):
                    if key in kw:
                        self.state[key] = int(bool(kw[key])) if key == "symmetry" else kw[key]
            elif kw.get("query"):
                for key in ("symmetry", "axis", "about"):
                    if kw.get(key):
                        return self.state[key]
            return None

        cmds.symmetricModelling = fake_symmetric_modelling

    def tearDown(self):
        cmds.symmetricModelling = self._orig
        cmds.file(new=True, force=True)

    @property
    def edit_calls(self):
        """Just the edit calls — filters out the query calls the feedback popup makes."""
        return [c for c in self.calls if c.get("edit")]

    def test_chk000_sets_x(self):
        self.instance.chk000(state=True, widget=None)
        self.assertEqual(self.edit_calls[-1]["axis"], "x")
        self.assertTrue(self.edit_calls[-1]["symmetry"])

    def test_chk001_sets_y(self):
        self.instance.chk001(state=True, widget=None)
        self.assertEqual(self.edit_calls[-1]["axis"], "y")

    def test_chk002_sets_z(self):
        self.instance.chk002(state=True, widget=None)
        self.assertEqual(self.edit_calls[-1]["axis"], "z")

    def test_unchecked_disables_symmetry(self):
        """state=False → symmetry=False (axis still set, but disabled)."""
        self.instance.chk000(state=False, widget=None)
        self.assertFalse(self.edit_calls[-1]["symmetry"])

    def test_chk004_selected_sets_object_space(self):
        self.instance.chk004(state=True, widget=None)
        self.assertEqual(self.edit_calls[-1]["about"], "object")

    def test_chk004_deselected_is_noop(self):
        """Deselection happens when Topo takes over — it must not clobber about='topo'."""
        self.instance.chk004(state=False, widget=None)
        self.assertEqual(self.calls, [])

    def _last_message(self):
        """The text of the most recent message_box call (args[0])."""
        args, _kwargs = self.instance.sb.messages[-1]
        return args[0]

    def test_axis_on_posts_space_and_highlighted_axis(self):
        """A live axis toggle queries the scene and posts ``Symmetry: <space> <hl>axis</hl>``."""
        self.instance.chk000(state=True, widget=None)
        self.assertTrue(any(c.get("query") for c in self.calls), "should query state back")
        self.assertEqual(self._last_message(), "Symmetry: Object <hl>X</hl>")

    def test_symmetry_off_posts_no_feedback(self):
        """Turning symmetry off is silent — no message box for the off state."""
        self.instance.chk000(state=False, widget=None)
        self.assertEqual(self.instance.sb.messages, [])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestChk005Topo(unittest.TestCase):
    """chk005 (Topo): the no-edge and activation-failure paths must revert the
    radio group to Object space (chk004) and warn — a regression that drops the
    revert leaves Topo checked while the scene stays object-space."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = symmetry_module.Symmetry.__new__(symmetry_module.Symmetry)
        self.instance.sb = _RecordedSb()
        self.instance.ui = _FakeUi()

        self._orig_sym = cmds.symmetricModelling
        self._orig_filter = cmds.filterExpand
        self.edges = None  # what the edge-selection filterExpand returns
        self.raise_on_topo = False
        self.calls = []
        self.state = {"symmetry": 0, "axis": "x", "about": "object"}

        def fake_symmetric_modelling(**kw):
            self.calls.append(kw)
            if kw.get("edit"):
                if self.raise_on_topo and kw.get("about") == "topo":
                    raise RuntimeError("activation failed")
                for key in ("symmetry", "axis", "about"):
                    if key in kw:
                        self.state[key] = (
                            int(bool(kw[key])) if key == "symmetry" else kw[key]
                        )
            elif kw.get("query"):
                for key in ("symmetry", "axis", "about"):
                    if kw.get(key):
                        return self.state[key]
            return None

        cmds.symmetricModelling = fake_symmetric_modelling
        cmds.filterExpand = lambda **kw: self.edges

    def tearDown(self):
        cmds.symmetricModelling = self._orig_sym
        cmds.filterExpand = self._orig_filter
        cmds.file(new=True, force=True)

    def _last_message(self):
        args, _kwargs = self.instance.sb.messages[-1]
        return args[0]

    def test_no_edge_reverts_to_object_radio_and_warns(self):
        self.edges = None
        self.instance.chk005(state=True, widget=None)
        self.assertTrue(self.instance.ui.chk004.checked)
        self.assertIn("Select an edge first", self._last_message())
        self.assertFalse(
            any(c.get("edit") for c in self.calls),
            "must return before editing symmetricModelling",
        )

    def test_activation_failure_reverts_to_object_radio_and_warns(self):
        self.edges = ["pCube1.e[0]"]
        self.raise_on_topo = True
        self.instance.chk005(state=True, widget=None)
        self.assertTrue(self.instance.ui.chk004.checked)
        self.assertIn("could not be activated", self._last_message())

    def test_success_posts_topological_feedback(self):
        self.edges = ["pCube1.e[0]"]
        self.instance.chk005(state=True, widget=None)
        self.assertEqual(self._last_message(), "Symmetry: <hl>Topological</hl>")


if __name__ == "__main__":
    unittest.main()
