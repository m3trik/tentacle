# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the Metashape Workflow panel.

Unlike the DCC bridges (which substitute ``__TOKEN__`` placeholders into a
script), this panel drives a single headless runner —
:mod:`extapps.photogrammetry.metashape_workflow.run_combined` — inside the
local ``metashape.exe``. So each :class:`AttributeSpec` here is keyed by the
**semantic name the runner / preset JSON use** (``align_downscale``,
``depth_filter``, ``face_count`` …), and :meth:`Parameters.to_argv` renders the collected
values into ``run_combined`` CLI flags — the Metashape analogue of the bridges'
placeholder substitution.

Keying by the semantic name is what lets one :class:`pythontk.PresetStore` serve
both front-ends: a built-in run-template like ``specular_metal.json`` (keys
``align_downscale`` / ``depth_downscale`` / ``depth_filter`` / ``face_count`` /
``mask_background``) loads straight into these widgets, and a preset saved from
the panel is read back verbatim by ``run_combined --preset``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from tentacle import Slots

AttributeSpec, ParamRegistry = Slots.AttributeSpec, Slots.ParamRegistry

from .shared_parameters import (
    PREPROCESSING_KEYS,
    PREPROCESSING_PARAMS,
    SharedParams,
)


# Display order is iteration order over this dict. Keys mirror the run_combined
# CLI flags / profile preset keys exactly (see module docstring). Input image
# pre-processing leads the panel (it runs first in the pipeline — order of
# operations), so the shared specs are merged in *first*; the engine-specific
# reconstruction / alignment / cleanup params follow.
PARAMS: "Dict[str, AttributeSpec]" = dict(PREPROCESSING_PARAMS)
PARAMS.update(
    {
        "align_downscale": AttributeSpec(
            key="align_downscale",
            label="Align Downscale",
            kind="int",
            default=2,
            minimum=1,
            maximum=16,
            tooltip="Match-photos downscale (1 = full res / highest quality, "
            "slower). Maps to --align-downscale.",
        ),
        "depth_downscale": AttributeSpec(
            key="depth_downscale",
            label="Depth Downscale",
            kind="int",
            default=2,
            minimum=1,
            maximum=16,
            tooltip="Depth-map downscale (1 = Ultra). On specular / low-texture "
            "surfaces, full-res depth over-fits and warps geometry — keep "
            "this at 2 there. Maps to --depth-downscale.",
        ),
        "depth_filter": AttributeSpec(
            key="depth_filter",
            label="Depth Filter",
            kind="choice",
            default="mild",
            choices=["mild", "moderate", "aggressive", "none"],
            tooltip="Depth-map filtering strength. 'mild' keeps the most detail; "
            "raise to 'moderate' to denoise specular geometry. Maps to "
            "--depth-filter.",
        ),
        "face_count": AttributeSpec(
            key="face_count",
            label="Face Count",
            kind="choice",
            default="medium",
            choices=["low", "medium", "high"],
            tooltip="Reconstructed mesh density (Metashape FaceCount). Maps to "
            "--face-count.",
        ),
        "texture_size": AttributeSpec(
            key="texture_size",
            label="Texture Size",
            kind="choice",
            default="auto",
            choices=["auto", "1024", "2048", "4096", "8192"],
            tooltip="Texture page resolution. 'auto' derives it from the source "
            "frames' long edge (next power-of-two, capped 8192). Maps to "
            "--texture-size.",
        ),
        "mask_background": AttributeSpec(
            key="mask_background",
            label="Mask Background",
            kind="bool",
            default=False,
            tooltip="Mask the background before alignment: Metashape 2.2's "
            "native AI masking when available, else rembg (needs rembg "
            "installed). Emits --use-masks.",
        ),
        "gate_mode": AttributeSpec(
            key="gate_mode",
            label="Gate Mode",
            kind="choice",
            default="warn",
            choices=["warn", "halt"],
            tooltip="Acceptance gates: warn (log + continue) or halt (raise on a "
            "failed gate). Maps to --gate-mode.",
        ),
        "save_project": AttributeSpec(
            key="save_project",
            label="Save .psx Project",
            kind="bool",
            default=False,
            tooltip="Save a reopenable Metashape project (.psx + full .files) so a "
            "later run can re-texture without redoing alignment/depth. "
            "Emits --save-project.",
        ),
        # --- Alignment quality (pre-align triage + matchPhotos levers) ----------
        "triage_quality": AttributeSpec(
            key="triage_quality",
            label="Triage Quality",
            kind="float",
            section="Alignment",
            default=0.0,
            minimum=0.0,
            maximum=1.0,
            decimals=2,
            tooltip="Disable cameras below this Metashape Image/quality score "
            "(analyzeImages) before alignment. 0 (default) = off: the score "
            "correlates with texture, so on low-texture / specular subjects "
            "triage disables good frames wholesale, on top of curation's "
            "blur culling. Set ~0.5 for genuinely messy input. Maps to "
            "--triage-quality.",
        ),
        "generic_preselection": AttributeSpec(
            key="generic_preselection",
            label="Generic Preselection",
            kind="bool",
            section="Alignment",
            default=True,
            tooltip="Fast low-res pairwise image preselection before matching "
            "(Metashape's own default; the key lever to fully align "
            "featureless / specular captures, where reference preselection "
            "has no camera coords to work from). Uncheck only for "
            "well-textured, geo-referenced sets. Emits "
            "--generic-preselection / --no-generic-preselection.",
        ),
        "keypoint_limit": AttributeSpec(
            key="keypoint_limit",
            label="Keypoint Limit",
            kind="int",
            section="Alignment",
            default=60000,
            minimum=10000,
            maximum=400000,
            tooltip="Max detected feature points per photo (matchPhotos keypoint "
            "limit). 60000 is the verified robust-alignment baseline "
            "(TUNING.md); Metashape's stock 40000 under-aligns low-texture "
            "/ specular surfaces. Maps to --keypoint-limit.",
        ),
        "tiepoint_limit": AttributeSpec(
            key="tiepoint_limit",
            label="Tiepoint Limit",
            kind="int",
            section="Alignment",
            default=10000,
            minimum=0,
            maximum=100000,
            tooltip="Max tie points kept per photo (matchPhotos tiepoint limit; "
            "0 = unlimited). Higher = denser sparse cloud + more robust "
            "alignment on hard sets. Maps to --tiepoint-limit.",
        ),
        # --- Alignment stage toggles (post initial align) -----------------------
        "dedupe_cameras": AttributeSpec(
            key="dedupe_cameras",
            label="Dedupe Cameras",
            kind="bool",
            section="Alignment",
            default=False,
            tooltip="Disable near-duplicate camera poses after alignment. OPT-IN: "
            "the distance threshold is in arbitrary chunk units (scale "
            "varies solve to solve) and disabled cameras are excluded from "
            "depth mapping - enable only on captures with genuinely "
            "redundant static footage. Emits --dedupe-cameras.",
        ),
        "skip_refine": AttributeSpec(
            key="skip_refine",
            label="Skip Refine",
            kind="bool",
            section="Alignment",
            default=False,
            tooltip="Skip gradual-selection alignment refinement. Emits --skip-refine.",
        ),
        "calibrate_colors": AttributeSpec(
            key="calibrate_colors",
            label="Calibrate Colors",
            kind="bool",
            section="Mesh Cleanup",
            default=False,
            tooltip="Run Metashape's calibrateColors (incl. white balance) before "
            "texturing. OPT-IN: with exposure equalization already applied "
            "to the frames this stacks a second color transform into the "
            "albedo - enable for mixed-lighting captures that skip "
            "equalization. Emits --calibrate-colors.",
        ),
        # --- Mesh cleanup (post-build) ------------------------------------------
        "min_component_size": AttributeSpec(
            key="min_component_size",
            label="Min Component Size",
            kind="int",
            section="Mesh Cleanup",
            default=100,
            minimum=0,
            maximum=200000,
            tooltip="Delete disconnected mesh islands smaller than this many faces "
            "(removeComponents) - the main lever against floater 'snow'. 0 "
            "disables. NOTE: on specular / low-texture metal do NOT crank "
            "this (it strips real detail without fixing depth-level noise). "
            "Maps to --clean-min-component (parity with the RC runner).",
        ),
        "smooth_strength": AttributeSpec(
            key="smooth_strength",
            label="Smooth Strength",
            kind="int",
            section="Mesh Cleanup",
            default=0,
            minimum=0,
            maximum=10,
            tooltip="Laplacian mesh-smoothing passes after cleanup (0 = none). A "
            "light value (1) denoises specular geometry; high values melt "
            "real detail. Maps to --smooth-strength.",
        ),
        "close_holes": AttributeSpec(
            key="close_holes",
            label="Close Holes %",
            kind="int",
            section="Mesh Cleanup",
            default=30,
            minimum=0,
            maximum=100,
            tooltip="Close mesh holes up to this percent of the total mesh size "
            "(closeHoles). 0 disables. Maps to --close-holes.",
        ),
        # --- Mesh processing (PyMeshLab, post-export) ---------------------------
        "mesh_remesh_pct": AttributeSpec(
            key="mesh_remesh_pct",
            label="Remesh Edge %",
            kind="float",
            section="Mesh Processing",
            default=0.0,
            minimum=0.0,
            maximum=10.0,
            decimals=2,
            tooltip="PyMeshLab isotropic remesh of the exported mesh toward a "
            "uniform edge length, as a percent of the bbox diagonal (0 = "
            "off). The evenness pass before decimation on unevenly dense "
            "scans. Runs post-export in the panel venv; needs "
            "extapps[mesh]. Maps to --mesh-remesh-pct.",
        ),
        "mesh_decimate_faces": AttributeSpec(
            key="mesh_decimate_faces",
            label="Decimate To Faces",
            kind="int",
            section="Mesh Processing",
            default=0,
            minimum=0,
            maximum=20000000,
            tooltip="PyMeshLab curvature-weighted quadric decimation of the "
            "exported mesh to this face count (0 = off) - adaptive "
            "density, spends the budget on high-curvature areas. Runs "
            "post-export in the panel venv; needs extapps[mesh]. Maps to "
            "--mesh-decimate-faces.",
        ),
        "bake_vertex_color": AttributeSpec(
            key="bake_vertex_color",
            label="Bake Vertex Color px",
            kind="int",
            section="Mesh Processing",
            default=0,
            minimum=0,
            maximum=8192,
            tooltip="Bake per-vertex color to a texture of this size on "
            "auto-generated UVs (PyMeshLab; 0 = off). For vertex-colored "
            "meshes with no texture pass. Maps to --bake-vertex-color.",
        ),
    }
)


# Value params -> CLI flags that take an argument (always emitted; the widget
# always holds a concrete value). The shared input-pre-processing flags are
# rendered separately via ``SharedParams.preprocessing_argv`` (its master toggle gates them).
_VALUE_FLAGS: "Dict[str, str]" = {
    "align_downscale": "--align-downscale",
    "depth_downscale": "--depth-downscale",
    "depth_filter": "--depth-filter",
    "face_count": "--face-count",
    "texture_size": "--texture-size",
    "gate_mode": "--gate-mode",
    # Alignment quality (pre-align triage + matchPhotos levers).
    "triage_quality": "--triage-quality",
    "keypoint_limit": "--keypoint-limit",
    "tiepoint_limit": "--tiepoint-limit",
    # Mesh cleanup (post-build).
    "min_component_size": "--clean-min-component",
    "smooth_strength": "--smooth-strength",
    "close_holes": "--close-holes",
    # Mesh processing (PyMeshLab, post-export).
    "mesh_remesh_pct": "--mesh-remesh-pct",
    "mesh_decimate_faces": "--mesh-decimate-faces",
    "bake_vertex_color": "--bake-vertex-color",
}

# Bool params -> store_true flags (emitted only when the value is truthy). Note
# the semantic-name -> flag indirection (``mask_background`` -> ``--use-masks``)
# that keeps the preset JSON / widget key independent of the CLI spelling.
_STORE_TRUE_FLAGS: "Dict[str, str]" = {
    "mask_background": "--use-masks",
    "save_project": "--save-project",
    "dedupe_cameras": "--dedupe-cameras",
    "skip_refine": "--skip-refine",
    "calibrate_colors": "--calibrate-colors",
}

# Bool params whose runner default is ON -> BooleanOptionalAction flags that
# always emit (--flag / --no-flag), so unchecking the panel box actually turns
# the stage off (a store_true flag can't override an on-by-default).
_BOOL_FLAGS: "Dict[str, str]" = {
    "generic_preselection": "--generic-preselection",
}


# Which params actually affect each run mode — the panel's relevance
# declaration, mirroring run_combined.main()'s stage order. This is the
# run-mode analogue of the DCC bridges' ``__TOKEN__`` placeholders: the bridge
# base feeds the active input to referenced_keys() and shows only the rows it
# returns. A stop-after mode hides the knobs for stages that never execute.
#   align : curate/equalize/mask → triage → align → STOP   (no dedupe/depth/mesh/tex)
#   refine: …as align… → refine → STOP            (adds skip_refine)
#   ""    : full pipeline → every param
# Mesh-cleanup knobs (min_component_size/smooth_strength/close_holes) are a
# post-build stage, so they're intentionally absent here → full pipeline only.
_ALIGN_MODE_KEYS = (
    frozenset(
        {
            "align_downscale",
            "mask_background",
            "gate_mode",
            "save_project",
            # Alignment-quality levers (pre-align triage + matchPhotos) run in every mode.
            "triage_quality",
            "generic_preselection",
            "keypoint_limit",
            "tiepoint_limit",
        }
    )
    | PREPROCESSING_KEYS
)  # input pre-processing runs before alignment -> every mode
_MODE_KEYS: "Dict[str, frozenset]" = {
    "align": _ALIGN_MODE_KEYS,
    "refine": _ALIGN_MODE_KEYS | {"skip_refine"},
    # Prep preview (--curate-preview) dry-runs curation only — nothing but the
    # shared pre-processing knobs is consulted.
    "prep_preview": PREPROCESSING_KEYS,
    # "" (full pipeline) intentionally absent → every registered param applies.
    # dedupe_cameras / calibrate_colors are post-align full-pipeline stages, so
    # like the mesh-cleanup knobs they're absent from the stop-after modes.
}


class Parameters(ParamRegistry):
    """The Metashape panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module``: :data:`PARAMS` plus
    ``defaults``; ``referenced_keys`` is the run-mode relevance and ``to_argv``
    renders the ``run_combined`` flags.
    """

    PARAMS = PARAMS

    @staticmethod
    def to_argv(values: "Dict[str, Any]") -> "List[str]":
        """Render collected param *values* into ``run_combined`` CLI flags (via the
        shared :func:`render_flag_argv` emit rules), then append the shared input
        pre-processing flags (curate + equalize), which its master toggle gates."""
        argv = SharedParams.render_flag_argv(
            values, _VALUE_FLAGS, _STORE_TRUE_FLAGS, _BOOL_FLAGS
        )
        argv += SharedParams.preprocessing_argv(values)
        return argv

    @classmethod
    def referenced_keys(cls, source: str = "") -> "set[str]":
        """Params relevant to the panel's current input — drives row visibility.

        Implements the same contract the DCC bridges' ``referenced_keys`` does
        (given the panel's current input descriptor, return the relevant keys), but
        this single-runner panel's input is the run **mode** (the ``--stop-after``
        value: ``""`` / ``"align"`` / ``"refine"``), not template script text scanned
        for ``__TOKEN__`` placeholders. A stop-after mode returns only the knobs for
        stages it actually runs; full pipeline (or any unknown mode) returns every
        registered key. ``BridgeSlotsBase`` feeds this through
        ``_relevant_param_keys`` and centrally manages the show/hide + height fit.
        """
        keys = set(cls.PARAMS)
        allowed = _MODE_KEYS.get(source)
        return keys if allowed is None else keys & allowed
