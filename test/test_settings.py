#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.settings.

Most of settings.py is reload/teardown plumbing and widget wiring. The units
worth pinning at this layer, after the marking-menu binding logic was
centralized into uitk's ``MarkingMenu``:

- _get_startmenus: delegates to the marking menu's ``start_menu_names`` SSoT.
- _on_binding_change: a route combo edit routes to ``marking_menu.set_route_target``
  (bind by gesture, not a captured key string — stays correct across an
  activation-key change).
- b023: opens the focused "global_shortcuts" editor.
- b_reset_bindings: resets marking-menu bindings to defaults.

Those four now live on ``SettingsMixin`` (``slots/_settings.py``, shared by the
Maya + Blender forks); the tests still drive them through the concrete Maya
``Settings`` class, so they also pin that the mixin extraction kept the
inherited behavior reachable. ``SettingsMixin.check_for_update`` is covered
directly at the bottom of this file — it is DCC-agnostic, so those cases need
no Maya import path.

The activation-key rewrite and repeat-last editing that used to live here now
live in uitk (``MarkingMenu.set_activation_key`` + the external-binding command
register) and are covered by uitk's test_marking_menu_shortcuts /
test_shortcut_commands.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tentacle.slots._settings import SettingsMixin

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
settings_module = maya_module("tentacle.slots.maya.settings")


class _FakeRegistry:
    def __init__(self, filenames=None):
        self.ui_registry = {"filename": filenames or []}


class _FakeMarkingMenu:
    """Stand-in for the registered marking menu (the binding SSoT).

    settings.py reads/writes bindings through the marking menu's public API
    (``start_menu_names`` / ``get_route_target`` / ``set_route_target`` /
    ``bindings``), not ``configurable`` directly, because the real store is
    host-namespaced in uitk.
    """

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
    def __init__(self, filenames=None, answer="Yes"):
        self.registry = _FakeRegistry(filenames=filenames)
        self.handlers = SimpleNamespace(marking_menu=_FakeMarkingMenu(self))
        self.editors = _FakeEditors()
        self.answer = answer  # what a modal message_box returns
        self.boxes = []  # (text, buttons) per message_box call

    def message_box(self, text, *buttons):
        self.boxes.append((text, buttons))
        return self.answer if buttons else None


def _settings_instance(sb):
    inst = settings_module.Settings.__new__(settings_module.Settings)
    inst.sb = sb
    return inst


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
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


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
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
        # Should not raise / rewrite (value already matches).
        inst._on_binding_change(("RightButton",), widget)
        self.assertEqual(
            sb.handlers.marking_menu.get_route_target(("RightButton",)),
            "main#startmenu",
        )


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestGlobalShortcutsButton(unittest.TestCase):
    """b023 launches the focused global-shortcuts editor."""

    def test_b023_opens_global_shortcuts_editor(self):
        sb = _FakeSb()
        _settings_instance(sb).b023()
        self.assertEqual(sb.editors.shown, ["global_shortcuts"])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestResetBindings(unittest.TestCase):
    """b_reset_bindings restores the marking menu's default bindings."""

    def test_reset_sets_defaults(self):
        sb = _FakeSb()
        defaults = {"Key_F12": "hud#startmenu"}
        sb.handlers.marking_menu.default_bindings = defaults
        sb.handlers.marking_menu.bindings = {"Key_F12": "main#startmenu"}
        _settings_instance(sb).b_reset_bindings()
        self.assertEqual(sb.handlers.marking_menu.bindings, defaults)


class _UpdaterHost(SettingsMixin):
    """Minimal concrete host — the mixin is DCC-agnostic, so no Maya needed.

    ``ecosystem_dists`` is PINNED rather than derived: the real one reads this
    interpreter's installed metadata (``Tcl.declared_dists``), so leaving it live would
    make every updater assertion depend on whether the test host happens to have an
    engine installed — passing in CI and inside Maya for different reasons. The
    derivation itself is covered by :class:`TestEcosystemDistsDerivation`.
    """

    #: A Maya install: base deps + Maya's engine extra + self. No ``blendertk``.
    DISTS = ("pythontk", "uitk", "mayatk", "tentacletk")

    def __init__(self, sb, dists=None):
        self.sb = sb
        self._dists = self.DISTS if dists is None else dists

    def ecosystem_dists(self, installed=None):
        self.seen_installed = installed  # the real one uses it; pin that it arrives
        return self._dists

    def _update_python_path(self):
        return "python"


class _FakePkgMgr:
    installed = {}
    latest = {}
    updated_with = None

    def __init__(self, python_path=None):
        self.python_path = python_path

    def list_packages(self):
        return dict(type(self).installed)

    def latest_versions(self, names, timeout=None):
        # Mirrors the real contract: an unreachable lookup maps to None.
        return {n: type(self).latest.get(n) for n in names}

    def update(self, names):
        type(self).updated_with = names


class TestCheckForUpdate(unittest.TestCase):
    """The updater diffs the WHOLE ecosystem, not just tentacletk.

    A fix routinely ships as a dependency patch release with no tentacletk
    bump, and pip's only-if-needed upgrade strategy leaves satisfied pins
    untouched — the old single-dist check answered "already the latest
    version" while e.g. uitk went stale (dep-blind regression, 2026-08-06).
    """

    ALL_CURRENT = {d: "1.0" for d in _UpdaterHost.DISTS}

    def _run(self, installed, latest, answer="Yes"):
        _FakePkgMgr.installed = installed
        _FakePkgMgr.latest = latest
        _FakePkgMgr.updated_with = None
        sb = _FakeSb(answer=answer)
        with patch("tentacle.slots._settings.ptk.PackageManager", _FakePkgMgr):
            _UpdaterHost(sb).check_for_update()
        return sb

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
        """A failed index lookup comes back None; comparing installed != None
        would offer a bogus "update" to a version that was never read."""
        latest = dict(self.ALL_CURRENT)
        del latest["uitk"]  # lookup failed for this one only
        self._run(dict(self.ALL_CURRENT), latest)
        self.assertIsNone(_FakePkgMgr.updated_with)

    def test_every_lookup_failing_reports_a_failure_not_all_current(self):
        """If nothing resolved, the check failed — saying "already the latest
        version" would be a confident claim built on zero information."""
        sb = self._run(dict(self.ALL_CURRENT), {})
        self.assertIsNone(_FakePkgMgr.updated_with)
        self.assertTrue(any("failed" in text for text, _b in sb.boxes))
        self.assertFalse(any("latest version" in text for text, _b in sb.boxes))

    def test_a_failure_surfaces_instead_of_raising(self):
        _FakePkgMgr.installed = dict(self.ALL_CURRENT)
        _FakePkgMgr.latest = dict(self.ALL_CURRENT)
        sb = _FakeSb()
        with patch("tentacle.slots._settings.ptk.PackageManager", _FakePkgMgr):
            with patch.object(
                _FakePkgMgr, "list_packages", side_effect=RuntimeError("no network")
            ):
                _UpdaterHost(sb).check_for_update()  # must not propagate
        self.assertTrue(any("failed" in text for text, _b in sb.boxes))

    def test_dialog_buttons_are_qt_standard_names(self):
        # MessageBox silently DROPS non-StandardButton names, leaving the
        # dialog without its affirmative action — pin that the confirm dialog
        # only ever uses real Qt names.
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
    """The updater's dist list is DERIVED per host, not hardcoded.

    The engines are extras, so a Maya install has no ``blendertk``. A hardcoded list
    naming both made the updater read the absent one as ``installed=None != latest``,
    report "blendertk not installed -> X.Y.Z", and pip-install the other DCC's engine
    into mayapy on the next update click.
    """

    def test_the_hosts_engine_is_included_and_the_others_is_not(self):
        """Drives the REAL derivation against the REAL metadata — only the detected host
        is faked. Stubbing ``declared_dists`` here would assert nothing but the stub."""
        from tentacle.tcl import Tcl

        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")

        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            maya = SettingsMixin.ecosystem_dists()
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "blender")):
            blender = SettingsMixin.ecosystem_dists()

        self.assertIn("mayatk", maya)
        self.assertNotIn("blendertk", maya)
        self.assertIn("blendertk", blender)
        self.assertNotIn("mayatk", blender)

    def test_an_already_installed_foreign_engine_keeps_being_maintained(self):
        """The upgrade path for the ENTIRE existing user base: today's release hard-pins
        both engines, so every Maya install already has a `blendertk` sitting in mayapy.
        Dropping it from the check would freeze it at its installed version forever."""
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
            dists = SettingsMixin.ecosystem_dists(installed)
        self.assertIn("blendertk", dists)
        self.assertIn("mayatk", dists)

    def test_an_absent_foreign_engine_is_never_added(self):
        """The bug this whole change fixes: a Maya install must not be told the Blender
        engine is "not installed -> X.Y.Z" and have pip fetch it into mayapy."""
        from tentacle.tcl import Tcl

        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        installed = {"pythontk": "1.0", "uitk": "1.0", "mayatk": "1.0", "tentacletk": "1.0"}
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            self.assertNotIn("blendertk", SettingsMixin.ecosystem_dists(installed))
        # ...and with no installed map at all, still never speculatively added
        with patch("tentacle.tcl.Tcl.host", classmethod(lambda cls: "maya")):
            self.assertNotIn("blendertk", SettingsMixin.ecosystem_dists())

    def test_the_updater_passes_the_installed_map_through(self):
        """If `check_for_update` stopped forwarding it, the foreign-engine rule above
        would be unreachable and every existing install would silently lose coverage."""
        seen = {}

        class _Host(_UpdaterHost):
            def ecosystem_dists(self, installed=None):
                seen["installed"] = installed
                return ("pythontk", "tentacletk")

        _FakePkgMgr.installed = {"pythontk": "1.0", "tentacletk": "1.0"}
        _FakePkgMgr.latest = {"pythontk": "1.0", "tentacletk": "1.0"}
        with patch("tentacle.slots._settings.ptk.PackageManager", _FakePkgMgr):
            _Host(_FakeSb()).check_for_update()
        self.assertEqual(seen["installed"], {"pythontk": "1.0", "tentacletk": "1.0"})

    def test_the_static_fallback_names_no_engine_at_all(self):
        """Reached when metadata is unreadable and the host is unknown — naming either
        engine there would reintroduce the bug for exactly the users who hit it."""
        self.assertNotIn("mayatk", SettingsMixin.ECOSYSTEM_DISTS)
        self.assertNotIn("blendertk", SettingsMixin.ECOSYSTEM_DISTS)
        self.assertIn("tentacletk", SettingsMixin.ECOSYSTEM_DISTS)

    def test_empty_metadata_falls_back_instead_of_checking_nothing(self):
        """A source checkout has no metadata. An empty list would make the updater
        silently check zero packages and report "could not reach the package index"."""
        with patch("tentacle.tcl.Tcl.declared_dists", return_value=()):
            self.assertEqual(
                SettingsMixin.ecosystem_dists(), SettingsMixin.ECOSYSTEM_DISTS
            )

    def test_an_unimportable_launcher_falls_back(self):
        with patch("tentacle.tcl.Tcl.declared_dists", side_effect=RuntimeError("boom")):
            self.assertEqual(
                SettingsMixin.ecosystem_dists(), SettingsMixin.ECOSYSTEM_DISTS
            )

    def test_the_updater_consumes_the_derived_list_not_the_constant(self):
        """Pins the wiring: if ``check_for_update`` reverted to reading the class
        constant, the per-host derivation would be dead code and the bug would return.

        The derived list must contain a dist the CONSTANT does not, and that dist must
        be the outdated one — otherwise the assertion passes under either wiring.
        """
        self.assertNotIn("mayatk", SettingsMixin.ECOSYSTEM_DISTS)  # fixture premise

        host = _UpdaterHost(_FakeSb(), dists=("pythontk", "mayatk", "tentacletk"))
        _FakePkgMgr.installed = {"pythontk": "1.0", "mayatk": "1.0", "tentacletk": "1.0"}
        _FakePkgMgr.latest = {"pythontk": "1.0", "mayatk": "2.0", "tentacletk": "1.0"}
        _FakePkgMgr.updated_with = None
        with patch("tentacle.slots._settings.ptk.PackageManager", _FakePkgMgr):
            host.check_for_update()
        self.assertEqual(_FakePkgMgr.updated_with, "mayatk")


if __name__ == "__main__":
    unittest.main()
