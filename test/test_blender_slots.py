#!/usr/bin/python
# coding=utf-8
"""Blender-specific structural guards: the ``tcl_blender`` add-on entry point parses and
carries its add-on surface. (Its Qt host, keymap bridge and click tracer are blendertk's, and
tested there.)

The slots layer's own invariants are host-agnostic (``test_dcc_invariants.py``): one
composed Slots class per category for both hosts, no per-host slot package. The
Blender behavior a slot reaches through ``self.tk`` (viewport tools and their modes,
the window's view layer) is blendertk's, and tested there. AST-based where it can
be: no Blender runtime needed.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"


class TestBlenderPlumbingParses(unittest.TestCase):
    """The consolidated Blender entry point parses cleanly (deferred bpy import keeps it valid
    outside a Blender runtime; qtpy/uitk load only after ``_bootstrap_paths`` runs)."""

    def test_launcher_parses(self):
        path = PKG / "tcl_blender.py"
        self.assertTrue(path.exists(), "Missing tcl_blender.py")
        ast.parse(path.read_text(encoding="utf-8"))  # raises SyntaxError on failure

    def test_addon_surface_present(self):
        """The add-on/launcher surface folded in from blender_host/blender_addon is intact."""
        source = (PKG / "tcl_blender.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertTrue(
            {"launch", "register", "unregister", "ensure_qapp", "start_event_pump", "diagnose"}
            <= funcs,
            f"Consolidated entry point missing host/add-on functions: have {sorted(funcs)}",
        )
        self.assertTrue(
            any(isinstance(n, ast.Assign)
                and any(getattr(t, "id", None) == "bl_info" for t in n.targets)
                for n in tree.body),
            "tcl_blender.py must define bl_info (add-on surface)",
        )


if __name__ == "__main__":
    unittest.main()
