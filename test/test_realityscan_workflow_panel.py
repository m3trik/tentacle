#!/usr/bin/env python
# coding=utf-8
"""Tests for the standalone RealityCapture Workflow panel (``slots/tools/realityscan_workflow.py``).

UI smoke tests cover the build-time wiring and the run dispatch (no engine
needed); the engines, runners and headless runs are extapps' own tests.

Run::

    python tentacle/test/run_tests.py realityscan_workflow_panel
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct run loads no conftest: the panels read and write QSettings, so the
# sandbox is activated before the first one. Idempotent.
TestSandbox.activate()


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestRealityScanPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as r

        self.ui = r.RealityScanWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from tentacle.slots.tools._photogrammetry import realityscan_parameters as P

        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_run_mode_combo_has_full_pipeline(self) -> None:
        cmb = self.ui.cmb000
        self.assertGreaterEqual(cmb.count(), 1)
        self.assertGreaterEqual(
            cmb.findText("Full pipeline"), 0, "Full pipeline mode missing"
        )

    def test_prep_preview_mode_maps_to_curate_preview(self) -> None:
        """Parity with the Metashape panel: the shared Prep-preview run mode
        emits --curate-preview (RC's runner executes in the panel's Python, so
        the dry-run just works) and shows only the pre-processing knobs."""
        from tentacle.slots.tools._photogrammetry import realityscan_parameters as P
        from tentacle.slots.tools._photogrammetry.shared_parameters import PREPROCESSING_KEYS

        cmb = self.ui.cmb000
        idx = cmb.findText("Prep preview")
        self.assertGreaterEqual(idx, 0, "Prep preview mode missing")
        cmb.setCurrentIndex(idx)
        self.assertEqual(self.slots._mode_argv(), ["--curate-preview"])
        self.assertEqual(
            P.Parameters.referenced_keys("prep_preview"),
            set(P.PARAMS) & PREPROCESSING_KEYS,
        )

    def test_semantic_preset_mode_uses_realityscan_store(self) -> None:
        listed = set(self.slots._preset_mgr.list())
        self.assertTrue(
            {"preview", "high", "specular_metal"} <= listed,
            f"RC presets missing; got {sorted(listed)}",
        )

    def test_builtin_preset_loads_into_param_widgets(self) -> None:
        from uitk.bridge.spec import KindFactory

        self.slots._preset_mgr.load("high")
        self.assertEqual(
            KindFactory.read_value(self.slots._param_widgets["quality"]), "max"
        )

    def test_missing_exe_reports_instead_of_dispatching(self) -> None:
        self.slots.bridge.is_available = lambda: False
        captured = {}
        self.slots.bridge.start = lambda *a, **k: captured.setdefault("ran", True)
        self.slots._name_edit.setText("p")
        self.ui.b000.click()
        self.assertNotIn("ran", captured, "must not dispatch when exe is missing")


class TestRealityScanPanelDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as r

        self.tmp = tempfile.mkdtemp(prefix="rc_dispatch_")
        self.frames = os.path.join(self.tmp, "frames")
        os.makedirs(self.frames)
        self.ui = r.RealityScanWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.captured: dict = {}
        self.slots.bridge.is_available = lambda: True
        self.slots.bridge.is_running = lambda: False

        def fake_start(argv, on_line=None, on_done=None, cwd=None):
            self.captured["argv"] = list(argv)

        self.slots.bridge.start = fake_start

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_argv_includes_name_frames_output_and_preset(self) -> None:
        self.slots._name_edit.setText("proj")
        self.slots._frames_edit.setText(self.frames)
        self.slots._output_dir_edit.setText(self.tmp)
        self.slots._preset_mgr.load("high")  # quality=max flows in
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch to the runner")
        self.assertEqual(argv[argv.index("--name") + 1], "proj")
        self.assertEqual(argv[argv.index("--frames-dir") + 1], self.frames)
        self.assertEqual(argv[argv.index("--output-root") + 1], self.tmp)
        self.assertEqual(argv[argv.index("--quality") + 1], "max")


if __name__ == "__main__":
    unittest.main()
