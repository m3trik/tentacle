# !/usr/bin/python
# coding=utf-8
from slots.blender import *
from slots.lighting import Lighting



class Lighting_blender(Lighting, Slots_blender):
	def __init__(self, *args, **kwargs):
		Slots_blender.__init__(self, *args, **kwargs)
		Lighting.__init__(self, *args, **kwargs)

		cmb = self.sb.lighting.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.lighting.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.lighting.draggable_header.contextMenu.cmb000

		# if index>0:
		# 	if index==cmd.items.index(''):
		# 		pass
		# 	cmb.setCurrentIndex(0)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------