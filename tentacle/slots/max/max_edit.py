# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Edit(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.edit_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Max Editors')

		cmb = self.edit_ui.draggable_header.contextMenu.cmb000
		items = []
		cmb.addItems_(items, 'Max Editors')

		cmb = self.edit_ui.cmb001
		cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		ctx = self.edit_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='N-Gons', setObjectName='chk002', setToolTip='Find N-gons.')
			ctx.add('QCheckBox', setText='Isolated Vertex', setObjectName='chk003', setChecked=True, setToolTip='Find isolated vertices within specified angle threshold.')
			ctx.add('QSpinBox', setPrefix='Loose Vertex Angle: ', setObjectName='s006', setMinMax_='1-360 step1', setValue=15, setToolTip='Loose vertex search: Angle Threshold.')
			ctx.add('QCheckBox', setText='Repair', setObjectName='chk004', setToolTip='Repair matching geometry. (else: select)')

		ctx = self.edit_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='For All Objects', setObjectName='chk018', setChecked=True, setToolTip='Delete history on All objects or just those selected.')
			ctx.add('QCheckBox', setText='Delete Unused Nodes', setObjectName='chk019', setChecked=True, setToolTip='Delete unused nodes.')
			ctx.add('QCheckBox', setText='Delete Deformers', setObjectName='chk020', setToolTip='Delete deformers.')

		ctx = self.edit_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Delete Edge Loop', setObjectName='chk001', setToolTip='Delete the edge loops of any edges selected.')
			# ctx.add('QCheckBox', setText='Delete Edge Ring', setObjectName='chk000', setToolTip='Delete the edge rings of any edges selected.')

		ctx = self.edit_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='-', setObjectName='chk006', setChecked=True, setToolTip='Perform delete along negative axis.')
			ctx.add('QRadioButton', setText='X', setObjectName='chk007', setChecked=True, setToolTip='Perform delete along X axis.')
			ctx.add('QRadioButton', setText='Y', setObjectName='chk008', setToolTip='Perform delete along Y axis.')
			ctx.add('QRadioButton', setText='Z', setObjectName='chk009', setToolTip='Perform delete along Z axis.')
			self.connect_('chk006-9', 'toggled', self.chk006_9, ctx)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.edit_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.edit_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots_max.attr
	def cmb001(self, index=-1):
		'''Object History Attributes
		'''
		cmb = self.edit_ui.cmb001

		sel = list(rt.selection)
		if sel:
			list_ = ['{}.{}'.format(sel[0].name, m.name) for m in sel[0].modifiers]
			list_.append('{}.{}'.format(sel[0].name, 'baseObject'))
		else:
			list_ = ['No selection.']
		cmb.addItems_(list_, 'History')

		cmb.setCurrentIndex(0)
		if index>0:
			if cmb.items[index]!='No selection.':
				objName, attrName = cmb.items[index].split('.')
				obj = rt.getNodeByName(objName)
				return getattr(obj, attrName)


	def chk006_9(self):
		'''Set the toolbutton's text according to the checkstates.
		'''
		axis = self.getAxisFromCheckBoxes('chk006-9')
		self.edit_ui.tb003.setText('Delete '+axis)


	def tb000(self, state=None):
		'''Mesh Cleanup
		'''
		tb = self.edit_ui.tb000

		isolatedVerts = tb.contextMenu.chk003.isChecked() #isolated vertices
		edgeAngle = tb.contextMenu.s006.value()
		nGons = tb.contextMenu.chk002.isChecked() #n-sided polygons
		repair = tb.contextMenu.chk004.isChecked() #attempt auto repair errors

		self.meshCleanup(isolatedVerts=isolatedVerts, edgeAngle=edgeAngle, nGons=nGons, repair=repair)


	@Slots.message
	def tb001(self, state=None):
		'''Delete History
		'''
		tb = self.edit_ui.tb001

		all_ = tb.contextMenu.chk018.isChecked()
		unusedNodes = tb.contextMenu.chk019.isChecked()
		deformers = tb.contextMenu.chk020.isChecked()

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
				return 'Delete <hl>All</hl> History.'
			else:
				return 'Delete <hl>All Non-Deformer</hl> History.'
		else:
			if deformers:
				return 'Delete history on '+str(objects)
			else:
				return 'Delete <hl>Non-Deformer</hl> history on '+str(objects)


	def tb002(self, state=None):
		'''Delete
		'''
		tb = self.edit_ui.tb002

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


	@Slots.message
	@Slots.hideMain
	def b001(self):
		'''Object History Attributes: get most recent node
		'''
		selection = rt.modPanel.getCurrentObject()
		if not selection:
			return 'Error: Operation requires a single selected object.'

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


	@staticmethod
	def findNGons(obj):
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


	@staticmethod
	def getVertexVectors(obj, vertices):
		'''Generator to query vertex vector angles.

		ex.
		vectors = Edit.getVertexVectors(obj, vertices)
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


	@staticmethod
	def findIsolatedVertices(obj):
		'''Get a list of isolated vertices of a given object.

		:Parameters:
			obj (obj) = polygonal object.

		:Return:
			(list) list containing any found isolated verts.		
		'''
		vertices = Slots_max.getComponents(obj, 'vertices') #get all vertices for the given object

		isolatedVerts=[]
		vectors = Edit.getVertexVectors(obj, vertices)
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
				_nGons = Edit.findNGons(obj)

				print('Found '+str(len(_nGons))+' N-gons.')

				if repair:
					maxEval('macros.run \"Modifiers\" \"QuadifyMeshMod\"') #add the quadify mesh modifier to the stack
				else: #Find and select N-gons	
					rt.setFaceSelection(obj, _nGons)


			if isolatedVerts: #delete loose vertices
				_isolatedVerts = Edit.findIsolatedVertices(obj)

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
		tb = self.edit_ui.tb003

		# selection = pm.ls(sl=1, objectsOnly=1)
		# axis = self.getAxisFromCheckBoxes('chk006-9', tb.contextMenu)

		# pm.undoInfo(openChunk=1)
		# for obj in selection:
		# 	self.deleteAlongAxis(obj, axis) #Slots_max.deleteAlongAxis - no max version.
		# pm.undoInfo(closeChunk=1)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

# maxEval('max array')

# maxEval('max mirror')