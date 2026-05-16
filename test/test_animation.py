#!/usr/bin/python
# coding=utf-8
"""Regression / smoke tests for tentacle.slots.maya.animation.

This module is 1700 lines of UI orchestration — the actual animation
logic (curve scaling, stepping, baking, audio-shift, manifest) lives in
mayatk and is covered by:

    test_anim_utils.py · test_scale_keys.py · test_stagger_keys.py ·
    test_unbake_keys.py · test_smart_bake.py · test_segment_keys.py ·
    test_audio_utils_*.py · test_shot_*.py · test_blendshape_animator.py

What's worth pinning at this layer:

1. Structural completeness — every advertised slot method is present.
   Catches accidental removal that the audit-style smoke test in
   test_slot_integrity does not catch (it does shape, not method roster).

2. Module import — Animation imports a long list of mayatk symbols at
   module top. A broken import would break the entire animation toolbar.

3. tb017's mode-string -> keys-argument translation — the only branching
   pure-Python logic in the file that isn't a thin mtk wrapper.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import animation as animation_module

    _MAYA_AVAILABLE = True
except ImportError:
    animation_module = None
    cmds = None
    _MAYA_AVAILABLE = False


class _FakeCombo:
    def __init__(self, value):
        self._v = value

    def currentData(self):
        return self._v


class _FakeMenu:
    def __init__(self, cmb000_value, cmb001_value):
        self.cmb000 = _FakeCombo(cmb000_value)
        self.cmb001 = _FakeCombo(cmb001_value)


class _FakeOptionBox:
    def __init__(self, cmb000_value, cmb001_value):
        self.menu = _FakeMenu(cmb000_value, cmb001_value)


class _FakeWidget:
    def __init__(self, cmb000_value, cmb001_value):
        self.option_box = _FakeOptionBox(cmb000_value, cmb001_value)


class _RecordedSb:
    def __init__(self):
        self.messages = []

    def message_box(self, *args, **kwargs):
        self.messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestAnimationModuleImport(unittest.TestCase):
    """Catch import-time breakage. Module-top imports a long mayatk list."""

    def test_module_imports_cleanly(self):
        self.assertIsNotNone(animation_module)
        self.assertTrue(hasattr(animation_module, "Animation"))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestAnimationSlotRoster(unittest.TestCase):
    """Pin the public slot roster — accidental removal of any tb###/b###
    silently breaks the corresponding toolbar button at runtime, with no
    error until the user clicks it. Test catches it at build time.
    """

    EXPECTED_TB_SLOTS = [f"tb{i:03d}" for i in range(0, 20)]
    EXPECTED_B_SLOTS = ["b000", "b004", "b005"]

    def test_all_tb_slots_present(self):
        cls = animation_module.Animation
        missing = [name for name in self.EXPECTED_TB_SLOTS if not hasattr(cls, name)]
        self.assertEqual(missing, [], f"Animation is missing tb slots: {missing}")

    def test_all_tb_slot_inits_present(self):
        cls = animation_module.Animation
        missing = [
            f"{name}_init"
            for name in self.EXPECTED_TB_SLOTS
            if not hasattr(cls, f"{name}_init")
        ]
        self.assertEqual(missing, [], f"Animation is missing init handlers: {missing}")

    def test_all_b_slots_present(self):
        cls = animation_module.Animation
        missing = [name for name in self.EXPECTED_B_SLOTS if not hasattr(cls, name)]
        self.assertEqual(missing, [], f"Animation is missing b slots: {missing}")

    def test_header_init_present(self):
        self.assertTrue(hasattr(animation_module.Animation, "header_init"))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestTb017StepKeysModeTranslation(unittest.TestCase):
    """tb017 translates the cmb000 'mode' string to step_keys' `keys` arg.

    The mapping is:
        "auto"          -> "auto"
        "current_time"  -> current frame number
        "selected"      -> list of selected key names (bails if empty)
        "all"           -> None  (default to all)

    Regression: a broken branch here causes step_keys to bake the wrong
    set of frames. The mtk-side logic is tested separately; here we pin
    the translation surface.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        # Bypass __init__; just need the method bound.
        self.instance = animation_module.Animation.__new__(animation_module.Animation)
        self.instance.sb = _RecordedSb()

        # Patch out the mtk call so we can capture its `keys` argument.
        import mayatk as mtk
        self._original_step_keys = mtk.AnimUtils.step_keys
        self.recorded_keys = []

        def fake_step_keys(keys=None, tangent="out"):
            self.recorded_keys.append(keys)
            return {"curves": 1, "keys": 1}

        mtk.AnimUtils.step_keys = staticmethod(fake_step_keys)

    def tearDown(self):
        import mayatk as mtk
        mtk.AnimUtils.step_keys = self._original_step_keys
        cmds.file(new=True, force=True)

    def test_mode_auto_passes_auto_string(self):
        widget = _FakeWidget(cmb000_value="auto", cmb001_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, ["auto"])

    def test_mode_all_passes_none(self):
        widget = _FakeWidget(cmb000_value="all", cmb001_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, [None])

    def test_mode_current_time_passes_current_frame(self):
        cmds.currentTime(42)
        widget = _FakeWidget(cmb000_value="current_time", cmb001_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, [42.0])

    def test_mode_selected_with_no_selection_bails_with_message(self):
        """No keys selected in Graph Editor — must NOT call step_keys."""
        widget = _FakeWidget(cmb000_value="selected", cmb001_value="out")
        self.instance.tb017(widget)
        self.assertEqual(self.recorded_keys, [])  # never called
        self.assertTrue(self.instance.sb.messages, "User must be told why nothing ran")


if __name__ == "__main__":
    unittest.main()
