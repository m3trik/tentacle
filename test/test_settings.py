#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.settings, the one Settings Slots class.

Host-free but for two calls: the updater's interpreter
(``self.tk.EnvUtils.python_executable``) and Reload Scripts (the launcher's
``Tcl.reload``, tested in ``test_tcl_launcher.py``). What's worth pinning here:

- _get_startmenus: delegates to the marking menu's ``start_menu_names`` SSoT.
- _on_binding_change: a route combo edit routes to ``marking_menu.set_route_target``
  (bind by gesture, not a captured key string -- correct across a key change).
- b023: opens the focused "global_shortcuts" editor.
- b_reset_bindings: resets marking-menu bindings to defaults.
- tb001: Reload Scripts goes through the launcher and reports its failure.
- check_for_update: the whole ecosystem, through the host's interpreter.

The activation-key rewrite and repeat-last editing live in uitk
(``MarkingMenu.set_activation_key``), covered by its own tests.
"""
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from _host import MAYA_AVAILABLE, maya_module
from tentacle.slots.settings import SettingsSlots


class _FakeRegistry:
    def __init__(self, filenames=None):
        self.ui_registry = {"filename": filenames or []}


class _FakeMarkingMenu:
    """Stand-in for the registered marking menu (the binding SSoT): the slot reads
    and writes bindings through its public API, not ``configurable``, because the
    real store is host-namespaced in uitk."""

    def __init__(self, sb, default_bindings=None):
        self._sb = sb
        self.default_bindings = default_bindings or {}
        self._routes = {}
        self.bindings = {}

    def start_menu_names(self, short=True):
        filenames = self._sb.registry.ui_registry.get("filename") or []
        names = sorted(f for f in filenames if "#startmenu" in f)
        return [n.replace("#startmenu", "") for n in names] if short else names

    def get_route_target(self, buttons=()):
        return self._routes.get(tuple(buttons), "")

    def set_route_target(self, buttons, menu):
        self._routes[tuple(buttons)] = menu

    def on_bindings_changed(self, callback):
        pass  # combo-sync wiring is not under test here


class _FakeEditors:
    def __init__(self):
        self.shown = []

    def show(self, name):
        self.shown.append(name)


class _FakeSb:
    def __init__(self, filenames=None, answer="Yes", python="python"):
        self.registry = _FakeRegistry(filenames=filenames)
        self.handlers = SimpleNamespace(marking_menu=_FakeMarkingMenu(self))
        self.editors = _FakeEditors()
        self.answer = answer  # what a modal message_box returns
        self.boxes = []  # (text, buttons) per message_box call
        self.logger = logging.getLogger("test_settings")  # a failure is logged too
        self.tk = SimpleNamespace(
            EnvUtils=SimpleNamespace(python_executable=lambda: python)
        )

    def message_box(self, text, *buttons):
        self.boxes.append((text, buttons))
        return self.answer if buttons else None


def _settings_instance(sb):
    inst = SettingsSlots.__new__(SettingsSlots)
    inst.sb = sb
    return inst


class TestGetStartmenus(unittest.TestCase):
    """_get_startmenus delegates to the marking menu's start_menu_names."""

    def test_filters_only_startmenu_ui_files(self):
        inst = _settings_instance(
            _FakeSb(
                filenames=[
                    "main#startmenu",
                    "hud#startmenu",
                    "hud#submenu",
                    "animation#startmenu",
                    "polygons",
                    "uv",
                ]
            )
        )
        self.assertEqual(
            inst._get_startmenus(),
            ["animation#startmenu", "hud#startmenu", "main#startmenu"],
        )

    def test_empty_registry_returns_empty_list(self):
        self.assertEqual(_settings_instance(_FakeSb(filenames=[]))._get_startmenus(), [])


class TestRouteCombos(unittest.TestCase):
    """A route combo edit persists via the marking menu's gesture-keyed API."""

    def test_on_binding_change_routes_to_set_route_target(self):
        sb = _FakeSb()
        inst = _settings_instance(sb)
        widget = SimpleNamespace(currentData=lambda: "cameras#startmenu")
        inst._on_binding_change(("LeftButton",), widget)
        self.assertEqual(
            sb.handlers.marking_menu.get_route_target(("LeftButton",)),
            "cameras#startmenu",
        )

    def test_on_binding_change_noop_when_unchanged(self):
        sb = _FakeSb()
        sb.handlers.marking_menu.set_route_target(("RightButton",), "main#startmenu")
        inst = _settings_instance(sb)
        widget = SimpleNamespace(currentData=lambda: "main#startmenu")
        inst._on_binding_change(("RightButton",), widget)
        self.assertEqual(
            sb.handlers.marking_menu.get_route_target(("RightButton",)),
            "main#startmenu",
        )


class TestEditorsAndBindings(unittest.TestCase):
    def test_b023_opens_global_shortcuts_editor(self):
        sb = _FakeSb()
        _settings_instance(sb).b023()
        self.assertEqual(sb.editors.shown, ["global_shortcuts"])

    def test_reset_sets_defaults(self):
        sb = _FakeSb()
        defaults = {"Key_F12": "hud#startmenu"}
        sb.handlers.marking_menu.default_bindings = defaults
        sb.handlers.marking_menu.bindings = {"Key_F12": "main#startmenu"}
        _settings_instance(sb).b_reset_bindings()
        self.assertEqual(sb.handlers.marking_menu.bindings, defaults)


class TestReloadScripts(unittest.TestCase):
    """tb001 is the launcher's reload; only a failure that reaches the slot is the
    panel's to report (Maya reports through Maya, its reload never raises)."""

    def test_reload_goes_through_the_launcher(self):
        sb = _FakeSb()
        with patch("tentacle.tcl.Tcl.reload", return_value=3) as reload:
            _settings_instance(sb).tb001()
        reload.assert_called_once_with()
        self.assertEqual(sb.boxes, [])

    def test_a_failed_reload_is_reported_escaped(self):
        sb = _FakeSb()
        with patch("tentacle.tcl.Tcl.reload", side_effect=RuntimeError("<boom>")):
            _settings_instance(sb).tb001()
        (text, _buttons), = sb.boxes
        self.assertIn("Reload failed", text)
        self.assertIn("&lt;boom&gt;", text)


class _UpdaterHost(SettingsSlots):
    """The slot class with ``ecosystem_dists`` PINNED: the real one reads this
    interpreter's installed metadata (``Tcl.declared_dists``), so leaving it live
    would make every updater assertion depend on what the test host has installed.
    The derivation itself is covered by :class:`TestEcosystemDistsDerivation`.
    """

    #: A Maya install: base deps + Maya's engine extra + self. No ``blendertk``.
    DISTS = ("pythontk", "uitk", "mayatk", "tentacletk")

    def __init__(self, sb, dists=None):  # no QObject / loaded .ui needed here
        self.sb = sb
        self._dists = self.DISTS if dists is None else dists

    def ecosystem_dists(self, installed=None):
        self.seen_installed = installed  # the real one uses it; pin that it arrives
        return self._dists


class _FakePkgMgr:
    installed = {}
    latest = {}
    updated_with = None
    python_path = None

    def __init__(self, python_path=None):
        type(self).python_path = python_path

    def list_packages(self):
        return dict(type(self).installed)

    def latest_versions(self, names, timeout=None):
        # Mirrors the real contract: an unreachable lookup maps to None.
        return {n: type(self).latest.get(n) for n in names}

    def update(self, names):
        type(self).updated_with = names


class TestCheckForUpdate(unittest.TestCase):
    """The updater diffs the WHOLE ecosystem, not just tentacletk: a fix routinely
    ships as a dependency patch with no tentacletk bump, and pip's only-if-needed
    strategy leaves satisfied pins untouched (dep-blind regression, 2026-08-06).
    """

    ALL_CURRENT = {d: "1.0" for d in _UpdaterHost.DISTS}

    def _run(self, installed, latest, answer="Yes"):
        _FakePkgMgr.installed = installed
        _FakePkgMgr.latest = latest
        _FakePkgMgr.updated_with = None
        sb = _FakeSb(answer=answer, python="C:/maya/bin/mayapy.exe")
        with patch("tentacle.slots.settings.ptk.PackageManager", _FakePkgMgr):
            _UpdaterHost(sb).check_for_update()
        return sb

    def test_pip_runs_through_the_hosts_interpreter(self):
        self._run(dict(self.ALL_CURRENT), dict(self.ALL_CURRENT))
        self.assertEqual(_FakePkgMgr.python_path, "C:/maya/bin/mayapy.exe")

    def test_stale_dependency_is_detected_without_a_tentacletk_bump(self):
        latest = dict(self.ALL_CURRENT)
        latest["uitk"] = "1.1"  # dep patch release; tentacletk unchanged
        sb = self._run(dict(self.ALL_CURRENT), latest)
        self.assertEqual(_FakePkgMgr.updated_with, "uitk")
        self.assertTrue(any("uitk" in text for text, _b in sb.boxes))

    def test_all_current_reports_latest_and_updates_nothing(self):
        sb = self._run(dict(self.ALL_CURRENT), dict(self.ALL_CURRENT))
        self.assertIsNone(_FakePkgMgr.updated_with)
        self.assertTrue(any("latest" in text for text, _b in sb.boxes))

    def test_declining_the_dialog_updates_nothing(self):
        latest = dict(self.ALL_CURRENT)
        latest["mayatk"] = "2.0"
        self._run(dict(self.ALL_CURRENT), latest, answer="No")
        self.assertIsNone(_FakePkgMgr.updated_with)

    def test_multiple_outdated_upgrade_in_one_pip_run(self):
        latest = dict(self.ALL_CURRENT)
        latest["pythontk"] = "2.0"
        latest["tentacletk"] = "2.0"
        self._run(dict(self.ALL_CURRENT), latest)
        self.assertEqual(_FakePkgMgr.updated_with, "pythontk tentacletk")

    def test_missing_dist_is_offered_for_install(self):
        installed = dict(self.ALL_CURRENT)
        del installed["mayatk"]
        self._run(installed, dict(self.ALL_CURRENT))
        self.assertEqual(_FakePkgMgr.updated_with, "mayatk")

    def test_an_unreachable_lookup_is_not_reported_as_outdated(self):
        latest = dict(self.ALL_CURRENT)
        del latest["uitk"]  # lookup failed for this one only
        self._run(dict(self.ALL_CURRENT), latest)
        self.assertIsNone(_FakePkgMgr.updated_with)

    def test_every_lookup_failing_reports_a_failure_not_all_current(self):
        sb = self._run(dict(self.ALL_CURRENT), {})
        self.assertIsNone(_FakePkgMgr.updated_with)
        self.assertTrue(any("failed" in text for text, _b in sb.boxes))
        self.assertFalse(any("latest version" in text for text, _b in sb.boxes))

    def test_a_failure_surfaces_instead_of_raising(self):
        _FakePkgMgr.installed = dict(self.ALL_CURRENT)
        _FakePkgMgr.latest = dict(self.ALL_CURRENT)
        sb = _FakeSb()
        with patch("tentacle.slots.settings.ptk.PackageManager", _FakePkgMgr):
            with patch.object(
                _FakePkgMgr, "list_packages", side_effect=RuntimeError("no network")
            ):
                _UpdaterHost(sb).check_for_update()  # must not propagate
        self.assertTrue(any("failed" in text for text, _b in sb.boxes))

    def test_dialog_buttons_are_qt_standard_names(self):
        # MessageBox silently DROPS non-StandardButton names, leaving the dialog
        # without its affirmative action.
        qt_names = {
            "Ok", "Open", "Save", "Cancel", "Close", "Discard", "Apply",
            "Reset", "RestoreDefaults", "Help", "SaveAll", "Yes", "YesToAll",
            "No", "NoToAll", "Abort", "Retry", "Ignore",
        }
        latest = dict(self.ALL_CURRENT)
        latest["uitk"] = "9.9"
        sb = self._run(dict(self.ALL_CURRENT), latest)
        confirm_buttons = next(b for _t, b in sb.boxes if b)
        self.assertTrue(set(confirm_buttons) <= qt_names, confirm_buttons)


class TestEcosystemDistsDerivation(unittest.TestCase):
    """The updater's dist list is DERIVED per host, not hardcoded: the engines are
    extras, so a Maya install has no ``blendertk``, and a hardcoded list naming
    both made the updater pip-install the other DCC's engine into mayapy."""

    def test_the_hosts_engine_is_included_and_the_others_is_not(self):
        from tentacle.tcl import Tcl

        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")

        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            maya = SettingsSlots.ecosystem_dists()
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "blender")):
            blender = SettingsSlots.ecosystem_dists()

        self.assertIn("mayatk", maya)
        self.assertNotIn("blendertk", maya)
        self.assertIn("blendertk", blender)
        self.assertNotIn("mayatk", blender)

    def test_an_already_installed_foreign_engine_keeps_being_maintained(self):
        from tentacle.tcl import Tcl

        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        installed = {
            "pythontk": "1.0",
            "uitk": "1.0",
            "mayatk": "1.0",
            "blendertk": "1.0",
            "tentacletk": "1.0",
        }
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            dists = SettingsSlots.ecosystem_dists(installed)
        self.assertIn("blendertk", dists)
        self.assertIn("mayatk", dists)

    def test_an_absent_foreign_engine_is_never_added(self):
        from tentacle.tcl import Tcl

        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        installed = {"pythontk": "1.0", "uitk": "1.0", "mayatk": "1.0", "tentacletk": "1.0"}
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            self.assertNotIn("blendertk", SettingsSlots.ecosystem_dists(installed))
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            self.assertNotIn("blendertk", SettingsSlots.ecosystem_dists())

    def test_the_updater_passes_the_installed_map_through(self):
        seen = {}

        class _Host(_UpdaterHost):
            def ecosystem_dists(self, installed=None):
                seen["installed"] = installed
                return ("pythontk", "tentacletk")

        _FakePkgMgr.installed = {"pythontk": "1.0", "tentacletk": "1.0"}
        _FakePkgMgr.latest = {"pythontk": "1.0", "tentacletk": "1.0"}
        with patch("tentacle.slots.settings.ptk.PackageManager", _FakePkgMgr):
            _Host(_FakeSb()).check_for_update()
        self.assertEqual(seen["installed"], {"pythontk": "1.0", "tentacletk": "1.0"})

    def test_the_static_fallback_names_no_engine_at_all(self):
        self.assertNotIn("mayatk", SettingsSlots.ECOSYSTEM_DISTS)
        self.assertNotIn("blendertk", SettingsSlots.ECOSYSTEM_DISTS)
        self.assertIn("tentacletk", SettingsSlots.ECOSYSTEM_DISTS)

    def test_empty_metadata_falls_back_instead_of_checking_nothing(self):
        with patch("tentacle.tcl.Tcl.declared_dists", return_value=()):
            self.assertEqual(
                SettingsSlots.ecosystem_dists(), SettingsSlots.ECOSYSTEM_DISTS
            )

    def test_an_unimportable_launcher_falls_back(self):
        with patch("tentacle.tcl.Tcl.declared_dists", side_effect=RuntimeError("boom")):
            self.assertEqual(
                SettingsSlots.ecosystem_dists(), SettingsSlots.ECOSYSTEM_DISTS
            )

    def test_the_updater_consumes_the_derived_list_not_the_constant(self):
        """If ``check_for_update`` reverted to reading the class constant, the
        per-host derivation would be dead code: the derived list must hold a dist
        the CONSTANT does not, and that dist must be the outdated one."""
        self.assertNotIn("mayatk", SettingsSlots.ECOSYSTEM_DISTS)  # fixture premise

        host = _UpdaterHost(_FakeSb(), dists=("pythontk", "mayatk", "tentacletk"))
        _FakePkgMgr.installed = {"pythontk": "1.0", "mayatk": "1.0", "tentacletk": "1.0"}
        _FakePkgMgr.latest = {"pythontk": "1.0", "mayatk": "2.0", "tentacletk": "1.0"}
        _FakePkgMgr.updated_with = None
        with patch("tentacle.slots.settings.ptk.PackageManager", _FakePkgMgr):
            host.check_for_update()
        self.assertEqual(_FakePkgMgr.updated_with, "mayatk")


@unittest.skipUnless(MAYA_AVAILABLE, "drives the real mtk; runs in a fresh Maya")
class TestUpdaterInMaya(unittest.TestCase):
    """Over the real ``mtk``, pip runs through this Maya's mayapy."""

    def test_the_interpreter_is_mayapy(self):
        mtk = maya_module("mayatk")
        sb = _FakeSb()
        sb.tk = mtk
        _FakePkgMgr.installed = {d: "1.0" for d in _UpdaterHost.DISTS}
        _FakePkgMgr.latest = dict(_FakePkgMgr.installed)
        with patch("tentacle.slots.settings.ptk.PackageManager", _FakePkgMgr):
            _UpdaterHost(sb).check_for_update()
        self.assertEqual(_FakePkgMgr.python_path, mtk.EnvUtils.get_env_info("mayapy"))


if __name__ == "__main__":
    unittest.main()
