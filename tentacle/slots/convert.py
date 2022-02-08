# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Convert(Slots):
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
		ctx = self.convert_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.convert_ui.draggable_header


	def b000(self):
		'''Polygon Edges to Curve
		'''
		self.cmb001(index=5)


	def b001(self):
		'''Instance to Object
		'''
		self.cmb001(index=18)


	def b002(self):
		'''NURBS to Polygons
		'''
		self.cmb001(index=1)


	def b003(self):
		'''Smooth Mesh Preview to Polygons
		'''
		self.cmb001(index=4)
