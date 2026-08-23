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


class TestSuiteIsolation(unittest.TestCase):
    """The suite must not be running against the developer's live user state.

    tentacle constructs real marking menus, and ``MarkingMenu`` **persists its bindings on
    construction** — so an unisolated run rewrites the user's live activation key and chord table
    in the shared ``QSettings`` store. That went unnoticed for a long time precisely because it
    breaks nothing here: no test fails, the user's hotkey just resets in a different app hours
    later (reported 2026-08-07 as "my set hotkey keeps being reset"; the give-away was
    ``marking_menu_bindings_dbg*`` litter in the live store).

    This lives in the structural suite because it has to run under **every** entry point — pytest,
    ``run_tests.py``, and the ``--in-maya`` dispatcher — which share no setup code and each have to
    activate the sandbox themselves. The original fix wired up only two of the three; this fails in
    whichever one ever forgets.
    """

    def test_live_settings_store_is_sandboxed(self):
        from uitk.testing import TestSandbox

        self.assertTrue(
            TestSandbox.is_active(),
            "The live QSettings store is NOT sandboxed — this run is writing to the "
            "developer's real settings. Whichever entry point started it must call "
            "uitk.testing.TestSandbox.activate() before any test module is imported.",
        )

    def test_qsettings_writes_land_in_the_sandbox(self):
        """Prove the redirect actually diverts a write, not just that a flag is set."""
        from qtpy import QtCore

        settings = QtCore.QSettings("uitk", "shared")  # the production (org, app)
        path = settings.fileName()
        self.assertNotIn(
            "Registry",
            path,
            f"QSettings still resolves to the native registry store ({path!r}).",
        )
        self.assertIn("uitk_test_qsettings", path.replace("\\", "/"))


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
    """External apps are auto-discovered from extapps' entry points — the
    hosts must carry NO hand-maintained registration table.

    The old per-app ``(name, module, entry)`` loop in tcl_maya / tcl_blender
    drifted from extapps' entry points (and from each other) every time an
    app was added or moved. The refactor deleted it in favour of
    ``ExternalAppHandler.discover()`` reading the entry points directly, with
    ``install_spec`` derived from the distribution. These tests guard that
    contract: (1) no host reintroduces a manual table, and (2) the entry
    points (the single source of truth) declare the expected apps and the
    per-host visibility gates the hosts rely on.
    """

    @staticmethod
    def _registered_modules(filename):
        """AST-extract ``{name: module}`` from any external-app ``register()``
        loop in *filename* (a host module). Read statically because the hosts
        import ``maya`` / ``bpy`` at module top and can't import off-DCC.

        Returns ``{}`` when there's no such table — the post-refactor state.
        """
        import ast
        import tentacle

        src = (Path(tentacle.__file__).parent / filename).read_text(
            encoding="utf-8"
        )
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple):
                continue
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

    def test_hosts_have_no_manual_registration_table(self):
        """Regression guard: neither host may hand-enumerate extapps apps."""
        for filename in ("tcl_maya.py", "tcl_blender.py"):
            self.assertEqual(
                self._registered_modules(filename),
                {},
                f"{filename} reintroduced a hardcoded external-app register() "
                f"table — apps must self-describe via extapps entry points and "
                f"be picked up by ExternalAppHandler.discover() instead.",
            )

    def test_entry_points_declare_apps_and_maya_gates(self):
        """extapps' entry points are the SSoT — they must carry the core apps
        and gate Substance/Marmoset out of Maya (native bridges supersede)."""
        try:
            from importlib.metadata import entry_points

            eps = list(entry_points(group="uitk.external_apps.in_process"))
        except Exception:
            eps = []
        if not eps:
            self.skipTest("extapps entry points not available in this environment")

        names = {ep.name for ep in eps}
        for expected in ("compositor", "metashape_workflow", "mesh_convert",
                         "substance_workflow", "marmoset_workflow"):
            self.assertIn(expected, names, f"extapps no longer declares {expected!r}")

        extras = {ep.name: set(ep.extras or ()) for ep in eps}
        for gated in ("substance_workflow", "marmoset_workflow"):
            self.assertIn(
                "hide_maya", extras.get(gated, set()),
                f"{gated} must keep the 'hide_maya' gate so Maya (which ships a "
                f"native bridge) doesn't surface the redundant external panel.",
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

    def test_plain_import_prints_nothing(self):
        """``import tentacle`` must be silent — root CLAUDE.md: "Imports: no side effects."

        The banner belongs to the launch path (``Tcl.launch``), not to every consumer that
        merely imports the package (test collectors, API-registry generators, tooling).
        """
        import os
        import subprocess

        # Under the --in-maya dispatcher `sys.executable` is the HOST binary
        # (maya.exe), not an interpreter: `maya.exe -c "import tentacle"` is not
        # a valid invocation and dies in native code -- rc 1 with an
        # unsymbolized stack trace and no Python traceback, which reads as this
        # assertion failing rather than as the spawn being nonsense. mayapy ships
        # beside maya.exe, so the check keeps its coverage under every entry
        # point instead of skipping the one where a stray print is most likely.
        exe = Path(sys.executable)
        if not exe.stem.lower().startswith("python"):
            mayapy = exe.with_name("mayapy.exe" if os.name == "nt" else "mayapy")
            if not mayapy.exists():
                self.skipTest(f"no standalone interpreter beside {exe.name}")
            exe = mayapy

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(sys.path[1:])
        proc = subprocess.run(
            [str(exe), "-c", "import tentacle"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout.strip(),
            "",
            "'import tentacle' wrote to stdout; imports must have no side effects.",
        )

    def test_greeting_python_version(self):
        import tentacle

        result = tentacle.greeting("{pyver}", outputToConsole=False)
        expected = (
            f"python v{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
