# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Scene(Slots):
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
		self.scene_ui.t000.returnPressed.connect(self.t001) #preform rename on returnPressed

		ctx = self.scene_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Scene Editors')

		ctx = self.scene_ui.t000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Ignore Case', setObjectName='chk000', setToolTip='Search case insensitive.')
			ctx.add('QCheckBox', setText='Regular Expression', setObjectName='chk001', setToolTip='When checked, regular expression syntax is used instead of the default \'*\' and \'|\' wildcards.')

		ctx = self.scene_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', addItems=['capitalize', 'upper', 'lower', 'swapcase', 'title'], setObjectName='cmb001', setToolTip='Set desired python case operator.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.scene_ui.draggable_header


	def t000(self, state=None):
		'''Find
		'''
		t000 = self.scene_ui.t000


	