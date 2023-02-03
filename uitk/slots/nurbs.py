# !/usr/bin/python
# coding=utf-8
from uitk.slots import Slots


class Nurbs(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.nurbs.draggable_header
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='Maya Curve Operations')

		tb000 = self.sb.nurbs.tb000
		tb000.ctxMenu.add('QSpinBox', setPrefix='Degree:', setObjectName='s002', setValue=3, setMinMax_='0-9999 step1', setToolTip='The degree of the resulting surface.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Start Sweep:', setObjectName='s003', setValue=3, setMinMax_='0-360 step1', setToolTip='	The value for the start sweep angle.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='End Sweep:', setObjectName='s004', setValue=3, setMinMax_='0-360 step1', setToolTip='The value for the end sweep angle.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Sections:', setObjectName='s005', setValue=8, setMinMax_='0-9999 step1', setToolTip='The number of surface spans between consecutive curves in the loft.')
		tb000.ctxMenu.add('QCheckBox', setText='Range', setObjectName='chk006', setChecked=False, setToolTip='Force a curve range on complete input curve.')
		tb000.ctxMenu.add('QCheckBox', setText='Polygon', setObjectName='chk007', setChecked=True, setToolTip='The object created by this operation.')
		tb000.ctxMenu.add('QCheckBox', setText='Auto Correct Normal', setObjectName='chk008', setChecked=False, setToolTip='Attempt to reverse the direction of the axis in case it is necessary to do so for the surface normals to end up pointing to the outside of the object.')
		tb000.ctxMenu.add('QCheckBox', setText='Use Tolerance', setObjectName='chk009', setChecked=False, setToolTip='Use the tolerance, or the number of sections to control the sections.')
		tb000.ctxMenu.add('QDoubleSpinBox', setPrefix='Tolerance:', setObjectName='s006', setValue=0.001, setMinMax_='0-9999 step.001', setToolTip='Tolerance to build to (if useTolerance attribute is set).')

		tb001 = self.sb.nurbs.tb001
		tb001.ctxMenu.add('QCheckBox', setText='Uniform', setObjectName='chk000', setChecked=True, setToolTip='The resulting surface will have uniform parameterization in the loft direction. If set to false, the parameterization will be chord length.')
		tb001.ctxMenu.add('QCheckBox', setText='Close', setObjectName='chk001', setChecked=False, setToolTip='The resulting surface will be closed (periodic) with the start (end) at the first curve. If set to false, the surface will remain open.')
		tb001.ctxMenu.add('QSpinBox', setPrefix='Degree:', setObjectName='s000', setValue=3, setMinMax_='0-9999 step1', setToolTip='The degree of the resulting surface.')
		tb001.ctxMenu.add('QCheckBox', setText='Auto Reverse', setObjectName='chk002', setChecked=False, setToolTip='The direction of the curves for the loft is computed automatically. If set to false, the values of the multi-use reverse flag are used instead.')
		tb001.ctxMenu.add('QSpinBox', setPrefix='Section Spans:', setObjectName='s001', setValue=1, setMinMax_='0-9999 step1', setToolTip='The number of surface spans between consecutive curves in the loft.')
		tb001.ctxMenu.add('QCheckBox', setText='Range', setObjectName='chk003', setChecked=False, setToolTip='Force a curve range on complete input curve.')
		tb001.ctxMenu.add('QCheckBox', setText='Polygon', setObjectName='chk004', setChecked=True, setToolTip='The object created by this operation.')
		tb001.ctxMenu.add('QCheckBox', setText='Reverse Surface Normals', setObjectName='chk005', setChecked=True, setToolTip='The surface normals on the output NURBS surface will be reversed. This is accomplished by swapping the U and V parametric directions.')
		tb001.ctxMenu.add('QCheckBox', setText='Angle Loft Between Two Curves', setObjectName='chk010', setChecked=False, setToolTip='Perform a loft at an angle between two selected curves or polygon edges (that will be extracted as curves).')
		tb001.ctxMenu.add('QSpinBox', setPrefix='Angle Loft: Spans:', setObjectName='s007', setValue=6, setMinMax_='2-9999 step1', setToolTip='Angle loft: Number of duplicated points (spans).')
