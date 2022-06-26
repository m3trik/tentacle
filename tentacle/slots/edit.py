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
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui object of <name>. ie. self.polygons_ui
					<widget> (registered widget) = Any widget previously registered in the switchboard module. ie. self.PushButton
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
		'''
		dh = self.edit_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='Editors')

		cmb001 = self.edit_ui.cmb001
		cmb001.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		tb001 = self.edit_ui.tb001
		tb001.contextMenu.add('QCheckBox', setText='For All Objects', setObjectName='chk018', setChecked=True, setToolTip='Delete history on All objects or just those selected.')
		tb001.contextMenu.add('QCheckBox', setText='Delete Unused Nodes', setObjectName='chk019', setChecked=True, setToolTip='Delete unused nodes.')
		tb001.contextMenu.add('QCheckBox', setText='Delete Deformers', setObjectName='chk020', setToolTip='Delete deformers.')
		tb001.contextMenu.add('QCheckBox', setText='Optimize Scene', setObjectName='chk030', setToolTip='Remove unused scene objects.')

		tb002 = self.edit_ui.tb002
		tb002.contextMenu.add('QCheckBox', setText='Delete Edge Loop', setObjectName='chk001', setToolTip='Delete the edge loops of any edges selected.')
		tb002.contextMenu.add('QCheckBox', setText='Delete Edge Ring', setObjectName='chk000', setToolTip='Delete the edge rings of any edges selected.')

		tb003 = self.edit_ui.tb003
		tb003.contextMenu.add('QCheckBox', setText='-', setObjectName='chk006', setChecked=True, setToolTip='Perform delete along negative axis.')
		tb003.contextMenu.add('QRadioButton', setText='X', setObjectName='chk007', setChecked=True, setToolTip='Perform delete along X axis.')
		tb003.contextMenu.add('QRadioButton', setText='Y', setObjectName='chk008', setToolTip='Perform delete along Y axis.')
		tb003.contextMenu.add('QRadioButton', setText='Z', setObjectName='chk009', setToolTip='Perform delete along Z axis.')
		self.connect_('chk006-9', 'toggled', self.chk006_9, tb003.contextMenu)

		tb004 = self.edit_ui.tb004
		tb004.contextMenu.add('QCheckBox', setText='All Nodes', setObjectName='chk026', setToolTip='Effect all nodes or only those currently selected.')
		tb004.contextMenu.add('QCheckBox', setText='UnLock', setObjectName='chk027', setChecked=True, setToolTip='Unlock nodes (else lock).')
		tb004.contextMenu.chk027.toggled.connect(lambda state: tb004.setText('Unlock Nodes' if state else 'Lock Nodes'))


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

		