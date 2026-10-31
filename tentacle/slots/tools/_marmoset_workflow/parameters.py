# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the Marmoset Workflow panel.

Each entry maps a placeholder token (e.g. ``__SKY_PRESET__``) to an
``AttributeSpec`` widget spec. ``BridgeSlotsBase`` scans the selected
template for these tokens, shows only the matching widgets, and the slot
passes the collected values to :meth:`MarmosetEngine.send` as a plain
dict (extapps' engine merges them over its ``template_params.DEFAULTS`` and
substitutes them into ``templates/*.py``).

This panel is scoped to "open + set up a project" (the ``import`` and
``lookdev`` templates), so it surfaces only the look-dev knobs. The full
bake parameter set lives with the DCC Marmoset Bridge, in
:mod:`mayatk.mat_utils.marmoset_bridge.parameters`. Defaults mirror the
engine's token defaults (extapps' ``marmoset_workflow/template_params.py``).
"""

from __future__ import annotations


from tentacle import Slots

AttributeSpec, ParamRegistry = Slots.AttributeSpec, Slots.ParamRegistry


# Display order is iteration order over this dict.
PARAMS: "dict[str, AttributeSpec]" = {
    "SKY_PRESET": AttributeSpec(
        key="SKY_PRESET",
        label="Sky",
        kind="choice",
        default="Marmoset Skies/Hangar.tbsky",
        choices=[
            ("Hangar", "Marmoset Skies/Hangar.tbsky"),
            ("Studio Light", "Marmoset Skies/Studio Light.tbsky"),
            ("Sunset", "Marmoset Skies/Sunset.tbsky"),
            ("Overcast", "Marmoset Skies/Overcast.tbsky"),
        ],
        tooltip="Built-in Toolbag sky preset to apply when the scene opens.",
    ),
    "FRAME_SELECTION": AttributeSpec(
        key="FRAME_SELECTION",
        label="Frame on Open",
        kind="bool",
        default=True,
        tooltip="Auto-frame the imported model in the viewport.",
    ),
}


class Parameters(ParamRegistry):
    """The Marmoset Workflow panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module``: :data:`PARAMS` plus
    ``referenced_keys`` / ``defaults`` / ``render_context`` (Python literals).
    """

    PARAMS = PARAMS
