#!/usr/bin/python
# coding=utf-8
"""Tests for tentacle package metadata, imports, and top-level API."""
import sys
import unittest
from pathlib import Path

# Ensure the package root is importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestPackageMetadata(unittest.TestCase):
    """Verify package-level attributes and registry."""

    def test_version_format(self):
        """__version__ must be a dotted triple (major.minor.patch)."""
        import tentacle

        parts = tentacle.__version__.split(".")
        self.assertEqual(len(parts), 3, f"Expected 3 version parts, got {parts}")
        for p in parts:
            self.assertTrue(p.isdigit(), f"Non-numeric version component: {p}")

    def test_default_include_keys_exist(self):
        """Every module path in DEFAULT_INCLUDE must resolve to a real .py file."""
        import tentacle

        pkg_dir = Path(tentacle.__file__).parent
        for mod_path in tentacle.DEFAULT_INCLUDE:
            # e.g. "tcl_maya" -> tentacle/tcl_maya.py
            # e.g. "slots.maya._slots_maya" -> tentacle/slots/maya/_slots_maya.py
            rel = mod_path.replace(".", "/") + ".py"
            full = pkg_dir / rel
            self.assertTrue(full.exists(), f"DEFAULT_INCLUDE module missing: {full}")

    def test_default_include_values_are_class_names(self):
        """DEFAULT_INCLUDE values must be PascalCase identifiers."""
        import tentacle

        for mod, cls_name in tentacle.DEFAULT_INCLUDE.items():
            self.assertTrue(
                cls_name[0].isupper(),
                f"Class name '{cls_name}' for module '{mod}' should be PascalCase",
            )
            self.assertTrue(
                cls_name.isidentifier(),
                f"Class name '{cls_name}' is not a valid Python identifier",
            )


class TestGreeting(unittest.TestCase):
    """Verify the greeting() helper."""

    def test_greeting_contains_version(self):
        import tentacle

        result = tentacle.greeting("Running {modver} on {pyver}", outputToConsole=False)
        self.assertIn(tentacle.__version__, result)

    def test_greeting_time_of_day(self):
        import tentacle

        result = tentacle.greeting("Good {hr}!", outputToConsole=False)
        self.assertIn(result, ["Good morning!", "Good afternoon!", "Good evening!"])

    def test_greeting_python_version(self):
        import tentacle

        result = tentacle.greeting("{pyver}", outputToConsole=False)
        expected = (
            f"python v{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
