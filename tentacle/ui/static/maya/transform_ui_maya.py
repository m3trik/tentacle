# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Transform_ui



class Transform_ui_maya(Transform_ui):
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
		Transform_ui.__init__(self, *args, **kwargs)


		cmb = self.transform_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')


		cmb = self.transform_ui.cmb001
		cmb.popupStyle = 'qmenu'
		cmb.menu_.setTitle('Constaints')
		#query and set current states:
		edge_constraint = True if pm.xformConstraint(query=1, type=1)=='edge' else False
		surface_constraint = True if pm.xformConstraint(query=1, type=1)=='surface' else False
		live_object = True if pm.ls(live=1) else False
		values = [('chk024', 'Edge', edge_constraint), ('chk025', 'Surface', surface_constraint), ('chk026', 'Make Live', live_object)]
		[cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName=chk, setText=typ, setChecked=state) for chk, typ, state in values]


		cmb = self.transform_ui.cmb002
		items = ['Point to Point', '2 Points to 2 Points', '3 Points to 3 Points', 'Align Objects', 'Position Along Curve', 'Align Tool', 'Snap Together Tool', 'Orient to Vertex/Edge Tool']
		cmb.addItems_(items, 'Align To')


		cmb = self.transform_ui.cmb003
		cmb.menu_.s021.setValue(pm.manipMoveContext('Move', q=True, snapValue=True))
		cmb.menu_.s022.setValue(pm.manipScaleContext('Scale', q=True, snapValue=True))
		cmb.menu_.s023.setValue(pm.manipRotateContext('Rotate', q=True, snapValue=True))