# !/usr/bin/python
# coding=utf-8
"""Test isolation for tentacle's suite.

tentacle constructs real marking menus, and ``MarkingMenu`` **persists its bindings on
construction** — so without this the suite rewrites the developer's live activation key and chord
table in the shared ``QSettings`` store. That failure is silent (no test fails; the user's hotkey
just resets in a different app hours later), which is why ``test_package.py`` **asserts** the
redirect is in place rather than trusting that it is.

The redirect itself lives upstream in ``uitk.testing`` because the store is process-wide and shared
across the ecosystem; see that module. It must run before the first ``QSettings`` is constructed,
hence import time.

**This file only covers ``pytest`` runs.** tentacle's canonical runner discovers with ``unittest``,
which never imports a ``conftest``, and its ``--in-maya`` mode is a third case again: a standalone
source string executed inside Maya that imports neither this file nor ``run_tests.py``. All three
entry points activate the same idempotent classmethod — that is coverage, not duplication, and
missing any one of them silently loses the isolation for that path (the ``--in-maya`` one was
missed on the first pass, which is the run that actually constructs the menus).
"""
from uitk.testing import TestSandbox

QSETTINGS_SANDBOX_DIR, PRESETS_SANDBOX_DIR = TestSandbox.activate()
