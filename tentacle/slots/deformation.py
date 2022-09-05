# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Deformation(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		ctx = self.sb.deformation.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.deformation.draggable_header
