# !/usr/bin/python
# coding=utf-8
import sys

from pythontk.core_utils.module_resolver import bootstrap_package

__package__ = "tentacle"
__version__ = "0.16.4"


DEFAULT_INCLUDE = {
    "tcl": "Tcl",  # host-detecting launcher — the documented entry point for every DCC
    "tcl_blender": "TclBlender",
    "tcl_max": "TclMax",
    "tcl_maya": "TclMaya",
    "slots._slots": "Slots",
}

#: Public names merged away (CODE_STANDARD section 5): no alias, so a read raises
#: MovedNameError naming the new home. ``{name: (new home, version)}``; a category
#: composed into one Slots class lists the mixin its forks shared.
MOVED_NAMES = {
    "NormalsMixin": ("tentacle.slots.normals.NormalsSlots", "0.17.0"),
    "SlotsMaya": ("tentacle.Slots", "0.17.0"),
    "SlotsBlender": ("tentacle.Slots", "0.17.0"),
    "DisplayMixin": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DuplicateMixin": ("tentacle.slots.duplicate.DuplicateSlots", "0.17.0"),
    "LightingMixin": ("tentacle.slots.lighting.LightingSlots", "0.17.0"),
    "HudWarningsMixin": ("tentacle.slots.hud.HudSlots", "0.17.0"),
    "EditMixin": ("tentacle.slots.edit.EditSlots", "0.17.0"),
    "MainMixin": ("tentacle.slots.main.MainSlots", "0.17.0"),
    "PivotMixin": ("tentacle.slots.pivot.PivotSlots", "0.17.0"),
    "PreferencesMixin": ("tentacle.slots.preferences.PreferencesSlots", "0.17.0"),
    "SettingsMixin": ("tentacle.slots.settings.SettingsSlots", "0.17.0"),
    "SelectionMixin": ("tentacle.slots.selection.SelectionSlots", "0.17.0"),
    "NurbsMixin": ("tentacle.slots.nurbs.NurbsSlots", "0.17.0"),
    "TransformMixin": ("tentacle.slots.transform.TransformSlots", "0.17.0"),
    "RiggingMixin": ("tentacle.slots.rigging.RiggingSlots", "0.17.0"),
    "RenderingMixin": ("tentacle.slots.rendering.RenderingSlots", "0.17.0"),
    "MaterialsMixin": ("tentacle.slots.materials.MaterialsSlots", "0.17.0"),
    "SceneMixin": ("tentacle.slots.scene.SceneSlots", "0.17.0"),
    "UvMixin": ("tentacle.slots.uv.UvSlots", "0.17.0"),
    "AnimationMixin": ("tentacle.slots.animation.AnimationSlots", "0.17.0"),
    # Panels merged into one tool (``slots.tools.RENAMED_FROM``).
    "BlenderBridgeSlots": ("tentacle.slots.tools.dcc_bridge.DccBridgeSlots", "0.17.0"),
    "MayaBridgeSlots": ("tentacle.slots.tools.dcc_bridge.DccBridgeSlots", "0.17.0"),
    "WorkspaceMapSlots": ("tentacle.slots.tools.workspaces.WorkspacesSlots", "0.17.0"),
    "WorkspaceEditorSlots": (
        "tentacle.slots.tools.workspaces.WorkspacesSlots",
        "0.17.0",
    ),
}


bootstrap_package(
    globals(),
    include=DEFAULT_INCLUDE,
    moved=MOVED_NAMES,
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
        print(result)  # noqa: T201 -- greeting() prints only when asked to
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
