# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Materials_ui



class Materials_ui_max(Materials_ui):
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
		Materials_ui.__init__(self, *args, **kwargs)

		ctx = self.materials_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Material Editors')
			ctx.add(self.tcl.wgts.Label, setText='Material Attributes', setObjectName='lbl004', setToolTip='Show the material attributes in the attribute editor.')

		cmb = self.materials_ui.draggable_header.contextMenu.cmb000
		items = ['Hypershade']
		cmb.addItems_(items, 'Maya Material Editors')

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
