# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Create_ui



class Create_ui_maya(Create_ui):
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
		Create_ui.__init__(self, *args, **kwargs)

		ctx = self.create_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.create_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')

		cmb = self.create_ui.cmb001
		list_ = ['Polygon', 'NURBS', 'Light']
		cmb.addItems_(list_)

		cmb = self.create_ui.cmb002
		list_ = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Platonic Solids", "Text"]
		cmb.addItems_(list_)

		ctx = self.create_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Translate', setObjectName='chk000', setChecked=True, setToolTip='Move the created object to the center point of any selected object(s).')
			ctx.add('QCheckBox', setText='Scale', setObjectName='chk001', setChecked=True, setToolTip='Uniformly scale the created object to match the averaged scale of any selected object(s).')
