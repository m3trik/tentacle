#!/usr/bin/env python
# coding=utf-8
"""Tests for the standalone Metashape Workflow panel (``slots/tools/metashape_workflow.py``).

UI smoke tests cover the build-time wiring and the run dispatch (no engine
needed); the engines, runners and headless runs are extapps' own tests.

Run::

    python tentacle/test/run_tests.py metashape_workflow_panel
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

from qtpy import QtCore
from qtpy.QtWidgets import QApplication

from uitk.testing import TestSandbox

# A direct run loads no conftest: the panels read and write QSettings, so the
# sandbox is activated before the first one. Idempotent.
TestSandbox.activate()


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication(sys.argv)


class TestMetashapeWorkflowLoads(unittest.TestCase):
    """Smoke checks against a freshly-built MetashapeWorkflow UI.

    The panel is a :class:`uitk.bridge.BridgeSlotsBase` subclass that drives the
    local ``metashape.exe`` headless (no in-process-SDK mock path) and uses the
    shared semantic preset store.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as m

        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)
        self.assertIsNotNone(self.slots, "Switchboard returned no slots instance")

    def tearDown(self) -> None:
        # Drop the window; QApplication persists for the next test.
        self.ui.deleteLater()
        self.app.processEvents()

    # ------------------------------------------------------------------

    def test_docs_link_logged_at_open(self) -> None:
        """The panel opens with its docs URL in the log pane as a clickable
        anchor (``BridgeSlotsBase.DOCS_URL`` -> ``_show_docs_link``), and the
        pane never navigates on click (uitk's handler routes web anchors to
        the browser instead)."""
        self.app.processEvents()
        url = self.slots.DOCS_URL
        self.assertTrue(url.endswith("docs/metashape_workflow.md"), url)
        html = self.ui.txt000.toHtml()
        self.assertIn(f'href="{url}"', html)
        self.assertIn(self.slots.DOCS_LABEL, self.ui.txt000.toPlainText())
        self.assertFalse(self.ui.txt000.openLinks())

    def test_ui_builds(self) -> None:
        self.assertEqual(self.ui.objectName(), "metashape_workflow")

        from uitk.widgets.header import Header
        from uitk.widgets.footer import Footer

        self.assertIsInstance(self.ui.header, Header)
        self.assertIsInstance(self.ui.footer, Footer)

        self.assertTrue(
            bool(self.ui.windowFlags() & QtCore.Qt.FramelessWindowHint),
            "FramelessWindowHint is not set — OS frame would be visible",
        )

    def test_run_modes_populate_template_combo(self) -> None:
        labels = [self.ui.cmb000.itemText(i) for i in range(self.ui.cmb000.count())]
        self.assertEqual(
            labels, ["Full pipeline", "Align only", "Refine only", "Prep preview"]
        )

    def test_param_widgets_built_for_every_spec(self) -> None:
        """Each semantic AttributeSpec gets a widget the panel can read/write."""
        from tentacle.slots.tools._photogrammetry import metashape_parameters as P

        for key in P.PARAMS:
            self.assertIn(
                key,
                self.slots._param_widgets,
                f"param widget {key!r} not built from PARAMS",
            )

    def test_param_visibility_is_dynamic_per_run_mode(self) -> None:
        """Switching the run mode shows/hides params per stage relevance —
        the panel is no longer static across modes.

        ``isHidden()`` (not ``isVisible()``) reflects the explicit setVisible
        flag independently of the unshown top-level window.
        """
        rows = self.slots._param_rows
        cmb = self.ui.cmb000

        # Set the mode explicitly each time — the combo's value persists across
        # panel instances (uitk widget-state), so we can't assume a default.
        # Full pipeline: every param row is shown.
        cmb.setCurrentIndex(cmb.findText("Full pipeline"))
        self.assertFalse(rows["depth_filter"].isHidden())
        self.assertFalse(rows["texture_size"].isHidden())

        # Align only: depth/mesh/texture + post-align knobs are irrelevant.
        cmb.setCurrentIndex(cmb.findText("Align only"))
        self.assertTrue(rows["depth_filter"].isHidden())
        self.assertTrue(rows["face_count"].isHidden())
        self.assertTrue(rows["texture_size"].isHidden())
        self.assertTrue(rows["skip_refine"].isHidden())
        self.assertTrue(rows["dedupe_cameras"].isHidden())
        self.assertTrue(rows["calibrate_colors"].isHidden())
        self.assertFalse(rows["align_downscale"].isHidden())  # align stage param
        self.assertFalse(rows["skip_curate"].isHidden())  # pre-align param

        # Refine only re-enables skip_refine (refine runs in this mode).
        cmb.setCurrentIndex(cmb.findText("Refine only"))
        self.assertFalse(rows["skip_refine"].isHidden())
        self.assertTrue(rows["depth_filter"].isHidden())

        # Prep preview (curation dry-run): only the pre-processing knobs apply.
        cmb.setCurrentIndex(cmb.findText("Prep preview"))
        self.assertFalse(rows["curate_hash_threshold"].isHidden())
        self.assertFalse(rows["preprocess_input"].isHidden())
        self.assertTrue(rows["align_downscale"].isHidden())
        self.assertTrue(rows["depth_filter"].isHidden())
        self.assertTrue(rows["min_component_size"].isHidden())

        # Back to Full pipeline: everything visible again.
        cmb.setCurrentIndex(cmb.findText("Full pipeline"))
        self.assertFalse(rows["depth_filter"].isHidden())
        self.assertFalse(rows["texture_size"].isHidden())

    def test_param_sections_have_dividers_that_track_mode(self) -> None:
        """Category dividers (uitk Separator) group the params, and a divider
        hides when its whole section is hidden for the active run mode."""
        seps = self.slots._section_separators
        self.assertIn("Input Pre-processing", seps)
        self.assertIn("Alignment", seps)
        self.assertIn("Mesh Cleanup", seps)
        cmb = self.ui.cmb000

        cmb.setCurrentIndex(cmb.findText("Full pipeline"))
        self.assertFalse(seps["Input Pre-processing"].isHidden())
        self.assertFalse(seps["Alignment"].isHidden())
        self.assertFalse(seps["Mesh Cleanup"].isHidden())

        # Align only: pre-processing + the alignment-quality levers apply (their
        # dividers stay), but Mesh Cleanup is a post-build stage that never runs
        # -> its whole section, and thus its divider, hides.
        cmb.setCurrentIndex(cmb.findText("Align only"))
        self.assertFalse(seps["Input Pre-processing"].isHidden())
        self.assertFalse(seps["Alignment"].isHidden())
        self.assertTrue(seps["Mesh Cleanup"].isHidden())

    def test_preprocessing_master_toggle_collapses_knobs(self) -> None:
        """The Input Pre-processing master toggle (preprocess_input) collapses
        its knobs when off — only the toggle + section divider stay — and
        restores them when on. (The section leads the panel, order of ops.)"""
        from uitk.bridge.spec import KindFactory

        rows = self.slots._param_rows
        seps = self.slots._section_separators
        cmb = self.ui.cmb000
        cmb.setCurrentIndex(cmb.findText("Full pipeline"))

        # On (default): the knobs are visible.
        self.assertFalse(rows["curate_hash_threshold"].isHidden())
        self.assertFalse(rows["equalize_strength"].isHidden())
        self.assertFalse(rows["preprocess_input"].isHidden())

        # Off: the knobs collapse, but the master toggle + its divider remain
        # (so the stage can be re-enabled).
        KindFactory.set_value(self.slots._param_widgets["preprocess_input"], False)
        self.assertTrue(rows["curate_hash_threshold"].isHidden())
        self.assertTrue(rows["skip_equalize"].isHidden())
        self.assertFalse(rows["preprocess_input"].isHidden())
        self.assertFalse(seps["Input Pre-processing"].isHidden())

        # On again: the knobs are restored.
        KindFactory.set_value(self.slots._param_widgets["preprocess_input"], True)
        self.assertFalse(rows["curate_hash_threshold"].isHidden())

    def test_semantic_preset_mode_active(self) -> None:
        # The panel uses the shared semantic PresetStore (not widget-state),
        # so the shipped built-in run-template shows in the preset combo.
        self.assertTrue(self.slots._semantic_presets)
        self.assertIsNotNone(self.slots._preset_mgr)
        self.assertIn("specular_metal", self.slots._preset_mgr.list())

    def test_builtin_preset_loads_into_param_widgets(self) -> None:
        from uitk.bridge.spec import KindFactory

        self.slots._preset_mgr.load("specular_metal")
        w = self.slots._param_widgets
        self.assertEqual(KindFactory.read_value(w["depth_filter"]), "moderate")
        self.assertEqual(KindFactory.read_value(w["face_count"]), "high")
        self.assertTrue(KindFactory.read_value(w["mask_background"]))

    def test_quality_presets_load_into_param_widgets(self) -> None:
        """preview / default / high each apply their explicit knobs to the
        widgets (the `quality` key is ignored — no widget for it)."""
        from uitk.bridge.spec import KindFactory

        w = self.slots._param_widgets

        self.slots._preset_mgr.load("preview")
        self.assertEqual(KindFactory.read_value(w["align_downscale"]), 4)
        self.assertEqual(KindFactory.read_value(w["face_count"]), "low")
        self.assertEqual(KindFactory.read_value(w["texture_size"]), "2048")

        self.slots._preset_mgr.load("high")
        self.assertEqual(KindFactory.read_value(w["align_downscale"]), 1)
        self.assertEqual(KindFactory.read_value(w["depth_downscale"]), 1)
        self.assertEqual(KindFactory.read_value(w["face_count"]), "high")

    def test_missing_exe_reports_instead_of_mocking(self) -> None:
        """No silent mock fallback: with no exe, b000 logs + leaves UI usable."""
        self.slots.bridge.is_available = lambda: False
        self.slots._name_edit.setText("proj")
        try:
            self.ui.b000.click()
        except Exception as exc:  # noqa: BLE001
            self.fail(f"b000 raised with missing exe: {type(exc).__name__}: {exc}")
        self.assertTrue(self.ui.b000.isEnabled())

    def test_run_empty_inputs_bails_gracefully(self) -> None:
        try:
            self.ui.b000.click()
        except Exception as exc:  # noqa: BLE001
            self.fail(f"b000 click raised: {type(exc).__name__}: {exc}")
        self.assertTrue(
            self.ui.b000.isEnabled(),
            "Run Workflow button left disabled after empty-input bail",
        )


class TestParametersReferencedKeys(unittest.TestCase):
    """``Parameters.referenced_keys(mode)`` is the relevance SSoT the panel +
    bridge base consume (the run-mode analogue of the DCC bridges' placeholder
    scan). Pinned at the data layer, not just via the integrated UI test."""

    def _P(self):
        from tentacle.slots.tools._photogrammetry import metashape_parameters as P

        return P

    def test_full_pipeline_returns_all_keys(self) -> None:
        P = self._P()
        self.assertEqual(P.Parameters.referenced_keys(""), set(P.PARAMS))

    def test_align_mode_drops_post_align_stage_knobs(self) -> None:
        P = self._P()
        keys = P.Parameters.referenced_keys("align")
        for hidden in (
            "depth_downscale",
            "depth_filter",
            "face_count",
            "texture_size",
            "dedupe_cameras",
            "skip_refine",
            "calibrate_colors",
            # mesh cleanup is a post-build stage -> full pipeline only
            "min_component_size",
            "smooth_strength",
            "close_holes",
        ):
            self.assertNotIn(hidden, keys, f"{hidden} should not apply in align-only")
        for shown in (
            "align_downscale",
            "skip_curate",
            "skip_equalize",
            "mask_background",
            "gate_mode",
            "save_project",
            # alignment-quality levers (pre-align triage + matchPhotos)
            "triage_quality",
            "generic_preselection",
            "keypoint_limit",
            "tiepoint_limit",
            # input pre-processing runs before align -> applies here too
            "curate_hash_threshold",
            "curate_sharpness_percentile",
            "curate_min_sharpness_frac",
            "keep_per_cluster",
            "equalize_strength",
            "equalize_reference",
        ):
            self.assertIn(shown, keys, f"{shown} should apply in align-only")

    def test_refine_mode_adds_skip_refine(self) -> None:
        P = self._P()
        keys = P.Parameters.referenced_keys("refine")
        self.assertIn("skip_refine", keys)
        self.assertNotIn("depth_filter", keys)

    def test_unknown_mode_falls_back_to_all_keys(self) -> None:
        P = self._P()
        self.assertEqual(P.Parameters.referenced_keys("bogus"), set(P.PARAMS))

    def test_preprocessing_values_render_to_cli_flags(self) -> None:
        P = self._P()
        argv = P.Parameters.to_argv(
            {
                "curate_hash_threshold": 0,  # 0 = disable dedup; must still emit
                "curate_sharpness_percentile": 12.5,
                "curate_min_sharpness_frac": 0.2,
                "keep_per_cluster": 2,
                "equalize_strength": 0.8,
                "equalize_reference": "global",
            }
        )
        self.assertEqual(argv[argv.index("--curate-hash-threshold") + 1], "0")
        self.assertEqual(argv[argv.index("--keep-per-cluster") + 1], "2")
        self.assertEqual(argv[argv.index("--equalize-reference") + 1], "global")
        self.assertIn("--curate-sharpness-percentile", argv)
        self.assertIn("--curate-min-sharpness-frac", argv)
        self.assertIn("--equalize-strength", argv)

    def test_alignment_and_cleanup_values_render_to_cli_flags(self) -> None:
        """The newly-exposed Metashape levers map to their run_combined flags:
        value flags always emit; generic_preselection is a BooleanOptionalAction
        pair (--flag / --no-flag), so unchecking it can override the on-by-default
        runner baseline."""
        P = self._P()
        argv = P.Parameters.to_argv(
            {
                "triage_quality": 0.3,
                "generic_preselection": True,
                "keypoint_limit": 60000,
                "tiepoint_limit": 20000,
                "min_component_size": 25000,
                "smooth_strength": 1,
                "close_holes": 10,
            }
        )
        self.assertEqual(argv[argv.index("--triage-quality") + 1], "0.3")
        self.assertEqual(argv[argv.index("--keypoint-limit") + 1], "60000")
        self.assertEqual(argv[argv.index("--tiepoint-limit") + 1], "20000")
        self.assertEqual(argv[argv.index("--clean-min-component") + 1], "25000")
        self.assertEqual(argv[argv.index("--smooth-strength") + 1], "1")
        self.assertEqual(argv[argv.index("--close-holes") + 1], "10")
        self.assertIn("--generic-preselection", argv)
        # bool flag: falsey emits the explicit --no- form (the runner default is
        # ON, so omission could never turn it off)
        off = P.Parameters.to_argv({"generic_preselection": False})
        self.assertNotIn("--generic-preselection", off)
        self.assertIn("--no-generic-preselection", off)

    def test_preprocessing_section_leads_param_order(self) -> None:
        """Input pre-processing runs first in the pipeline, so it leads the
        panel (order of operations): the master toggle is the first param and
        every pre-processing key precedes the engine-specific ones."""
        from tentacle.slots.tools._photogrammetry.shared_parameters import PREPROCESSING_KEYS

        P = self._P()
        keys = list(P.PARAMS)
        self.assertEqual(keys[0], "preprocess_input")
        last_pre = max(keys.index(k) for k in PREPROCESSING_KEYS)
        first_engine = min(
            keys.index(k) for k in ("align_downscale", "depth_filter", "face_count")
        )
        self.assertLess(
            last_pre, first_engine, "pre-processing must precede the engine params"
        )

    def test_preprocessing_master_off_skips_whole_stage(self) -> None:
        """preprocess_input=False renders the wholesale skip (both stages) and
        omits the now-moot knob flags; True renders the knobs and emits no
        skip (with the per-stage skips left off)."""
        P = self._P()
        off = P.Parameters.to_argv(
            {
                "preprocess_input": False,
                "curate_hash_threshold": 7,
                "equalize_strength": 0.9,
            }
        )
        self.assertIn("--skip-curate", off)
        self.assertIn("--skip-equalize", off)
        self.assertNotIn("--curate-hash-threshold", off)
        self.assertNotIn("--equalize-strength", off)
        on = P.Parameters.to_argv(
            {
                "preprocess_input": True,
                "curate_hash_threshold": 7,
                "equalize_strength": 0.9,
            }
        )
        self.assertEqual(on[on.index("--curate-hash-threshold") + 1], "7")
        self.assertNotIn("--skip-curate", on)


class TestMetashapePanelDispatch(unittest.TestCase):
    """b000 assembles ``run_combined`` argv from the inputs + active preset +
    run mode and hands it to the runner — without launching a real process."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as m

        self.tmp = tempfile.mkdtemp(prefix="mw_dispatch_")
        self.frames = os.path.join(self.tmp, "frames")
        os.makedirs(self.frames)
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

        # Capture the dispatched argv; never launch a real metashape.exe.
        self.captured: dict = {}
        self.slots.bridge.is_available = lambda: True
        self.slots.bridge.is_running = lambda: False

        def fake_start(argv, on_line=None, on_done=None, cwd=None):
            self.captured["argv"] = list(argv)
            self.captured["cwd"] = cwd

        self.slots.bridge.start = fake_start

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _set_inputs(self, name: str = "proj") -> None:
        self.slots._name_edit.setText(name)
        self.slots._frames_edit.setText(self.frames)
        self.slots._output_dir_edit.setText(self.tmp)

    def test_argv_includes_name_frames_output(self) -> None:
        self._set_inputs()
        self.ui.b000.click()
        argv = self.captured.get("argv")
        self.assertIsNotNone(argv, "b000 did not dispatch to the runner")
        self.assertEqual(argv[argv.index("--name") + 1], "proj")
        self.assertEqual(argv[argv.index("--frames-dir") + 1], self.frames)
        self.assertEqual(argv[argv.index("--output-root") + 1], self.tmp)

    def test_launch_captures_output_dir_for_open_action(self) -> None:
        """b000 records <output-root>/<name> at launch so 'Open Output Folder'
        targets the run that actually ran, even if the fields change after."""
        self._set_inputs()
        self.ui.b000.click()
        self.assertEqual(self.slots._last_output_dir, os.path.join(self.tmp, "proj"))
        # Editing the name afterward must not move the captured path.
        self.slots._name_edit.setText("renamed")
        self.assertEqual(self.slots._last_output_dir, os.path.join(self.tmp, "proj"))

    def test_success_logs_clickable_output_link(self) -> None:
        """On success the completion message embeds a clickable ``action://open``
        link to the output dir (the log pane is a QTextBrowser with openLinks
        off + anchorClicked wired to the base's open handler), not plain text —
        so a click reveals the folder. The link round-trips back to the dir."""
        import re
        from unittest import mock as umock
        from urllib.parse import parse_qs, urlparse

        self._set_inputs()
        self.ui.b000.click()  # captures _last_output_dir at launch
        with umock.patch.object(self.slots.bridge.logger, "info") as info:
            self.slots._on_run_done(0)
        msg = info.call_args[0][0]
        match = re.search(r'href="(action://[^"]+)"', msg)
        self.assertIsNotNone(match, f"no action:// link in completion msg: {msg}")
        url = urlparse(match.group(1))
        self.assertEqual(url.netloc, "open")
        self.assertEqual(parse_qs(url.query)["path"][0], os.path.join(self.tmp, "proj"))

    def test_active_preset_values_flow_into_argv(self) -> None:
        self.slots._preset_mgr.load("specular_metal")
        self._set_inputs()
        self.ui.b000.click()
        argv = self.captured["argv"]
        self.assertEqual(argv[argv.index("--depth-filter") + 1], "moderate")
        self.assertEqual(argv[argv.index("--face-count") + 1], "high")
        self.assertIn("--use-masks", argv)  # mask_background -> store_true flag

    def test_align_only_mode_adds_stop_after(self) -> None:
        self._set_inputs()
        idx = self.ui.cmb000.findText("Align only")
        self.ui.cmb000.setCurrentIndex(idx)
        self.ui.b000.click()
        argv = self.captured["argv"]
        self.assertEqual(argv[argv.index("--stop-after") + 1], "align")

    def test_prep_preview_mode_adds_curate_preview(self) -> None:
        self._set_inputs()
        idx = self.ui.cmb000.findText("Prep preview")
        self.ui.cmb000.setCurrentIndex(idx)
        self.ui.b000.click()
        argv = self.captured["argv"]
        self.assertIn("--curate-preview", argv)
        self.assertNotIn("--stop-after", argv)

    def test_missing_frames_dir_does_not_dispatch(self) -> None:
        self.slots._name_edit.setText("proj")
        self.slots._frames_edit.setText(os.path.join(self.tmp, "does_not_exist"))
        self.ui.b000.click()
        self.assertNotIn("argv", self.captured)
        self.assertTrue(self.ui.b000.isEnabled())


class TestMetashapeVideoInput(unittest.TestCase):
    """A single Source browser handles both inputs: picking video clip(s)
    extracts them (in the panel's full Python — Metashape's bundled Python has
    no cv2) into one frames dir; picking a frame uses its containing folder."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as m

        self.tmp = tempfile.mkdtemp(prefix="mw_video_")
        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_source_browser_extracts_all_selected_clips(self) -> None:
        from unittest import mock as umock
        from extapps.photogrammetry import prep_stages

        v1 = os.path.join(self.tmp, "a.mp4")
        v2 = os.path.join(self.tmp, "b.mp4")
        for v in (v1, v2):
            open(v, "w").close()
        out = os.path.join(self.tmp, "frames")
        self.slots._frames_edit.setText(out)

        captured: dict = {}

        def fake_extract(videos, output_dir, **kw):
            captured["videos"] = list(videos)
            captured["out"] = output_dir
            return ["f1.jpg", "f2.jpg"]

        # The single '...' browser returns BOTH video clips -> extraction path.
        with (
            umock.patch.object(self.slots.sb, "file_dialog", lambda **kw: [v1, v2]),
            umock.patch.object(prep_stages.PrepStagesMixin, "extract_videos_to_dir", fake_extract),
        ):
            self.slots._pick_source()

        self.assertEqual(
            captured.get("videos"),
            [v1, v2],
            "both selected videos must reach the extractor",
        )
        self.assertEqual(captured.get("out"), out)

    def test_source_browser_uses_folder_of_a_picked_frame(self) -> None:
        from unittest import mock as umock

        frames_dir = os.path.join(self.tmp, "cap")
        os.makedirs(frames_dir)
        img = os.path.join(frames_dir, "0.jpg")
        open(img, "w").close()

        # The same browser returns a frame image -> use its containing folder,
        # no extraction.
        with umock.patch.object(self.slots.sb, "file_dialog", lambda **kw: [img]):
            self.slots._pick_source()

        self.assertEqual(self.slots._frames_edit.text(), frames_dir)


class TestPanelPresetResetsUnnamedKeys(unittest.TestCase):
    """Panel presets apply as defaults + overlay (CLI semantics): keys a
    preset does not name reset to registry defaults instead of keeping
    session-persisted leftovers from a previously applied preset."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _ensure_app()

    def setUp(self) -> None:
        from tentacle import tcl_standalone as m

        self.ui = m.MetashapeWorkflowUI()
        self.slots = self.ui.sb.get_slots_instance(self.ui)

    def tearDown(self) -> None:
        self.ui.deleteLater()
        self.app.processEvents()

    def test_unnamed_keys_reset_to_defaults(self) -> None:
        from tentacle.slots.tools._photogrammetry import metashape_parameters as P

        # Simulate residue from an earlier preset/session.
        self.slots._write_param("smooth_strength", 3)
        self.slots._write_param("depth_filter", "aggressive")
        # Apply a preset that names neither key.
        self.slots._apply_param_dict({"align_downscale": 4})
        self.assertEqual(self.slots._read_param("align_downscale"), 4)
        self.assertEqual(
            self.slots._read_param("smooth_strength"),
            P.PARAMS["smooth_strength"].default,
        )
        self.assertEqual(
            self.slots._read_param("depth_filter"), P.PARAMS["depth_filter"].default
        )

    def test_widgetless_preset_keys_are_logged(self) -> None:
        from unittest import mock as umock

        with umock.patch.object(self.slots.bridge.logger, "warning") as warn:
            self.slots._apply_param_dict({"align_downscale": 2, "no_such_key": True})
        self.assertTrue(warn.called)
        self.assertIn("no_such_key", str(warn.call_args))


if __name__ == "__main__":
    unittest.main()
