# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Duplicate(Slots):
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
		ctx = self.duplicate_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.duplicate_ui.draggable_header


	def radialArray(self):
		'''Radial Array: Reset
		'''
		self.chk015() #calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg


	def duplicateArray(self):
		'''Duplicate: Reset
		'''
		self.chk016() #calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg


	def chk007(self, state=None):
		'''Duplicate: Translate To Components
		'''
		if self.duplicate_linear_ui.chk007.isChecked():
			self.toggleWidgets(setEnabled='chk008,b034,cmb001', setDisabled='chk000,chk009,s005')
			self.b008()
		else:
			self.toggleWidgets(setDisabled='chk008,b034,cmb001', setEnabled='chk000,chk009,s005')


	def chk011(self, state=None):
		'''Radial Array: Instance/Duplicate Toggle
		'''
		self.chk015() #calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg


	def chk012(self, state=None):
		'''Radial Array: X Axis
		'''
		self.toggleWidgets(setChecked='chk012', setUnChecked='chk013,chk014')
		self.chk015()


	def chk013(self, state=None):
		'''Radial Array: Y Axis
		'''
		self.toggleWidgets(setChecked='chk013', setUnChecked='chk012,chk014')
		self.chk015()


	def chk014(self, state=None):
		'''Radial Array: Z Axis
		'''
		self.toggleWidgets(setChecked='chk014', setUnChecked='chk012,chk013')
		self.chk015()


	def b002(self):
		'''Duplicate: Create
		'''
		self.duplicate_linear_ui.chk016.setChecked(False) #must be in the false unchecked state to catch the create flag in chk015
		self.chk016(create=True)


	def b003(self):
		'''Radial Array: Create
		'''
		self.duplicate_radial_ui.chk015.setChecked(False) #must be in the false unchecked state to catch the create flag in chk015
		self.chk015(create=True)


	def b006(self):
		'''
		'''
		self.sb.parent().setUi('duplicate_linear')

		self.duplicate_linear_ui.s002.valueChanged.connect(self.duplicateArray) #update duplicate array
		self.duplicate_linear_ui.s003.valueChanged.connect(self.duplicateArray)
		self.duplicate_linear_ui.s004.valueChanged.connect(self.duplicateArray)
		self.duplicate_linear_ui.s005.valueChanged.connect(self.duplicateArray)
		self.duplicate_linear_ui.s007.valueChanged.connect(self.duplicateArray) 
		self.duplicate_linear_ui.s008.valueChanged.connect(self.duplicateArray)
		self.duplicate_linear_ui.s009.valueChanged.connect(self.duplicateArray)


	def b007(self):
		'''
		'''
		self.sb.parent().setUi('duplicate_radial')

		self.duplicate_radial_ui.s000.valueChanged.connect(self.radialArray) #update radial array
		self.duplicate_radial_ui.s001.valueChanged.connect(self.radialArray) 


	def b008(self):
		'''Add Selected Components To cmb001
		'''
		cmb = self.duplicate_linear_ui.cmb001

		selection = pm.ls (selection=1, flatten=1)

		for obj in selection:
			cmb.add(obj)
