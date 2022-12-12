# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.editors import Editors



class Editors_max(Editors, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.stackedWidget = self.sb.dynLayout.stackedWidget

		self.editors_ui.v000.setText('Command Panel')
		self.editors_ui.v001.setText('Scene Explorer')
		self.editors_ui.v002.setText('Ribbon')
		self.editors_ui.v003.setText('Layer Manager')
		self.editors_ui.v004.setText('Channel Info')
		self.editors_ui.v005.setText('Schematic View')
		self.editors_ui.v006.setText('Asset Tracking')

		tree = self.sb.editors_lower_submenu.tree000
		tree.expandOnHover = True

		l = ['General Editors', 'Modeling Editors', 'Animation Editors', 'Rendering Editors', 'Relationship Editors']
		[tree.add('QLabel', childHeader=s, setText=s) for s in l] #root

		l = ['Channel Info','Rename Objects','Layer Explorer','Scene Explorer','Property Explorer','Container Explorer','Max Creation Graph',
		'Max Creation Graph Editor','Asset Tracking','Missing Objects Explorer','Particle View','Maxscript: Editor','Maxscript: Listener',
		'Maxscript: Debugger Dialog','Visual Maxscript Editor','Units Setup','Customize User Interface','Configure Project Paths',
		'Configure User and System Paths','Hotkey Editor','Plug-in Manager','Preferences']
		[tree.add('QLabel', 'General Editors', setText=s) for s in l]

		l = ['Grid and Snap Settings']
		[tree.add('QLabel', 'Modeling Editors', setText=s) for s in l]
		
		l = ['Track View: Curve Editor','Track View: Dope Sheet','Track View: New Track View','Motion Mixer','Bone Tools','Pose Mixer','MassFx Tools',
		'Dynamics Explorer','Parameter Editor','Parameter Collector','Parameter Wire Dialog','Reaction Manager','Walkthrough Assistant']
		[tree.add('QLabel', 'Animation Editors', setText=s) for s in l]

		l = ['Render Setup','Render Window','State Sets','Camera Sequencer','Light Tracer','Light Explorer','light Lister','Scene Converter','Environment',
		'Material Editor: Compact','Material Editor: Slate','Material/Map Browser','Material Explorer','Video Post','Panorama Explorer','Print Size Assistant',
		'Gamma/LUT Setup','Compare Midia in RAM Player']
		[tree.add('QLabel', 'Rendering Editors', setText=s) for s in l]

		l = ['Schematic View','schematic View: New']
		[tree.add('QLabel', 'Relationship Editors', setText=s) for s in l]


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.editors_ui.draggable_header


	def tree000(self, wItem=None, column=None):
		'''All Editors
		'''
		tree = self.sb.editors_lower_submenu.tree000

		if not any([wItem, column]): # code here will run before each show event. generally used to refresh tree contents. -----------------------------
			return

		widget = tree.getWidget(wItem, column)
		text = tree.getWidgetText(wItem, column)
		header = tree.getHeaderFromColumn(column)

		self.sb.parent().hide() #hide the menu before opening an external editor.

		if header=='General Editors':
			if text=='Channel Info':
				maxEval('macros.run "Tools" "Channel_Info"')
			elif text=='Rename Objects':
				maxEval('macros.run "Tools" "RenameObjects"')
			elif text=='Layer Explorer':
				maxEval('actionMan.executeAction 427416257 "13"') #Scene Explorer: Open Scene Explorer Default 3
			elif text=='Scene Explorer':
				maxEval('actionMan.executeAction 427416257 "19"') #Scene Explorer: Open Scene Explorer Default 9
			elif text=='Property Explorer':
				maxEval('actionMan.executeAction 427416257 "17"') #Scene Explorer: Open Scene Explorer Default 7
			elif text=='Container Explorer':
				maxEval('actionMan.executeAction 427416257 "11"')
			elif text=='Max Creation Graph':
				maxEval('actionMan.executeAction 62682 "44354"') #Max Creation Graph: New Max Creation Graph
			elif text=='Max Creation Graph Editor':
				maxEval('actionMan.executeAction 62682 "54734"')
			elif text=='Asset Tracking':
				maxEval('macros.run "Asset Tracking System" "AssetTrackingSystemToggle"')
			elif text=='Missing Objects Explorer':
				maxEval('actionMan.executeAction 427416257 "16"') #Scene Explorer: Open Scene Explorer Default 6
			elif text=='Particle View':
				maxEval('actionMan.executeAction 135018554 "32771"') #Particle Flow: Particle View Toggle
			elif text=='Maxscript: Editor':
				maxEval('actionMan.executeAction 0 "40839"') #MAX Script: MAXScript Editor
			elif text=='Maxscript: Listener':
				maxEval('actionMan.executeAction 0 "40472"') #MAX Script: MAXScript Listener
			elif text=='Maxscript: Debugger Dialog':
				maxEval('actionMan.executeAction 0 "576"') #MAX Script: Debugger Dialog
			elif text=='Visual Maxscript Editor':
				maxEval('macros.run "MAX Script" "Launch_VMS"')
			elif text=='Units Setup':
				maxEval('actionMan.executeAction 0 "40025"') #Customize User Interface: Unit Setup
			elif text=='Customize User Interface':
				maxEval('actionMan.executeAction 0 "59226"') #Customize User Interface: Customize User Interface
			elif text=='Configure Project Paths':
				maxEval('actionMan.executeAction 0 "40209"') #File: Configure User Paths
			elif text=='Configure User and System Paths':
				maxEval('actionMan.executeAction 0 "41001"') #File: Configure User and System Paths
			elif text=='Hotkey Editor':
				maxEval('actionMan.executeAction 0 "59245"') #Customize User Interface: Hotkey Editor
			elif text=='Plug-in Manager':
				maxEval('Plug_in_Manager.PluginMgrAction.show()')
			elif text=='Preferences':
				maxEval('actionMan.executeAction 0 "40108"') #File: Preferences

		if header=='Modeling Editors':
			if text=='Grid and Snap Settings':
				maxEval('actionMan.executeAction 0 "40024"')

		if header=='Animation Editors':
			if text=='Track View: Curve Editor':
				maxEval('macros.run "Track View" "LaunchFCurveEditor"')
			elif text=='Track View: Dope Sheet':
				maxEval('macros.run "Track View" "LaunchDopeSheetEditor"')
			elif text=='Track View: New Track View':
				maxEval('actionMan.executeAction 0 "40278"') #Track View: New Track View
			elif text=='Motion Mixer':
				maxEval('macros.run "Mixer" "ToggleMotionMixerDlg"')
			elif text=='Bone Tools':
				maxEval('macros.run "Animation Tools" "BoneAdjustmentTools"')
			elif text=='Pose Mixer':
				maxEval('macros.run "CAT" "catPoseMixer"')
			elif text=='MassFx Tools':
				maxEval('macros.run "PhysX" "PxShowToolsWindowMS"')
			elif text=='Dynamics Explorer':
				maxEval('macros.run "PhysX" "OpenDynamicsExplorer"')
			elif text=='Parameter Editor':
				maxEval('macros.run "Customize User Interface" "Custom_Attributes"')
			elif text=='Parameter Collector':
				maxEval('macros.run "Parameter Collector" "ParamCollectorShow"')
			elif text=='Parameter Wire Dialog':
				maxEval('macros.run "Parameter Wire" "paramWire_dialog"')
			elif text=='Reaction Manager':
				maxEval('macros.run "Animation Tools" "OpenReactionManager"')
			elif text=='Walkthrough Assistant':
				maxEval('macros.run "Animation Tools" "walk_assist"')

		if header=='Rendering Editors':
			if text=='Render Setup':
				maxEval('actionMan.executeAction 0 "60010"') #render setup
			elif text=='Render Window':
				maxEval('actionMan.executeAction 0 "348"') #Render: Rendered Frame Window
			elif text=='State Sets':
				maxEval('actionMan.executeAction 29771 "33764"') #State Sets: State Sets...
			elif text=='Camera Sequencer':
				maxEval('actionMan.executeAction 29771 "57491"') #State Sets: Camera Sequencer...
			elif text=='Light Tracer':
				maxEval('macros.run "Render" "AdvLighting_LightTracer"')
			elif text=='Light Explorer':
				maxEval('actionMan.executeAction 427416257 "15"') #Scene Explorer: Open Scene Explorer Default 5
			elif text=='Light Lister':
				maxEval('macros.run "Lights and Cameras" "Light_List"')
			elif text=='Scene Converter':
				maxEval('macros.run "Show" "Sceneconverter"')
			elif text=='Environment':
				maxEval('actionMan.executeAction 0 "40029"') #Render: Environment Dialog Toggle
			elif text=='Material Editor: Compact':
				maxEval('macros.run "Medit Tools" "basic_material_editor"')
			elif text=='Material Editor: Slate':
				maxEval('macros.run "Medit Tools" "advanced_material_editor"')
			elif text=='Material/Map Browser':
				maxEval('actionMan.executeAction 0 "40312"') #Tools: Material/Map Browser Toggle
			elif text=='Material Explorer':
				maxEval('macros.run "Material Explorer" "MaterialExplorerToggle"')
			elif text=='Video Post':
				maxEval('actionMan.executeAction 0 "40027"') #Render: Video Post Dialog Toggle
			elif text=='Panorama Explorer':
				maxEval('macros.run "Render" "Panoramic_Exporter"')
			elif text=='Print Size Assistant':
				maxEval('macros.run "Render" "RenderToPrint"')
			elif text=='Gamma/LUT Setup':
				maxEval('macros.run "Render" "GammaSetup"')
			elif text=='Compare Midia in RAM Player':
				maxEval('macros.run "Render" "GammaSetup"')

		if header=='Relationship Editors':
			if text=='Schematic View':
				maxEval('schematicView.Open "Schematic View 1"')
			elif text=='schematic View: New':
				maxEval('actionMan.executeAction 0 "40429"') #Schematic View: New Schematic View


	def getEditorWidget(self, name):
		'''Get a maya widget from a given name.

		:Parameters:
			name (str) = name of widget
		'''
		_name = '_'+name
		if not hasattr(self, _name):
			w = self.convertToWidget(name)
			self.stackedWidget.addWidget(w)
			setattr(self, _name, w)

		return getattr(self, _name)


	def showEditor(self, name, width=640, height=480):
		'''Show, resize, and center the given editor.

		:Parameters:
			name (str) = The name of the editor.
			width (int) = The editor's desired width.
			height (int) = The editor's desired height.

		:Return:
			(obj) The editor as a QWidget.
		'''
		w = self.getEditorWidget(name)

		self.sb.parent().setUi('dynLayout')
		self.stackedWidget.setCurrentWidget(w)
		self.sb.parent().resize(width, height)
		self.sb.parent().move(QtGui.QCursor.pos() - self.sb.parent().rect().center()) #move window to cursor position and offset from left corner to center

		return w


	def v000(self):
		'''Attributes
		'''
		maxEval('actionMan.executeAction 0 "408"') #Tools: Show Command Panel Toggle.


	def v001(self):
		'''Outliner
		'''
		maxEval('macros.run "Scene Explorer" "SESceneExplorer"') #Scene Explorer


	def v002(self):
		'''Tool
		'''
		maxEval('actionMan.executeAction 60545 "26914"') #Ribbon: Show Ribbon.


	def v003(self):
		'''Layers
		'''
		maxEval('macros.run "Layers" "LayerManager"') #Layer Explorer


	def v004(self):
		'''Channels
		'''
		maxEval('macros.run "Tools" "Channel_Info"') #Channel-Info


	def v005(self):
		'''Node Editor
		'''
		maxEval('schematicView.Open "Schematic View 3"') #Schematic View


	def v006(self):
		'''Dependancy Graph
		'''
		maxEval('macros.run "Asset Tracking System" "AssetTrackingSystemToggle"') #Asset Tracking









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------