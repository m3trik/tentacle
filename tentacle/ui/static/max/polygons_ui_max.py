# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Polygons_ui



class Polygons_ui_max(Polygons_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (passed in via the switchboard module's 'getClassInstanceFromUiName' method.)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		Polygons_ui.__init__(self, *args, **kwargs)

		ctx = self.polygons_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.polygons_ui.draggable_header.contextMenu.cmb000
		list_ = ['Extrude','Bevel','Bridge','Combine','Merge Vertex','Offset Edgeloop','Edit Edgeflow','Extract Curve','Poke','Wedge','Assign Invisible']
		cmb.addItems_(list_, 'Maya Polygon Operations')

		ctx = self.polygons_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Distance: ', setObjectName='s002', setMinMax_='0.000-10 step.005', setValue=0.001, setHeight_=20, setToolTip='Merge Distance.')

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

		ctx = self.polygons_ui.tb008.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Union', setObjectName='chk011', setHeight_=20, setToolTip='Fuse two objects together.')
			ctx.add('QRadioButton', setText='Difference', setObjectName='chk012', setChecked=True, setHeight_=20, setToolTip='Indents one object with the shape of another at the point of their intersection.')
			ctx.add('QRadioButton', setText='Intersection', setObjectName='chk013', setHeight_=20, setToolTip='Keep only the interaction point of two objects.')

		ctx = self.polygons_ui.tb009.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s005', setMinMax_='.000-100 step.05', setValue=10, setToolTip='Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.')
			ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk016', setChecked=True, setToolTip='Freeze Transformations on the object that is being snapped to.')

	