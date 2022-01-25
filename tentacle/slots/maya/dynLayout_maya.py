# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.dynLayout import DynLayout



class DynLayout_maya(DynLayout, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		DynLayout.__init__(self, *args, **kwargs)

		cmb = self.dynLayout_ui.draggable_header.contextMenu.cmb000
		list_ = []
		cmb.addItems_(list_, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.dynLayout_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------