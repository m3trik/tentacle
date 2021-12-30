# !/usr/bin/python
# coding=utf-8
from maya_init import *



class Vfx(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		dh = self.vfx_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.vfx_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')


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


	def b000(self):
		''''''
		pass


	def b001(self):
		''''''
		pass


	def b002(self):
		''''''
		pass


	def b003(self):
		''''''
		pass


	def b004(self):
		''''''
		pass


	def b005(self):
		''''''
		pass


	def b006(self):
		''''''
		pass


	def b007(self):
		''''''
		pass


	def b008(self):
		''''''
		mel.eval("")


	def b009(self):
		''''''
		pass






#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------