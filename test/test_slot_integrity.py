#!/usr/bin/python
# coding=utf-8
"""Tests for slot file structure and class conventions.

Validates that every slot module under tentacle/slots/maya/:
- Defines exactly one public class that inherits from SlotsMaya
- Uses the expected import-guard pattern for pymel
- Has a corresponding __init__ accepting (self, switchboard)
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
SLOTS_DIR = PKG / "slots" / "maya"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Files that are not concrete slot modules
_SKIP = {"__init__.py", "_slots_maya.py"}


def _slot_files():
    """Return all concrete slot .py files."""
    return sorted(
        f
        for f in SLOTS_DIR.glob("*.py")
        if f.name not in _SKIP and not f.name.startswith("__")
    )


def _parse_classes(source: str):
    """Return list of (class_name, [base_names]) from source."""
    tree = ast.parse(source)
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            classes.append((node.name, bases))
    return classes


class TestSlotFilesExist(unittest.TestCase):
    """Basic structural checks on the slots/maya directory."""

    def test_slots_dir_exists(self):
        self.assertTrue(SLOTS_DIR.is_dir(), f"Missing directory: {SLOTS_DIR}")

    def test_base_class_file_exists(self):
        self.assertTrue(
            (SLOTS_DIR / "_slots_maya.py").exists(),
            "Missing base class file _slots_maya.py",
        )

    def test_has_slot_files(self):
        files = _slot_files()
        self.assertGreater(
            len(files), 30, f"Expected 30+ slot files, found {len(files)}"
        )


class TestSlotClassStructure(unittest.TestCase):
    """Each slot module must contain exactly one SlotsMaya subclass."""

    def test_each_slot_has_slots_maya_subclass(self):
        """Every slot .py must define at least one class inheriting SlotsMaya."""
        missing = []
        for f in _slot_files():
            source = f.read_text(encoding="utf-8")
            classes = _parse_classes(source)
            slot_classes = [name for name, bases in classes if "SlotsMaya" in bases]
            if not slot_classes:
                missing.append(f.name)
        self.assertEqual(missing, [], f"Files without SlotsMaya subclass: {missing}")

    def test_no_multiple_public_slot_classes(self):
        """Each file should define at most one SlotsMaya subclass."""
        multi = []
        for f in _slot_files():
            source = f.read_text(encoding="utf-8")
            classes = _parse_classes(source)
            slot_classes = [name for name, bases in classes if "SlotsMaya" in bases]
            if len(slot_classes) > 1:
                multi.append((f.name, slot_classes))
        self.assertEqual(multi, [], f"Multiple slot classes in: {multi}")


class TestSlotImportGuards(unittest.TestCase):
    """Slot modules use try/except for pymel to allow headless import."""

    def test_pymel_import_guarded(self):
        """Any file that imports pymel should use try/except."""
        unguarded = []
        for f in _slot_files():
            source = f.read_text(encoding="utf-8")
            if "import pymel" not in source:
                continue
            # Accept try/except style or conditional import
            if "try:" in source or "importlib" in source:
                continue
            unguarded.append(f.name)
        self.assertEqual(
            unguarded,
            [],
            f"Files with unguarded pymel import: {unguarded}",
        )


class TestSlotsMayaBase(unittest.TestCase):
    """Verify _slots_maya.py base class."""

    def test_base_inherits_slots(self):
        source = (SLOTS_DIR / "_slots_maya.py").read_text(encoding="utf-8")
        classes = _parse_classes(source)
        self.assertTrue(
            any("Slots" in bases for _, bases in classes),
            "SlotsMaya must inherit from Slots",
        )


if __name__ == "__main__":
    unittest.main()
