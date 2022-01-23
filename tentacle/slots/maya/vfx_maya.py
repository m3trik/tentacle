# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.vfx import Vfx
from ui.static.maya.vfx_ui_maya import Vfx_ui_maya



class Vfx_maya(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Vfx_ui_maya.__init__(self, *args, **kwargs)
		Vfx.__init__(self, *args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.vfx_ui.draggable_header


	def cmb000(self, index=-1):
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