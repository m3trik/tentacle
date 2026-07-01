#!/usr/bin/python
# coding=utf-8
"""Regression tests for the base ``tentacle.slots._slots.Slots``.

Pins the repeat-last consolidation:

- The legacy per-slot ``Ctrl+Shift+R`` QShortcut machinery is GONE. It created
  one application-scoped shortcut in every slot instance's ``__init__`` (so N
  loaded UIs stacked N identical shortcuts on the marking menu → Qt declared an
  ambiguous overload and fired none). Repeat-last is now the single uitk
  ``repeat_last_command`` command.
- ``_migrate_legacy_repeat_last`` folds a *customized* legacy key into that
  command once, and is a no-op when the key was never set.

These run under plain pytest — ``_slots.py`` imports only ``qtpy`` (no maya).
"""
import unittest

from qtpy import QtCore  # noqa: F401  (ensures a Qt binding is importable)
from tentacle.slots._slots import Slots


class _Item:
    """Stand-in for a ``SettingsManager`` SettingItem (get/set proxy)."""

    def __init__(self, value):
        self._v = value

    def get(self, default=None):
        return self._v if self._v is not None else default

    def set(self, value):
        self._v = value


class _Cfg:
    """Stand-in for ``sb.configurable`` exposing the legacy key + clear()."""

    def __init__(self, legacy):
        self.repeat_last_shortcut = _Item(legacy)
        self.cleared = False

    def clear(self, key=None):
        self.cleared = True
        self.repeat_last_shortcut._v = None


class _Sb:
    """Minimal switchboard double for the migration path."""

    def __init__(self, legacy=None, cmd_default=""):  # command ships unbound
        self.configurable = _Cfg(legacy)
        self._cmd_default = cmd_default
        self.set_calls = []

    def get_command_registry(self):
        return [
            {
                "method": "repeat_last_command",
                "default": self._cmd_default,
                "current": self._cmd_default,
                "command": True,
            }
        ]

    def set_command_shortcut(self, name, sequence, scope=None):
        self.set_calls.append((name, sequence, scope))


class TestLegacyRepeatLastRemoved(unittest.TestCase):
    """The old per-slot shortcut machinery must stay deleted."""

    def test_no_legacy_attributes_or_method(self):
        for name in (
            "_update_repeat_last_shortcut",
            "_repeat_last_shortcut",
            "repeat_last_command",
        ):
            self.assertFalse(
                hasattr(Slots, name),
                f"legacy repeat-last surface {name!r} should be gone",
            )


class TestMigrateLegacyRepeatLast(unittest.TestCase):
    """``_migrate_legacy_repeat_last`` folds a customized key into the command."""

    def test_absent_key_is_noop(self):
        sb = _Sb(legacy=None)
        Slots._migrate_legacy_repeat_last(sb)
        self.assertEqual(sb.set_calls, [])
        self.assertFalse(sb.configurable.cleared)  # nothing to retire

    def test_customized_key_becomes_command_override(self):
        sb = _Sb(legacy="Ctrl+R")
        Slots._migrate_legacy_repeat_last(sb)
        self.assertEqual(
            sb.set_calls, [("repeat_last_command", "Ctrl+R", "application")]
        )
        self.assertTrue(sb.configurable.cleared)

    def test_value_equal_to_unbound_default_retired_without_override(self):
        # The command ships UNBOUND, so a legacy value equal to that empty
        # default — i.e. the user had explicitly *disabled* repeat-last — is just
        # retired: no redundant "" override is written, because the unbound
        # default already yields the same (no shortcut) result.
        sb = _Sb(legacy="")
        Slots._migrate_legacy_repeat_last(sb)
        self.assertEqual(sb.set_calls, [])
        self.assertTrue(sb.configurable.cleared)

    def test_legacy_old_default_preserved_as_override(self):
        # A user carrying the *old* Ctrl+Shift+R default (from before repeat-last
        # was unbound) keeps it: it differs from the new empty default, so it's
        # folded into an explicit override rather than silently dropped.
        sb = _Sb(legacy="Ctrl+Shift+R")
        Slots._migrate_legacy_repeat_last(sb)
        self.assertEqual(
            sb.set_calls, [("repeat_last_command", "Ctrl+Shift+R", "application")]
        )
        self.assertTrue(sb.configurable.cleared)

    def test_missing_command_keeps_legacy_key(self):
        # If repeat_last_command isn't registered, the legacy key must NOT be
        # cleared into the void — that would silently lose the user's value.
        class _SbNoCmd(_Sb):
            def get_command_registry(self):
                return []

        sb = _SbNoCmd(legacy="Ctrl+R")
        Slots._migrate_legacy_repeat_last(sb)
        self.assertEqual(sb.set_calls, [])
        self.assertFalse(sb.configurable.cleared)  # legacy preserved, not lost
        self.assertEqual(sb.configurable.repeat_last_shortcut.get(None), "Ctrl+R")


class TestMigrationRunsOnce(unittest.TestCase):
    """Instantiating slots migrates once per process, not per instance."""

    def setUp(self):
        Slots._legacy_repeat_last_migrated = False

    def tearDown(self):
        Slots._legacy_repeat_last_migrated = False

    def test_only_first_slot_instance_migrates(self):
        sb1 = _Sb(legacy="Ctrl+R")
        Slots(sb1)
        self.assertEqual(
            sb1.set_calls, [("repeat_last_command", "Ctrl+R", "application")]
        )

        # A second slot instance (same process) must NOT re-run the migration.
        sb2 = _Sb(legacy="Ctrl+R")
        Slots(sb2)
        self.assertEqual(sb2.set_calls, [])
        self.assertFalse(sb2.configurable.cleared)

    def test_migration_failure_does_not_block_slot_init(self):
        class _BadSb:
            configurable = property(lambda self: (_ for _ in ()).throw(RuntimeError))

        # Must not raise — slot init has to survive a migration hiccup.
        Slots(_BadSb())


if __name__ == "__main__":
    unittest.main()
