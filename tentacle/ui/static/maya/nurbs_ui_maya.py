# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Nurbs_ui



class Nurbs_ui_maya(Nurbs_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		Nurbs_ui.__init__(self, *args, **kwargs)

		ctx = self.nurbs_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Curve Operations')
		
		cmb = self.nurbs_ui.draggable_header.contextMenu.cmb000
		items = ['Project Curve','Duplicate Curve','Create Curve from Poly','Bend Curve', 'Curl Curve','Modify Curve Curvature','Smooth Curve','Straighten Curves','Extrude Curves','Revolve Curves','Loft Curves','Planar Curves','Insert Isoparms','Insert Knot','Rebuild Curve','Extend Curve', 'Extend Curve On Surface']
		cmb.addItems_(items, 'Maya Curve Operations')
		
		cmb = self.nurbs_ui.cmb001
		items = ['Ep Curve Tool','CV Curve Tool','Bezier Curve Tool','Pencil Curve Tool','2 Point Circular Arc','3 Point Circular Arc']
		cmb.addItems_(items, 'Create Curve')

		ctx = self.nurbs_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Degree:', setObjectName='s002', setValue=3, setMinMax_='0-9999 step1', setToolTip='The degree of the resulting surface.')
			ctx.add('QSpinBox', setPrefix='Start Sweep:', setObjectName='s003', setValue=3, setMinMax_='0-360 step1', setToolTip='	The value for the start sweep angle.')
			ctx.add('QSpinBox', setPrefix='End Sweep:', setObjectName='s004', setValue=3, setMinMax_='0-360 step1', setToolTip='The value for the end sweep angle.')
			ctx.add('QSpinBox', setPrefix='Sections:', setObjectName='s005', setValue=8, setMinMax_='0-9999 step1', setToolTip='The number of surface spans between consecutive curves in the loft.')
			ctx.add('QCheckBox', setText='Range', setObjectName='chk006', setChecked=False, setToolTip='Force a curve range on complete input curve.')
			ctx.add('QCheckBox', setText='Polygon', setObjectName='chk007', setChecked=True, setToolTip='The object created by this operation.')
			ctx.add('QCheckBox', setText='Auto Correct Normal', setObjectName='chk008', setChecked=False, setToolTip='Attempt to reverse the direction of the axis in case it is necessary to do so for the surface normals to end up pointing to the outside of the object.')
			ctx.add('QCheckBox', setText='Use Tolerance', setObjectName='chk009', setChecked=False, setToolTip='Use the tolerance, or the number of sections to control the sections.')
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance:', setObjectName='s006', setValue=0.001, setMinMax_='0-9999 step.001', setToolTip='Tolerance to build to (if useTolerance attribute is set).')

		ctx = self.nurbs_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Uniform', setObjectName='chk000', setChecked=True, setToolTip='The resulting surface will have uniform parameterization in the loft direction. If set to false, the parameterization will be chord length.')
			ctx.add('QCheckBox', setText='Close', setObjectName='chk001', setChecked=False, setToolTip='The resulting surface will be closed (periodic) with the start (end) at the first curve. If set to false, the surface will remain open.')
			ctx.add('QSpinBox', setPrefix='Degree:', setObjectName='s000', setValue=3, setMinMax_='0-9999 step1', setToolTip='The degree of the resulting surface.')
			ctx.add('QCheckBox', setText='Auto Reverse', setObjectName='chk002', setChecked=False, setToolTip='The direction of the curves for the loft is computed automatically. If set to false, the values of the multi-use reverse flag are used instead.')
			ctx.add('QSpinBox', setPrefix='Section Spans:', setObjectName='s001', setValue=1, setMinMax_='0-9999 step1', setToolTip='The number of surface spans between consecutive curves in the loft.')
			ctx.add('QCheckBox', setText='Range', setObjectName='chk003', setChecked=False, setToolTip='Force a curve range on complete input curve.')
			ctx.add('QCheckBox', setText='Polygon', setObjectName='chk004', setChecked=True, setToolTip='The object created by this operation.')
			ctx.add('QCheckBox', setText='Reverse Surface Normals', setObjectName='chk005', setChecked=True, setToolTip='The surface normals on the output NURBS surface will be reversed. This is accomplished by swapping the U and V parametric directions.')
			ctx.add('QCheckBox', setText='Angle Loft Between Two Curves', setObjectName='chk010', setChecked=False, setToolTip='Perform a loft at an angle between two selected curves or polygon edges (that will be extracted as curves).')
			ctx.add('QSpinBox', setPrefix='Angle Loft: Spans:', setObjectName='s007', setValue=6, setMinMax_='2-9999 step1', setToolTip='Angle loft: Number of duplicated points (spans).')

