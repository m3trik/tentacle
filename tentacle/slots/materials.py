# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Materials(Slots):
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
		self.materials_submenu_ui.b003.setVisible(False) #hide the current material submenu button until a material is available.

		cmb002 = self.materials_ui.cmb002
		cmb002.contextMenu.add('QComboBox', setObjectName='cmb001', addItems=['Scene Materials', 'ID Map Materials', 'Favorite Materials'], setToolTip='Filter materials list based on type.')
		cmb002.contextMenu.add(self.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
		cmb002.contextMenu.add(self.Label, setText='Rename', setObjectName='lbl001', setToolTip='Rename the current material.')
		cmb002.contextMenu.add(self.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current material.')
		cmb002.contextMenu.add(self.Label, setText='Delete All Unused Materials', setObjectName='lbl003', setToolTip='Delete All unused materials.')
		cmb002.beforePopupShown.connect(self.cmb002) #refresh comboBox contents before showing it's menu.
		cmb002.returnPressed.connect(lambda: self.lbl001(setEditable=False))
		cmb002.currentIndexChanged.connect(lambda: cmb002.contextMenu.setTitle(cmb002.currentText())) #set the popup title to be the current materials name.
		cmb002.contextMenu.cmb001.currentIndexChanged.connect(lambda: self.materials_ui.group000.setTitle(cmb002.contextMenu.cmb001.currentText())) #set the groupbox title to reflect the current filter.
		cmb002.contextMenu.cmb001.currentIndexChanged.connect(self.cmb002) #refresh cmb002 contents.
		self.cmb002() #initialize the materials list

		tb000 = self.materials_ui.tb000
		tb000.contextMenu.add('QCheckBox', setText='All Objects', setObjectName='chk003', setToolTip='Search all scene objects, or only those currently selected.')
		tb000.contextMenu.add('QCheckBox', setText='Shell', setObjectName='chk005', setToolTip='Select entire shell.')
		tb000.contextMenu.add('QCheckBox', setText='Invert', setObjectName='chk006', setToolTip='Invert Selection.')

		tb002 = self.materials_ui.tb002
		tb002.contextMenu.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
		tb002.contextMenu.add('QRadioButton', setText='New Material', setObjectName='chk009', setToolTip='Assign a new material.')
		tb002.contextMenu.add('QRadioButton', setText='New Random Material', setObjectName='chk008', setToolTip='Assign a new random ID material.')
		tb002.contextMenu.chk007.clicked.connect(lambda state: tb002.setText('Assign Current')) 
		tb002.contextMenu.chk009.clicked.connect(lambda state: tb002.setText('Assign New'))
		tb002.contextMenu.chk008.clicked.connect(lambda state: tb002.setText('Assign Random'))


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.materials_ui.draggable_header


	def b000(self):
		'''Material List: Delete
		'''
		self.lbl002()


	def b001(self):
		'''Material List: Edit
		'''
		self.lbl000()


	def b003(self):
		'''Assign: Assign Current
		'''
		self.materials_ui.tb002.contextMenu.chk007.setChecked(True)
		self.materials_ui.tb002.setText('Assign Current')
		self.tb002()


	def b004(self):
		'''Assign: Assign Random
		'''
		self.materials_ui.tb002.contextMenu.chk008.setChecked(True)
		self.materials_ui.tb002.setText('Assign Random')
		self.tb002()


	def b005(self):
		'''Assign: Assign New
		'''
		self.materials_ui.tb002.contextMenu.chk009.setChecked(True)
		self.materials_ui.tb002.setText('Assign New')
		self.tb002()

