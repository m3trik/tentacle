# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the RealityCapture Workflow panel.

Like the Metashape panel, this drives a single headless runner —
:mod:`extapps.photogrammetry.realityscan_workflow.run_combined` — so each
:class:`AttributeSpec` is keyed by the **semantic name the runner / preset JSON
use** and :meth:`Parameters.to_argv` renders the collected values into ``run_combined`` CLI
flags.

RealityScan's automation surface is deliberately thin: its strongest noise levers
(image/depth downscale, depth-map filtering, a tight reconstruction region,
masking) are GUI / per-project-Settings only and can't be reached from the CLI
(see TUNING.md). So the panel exposes only RC's CLI-reachable knobs — the quality
tier, the mesh-cleanup floor + simplify target — plus the shared input
pre-processing (curate + equalize), which runs before RC in the panel's own
Python.
"""

from __future__ import annotations

from typing import Any, Dict, List

from extapps import QUALITY_TIERS

from tentacle import Slots

AttributeSpec, ParamRegistry = Slots.AttributeSpec, Slots.ParamRegistry

from .shared_parameters import (
    PREPROCESSING_KEYS,
    PREPROCESSING_PARAMS,
    SharedParams,
)


# Display order is iteration order over this dict. Keys mirror the run_combined
# CLI flags / profile preset keys exactly. Input image pre-processing leads the
# panel (it runs first in the pipeline — order of operations), so the shared
# specs are merged in *first*; RC's reconstruction / cleanup params follow.
PARAMS: "Dict[str, AttributeSpec]" = dict(PREPROCESSING_PARAMS)
PARAMS.update(
    {
        "quality": AttributeSpec(
            key="quality",
            label="Quality",
            kind="choice",
            # SSoT: profile.QUALITY_TIERS — a hardcoded copy here could drift
            # from the four runners that were already converted to it.
            default="balanced",
            choices=list(QUALITY_TIERS),
            tooltip="Reconstruction quality → RC's mesh preset (draft=preview / "
            "balanced=normal / max=high). Maps to --quality.",
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
            label="Save .rsproj Project",
            kind="bool",
            default=False,
            tooltip="Keep a reopenable RC project (.rsproj) so a later run can reopen "
            "it and re-run only some stages. Default off removes the local "
            ".rsproj after export, leaving only deliverables. Emits "
            "--save-project.",
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
            "(RC -setMinComponentSize) - the main CLI-reachable lever against "
            "floater 'snow'. 0 disables. On specular / low-texture metal do "
            "NOT crank this (strips real detail without fixing depth noise). "
            "Maps to --clean-min-component.",
        ),
        "simplify_target": AttributeSpec(
            key="simplify_target",
            label="Simplify Target",
            kind="int",
            section="Mesh Cleanup",
            default=20_000_000,
            minimum=0,
            maximum=200_000_000,
            tooltip="Simplify the high model to ~N triangles before unwrap so the UV "
            "atlas fits the texture budget (fixes RC's unwrap-overflow). "
            "Texture quality is unaffected (bakes from the photos). 0 = no "
            "simplify. Maps to --simplify.",
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
            "scans. Needs extapps[mesh]. Maps to --mesh-remesh-pct.",
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
            "exported mesh to this face count (0 = off) - adaptive density, "
            "distinct from the RC-native pre-unwrap Simplify Target. Needs "
            "extapps[mesh]. Maps to --mesh-decimate-faces.",
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


# Value params -> CLI flags that take an argument (always emitted). The shared
# input-pre-processing flags are rendered separately via ``SharedParams.preprocessing_argv``
# (its master toggle gates them).
_VALUE_FLAGS: "Dict[str, str]" = {
    "quality": "--quality",
    "gate_mode": "--gate-mode",
    "min_component_size": "--clean-min-component",
    "simplify_target": "--simplify",
    # Mesh processing (PyMeshLab, post-export).
    "mesh_remesh_pct": "--mesh-remesh-pct",
    "mesh_decimate_faces": "--mesh-decimate-faces",
    "bake_vertex_color": "--bake-vertex-color",
}

# Bool params -> store_true flags (emitted only when truthy).
_STORE_TRUE_FLAGS: "Dict[str, str]" = {
    "save_project": "--save-project",
}


class Parameters(ParamRegistry):
    """The RealityScan panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

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
        argv = SharedParams.render_flag_argv(values, _VALUE_FLAGS, _STORE_TRUE_FLAGS)
        # Shared input pre-processing (curate + equalize), gated by its master toggle.
        argv += SharedParams.preprocessing_argv(values)
        return argv

    @classmethod
    def referenced_keys(cls, source: str = "") -> "set[str]":
        """Params relevant to the panel's current input — drives row visibility.

        RealityScan has no ``--stop-after`` run modes, so the Full-pipeline mode
        shows every registered param; the shared Prep-preview mode (a curation
        dry-run) shows only the pre-processing knobs. Same relevance contract as
        the Metashape panel (the panel + bridge base consume this the same way).
        """
        keys = set(cls.PARAMS)
        if source == "prep_preview":
            return keys & PREPROCESSING_KEYS
        return keys
