# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.editors import Editors


class Editors_maya(Editors, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # tree = self.sb.editors_lower_submenu.tree000
        # tree.expandOnHover = True

        # l = ['General Editors', 'Modeling Editors', 'Animation Editors', 'Rendering Editors', 'Relationship Editors']
        # [tree.add('QLabel', childHeader=s, setText=s) for s in l] #root

        # l = ['Attribute Editor', 'Channel Box', 'Layer Editor', 'Content Browser', 'Tool Settings', 'Hypergraph: Hierarchy', 'Hypergraph: Connections', 'Viewport', 'Adobe After Effects Live Link', 'Asset Editor', 'Attribute Spread Sheet', 'Component Editor', 'Channel Control', 'Display Layer Editor', 'File Path Editor', 'Namespace Editor', 'Script Editor', 'Command Shell', 'Profiler', 'Evaluation Toolkit']
        # [tree.add('QLabel', 'General Editors', setText=s) for s in l]

        # l = ['Modeling Toolkit', 'Paint Effects', 'UV Editor', 'XGen Editor', 'Crease Sets']
        # [tree.add('QLabel', 'Modeling Editors', setText=s) for s in l]

        # l = ['Graph Editor', 'Time Editor', 'Trax Editor', 'Camera Sequencer', 'Dope Sheet', 'Quick Rig', 'HumanIK', 'Shape Editor', 'Pose Editor', 'Expression Editor']
        # [tree.add('QLabel', 'Animation Editors', setText=s) for s in l]

        # l = ['Render View', 'Render Settings', 'Hypershade', 'Render Setup', 'Light Editor', 'Custom Stereo Rig Editor', 'Rendering Flags', 'Shading Group Attributes']
        # [tree.add('QLabel', 'Rendering Editors', setText=s) for s in l]

        # l = ['Animation Layers', 'Camera Sets', 'Character Sets', 'Deformer Sets', 'Display Layers', 'Dynamic Relationships', 'Light Linking: Light Centric','Light Linking: Object Centric', 'Partitions', 'Render Pass Sets', 'Sets', 'UV Linking: Texture-Centric', 'UV Linking: UV-Centric', 'UV Linking: Paint Effects/UV', 'UV Linking: Hair/UV']
        # [tree.add('QLabel', 'Relationship Editors', setText=s) for s in l]

    def tree000(self, wItem=None, column=None):
        """ """
        tree = self.sb.editors_lower_submenu.tree000

        if not any(
            [wItem, column]
        ):  # code here will run before each show event. generally used to refresh tree contents. -----------------------------
            return

        widget = tree.get_widget(wItem, column)
        text = tree.getWidgetText(wItem, column)
        header = tree.getHeaderFromColumn(column)

        self.sb.parent().hide()  # hide the menu before opening an external editor.

        if header == "General Editors":
            if text == "Attribute Editor":
                pm.mel.AttributeEditor()
            if text == "Channel Box":
                pm.mel.OpenChannelBox()
            if text == "Layer Editor":
                pm.mel.OpenLayerEditor()
            if text == "Content Browser":
                pm.mel.OpenContentBrowser()
            if text == "Tool Settings":
                pm.mel.ToolSettingsWindow()
            if text == "Hypergraph: Hierarchy":
                pm.mel.HypergraphHierarchyWindow()
            if text == "Hypergraph: Connections":
                pm.mel.HypergraphDGWindow()
            if text == "Viewport":
                pm.mel.DisplayViewport()
            if text == "Adobe After Effects Live Link":
                pm.mel.OpenAELiveLink()
            if text == "Asset Editor":
                pm.mel.AssetEditor()
            if text == "Attribute Spread Sheet":
                pm.mel.SpreadSheetEditor()
            if text == "Component Editor":
                pm.mel.ComponentEditor()
            if text == "Channel Control":
                pm.mel.ChannelControlEditor()
            if text == "Display Layer Editor":
                pm.mel.DisplayLayerEditorWindow()
            if text == "File Path Editor":
                pm.mel.FilePathEditor()
            if text == "Namespace Editor":
                pm.mel.NamespaceEditor()
            if text == "Script Editor":
                pm.mel.ScriptEditor()
            if text == "Command Shell":
                pm.mel.CommandShell()
            if text == "Profiler":
                pm.mel.ProfilerTool()
            if text == "Evaluation Toolkit":
                pm.mel.EvaluationToolkit()

        elif header == "Modeling Editors":
            if text == "Modeling Toolkit":
                pm.mel.OpenModelingToolkit()
            if text == "Paint Effects":
                pm.mel.PaintEffectsWindow()
            if text == "UV Editor":
                pm.mel.TextureViewWindow()
            if text == "XGen Editor":
                pm.mel.OpenXGenEditor()
            if text == "Crease Sets":
                pm.mel.OpenCreaseEditor()

        elif header == "Animation Editors":
            if text == "Graph Editor":
                pm.mel.GraphEditor()
            if text == "Time Editor":
                pm.mel.TimeEditorWindow()
            if text == "Trax Editor":
                pm.mel.CharacterAnimationEditor()
            if text == "Camera Sequencer":
                pm.mel.SequenceEditor()
            if text == "Dope Sheet":
                pm.mel.DopeSheetEditor()
            if text == "Quick Rig":
                pm.mel.QuickRigEditor()
            if text == "HumanIK":
                pm.mel.HIKCharacterControlsTool()
            if text == "Shape Editor":
                pm.mel.ShapeEditor()
            if text == "Pose Editor":
                pm.mel.PoseEditor()
            if text == "Expression Editor":
                pm.mel.ExpressionEditor()

        elif header == "Rendering Editors":
            if text == "Render View":
                pm.mel.RenderViewWindow()
            if text == "Render Settings":
                pm.mel.RenderGlobalsWindow()
            if text == "Hypershade":
                pm.mel.HypershadeWindow()
            if text == "Render Setup":
                pm.mel.RenderSetupWindow()
            if text == "Light Editor":
                pm.mel.OpenLightEditor()
            if text == "Custom Stereo Rig Editor":
                pm.mel.OpenStereoRigManager()
            if text == "Rendering Flags":
                pm.mel.RenderFlagsWindow()
            if text == "Shading Group Attributes":
                pm.mel.ShadingGroupAttributeEditor()

        elif header == "Relationship Editors":
            if text == "Animation Layers":
                pm.mel.AnimLayerRelationshipEditor()
            if text == "Camera Sets":
                pm.mel.CameraSetEditor()
            if text == "Character Sets":
                pm.mel.CharacterSetEditor()
            if text == "Deformer Sets":
                pm.mel.DeformerSetEditor()
            if text == "Display Layers":
                pm.mel.LayerRelationshipEditor()
            if text == "Dynamic Relationships":
                pm.mel.DynamicRelationshipEditor()
            if text == "Light Linking: Light Centric":
                pm.mel.LightCentricLightLinkingEditor()
            if text == "Light Linking: Object Centric":
                pm.mel.ObjectCentricLightLinkingEditor()
            if text == "Partitions":
                pm.mel.PartitionEditor()
            if text == "Render Pass Sets":
                pm.mel.RenderPassSetEditor()
            if text == "Sets":
                pm.mel.SetEditor()
            if text == "UV Linking: Texture-Centric":
                pm.mel.TextureCentricUVLinkingEditor()
            if text == "UV Linking: UV-Centric":
                pm.mel.UVCentricUVLinkingEditor()
            if text == "UV Linking: Paint Effects/UV":
                pm.mel.PFXUVSetLinkingEditor()
            if text == "UV Linking: Hair/UV":
                pm.mel.HairUVSetLinkingEditor()

    def cmb000(self, index=-1):
        """Editors"""
        cmb = self.editors_ui.draggableHeader.ctxMenu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

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

    def b000(self):
        """Attributes"""
        # e = pm.mel.eval('$tmp=$gAttributeEditorForm')
        # self.showEditor(e, 640, 480)
        pm.mel.AttributeEditor()

    def b001(self):
        """Outliner"""
        # e = pm.mel.eval('$tmp=$gOutlinerForm')

        # if not hasattr(self, 'outlinerEditor_'):
        #   panel = pm.outlinerPanel()
        #   self.outliner_ = pm.outlinerPanel(panel, query=True, outlinerEditor=True)
        #   pm.outlinerEditor(self.outliner_, edit=True, mainListConnection='worldList', selectionConnection='modelList', showShapes=False, showReferenceNodes=False, showReferenceMembers=False, showAttributes=False, showConnected=False, showAnimCurvesOnly=False, autoExpand=False, showDagOnly=True, ignoreDagHierarchy=False, expandConnections=False, showNamespace=True, showCompounds=True, showNumericAttrsOnly=False, highlightActive=True, autoSelectNewObjects=False, doNotSelectNewObjects=False, transmitFilters=False, showSetMembers=True, setFilter='defaultSetFilter', ignoreHiddenAttribute=False)

        # e = pm.outlinerEditor(self.outliner_, edit=True, showSelected=True) #expand to the current selection in the outliner.
        # w = self.showEditor(e, 260, 740)

        # panels = pm.get_panel(type='outlinerPanel')
        # for panel in panels:
        #   pm.outlinerEditor(panel, edit=1, showSelected=1)
        pm.mel.OutlinerWindow()

    def b002(self):
        """Tool"""
        # e = pm.mel.eval('$tmp=$gToolSettingsForm')
        # self.showEditor(e, 461, 480)
        pm.toolPropertyWindow()

    def b003(self):
        """Layers"""
        # e = pm.mel.eval('$tmp=$gLayerEditorForm')
        # self.showEditor(e, 320, 480)
        # pm.mel.OpenLayerEditor()
        pm.mel.OpenChannelsLayers()

    def b004(self):
        """Channels"""
        # e = pm.mel.eval('$tmp=$gChannelsForm')
        # self.showEditor(e, 320, 640)
        # pm.mel.OpenChannelBox()
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


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# deprecated: -----------------------------------
