# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.vfx import Vfx



class Vfx_maya(Vfx, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Vfx.__init__(self, *args, **kwargs)

		cmb = self.vfx_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.vfx_ui.draggable_header.contextMenu.cmb000

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