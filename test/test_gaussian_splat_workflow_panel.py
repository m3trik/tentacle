#!/usr/bin/env python
# coding=utf-8
"""Tests for the standalone Brush Splat Workflow panel (``slots/tools/gaussian_splat_workflow.py``).

UI smoke tests cover the build-time wiring and the run dispatch (no engine
needed); the engines, runners and headless runs are extapps' own tests.

Run::

    python tentacle/test/run_tests.py gaussian_splat_workflow_panel
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct run loads no conftest: the panels read and write QSettings, so the
# sandbox is activated before the first one. Idempotent.
TestSandbox.activate()


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestParametersReferencedKeys(unittest.TestCase):
    def _P(self):
        from tentacle.slots.tools._photogrammetry import gaussian_splat_parameters as P

        return P

    def test_train_only_hides_publish_keys(self) -> None:
        P = self._P()
        keys = P.Parameters.referenced_keys("")
        for train in ("total_steps", "max_resolution", "max_splats", "sh_degree"):
            self.assertIn(train, keys)
        for pub in ("publish_targets", "web_format", "spz_version"):
            self.assertNotIn(pub, keys, f"{pub} should be hidden in Train only")

    def test_publish_mode_shows_publish_keys(self) -> None:
        P = self._P()
        keys = P.Parameters.referenced_keys("publish")
        self.assertEqual(keys, set(P.PARAMS))

    def test_training_values_render_to_cli_flags(self) -> None:
        P = self._P()
        argv = P.Parameters.to_argv(
            {"total_steps": 50000, "sh_degree": 2, "web_format": "sog"}
        )
        self.assertEqual(argv[argv.index("--total-steps") + 1], "50000")
        self.assertEqual(argv[argv.index("--sh-degree") + 1], "2")
        self.assertEqual(argv[argv.index("--web-format") + 1], "sog")


class TestBrushPanelLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as g

        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_param_widgets_built_for_every_spec(self) -> None:
        from tentacle.slots.tools._photogrammetry import gaussian_splat_parameters as P

        for key in P.PARAMS:
            self.assertIn(key, self.slots._param_widgets, f"no widget for {key}")

    def test_run_mode_combo_has_both_modes(self) -> None:
        cmb = self.ui.cmb000
        self.assertGreaterEqual(cmb.findText("Train only"), 0)
        self.assertGreaterEqual(cmb.findText("Train + Publish"), 0)

    def test_semantic_preset_mode_uses_gsplat_store(self) -> None:
        listed = set(self.slots._preset_mgr.list())
        self.assertTrue(
            {"preview", "high"} <= listed,
            f"gsplat presets missing; got {sorted(listed)}",
        )
        # No shipped 'default' preset — the Reset to Defaults button covers it.
        self.assertNotIn("default", listed)

    def test_high_preset_loads_into_param_widgets(self) -> None:
        from uitk.bridge.spec import KindFactory

        self.slots._preset_mgr.load("high")
        self.assertEqual(
            KindFactory.read_value(self.slots._param_widgets["total_steps"]), 50000
        )


class TestBrushPanelDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as g

        self.tmp = tempfile.mkdtemp(prefix="brush_dispatch_")
        self.colmap = os.path.join(self.tmp, "ds")
        os.makedirs(self.colmap)
        self.ui = g.GaussianSplatWorkflowUI()
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

    def _set_inputs(self) -> None:
        self.slots._name_edit.setText("splat")
        self.slots._colmap_edit.setText(self.colmap)
        self.slots._output_dir_edit.setText(self.tmp)

    def test_train_only_argv_has_colmap_no_publish(self) -> None:
        self._set_inputs()
        self.ui.cmb000.setCurrentIndex(self.ui.cmb000.findText("Train only"))
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch")
        self.assertEqual(argv[argv.index("--colmap-dir") + 1], self.colmap)
        self.assertEqual(argv[argv.index("--name") + 1], "splat")
        self.assertNotIn("--publish", argv)

    def test_train_plus_publish_adds_publish_flag(self) -> None:
        self._set_inputs()
        self.ui.cmb000.setCurrentIndex(self.ui.cmb000.findText("Train + Publish"))
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch")
        self.assertIn("--publish", argv)

    def test_missing_colmap_dir_does_not_dispatch(self) -> None:
        self.slots._name_edit.setText("splat")
        self.slots._colmap_edit.setText(os.path.join(self.tmp, "nope"))
        self.slots._output_dir_edit.setText(self.tmp)
        self.ui.b000.click()
        self.assertNotIn("argv", self.captured, "must not dispatch with a bad dir")


class TestBrushViewerActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as g
        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots)
        # bridge.exe is a read-only property over find_brush_exe(); patch that so
        # the panel sees a known install without a real Brush on the machine.
        p = mock.patch(
            "extapps.photogrammetry.gaussian_splat_workflow."
            "_gaussian_splat_runner.GaussianSplatWorkflow.find_brush_exe",
            return_value="/fake/brush.exe",
        )
        self.find_brush = p.start()
        self.addCleanup(p.stop)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    # ---- header wiring -----------------------------------------------------
    def test_header_has_viewer_actions(self) -> None:
        menu = self.ui.header.menu
        self.assertEqual(menu.btn_open_brush.text(), "Open Brush Viewer")
        self.assertEqual(menu.btn_view_result.text(), "View Result in Brush")

    # ---- open empty viewer -------------------------------------------------
    def test_open_brush_viewer_launches_empty(self) -> None:
        with mock.patch("pythontk.AppLauncher.launch", return_value=object()) as L:
            self.slots.open_brush_viewer()
        L.assert_called_once()
        self.assertEqual(L.call_args.args[0], "/fake/brush.exe")
        self.assertEqual(L.call_args.kwargs["args"], [])

    def test_launch_skipped_when_brush_missing(self) -> None:
        self.find_brush.return_value = None
        with mock.patch("pythontk.AppLauncher.launch") as L:
            self.slots.open_brush_viewer()
        L.assert_not_called()

    # ---- open the result ---------------------------------------------------
    def test_view_result_passes_ply_and_with_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            old = os.path.join(d, "splat_1000.ply")
            new = os.path.join(d, "splat_30000.ply")
            for p in (old, new):
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("ply\n")
            # Make `new` unambiguously newest.
            os.utime(old, (time.time() - 100, time.time() - 100))
            self.slots._last_output_dir = d

            with mock.patch(
                "pythontk.AppLauncher.launch", return_value=object()
            ) as L:
                self.slots.open_result_in_brush()
            L.assert_called_once()
            self.assertEqual(L.call_args.args[0], "/fake/brush.exe")
            self.assertEqual(L.call_args.kwargs["args"], [new, "--with-viewer"])

    def test_view_result_no_result_does_not_launch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.slots._last_output_dir = d  # empty dir, no .ply
            with mock.patch("pythontk.AppLauncher.launch") as L:
                self.slots.open_result_in_brush()
            L.assert_not_called()

    def test_latest_result_picks_newest_ply_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "publish")
            os.makedirs(sub)
            a = os.path.join(d, "raw.ply")
            b = os.path.join(sub, "clean.ply")
            for p in (a, b):
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("ply\n")
            os.utime(a, (time.time() - 100, time.time() - 100))
            self.slots._last_output_dir = d
            self.assertEqual(self.slots._latest_result_splat(), b)


class TestBrushInstallAction(unittest.TestCase):
    """Panel wiring: the header action exists and dispatches correctly."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as g
        self.ui = g.GaussianSplatWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_header_has_download_brush_button(self) -> None:
        btn = self.ui.header.menu.btn_install_brush
        self.assertIsNotNone(btn)
        self.assertEqual(btn.text(), "Download Brush")

    def test_install_skipped_when_brush_available(self) -> None:
        self.slots.bridge.is_available = lambda: True
        with mock.patch.object(self.slots._install_runner, "start") as start:
            self.slots.install_brush()
        start.assert_not_called()

    def test_install_starts_runner_when_missing(self) -> None:
        self.slots.bridge.is_available = lambda: False
        self.slots._install_runner.is_running = lambda: False
        with mock.patch.object(self.slots._install_runner, "start") as start:
            self.slots.install_brush()
        start.assert_called_once()
        kw = start.call_args.kwargs
        # Bound methods compare equal (same instance + function) but aren't
        # identical objects, so use assertEqual.
        self.assertEqual(kw["on_line"], self.slots._append_output)
        self.assertEqual(kw["on_done"], self.slots._on_install_done)

    def test_cancel_run_cancels_inflight_install(self) -> None:
        self.slots._install_runner.is_running = lambda: True
        with mock.patch.object(self.slots._install_runner, "cancel") as cancel:
            self.slots.cancel_run()
        cancel.assert_called_once()

    def test_cancel_run_delegates_to_base_when_no_install(self) -> None:
        self.slots._install_runner.is_running = lambda: False
        self.slots.bridge.is_running = lambda: False
        with mock.patch.object(self.slots._install_runner, "cancel") as cancel:
            self.slots.cancel_run()  # falls through to base (training bridge)
        cancel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
