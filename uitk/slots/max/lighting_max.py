# !/usr/bin/python
# coding=utf-8
from uitk.slots.max import *
from uitk.slots.lighting import Lighting



class Lighting_max(Lighting, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.lighting.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.lighting.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.lighting.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------