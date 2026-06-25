#!/usr/bin/python
# coding=utf-8
"""Regression guard for tentacle's Blender window ownership.

Blender isn't a Qt app, so every tentacle window (the marking-menu overlay + each standalone
tool panel) is an unrelated top-level OS window unless we explicitly tie it to Blender's native
GHOST window. The original code did this with ``QWindow.setTransientParent`` — but for a
*foreign* transient parent (Blender's window wrapped via ``QWindow.fromWinId``) Qt never sets the
Windows owner (``GWLP_HWNDPARENT``), so the windows were unowned and fell behind Blender the
moment they lost focus. ``tcl_blender._NativeWindow.set_owner`` sets the owner directly instead.

These tests need real native HWNDs (the ownership lives in the OS window manager), so they run
only on Windows with a real Qt platform — they skip elsewhere and in CI. The negative test pins
the root cause so a well-meaning "just use setTransientParent" refactor can't silently regress it.
"""
from __future__ import annotations

import ctypes
import os
import sys
import unittest


def _real_windows_platform() -> bool:
    """True only on a real Windows Qt platform — not the offscreen/minimal QPA.

    The ownership these tests assert lives in the OS window manager, so they
    need genuine native HWNDs. Under ``QT_QPA_PLATFORM=offscreen`` (CI and
    headless local runs) ``winId()`` returns a synthetic handle that Win32
    ``SetWindowLongPtr`` rejects, so the tests must *skip* there rather than
    run-and-fail.
    """
    if os.environ.get("QT_QPA_PLATFORM", "").lower() in ("offscreen", "minimal"):
        return False
    try:
        from qtpy import QtGui

        app = QtGui.QGuiApplication.instance()
        if app is not None and app.platformName().lower() in ("offscreen", "minimal"):
            return False
    except Exception:
        return False
    return True


def _can_run() -> bool:
    """Windows + a real (non-offscreen) Qt platform + an importable tcl_blender."""
    if sys.platform != "win32" or not _real_windows_platform():
        return False
    try:
        from qtpy import QtWidgets  # noqa: F401
        from tentacle import tcl_blender  # noqa: F401
    except Exception:
        return False
    return True


_SKIP_REASON = "Window-ownership tests need Windows + a real Qt platform (skipped in CI / off-Windows / offscreen)."

_GWLP_HWNDPARENT = -8


def _os_owner(widget):
    """The window's OS owner handle (``GWLP_HWNDPARENT``), or ``None`` when unowned."""
    user32 = ctypes.windll.user32
    user32.GetWindowLongPtrW.restype = ctypes.c_void_p
    user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return user32.GetWindowLongPtrW(ctypes.c_void_p(int(widget.winId())), _GWLP_HWNDPARENT)


@unittest.skipUnless(_can_run(), _SKIP_REASON)
class TestBlenderWindowOwnership(unittest.TestCase):
    """Verify the owner relationship that keeps tentacle windows above Blender."""

    @classmethod
    def setUpClass(cls):
        from qtpy import QtWidgets

        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["test"])

    def setUp(self):
        from qtpy import QtCore, QtWidgets

        # Stand-in for Blender's GHOST window: a real top-level whose HWND we own things to.
        self.owner = QtWidgets.QWidget()
        self.owner.setWindowFlag(QtCore.Qt.Window)
        self.owner_hwnd = int(self.owner.winId())
        self.addCleanup(self.owner.deleteLater)

    def _make_window(self):
        from qtpy import QtCore, QtWidgets

        w = QtWidgets.QWidget()
        w.setWindowFlag(QtCore.Qt.Window)
        w.winId()  # force native-window creation
        self.addCleanup(w.deleteLater)
        return w

    def test_set_native_owner_sets_os_owner(self):
        """``_NativeWindow.set_owner`` makes the window owned by the given HWND — the actual fix."""
        from tentacle import tcl_blender

        w = self._make_window()
        result = tcl_blender._NativeWindow.set_owner(w, self.owner_hwnd)
        self.assertEqual(result, self.owner_hwnd)
        self.assertEqual(_os_owner(w), self.owner_hwnd)

    def test_set_native_owner_idempotent(self):
        """Re-asserting the same owner (every show / native-window recreate) stays a clean no-op."""
        from tentacle import tcl_blender

        w = self._make_window()
        tcl_blender._NativeWindow.set_owner(w, self.owner_hwnd)
        tcl_blender._NativeWindow.set_owner(w, self.owner_hwnd)
        self.assertEqual(_os_owner(w), self.owner_hwnd)

    def test_set_native_owner_noop_without_owner(self):
        """No owner handle yet (GHOST not enumerable) → leave the window untouched, never raise."""
        from tentacle import tcl_blender

        w = self._make_window()
        self.assertIsNone(tcl_blender._NativeWindow.set_owner(w, 0))
        self.assertFalse(_os_owner(w))  # still unowned

    def test_foreign_transient_parent_does_not_set_owner(self):
        """Root-cause pin: ``setTransientParent`` to a FOREIGN window does NOT set the OS owner.

        This is why the explicit ``_NativeWindow.set_owner`` is required — if a future change drops it
        and relies on transient-parenting alone, this test fails and explains why the windows
        fall behind Blender.
        """
        from qtpy import QtGui

        foreign = QtGui.QWindow.fromWinId(self.owner_hwnd)
        w = self._make_window()
        w.windowHandle().setTransientParent(foreign)
        self.app.processEvents()
        self.assertNotEqual(
            _os_owner(w),
            self.owner_hwnd,
            "setTransientParent unexpectedly set the OS owner — the explicit owner-set "
            "may now be redundant; re-check before removing _NativeWindow.set_owner.",
        )


if __name__ == "__main__":
    unittest.main()
