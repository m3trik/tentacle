# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.deformation import Deformation



class Deformation_max(Deformation, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Deformation.__init__(self, *args, **kwargs)

		cmb = self.deformation_ui.draggable_header.contextMenu.cmb000
		list_ = []
		cmb.addItems_(list_, '')


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.deformation_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''
		'''
		pass









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------