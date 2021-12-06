# !/usr/bin/python
# coding=utf-8
import os.path

from maya_init import *



class Polygons(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.polygons_ui.draggable_header

		if state=='setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


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
		self.toggleWidgets(setUnChecked='chk008-9')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.polygons_ui.draggable_header.contextMenu.cmb000

		if index=='setMenu':
			list_ = ['Extrude','Bevel','Bridge','Combine','Merge Vertex','Offset Edgeloop','Edit Edgeflow','Extract Curve','Poke','Wedge','Assign Invisible']
			cmb.addItems_(list_, 'Maya Polygon Operations')
			return

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
		tb = self.current_ui.tb000
		if state=='setMenu':
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Distance: ', setObjectName='s002', setMinMax_='0.000-10 step.005', setValue=0.001, setHeight_=20, setToolTip='Merge Distance.')
			return

		tolerance = float(tb.contextMenu.s002.value())
		objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
		componentMode = pm.selectMode(query=1, component=1)

		if not objects:
			return 'Warning: <hl>Nothing selected</hl>.<br>Operation requires an object or vertex selection.'

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


	@Init.attr
	def tb001(self, state=None):
		'''Bridge
		'''
		tb = self.current_ui.tb001
		if state=='setMenu':
			tb.contextMenu.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s003', setMinMax_='0-10000 step1', setValue=0, setHeight_=20, setToolTip='Subdivision Amount.')
			return

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
		tb = self.current_ui.tb002
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Merge', setObjectName='chk000', setChecked=True, setHeight_=20, setToolTip='Combine selected meshes and merge any coincident verts/edges.')
			return

		# pm.polyUnite( 'plg1', 'plg2', 'plg3', name='result' ) #for future reference. if more functionality is needed use polyUnite
		if tb.contextMenu.chk000.isChecked():
			sel = pm.ls(sl=1, objectsOnly=1)
			if not sel:
				return '# Error: Nothing selected. #'
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


	@Init.attr
	def tb003(self, state=None):
		'''Extrude
		'''
		tb = self.current_ui.tb003
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Keep Faces Together', setObjectName='chk002', setChecked=True, setHeight_=20, setToolTip='Keep edges/faces together.')
			tb.contextMenu.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s004', setMinMax_='1-10000 step1', setValue=1, setHeight_=20, setToolTip='Subdivision Amount.')
			return

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


	@Init.attr
	def tb004(self, state=None):
		'''Bevel (Chamfer)
		'''
		tb = self.current_ui.tb004
		if state=='setMenu':
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', setMinMax_='0.00-100 step.05', setValue=0.25, setHeight_=20, setToolTip='Bevel Width.')
			return

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
		tb = self.current_ui.tb005
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Duplicate', setObjectName='chk014', setChecked=True, setToolTip='Duplicate any selected faces, leaving the originals.')
			tb.contextMenu.add('QCheckBox', setText='Separate', setObjectName='chk015', setChecked=True, setToolTip='Separate mesh objects after detaching faces.')
			# tb.contextMenu.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')
			return

		duplicate = tb.contextMenu.chk014.isChecked()
		separate = tb.contextMenu.chk015.isChecked()

		vertexMask = pm.selectType (query=True, vertex=True)
		edgeMask = pm.selectType (query=True, edge=True)
		facetMask = pm.selectType (query=True, facet=True)

		component_sel = pm.ls(sl=1)
		if not component_sel:
			return 'Error: Nothing selected.'

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


	@Init.attr
	def tb006(self, state=None):
		'''Inset Face Region
		'''
		tb = self.current_ui.tb006
		if state=='setMenu':
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Offset: ', setObjectName='s001', setMinMax_='0.00-100 step.01', setValue=2.00, setHeight_=20, setToolTip='Offset amount.')
			return

		offset = float(tb.contextMenu.s001.value())
		return pm.polyExtrudeFacet (keepFacesTogether=1, pvx=0, pvy=40.55638003, pvz=33.53797107, divisions=1, twist=0, taper=1, offset=offset, thickness=0, smoothingAngle=30)


	@Slots.message
	def tb007(self, state=None):
		'''Divide Facet
		'''
		tb = self.current_ui.tb007
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='U', setObjectName='chk008', setChecked=True, setHeight_=20, setToolTip='Divide facet: U coordinate.')
			tb.contextMenu.add('QCheckBox', setText='V', setObjectName='chk009', setChecked=True, setHeight_=20, setToolTip='Divide facet: V coordinate.')
			tb.contextMenu.add('QCheckBox', setText='Tris', setObjectName='chk010', setHeight_=20, setToolTip='Divide facet: Tris.')
			return

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
			return 'Warning: No faces selected.'


	def tb008(self, state=None):
		'''Boolean Operation
		'''
		tb = self.polygons_ui.tb008
		if state=='setMenu':
			tb.contextMenu.add('QRadioButton', setText='Union', setObjectName='chk011', setHeight_=20, setToolTip='Fuse two objects together.')
			tb.contextMenu.add('QRadioButton', setText='Difference', setObjectName='chk012', setChecked=True, setHeight_=20, setToolTip='Indents one object with the shape of another at the point of their intersection.')
			tb.contextMenu.add('QRadioButton', setText='Intersection', setObjectName='chk013', setHeight_=20, setToolTip='Keep only the interaction point of two objects.')
			return

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
		if state=='setMenu':
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s005', setMinMax_='.000-100 step.05', setValue=10, setToolTip='Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.')
			tb.contextMenu.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk016', setChecked=True, setToolTip='Freeze Transformations on the object that is being snapped to.')
			return

		tolerance = tb.contextMenu.s005.value()
		freezetransforms = tb.contextMenu.chk016.isChecked()

		selection = pm.ls(sl=1, objectsOnly=1)
		if len(selection)>1:
			obj1, obj2 = selection
			Init.snapClosestVerts(obj1, obj2, tolerance, freezetransforms)
		else:
			return 'Error: Operation requires at least two selected objects.'


	@Init.attr
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


	@Init.attr
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


	@Init.attr
	def b010(self):
		'''Extract Curve
		'''
		objects = pm.ls(sl=1, objectsOnly=1)
		sel_edges = Init.getComponents(objects, 'edges', selection=1, flatten=1)
		edge_rings = Init.getContigiousEdges(sel_edges)
		multi = len(edge_rings)>1

		for edge_ring in edge_rings:
			pm.select(edge_ring)
			if multi:
				pm.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=True) #degree: 1=linear,2= ,3=cubic,5= ,7=
			else:
				return pm.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=True) #degree: 1=linear,2= ,3=cubic,5= ,7=


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
		pm.mel.PolyEditEdgeFlow()












#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated:

# @Slots.message
# 	def tb005(self, state=None):
# 		'''
# 		Detach
# 		'''
# 		tb = self.current_ui.tb005
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
# 					return 'Warning: Nothing selected.'

# 				# if len(selObj) > 1:
# 				# 	return 'Warning: Only components from a single object can be extracted.'

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