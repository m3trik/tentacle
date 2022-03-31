# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.polygons import Polygons



class Polygons_max(Polygons, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Polygons.__init__(self, *args, **kwargs)

		cmb = self.polygons_ui.draggable_header.contextMenu.cmb000
		items = ['Bridge','Extrude']
		cmb.addItems_(items, 'Polygon Editors')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.polygons_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Bridge':
				maxEval('''
				if Ribbon - Modeling.ValidSOMode() and (subObjectLevel == 2 or subObjectLevel == 3) then
				(
					curmod = Modpanel.getcurrentObject()
					if subObjectLevel == 2 then
					(   
					    curmod.popupDialog #BridgeEdge
					)
					else 
					(
					    curmod.popupDialog #BridgeBorder
					)
				)
				''')
			if text=='Extrude':
				maxEval('''
				If subObjectLevel == undefined then Max Modify Mode
				-- default to Face level:
				if subObjectLevel == 0 then subObjectLevel = 4
				local A = modPanel.getCurrentObject()
				if (Filters.Is_This_EditPolyMod A) then
				(
					local level = A.GetMeshSelLevel()
					if (level == #Vertex) then (A.PopupDialog #ExtrudeVertex)
					else if (level == #Edge) then (A.PopupDialog #ExtrudeEdge)
					else if (level == #Face) then (A.PopupDialog #ExtrudeFace)
				)
				else (A.popupDialog #Extrude)
				''')
			cmb.setCurrentIndex(0)


	@Slots.message
	def tb000(self, state=None):
		'''Merge Vertices
		'''
		tb = self.polygons_ui.tb000

		tolerance = float(tb.contextMenu.s002.value())
		selection = rt.selection

		if selection:
			for n, obj in enumerate(selection):
				if not self.polygons_ui.progressBar.step(n, len(selection)): #register progress while checking for cancellation:
					break

				vertSelection = rt.getVertSelection(obj)
				if rt.subObjectLevel==1 and vertSelection>1: #merge selected components.
					obj.weldThreshold = tolerance
					rt.polyop.weldVertsByThreshold(obj, vertSelection)

				else: #if object mode. merge all vertices on the selected object.
					rt.polyop.weldVertsByThreshold(obj, obj.verts)
		else:
			return 'Error: No object selected.'


	def tb001(self, state=None):
		'''Bridge
		'''
		tb = self.polygons_ui.tb001

		divisions = tb.contextMenu.s003.value()

		for obj in rt.selection:
			obj.EditablePoly.Bridge() #perform bridge
		rt.redrawViews() #redraw changes in viewport


	def tb002(self, state=None):
		'''Combine
		'''
		tb = self.polygons_ui.tb002

		if tb.contextMenu.chk000.isChecked():
			pass

		sel = rt.selection
		maxEval('''
		j = 1;
		count = sel.count;

		undo off;

		while sel.count > 1 do
		(
			if classof sel != Editable_Poly then converttopoly sel
			(
				polyop.attach sel sel;
			  deleteItem sel (j+1);

			  j += 1;

			  if (j + 1) > sel.count then 
			  (
			      j = 1
			  )
			)
		)
		''')


	def tb003(self, state=None):
		'''Extrude
		'''
		tb = self.polygons_ui.tb003

		keepFacesTogether = tb.contextMenu.chk002.isChecked() #keep faces/edges together.

		rt.macros.run('Ribbon - Modeling', 'EPoly_Extrude')
		# for obj in rt.selection:
		# 	self.extrudeObject(obj)


	def tb004(self, state=None):
		'''Bevel (Chamfer)
		'''
		tb = self.polygons_ui.tb004

		width = float(tb.contextMenu.s000.value())

		rt.macros.run('Ribbon - Modeling', 'EPoly_Chamfer')
		# width = float(self.polygons_ui.s000.value())
		# chamfer = True

		# if chamfer:
		# rt.macros.run('Modifiers', 'ChamferMod')
		# else: #bevel
		# 	maxEval('modPanel.addModToSelection (Bevel ()) ui:on')


	def tb005(self, state=None):
		'''Detach
		'''
		tb = self.polygons_ui.tb005

		#rt.macros.run('Ribbon - Modeling', 'GeometryDetach')
		level = rt.subObjectLevel

		
		for obj in rt.selection:
			if level==1: #vertices
				vertices = rt.getVertSelection(obj)
				for v in vertices:
					obj.EditablePoly.breakVerts(v)

			if level==2: #edges
				pass #add function to detach edge. likely as spline.

			if level==4: #faces
				element=rt.polyop.getElementsUsingFace(obj, 1)
				if rt.queryBox('Detach as Element?', title='Detach'): #detach as element
					rt.polyop.detachFaces(obj, element, delete=False, asNode=False)
				else: #detach as separate object
					rt.polyop.detachFaces(obj, element, delete=True, asNode=True)
	

	def tb006(self, state=None):
		'''Inset Face Region
		'''
		tb = self.polygons_ui.tb006

		offset = float(tb.contextMenu.s001.value())
		maxEval('''
		Try 
		(
			If subObjectLevel == undefined then Max Modify Mode
			local A = modPanel.getCurrentObject()
			if keyboard.shiftpressed then A.popupDialog #Inset
			else A.toggleCommandMode #InsetFace
		)
		Catch()
		''')


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
		selectedFaces = rt.getFaceSelection()
		# for face in selectedFaces: #when performing polySubdivideFacet on multiple faces, adjacent subdivided faces will make the next face an n-gon and therefore not able to be subdivided. 
		# 	pm.polySubdivideFacet(face, divisions=0, divisionsU=2, divisionsV=2, mode=0, subdMethod=1)


	def tb008(self, state=None):
		'''Boolean Operation
		'''
		tb = self.polygons_ui.tb008

		objects = list(Slots_max.bitArrayToArray(rt.selection))

		if tb.contextMenu.chk011.isChecked(): #union
			for obj in objects[:-1]:
				objects[-1] + obj

		if tb.contextMenu.chk012.isChecked(): #difference
			for obj in objects[:-1]:
				objects[-1] - obj

		if tb.contextMenu.chk013.isChecked(): #intersection
			for obj in objects[:-1]:
				objects[-1] * obj


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
			Slots_max.snapClosestVerts(obj1, obj2, tolerance, freezetransforms)
		else:
			return 'Error: Operation requires at least two selected objects.'


	def b000(self):
		'''Circularize
		'''
		obj = rt.selection[0]
		vertices = rt.polyop.getVertSelection(obj)
		
		self.circularize(vertices)


	def b001(self):
		'''Fill Holes
		'''
		rt.macros.run('Modifiers', 'Cap_Holes')


	@Slots.message
	def b002(self):
		'''Separate
		'''
		obj = rt.selection[0]

		self.detachElement(obj)


	def b003(self):
		'''Symmetrize
		'''
		pm.mel.Symmetrize()


	def b004(self):
		'''Slice
		'''
		rt.macros.run('Ribbon - Modeling', 'CutsQuickSlice')


	def b009(self):
		'''Collapse Component
		'''
		#--[mesh] 0=object level,1=vertex level,2=edge level,3=face,4=polygon,5=element,
		#--[poly] 0=object level,1=vertex level,2=edge level,3=border,4=polygon,5=element
		
		level = rt.subObjectLevel

		for obj in rt.selection:
			if level == 1: #--vertex level
				obj.EditablePoly.collapse('Vertex')

			if level == 2: #--edge level
				obj.EditablePoly.collapse('Edge')

			if level == 4: #--face level
				obj.EditablePoly.collapse('Face')

		# rt.macros.run('Ribbon - Modeling', 'GeometryCollapse')


	def b012(self):
		'''Multi-Cut Tool
		'''
		self.setSubObjectLevel(4)
		rt.macros.run('Ribbon - Modeling', 'CutsCut')
		# obj = rt.Filters.GetModOrObj()
		# if obj:
		# 	obj.ToggleCommandMode('CutVertex') #cut vertex tool


	def b021(self):
		'''Connect Border Edges
		'''
		mel.eval("performPolyConnectBorders 0;")


	def b022(self):
		'''Attach
		'''
		rt.macros.run('Ribbon - Modeling', 'AttachMode')


	def b028(self):
		'''Quad Draw
		'''
		mel.eval("dR_quadDrawTool;")


	def b032(self):
		'''Poke
		'''
		mel.eval("PokePolygon;")


	def b034(self):
		'''Wedge
		'''
		mel.eval("WedgePolygon;")


	def b038(self):
		'''Assign Invisible
		'''
		mel.eval("polyHole -assignHole 1;")


	def b043(self):
		'''Target Weld
		'''
		self.setSubObjectLevel(1) #set component mode to vertex
		rt.macros.run('Editable Polygon Object', 'EPoly_TargetWeld')
		

	def b045(self):
		'''Re-Order Vertices
		'''
		# symmetryOn = pm.symmetricModelling(query=True, symmetry=True) #query symmetry state
		
		# if symmetryOn:
		# 	pm.symmetricModelling(symmetry=False)
		# mel.eval("setPolygonDisplaySettings(\"vertIDs\");") #set vertex id on
		# mel.eval("doBakeNonDefHistory( 1, {\"pre\"});") #history must be deleted
		# mel.eval("performPolyReorderVertex;") #start vertex reorder ctx


	def b046(self):
		'''Split
		'''
		level = rt.subObjectLevel

		for obj in rt.selection:
			if level==1:
				vertex = rt.polyop.getVertSelection(obj)
				rt.polyop.breakVerts(obj, vertex)

			if level==2:
				position = 0.5

				edges = rt.getEdgeSelection(obj)
				for edge in Slots_max.bitArrayToArray(edges):
					rt.polyop.divideEdge(obj, edge, position)

			if level==4:
				mel.eval("polyChamferVtx 0 0.25 0;")

		rt.redrawViews


	def b047(self):
		'''Insert Edgeloop
		'''
		self.setSubObjectLevel(0)
		rt.macros.run('PolyTools', 'SwiftLoop')


	def b048(self):
		'''Collapse Edgering
		'''
		mel.eval("bt_polyCollapseEdgeRingTool;")


	def b049(self):
		'''Slide Edge Tool
		'''
		mel.eval("SlideEdgeTool;")


	def b050(self):
		'''Spin Edge
		'''
		mel.eval("bt_polySpinEdgeTool;")


	def b051(self):
		'''Offset Edgeloop
		'''
		mel.eval("performPolyDuplicateEdge 0;")


	def b053(self):
		'''Edit Edge Flow
		'''
		mel.eval("PolyEditEdgeFlow;")


	def circularize(self):
		'''Circularize a set of vertices on a circle or an elipse.

		tm = (matrix3 [-0.99596,0.022911,-0.0868241] [-0.0229109,0.870065,0.492404] [0.086824,0.492404,-0.866025] [-18.3751,-66.1508,30.969])
		c = [-18.3751,-66.1508,30.969]
		s = [-123.81,-63.7254,21.7775]
		u = [0.086824,0.492404,-0.866025]

		pCircle = pointCircle c s u 20
		'''
		maxEval('''
		fn pointCircle center startPoint upVector n = (
			rad = distance center startPoint
			dir = normalize (startPoint - center)
			crossVector = normalize (cross (normalize (startPoint - center)) upVector)
			tm = (matrix3 upVector crossVector dir center)

			p3Array = #()

			for i = 1 to n do (
				preRotateX tm (360.0 / n)
				append p3Array ([0,0,rad] * tm)
			)

			return p3Array
		)
		pointCircle()
		''')


	def detachElement(self, obj):
		'''Detach editable_mesh elements into new objects.

		:Parameters:
			obj (obj) = A polygon object.

		:Return:
			(list) detached objects.
		'''
		elementArray = []

		print(obj[0]) #object
		print(obj[6]) #baseObject class TYPE |string|
		print(obj[7]) #isValidNode

		if (obj[4] == rt.Editable_Poly and obj[7]): #or obj[6] == "Shape" or obj[6] == "Geometry" 

			rename = obj[0].name	
			rename += "_ele"
			#~ maxEval("undo \"DetachToElement\" on")
			while ((rt.polyOp.getNumFaces(obj[0])) > 0):
				elementToDetach = rt.polyOp.getElementsUsingFace(obj[0],[1]) #(1)
				rt.polyOp.detachFaces(obj[0], elementToDetach, delete=True, asNode=True, name=rename)
			rt.delete(obj[0])
			elementArray = rt.execute("$"+rename+"*")

			rt.select(elementArray)

		else:
			return 'Error: Object must be an Editable_Poly.'
		
		return elementArray











#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------