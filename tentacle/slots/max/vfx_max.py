# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.vfx import Vfx
from ui.static.max.vfx_ui_max import Vfx_ui_max



class Vfx(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Vfx_ui_max.__init__(self, *args, **kwargs)
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