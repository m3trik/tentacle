# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.utilities import Utilities



class Utilities_maya(Utilities, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Utilities.__init__(self, *args, **kwargs)

		cmb = self.utilities_ui.draggable_header.contextMenu.cmb000
		files = ['']
		cmb.addItems_(files, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.utilities_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''Measure
		'''
		mel.eval("DistanceTool;")


	def b001(self):
		'''Annotation
		'''
		mel.eval('CreateAnnotateNode;')


	def b002(self):
		'''Calculator
		'''
		mel.eval('calculator;')


	def b003(self):
		'''Grease Pencil
		'''
		mel.eval('greasePencilCtx;')









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------