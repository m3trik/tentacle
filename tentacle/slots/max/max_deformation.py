# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Deformation(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.deformation_ui.draggable_header.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.deformation_ui.draggable_header.contextMenu.cmb000
		list_ = []
		cmb.addItems_(list_, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.deformation_ui.draggable_header


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