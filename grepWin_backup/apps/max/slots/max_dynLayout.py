# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from max_init import *



class DynLayout(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.dynLayout_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.dynLayout_ui.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''pass
		pass





#module name
print os.path.splitext(os.path.basename(__file__))[0]
# -----------------------------------------------
# Notes
# -----------------------------------------------