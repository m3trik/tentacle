# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
import pythontk as ptk
from tentacle import SlotsMaya

# The class's name before it took the ``<Base>Slots`` suffix: mayatk's tests import
# it by module path, so it resolves (with a DeprecationWarning) for one release.
ptk.Deprecation.attributes(
    globals(),
    {"Editors": "tentacle.slots.maya.editors.EditorsSlots"},
    remove_in="0.15.0",
    since="2026-09-26",
)


class EditorsSlots(SlotsMaya):
    # (category -> [editor friendly-names]) for the lower-submenu list. Every
    # name is a key of ``mtk.UiUtils.get_editor_types()``, which owns the
    # name -> runtime-command registry (the mirror of the Blender slot's
    # ``btk.get_editor_types()``); the list is filtered against it at init, so
    # no row can dead-end.
    _EDITORS = {
        "General Editors": [
            "Attribute Editor",
            "Channel Box",
            "Layer Editor",
            "Content Browser",
            "Tool Settings",
            "Hypergraph: Hierarchy",
            "Hypergraph: Connections",
            "Viewport",
            "Adobe After Effects Live Link",
            "Asset Editor",
            "Attribute Spread Sheet",
            "Component Editor",
            "Channel Control",
            "Display Layer Editor",
            "File Path Editor",
            "Namespace Editor",
            "Reference Editor",
            "Script Editor",
            "Command Shell",
            "Profiler",
            "Evaluation Toolkit",
        ],
        "Modeling Editors": [
            "Modeling Toolkit",
            "Paint Effects",
            "UV Editor",
            "XGen Editor",
            "Crease Sets",
        ],
        "Animation Editors": [
            "Graph Editor",
            "Time Editor",
            "Trax Editor",
            "Camera Sequencer",
            "Dope Sheet",
            "Quick Rig",
            "HumanIK",
            "Shape Editor",
            "Pose Editor",
            "Expression Editor",
        ],
        "Rendering Editors": [
            "Render View",
            "Render Settings",
            "Hypershade",
            "Render Setup",
            "Light Editor",
            "Custom Stereo Rig Editor",
            "Rendering Flags",
            "Shading Group Attributes",
        ],
        "Relationship Editors": [
            "Animation Layers",
            "Camera Sets",
            "Character Sets",
            "Deformer Sets",
            "Display Layers",
            "Dynamic Relationships",
            "Light Linking: Light Centric",
            "Light Linking: Object Centric",
            "Partitions",
            "Render Pass Sets",
            "Sets",
            "UV Linking: Texture-Centric",
            "UV Linking: UV-Centric",
            "UV Linking: Paint Effects/UV",
            "UV Linking: Hair/UV",
        ],
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.editors

    def list000_init(self, widget):
        """Initialize the editors list (categories -> Maya editors), filtered
        against ``mtk.UiUtils.get_editor_types()`` so every row opens."""
        widget.fixed_item_height = 18
        valid = mtk.UiUtils.get_editor_types()
        for category, items in self._EDITORS.items():
            items = [e for e in items if e in valid]
            if not items:
                continue
            w = widget.add(category)
            w.sublist.add(sorted(items))

    @SlotsMaya.Signals("on_item_interacted")
    def list000(self, item):
        """Open the chosen Maya editor (category headers are nav-only)."""
        text = item.item_text()
        if text not in mtk.UiUtils.get_editor_types():
            return
        if mtk.UiUtils.open_editor(text) is None:
            self.sb.message_box(f"Could not open <strong>{text}</strong>.")

    def b000(self):
        """Attributes: open the Attribute Editor."""
        mel.eval("AttributeEditor")

    def b001(self):
        """Outliner: open the Outliner window."""
        mel.eval("OutlinerWindow")

    def b002(self):
        """Tool: open the Tool Settings window."""
        cmds.toolPropertyWindow()

    def b003(self):
        """Layers: open the Channels / Layers panel."""
        mel.eval("OpenChannelsLayers")

    def b004(self):
        """Channels: open the Channels / Layers panel."""
        mel.eval("OpenChannelsLayers")

    def b005(self):
        """Node Editor: open the Node Editor window."""
        mel.eval("NodeEditorWindow")

    def b006(self):
        """Dependancy Graph

        $editorName = ($panelName+"HyperGraphEd");
        hyperGraph -e
                -graphLayoutStyle "hierarchicalLayout"
                -orientation "horiz"
                -mergeConnections 0
                -zoom 1
                -animateTransition 0
                -showRelationships 1
                -showShapes 0
                -showDeformers 0
                -showExpressions 0
                -showConstraints 0
                -showConnectionFromSelected 0
                -showConnectionToSelected 0
                -showConstraintLabels 0
                -showUnderworld 0
                -showInvisible 0
                -transitionFrames 1
                -opaqueContainers 0
                -freeform 0
                -imagePosition 0 0
                -imageScale 1
                -imageEnabled 0
                -graphType "DAG"
                -heatMapDisplay 0
                -updateSelection 1
                -updateNodeAdded 1
                -useDrawOverrideColor 0
                -limitGraphTraversal -1
                -range 0 0
                -iconSize "smallIcons"
                -showCachedConnections 0
                $editorName //
        """
        mel.eval("HypergraphHierarchyWindow")

    def b007(self):
        """Status Line: toggle the Status Line UI."""
        mel.eval("ToggleStatusLine")

    def b008(self):
        """Shelf: toggle the Shelf UI."""
        mel.eval("ToggleShelf")

    def b009(self):
        """Time & Range"""
        ts_visible = mel.eval('isUIComponentVisible "Time Slider"')
        rs_visible = mel.eval('isUIComponentVisible "Range Slider"')

        if ts_visible or rs_visible:
            if ts_visible:
                mel.eval("ToggleTimeSlider")
            if rs_visible:
                mel.eval("ToggleRangeSlider")
        else:
            mel.eval("ToggleTimeSlider")
            mel.eval("ToggleRangeSlider")

    def b010(self):
        """Script Output"""
        mtk.ScriptConsole.toggle(
            dock=("TimeSlider", "top"), tab_position="right", height=50
        )

    def b011(self):
        """Command Line"""
        mel.eval("ToggleCommandLine")

    def b012(self):
        """Help Line: toggle the Help Line UI."""
        mel.eval("ToggleHelpLine")

    def b013(self):
        """Tool Box: toggle the Toolbox UI."""
        mel.eval("ToggleToolbox")

    def getEditorWidget(self, name):
        """Get a maya widget from a given name.

        Parameters:
                name (str): name of widget
        """
        _name = "_" + name
        if not hasattr(self, _name):
            w = self.convertToWidget(name)
            self.stackedWidget.addWidget(w)
            setattr(self, _name, w)

        return getattr(self, _name)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
