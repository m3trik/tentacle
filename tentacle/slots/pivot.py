# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Pivot(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		ctx = self.sb.pivot.draggable_header.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.pivot.draggable_header


	def b000(self):
		'''Center Pivot: Object
		'''
		tb = self.sb.pivot.tb001
		tb.ctxMenu.chk003.setChecked(True)
		self.tb001()


	def b001(self):
		'''Center Pivot: Component
		'''
		tb = self.sb.pivot.tb001
		tb.ctxMenu.chk002.setChecked(True)
		self.tb001()


	def b002(self):
		'''Center Pivot: World
		'''
		tb = self.sb.pivot.tb001
		tb.ctxMenu.chk004.setChecked(True)
		self.tb001()
