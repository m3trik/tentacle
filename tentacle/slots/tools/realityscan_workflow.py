# !/usr/bin/python
# coding=utf-8
"""Slots for the RealityCapture Workflow panel.

A thin :class:`~._photogrammetry.panel_slots.PhotogrammetryPanelSlots`
subclass sharing the photogrammetry-panel scaffolding with the Metashape panel
(Project-Name row, frames Source row via :class:`FramesSourceMixin`, run-mode
combo, semantic presets, header menu, async log-streaming ``b000``). It
**discovers the local RealityScan / RealityCapture install and drives the
headless pipeline** (extapps' ``realityscan_workflow/run_combined.py``) through it
via extapps' :class:`RealityScanRunner`.

Presets are engine-scoped (``presets/realityscan/``) and shared with the CLI: a
preset saved here is a RealityScan preset, picked up by ``run_combined --preset``
and never shown in another engine's list.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from extapps import Profile, RealityScanRunner

from ._photogrammetry import realityscan_parameters as _params
from ._photogrammetry.panel_slots import FramesSourceMixin, PhotogrammetryPanelSlots

# RealityScan has no --stop-after; besides the full pipeline it offers only
# the shared curation-preview dry-run (its runner executes in the panel's own
# Python, so --curate-preview just works — no Metashape-style venv chaining).
_RUN_MODES: List[Tuple[str, str]] = [
    ("Full pipeline", ""),
    ("Prep preview", PhotogrammetryPanelSlots.PREP_PREVIEW_MODE),
]


class RealityscanWorkflowSlots(FramesSourceMixin, PhotogrammetryPanelSlots):
    """Switchboard slots wired to ``realityscan_workflow.ui``.

    Note the class name casing — Switchboard resolves a UI's slots by
    title-casing each underscore part of the UI base name
    (``realityscan_workflow`` -> ``RealityscanWorkflow`` + ``Slots``), so the
    class must be ``Realityscan...`` (lowercase 's'), not ``RealityScan...``.
    """

    UI_NAME = "realityscan_workflow"
    LOG_TAG = "realityscan_workflow"

    ENGINE_LABEL = "RealityCapture"
    PRESET_ENGINE = "realityscan"
    MISSING_ENGINE_MESSAGE = (
        "RealityScan / RealityCapture not found. Point the panel at an install "
        "by any of: set $RC_EXE, set 'apps.realityscan_exe' in the photogrammetry "
        "profile, or install it to the standard location. (No mock fallback — the "
        "panel drives the real install.)"
    )
    NAME_PLACEHOLDER = "(basename for the .rsproj project + outputs)"
    NAME_TOOLTIP = "Project basename (--name). Outputs land in <output-root>/<name>/."
    MODE_DESC = {
        "": "Full pipeline: align → mesh → texture → export → publish.",
        PhotogrammetryPanelSlots.PREP_PREVIEW_MODE:
            "Prep preview: dry-run the input curation — survivor counts per "
            "dedup threshold + the sharpness distribution. No RealityScan "
            "launch, no files written; use it to tune the pre-processing "
            "knobs before a run.",
    }
    OUTPUT_FOLDER_TOOLTIP = (
        "Open <output-root>/<name>/ — the exported mesh/texture, QC report, and "
        "sidecar land here."
    )

    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Output Root:"
    OUTPUT_DIR_PLACEHOLDER = "(defaults to the profile's RealityScan scratch root)"
    OUTPUT_DIR_TOOLTIP = (
        "Local scratch root the project is written under as <output-root>/<name>/ "
        "(--output-root). RealityScan's live project I/O must NOT run in a "
        "cloud-sync folder; deliverables are published to the synced root "
        "afterward. Leave blank for the profile's realityscan_scratch_root."
    )

    # ------------------------------------------------------------------ hooks
    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        return Path(__file__).parent

    def make_bridge(self) -> RealityScanRunner:
        return RealityScanRunner()

    def _log_extra_availability(self) -> None:
        """State the RSNode requirement at panel open — the instructions, not a
        live probe.

        Unlike Metashape (driven headless via ``metashape.exe -r``), RealityScan's
        CLI launcher is window-station + sign-in gated and can't process in a
        non-interactive / SSH session — the reliable headless transport is RSNode,
        which needs RealityScan **launched, signed in, with Real-time Assistance
        enabled**. That's the common "it won't connect" case, so surface the fix
        up front. (No network probe here: a socket call in panel construction
        would stall opening the panel for up to the connect timeout; actual
        reachability is reported when a run dispatches via ``--rsnode auto``.)
        """
        self.bridge.logger.info(
            "Headless runs drive RealityScan through its RSNode REST bridge. If a "
            "run can't connect, launch RealityScan, sign in, and enable Workflow ▸ "
            "Real-time Assistance — the CLI fallback works only in an interactive "
            "desktop session. A node on another host answers only on its own "
            "localhost: tunnel to it (ssh -L 8000:127.0.0.1:8000 <host>) and set "
            "$RC_RSNODE=1 + $RC_RSNODE_URL to the tunnel's local end."
        )

    def list_template_modes(self) -> List[Tuple[str, str]]:
        return list(_RUN_MODES)

    def default_output_dir(self) -> str:
        try:
            return Profile.get_profile()["realityscan_scratch_root"]
        except Exception:  # noqa: BLE001
            return ""

    def help_spec(self) -> dict:
        return dict(
            title="RealityCapture Workflow",
            body="Drive RealityScan / RealityCapture photogrammetry headless from "
            "the local install — project setup, source frames, and tuning presets "
            "shared with the CLI.",
            steps=[
                "Set a <b>Project Name</b> and pick a <b>Source</b> (frames folder "
                "or video clip(s) to extract).",
                "Optionally set an <b>Output Root</b> (else the profile's local "
                "scratch root).",
                "Choose a tuning <b>preset</b> and/or tweak the parameters.",
                "Press <b>Run Workflow</b> and watch the log stream.",
            ],
            notes=[
                "RealityScan's strongest noise levers (image/depth downscale, "
                "depth-map filtering, a tight reconstruction region, masking) are "
                "GUI / per-project Settings only — the panel exposes its "
                "CLI-reachable knobs (quality, component floor, simplify) plus the "
                "shared input pre-processing. See TUNING.md.",
                "Needs RealityScan / RealityCapture installed (auto-discovered, "
                "$RC_EXE, or the profile's apps.realityscan_exe). Deliverables are "
                "auto-published to the synced output root on success.",
                "For headless runs (and any non-interactive session), launch "
                "RealityScan, sign in, and enable <b>Workflow ▸ Real-time "
                "Assistance</b> (the RSNode REST server) — the log reports whether "
                "it's reachable. Without it the run falls back to the CLI launcher, "
                "which only works in an interactive desktop session.",
            ],
        )
