# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Editors_ui



class Editors_ui_maya(Editors_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (passed in via the switchboard module's 'getClassInstanceFromUiName' method.)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		Editors_ui.__init__(self, *args, **kwargs)

		# self.dynLayout_ui = self.tcl.sb.getUi('dynLayout')
		# self.stackedWidget = self.dynLayout_ui.stackedWidget

		tree = self.editors_lower_submenu_ui.tree000
		tree.expandOnHover = True

		l = ['General Editors', 'Modeling Editors', 'Animation Editors', 'Rendering Editors', 'Relationship Editors']
		[tree.add('QLabel', childHeader=s, setText=s) for s in l] #root

		l = ['Attribute Editor', 'Channel Box', 'Layer Editor', 'Content Browser', 'Tool Settings', 'Hypergraph: Hierarchy', 'Hypergraph: Connections', 'Viewport', 'Adobe After Effects Live Link', 'Asset Editor', 'Attribute Spread Sheet', 'Component Editor', 'Channel Control', 'Display Layer Editor', 'File Path Editor', 'Namespace Editor', 'Script Editor', 'Command Shell', 'Profiler', 'Evaluation Toolkit']
		[tree.add('QLabel', 'General Editors', setText=s) for s in l]

		l = ['Modeling Toolkit', 'Paint Effects', 'UV Editor', 'XGen Editor', 'Crease Sets']
		[tree.add('QLabel', 'Modeling Editors', setText=s) for s in l]

		l = ['Graph Editor', 'Time Editor', 'Trax Editor', 'Camera Sequencer', 'Dope Sheet', 'Quick Rig', 'HumanIK', 'Shape Editor', 'Pose Editor', 'Expression Editor']
		[tree.add('QLabel', 'Animation Editors', setText=s) for s in l]

		l = ['Render View', 'Render Settings', 'Hypershade', 'Render Setup', 'Light Editor', 'Custom Stereo Rig Editor', 'Rendering Flags', 'Shading Group Attributes']
		[tree.add('QLabel', 'Rendering Editors', setText=s) for s in l]

		l = ['Animation Layers', 'Camera Sets', 'Character Sets', 'Deformer Sets', 'Display Layers', 'Dynamic Relationships', 'Light Linking: Light Centric','Light Linking: Object Centric', 'Partitions', 'Render Pass Sets', 'Sets', 'UV Linking: Texture-Centric', 'UV Linking: UV-Centric', 'UV Linking: Paint Effects/UV', 'UV Linking: Hair/UV']
		[tree.add('QLabel', 'Relationship Editors', setText=s) for s in l]