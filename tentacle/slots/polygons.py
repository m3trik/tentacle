# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots



class Polygons(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.polygons.draggableHeader
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

		tb000 = self.sb.polygons.tb000
		tb000.ctxMenu.add('QDoubleSpinBox', setPrefix='Distance: ', setObjectName='s002', setMinMax_='0.0000-10 step.0005', setValue=0.0005, setHeight_=20, setToolTip='Merge Distance.')
		tb000.ctxMenu.add('QPushButton', setText='Set Distance', setObjectName='b005', setHeight_=20, setToolTip='Set the distance using two selected vertices.\nElse; return the Distance to it\'s default value')

		tb001 = self.sb.polygons.tb001
		tb001.ctxMenu.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s003', setMinMax_='0-10000 step1', setValue=0, setHeight_=20, setToolTip='Subdivision Amount.')

		tb002 = self.sb.polygons.tb002
		tb002.ctxMenu.add('QCheckBox', setText='Merge', setObjectName='chk000', setChecked=True, setHeight_=20, setToolTip='Combine selected meshes and merge any coincident verts/edges.')

		tb003 = self.sb.polygons.tb003
		tb003.ctxMenu.add('QCheckBox', setText='Keep Faces Together', setObjectName='chk002', setChecked=True, setHeight_=20, setToolTip='Keep edges/faces together.')
		tb003.ctxMenu.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s004', setMinMax_='1-10000 step1', setValue=1, setHeight_=20, setToolTip='Subdivision Amount.')

		tb004 = self.sb.polygons.tb004
		tb004.ctxMenu.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', setMinMax_='0.00-100 step.05', setValue=0.25, setHeight_=20, setToolTip='Bevel Width.')
		tb004.ctxMenu.add('QDoubleSpinBox', setPrefix='Segments: ', setObjectName='s006', setMinMax_='1-100 step1', setValue=1, setHeight_=20, setToolTip='Bevel Segments.')

		tb005 = self.sb.polygons.tb005
		tb005.ctxMenu.add('QCheckBox', setText='Duplicate', setObjectName='chk014', setChecked=True, setToolTip='Duplicate any selected faces, leaving the originals.')
		tb005.ctxMenu.add('QCheckBox', setText='Separate', setObjectName='chk015', setChecked=True, setToolTip='Separate mesh objects after detaching faces.')
		# tb005.ctxMenu.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')

		tb006 = self.sb.polygons.tb006
		tb006.ctxMenu.add('QDoubleSpinBox', setPrefix='Offset: ', setObjectName='s001', setMinMax_='0.00-100 step.01', setValue=2.00, setHeight_=20, setToolTip='Offset amount.')

		tb007 = self.sb.polygons.tb007
		tb007.ctxMenu.add('QCheckBox', setText='U', setObjectName='chk008', setChecked=True, setHeight_=20, setToolTip='Divide facet: U coordinate.')
		tb007.ctxMenu.add('QCheckBox', setText='V', setObjectName='chk009', setChecked=True, setHeight_=20, setToolTip='Divide facet: V coordinate.')
		tb007.ctxMenu.add('QCheckBox', setText='Tris', setObjectName='chk010', setHeight_=20, setToolTip='Divide facet: Tris.')

		tb008 = self.sb.polygons.tb008
		tb008.ctxMenu.add('QRadioButton', setText='Union', setObjectName='chk011', setHeight_=20, setToolTip='Fuse two objects together.')
		tb008.ctxMenu.add('QRadioButton', setText='Difference', setObjectName='chk012', setChecked=True, setHeight_=20, setToolTip='Indents one object with the shape of another at the point of their intersection.')
		tb008.ctxMenu.add('QRadioButton', setText='Intersection', setObjectName='chk013', setHeight_=20, setToolTip='Keep only the interaction point of two objects.')

		tb009 = self.sb.polygons.tb009
		tb009.ctxMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s005', setMinMax_='.000-100 step.05', setValue=10, setToolTip='Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.')
		tb009.ctxMenu.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk016', setChecked=True, setToolTip='Freeze Transformations on the object that is being snapped to.')


	def draggableHeader(self, state=None):
		'''Context menu
		'''
		dh = self.sb.polygons.draggableHeader


	def chk008(self, state=None):
		'''Divide Facet: Split U
		'''
		self.sb.toggleWidgets(setUnChecked='chk010')


	def chk009(self, state=None):
		'''Divide Facet: Split V
		'''
		self.sb.toggleWidgets(setUnChecked='chk010')


	def chk010(self, state=None):
		'''Divide Facet: Tris
		'''
		self.sb.toggleWidgets(setUnChecked='chk008,chk009')


	def setMergeVertexDistance(self, p1, p2):
		'''Merge Vertices: Set Distance
		'''
		from pythontk import getDistBetweenTwoPoints
		s = self.sb.polygons.tb000.ctxMenu.s002
		dist = getDistBetweenTwoPoints(p1, p2)
		s.setValue(dist)