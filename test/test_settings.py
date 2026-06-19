#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.settings.

Most of settings.py is reload/teardown plumbing and widget wiring. The
units worth pinning at this layer:

- _get_startmenus: filters registry filenames for ``#startmenu`` suffix.
- _get_activation_key: parses Key_X prefix out of binding strings.
- _on_activation_key_change: rewrites every binding key when the user
  changes the activation key — the compound parts split logic is fragile
  and the bug would silently disable every marking menu binding.
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


class _ConfigurableValue:
    """Stand-in for a configurable value with get/set."""

    def __init__(self, value=None):
        self._v = value if value is not None else {}

    def get(self, default=None):
        return self._v if self._v else default

    def set(self, value):
        self._v = value


class _FakeRegistry:
    def __init__(self, filenames=None):
        self.ui_registry = {"filename": filenames or []}


class _FakeConfigurable:
    def __init__(self, bindings=None):
        self.marking_menu_bindings = _ConfigurableValue(bindings or {})


class _FakeMarkingMenu:
    """Stand-in for the registered marking menu (the binding SSoT).

    settings.py reads/writes bindings through ``marking_menu.bindings`` /
    ``on_bindings_changed`` (not ``configurable`` directly) because the real
    store is host-namespaced in uitk. ``bindings`` here delegates to the fake
    ``configurable`` store the tests inspect, so the indirection is transparent.
    """

    def __init__(self, sb, default_bindings=None):
        self._sb = sb
        self.default_bindings = default_bindings or {}

    @property
    def bindings(self):
        return self._sb.configurable.marking_menu_bindings.get({})

    @bindings.setter
    def bindings(self, value):
        self._sb.configurable.marking_menu_bindings.set(value)

    def on_bindings_changed(self, callback):
        pass  # combo-sync wiring is not under test here


class _FakeSb:
    def __init__(self, filenames=None, bindings=None):
        self.registry = _FakeRegistry(filenames=filenames)
        self.configurable = _FakeConfigurable(bindings=bindings)
        self.handlers = SimpleNamespace(marking_menu=_FakeMarkingMenu(self))


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestGetStartmenus(unittest.TestCase):
    """_get_startmenus filters registry filenames for ``#startmenu`` suffix."""

    def setUp(self):
        self.instance = settings_module.Settings.__new__(settings_module.Settings)

    def test_filters_only_startmenu_ui_files(self):
        self.instance.sb = _FakeSb(
            filenames=[
                "main#startmenu",
                "hud#startmenu",
                "hud#submenu",
                "animation#startmenu",
                "polygons",
                "uv",
            ]
        )
        result = self.instance._get_startmenus()
        self.assertEqual(
            result, ["animation#startmenu", "hud#startmenu", "main#startmenu"]
        )

    def test_empty_registry_returns_empty_list(self):
        self.instance.sb = _FakeSb(filenames=[])
        self.assertEqual(self.instance._get_startmenus(), [])

    def test_no_matching_returns_empty_list(self):
        self.instance.sb = _FakeSb(filenames=["polygons", "uv", "mesh"])
        self.assertEqual(self.instance._get_startmenus(), [])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestGetActivationKey(unittest.TestCase):
    """_get_activation_key scans binding keys for a Key_X prefix."""

    def setUp(self):
        self.instance = settings_module.Settings.__new__(settings_module.Settings)

    def test_empty_bindings_returns_default_f12(self):
        self.instance.sb = _FakeSb(bindings={})
        self.assertEqual(self.instance._get_activation_key(), "Key_F12")

    def test_finds_key_f12_from_compound_binding(self):
        self.instance.sb = _FakeSb(
            bindings={"Key_F12|LeftButton": "hud#startmenu"}
        )
        self.assertEqual(self.instance._get_activation_key(), "Key_F12")

    def test_finds_alternative_key_when_user_rebinds(self):
        """If the user binds to F11, _get_activation_key reports that."""
        self.instance.sb = _FakeSb(
            bindings={"Key_F11|RightButton": "polygons#startmenu"}
        )
        self.assertEqual(self.instance._get_activation_key(), "Key_F11")

    def test_returns_default_when_no_key_part(self):
        """A binding without Key_X prefix falls through to default."""
        self.instance.sb = _FakeSb(bindings={"LeftButton": "main"})
        self.assertEqual(self.instance._get_activation_key(), "Key_F12")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestOnActivationKeyChange(unittest.TestCase):
    """_on_activation_key_change rewrites the Key_X prefix across all bindings."""

    def setUp(self):
        self.instance = settings_module.Settings.__new__(settings_module.Settings)

    def _widget(self, key_str):
        return SimpleNamespace(
            keySequence=lambda: SimpleNamespace(toString=lambda: key_str)
        )

    def test_renames_key_prefix_in_all_bindings(self):
        """Changing F12 → F11 should rewrite every binding that uses Key_F12."""
        sb = _FakeSb(
            bindings={
                "Key_F12": "main#startmenu",
                "Key_F12|LeftButton": "hud#startmenu",
                "Key_F12|RightButton": "polygons#startmenu",
            }
        )
        self.instance.sb = sb

        self.instance._on_activation_key_change(self._widget("F11"))

        new = sb.configurable.marking_menu_bindings.get({})
        self.assertEqual(
            new,
            {
                "Key_F11": "main#startmenu",
                "Key_F11|LeftButton": "hud#startmenu",
                "Key_F11|RightButton": "polygons#startmenu",
            },
        )

    def test_empty_keysequence_is_noop(self):
        """An empty keySequence text returns early — bindings unchanged."""
        sb = _FakeSb(bindings={"Key_F12": "main#startmenu"})
        self.instance.sb = sb
        self.instance._on_activation_key_change(self._widget(""))
        self.assertEqual(
            sb.configurable.marking_menu_bindings.get({}),
            {"Key_F12": "main#startmenu"},
        )

    def test_same_key_is_noop(self):
        """Re-setting to the current key should NOT rewrite bindings."""
        sb = _FakeSb(bindings={"Key_F12": "main#startmenu"})
        self.instance.sb = sb
        # Track set() calls.
        original_set = sb.configurable.marking_menu_bindings.set
        set_calls = []
        sb.configurable.marking_menu_bindings.set = lambda v: set_calls.append(v)
        try:
            self.instance._on_activation_key_change(self._widget("F12"))
        finally:
            sb.configurable.marking_menu_bindings.set = original_set
        self.assertEqual(set_calls, [])

    def test_does_not_overwrite_non_key_parts(self):
        """Modifier parts (LeftButton, MiddleButton, …) stay intact."""
        sb = _FakeSb(
            bindings={"Key_F12|LeftButton|RightButton": "hud#startmenu"}
        )
        self.instance.sb = sb
        self.instance._on_activation_key_change(self._widget("A"))
        new = sb.configurable.marking_menu_bindings.get({})
        self.assertEqual(
            new, {"Key_A|LeftButton|RightButton": "hud#startmenu"}
        )

    def test_no_keysequence_method_returns_early(self):
        """A widget without keySequence() shouldn't crash."""
        sb = _FakeSb(bindings={"Key_F12": "main"})
        self.instance.sb = sb

        # Widget where keySequence().toString() raises AttributeError
        class _BrokenWidget:
            def keySequence(self):
                raise AttributeError("no keySequence")

        self.instance._on_activation_key_change(_BrokenWidget())
        # Bindings unchanged.
        self.assertEqual(
            sb.configurable.marking_menu_bindings.get({}),
            {"Key_F12": "main"},
        )


if __name__ == "__main__":
    unittest.main()
