#!/usr/bin/python
# coding=utf-8
"""End-to-end persistence tests for tentacle slot panels.

Production registry inspection (``HKCU\\Software\\uitk\\shared\\switchboard\\``)
showed polygons / edit / hierarchy_manager panels saving ONLY
``window_geometry`` — no widget-state subkeys — despite users
interacting with their option_box menu widgets across sessions. The
existing tentacle test suite uses fake widget stubs and bypasses the
entire uitk persistence chain, so this regression had no end-to-end
coverage.

This file fills the gap. Each test constructs a real :class:`TclMaya`
(which registers the marking_menu handler the production slot classes
require at construction time), loads a real slot panel, exercises its
dynamically-added option_box widgets, and verifies the
``StateManager.save`` / ``StateManager.load`` round-trip writes to and
reads from QSettings correctly.

Runs under mayapy.standalone via:

    PYTHONPATH=...tentacle;...uitk;...mayatk;...pythontk \\
        mayapy.exe tentacle/test/slots/test_widget_state_persistence.py
"""
from __future__ import annotations

import sys
import unittest

from _helpers import maya_available, qt_widgets_available

_SKIP_REASON = "Requires maya.cmds + Qt widgets (run via mayapy)"


@unittest.skipUnless(maya_available() and qt_widgets_available(), _SKIP_REASON)
class _PersistenceBase(unittest.TestCase):
    """Shared setup: one TclMaya per class, isolated QSettings, event drain.

    Clearing the test store goes through the LIVE ``sb.settings``
    instance so the long-lived QSettings cache stays consistent with
    on-disk state. Clearing via a transient ``SettingsManager(...).clear()``
    would corrupt the long-lived instance's write cache and cause
    spurious save-but-not-read failures.
    """

    TEST_ORG = "uitk_persist_test_in_maya"
    TEST_APP = "tentacle"

    tcl = None

    @classmethod
    def setUpClass(cls):
        from qtpy import QtCore, QtWidgets
        cls.QtCore = QtCore
        cls.QtWidgets = QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

        from tentacle.tcl_maya import TclMaya
        cls.tcl = TclMaya(parent=None, log_level="WARNING")
        cls.sb = cls.tcl.sb

        from uitk.widgets.mixins.settings_manager import SettingsManager
        cls.SettingsManager = SettingsManager
        cls.sb.settings = SettingsManager(
            org=cls.TEST_ORG, app=cls.TEST_APP, namespace="switchboard"
        )

    @classmethod
    def tearDownClass(cls):
        # Clear and tear down the TclMaya instance so no QObjects leak
        # into subsequent test modules (mayapy reuses one process for
        # the whole suite).
        cls.sb.settings.settings.clear()
        cls.sb.settings.settings.sync()
        try:
            cls.tcl.deleteLater()
        except Exception:
            pass
        cls.QtWidgets.QApplication.processEvents()

    def setUp(self):
        # Clear via the LIVE sb.settings instance — see class docstring.
        self.sb.settings.settings.clear()
        self.sb.settings.settings.sync()

    def tearDown(self):
        for _ in range(3):
            self.QtWidgets.QApplication.processEvents(
                self.QtCore.QEventLoop.AllEvents, 25
            )

    def _drain(self, pumps=10):
        for _ in range(pumps):
            self.QtWidgets.QApplication.processEvents(
                self.QtCore.QEventLoop.AllEvents, 25
            )

    def _load_panel(self, ui_name):
        """Force-construct *ui_name* via ``sb.loaded_ui`` (subsequent
        accesses return the same MainWindow). Re-points settings/state
        at the isolated test store so reads round-trip through our
        cleared QSettings."""
        from uitk.widgets.mixins.state_manager import StateManager
        ui = getattr(self.sb.loaded_ui, ui_name)
        ui.settings = self.sb.settings.branch(ui.objectName())
        ui.state = StateManager(ui.settings)
        ui.register_children()
        self._drain(); self._drain()
        return ui

    def _raw_keys(self):
        return sorted(
            self.SettingsManager(org=self.TEST_ORG, app=self.TEST_APP).keys()
        )


# ===========================================================================
# Polygons: tb007 has chk008 (U) / chk009 (V) / chk010 (Tris)
# ===========================================================================

class TestPolygonsOptionBoxPersistence(_PersistenceBase):

    def test_tb007_init_adds_chk008_to_option_box_menu(self):
        ui = self._load_panel("polygons")
        menu = ui.tb007.option_box.menu
        self._drain()
        self.assertIsNotNone(
            getattr(menu, "chk008", None),
            "tb007_init did not add chk008 — "
            "PolygonsSlots construction may have failed silently. "
            f"Menu children: {[w.objectName() for w in menu.findChildren(self.QtWidgets.QWidget) if w.objectName()]}"
        )

    def test_tb007_chk008_toggle_writes_to_qsettings(self):
        ui = self._load_panel("polygons")
        chk008 = ui.tb007.option_box.menu.chk008
        original = chk008.isChecked()
        chk008.setChecked(not original)
        self._drain()

        sm = self.SettingsManager(org=self.TEST_ORG, app=self.TEST_APP)
        self.assertEqual(
            sm.value("switchboard/polygons/chk008/toggled"),
            not original,
            "tb007 chk008 toggle did not persist to expected key",
        )

    def test_tb007_chk008_value_visible_without_explicit_sync(self):
        """Pin the per-save sync contract: a brand-new QSettings sees
        the value without anyone calling ``settings.sync()`` between
        the write and the read."""
        ui = self._load_panel("polygons")
        chk008 = ui.tb007.option_box.menu.chk008
        chk008.setChecked(not chk008.isChecked())
        self._drain()

        # NO explicit sync. NEW QSettings.
        fresh = self.QtCore.QSettings(self.TEST_ORG, self.TEST_APP)
        self.assertIn(
            "switchboard/polygons/chk008/toggled", fresh.allKeys(),
            "Per-save sync regressed: write not visible to fresh QSettings",
        )


# ===========================================================================
# Smoke test: every major panel persists something
# ===========================================================================

class TestEveryPanelPersistsAtLeastOneWidget(_PersistenceBase):
    """Walk each panel, find one stateful widget after init, toggle it,
    assert a registry key appears. The failure mode reproduces the
    user-reported "panel saves nothing across sessions" bug if any
    panel breaks the chain."""

    def _exercise_panel(self, name):
        from uitk.widgets.menu import Menu
        ui = self._load_panel(name)
        # Force every tb* button to expose its option_box menu — this
        # triggers lazy tb*_init.
        for w in list(ui.widgets):
            if w.objectName().startswith("tb") and hasattr(w, "option_box"):
                try:
                    _ = w.option_box.menu
                except Exception:
                    pass
        self._drain(); self._drain()

        stateful = (
            self.QtWidgets.QCheckBox, self.QtWidgets.QSpinBox,
            self.QtWidgets.QDoubleSpinBox, self.QtWidgets.QComboBox,
        )
        candidates = []
        seen = set()
        for w in ui.widgets:
            if id(w) in seen: continue
            seen.add(id(w))
            if isinstance(w, stateful) and w.objectName():
                candidates.append(w)
        for m in ui.findChildren(Menu):
            for c in m.findChildren(self.QtWidgets.QWidget):
                if id(c) in seen: continue
                seen.add(id(c))
                if isinstance(c, stateful) and c.objectName():
                    candidates.append(c)
        return ui, candidates

    def _flip(self, w):
        if hasattr(w, "setChecked"):
            w.setChecked(not w.isChecked())
            return True
        if hasattr(w, "setValue"):
            new = (w.value() or 0) + 1
            if hasattr(w, "maximum") and new > w.maximum():
                new = w.minimum()
            w.setValue(new)
            return True
        if hasattr(w, "setCurrentIndex"):
            if w.count() > 1:
                w.setCurrentIndex((w.currentIndex() + 1) % w.count())
                return True
        return False

    def _assert_panel_persists_something(self, panel_name):
        ui, candidates = self._exercise_panel(panel_name)
        if not candidates:
            self.skipTest(f"{panel_name} exposed no stateful widget after init")

        # Try up to 5 candidates so a single slot with side-effects (a
        # combobox that can't change index, etc.) doesn't make the test
        # spuriously skip.
        for cand in candidates[:5]:
            if not self._flip(cand):
                continue
            self._drain()
            after = self._raw_keys()
            if any(cand.objectName() in k for k in after):
                return
        self.fail(
            f"{panel_name}: toggled {min(5, len(candidates))} stateful widget(s) "
            f"but none produced a registry key. Persistence is broken for this panel."
        )

    def test_polygons(self):
        self._assert_panel_persists_something("polygons")

    def test_edit(self):
        self._assert_panel_persists_something("edit")

    def test_selection(self):
        self._assert_panel_persists_something("selection")

    def test_channels(self):
        self._assert_panel_persists_something("channels")


# ===========================================================================
# Round-trip: save in one "session", rebuild fresh state, expect restore
# ===========================================================================

class TestPolygonsSessionRoundTrip(_PersistenceBase):
    """The user-facing contract: change a widget in session 1, expect
    that value to show up in session 2.

    "Rebuild" here means tearing down ui.state and re-running
    state.load — equivalent to what happens when a new MainWindow loads
    with a non-empty QSettings store."""

    def test_chk008_value_restored_after_state_rebuild(self):
        from uitk.widgets.mixins.state_manager import StateManager

        ui = self._load_panel("polygons")
        chk008 = ui.tb007.option_box.menu.chk008
        original = chk008.isChecked()

        # Session 1: flip and save. This sync goes through the real
        # signal path, so the value persists to QSettings.
        chk008.setChecked(not original)
        self._drain()
        ui.settings.sync()

        # Restore the widget's in-memory state to the .ui-file default
        # so we can observe state.load actually re-applying the persisted
        # value (rather than the test trivially seeing a value that was
        # never changed). Block signals so this in-memory restore does
        # NOT echo back as a save and overwrite what we just persisted.
        chk008.blockSignals(True)
        try:
            chk008.setChecked(original)
        finally:
            chk008.blockSignals(False)
        self._drain()
        self.assertEqual(chk008.isChecked(), original)

        # Session 2: rebuild state, ask state.load to repopulate. The
        # value we saved (not-original) should come back.
        ui.state = StateManager(ui.settings)
        ui.state.load(chk008)
        self._drain()

        self.assertEqual(
            chk008.isChecked(), not original,
            "state.load did not restore the persisted chk008 value "
            "after the state manager was rebuilt",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
