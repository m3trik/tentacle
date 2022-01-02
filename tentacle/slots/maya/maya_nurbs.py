# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class Nurbs(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		ctx = self.nurbs_ui.draggable_header.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Curve Operations')
		
		cmb = self.nurbs_ui.draggable_header.contextMenu.cmb000
		items = ['Project Curve','Duplicate Curve','Create Curve from Poly','Bend Curve', 'Curl Curve','Modify Curve Curvature','Smooth Curve','Straighten Curves','Extrude Curves','Revolve Curves','Loft Curves','Planar Curves','Insert Isoparms','Insert Knot','Rebuild Curve','Extend Curve', 'Extend Curve On Surface']
		cmb.addItems_(items, 'Maya Curve Operations')
		
		cmb = self.nurbs_ui.cmb001
		items = ['Ep Curve Tool','CV Curve Tool','Bezier Curve Tool','Pencil Curve Tool','2 Point Circular Arc','3 Point Circular Arc']
		cmb.addItems_(items, 'Create Curve')
			
		ctx = self.nurbs_ui.tb000.contextMenu
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


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.nurbs_ui.draggable_header


	def cmb000(self, index=-1):
		'''Maya Curve Operations
		'''
		cmb = self.nurbs_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Project Curve':
				mel.eval("ProjectCurveOnSurfaceOptions;")
			elif text=='Duplicate Curve':
				mel.eval("DuplicateCurveOptions;")
			elif text=='Create Curve from Poly':
				mel.eval("CreateCurveFromPolyOptions")
			elif text=='Bend Curve':
				mel.eval("BendCurvesOptions;")
			elif text=='Curl Curve':
				mel.eval("CurlCurvesOptions;")
			elif text=='Modify Curve Curvature':
				mel.eval("ScaleCurvatureOptions;")
			elif text=='Smooth Curve':
				mel.eval("SmoothHairCurvesOptions;")
			elif text=='Straighten Curves':
				mel.eval("StraightenCurvesOptions;")
			elif text=='Extrude Curves':
				mel.eval("ExtrudeOptions;")
			elif text=='Revolve Curves':
				mel.eval("RevolveOptions;")
			elif text=='Loft Curves':
				mel.eval("LoftOptions;")
			elif text=='Planar Curves':
				mel.eval("PlanarOptions;")
			elif text=='Insert Isoparms':
				mel.eval("InsertIsoparmsOptions;")
			elif text=='Insert Knot':
				mel.eval("InsertKnotOptions;")
			elif text=='Rebuild Curve':
				mel.eval("RebuildCurveOptions;")
			elif text=='Extend Curve':
				mel.eval("ExtendCurveOptions;")
			elif text=='Extend Curve On Surface':
				mel.eval("ExtendCurveOnSurfaceOptions;")
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Create: Curve
		'''
		cmb = self.nurbs_ui.cmb001

		if index>0:
			text = cmb.items[index]
			if text=='Ep Curve Tool':
				mel.eval('EPCurveToolOptions;') #mel.eval('EPCurveTool;')
			elif text=='CV Curve Tool':
				mel.eval('CVCurveToolOptions') #mel.eval('CVCurveTool')
			elif text=='Bezier Curve Tool':
				mel.eval('CreateBezierCurveToolOptions') #mel.eval('CreateBezierCurveTool;')
			elif text=='Pencil Curve Tool':
				mel.eval('PencilCurveToolOptions;') #mel.eval('PencilCurveTool;')
			elif text=='2 Point Circular Arc':
				mel.eval('TwoPointArcToolOptions;') #mel.eval("TwoPointArcTool;")
			elif text=='3 Point Circular Arc':
				mel.eval("ThreePointArcToolOptions;") #mel.eval("ThreePointArcTool;")
			cmb.setCurrentIndex(0)


	@Slots_maya.attr
	def tb000(self, state=None):
		'''Revolve
		'''
		tb = self.nurbs_ui.tb000

		degree = tb.contextMenu.s002.value()
		startSweep = tb.contextMenu.s003.value()
		endSweep = tb.contextMenu.s004.value()
		sections = tb.contextMenu.s005.value()
		range_ = tb.contextMenu.chk006.isChecked()
		polygon = 1 if tb.contextMenu.chk007.isChecked() else 0
		autoCorrectNormal = tb.contextMenu.chk008.isChecked()
		useTolerance = tb.contextMenu.chk009.isChecked()
		tolerance = tb.contextMenu.s006.value()

		return pm.revolve(curves, po=polygon, rn=range_, ssw=startSweep, esw=endSweep, ut=useTolerance, tol=tolerance, degree=degree, s=sections, ulp=1, ax=[0,1,0])


	# @Slots_maya.attr
	def tb001(self, state=None):
		'''Loft
		'''
		tb = self.nurbs_ui.tb001

		uniform = tb.contextMenu.chk000.isChecked()
		close = tb.contextMenu.chk001.isChecked()
		degree = tb.contextMenu.s000.value()
		autoReverse = tb.contextMenu.chk002.isChecked()
		sectionSpans = tb.contextMenu.s001.value()
		range_ = tb.contextMenu.chk003.isChecked()
		polygon = 1 if tb.contextMenu.chk004.isChecked() else 0
		reverseSurfaceNormals = tb.contextMenu.chk005.isChecked()
		angleLoftBetweenTwoCurves = tb.contextMenu.chk010.isChecked()
		angleLoftSpans = tb.contextMenu.s007.value()

		Nurbs.loft(uniform=uniform, close=close, degree=degree, autoReverse=autoReverse, sectionSpans=sectionSpans, range_=range_, polygon=polygon, reverseSurfaceNormals=reverseSurfaceNormals, angleLoftBetweenTwoCurves=angleLoftBetweenTwoCurves, angleLoftSpans=angleLoftSpans)


	def b012(self):
		'''Project Curve
		'''
		mel.eval("projectCurve;") #ProjectCurveOnMesh;


	def b014(self):
		'''Duplicate Curve
		'''
		pm.mel.DuplicateCurve()


	def b016(self):
		'''Extract Curve
		'''
		try:
			pm.mel.CreateCurveFromPoly()

		except Exception as error:
			objects = pm.ls(sl=1, objectsOnly=1)
			sel_edges = Slots_maya.getComponents(objects, 'edges', selection=1, flatten=1)
			edge_rings = Slots_maya.getContigiousEdges(sel_edges)
			multi = len(edge_rings)>1

			for edge_ring in edge_rings:
				pm.select(edge_ring)
				if multi:
					pm.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=True) #degree: 1=linear,2= ,3=cubic,5= ,7=
				else:
					return pm.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=True) #degree: 1=linear,2= ,3=cubic,5= ,7=


	def b018(self):
		'''Lock Curve
		'''
		pm.mel.LockCurveLength()


	def b019(self):
		'''Unlock Curve
		'''
		pm.mel.UnlockCurveLength()


	def b020(self):
		'''Bend Curve
		'''
		pm.mel.BendCurves()


	def b022(self):
		'''Curl Curve
		'''
		pm.mel.CurlCurves()


	def b024(self):
		'''Modify Curve Curvature
		'''
		pm.mel.ScaleCurvature()


	def b026(self):
		'''Smooth Curve
		'''
		pm.mel.SmoothHairCurves()


	def b028(self):
		'''Straighten Curve

		'''
		pm.mel.StraightenCurves()


	def b030(self):
		'''Extrude

		'''
		pm.mel.Extrude()


	def b036(self):
		'''Planar
		'''
		pm.mel.Planar()


	def b038(self):
		'''Insert Isoparm
		'''
		pm.mel.InsertIsoparms()


	def b040(self):
		'''Edit Curve Tool
		'''
		pm.mel.CurveEditTool()


	def b041(self):
		'''Attach Curve
		'''
		pm.mel.AttachCurveOptions()


	def b042(self):
		'''Detach Curve
		'''
		pm.mel.DetachCurve()


	def b043(self):
		'''Extend Curve
		'''
		pm.mel.ExtendCurveOptions()


	def b045(self):
		'''Cut Curve
		'''
		pm.mel.CutCurve()


	def b046(self):
		'''Open/Close Curve
		'''
		pm.mel.OpenCloseCurve()


	def b047(self):
		'''Insert Knot
		'''
		pm.mel.InsertKnot()


	def b049(self):
		'''Add Points Tool
		'''
		pm.mel.AddPointsTool()


	def b051(self):
		'''Reverse Curve

		'''
		mel.eval("reverse;")


	def b052(self):
		'''Extend Curve
		'''
		pm.mel.ExtendCurve()


	def b054(self):
		'''Extend On Surface
		'''
		pm.mel.ExtendCurveOnSurface()


	@staticmethod
	@Slots_maya.undoChunk
	def loft(uniform=True, close=False, degree=3, autoReverse=False, sectionSpans=1, range_=False, polygon=True, reverseSurfaceNormals=True, angleLoftBetweenTwoCurves=False, angleLoftSpans=6):
		'''Create a loft between two selections.

		:Parameters:
			uniform (bool) = The resulting surface will have uniform parameterization in the loft direction. If set to false, the parameterization will be chord length.
			close (bool) = The resulting surface will be closed (periodic) with the start (end) at the first curve. If set to false, the surface will remain open.
			degree (int) = The degree of the resulting surface.
			autoReverse (bool) = The direction of the curves for the loft is computed automatically. If set to false, the values of the multi-use reverse flag are used instead.
			sectionSpans (int) = The number of surface spans between consecutive curves in the loft.
			range_ (bool) = Force a curve range on complete input curve.
			polygon (bool) = The object created by this operation.
			reverseSurfaceNormals (bool) = The surface normals on the output NURBS surface will be reversed. This is accomplished by swapping the U and V parametric directions.
			angleLoftBetweenTwoCurves (bool) = Perform a loft at an angle between two selected curves or polygon edges (that will be extracted as curves).
			angleLoftSpans (int) = Angle loft: Number of duplicated points (spans).

		:Return:
			(obj) nurbsToPoly history node.
		'''
		# pm.undoInfo(openChunk=1)

		sel = pm.ls(sl=1)
		if len(sel)>1:
			if angleLoftBetweenTwoCurves:
				start, end = sel[:2] #get the first two selected edge loops or curves.
				result = Slots_maya.angleLoftBetweenTwoCurves(start, end, count=angleLoftSpans, cleanup=True, uniform=uniform, close=close, autoReverse=autoReverse, degree=degree, sectionSpans=sectionSpans, range=range_, polygon=0, reverseSurfaceNormals=reverseSurfaceNormals)
			else:
				result = pm.loft(sel, u=uniform, c=close, ar=autoReverse, d=degree, ss=sectionSpans, rn=range_, po=0, rsn=reverseSurfaceNormals)
		else:
			return '# Error: Operation requires the selection of two curves or polygon edge sets. #'

		if polygon: #convert nurb surface to polygon.
			converted = pm.nurbsToPoly(result[0], mnd=1,  f=3, pt=1, pc=200, chr=0.1, ft=0.01, mel=0.001, d=0.1, ut=1, un=3, vt=1, vn=3, uch=0, ucr=0, cht=0.2, es=0, ntr=0, mrt=0, uss=1)
			for obj in result:
				try:
					pm.delete(obj)
				except:
					pass
			result=converted

		# pm.undoInfo(closeChunk=1)
		return result









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------