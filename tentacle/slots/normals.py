# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Normals(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		ctx = self.normals_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		ctx = self.normals_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Display Size: ', setObjectName='s001', setMinMax_='1-100 step1', setValue=1, setToolTip='Normal display size.')

		ctx = self.normals_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Angle: ', setObjectName='s002', setMinMax_='0-180 step1', setValue=0, setToolTip='The normal angle in degrees.')
			ctx.add('QCheckBox', setText='Harden Creased Edges', setObjectName='chk001', setChecked=True, setToolTip='Soften all non-creased edges.')
			ctx.add('QCheckBox', setText='Harden UV Borders', setObjectName='chk002', setChecked=True, setToolTip='Harden UV shell border edges.')
			ctx.add('QCheckBox', setText='Soften All Other', setObjectName='chk000', setChecked=True, setToolTip='Soften all non-hard edges.')

		ctx = self.normals_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Angle: ', setObjectName='s000', setMinMax_='0-180 step1', setValue=60, setToolTip='Angle degree.')

		ctx = self.normals_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Lock', setObjectName='chk002', setChecked=True, setToolTip='Toggle Lock/Unlock.')
			ctx.add('QCheckBox', setText='All', setObjectName='chk001', setChecked=True, setToolTip='Lock/Unlock All.')
			ctx.chk002.toggled.connect(lambda state, w=ctx.chk002: w.setText('Lock') if state else w.setText('Unlock')) 

		ctx = self.normals_ui.tb004.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='By UV Shell', setObjectName='chk003', setToolTip='Average the normals of each object\'s faces per UV shell.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.normals_ui.draggable_header