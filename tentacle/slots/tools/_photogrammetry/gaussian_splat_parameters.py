# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the Brush (gaussian-splat) Workflow panel.

Drives the single headless runner
:mod:`extapps.photogrammetry.gaussian_splat_workflow.run_combined`, so each
:class:`AttributeSpec` is keyed by the **semantic name the runner / preset JSON
use** and :meth:`Parameters.to_argv` renders the collected values into ``run_combined`` CLI
flags. The two run modes are ``""`` (Train only) and ``"publish"`` (Train +
Publish); :meth:`Parameters.referenced_keys` hides the Publish-section knobs in Train-only.
"""

from __future__ import annotations

from typing import Any, Dict, List

from tentacle import Slots

AttributeSpec, ParamRegistry = Slots.AttributeSpec, Slots.ParamRegistry

from .shared_parameters import SharedParams


# Display order is iteration order over this dict. Keys mirror the run_combined
# CLI flags / profile preset keys exactly.
PARAMS: "Dict[str, AttributeSpec]" = {
    # --- Brush splat training -----------------------------------------------
    "total_steps": AttributeSpec(
        key="total_steps",
        label="Total Steps",
        kind="int",
        default=30000,
        minimum=1000,
        maximum=100000,
        tooltip="Brush training steps. More steps is a VRAM-free quality lever on "
        "an 8-10 GB card (draft 7k / balanced 30k / max 50k). Maps to "
        "--total-steps.",
    ),
    "max_resolution": AttributeSpec(
        key="max_resolution",
        label="Max Resolution",
        kind="int",
        default=1920,
        minimum=512,
        maximum=7680,
        tooltip="Input long-edge cap. 1920 — A/B showed no gain from 3840 at the "
        "gaussian budget an 8 GB GPU holds. Maps to --max-resolution.",
    ),
    "max_splats": AttributeSpec(
        key="max_splats",
        label="Max Splats",
        kind="int",
        default=10_000_000,
        minimum=100_000,
        maximum=30_000_000,
        tooltip="Upper bound on gaussians; Brush's stock growth settles ~2.5-3M "
        "on 8 GB. Maps to --max-splats.",
    ),
    "sh_degree": AttributeSpec(
        key="sh_degree",
        label="SH Degree",
        kind="int",
        default=3,
        minimum=0,
        maximum=3,
        tooltip="Spherical-harmonics degree (view-dependent colour detail; "
        "0 = flat). Maps to --sh-degree.",
    ),
    # --- Publish (engine delivery — Train + Publish mode only) --------------
    "publish_targets": AttributeSpec(
        key="publish_targets",
        label="Targets",
        kind="str",
        section="Publish",
        default="unity,web",
        tooltip="Comma-separated engine targets for the publish stage: unity "
        "(.spz) and/or web (.sog + .html viewer). Maps to "
        "--publish-targets.",
    ),
    "web_format": AttributeSpec(
        key="web_format",
        label="Web Format",
        kind="choice",
        section="Publish",
        default="sog",
        choices=["sog", "compressed-ply"],
        tooltip="Browser data format for the web target. Maps to --web-format.",
    ),
    "spz_version": AttributeSpec(
        key="spz_version",
        label="SPZ Version",
        kind="choice",
        section="Publish",
        default="4",
        choices=["4", "3"],
        tooltip="SPZ format version for the Unity .spz. Maps to --spz-version.",
    ),
}


# Value params -> CLI flags that take an argument (always emitted).
_VALUE_FLAGS: "Dict[str, str]" = {
    "total_steps": "--total-steps",
    "max_resolution": "--max-resolution",
    "max_splats": "--max-splats",
    "sh_degree": "--sh-degree",
    "publish_targets": "--publish-targets",
    "web_format": "--web-format",
    "spz_version": "--spz-version",
}


# Which params apply per run mode: training knobs always; the Publish-section
# knobs only in the "publish" (Train + Publish) mode.
_TRAIN_KEYS = frozenset({"total_steps", "max_resolution", "max_splats", "sh_degree"})
_PUBLISH_KEYS = frozenset({"publish_targets", "web_format", "spz_version"})


class Parameters(ParamRegistry):
    """The Brush (gaussian-splat) panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module``: :data:`PARAMS` plus
    ``defaults``; ``referenced_keys`` is the run-mode relevance and ``to_argv``
    renders the ``run_combined`` flags.
    """

    PARAMS = PARAMS

    @staticmethod
    def to_argv(values: "Dict[str, Any]") -> "List[str]":
        """Render collected param *values* into ``run_combined`` CLI flags via the
        shared :func:`render_flag_argv` emit rules (Brush has no store-true flags or
        input pre-processing). Keys absent from *values* are skipped."""
        return SharedParams.render_flag_argv(values, _VALUE_FLAGS)

    @classmethod
    def referenced_keys(cls, source: str = "") -> "set[str]":
        """Params relevant to the selected run mode — drives row visibility. Train
        only (``""``) shows the training knobs; Train + Publish (``"publish"``) adds
        the Publish section."""
        keys = set(_TRAIN_KEYS)
        if source == "publish":
            keys |= _PUBLISH_KEYS
        return keys
