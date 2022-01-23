# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.dynLayout import DynLayout
from ui.static.max.dynLayout_ui_max import DynLayout_ui_max



class DynLayout(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		DynLayout_ui_max.__init__(self, *args, **kwargs)
		DynLayout.__init__(self, *args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.dynLayout_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.dynLayout_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''
		'''
		self.tcl.sb.getMethod('edit', 'tb001')()









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------