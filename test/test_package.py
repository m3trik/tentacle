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


class TestExtappsRegistration(unittest.TestCase):
    """tcl_maya's hardcoded extapps registrations must match extapps' entry points.

    tcl_maya manually registers each extapps app (module + entry) so the
    handler can install-on-demand before auto-discovery would see it. That
    manual registration *wins* over auto-discovery, so a wrong module path
    here silently shadows the correct one and breaks launch — which is what
    happened when ``metashape_workflow`` moved into ``extapps.photogrammetry``
    but tcl_maya still derived ``extapps.metashape_workflow`` from the name.

    Pins the table to extapps' entry-point metadata (the single source of
    truth). Skips when extapps isn't importable in the test environment.
    """

    @staticmethod
    def _registered_modules():
        """AST-extract ``{name: module}`` from tcl_maya's register() table.

        Read statically because tcl_maya imports ``maya`` at module top and
        can't be imported outside a Maya interpreter.
        """
        import ast
        import tentacle

        src = (Path(tentacle.__file__).parent / "tcl_maya.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple):
                continue
            # The loop body must register external apps.
            if not any(
                isinstance(c, ast.Call)
                and isinstance(c.func, ast.Attribute)
                and c.func.attr == "register"
                for c in ast.walk(node)
            ):
                continue
            mapping = {}
            for elt in node.iter.elts:
                if (
                    isinstance(elt, ast.Tuple)
                    and len(elt.elts) == 3
                    and all(isinstance(e, ast.Constant) for e in elt.elts)
                ):
                    name, module, _entry = (e.value for e in elt.elts)
                    mapping[name] = module
            if mapping:
                return mapping
        return {}

    def test_registered_modules_match_extapps_entry_points(self):
        try:
            from importlib.metadata import entry_points

            eps = {
                ep.name: ep.module
                for ep in entry_points(group="uitk.external_apps.in_process")
            }
        except Exception:
            eps = {}
        if not eps:
            self.skipTest("extapps entry points not available in this environment")

        registered = self._registered_modules()
        self.assertTrue(
            registered, "no extapps registration table found in tcl_maya.py"
        )
        for name, module in registered.items():
            if name in eps:
                self.assertEqual(
                    module,
                    eps[name],
                    f"tcl_maya registers {name!r} as module {module!r} but extapps "
                    f"declares {eps[name]!r} — the manual registration would shadow "
                    f"auto-discovery with a wrong path and break launch.",
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
