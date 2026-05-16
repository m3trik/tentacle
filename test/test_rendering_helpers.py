#!/usr/bin/python
# coding=utf-8
"""Regression tests for the pure helpers in tentacle.slots.maya.rendering.

test_rendering.py exists but only covers the VRay setup path (b005).
The pure-Python helpers (_default_playblast_path, _scene_base_name,
_camera_transforms) had no coverage — they underpin the entire Export
Playblast workflow.
"""
import os
import tempfile
import unittest

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import rendering as rendering_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    rendering_module = None
    _MAYA_AVAILABLE = False


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestSceneBaseName(unittest.TestCase):
    """_scene_base_name returns basename(scene).rsplit('.', 1)[0] or 'playblast'."""

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_unsaved_scene_returns_fallback(self):
        """Fresh scene has no on-disk name. _scene_base_name reads
        cmds.file(query=sceneName); if Maya returns empty string, the
        helper falls back to 'playblast'. If Maya returns 'untitled'
        (some configurations), that's used as the basename instead.

        Test the fallback by mocking sceneName=''.
        """
        original = cmds.file
        try:
            def fake_file(*args, **kwargs):
                if kwargs.get("query") and kwargs.get("sceneName"):
                    return ""  # Simulate genuinely empty sceneName
                return original(*args, **kwargs)
            cmds.file = fake_file

            result = rendering_module.Rendering._scene_base_name()
            self.assertEqual(result, "playblast")
        finally:
            cmds.file = original

    def test_saved_scene_returns_basename_without_extension(self):
        # Save the scene under a known name, then query.
        tmpdir = tempfile.mkdtemp(prefix="rh_test_")
        try:
            scene_path = os.path.join(tmpdir, "MyShot.ma").replace("\\", "/")
            cmds.file(rename=scene_path)
            cmds.file(save=True, type="mayaAscii")

            result = rendering_module.Rendering._scene_base_name()
            self.assertEqual(result, "MyShot")
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_saved_scene_with_multi_dot_strips_only_last(self):
        """A filename like 'v1.test.ma' should yield 'v1.test', not 'v1'."""
        tmpdir = tempfile.mkdtemp(prefix="rh_dot_")
        try:
            scene_path = os.path.join(tmpdir, "v1.test.ma").replace("\\", "/")
            cmds.file(rename=scene_path)
            cmds.file(save=True, type="mayaAscii")

            result = rendering_module.Rendering._scene_base_name()
            self.assertEqual(result, "v1.test")
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestDefaultPlayblastPath(unittest.TestCase):
    """_default_playblast_path joins Desktop with _scene_base_name."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = rendering_module.Rendering.__new__(rendering_module.Rendering)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_returns_normalized_path_under_desktop(self):
        path = self.instance._default_playblast_path()
        # Should be normalized + under Desktop.
        desktop = os.path.normpath(os.path.expanduser(os.path.join("~", "Desktop")))
        self.assertTrue(
            path.startswith(desktop),
            f"Expected path under {desktop}, got {path}",
        )

    def test_uses_scene_name_when_saved(self):
        tmpdir = tempfile.mkdtemp(prefix="rh_path_")
        try:
            scene_path = os.path.join(tmpdir, "ShotA.ma").replace("\\", "/")
            cmds.file(rename=scene_path)
            cmds.file(save=True, type="mayaAscii")

            path = self.instance._default_playblast_path()
            # Should end with the scene basename.
            self.assertTrue(
                path.endswith("ShotA"),
                f"Expected path to end with 'ShotA', got {path}",
            )
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_uses_playblast_fallback_when_scene_name_empty(self):
        """Force sceneName='' to exercise the 'playblast' fallback branch."""
        original = cmds.file
        try:
            def fake_file(*args, **kwargs):
                if kwargs.get("query") and kwargs.get("sceneName"):
                    return ""
                return original(*args, **kwargs)
            cmds.file = fake_file

            path = self.instance._default_playblast_path()
            self.assertTrue(
                path.endswith("playblast"),
                f"Expected path to end with 'playblast', got {path}",
            )
        finally:
            cmds.file = original


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCameraTransforms(unittest.TestCase):
    """_camera_transforms returns sorted unique transform names from camera shapes."""

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_default_scene_includes_persp_top_front_side(self):
        """Maya's default scene has the standard 4 cameras."""
        result = rendering_module.Rendering._camera_transforms()
        # Maya creates persp, top, front, side by default.
        self.assertIn("persp", result)
        self.assertIn("top", result)
        self.assertIn("front", result)
        self.assertIn("side", result)

    def test_result_is_sorted(self):
        result = rendering_module.Rendering._camera_transforms()
        self.assertEqual(result, sorted(result))

    def test_includes_user_camera(self):
        cmds.camera(name="renderCam")
        result = rendering_module.Rendering._camera_transforms()
        # renderCam transform should be present
        self.assertTrue(
            any("renderCam" in name for name in result),
            f"Expected renderCam in {result}",
        )


if __name__ == "__main__":
    unittest.main()
