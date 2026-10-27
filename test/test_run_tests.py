#!/usr/bin/python
# coding=utf-8
"""Tests for tentacle's test runner (``test/run_tests.py``): pointed runs.

A run can name its modules (``test/`` or ``test/slots/``) and narrow them with
``-k``, in the plain run and in the fresh-Maya ``--in-maya`` dispatcher alike; a
name no module answers to is refused; every status mark is written once. No Maya
is launched here: the dispatcher is checked as the source it generates.
"""

import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "_tentacle_run_tests_under_test", TEST_DIR / "run_tests.py"
)
rt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rt)


def _ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _ids(item)
        else:
            yield item.id()


class TestPointedRuns(unittest.TestCase):
    def setUp(self):
        self._path = list(sys.path)
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), self._path))

    def test_names_resolve_bare_prefixed_or_in_slots_and_unknowns_are_named(self):
        slot = next((TEST_DIR / "slots").glob("test_*.py")).stem
        stems, unknown = rt.TestRunner.resolve_modules(
            TEST_DIR, ["package", "test_ui_integrity.py", slot, "no_such_module"]
        )
        self.assertEqual(stems, ["test_package", "test_ui_integrity", slot])
        self.assertEqual(unknown, ["no_such_module"])

    def test_a_named_module_runs_alone_and_k_narrows_it(self):
        runner = rt.TestRunner(TEST_DIR, verbosity=0, modules=["run_tests"], patterns=["unknowns"])
        ids = list(_ids(runner.discover_tests()))
        self.assertEqual(
            [i.rsplit(".", 1)[-1] for i in ids],
            ["test_names_resolve_bare_prefixed_or_in_slots_and_unknowns_are_named"],
        )

    def test_the_in_maya_dispatcher_carries_the_selection(self):
        source = rt._build_in_maya_dispatcher(
            TEST_DIR, TEST_DIR.parent.parent, TEST_DIR / "temp_tests" / "x.txt", 1,
            modules=["test_lighting"], patterns=["light"],
        )
        compile(source, "<dispatcher>", "exec")  # it is valid Python
        self.assertIn("_modules = ['test_lighting']", source)
        self.assertIn("_patterns = ['*light*']", source)

    def test_an_unknown_module_exits_two_before_any_run(self):
        argv = ["run_tests.py", "definitely_not_a_module"]
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(rt.TestRunner, "run") as ran, \
                mock.patch.object(sys, "stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as exited:
                rt.main()
        self.assertEqual(exited.exception.code, 2)
        ran.assert_not_called()

    def test_each_status_mark_is_written_once(self):
        """The runner used to add its own mark after TextTestResult's: two tests
        printed ``....``. Driven through the runner's own run() on two of this
        file's other tests (never this one -- no recursion)."""
        runner = rt.TestRunner(
            TEST_DIR, verbosity=1, modules=["run_tests"],
            patterns=["names_resolve", "dispatcher_carries"],
        )
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", io.StringIO()):
            result = runner.run()
        self.assertEqual(result.tests_run, 2)
        self.assertIn("\n..\n", out.getvalue().replace("\r", ""))


class TestBlenderChecks(unittest.TestCase):
    """``--in-blender`` runs each Blender check whose usage line runs it in a
    background Blender; one that drives a real window is run by hand."""

    def _dir(self, files):
        import shutil
        import tempfile

        root = Path(tempfile.mkdtemp(prefix="tcl_blender_checks_"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for name, usage in files.items():
            (root / name).write_text(f'"""Check.\n\n    {usage}\n"""\n', encoding="utf-8")
        return root

    def test_only_checks_run_in_a_background_blender_are_discovered(self):
        root = self._dir({
            "edit_slot_check.py": "blender --background --factory-startup --python edit_slot_check.py",
            "gui_drag_check.py": "blender --python gui_drag_check.py",
            "_input.py": "blender --background --python _input.py",
        })
        self.assertEqual([p.name for p in rt.headless_blender_checks(root)], ["edit_slot_check.py"])

    def test_a_named_check_answers_with_or_without_its_suffix(self):
        root = self._dir({
            "edit_slot_check.py": "blender --background --python edit_slot_check.py",
            "uv_slot_check.py": "blender --background --python uv_slot_check.py",
        })
        for name in ("uv_slot", "uv_slot_check", "uv_slot_check.py"):
            self.assertEqual([p.name for p in rt.headless_blender_checks(root, [name])], ["uv_slot_check.py"])

    def test_the_real_headless_checks_are_found(self):
        found = rt.headless_blender_checks(TEST_DIR / "blender")
        self.assertIn("edit_slot_check.py", [p.name for p in found])
        self.assertNotIn("native_drag_check.py", [p.name for p in found])


if __name__ == "__main__":
    unittest.main()
