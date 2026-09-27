# !/usr/bin/python
# coding=utf-8
import sys

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "tentacle"
__version__ = "0.14.0"


DEFAULT_INCLUDE = {
    "tcl": "Tcl",  # host-detecting launcher — the documented entry point for every DCC
    "tcl_blender": "TclBlender",
    "tcl_max": "TclMax",
    "tcl_maya": "TclMaya",
    "slots._slots": "Slots",
    "slots.maya._slots_maya": "SlotsMaya",
    "slots.blender._slots_blender": "SlotsBlender",
    # Per-panel shared mixins (slots/_<panel>.py). Registered so a concrete panel
    # pulls its mixin and its DCC base from ONE package-namespace import
    # (``from tentacle import SceneMixin, SlotsMaya``) instead of two deep module
    # paths. They are deliberately NOT folded into the DCC bases: nearly every
    # mixin defines widget-named slot methods (SceneMixin.tb002,
    # MaterialsMixin.b003, PreferencesMixin.cmb004/cmb005), and those
    # objectNames are reused across panels — 12 .ui files carry a ``tb002``,
    # only 8 Maya slot files define one. Inherited from a shared base, the
    # panels that DON'T define their own would silently bind their widget to
    # another panel's slot. Mixing in per panel keeps each name owned by exactly
    # the panels that opted in.
    # AnimationMixin, too, now defines a widget-named slot (``list000_init``, the
    # Tools list both forks build identically), so it is mixed in per panel for
    # the same reason as the rest.
    "slots._animation": "AnimationMixin",
    "slots._display": "DisplayMixin",
    "slots._duplicate": "DuplicateMixin",
    "slots._edit": "EditMixin",
    "slots._hud_warnings": "HudWarningsMixin",
    "slots._lighting": "LightingMixin",
    "slots._main": "MainMixin",
    "slots._materials": "MaterialsMixin",
    "slots._normals": "NormalsMixin",
    "slots._nurbs": "NurbsMixin",
    "slots._pivot": "PivotMixin",
    "slots._preferences": "PreferencesMixin",
    "slots._rendering": "RenderingMixin",
    "slots._rigging": "RiggingMixin",
    "slots._scene": "SceneMixin",
    "slots._selection": "SelectionMixin",
    "slots._settings": "SettingsMixin",
    "slots._transform": "TransformMixin",
    "slots._uv": "UvMixin",
}


bootstrap_package(
    globals(),
    include=DEFAULT_INCLUDE,
)


def greeting(string, outputToConsole=True):
    """Format a string using preset variables.

    Parameters:
        string (str): The greeting to format as a string with placeholders using the below keywords.
                ex. 'Good {hr}! You are using {modver} with {pyver}.'
                {hr} - Gives the current time of day (morning, afternoon, evening)
                {pyver} - The python interpreter version.
                {modver} - This modules version.
        outputToConsole = Print the greeting.

    Returns:
        (str)

    Example: greeting('Good {hr}! You are using {modver} with {pyver}.')
    """
    import datetime

    h = datetime.datetime.now().hour
    hr = "morning" if 5 <= h < 12 else "afternoon" if h < 18 else "evening"

    pyver = "python v{}.{}.{}".format(
        sys.version_info[0], sys.version_info[1], sys.version_info[2]
    )

    modver = "tentacle v{}".format(__version__)

    result = string.format(hr=hr, pyver=pyver, modver=modver)

    if outputToConsole:
        print(result)
    return result


# --------------------------------------------------------------------------------------------
# The startup banner is NOT issued here: ``import tentacle`` must have no side effects
# (root CLAUDE.md), and the package is imported by test collectors, the API-registry
# generator and other tooling that has no business printing. ``Tcl.launch`` — the
# documented entry point for every DCC — issues it instead, so a real launch still
# banners (and Blender's ScriptConsole capture, installed before the import, still
# catches it: the launch call happens after).

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
# Test: 222117
