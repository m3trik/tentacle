# !/usr/bin/python
# coding=utf-8
from slots import Slots



class DynLayout(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		ctx = self.sb.dynLayout.draggable_header.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')
			ctx.add('QPushButton', setText='Delete History', setObjectName='b000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.dynLayout.draggable_header


	def b000(self):
		'''
		'''
		self.sb.getMethod('edit', 'tb001')()
