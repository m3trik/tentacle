# !/usr/bin/python
# coding=utf-8
from slots.blender import *
from slots.deformation import Deformation



class Deformation_blender(Deformation, Slots_blender):
	def __init__(self, *args, **kwargs):
		Slots_blender.__init__(self, *args, **kwargs)
		Deformation.__init__(self, *args, **kwargs)

		cmb = self.deformation_ui.draggable_header.contextMenu.cmb000
		list_ = []
		cmb.addItems_(list_, '')


	def cmb000(self, index=-1):
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