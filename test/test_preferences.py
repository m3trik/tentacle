#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.preferences.

preferences.py is mostly Maya unit/autosave widget wiring. The units
worth pinning at this layer:

- cmb001: sets cmds.currentUnit(linear=...) from widget.currentData(),
  lowercased — case drift would silently break the option.
- cmb002: sets cmds.currentUnit(time=...) — pin the unit name forwarded.

- cmb003: app-style / theme selector. Its slot forwards the picked template
  (widget.currentData()) to mtk.StyleSetter.apply_template — pin that wiring.

(A prior b002 "Autosave Delete All" handler was removed 2026-07-02 as dead code;
b002 was briefly reused 2026-07-04 for a "Match Style" push-button, then that was
replaced the same day by the cmb003 combo — a theme selector mirroring the app's
native theme dropdown. See Preferences.cmb003 here and in slots/blender/preferences.py.)
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import preferences as preferences_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    preferences_module = None
    _MAYA_AVAILABLE = False


class _FakeWidget:
    def __init__(self, current_data):
        self._d = current_data

    def currentData(self):
        return self._d


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb001SetLinearUnit(unittest.TestCase):
    """cmb001 forwards widget.currentData().lower() to cmds.currentUnit."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )
        self._orig = cmds.currentUnit
        self.calls = []
        cmds.currentUnit = lambda **kw: (
            self.calls.append(kw) or None
        )

    def tearDown(self):
        cmds.currentUnit = self._orig
        cmds.file(new=True, force=True)

    def test_lowercases_unit_value(self):
        """The unit name is lowercased before forwarding (cmds expects lc)."""
        self.instance.cmb001(0, _FakeWidget("Meter"))
        self.assertEqual(self.calls, [{"linear": "meter"}])

    def test_known_unit_name_forwarded(self):
        for unit in ("millimeter", "centimeter", "meter", "kilometer", "inch"):
            self.calls.clear()
            self.instance.cmb001(0, _FakeWidget(unit))
            self.assertEqual(self.calls, [{"linear": unit}])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb002SetTimeUnit(unittest.TestCase):
    """cmb002 sets cmds.currentUnit(time=...) from widget.currentData()."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )
        self._orig = cmds.currentUnit
        self.calls = []
        cmds.currentUnit = lambda **kw: self.calls.append(kw)

    def tearDown(self):
        cmds.currentUnit = self._orig
        cmds.file(new=True, force=True)

    def test_film_fps_forwarded(self):
        """Time mode names (game/film/pal/ntsc/show/palf/ntscf) flow through."""
        self.instance.cmb002(0, _FakeWidget("film"))
        self.assertEqual(self.calls, [{"time": "film"}])

    def test_ntsc_fps_forwarded(self):
        self.instance.cmb002(0, _FakeWidget("ntsc"))
        self.assertEqual(self.calls, [{"time": "ntsc"}])


class _FakeCombo:
    """Minimal stand-in for the uitk ComboBox: records add()/setCurrentIndex and returns a
    chosen currentData(), so cmb003_init/cmb003 can be exercised without a real widget.

    Faithful to the real ComboBox contract that tripped up the first draft: ``.items`` returns the
    item DATA values (``itemData`` when set), NOT the display labels — so the slot must index by a
    template's token, not its display name."""

    def __init__(self, current_data=None):
        self.is_initialized = False
        self.items = []
        self._current_data = current_data
        self.current_index = None

    def add(self, mapping):
        self.items = list(mapping.values())  # data values, matching the real ComboBox.items

    def setCurrentIndex(self, i):
        self.current_index = i

    def currentData(self):
        return self._current_data


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb003StyleSelector(unittest.TestCase):
    """cmb003 is the app-style selector. Its init just populates from
    mtk.StyleSetter.list_templates() (no backup/auto-select — removed 2026-07-05, see the mayatk
    CHANGELOG); picking an entry forwards its token to apply_template. Both are mocked here so the
    wiring is pinned without touching real Maya color prefs."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_init_populates_from_list_templates(self):
        import mayatk as mtk

        # Tokens deliberately DIFFER from display names (as Blender's real filepath tokens do) so
        # this pins that .items holds tokens, not labels, even though nothing gets auto-selected.
        orig_list = mtk.StyleSetter.list_templates
        mtk.StyleSetter.list_templates = staticmethod(lambda: {"Maya": "tok_maya", "Blender": "tok_blender"})
        try:
            widget = _FakeCombo()
            self.instance.cmb003_init(widget)
        finally:
            mtk.StyleSetter.list_templates = orig_list
        self.assertEqual(widget.items, ["tok_maya", "tok_blender"])  # .items are DATA tokens
        self.assertIsNone(widget.current_index)  # no auto-select — mirrors the native dropdown

    def test_select_forwards_token_to_apply_template(self):
        import mayatk as mtk

        calls = []
        orig = mtk.StyleSetter.apply_template
        mtk.StyleSetter.apply_template = staticmethod(lambda token, **kw: calls.append(token))
        try:
            self.instance.cmb003(1, _FakeCombo(current_data="Blender"))
        finally:
            mtk.StyleSetter.apply_template = orig
        self.assertEqual(calls, ["Blender"])


if __name__ == "__main__":
    unittest.main()
