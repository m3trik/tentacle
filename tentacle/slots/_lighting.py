# !/usr/bin/python
# coding=utf-8
"""Shared surface for the ``lighting`` panel's Maya and Blender forks.

Both forks build the same *Lights From Geometry* option box over their own
engine (``mtk.LightUtils`` / ``btk.LightUtils``), so the controls are per fork —
what is shared is the colour-temperature reference the Kelvin field documents,
which is physics and reads the same in either host.
"""


class LightingMixin:
    """Behaviour and reference data shared by both ``lighting`` forks."""

    #: Real-world sources at each colour temperature, for the Kelvin field's
    #: tooltip. Kelvin is the one light property the panel still owns -- it is
    #: the FALLBACK the light derivation uses when the fixture's material names
    #: no emission colour, not a dial for lights that already exist -- and a
    #: bare number is unguessable, so the tooltip names things the artist has
    #: actually seen at each level.
    #:
    #: Rich text, and a ``<pre>`` block: Qt renders tooltip HTML, and only a
    #: preformatted block keeps both the newlines and the column. The font stack
    #: is explicit because Qt's generic ``monospace`` alias resolves per platform.
    KELVIN_REFERENCE = (
        "<pre style=\"font-family: Consolas, 'Courier New', monospace\">"
        "1700 K   match flame\n"
        "1900 K   candlelight\n"
        "2400 K   incandescent bulb, dimmed\n"
        "2700 K   soft-white bulb, warm halogen\n"
        "3000 K   warm-white LED, film tungsten\n"
        "3500 K   office troffer, warm end\n"
        "4100 K   cool-white fluorescent\n"
        "5000 K   horizon daylight, neutral white\n"
        "5500 K   midday sun, camera flash\n"
        "6500 K   overcast sky, monitor white\n"
        "7500 K   shade under a blue sky\n"
        "9000 K   clear blue northern sky"
        "</pre>"
    )

    #: Value the Kelvin field starts on — horizon daylight, which reads neutral
    #: rather than casting every fixture warm.
    DEFAULT_KELVIN = 5000

    @classmethod
    def kelvin_tooltip(cls, lead: str, tail: str) -> str:
        """*lead*, then the reference table, then *tail*.

        The wording either side is per fork (Maya's Kelvin is a fallback behind
        the material's own emission; Blender's drives the light's blackbody
        directly), so only the table and the assembly are shared.
        """
        return f"{lead}{cls.KELVIN_REFERENCE}{tail}"
