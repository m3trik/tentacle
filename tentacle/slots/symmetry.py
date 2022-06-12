# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Symmetry(Slots):
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
		dh = self.symmetry_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.symmetry_ui.draggable_header


	def chk000(self, state=None):
		'''Symmetry X
		'''
		self.toggleWidgets(setUnChecked='chk001,chk002')
		self.setSymmetry(state, 'x')


	def chk001(self, state=None):
		'''Symmetry Y
		'''
		self.toggleWidgets(setUnChecked='chk000,chk002')
		self.setSymmetry(state, 'y')


	def chk002(self, state=None):
		'''Symmetry Z
		'''
		self.toggleWidgets(setUnChecked='chk000,chk001')
		self.setSymmetry(state, 'z')


	def chk004(self, state=None):
		'''Symmetry: Object
		'''
		self.symmetry_ui.chk005.setChecked(False) #uncheck symmetry:topological

	