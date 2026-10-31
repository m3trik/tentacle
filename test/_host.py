#!/usr/bin/python
# coding=utf-8
"""Shared host-runtime probes for tentacle's test suite.

Loud-failure contract
---------------------
``MAYA_AVAILABLE`` reflects ONLY whether the Maya runtime (``maya.cmds``)
is importable. ``maya_module()`` gates on that flag alone: when Maya IS
present, the requested module is imported **unguarded**, so an ImportError
raised inside a slots module (a real bug) fails the importing test file
loudly at load time instead of silently turning the whole module into
skips. Skips masquerading as passes are forbidden — see
m3trik/docs/TEST_BADGE_STANDARD.md.

Underscore-prefixed so ``test_*`` discovery never collects it.
Stdlib-only; no project dependencies.
"""
from __future__ import annotations

import importlib

try:
    importlib.import_module("maya.cmds")
    MAYA_AVAILABLE: bool = True
except ImportError:
    MAYA_AVAILABLE = False


def maya_module(name: str):
    """Import *name* iff the Maya runtime is present; else return ``None``.

    When ``MAYA_AVAILABLE`` is True the import is deliberately UNGUARDED:
    an ImportError from the target module itself must propagate (real
    defect), never read as "Maya absent".
    """
    if not MAYA_AVAILABLE:
        return None
    return importlib.import_module(name)


def qt_widgets_available() -> bool:
    """True iff QWidget construction is supported in the current process.

    QWidget construction silently aborts (exit 127/9, no Python traceback)
    in mayapy.standalone / maya -batch — even after a QApplication has been
    promoted by other imports — because Maya's batch/standalone Qt is a
    stub that can't host real widgets. A ``try/except`` around actually
    instantiating one cannot catch this: it's a native abort, not a Python
    exception. ``cmds.about(batch=True)`` is the safe, Qt-free
    discriminator:

    - Plain Python:       no maya.cmds  -> True (regular Qt context)
    - Interactive Maya:    batch=False  -> True (full GUI Qt)
    - mayapy.standalone:   batch=True   -> False (widgets abort the process)
    """
    if not MAYA_AVAILABLE:
        return True
    import maya.cmds as cmds

    try:
        return not bool(cmds.about(batch=True))
    except Exception:
        return False

def standalone_interpreter():
    """``(path, "")`` of a Python interpreter a test can spawn, or ``(None, reason)``.

    Under the --in-maya dispatcher ``sys.executable`` is the HOST binary
    (maya.exe), not an interpreter: ``maya.exe -c ...`` is not a valid
    invocation -- it starts another GUI Maya or dies in native code, with no
    Python traceback. mayapy ships beside maya.exe, so a spawning check keeps
    its coverage under every entry point instead of skipping the one where a
    stray side effect is most likely.
    """
    import os
    import sys
    from pathlib import Path

    if not sys.executable:
        # Embedded interpreters can leave this empty, and Path("") has no
        # name to substitute -- with_name() would raise ValueError.
        return None, "sys.executable is empty; nothing to spawn"
    exe = Path(sys.executable)
    if exe.stem.lower().startswith("python"):
        return exe, ""
    mayapy = exe.with_name("mayapy.exe" if os.name == "nt" else "mayapy")
    if mayapy.exists():
        return mayapy, ""
    return None, f"no standalone interpreter beside {exe.name}"


class MemoryClipboard:
    """``QApplication.clipboard()`` for a test: the copy stays in this process.

    In a GUI Maya the real one is the Windows clipboard, shared with every
    program on the machine: one holding it made every read come back empty,
    the test's own "before" text included (2026-10-12, 7 Export tests red
    with nothing wrong). Python owns the QMimeData here, so nothing is left
    in Qt's global for libc exit to tear down either (exit 139 after a green
    summary under the offscreen platform). Qt is imported on first use, so
    this module stays importable where Qt is not.
    """

    def __init__(self):
        from qtpy import QtCore

        self._QMimeData = QtCore.QMimeData
        self._mime = QtCore.QMimeData()

    def setText(self, text):
        mime = self._QMimeData()
        mime.setText(text)
        self._mime = mime

    def setMimeData(self, mime):
        self._mime = mime

    def mimeData(self):
        return self._mime

    def text(self):
        return self._mime.text()

    def clear(self):
        self._mime = self._QMimeData()


def use_memory_clipboard(case):
    """Give *case* a :class:`MemoryClipboard` for every
    ``QApplication.clipboard()`` call -- the panel's and the test's -- until
    it ends; returns the clipboard."""
    from unittest import mock

    from qtpy import QtWidgets

    board = MemoryClipboard()
    patch = mock.patch.object(QtWidgets.QApplication, "clipboard", return_value=board)
    patch.start()
    case.addCleanup(patch.stop)
    return board
