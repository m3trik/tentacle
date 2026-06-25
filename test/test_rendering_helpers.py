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


# --- Stubs for the tb001 option-box render button ---------------------------
class _Signal:
    def __init__(self):
        self.fns = []

    def connect(self, fn):
        self.fns.append(fn)

    def emit(self):
        for fn in list(self.fns):
            fn()


class _Combo:
    def __init__(self):
        self._items = []  # (label, data)
        self._idx = 0
        self.currentIndexChanged = _Signal()

    def addItems(self, labels):
        self._items.extend((str(label), None) for label in labels)

    def setItemData(self, i, data):
        label, _ = self._items[i]
        self._items[i] = (label, data)

    def setCurrentIndex(self, i):
        self._idx = i
        self.currentIndexChanged.emit()

    def currentIndex(self):
        return self._idx

    def currentText(self):
        return self._items[self._idx][0] if self._items else ""

    def currentData(self):
        return self._items[self._idx][1] if self._items else None

    def select(self, data):
        """Test helper: select the item whose itemData == data."""
        for i, (_, d) in enumerate(self._items):
            if d == data:
                self.setCurrentIndex(i)
                return


class _Check:
    def __init__(self, checked=False):
        self._checked = checked
        self._enabled = True

    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        self._checked = bool(v)

    def setEnabled(self, v):
        self._enabled = bool(v)

    def isEnabled(self):
        return self._enabled


class _Menu:
    def setTitle(self, t):
        self._title = t

    def add(self, kind, **kw):
        if kind == "QComboBox":
            w = _Combo()
            w.addItems(kw.get("addItems", []))
            if "setCurrentIndex" in kw:
                w._idx = kw["setCurrentIndex"]
        else:  # QCheckBox
            w = _Check(kw.get("setChecked", False))
        setattr(self, kw["setObjectName"], w)
        return w


class _OptionBox:
    def __init__(self):
        self.menu = _Menu()


class _Widget:
    def __init__(self):
        self.option_box = _OptionBox()


class _SB:
    def __init__(self):
        self.messages = []

    def message_box(self, msg):
        self.messages.append(msg)


class _FakeBridge:
    """Records add() calls; instances tracked on the class."""

    instances = []

    def __init__(self):
        _FakeBridge.instances.append(self)
        self.added = "UNSET"

    def add(self, materials=None, **kw):
        self.added = materials
        return materials or []


class _FakeRenderUtils:
    """Stand-in for mtk.RenderUtils that records calls (no live render)."""

    def __init__(self, current="mayaSoftware", renderers=None, ipr_ok=True):
        self.calls = []
        self._current = current
        self._renderers = renderers or [
            {"name": "mayaSoftware", "label": "Maya Software", "loaded": True},
            {"name": "mayaHardware2", "label": "Maya Hardware 2.0", "loaded": True},
            {"name": "arnold", "label": "Arnold", "loaded": False},
        ]
        self._ipr_ok = ipr_ok

    def get_available_renderers(self):
        return list(self._renderers)

    def current_renderer(self):
        return self._current

    def supports_ipr(self, renderer=None):
        renderer = renderer or self._current
        # Mirror the real gate: built-in Software + the optional renderers do
        # IPR; Hardware 2.0 (Viewport 2.0) does not.
        return renderer in ("arnold", "vray", "redshift", "mayaSoftware")

    def set_renderer(self, name):
        self.calls.append(("set_renderer", name))

    def render_camera(self, camera):
        self.calls.append(("render_camera", camera))

    def redo_previous_render(self):
        self.calls.append(("redo",))

    def start_ipr(self, camera, renderer):
        self.calls.append(("ipr", camera, renderer))
        return self._ipr_ok


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestRenderButtonInit(unittest.TestCase):
    """tb001_init populates camera + renderer combos and gates the Arnold option."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self._orig_ru = rendering_module.mtk.RenderUtils
        rendering_module.mtk.RenderUtils = _FakeRenderUtils()

    def tearDown(self):
        rendering_module.mtk.RenderUtils = self._orig_ru
        cmds.file(new=True, force=True)

    def _init(self):
        cam_tf = cmds.rename(cmds.camera()[0], "renderCam")
        inst = rendering_module.Rendering.__new__(rendering_module.Rendering)
        widget = _Widget()
        inst.tb001_init(widget)
        return inst, widget.option_box.menu, cam_tf

    def test_camera_combo_lists_transforms(self):
        _, menu, cam_tf = self._init()
        labels = [menu.cmb002.currentText()] + [
            menu.cmb002._items[i][0] for i in range(len(menu.cmb002._items))
        ]
        self.assertIn("persp", labels)
        self.assertIn(cam_tf, labels)
        self.assertNotIn("perspShape", labels)

    def test_camera_combo_defaults_to_persp(self):
        # persp is the conventional render view; default to it, not the first
        # camera alphabetically (front).
        _, menu, _ = self._init()
        self.assertEqual(menu.cmb002.currentText(), "persp")

    def test_renderer_combo_carries_internal_names(self):
        _, menu, _ = self._init()
        names = [d for _, d in menu.cmb003._items]
        self.assertIn("arnold", names)
        self.assertIn("mayaSoftware", names)

    def test_arnold_option_gated_on_renderer(self):
        _, menu, _ = self._init()
        # Default renderer (mayaSoftware) -> Add Arnold Network disabled.
        self.assertFalse(menu.chk000.isEnabled())
        # Selecting Arnold enables it; switching away disables + unchecks it.
        menu.cmb003.select("arnold")
        self.assertTrue(menu.chk000.isEnabled())
        menu.chk000.setChecked(True)
        menu.cmb003.select("mayaSoftware")
        self.assertFalse(menu.chk000.isEnabled())
        self.assertFalse(menu.chk000.isChecked())

    def test_ipr_option_gated_on_renderer_support(self):
        _, menu, _ = self._init()
        # Default renderer (mayaSoftware) provides IPR -> enabled.
        self.assertTrue(menu.chk001.isEnabled())
        menu.chk001.setChecked(True)
        # A renderer without IPR (Viewport 2.0) disables AND unchecks it, so
        # the user can't ask for something that would fail after the click.
        menu.cmb003.select("mayaHardware2")
        self.assertFalse(menu.chk001.isEnabled())
        self.assertFalse(menu.chk001.isChecked())
        # Back to an IPR-capable renderer -> re-enabled.
        menu.cmb003.select("arnold")
        self.assertTrue(menu.chk001.isEnabled())


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestRenderButtonAction(unittest.TestCase):
    """tb001 routes camera/renderer/network/IPR/smart-redo through RenderUtils."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self._orig_ru = rendering_module.mtk.RenderUtils
        self._orig_bridge = rendering_module.mtk.ArnoldBridge
        self.ru = _FakeRenderUtils()
        rendering_module.mtk.RenderUtils = self.ru
        rendering_module.mtk.ArnoldBridge = _FakeBridge
        _FakeBridge.instances = []

    def tearDown(self):
        rendering_module.mtk.RenderUtils = self._orig_ru
        rendering_module.mtk.ArnoldBridge = self._orig_bridge
        cmds.file(new=True, force=True)

    def _menu(self, camera="", renderer="mayaSoftware", add_net=False,
              ipr=False, smart=True):
        menu = _Menu()
        menu.cmb002 = _Combo()
        menu.cmb002.addItems([camera] if camera else [])
        menu.cmb003 = _Combo()
        menu.cmb003.addItems([renderer])
        menu.cmb003.setItemData(0, renderer)
        menu.chk000 = _Check(add_net)
        menu.chk001 = _Check(ipr)
        menu.chk002 = _Check(smart)
        w = _Widget()
        w.option_box.menu = menu
        return w

    def _inst(self):
        inst = rendering_module.Rendering.__new__(rendering_module.Rendering)
        inst.sb = _SB()
        inst._last_render_key = None
        return inst

    def test_renders_selected_camera(self):
        cam_tf = cmds.rename(cmds.camera()[0], "shotCam")
        inst = self._inst()
        inst.tb001(self._menu(camera=cam_tf))
        self.assertIn(("set_renderer", "mayaSoftware"), self.ru.calls)
        self.assertIn(("render_camera", cam_tf), self.ru.calls)
        self.assertEqual(inst._last_render_key, (cam_tf, "mayaSoftware"))

    def test_resolves_camera_shape_to_transform(self):
        cam_tf = cmds.rename(cmds.camera()[0], "shapeCam")
        shape = cmds.listRelatives(cam_tf, shapes=True)[0]
        inst = self._inst()
        inst.tb001(self._menu(camera=shape))
        self.assertIn(("render_camera", cam_tf), self.ru.calls)

    def test_no_camera_warns_and_skips(self):
        inst = self._inst()
        inst.tb001(self._menu(camera=""))
        self.assertTrue(inst.sb.messages)
        self.assertFalse(any(c[0] == "render_camera" for c in self.ru.calls))

    def test_smart_redo_when_key_unchanged(self):
        cam_tf = cmds.rename(cmds.camera()[0], "redoCam")
        inst = self._inst()
        inst._last_render_key = (cam_tf, "mayaSoftware")
        inst.tb001(self._menu(camera=cam_tf, smart=True))
        self.assertIn(("redo",), self.ru.calls)
        self.assertFalse(any(c[0] == "render_camera" for c in self.ru.calls))

    def test_no_redo_when_camera_changed(self):
        cam_tf = cmds.rename(cmds.camera()[0], "freshCam")
        inst = self._inst()
        inst._last_render_key = ("otherCam", "mayaSoftware")
        inst.tb001(self._menu(camera=cam_tf, smart=True))
        self.assertIn(("render_camera", cam_tf), self.ru.calls)
        self.assertFalse(any(c[0] == "redo" for c in self.ru.calls))

    def test_add_arnold_network_only_for_arnold(self):
        cam_tf = cmds.rename(cmds.camera()[0], "aiCam")
        # A real scene material so get_scene_mats() has something to bridge.
        shader = cmds.shadingNode("standardSurface", asShader=True, name="aiMat")
        inst = self._inst()
        inst.tb001(self._menu(camera=cam_tf, renderer="arnold", add_net=True))
        self.assertTrue(_FakeBridge.instances, "ArnoldBridge().add should run")
        self.assertIn(shader, _FakeBridge.instances[-1].added)

        # Non-arnold renderer: never add the network, even with the box ticked.
        _FakeBridge.instances = []
        inst.tb001(self._menu(camera=cam_tf, renderer="mayaSoftware", add_net=True))
        self.assertFalse(_FakeBridge.instances, "no Arnold network for non-arnold")

    def test_ipr_supersedes_single_render(self):
        cam_tf = cmds.rename(cmds.camera()[0], "iprCam")
        inst = self._inst()
        inst.tb001(self._menu(camera=cam_tf, renderer="arnold", ipr=True))
        self.assertTrue(any(c[0] == "ipr" for c in self.ru.calls))
        self.assertFalse(any(c[0] == "render_camera" for c in self.ru.calls))

    def test_ipr_falls_back_to_render_silently_on_launch_race(self):
        # IPR is gated in the option box (disabled for renderers without it), so
        # a False start_ipr here is the rare launch race: fall through to a
        # single render WITHOUT an after-the-fact message box.
        cam_tf = cmds.rename(cmds.camera()[0], "noIprCam")
        self.ru._ipr_ok = False
        inst = self._inst()
        inst.tb001(self._menu(camera=cam_tf, renderer="mayaSoftware", ipr=True))
        self.assertFalse(inst.sb.messages, "no message box — the option is gated")
        self.assertIn(("render_camera", cam_tf), self.ru.calls)


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestExportPlayblastGuard(unittest.TestCase):
    """tb000 bails early (message + no capture) on a scene with no animation."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self._orig_exporter = rendering_module.PlayblastExporter

        def _spy(*a, **k):  # constructing the exporter on a static scene is the bug
            raise AssertionError("PlayblastExporter must not run on a static scene")

        rendering_module.PlayblastExporter = _spy

    def tearDown(self):
        rendering_module.PlayblastExporter = self._orig_exporter
        cmds.file(new=True, force=True)

    def _inst(self):
        inst = rendering_module.Rendering.__new__(rendering_module.Rendering)
        inst.sb = _SB()
        return inst

    def test_static_scene_blocks_with_message(self):
        # Fresh scene: geometry but no keys. The guard short-circuits before the
        # menu is even read, so an empty _Widget is enough.
        cmds.polyCube(name="static_cube")
        inst = self._inst()
        inst.tb000(_Widget())
        self.assertTrue(inst.sb.messages, "a message box should explain why")
        self.assertIn("no animation", inst.sb.messages[-1].lower())

    def test_animated_scene_passes_guard(self):
        # A keyed transform must NOT be short-circuited. We let the real exporter
        # path run into the empty stub menu (which raises downstream) and only
        # assert the no-animation guard message was never produced — i.e. the
        # guard let us through (catches an inverted / always-on guard).
        cube = cmds.polyCube(name="anim_cube")[0]
        cmds.setKeyframe(cube, attribute="translateX", time=1, value=0)
        cmds.setKeyframe(cube, attribute="translateX", time=10, value=10)
        rendering_module.PlayblastExporter = self._orig_exporter
        inst = self._inst()
        try:
            inst.tb000(_Widget())
        except Exception:
            pass  # downstream menu access fails — irrelevant to the guard
        self.assertFalse(
            any("no animation" in m.lower() for m in inst.sb.messages),
            "guard must not block an animated scene",
        )


if __name__ == "__main__":
    unittest.main()
