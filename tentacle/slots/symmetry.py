# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Symmetry(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		dh = self.symmetry_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		# w2 = self.tcl.sb.getWidget('chk002', self.tcl.sb.getUi('symmetry', level=3))
		# print ('here ----->', w2)
		# self.symmetry_submenu_ui.chk002.toggled.connect(lambda w2=w2: self.tcl.sb.syncAttributes(self.symmetry_submenu_ui.chk002, w2))


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.symmetry_ui.draggable_header


	def chk000(self, state=None):
		'''Symmetry X
		'''
		self.toggleWidgets(setUnChecked='chk001,chk002')
		state = self.symmetry_ui.chk000.isChecked() #symmetry button state
		self.setSymmetry(state, 'x')


	def chk001(self, state=None):
		'''Symmetry Y
		'''
		self.toggleWidgets(setUnChecked='chk000,chk002')
		state = self.symmetry_ui.chk001.isChecked() #symmetry button state
		self.setSymmetry(state, 'y')


	def chk002(self, state=None):
		'''Symmetry Z
		'''
		self.toggleWidgets(setUnChecked='chk000,chk001')
		state = self.symmetry_ui.chk002.isChecked() #symmetry button state
		self.setSymmetry(state, 'z')


	def chk004(self, state=None):
		'''Symmetry: Object
		'''
		self.symmetry_ui.chk005.setChecked(False) #uncheck symmetry:topological

	