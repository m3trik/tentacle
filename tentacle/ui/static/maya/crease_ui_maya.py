# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Crease_ui



class Crease_ui_maya(Crease_ui):
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
		Crease_ui.__init__(self, *args, **kwargs)

		ctx = self.crease_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Crease Editors')

		cmb = self.crease_ui.draggable_header.contextMenu.cmb000
		items = ['Crease Set Editor']
		cmb.addItems_(items, 'Crease Editors:')

		ctx = self.crease_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Crease Amount: ', setObjectName='s003', setMinMax_='0-10 step1', setValue=10, setToolTip='Crease amount 0-10. Overriden if "max" checked.')
			ctx.add('QCheckBox', setText='Toggle Max', setObjectName='chk003', setToolTip='Toggle crease amount from it\'s current value to the maximum amount.')
			ctx.add('QCheckBox', setText='Un-Crease', setObjectName='chk002', setToolTip='Un-crease selected components or If in object mode, uncrease all.')
			ctx.add('QCheckBox', setText='Perform Normal Edge Hardness', setObjectName='chk005', setChecked=True, setToolTip='Toggle perform normal edge hardness.')
			ctx.add('QSpinBox', setPrefix='Hardness Angle: ', setObjectName='s004', setMinMax_='0-180 step1', setValue=30, setToolTip='Normal edge hardness 0-180.')
			ctx.add('QCheckBox', setText='Crease Vertex Points', setObjectName='chk004', setChecked=True, setToolTip='Crease vertex points.')
			ctx.add('QCheckBox', setText='Auto Crease', setObjectName='chk011', setToolTip='Auto crease selected object(s) within the set angle tolerance.')
			ctx.add('QSpinBox', setPrefix='Auto Crease: Low: ', setObjectName='s005', setMinMax_='0-180 step1', setValue=85, setToolTip='Auto crease: low angle constraint.')
			ctx.add('QSpinBox', setPrefix='Auto Crease: high: ', setObjectName='s006', setMinMax_='0-180 step1', setValue=95, setToolTip='Auto crease: max angle constraint.')
			self.toggleWidgets(ctx, setDisabled='s005,s006')

			