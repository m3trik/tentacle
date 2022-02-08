# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Edit(Slots):
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
		ctx = self.edit_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Editors')

		cmb = self.edit_ui.cmb001
		cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		ctx = self.edit_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='For All Objects', setObjectName='chk018', setChecked=True, setToolTip='Delete history on All objects or just those selected.')
			ctx.add('QCheckBox', setText='Delete Unused Nodes', setObjectName='chk019', setChecked=True, setToolTip='Delete unused nodes.')
			ctx.add('QCheckBox', setText='Delete Deformers', setObjectName='chk020', setToolTip='Delete deformers.')

		ctx = self.edit_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Delete Edge Loop', setObjectName='chk001', setToolTip='Delete the edge loops of any edges selected.')
			ctx.add('QCheckBox', setText='Delete Edge Ring', setObjectName='chk000', setToolTip='Delete the edge rings of any edges selected.')

		ctx = self.edit_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='-', setObjectName='chk006', setChecked=True, setToolTip='Perform delete along negative axis.')
			ctx.add('QRadioButton', setText='X', setObjectName='chk007', setChecked=True, setToolTip='Perform delete along X axis.')
			ctx.add('QRadioButton', setText='Y', setObjectName='chk008', setToolTip='Perform delete along Y axis.')
			ctx.add('QRadioButton', setText='Z', setObjectName='chk009', setToolTip='Perform delete along Z axis.')
			self.connect_('chk006-9', 'toggled', self.chk006_9, ctx)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.edit_ui.draggable_header


	def chk006_9(self):
		'''Set the toolbutton's text according to the checkstates.
		'''
		tb = self.edit_ui.tb003
		axis = self.getAxisFromCheckBoxes('chk006-9', tb.contextMenu)
		tb.setText('Delete '+axis)

		