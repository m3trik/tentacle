#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.preferences.

preferences.py is mostly Maya unit/autosave widget wiring. The units
worth pinning at this layer:

- cmb001: sets cmds.currentUnit(linear=...) from widget.currentData(),
  lowercased — case drift would silently break the option.
- cmb002: sets cmds.currentUnit(time=...) — pin the unit name forwarded.
- b002 (Autosave Delete All): iterates mtk.get_recent_autosave() and
  os.remove()s each file. Captures the (file, _) tuple unpacking.
"""
import os
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


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB002DeleteAutosaves(unittest.TestCase):
    """b002 iterates mtk.get_recent_autosave() (file, ts tuples) and
    deletes the files via os.remove. Errors are swallowed (print only)."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )

        import mayatk as mtk
        self._orig = mtk.get_recent_autosave
        # Will be set per-test:
        self.fake_files = []
        mtk.get_recent_autosave = lambda: self.fake_files

        self._orig_remove = os.remove
        self.removed = []
        os.remove = lambda path: self.removed.append(path)

    def tearDown(self):
        import mayatk as mtk
        mtk.get_recent_autosave = self._orig
        os.remove = self._orig_remove
        cmds.file(new=True, force=True)

    def test_removes_every_listed_file(self):
        self.fake_files = [
            ("/tmp/scene1.ma", 100),
            ("/tmp/scene2.ma", 200),
        ]
        self.instance.b002()
        self.assertEqual(self.removed, ["/tmp/scene1.ma", "/tmp/scene2.ma"])

    def test_empty_list_is_noop(self):
        self.fake_files = []
        self.instance.b002()
        self.assertEqual(self.removed, [])

    def test_os_remove_failure_is_swallowed(self):
        """A missing-file error should not crash b002."""
        self.fake_files = [("/tmp/missing.ma", 100), ("/tmp/ok.ma", 200)]

        def fake_remove(path):
            if path == "/tmp/missing.ma":
                raise OSError("no such file")
            self.removed.append(path)

        os.remove = fake_remove

        # Should not raise.
        self.instance.b002()
        # Second file still removed.
        self.assertEqual(self.removed, ["/tmp/ok.ma"])


if __name__ == "__main__":
    unittest.main()
