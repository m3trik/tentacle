# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Rigging_ui



class Rigging_ui_maya(Rigging_ui):
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
		Rigging_ui.__init__(self, *args, **kwargs)

		ctx = self.rigging_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Rigging Editors')

		cmb = self.rigging_ui.draggable_header.contextMenu.cmb000
		items = ['Quick Rig','HumanIK','Expression Editor','Shape Editor','Connection Editor','Channel Control Editor','Set Driven Key']
		cmb.addItems_(items, 'Maya Rigging Editors')

		cmb = self.rigging_ui.cmb001
		items = ['Joints','Locator','IK Handle', 'Lattice', 'Cluster']
		cmb.addItems_(items, "Create")

		ctx = self.rigging_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Joints', setObjectName='chk000', setChecked=True, setToolTip='Display Joints.')
			ctx.add('QCheckBox', setText='IK', setObjectName='chk001', setChecked=True, setToolTip='Display IK.')
			ctx.add('QCheckBox', setText='IK\\FK', setObjectName='chk002', setChecked=True, setToolTip='Display IK\\FK.')
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.00-10 step.5', setValue=1.0, setToolTip='Global Display Scale for the selected type.')
			self.chk000() #init scale joint value

		ctx = self.rigging_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Align world', setObjectName='chk003', setToolTip='Align joints with the worlds transform.')

		ctx = self.rigging_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Template Child', setObjectName='chk004', setChecked=False, setToolTip='Template child object(s) after parenting.')		

		ctx = self.rigging_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QLineEdit', setPlaceholderText='Suffix:', setText='', setObjectName='t000', setToolTip='A string appended to the end of the created locators name.')
			ctx.add('QCheckBox', setText='Strip Digits', setObjectName='chk005', setChecked=True, setToolTip='Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit.')
			ctx.add('QLineEdit', setPlaceholderText='Strip:', setText='_GEO', setObjectName='t001', setToolTip='Strip a specific character set from the locator name. The locators name is based off of the selected objects name.')
			ctx.add('QDoubleSpinBox', setPrefix='Scale: ', setObjectName='s001', setMinMax_='.000-1000 step1', setValue=1, setToolTip='The scale of the locator.')
			ctx.add('QCheckBox', setText='Parent', setObjectName='chk006', setChecked=True, setToolTip='Parent to object to the locator.')
			ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk010', setChecked=True, setToolTip='Freeze transforms on the locator.')
			ctx.add('QCheckBox', setText='Bake Child Pivot', setObjectName='chk011', setChecked=True, setToolTip='Bake pivot positions on the child object.')
			ctx.add('QCheckBox', setText='Lock Child Translate', setObjectName='chk007', setChecked=True, setToolTip='Lock the translate values of the child object.')
			ctx.add('QCheckBox', setText='Lock Child Rotation', setObjectName='chk008', setChecked=True, setToolTip='Lock the rotation values of the child object.')
			ctx.add('QCheckBox', setText='Lock Child Scale', setObjectName='chk009', setChecked=False, setToolTip='Lock the scale values of the child object.')
			ctx.add('QCheckBox', setText='Remove Locators', setObjectName='chk015', setChecked=False, setToolTip='Removes the locator, and inverts the above process. (not valid with component selections)')
			ctx.chk015.stateChanged.connect(lambda state: self.toggleWidgets(ctx, setDisabled='t000-1,s001,chk005-11') if state 
															else self.toggleWidgets(ctx, setEnabled='t000-1,s001,chk005-11')) #disable non-relevant options.
		ctx = self.rigging_ui.tb004.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Translate', setObjectName='chk012', setChecked=False, setToolTip='')
			ctx.add('QCheckBox', setText='Rotate', setObjectName='chk013', setChecked=False, setToolTip='')
			ctx.add('QCheckBox', setText='Scale', setObjectName='chk014', setChecked=False, setToolTip='')
			self.connect_((ctx.chk012, ctx.chk013, ctx.chk014), 'toggled', 
				[lambda state: self.rigging_ui.tb004.setText('Lock Attributes' 
					if any((ctx.chk012.isChecked(), ctx.chk013.isChecked(), ctx.chk014.isChecked())) else 'Unlock Attributes'), 
				lambda state: self.rigging_submenu_ui.tb004.setText('Lock Transforms' 
					if any((ctx.chk012.isChecked(), ctx.chk013.isChecked(), ctx.chk014.isChecked())) else 'Unlock Attributes')])
