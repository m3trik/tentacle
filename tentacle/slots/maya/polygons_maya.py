# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.polygons import Polygons



class Polygons_maya(Polygons, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Polygons.__init__(self, *args, **kwargs)

		cmb000 = self.polygons_ui.draggable_header.contextMenu.cmb000
		items = ['Extrude','Bevel','Bridge','Combine','Merge Vertex','Offset Edgeloop','Edit Edgeflow','Extract Curve','Poke','Wedge','Assign Invisible']
		cmb000.addItems_(items, 'Polygon Editors')


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.polygons_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Extrude':
				pm.mel.PolyExtrudeOptions()
			elif text=='Bevel':
				pm.mel.BevelPolygonOptions()
			elif text=='Bridge':
				pm.mel.BridgeEdgeOptions()
			elif text=='Combine':
				pm.mel.CombinePolygonsOptions()
			elif text=='Merge Vertex':
				pm.mel.PolyMergeOptions()
			elif text=='Offset Edgeloop':
				pm.mel.DuplicateEdgesOptions()
			elif text=='Edit Edgeflow':
				pm.mel.PolyEditEdgeFlowOptions()
			elif text=='Extract Curve':
				pm.mel.CreateCurveFromPolyOptions()
			elif text=='Poke':
				pm.mel.PokePolygonOptions()
			elif text=='Wedge':
				pm.mel.WedgePolygonOptions()
			elif text=='Assign Invisible':
				pm.mel.PolyAssignSubdivHoleOptions()
			cmb.setCurrentIndex(0)


	@Slots.message
	def tb000(self, state=None):
		'''Merge Vertices
		'''
		tb = self.polygons_ui.tb000

		tolerance = float(tb.contextMenu.s002.value())
		objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
		componentMode = pm.selectMode(query=1, component=1)

		if not objects:
			return 'Error: <strong>Nothing selected</strong>.<br>Operation requires an object or vertex selection.'

		for obj in objects:
			object_vert_sel = pm.ls(obj, sl=1)
			if componentMode: #merge selected components.
				if pm.filterExpand(selectionMask=31): #selectionMask=vertices
					pm.polyMergeVertex(object_vert_sel, distance=tolerance, alwaysMergeTwoVertices=True, constructionHistory=True)
				else: #if selection type =edges or facets:
					pm.mel.MergeToCenter()

			else: #if object mode. merge all vertices on the selected object.
				for n, vert in enumerate(object_vert_sel):
					if not self.polygons_ui.progressBar.step(n, len(object_vert_sel)): #register progress while checking for cancellation:
						break

					# get number of vertices
					count = pm.polyEvaluate(obj, vertex=1)
					vertices = str(obj) + ".vtx [0:" + str(count) + "]" # mel expression: select -r geometry.vtx[0:1135];
					pm.polyMergeVertex(vertices, distance=tolerance, alwaysMergeTwoVertices=False, constructionHistory=False)

				#return to original state
				pm.select(clear=1)
				pm.select(objects)


	@Slots_maya.attr
	def tb001(self, state=None):
		'''Bridge
		'''
		tb = self.polygons_ui.tb001

		divisions = tb.contextMenu.s003.value()

		selection = pm.ls(sl=1)
		edges = pm.filterExpand(selection, selectionMask=32, expand=1) #get edges from selection

		node = pm.polyBridgeEdge(edges, divisions=divisions) #bridge edges
		pm.polyCloseBorder(edges) #fill edges if they lie on a border
		return node


	@Slots.message
	def tb002(self, state=None):
		'''Combine
		'''
		tb = self.polygons_ui.tb002

		# pm.polyUnite( 'plg1', 'plg2', 'plg3', name='result' ) #for future reference. if more functionality is needed use polyUnite
		if tb.contextMenu.chk000.isChecked():
			sel = pm.ls(sl=1, objectsOnly=1)
			if not sel:
				return 'Error: <strong>Nothing selected</strong>.'
			objName = sel[0].name()
			objParent = pm.listRelatives(objName, parent=1)
			#combine
			newObj = pm.polyUnite(ch=1, mergeUVSets=1, centerPivot=1)
			#rename using the first selected object
			pm.bakePartialHistory(objName, all=True)
			objName_ = pm.rename(newObj[0], objName)
			#reparent
			pm.parent(objName_, objParent)
		else:
			pm.mel.CombinePolygons()


	@Slots_maya.attr
	def tb003(self, state=None):
		'''Extrude
		'''
		tb = self.polygons_ui.tb003

		keepFacesTogether = tb.contextMenu.chk002.isChecked() #keep faces/edges together.
		divisions = tb.contextMenu.s004.value()

		selection = pm.ls(sl=1)
		if pm.selectType(query=1, facet=1): #face selection
			pm.polyExtrudeFacet(edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions)
			mel.eval('PolyExtrude;')
			# return pm.polyExtrudeFacet(selection, ch=1, keepFacesTogether=keepFacesTogether, divisions=divisions)

		elif pm.selectType(query=1, edge=1): #edge selection
			pm.polyExtrudeEdge(edit=1, keepFacesTogether=keepFacesTogether, divisions=divisions)
			mel.eval('PolyExtrude;')
			# return pm.polyExtrudeEdge(selection, ch=1, keepFacesTogether=keepFacesTogether, divisions=divisions)

		elif pm.selectType(query=1, vertex=1): #vertex selection
			pm.polyExtrudeVertex(edit=1, width=0.5, length=1, divisions=divisions)
			mel.eval('PolyExtrude;')
			# return polyExtrudeVertex(selection, ch=1, width=0.5, length=1, divisions=divisions)


	@Slots_maya.attr
	def tb004(self, state=None):
		'''Bevel (Chamfer)
		'''
		tb = self.polygons_ui.tb004

		width = float(tb.contextMenu.s000.value())
		chamfer = True
		segments = 1

		return pm.polyBevel3(fraction=width, offsetAsFraction=1, autoFit=1, depth=1, mitering=0, 
			miterAlong=0, chamfer=chamfer, segments=segments, worldSpace=1, smoothingAngle=30, subdivideNgons=1,
			mergeVertices=1, mergeVertexTolerance=0.0001, miteringAngle=180, angleTolerance=180, ch=0)


	@Slots.message
	def tb005(self, state=None):
		'''Detach
		'''
		tb = self.polygons_ui.tb005

		duplicate = tb.contextMenu.chk014.isChecked()
		separate = tb.contextMenu.chk015.isChecked()

		vertexMask = pm.selectType (query=True, vertex=True)
		edgeMask = pm.selectType (query=True, edge=True)
		facetMask = pm.selectType (query=True, facet=True)

		component_sel = pm.ls(sl=1)
		if not component_sel:
			return 'Error: <strong>Nothing selected</strong>.'

		if vertexMask:
			pm.mel.polySplitVertex()

		elif facetMask:
			extract = pm.polyChipOff(component_sel, ch=1, keepFacesTogether=1, dup=duplicate, off=0)
			if separate:
				try:
					splitObjects = pm.polySeparate(component_sel)
				except:
					splitObjects = pm.polySeparate(pm.ls(component_sel, objectsOnly=1))
			pm.select(splitObjects[-1])
			return extract

		else:
			pm.mel.DetachComponent()


	@Slots_maya.attr
	@Slots.message
	def tb006(self, state=None):
		'''Inset Face Region
		'''
		tb = self.polygons_ui.tb006

		selected_faces = pm.polyEvaluate(faceComponent=1)
		if isinstance(selected_faces, str): #'Nothing counted : no polygonal object is selected.'
			return 'Error: <strong>Nothing selected</strong>.<br>Operation requires a face selection.'

		offset = float(tb.contextMenu.s001.value())
		return pm.polyExtrudeFacet(selected_faces, keepFacesTogether=1, pvx=0, pvy=40.55638003, pvz=33.53797107, divisions=1, twist=0, taper=1, offset=offset, thickness=0, smoothingAngle=30)


	@Slots.message
	def tb007(self, state=None):
		'''Divide Facet
		'''
		tb = self.polygons_ui.tb007

		dv=u=v=0
		if tb.contextMenu.chk008.isChecked(): #Split U
			u=2
		if tb.contextMenu.chk009.isChecked(): #Split V
			v=2

		mode = 0 #The subdivision mode. 0=quads, 1=triangles
		subdMethod = 1 #subdivision type: 0=exponential(traditional subdivision) 1=linear(number of faces per edge grows linearly)
		if tb.contextMenu.chk010.isChecked(): #tris
			mode=dv=1
			subdMethod=0
		if all([tb.contextMenu.chk008.isChecked(), tb.contextMenu.chk009.isChecked()]): #subdivide once into quads
			dv=1
			subdMethod=0
			u=v=0
		#perform operation
		selectedFaces = pm.filterExpand (pm.ls(sl=1), selectionMask=34, expand=1)
		if selectedFaces:
			for face in selectedFaces: #when performing polySubdivideFacet on multiple faces, adjacent subdivided faces will make the next face an n-gon and therefore not able to be subdivided. 
				pm.polySubdivideFacet(face, divisions=0, divisionsU=2, divisionsV=2, mode=0, subdMethod=1)
		else:
			return 'Error: <strong>Nothing selected</strong>.<br>Operation requires a face selection.'


	def tb008(self, state=None):
		'''Boolean Operation
		'''
		tb = self.polygons_ui.tb008

		if tb.contextMenu.chk011.isChecked(): #union
			pm.mel.PolygonBooleanIntersection()

		if tb.contextMenu.chk012.isChecked(): #difference
			pm.mel.PolygonBooleanDifference()

		if tb.contextMenu.chk013.isChecked(): #intersection
			pm.mel.PolygonBooleanIntersection()


	@Slots.message
	def tb009(self, state=None):
		'''Snap Closest Verts
		'''
		tb = self.polygons_ui.tb009

		tolerance = tb.contextMenu.s005.value()
		freezetransforms = tb.contextMenu.chk016.isChecked()

		selection = pm.ls(sl=1, objectsOnly=1)
		if len(selection)>1:
			obj1, obj2 = selection
			self.snapClosestVerts(obj1, obj2, tolerance, freezetransforms)
		else:
			return 'Error: <strong>Nothing selected</strong>.<br>Operation requires at least two selected objects.'


	@Slots_maya.attr
	def b000(self):
		'''Circularize
		'''
		circularize = pm.polyCircularize(
			constructionHistory=1, 
			alignment=0, 
			radialOffset=0, 
			normalOffset=0, 
			normalOrientation=0, 
			smoothingAngle=30, 
			evenlyDistribute=1, 
			divisions=0, 
			supportingEdges=0, 
			twist=0, 
			relaxInterior=1
		)
		return circularize


	def b001(self):
		'''Fill Holes
		'''
		pm.mel.FillHole()


	def b002(self):
		'''Separate
		'''
		pm.mel.SeparatePolygon()


	def b003(self):
		'''Symmetrize
		'''
		pm.mel.Symmetrize()


	@Slots_maya.attr
	def b004(self):
		'''Slice
		'''
		cuttingDirection = 'Y' #valid values: 'x','y','z' A value of 'x' will cut the object along the YZ plane cutting through the center of the bounding box. 'y':ZX. 'z':XY.

		component_sel = pm.ls(sl=1)
		return pm.polyCut(component_sel, cuttingDirection=cuttingDirection, ch=1)


	def b009(self):
		'''Collapse Component
		'''
		if pm.selectType(query=1, vertex=1):
			pm.mel.MergeToCenter() #merge vertices
		else:
			pm.mel.PolygonCollapse()


	def b012(self):
		'''Multi-Cut Tool
		'''
		pm.mel.dR_multiCutTool()


	def b021(self):
		'''Connect Border Edges
		'''
		pm.mel.performPolyConnectBorders(0)


	def b022(self):
		'''Attach
		'''
		# pm.mel.AttachComponent()
		pm.mel.dR_connectTool()


	def b028(self):
		'''Quad Draw
		'''
		pm.mel.dR_quadDrawTool()


	def b032(self):
		'''Poke
		'''
		pm.mel.PokePolygon()


	def b034(self):
		'''Wedge
		'''
		pm.mel.WedgePolygon()


	def b038(self):
		'''Assign Invisible
		'''
		pm.polyHole(assignHole=1)


	def b043(self):
		'''Target Weld
		'''
		pm.select(deselect=True)
		pm.mel.dR_targetWeldTool()


	def b045(self):
		'''Re-Order Vertices
		'''
		symmetryOn = pm.symmetricModelling(query=True, symmetry=True) #query symmetry state
		if symmetryOn:
			pm.symmetricModelling(symmetry=False)
		pm.mel.setPolygonDisplaySettings("vertIDs") #set vertex id on
		pm.mel.doBakeNonDefHistory(1, "pre") #history must be deleted
		pm.mel.performPolyReorderVertex() #start vertex reorder ctx


	def b046(self):
		'''Split
		'''
		vertexMask = pm.selectType (query=True, vertex=True)
		edgeMask = pm.selectType (query=True, edge=True)
		facetMask = pm.selectType (query=True, facet=True)

		if facetMask:
			pm.mel.performPolyPoke(1)

		elif edgeMask:
			pm.polySubdivideEdge(ws=0, s=0, dv=1, ch=0)

		elif vertexMask:
			pm.mel.polyChamferVtx(0, 0.25, 0)


	def b047(self):
		'''Insert Edgeloop
		'''
		pm.mel.SplitEdgeRingTool()


	def b048(self):
		'''Collapse Edgering
		'''
		pm.mel.bt_polyCollapseEdgeRingTool()


	def b049(self):
		'''Slide Edge Tool
		'''
		pm.mel.SlideEdgeTool()


	def b050(self):
		'''Spin Edge
		'''
		pm.mel.bt_polySpinEdgeTool()


	def b051(self):
		'''Offset Edgeloop
		'''
		pm.mel.performPolyDuplicateEdge(0)


	def b053(self):
		'''Edit Edge Flow
		'''
		pm.polyEditEdgeFlow(adjustEdgeFlow=1)


	@Slots_maya.undoChunk
	def snapClosestVerts(self, obj1, obj2, tolerance=10.0, freezeTransforms=False):
		'''Snap the vertices from object one to the closest verts on object two.

		:Parameters:
			obj1 (obj) = The object in which the vertices are moved from.
			obj2 (obj) = The object in which the vertices are moved to.
			tolerance (float) = Maximum search distance.
			freezeTransforms (bool) = Reset the selected transform and all of its children down to the shape level.
		'''
		vertices = Slots_maya.getComponents(obj1, 'vertices')
		closestVerts = Slots_maya.getClosestVertex(vertices, obj2, tolerance=tolerance, freezeTransforms=freezeTransforms)

		progressBar = mel.eval("$container=$gMainProgressBar");
		pm.progressBar(progressBar, edit=True, beginProgress=True, isInterruptable=True, status="Snapping Vertices ...", maxValue=len(closestVerts)) 

		# pm.undoInfo(openChunk=True)
		for v1, v2 in closestVerts.items():
			if pm.progressBar(progressBar, query=True, isCancelled=True):
				break

			v2Pos = pm.pointPosition(v2, world=True)
			pm.xform(v1, translation=v2Pos, worldSpace=True)

			pm.progressBar(progressBar, edit=True, step=1)
		# pm.undoInfo(closeChunk=True)

		pm.progressBar(progressBar, edit=True, endProgress=True)













#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated:

# @Slots.message
# 	def tb005(self, state=None):
# 		'''
# 		Detach
# 		'''
# 		tb = self.polygons_ui.tb005
# 		if state=='setMenu':
# 			# tb.contextMenu.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')
# 			return

# 		vertexMask = pm.selectType (query=True, vertex=True)
# 		edgeMask = pm.selectType (query=True, edge=True)
# 		facetMask = pm.selectType (query=True, facet=True)

# 		if vertexMask:
# 			mel.eval("polySplitVertex()")

# 		if facetMask:
# 			maskVertex = pm.selectType (query=True, vertex=True)
# 			if maskVertex:
# 				mel.eval("DetachComponent;")
# 			else:
# 				selFace = pm.ls(ni=1, sl=1)
# 				selObj = pm.ls(objectsOnly=1, noIntermediate=1, sl=1) #to errorcheck if more than 1 obj selected

# 				if len(selFace) < 1:
# 					return 'Error: Nothing selected.'

# 				# if len(selObj) > 1:
# 				# 	return 'Error: Only components from a single object can be extracted.'

# 				else:
# 					mel.eval("DetachComponent;")
# 					# pm.undoInfo (openChunk=1)
# 					# sel = str(selFace[0]).split(".") #creates ex. ['polyShape', 'f[553]']
# 					# print(sel)
# 					# extractedObject = "extracted_"+sel[0]
# 					# pm.duplicate (sel[0], name=extractedObject)
# 					# if tb.contextMenu.chk007.isChecked(): #delete original
# 					# 	pm.delete (selFace)

# 					# allFace = [] #populate a list of all faces in the duplicated object
# 					# numFaces = pm.polyEvaluate(extractedObject, face=1)
# 					# num=0
# 					# for _ in range(numFaces):
# 					# 	allFace.append(extractedObject+".f["+str(num)+"]")
# 					# 	num+=1

# 					# extFace = [] #faces to keep
# 					# for face in selFace:
# 					# 	fNum = str(face.split(".")[0]) #ex. f[4]
# 					# 	extFace.append(extractedObject+"."+fNum)

# 					# delFace = [x for x in allFace if x not in extFace] #all faces not in extFace
# 					# pm.delete (delFace)

# 					# pm.select (extractedObject)
# 					# pm.xform (cpc=1) #center pivot
# 					# pm.undoInfo (closeChunk=1)
# 					# return extractedObject