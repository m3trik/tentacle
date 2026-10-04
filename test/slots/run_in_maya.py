#!/usr/bin/python
# coding=utf-8
"""Runner for slot migration tests inside a fresh mayapy interpreter.

Usage (from repo root):
    & "C:\\Program Files\\Autodesk\\Maya2025\\bin\\mayapy.exe" \
        tentacle\\test\\slots\\run_in_maya.py

What it does:
    1. Adds the four ecosystem packages (pythontk, uitk, mayatk, tentacle)
       to PYTHONPATH so the slot modules can resolve their dependencies.
    2. Initializes maya.standalone (a fresh, in-process Maya — never
       touches an existing Maya session, per the project's hard rule),
       then opens a throwaway Maya project inside the test sandbox.
    3. Discovers and runs every test_*.py in this directory.
    4. Exits 0 on success, non-zero on failure.

It launches no Maya through mayatk's MayaConnection. From tentacle's own
run_tests.py it takes one helper, ``_sandbox_maya_workspace``; importing
that module also activates the live-settings ``TestSandbox``.
"""
import sys
import unittest
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
TENTACLE_TEST = THIS_DIR.parent
TENTACLE_ROOT = TENTACLE_TEST.parent
MONOREPO = TENTACLE_ROOT.parent


def _ensure_paths():
    """Push ecosystem package roots onto sys.path."""
    for pkg in ("pythontk", "uitk", "mayatk", "tentacle"):
        p = MONOREPO / pkg
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    # The slots subdir itself, so test files can import _helpers
    if str(THIS_DIR) not in sys.path:
        sys.path.insert(0, str(THIS_DIR))
    # The parent test dir, so test files can import the shared _host probes
    if str(TENTACLE_TEST) not in sys.path:
        sys.path.insert(0, str(TENTACLE_TEST))


def _start_maya():
    """Initialize maya.standalone (fresh, in-process)."""
    import maya.standalone

    maya.standalone.initialize(name="python")
    # Off the user's live settings and real Maya project, like run_tests.py:
    # importing it activates the TestSandbox, and a tool that names no path
    # writes into the CURRENT project, which mayapy opens as the user's default.
    from run_tests import _sandbox_maya_workspace

    _sandbox_maya_workspace()


def _run() -> int:
    _ensure_paths()
    _start_maya()

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(THIS_DIR),
        pattern="test_*.py",
        top_level_dir=str(THIS_DIR),
    )

    print("=" * 72)
    print("Tentacle slot migration tests (Maya)")
    print("  PYTHONPATH roots: pythontk, uitk, mayatk, tentacle")
    print(f"  Discovering from: {THIS_DIR}")
    print("=" * 72)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(_run())
