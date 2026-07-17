#!/usr/bin/python
# coding=utf-8
"""Regression tests for the base ``tentacle.slots._slots.Slots``.

Pins ``mirror_app_state`` (widgets whose value IS live DCC state are never persisted —
see ``TestMirrorAppState``) and the repeat-last consolidation:

- The legacy per-slot ``Ctrl+Shift+R`` QShortcut machinery is GONE. It created
  one application-scoped shortcut in every slot instance's ``__init__`` (so N
  loaded UIs stacked N identical shortcuts on the marking menu → Qt declared an
  ambiguous overload and fired none). Repeat-last is now the single uitk
  ``repeat_last_command`` command.
- ``_migrate_legacy_repeat_last`` folds a *customized* legacy key into that
  command once, and is a no-op when the key was never set.

These run under plain pytest — ``_slots.py`` imports only ``qtpy`` (no maya).
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before any widget is built

from qtpy import QtCore, QtWidgets  # noqa: E402
from uitk.widgets.mixins.state_manager import StateManager  # noqa: E402
from tentacle.slots._slots import Slots  # noqa: E402


def _can_create_widgets() -> bool:
    """False under mayapy.standalone / maya -batch: Maya's non-GUI Qt stub
    hard-crashes on QWidget construction (exit 9, no traceback) — the offscreen
    QPA above does not help there. Same discriminator as test_overlay_safety.
    The migration tests below use pure doubles and run everywhere."""
    try:
        import maya.cmds as cmds
    except ImportError:
        return True
    try:
        return not bool(cmds.about(batch=True))
    except Exception:
        return False


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


@unittest.skipUnless(
    _can_create_widgets(),
    "QWidget tests need an interactive-Qt context "
    "(plain Python or interactive Maya — not mayapy.standalone / batch).",
)
class TestMirrorAppState(unittest.TestCase):
    """``mirror_app_state`` keeps live-DCC-state widgets out of QSettings.

    The bug: opening tentacle's Blender selection submenu popped "<hl>Box Select</hl> tool
    active." every time. chk005 (Select Style: Marquee) persisted like any widget, and
    restoring it *fires the slot* — ``StateManager.apply`` unblocks signals per
    ``block_signals_on_restore`` (default False) — so merely opening the panel re-set the
    viewport tool and toasted. Same shape across submenus: symmetry re-mirrored the mesh,
    subdivision re-subdivided the selection, preferences overwrote the scene's units.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _checkbox(self, name="chk005", checked=False):
        """A QCheckBox stamped like ``MainWindow.register_widget`` leaves one."""
        w = QtWidgets.QCheckBox()
        w.setObjectName(name)
        w.setChecked(checked)
        w.restore_state = True
        w.derived_type = QtWidgets.QCheckBox
        w.default_signals = lambda: "toggled"
        return w

    def _state_manager(self):
        """Real StateManager over a throwaway INI — never the live ``uitk\\shared`` store."""
        tmp = tempfile.NamedTemporaryFile(suffix=".ini", delete=False)
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        qs = QtCore.QSettings(tmp.name, QtCore.QSettings.IniFormat)
        return StateManager(qs)

    def test_marks_widget_as_not_restorable(self):
        w = self._checkbox()
        Slots.mirror_app_state(w)
        self.assertFalse(w.restore_state)

    def test_seed_applies_value_without_firing_the_slot(self):
        w = self._checkbox(checked=False)
        fired = []
        w.toggled.connect(fired.append)

        Slots.mirror_app_state(w, lambda: w.setChecked(True))

        self.assertTrue(w.isChecked())  # seeded from "live DCC state"
        self.assertEqual(fired, [])  # ...but the command never ran

    def test_seed_leaves_signals_unblocked_afterwards(self):
        """Seeding must not leave the widget deaf to the user's own clicks."""
        w = self._checkbox()
        Slots.mirror_app_state(w, lambda: w.setChecked(True))
        self.assertFalse(w.signalsBlocked())

        fired = []
        w.toggled.connect(fired.append)
        w.setChecked(False)  # stands in for a real user toggle
        self.assertEqual(fired, [False])

    def test_seed_preserves_an_outer_block(self):
        """``init_slot`` wraps ``*_init`` in blockSignals(True); seeding must restore it."""
        w = self._checkbox()
        w.blockSignals(True)
        Slots.mirror_app_state(w, lambda: w.setChecked(True))
        self.assertTrue(w.signalsBlocked())

    def test_mark_survives_a_seed_that_re_arms_restore_state(self):
        """``ComboBox.add`` ends with ``restore_state = not self.has_header``, so a headerless
        combo seeded by its own ``add`` re-arms persistence mid-seed. The mark has to land
        after the seed, or the three headerless combos silently opt back in."""
        w = self._checkbox()

        def seed():
            w.setChecked(True)
            w.restore_state = True  # what ComboBox.add does on a headerless combo

        Slots.mirror_app_state(w, seed)
        self.assertFalse(w.restore_state)
        self.assertTrue(w.isChecked())

    def test_without_a_seed_the_value_is_untouched(self):
        w = self._checkbox(checked=True)
        fired = []
        w.toggled.connect(fired.append)
        Slots.mirror_app_state(w)
        self.assertTrue(w.isChecked())
        self.assertEqual(fired, [])

    def test_state_manager_restore_fires_the_slot_without_the_guard(self):
        """Positive control: this is the bug. Without ``mirror_app_state``, restoring a
        stored value runs the slot — so the toast fires on panel open, not on a click."""
        state = self._state_manager()
        w = self._checkbox(checked=False)
        state.save(w, True)  # a previous session left "Marquee" checked

        w2 = self._checkbox(checked=False)
        fired = []
        w2.toggled.connect(fired.append)
        state.load(w2)

        self.assertTrue(w2.isChecked())
        self.assertEqual(fired, [True], "restore must fire the slot when unguarded")

    def test_state_manager_skips_a_mirrored_widget(self):
        """The fix: a mirrored widget is neither restored nor re-fired on panel open."""
        state = self._state_manager()
        seeded = self._checkbox(checked=False)
        state.save(seeded, True)  # a stale "Marquee" is still on disk

        w = self._checkbox(checked=False)
        Slots.mirror_app_state(w)
        fired = []
        w.toggled.connect(fired.append)
        state.load(w)

        self.assertFalse(w.isChecked(), "stale stored state must not reach the widget")
        self.assertEqual(fired, [], "the tool must not be set (nor toasted) on panel open")

    def test_a_mirrored_widget_is_not_saved(self):
        """The DCC is the source of truth, so nothing is written back to persist over it."""
        state = self._state_manager()
        w = self._checkbox(checked=False)
        Slots.mirror_app_state(w)
        state.save(w, True)
        self.assertIsNone(state.qsettings.value("chk005/toggled"))


@unittest.skipUnless(
    _can_create_widgets(),
    "QWidget tests need an interactive-Qt context "
    "(plain Python or interactive Maya — not mayapy.standalone / batch).",
)
class TestAddSlotWidget(unittest.TestCase):
    """``add_slot_widget`` — a slot-wired widget as an ExpandableList entry.

    Backs the Scene submenu's Export list, whose first entry is the tb003
    exporter *widget* (option-box gear and all) rather than a plain label. Two
    cross-package uitk behaviors carry that design, and both would fail silently
    if uitk changed — hence real widgets here, not doubles:

    1. The widget must be PARENTED before its ``*_init`` runs. uitk wraps an
       option box synchronously only while ``parent()`` is set; unparented, the
       wrap defers to a retry timer and the gear misses the first paint. The
       helper's add-then-register order is what guarantees it.
    2. The wrap REPLACES the widget with its container in the list layout, so the
       widget leaves ``get_items()``. That is what stops the list from consuming
       its mouse release (``eventFilter`` gates on item membership) and lets its
       own ``clicked`` drive its slot.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _slot(self, init=None):
        """A bare Slots instance whose sb yields a real uitk PushButton, plus a
        stand-in MainWindow that registers like the real one (running the
        widget's ``*_init``)."""
        from types import SimpleNamespace
        from uitk.widgets.pushButton import PushButton

        registered = []

        class _Ui:
            def register_widget(_self, widget):
                # Mirrors MainWindow.register_widget's order: bind, then init.
                registered.append((widget, widget.parent()))
                widget.ui = _self
                widget.is_initialized = False
                if init:
                    init(widget)
                widget.is_initialized = True

        slot = Slots.__new__(Slots)
        slot.sb = SimpleNamespace(
            registered_widgets=SimpleNamespace(PushButton=PushButton)
        )
        return slot, _Ui(), registered

    def _list(self, ui):
        from uitk.widgets.expandableList import ExpandableList

        lst = ExpandableList()
        lst.ui = ui
        self.addCleanup(lst.deleteLater)
        return lst

    def test_widget_is_added_and_registered(self):
        slot, ui, registered = self._slot()
        lst = self._list(ui)
        root = lst.add("Export")

        w = slot.add_slot_widget(root.sublist, setObjectName="tb003", setText="Export Scene")

        self.assertEqual(w.objectName(), "tb003")
        self.assertIn(w, root.sublist.get_items())
        self.assertEqual([r[0] for r in registered], [w], "must register exactly once")

    def test_widget_is_parented_before_registration(self):
        """The ordering that makes an option-box wrap synchronous (see class docstring)."""
        slot, ui, registered = self._slot()
        lst = self._list(ui)
        root = lst.add("Export")

        slot.add_slot_widget(root.sublist, setObjectName="tb003")

        _widget, parent_at_register = registered[0]
        self.assertIsNotNone(
            parent_at_register,
            "widget must already be in the sublist layout when its *_init runs — "
            "an unparented widget defers its option-box wrap to a retry timer",
        )

    def test_option_box_wrap_removes_widget_from_item_set(self):
        """An *_init that builds an option box leaves the entry click-through."""
        def _init(widget):
            widget.option_box.menu.add("QComboBox", setObjectName="cmb_scope")

        slot, ui, _registered = self._slot(init=_init)
        lst = self._list(ui)
        root = lst.add("Export")

        w = slot.add_slot_widget(root.sublist, setObjectName="tb003")

        self.assertTrue(w.option_box._is_wrapped, "wrap must complete during *_init")
        self.assertNotIn(
            w,
            root.sublist.get_items(),
            "the wrap must swap the widget for its container — while it remains an "
            "item the list consumes its release and clicked never fires",
        )

    def test_widget_without_option_box_stays_an_item(self):
        """The documented contract's other half: no option box ⇒ still an item, so
        the list consumes its release and the list's own handler must dispatch it."""
        slot, ui, _registered = self._slot()
        lst = self._list(ui)
        root = lst.add("Export")

        w = slot.add_slot_widget(root.sublist, setObjectName="b099")

        self.assertIn(w, root.sublist.get_items())


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
