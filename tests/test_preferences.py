#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.preferences, the one Preferences Slots class.

Two halves. Tentacle's own preferences (the window themes, the presentation of
unavailable tools, the header's re-check) are uitk state: pinned here with the
REAL uitk ComboBox, whose label -> token contract only the real widget pins. The
host's preferences (working units, autosave, app style, the host's windows, the
Macro Manager) go through ``self.tk``: a fake toolkit records what each slot asks
of it, and in Maya the same class drives the real ``mtk``.

The host operations themselves (``EnvUtils.set_linear_unit``, ``frame_rates``,
``UiUtils.open_preferences`` ...) are tested in mayatk and blendertk.
"""

import os
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before any widget is built

from qtpy import QtWidgets  # noqa: E402

from _host import MAYA_AVAILABLE, maya_module  # noqa: E402
from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.preferences import PreferencesSlots  # noqa: E402

UI_DIR = Path(__file__).resolve().parent.parent / "tentacle" / "ui"
cmds = maya_module("maya.cmds")


def _can_create_widgets() -> bool:
    """False under mayapy.standalone / maya -batch: Maya's non-GUI Qt stub hard-crashes
    on QWidget construction (exit 9, no traceback) -- the offscreen QPA above does not
    help there."""
    try:
        import maya.cmds as _cmds
    except ImportError:
        return True
    try:
        return not bool(_cmds.about(batch=True))
    except Exception:
        return False


class _FakeCombo:
    """A uitk ComboBox double: ``add`` takes ``{label: data}`` and ``items`` holds the
    DATA (as the real widget's does), ``blockSignals`` answers like Qt's."""

    def __init__(self, initialized=False):
        self.is_initialized = initialized
        self.items = []
        self.labels = []
        self.current_index = None
        self.restore_state = True
        self.data = None

    def add(self, mapping, **_):
        self.labels, self.items = list(mapping), list(mapping.values())

    def setCurrentIndex(self, index):
        self.current_index = index

    def currentData(self):
        return self.data

    def blockSignals(self, block):
        return False


class _FakeSpin:
    def __init__(self):
        self.is_initialized = False
        self.value = None
        self.valueChanged = mock.MagicMock()

    def setValue(self, value):
        self.value = value


class _SlotsCase(unittest.TestCase):
    def setUp(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        self.sb = mock.MagicMock()
        self.sb.tk.EnvUtils.APP_NAME = "Maya"
        self.slots = PreferencesSlots(self.sb)
        self.env = self.sb.tk.EnvUtils
        self.ui_utils = self.sb.tk.UiUtils


class TestTheAppNamesItsPreferences(unittest.TestCase):
    """The .ui pair is shared: each host names its own preferences over ``<app>``
    (``EnvUtils.APP_NAME``) on the group and on the submenu's button."""

    def test_each_host_names_itself(self):
        migrated = Slots._legacy_repeat_last_migrated
        Slots._legacy_repeat_last_migrated = True  # no migration under test
        self.addCleanup(setattr, Slots, "_legacy_repeat_last_migrated", migrated)
        for app in ("Maya", "Blender"):
            with self.subTest(app=app):
                sb = mock.MagicMock()
                sb.tk.EnvUtils.APP_NAME = app
                PreferencesSlots(sb)
                label = f"{app} Preferences"
                sb.loaded_ui.preferences.parent_app.setTitle.assert_called_once_with(label)
                sb.loaded_ui.preferences_submenu.b010.setText.assert_called_once_with(label)


class TestWorkingUnits(_SlotsCase):
    def setUp(self):
        super().setUp()
        self.env.SCENE_UNIT_VALUES = {"millimeter": "mm", "centimeter": "cm", "meter": "m"}
        self.env.get_linear_unit.return_value = "centimeter"
        self.env.frame_rates.return_value = {"film": 24.0, "ntsc": 30.0}
        self.env.scene_settings.return_value = {"fps": 30.0}

    def test_linear_init_mirrors_the_scene_and_follows_it(self):
        combo = _FakeCombo()
        self.slots.cmb001_init(combo)
        self.assertEqual(combo.labels, ["MILLIMETER", "CENTIMETER", "METER"])
        self.assertEqual(combo.current_index, 1)
        self.assertFalse(combo.restore_state, "scene state is mirrored, never restored")
        jobs = self.sb.tk.ScriptJobManager.instance.return_value
        event, follow = jobs.subscribe.call_args.args
        self.assertEqual(event, "linearUnitChanged")
        self.env.get_linear_unit.return_value = "meter"
        follow()
        self.assertEqual(combo.current_index, 2)

    def test_an_unlisted_unit_selects_nothing(self):
        self.env.get_linear_unit.return_value = None  # Blender's Adaptive
        combo = _FakeCombo(initialized=True)
        self.slots.cmb001_init(combo)
        self.assertEqual(combo.current_index, -1)
        self.sb.tk.ScriptJobManager.instance.assert_not_called()

    def test_a_pick_sets_the_unit(self):
        combo = _FakeCombo()
        combo.data = "meter"
        self.slots.cmb001(0, combo)
        self.env.set_linear_unit.assert_called_once_with("meter")

    def test_the_frame_rate_init_mirrors_the_scene(self):
        combo = _FakeCombo()
        self.slots.cmb002_init(combo)
        self.assertEqual(combo.labels, ["24.0 fps FILM", "30.0 fps NTSC"])
        self.assertEqual(combo.current_index, 1)
        jobs = self.sb.tk.ScriptJobManager.instance.return_value
        self.assertEqual(jobs.subscribe.call_args.args[0], "timeUnitChanged")

    def test_a_pick_sets_the_rate(self):
        combo = _FakeCombo()
        combo.data = "film"
        self.slots.cmb002(0, combo)
        self.env.apply_scene_settings.assert_called_once_with({"fps": 24.0})


class TestAutosave(_SlotsCase):
    def test_the_widgets_read_then_write_the_host(self):
        self.env.autosave_settings.return_value = {"max_backups": 4, "interval": 7.5}
        backups, interval = _FakeSpin(), _FakeSpin()
        self.slots.s000_init(backups)
        self.slots.s001_init(interval)
        self.assertEqual((backups.value, interval.value), (4, 8))
        backups.valueChanged.connect.call_args.args[0](0)
        self.env.set_autosave_settings.assert_called_with(max_backups=0)
        interval.valueChanged.connect.call_args.args[0](3)
        self.env.set_autosave_settings.assert_called_with(interval=3)


class TestHostWindowsAndStyle(_SlotsCase):
    def test_each_button_opens_its_section(self):
        for button, section in (
            ("b001", "colors"),
            ("b008", "hotkeys"),
            ("b009", "plugins"),
            ("b010", "general"),
        ):
            with self.subTest(button=button):
                getattr(self.slots, button)()
                self.ui_utils.open_preferences.assert_called_with(section)

    def test_a_refusal_says_why(self):
        self.ui_utils.open_preferences.side_effect = RuntimeError("no window")
        self.slots.b008()
        (message,), _ = self.sb.message_box.call_args
        self.assertIn("no window", message)

    def test_the_macro_manager_is_the_hosts(self):
        self.slots.b011()
        self.sb.tk.Macros.show_editor.assert_called_once_with(
            parent=self.sb.handlers.marking_menu
        )

    def test_the_style_list_selects_nothing_and_a_pick_applies(self):
        """The host keeps no "current" style; a restored index would re-apply a
        stale pick on panel open."""
        self.sb.tk.StyleSetter.list_templates.return_value = {"Blender": "tok"}
        combo = _FakeCombo()
        self.slots.cmb003_init(combo)
        self.assertEqual((combo.items, combo.current_index), (["tok"], -1))
        self.assertFalse(combo.restore_state)
        combo.data = "tok"
        self.slots.cmb003(0, combo)
        self.sb.tk.StyleSetter.apply_template.assert_called_once_with("tok")


class _StubMarkingMenu:
    """The two hosted-theme properties the theme combos drive."""

    def __init__(self):
        self.menu_theme = "dark"
        self.window_theme = "dark"


def _slots_over(sb):
    """A PreferencesSlots without ``__init__`` (no loaded .ui): the uitk half only."""
    slots = PreferencesSlots.__new__(PreferencesSlots)
    slots.sb = sb
    return slots


@unittest.skipUnless(
    _can_create_widgets(),
    "Maya's non-GUI Qt stub hard-crashes on QWidget construction",
)
class TestThemeCombos(unittest.TestCase):
    """cmb004 / cmb005 expose uitk's two window themes. Host-free: only
    ``sb.handlers.marking_menu`` and ``sb.style`` (the switchboard's proxy for
    ``uitk.StyleSheet``) are touched."""

    @classmethod
    def setUpClass(cls):
        try:
            from uitk.widgets.comboBox import ComboBox  # noqa: F401
        except ImportError as error:
            raise unittest.SkipTest(f"uitk unavailable: {error}")
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from uitk.themes.style_sheet import StyleSheet

        self.menu = _StubMarkingMenu()
        self.slots = _slots_over(
            types.SimpleNamespace(
                handlers=types.SimpleNamespace(marking_menu=self.menu),
                style=StyleSheet,
            )
        )

    def _combo(self):
        from uitk.widgets.comboBox import ComboBox

        widget = ComboBox()
        widget.is_initialized = False
        return widget

    def test_labels_are_titled_tokens(self):
        self.assertEqual(self.slots._theme_items().get("High Contrast"), "high-contrast")

    def test_items_cover_every_registered_theme(self):
        from uitk.themes.style_sheet import StyleSheet

        self.assertEqual(sorted(self.slots._theme_items().values()), sorted(StyleSheet.themes))

    def test_each_init_selects_the_live_theme(self):
        self.menu.menu_theme = "high-contrast"
        self.menu.window_theme = "light"
        menu, window = self._combo(), self._combo()
        self.slots.cmb004_init(menu)
        self.slots.cmb005_init(window)
        self.assertEqual((menu.currentData(), window.currentData()), ("high-contrast", "light"))

    def test_each_combo_writes_its_own_theme(self):
        widget = self._combo()
        self.slots.cmb004_init(widget)
        widget.setCurrentText("Light")
        self.slots.cmb004(widget.currentIndex(), widget)
        self.assertEqual((self.menu.menu_theme, self.menu.window_theme), ("light", "dark"))
        widget = self._combo()
        self.slots.cmb005_init(widget)
        widget.setCurrentText("High Contrast")
        self.slots.cmb005(widget.currentIndex(), widget)
        self.assertEqual(self.menu.window_theme, "high-contrast")

    def test_the_header_row_writes_nothing(self):
        widget = self._combo()
        self.slots.cmb004_init(widget)
        widget.setCurrentIndex(-1)
        self.assertIsNone(widget.currentData())
        self.slots.cmb004(widget.currentIndex(), widget)  # must not raise
        self.assertEqual(self.menu.menu_theme, "dark")

    def test_init_repopulates_only_once(self):
        widget = self._combo()
        self.slots.cmb004_init(widget)
        count = widget.count()
        widget.is_initialized = True
        self.menu.menu_theme = "light"
        self.slots.cmb004_init(widget)
        self.assertEqual(widget.count(), count)
        self.assertEqual(widget.currentData(), "light")


@unittest.skipUnless(
    _can_create_widgets(),
    "Maya's non-GUI Qt stub hard-crashes on QWidget construction",
)
class TestUnavailableToolsPolicy(unittest.TestCase):
    """``cmb006`` + the header re-check: the tentacle glue over uitk's gate system."""

    @classmethod
    def setUpClass(cls):
        try:
            from uitk.widgets.comboBox import ComboBox  # noqa: F401
        except ImportError as error:
            raise unittest.SkipTest(f"uitk unavailable: {error}")
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.rechecks = []
        self.slots = _slots_over(
            types.SimpleNamespace(
                UNMET_POLICIES=("hide", "disable", "show"),
                unmet_policy="hide",
                recheck_gates=lambda: self.rechecks.append("gates"),
                registered_widgets=types.SimpleNamespace(PushButton="PushButton"),
                message_box=lambda *a, **k: self.rechecks.append("message"),
            )
        )

    def _combo(self):
        from uitk.widgets.comboBox import ComboBox

        widget = ComboBox()
        widget.is_initialized = False
        return widget

    def test_labels_override_only_where_title_is_wrong(self):
        self.assertEqual(self.slots._unmet_label("disable"), "Show disabled")
        self.assertEqual(self.slots._unmet_label("hide"), "Hide")

    def test_the_entries_come_from_the_switchboard_not_a_local_table(self):
        self.slots.sb.UNMET_POLICIES = ("hide", "disable", "show", "warn")
        widget = self._combo()
        self.slots.cmb006_init(widget)
        self.assertEqual(
            [widget.itemData(i) for i in range(widget.count()) if widget.itemData(i)],
            ["hide", "disable", "show", "warn"],
        )

    def test_a_selection_is_persisted_and_applied_immediately(self):
        widget = self._combo()
        self.slots.cmb006_init(widget)
        widget.setCurrentText("Show disabled")
        self.slots.cmb006(widget.currentIndex(), widget)
        self.assertEqual(self.slots.sb.unmet_policy, "disable")
        self.assertEqual(self.rechecks, ["gates"])

    def test_the_header_row_writes_nothing(self):
        widget = self._combo()
        self.slots.cmb006_init(widget)
        widget.setCurrentIndex(-1)
        self.slots.cmb006(widget.currentIndex(), widget)
        self.assertEqual(self.slots.sb.unmet_policy, "hide")
        self.assertEqual(self.rechecks, [])

    def test_the_header_offers_the_re_check_and_it_reports(self):
        header = types.SimpleNamespace(
            is_initialized=False,
            menu=types.SimpleNamespace(hide_on_trigger=False, add=mock.Mock()),
        )
        self.slots.header_init(header)
        self.assertEqual(header.menu.add.call_args.kwargs["setObjectName"], "tb000")
        self.assertTrue(header.menu.hide_on_trigger)
        self.slots.recheck_app_gates = lambda: 3
        self.slots.tb000()
        self.assertEqual(self.rechecks, ["message"])


@unittest.skipUnless(
    _can_create_widgets(),
    "Needs real-widget Qt (skipped under mayapy.standalone's non-GUI stub).",
)
class TestAppLabelTargetsResolve(unittest.TestCase):
    """The widgets ``__init__`` names resolve from the real .ui BEFORE any show:
    ``register_children`` binds children on ``showEvent``, so these lookups land
    on the ``__getattr__`` findChild fallback, as the real ``__init__``'s do. A
    renamed ``parent_app`` or ``b010`` would take the whole panel down."""

    @classmethod
    def setUpClass(cls):
        try:
            from uitk import Switchboard
        except ImportError as error:
            raise unittest.SkipTest(f"uitk unavailable: {error}")
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.sb = Switchboard(ui_source=str(UI_DIR))

    def test_the_labels_reach_the_widgets_unshown(self):
        ui = self.sb.loaded_ui.preferences
        submenu = self.sb.loaded_ui.preferences_submenu
        self.assertFalse(ui.isVisible(), "must exercise the pre-show path")
        ui.parent_app.setTitle("Maya Preferences")
        submenu.b010.setText("Maya Preferences")
        self.assertEqual(ui.parent_app.title(), "Maya Preferences")
        self.assertEqual(submenu.b010.text(), "Maya Preferences")

    def test_the_in_panel_button_keeps_its_own_label(self):
        """Only the group is app-named in the panel, so it never reads
        'Maya Preferences > Maya Preferences'."""
        self.assertEqual(self.sb.loaded_ui.preferences.b010.text(), "Preferences")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestPreferencesInMaya(_SlotsCase):
    """The same class over the real ``mtk``."""

    def setUp(self):
        super().setUp()
        cmds.file(new=True, force=True)
        self.sb.tk = maya_module("mayatk")
        self._unit = cmds.currentUnit(query=True, linear=True)
        self._time = cmds.currentUnit(query=True, time=True)

    def tearDown(self):
        cmds.currentUnit(linear=self._unit, time=self._time)
        cmds.file(new=True, force=True)

    def test_a_linear_pick_sets_mayas_unit(self):
        combo = _FakeCombo()
        combo.data = "meter"
        self.slots.cmb001(0, combo)
        self.assertEqual(cmds.currentUnit(query=True, fullName=True, linear=True), "meter")

    def test_a_rate_pick_sets_mayas_time_unit(self):
        combo = _FakeCombo()
        combo.data = "ntsc"
        self.slots.cmb002(0, combo)
        self.assertEqual(cmds.currentUnit(query=True, time=True), "ntsc")

    def test_the_inits_seed_mayas_state(self):
        cmds.currentUnit(linear="centimeter", time="film")
        linear, rate = _FakeCombo(initialized=True), _FakeCombo(initialized=True)
        self.slots.cmb001_init(linear)
        self.slots.cmb002_init(rate)
        self.assertEqual(linear.items[linear.current_index], "centimeter")
        self.assertEqual(rate.items[rate.current_index], "film")


if __name__ == "__main__":
    unittest.main()
