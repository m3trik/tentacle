# !/usr/bin/python
# coding=utf-8
"""Input pre-processing parameter specs shared by the image-in engines.

Metashape and RealityScan both run the identical pre-SfM curation (dHash +
sharpness culling) and cross-capture exposure equalization, and expose the same
``--curate-*`` / ``--equalize-*`` flags. So the :class:`uitk.bridge.AttributeSpec`
widgets + their flag mappings are defined **once** here and merged into each
engine's ``<engine>_parameters.PARAMS`` — **first**, so the section leads the panel in
pipeline order (pre-processing runs before alignment). Brush has no image
pre-processing, so it doesn't use these.

A master :data:`PREPROCESS_MASTER_KEY` toggle (``preprocess_input``) gates the
whole stage: on, the per-stage knobs show and run; off, they collapse and the
stage is skipped wholesale (``--skip-curate --skip-equalize``). The argv
rendering lives once in :func:`preprocessing_argv`, and the panel collapses the
knobs via :data:`PREPROCESSING_KNOB_KEYS`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from tentacle import Slots

AttributeSpec = Slots.AttributeSpec

_SECTION = "Input Pre-processing"

# The master enable/disable toggle for the whole pre-processing stage.
PREPROCESS_MASTER_KEY = "preprocess_input"

# Display order is iteration order; keys mirror the run_combined CLI flags /
# profile preset keys exactly. The master toggle leads the section.
PREPROCESSING_PARAMS: "Dict[str, AttributeSpec]" = {
    "preprocess_input": AttributeSpec(
        key="preprocess_input", label="Pre-process Input", kind="bool",
        section=_SECTION, default=True,
        tooltip="Master switch for the input-image pre-processing stage that "
                "runs before alignment (dHash + sharpness curation, then "
                "cross-capture exposure equalization). On: the knobs below "
                "apply. Off: the whole stage is skipped (the engine sees the "
                "frames as-is) and the knobs collapse.",
    ),
    "skip_curate": AttributeSpec(
        key="skip_curate", label="Skip Curate", kind="bool", section=_SECTION,
        default=False,
        tooltip="Skip the pre-SfM dHash + sharpness culling pass. "
                "Emits --skip-curate.",
    ),
    "curate_hash_threshold": AttributeSpec(
        key="curate_hash_threshold", label="Dedup Threshold", kind="int",
        section=_SECTION,
        default=0, minimum=0, maximum=32,
        tooltip="Near-duplicate culling: dHash Hamming distance for clustering "
                "(--curate-hash-threshold). Default 0 = no dedup (keep all; "
                "blur culling still applies) - right for continuous video / "
                "single-pass captures, whose near-identical frames carry the "
                "small-baseline overlap SfM triangulates from. 5 = "
                "near-identical only; use for redundant static photo sets.",
    ),
    "curate_sharpness_percentile": AttributeSpec(
        key="curate_sharpness_percentile", label="Blur Cutoff %", kind="float",
        default=0.0, minimum=0.0, maximum=100.0, decimals=1,
        section=_SECTION,
        tooltip="Drop frames below this percentile of the set's own sharpness "
                "distribution (--curate-sharpness-percentile). Default 0 = off: "
                "a percentile cut always removes that share of the set even "
                "when every frame is sharp (video frames are already "
                "sharpest-per-window at extraction); Min Sharpness Frac below "
                "handles genuinely defocused frames.",
    ),
    "curate_min_sharpness_frac": AttributeSpec(
        key="curate_min_sharpness_frac", label="Min Sharpness Frac", kind="float",
        section=_SECTION,
        default=0.15, minimum=0.0, maximum=1.0, decimals=2,
        tooltip="Also drop frames below this fraction of the survivor-median "
                "sharpness (--curate-min-sharpness-frac), catching catastrophically "
                "defocused frames the percentile misses. 0 disables.",
    ),
    "keep_per_cluster": AttributeSpec(
        key="keep_per_cluster", label="Keep / Cluster", kind="int",
        section=_SECTION,
        default=1, minimum=1, maximum=10,
        tooltip="Keep the top-K sharpest frames per near-duplicate cluster "
                "(--keep-per-cluster).",
    ),
    "skip_equalize": AttributeSpec(
        key="skip_equalize", label="Skip Equalize", kind="bool", section=_SECTION,
        default=False,
        tooltip="Skip cross-session exposure equalization. Emits --skip-equalize.",
    ),
    "equalize_strength": AttributeSpec(
        key="equalize_strength", label="Equalize Strength", kind="float",
        section=_SECTION,
        default=0.5, minimum=0.0, maximum=1.0, decimals=2,
        tooltip="Cross-capture exposure-match blend 0-1 (--equalize-strength). "
                "Below 1 preserves each frame's local contrast; 1.0 = full match. "
                "Only applies with 2+ captures.",
    ),
    "equalize_reference": AttributeSpec(
        key="equalize_reference", label="Equalize Ref", kind="choice",
        section=_SECTION,
        default="median", choices=["first", "median", "global"],
        tooltip="Target distribution for exposure equalization "
                "(--equalize-reference). 'median' avoids letting the first "
                "capture's color cast dominate.",
    ),
    "video_window_sec": AttributeSpec(
        key="video_window_sec", label="Video Window (s)", kind="float",
        section=_SECTION,
        default=1.0, minimum=0.1, maximum=10.0, decimals=2,
        tooltip="Video-source extraction window in seconds - one sharpest "
                "frame is kept per window. Read by the panel's Source browser "
                "when a video is picked (the headless Metashape runner's "
                "--video path exposes the same knob as --video-window-sec). "
                "1.0 (~1 fps) suits a slow orbit; lower it (0.25-0.5) for "
                "fast handheld moves so small-baseline overlap isn't starved.",
    ),
}

# Value params -> CLI flags that take an argument (always emitted).
# ``video_window_sec`` is deliberately absent: extraction happens panel-side at
# pick time (FramesSourceMixin reads the widget), and the RC runner has no
# --video path to accept such a flag.
PREPROCESSING_VALUE_FLAGS: "Dict[str, str]" = {
    "curate_hash_threshold": "--curate-hash-threshold",
    "curate_sharpness_percentile": "--curate-sharpness-percentile",
    "curate_min_sharpness_frac": "--curate-min-sharpness-frac",
    "keep_per_cluster": "--keep-per-cluster",
    "equalize_strength": "--equalize-strength",
    "equalize_reference": "--equalize-reference",
}

# Bool params -> store_true flags (emitted only when truthy).
PREPROCESSING_STORE_TRUE_FLAGS: "Dict[str, str]" = {
    "skip_curate": "--skip-curate",
    "skip_equalize": "--skip-equalize",
}

# Pre-processing runs before alignment, so it applies in every run mode.
PREPROCESSING_KEYS = frozenset(PREPROCESSING_PARAMS)

# Knob keys that collapse when the master toggle is off (everything but the
# master itself — the panel keeps the toggle visible so the stage can be
# re-enabled — and the video-extraction window, which applies at Source-pick
# time regardless of whether curation/equalization run). Used by the panel
# base's visibility gate.
PREPROCESSING_KNOB_KEYS = frozenset(PREPROCESSING_PARAMS) - {
    PREPROCESS_MASTER_KEY, "video_window_sec",
}


class SharedParams:
    """Argv renderers shared by the image-in engines' ``<engine>_parameters`` modules.

    A class rather than module functions per the encapsulation standard. The
    module still exposes the ``PARAMS``/key **data** flat, because that half is
    merged into each engine's ``<engine>_parameters.PARAMS`` dict, which uitk's
    ``BridgeSlotsBase`` reads as a module attribute.
    """

    @staticmethod
    def render_flag_argv(
        values: "Dict[str, Any]",
        value_flags: "Dict[str, str]",
        store_true_flags: "Optional[Dict[str, str]]" = None,
        bool_flags: "Optional[Dict[str, str]]" = None,
    ) -> "List[str]":
        """Render *values* into CLI flags — the shared loop behind every engine's
        ``to_argv`` (and :func:`preprocessing_argv`), so the emit rules stay
        identical everywhere.

        ``value_flags`` always emit their argument when the key is present and the
        value isn't ``None`` / empty (the widget always holds a concrete value);
        ``store_true_flags`` emit their bare flag only when the value is truthy.
        ``bool_flags`` map to argparse ``BooleanOptionalAction`` flags and always
        emit — ``--flag`` when truthy, ``--no-flag`` when falsy — which is what
        lets a panel checkbox turn OFF a runner default that is on (a store_true
        flag can only ever push toward true). Keys absent from *values* are
        skipped, so a partial dict (e.g. a preset overlay) renders cleanly.
        """
        argv: List[str] = []
        for key, flag in value_flags.items():
            if key not in values:
                continue
            val = values[key]
            if val is None or str(val) == "":
                continue
            argv += [flag, str(val)]
        for key, flag in (store_true_flags or {}).items():
            if values.get(key):
                argv.append(flag)
        for key, flag in (bool_flags or {}).items():
            if key not in values:
                continue
            argv.append(flag if values[key] else "--no-" + flag.lstrip("-"))
        return argv

    @staticmethod
    def preprocessing_argv(values: "Dict[str, Any]") -> "List[str]":
        """Render the input pre-processing CLI flags from collected *values*.

        Single source of truth for the pre-processing argv across the image-in
        engines (each engine's ``to_argv`` appends this). The master
        ``preprocess_input`` toggle gates the whole stage: when present and falsey,
        the stage is skipped wholesale (``--skip-curate --skip-equalize``) and the
        per-stage knobs are moot, so only those two flags emit. Otherwise the
        per-stage skips (store-true) + value knobs render normally (an absent master
        key defaults to enabled).
        """
        if PREPROCESS_MASTER_KEY in values and not values[PREPROCESS_MASTER_KEY]:
            return ["--skip-curate", "--skip-equalize"]
        return SharedParams.render_flag_argv(
            values, PREPROCESSING_VALUE_FLAGS, PREPROCESSING_STORE_TRUE_FLAGS
        )
