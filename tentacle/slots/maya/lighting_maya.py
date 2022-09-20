# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.lighting import Lighting



class Lighting_maya(Lighting, Slots_maya):
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

		# if index>0:
		# 	if index==cmd.items.index(''):
		# 		pass
		# 	cmb.setCurrentIndex(0)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------