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



class Init(Slots):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		try:
			self.init_ui.hud.shown.connect(self.construct_hud)
		except AttributeError: #(an inherited class)
			pass


	def construct_hud(self):
		'''Add current scene attributes to a lineEdit.
		Only those with relevant values will be displayed.
		'''
		hud = self.init_ui.hud

		try:
			selection = rt.selection
		except AttributeError:
			selection = None

		if selection:
			if len(selection) is 1:
				obj = selection[0]
				symmetry = obj.modifiers[rt.Symmetry]
				if symmetry:
					int_ = symmetry.axis
					axis = {0:'x', 1:'y', 2:'z'}
					hud.insertText('Symmetry Axis: <font style="color: Yellow;">{}'.format(axis[int_].upper())) #symmetry axis

				level = rt.subObjectLevel if rt.subObjectLevel else 0
				if level==0: #object level
					numberOfSelected = len(selection)
					if numberOfSelected<11:
						name_and_type = ['<font style="color: Yellow;">{0}<font style="color: LightGray;">:{1}'.format(obj.name, rt.classOf(obj.baseObject)) for obj in selection]
						name_and_type_str = str(name_and_type).translate(str.maketrans('', '', ',[]\'')) #format as single string. remove brackets, single quotes, and commas.
					else:
						name_and_type_str = '' #if more than 10 objects selected, don't list each object.
					hud.insertText('Selected: <font style="color: Yellow;">{0}<br/>{1}'.format(numberOfSelected, name_and_type_str)) #currently selected objects by name and type.

				elif level>0: #component level
					obj = selection[0]
					objType = rt.classOf(obj.baseObject)

					if objType==rt.Editable_Poly or objType==rt.Edit_Poly:
						if level==1: #get vertex info
							type_ = 'Verts'
							components = Init.bitArrayToArray(rt.polyop.getVertSelection(obj))
							total_num = rt.polyop.getNumVerts(obj)

						elif level==2: #get edge info
							type_ = 'Edges'
							components = Init.bitArrayToArray(rt.polyop.getEdgeSelection(obj))
							total_num = rt.polyop.getNumEdges(obj)

						elif level==3: #get border info
							type_ = 'Borders'
							# rt.polyop.SetSelection #Edge ((polyOp.getOpenEdges $) as bitarray)
							components = Init.bitArrayToArray(rt.polyop.getBorderSelection(obj))
							total_num = rt.polyop.getNumBorders(obj)

						elif level==4: #get face info
							type_ = 'Faces'
							components = Init.bitArrayToArray(rt.polyop.getFaceSelection(obj))
							total_num = rt.polyop.getNumFaces(obj)

						elif level==5: #get element info
							type_ = 'Elements'
							components = Init.bitArrayToArray(rt.polyop.getElementSelection(obj))
							total_num = rt.polyop.getNumElements(obj)

						try:
							hud.insertText('Selected {}: <font style="color: Yellow;">{} <font style="color: LightGray;">/{}'.format(type_, len(components), total_num)) #selected components
						except NameError:
							pass

		prevCommand = self.tcl.sb.prevCommand(docString=True)
		if prevCommand:
			hud.insertText('Prev Command: <font style="color: Yellow;">{}'.format(prevCommand))  #get button text from last used command

		# prevUi = self.tcl.sb.previousName(omitLevel=[0,1,2])
		# hud.insertText('Prev UI: {}'.format(prevUi.replace('_', '').title())) #get the last level 3 ui name string.

		# prevCamera = self.tcl.sb.prevCamera(docString=True)
		# hud.insertText('Prev Camera: {}'.format(prevCamera)) #get the previously used camera.






	# # ------------------------------------------------
	' DAG Objects'
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
	' Geometry'
	# ------------------------------------------------

	@staticmethod
	def selectLoop(obj):
		'''Select a component loop from two or more selected adjacent components (or a single edge).

		:Parameters:
			obj (obj) = An Editable polygon object.

		ex. obj = rt.selection[0]
			selectLoop(obj)
		'''
		level = rt.subObjectLevel
		if level is 1: #vertex
			obj.convertselection('Vertex',  'Edge', requireAll=True)
			obj.SelectEdgeLoop()
			obj.convertselection('Edge', 'Vertex')

		elif level is 2: #edge
			obj.SelectEdgeLoop()

		elif level is 4: #face
			obj.convertselection('Face', 'Edge', requireAll=True)
			obj.SelectEdgeRing()
			obj.convertselection('Edge', 'Face')

		rt.redrawViews()


	@staticmethod
	def selectRing(obj):
		'''Select a component ring from two or more selected adjacent components (or a single edge).

		:Parameters:
			obj (obj) = An Editable polygon object.

		ex. obj = rt.selection[0]
			selectRing(obj)
		'''
		level = rt.subObjectLevel
		if level is 1: #vertex
			obj.convertselection('Vertex',  'Edge', requireAll=True)
			obj.SelectEdgeRing()
			obj.convertselection('Edge', 'Vertex')

		elif level is 2: #edge
			obj.SelectEdgeRing()

		elif level is 4: #face
			obj.convertselection('Face', 'Edge', requireAll=True)
			obj.SelectEdgeLoop()
			obj.convertselection('Edge', 'Face')

		rt.redrawViews()


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


	@Slots.message
	def detachElement(self, obj):
		'''Detach editable_mesh elements into new objects.

		:Parameters:
			obj (obj) = polygon object.

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


	@property
	def currentSelection(self):
		'''Gets the currently selected objects or object components.

		:Return:
			(array) current selection as a maxscript array.
		'''
		sel = rt.selection
		if not sel:
			return 'Error: Nothing Selected.'

		level = rt.subObjectLevel
		if level in (0, None): #objs
			s = [i for i in sel]
		elif level==1: #verts
			s = Init.getComponents(sel[0], 'vertices', selection=True)
		elif level==2: #edges
			s = Init.getComponents(sel[0], 'edges', selection=True)
		elif level==3: #borders
			s = rt.getBorderSelection(sel[0])
		elif level==4: #faces
			s = Init.getComponents(sel[0], 'faces', selection=True)

		return rt.array(*s) #unpack list s and convert to an array.


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
			result = Init.bitArrayToArray(c)
			if returnType is 'List':
				result = list(result)
		else:
			result = Init.arrayToBitArray(c)

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
			components = Init.getComponents(obj, convertFrom)

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
			result = Init.bitArrayToArray(c)
			if returnType is 'List':
				result = list(result)
		else:
			result = Init.arrayToBitArray(c)

		return result


	@Slots.message
	def alignVertices(self, selection, mode):
		'''Align Vertices

		Align all vertices at once by putting each vert index and coordinates in a dict (or two arrays) then if when iterating through a vert falls within the tolerance specified in a textfield align that vert in coordinate. then repeat the process for the other coordinates x,y,z specified by checkboxes. using edges may be a better approach. or both with a subObjectLevel check
		create edge alignment tool and then use subObjectLevel check to call either that function or this one from the same buttons.
		to save ui space; have a single align button, x, y, z, and align 'all' checkboxes and a tolerance textfield.

		:Parameters:
			selection (list) = vertex selection
			mode (int) = valid values are: 0 (YZ), 1 (XZ), 2 (XY), 3 (X), 4 (Y), 5 (Z)

		notes:
		'vertex.pos.x = vertPosX' ect doesnt work. had to use maxscript
		'''
		# maxEval('undo "alignVertices" on')
		componentArray = selection.selectedVerts
		
		if len(componentArray) == 0:
			return 'Error: No vertices selected.'
		
		if len(componentArray) < 2:
			return 'Error: Selection must contain at least two vertices.'

		lastSelected = componentArray[-1]#3ds max re-orders array by vert index, so this doesnt work for aligning to last selected
		#~ print(lastSelected.pos)
		aX = lastSelected.pos[0]
		aY = lastSelected.pos[1]
		aZ = lastSelected.pos[2]
		
		for vertex in componentArray:
			#~ print(vertex.pos)
			vX = vertex.pos[0]
			vY = vertex.pos[1]
			vZ = vertex.pos[2]

			maxEval('global alignXYZ')
			
			if mode == 0: #align YZ
				maxEval('''
				fn alignXYZ mode vertex vX vY vZ aX aY aZ=
				(
					vertex.pos.x = vX
					vertex.pos.y = aY
					vertex.pos.z = aZ
				)
				''')
				
			if mode == 1: #align XZ
				maxEval('''
				fn alignXYZ mode vertex vX vY vZ aX aY aZ=
				(
					vertex.pos.x = aX
					vertex.pos.y = vY
					vertex.pos.z = aZ
				)
				''')
			
			if mode == 2: #align XY
				maxEval('''
				fn alignXYZ mode vertex vX vY vZ aX aY aZ=
				(
					vertex.pos.x = aX
					vertex.pos.y = aY
					vertex.pos.z = vZ
				)
				''')
			
			if mode == 3: #X
				maxEval('''
				fn alignXYZ mode vertex vX vY vZ aX aY aZ=
				(
					vertex.pos.x = aX
					vertex.pos.y = vY
					vertex.pos.z = vZ
				)
				''')
			
			if mode == 4: #Y
				maxEval('''
				fn alignXYZ mode vertex vX vY vZ aX aY aZ=
				(
					vertex.pos.x = vX
					vertex.pos.y = aY
					vertex.pos.z = vZ
				)
				''')
			
			if mode == 5: #Z
				maxEval('''
				fn alignXYZ mode vertex vX vY vZ aX aY aZ=
				(
					vertex.pos.x = vX
					vertex.pos.y = vY
					vertex.pos.z = aZ
				)
				''')
			
			print(100*"-")
			print("vertex.index:", vertex.index)
			print("position:", vX, vY, vZ)
			print("align:   ", aX, aY, aZ)
			
			rt.alignXYZ(mode, vertex, vX, vY, vZ, aX, aY, aZ)

			return '{0}{1}{2}{3}'.format("result: ", vertex.pos[0], vertex.pos[1], vertex.pos[2])


	@staticmethod
	def scaleObject (size, x, y ,z):
		'''
		:Parameters:
			size (float) = Scale amount
			x (bool) = Scale in the x direction.
			y (bool) = Scale in the y direction.
			z (bool) = Scale in the z direction.

		Basically working except for final 'obj.scale([s, s, s])' command in python. variable definitions included for debugging.
		to get working an option is to use the maxEval method in the alignVertices function.
		'''
		textField_000 = 1.50
		isChecked_002 = True
		isChecked_003 = True
		isChecked_004 = True

		s = textField_000
		x = isChecked_002
		y = isChecked_003
		z = isChecked_004
		#-------------------------
		s = size
		selection = rt.selection

		for obj in selection:
			if (isChecked_002 and isChecked_003 and isChecked_004):
				obj.scale([s, s, s])
			if (not isChecked_002 and isChecked_003 and isChecked_004):
				obj.scale([1, s, s])
			if (isChecked_002 (not isChecked_003) and isChecked_004):
				obj.scale([s, 1, s])
			if (isChecked_002 and isChecked_003 (not isChecked_004)):
				obj.scale([s, s, 1])
			if (not isChecked_002 (not isChecked_003) and isChecked_004):
				obj.scale([1, 1, s])
			if (isChecked_002 (not isChecked_003) (not isChecked_004)):
				obj.scale([s, 1, 1])
			if (isChecked_002 and isChecked_003 and isChecked_004):
				obj.scale([1, s, 1])
			if (not isChecked_002 (not isChecked_003) (not isChecked_004)):
				obj.scale([1, 1, 1])


	@staticmethod
	def compareSize(obj1, obj2, factor):
		'''Compares two point3 sizes from obj bounding boxes.

		:Parameters:
			obj1 (obj) = 
			obj2 (obj) = 
			factor () = 
		'''
		maxEval('''
		s1 = obj1.max - obj1.min --determine bounding boxes
		s2 = obj2.max - obj2.min
		
		if (s2.x >= (s1.x*(1-factor)) AND s2.x <= (s1.x*(1+factor))) OR (s2.x >= (s1.y*(1-factor)) AND s2.x <= (s1.y*(1+factor))) OR (s2.x >= (s1.z*(1-factor)) AND s2.x <= (s1.z*(1+factor)))THEN
			if (s2.y >= (s1.y*(1-factor)) AND s2.y <= (s1.y*(1+factor))) OR (s2.y >= (s1.x*(1-factor)) AND s2.y <= (s1.x*(1+factor))) OR (s2.y >= (s1.z*(1-factor)) AND s2.y <= (s1.z*(1+factor))) THEN
				if (s2.z >= (s1.z*(1-factor)) AND s2.z <= (s1.z*(1+factor))) OR (s2.z >= (s1.x*(1-factor)) AND s2.z <= (s1.x*(1+factor))) OR (s2.z >= (s1.y*(1-factor)) AND s2.z <= (s1.y*(1+factor))) THEN
				(
					dbgSelSim ("  Size match on '" + obj1.name + "' with '" + obj2.name + "'")
					return true
				)
				else return false
			else return false
		else return false			
		''')


	@staticmethod
	def compareMesh(obj1, obj2, factor):
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
	

	@staticmethod
	def compareMats(obj1, obj2):
		'''Compare material names. unlike other properties, this is a simple true/false comparison, it doesn't find 'similar' names.

		:Parameters:
			obj1 (obj) = 
			obj2 (obj) = 
		'''
		maxEval('''
		m1 = obj1.material
		m2 = obj2.material
		
		if m1 != undefined and m2 != undefined then --verify both objects have a material assigned
		(
			if m1.name == m2.name then 
			(
				dbgSelSim ("  Material match on object: '" + obj1.name + "' with '" + obj2.name + "'")
				true	--check if material names are the same, if they are, return a true value
			)
			else false --uh oh. material names aren't the same. return false.
		)
		else false	--one or both objects do not have a material assigned. returning false.
		''')


	#--ExtrudeObject------------------------------------------------------------------------

	#extrudes one object at a time but can be called repeatedly for an array of selected objects
	#takes classString as an argument which is an array containing the object and class information
	#	[0] --object
	#	[1] --baseObject
	#	[4] --baseObject class
	#	[6] --baseObject class type string. eg. Editable,Shape,Geometry
	#notes: in another function; if selection (subobjectlevel) is == face or edge, store that face if necessary in an array and then extrude by a certain amount (if needed surface normal direction). then switch to move tool (calling a center pivot on component if needed) so that the extrude can be manipulated with widget instead of spinner.
	# @staticmethod
	# def extrudeObject (objects):
	# 	if (objects == rt.undefined or objects == "noSelection"):
	# 		print "# Error: Nothing selected. Returned string: noSelection #"
	# 		return "noSelection"

	# 	for obj in objects:
			
	# 		classString = classInfo(obj)
			
	# 		if (classString[6] == "Editable_Poly" or classString[4] == rt.Editable_mesh): #had to add Editable_mesh explicitly, here and in the error catch, because the keyword was unknown to pymxs.runtime. added it to the called function anyhow in case they fix it at some point
	# 			maxEval('macros.run "Modifiers" "Face_Extrude")
	# 			print classString[4]
				
	# 		if (classString[6] == "Shape"):
	# 			#if 'convert to mesh object' checkbox true convert currently selected:
	# 			if (isChecked_000 == True):
	# 				maxEval('''
	# 				convertTo $ PolyMeshObject; --convert to poly
	# 				macros.run "Modifiers" "Face_Extrude"; --extrude modifier
	# 				''')
	# 			else:
	# 				maxEval('macros.run "Modifiers" "Extrude")
	# 			print classString[4]

	# 		if (classString[6] == "Geometry"):
	# 			#if 'convert to mesh object' checkbox true convert currently selected:
	# 			if (isChecked_000 == True):
	# 				maxEval('''
	# 				convertTo $ TriMeshGeometry; --convert to mesh object
	# 				maxEval('macros.run "Modifiers" "Face_Extrude"; --extrude
	# 				''')

	# 		#else, if undefined..
	# 		else:
	# 			print "::unknown object type::"
	# 			print classString[4]

	# 		if (objects.count > 1):
	# 			rt.deselect(classString[0])
			
	# 	if (objects.count > 1): #reselect all initially selected nodes
	# 		rt.clearSelection()
	# 		for obj in objects:
	# 			rt.selectMore(obj)



	#--centerPivotOnSelection----------------------------------------------------------------

	# @staticmethod
	# def centerPivotOnSelection ():

		#Get the face vertices, add their positions together, divide by the number of the vertices 
		#- that's your centerpoint.

		# the above method will get you the average position of the vertices that constitute the 
		#faces in question. For the center of the bounds of these vertices (if that's of interest 
		#to you), you'll need to get the min position and the max position of the vertex set and 
		#then calculate the median position:
		#p3_minPosition + P3_maxPosition / 2 -- The min and the max position values contain the 
		#minimum x, y and z values and the maximum x, y and z values of the vertex set 
		#respectively. That is to say, for example, that the min x value may come from a 
		#different vert than the min y value.

		#component bounding box method:
		#two bits of code written by anubis will need cleaning up, but might be helpful
	# 	(	
	# 	if selection.count == 1 and classOf (curO = selection[1]) == Editable_Poly do
	# 	(
	# 		if (selFacesBA = polyop.getFaceSelection curO).numberset != 0 do
	# 		(
	# 			faceVertsBA = polyop.getVertsUsingFace curO selFacesBA
	# 			with redraw off 
	# 			(
	# 				tMesh = mesh mesh:curO.mesh
	# 				tMesh.pos = curO.pos
	# 				tMesh.objectOffsetPos = curO.objectOffsetPos
	# 				if faceVertsBA.count > 0 do 
	# 				(
	# 					delete tMesh.verts[((tMesh.verts as BitArray) - (faceVertsBA))]
	# 				)
	# 				c = snapshot tMesh
	# 				c.transform = matrix3 1
	# 				d = dummy boxsize:(c.max - c.min)
	# 				delete c
	# 				d.transform = tMesh.transform
	# 				d.pos = tMesh.center
	# 				d.name = tMesh.name + "_box"
	# 				delete tMesh
	# 			)
	# 		)
	# 	)
	# )


	@Slots.message
	def deleteAlongAxis(self, obj, axis):
		'''Delete components of the given mesh object along the specified axis.

		:Parameters:
			obj (obj) = Mesh object.
			axis (str) = Axis to delete on. ie. '-x' Components belonging to the mesh object given in the 'obj' arg, that fall on this axis, will be deleted. 
		'''
		# for node in [n for n in pm.listRelatives(obj, allDescendents=1) if pm.objectType(n, isType='mesh')]: #get any mesh type child nodes of obj.
		# 	faces = self.getAllFacesOnAxis(node, axis)
		# 	if len(faces)==pm.polyEvaluate(node, face=1): #if all faces fall on the specified axis.
		# 		pm.delete(node) #delete entire node
		# 	else:
		# 		pm.delete(faces) #else, delete any individual faces.

		# return 'Delete faces on <hl>'+axis.upper()+'</hl>.'


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
	def convertToEditPoly(prompt=False):
		'''
		:Parameters:
			prompt=bool - prompt user before execution
		'''
		for obj in rt.selection:
			if prompt:
				if not rt.queryBox('Convert Object to Editable Poly?'):
					return
			
			rt.modPanel.setCurrentObject (obj.baseObject)
			
			mod = rt.Edit_Poly()
			rt.modpanel.addModToSelection(mod)

			index = rt.modPanel.getModifierIndex(obj, mod)
			rt.maxOps.CollapseNodeTo(obj, index, False)


	@staticmethod
	def toggleXraySelected():
		''''''
		toggle = Slots.cycle([0,1], 'toggleXraySelected') #toggle 0/1

		for obj in rt.selection:
			obj.xray = toggle


	@staticmethod
	def toggleBackfaceCull():
		''''''
		toggle = Slots.cycle([0,1], 'toggleBackfaceCull') #toggle 0/1

		for obj in rt.Geometry:
			obj.backfacecull = toggle


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
	def displayWireframeOnMesh(state=None, query=False):
		'''
		:Parameters:
			state=bool - display wireframe on mesh in viewport True/False
			query=bool - return current state
		:Return:
			bool (current state) if query
		'''
		graphicsManager = rt.NitrousGraphicsManager.GetActiveViewportSetting()
		currentState = graphicsManager.ShowEdgedFacesEnabled
		if query:
			return currentState
		if state:
			graphicsManager.ShowEdgedFacesEnabled = state
		else:
			graphicsManager.ShowEdgedFacesEnabled = not currentState


	previousSmoothPreviewLevel=int
	@staticmethod
	def toggleSmoothPreview():
		''''''
		global previousSmoothPreviewLevel
		toggle = Slots.cycle([0,1], 'toggleSmoothPreview') #toggle 0/1

		geometry = rt.selection #if there is a selection; perform operation on those object/s
		if not len(geometry): #else: perform operation on all scene geometry.
			geometry = rt.geometry


		if toggle==0: #preview off
			rt.showEndResult = False
			Init.displayWireframeOnMesh(True)

			for obj in geometry:
				try:
					mod = obj.modifiers['TurboSmooth'] or obj.modifiers['TurboSmooth_Pro'] or obj.modifiers['OpenSubDiv']
					mod.iterations = 0 #set subdivision levels to 0.
					obj.showcage = True #Show cage on
				except: pass

		else: #preview on
			rt.showEndResult = True
			Init.displayWireframeOnMesh(False)

			for obj in geometry:
				try:
					mod = obj.modifiers['TurboSmooth'] or obj.modifiers['TurboSmooth_Pro'] or obj.modifiers['OpenSubDiv']
					renderIters = mod.renderIterations #get renderIter value.
					mod.iterations = renderIters #apply to iterations value.
					obj.showcage = False #Show cage off
				except: pass

		rt.redrawViews() #refresh viewport. only those parts of the view that have changed are redrawn.


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
	' Ui'
	# ------------------------------------------------

	@classmethod
	def attr(cls, fn):
		'''Decorator for objAttrWindow.
		'''
		def wrapper(self, *args, **kwargs):
			self.setAttributeWindow(fn(self, *args, **kwargs))
		return wrapper

	def setAttributeWindow(self, obj, include=[], exclude=[], attributes={}):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (obj) = The object to get the attributes of.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']
			attributes (dict) = Explicitly pass in attribute:values pairs.
		'''
		if not obj:
			return

		if isinstance(obj, (list, set, tuple)):
			obj = obj[0]

		if attributes:
			attributes = {k:v for k, v in attributes.items() 
				if not k in exclude and (k in include if include else k not in include)}
		else:
			attributes = self.getAttributesMax(obj, include=include, exclude=exclude)
		children = self.objAttrWindow(obj, attributes, self.setAttributesMax, checkableLabel=True)

		'this is not set up yet for max. currently just outputs the check state for testing.'
		for c in children:
			if c.__class__.__name__=='QCheckBox':
				# c.stateChanged.connect(lambda state, obj=obj, attr=attr: rt.selectMore(prop) if state else rt.deselect(prop))
				c.stateChanged.connect(lambda state, obj=obj, w=c: print('select: '+'{}.{}'.format(obj.name, w.objectName())) if state 
					else print('deselect: '+'{}.{}'.format(obj.name, w.objectName())))
				# if attr in list(rt.selection):
					# c.setChecked(True)


	@Slots.message
	def maxUiSetChecked(self, id, table, item, state=True, query=False):
		'''
		:Parameters:
			id (str) = actionMan ID
			table (int) = actionMan table
			item (int) = actionMan item number
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
print(os.path.splitext(os.path.basename(__file__))[0])
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
	# 		vertices = Init.bitArrayToArray(rt.polyop.getVertSelection(obj)) #polygon
	# 	except:
	# 		vertices = Init.bitArrayToArray(rt.getVertSelection(obj)) #mesh

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
	# 		edges = Init.bitArrayToArray(rt.polyop.getEdgeSelection(obj)) #polygon
	# 	except:
	# 		edges = Init.bitArrayToArray(rt.getEdgeSelection(obj)) #mesh

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
	# 		faces = Init.bitArrayToArray(rt.polyop.getFaceSelection(obj)) #polygon
	# 	except:
	# 		faces = Init.bitArrayToArray(rt.getFaceSelection(obj)) #mesh

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
	# 	for face in Init.bitArrayToArray(connected_faces):
	# 		connected_verts = rt.polyop.getVertsUsingFace(obj, face)
	# 		verts_sorted_by_face.append(Init.bitArrayToArray(connected_verts))


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