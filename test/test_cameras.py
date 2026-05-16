#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.cameras.

Most CamerasSlots methods are one-liners that delegate to
mtk.switch_viewport_camera or mel.eval. The units worth pinning at this
layer:

- toggle_camera_view: stateful dispatch that reads slot_history and
  decides "go to perspective" vs "restore last orthographic view". Easy
  to break when slot_history's shape changes or when b004 is renamed.
- b007 (Align View): creates the persistent "alignToPoly" camera on
  first use and reuses it after. Worth verifying the create-once
  contract so the scene doesn't accrete duplicates.
"""
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import cameras as cameras_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    cameras_module = None
    _MAYA_AVAILABLE = False


class _FakeSb:
    """Stand-in for switchboard with the surfaces toggle_camera_view reads."""

    def __init__(self, history=None, slots=None):
        self._history = list(history or [])
        self._slots = list(slots or [])
        self.added_messages = []

    def get_methods_by_string_pattern(self, instance, pattern):
        # Return whatever the test pre-loaded as `b000-7`.
        return self._slots

    def slot_history(self, sl=None, inc=None, add=None):
        if add is not None:
            self._history.append(add)
            return
        if sl is not None:
            return self._history[sl]
        return list(self._history)

    def message_box(self, *args, **kwargs):
        self.added_messages.append((args, kwargs))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestToggleCameraView(unittest.TestCase):
    """toggle_camera_view alternates between perspective (b004) and the
    last non-perspective view in slot_history."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = cameras_module.Cameras.__new__(cameras_module.Cameras)
        self.calls = []

        # Stub each b00X to record itself rather than touch real cameras.
        def _record(name):
            def _f(*a, **kw):
                self.calls.append(name)

            _f.__name__ = name
            return _f

        for name in ("b000", "b001", "b002", "b003", "b004", "b005", "b006", "b007"):
            setattr(self.instance, name, _record(name))

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_empty_history_is_noop(self):
        """No previous camera switches → toggle returns without calling anything."""
        self.instance.sb = _FakeSb(history=[], slots=[self.instance.b004])
        self.instance.toggle_camera_view()
        self.assertEqual(self.calls, [])

    def test_last_was_non_persp_goes_to_persp(self):
        """If last camera was non-persp (e.g. b000 back), toggle calls b004."""
        self.instance.sb = _FakeSb(
            history=[self.instance.b000],  # last view = back
            slots=[
                self.instance.b000,
                self.instance.b004,
            ],
        )
        self.instance.toggle_camera_view()
        self.assertEqual(self.calls, ["b004"])

    def test_last_was_persp_restores_prior_non_persp(self):
        """If last was b004, toggle should restore the previous non-persp view."""
        self.instance.sb = _FakeSb(
            history=[self.instance.b000, self.instance.b004],
            slots=[
                self.instance.b000,
                self.instance.b004,
            ],
        )
        self.instance.toggle_camera_view()
        self.assertEqual(self.calls, ["b000"])

    def test_last_was_persp_no_prior_is_noop(self):
        """If only b004 is in history (no prior non-persp), nothing to restore."""
        self.instance.sb = _FakeSb(
            history=[self.instance.b004],
            slots=[self.instance.b004],
        )
        self.instance.toggle_camera_view()
        self.assertEqual(self.calls, [])

    def test_history_updated_after_toggle_to_persp(self):
        """After toggling to b004, b004 is appended to history."""
        sb = _FakeSb(
            history=[self.instance.b000],
            slots=[self.instance.b000, self.instance.b004],
        )
        self.instance.sb = sb
        self.instance.toggle_camera_view()
        # Last item should now be b004
        self.assertEqual(sb._history[-1].__name__, "b004")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestBackPersistentAlignCamera(unittest.TestCase):
    """b007 (Align View) creates 'alignToPoly' on first call and reuses it."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = cameras_module.Cameras.__new__(cameras_module.Cameras)
        self.sb = _FakeSb()
        self.instance.sb = self.sb

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_no_selection_warns_and_skips(self):
        """b007 with empty selection should message and not create a camera."""
        cmds.select(clear=True)
        self.instance.b007()
        # No alignToPoly camera should be created.
        self.assertFalse(cmds.objExists("alignToPoly"))
        # And it warned.
        self.assertTrue(self.sb.added_messages)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestPerViewButtons(unittest.TestCase):
    """b000-b006 each delegate to a single mtk.switch_viewport_camera call
    with a specific view name. Pin these so the view name strings can't
    drift silently."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = cameras_module.Cameras.__new__(cameras_module.Cameras)
        # Capture mtk.switch_viewport_camera calls.
        import mayatk as mtk
        self._original = mtk.switch_viewport_camera
        self.captured = []
        mtk.switch_viewport_camera = lambda name: self.captured.append(name)

    def tearDown(self):
        import mayatk as mtk
        mtk.switch_viewport_camera = self._original
        cmds.file(new=True, force=True)

    def test_b000_back(self):
        self.instance.b000()
        self.assertEqual(self.captured, ["back"])

    def test_b001_top(self):
        self.instance.b001()
        self.assertEqual(self.captured, ["top"])

    def test_b002_right_maps_to_side(self):
        """Right view maps to Maya's 'side' camera (historical naming)."""
        self.instance.b002()
        self.assertEqual(self.captured, ["side"])

    def test_b003_left(self):
        self.instance.b003()
        self.assertEqual(self.captured, ["left"])

    def test_b004_perspective(self):
        self.instance.b004()
        self.assertEqual(self.captured, ["persp"])

    def test_b005_front(self):
        self.instance.b005()
        self.assertEqual(self.captured, ["front"])

    def test_b006_bottom(self):
        self.instance.b006()
        self.assertEqual(self.captured, ["bottom"])


if __name__ == "__main__":
    unittest.main()
