# !/usr/bin/python
# coding=utf-8
from uitk.slots import Slots



class Symmetry(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.symmetry.draggable_header
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.symmetry.draggable_header


	def chk000(self, state=None):
		'''Symmetry X
		'''
		self.sb.toggleWidgets(setUnChecked='chk001,chk002')
		self.setSymmetry(state, 'x')


	def chk001(self, state=None):
		'''Symmetry Y
		'''
		self.sb.toggleWidgets(setUnChecked='chk000,chk002')
		self.setSymmetry(state, 'y')


	def chk002(self, state=None):
		'''Symmetry Z
		'''
		self.sb.toggleWidgets(setUnChecked='chk000,chk001')
		self.setSymmetry(state, 'z')


	def chk004(self, state=None):
		'''Symmetry: Object
		'''
		self.sb.symmetry.chk005.setChecked(False) #uncheck symmetry:topological









# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



#deprecated:
		#sync widgets
		# self.sb.setSyncConnections(self.sb.transform.menu_.chk000, self.sb.transform_submenu.chk000, attributes='setChecked')
		# self.sb.setSyncConnections(self.sb.transform.menu_.chk001, self.sb.transform_submenu.chk001, attributes='setChecked')
		# self.sb.setSyncConnections(self.sb.transform.menu_.chk002, self.sb.transform_submenu.chk002, attributes='setChecked')