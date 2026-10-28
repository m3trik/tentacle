#!/usr/bin/python
# coding=utf-8
"""The HDR Manager panel's one Slots class, shared by both hosts.

It reaches its host only through ``self.tk``: a fake toolkit's ``HdrManager``
stands in for ``mtk`` / ``btk``'s and records what the panel asks of it, so
these run as plain pytest with no DCC. The ``.ui`` checks read tentacle's
``ui/tools/hdr_manager.ui``; the header lock runs the real uitk ComboBox
(offscreen Qt). In Maya, the same class drives the real ``mtk``. The managers
themselves (the knobs, the network, ``defer_apply``, ``select``) are the
libraries': mayatk's ``test_hdr_manager.py``, blendertk's ``test_light_utils.py``.
"""

import logging
import os
import shutil
import struct
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import tentacle
from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots._slots import Slots
from tentacle.slots.tools.hdr_manager import HdrManagerSlots

UI_PATH = Path(tentacle.__file__).resolve().parent / "ui" / "tools" / "hdr_manager.ui"

#: mayatk's knobs (an Arnold skydome) and blendertk's (a world shader: no
#: per-light samples, no viewport-only backdrop).
MAYA_KNOBS = (
    "rotation",
    "visibility",
    "preview",
    "intensity",
    "exposure",
    "resolution",
    "samples",
    "diffuse",
    "specular",
)
BLENDER_KNOBS = tuple(k for k in MAYA_KNOBS if k not in ("samples", "preview"))

#: Each knob's reading with no environment (mayatk's defaults).
DEFAULTS = {
    "rotation": 0.0,
    "visibility": False,
    "preview": False,
    "intensity": 1.0,
    "exposure": 0.0,
    "resolution": 1000,
    "samples": 1,
    "diffuse": 1.0,
    "specular": 1.0,
}

NONE = HdrManagerSlots.NONE_TOKEN


class _FakeManager:
    """The ``HdrManager`` contract the panel reads: ``KNOBS``, a property per
    knob (only the listed ones exist), ``hdr_env`` None until an environment is
    live, and the writes recorded. *selectable* / *arnold* add mayatk's
    Maya-only ``select`` / ``arnold_loaded``."""

    def __init__(self, env=None, knobs=MAYA_KNOBS, selectable=False, arnold=None):
        self.KNOBS = knobs
        self._env = env
        self.set_paths = []
        self.networks = []
        self.clear_calls = 0
        self.deferred = []
        self.selected = []
        self.parts = {}
        self.build_result = "aiSkyDomeLight_"
        self.hdr_file_path = None
        for knob in knobs:
            setattr(self, knob, DEFAULTS[knob])
        if selectable:
            self.select = self._select
        if arnold is not None:
            self.arnold_loaded = lambda: arnold

    @property
    def hdr_env(self):
        return self._env

    @hdr_env.setter
    def hdr_env(self, value):
        self.set_paths.append(value)
        self._env = "aiSkyDomeLight_"

    def create_network(self, **kwargs):
        self.networks.append(kwargs)
        self._env = self.build_result
        return self.build_result

    def clear(self):
        self.clear_calls += 1
        self._env = None

    def defer_apply(self, callback):
        self.deferred.append(callback)

    def _select(self, part):
        self.selected.append(part)
        return self.parts.get(part)


class _StubFooter:
    """Captures the last status and its level."""

    def __init__(self):
        self.text = None
        self.level = None

    def setText(self, text, level=None):
        self.text = text or ""
        self.level = level


class _StubCombo:
    """A combobox stand-in holding each row's userData."""

    def __init__(self, items=None, current=None):
        self.current_index = current
        self._items = list(items or [])
        self.last_header = None
        # Mirrors ComboBox.restore_state: add() resets it to ``not has_header``.
        self.restore_state = True

    def count(self):
        return len(self._items)

    def itemData(self, i):
        return self._items[i]

    def currentData(self):
        if self.current_index is not None and 0 <= self.current_index < len(
            self._items
        ):
            return self._items[self.current_index]
        return None

    def findData(self, data):
        try:
            return self._items.index(data)
        except ValueError:
            return -1

    def blockSignals(self, blocked):
        pass

    def setCurrentIndex(self, index):
        self.current_index = index

    def addItem(self, text, data=None):
        self._items.append(data)

    def insertItem(self, index, text, data=None):
        self._items.insert(index, data)
        if self.current_index is not None and index <= self.current_index:
            self.current_index += 1

    def add(self, pairs, ascending=True, clear=False, header=None, **kwargs):
        self.last_header = header
        self.restore_state = not bool(header)
        if clear:
            self._items = []
        for _text, data in pairs:
            self._items.append(data)


#: The values the panel's controls hold in a fresh stub ui.
CONTROL_VALUES = {
    "spn_intensity": 2.0,
    "spn_exposure": 1.5,
    "spn_resolution": 2048,
    "spn_samples": 3,
    "spn_diffuse": 0.5,
    "spn_specular": 0.25,
}


class _StubUi:
    """A footer, a stub dropdown, and mock controls holding CONTROL_VALUES."""

    def __init__(self, combo=None, rotation=30):
        self.destroyed = mock.MagicMock(name="destroyed")  # the cleanup hook
        self.footer = _StubFooter()
        self.cmb000 = combo if combo is not None else _StubCombo()
        self.slider000 = mock.MagicMock(name="slider000")
        self.slider000.sliderPosition.return_value = rotation
        for name, value in CONTROL_VALUES.items():
            widget = mock.MagicMock(name=name)
            widget.value.return_value = value
            setattr(self, name, widget)


def _panel(manager=None, ui=None, src="", tk=None):
    """A Slots instance over *ui* (a :class:`_StubUi`) and a fake toolkit whose
    ``HdrManager()`` is *manager* and whose texture folder is *src* -- or *tk*,
    handed over before the panel is built, as ``Slots.tk`` is."""
    sb = mock.MagicMock()
    if tk is not None:
        sb.tk = tk
    else:
        sb.tk.HdrManager.return_value = manager or _FakeManager()
        sb.tk.EnvUtils.source_images_dir.return_value = src
    # Two toggles, two distinct option instances.
    sb.ToggleOption.side_effect = lambda **kw: mock.MagicMock(name=kw["icon"])
    sb.loaded_ui.hdr_manager = ui or _StubUi()
    slots = HdrManagerSlots(sb)
    slots.logger.setLevel(logging.CRITICAL)  # assert on the footer, not the log
    return slots, sb


def _write_truncated_hdr(path=None):
    """A Radiance HDR whose header declares 16x16 but carries no data."""
    blob = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 16 +X 16\n\x02\x02\x00\x10"
    if path is None:
        f = tempfile.NamedTemporaryFile(suffix=".hdr", delete=False)
        f.write(blob)
        f.close()
        return f.name
    with open(path, "wb") as fh:
        fh.write(blob)
    return path


def _write_complete_hdr(path):
    """An 8x4 flat-RGBE Radiance HDR: complete, and 2:1 like a latlong."""
    blob = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 4 +X 8\n" + b"\x10" * (8 * 4 * 4)
    with open(path, "wb") as f:
        f.write(blob)


# A 32x16 (2:1) RLE HDR whose scanlines never arrive: an environment map by
# shape, so a folder add reaches its integrity check and counts it skipped.
_TRUNCATED_LATLONG_HDR = (
    b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 16 +X 32\n\x02\x02\x00\x20"
)


def _write_exr_header(path, width, height):
    """A header-only OpenEXR of *width* x *height* (enough to size, not decode)."""
    window = struct.pack("<iiii", 0, 0, width - 1, height - 1)
    blob = (
        b"\x76\x2f\x31\x01"
        + struct.pack("<I", 2)
        + b"dataWindow\0box2i\0"
        + struct.pack("<i", len(window))
        + window
        + b"\0"
    )
    with open(path, "wb") as f:
        f.write(blob)


class _PanelCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)

    def tmpdir(self):
        path = tempfile.mkdtemp(prefix="tcl_hdr_")
        self.addCleanup(shutil.rmtree, path, True)
        return path


class TestHdrManagerPanelSetup(_PanelCase):
    def test_composes_the_hosts_manager_and_follows_the_scene(self):
        slots, sb = _panel()
        sb.tk.HdrManager.assert_called_once_with()
        jobs = sb.tk.ScriptJobManager.instance.return_value
        subscribed = {c.args[0]: c.args[1] for c in jobs.subscribe.call_args_list}
        self.assertEqual(
            subscribed,
            {
                "SceneOpened": slots._on_scene_changed,
                "NewSceneOpened": slots._on_scene_changed,
                "SceneImported": slots._on_scene_changed,
                "Undo": slots._sync_ui_to_scene,
                "Redo": slots._sync_ui_to_scene,
            },
        )
        jobs.connect_cleanup.assert_called_once_with(sb.loaded_ui.hdr_manager, owner=slots)
        sb.QtCore.QTimer.singleShot.assert_called_once_with(0, slots._initialize_ui)

    def test_an_event_the_host_lacks_never_blocks_the_open(self):
        """Blender has no "SceneImported": its subscribe raises."""
        jobs = mock.MagicMock()

        def subscribe(event, handler, owner):
            if event == "SceneImported":
                raise ValueError("no Blender backing")

        jobs.subscribe.side_effect = subscribe
        sb = mock.MagicMock()
        sb.tk.ScriptJobManager.instance.return_value = jobs
        sb.loaded_ui.hdr_manager = _StubUi()
        HdrManagerSlots(sb)  # no raise
        self.assertEqual(jobs.subscribe.call_count, 5)
        jobs.connect_cleanup.assert_called_once()

    def test_initialize_wires_every_control_of_a_full_host(self):
        manager = _FakeManager(knobs=MAYA_KNOBS)
        slots, sb = _panel(manager)
        ui = sb.loaded_ui.hdr_manager
        slots._initialize_ui()
        sb.add_reset_buttons.assert_called_once_with(ui, skip=())
        ui.spn_samples.setEnabled.assert_not_called()
        icons = [c.kwargs["icon"] for c in sb.ToggleOption.call_args_list]
        self.assertEqual(icons, ["screen", "camera"])
        slots._viewport_toggle.widget.setEnabled.assert_not_called()
        slots._viewport_toggle.toggled.connect.assert_called_once_with(
            slots._on_viewport_visible
        )
        slots._render_toggle.toggled.connect.assert_called_once_with(
            slots._on_render_visible
        )
        option_box = ui.slider000.option_box
        option_box.add_value.assert_called_once_with(width=46, suffix="°")
        self.assertEqual(
            [c.args[0] for c in option_box.add_option.call_args_list],
            [slots._viewport_toggle, slots._render_toggle],
        )
        option_box.find_option.assert_called_once_with(sb.ValueOption)

    def test_a_knob_the_host_lacks_disables_its_control(self):
        """Blender's world has no per-light samples and no viewport-only
        backdrop: those controls stay, disabled, with no reset button."""
        manager = _FakeManager(knobs=BLENDER_KNOBS)
        slots, sb = _panel(manager)
        ui = sb.loaded_ui.hdr_manager
        slots._initialize_ui()
        ui.spn_samples.setEnabled.assert_called_once_with(False)
        ui.spn_samples.setToolTip.assert_called_once_with(HdrManagerSlots._UNAVAILABLE)
        sb.add_reset_buttons.assert_called_once_with(ui, skip=(ui.spn_samples,))
        for name in ("spn_intensity", "spn_resolution", "spn_diffuse"):
            getattr(ui, name).setEnabled.assert_not_called()
        slots._viewport_toggle.widget.setEnabled.assert_called_once_with(False)
        viewport = sb.ToggleOption.call_args_list[0].kwargs
        self.assertEqual(viewport["tooltip_on"], HdrManagerSlots._UNAVAILABLE)
        # The sync never reads a knob the manager lacks (it has no attribute).
        self.assertFalse(hasattr(manager, "samples"))

    def test_the_arnold_hint_shows_only_where_the_plugin_is_unloaded(self):
        for arnold, expected in ((False, True), (True, False), (None, False)):
            with self.subTest(arnold=arnold):
                slots, sb = _panel(_FakeManager(arnold=arnold))
                slots._initialize_ui()
                hinted = "Arnold" in (sb.loaded_ui.hdr_manager.footer.text or "")
                self.assertIs(hinted, expected)

    def test_the_header_menu_and_help(self):
        slots, sb = _panel()
        header = mock.MagicMock()
        slots.header_init(header)
        header.config_buttons.assert_called_once_with("refresh", "menu", "collapse", "hide")
        header.refresh_requested.connect.assert_called_once_with(
            slots._refresh_and_sync_combo
        )
        names = [c.kwargs.get("setObjectName") for c in header.menu.add.call_args_list]
        self.assertEqual(names, [None, "open_sourceimages", None, "clear_network"])
        header.set_help_text.assert_called_once()

    def test_the_dropdown_menus(self):
        slots, sb = _panel(_FakeManager(selectable=True))
        combo = mock.MagicMock()
        slots.cmb000_init(combo)
        combo.before_popup_shown.connect.assert_called_once_with(
            slots._refresh_and_sync_combo
        )
        self.assertIs(combo.restore_state, False)
        names = [c.kwargs.get("setObjectName") for c in combo.menu.add.call_args_list]
        self.assertEqual(
            names,
            [
                "ctx_select_skydome",
                "ctx_select_transform",
                "ctx_select_file_node",
                None,
                "ctx_reveal_in_explorer",
            ],
        )
        combo.menu.add.return_value.setEnabled.assert_not_called()
        menu = combo.option_box.menu
        add_mode = next(
            c.kwargs
            for c in menu.add.call_args_list
            if c.kwargs.get("setObjectName") == "cmb_add_mode"
        )
        # The combo saves an index: the order is the dispatch.
        self.assertEqual(
            add_mode["addItems"], [label for label, _ in HdrManagerSlots._ADD_MODES]
        )
        self.assertEqual(
            [token for _, token in HdrManagerSlots._ADD_MODES], ["copy", "move", "link"]
        )

    def test_the_select_items_are_disabled_where_the_host_cant_select(self):
        """A Blender world is not a selectable object: its manager has no
        ``select``."""
        slots, sb = _panel(_FakeManager(knobs=BLENDER_KNOBS))
        combo = mock.MagicMock()
        slots.cmb000_init(combo)
        self.assertEqual(combo.menu.add.return_value.setEnabled.call_count, 3)


class TestHdrManagerPanelSync(_PanelCase):
    def test_the_controls_show_the_scenes_environment(self):
        manager = _FakeManager(env="aiSkyDomeLight_")
        manager.rotation, manager.intensity, manager.resolution = 370.4, 3.0, 4096
        manager.visibility, manager.preview = True, False
        slots, sb = _panel(manager)
        ui = sb.loaded_ui.hdr_manager
        slots._viewport_toggle = mock.MagicMock()
        slots._render_toggle = mock.MagicMock()
        slots._sync_ui_to_scene()
        ui.slider000.setSliderPosition.assert_called_once_with(10)  # 370 wraps
        ui.spn_intensity.setValue.assert_called_once_with(3.0)
        ui.spn_resolution.setValue.assert_called_once_with(4096)
        ui.spn_samples.setValue.assert_called_once_with(1)
        slots._viewport_toggle.set_on.assert_called_once_with(False, emit=False)
        slots._render_toggle.set_on.assert_called_once_with(True, emit=False)

    def test_a_knob_reading_none_leaves_its_control(self):
        """Blender's automatic importance-map size reads None: the control keeps
        its value rather than showing a size Cycles isn't using."""
        manager = _FakeManager(knobs=BLENDER_KNOBS)
        manager.resolution = None
        slots, sb = _panel(manager)
        ui = sb.loaded_ui.hdr_manager
        slots._sync_ui_to_scene()
        ui.spn_resolution.setValue.assert_not_called()
        ui.spn_samples.setValue.assert_not_called()  # not a Blender knob
        ui.spn_intensity.setValue.assert_called_once_with(1.0)

    def test_each_control_writes_its_knob_live(self):
        slots, sb = _panel(_FakeManager(env="aiSkyDomeLight_"))
        manager = slots.manager
        slots.slider000(90, None)
        slots.spn_intensity(2.5)
        slots.spn_exposure(-1.0)
        slots.spn_resolution(512)
        slots.spn_samples(4)
        slots.spn_diffuse(0.0)
        slots.spn_specular(0.75)
        slots._on_viewport_visible(1)
        slots._on_render_visible(1)
        self.assertEqual(
            (
                manager.rotation,
                manager.intensity,
                manager.exposure,
                manager.resolution,
                manager.samples,
                manager.diffuse,
                manager.specular,
                manager.preview,
                manager.visibility,
            ),
            (90, 2.5, -1.0, 512, 4, 0.0, 0.75, True, True),
        )
        self.assertEqual(manager.deferred, [])  # live, never deferred

    def test_a_control_for_a_knob_the_host_lacks_writes_nothing(self):
        slots, sb = _panel(_FakeManager(knobs=BLENDER_KNOBS))
        slots.spn_samples(4)
        slots._on_viewport_visible(True)
        self.assertFalse(hasattr(slots.manager, "samples"))
        self.assertFalse(hasattr(slots.manager, "preview"))

    def test_the_render_toggle_applies_synchronously(self):
        """Regression (issue 1: gray IPR): the Visible flag is set at once, like
        the other live controls -- deferring it let a running IPR starve it."""
        slots, sb = _panel(_FakeManager(env="aiSkyDomeLight_"))
        slots._on_render_visible(False)
        self.assertIs(slots.manager.visibility, False)
        self.assertEqual(slots.manager.deferred, [])

    def test_the_view_flags_fall_back_before_the_toggles_exist(self):
        manager = _FakeManager()
        manager.visibility = True  # Blender's world shows as the backdrop
        slots, sb = _panel(manager)
        self.assertIs(slots.hdr_map_visibility, True)
        self.assertIs(slots.hdr_map_preview, False)


class TestHdrManagerPanelApply(_PanelCase):
    def _pick(self, path, env=None, **kw):
        slots, sb = _panel(_FakeManager(env=env, **kw), _StubUi(_StubCombo([NONE, path], 1)))
        return slots, sb.loaded_ui.hdr_manager

    def test_a_pick_hands_the_apply_to_the_manager(self):
        """Regression (2026-06-16 crash, 2026-06-21 black render): a pick never
        mutates the scene inside the combo signal; Maya's manager defers it to
        idle, Blender's runs it at once."""
        slots, ui = self._pick("C:/img/sky.exr")
        slots.cmb000(1, ui.cmb000)
        self.assertEqual(slots.manager.deferred, [slots._apply_selection])
        self.assertEqual(slots.manager.set_paths, [])
        self.assertEqual(slots.manager.networks, [])
        self.assertIn("Applying sky.exr", ui.footer.text)

    def test_nothing_picked_schedules_nothing(self):
        slots, ui = self._pick("C:/img/sky.exr")
        ui.cmb000.current_index = None
        slots.cmb000(0, ui.cmb000)
        self.assertEqual(slots.manager.deferred, [])

    def test_a_pick_without_an_environment_builds_one_from_the_controls(self):
        slots, ui = self._pick("C:/img/sky.exr")
        slots._apply_selection()
        self.assertEqual(
            slots.manager.networks,
            [
                {
                    "hdrMap": "C:/img/sky.exr",
                    "hdrMapVisibility": False,
                    "intensity": 2.0,
                    "exposure": 1.5,
                    "rotation": 30,
                    "resolution": 2048,
                    "samples": 3,
                    "diffuse": 0.5,
                    "specular": 0.25,
                    "preview": False,
                }
            ],
        )
        self.assertEqual(slots.manager.set_paths, [])
        self.assertEqual(ui.footer.level, "success")
        self.assertIn("sky.exr", ui.footer.text)

    def test_a_pick_with_a_live_environment_swaps_the_map_in_place(self):
        slots, ui = self._pick("C:/img/dusk.exr", env="aiSkyDomeLight_")
        slots._apply_selection()
        self.assertEqual(slots.manager.set_paths, ["C:/img/dusk.exr"])
        self.assertEqual(slots.manager.networks, [])
        self.assertEqual(ui.footer.level, "success")

    def test_an_incomplete_image_is_never_wired_and_the_dropdown_re_mirrors(self):
        """Regression: a truncated cloud HDR crashed Viewport 2.0; and a refused
        pick left the dropdown showing a map that wasn't lighting the scene."""
        path = _write_truncated_hdr()
        self.addCleanup(os.remove, path)
        active = "C:/proj/sourceimages/active.hdr"
        manager = _FakeManager(env="aiSkyDomeLight_")
        manager.hdr_file_path = active
        slots, sb = _panel(manager, _StubUi(_StubCombo([active, path], 1)))
        ui = sb.loaded_ui.hdr_manager
        slots._apply_selection()
        self.assertEqual(manager.set_paths, [])
        self.assertEqual(ui.cmb000.current_index, 0)  # back on the live map
        self.assertEqual(ui.footer.level, "error")
        self.assertIn("truncated", ui.footer.text)
        sb.message_box.assert_not_called()  # a casual pick: no modal

    def test_a_build_that_fails_re_mirrors_to_none(self):
        """Maya without Arnold: create_network builds nothing (None)."""
        slots, ui = self._pick("C:/x.exr")
        slots.manager.build_result = None
        slots._apply_selection()
        self.assertEqual(ui.cmb000.current_index, 0)  # the None row
        self.assertEqual(ui.footer.level, "warning")

    def test_none_removes_the_environment(self):
        slots, sb = _panel(
            _FakeManager(env="aiSkyDomeLight_"), _StubUi(_StubCombo([NONE], 0))
        )
        ui = sb.loaded_ui.hdr_manager
        slots.cmb000(0, ui.cmb000)
        self.assertIn("Removing", ui.footer.text)
        self.assertEqual(slots.manager.clear_calls, 0)  # handed to the manager
        slots.manager.deferred[0]()
        self.assertEqual(slots.manager.clear_calls, 1)
        self.assertEqual(ui.footer.level, "success")
        self.assertEqual(slots.manager.set_paths, [])

    def test_none_without_an_environment_only_informs(self):
        slots, sb = _panel(_FakeManager(), _StubUi(_StubCombo([NONE], 0)))
        ui = sb.loaded_ui.hdr_manager
        slots._apply_selection()
        self.assertEqual(slots.manager.clear_calls, 0)
        self.assertEqual(ui.footer.level, "info")
        self.assertIn("None", ui.footer.text)

    def test_clear_network(self):
        slots, sb = _panel(_FakeManager(env="aiSkyDomeLight_"))
        slots.clear_network()
        self.assertEqual(slots.manager.clear_calls, 1)
        slots.clear_network()  # nothing left
        self.assertEqual(slots.manager.clear_calls, 1)
        self.assertIn("No HDR network", sb.loaded_ui.hdr_manager.footer.text)


class TestHdrManagerPanelValidate(_PanelCase):
    def test_a_missing_file_is_allowed(self):
        slots, sb = _panel()
        self.assertTrue(slots._validate_or_warn("C:/no/such/x.hdr"))

    def test_an_incomplete_file_raises_a_digestible_modal(self):
        path = _write_truncated_hdr()
        self.addCleanup(os.remove, path)
        slots, sb = _panel()
        self.assertFalse(slots._validate_or_warn(path))
        self.assertEqual(sb.loaded_ui.hdr_manager.footer.level, "error")
        message = sb.message_box.call_args.args[0]
        low = message.lower()
        for cause in ("cloud", "sync", "free up space"):
            self.assertIn(cause, low)
        self.assertNotIn(path, message)  # the raw path goes to the console

    def test_no_modal_when_suppressed(self):
        path = _write_truncated_hdr()
        self.addCleanup(os.remove, path)
        slots, sb = _panel()
        self.assertFalse(slots._validate_or_warn(path, dialog=False))
        sb.message_box.assert_not_called()

    def test_notify_keeps_the_popup_digestible(self):
        slots, sb = _panel()
        slots._notify(
            "short footer",
            level="error",
            detail="full boom at C:/secret/raw/path.hdr",
            dialog=True,
            dialog_text="digestible dialog body",
        )
        self.assertEqual(sb.loaded_ui.hdr_manager.footer.text, "short footer")
        sb.message_box.assert_called_once_with("Error: digestible dialog body", "Ok")


class TestHdrManagerPanelAdd(_PanelCase):
    def _slots(self, mode, src="", env="aiSkyDomeLight_", picked=None):
        slots, sb = _panel(_FakeManager(env=env), src=src)
        slots._add_mode = lambda: mode
        if picked is not None:
            slots._pick_hdr_paths = lambda start: picked
        return slots, sb.loaded_ui.hdr_manager

    def _add_folder(self, slots, folder):
        slots._add_hdrs(slots._folder_hdrs(folder), where="folder", careful=False)

    def test_link_adds_the_complete_and_skips_the_truncated(self):
        folder = self.tmpdir()
        _write_complete_hdr(os.path.join(folder, "good.hdr"))
        with open(os.path.join(folder, "bad.hdr"), "wb") as f:
            f.write(_TRUNCATED_LATLONG_HDR)
        slots, ui = self._slots("link")
        self._add_folder(slots, folder)
        self.assertEqual([os.path.basename(p) for p in slots.manager.set_paths], ["good.hdr"])
        self.assertIn("Added 1", ui.footer.text)
        self.assertIn("skipped", ui.footer.text)

    def test_an_add_with_no_environment_builds_one_from_the_controls(self):
        """The add lights the scene as a pick does (the old Maya flow built a
        bare dome at Arnold's defaults instead)."""
        folder = self.tmpdir()
        good = os.path.join(folder, "good.hdr")
        _write_complete_hdr(good)
        slots, ui = self._slots("link", env=None)
        slots._add_hdrs([good], where="selection", careful=True)
        self.assertEqual([n["hdrMap"] for n in slots.manager.networks], [good])
        self.assertEqual(slots.manager.networks[0]["intensity"], 2.0)
        self.assertIn("Linked", ui.footer.text)

    def test_an_empty_or_all_truncated_folder_warns(self):
        folder = self.tmpdir()
        slots, ui = self._slots("link")
        self._add_folder(slots, folder)
        self.assertEqual(ui.footer.level, "warning")
        with open(os.path.join(folder, "bad.hdr"), "wb") as f:
            f.write(_TRUNCATED_LATLONG_HDR)
        self._add_folder(slots, folder)
        self.assertEqual(slots.manager.set_paths, [])
        self.assertIn("incomplete", ui.footer.text)

    def test_copy_brings_the_file_into_sourceimages(self):
        folder, src = self.tmpdir(), self.tmpdir()
        _write_complete_hdr(os.path.join(folder, "good.hdr"))
        slots, ui = self._slots("copy", src=src)
        self._add_folder(slots, folder)
        self.assertTrue(os.path.exists(os.path.join(src, "good.hdr")))
        self.assertEqual(
            os.path.normcase(slots.manager.set_paths[0]),
            os.path.normcase(os.path.join(src, "good.hdr")),
        )
        self.assertEqual(ui.footer.level, "success")

    def test_copy_without_a_project_says_so(self):
        folder = self.tmpdir()
        _write_complete_hdr(os.path.join(folder, "good.hdr"))
        slots, ui = self._slots("copy", src="")
        self._add_folder(slots, folder)
        self.assertEqual(slots.manager.set_paths, [])
        self.assertIn("set a project", ui.footer.text)

    def test_copy_never_reuses_a_truncated_existing_file(self):
        folder, src = self.tmpdir(), self.tmpdir()
        _write_complete_hdr(os.path.join(folder, "x.hdr"))
        _write_truncated_hdr(os.path.join(src, "x.hdr"))
        slots, ui = self._slots("copy", src=src)
        self._add_folder(slots, folder)
        self.assertEqual(slots.manager.set_paths, [])
        self.assertEqual(ui.footer.level, "warning")

    def test_a_file_in_a_sourceimages_subfolder_is_used_in_place(self):
        """Regression (2026-06-16): Copy duplicated sourceimages/hdr/x.hdr into
        the sourceimages root instead of wiring it where it lives."""
        src = self.tmpdir()
        sub = os.path.join(src, "hdr")
        os.makedirs(sub)
        f = os.path.join(sub, "env.hdr")
        _write_complete_hdr(f)
        slots, ui = self._slots("copy", src=src)
        slots._add_hdrs([f], where="hdr", careful=False)
        self.assertFalse(os.path.exists(os.path.join(src, "env.hdr")))
        self.assertEqual(
            os.path.normcase(slots.manager.set_paths[0]),
            os.path.normcase(os.path.normpath(f)),
        )

    def test_a_careful_overwrite_asks_first(self):
        folder, src = self.tmpdir(), self.tmpdir()
        _write_complete_hdr(os.path.join(folder, "x.hdr"))
        _write_complete_hdr(os.path.join(src, "x.hdr"))
        slots, ui = self._slots("copy", src=src)
        slots.sb.message_box.return_value = "No"
        slots._add_hdrs([os.path.join(folder, "x.hdr")], where="selection", careful=True)
        self.assertIn("already exists", slots.sb.message_box.call_args.args[0])
        self.assertEqual(slots.manager.set_paths, [])
        self.assertIn("cancelled", ui.footer.text)

    def test_the_dialog_dispatch(self):
        """One loose file is careful (a modal on a bad one); a folder or several
        files is a bulk add (skip + count, no per-file modal)."""
        folder = self.tmpdir()
        good = os.path.join(folder, "good.hdr")
        _write_complete_hdr(good)
        bad = _write_truncated_hdr(os.path.join(folder, "bad.hdr"))

        slots, ui = self._slots("link", picked=[])
        slots.add_hdr()
        self.assertEqual(slots.manager.set_paths, [])

        slots, ui = self._slots("link", picked=[good])
        slots.add_hdr()
        self.assertEqual(slots.manager.set_paths, [good])
        self.assertIn("Linked", ui.footer.text)

        slots, ui = self._slots("link", picked=[bad])
        slots.add_hdr()
        self.assertEqual(slots.manager.set_paths, [])
        slots.sb.message_box.assert_called_once()

        os.remove(bad)
        with open(bad, "wb") as fh:
            fh.write(_TRUNCATED_LATLONG_HDR)
        slots, ui = self._slots("link", picked=[folder])
        slots.add_hdr()
        self.assertEqual(len(slots.manager.set_paths), 1)
        self.assertIn("Added 1", ui.footer.text)
        slots.sb.message_box.assert_not_called()

        second = os.path.join(folder, "second.hdr")
        _write_complete_hdr(second)
        slots, ui = self._slots("link", picked=[good, second])
        slots.add_hdr()
        self.assertIn("Added 2", ui.footer.text)


class TestHdrManagerPanelList(_PanelCase):
    def _refresh(self, src, combo=None):
        slots, sb = _panel(src=src, ui=_StubUi(combo or _StubCombo()))
        slots._refresh_combo()
        return slots, sb.loaded_ui.hdr_manager

    def test_no_project_lists_only_none(self):
        slots, ui = self._refresh("")
        self.assertEqual([ui.cmb000.itemData(i) for i in range(ui.cmb000.count())], [NONE])
        self.assertIsNone(ui.cmb000.last_header)  # a header hides the active map
        self.assertFalse(ui.cmb000.restore_state)
        self.assertEqual(ui.footer.level, "warning")

    def test_sourceimages_is_scanned_recursively_none_first(self):
        src = self.tmpdir()
        os.makedirs(os.path.join(src, "hdr"))
        _write_complete_hdr(os.path.join(src, "hdr", "env.hdr"))
        slots, ui = self._refresh(src)
        data = [ui.cmb000.itemData(i) for i in range(ui.cmb000.count())]
        self.assertEqual(data[0], NONE)
        self.assertEqual([os.path.basename(d) for d in data[1:]], ["env.hdr"])
        self.assertIsNone(ui.cmb000.last_header)
        self.assertFalse(ui.cmb000.restore_state)

    def test_an_unchanged_listing_skips_the_rebuild(self):
        """Rebuilding the model right before the popup shows drops the first
        click."""
        src = self.tmpdir()
        path = os.path.join(src, "a.hdr")
        _write_complete_hdr(path)
        combo = _StubCombo([NONE, path])
        with mock.patch.object(combo, "add", wraps=combo.add) as add:
            self._refresh(src, combo)
        add.assert_not_called()
        _write_complete_hdr(os.path.join(src, "b.hdr"))
        with mock.patch.object(combo, "add", wraps=combo.add) as add:
            self._refresh(src, combo)
        add.assert_called()

    def test_the_list_holds_environment_maps_only(self):
        """Bug (2026-09-26): the lightmap baker's EXRs listed as HDRs. Shape (a
        latlong is 2:1) and name (the convention's lightmap affix) filter them,
        each a toggle in the option box."""
        from pythontk import TestSandbox

        sandbox = TestSandbox.user_config()  # the developer's affix mustn't decide
        sandbox.__enter__()
        self.addCleanup(sandbox.__exit__, None, None, None)
        src = self.tmpdir()
        _write_complete_hdr(os.path.join(src, "workshop_8k.hdr"))
        _write_exr_header(os.path.join(src, "ROOM_ENV_Lightmap_12.exr"), 256, 256)
        _write_exr_header(os.path.join(src, "crate.exr"), 512, 512)
        _write_exr_header(os.path.join(src, "desk_LightMap.LIGHT_A.exr"), 2048, 1024)

        slots, ui = self._refresh(src)
        listed = [os.path.basename(ui.cmb000.itemData(i)) for i in range(1, ui.cmb000.count())]
        self.assertEqual(listed, ["workshop_8k.hdr"])
        self.assertIn("1 HDR", ui.footer.text)
        self.assertIn("3", ui.footer.text)  # how many were held back

        combo = _StubCombo()
        combo.option_box = types.SimpleNamespace(
            menu=types.SimpleNamespace(
                chk_latlong_only=mock.Mock(isChecked=lambda: False),
                chk_hide_lightmaps=mock.Mock(isChecked=lambda: False),
            )
        )
        slots, ui = self._refresh(src, combo)
        self.assertEqual(ui.cmb000.count() - 1, 4)

        # A folder add never wires a lightmap (it took the listing's last file).
        slots, sb = _panel(_FakeManager(env="aiSkyDomeLight_"))
        slots._add_mode = lambda: "link"
        slots._add_hdrs(slots._folder_hdrs(src), where="folder", careful=False)
        self.assertEqual(
            [os.path.basename(p) for p in slots.manager.set_paths], ["workshop_8k.hdr"]
        )


class TestHdrManagerPanelMirror(_PanelCase):
    def test_the_active_map_is_selected(self):
        manager = _FakeManager(env="aiSkyDomeLight_")
        manager.hdr_file_path = "C:/proj/sourceimages/env.hdr"
        slots, sb = _panel(manager, _StubUi(_StubCombo([NONE, manager.hdr_file_path])))
        slots._select_active_in_combo()
        self.assertEqual(sb.loaded_ui.hdr_manager.cmb000.current_index, 1)

    def test_no_environment_selects_none(self):
        slots, sb = _panel(ui=_StubUi(_StubCombo([NONE, "C:/proj/sourceimages/env.hdr"])))
        slots._select_active_in_combo()
        self.assertEqual(sb.loaded_ui.hdr_manager.cmb000.current_index, 0)

    def test_an_unlisted_active_map_is_surfaced(self):
        """A Link-mode HDR outside sourceimages shows as itself, not as None."""
        manager = _FakeManager(env="aiSkyDomeLight_")
        manager.hdr_file_path = "C:/ext/linked.hdr"
        slots, sb = _panel(manager, _StubUi(_StubCombo([NONE, "C:/proj/sourceimages/x.hdr"])))
        slots._select_active_in_combo()
        self.assertEqual(sb.loaded_ui.hdr_manager.cmb000.currentData(), "C:/ext/linked.hdr")

    def test_paths_match_across_slash_styles(self):
        """Regression (2026-06-16): the combo holds os.path.join on Maya's
        forward-slash workspace (``C:/proj/sourceimages\\x.hdr``), a caller a
        normpath, so an exact findData missed the added map."""
        mixed = "C:/proj/sourceimages\\machine_shop.hdr"
        slots, sb = _panel(ui=_StubUi(_StubCombo([mixed])))
        target = os.path.normpath("C:/proj/sourceimages/machine_shop.hdr")
        self.assertTrue(slots._select_combo_path(target))
        self.assertFalse(slots._select_combo_path("C:/proj/sourceimages/missing.hdr"))


class TestHdrManagerPanelContext(_PanelCase):
    def test_select_items_go_through_the_manager(self):
        manager = _FakeManager(env="aiSkyDomeLight_", selectable=True)
        manager.parts = {"skydome": "|aiSkyDomeLight_|aiSkyDomeLightShape_"}
        slots, sb = _panel(manager)
        ui = sb.loaded_ui.hdr_manager
        slots.ctx_select_skydome()
        self.assertIn("Selected: |aiSkyDomeLight_", ui.footer.text)
        slots.ctx_select_transform()
        slots.ctx_select_file_node()
        self.assertEqual(manager.selected, ["skydome", "transform", "file_node"])
        self.assertIn("No file node", ui.footer.text)
        self.assertEqual(ui.footer.level, "warning")

    def test_reveal_falls_back_to_the_texture_folder(self):
        src = self.tmpdir()
        slots, sb = _panel(src=src)
        with mock.patch("pythontk.FileUtils.open_explorer") as open_explorer:
            slots.ctx_reveal_in_explorer()
        self.assertEqual(open_explorer.call_args.args[0], src)

        slots, sb = _panel(src="")
        slots.ctx_reveal_in_explorer()
        self.assertIn("not found", sb.loaded_ui.hdr_manager.footer.text)


class TestHdrManagerUi(unittest.TestCase):
    """The shared ``.ui``: uitk spin boxes and slider (each carries the
    option-box reset / value + toggles); the retired controls stay gone."""

    @classmethod
    def setUpClass(cls):
        root = ET.parse(UI_PATH).getroot()
        cls.classes = {w.get("name"): w.get("class") for w in root.iter("widget")}
        cls.declared = {cw.findtext("class") for cw in root.iter("customwidget")}

    def test_the_spin_boxes_are_uitk_types(self):
        for name in ("spn_intensity", "spn_exposure", "spn_diffuse", "spn_specular"):
            self.assertEqual(self.classes.get(name), "DoubleSpinBox", name)
        for name in ("spn_resolution", "spn_samples"):
            self.assertEqual(self.classes.get(name), "SpinBox", name)
        self.assertFalse(
            [n for n, c in self.classes.items() if c in ("QSpinBox", "QDoubleSpinBox")]
        )
        self.assertTrue({"DoubleSpinBox", "SpinBox", "Slider"} <= self.declared)

    def test_the_rotation_slider_replaced_the_old_controls(self):
        self.assertEqual(self.classes.get("slider000"), "Slider")
        for gone in ("chk000", "spn_tilt", "sld_preview"):
            self.assertNotIn(gone, self.classes)

    def test_every_control_the_panel_drives_is_in_the_ui(self):
        for name in ("cmb000", "slider000", "footer", *HdrManagerSlots._SPINBOX_KNOBS):
            self.assertIn(name, self.classes)


class TestComboHeaderBreaksSelection(unittest.TestCase):
    """Root-cause lock for "selecting an HDR does nothing" (2026-06-21), on the
    real uitk ComboBox: with a header, ``check_index`` snaps a pick back to -1,
    so the slot read ``currentData()`` None and the apply no-opped. Hence the
    panel's headerless dropdown."""

    @classmethod
    def setUpClass(cls):
        try:
            from qtpy import QtWidgets
        except Exception as e:  # pragma: no cover - no Qt
            raise unittest.SkipTest(f"qtpy unavailable: {e}")
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    @staticmethod
    def _combo():
        from uitk import ComboBox

        return ComboBox()

    def test_a_header_combo_loses_the_pick(self):
        cmb = self._combo()
        cmb.add([("envA", "C:/a.exr"), ("envB", "C:/b.exr")], header="HDR Map:", clear=True)
        cmb.setCurrentIndex(1)
        self.assertEqual(cmb.currentIndex(), -1)
        self.assertIsNone(cmb.currentData())

    def test_a_headerless_combo_delivers_the_pick(self):
        cmb = self._combo()
        cmb.add([("envA", "C:/a.exr"), ("envB", "C:/b.exr")], clear=True)
        cmb.restore_state = False
        seen = []
        cmb.currentIndexChanged.connect(lambda i: seen.append(cmb.currentData()))
        cmb.setCurrentIndex(1)
        self.assertEqual(cmb.currentIndex(), 1)
        self.assertEqual(seen[-1], "C:/b.exr")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestHdrManagerPanelInMaya(_PanelCase):
    def setUp(self):
        super().setUp()
        self.cmds = maya_module("maya.cmds")
        self.cmds.file(new=True, force=True)
        self.mtk = maya_module("mayatk")

    def _real(self, combo=None):
        slots, sb = _panel(ui=_StubUi(combo), tk=self.mtk)
        # The panel subscribed real scriptJobs; a stub ui is never destroyed.
        self.addCleanup(self.mtk.ScriptJobManager.instance().unsubscribe_all, slots)
        return slots, sb.loaded_ui.hdr_manager

    def _require_arnold(self):
        if not self.mtk.HdrManager.arnold_available():
            self.skipTest("Arnold (mtoa) is not available")

    def test_a_fresh_scene_reads_the_managers_defaults(self):
        slots, ui = self._real(_StubCombo([NONE]))
        slots._sync_ui_to_scene()
        ui.slider000.setSliderPosition.assert_called_once_with(0)
        ui.spn_intensity.setValue.assert_called_once_with(1.0)
        ui.spn_resolution.setValue.assert_called_once_with(1000)
        ui.spn_samples.setValue.assert_called_once_with(1)
        self.assertEqual(ui.cmb000.current_index, 0)  # None

    def test_a_pick_builds_the_skydome_from_the_controls(self):
        self._require_arnold()
        cmds = self.cmds
        slots, ui = self._real(_StubCombo([NONE, "C:/tmp/panel_sky.exr"], 1))
        slots._apply_selection()
        dome = slots.manager.hdr_env
        self.assertTrue(dome)
        self.assertAlmostEqual(cmds.getAttr(f"{dome}.intensity"), 2.0)
        self.assertEqual(cmds.getAttr(f"{dome}.resolution"), 2048)
        self.assertEqual(slots.manager.hdr_file_path, "C:/tmp/panel_sky.exr")
        self.assertEqual(ui.footer.level, "success")

        slots._on_render_visible(True)  # live, synchronous
        self.assertEqual(cmds.getAttr(f"{dome}.camera"), 1)

        cmds.select(clear=True)
        slots.ctx_select_skydome()
        self.assertEqual(cmds.ls(selection=True, long=True), cmds.ls(dome, long=True))

        ui.cmb000 = _StubCombo([NONE], 0)
        slots._apply_selection()  # None removes it
        self.assertIsNone(slots.manager.hdr_env)


if __name__ == "__main__":
    unittest.main()
