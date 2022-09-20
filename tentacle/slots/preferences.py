# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Preferences(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		ctx = self.sb.preferences.draggable_header.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.preferences.draggable_header


	def cmb003(self, index=-1):
		'''Ui Style: Set main ui style using QStyleFactory
		'''
		cmb = self.sb.preferences.cmb003

		if index>0:
			self.sb.parent().app.setStyle(cmb.items[index])