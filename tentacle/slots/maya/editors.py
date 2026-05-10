# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
from uitk import Signals
from tentacle.slots.maya._slots_maya import SlotsMaya


class Editors(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.sb = switchboard
        self.ui = self.sb.loaded_ui.editors

    def list000_init(self, widget):
        """Initialize the widget with structured data for easier maintenance."""
        widget.fixed_item_height = 18

        editors_dict = {
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

        for category, items in editors_dict.items():
            w = widget.add(category)
            w.sublist.add(sorted(items))

    @Signals("on_item_interacted")
    def list000(self, item):
        """ """
        text = item.item_text()
        parent_text = item.parent_item_text()

        if parent_text == "General Editors":
            if text == "Attribute Editor":
                mel.eval("AttributeEditor")
            elif text == "Channel Box":
                mel.eval("OpenChannelBox")
            elif text == "Layer Editor":
                mel.eval("OpenLayerEditor")
            elif text == "Content Browser":
                mel.eval("OpenContentBrowser")
            elif text == "Tool Settings":
                mel.eval("ToolSettingsWindow")
            elif text == "Hypergraph: Hierarchy":
                mel.eval("HypergraphHierarchyWindow")
            elif text == "Hypergraph: Connections":
                mel.eval("HypergraphDGWindow")
            elif text == "Viewport":
                mel.eval("DisplayViewport")
            elif text == "Adobe After Effects Live Link":
                mel.eval("OpenAELiveLink")
            elif text == "Asset Editor":
                mel.eval("AssetEditor")
            elif text == "Attribute Spread Sheet":
                mel.eval("SpreadSheetEditor")
            elif text == "Component Editor":
                mel.eval("ComponentEditor")
            elif text == "Channel Control":
                mel.eval("ChannelControlEditor")
            elif text == "Display Layer Editor":
                mel.eval("DisplayLayerEditorWindow")
            elif text == "File Path Editor":
                mel.eval("FilePathEditor")
            elif text == "Namespace Editor":
                mel.eval("NamespaceEditor")
            elif text == "Script Editor":
                mel.eval("ScriptEditor")
            elif text == "Command Shell":
                mel.eval("CommandShell")
            elif text == "Profiler":
                mel.eval("ProfilerTool")
            elif text == "Evaluation Toolkit":
                mel.eval("EvaluationToolkit")

        elif parent_text == "Modeling Editors":
            if text == "Modeling Toolkit":
                mel.eval("OpenModelingToolkit")
            elif text == "Paint Effects":
                mel.eval("PaintEffectsWindow")
            elif text == "UV Editor":
                mel.eval("TextureViewWindow")
            elif text == "XGen Editor":
                mel.eval("OpenXGenEditor")
            elif text == "Crease Sets":
                mel.eval("OpenCreaseEditor")

        elif parent_text == "Animation Editors":
            if text == "Graph Editor":
                mel.eval("GraphEditor")
            elif text == "Time Editor":
                mel.eval("TimeEditorWindow")
            elif text == "Trax Editor":
                mel.eval("CharacterAnimationEditor")
            elif text == "Camera Sequencer":
                mel.eval("SequenceEditor")
            elif text == "Dope Sheet":
                mel.eval("DopeSheetEditor")
            elif text == "Quick Rig":
                mel.eval("QuickRigEditor")
            elif text == "HumanIK":
                mel.eval("HIKCharacterControlsTool")
            elif text == "Shape Editor":
                mel.eval("ShapeEditor")
            elif text == "Pose Editor":
                mel.eval("PoseEditor")
            elif text == "Expression Editor":
                mel.eval("ExpressionEditor")

        elif parent_text == "Rendering Editors":
            if text == "Render View":
                mel.eval("RenderViewWindow")
            elif text == "Render Settings":
                mel.eval("RenderGlobalsWindow")
            elif text == "Hypershade":
                mel.eval("HypershadeWindow")
            elif text == "Render Setup":
                mel.eval("RenderSetupWindow")
            elif text == "Light Editor":
                mel.eval("OpenLightEditor")
            elif text == "Custom Stereo Rig Editor":
                mel.eval("OpenStereoRigManager")
            elif text == "Rendering Flags":
                mel.eval("RenderFlagsWindow")
            elif text == "Shading Group Attributes":
                mel.eval("ShadingGroupAttributeEditor")

        elif parent_text == "Relationship Editors":
            if text == "Animation Layers":
                mel.eval("AnimLayerRelationshipEditor")
            elif text == "Camera Sets":
                mel.eval("CameraSetEditor")
            elif text == "Character Sets":
                mel.eval("CharacterSetEditor")
            elif text == "Deformer Sets":
                mel.eval("DeformerSetEditor")
            elif text == "Display Layers":
                mel.eval("LayerRelationshipEditor")
            elif text == "Dynamic Relationships":
                mel.eval("DynamicRelationshipEditor")
            elif text == "Light Linking: Light Centric":
                mel.eval("LightCentricLightLinkingEditor")
            elif text == "Light Linking: Object Centric":
                mel.eval("ObjectCentricLightLinkingEditor")
            elif text == "Partitions":
                mel.eval("PartitionEditor")
            elif text == "Render Pass Sets":
                mel.eval("RenderPassSetEditor")
            elif text == "Sets":
                mel.eval("SetEditor")
            elif text == "UV Linking: Texture-Centric":
                mel.eval("TextureCentricUVLinkingEditor")
            elif text == "UV Linking: UV-Centric":
                mel.eval("UVCentricUVLinkingEditor")
            elif text == "UV Linking: Paint Effects/UV":
                mel.eval("PFXUVSetLinkingEditor")
            elif text == "UV Linking: Hair/UV":
                mel.eval("HairUVSetLinkingEditor")

    def b000(self):
        """Attributes"""
        mel.eval("AttributeEditor")

    def b001(self):
        """Outliner"""
        mel.eval("OutlinerWindow")

    def b002(self):
        """Tool"""
        cmds.toolPropertyWindow()

    def b003(self):
        """Layers"""
        mel.eval("OpenChannelsLayers")

    def b004(self):
        """Channels"""
        mel.eval("OpenChannelsLayers")

    def b005(self):
        """Node Editor"""
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
        """Status Line"""
        mel.eval("ToggleStatusLine")

    def b008(self):
        """Shelf"""
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
        from mayatk.env_utils import script_output

        script_output.toggle(
            dock=("TimeSlider", "top"), tab_position="right", height=50
        )

    def b011(self):
        """Command Line"""
        mel.eval("ToggleCommandLine")

    def b012(self):
        """Help Line"""
        mel.eval("ToggleHelpLine")

    def b013(self):
        """Tool Box"""
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
