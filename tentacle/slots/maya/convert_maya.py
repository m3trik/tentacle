# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.convert import Convert



class Convert_maya(Convert, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.convert.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		cmb = self.sb.convert.cmb001
		items = ['NURBS to Polygons', 'NURBS to Subdiv', 'Polygons to Subdiv', 'Smooth Mesh Preview to Polygons', 'Polygon Edges to Curve', 'Type to Curves', 'Subdiv to Polygons', 'Subdiv to NURBS', 'NURBS Curve to Bezier', 'Bezier Curve to NURBS', 'Paint Effects to NURBS', 'Paint Effects to Curves', 'Texture to Geometry', 'Displacement to Polygons', 'Displacement to Polygons with History', 'Fluid to Polygons', 'nParticle to Polygons', 'Instance to Object', 'Geometry to Bounding Box', 'Convert XGen Primitives to Polygons'] 
		contents = cmb.addItems_(items, 'Convert To')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.convert.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Convert To
		'''
		cmb = self.sb.convert.cmb001

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









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------