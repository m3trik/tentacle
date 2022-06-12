# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Polygons(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui object of <name>. ie. self.polygons_ui
					<widget> (registered widget) = Any widget previously registered in the switchboard module. ie. self.PushButton
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
		'''
		ctx = self.polygons_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.ComboBox, setObjectName='cmb000', setToolTip='')

		ctx = self.polygons_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Distance: ', setObjectName='s002', setMinMax_='0.0000-10 step.0005', setValue=0.0005, setHeight_=20, setToolTip='Merge Distance.')

		ctx = self.polygons_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s003', setMinMax_='0-10000 step1', setValue=0, setHeight_=20, setToolTip='Subdivision Amount.')

		ctx = self.polygons_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Merge', setObjectName='chk000', setChecked=True, setHeight_=20, setToolTip='Combine selected meshes and merge any coincident verts/edges.')

		ctx = self.polygons_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Keep Faces Together', setObjectName='chk002', setChecked=True, setHeight_=20, setToolTip='Keep edges/faces together.')
			ctx.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s004', setMinMax_='1-10000 step1', setValue=1, setHeight_=20, setToolTip='Subdivision Amount.')

		ctx = self.polygons_ui.tb004.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', setMinMax_='0.00-100 step.05', setValue=0.25, setHeight_=20, setToolTip='Bevel Width.')

		ctx = self.polygons_ui.tb005.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Duplicate', setObjectName='chk014', setChecked=True, setToolTip='Duplicate any selected faces, leaving the originals.')
			ctx.add('QCheckBox', setText='Separate', setObjectName='chk015', setChecked=True, setToolTip='Separate mesh objects after detaching faces.')
			# ctx.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')

		ctx = self.polygons_ui.tb006.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Offset: ', setObjectName='s001', setMinMax_='0.00-100 step.01', setValue=2.00, setHeight_=20, setToolTip='Offset amount.')

		ctx = self.polygons_ui.tb007.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='U', setObjectName='chk008', setChecked=True, setHeight_=20, setToolTip='Divide facet: U coordinate.')
			ctx.add('QCheckBox', setText='V', setObjectName='chk009', setChecked=True, setHeight_=20, setToolTip='Divide facet: V coordinate.')
			ctx.add('QCheckBox', setText='Tris', setObjectName='chk010', setHeight_=20, setToolTip='Divide facet: Tris.')

		ctx = self.polygons_ui.tb008.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Union', setObjectName='chk011', setHeight_=20, setToolTip='Fuse two objects together.')
			ctx.add('QRadioButton', setText='Difference', setObjectName='chk012', setChecked=True, setHeight_=20, setToolTip='Indents one object with the shape of another at the point of their intersection.')
			ctx.add('QRadioButton', setText='Intersection', setObjectName='chk013', setHeight_=20, setToolTip='Keep only the interaction point of two objects.')

		ctx = self.polygons_ui.tb009.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s005', setMinMax_='.000-100 step.05', setValue=10, setToolTip='Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.')
			ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk016', setChecked=True, setToolTip='Freeze Transformations on the object that is being snapped to.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.polygons_ui.draggable_header


	def chk008(self, state=None):
		'''Divide Facet: Split U
		'''
		self.toggleWidgets(setUnChecked='chk010')


	def chk009(self, state=None):
		'''Divide Facet: Split V
		'''
		self.toggleWidgets(setUnChecked='chk010')


	def chk010(self, state=None):
		'''Divide Facet: Tris
		'''
		self.toggleWidgets(setUnChecked='chk008,chk009')

