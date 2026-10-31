# !/usr/bin/python
# coding=utf-8
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
    # The startup banner's formatter is the launcher's (``Tcl.banner``).
    "greeting": ("tentacle.Tcl.greeting", "0.17.0"),
    # Panels merged into one tool (``slots.tools.RENAMED_FROM``).
    "BlenderBridgeSlots": ("tentacle.slots.tools.dcc_bridge.DccBridgeSlots", "0.17.0"),
    "MayaBridgeSlots": ("tentacle.slots.tools.dcc_bridge.DccBridgeSlots", "0.17.0"),
    "WorkspaceMapSlots": ("tentacle.slots.tools.workspaces.WorkspacesSlots", "0.17.0"),
    "WorkspaceEditorSlots": (
        "tentacle.slots.tools.workspaces.WorkspacesSlots",
        "0.17.0",
    ),
    # The native-menu wrappers (slots/maya, slots/blender): the chord menu's pages
    # need no Slots class; each host's UI handler builds its own menus.
    "BlenderSlots": ("blendertk.BlenderUiHandler", "0.17.0"),
    "ArnoldSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "CacheSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "ConstrainSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "ControlSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "CurvesSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "DeformSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "EditMeshSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "EffectsSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "FieldsSolversSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "FluidsSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "GenerateSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "HelpSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "KeySlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "LightingShadingSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "MashSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "MeshDisplaySlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "MeshSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "MeshToolsSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "NClothSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "NConstraintSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "NHairSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "NParticlesSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "PlaybackSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "RenderSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "SelectSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "SkeletonSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "SkinSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "StereoSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "SurfacesSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "TexturingSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "ToonSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "VisualizeSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    "WindowsSlots": ("mayatk.MayaUiHandler", "0.17.0"),
    # The per-host Slots classes' handlers (slots/maya, slots/blender) composed
    # into one Slots class per category (2026-10-28): each now serves both hosts
    # from slots/<category>.py, or its widget left the panel.
    "EditorsSlots.b006_init": ("tentacle.slots.editors.EditorsSlots", "0.17.0"),
    "EditorsSlots.b007_init": ("tentacle.slots.editors.EditorsSlots", "0.17.0"),
    "EditorsSlots.b008_init": ("tentacle.slots.editors.EditorsSlots", "0.17.0"),
    "EditorsSlots.b012_init": ("tentacle.slots.editors.EditorsSlots", "0.17.0"),
    "EditorsSlots.b013_init": ("tentacle.slots.editors.EditorsSlots", "0.17.0"),
    "HudSelectionMixin": ("tentacle.slots.hud.HudSlots", "0.17.0"),
    "StatusMixin": ("tentacle.slots.hud.HudSlots", "0.17.0"),
    "WarningsMixin": ("tentacle.slots.hud.HudSlots", "0.17.0"),
    "LightingSlots.b002_init": ("tentacle.slots.lighting.LightingSlots", "0.17.0"),
    "MaterialsSlots.b_shader_editor": (
        "tentacle.slots.materials.MaterialsSlots",
        "0.17.0",
    ),
    "PolygonsSlots.b038_init": ("tentacle.slots.polygons.PolygonsSlots", "0.17.0"),
    "SceneSlots.b008": ("tentacle.slots.scene.SceneSlots", "0.17.0"),
    "TransformSlots.tb004": ("tentacle.slots.transform.TransformSlots", "0.17.0"),
    "DisplaySlots.b000": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b001": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b002": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b003": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b004": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b005": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b006": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b007": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b009": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b011": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b012": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b021": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b022": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b023": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "DisplaySlots.b024": ("tentacle.slots.display.DisplaySlots", "0.17.0"),
    "EditorsSlots.getEditorWidget": ("tentacle.slots.editors.EditorsSlots", "0.17.0"),
    "NurbsSlots.b016": ("tentacle.slots.nurbs.NurbsSlots", "0.17.0"),
    "RiggingSlots.chk000": ("tentacle.slots.rigging.RiggingSlots", "0.17.0"),
    "RiggingSlots.chk001": ("tentacle.slots.rigging.RiggingSlots", "0.17.0"),
    "RiggingSlots.chk002": ("tentacle.slots.rigging.RiggingSlots", "0.17.0"),
    "RiggingSlots.s000": ("tentacle.slots.rigging.RiggingSlots", "0.17.0"),
    "SelectionSlots.chkxxx": ("tentacle.slots.selection.SelectionSlots", "0.17.0"),
    "SelectionSlots.get_selection_tool": (
        "tentacle.slots.selection.SelectionSlots",
        "0.17.0",
    ),
    "SelectionSlots.set_selection_tool": (
        "tentacle.slots.selection.SelectionSlots",
        "0.17.0",
    ),
    "SubdivisionSlots.smoothProxy": (
        "tentacle.slots.subdivision.SubdivisionSlots",
        "0.17.0",
    ),
    "TransformSlots.setTransformSnap": (
        "tentacle.slots.transform.TransformSlots",
        "0.17.0",
    ),
}


bootstrap_package(
    globals(),
    include=DEFAULT_INCLUDE,
    moved=MOVED_NAMES,
)


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
