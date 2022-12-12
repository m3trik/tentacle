# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.edit import Edit



class Edit_max(Edit, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.edit.draggable_header.ctxMenu.cmb000
		items = []
		cmb.addItems_(items, 'Max Editors')

		ctx = self.sb.edit.tb000.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='N-Gons', setObjectName='chk002', setToolTip='Find N-gons.')
			ctx.add('QCheckBox', setText='Isolated Vertex', setObjectName='chk003', setChecked=True, setToolTip='Find isolated vertices within specified angle threshold.')
			ctx.add('QSpinBox', setPrefix='Loose Vertex Angle: ', setObjectName='s006', setMinMax_='1-360 step1', setValue=15, setToolTip='Loose vertex search: Angle Threshold.')
			ctx.add('QCheckBox', setText='Repair', setObjectName='chk004', setToolTip='Repair matching geometry. (else: select)')

		ctx = self.sb.edit.tb002.ctxMenu
		ctx.chk000.setDisabled(True) #disable: Delete Edge Ring.


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.edit.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots_max.attr
	def cmb001(self, index=-1):
		'''Object History Attributes
		'''
		cmb = self.sb.edit.cmb001

		sel = list(rt.selection)
		if sel:
			items = ['{}.{}'.format(sel[0].name, m.name) for m in sel[0].modifiers]
			items.append('{}.{}'.format(sel[0].name, 'baseObject'))
		else:
			items = ['No selection.']
		cmb.addItems_(items, 'History')

		cmb.setCurrentIndex(0)
		if index>0:
			if cmb.items[index]!='No selection.':
				objName, attrName = cmb.items[index].split('.')
				obj = rt.getNodeByName(objName)
				return getattr(obj, attrName)


	def tb000(self, state=None):
		'''Mesh Cleanup
		'''
		tb = self.sb.edit.tb000

		isolatedVerts = tb.ctxMenu.chk003.isChecked() #isolated vertices
		edgeAngle = tb.ctxMenu.s006.value()
		nGons = tb.ctxMenu.chk002.isChecked() #n-sided polygons
		repair = tb.ctxMenu.chk004.isChecked() #attempt auto repair errors

		self.meshCleanup(isolatedVerts=isolatedVerts, edgeAngle=edgeAngle, nGons=nGons, repair=repair)


	def tb001(self, state=None):
		'''Delete History
		'''
		tb = self.sb.edit.tb001

		all_ = tb.ctxMenu.chk018.isChecked()
		unusedNodes = tb.ctxMenu.chk019.isChecked()
		deformers = tb.ctxMenu.chk020.isChecked()

		objects = pm.ls(selection=1)
		if all_:
			objects = pm.ls(typ="mesh")

		for obj in objects:
			try:
				if all_:
					pm.delete (obj, constructionHistory=1)
				else:
					pm.bakePartialHistory (obj, prePostDeformers=1)
			except:
				pass
		if unusedNodes:
			maxEval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')

		#display viewPort messages
		if all_:
			if deformers:
				self.messageBox('Delete <hl>All</hl> History.')
				return
			else:
				self.messageBox('Delete <hl>All Non-Deformer</hl> History.')
				return
		else:
			if deformers:
				self.messageBox('Delete history on '+str(objects))
				return
			else:
				self.messageBox('Delete <hl>Non-Deformer</hl> history on '+str(objects))
				return


	def tb002(self, state=None):
		'''Delete
		'''
		tb = self.sb.edit.tb002

		level = rt.subObjectLevel

		for obj in rt.selection:
			if level==1: #vertices
				obj.EditablePoly.remove(selLevel='Vertex', flag=1)

			if level==2: #edges
				edges = rt.polyop.getEdgeSelection(obj)
				verts = rt.polyop.getVertsUsingEdge(obj, edges)
				rt.polyop.setVertSelection(obj, verts) #set vertex selection to be used by meshCleanup
				
				obj.EditablePoly.remove(selLevel='Edge', flag=1)
				self.meshCleanup(isolatedVerts=1, repair=1) #if any isolated verts exist: delete them

			if level==4: #faces
				faces = rt.polyop.getFaceSelection(obj)
				rt.polyop.deleteFaces(obj, faces, delIsoVerts=1)


	@Slots.hideMain
	def b001(self):
		'''Object History Attributes: get most recent node
		'''
		selection = rt.modPanel.getCurrentObject()
		if not selection:
			self.messageBox('Operation requires a single selected object.')
			return

		self.setAttributeWindow(selection, checkableLabel=True)


	def b021(self):
		'''Tranfer Maps
		'''
		maxEval('performSurfaceSampling 1;')


	def b022(self):
		'''Transfer Vertex Order
		'''
		maxEval('TransferVertexOrder;')


	def b023(self):
		'''Transfer Attribute Values
		'''
		maxEval('TransferAttributeValues;')


	def b027(self):
		'''Shading Sets
		'''
		print('no function')


	def findNGons(self, obj):
		'''Get a list of faces of a given object having more than four sides.

		:Parameters:
			obj (obj) = polygonal object.

		:Return:
			(list) list containing any found N-Gons		
		'''
		faces = Slots_max.getComponents(obj, 'faces')

		Slots_max.setSubObjectLevel(4)
				
		nGons = [f for f in faces if rt.polyop.getFaceDeg(obj, f)>4]
		return nGons


	def getVertexVectors(self, obj, vertices):
		'''Generator to query vertex vector angles.

		ex.
		vectors = getVertexVectors(obj, vertices)
		for _ in range(len(vertices)):
			vector = vectors.next()
		'''
		for vertex in vertices:
			try:
				edges = Slots_max.bitArrayToArray(rt.polyop.getEdgesUsingVert(obj, vertex)) #get the edges that use the vertice
			except:
				edges = Slots_max.bitArrayToArray(rt.getEdgesUsingVert(obj, vertex)) #get the edges that use the vertice

			if len(edges)==2:
				try:
					vertexPosition = rt.polyop.getVert(obj, vertex)
				except:
					vertexPosition = rt.getVert(obj, vertex)

				try:
					edgeVerts = Slots_max.bitArrayToArray([rt.polyop.getVertsUsingEdge(obj, e) for e in edges])
				except:
					edgeVerts = Slots_max.bitArrayToArray([rt.getVertsUsingEdge(obj, e) for e in edges])

				edgeVerts = [v for v in edgeVerts if not v==vertex]

				try:
					vector1 = rt.normalize(rt.polyop.getVert(obj, edgeVerts[0]) - vertexPosition)
					vector2 = rt.normalize(rt.polyop.getVert(obj, edgeVerts[1]) - vertexPosition)
				except:
					vector1 = rt.normalize(rt.getVert(obj, edgeVerts[0]) - vertexPosition)
					vector2 = rt.normalize(rt.getVert(obj, edgeVerts[1]) - vertexPosition)

				vector = rt.length(vector1 + vector2)
				yield vector


	def findIsolatedVertices(self, obj):
		'''Get a list of isolated vertices of a given object.

		:Parameters:
			obj (obj) = polygonal object.

		:Return:
			(list) list containing any found isolated verts.		
		'''
		vertices = Slots_max.getComponents(obj, 'vertices') #get all vertices for the given object

		isolatedVerts=[]
		vectors = self.getVertexVectors(obj, vertices)
		for _ in range(len(vertices)):
			vector = vectors.next()
			if vector and vector <= float(edgeAngle) / 50:
				isolatedVerts.append(vector)

		return isolatedVerts


	def meshCleanup(self, isolatedVerts=False, edgeAngle=10, nGons=False, repair=False):
		'''Find mesh artifacts.

		:Parameters:
			isolatedVerts (bool) = find vertices with two edges which fall below a specified angle.
			edgeAngle (int) = used with isolatedVerts argument to specify the angle tolerance
			nGons (bool) = search for n sided polygon faces.
			repair (bool) = delete or auto repair any of the specified artifacts 
		'''
		for obj in rt.selection:
			if not rt.classof(obj)==rt.Editable_poly:
				print('Error: '+obj.name+' isn\'t an editable poly or nothing is selected.')

			obj.selectMode = 2 #multi-component selection preview

			if nGons: #Convert N-Sided Faces To Quads
				_nGons = self.findNGons(obj)

				print('Found '+str(len(_nGons))+' N-gons.')

				if repair:
					maxEval('macros.run \"Modifiers\" \"QuadifyMeshMod\"') #add the quadify mesh modifier to the stack
				else: #Find and select N-gons	
					rt.setFaceSelection(obj, _nGons)


			if isolatedVerts: #delete loose vertices
				_isolatedVerts = self.findIsolatedVertices(obj)

				Slots_max.undo(True)
				try:
					rt.polyop.setVertSelection(obj, _isolatedVerts)
				except:
					rt.setVertSelection(obj, _isolatedVerts)

				print('Found '+str(len(_isolatedVerts))+' isolated vertices.')
				
				if repair:
					obj.EditablePoly.remove(selLevel='Vertex', flag=1)
					obj.selectMode = 0 #multi-component selection preview off
				rt.redrawViews()
				Slots_max.undo(False)


	def tb003(self, state=None):
		'''Delete Along Axis
		'''
		tb = self.sb.edit.tb003

		# selection = pm.ls(sl=1, objectsOnly=1)
		# axis = self.sb.getAxisFromCheckBoxes('chk006-9', tb.ctxMenu)

		# pm.undoInfo(openChunk=1)
		# for obj in selection:
		# 	self.deleteAlongAxis(obj, axis) #Slots_max.deleteAlongAxis - no max version.
		# pm.undoInfo(closeChunk=1)


	def b000(self):
		'''Clean: Repair
		'''
		self.cleanGeometry(repair=True, nsided=True, concave=False, nonplanar=False, zeroGeom=False, zeroEdge=False, zeroMap=False, 
							sharedUVs=False, nonmanifold=True, invalidComponents=False, splitNonManifoldVertex=False)


	@Slots.hideMain
	def b001(self):
		'''Object History Attributes: get most recent node
		'''
		cmb = self.sb.edit.cmb001
		self.cmb001() #refresh the contents of the combobox.

		items = pm.ls(cmb.items[-1])
		if items:
			self.setAttributeWindow(items, checkableLabel=True)
		else:
			self.messageBox('Found no items to list the history for.')
			return


	def b021(self):
		'''Tranfer Maps
		'''
		pm.mel.performSurfaceSampling(1)


	def b022(self):
		'''Transfer Vertex Order
		'''
		pm.mel.TransferVertexOrder()


	def b023(self):
		'''Transfer Attribute Values
		'''
		pm.mel.TransferAttributeValues()


	def b027(self):
		'''Shading Sets
		'''
		pm.mel.performTransferShadingSets(0)


	def compareMesh(self, obj1, obj2, factor):
		'''Compares vert/face/edges counts.

		:Parameters:
			obj1 (obj) = 
			obj2 (obj) = 
			factor () = 
		'''
		maxEval('''
		if superclassof obj1 == GeometryClass then	--if object is a geometry type (mesh)
		(
			o1v = obj1.mesh.verts.count	--store object 1 and 2 vert / face / edge counts
			o1f = obj1.mesh.faces.count
			o1e = obj1.mesh.edges.count
			o2v = obj2.mesh.verts.count
			o2f = obj2.mesh.faces.count
			o2e = obj2.mesh.edges.count
			
			if o2v >= o1v*(1-factor) AND o2v <= o1v*(1+factor) THEN 		--simpler than it looks. the 'factor' aka 'ratio' in the ui is 
				if o2f >= o1f*(1-factor) AND o2f <= o1f*(1+factor) THEN		--allows for slop in the comparison. 0.1 is a 10% difference so comparing
					if o2e >= o1e*(1-factor) AND o2e <= o1e*(1+factor) THEN	--face*(1-factor) is the same as saying face*0.9 in our example
					(
						dbgSelSim ("  Mesh match on '" + obj1.name + "' with '" + obj2.name + "' | V: " + o1v as string + ", " + o2v as string + " | F: " + o1f as string + ", " + o2f as string + " | E: " + o1e as string + ", " + o2e as string)
						return true
					)
					else return false
				else return false
			else return false
		)
		else if superclassof obj1 == shape then
		(
			o1v = numKnots obj1
			o2v = numKnots obj2
			
			if o2v >= o1v*(1-factor) AND o2v <= o1v*(1+factor) THEN
				return true
			else return false
		)
		''')









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

# maxEval('max array')

# maxEval('max mirror')