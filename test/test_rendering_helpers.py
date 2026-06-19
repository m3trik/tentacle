#!/usr/bin/python
# coding=utf-8
"""Regression tests for the pure helpers in tentacle.slots.maya.rendering.

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


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestRenderCurrentFrame(unittest.TestCase):
    """b000 (Render Current Frame) must surface the Render View.

    Regression: b000 called `cmds.render(camera)`, which renders offscreen
    to a temp file and returns a path -- it never opens the Render View, so
    the button appeared to do nothing. It must instead route the *selected*
    camera transform through `renderWindowRenderCamera` (Maya's own
    "Render Current Frame" path).
    """

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    def _make_instance(self, camera_text):
        inst = rendering_module.Rendering.__new__(rendering_module.Rendering)

        class _Combo:
            def currentText(_self):
                return camera_text

        class _UI:
            cmb001 = _Combo()

        class _SB:
            def __init__(s):
                s.messages = []

            def message_box(s, msg):
                s.messages.append(msg)

        inst.ui = _UI()
        inst.sb = _SB()
        return inst

    def _run_b000(self, inst):
        """Call b000 with mel.eval / cmds.render patched to capture calls."""
        captured = {}
        orig_eval = rendering_module.mel.eval
        orig_render = rendering_module.cmds.render

        def fake_eval(cmd, *a, **k):
            captured["mel"] = cmd

        def fake_render(*a, **k):
            captured["render"] = (a, k)

        try:
            rendering_module.mel.eval = fake_eval
            rendering_module.cmds.render = fake_render
            inst.b000()
        finally:
            rendering_module.mel.eval = orig_eval
            rendering_module.cmds.render = orig_render
        return captured

    def test_b000_renders_into_render_view_not_offscreen(self):
        cam_tf = cmds.rename(cmds.camera()[0], "renderCam")
        shape = cmds.listRelatives(cam_tf, shapes=True)[0]

        # Combo yields the camera *shape*; b000 must resolve it to the transform.
        inst = self._make_instance(shape)
        captured = self._run_b000(inst)

        self.assertIn(
            "renderWindowRenderCamera",
            captured.get("mel", ""),
            "b000 should render into the Render View via renderWindowRenderCamera",
        )
        self.assertIn(
            cam_tf,
            captured.get("mel", ""),
            "the resolved camera transform should be passed to the Render View",
        )
        self.assertNotIn(
            "render", captured, "b000 must not fall back to silent offscreen cmds.render"
        )

    def test_b000_passes_transform_unchanged(self):
        cam_tf = cmds.rename(cmds.camera()[0], "shotCam")

        inst = self._make_instance(cam_tf)  # combo already yields a transform
        captured = self._run_b000(inst)

        self.assertIn("renderWindowRenderCamera", captured.get("mel", ""))
        self.assertIn(cam_tf, captured.get("mel", ""))

    def test_b000_no_camera_warns_and_skips(self):
        inst = self._make_instance("")  # empty selection
        captured = self._run_b000(inst)

        self.assertNotIn("mel", captured, "b000 must not render with no camera")
        self.assertTrue(inst.sb.messages, "b000 should warn when no camera is available")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestRenderCameraCombo(unittest.TestCase):
    """cmb001_init must populate transforms and wire refresh-on-show/popup."""

    def setUp(self):
        cmds.file(new=True, force=True)

    def tearDown(self):
        cmds.file(new=True, force=True)

    class _FakeSignal:
        def __init__(self):
            self.connected = []

        def connect(self, fn):
            self.connected.append(fn)

    class _FakeWidget:
        def __init__(self):
            self.is_initialized = False
            self.refresh_on_show = False
            self.before_popup_shown = TestRenderCameraCombo._FakeSignal()
            self.added = None
            self.add_kwargs = None

        def init_slot(self):
            pass

        def add(self, items, **kwargs):
            self.added = list(items)
            self.add_kwargs = kwargs

    def test_cmb001_init_lists_transforms_and_wires_refresh(self):
        cam_tf = cmds.rename(cmds.camera()[0], "renderCam")
        inst = rendering_module.Rendering.__new__(rendering_module.Rendering)
        widget = self._FakeWidget()

        inst.cmb001_init(widget)

        # Transforms, not shapes.
        self.assertIn("persp", widget.added)
        self.assertIn(cam_tf, widget.added)
        self.assertNotIn("perspShape", widget.added)
        # Selection is preserved across refreshes.
        self.assertTrue(widget.add_kwargs.get("restore_index"))
        # Refresh wired for both panel-show and dropdown-open (and only once).
        self.assertTrue(widget.refresh_on_show)
        self.assertIn(widget.init_slot, widget.before_popup_shown.connected)

    def test_cmb001_init_skips_rewiring_when_already_initialized(self):
        cmds.camera()
        inst = rendering_module.Rendering.__new__(rendering_module.Rendering)
        widget = self._FakeWidget()
        widget.is_initialized = True

        inst.cmb001_init(widget)

        # Already-initialized refresh path must not re-connect the popup signal.
        self.assertEqual(widget.before_popup_shown.connected, [])
        # ...but the list is still repopulated on every init.
        self.assertIn("persp", widget.added)


if __name__ == "__main__":
    unittest.main()
