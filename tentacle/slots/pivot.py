# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Pivot(Slots):
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
		ctx = self.pivot_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.pivot_ui.draggable_header


	def b000(self):
		'''Center Pivot: Object
		'''
		tb = self.pivot_ui.tb001
		tb.contextMenu.chk003.setChecked(True)
		self.tb001()


	def b001(self):
		'''Center Pivot: Component
		'''
		tb = self.pivot_ui.tb001
		tb.contextMenu.chk002.setChecked(True)
		self.tb001()


	def b002(self):
		'''Center Pivot: World
		'''
		tb = self.pivot_ui.tb001
		tb.contextMenu.chk004.setChecked(True)
		self.tb001()
