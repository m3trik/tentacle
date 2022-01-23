# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Animation_ui



class Animation_ui_max(Animation_ui):
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
		Animation_ui.__init__(self, *args, **kwargs)

		ctx = self.animation_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.animation_ui.draggable_header.contextMenu.cmb000
		items = ['Track View: Curve Editor','Track View: Dope Sheet','Track View: New Track View','Motion Mixer','Pose Mixer','MassFx Tools', 'Dynamics Explorer','Reaction Manager','Walkthrough Assistant']
		cmb.addItems_(items, 'Animation Editors')

		ctx = self.animation_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Frame: ', setObjectName='s000', setMinMax_='0-10000 step1', setValue=1, setToolTip='')
			ctx.add('QCheckBox', setText='Relative', setObjectName='chk000', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Update', setObjectName='chk001', setChecked=True, setToolTip='')

		ctx = self.animation_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Time: ', setObjectName='s001', setMinMax_='0-10000 step1', setValue=1, setToolTip='The desired start time for the inverted keys.')
			ctx.add('QCheckBox', setText='Relative', setObjectName='chk002', setChecked=False, setToolTip='Start time position as relative or absolute.')

