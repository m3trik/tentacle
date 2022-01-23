# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Subdivision_ui



class Subdivision_ui_max(Subdivision_ui):
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
		Subdivision_ui.__init__(self, *args, **kwargs)

		ctx = self.subdivision_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Subdivision Editiors.')
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb001', setToolTip='Smooth Proxy.')
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb002', setToolTip='Maya Subdivision Operations.')

		cmb = self.subdivision_ui.draggable_header.contextMenu.cmb000
		items = ['Polygon Display Options']
		cmb.addItems_(items, 'Subdivision Editiors')

		cmb = self.subdivision_ui.draggable_header.contextMenu.cmb001
		items = ['Create Subdiv Proxy','Remove Subdiv Proxy Mirror','Crease Tool','Toggle Subdiv Proxy Display', 'Both Proxy and Subdiv Display']
		cmb.addItems_(items, 'Smooth Proxy')

		cmb = self.subdivision_ui.draggable_header.contextMenu.cmb002
		items = ['Reduce Polygons','Add Divisions','Smooth']
		cmb.addItems_(items, 'Maya Subdivision Operations')
