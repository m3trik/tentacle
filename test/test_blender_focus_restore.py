#!/usr/bin/python
# coding=utf-8
"""Regression guard for tentacle's Blender foreground/focus hand-back.

Blender's activation key (F12) is delivered by a Blender keymap operator, which only fires
while Blender's native GHOST window has OS keyboard focus (the Qt shortcut fallback is inert —
its owner widget is hidden). Any Qt popup that takes activation and then hides without handing
the OS foreground back to GHOST leaves the key dead until the user clicks the viewport. The
live repro: open a marking-menu option_box, release F12 while its dropdown is open, dismiss the
dropdown — ``uitk.Menu.hideEvent`` restores focus Qt-side only, so the foreground stays on a
hidden Qt window and neither Blender's keymap nor Qt ever sees F12 again.

These tests pin ``tcl_blender._NativeWindow``'s foreground primitives:

* ``_qt_widget_for_hwnd`` — maps an OS foreground handle back to one of OUR Qt top-levels
  without forcing native-window creation on unrelated widgets.
* ``restore_foreground`` — hands focus to GHOST only when the foreground is ours (never steals
  from another app, or from Blender's own secondary GHOST windows / native dialogs — same PID,
  not Qt), and no-ops when GHOST already has it.
* ``restore_foreground_if_stranded`` — the poller watchdog: detects "foreground stuck on one of
  our HIDDEN Qt windows" and heals it; leaves every other state alone.

All ctypes goes through the ``_foreground_hwnd``/``_set_foreground`` seams (patched here), so
the tests are deterministic and offscreen-QPA safe — no real HWNDs or OS focus involved.
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch, MagicMock


def _can_run() -> bool:
    """Windows (the primitives are win32 no-ops elsewhere) + an importable tcl_blender
    + a Qt that can host real widgets.

    The fixture builds a QApplication and forces native-window creation
    (``winId()``); under mayapy.standalone / maya -batch Maya's Qt is a non-GUI
    stub and that hard-crashes the process (exit 9, no traceback) — the same
    reason test_overlay_safety skips there. ``cmds.about(batch=True)`` is the
    reliable discriminator; no maya.cmds means plain Python with regular Qt.
    """
    if sys.platform != "win32":
        return False
    try:
        from qtpy import QtWidgets  # noqa: F401
        from tentacle import tcl_blender  # noqa: F401
    except Exception:
        return False
    try:
        import maya.cmds as cmds
    except ImportError:
        return True  # no Maya — plain Python with regular Qt
    try:
        return not bool(cmds.about(batch=True))
    except Exception:
        return False


_SKIP_REASON = (
    "Foreground hand-back tests need win32 + an interactive-Qt context "
    "(plain Python or interactive Maya — not mayapy.standalone / batch)."
)

GHOST_HWND = 0xB1E42  # fake GHOST handle — never dereferenced (the ctypes seams are patched)


def _foreign_hwnd():
    """An HWND guaranteed not to belong to any of our Qt top-levels."""
    from qtpy import QtWidgets

    ids = {int(w.internalWinId() or 0) for w in QtWidgets.QApplication.topLevelWidgets()}
    return max(ids | {0x1000}) + 0x5150


@unittest.skipUnless(_can_run(), _SKIP_REASON)
class _FocusRestoreBase(unittest.TestCase):
    """Shared fixture: QApplication, a fake GHOST handle, patched ctypes seams."""

    @classmethod
    def setUpClass(cls):
        from qtpy import QtWidgets

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["test"])

    def setUp(self):
        from qtpy import QtWidgets
        from tentacle import tcl_blender

        self.nw = tcl_blender._NativeWindow
        self.app._blender_native_hwnd = GHOST_HWND
        self.addCleanup(lambda: delattr(self.app, "_blender_native_hwnd"))
        # Deterministic: no window is Qt-active unless a test says so (offscreen-QPA rule).
        self._aw = patch.object(QtWidgets.QApplication, "activeWindow", return_value=None)
        self._aw.start()
        self.addCleanup(self._aw.stop)
        self.set_fg = MagicMock()
        patcher = patch.object(self.nw, "_set_foreground", self.set_fg)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sentinel_tcl = self._widget()  # stands in for the live TclBlender overlay

    def _widget(self, native=True, visible=False):
        from qtpy import QtCore, QtWidgets

        w = QtWidgets.QWidget()
        w.setWindowFlag(QtCore.Qt.Window)
        if native:
            w.winId()  # force native-window creation so internalWinId is set
        if visible:
            w.show()
        self.addCleanup(w.deleteLater)
        return w

    def _with_fg(self, hwnd):
        patcher = patch.object(self.nw, "_foreground_hwnd", MagicMock(return_value=int(hwnd)))
        patcher.start()
        self.addCleanup(patcher.stop)


class TestQtWidgetForHwnd(_FocusRestoreBase):
    """``_qt_widget_for_hwnd`` — foreground handle → our Qt top-level, without side effects."""

    def test_matches_widget_with_created_native_window(self):
        w = self._widget()
        self.assertIs(self.nw._qt_widget_for_hwnd(int(w.winId())), w)

    def test_foreign_hwnd_returns_none(self):
        self.assertIsNone(self.nw._qt_widget_for_hwnd(_foreign_hwnd()))

    def test_zero_returns_none(self):
        self.assertIsNone(self.nw._qt_widget_for_hwnd(0))

    def test_lookup_never_forces_native_window_creation(self):
        """The scan must skip natively-uncreated widgets, not create windows for them.

        ``QWidget.winId()`` forces native creation; ``internalWinId()`` doesn't. A poller
        running this 50×/s would otherwise materialize native windows for every lazy
        top-level in the process.
        """
        virgin = self._widget(native=False)
        self.nw._qt_widget_for_hwnd(_foreign_hwnd())
        self.assertEqual(int(virgin.internalWinId() or 0), 0)


class TestRestoreForeground(_FocusRestoreBase):
    """``restore_foreground`` — hand focus to GHOST, but never steal it from anyone else."""

    def test_noop_when_ghost_already_foreground(self):
        self._with_fg(GHOST_HWND)
        self.nw.restore_foreground(self.sentinel_tcl)
        self.set_fg.assert_not_called()

    def test_restores_when_foreground_is_our_hidden_window(self):
        """The stranded state: a dead Qt popup still holds the OS foreground."""
        dead = self._widget()
        self._with_fg(int(dead.winId()))
        self.nw.restore_foreground(self.sentinel_tcl)
        self.set_fg.assert_called_once_with(GHOST_HWND)

    def test_never_steals_from_foreign_window(self):
        """Foreground belongs to another app (or a Blender-native dialog) → leave it alone.

        This is the pin for the alt-tab case: releasing the activation key after switching
        to another application must not yank focus back to Blender.
        """
        self._with_fg(_foreign_hwnd())
        self.nw.restore_foreground(self.sentinel_tcl)
        self.set_fg.assert_not_called()

    def test_restores_when_no_foreground_at_all(self):
        """A destroyed foreground window leaves fg=0 — restoring steals from nobody."""
        self._with_fg(0)
        self.nw.restore_foreground(self.sentinel_tcl)
        self.set_fg.assert_called_once_with(GHOST_HWND)

    def test_bails_when_another_visible_tentacle_window_is_active(self):
        """Maya-parity guard (pre-existing): a pinned tool window the user works in keeps focus."""
        from qtpy import QtWidgets

        pinned = self._widget(visible=True)
        dead = self._widget()
        self._with_fg(int(dead.winId()))
        with patch.object(QtWidgets.QApplication, "activeWindow", return_value=pinned):
            self.nw.restore_foreground(self.sentinel_tcl)
        self.set_fg.assert_not_called()

    def test_idempotent_second_call_after_restore(self):
        """Once foreground is back on GHOST, further calls are clean no-ops."""
        dead = self._widget()
        self._with_fg(int(dead.winId()))
        self.nw.restore_foreground(self.sentinel_tcl)
        self._with_fg(GHOST_HWND)  # the restore landed
        self.nw.restore_foreground(self.sentinel_tcl)
        self.set_fg.assert_called_once_with(GHOST_HWND)


class TestRestoreForegroundIfStranded(_FocusRestoreBase):
    """``restore_foreground_if_stranded`` — the poller watchdog's decision table."""

    def test_hidden_our_window_foreground_heals(self):
        dead = self._widget()
        self._with_fg(int(dead.winId()))
        self.assertTrue(self.nw.restore_foreground_if_stranded(self.sentinel_tcl))
        self.set_fg.assert_called_once_with(GHOST_HWND)

    def test_ghost_foreground_is_not_stranded(self):
        self._with_fg(GHOST_HWND)
        self.assertFalse(self.nw.restore_foreground_if_stranded(self.sentinel_tcl))
        self.set_fg.assert_not_called()

    def test_visible_our_window_is_not_stranded(self):
        """A visible tentacle window holding focus is in use — never yank it."""
        live = self._widget(visible=True)
        self._with_fg(int(live.winId()))
        self.assertFalse(self.nw.restore_foreground_if_stranded(self.sentinel_tcl))
        self.set_fg.assert_not_called()

    def test_foreign_foreground_is_not_stranded(self):
        self._with_fg(_foreign_hwnd())
        self.assertFalse(self.nw.restore_foreground_if_stranded(self.sentinel_tcl))
        self.set_fg.assert_not_called()

    def test_no_foreground_is_not_stranded(self):
        self._with_fg(0)
        self.assertFalse(self.nw.restore_foreground_if_stranded(self.sentinel_tcl))
        self.set_fg.assert_not_called()

    def test_without_ghost_handle_does_nothing(self):
        dead = self._widget()
        self._with_fg(int(dead.winId()))
        delattr(self.app, "_blender_native_hwnd")
        self.addCleanup(lambda: setattr(self.app, "_blender_native_hwnd", GHOST_HWND))
        self.assertFalse(self.nw.restore_foreground_if_stranded(self.sentinel_tcl))
        self.set_fg.assert_not_called()


if __name__ == "__main__":
    unittest.main()
