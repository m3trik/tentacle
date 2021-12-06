# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Convert(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.convert_ui.draggable_header

		if state=='setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.convert_ui.draggable_header.contextMenu.cmb000

		if index=='setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Convert To
		'''
		cmb = self.convert_ui.cmb001

		if index=='setMenu':
			list_ = ['NURBS to Polygons', 'NURBS to Subdiv', 'Polygons to Subdiv', 'Smooth Mesh Preview to Polygons', 'Polygon Edges to Curve', 'Type to Curves', 'Subdiv to Polygons', 'Subdiv to NURBS', 'NURBS Curve to Bezier', 'Bezier Curve to NURBS', 'Paint Effects to NURBS', 'Paint Effects to Curves', 'Texture to Geometry', 'Displacement to Polygons', 'Displacement to Polygons with History', 'Fluid to Polygons', 'nParticle to Polygons', 'Instance to Object', 'Geometry to Bounding Box', 'Convert XGen Primitives to Polygons'] 
			cmb.addItems_(list_, 'Convert To')
			return

		if index>0:
			text = cmb.items[index]
			if text=='NURBS to Polygons': #index 1
				mel.eval('performnurbsToPoly 0;')
			elif text=='NURBS to Subdiv': #index 2
				mel.eval('performSubdivCreate 0;')
			elif text=='Polygons to Subdiv': #index 3
				mel.eval('performSubdivCreate 0;')
			elif text=='Smooth Mesh Preview to Polygons': #index 4
				mel.eval('performSmoothMeshPreviewToPolygon;')
			elif text=='Polygon Edges to Curve': #index 5
				mel.eval('polyToCurve -form 2 -degree 3 -conformToSmoothMeshPreview 1;')
			elif text=='Type to Curves': #index 6
				mel.eval('convertTypeCapsToCurves;')
			elif text=='Subdiv to Polygons': #index 7
				mel.eval('performSubdivTessellate  false;')
			elif text=='Subdiv to NURBS': #index 8
				mel.eval('performSubdToNurbs 0;')
			elif text=='NURBS Curve to Bezier': #index 9
				mel.eval('nurbsCurveToBezier;')
			elif text=='Bezier Curve to NURBS': #index 10
				mel.eval('bezierCurveToNurbs;')
			elif text=='Paint Effects to NURBS': #index 11
				mel.eval('performPaintEffectsToNurbs  false;')
			elif text=='Paint Effects to Curves': #index 12
				mel.eval('performPaintEffectsToCurve  false;')
			elif text=='Texture to Geometry': #index 13
				mel.eval('performTextureToGeom 0;')
			elif text=='Displacement to Polygons': #index 14
				mel.eval('displacementToPoly;')
			elif text=='Displacement to Polygons with History': #index 15
				mel.eval('setupAnimatedDisplacement;')
			elif text=='Fluid to Polygons': #index 16
				mel.eval('fluidToPoly;')
			elif text=='nParticle to Polygons': #index 17
				mel.eval('particleToPoly;')
			elif text=='Instance to Object': #index 18
				mel.eval('convertInstanceToObject;')
			elif text=='Geometry to Bounding Box': #index 19
				mel.eval('performGeomToBBox 0;')
			elif text=='Convert XGen Primitives to Polygons': #index 20
				import xgenm.xmaya.xgmConvertPrimToPolygon as cpp
				cpp.convertPrimToPolygon(False)

			cmb.setCurrentIndex(0)


	def b000(self):
		'''Polygon Edges to Curve
		'''
		self.cmb001(index=5)


	def b001(self):
		'''Instance to Object
		'''
		self.cmb001(index=18)


	def b002(self):
		'''NURBS to Polygons
		'''
		self.cmb001(index=1)


	def b003(self):
		'''Smooth Mesh Preview to Polygons
		'''
		self.cmb001(index=4)


	def b004(self):
		''''''
		pass


	def b005(self):
		''''''
		pass


	def b006(self):
		''''''
		pass


	def b007(self):
		''''''
		pass


	def b008(self):
		''''''
		pass


	def b009(self):
		''''''
		pass







#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------