# !/usr/bin/python
# coding=utf-8
"""Slots for the Brush (gaussian-splat) Workflow panel.

A thin :class:`~._photogrammetry.panel_slots.PhotogrammetryPanelSlots`
subclass sharing the photogrammetry-panel scaffolding (Project-Name row, run-mode
combo, semantic presets, header menu, async log-streaming ``b000``). Unlike the
image-in panels it takes a **COLMAP dataset directory** (e.g. from Metashape's
``--export-colmap``) rather than frames/video, so it builds its own input row
instead of using :class:`FramesSourceMixin`.

It discovers the local **Brush** install and drives the headless splat pipeline
(extapps' ``gaussian_splat_workflow/run_combined.py``) through it via extapps'
:class:`GaussianSplatRunner`. Run modes: *Train only* and
*Train + Publish* (clean + convert to Unity ``.spz`` / web ``.sog`` + viewer).
"""
from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import List, Optional, Tuple

from extapps import BrushInstallRunner, GaussianSplatRunner, Profile
from qtpy import QtWidgets

from ._photogrammetry import gaussian_splat_parameters as _params
from ._photogrammetry.panel_slots import PhotogrammetryPanelSlots

_RUN_MODES: List[Tuple[str, str]] = [
    ("Train only", ""),
    ("Train + Publish", "publish"),
]


class GaussianSplatWorkflowSlots(PhotogrammetryPanelSlots):
    """Switchboard slots wired to ``gaussian_splat_workflow.ui``."""

    UI_NAME = "gaussian_splat_workflow"
    LOG_TAG = "gaussian_splat_workflow"

    ENGINE_LABEL = "Brush"
    PRESET_ENGINE = "gaussian_splat"
    MISSING_ENGINE_MESSAGE = (
        "Brush not found. Use the header menu's 'Download Brush' to install it "
        "automatically, or set $BRUSH_EXE / install from "
        "github.com/ArthurBrussee/brush. (No mock fallback — the panel drives the "
        "real install.)"
    )
    NAME_PLACEHOLDER = "(basename for the splat .ply + exports)"
    NAME_TOOLTIP = "Project basename (--name). Outputs land in <output-root>/<name>/."
    OUTPUT_FOLDER_TOOLTIP = (
        "Open <output-root>/<name>/ — the trained splat .ply (and, for Train + "
        "Publish, the Unity .spz / web .sog + .html viewer) land here."
    )
    MODE_DESC = {
        "": "Train only: train the splat .ply from the COLMAP dataset.",
        "publish": "Train + Publish: train, then clean + convert to engine "
                   "formats (Unity .spz / web .sog + viewer; needs splat-transform).",
    }

    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Output Root:"
    OUTPUT_DIR_PLACEHOLDER = "(defaults to the profile's gsplat scratch root)"
    OUTPUT_DIR_TOOLTIP = (
        "Local scratch root the splat is written under as <output-root>/<name>/ "
        "(--output-root). The multi-hundred-MB checkpoints must NOT churn inside a "
        "cloud-sync folder. Leave blank for the profile's gsplat_scratch_root."
    )

    # ------------------------------------------------------------------ input row
    def _init_inputs(self, kwargs) -> None:
        self._initial_colmap: str = kwargs.get("colmap_dir", "") or ""
        self._colmap_edit: Optional[QtWidgets.QLineEdit] = None
        # Separate runner for the "Download Brush" action so it can stream the
        # installer even while no Brush exists (the training bridge refuses to
        # run when Brush is unavailable).
        self._install_runner = BrushInstallRunner()

    def _build_source_rows(self) -> None:
        self._colmap_edit = self._insert_top_row(
            label="COLMAP Dir:",
            placeholder="(COLMAP dataset: images/ + sparse/0/)",
            tooltip="The COLMAP dataset directory Brush trains from (--colmap-dir) "
                    "— images/ + sparse/0/, e.g. from Metashape's --export-colmap.",
            initial=self._initial_colmap,
            buttons=[("...", self._pick_colmap)],
        )

    def resolved_colmap_dir(self) -> str:
        return self._colmap_edit.text().strip() if self._colmap_edit else ""

    def _pick_colmap(self) -> None:
        try:
            d = self.sb.dir_dialog(
                title="Select COLMAP dataset directory",
                start_dir=self.resolved_colmap_dir() or os.getcwd(),
            )
        except Exception:  # noqa: BLE001
            d = None
        if d and self._colmap_edit is not None:
            self._colmap_edit.setText(d)

    def _resolve_input_argv(self) -> Optional[List[str]]:
        d = self.resolved_colmap_dir()
        if not d or not os.path.isdir(d):
            self.bridge.logger.error(
                f"COLMAP Dir is required and must exist: {d or '(empty)'}"
            )
            if self._colmap_edit is not None:
                self._colmap_edit.setFocus()
            return None
        return ["--colmap-dir", d]

    # ------------------------------------------------------------------ hooks
    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        return Path(__file__).parent

    def make_bridge(self) -> GaussianSplatRunner:
        return GaussianSplatRunner()

    # ------------------------------------------------------------------ install + view
    def header_init(self, widget) -> None:
        super().header_init(widget)
        # Brush is itself a splat viewer, so offer launch actions (the result
        # is a .ply; Brush loads .ply / .compressed.ply).
        widget.menu.add(
            "QPushButton", setText="Open Brush Viewer",
            setObjectName="btn_open_brush",
            setToolTip="Launch Brush's GUI viewer empty, to load any splat manually.",
        )
        widget.menu.btn_open_brush.clicked.connect(self.open_brush_viewer)
        widget.menu.add(
            "QPushButton", setText="View Result in Brush",
            setObjectName="btn_view_result",
            setToolTip="Open the latest trained splat (.ply) from this run's output "
                       "folder in Brush's viewer.",
        )
        widget.menu.btn_view_result.clicked.connect(self.open_result_in_brush)
        # Brush is a single downloadable binary, so offer a one-click install
        # (Metashape / RealityScan are large commercial installers — no
        # equivalent, which is why this lives on the Brush panel only).
        widget.menu.add(
            "QPushButton", setText="Download Brush",
            setObjectName="btn_install_brush",
            setToolTip="Download + install Brush (github.com/ArthurBrussee/brush) "
                       "into the per-user tools dir via pythontk's app installer.",
        )
        widget.menu.btn_install_brush.clicked.connect(self.install_brush)

    def _launch_brush(self, args: List[str], what: str) -> None:
        """Fire-and-forget launch of the Brush GUI (the viewer keeps running
        independently of the panel). Logs a missing-engine error when Brush
        isn't found so the user can use Download Brush / set $BRUSH_EXE."""
        exe = self.bridge.exe
        if not exe:
            self.bridge.logger.error(self.MISSING_ENGINE_MESSAGE)
            return
        from pythontk import AppLauncher

        proc = AppLauncher.launch(exe, args=args)
        if proc is None:
            self.bridge.logger.error(f"Failed to launch Brush {what}.")
        else:
            self.bridge.logger.info(f"Launched Brush {what}.")

    def open_brush_viewer(self) -> None:
        """Open Brush's GUI viewer with nothing loaded (``brush`` defaults to the
        viewer UI when given no source)."""
        self._launch_brush([], "viewer")

    def open_result_in_brush(self) -> None:
        """Open the latest trained splat in Brush's viewer.

        A source flips Brush's ``--with-viewer`` off by default (headless
        training), so viewing a ``.ply`` needs it passed explicitly."""
        result = self._latest_result_splat()
        if not result:
            self.bridge.logger.error(
                "No trained splat (.ply) found in the output folder yet — run the "
                "workflow first."
            )
            return
        self._launch_brush(
            [result, "--with-viewer"], f"viewer: {os.path.basename(result)}"
        )

    def _latest_result_splat(self) -> str:
        """Newest ``.ply`` (covers ``.compressed.ply``) under this run's output
        folder — the last run's, or where the current inputs would write."""
        base = self._last_output_dir or self._resolved_output_project_dir()
        if not base or not os.path.isdir(base):
            return ""
        cands = [
            p
            for p in glob.glob(os.path.join(base, "**", "*.ply"), recursive=True)
            if os.path.isfile(p)
        ]
        return max(cands, key=os.path.getmtime) if cands else ""

    def install_brush(self) -> None:
        """Download + install Brush if it isn't already discoverable.

        Streams pythontk's downloader in a child process into the log pane; on
        success the bridge re-discovers Brush via the install catalog (its
        ``exe`` / ``is_available`` re-query :meth:`GaussianSplatWorkflow.find_brush_exe` each call, so
        no further wiring is needed)."""
        if self.bridge.is_available():
            self.bridge.logger.info(f"Brush already available: {self.bridge.exe}")
            return
        if self._install_runner.is_running():
            self.bridge.logger.warning("Brush download already in progress.")
            return
        self.bridge.logger.info(
            "Downloading Brush from github.com/ArthurBrussee/brush "
            "(~160 MB) — this can take a minute…"
        )
        try:
            self._install_runner.start(
                [], on_line=self._append_output, on_done=self._on_install_done,
            )
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Could not start Brush download: {e}")

    def _on_install_done(self, code: int) -> None:
        if code == 0 and self.bridge.is_available():
            self.bridge.logger.info(f"Brush ready: {self.bridge.exe}")
        else:
            self.bridge.logger.error(
                "Brush install did not complete — install manually "
                "(github.com/ArthurBrussee/brush) or set $BRUSH_EXE."
            )

    def cancel_run(self) -> None:
        """Cancel an in-flight Brush download too — the base 'Cancel Run' action
        only knows the training bridge, so without this a ~160 MB download
        couldn't be stopped from the panel."""
        if self._install_runner.is_running():
            self.bridge.logger.warning("Cancelling Brush download…")
            self._install_runner.cancel()
            return
        super().cancel_run()

    def list_template_modes(self) -> List[Tuple[str, str]]:
        return list(_RUN_MODES)

    def default_output_dir(self) -> str:
        try:
            return Profile.get_profile()["gsplat_scratch_root"]
        except Exception:  # noqa: BLE001
            return ""

    def _mode_argv(self) -> List[str]:
        pair = self._selected_template_mode()
        if pair and pair[1] == "publish":
            return ["--publish"]
        return []

    def help_spec(self) -> dict:
        return dict(
            title="Brush Splat Workflow",
            body="Train a 3D Gaussian Splat from a COLMAP dataset with Brush, and "
            "optionally publish it to engine formats (Unity .spz / web viewer).",
            steps=[
                "Set a <b>Project Name</b> and pick a <b>COLMAP Dir</b> (images/ + "
                "sparse/0/, e.g. from Metashape's --export-colmap).",
                "Optionally set an <b>Output Root</b> (else the profile's local "
                "scratch root).",
                "Pick a <b>Run Mode</b> (Train only / Train + Publish).",
                "Choose a tuning <b>preset</b> and/or tweak the parameters.",
                "Press <b>Run Workflow</b> and watch the log stream.",
            ],
            notes=[
                "More training steps is a VRAM-free quality lever on an 8-10 GB "
                "card; raising the gaussian growth aggressiveness instead tends to "
                "OOM. See TUNING.md.",
                "Needs Brush installed (auto-discovered, or set $BRUSH_EXE). If "
                "it's missing, the header menu's <b>Download Brush</b> fetches the "
                "prebuilt binary into the per-user tools dir. Train + Publish also "
                "needs splat-transform (npm i -g @playcanvas/splat-transform).",
                "Brush is also a viewer: the header menu's <b>Open Brush Viewer</b> "
                "launches it empty, and <b>View Result in Brush</b> opens the latest "
                "trained .ply from the output folder.",
            ],
        )
