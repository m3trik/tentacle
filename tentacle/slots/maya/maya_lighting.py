# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class Lighting(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		ctx = self.lighting_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.lighting_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.lighting_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.lighting_ui.draggable_header.contextMenu.cmb000

		# if index>0:
		# 	if index==cmd.items.index(''):
		# 		pass
		# 	cmb.setCurrentIndex(0)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------