#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.hud WarningsMixin gating.

Bug: warnings (e.g. autosave-off, default-framerate) fired on brand-new
untitled scenes during initial setup, creating noise. The mixin now
short-circuits when chk_warn_skip_unsaved is enabled (default) AND no
scene file exists on disk yet.
"""
import os
import tempfile
import unittest

try:
    from tentacle.slots.maya import hud
    _MAYA_AVAILABLE = True
except ImportError:
    # tentacle.slots.maya.hud imports maya.cmds at module load; in plain
    # Python (no Maya runtime) this raises. The whole test module then
    # has nothing meaningful to do — skip cleanly.
    hud = None
    _MAYA_AVAILABLE = False


class _FakeCmds:
    """Stand-in for maya.cmds covering only what hud._scene_is_unsaved needs."""

    def __init__(self, scene_name: str):
        self._scene_name = scene_name

    def file(self, query=False, sceneName=False):
        if query and sceneName:
            return self._scene_name
        return ""


class _FakeCheckbox:
    def __init__(self, checked: bool):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _FakePrefs:
    def __init__(self, **flags):
        for k, v in flags.items():
            setattr(self, k, _FakeCheckbox(v))


class _FakeLoadedUi:
    def __init__(self, prefs):
        self.preferences = prefs


class _FakeSb:
    def __init__(self, prefs):
        self.loaded_ui = _FakeLoadedUi(prefs)


if _MAYA_AVAILABLE:

    class _GateOnlyHarness(hud.WarningsMixin):
        """Strip WARNING_DEFS so we test only the unsaved-scene gate, not real checks."""

        WARNING_DEFS = (
            {
                "key": "chk_warn_dummy",
                "icon": "!",
                "color": "Red",
                "label": "Dummy",
                "check": lambda self: True,
                "describe": lambda self: "dummy",
            },
        )

else:
    _GateOnlyHarness = None  # type: ignore[assignment]


class TestSharedMixinGating(unittest.TestCase):
    """The DCC-agnostic framework (tentacle.slots._hud_warnings) — runs without any DCC.

    Covers the gating logic the Maya-gated tests above exercise through the Maya subclass,
    so CI keeps coverage even where maya.cmds can't import.
    """

    def _make(self, unsaved, skip_unsaved, dummy=True):
        from tentacle.slots._hud_warnings import HudWarningsMixin

        class _Harness(HudWarningsMixin):
            WARNING_DEFS = (
                {
                    "key": "chk_warn_dummy",
                    "icon": "!",
                    "color": "Red",
                    "label": "Dummy",
                    "check": lambda self: True,
                    "describe": lambda self: "dummy",
                },
            )

            def _scene_is_unsaved(self):
                return unsaved

        instance = _Harness()
        instance.sb = _FakeSb(
            _FakePrefs(chk_warn_skip_unsaved=skip_unsaved, chk_warn_dummy=dummy)
        )
        return instance

    def test_skip_unsaved_gate_blocks(self):
        self.assertEqual(self._make(unsaved=True, skip_unsaved=True).evaluate_warnings(), [])

    def test_gate_off_lets_warnings_through(self):
        self.assertEqual(len(self._make(unsaved=True, skip_unsaved=False).evaluate_warnings()), 1)

    def test_saved_scene_lets_warnings_through(self):
        self.assertEqual(len(self._make(unsaved=False, skip_unsaved=True).evaluate_warnings()), 1)

    def test_disabled_warning_never_fires(self):
        self.assertEqual(
            self._make(unsaved=False, skip_unsaved=False, dummy=False).evaluate_warnings(), []
        )

    def test_missing_prefs_means_disabled(self):
        instance = self._make(unsaved=False, skip_unsaved=False)
        instance.sb = type("Sb", (), {})()  # no loaded_ui at all
        self.assertEqual(instance.evaluate_warnings(), [])

    def test_icon_and_detail_rendering(self):
        instance = self._make(unsaved=False, skip_unsaved=False)
        warnings = instance.evaluate_warnings()
        texts = []
        hud = type("Hud", (), {"insertText": lambda self, t: texts.append(t)})()
        instance.insert_warning_icons(hud, warnings)
        instance.insert_warning_details(hud, warnings)
        self.assertEqual(len(texts), 2)
        self.assertIn("Dummy", texts[0])
        self.assertEqual(texts[1], "dummy")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestUnsavedSceneGate(unittest.TestCase):
    _SENTINEL = object()

    def setUp(self):
        self._original_cmds = getattr(hud, "cmds", self._SENTINEL)

    def tearDown(self):
        if self._original_cmds is self._SENTINEL:
            if hasattr(hud, "cmds"):
                delattr(hud, "cmds")
        else:
            hud.cmds = self._original_cmds

    def _make(self, scene_name, skip_unsaved, dummy=True):
        instance = _GateOnlyHarness.__new__(_GateOnlyHarness)
        instance.sb = _FakeSb(
            _FakePrefs(chk_warn_skip_unsaved=skip_unsaved, chk_warn_dummy=dummy)
        )
        hud.cmds = _FakeCmds(scene_name)
        return instance

    def test_gate_blocks_when_scene_untitled_and_skip_enabled(self):
        instance = self._make("", skip_unsaved=True)
        self.assertEqual(instance.evaluate_warnings(), [])

    def test_gate_blocks_when_scene_path_does_not_exist(self):
        instance = self._make("C:/nope/missing.ma", skip_unsaved=True)
        self.assertEqual(instance.evaluate_warnings(), [])

    def test_gate_off_lets_warnings_through_on_untitled(self):
        instance = self._make("", skip_unsaved=False)
        self.assertEqual(len(instance.evaluate_warnings()), 1)

    def test_gate_with_real_saved_scene_lets_warnings_through(self):
        with tempfile.NamedTemporaryFile(suffix=".ma", delete=False) as tmp:
            path = tmp.name
        try:
            instance = self._make(path, skip_unsaved=True)
            self.assertEqual(len(instance.evaluate_warnings()), 1)
        finally:
            os.unlink(path)

    def test_default_pref_value_is_checked(self):
        """The .ui must ship chk_warn_skip_unsaved checked by default."""
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tentacle", "ui", "preferences.ui",
        )
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        idx = content.find('name="chk_warn_skip_unsaved"')
        self.assertNotEqual(idx, -1, "chk_warn_skip_unsaved missing from preferences.ui")
        widget_end = content.find("</widget>", idx)
        widget_block = content[idx:widget_end]
        self.assertIn("<bool>true</bool>", widget_block,
                      "chk_warn_skip_unsaved must default to checked")


if __name__ == "__main__":
    unittest.main()
