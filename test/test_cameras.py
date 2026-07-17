#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.cameras.

Most CamerasSlots methods are one-liners that delegate to
mtk.switch_viewport_camera or mel.eval. The units worth pinning at this
layer:

- b007 (Align View): creates the persistent "alignToPoly" camera on
  first use and reuses it after. Worth verifying the create-once
  contract so the scene doesn't accrete duplicates.
- b000-b006: each maps to a specific mtk.switch_viewport_camera view name.

The DCC-agnostic ``toggle_camera_view`` dispatch now lives on the shared base
``tentacle.slots._slots.Slots`` (both DCC cameras slots inherit it) and is
pinned, without Maya, in ``test_slots_base.py::TestToggleCameraView``.
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
    """Stand-in for switchboard exposing the ``message_box`` surface b007 uses."""

    def __init__(self):
        self.added_messages = []

    def message_box(self, *args, **kwargs):
        self.added_messages.append((args, kwargs))


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
