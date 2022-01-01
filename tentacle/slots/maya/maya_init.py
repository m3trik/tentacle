# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class Init(Slots_maya):
	'''
	'''
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		try:
			self.init_ui.hud.shown.connect(self.construct_hud)
		except AttributeError: #(an inherited class)
			pass


	def construct_hud(self):
		'''Add current scene attributes to the hud lineEdit.
		Only those with relevant values will be displayed.
		'''
		hud = self.init_ui.hud

		try:
			selection = pm.ls(selection=1)
		except NameError:
			return

		symmetry = pm.symmetricModelling(query=1, symmetry=1);
		if symmetry:
			axis = pm.symmetricModelling(query=1, axis=1)
			hud.insertText('Symmetry Axis: <font style="color: Yellow;">{}'.format(axis.upper())) #symmetry axis

		xformConstraint = pm.xformConstraint(query=True, type=True)
		if xformConstraint=='none':
			xformConstraint=None
		if xformConstraint:
			hud.insertText('Xform Constrait: <font style="color: Yellow;">{}'.format(xformConstraint)) #transform constraits

		if selection:
			if pm.selectMode(query=1, object=1): #object mode:
				if pm.selectType(query=1, allObjects=1): #get object/s

					selectedObjects = pm.ls(selection=1)#, objectsOnly=1)
					numberOfSelected = len(selectedObjects)
					if numberOfSelected<11:
						name_and_type = ['<font style="color: Yellow;">{0}<font style="color: LightGray;">:{1}<br/>'.format(i.name(), pm.objectType(i)) for i in selectedObjects] #ie. ['pCube1:transform', 'pSphere1:transform']
						name_and_type_str = str(name_and_type).translate(str.maketrans('', '', ',[]\'')) #format as single string. remove brackets, single quotes, and commas.
					else:
						name_and_type_str = '' #if more than 10 objects selected, don't list each object.
					hud.insertText('Selected: <font style="color: Yellow;">{0}<br/>{1}'.format(numberOfSelected, name_and_type_str)) #currently selected objects by name and type.

					objectFaces = pm.polyEvaluate(selectedObjects, face=True)
					if type(objectFaces)==int:
						hud.insertText('Faces: <font style="color: Yellow;">{}'.format(objectFaces, ',d')) #add commas each 3 decimal places.

					objectTris = pm.polyEvaluate(selectedObjects, triangle=True)
					if type(objectTris)==int:
						hud.insertText('Tris: <font style="color: Yellow;">{}'.format(objectTris, ',d')) #add commas each 3 decimal places.

					objectUVs = pm.polyEvaluate(selectedObjects, uvcoord=True)
					if type(objectUVs)==int:
						hud.insertText('UVs: <font style="color: Yellow;">{}'.format(objectUVs, ',d')) #add commas each 3 decimal places.

			elif pm.selectMode(query=1, component=1): #component mode:
				if pm.selectType(query=1, vertex=1): #get vertex selection info
					type_ = 'Verts'
					num_selected = pm.polyEvaluate(vertexComponent=1)
					total_num = pm.polyEvaluate(selection, vertex=1)

				elif pm.selectType(query=1, edge=1): #get edge selection info
					type_ = 'Edges'
					num_selected = pm.polyEvaluate(edgeComponent=1)
					total_num = pm.polyEvaluate(selection, edge=1)

				elif pm.selectType(query=1, facet=1): #get face selection info
					type_ = 'Faces'
					num_selected = pm.polyEvaluate(faceComponent=1)
					total_num = pm.polyEvaluate(selection, face=1)

				elif pm.selectType(query=1, polymeshUV=1): #get uv selection info
					type_ = 'UVs'
					num_selected = pm.polyEvaluate(uvComponent=1)
					total_num = pm.polyEvaluate(selection, uvcoord=1)

				try:
					hud.insertText('Selected {}: <font style="color: Yellow;">{} <font style="color: LightGray;">/{}'.format(type_, num_selected, total_num)) #selected components
				except NameError:
					pass


		prevCommand = self.tcl.sb.prevCommand(docString=True)
		if prevCommand:
			hud.insertText('Prev Command: <font style="color: Yellow;">{}'.format(prevCommand))  #get button text from last used command

		# prevUi = self.tcl.sb.prevUiName(omitLevel=[0,1,2])
		# hud.insertText('Prev UI: {}'.format(prevUi.replace('_', '').title())) #get the last level 3 ui name string.

		# prevCamera = self.tcl.sb.prevCamera(docString=True)
		# hud.insertText('Prev Camera: {}'.format(prevCamera)) #get the previously used camera.









#module name
print (__name__)
# ======================================================================
# Notes
# ======================================================================





#deprecated -------------------------------------


# def getBorderFacesOfFaces(faces, includeBordered=False):
# 	'''
# 	Get any faces attached to the given faces.

# 	:Parameters:
# 		faces (unicode, str, list) = faces to get bordering faces for.
# 		includeBordered (bool) = optional. return the bordered face along with the results.

# 	:Return:
# 		list - the border faces of the given faces.
# 	'''
# 	adjEdges = pm.polyListComponentConversion(faces, fromFace=1, toEdge=1)
# 	adjFaces = pm.polyListComponentConversion(adjEdges, toFace=1, fromEdge=1)
# 	expanded = pm.filterExpand(adjFaces, expand=True, selectionMask=34) #keep faces as individual elements.

# 	if includeBordered:
# 		return list(str(f) for f in expanded) #convert unicode to str.
# 	else:
# 		return list(str(f) for f in expanded if f not in faces) #convert unicode to str and exclude the original faces.



	# def getComponents(objects, type_, flatten=True):
	# 	'''
	# 	Get the components of the given type from the given object.

	# 	:Parameters:
	# 		objects (obj)(list) = The polygonal object(s) to get the components of.
	# 		flatten (bool) = Flattens the returned list of objects so that each component is identified individually. (much faster)

	# 	:Return:
	# 		(list) component objects.
	# 	'''
	# 	if isinstance(objects, (str, unicode)):
	# 		objects = pm.ls(objects)

	# 	if not isinstance(objects, (list, set, tuple)):
	# 		objects=[objects]

	# 	types = {'vertices':'vtx', 'edges':'e', 'faces':'f'}

	# 	components=[]
	# 	for obj in objects:
	# 		cmpts = pm.ls('{}.{}[*]'.format(obj, types[type_]), flatten=flatten)
	# 		components+=cmpts

	# 	return components


	# @staticmethod
	# def getSelectedComponents(componentType, objects=None, returnType=str):
	# 	'''
	# 	Get the component selection of the given type.

	# 	:Parameters:
	# 		componentType (str) = The desired component type. (valid values are: 'vertices', 'edges', 'faces')
	# 		objects (obj)(list) = If polygonal object(s) are given, then only selected components from those object(s) will be returned.
	# 		returnType (str) = Desired output style.
	# 				ex. str (default) = [u'test_cube:pCube1.vtx[0]']
	# 					int = {nt.Mesh(u'test_cube:pCube1Shape'): set([0])}
	# 					object = [MeshVertex(u'test_cube:pCube1Shape.vtx[0]')]

	# 	:Return:
	# 		(list)(dict) components (based on given 'componentType' and 'returnType' value).
	# 	'''
	# 	types = {'vertices':31, 'edges':32, 'faces':34}

	# 	if objects:
	# 		selection = pm.ls(objects, sl=1)
	# 		components = pm.filterExpand(selection, selectionMask=types[componentType])
	# 	else:
	# 		components = pm.filterExpand(selectionMask=types[componentType])


	# 	if returnType==str:
	# 		selectedComponents = components

	# 	if returnType==int:
	# 		selectedComponents={}
	# 		for c in components:
	# 			obj = pm.ls(c, objectsOnly=1)[0]
	# 			componentNum = int(c.split('[')[-1].rstrip(']'))

	# 			if obj in selectedComponents:
	# 				selectedComponents[obj].add(componentNum)
	# 			else:
	# 				selectedComponents[obj] = {componentNum}

	# 	if returnType==object:
	# 		attrs = {'vertices':'vtx', 'edges':'e', 'faces':'f'}
	# 		selectedComponents = [getattr(pm.ls(c, objectsOnly=1)[0], attrs[componentType])[n] for n, c in enumerate(components)] if components else []


	# 	return selectedComponents


# @staticmethod
# 	def getUvShellSets(objects=None):
# 		'''
# 		Get All UV shells and their corresponding sets of faces.

# 		:Parameters:
# 			objects (obj)(list) = Polygon object(s).

# 		:Return:
# 			(dict) ex. {0L:[[MeshFace(u'pShape.f[0]'), MeshFace(u'pShape.f[1]')], 1L:[[MeshFace(u'pShape.f[2]'), MeshFace(u'pShape.f[3]')]}
# 		'''
# 		if not objects:
# 			objects = pm.ls(selection=1, objectsOnly=1, transforms=1, flatten=1)

# 		if not isinstance(objects, (list, set, tuple)):
# 			objects=[objects]

# 		shells={}
# 		for obj in objects:
# 			faces = Init.getComponents(obj, 'f')
# 			for face in faces:
# 				shell_Id = pm.polyEvaluate(face, uvShellIds=True)

# 				try:
# 					shells[shell_Id[0]].append(face)
# 				except KeyError:
# 					try:
# 						shells[shell_Id[0]]=[face]
# 					except IndexError:
# 						pass

# 		return shells



# @staticmethod
# 	def getSelectedComponents(type_, obj=None):
# 		'''
# 		Get the component selection of the given type.

# 		:Parameters:
# 			obj (obj) = If a polygonal object is given, then only selected components from that object will be returned.

# 		:Return:
# 			(list) component objects.
# 		'''
# 		types = {'vertices':31, 'edges':32, 'faces':34}

# 		if obj:
# 			components = pm.filterExpand(pm.ls(obj, sl=1), selectionMask=types[type_])
# 		else:
# 			components = pm.filterExpand(selectionMask=types[type_])

# 		selectedComponents = [c.split('[')[-1].rstrip(']') for c in components] if components else []

# 		return selectedComponents

# def getClosestVerts(set1, set2, tolerance=100):
# 		'''
# 		Find the two closest vertices between the two sets of vertices.

# 		:Parameters:
# 			set1 (list) = The first set of vertices.
# 			set2 (list) = The second set of vertices.
# 			tolerance (int) = Maximum search distance.

# 		:Return:
# 			(list) closest vertex pair (<vertex from set1>, <vertex from set2>).
# 		'''
# 		closestDistance=tolerance
# 		closestVerts=None
# 		for v1 in set1:
# 			v1Pos = pm.pointPosition(v1, world=1)
# 			for v2 in set2:
# 				v2Pos = pm.pointPosition(v2, world=1)
# 				distance = Init.getDistanceBetweenTwoPoints(v1Pos, v2Pos)

# 				if distance < closestDistance:
# 					closestDistance = distance
# 					if closestDistance < tolerance:
# 						closestVerts = [v1, v2]

# 		return closestVerts


	# @staticmethod
	# def shortestEdgePath():
	# 	'''
	# 	Select shortest edge path between (two or more) selected edges.
	# 	'''
	# 	#:Return: list of lists. each containing an edge paths components
	# 	selectTypeEdge = pm.filterExpand (selectionMask=32) #returns True if selectionMask=Edges
	# 	if (selectTypeEdge): #if selection is polygon edges, convert to vertices.
	# 		mel.eval("PolySelectConvert 3;")
	# 	selection=pm.ls (selection=1, flatten=1)

	# 	vertList=[]

	# 	for objName in selection:
	# 		objName = str(objName) #ex. "polyShape.vtx[176]"
	# 		index1 = objName.find("[")
	# 		index2 = objName.find("]")
	# 		vertNum = objName[index1+1:index2] #ex. "176"
	# 		# position = pm.pointPosition(objName) 
	# 		object_ = objName[:index1-4] #ex. "polyShape"
	# 		# print(object_, index1, index2#, position)
	# 		vertList.append(vertNum)

	# 	if (selectTypeEdge):
	# 		pm.selectType (edge=True)

	# 	paths=[]
	# 	for index in range(3): #get edge path between vertList[0],[1] [1],[2] [2],[3] to make sure everything is selected between the original four vertices/two edges
	# 		edgePath = pm.polySelect(object_, shortestEdgePath=(int(vertList[index]), int(vertList[index+1])))
	# 		paths.append(edgePath)

	# 	return paths



	# def snapToClosestVertex(vertices, obj, tolerance=0.125):
	# 	'''
	# 	This Function Snaps Vertices To Onto The Reference Object.

	# 	:Parameters:
	# 		obj (str) = The object to snap to.
	# 		vertices (list) = The vertices to snap.
	# 		tolerance (float) = Max distance.
	# 	'''
	# 	Init.loadPlugin('nearestPointOnMesh')
	# 	nearestPointOnMeshNode = mel.eval('{} {}'.format('nearestPointOnMesh', obj))
	# 	pm.delete(nearestPointOnMeshNode)

	# 	pm.undoInfo(openChunk=True)
	# 	for vertex in vertices:

	# 		vertexPosition = pm.pointPosition(vertex, world=True)
	# 		pm.setAttr('{}.inPosition'.format(nearestPointOnMeshNode), vertexPosition[0], vertexPosition[1], vertexPosition[2])
	# 		associatedFaceId = pm.getAttr('{}.nearestFaceIndex'.format(nearestPointOnMeshNode))
	# 		vtxsFaces = pm.filterExpand(pm.polyListComponentConversion('{0}.f[{1}]'.format(obj, associatedFaceId), fromFace=True,  toVertexFace=True), sm=70, expand=True)

	# 		closestDistance = 2**32-1

	# 		closestPosition=[]
	# 		for vtxsFace in vtxsFaces:
	# 			associatedVtx = pm.polyListComponentConversion(vtxsFace, fromVertexFace=True, toVertex=True)
	# 			associatedVtxPosition = pm.pointPosition(associatedVtx, world=True)
				
	# 			distance = Init.getDistanceBetweenTwoPoints(vertexPosition, associatedVtxPosition)

	# 			if distance<closestDistance:
	# 				closestDistance = distance
	# 				closestPosition = associatedVtxPosition
				
	# 			if closestDistance<tolerance:
	# 				pm.move(closestPosition[0], closestPosition[1], closestPosition[2], vertex, worldSpace=True)

	# 	# pm.delete(nearestPointOnMeshNode)
	# 	pm.undoInfo(closeChunk=True)








# def getContigiousIslands(faces, faceIslands=[]):
# 	'''
# 	Get a list containing sets of adjacent polygon faces grouped by islands.
# 	:Parameters:
# 		faces (list) = polygon faces to be filtered for adjacent.
# 		faceIslands (list) = optional. list of sets. ability to add faces from previous calls to the return value.
# 	:Return:
# 		list of sets of adjacent faces.
# 	'''
# 	face=None
# 	faces = list(str(f) for f in faces) #work on a copy of the argument so that removal of elements doesn't effect the passed in list.
# 	prevFaces=[]

# 	for _ in range(len(faces)):
# 		# print ''
# 		if not face:
# 			try:
# 				face = faces[0]
# 				island=set([face])
# 			except:
# 				break

# 		adjFaces = [f for f in Init.getBorderComponents(face) if not f in prevFaces and f in faces]
# 		prevFaces.append(face)
# 		# print '-face     ','   *',face
# 		# print '-adjFaces ','  **',adjFaces
# 		# print '-prevFaces','    ',prevFaces

# 		try: #add face to current island if it hasn't already been added, and is one of the faces specified by the faces argument.
# 			island.add(adjFaces[0])
# 			face = adjFaces[0]

# 		except: #if there are no adjacent faces, start a new island set.
# 			faceIslands.append(island)
# 			face = None
# 			# print '-island   ','   $',island
# 			# print '\n',40*'-'
# 		faces.remove(prevFaces[-1])

# 	return faceIslands