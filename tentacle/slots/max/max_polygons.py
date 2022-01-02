# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Polygons(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.polygons_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.polygons_ui.draggable_header.contextMenu.cmb000
		items = ['Bridge','Extrude']
		cmb.addItems_(items, '3dsMax Polygon Operations')

		ctx = self.polygons_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Distance: ', setObjectName='s002', setMinMax_='0.000-10 step.005', setValue=0.001, setHeight_=20, setToolTip='Merge Distance.')

		ctx = self.polygons_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s003', setMinMax_='0-10000 step1', setValue=0, setHeight_=20, setToolTip='Subdivision Amount.')

		ctx = self.polygons_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Merge', setObjectName='chk000', setChecked=True, setHeight_=20, setToolTip='Combine selected meshes and merge any coincident verts/edges.')

		ctx = self.polygons_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Keep Faces Together', setObjectName='chk002', setChecked=True, setHeight_=20, setToolTip='Keep edges/faces together.')
			ctx.add('QSpinBox', setPrefix='Divisions: ', setObjectName='s004', setMinMax_='1-10000 step1', setValue=1, setHeight_=20, setToolTip='Subdivision Amount.')

		ctx = self.polygons_ui.tb004.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', setMinMax_='0.00-100 step.05', setValue=0.25, setHeight_=20, setToolTip='Bevel Width.')

		ctx = self.polygons_ui.tb005.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Duplicate', setObjectName='chk014', setChecked=True, setToolTip='Duplicate any selected faces, leaving the originals.')
			ctx.add('QCheckBox', setText='Separate', setObjectName='chk015', setChecked=True, setToolTip='Separate mesh objects after detaching faces.')
			# ctx.add('QCheckBox', setText='Delete Original', setObjectName='chk007', setChecked=True, setToolTip='Delete original selected faces.')

		ctx = self.polygons_ui.tb006.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Offset: ', setObjectName='s001', setMinMax_='0.00-100 step.01', setValue=2.00, setHeight_=20, setToolTip='Offset amount.')

		ctx = self.polygons_ui.tb007.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='U', setObjectName='chk008', setChecked=True, setHeight_=20, setToolTip='Divide facet: U coordinate.')
			ctx.add('QCheckBox', setText='V', setObjectName='chk009', setChecked=True, setHeight_=20, setToolTip='Divide facet: V coordinate.')
			ctx.add('QCheckBox', setText='Tris', setObjectName='chk010', setHeight_=20, setToolTip='Divide facet: Tris.')

		ctx = self.polygons_ui.tb008.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Union', setObjectName='chk011', setHeight_=20, setToolTip='Fuse two objects together.')
			ctx.add('QRadioButton', setText='Difference', setObjectName='chk012', setChecked=True, setHeight_=20, setToolTip='Indents one object with the shape of another at the point of their intersection.')
			ctx.add('QRadioButton', setText='Intersection', setObjectName='chk013', setHeight_=20, setToolTip='Keep only the interaction point of two objects.')

		ctx = self.polygons_ui.tb008.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Union', setObjectName='chk011', setHeight_=20, setToolTip='Fuse two objects together.')
			ctx.add('QRadioButton', setText='Difference', setObjectName='chk012', setChecked=True, setHeight_=20, setToolTip='Indents one object with the shape of another at the point of their intersection.')
			ctx.add('QRadioButton', setText='Intersection', setObjectName='chk013', setHeight_=20, setToolTip='Keep only the interaction point of two objects.')

		ctx = self.polygons_ui.tb009.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s005', setMinMax_='.000-100 step.05', setValue=10, setToolTip='Set the max Snap Distance. Vertices with a distance exceeding this value will be ignored.')
			ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk016', setChecked=True, setToolTip='Freeze Transformations on the object that is being snapped to.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.polygons_ui.draggable_header


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
		self.toggleWidgets(setUnChecked='chk008,chk009')


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
		tb = self.current_ui.tb000

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
		tb = self.current_ui.tb001

		divisions = tb.contextMenu.s003.value()

		for obj in rt.selection:
			obj.EditablePoly.Bridge() #perform bridge
		rt.redrawViews() #redraw changes in viewport


	def tb002(self, state=None):
		'''Combine
		'''
		tb = self.current_ui.tb002

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
		tb = self.current_ui.tb003

		keepFacesTogether = tb.contextMenu.chk002.isChecked() #keep faces/edges together.

		rt.macros.run('Ribbon - Modeling', 'EPoly_Extrude')
		# for obj in rt.selection:
		# 	self.extrudeObject(obj)


	def tb004(self, state=None):
		'''Bevel (Chamfer)
		'''
		tb = self.current_ui.tb004

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
		tb = self.current_ui.tb005

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
		tb = self.current_ui.tb006

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
		tb = self.current_ui.tb007

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
		
		Slots_max.circularize(vertices)


	def b001(self):
		'''Fill Holes
		'''
		rt.macros.run('Modifiers', 'Cap_Holes')


	def b002(self):
		'''Separate
		'''
		pass
		# rt.detachElement(obj)


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











#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------