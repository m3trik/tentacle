# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.utilities import Utilities



class Utilities_max(Utilities, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.utilities.draggable_header.ctxMenu.cmb000
		files = ['']
		cmb.addItems_(files, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.utilities.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''Measure
		'''
		maxEval('macros.run \"Tools\" \"two_point_dist\"')


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