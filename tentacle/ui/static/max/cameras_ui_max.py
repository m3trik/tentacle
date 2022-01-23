# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Cameras_ui



class Cameras_ui_max(Cameras_ui):
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
		Cameras_ui.__init__(self, *args, **kwargs)

		tree = self.cameras_lower_submenu_ui.tree000
		tree.expandOnHover = True
		tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.

		l = ['Camera Sequencer', 'Camera Set Editor']
		[tree.add('QLabel', 'Editors', setText=s) for s in l]

		l = ['Exclusive to Camera', 'Hidden from Camera', 'Remove from Exclusive', 'Remove from Hidden', 'Remove All for Camera', 'Remove All']
		[tree.add('QLabel', 'Per Camera Visibility', setText=s) for s in l]
