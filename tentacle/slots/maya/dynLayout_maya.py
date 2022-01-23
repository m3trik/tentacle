# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from ui.static.maya.dynLayout_ui_maya import DynLayout_ui_maya



class DynLayout(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Duplicate_ui_maya.__init__(self, *args, **kwargs)


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