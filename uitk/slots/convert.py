# !/usr/bin/python
# coding=utf-8
from uitk.slots import Slots



class Convert(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		ctx = self.sb.convert.draggable_header.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.convert.draggable_header


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
