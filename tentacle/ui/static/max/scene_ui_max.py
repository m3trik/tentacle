# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Scene_ui



class Scene_ui_max(Scene_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		Scene_ui.__init__(self, *args, **kwargs)

		ctx = self.scene_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Scene Editors')

		cmb = self.scene_ui.draggable_header.contextMenu.cmb000
		items = ['Node Editor', 'Outlinder', 'Content Browser', 'Optimize Scene Size', 'Prefix Hierarchy Names', 'Search and Replace Names']
		cmb.addItems_(items, 'Maya Scene Editors')

		ctx = self.scene_ui.t000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Ignore Case', setObjectName='chk000', setToolTip='Search case insensitive.')
			ctx.add('QCheckBox', setText='Regular Expression', setObjectName='chk001', setToolTip='When checked, regular expression syntax is used instead of the default \'*\' and \'|\' wildcards.')

		ctx = self.scene_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', addItems=['capitalize', 'upper', 'lower', 'swapcase', 'title'], setObjectName='cmb001', setToolTip='Set desired python case operator.')

