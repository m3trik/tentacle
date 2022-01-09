# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtGui, QtWidgets, QtCore

try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as OpenMayaUI

	import shiboken2

except ImportError as error:
	print(__file__, error)

from slots import Slots



class Slots_maya(Slots):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		Slots.__init__(self, *args, **kwargs)


	@staticmethod
	def loadPlugin(plugin):
		'''Loads A Plugin.
		
		:Parameters:
			plugin (str) = The desired plugin to load.

		ex. loadPlugin('nearestPointOnMesh')
		'''
		not pm.pluginInfo(plugin, query=True, loaded=True) and pm.loadPlugin(plugin)


	def undoChunk(fn):
		'''A decorator to place a function into Maya's undo chunk.
		Prevents the undo queue from breaking entirely if an exception is raised within the given function.

		:Parameters:
			fn (obj) = The decorated python function that will be placed into the undo que as a single entry.
		'''
		def wrapper(*args, **kwargs):
			pm.undoInfo(openChunk=True)
			rtn = fn(*args, **kwargs)
			pm.undoInfo(closeChunk=True)
			return rtn
		return wrapper

	# ----------------------------------------------------------------------









	# ======================================================================
		'MATH'
	# ======================================================================

	def getVectorFromComponents(components):
		'''Get a vector using the averaged vertex normals of the given components.

		:Parameters:
			components (list) = A list of component to get normals of.

		:Return:
			(vector) ex. [-4.5296159711938344e-08, 1.0, 1.6846732009412335e-08]
		'''
		vertices = pm.polyListComponentConversion(components, toVertex=1)

		norm = pm.polyNormalPerVertex(vertices, query=True, xyz=True)
		normal_vector = [sum(norm[0::3])/len(norm[0::3]), sum(norm[1::3])/len(norm[1::3]), sum(norm[2::3])/len(norm[2::3])] #averaging of all x,y,z points.

		return normal_vector

	# ----------------------------------------------------------------------









	# ======================================================================
		'COMPONENT LEVEL'
	# ======================================================================

	@staticmethod
	def convertComponentName(componentType, returnType='abv'):
		'''Return an alternate component alias for the given alias. ie. a hex value of 0x0001 for 'vertex'
		If nothing is found, a value of 'None' will be returned.

		:Parameters:
			componentType (str) = Component type as a string.
			returnType (str) = The desired returned alias. (valid: 'abv', 'singular', 'plural', 'full', 'int', 'hex')

		:Return:
			(str)(int)(hex)(None) dependant on returnType argument.

		ex. call: convertComponentName('control vertex', 'hex')
		'''
		rtypes = ('abv', 'singular', 'plural', 'full', 'int', 'hex')
		types = [
			('vtx', 'vertex', 'vertices', 'Polygon Vertex', 31, 0x0001),
			('e', 'edge', 'edges', 'Polygon Edge', 32, 0x8000),
			('f', 'face', 'faces', 'Polygon Face', 34, 0x0008),
			('cv', 'control vertex', 'control vertices', 'Control Vertex', 28, 0x0010),
			('uv', 'texture', 'texture coordinates', 'Polygon UV', 35, 0x0010),
		]

		result = None
		for t in types:
			if componentType in t:
				index = rtypes.index(returnType)
				result = t[index]
				break

		return result


	@staticmethod
	def convertType(objects, returnType='str', returnNodeType='shape', flatten=False):
		'''Convert objects to/from <obj>, 'strings', integers.

		:Parameters:
			objects (str)(obj)(list) = The object(s) to convert.
			returnType (str) = The desired returned object type. (valid: 'str', 'obj', 'int') ('int' valid only at sub-object level).
			returnNodeType (str) = Specify whether objects are returned with transform or shape nodes (valid only with str returnTypes). (valid: 'transform', 'shape'(default)) ex. 'pCylinder1.f[0]' or 'pCylinderShape1.f[0]'
			flatten (bool) = Flattens the returned list of objects so that each component is identified individually.

		:Return:
			(list)(dict) Dependant on flags.

		ex. call: Slots_maya.convertType(<edges>, 'str', flatten=True) #returns a list of string object names from a list of edge objects.
		'''
		if returnType=='str':
			objects = pm.ls(objects, flatten=flatten)
			result = [str(c) for c in objects]

			if returnNodeType=='transform':
				result = [str(''.join(c.rsplit('Shape', 1))) for c in result]


		elif returnType=='obj':
			result = pm.ls(objects, flatten=flatten)

		else: #returnType=='int':
			result={}
			for c in pm.ls(objects, flatten=True):
				obj = pm.ls(c, objectsOnly=1)[0]
				num = c.split('[')[-1].rstrip(']')

				try:
					if flatten:
						componentNum = int(num)
					else:
						n = [int(n) for n in num.split(':')]
						componentNum = tuple(n) if len(n)>1 else n[0]

					if obj in result: #append to existing object key.
						result[obj].append(componentNum)
					else:
						result[obj] = [componentNum]
				except ValueError as error: #incompatible object type.
					break; print ('# Error: {}.convertType(): unable to convert {} {} to int. {}. #'.format(__name__, obj, num, error)) 

		return result


	@staticmethod
	def getComponents(objects=None, componentType=None, returnType='str', returnNodeType='shape', selection=False, flatten=False):
		'''Get the components of the given type.

		:Parameters:
			objects (str)(obj)(list) = The object(s) to get the components of.
			componentType (str)(int) = The desired component mask. (valid: any type allowed in the 'convertComponentName' method)
			returnType (str) = The desired returned object type. (valid: 'str', 'obj', 'int')
			returnNodeType (str) = Specify whether the components are returned with the transform or shape nodes (valid only with str returnTypes). (valid: 'transform', 'shape'(default)) ex. 'pCylinder1.f[0]' or 'pCylinderShape1.f[0]'
			selection (bool) = Filter to currently selected objects.
			flatten (bool) = Flattens the returned list of objects so that each component is identified individually.

		:Return:
			(list)(dict) Dependant on flags.

		ex. getComponents(objects, 'faces' returnType='object')
		'''
		if not componentType: #get component type from the current selection.
			if selection:
				o = pm.ls(sl=1)
				t = Slots_maya.getObjectType(o)
				componentType = Slots_maya.convertComponentName(t, returnType='full')
				if not componentType: #get all components of the given objects.
					all_components = [Slots_maya.getComponents(objects, typ) for typ in ('vtx', 'e', 'f', 'cv')]
					return all_components
			else:
				return
		else: #get the correct componentType variable from possible args.
			componentType = Slots_maya.convertComponentName(componentType, returnType='abv')

		mask = Slots_maya.convertComponentName(componentType, returnType='int')
		components=[]

		if selection:
			if objects:
				transforms = pm.ls(objects, sl=1, transforms=1)
				if transforms: #get ALL selected components, FILTERING for those of the given transform object(s).
					selected_shapes=[]
					for obj in transforms:
						selected_shapes+=pm.ls('{}.{}[*]'.format(obj, componentType), flatten=flatten)
				else: #get selected components, FILTERING for those of the given tranform object(s).
					shapes = Slots_maya.getShapeNode(objects)
					selected_shapes = pm.ls(shapes, sl=1)
				components = pm.filterExpand(selected_shapes, selectionMask=mask, expand=flatten)
			else:
				transforms = pm.ls(sl=1, transforms=1)
				if transforms:
					for obj in transforms: #get ALL selected components, for each selected transform object.
						components+=pm.ls('{}.{}[*]'.format(obj, componentType), flatten=flatten)
				else: #get selected components.
					components = pm.filterExpand(selectionMask=mask, expand=flatten)
		else:
			for obj in pm.ls(objects):
				components+=pm.ls('{}.{}[*]'.format(obj, componentType), flatten=flatten)

		if not components:
			components=[]

		result = Slots_maya.convertType(components, returnType=returnType, returnNodeType=returnNodeType, flatten=flatten)

		return result


	@staticmethod
	def getRandomComponents(objects, componentType='vertex', randomRatio=0.5, returnType='unicode', flatten=False):
		'''Get a list of random components from the given object(s) using maya's polySelectConstraint.

		:Parameters:
			objects (str)(list)(obj) = The object(s) to get random components of.
			componentType (str)(int) = The desired component mask. (valid: 'vtx','vertex','vertices','Polygon Vertex',31,0x0001(vertices), 'e','edge','edges','Polygon Edge',32,0x8000(edges), 'f','face','faces','Polygon Face',34,0x0008(faces), 'uv','texture','texture coordinates','Polygon UV',35,0x0010(texture coordiantes).
			randomRatio (float) = Randomize amount in range 0-1.
			returnType (str) = The desired returned object type. (valid: 'unicode'(default), 'str', 'int', 'object')
			flatten (bool) = Flattens the returned list of objects so that each component is identified individually.

		:Return:
			(list) Polygon components.
		'''
		componentType = Slots_maya.convertComponentName(componentType, returnType='hex')

		orig_selection = pm.ls(sl=1) #get currently selected objects in order to re-select them after the contraint operation.

		pm.polySelectConstraint(mode=3, type=componentType, random=True, randomratio=randomRatio)

		if componentType==0x0001:
			pm.selectType(polymeshVertex=True)
		elif componentType==0x8000:
			pm.selectType(polymeshEdge=True)
		elif componentType==0x0008:
			pm.selectType(polymeshFace=True)
		else:
			pm.selectType(polymeshUV=True) #pm.selectType(texture=True)

		result = Slots_maya.getComponents(objects, selection=1, returnType=returnType, flatten=flatten)

		pm.polySelectConstraint(random=False) # turn off the random constraint
		pm.select(orig_selection) #re-select any originally selected objects.

		return result


	@staticmethod
	def getContigiousEdges(edges):
		'''Get a list containing sets of adjacent edges.

		:Parameters:
			edges (list) = Polygon edges to be filtered for adjacent.

		:Return:
			(list) adjacent edge sets.
		'''
		sets=[]
		edges = pm.ls(edges, flatten=1)
		for edge in edges:
			vertices = pm.polyListComponentConversion(edge, fromEdge=1, toVertex=1)
			connEdges = pm.polyListComponentConversion(vertices, fromVertex=1, toEdge=1)
			edge_set = set([e for e in pm.ls(connEdges, flatten=1) if e in edges]) #restrict the connected edges to the original edge pool.
			sets.append(edge_set)

		result=[]
		while len(sets)>0: #combine sets in 'sets' that share common elements.
			first, rest = sets[0], sets[1:] #python 3: first, *rest = sets
			first = set(first)

			lf = -1
			while len(first)>lf:
				lf = len(first)

				rest2 = []
				for r in rest:
					if len(first.intersection(set(r)))>0:
						first |= set(r)
					else:
						rest2.append(r)     
				rest = rest2

			result.append(first)
			sets = rest

		return result


	@staticmethod
	def getContigiousIslands(faces, faceIslands=[]):
		'''Get a list containing sets of adjacent polygon faces grouped by islands.

		:Parameters:
			faces (list) = Polygon faces to be filtered for adjacent.
			faceIslands (list) = optional. list of sets. ability to add faces from previous calls to the return value.

		:Return:
			(list) of sets of adjacent faces.
		'''
		sets=[]
		faces = pm.ls(faces, flatten=1)
		for face in faces:
			edges = pm.polyListComponentConversion(face, fromFace=1, toEdge=1)
			borderFaces = pm.ls(pm.polyListComponentConversion(edges, fromEdge=1, toFace=1), flatten=1)
			set_ = set([str(f) for f in borderFaces if f in faces])
			if set_:
				sets.append(set_)

		while len(sets)>0: #combine sets in 'sets' that share common elements.
			first, rest = sets[0], sets[1:] #python 3: first, *rest = sets
			first = set(first)

			lf = -1
			while len(first)>lf:
				lf = len(first)

				rest2 = []
				for r in rest:
					if len(first.intersection(set(r)))>0:
						first |= set(r)
					else:
						rest2.append(r)     
				rest = rest2

			faceIslands.append(first)
			sets = rest

		return faceIslands


	@staticmethod
	def getBorderComponents(x, returnCompType='default', borderType='object', returnType='str', flatten=False):
		'''Get any object border components from given component(s) or a polygon object.

		:Parameters:
			x (obj)(list) = Component(s) (or a polygon object) to find any border components for.
			returnCompType (str) = The desired returned component type. (valid: 'vertices','edges','faces','default'(the returnCompType will be the same as the given component type, or edges if an object is given))
			borderType (str) = Get the components that border given components, or components on the border of an object. (valid: 'component', 'object'(default))
			returnType (str) = Return objects or string names of the components. (valid: 'str', 'obj')
			flatten (bool) = Flattens the returned list of objects so that each component is identified individually.

		:Return:
			(list)

		ex. borderVertices = getBorderComponents(selection, returnCompType='vertices', borderType='component', flatten=True)
		'''
		x = pm.ls(x)
		if not x:
			print ('# Error: Operation requires an selected object or components. #')
			return []

		object_type = Slots_maya.getObjectType(x[0])
		if object_type=='Polygon':
			x = Slots_maya.getComponents(x, 'edges')
		elif object_type=='Polygon Vertex':
			x = pm.polyListComponentConversion(x, fromVertex=1, toEdge=1)
		elif object_type=='Polygon Face':
			x = pm.polyListComponentConversion(x, fromFace=1, toEdge=1)

		result=[]
		edges = pm.ls(x, flatten=1)

		if borderType is 'object': #get edges that form the border of the object.
			for edge in edges:
				attachedFaces = pm.ls(pm.polyListComponentConversion(edge, fromEdge=1, toFace=1), flatten=1)
				if len(attachedFaces)==1:
					result.append(edge)

		elif borderType is 'component' and not object_type=='Polygon': #get edges that form the border of the given components.
			for edge in edges:
				attachedFaces = pm.polyListComponentConversion(edge, fromEdge=1, toFace=1)
				attachedEdges = pm.ls(pm.polyListComponentConversion(attachedFaces, fromFace=1, toEdge=1), flatten=1)
				for e in attachedEdges:
					if e not in edges:
						result.append(edge)
						break

		if returnCompType=='default': #if no returnCompType is specified, return the same type of component as given. in the case of 'Polygon' object, edges will be returned.
			returnCompType = object_type if not object_type=='Polygon' else 'Polygon Edge'
		#convert back to the original component type and flatten /un-flatten list.
		if returnCompType in ('Polygon Vertex', 'vertices', 'vertex', 'vtx'):
			result = pm.ls(pm.polyListComponentConversion(result, fromEdge=1, toVertex=1), flatten=flatten) #vertices.
		elif returnCompType in ('Polygon Edge', 'edges', 'edge', 'e'):
			result = pm.ls(pm.polyListComponentConversion(result, fromEdge=1, toEdge=1), flatten=flatten) #edges.
		elif returnCompType in ('Polygon Face', 'faces', 'face', 'f'):
			result = pm.ls(pm.polyListComponentConversion(result, fromEdge=1, toFace=1), flatten=flatten) #faces.

		if returnType=='str':
			result = [str(i) for i in result]

		return result


	@staticmethod
	def getClosestVerts(set1, set2, tolerance=100):
		'''Find the two closest vertices between the two sets of vertices.

		:Parameters:
			set1 (str)(list) = The first set of vertices.
			set2 (str)(list) = The second set of vertices.
			tolerance (int) = Maximum search distance.

		:Return:
			(list) closest vertex pairs by order of distance (excluding those not meeting the tolerance). (<vertex from set1>, <vertex from set2>).

		ex. verts1 = Slots_maya.getComponents('pCube1', 'vertices')
			verts2 = Slots_maya.getComponents(pCube2', 'vertices')
			closestVerts = getClosestVerts(verts1, verts2)
		'''
		set1 = [str(i) for i in pm.ls(set1, flatten=1)]
		set2 = [str(i) for i in pm.ls(set2, flatten=1)]
		vertPairsAndDistance={}
		for v1 in set1:
			v1Pos = pm.pointPosition(v1, world=1)
			for v2 in set2:
				v2Pos = pm.pointPosition(v2, world=1)
				distance = Slots.getDistanceBetweenTwoPoints(v1Pos, v2Pos)
				if distance<tolerance:
					vertPairsAndDistance[(v1, v2)] = distance

		import operator
		sorted_ = sorted(vertPairsAndDistance.items(), key=operator.itemgetter(1))

		vertPairs = [i[0] for i in sorted_]

		return vertPairs


	@staticmethod
	@undoChunk
	def getClosestVertex(vertices, obj, tolerance=0.0, freezeTransforms=False):
		'''Find the closest vertex of the given object for each vertex in the list of given vertices.

		:Parameters:
			vertices (list) = A set of vertices.
			obj (obj) = The reference object in which to find the closest vertex for each vertex in the list of given vertices.
			tolerance (float) = Maximum search distance. Default is 0.0, which turns off the tolerance flag.
			freezeTransforms (bool) = Reset the selected transform and all of its children down to the shape level.

		:Return:
			(dict) closest vertex pairs {<vertex from set1>:<vertex from set2>}.

		ex. obj1, obj2 = selection
			vertices = Slots_maya.getComponents(obj1, 'vertices')
			closestVerts = getClosestVertex(vertices, obj2, tolerance=10)
		'''
		vertices = [str(i) for i in pm.ls(vertices, flatten=1)]
		# pm.undoInfo(openChunk=True)
		if freezeTransforms:
			pm.makeIdentity(obj, apply=True)

		obj2Shape = pm.listRelatives(obj, children=1, shapes=1)[0] #pm.listRelatives(obj, fullPath=False, shapes=True, noIntermediate=True)

		cpmNode = pm.ls(pm.createNode('closestPointOnMesh'))[0] #create a closestPointOnMesh node.
		pm.connectAttr(obj2Shape.outMesh, cpmNode.inMesh, force=1) #object's shape mesh output to the cpm node.

		closestVerts={}
		for v1 in vertices: #assure the list of vertices is a flattened list of stings. prevent unhashable type error when closestVerts[v1] = v2.  may not be needed with python versions 3.8+
			v1Pos = pm.pointPosition(v1, world=True)
			pm.setAttr(cpmNode.inPosition, v1Pos[0], v1Pos[1], v1Pos[2], type="double3") #set a compound attribute

			index = pm.getAttr(cpmNode.closestVertexIndex) #vertex Index. | ie. result: [34]
			v2 = obj2Shape.vtx[index]

			v2Pos = pm.pointPosition(v2, world=True)
			distance = Slots.getDistanceBetweenTwoPoints(v1Pos, v2Pos)

			if not tolerance:
				closestVerts[v1] = v2
			elif distance < tolerance:
				closestVerts[v1] = v2

		pm.delete(cpmNode)
		# pm.undoInfo(closeChunk=True)

		return closestVerts


	@staticmethod
	def getEdgePath(components, returnType='edgeLoop'):
		'''Query the polySelect command for the components along different edge paths.
		Supports components from a single object.

		:Parameters:
			components (str)(obj)(list) = The components used for the query (dependant on the operation type).
			returnType (str) = The desired return type. 'shortestEdgePath', 'edgeRing', 'edgeRingPath', 'edgeLoop', 'edgeLoopPath'.

		:Return:
			(list) The components comprising the path.
		'''
		obj = set(pm.ls(components, objectsOnly=1, flatten=1))[0]

		result=[]
		componentNumbers = list(Slots_maya.convertType(components, returnType='int', flatten=1).values())[0] #get the vertex numbers as integer values. ie. [818, 1380]

		if returnType=='shortestEdgePath':
			edgesLong = pm.polySelect(obj, query=1, shortestEdgePath=(componentNumbers[0], componentNumbers[1])) #(vtx, vtx)

		elif returnType=='edgeRing':
			edgesLong = pm.polySelect(obj, query=1, edgeRing=componentNumbers) #(e..)

		elif returnType=='edgeRingPath':
			edgesLong = pm.polySelect(obj, query=1, edgeRingPath=(componentNumbers[0], componentNumbers[1])) #(e, e)

		elif returnType=='edgeLoop':
			edgesLong = pm.polySelect(obj, query=1, edgeLoop=componentNumbers) #(e..)

		elif returnType=='edgeLoopPath':
			edgesLong = pm.polySelect(obj, query=1, edgeLoopPath=(componentNumbers[0], componentNumbers[1])) #(e, e)

		if not edgesLong:
			print('# Error: Unable to find edge path: {}. #'.format(obj))

		[result.append('{}.e[{}]'.format(obj.name(), int(edge))) for edge in edgesLong]

		return result


	@staticmethod
	def getShortestPath(components=None):
		'''Get the shortest path between to vertices or edges.

		:Parameters:
			components (obj) = A Pair of vertices or edges.

		:Return:
			(list) the components that comprise the path as strings.
		'''
		type_ = Slots_maya.getObjectType(components[0])
		
		result=[]
		objects = set(pm.ls(components, objectsOnly=1))
		for obj in objects:

			if type_=='Polygon Edge':
				components = [pm.ls(pm.polyListComponentConversion(e, fromEdge=1, toVertex=1), flatten=1) for e in components]
				try:
					closestVerts = Slots_maya.getClosestVerts(components[0], components[1])[0]
				except IndexError as error:
					print ('# Error: Operation requires exactly two selected edges. #')
					return
				edges = Slots_maya.getEdgePath(closestVerts, 'shortestEdgePath')
				[result.append(e) for e in edges]

			elif type_=='Polygon Vertex':
				closestVerts = Slots_maya.getClosestVerts(components[0], components[1])[0]
				edges = Slots_maya.getEdgePath(closestVerts, 'shortestEdgePath')
				vertices = pm.ls(pm.polyListComponentConversion(edges, fromEdge=1, toVertex=1), flatten=1)
				[result.append(v) for v in vertices]

		return result


	@staticmethod
	def getPathAlongLoop(components=None):
		'''Get the shortest path between to vertices or edges along an edgeloop.

		:Parameters:
			components (obj) = A Pair of vertices, edges, or faces.

		:Return:
			(list) the components that comprise the path as strings.
		'''
		type_ = Slots_maya.getObjectType(components[0])
		
		result=[]
		objects = set(pm.ls(components, objectsOnly=1))
		for obj in objects:

			if type_=='Polygon Vertex':
				vertices=[]
				for component in components:
					edges = pm.ls(pm.polyListComponentConversion(component, fromVertex=1, toEdge=1), flatten=1)
					_vertices = pm.ls(pm.polyListComponentConversion(edges, fromEdge=1, toVertex=1), flatten=1)
					vertices.append(_vertices)

				closestVerts = Slots_maya.getClosestVerts(vertices[0], vertices[1])[0]
				_edges = pm.ls(pm.polyListComponentConversion(list(components)+list(closestVerts), fromVertex=1, toEdge=1), flatten=1)

				edges=[]
				for edge in _edges:
					verts = pm.ls(pm.polyListComponentConversion(edge, fromEdge=1, toVertex=1), flatten=1)
					if closestVerts[0] in verts and components[0] in verts or closestVerts[1] in verts and components[1] in verts:
						edges.append(edge)

				edges = Slots_maya.getEdgePath(edges, 'edgeLoopPath')

				vertices = [pm.ls(pm.polyListComponentConversion(edges, fromEdge=1, toVertex=1), flatten=1)]
				[result.append(v) for v in vertices]


			elif type_=='Polygon Edge':
				edges = Slots_maya.getEdgePath(components, 'edgeLoopPath')
				[result.append(e) for e in edges]


			elif type_=='Polygon Face':
				vertices=[]
				for component in components:
					edges = pm.ls(pm.polyListComponentConversion(component, fromFace=1, toEdge=1), flatten=1)
					_vertices = pm.ls(pm.polyListComponentConversion(edges, fromEdge=1, toVertex=1), flatten=1)
					vertices.append(_vertices)

				closestVerts1 = Slots_maya.getClosestVerts(vertices[0], vertices[1])[0]
				closestVerts2 = Slots_maya.getClosestVerts(vertices[0], vertices[1])[1] #get the next pair of closest verts

				_edges = pm.ls(pm.polyListComponentConversion(closestVerts1+closestVerts2, fromVertex=1, toEdge=1), flatten=1)
				edges=[]
				for edge in _edges:
					verts = pm.ls(pm.polyListComponentConversion(edge, fromEdge=1, toVertex=1), flatten=1)
					if closestVerts1[0] in verts and closestVerts2[0] in verts or closestVerts1[1] in verts and closestVerts2[1] in verts:
						edges.append(edge)

				edges = Slots_maya.getEdgePath(edges, 'edgeRingPath')

				faces = pm.ls(pm.polyListComponentConversion(edges, fromEdge=1, toFace=1), flatten=1)
				[result.append(f) for f in faces]

		return result


	@staticmethod
	def getEdgesByNormalAngle(objects, lowAngle=50, highAngle=130, returnType='str', flatten=False):
		'''Get a list of edges having normals between the given high and low angles using maya's polySelectConstraint.

		:Parameters:
			objects (str)(list)(obj) = The object(s) to get edges of.
			lowAngle (int) = Normal angle low range.
			highAngle (int) = Normal angle high range.
			returnType (str) = The desired returned object type. (valid: 'unicode'(default), 'str', 'int', 'object')
			flatten (bool) = Flattens the returned list of objects so that each component is identified individually.

		:Return:
			(list) Polygon edges.
		'''
		orig_selection = pm.ls(sl=1) #get currently selected objects in order to re-select them after the contraint operation.

		pm.polySelectConstraint(angle=True, anglebound=(lowAngle, highAngle), mode=3, type=0x8000) #Constrain that selection to only edges of a certain Angle
		pm.selectType(polymeshEdge=True)
		edges = Slots_maya.getComponents(objects, 'edges', selection=1, returnType=returnType, flatten=flatten)

		pm.polySelectConstraint(mode=0) #Remove the selection constraint.
		pm.select(orig_selection) #re-select any originally selected objects.

		return edges


	@staticmethod
	def getComponentsByNumberOfConnected(components, num_of_connected=(0,2), connectedType=None, returnType='str', flatten=False):
		'''Get a list of components filtered by the number of their connected components.

		:Parameters:
			components (str)(list)(obj) = The components to filter.
			num_of_connected (int)(tuple) = The number of connected components. Can be given as a range. (Default: (0,2))
			connectedType (str)(int) = The desired component mask. (valid: 'vtx','vertex','vertices','Polygon Vertex',31,0x0001(vertices), 'e','edge','edges','Polygon Edge',32,0x8000(edges), 'f','face','faces','Polygon Face',34,0x0008(faces), 'uv','texture','texture coordinates','Polygon UV',35,0x0010(texture coordiantes).
			returnType (str) = The desired returned object type. (valid: 'unicode'(default), 'str', 'int', 'object')
			flatten (bool) = Flattens the returned list of objects so that each component is identified individually.

		:Return:
			(list) Polygon vertices.

		ex. components = Slots_maya.getComponents(objects, 'faces', selection=1)
			faces = getComponentsByNumberOfConnected(components, 4, 'Polygon Edge') #returns faces with four connected edges (four sided faces).

		ex. components = Slots_maya.getComponents(objects, 'vertices', selection=1)
			verts = getComponentsByNumberOfConnected(components, (0,2), 'Polygon Edge') #returns vertices with up to two connected edges.
		'''
		if connectedType in ('vtx', 'vertex', 'vertices', 'Polygon Vertex', 31, 0x0001):
			connectedType = 'Polygon Vertex'
		elif connectedType in ('e', 'edge', 'edges', 'Polygon Edge', 32, 0x8000):
			connectedType = 'Polygon Edge'
		elif connectedType in ('f', 'face', 'faces', 'Polygon Face', 34, 0x0008):
			connectedType = 'Polygon Face'

		if isinstance(num_of_connected, (tuple, list, set)):
			lowRange, highRange = num_of_connected
		else:
			lowRange = highRange = num_of_connected

		component_type = Slots_maya.getObjectType(components)
		if not connectedType:
			connectedType = component_type

		result=[]
		for c in pm.ls(components, flatten=1):
			fm = {'Polygon Vertex':'fromVertex', 'Polygon Edge':'fromEdge', 'Polygon Face':'fromFace'}
			to = {'Polygon Vertex':'toVertex', 'Polygon Edge':'toEdge', 'Polygon Face':'toFace'}
			kwargs = {'fromVertex':False, 'fromEdge':False, 'fromFace':False, 'toVertex':False, 'toEdge':False, 'toFace':False}

			kwargs[fm[component_type]] = True #ex. kwargs['fromVertex'] = True
			kwargs[to[connectedType]] = True #ex. kwargs['toEdge'] = True

			num = len(pm.ls(pm.polyListComponentConversion(c, **kwargs), flatten=1))
			if num>=lowRange and num<=highRange:
				result.append(c)

		return result

	# ----------------------------------------------------------------------









	# ======================================================================
		'OBJECT LEVEL'
	# ======================================================================

	@staticmethod
	def getMelGlobals(keyword=None, caseSensitive=False):
		'''Get global MEL variables.

		:Parameters:
			keyword (str) = search string.

		:Return:
			(list)
		'''
		variables = [
			v for v in sorted(mel.eval('env')) 
				if not keyword 
					or (v.count(keyword) if caseSensitive else v.lower().count(keyword.lower()))
		]

		return variables


	@staticmethod
	def getObjectType(obj, returnType='objectType'):
		'''Get the type of a given object.

		:Parameters:
			obj (obj) = A single maya component.
			returnType (str) = Specify the desired return value type. 'mask' will return the maya mask value as an integer. (valid: 'objectType', 'mask')(default: 'objectType')

		:Return:
			(str)(int) matching type from the types dict.
		'''
		types = {0:'Handle', 9:'Nurbs Curve', 10:'Nurbs Surfaces', 11:'Nurbs Curves On Surface', 12:'Polygon', 22:'Locator XYZ', 23:'Orientation Locator', 
			24:'Locator UV', 28:'Control Vertex', 30:'Edit Point', 31:'Polygon Vertex', 32:'Polygon Edge', 34:'Polygon Face', 35:'Polygon UV', 36:'Subdivision Mesh Point', 
			37:'Subdivision Mesh Edge', 38:'Subdivision Mesh Face', 39:'Curve Parameter Point', 40:'Curve Knot', 41:'Surface Parameter Point', 42:'Surface Knot', 
			43:'Surface Range', 44:'Trim Surface Edge', 45:'Surface Isoparm', 46:'Lattice Point', 47:'Particle', 49:'Scale Pivot', 50:'Rotate Pivot', 51:'Select Handle', 
			68:'Subdivision Surface', 70:'Polygon Vertex Face', 72:'NURBS Surface Face', 73:'Subdivision Mesh UV'}

		for k, v in types.items():
			if pm.filterExpand(obj, sm=k):
				return v if returnType=='objectType' else k


	@staticmethod
	def getObjectFromComponent(components, returnType='transform'):
		'''Get the object's transform, shape, or history node from the given components.

		:Parameters:
			components (str)(obj(list) = Component(s).
			returnType (str) = The desired returned node type. (valid: 'transform','shape','history')(default: 'transform')

		:Return:
			(dict) {transform node: [components of that node]}
			ie. {'pCube2': ['pCube2.f[21]', 'pCube2.f[22]', 'pCube2.f[25]'], 'pCube1': ['pCube1.f[21]', 'pCube1.f[26]']}
		'''
		if not isinstance(components,(list, tuple, set)):
			components = [components]

		result={}
		for component in components:
			shapeNode = pm.listRelatives(component, parent=1)[0] #set(pm.ls(components, transform=1))
			transform = pm.listRelatives(shapeNode, parent=1)[0] #set(pm.ls(components, shape=1))

			if returnType=='transform':
				node = transform
			elif returnType=='shape':
				node = shapeNode
			elif returnType=='history':
				history = pm.listConnections(shapeNode, source=1, destination=0)[0] #get incoming connections: returns list ie. [nt.PolyCone('polyCone1')]
				node = history

			try:
				result[node].append(component)
			except:
				result[node] = [component]

		return result


	@staticmethod
	def isGroup(node):
		'''Check if the given node is a group.
		'''
		for child in node.getChildren():
			if type(child) is not pm.nodetypes.Transform:
				return False
		return True


	@staticmethod
	def getTransformNode(node, attributes=False, regEx=''):
		'''Get the transform node(s).

		:Parameters:
			node (obj) = A relative of a transform Node.
			attributes (bool) = Return the attributes of the node, rather then the node itself.
			regEx (str) = List only the attributes that match the string(s) passed from this flag. String can be a regular expression.

		:Return:
			(list) node(s) or node attributes.
		'''
		transforms = pm.ls(node, type='transform')
		if not transforms: #from shape
			shapeNodes = pm.ls(node, objectsOnly=1)
			transforms = pm.listRelatives(shapeNodes, parent=1)
			if not transforms: #from history
				try:
					print ('getTransformNode: node:', node)
					transforms = pm.listRelatives(pm.listHistory(node, future=1), parent=1)
				except Exception as error:
					transforms = []

		if attributes:
			transforms = pm.listAttr(transforms, read=1, hasData=1, string=regEx)

		return list(set(transforms))


	@staticmethod
	def getShapeNode(node=None, attributes=False, regEx=''):
		'''Get the shape node(s).

		:Parameters:
			node (obj) = A relative of a shape Node.
			attributes (bool) = Return the attributes of the node, rather then the node itself.
			regEx (str) = 	List only the attributes that match the string(s) passed from this flag. String can be a regular expression.

		:Return:
			(list) node(s) or node attributes.
		'''
		shapes = pm.listRelatives(node, children=1, shapes=1) #get shape node from transform: returns list ie. [nt.Mesh('pConeShape1')]
		if not shapes:
			shapes = pm.ls(node, type='shape')
			if not shapes: #get shape from transform
				try:
					transforms = pm.listRelatives(pm.listHistory(node, future=1), parent=1)
					shapes = Slots_maya.getShapeNode(transforms)
				except Exception as error:
					shapes = []

		if attributes:
			shapes = pm.listAttr(shapes, read=1, hasData=1, string=regEx)

		return list(set(shapes))


	@staticmethod
	def getHistoryNode(node=None, attributes=False, regEx=''):
		'''Get the history node(s).

		:Parameters:
			node (obj) = A relative of a history Node.
			attributes (bool) = Return the attributes of the node, rather then the node itself.
			regEx (str) = 	List only the attributes that match the string(s) passed from this flag. String can be a regular expression.

		:Return:
			(list) node(s) or node attributes.
		'''
		shapes = pm.listRelatives(node, children=1, shapes=1) #get shape node from transform: returns list ie. [nt.Mesh('pConeShape1')]
		connections = pm.listConnections(shapes, source=1, destination=0) #get incoming connections: returns list ie. [nt.PolyCone('polyCone1')]
		if not connections:
			try:
				connections = node.history()[-1]
			except AttributeError as error:
				print ('error:', error)
				connections = [] #object has no attribute 'history'

		if attributes:
			connections = pm.listAttr(connections, read=1, hasData=1, string=regEx)

		return connections


	@staticmethod
	def getAllParents(node):
		'''List ALL parents of an object
		'''
		objects = pm.ls(node, l=1)
		tokens=[]

		return objects[0].split("|")

	# ----------------------------------------------------------------------









	# ======================================================================
		'ATTRIBUTES:'
	# ======================================================================

	@staticmethod
	def getParameterValuesMEL(node, cmd, parameters):
		'''Query a Maya command, and return a key(the parameter):value pair for each of the given parameters.

		:Parameters:
			node (str)(obj)(list) = The object to query attributes of.
			parameters (list) = The command parameters to query. ie. ['enableTranslationX','translationX']

		:Return:
			(dict) {'parameter name':<value>} ie. {'enableTranslationX': [False, False], 'translationX': [-1.0, 1.0]}

		ex. call: attrs = getParameterValuesMEL(obj, 'transformLimits', ['enableTranslationX','translationX'])
		'''
		cmd = getattr(pm, cmd)
		node = pm.ls(node)[0]

		result={}
		for p in parameters:
			values = cmd(node, **{'q':True, p:True}) #query the parameter to get it's value.

			# for n, i in enumerate(values): #convert True|False to 1|0
			# 	if i==True:
			# 		values[n] = 1
			# 	elif i==False:
			# 		values[n] = 0

			result[p] = values

		return result


	@staticmethod
	def setParameterValuesMEL(node, cmd, parameters):
		'''Set parameters using a maya command.

		:Parameters:
			node (str)(obj)(list) = The object to query attributes of.
			parameters (dict) = The command's parameters and their desired values. ie. {'enableTranslationX': [False, False], 'translationX': [-1.0, 1.0]}

		ex. call: setParameterValuesMEL(obj, 'transformLimits', {'enableTranslationX': [False, False], 'translationX': [-1.0, 1.0]})
		'''
		cmd = getattr(pm, cmd)
		node = pm.ls(node)[0]

		for p, v in parameters.items():
		 	cmd(node, **{p:v})


	@staticmethod
	def getAttributesMEL(node, include=[], exclude=[]):
		'''Get node attributes and their corresponding values as a dict.

		:Parameters:
			node (obj) = The node to get attributes for.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']

		:Return:
			(dict) {'string attribute': current value}
		'''
		if not all((include, exclude)):
			exclude = ['message', 'caching', 'frozen', 'isHistoricallyInteresting', 'nodeState', 'binMembership', 'output', 'edgeIdMap', 'miterAlong', 'axis', 'axisX', 'axisY', 
				'axisZ', 'paramWarn', 'uvSetName', 'createUVs', 'texture', 'maya70', 'inputPolymesh', 'maya2017Update1', 'manipMatrix', 'inMeshCache', 'faceIdMap', 'subdivideNgons', 
				'useOldPolyArchitecture', 'inputComponents', 'vertexIdMap', 'binMembership', 'maya2015', 'cacheInput', 'inputMatrix', 'forceParallel', 'autoFit', 'maya2016SP3', 
				'maya2017', 'caching', 'output', 'useInputComp', 'worldSpace', 'taperCurve_Position', 'taperCurve_FloatValue', 'taperCurve_Interp', 'componentTagCreate', 
				'isCollapsed', 'blackBox', 'viewMode', 'templateVersion', 'uiTreatment', 'boundingBoxMinX', 'boundingBoxMinY', 'boundingBoxMinZ', 'boundingBoxMaxX', 'boundingBoxMaxY', 
				'boundingBoxMaxZ', 'boundingBoxSizeX', 'boundingBoxSizeY', 'boundingBoxSizeZ', 'boundingBoxCenterX', 'boundingBoxCenterY', 'boundingBoxCenterZ', 'visibility', 
				'intermediateObject', 'template', 'objectColorR', 'objectColorG', 'objectColorB', 'wireColorR', 'wireColorG', 'wireColorB', 'useObjectColor', 'objectColor', 
				'overrideDisplayType', 'overrideLevelOfDetail', 'overrideShading', 'overrideTexturing', 'overridePlayback', 'overrideEnabled', 'overrideVisibility', 'hideOnPlayback', 
				'overrideRGBColors', 'overrideColor', 'overrideColorR', 'overrideColorG', 'overrideColorB', 'lodVisibility', 'selectionChildHighlighting', 'identification', 
				'layerRenderable', 'layerOverrideColor', 'ghosting', 'ghostingMode', 'ghostPreFrames', 'ghostPostFrames', 'ghostStep', 'ghostFarOpacity', 'ghostNearOpacity', 
				'ghostColorPreR', 'ghostColorPreG', 'ghostColorPreB', 'ghostColorPostR', 'ghostColorPostG', 'ghostColorPostB', 'ghostUseDriver', 'hiddenInOutliner', 'useOutlinerColor', 
				'outlinerColorR', 'outlinerColorG', 'outlinerColorB', 'renderType', 'renderVolume', 'visibleFraction', 'hardwareFogMultiplier', 'motionBlur', 'visibleInReflections', 
				'visibleInRefractions', 'castsShadows', 'receiveShadows', 'asBackground', 'maxVisibilitySamplesOverrider', 'maxVisibilitySamples', 'geometryAntialiasingOverride', 
				'antialiasingLevel', 'shadingSamplesOverride', 'shadingSamples', 'maxShadingSamples','volumeSamplesOverride', 'volumeSamples', 'depthJitter', 'IgnoreSelfShadowing', 
				'primaryVisibility', 'tweak', 'relativeTweak', 'uvPivotX', 'uvPivotY', 'displayImmediate', 'displayColors', 'ignoreHwShader', 'holdOut', 'smoothShading', 
				'boundingBoxScaleX', 'boundingBoxScaleY', 'boundingBoxScaleZ', 'featureDisplacement', 'randomSeed', 'compId', 'weight', 'gravityX', 'gravityY', 'gravityZ', 'attraction', 
				'magnX', 'magnY', 'magnZ', 'maya2012', 'maya2018', 'newThickness', 'compBoundingBoxMinX', 'compBoundingBoxMinY', 'compBoundingBoxMinZ', 'compBoundingBoxMaxX', 
				'compBoundingBoxMaxY', 'compBoundingBoxMaxZ', 'hyperLayout', 'borderConnections', 'isHierarchicalConnection', 'rmbCommand', 'templateName', 'templatePath', 'viewName', 
				'iconName', 'customTreatment', 'creator', 'creationDate', 'containerType', 'boundingBoxMin', 'boundingBoxMax', 'boundingBoxSize', 'matrix', 'inverseMatrix', 'worldMatrix', 
				'worldInverseMatrix', 'parentMatrix', 'parentInverseMatrix', 'instObjGroups', 'wireColorRGB', 'drawOverride', 'overrideColorRGB', 'renderInfo', 'ghostCustomSteps', 
				'ghostsStep', 'ghostFrames', 'ghostOpacityRange', 'ghostColorPre', 'ghostColorPost', 'ghostDriver', 'outlinerColor', 'shadowRays', 'rayDepthLimit', 'centerOfIllumination', 
				'pointCamera', 'pointCameraX', 'pointCameraY', 'pointCameraZ', 'matrixWorldToEye', 'matrixEyeToWorld', 'objectId', 'primitiveId', 'raySampler', 'rayDepth', 'renderState', 
				'locatorScale', 'uvCoord', 'uCoord', 'vCoord', 'uvFilterSize', 'uvFilterSizeX', 'uvFilterSizeY', 'infoBits', 'lightData', 'lightDirectionX', 'lightDirectionY', 'lightDirectionZ', 
				'lightIntensityR', 'lightIntensityG', 'lightIntensityB', 'lightShadowFraction', 'preShadowIntensity', 'lightBlindData', 'opticalFXvisibility', 'opticalFXvisibilityR', 
				'opticalFXvisibilityG', 'opticalFXvisibilityB', 'rayInstance', 'ambientShade', 'objectType', 'shadowRadius', 'castSoftShadows', 'normalCamera', 'normalCameraX', 'normalCameraY', 
				'normalCameraZ', 'color', 'shadowColor', 'decayRate', 'emitDiffuse', 'emitSpecular', 'lightRadius', 'reuseDmap', 'useMidDistDmap', 'dmapFilterSize', 'dmapResolution', 
				'dmapFocus', 'dmapWidthFocus', 'useDmapAutoFocus', 'volumeShadowSamples', 'fogShadowIntensity', 'useDmapAutoClipping', 'dmapNearClipPlane', 'dmapFarClipPlane', 
				'useOnlySingleDmap', 'useXPlusDmap', 'useXMinusDmap', 'useYPlusDmap', 'useYMinusDmap', 'useZPlusDmap', 'useZMinusDmap', 'dmapUseMacro', 'dmapName', 'dmapLightName', 
				'dmapSceneName', 'dmapFrameExt', 'writeDmap', 'lastWrittenDmapAnimExtName', 'useLightPosition', 'lightAngle', 'pointWorld', 'pointWorldX', 'pointWorldY', 'pointWorldZ', 

			]
		# print('node:', node); print('attr:', pm.listAttr(node))
		attributes={} 
		for attr in pm.listAttr(node):
			if not attr in exclude and (attr in include if include else attr not in include): #ie. pm.getAttr('polyCube1.subdivisionsDepth')
				try:
					attributes[attr] = pm.getAttr(getattr(node, attr), silent=True) #get the attribute's value.
				except Exception as error:
					print (error)

		return attributes


	@staticmethod
	def setAttributesMEL(node, attributes):
		'''Set node attribute values using a dict.

		:Parameters:
			node (obj) = The node to set attributes for.
			attributes (dict) = Attributes and their correponding value to set. ie. {'string attribute': value}

		ex call:
		self.setAttributesMEL(obj, {'smoothLevel':1})
		'''
		[pm.setAttr(getattr(node, attr), value)
			for attr, value in attributes.items() 
				if attr and value] #ie. pm.setAttr('polyCube1.subdivisionsDepth', 5)


	@staticmethod
	def connectAttributes(attr, place, file):
		'''A convenience procedure for connecting common attributes between two nodes.

		:Parameters:
			attr () = 
			place () = 
			file () = 

		// Use convenience command to connect attributes which share 
		// their names for both the placement and file nodes.
		self.connectAttributes('coverage', 'place2d', fileNode')
		self.connectAttributes('translateFrame', 'place2d', fileNode')
		self.connectAttributes('rotateFrame', 'place2d', fileNode')
		self.connectAttributes('mirror', 'place2d', fileNode')
		self.connectAttributes('stagger', 'place2d', fileNode')
		self.connectAttributes('wrap', 'place2d', fileNode')
		self.connectAttributes('wrapV', 'place2d', fileNode')
		self.connectAttributes('repeatUV', 'place2d', fileNode')
		self.connectAttributes('offset', 'place2d', fileNode')
		self.connectAttributes('rotateUV', 'place2d', fileNode')

		// These two are named differently.
		connectAttr -f ( $place2d + ".outUV" ) ( $fileNode + ".uv" );
		connectAttr -f ( $place2d + ".outUvFilterSize" ) ( $fileNode + ".uvFilterSize" );
		'''
		pm.connectAttr((place + "." + attr), (file + "." + attr), f=1)

	# ----------------------------------------------------------------------









	# ======================================================================
		'UI'
	# ======================================================================

	@staticmethod
	def getSelectedChannels():
		'''Get any attributes (channels) that are selected in the channel box.

		:Return:
			(str) list of any selected attributes as strings. (ie. ['tx', ry', 'sz'])
		'''
		channelBox = mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;') #fetch maya's main channelbox
		attrs = pm.channelBox(channelBox, q=True, sma=True)

		if attrs is None:
			attrs=[]
		return attrs


	@staticmethod
	def getMayaMainWindow():
		'''Get the main Maya window as a QtWidgets.QMainWindow instance

		:Return:
			QtGui.QMainWindow instance of the top level Maya windows
		'''
		ptr = OpenMayaUI.MQtUtil.mainWindow()
		if ptr:
			return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)


	@staticmethod
	def getPanel(*args, **kwargs):
		'''Returns panel and panel configuration information.
		A fix for broken pymel class.

		:Parameters:
			[allConfigs=boolean], [allPanels=boolean], [allScriptedTypes=boolean], [allTypes=boolean], [configWithLabel=string], [containing=string], [invisiblePanels=boolean], [scriptType=string], [type=string], [typeOf=string], [underPointer=boolean], [visiblePanels=boolean], [withFocus=boolean], [withLabel=string])

		:Return:
			(str) An array of panel names.
		'''
		from maya.cmds import getPanel #pymel getPanel is broken in ver: 2022.

		result = getPanel(*args, **kwargs)

		return result


	@staticmethod
	def convertToWidget(name):
		'''
		:Parameters:
			name (str) = name of a Maya UI element of any type. ex. name = mel.eval('$tmp=$gAttributeEditorForm') (from MEL global variable)

		:Return:
			(QWidget) If the object does not exist, returns None
		'''
		for f in ('findControl', 'findLayout', 'findMenuItem'):
			ptr = getattr(OpenMayaUI.MQtUtil, f)(name) #equivalent to: ex. OpenMayaUI.MQtUtil.findControl(name)
			if ptr:
				return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)


	@classmethod
	def attr(cls, fn):
		'''A decorator for setAttributeWindow (objAttrWindow).
		'''
		def wrapper(self, *args, **kwargs):
			self.setAttributeWindow(fn(self, *args, **kwargs))
		return wrapper

	def setAttributeWindow(self, obj, attributes={}, include=[], exclude=[], checkableLabel=False, fn=None, fn_args=[]):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (str)(obj)(list) = The object to get the attributes of, or it's name. If given as a list, only the first index will be used.
			attributes (dict) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from self.getAttributesMax for the given obj.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']
			checkableLabel (bool) = Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. fn(obj, {'attr':<value>})
			fn_args (list) = Any additonal args to pass to fn.
				The first parameter of fn is always the given object, and the last parameter is the attribute:value pairs as a dict.

		ex. call: self.setAttributeWindow(node, attrs, fn=Slots_maya.setParameterValuesMEL, fn_args='transformLimits') #set attributes for the Maya command transformLimits.
		ex. call: self.setAttributeWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)
		'''
		try:
			obj = pm.ls(obj)[0]
		except Exception as error:
			return 'Error: {}.setAttributeWindow: Invalid Object: {}'.format(__name__, obj)

		fn = fn if fn else self.setAttributesMEL

		if attributes:
			attributes = {k:v for k, v in attributes.items() 
				if not k in exclude and (k in include if include else k not in include)}
		else:
			attributes = self.getAttributesMEL(obj, include=include, exclude=exclude)

		menu = self.objAttrWindow(obj, attributes, checkableLabel=checkableLabel, fn=fn, fn_args=fn_args)

		if checkableLabel:
			for c in menu.childWidgets:
				if c.__class__.__name__=='QCheckBox':
					attr = getattr(obj, c.objectName())
					c.stateChanged.connect(lambda state, obj=obj, attr=attr: pm.select(attr, deselect=not state, add=1))
					if attr in pm.ls(sl=1):
						c.setChecked(True)


	@staticmethod
	def mainProgressBar(size, name="progressBar_", stepAmount=1):
		'''#add esc key pressed return False

		:Parameters:
			size (int) = total amount
			name (str) = name of progress bar created
			stepAmount(int) = increment amount

		example use-case:
		mainProgressBar (len(edges), progressCount)
			pm.progressBar ("progressBar_", edit=1, step=1)
			if pm.progressBar ("progressBar_", query=1, isCancelled=1):
				break
		pm.progressBar ("progressBar_", edit=1, endProgress=1)

		to use main progressBar: name=string $gMainProgressBar
		'''
		status = "processing: "+str(size)+"."
		edit=0
		if pm.progressBar(name, exists=1):
			edit=1
		pm.progressBar(name, edit=edit,
						beginProgress=1,
						isInterruptable=True,
						status=status,
						maxValue=size,
						step=stepAmount)


	@staticmethod
	def mainProgressBar(gMainProgressBar, numFaces, count):
		''''''
		num=str(numFaces)
		status="iterating through " + num + " faces"
		pm.progressBar(gMainProgressBar, 
			edit=1, 
			status=status, 
			isInterruptable=True, 
			maxValue=count, 
			beginProgress=1)


	@staticmethod
	def viewPortMessage(message='', statusMessage='', assistMessage='', position='topCenter'):
		'''
		:Parameters:
			message (str) = The message to be displayed, (accepts html formatting). General message, inherited by -amg/assistMessage and -smg/statusMessage.
			statusMessage (str) = The status info message to be displayed (accepts html formatting).
			assistMessage (str) = The user assistance message to be displayed, (accepts html formatting).
			position (str) = position on screen. possible values are: topCenter","topRight","midLeft","midCenter","midCenterTop","midCenterBot","midRight","botLeft","botCenter","botRight"

		ex. viewPortMessage("shutting down:<hl>"+str(timer)+"</hl>")
		'''
		fontSize=10
		fade=1
		fadeInTime=0
		fadeStayTime=1000
		fadeOutTime=500
		alpha=75

		if message:
			pm.inViewMessage(message=message, position=position, fontSize=fontSize, fade=fade, fadeInTime=fadeInTime, fadeStayTime=fadeStayTime, fadeOutTime=fadeOutTime, alpha=alpha) #1000ms = 1 sec
		elif statusMessage:
			pm.inViewMessage(statusMessage=statusMessage, position=position, fontSize=fontSize, fade=fade, fadeInTime=fadeInTime, fadeStayTime=fadeStayTime, fadeOutTime=fadeOutTime, alpha=alpha) #1000ms = 1 sec
		elif assistMessage:
			pm.inViewMessage(assistMessage=assistMessage, position=position, fontSize=fontSize, fade=fade, fadeInTime=fadeInTime, fadeStayTime=fadeStayTime, fadeOutTime=fadeOutTime, alpha=alpha) #1000ms = 1 sec


	@staticmethod
	def outputText (text, window_title):
		'''output text
		'''
		#window_title = mel.eval(python("window_title"))
		window = str(pm.window(	widthHeight=(300, 300), 
								topLeftCorner=(65,265),
								maximizeButton=False,
								resizeToFitChildren=True,
								toolbox=True,
								title=window_title))
		scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
										horizontalScrollBarThickness=16))
		pm.columnLayout(adjustableColumn=True)
		text_field = str(pm.text(label=text, align='left'))
		print(text_field)
		pm.setParent('..')
		pm.showWindow(window)
		return

	# #output textfield parsed by ';'
	# def outputTextField2(text):
	# 	window = str(pm.window(	widthHeight=(250, 650), 
	# 							topLeftCorner=(50,275),
	# 							maximizeButton=False,
	# 							resizeToFitChildren=False,
	# 							toolbox=True,
	# 							title=""))
	# 	scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
	# 									horizontalScrollBarThickness=16))
	# 	pm.columnLayout(adjustableColumn=True)
	# 	print(text)
	# 	#for item in array:
	# 	text_field = str(pm.textField(height=20,
	# 										width=250, 
	# 										editable=False,
	# 										insertText=str(text)))
	# 	pm.setParent('..')
	# 	pm.showWindow(window)
	# 	return


	@staticmethod
	def outputscrollField (text, window_title, width, height):
		'''Create an output scroll layout.
		'''
		window_width  = width  * 300
		window_height = height * 600
		scroll_width  = width  * 294
		scroll_height = height * 590
		window = str(pm.window(	widthHeight=(window_width, window_height),
								topLeftCorner=(45, 0),
								maximizeButton=False,
								sizeable=False,
								title=window_title
								))
		scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
										horizontalScrollBarThickness=16))
		pm.columnLayout(adjustableColumn=True)
		text_field = str(pm.scrollField(text=(text),
										width=scroll_width,
										height=scroll_height,))
		print(window)
		pm.setParent('..')
		pm.showWindow(window)
		return


	@staticmethod
	def outputTextField (array, window_title):
		'''Create an output text field.
		'''
		window = str(pm.window(	widthHeight=(250, 650), 
								topLeftCorner=(65,275),
								maximizeButton=False,
								resizeToFitChildren=False,
								toolbox=True,
								title=window_title))
		scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
										horizontalScrollBarThickness=16))
		pm.columnLayout(adjustableColumn=True)
		for item in array:
			text_field = str(pm.textField(height=20,
											width=500, 
											editable=False,
											insertText=str(item)))
		pm.setParent('..')
		pm.showWindow(window)
		return

	# ----------------------------------------------------------------------









	# ======================================================================
		' SCRIPTING'
	# ======================================================================

	@staticmethod
	def convertMelToPy(mel, excludeFromInput=[], excludeFromOutput=['from pymel.all import *','s pm']):
		'''Convert a string representing mel code into a string representing python code.

		:Parameters:
			mel (str) = string containing mel code.
			excludeFromInput (list) (list) = of strings specifying series of chars to strip from the Input.
			excludeFromOutput (list) (list) = of strings specifying series of chars to strip from the Output.
		
		mel2PyStr Parameters:
			currentModule (str) = The name of the module that the hypothetical code is executing in. In most cases you will leave it at its default, the __main__ namespace.
			pymelNamespace (str) = The namespace into which pymel will be imported. the default is '', which means from pymel.all import *
			forceCompatibility (bool) = If True, the translator will attempt to use non-standard python types in order to produce python code which more exactly reproduces the behavior of the original mel file, but which will produce 'uglier' code. Use this option if you wish to produce the most reliable code without any manual cleanup.
			verbosity (int) = Set to non-zero for a lot of feedback.
		'''
		from pymel.tools import mel2py
		import re

		l = filter(None, re.split('[\n][;]', mel))

		python=[]
		for e in l:
			if not e in excludeFromInput:
				try:
					py = mel2py.mel2pyStr(e, pymelNamespace='pm')
					for i in excludeFromOutput:
						py = py.strip(i)
				except:
					py = e
				python.append(py)

		return ''.join(python)


	@staticmethod
	def commandHelp(command): #mel command help
		#:Parameters: command (str) = mel command
		command = ('help ' + command)
		modtext = (mel.eval(command))
		outputscrollField (modtext, "command help", 1.0, 1.0) #text, window_title, width, height


	@staticmethod
	def keywordSearch (keyword): #keyword command search
		#:Parameters: keyword (str) = 
		keyword = ('help -list' + '"*' + keyword + '*"')
		array = sorted(mel.eval(keyword))
		outputTextField(array, "keyword search")


	@staticmethod
	def queryRuntime (command): #query runtime command info
		type       = ('whatIs '                           + command + ';')
		catagory   = ('runTimeCommand -query -category '  + command + ';')
		command	   = ('runTimeCommand -query -command '   + command + ';')
		annotation = ('runTimeCommand -query -annotation '+ command + ';')
		type = (mel.eval(type))
		catagory = (mel.eval(catagory))
		command = (mel.eval(command))
		annotation = (mel.eval(annotation))
		output_text = '{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}'.format(command, "Type:", type, "Annotation:", annotation, "Catagory:", catagory, "Command:", command)
		outputscrollField(output_text, "runTimeCommand", 1.0, 1.0) #text, window_title, width, height


	@staticmethod
	def searchMEL (keyword): #search autodest MEL documentation
		url = '{}{}{}'.format("http://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/Commands/",keyword,".html")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def searchPython (keyword): #Search autodesk Python documentation
		url = '{}{}{}'.format("http://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/CommandsPython/",keyword,".html")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def searchPymel (keyword): #search online pymel documentation
		url = '{}{}{}'.format("http://download.autodesk.com/global/docs/maya2014/zh_cn/PyMel/search.html?q=",keyword,"&check_keywords=yes&area=default")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def currentCtx(): #get current tool context
		output_text = mel.eval('currentCtx;')
		outputscrollField(output_text, "currentCtx", 1.0, 1.0)


	@staticmethod
	def sourceScript(): #Source External Script file
		import os.path

		mel_checkBox = checkBox('mel_checkBox', query=1, value=1)
		python_checkBox = checkBox('python_checkBox', query=1, value=1)

		if mel_checkBox == 1:
			path = os.path.expandvars("%\CLOUD%/____graphics/Maya/scripts/*.mel")
			
		else:
			path = os.path.expandvars("%\CLOUD%/____graphics/Maya/scripts/*.py")

		file = pm.system.fileDialog (directoryMask=path)
		pm.openFile(file)


	@staticmethod
	def commandRef(): #open maya MEL commands list 
		pm.showHelp ('http://download.autodesk.com/us/maya/2011help/Commands/index.html', absolute=True)


	@staticmethod
	def globalVars(): #$g List all global mel variables in current scene
		mel.eval('scriptEditorInfo -clearHistory')
		array = sorted(mel.eval("env"))
		outputTextField(array, "Global Variables")


	@staticmethod
	def listUiObjects(): #lsUI returns the names of UI objects
		windows			= '{}\n{}\n{}\n'.format("Windows", "Windows created using ELF UI commands:", pm.lsUI (windows=True))
		panels			= '{}\n{}\n{}\n'.format("Panels", "All currently existing panels:", pm.lsUI (panels=True))
		editors			= '{}\n{}\n{}\n'.format("Editors", "All currently existing editors:", pm.lsUI (editors=True))
		controls		= '{}\n{}\n{}\n'.format("Controls", "Controls created using ELF UI commands: [e.g. buttons, checkboxes, etc]", pm.lsUI (controls=True))
		control_layouts = '{}\n{}\n{}\n'.format("Control Layouts", "Control layouts created using ELF UI commands: [e.g. formLayouts, paneLayouts, etc.]", pm.lsUI (controlLayouts=True))
		menus			= '{}\n{}\n{}\n'.format("Menus", "Menus created using ELF UI commands:", pm.lsUI (menus=True))
		menu_items	= '{}\n{}\n{}\n'.format("Menu Items", "Menu items created using ELF UI commands:", pm.lsUI (menuItems=True))
		contexts		= '{}\n{}\n{}\n'.format("Tool Contexts", "Tool contexts created using ELF UI commands:", pm.lsUI (contexts=True))
		output_text	= '{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}'.format(windows, panels, editors, menus, menu_items, controls, control_layouts, contexts)
		outputscrollField(output_text, "Ui Elements", 6.4, 0.85)

	# ----------------------------------------------------------------------









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
# 				distance = Slots_maya.getDistanceBetweenTwoPoints(v1Pos, v2Pos)

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
	# 	Slots_maya.loadPlugin('nearestPointOnMesh')
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
				
	# 			distance = Slots_maya.getDistanceBetweenTwoPoints(vertexPosition, associatedVtxPosition)

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

# 		adjFaces = [f for f in Slots_maya.getBorderComponents(face) if not f in prevFaces and f in faces]
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