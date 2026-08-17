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
