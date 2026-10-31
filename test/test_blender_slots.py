#!/usr/bin/python
# coding=utf-8
"""Blender-specific structural guards: the consolidated ``tcl_blender`` entry point
(Qt host + keymap bridge + launcher + add-on surface) and its opt-in click tracer.

The slots layer's own invariants are host-agnostic (``test_dcc_invariants.py``): one
composed Slots class per category for both hosts, no per-host slot package. The
Blender behavior a slot reaches through ``self.tk`` (viewport tools and their modes,
the window's view layer) is blendertk's, and tested there. AST-based where it can
be: no Blender runtime needed.
"""
import ast
import os
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"

try:  # the live module — needs a Qt binding + blendertk, absent in the [maya]-only CI env
    from tentacle import tcl_blender as _tcl_blender
except Exception:  # noqa: BLE001 - any import-time miss means "not testable here"
    _tcl_blender = None


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


@unittest.skipUnless(
    _tcl_blender is not None, "needs a Qt binding (qtpy/PySide6) + blendertk"
)
class ClickDebuggerSink(unittest.TestCase):
    """The opt-in click tracer must stay off, and must never sink into the user's HOME.

    ``_ClickDebugger`` is a support tool: a user is told to run ``enable_click_debug()``,
    reproduce a dead click, then share the log. Its original sink was
    ``~/tentacle_click_debug.log`` — an unmanaged, never-reclaimed file in the user's home
    (a 2.2 MB one was found there from a July capture). Managed scratch owns it now, with
    an env override for anyone who wants it somewhere specific.
    """

    def setUp(self):
        self.dbg = _tcl_blender._ClickDebugger
        self._cached = self.dbg._path
        self.dbg._path = None

    def tearDown(self):
        self.dbg._path = self._cached

    def test_tracer_is_off_until_enabled(self):
        """Nothing is opened, filtered or traced by import alone."""
        self.assertIsNone(
            self.dbg._fh, "the trace file handle must be opened by enable() only"
        )
        self.assertIsNone(
            self.dbg._filter, "the event filter must be installed by enable() only"
        )
        self.assertIsNone(
            self.dbg._slot_patch, "the slot trace must be installed by enable() only"
        )

    def test_a_write_while_disabled_creates_nothing(self):
        """``_write`` must be a silent no-op with no handle — not an implicit open."""
        target = Path(self.dbg.log_path())
        self.dbg._write("this line must never be recorded")
        self.assertFalse(target.exists(), f"a disabled tracer wrote to {target}")

    def test_sink_is_not_a_hardcoded_file_in_the_user_home(self):
        target = Path(self.dbg.log_path())
        home = Path(os.path.expanduser("~")).resolve()
        self.assertNotEqual(
            target.resolve().parent,
            home,
            f"the click trace sinks straight into the user's home directory ({target}); "
            "it must land in managed scratch (ptk.TempArtifacts) instead.",
        )

    def test_resolving_the_sink_creates_no_file(self):
        target = Path(self.dbg.log_path())
        self.assertFalse(
            target.exists(),
            "resolving the sink path must not create the file — only enable() opens it.",
        )

    def test_env_var_overrides_the_sink(self):
        """An explicit path wins, so a support capture can be steered anywhere."""
        wanted = ROOT / "test" / "temp_tests" / "click_debug_override.log"
        with mock.patch.dict(os.environ, {self.dbg.PATH_ENV: str(wanted)}):
            self.dbg._path = None
            self.assertEqual(Path(self.dbg.log_path()), wanted)


if __name__ == "__main__":
    unittest.main()
