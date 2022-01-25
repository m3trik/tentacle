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
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		ctx = self.materials_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Material Editors')

		cmb = self.materials_ui.cmb002
		ctx = cmb.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', setObjectName='cmb001', addItems=['Scene Materials', 'ID Map Materials', 'Favorite Materials'], setToolTip='Filter materials list based on type.')
			ctx.add(self.tcl.wgts.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
			ctx.add(self.tcl.wgts.Label, setText='Rename', setObjectName='lbl001', setToolTip='Rename the current material.')
			ctx.add(self.tcl.wgts.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current material.')
			ctx.add(self.tcl.wgts.Label, setText='Delete All Unused Materials', setObjectName='lbl003', setToolTip='Delete All unused materials.')
			cmb.beforePopupShown.connect(self.cmb002) #refresh comboBox contents before showing it's menu.
			cmb.returnPressed.connect(lambda: self.lbl001(setEditable=False))
			cmb.currentIndexChanged.connect(lambda: ctx.setTitle(cmb.currentText())) #set the popup title to be the current materials name.
			ctx.cmb001.currentIndexChanged.connect(lambda: self.materials_ui.group000.setTitle(ctx.cmb001.currentText())) #set the groupbox title to reflect the current filter.
			ctx.cmb001.currentIndexChanged.connect(self.cmb002) #refresh cmb002 contents.
			self.cmb002() #initialize the materials list

		ctx = self.materials_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='All Objects', setObjectName='chk003', setToolTip='Search all scene objects, or only those currently selected.')
			ctx.add('QCheckBox', setText='Shell', setObjectName='chk005', setToolTip='Select entire shell.')
			ctx.add('QCheckBox', setText='Invert', setObjectName='chk006', setToolTip='Invert Selection.')

		tb = self.materials_ui.tb002
		ctx = tb.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
			ctx.add('QRadioButton', setText='New Material', setObjectName='chk009', setToolTip='Assign a new material.')
			ctx.add('QRadioButton', setText='New Random Material', setObjectName='chk008', setToolTip='Assign a new random ID material.')
			ctx.chk007.clicked.connect(lambda state: tb.setText('Assign Current')) 
			ctx.chk009.clicked.connect(lambda state: tb.setText('Assign New'))
			ctx.chk008.clicked.connect(lambda state: tb.setText('Assign Random'))


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

