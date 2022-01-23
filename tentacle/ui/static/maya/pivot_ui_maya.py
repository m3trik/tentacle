# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Pivot_ui



class Pivot_ui_maya(Pivot_ui):
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
		Pivot_ui.__init__(self, *args, **kwargs)

		ctx = self.pivot_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.pivot_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		ctx = self.pivot_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Reset Pivot Position', setObjectName='chk000', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Reset Pivot Orientation', setObjectName='chk001', setChecked=True, setToolTip='')

		ctx = self.pivot_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Component', setObjectName='chk002', setToolTip='Center the pivot on the center of the selected component\'s bounding box')
			ctx.add('QRadioButton', setText='Object', setObjectName='chk003', setChecked=True, setToolTip='Center the pivot on the center of the object\'s bounding box')
			ctx.add('QRadioButton', setText='World', setObjectName='chk004', setToolTip='Center the pivot on world origin.')