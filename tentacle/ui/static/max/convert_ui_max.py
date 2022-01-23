# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Convert_ui



class Convert_ui_max(Convert_ui):
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
		Convert_ui.__init__(self, *args, **kwargs)

		ctx = self.convert_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.convert_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')

		cmb = self.convert_ui.cmb001
		list_ = ['NURBS to Polygons', 'NURBS to Subdiv', 'Polygons to Subdiv', 'Smooth Mesh Preview to Polygons', 'Polygon Edges to Curve', 'Type to Curves', 'Subdiv to Polygons', 'Subdiv to NURBS', 'NURBS Curve to Bezier', 'Bezier Curve to NURBS', 'Paint Effects to NURBS', 'Paint Effects to Curves', 'Texture to Geometry', 'Displacement to Polygons', 'Displacement to Polygons with History', 'Fluid to Polygons', 'nParticle to Polygons', 'Instance to Object', 'Geometry to Bounding Box', 'Convert XGen Primitives to Polygons'] 
		contents = cmb.addItems_(list_, 'Convert To')
