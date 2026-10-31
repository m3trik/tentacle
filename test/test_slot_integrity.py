#!/usr/bin/python
# coding=utf-8
"""Slot-file conventions across the whole slots layer.

- No pymel imports (the package is fully migrated to maya.cmds).
- 30+ slot files sanity floor.

The layer's structural invariants (one composed class per category, no per-host
slot package, unique objectNames, import discipline) live in ``test_dcc_invariants.py``.
"""

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
SLOTS_DIR = PKG / "slots"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Files that are not concrete slot modules
_SKIP = {"__init__.py"}


def _slot_files():
    """Every module of the slots layer: the composed categories, the shared tools
    and their helpers."""
    return sorted(
        f
        for f in SLOTS_DIR.rglob("*.py")
        if f.name not in _SKIP
        and not f.name.startswith("__")
        and "__pycache__" not in f.parts
    )


class TestSlotFilesExist(unittest.TestCase):
    """Sanity floor (wiring/uniqueness checks live in test_dcc_invariants)."""

    def test_has_slot_files(self):
        files = _slot_files()
        self.assertGreater(
            len(files), 30, f"Expected 30+ slot files, found {len(files)}"
        )


class TestNoPymelImports(unittest.TestCase):
    """Slot modules must not import pymel — the package is migrated to cmds."""

    def test_no_pymel_imports(self):
        offenders = []
        for f in _slot_files():
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] == "pymel" for a in node.names):
                        offenders.append(f.name)
                        break
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] == "pymel":
                        offenders.append(f.name)
                        break
        self.assertEqual(offenders, [], f"Slot files re-introduced pymel: {offenders}")


# Edit's Delete History moved to mayatk (``NodeUtils.delete_history_in_scope``); its
# AST guard against ``ls -dag -exactType`` lives in mayatk's test_node_utils.py
# (TestDeleteHistoryInScope), the behaviour in tentacle's test_edit.py.


if __name__ == "__main__":
    unittest.main()
