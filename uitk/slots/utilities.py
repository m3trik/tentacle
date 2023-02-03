# !/usr/bin/python
# coding=utf-8
from uitk.slots import Slots



class Utilities(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		ctx = self.sb.utilities.draggable_header.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

	
	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.utilities.draggable_header


