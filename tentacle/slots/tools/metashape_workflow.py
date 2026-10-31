# !/usr/bin/python
# coding=utf-8
"""Slots for the Metashape Workflow panel.

A thin :class:`~._photogrammetry.panel_slots.PhotogrammetryPanelSlots`
subclass (the shared photogrammetry-panel scaffolding: Project-Name row, frames
Source row via :class:`FramesSourceMixin`, run-mode combo, semantic presets,
header menu, async log-streaming ``b000``). Where the DCC bridges fire an RPC
into a live host, this panel **discovers the local ``metashape.exe`` and drives
the headless pipeline** (extapps' ``metashape_workflow/run_combined.py``) through
it via extapps' :class:`MetashapeRunner` — the real pipeline by default, not
the old in-process-SDK path that silently fell back to mock mode.

Presets are **semantic run-templates** shared with the headless CLI: the panel's
preset combo is backed by the same engine-scoped
:meth:`extapps.Profile.preset_store` the runner reads, so a
built-in like ``specular_metal`` loads straight into the param widgets and a
preset saved here is picked up by ``run_combined --preset``.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from extapps import DOCS_BASE_URL, MetashapeRunner, Profile

from ._photogrammetry import metashape_parameters as _params
from ._photogrammetry.panel_slots import FramesSourceMixin, PhotogrammetryPanelSlots

# Pipeline run modes shown in the template combo (cmb000). The label is the
# display stem; the second element is the ``--stop-after`` value ("" = full).
_RUN_MODES: List[Tuple[str, str]] = [
    ("Full pipeline", ""),
    ("Align only", "align"),
    ("Refine only", "refine"),
    ("Prep preview", PhotogrammetryPanelSlots.PREP_PREVIEW_MODE),
]


class MetashapeWorkflowSlots(FramesSourceMixin, PhotogrammetryPanelSlots):
    """Switchboard slots wired to ``metashape_workflow.ui``."""

    UI_NAME = "metashape_workflow"
    LOG_TAG = "metashape_workflow"

    ENGINE_LABEL = "Metashape"
    PRESET_ENGINE = "metashape"
    MISSING_ENGINE_MESSAGE = (
        "metashape.exe not found. Install Agisoft Metashape, or set "
        "$METASHAPE_EXE to its path. (No mock fallback — the panel drives the "
        "real install.)"
    )
    NAME_PLACEHOLDER = "(basename for the .psx project + outputs)"
    NAME_TOOLTIP = (
        "Project basename (--name). Outputs land in <output-root>/<name>/."
    )
    OUTPUT_FOLDER_TOOLTIP = (
        "Open <output-root>/<name>/ — the QC report PDF + sidecar (and, for a "
        "full run, the mesh/texture) land here. This is how you inspect an "
        "Align-only / Refine-only result."
    )
    MODE_DESC = {
        "": "Full pipeline: align → depth → model → texture → export.",
        "align": "Align only: stop after alignment (fast A/B of input prep, "
                 "minutes vs a multi-hour bake).",
        "refine": "Refine only: stop after gradual-selection alignment refinement.",
        PhotogrammetryPanelSlots.PREP_PREVIEW_MODE:
            "Prep preview: dry-run the input curation in the panel's Python — "
            "survivor counts per dedup threshold + the sharpness distribution. "
            "No Metashape launch, no files written; use it to tune the "
            "pre-processing knobs before a run.",
    }

    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Output Root:"
    OUTPUT_DIR_PLACEHOLDER = "(defaults to the profile's Metashape output root)"
    OUTPUT_DIR_TOOLTIP = (
        "Root the project is written under as <output-root>/<name>/ "
        "(--output-root). Leave blank to use the active photogrammetry "
        "profile's metashape_output_root."
    )

    # Metashape has a full page of its own (install, GUI controls, two-stage
    # runs, presets, API) that links on to the shared TUNING.md, so it
    # overrides the base's TUNING.md link.
    DOCS_URL = DOCS_BASE_URL + "docs/metashape_workflow.md"
    DOCS_LABEL = "Detailed docs (install, controls, presets, API)"

    # ------------------------------------------------------------------ hooks
    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        # No per-template script files; this is just where the runner lives.
        return Path(__file__).parent

    def make_bridge(self) -> MetashapeRunner:
        return MetashapeRunner()

    def list_template_modes(self) -> List[Tuple[str, str]]:
        return list(_RUN_MODES)

    def default_output_dir(self) -> str:
        try:
            return Profile.get_profile()["metashape_output_root"]
        except Exception:  # noqa: BLE001
            return ""

    def _mode_argv(self) -> List[str]:
        pair = self._selected_template_mode()
        if pair and pair[1] in ("align", "refine"):
            return ["--stop-after", pair[1]]
        return super()._mode_argv()  # base handles the shared prep-preview mode

    def help_spec(self) -> dict:
        return dict(
            title="Metashape Workflow",
            body="Drive Agisoft Metashape photogrammetry headless from the local "
            "install — project setup, source frames, run mode, and tuning presets "
            "shared with the CLI.",
            steps=[
                "Set a <b>Project Name</b> and pick a <b>Source</b> (frames folder "
                "or video clip(s) to extract).",
                "Optionally set an <b>Output Root</b> (else the profile default).",
                "Pick a <b>Run Mode</b> (full / align-only / refine-only).",
                "Choose a tuning <b>preset</b> (e.g. specular_metal) and/or tweak "
                "the parameters.",
                "Press <b>Run Workflow</b> and watch the log stream.",
            ],
            notes=[
                "Align-only / Refine-only stop after alignment and write only a QC "
                "report PDF + sidecar (no mesh) — a fast A/B of input prep before a "
                "multi-hour full bake. Inspect them via the header menu's 'Open "
                "Output Folder'.",
                "Needs Agisoft Metashape installed (auto-discovered, or set "
                "$METASHAPE_EXE). Presets are shared with the headless "
                "run_combined --preset.",
            ],
        )
