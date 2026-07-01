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

The activation-key rewrite and repeat-last editing that used to live here now
live in uitk (``MarkingMenu.set_activation_key`` + the external-binding command
register) and are covered by uitk's test_marking_menu_shortcuts /
test_shortcut_commands.
"""
import unittest
from types import SimpleNamespace

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import settings as settings_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    settings_module = None
    _MAYA_AVAILABLE = False


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
    def __init__(self, filenames=None):
        self.registry = _FakeRegistry(filenames=filenames)
        self.handlers = SimpleNamespace(marking_menu=_FakeMarkingMenu(self))
        self.editors = _FakeEditors()


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


if __name__ == "__main__":
    unittest.main()
