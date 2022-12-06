# !/usr/bin/python
# coding=utf-8
try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)

from slots import tls
import mayatls as mtls


class GetComponents():
	'''
	'''
	componentTypes = [
			#abv 	singular 	plural 		full						int		hex 
			('vtx', 'vertex', 	'vertices', 'Polygon Vertex', 			31, 	0x0001),
			('e', 	'edge', 	'edges', 	'Polygon Edge', 			32,		0x8000),
			('f', 	'face', 	'faces', 	'Polygon Face', 			34, 	0x0008),
			('uv', 	'texture', 	'texture coordinates', 'Polygon UV', 	35, 	0x0010),
			('cv', 	'control vertex', 'control vertices', 'Control Vertex', 28, None),
			(None,	None, 		None, 		'Polygon Vertex Face', 		70, 	None),
			(None, 	None, 		None, 		'Edit Point', 				30, 	None),
			(None, 	None, 		None, 		'Handle', 					0, 		None),
			(None, 	None, 		None, 		'Nurbs Curves On Surface', 	11, 	None),
			(None, 	None, 		None, 		'Subdivision Mesh Point', 	36, 	None),
			(None, 	None, 		None, 		'Subdivision Mesh Edge', 	37, 	None), 
			(None, 	None, 		None, 		'Subdivision Mesh Face', 	38, 	None), 
			(None, 	None, 		None, 		'Curve Parameter Point', 	39, 	None), 
			(None, 	None, 		None, 		'Curve Knot', 				40, 	None),
			(None, 	None, 		None, 		'Surface Parameter Point', 	41, 	None),
			(None, 	None, 		None, 		'Surface Knot', 			42, 	None),
			(None, 	None, 		None, 		'Surface Range', 			43, 	None),
			(None, 	None, 		None, 		'Trim Surface Edge', 		44, 	None),
			(None, 	None, 		None, 		'Surface Isoparm', 			45, 	None),
			(None, 	None, 		None, 		'Lattice Point', 			46, 	None),
			(None, 	None, 		None, 		'Particle', 				47, 	None),
			(None, 	None, 		None, 		'Scale Pivot', 				49, 	None),
			(None, 	None, 		None, 		'Rotate Pivot', 			50, 	None),
			(None, 	None, 		None, 		'Select Handle', 			51, 	None),
			(None, 	None, 		None, 		'NURBS Surface Face', 		72, 	None),
			(None, 	None, 		None, 		'Subdivision Mesh UV', 		73, 	None),
	]

	@classmethod
	def getComponentType(cls, component, nom='abv'):
		'''Get the type of a given component.

		:Parameters:
			obj (str)(obj)(list) = A single maya component.
				If multiple components are given, only the first will be sampled.
			nom (str) = Specify the desired return value type. (default: 'str')
				(valid: 'full' - object type as a string.
						'int' - maya mask value as an integer.
						'hex' - hex value. ie. 0x0001
						'abv' - abreviated object type as a string. ie. 'vtx'
		:Return:
			(str)(int) dependant on 'nom' arg.

		ex. call:
		getComponentType('cyl.e[:]') #returns: 'e'
		getComponentType('cyl.vtx[:]', 'abv') #returns: 'vtx'
		getComponentType('cyl.e[:]', 'int') #returns: 32
		'''
		for a, s, p, f, i, h in cls.componentTypes:
			try:
				if pm.filterExpand(component, sm=i):
					if nom=='abv': return a
					elif nom=='full': return f
					elif nom=='int': return i
					elif nom=='hex': return h
					elif nom=='plural': return p
					else: return s
			except Exception as error:
				print ('File "{}" in getComponentType\n# Error: Not a valid component. #\n	{}{}'.format(__file__, error, '(empty string)' if component=='' else ''))
				break
		return None


	@classmethod
	def convertComponentName(cls, componentType, nom='abv'):
		'''Return an alternate component alias for the given alias. 
		ie. a hex value of 0x0001 for 'vertex'
		If nothing is found, a value of 'None' will be returned.

		:Parameters:
			componentType () = A component type. ex. 'vertex', 'vtx', 31, or 0x0001
			nom (str) = The desired returned alias.  (default: 'abv')
				(valid: 'abv', 'singular', 'plural', 'str', 'int', 'hex')

		:Return:
			(str)(int)(hex)(None) dependant on 'nom' argument.

		ex. call:
		convertComponentName('vertex', 'hex') #returns: 0x0001
		convertComponentName(0x0001, 'str') #returns: 'Polygon Vertex'
		'''
		rtypes = ('abv', 'singular', 'plural', 'full', 'int', 'hex')

		for t in cls.componentTypes:
			if componentType in t:
				index = rtypes.index(nom)
				return t[index]
		return None


	@staticmethod
	def getElementType(obj):
		'''Determine if the given element(s) type.

		:Parameters:
			obj (str)(obj)(list) = The components(s) to query.

		:Return:
			(list) 'str', 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level)

		ex. call:
		getElementType('cyl.vtx[0]') #returns: 'transform'
		getElementType('cylShape.vtx[:]') #returns: 'str'
		'''
		try:
			o = tls.itertls.makeList(obj)[0]
		except IndexError as error:
			# print ('{}\n# Error: getElementType: Operation requires at least one object. #\n	{}'.format(__file__, error))
			return ''

		if isinstance(o, str):
			return 'str' if 'Shape' in o else 'transform'
		elif isinstance(o, int):
			return 'int'
		else:
			return 'obj'


	@classmethod
	def convertElementType(cls, lst, returnType='str', flatten=False):
		'''Convert the given element(s) to <obj>, 'str', or int values.

		:Parameters:
			lst (str)(obj)(list) = The components(s) to convert.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list)(dict) return a dict only with a return type of 'int' and more that one object given.

		ex. call:
		convertElementType('obj.vtx[:2]', 'str') #returns: ['objShape.vtx[0:2]']
		convertElementType('obj.vtx[:2]', 'str', True) #returns: ['objShape.vtx[0]', 'objShape.vtx[1]', 'objShape.vtx[2]']
		convertElementType('obj.vtx[:2]', 'obj') #returns: [MeshVertex('objShape.vtx[0:2]')]
		convertElementType('obj.vtx[:2]', 'obj', True) #returns: [MeshVertex('objShape.vtx[0]'), MeshVertex('objShape.vtx[1]'), MeshVertex('objShape.vtx[2]')]
		convertElementType('obj.vtx[:2]', 'transform') #returns: ['obj.vtx[0:2]']
		convertElementType('obj.vtx[:2]', 'transform', True) #returns: ['obj.vtx[0]', 'obj.vtx[1]', 'obj.vtx[2]']
		convertElementType('obj.vtx[:2]', 'int')) #returns: {nt.Mesh('objShape'): [(0, 2)]}
		convertElementType('obj.vtx[:2]', 'int', True)) #returns: {nt.Mesh('objShape'): [0, 1, 2]}
		'''
		lst = pm.ls(lst, flatten=flatten)
		if not lst or isinstance(lst[0], int):
			return []

		if returnType=='int':
			result={}
			for c in lst:
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
					break; print ('File "{}" in convertElementType\n# Error: unable to convert {} {} to int. {}. #'.format(__file__, obj, num, error))

			objects = set(pm.ls(lst, objectsOnly=True))
			if len(objects)==1: #flatten the dict values from 'result' and remove any duplicates.
				flattened = tls.itertls.flatten(result.values())
				result = tls.itertls.removeDuplicates(flattened)
		else:
			if returnType=='transform':
				result = list(map(lambda s: ''.join(s.rsplit('Shape', 1)), lst))
			elif returnType=='str':
				result = list(map(str, lst))
			else:
				result = lst

		return result


	@classmethod
	def convertComponentType(cls, components, componentType, returnType='str', flatten=False):
		'''Convert component(s) to it's sub-components of the given type.

		:Parameters:
			components (str)(obj)(list) = The components(s) to convert.
			componentType (str) = The desired returned component type. 
				valid: 'vtx' (or 'vertex', 'vertices', 'Polygon Vertex', 31, 0x0001), 
					and the same for each: 'edge', 'uv', 'face'.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list)(dict)

		ex. call:
		convertComponentType('obj.vtx[:2]', 'vertex') #returns: ['obj.vtx[0:2]']
		convertComponentType('obj.vtx[:2]', 'face') #returns: ['obj.f[0:2]', 'obj.f[11:14]', 'obj.f[23]']
		convertComponentType('obj.vtx[:2]', 'edge') #returns: ['obj.e[0:2]', 'obj.e[11]', 'obj.e[24:26]', 'obj.e[36:38]']
		convertComponentType('obj.vtx[:2]', 'uv') #returns: ['obj.map[0:2]', 'obj.map[12:14]', 'obj.map[24]']
		'''
		d = {'vtx':'toVertex', 'e':'toEdge', 'uv':'toUV', 'f':'toFace'}
		typ = cls.convertComponentName(componentType) #get the correct componentType variable from possible args.
		components = pm.polyListComponentConversion(components, **{d[typ.lower()]:True})
		return cls.convertElementType(components, returnType=returnType, flatten=flatten)


	@classmethod
	def convertIntToComponent(cls, obj, integers, componentType, returnType='str', flatten=False):
		'''Convert the given integers to components of the given object.

		:Parameters:
			obj (str)(obj)(list) = The object to convert to vertices of.
			integers (list) = The integer(s) to convert.
			componentType (str) = The desired returned component type. 
				valid: 'vtx' (or 'vertex', 'vertices', 'Polygon Vertex', 31, 0x0001), 
					and the same for each: 'edge', 'uv', 'face'.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list)

		ex. call: convertIntToComponent('cyl', range(4), 'f') #returns: ['cylShape.f[0:3]']
		'''
		obj = pm.ls(obj, objectsOnly=True)[0]
		objName = obj.name()

		if not flatten:
			n = lambda c: '{}:{}'.format(c[0], c[-1]) if len(c)>1 else str(c[0])
			result = ['{}.{}[{}]'.format(objName, componentType, n(c)) for c in tls.itertls.splitList(integers, 'range')]
		else:
			result = ['{}.{}[{}]'.format(objName, componentType, c) for c in integers]

		return cls.convertElementType(result, returnType=returnType, flatten=flatten)


	@classmethod
	def filterComponents(cls, components, include=[], exclude=[], flatten=False):
		'''Filter the given components.

		:Parameters:
			components (str)(obj)(list) = The components(s) to filter.
			include (str)(int)(obj)(list) = The component(s) to include.
			exclude (str)(int)(obj)(list) = The component(s) to exclude.
						(exlude take precidence over include)
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list)

		ex. call:
		filterComponents('cyl.vtx[:]', 'cyl.vtx[:2]', 'cyl.vtx[1:23]') #returns: ['cyl.vtx[0]']
		filterComponents('cyl.f[:]', range(2), range(1, 23)) #returns: ['cyl.f[0]']
		'''
		typ = cls.getComponentType(components)
		etyp = cls.getElementType(components)
		etyp_include = cls.getElementType(include)
		etyp_exclude = cls.getElementType(exclude)

		if etyp_include=='int' or etyp_exclude=='int':
			try:
				obj = pm.ls(components, objectsOnly=True)[0]
			except IndexError as error:
				print ('File "{}" in filterComponents\n# Error: Operation requires at least one component. #\n	{}'.format(__file__, error))
				return []

		if etyp_include=='int':
			include = cls.convertIntToComponent(obj, include, typ)
		include = pm.ls(include, flatten=True)

		if etyp_exclude=='int':
			exclude = cls.convertIntToComponent(obj, exclude, typ)
		exclude = pm.ls(exclude, flatten=True)

		components = pm.ls(components, flatten=True)

		filtered = tls.itertls.filterList(components, include=include, exclude=exclude)
		result = cls.convertElementType(filtered, returnType=etyp, flatten=flatten)
		return result


	@classmethod
	def getComponents(cls, objects, componentType, returnType='str', include=[], exclude=[], randomize=0, flatten=False):
		'''Get the components of the given type from the given object(s).
		If no objects are given the current selection will be used.

		:Parameters:
			objects (str)(obj)(list) = The object(s) to get the components of. (Polygon, Polygon components)(default: current selection)
			componentType (str)(int) = The desired component mask. (valid: any type allowed in the 'convertComponentName' method)
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
			include (str)(obj)(list) = The component(s) to include.
			exclude (str)(obj)(list) = The component(s) to exclude. (exlude take precidence over include)
			randomize (float) = If a 0.1-1 value is given, random components will be returned with a quantity determined by the given ratio. 
								A value of 0.5 will return a 50% of the components of an object in random order.
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list)(dict) Dependant on flags.

		ex. call:
		getComponents('obj', 'vertex', 'str', '', 'obj.vtx[2:23]') #returns: ['objShape.vtx[0]', 'objShape.vtx[1]', 'objShape.vtx[24]', 'objShape.vtx[25]']
		getComponents('obj', 'vertex', 'obj', '', 'obj.vtx[:23]') #returns: [MeshVertex('objShape.vtx[24]'), MeshVertex('objShape.vtx[25]')]
		getComponents('obj', 'f', 'int') #returns: {nt.Mesh('objShape'): [(0, 35)]}
		getComponents('obj', 'edges') #returns: ['objShape.e[0:59]']
		getComponents('obj', 'edges', 'str', 'obj.e[:2]') #returns: ['objShape.e[0]', 'objShape.e[1]', 'objShape.e[2]']
		'''
		components = cls.convertComponentType(objects, componentType)

		if include or exclude:
			components = cls.filterComponents(components, include=include, exclude=exclude)

		if randomize:
			components = tls.randomize(pm.ls(components, flatten=1), randomize)

		result = cls.convertElementType(components, returnType=returnType, flatten=flatten)
		return result



class Componenttls(GetComponents):
	'''
	'''
	@classmethod
	def getContigiousEdges(cls, components):
		'''Get a list containing sets of adjacent edges.

		:Parameters:
			components (list) = Polygon components to be filtered for adjacent edges.

		:Return:
			(list) adjacent edge sets.

		ex. call:
		getContigiousEdges(['obj.e[:2]']) #returns: [{'objShape.e[1]', 'objShape.e[0]', 'objShape.e[2]'}]
		getContigiousEdges(['obj.f[0]']) #returns: [{'objShape.e[24]', 'objShape.e[0]', 'objShape.e[25]', 'objShape.e[12]'}]
		'''
		edges = cls.convertComponentType(components, 'edge', flatten=1)

		sets=[]
		for edge in edges:
			vertices = pm.polyListComponentConversion(edge, fromEdge=1, toVertex=1)
			connEdges = cls.convertComponentType(vertices, 'edge', flatten=1)
			edge_set = set([e for e in connEdges if e in edges]) #restrict the connected edges to the original edge pool.
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


	@classmethod
	def getContigiousIslands(cls, faces, faceIslands=[]):
		'''Get a list containing sets of adjacent polygon faces grouped by islands.

		:Parameters:
			faces (str)(obj)(list) = The polygon faces to be filtered for adjacent.
			faceIslands (list) = optional. list of sets. ability to add faces from previous calls to the return value.

		:Return:
			(list) of sets of adjacent faces.

		ex. call: getContigiousIslands('obj.f[21:26]') #returns: [{'objShape.f[22]', 'objShape.f[21]', 'objShape.f[23]'}, {'objShape.f[26]', 'objShape.f[24]', 'objShape.f[25]'}]
		'''
		sets=[]
		faces = pm.ls(faces, flatten=1)
		for face in faces:
			edges = pm.polyListComponentConversion(face, fromFace=1, toEdge=1)
			borderFaces = cls.convertComponentType(edges, 'face', 'obj', flatten=1)
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
	def getIslands(obj, returnType='str', flatten=False):
		'''Get the group of components in each separate island of a combined mesh.

		:parameters:
			obj (str)(obj)(list) = The object to get shells from.
			returnType (bool) = Return the shell faces as a list of type: 'str' (default), 'int', or 'obj'.
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:return:
			(generator)

		ex. call: getIslands('combined_obj') #returns: [['combined_obj.f[0]', 'combined_obj.f[5]', ..etc, ['combined_obj.f[15]', ..etc]] 
		'''
		num_shells = pm.polyEvaluate(obj, shell=True)
		num_faces = pm.polyEvaluate(obj, face=True)

		unprocessed = set(range(num_faces))

		shells=[]
		while unprocessed:
			index = next(iter(unprocessed)) #face_index
			faces = pm.polySelect(obj, extendToShell=index, noSelection=True) #shell faces

			if returnType=='str':
				yield ["{}.f[{}]".format(obj, index) for index in faces]

			elif returnType=='int':
				yield [index for index in faces]

			elif returnType=='obj':
				yield [pm.ls("{}.f[{}]".format(obj, index))[0] for index in faces]

			unprocessed.difference_update(faces)


	@classmethod
	def getBorderComponents(cls, x, componentType='', returnType='str', componentBorder=False, flatten=False):
		'''Get any object border components from given component(s) or a polygon object.
		A border is defined as a hole or detached edge.

		:Parameters:
			x (str)(obj)(list) = Component(s) (or a polygon object) to find any border components for.
			componentType (str) = The desired returned component type. (valid: 'vertex','edge','face', '',
				An empty string returns the same type as the first given component, or edges if an object is given)
			returnType (str) = The desired returned object type.
				(valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
			componentBorder (bool) = Get the components that border given components instead of the mesh border.
				(valid: 'component', 'object'(default))
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list) components that border an open edge.

		ex. call:
		getBorderComponents('pln', 'vtx') #returns: ['plnShape.vtx[0:4]', 'plnShape.vtx[7:8]', 'plnShape.vtx[11:15]'],
		getBorderComponents('pln') #returns: ['plnShape.e[0:2]', 'plnShape.e[4]', 'plnShape.e[6]', 'plnShape.e[8]', 'plnShape.e[13]', 'plnShape.e[15]', 'plnShape.e[20:23]'],
		getBorderComponents('pln.e[:]') #returns: ['plnShape.e[0:2]', 'plnShape.e[4]', 'plnShape.e[6]', 'plnShape.e[8]', 'plnShape.e[13]', 'plnShape.e[15]', 'plnShape.e[20:23]'],
		getBorderComponents(['pln.e[9]','pln.e[10]', 'pln.e[12]', 'pln.e[16]'], 'f', componentBorder=True) #returns: ['plnShape.f[1]', 'plnShape.f[3:5]', 'plnShape.f[7]'],
		getBorderComponents('pln.f[3:4]', 'vtx', componentBorder=True) #returns: ['plnShape.vtx[4:6]', 'plnShape.vtx[8:10]'],
		'''
		if not x:
			print ('File "{}" in getBorderComponents\n# Error: Operation requires a given object(s) or component(s). #'.format(__file__))
			return []

		origType = cls.getComponentType(x, 'abv')
		if not origType:
			origType, x = 'mesh', cls.getComponents(x, 'edges')
		origVerts = cls.convertComponentType(x, 'vtx', flatten=True)
		origEdges = cls.convertComponentType(x, 'edge', flatten=True)
		origFaces = cls.convertComponentType(x, 'face', flatten=True)

		if not componentType: #if no component type is specified, return the same type of component as given. in the case of mesh object, edges will be returned.
			componentType = origType if not origType=='mesh' else 'e'
		else:
			componentType = cls.convertComponentName(componentType) #get the correct componentType variable from possible args.

		result=[]
		if componentBorder: #get edges Qthat form the border of the given components.
			for edge in origEdges:
				attachedFaces = cls.convertComponentType(edge, 'face', flatten=1)
				if componentType=='f':
					for f in attachedFaces:
						if origType=='f' and f in origFaces:
							continue
						result.append(f)
					continue
				attachedEdges = cls.convertComponentType(attachedFaces, 'edge', flatten=1)
				for e in attachedEdges:
					if origType=='e' and e in origEdges:
						continue
					attachedVerts = cls.convertComponentType(e, 'vtx', flatten=1)
					for v in attachedVerts:
						if v in origVerts:
							result.append(v)

		else: #get edges that form the border of the object.
			for edge in origEdges:
				attachedFaces = cls.convertComponentType(edge, 'face', flatten=1)
				if len(attachedFaces)==1:
					result.append(edge)

		result = cls.convertComponentType(result, componentType) #convert back to the original component type and flatten /un-flatten list.
		result = cls.convertElementType(result, returnType=returnType, flatten=flatten)
		return result


	@classmethod
	def getClosestVerts(cls, set1, set2, tolerance=1000):
		'''Find the two closest vertices between the two sets of vertices.

		:Parameters:
			set1 (str)(list) = The first set of vertices.
			set2 (str)(list) = The second set of vertices.
			tolerance (float) = Maximum search distance.

		:Return:
			(list) closest vertex pairs by order of distance (excluding those not meeting the tolerance). (<vertex from set1>, <vertex from set2>).

		ex. call: getClosestVerts('pln.vtx[:10]', 'pln.vtx[11:]', 6.667) #returns: [('plnShape.vtx[7]', 'plnShape.vtx[11]'), ('plnShape.vtx[8]', 'plnShape.vtx[12]'), ('plnShape.vtx[9]', 'plnShape.vtx[13]'), ('plnShape.vtx[10]', 'plnShape.vtx[11]'), ('plnShape.vtx[10]', 'plnShape.vtx[14]')]
		'''
		from operator import itemgetter
		from slots.tls.mathtls import getDistBetweenTwoPoints

		set1 = cls.convertElementType(set1, returnType='str', flatten=True)
		set2 = cls.convertElementType(set2, returnType='str', flatten=True)
		vertPairsAndDistance={}
		for v1 in set1:
			v1Pos = pm.pointPosition(v1, world=1)
			for v2 in set2:
				v2Pos = pm.pointPosition(v2, world=1)
				distance = getDistBetweenTwoPoints(v1Pos, v2Pos)
				if distance<tolerance:
					vertPairsAndDistance[(v1, v2)] = distance

		sorted_ = sorted(vertPairsAndDistance.items(), key=itemgetter(1))
		vertPairs = [i[0] for i in sorted_]

		return vertPairs


	@classmethod
	def getClosestVertex(cls, vertices, obj, tolerance=0.0, freezeTransforms=False, returnType='str'):
		'''Find the closest vertex of the given object for each vertex in the list of given vertices.

		:Parameters:
			vertices (list) = A set of vertices.
			obj (str)(obj)(list) = The reference object in which to find the closest vertex for each vertex in the list of given vertices.
			tolerance (float) = Maximum search distance. Default is 0.0, which turns off the tolerance flag.
			freezeTransforms (bool) = Reset the selected transform and all of its children down to the shape level.
			returnType (str) = The desired returned object type. This only affects the dict value (found vertex), 
					the key (orig vertex) is always a string. ex. {'planeShape.vtx[0]': 'objShape.vtx[3]'} vs. {'planeShape.vtx[0]': MeshVertex('objShape.vtx[3]')}
					(valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
		:Return:
			(dict) closest vertex pairs {<vertex from set1>:<vertex from set2>}.

		ex. call:
		getClosestVertex('plnShape.vtx[0]', 'cyl', returnType='int') #returns: {'plnShape.vtx[0]': 3},
		getClosestVertex('plnShape.vtx[0]', 'cyl') #returns: {'plnShape.vtx[0]': 'cylShape.vtx[3]'},
		getClosestVertex('plnShape.vtx[2:3]', 'cyl') #returns: {'plnShape.vtx[2]': 'cylShape.vtx[2]', 'plnShape.vtx[3]': 'cylShape.vtx[1]'}
		'''
		from slots.tls.mathtls import getDistBetweenTwoPoints

		vertices = cls.convertElementType(vertices, returnType='str', flatten=True)
		pm.undoInfo(openChunk=True)

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
			distance = getDistBetweenTwoPoints(v1Pos, v2Pos)

			v2_convertedType = cls.convertElementType(v2, returnType=returnType)[0]
			if not tolerance:
				closestVerts[v1] = v2_convertedType
			elif distance < tolerance:
				closestVerts[v1] = v2_convertedType

		pm.delete(cpmNode)
		pm.undoInfo(closeChunk=True)

		return closestVerts


	@classmethod
	def getEdgePath(cls, components, path='edgeLoop', returnType='str', flatten=False):
		'''Query the polySelect command for the components along different edge paths.
		Supports components from a single object.

		:Parameters:
			components (str)(obj)(list) = The components used for the query (dependant on the operation type).
			path (str) = The desired return type. valid: 'edgeLoop': Select an edge loop starting at the given edge.
				'edgeRing': Select an edge ring starting at the given edge.
				'edgeRingPath', Given two edges that are on the same edge ring, this will select the shortest path between them on the ring.
				'edgeLoopPath': Given two edges that are on the same edge loop, this will select the shortest path between them on the loop.
			returnType (str) = The desired returned object type.
				(valid: 'str'(default), 'obj'(shape object), 'transform'(as string), 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list) The components comprising the path.

		ex. call:
		getEdgePath('sph.e[12]', 'edgeLoop') #returns: ['sphShape.e[12]', 'sphShape.e[17]', 'sphShape.e[16]', 'sphShape.e[15]', 'sphShape.e[14]', 'sphShape.e[13]']
		getEdgePath('sph.e[12]', 'edgeLoop', 'int') #returns: [12, 17, 16, 15, 14, 13]
		getEdgePath('sph.e[12]', 'edgeRing') #returns: ['sphShape.e[0]', 'sphShape.e[6]', 'sphShape.e[12]', 'sphShape.e[18]', 'sphShape.e[24]']
		getEdgePath(['sph.e[43]', 'sph.e[46]'], 'edgeRingPath') #returns: ['sphShape.e[43]', 'sphShape.e[42]', 'sphShape.e[47]', 'sphShape.e[46]']
		getEdgePath(['sph.e[54]', 'sph.e[60]'], 'edgeLoopPath') #returns: ['sphShape.e[60]', 'sphShape.e[48]', 'sphShape.e[42]', 'sphShape.e[36]', 'sphShape.e[30]', 'sphShape.e[54]']
		'''
		obj, *other = pm.ls(components, objectsOnly=1)
		cnums = cls.convertComponentType(components, 'edge', returnType='int', flatten=True)

		if len(cnums)<2 and path in ('edgeRingPath', 'edgeLoopPath'):
			print ('File "{}" in getEdgePath\n# Error: Operation requires at least two components. #\n	Edges given: {}'.format(__file__, cnums))
			return []

		if path=='edgeRing':
			edgesLong = pm.polySelect(obj, query=1, edgeRing=cnums) #(e..)

		elif path=='edgeRingPath':
			edgesLong = pm.polySelect(obj, query=1, edgeRingPath=(cnums[0], cnums[1])) #(e, e)
			if not edgesLong:
				print ('File "{}" in getEdgePath\n# Error: getEdgePath: Operation requires two edges that are on the same edge ring. #\n	Edges given: {}, {}'.format(__file__, cnums[0], cnums[1]))
				return []

		elif path=='edgeLoopPath':
			edgesLong = pm.polySelect(obj, query=1, edgeLoopPath=(cnums[0], cnums[1])) #(e, e)
			if not edgesLong:
				print ('File "{}" in getEdgePath\n# Error: getEdgePath: Operation requires two edges that are on the same edge loop. #\n	Edges given: {}, {}'.format(__file__, cnums[0], cnums[1]))
				return []
		else: #'edgeLoop'
			edgesLong = pm.polySelect(obj, query=1, edgeLoop=cnums) #(e..)

		objName = obj.name()
		result = tls.itertls.removeDuplicates(['{}.e[{}]'.format(objName, e) for e in edgesLong])
		return cls.convertElementType(result, returnType=returnType, flatten=flatten)


	@classmethod
	def getShortestPath(cls, components, returnType='str', flatten=False):
		'''Get the shortest path between two components.

		:Parameters:
			components (obj) = A Pair of vertices or edges.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list) the components that comprise the path as strings.

		ex. call:
		getEdgePath('sph.e[12]', 'edgeLoop') #returns: ['sphShape.e[12]', 'sphShape.e[17]', 'sphShape.e[16]', 'sphShape.e[15]', 'sphShape.e[14]', 'sphShape.e[13]']
		getEdgePath('sph.e[12]', 'edgeLoop', 'int') #returns: [12, 17, 16, 15, 14, 13]
		getEdgePath('sph.e[12]', 'edgeRing') #returns: ['sphShape.e[0]', 'sphShape.e[6]', 'sphShape.e[12]', 'sphShape.e[18]', 'sphShape.e[24]']
		getEdgePath(['sph.e[43]', 'sph.e[46]'], 'edgeRingPath') #returns: ['sphShape.e[43]', 'sphShape.e[42]', 'sphShape.e[47]', 'sphShape.e[46]']
		getEdgePath(['sph.e[54]', 'sph.e[60]'], 'edgeLoopPath') #returns: ['sphShape.e[60]', 'sphShape.e[48]', 'sphShape.e[42]', 'sphShape.e[36]', 'sphShape.e[30]', 'sphShape.e[54]']
		'''
		obj = pm.ls(components, objectsOnly=1)[0]
		ctype = cls.getComponentType(components)
		try:
			A, B = components = cls.convertComponentType(components, ctype)[:2]
		except ValueError as error:
			print ('File "{}" in getShortestPath\n# Error: Operation requires exactly two components. #\n	{}'.format(__file__, error))
			return []

		returnAsVerts=False
		if ctype=='vtx':
			edgesA = cls.convertComponentType(A, 'e', flatten=1)
			vertsA = cls.convertComponentType(edgesA, 'vtx', flatten=1)
			closestA = cls.getClosestVerts(B, [i for i in vertsA if not i==A])[0]
			edgeA = [e for e in edgesA if closestA[1] in cls.convertComponentType(e, 'vtx', flatten=1)]

			edgeB = cls.convertComponentType(B, 'e', flatten=1)
			vertsB = cls.convertComponentType(edgeB, 'vtx', flatten=1)
			closestB = cls.getClosestVerts(A, [i for i in vertsB if not i==B])[0]
			edgeB = [e for e in edgeB if closestB[1] in cls.convertComponentType(e, 'vtx', flatten=1)]

			components = (edgeA, edgeB)
			ctype = 'e'
			returnAsVerts = True

		compNums = cls.convertComponentType(components, ctype, returnType='int', flatten=True)

		kwargs = {
			'shortestFacePath' if ctype=='f' 
			else 'shortestEdgePathUV' if ctype=='uv' 
			else 'shortestEdgePath': compNums
		}
		compLong = set(pm.polySelect(obj, query=1, **kwargs) + compNums)

		result = cls.convertIntToComponent(obj, compLong, ctype, returnType=returnType, flatten=flatten)

		if returnAsVerts:
			result = cls.convertComponentType(result, 'vtx', flatten=flatten)

		return result


	@classmethod
	def getEdgesByNormalAngle(cls, objects, lowAngle=50, highAngle=130, returnType='str', flatten=False):
		'''Get a list of edges having normals between the given high and low angles using maya's polySelectConstraint.

		:Parameters:
			objects (str)(list)(obj) = The object(s) to get edges of.
			lowAngle (int) = Normal angle low range.
			highAngle (int) = Normal angle high range.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list) Polygon edges.

		ex. call: getEdgesByNormalAngle('cyl', 50, 130) #returns: ['cylShape.e[0:23]']
		'''
		orig_selection = pm.ls(sl=1) #get currently selected objects in order to re-select them after the contraint operation.

		pm.select(objects)
		pm.polySelectConstraint(angle=True, anglebound=(lowAngle, highAngle), mode=3, type=0x8000) #Constrain that selection to only edges of a certain Angle
		pm.selectType(polymeshEdge=True)

		mask = cls.convertComponentName('edges', 'int')
		objects = pm.filterExpand(selectionMask=mask, expand=flatten)

		edges = cls.getComponents(objects, componentType='edges', returnType=returnType, flatten=flatten) #get selected edges with constraint active.
		pm.polySelectConstraint(mode=0) #Remove the selection constraint.

		pm.select(orig_selection) #re-select any originally selected objects.
		return edges


	@classmethod
	def getComponentsByNumberOfConnected(cls, components, num_of_connected=(0,2), connectedType='', returnType='str'):
		'''Get a list of components filtered by the number of their connected components.

		:Parameters:
			components (str)(list)(obj) = The components to filter.
			num_of_connected (int)(tuple) = The number of connected components. Can be given as a range. (Default: (0,2))
			connectedType (str)(int) = The desired component mask. (valid: 'vtx','vertex','vertices','Polygon Vertex',31,0x0001(vertices), 'e','edge','edges','Polygon Edge',32,0x8000(edges), 'f','face','faces','Polygon Face',34,0x0008(faces), 'uv','texture','texture coordinates','Polygon UV',35,0x0010(texture coordiantes).
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level).

		:Return:
			(list) flattened list.

		ex. faces = getComponentsByNumberOfConnected('sph.f[:]', 4, 'e') #returns faces with four connected edges (four sided faces).
		ex. verts = getComponentsByNumberOfConnected('pln.vtx[:]', (0,2), 'e') #returns vertices with up to two connected edges.
		'''
		try:
			lowRange, highRange = num_of_connected
		except TypeError as error:
			lowRange = highRange = num_of_connected

		typ = cls.getComponentType(components)
		if connectedType:
			ctype = cls.convertComponentName(connectedType)
		else:
			ctype = typ

		result=[]
		for c in pm.ls(components, flatten=True):

			attached = cls.convertComponentType(c, ctype, flatten=True)
			n = len(attached)
			if n>=lowRange and n<=highRange:
				result.append(c)

		result = cls.convertElementType(result, returnType=returnType)
		return result


	@classmethod
	def getVertexNormal(cls, vertex, angleWeighted=False):
		'''Return the normal at the given vertex. The returned normal is a single 
		per-vertex normal, so unshared normals at a vertex will be averaged.

		:Parameters:
			vertex (str)(obj)(list) = A polygon vertex.
			angleWeighted (bool) = Weight by the angle subtended by the face at the vertex. 
				If angleWeighted is set to false, a simple average of surround face normals is returned.
				The simple average evaluation is significantly faster than the angle-weighted average.
		:Return:
			(MVector)
		'''
		import maya.api.OpenMaya as om

		mesh = pm.ls(vertex, objectsOnly=True)[0].name()
		selectionList = om.MSelectionList() #empty selection list.
		selectionList.add(mesh)

		dagPath = selectionList.getDagPath(0) #create empty dag path object.
		mesh = om.MFnMesh(dagPath) #get mesh.

		vtxID = cls.convertElementType(vertex, 'int')[0]
		return mesh.getVertexNormal(vtxID, angleWeighted, space=om.MSpace.kWorld) #get vertex normal and use om.MSpace.kObject for object space.


	@staticmethod
	def getVectorFromComponents(components):
		'''Get a vector representing the averaged and normalized vertex-face normals.

		:Parameters:
			components (list) = A list of component to get normals of.

		:Return:
			(tuple) vector ie. (-4.5296159711938344e-08, 1.0, 1.6846732009412335e-08)
		'''
		vertices = pm.polyListComponentConversion(components, toVertex=1)

		norm = pm.polyNormalPerVertex(vertices, query=True, xyz=True) #return all of the normals associated with the vert.
		normal_vector = (sum(norm[0::3])/len(norm[0::3]), sum(norm[1::3])/len(norm[1::3]), sum(norm[2::3])/len(norm[2::3])) #averaging of all x,y,z points.

		return normal_vector

# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)








# print (__name__) #module name
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated: -----------------------------------


# def filterComponents(cls, frm, include=[], exclude=[]):
# 		'''Filter the given 'frm' list for the items in 'exclude'.

# 		:Parameters:
# 			frm (str)(obj)(list) = The components(s) to filter.
# 			exclude (str)(obj)(list) = The component(s) to include.
# 			exclude (str)(obj)(list) = The component(s) to exclude.
# 								(exlude take precidence over include)
# 		:Return:
# 			(list)

# 		ex. call: filterComponents('obj.vtx[:]', 'obj.vtx[1:23]') #returns: [MeshVertex('objShape.vtx[0]'), MeshVertex('objShape.vtx[24]'), MeshVertex('objShape.vtx[25]')]
# 		'''
# 		exclude = pm.ls(exclude, flatten=True)
# 		if not exclude:
# 			return frm

# 		c, *other = components = pm.ls(frm, flatten=True)
# 		#determine the type of items in 'exclude' by sampling the first element.
# 		if isinstance(c, str):
# 			if 'Shape' in c:
# 				rtn = 'transform'
# 			else:
# 				rtn = 'str'
# 		elif isinstance(c, int):
# 			rtn = 'int'
# 		else:
# 			rtn = 'obj'

# 		if exclude and isinstance(exclude[0], int): #attempt to create a component list from the given integers. warning: this will only exclude from a single object.
# 			obj = pm.ls(frm, objectsOnly=1)
# 			if len(obj)>1:
# 				return frm
# 			componentType = cls.getComponentType(frm[0])
# 			typ = cls.convertComponentName(componentType) #get the correct componentType variable from possible args.
# 			exclude = ["{}.{}[{}]".format(obj[0], typ, n) for n in exclude]

# 		if include and isinstance(include[0], int): #attempt to create a component list from the given integers. warning: this will only exclude from a single object.
# 			obj = pm.ls(frm, objectsOnly=1)
# 			if len(obj)>1:
# 				return frm
# 			componentType = cls.getComponentType(frm[0])
# 			typ = cls.convertComponentName(componentType) #get the correct componentType variable from possible args.
# 			include = ["{}.{}[{}]".format(obj[0], typ, n) for n in include]

# 		include = cls.convertElementType(include, returnType=rtn, flatten=True) #assure both lists are of the same type for comparison.
# 		exclude = cls.convertElementType(exclude, returnType=rtn, flatten=True)
# 		return [i for i in components if i not in exclude and (include and i in include)]