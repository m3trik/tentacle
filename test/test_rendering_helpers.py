#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.rendering, the one Rendering Slots class.

It reaches its host only through ``self.tk``: a fake toolkit stands in for it
here (a recording ``RenderUtils`` and ``PlayblastExporter``), and in Maya the
same class drives the real ``mtk``. Pinned at this layer:

- Export Playblast: the option box built from the exporter's own registry (a
  bundle naming a target the host lacks is left out), the custom range, and
  its state reaching ``PlayblastExporter(...).export(...)``; ffmpeg offered
  only for an encoded target; the results reported;
- Render: the host's cameras (its default first) and renderers, the IPR gate,
  the scene-backed setting fields and presets, Smart Redo, Arnold's preview;
- the controls only Maya serves tagged ``requires``;
- the settings buttons opening the host's editors by mayatk's names.
The operations themselves are tested in mayatk and blendertk.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest import mock

import pythontk as ptk
from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.rendering import RenderingSlots

cmds = maya_module("maya.cmds")


# --- Stubs for the option-box widgets -----------------------------------------
class _Signal:
    def __init__(self):
        self.fns = []
        self.blocked = False

    def connect(self, fn):
        self.fns.append(fn)

    def emit(self, *args):
        if self.blocked:
            return
        for fn in list(self.fns):
            fn(*args)


class _Tagged:
    """``setProperty`` / ``property``, as ``Slots.requires`` tags a widget."""

    def setProperty(self, name, value):
        self.__dict__.setdefault("_props", {})[name] = value

    def property(self, name):
        return self.__dict__.get("_props", {}).get(name)


class _Combo(_Tagged):
    def __init__(self):
        self._items = []  # (label, data)
        self._idx = 0
        self._visible = True
        self.currentIndexChanged = _Signal()
        self.activated = _Signal()  # Qt: the USER's pick only

    def addItems(self, labels):
        self._items.extend((str(label), None) for label in labels)

    def clear(self):
        self._items, self._idx = [], 0

    def blockSignals(self, block):
        self.currentIndexChanged.blocked = bool(block)

    def setItemData(self, i, data):
        label, _ = self._items[i]
        self._items[i] = (label, data)

    def itemData(self, i):
        try:
            return self._items[i][1]
        except IndexError:
            return None

    def setCurrentIndex(self, i):
        self._idx = i
        self.currentIndexChanged.emit(i)

    def currentIndex(self):
        return self._idx

    def currentText(self):
        return self._items[self._idx][0] if self._items else ""

    def currentData(self):
        return self._items[self._idx][1] if self._items else None

    def setVisible(self, v):
        self._visible = bool(v)

    def select(self, data):
        """Select the item whose data is *data* (programmatic: no ``activated``)."""
        for i, (_, d) in enumerate(self._items):
            if d == data:
                self.setCurrentIndex(i)
                return

    def pick(self, data):
        """The USER picks the item whose data is *data*."""
        self.select(data)
        self.activated.emit(self._idx)


class _Check(_Tagged):
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


class _Spin(_Tagged):
    def __init__(self, value=0):
        self._value = value
        self._visible = True
        self._enabled = True
        self.valueChanged = _Signal()

    def value(self):
        return self._value

    def setValue(self, v):
        changed = v != self._value
        self._value = v
        if changed:
            self.valueChanged.emit(v)

    def blockSignals(self, block):
        self.valueChanged.blocked = bool(block)

    def setEnabled(self, v):
        self._enabled = bool(v)

    def isEnabled(self):
        return self._enabled

    def setVisible(self, v):
        self._visible = bool(v)


class _Line(_Tagged):
    def __init__(self, text=""):
        self._text = text
        self._placeholder = ""

    def text(self):
        return self._text

    def setText(self, t):
        self._text = t

    def setPlaceholderText(self, t):
        self._placeholder = t

    def placeholderText(self):
        return self._placeholder


class _Presets:
    """Stand-in for the menu's PresetManager namespace (``menu.presets``)."""

    def __init__(self):
        self.preset_dir = self.builtin_dir = None
        self.value_provider = self.value_applier = None
        self.refreshes = 0

    def refresh_modified_state(self):
        self.refreshes += 1
        return False


class _Menu:
    def __init__(self):
        self.presets = _Presets()
        self.add_presets = False
        self.added = []

    def setTitle(self, t):
        self._title = t

    def add(self, kind, **kw):
        self.added.append(kw.get("setObjectName", kind))
        if kind == "Separator":
            return None
        if kind == "QComboBox":
            w = _Combo()
            w.addItems(kw.get("addItems", []))
            if "setCurrentIndex" in kw:
                w._idx = kw["setCurrentIndex"]
        elif kind == "QSpinBox":
            w = _Spin(kw.get("setValue", 0))
        elif kind == "QLineEdit":
            w = _Line(kw.get("setText", ""))
        else:  # QCheckBox
            w = _Check(kw.get("setChecked", False))
        setattr(self, kw["setObjectName"], w)
        return w


class _Widget:
    def __init__(self):
        self.option_box = NS(menu=_Menu())


class _SB:
    def __init__(self, tk):
        self.tk = tk
        self.messages = []
        self.handlers = mock.MagicMock()
        self.loaded_ui = mock.MagicMock()  # the windows RenderingSlots.__init__ reads

    def message_box(self, msg, *buttons):
        self.messages.append(msg)

    def apply_visibility_policy(self, widget):
        return False  # every control served (Maya)

    def progress(self, text=""):
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            yield lambda *a, **k: None

        return _ctx()

    def progress_adapter(self, update):
        return None


# --- The fake toolkit -------------------------------------------------------------
class _FakeRenderUtils:
    """Stand-in for ``RenderUtils`` that records calls (no live render)."""

    def __init__(self, current="mayaSoftware", ipr_ok=True, arnold_error=None):
        self.calls = []
        self._arnold_error = arnold_error  # raised by ensure_arnold_options
        self._current = current
        self._renderers = [
            {"name": "mayaSoftware", "label": "Maya Software", "loaded": True},
            {"name": "mayaHardware2", "label": "Maya Hardware 2.0", "loaded": True},
            {"name": "arnold", "label": "Arnold", "loaded": False},
        ]
        self._ipr_ok = ipr_ok
        self.cameras = ["persp", "front", "side", "top"]
        self.settings = {"width": 1920, "height": 1080}
        self.builtin_dir = "builtin/render"

    def render_cameras(self):
        return list(self.cameras)

    def get_available_renderers(self):
        return list(self._renderers)

    def current_renderer(self):
        return self._current

    def supports_ipr(self, renderer=None):
        # The real gate: Software + the optional renderers; not Viewport 2.0.
        return (renderer or self._current) in ("arnold", "vray", "redshift", "mayaSoftware")

    def set_renderer(self, name):
        self.calls.append(("set_renderer", name))

    def render_camera(self, camera):
        self.calls.append(("render_camera", camera))

    def redo_previous_render(self):
        self.calls.append(("redo",))

    def start_ipr(self, camera, renderer):
        self.calls.append(("ipr", camera, renderer))
        return self._ipr_ok

    def prepare_arnold_preview(self):
        self.calls.append(("prepare_arnold",))

    def ensure_arnold_options(self):
        self.calls.append(("ensure_arnold",))
        if self._arnold_error is not None:
            raise self._arnold_error
        self.settings.setdefault("camera_samples", 3)

    def render_settings(self):
        return dict(self.settings)

    def set_render_settings(self, values):
        self.calls.append(("set_settings", dict(values)))
        self.settings.update(values)
        return len(values)

    def render_preset_store(self):
        return NS(user_dir="user/render", builtin_dir=self.builtin_dir)


class _NoArnoldRenderUtils(_FakeRenderUtils):
    """A host whose ``RenderUtils`` has no Arnold (Blender's): neither its render
    options nor the scene preparation exist there."""

    _ABSENT = ("ensure_arnold_options", "prepare_arnold_preview")

    def __getattribute__(self, name):
        if name in type(self)._ABSENT:
            raise AttributeError(name)
        return super().__getattribute__(name)


class _FakeExporter:
    """Stand-in for ``PlayblastExporter``: records constructor + export() kwargs."""

    TARGETS = {
        "mp4": NS(label="MP4 (H.264)", kind="encode"),
        "png_sequence": NS(label="PNG Sequence", kind="sequence"),
        "arnold": NS(label="Arnold Sequence", kind="arnold"),
    }
    instances = []
    results = []

    @classmethod
    def available_targets(cls):
        return [(name, t.label) for name, t in cls.TARGETS.items()]

    @classmethod
    def resolve_frame_range(cls, mode="custom", start=None, end=None):
        return 1, 120

    @staticmethod
    def scene_name():
        return "ShotA"

    def __init__(self, **kwargs):
        type(self).instances.append(self)
        self.ctor_kwargs = kwargs
        self.export_kwargs = None

    def export(self, **kwargs):
        self.export_kwargs = kwargs
        return list(type(self).results)


def _exporter(targets=None, results=()):
    """A fresh exporter class (its own records)."""
    return type(
        "Exporter",
        (_FakeExporter,),
        {
            "TARGETS": dict(targets or _FakeExporter.TARGETS),
            "instances": [],
            "results": list(results),
        },
    )


def _tk(render_utils=None, exporter=None, animated=True):
    tk = mock.MagicMock()
    tk.RenderUtils = render_utils or _FakeRenderUtils()
    tk.PlayblastExporter = exporter or _exporter()
    tk.AnimUtils.scene_has_animation.return_value = animated
    tk.DataNodes.scene_workspace.return_value = None
    return tk


def _slots(tk):
    migrated = Slots._legacy_repeat_last_migrated
    Slots._legacy_repeat_last_migrated = True  # no migration under test
    try:
        return RenderingSlots(_SB(tk))
    finally:
        Slots._legacy_repeat_last_migrated = migrated


# ===================================================================== Playblast
class TestExportPlayblastInit(unittest.TestCase):
    def setUp(self):
        self.tk = _tk()
        self.slots = _slots(self.tk)
        self.widget = _Widget()
        self.slots.tb000_init(self.widget)
        self.menu = self.widget.option_box.menu

    def test_the_output_picker_is_the_registry_then_its_bundles(self):
        labels = [label for label, _ in self.menu.cmb050._items]
        data = [d for _, d in self.menu.cmb050._items]
        self.assertEqual(
            labels,
            ["MP4 (H.264)", "PNG Sequence", "Arnold Sequence", "MP4 + PNG Sequence",
             "MP4 + Arnold Sequence"],
        )
        self.assertEqual(data[-2:], [["mp4", "png_sequence"], ["mp4", "arnold"]])
        self.assertEqual(self.menu.cmb050.restore_by, "text")

    def test_a_bundle_the_host_cannot_make_is_left_out(self):
        targets = {k: v for k, v in _FakeExporter.TARGETS.items() if k != "arnold"}
        slots = _slots(_tk(exporter=_exporter(targets)))
        widget = _Widget()
        slots.tb000_init(widget)
        labels = [label for label, _ in widget.option_box.menu.cmb050._items]
        self.assertNotIn("MP4 + Arnold Sequence", labels)
        self.assertIn("MP4 + PNG Sequence", labels)

    def test_the_camera_picker_lists_the_hosts_cameras(self):
        items = self.menu.cmb041._items
        self.assertEqual(items[0], ("Active Viewport", None))
        self.assertEqual([d for _, d in items[1:]], ["persp", "front", "side", "top"])
        self.assertEqual(self.menu.cmb041.restore_by, "text")

    def test_a_reshow_lists_a_new_camera_and_keeps_the_pick(self):
        self.menu.cmb041.setCurrentIndex(2)  # front
        self.tk.RenderUtils.cameras.append("laterCam")
        self.slots.tb000_init(self.widget)
        self.assertIn("laterCam", [d for _, d in self.menu.cmb041._items])
        self.assertEqual(self.menu.cmb041.currentData(), "front")

    def test_offscreen_capture_is_mayas(self):
        self.assertEqual(self.menu.chk056.property("requires"), "maya")
        for name in ("chk057", "chk058", "chk060"):
            self.assertIsNone(getattr(self.menu, name).property("requires"), name)

    def test_the_output_field_is_empty_and_shows_the_default(self):
        self.assertEqual(self.menu.t000.text(), "")
        self.assertEqual(
            self.menu.t000.placeholderText(), self.slots._default_playblast_path()
        )

    def test_a_reshow_rebuilds_nothing(self):
        built = list(self.menu.added)
        self.slots.tb000_init(self.widget)
        self.assertEqual(self.menu.added, built)

    def test_custom_range_spinboxes_toggle_and_take_the_playback_range(self):
        self.assertFalse(self.menu.s010._visible)
        self.assertEqual((self.menu.s010.value(), self.menu.s011.value()), (1, 120))
        self.menu.cmb010.setCurrentIndex(3)  # Custom Range
        self.assertTrue(self.menu.s010._visible)
        self.menu.cmb010.setCurrentIndex(0)
        self.assertFalse(self.menu.s011._visible)

    def test_split_output_base(self):
        tmpdir = tempfile.mkdtemp(prefix="rh_split_")
        self.addCleanup(__import__("shutil").rmtree, tmpdir, True)
        directory, name = self.slots._split_output_base(tmpdir)
        self.assertEqual(
            (os.path.normpath(directory), name), (os.path.normpath(tmpdir), "ShotA")
        )
        directory, name = self.slots._split_output_base(os.path.join(tmpdir, "myShot.mp4"))
        self.assertEqual((os.path.normpath(directory), name), (os.path.normpath(tmpdir), "myShot"))
        directory, name = self.slots._split_output_base("")
        self.assertEqual(os.path.join(directory, name), self.slots._default_playblast_path())
        # A .blend-relative path is the exporter's to resolve, never normalized.
        self.assertEqual(self.slots._split_output_base("//renders/shot"), ("//renders", "shot"))


class TestExportPlayblastAction(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rh_action_")
        self.addCleanup(__import__("shutil").rmtree, self.tmpdir, True)
        ffmpeg = mock.patch.object(ptk.VidUtils, "ensure_ffmpeg", return_value=None)
        self.ensure_ffmpeg = ffmpeg.start()
        self.addCleanup(ffmpeg.stop)

    def _run(self, exporter=None, animated=True, targets=("mp4",), start=2, end=8):
        self.exporter = exporter or _exporter()
        slots = _slots(_tk(exporter=self.exporter, animated=animated))
        widget = _Widget()
        slots.tb000_init(widget)
        menu = widget.option_box.menu
        menu.t000.setText(os.path.join(self.tmpdir, "shotName"))
        menu.cmb010.setCurrentIndex(3)  # custom
        menu.s010.setValue(start)
        menu.s011.setValue(end)
        menu.cmb040.setCurrentIndex(3)  # 1280 x 720
        menu.cmb050.addItems(["picked"])
        menu.cmb050.setItemData(len(menu.cmb050._items) - 1, list(targets))
        menu.cmb050.setCurrentIndex(len(menu.cmb050._items) - 1)
        menu.chk060.setChecked(True)
        slots.tb000(widget)
        return slots, menu

    def test_a_static_scene_is_refused_before_any_capture(self):
        slots, _ = self._run(animated=False)
        self.assertFalse(self.exporter.instances, "the exporter must not run")
        self.assertIn("No animation", slots.sb.messages[-1])

    def test_the_option_box_reaches_the_exporter(self):
        self._run()
        exporter = self.exporter.instances[0]
        self.assertEqual((exporter.ctor_kwargs["width"], exporter.ctor_kwargs["height"]), (1280, 720))
        self.assertIsNone(exporter.ctor_kwargs["camera"])  # Active Viewport
        self.assertTrue(exporter.ctor_kwargs["include_audio"])
        self.assertTrue(exporter.ctor_kwargs["off_screen"])
        kwargs = exporter.export_kwargs
        self.assertEqual(kwargs["targets"], ["mp4"])
        self.assertEqual(kwargs["range_mode"], "custom")
        self.assertEqual((kwargs["start"], kwargs["end"]), (2, 8))
        self.assertEqual(kwargs["name"], "shotName")
        self.assertEqual(os.path.normpath(kwargs["output_dir"]), os.path.normpath(self.tmpdir))

    def test_an_encoded_output_offers_ffmpeg_first(self):
        self.ensure_ffmpeg.side_effect = FileNotFoundError("FFmpeg ... declined")
        slots, _ = self._run(targets=("mp4",))
        self.assertFalse(self.exporter.instances, "export must not run")
        self.assertIn("FFmpeg", slots.sb.messages[-1])

    def test_sequence_and_native_outputs_never_ask_for_ffmpeg(self):
        targets = dict(_FakeExporter.TARGETS, mp4=NS(label="MP4 (H.264)", kind="native"))
        self._run(exporter=_exporter(targets), targets=("mp4", "png_sequence"))
        self.ensure_ffmpeg.assert_not_called()
        self.assertEqual(len(self.exporter.instances), 1)

    def test_an_inverted_custom_range_is_refused(self):
        slots, _ = self._run(start=9, end=2)
        self.assertFalse(self.exporter.instances)
        self.assertIn("Start frame", slots.sb.messages[-1])

    def test_results_are_reported_and_the_movie_opened(self):
        results = [
            ptk.ExportResult("mp4", "encode", output="C:/out/shotName.mp4"),
            ptk.ExportResult("png_sequence", "sequence", output=["a", "b"]),
        ]
        with mock.patch.object(ptk.FileUtils, "open_explorer") as opened:
            exporter = _exporter(results=results)
            slots = _slots(_tk(exporter=exporter))
            widget = _Widget()
            slots.tb000_init(widget)
            menu = widget.option_box.menu
            menu.chk058.setChecked(True)
            menu.cmb050.setCurrentIndex(3)  # MP4 + PNG Sequence
            slots.tb000(widget)
        opened.assert_called_once_with(os.path.normpath("C:/out/shotName.mp4"))
        self.assertIn("PNG Sequence: 2 frame(s)", slots.sb.messages[-1])

    def test_a_failed_target_is_reported(self):
        results = [ptk.ExportResult("mp4", "encode", error="no frames")]
        slots, _ = self._run(exporter=_exporter(results=results))
        self.assertIn("MP4 (H.264): no frames", slots.sb.messages[-1])


# ===================================================================== Render
class TestRenderInit(unittest.TestCase):
    def setUp(self):
        self.ru = _FakeRenderUtils()
        self.slots = _slots(_tk(render_utils=self.ru))
        self.widget = _Widget()
        self.slots.tb001_init(self.widget)
        self.menu = self.widget.option_box.menu

    def test_the_cameras_are_the_hosts_its_default_first(self):
        self.assertEqual([label for label, _ in self.menu.cmb002._items], self.ru.cameras)
        self.assertEqual(self.menu.cmb002.currentText(), "persp")

    def test_the_renderers_carry_their_names(self):
        self.assertEqual([d for _, d in self.menu.cmb003._items], ["mayaSoftware", "mayaHardware2", "arnold"])

    def test_ipr_is_gated_on_the_renderer(self):
        self.assertTrue(self.menu.chk001.isEnabled())
        self.menu.chk001.setChecked(True)
        self.menu.cmb003.select("mayaHardware2")
        self.assertFalse(self.menu.chk001.isEnabled())
        self.assertFalse(self.menu.chk001.isChecked())
        self.menu.cmb003.select("arnold")
        self.assertTrue(self.menu.chk001.isEnabled())

    def test_ipr_smart_redo_and_arnold_are_mayas(self):
        for name in ("chk001", "chk002", "s022", "s023", "s028"):
            self.assertEqual(getattr(self.menu, name).property("requires"), "maya", name)
        for name in ("cmb002", "cmb003", "s020", "s021"):
            self.assertIsNone(getattr(self.menu, name).property("requires"), name)

    def test_fields_show_the_scene_without_writing_and_never_restore(self):
        self.assertEqual((self.menu.s020.value(), self.menu.s021.value()), (1920, 1080))
        self.assertFalse(any(c[0] == "set_settings" for c in self.ru.calls))
        for name in ("s020", "s021", "s022", "s028"):
            self.assertFalse(getattr(self.menu, name).restore_state, name)

    def test_editing_a_field_writes_the_scene(self):
        self.menu.s020.setValue(640)
        self.assertIn(("set_settings", {"width": 640}), self.ru.calls)

    def test_only_the_users_arnold_pick_creates_its_options(self):
        self.assertFalse(self.menu.s022.isEnabled())
        self.menu.cmb003.select("arnold")  # a restore: programmatic
        self.assertNotIn(("ensure_arnold",), self.ru.calls)
        self.assertTrue(self.menu.s022.isEnabled())
        self.menu.cmb003.pick("arnold")  # the user
        self.assertIn(("ensure_arnold",), self.ru.calls)
        self.assertEqual(self.menu.s022.value(), 3)

    def test_an_arnold_pick_on_a_host_without_arnold_does_nothing(self):
        # The checks are the parity gate's host limit: a toolkit lacking the
        # Arnold steps never reaches them (and never raises out of the signal).
        ru = _NoArnoldRenderUtils()
        slots = _slots(_tk(render_utils=ru))
        widget = _Widget()
        slots.tb001_init(widget)
        widget.option_box.menu.cmb003.pick("arnold")
        self.assertFalse(any(c[0] == "ensure_arnold" for c in ru.calls))
        self.assertFalse(slots.sb.messages)

    def test_an_unavailable_mtoa_disables_the_fields(self):
        self.ru._arnold_error = RuntimeError("mtoa failed to initialize")
        self.menu.cmb003.pick("arnold")  # must not raise out of the signal
        self.assertFalse(self.menu.s022.isEnabled())
        self.assertIn("mtoa failed", self.slots.sb.messages[-1])

    def test_native_presets_drive_the_render_settings(self):
        presets = self.menu.presets
        self.assertTrue(self.menu.add_presets)
        self.assertEqual((presets.preset_dir, presets.builtin_dir), ("user/render", "builtin/render"))
        self.assertEqual(presets.value_provider(), self.ru.settings)
        self.assertEqual(presets.value_applier({"width": 960, "camera_samples": 8}), 2)
        self.assertEqual(self.menu.s020.value(), 960)

    def test_a_host_without_shipped_presets(self):
        ru = _FakeRenderUtils()
        ru.builtin_dir = None
        slots = _slots(_tk(render_utils=ru))
        widget = _Widget()
        slots.tb001_init(widget)
        self.assertIsNone(widget.option_box.menu.presets.builtin_dir)

    def test_a_show_rereads_the_scene_without_rebuilding(self):
        built = list(self.menu.added)
        self.menu.cmb002.setCurrentIndex(3)  # top
        self.ru.cameras.append("laterCam")
        self.ru.settings["width"] = 800
        self.slots.tb001_init(self.widget)
        self.assertEqual(self.menu.added, built)
        self.assertIn("laterCam", [label for label, _ in self.menu.cmb002._items])
        self.assertEqual(self.menu.cmb002.currentText(), "top")  # the pick kept
        self.assertEqual(self.menu.s020.value(), 800)


class TestRenderAction(unittest.TestCase):
    def setUp(self):
        self.ru = _FakeRenderUtils()
        self.slots = _slots(_tk(render_utils=self.ru))

    def _widget(self, camera="shotCam", renderer="mayaSoftware", ipr=False, smart=True):
        widget = _Widget()
        menu = widget.option_box.menu
        menu.cmb002 = _Combo()
        menu.cmb002.addItems([camera] if camera else [])
        menu.cmb003 = _Combo()
        menu.cmb003.addItems([renderer])
        menu.cmb003.setItemData(0, renderer)
        menu.chk001 = _Check(ipr)
        menu.chk002 = _Check(smart)
        return widget

    def test_renders_the_picked_camera(self):
        self.slots.tb001(self._widget())
        self.assertEqual(
            self.ru.calls, [("set_renderer", "mayaSoftware"), ("render_camera", "shotCam")]
        )

    def test_no_camera_warns_and_skips(self):
        self.slots.tb001(self._widget(camera=""))
        self.assertFalse(self.ru.calls)
        self.assertIn("No render camera", self.slots.sb.messages[-1])

    def test_smart_redo_only_when_nothing_changed(self):
        self.slots.tb001(self._widget())
        self.slots.tb001(self._widget())
        self.assertEqual(self.ru.calls[-1], ("redo",))
        self.slots.tb001(self._widget(camera="otherCam"))
        self.assertEqual(self.ru.calls[-1], ("render_camera", "otherCam"))

    def test_an_arnold_render_prepares_the_scene_first(self):
        calls = self.ru.calls
        self.slots.tb001(self._widget(renderer="arnold"))
        self.assertLess(calls.index(("prepare_arnold",)), calls.index(("render_camera", "shotCam")))
        calls.clear()
        self.slots.tb001(self._widget(renderer="mayaSoftware"))
        self.assertNotIn(("prepare_arnold",), calls)

    def test_a_host_without_arnold_renders_without_preparing(self):
        ru = _NoArnoldRenderUtils()
        slots = _slots(_tk(render_utils=ru))
        slots.tb001(self._widget(renderer="arnold"))
        self.assertEqual(ru.calls, [("set_renderer", "arnold"), ("render_camera", "shotCam")])

    def test_ipr_supersedes_a_render_and_a_launch_race_falls_back(self):
        self.slots.tb001(self._widget(renderer="arnold", ipr=True))
        self.assertFalse(any(c[0] == "render_camera" for c in self.ru.calls))
        self.ru._ipr_ok = False
        self.ru.calls.clear()
        self.slots.tb001(self._widget(ipr=True))
        self.assertIn(("render_camera", "shotCam"), self.ru.calls)
        self.assertFalse(self.slots.sb.messages, "no message: the option is gated")

    def test_a_render_refusal_is_shown(self):
        self.ru.render_camera = mock.Mock(side_effect=RuntimeError("no window"))
        self.slots.tb001(self._widget())
        self.assertIn("no window", self.slots.sb.messages[-1])


# ===================================================================== editors
class TestSettingsEditors(unittest.TestCase):
    def test_each_button_opens_the_hosts_editor_by_mayatks_name(self):
        tk = _tk()
        slots = _slots(tk)
        for slot, editor in (
            (slots.b001, "Render Settings"),
            (slots.b003, "Render Setup"),
            (slots.b004, "Rendering Flags"),
        ):
            with self.subTest(editor=editor):
                slot()
                tk.UiUtils.open_editor.assert_called_with(editor)

    def test_a_failed_open_is_shown(self):
        tk = _tk()
        tk.UiUtils.open_editor.return_value = None
        slots = _slots(tk)
        slots.b001()
        self.assertIn("Could not open", slots.sb.messages[-1])


# ===================================================================== in Maya
@unittest.skipUnless(_MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestRenderingInMaya(unittest.TestCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.slots = _slots(maya_module("mayatk"))

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_an_unsaved_scene_playblasts_as_playblast(self):
        self.assertEqual(self.slots._scene_base_name(), "playblast")

    def test_a_saved_scene_playblasts_under_its_name(self):
        tmpdir = tempfile.mkdtemp(prefix="rh_test_")
        self.addCleanup(__import__("shutil").rmtree, tmpdir, True)
        for file_name, base in (("MyShot.ma", "MyShot"), ("v1.test.ma", "v1.test")):
            with self.subTest(file_name=file_name):
                cmds.file(rename=os.path.join(tmpdir, file_name).replace("\\", "/"))
                cmds.file(save=True, type="mayaAscii")
                self.assertEqual(self.slots._scene_base_name(), base)
                self.assertTrue(self.slots._default_playblast_path().endswith(base))

    def test_the_default_is_the_active_projects_movie_folder(self):
        import mayatk as mtk

        path = self.slots._default_playblast_path()
        movies = ptk.Workspace.load(mtk.EnvUtils.workspace_root()).movie_dir()
        self.assertEqual(os.path.dirname(path), os.path.normpath(movies))

    def test_the_playblast_picker_is_the_real_registry(self):
        import mayatk as mtk

        widget = _Widget()
        self.slots.tb000_init(widget)
        menu = widget.option_box.menu
        data = [d for _, d in menu.cmb050._items]
        for name, _label in mtk.PlayblastExporter.available_targets():
            self.assertIn([name], data)
        self.assertIn(["mp4", "arnold"], data)  # Maya renders Arnold

    def test_the_default_follows_a_newly_saved_scene(self):
        widget = _Widget()
        self.slots.tb000_init(widget)
        menu = widget.option_box.menu
        tmpdir = tempfile.mkdtemp(prefix="rh_follow_")
        self.addCleanup(__import__("shutil").rmtree, tmpdir, True)
        cmds.file(rename=os.path.join(tmpdir, "ShotB.ma").replace("\\", "/"))
        cmds.file(save=True, type="mayaAscii")
        self.slots.tb000_init(widget)  # refresh_on_show re-runs the init
        self.assertEqual(os.path.basename(menu.t000.placeholderText()), "ShotB")
        directory, name = self.slots._split_output_base(menu.t000.text())
        self.assertEqual(os.path.join(directory, name), self.slots._default_playblast_path())

    def test_the_render_cameras_put_persp_first(self):
        cmds.rename(cmds.camera()[0], "renderCam")
        widget = _Widget()
        self.slots.tb001_init(widget)
        labels = [label for label, _ in widget.option_box.menu.cmb002._items]
        self.assertEqual(labels[0], "persp")
        self.assertIn("renderCam", labels)
        self.assertNotIn("perspShape", labels)

    def test_a_static_scene_blocks_the_playblast(self):
        cmds.polyCube(name="static_cube")
        with mock.patch("mayatk.PlayblastExporter") as exporter:
            self.slots.tb000(_Widget())
        exporter.assert_not_called()
        self.assertIn("no animation", self.slots.sb.messages[-1].lower())


if __name__ == "__main__":
    unittest.main()
