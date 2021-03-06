# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtGui, QtWidgets, QtCore

try: #3ds Max dependancies
	from pymxs import runtime as rt
	maxEval = rt.execute #rt.executeScriptFile

except ImportError as error:
	print(__file__, error); rt=None; maxEval=lambda s: None

from slots import Slots
from .staticUi_max import StaticUi_max

staticUiInitialized = False



class Slots_max(Slots):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		Slots.__init__(self, *args, **kwargs)

		global staticUiInitialized
		if not staticUiInitialized:
			StaticUi_max.__init__(self, *args, **kwargs)
			staticUiInitialized = True


	# --------------------------------------------------
		'ATTRIBUTES:'
	# --------------------------------------------------
	@staticmethod
	def getAttributesMax(node, include=[], exclude=[]):
		'''Get node attributes and their corresponding values as a dict.

		:Parameters:
			node (obj) = Transform node.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']

		:Return:
			(dict) {'string attribute': current value}

		# print (rt.showProperties(obj))
		# print (rt.getPropNames(obj))
		'''
		if not all((include, exclude)):
			exclude = ['getmxsprop', 'setmxsprop', 'typeInHeight', 'typeInLength', 'typeInPos', 'typeInWidth', 'typeInDepth', 
				'typeInRadius', 'typeInRadius1', 'typeInRadius2', 'typeinCreationMethod', 'edgeChamferQuadIntersections', 
				'edgeChamferType', 'hemisphere', 'realWorldMapSize', 'mapcoords']

		attributes = {attr:node.getmxsprop(attr) for attr in [str(n) for n in rt.getPropNames(node)] 
				if not attr in exclude and (attr in include if include else attr not in include)}

		return attributes


	@staticmethod
	def setAttributesMax(node, attributes):
		'''Set history node attributes using the transform node.

		:Parameters:
			node (obj) = Transform node.
			attributes (dict) = Attributes and their correponding value to set. ie. {'string attribute': value}
		'''
		[setattr(node, attribute, value) for attribute, value in attributes.items() 
		if attribute and value]

		rt.redrawViews()






	# ------------------------------------------------
		'COMPONENT LEVEL:'
	# ------------------------------------------------

	@staticmethod
	def getFacesByNormal(normal, tolerance, includeBackFaces):
		'''Get all faces in a mesh/poly that have normals within the given tolerance range.

		:Parameters:
			normal (obj) = Polygon face normal.
			tolerance (float) = Normal tolerance.
			includeBackFaces (bool) = Include back-facing faces.
		'''
		maxEval('''
		local collected_faces = for i = 1 to num_faces
			where (local norm_vect = normalize (get_face_normal obj i)).x <= (normal.x + tolerance.x) AND norm_vect.x >= (normal.x - tolerance.x) AND
				norm_vect.y <= (normal.y + tolerance.y) AND norm_vect.y >= (normal.y - tolerance.y) AND
				norm_vect.z <= (normal.z + tolerance.z) AND norm_vect.z >= (normal.z - tolerance.z) collect i

		if includeBackFaces do
		(
			local collected_back_faces = for i = 1 to num_faces
				where (local norm_vect = - (normalize (get_face_normal obj i))).x <= (normal.x + tolerance.x) AND norm_vect.x >= (normal.x - tolerance.x) AND
					norm_vect.y <= (normal.y + tolerance.y) AND norm_vect.y >= (normal.y - tolerance.y) AND
					norm_vect.z <= (normal.z + tolerance.z) AND norm_vect.z >= (normal.z - tolerance.z) collect i
			join collected_faces collected_back_faces
		)
		''')
		return collected_faces


	@staticmethod
	def getEdgesByAngle(minAngle, maxAngle):
		'''Get edges between min and max angle.

		:Parameters:
			minAngle (float) = minimum search angle tolerance.
			maxAngle (float) = maximum search angle tolerance.

		:Return:
			(list) edges within the given range.
		'''
		edgelist=[]
		for obj in rt.selection:

			for edge in list(range(1, obj.edges.count)):
				faces = rt.polyOp.getEdgeFaces(obj, edge)
				if faces.count==2:

					v1 = rt.polyop.getFaceNormal(obj, faces[0])
					v2 = rt.polyop.getFaceNormal(obj, faces[1])

					angle = rt.acos(rt.dot(rt.normalize(v1), rt.normalize(v2)))
					if angle >= minAngle and angle <= maxAngle:
						edgelist.append(edge)

			return edgelist


	@staticmethod
	def getComponents(obj=None, componentType=None, selection=False, returnType='List'):
		'''Get the components of the given type. (editable mesh or polygon)

		:Parameters:
			obj (obj) = An Editable mesh or Editable polygon object. If None; the first currently selected object will be used.
			componentType (str)(int) = The desired component mask. (valid: 'vertex', 'vertices', 'edge', 'edges', 'face', 'faces').
			selection (bool) = Filter to currently selected components.
			returnType (type) = The desired returned object type. (valid: 'Array', 'BitArray', 'List'(default))

		:Return:
			(array) Dependant on flags.

		ex. getComponents(obj, 'vertices', selection=True, returnType='BitArray')
		'''
		if not obj:
			obj = rt.selection[0]

		if not any((rt.isKindOf(obj, rt.Editable_Mesh), rt.isKindOf(obj, rt.Editable_Poly))): #filter for valid objects.
			return '# Error: Invalid object type: {} #'.format(obj)

		c=[] #for cases when no componentType given; initialize c with an empty list.
		if componentType in ('vertex', 'vertices'):
			if selection:
				try:
					c = rt.polyop.getVertSelection(obj) #polygon
				except:
					c = rt.getVertSelection(obj) #mesh
			else:
				try:
					c = range(1, rt.polyop.getNumVerts(obj))
				except:
					c = range(1, rt.getNumVerts(obj))

		elif componentType in ('edge', 'edges'):
			if selection:
				try:
					c = rt.polyop.getEdgeSelection(obj) #polygon
				except:
					c = rt.getEdgeSelection(obj) #mesh
			else:
				try:
					c = range(1, rt.polyop.getNumEdges(obj))
				except:
					c = range(1, obj.edges.count)

		elif componentType in ('face', 'faces'):
			if selection:
				try:
					c = rt.polyop.getFaceSelection(obj) #polygon
				except:
					c = rt.getFaceSelection(obj) #mesh
			else:
				try:
					c = range(1, rt.polyop.getNumFaces(obj))
				except:
					c = range(1, obj.faces.count)

		if returnType in ('Array', 'List'):
			result = Slots_max.bitArrayToArray(c)
			if returnType is 'List':
				result = list(result)
		else:
			result = Slots_max.arrayToBitArray(c)

		return result


	@staticmethod
	def convertComponents(obj=None, components=None, convertFrom=None, convertTo=None, returnType='List'):
		'''Convert the components to the given type. (editable mesh, editable poly)

		:Parameters:
			obj (obj) = An Editable mesh or Editable polygon object. If None; the first currently selected object will be used.
			components (list) = The component id's of the given object.  If None; all components of the given convertFrom type will be used.
			convertFrom (str) = Starting component type. (valid: 'vertex', 'vertices', 'edge', 'edges', 'face', 'faces').
			convertTo (str) = Resulting component type.  (valid: 'vertex', 'vertices', 'edge', 'edges', 'face', 'faces').
			returnType (type) = The desired returned object type. (valid: 'Array', 'BitArray', 'List'(default))

		:Return:
			(array) Component ID's. ie. [1, 2, 3]

		ex. obj = rt.selection[0]
			edges = rt.getEdgeSelection(obj)
			faces = convertComponents(obj, edges, 'edges', 'faces')
			rt.setFaceSelection(obj, faces)
		'''
		if not obj:
			obj = rt.selection[0]
		if not components:
			components = Slots_max.getComponents(obj, convertFrom)

		if not any((rt.isKindOf(obj, rt.Editable_Mesh), rt.isKindOf(obj, rt.Editable_Poly))): #filter for valid objects.
			return '# Error: Invalid object type: {} #'.format(obj)

		if convertFrom in ('vertex', 'vertices') and convertTo in ('edge', 'edges'): #vertex to edge
			c = rt.polyop.getEdgesUsingVert(obj, components)

		elif convertFrom in ('vertex', 'vertices') and convertTo in ('face', 'faces'): #vertex to edge
			c = rt.polyop.getFacesUsingVert(obj, components)

		elif convertFrom in ('edge', 'edges') and convertTo in ('vertex', 'vertices'): #vertex to edge
			c = rt.polyop.getVertsUsingEdge(obj, components)

		elif convertFrom in ('edge', 'edges') and convertTo in ('face', 'faces'): #vertex to edge
			c = rt.polyop.getFacesUsingEdge(obj, components)

		elif convertFrom in ('face', 'faces') and convertTo in ('vertex', 'vertices'): #vertex to edge
			c = rt.polyop.getVertsUsingFace(obj, components)

		elif convertFrom in ('face', 'faces') and convertTo in ('edge', 'edges'): #vertex to edge
			c = rt.polyop.getEdgesUsingFace(obj, components)

		else:
			return '# Error: Cannot convert from {} to type: {}: #'.format(convertFrom, convertTo)

		if returnType in ('Array', 'List'):
			result = Slots_max.bitArrayToArray(c)
			if returnType is 'List':
				result = list(result)
		else:
			result = Slots_max.arrayToBitArray(c)

		return result










	# -------------------------------------------------------------
		':'
	# -------------------------------------------------------------

	@staticmethod
	def arrayToBitArray(array):
		'''Convert an integer array to a bitArray.

		:Parameters:
			array (list) = The array that will be converted to a bitArray.
		'''
		maxEval("fn _arrayToBitArray a = (return a as bitArray)")
		result = rt._arrayToBitArray(array)

		return result


	@staticmethod
	def bitArrayToArray(bitArray):
		'''Convert a bitArray to an integer array.

		:Parameters:
			bitArray (list) = The bitArray that will be converted to a standard array.
		'''
		maxEval("fn _bitArrayToArray b = (return b as array)")
		result = rt._bitArrayToArray(bitArray)

		return result


	@staticmethod
	def toggleMaterialOverride(checker=False):
		'''Toggle override all materials in the scene.

		:Parameters:
			checker (bool) = Override with UV checkered material.
		'''
		state = Slots.cycle([0,1], 'OverrideMateridal') #toggle 0/1
		if state:
			rt.actionMan.executeAction(0, "63574") #Views: Override Off	
		else:
			if checker:
				rt.actionMan.executeAction(0, "63573") #Views: Override with UV Checker
			else:	
				rt.actionMan.executeAction(0, "63572") #Views: Override with Fast Shader
		rt.redrawViews


	@staticmethod
	def setSubObjectLevel(level):
		'''
		:Parameters:
			level (int) = set component mode. 0(object), 1(vertex), 2(edge), 3(border), 4(face), 5(element)
		'''
		maxEval ('max modify mode') #set focus: modifier panel.

		selection = rt.selection

		for obj in selection:
			rt.modPanel.setCurrentObject(obj.baseObject)
			rt.subObjectLevel = level

			if level==0: #reset the modifier selection to the top of the stack.
				toggle = Slots.cycle([0,1], 'toggle_baseObjectLevel')
				if toggle:
					rt.modPanel.setCurrentObject(obj.baseObject)
				else:
					try:
						rt.modPanel.setCurrentObject(obj.modifiers[0])
					except:
						rt.modPanel.setCurrentObject(obj.baseObject) #if index error


	@staticmethod
	def getModifier(obj, modifier, index=0):
		'''Gets (and sets (if needed)) the given modifer for the given object at the given index.
		
		:Parameters:
			obj = <object> - the object to add or retrieve the modifier from.
			modifier (str) = modifier name.
			index (int) = place modifier before given index. default is at the top of the stack.
						Negative indices place the modifier from the bottom of the stack.
		:Return:
			(obj) modifier object.
		'''
		m = obj.modifiers[modifier] #check the stack for the given modifier.
		
		if not m:
			m = getattr(rt, modifier)()
			if index<0:
				index = index+len(obj.modifiers)+1 #place from the bottom index.
			rt.addModifier(obj, m, before=index)
		
		if not rt.modPanel.getCurrentObject()==m:
			rt.modPanel.setCurrentObject(m) #set modifier in stack (if it is not currently active).

		return m


	@staticmethod
	def undo(state=True):
		'''
		'''
		import pymxs
		pymxs.undo(state)
		return state






	# ------------------------------------------------
		'UI:'
	# ------------------------------------------------

	@classmethod
	def attr(cls, fn):
		'''Decorator for objAttrWindow.
		'''
		def wrapper(self, *args, **kwargs):
			self.setAttributeWindow(fn(self, *args, **kwargs))
		return wrapper

	def setAttributeWindow(self, obj, attributes={}, include=[], exclude=[], checkableLabel=True, fn=None, fn_args=[]):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (obj)(list) = The object to get the attributes of.
			attributes (dict) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from self.getAttributesMax for the given obj.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']
			checkableLabel (bool) = Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. fn(obj, {'attr':<value>})
			fn_args (list) = Any additonal args to pass to fn.
				The first parameter of fn is always the given object, and the last parameter is the attribute:value pairs as a dict.

		ex. call: self.setAttributeWindow(obj, attributes=attrs, checkableLabel=True)
		'''
		if not obj:
			return
		elif isinstance(obj, (list, set, tuple)):
			obj = obj[0]

		fn = fn if fn else self.setAttributesMax

		if attributes:
			attributes = {k:v for k, v in attributes.items() 
				if not k in exclude and (k in include if include else k not in include)}
		else:
			attributes = self.getAttributesMax(obj, include=include, exclude=exclude)

		children = self.objAttrWindow(obj, attributes, checkableLabel=checkableLabel, fn=fn, fn_args=fn_args)

		if checkableLabel: # this is not set up yet for max. currently just outputs the check state for testing.
			for c in children:
				if c.__class__.__name__=='QCheckBox':
					# c.stateChanged.connect(lambda state, obj=obj, attr=attr: rt.selectMore(prop) if state else rt.deselect(prop))
					c.stateChanged.connect(lambda state, obj=obj, w=c: print('select: '+'{}.{}'.format(obj.name, w.objectName())) if state 
						else print('deselect: '+'{}.{}'.format(obj.name, w.objectName())))
					# if attr in list(rt.selection):
						# c.setChecked(True)


	def maxUiSetChecked(self, id, table, item, state=True, query=False):
		'''
		:Parameters:
			id (str) = The actionMan ID
			table (int) = The actionMan table
			item (int) = The actionMan item number
			state (bool) = Set the check state.
			query (bool) = Query the check state.

		:Return:
			(bool) The check state.
		'''
		atbl = rt.actionMan.getActionTable(table)
		if atbl:
			aitm = atbl.getActionItem(item)
			if query:
				return aitm.isChecked
			else:
				if state: #check
					if not aitm.isChecked:
						rt.actionMan.executeAction(0, id)
						return aitm.isChecked
				else: #uncheck
					if aitm.isChecked:
						rt.actionMan.executeAction(0, id)
						return aitm.isChecked









#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------




# -----------------------------------------------
# deprecated:
# -----------------------------------------------

	# def selectFaceLoop(tolerance, includeOpenEdges=False):
	# 	'''
	# 	:Parameters:
	# 		tolerance (float) = Face normal tolerance.
	# 		includeOpenEdges (bool) = 
	# 	'''
	# 	maxEval('''
	# 	selEdges = #{}
	# 	theObj = $

	# 	eCount = polyOp.getNumEdges theObj
	# 	for e = 1 to eCount do
	# 	(
	# 		theFaces = (polyOp.getEdgeFaces theObj e) as array
	# 		if theFaces.count == 2 then
	# 		(
	# 		 theAngle = acos(dot (polyOp.getFaceNormal theObj theFaces[1]) (polyOp.getFaceNormal theObj theFaces[2])) 
	# 			if theAngle >= tolerance do selEdges[e] = true
	# 		)	
	# 		else 
	# 			if includeOpenEdges do selEdges[e] = true
	# 	)
	# 	case classof (modPanel.getCurrentObject()) of
	# 	(
	# 		Editable_Poly: polyOp.setEdgeSelection theObj selEdges 
	# 		Edit_Poly: (modPanel.getCurrentObject()).SetSelection #Edge &selEdges 
	# 	)	
	# 	redrawViews()
	# 	''')


	# @staticmethod
	# def getVertices(obj):
	# 	'''Get the vertices of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) vertex list.		
	# 	'''
	# 	try:
	# 		vertices = Slots_max.bitArrayToArray(rt.polyop.getVertSelection(obj)) #polygon
	# 	except:
	# 		vertices = Slots_max.bitArrayToArray(rt.getVertSelection(obj)) #mesh

	# 	return vertices


	# @staticmethod
	# def getSelectedVertices(obj):
	# 	'''Get the selected vertices of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) vertex list.		
	# 	'''
	# 	try:
	# 		vertices = list(range(1, rt.polyop.getNumVerts(obj)))
	# 	except:
	# 		vertices = list(range(1, rt.getNumVerts(obj)))

	# 	return vertices


	# @staticmethod
	# def getEdges(obj):
	# 	'''Get the edges of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) edge list.		
	# 	'''
	# 	try:
	# 		edges = list(range(1, rt.polyop.getNumEdges(obj)))
	# 	except:
	# 		edges = list(range(1, obj.edges.count))

	# 	return edges


	# @staticmethod
	# def getSelectedEdges(obj):
	# 	'''Get the selected edges of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) edge list.		
	# 	'''
	# 	try:
	# 		edges = Slots_max.bitArrayToArray(rt.polyop.getEdgeSelection(obj)) #polygon
	# 	except:
	# 		edges = Slots_max.bitArrayToArray(rt.getEdgeSelection(obj)) #mesh

	# 	return edges


	# @staticmethod
	# def getFaces(obj):
	# 	'''Get the faces of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) facet list.		
	# 	'''
	# 	try:
	# 		faces = list(range(1, rt.polyop.getNumFaces(obj)))
	# 	except:
	# 		faces = list(range(1, obj.faces.count))

	# 	return faces


	# @staticmethod
	# def getSelectedFaces(obj):
	# 	'''Get the selected faces of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) facet list.		
	# 	'''
	# 	try:
	# 		faces = Slots_max.bitArrayToArray(rt.polyop.getFaceSelection(obj)) #polygon
	# 	except:
	# 		faces = Slots_max.bitArrayToArray(rt.getFaceSelection(obj)) #mesh

	# 	return faces




	# @staticmethod
	# def splitNonManifoldVertex(obj, vertex):
	# 	'''
	# 	Separate a connected vertex of non-manifold geometry where the faces share a single vertex.

	# 	:Parameters:
	# 		obj (obj) = A polygon object.
	# 		vertex (int) = A single vertex number of the given polygon object.
	# 	'''
	# 	connected_faces = rt.polyop.getFacesUsingVert(obj, vertex)

	# 	rt.polyop.breakVerts(obj, vertex)

	# 	#get a list for the vertices of each face that is connected to the original vertex.
	# 	verts_sorted_by_face=[]
	# 	for face in Slots_max.bitArrayToArray(connected_faces):
	# 		connected_verts = rt.polyop.getVertsUsingFace(obj, face)
	# 		verts_sorted_by_face.append(Slots_max.bitArrayToArray(connected_verts))


	# 	out=[] #1) take first set A from list. 2) for each other set B in the list do if B has common element(s) with A join B into A; remove B from list. 3) repeat 2. until no more overlap with A. 4) put A into outpup. 5) repeat 1. with rest of list.
	# 	while len(verts_sorted_by_face)>0:
	# 		first, rest = verts_sorted_by_face[0], verts_sorted_by_face[1:] #first, *rest = edges
	# 		first = set(first)

	# 		lf = -1
	# 		while len(first)>lf:
	# 			lf = len(first)

	# 			rest2=[]
	# 			for r in rest:
	# 				if len(first.intersection(set(r)))>0:
	# 					first |= set(r)
	# 				else:
	# 					rest2.append(r)     
	# 			rest = rest2

	# 		out.append(first)
	# 		verts_sorted_by_face = rest


	# 	for vertex_set in out:
	# 		obj.weldThreshold = 0.001
	# 		rt.polyop.weldVertsByThreshold(obj, list(vertex_set))


	# 	rt.polyop.setVertSelection(obj, vertex)



	# def setComboBox(self, comboBox, index):
	# 	'''
	# 	Set the given comboBox's index using a text string.
	# 	:Parameters:
	# 		comboBox (str) = comboBox name (will also be used as the methods name).
	# 		index = int or 'string' - text of the index to switch to.
	# 	'''
	# 	cmb = getattr(self.init_ui, comboBox)
	# 	method = getattr(self, comboBox)
	# 	cmb.currentIndexChanged.connect(method)
	# 	if not type(index)==int:
	# 		index = cmb.findText(index)
	# 	cmb.setCurrentIndex(index)