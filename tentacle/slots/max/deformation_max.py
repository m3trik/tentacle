# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.deformation import Deformation



class Deformation_max(Deformation, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.deformation.draggable_header.ctxMenu.cmb000
		items = []
		cmb.addItems_(items, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.deformation.draggable_header.ctxMenu.cmb000

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