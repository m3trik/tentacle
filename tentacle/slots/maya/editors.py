# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from uitk.switchboard import signals
from tentacle.slots.maya import SlotsMaya


class Editors(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def list000_init(self, widget):
        """ """
        widget.fixed_item_height = 18
        widget.sublist_x_offset = -10
        widget.sublist_y_offset = -10

        w1 = widget.add("General Editors")
        general_editors = sorted(
            [
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
            ]
        )
        w1.sublist.add(general_editors)

        w2 = widget.add("Modeling Editors")
        modeling_editors = sorted(
            [
                "Modeling Toolkit",
                "Paint Effects",
                "UV Editor",
                "XGen Editor",
                "Crease Sets",
            ]
        )
        w2.sublist.add(modeling_editors)

        w3 = widget.add("Animation Editors")
        animation_editors = sorted(
            [
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
            ]
        )
        w3.sublist.add(animation_editors)

        w4 = widget.add("Rendering Editors")
        rendering_editors = sorted(
            [
                "Render View",
                "Render Settings",
                "Hypershade",
                "Render Setup",
                "Light Editor",
                "Custom Stereo Rig Editor",
                "Rendering Flags",
                "Shading Group Attributes",
            ]
        )
        w4.sublist.add(rendering_editors)

        w5 = widget.add("Relationship Editors")
        relationship_editors = sorted(
            [
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
            ]
        )
        w5.sublist.add(relationship_editors)

    @signals("on_item_interacted")
    def list000(self, item):
        """ """
        text = item.item_text()
        parent_text = item.parent_item_text()

        if parent_text == "General Editors":
            if text == "Attribute Editor":
                pm.mel.AttributeEditor()
            elif text == "Channel Box":
                pm.mel.OpenChannelBox()
            elif text == "Layer Editor":
                pm.mel.OpenLayerEditor()
            elif text == "Content Browser":
                pm.mel.OpenContentBrowser()
            elif text == "Tool Settings":
                pm.mel.ToolSettingsWindow()
            elif text == "Hypergraph: Hierarchy":
                pm.mel.HypergraphHierarchyWindow()
            elif text == "Hypergraph: Connections":
                pm.mel.HypergraphDGWindow()
            elif text == "Viewport":
                pm.mel.DisplayViewport()
            elif text == "Adobe After Effects Live Link":
                pm.mel.OpenAELiveLink()
            elif text == "Asset Editor":
                pm.mel.AssetEditor()
            elif text == "Attribute Spread Sheet":
                pm.mel.SpreadSheetEditor()
            elif text == "Component Editor":
                pm.mel.ComponentEditor()
            elif text == "Channel Control":
                pm.mel.ChannelControlEditor()
            elif text == "Display Layer Editor":
                pm.mel.DisplayLayerEditorWindow()
            elif text == "File Path Editor":
                pm.mel.FilePathEditor()
            elif text == "Namespace Editor":
                pm.mel.NamespaceEditor()
            elif text == "Script Editor":
                pm.mel.ScriptEditor()
            elif text == "Command Shell":
                pm.mel.CommandShell()
            elif text == "Profiler":
                pm.mel.ProfilerTool()
            elif text == "Evaluation Toolkit":
                pm.mel.EvaluationToolkit()

        elif parent_text == "Modeling Editors":
            if text == "Modeling Toolkit":
                pm.mel.OpenModelingToolkit()
            elif text == "Paint Effects":
                pm.mel.PaintEffectsWindow()
            elif text == "UV Editor":
                pm.mel.TextureViewWindow()
            elif text == "XGen Editor":
                pm.mel.OpenXGenEditor()
            elif text == "Crease Sets":
                pm.mel.OpenCreaseEditor()

        elif parent_text == "Animation Editors":
            if text == "Graph Editor":
                pm.mel.GraphEditor()
            elif text == "Time Editor":
                pm.mel.TimeEditorWindow()
            elif text == "Trax Editor":
                pm.mel.CharacterAnimationEditor()
            elif text == "Camera Sequencer":
                pm.mel.SequenceEditor()
            elif text == "Dope Sheet":
                pm.mel.DopeSheetEditor()
            elif text == "Quick Rig":
                pm.mel.QuickRigEditor()
            elif text == "HumanIK":
                pm.mel.HIKCharacterControlsTool()
            elif text == "Shape Editor":
                pm.mel.ShapeEditor()
            elif text == "Pose Editor":
                pm.mel.PoseEditor()
            elif text == "Expression Editor":
                pm.mel.ExpressionEditor()

        elif parent_text == "Rendering Editors":
            if text == "Render View":
                pm.mel.RenderViewWindow()
            elif text == "Render Settings":
                pm.mel.RenderGlobalsWindow()
            elif text == "Hypershade":
                pm.mel.HypershadeWindow()
            elif text == "Render Setup":
                pm.mel.RenderSetupWindow()
            elif text == "Light Editor":
                pm.mel.OpenLightEditor()
            elif text == "Custom Stereo Rig Editor":
                pm.mel.OpenStereoRigManager()
            elif text == "Rendering Flags":
                pm.mel.RenderFlagsWindow()
            elif text == "Shading Group Attributes":
                pm.mel.ShadingGroupAttributeEditor()

        elif parent_text == "Relationship Editors":
            if text == "Animation Layers":
                pm.mel.AnimLayerRelationshipEditor()
            elif text == "Camera Sets":
                pm.mel.CameraSetEditor()
            elif text == "Character Sets":
                pm.mel.CharacterSetEditor()
            elif text == "Deformer Sets":
                pm.mel.DeformerSetEditor()
            elif text == "Display Layers":
                pm.mel.LayerRelationshipEditor()
            elif text == "Dynamic Relationships":
                pm.mel.DynamicRelationshipEditor()
            elif text == "Light Linking: Light Centric":
                pm.mel.LightCentricLightLinkingEditor()
            elif text == "Light Linking: Object Centric":
                pm.mel.ObjectCentricLightLinkingEditor()
            elif text == "Partitions":
                pm.mel.PartitionEditor()
            elif text == "Render Pass Sets":
                pm.mel.RenderPassSetEditor()
            elif text == "Sets":
                pm.mel.SetEditor()
            elif text == "UV Linking: Texture-Centric":
                pm.mel.TextureCentricUVLinkingEditor()
            elif text == "UV Linking: UV-Centric":
                pm.mel.UVCentricUVLinkingEditor()
            elif text == "UV Linking: Paint Effects/UV":
                pm.mel.PFXUVSetLinkingEditor()
            elif text == "UV Linking: Hair/UV":
                pm.mel.HairUVSetLinkingEditor()

    def b000(self):
        """Attributes"""
        pm.mel.AttributeEditor()

    def b001(self):
        """Outliner"""
        pm.mel.OutlinerWindow()

    def b002(self):
        """Tool"""
        pm.toolPropertyWindow()

    def b003(self):
        """Layers"""
        pm.mel.OpenChannelsLayers()

    def b004(self):
        """Channels"""
        pm.mel.OpenChannelsLayers()

    def b005(self):
        """Node Editor"""
        pm.mel.NodeEditorWindow()

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
        # e = pm.mel.eval('$tmp=$gHyperGraphPanel')
        # self.showEditor(e, 640, 480)
        pm.mel.HypergraphHierarchyWindow()

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

    def showEditor(self, name, width=640, height=480):
        """Show, resize, and center the given editor.

        Parameters:
                name (str): The name of the editor.
                width (int): The editor's desired width.
                height (int): The editor's desired height.

        Returns:
                (obj) The editor as a QWidget.
        """
        w = self.getEditorWidget(name)

        self.sb.parent().set_ui("dynLayout")
        self.stackedWidget.setCurrentWidget(w)
        self.sb.parent().resize(width, height)
        return w


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
