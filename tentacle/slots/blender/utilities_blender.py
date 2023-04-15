# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.utilities import Utilities



class Utilities_blender(Utilities, Slots_blender):
	def __init__(self, *args, **kwargs):
		Slots_blender.__init__(self, *args, **kwargs)
		Utilities.__init__(self, *args, **kwargs)

		cmb = self.sb.utilities.draggableHeader.ctxMenu.cmb000
		files = ['']
		cmb.addItems_(files, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.utilities.draggableHeader.ctxMenu.cmb000

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
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------