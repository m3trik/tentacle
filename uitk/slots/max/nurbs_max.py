# !/usr/bin/python
# coding=utf-8
from uitk.slots.max import *
from uitk.slots.nurbs import Nurbs


class Nurbs_max(Nurbs, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb000 = self.sb.nurbs.draggable_header.ctxMenu.cmb000
		items = []
		cmb000.addItems_(items, 'Curve Editors')

		cmb001 = self.sb.nurbs.cmb001
		items = []
		cmb001.addItems_(items, 'Create Curve')


	def cmb000(self, index=-1):
		'''Maya Curve Operations
		'''
		cmb = self.sb.nurbs.draggable_header.ctxMenu.cmb000

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
		cmb = self.sb.nurbs.cmb001

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


	@Slots_max.attr
	def tb000(self, state=None):
		'''Revolve
		'''
		tb = self.sb.nurbs.tb000

		degree = tb.ctxMenu.s002.value()
		startSweep = tb.ctxMenu.s003.value()
		endSweep = tb.ctxMenu.s004.value()
		sections = tb.ctxMenu.s005.value()
		range_ = tb.ctxMenu.chk006.isChecked()
		polygon = 1 if tb.ctxMenu.chk007.isChecked() else 0
		autoCorrectNormal = tb.ctxMenu.chk008.isChecked()
		useTolerance = tb.ctxMenu.chk009.isChecked()
		tolerance = tb.ctxMenu.s006.value()

		return pm.revolve(curves, po=polygon, rn=range_, ssw=startSweep, esw=endSweep, ut=useTolerance, tol=tolerance, degree=degree, s=sections, ulp=1, ax=[0,1,0])


	@Slots_max.attr
	def tb001(self, state=None):
		'''Loft
		'''
		tb = self.sb.nurbs.tb001

		uniform = tb.ctxMenu.chk000.isChecked()
		close = tb.ctxMenu.chk001.isChecked()
		degree = tb.ctxMenu.s000.value()
		autoReverse = tb.ctxMenu.chk002.isChecked()
		sectionSpans = tb.ctxMenu.s001.value()
		range_ = tb.ctxMenu.chk003.isChecked()
		polygon = 1 if tb.ctxMenu.chk004.isChecked() else 0
		reverseSurfaceNormals = tb.ctxMenu.chk005.isChecked()
		angleLoftBetweenTwoCurves = tb.ctxMenu.chk010.isChecked()
		angleLoftSpans = tb.ctxMenu.s007.value()

		if angleLoftBetweenTwoCurves:
			start, end = pm.ls(sl=1)[:2] #get the first two selected edge loops or curves.
			return Slots_max.angleLoftBetweenTwoCurves(start, end, count=angleLoftSpans, cleanup=True, uniform=uniform, close=close, autoReverse=autoReverse, degree=degree, sectionSpans=sectionSpans, range=range_, polygon=polygon, reverseSurfaceNormals=reverseSurfaceNormals)

		return pm.loft(curves, u=uniform, c=close, ar=autoReverse, d=degree, ss=sectionSpans, rn=range_, po=polygon, rsn=reverseSurfaceNormals)


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
		pm.mel.CreateCurveFromPoly()


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









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------