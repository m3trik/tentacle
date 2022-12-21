# !/usr/bin/python
# coding=utf-8
try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)

from tentacle.slots.tk import mathtk
from tentacle.slots.maya.mayatk import comptk, viewportMessage, undo


class Xformtk(object):
	'''
	'''
	@classmethod
	@undo
	def resetTranslation(cls, objects):
		'''Reset the translation transformations on the given object(s).

		:Parameters:
			objects (str)(obj)(list) = The object(s) to reset the translation values for.
		'''
		# pm.undoInfo(openChunk=1)
		for obj in pm.ls(objects):
			pos = pm.objectCenter(obj) #get the object's current position.
			cls.dropToGrid(obj, origin=1, centerPivot=1) #move to origin and center pivot.
			pm.makeIdentity(obj, apply=1, t=1, r=0, s=0, n=0, pn=1) #bake transforms
			pm.xform(obj, translation=pos) #move the object back to it's original position.
		# pm.undoInfo(closeChunk=1)


	@staticmethod
	def moveTo(source, target, targetCenter=True):
		'''Move an object(s) to the given target.

		:Parameters:
			source (str)(obj)(list) = The objects to move.
			target (str)(obj) = The object to move to.
			targetCenter (bool) = Move to target pivot pos, or the bounding box center of the target.
		'''
		if targetCenter: #temporarily move the targets pivot to it's bounding box center.
			orig_target_piv = pm.xform(target, q=1, worldSpace=1, rp=1) #get target pivot position.
			pm.xform(target, centerPivots=1) #center target pivot.
			target_pos = pm.xform(target, q=1, worldSpace=1, rp=1) #get the pivot position at center of object.
			pm.xform(target, worldSpace=1, rp=orig_target_piv) #return the target pivot to it's orig position.
		else:
			target_pos = pm.xform(target, q=1, worldSpace=1, rp=1) #get the pivot position.

		pm.xform(source, translation=target_pos, worldSpace=1, relative=1)


	@staticmethod
	@undo
	def dropToGrid(objects, align='Mid', origin=False, centerPivot=False, freezeTransforms=False):
		'''Align objects to Y origin on the grid using a helper plane.

		:Parameters:
			objects (str)(obj)(list) = The objects to translate.
			align (bool) = Specify which point of the object's bounding box to align with the grid. (valid: 'Max','Mid'(default),'Min')
			origin (bool) = Move to world grid's center.
			centerPivot (bool) = Center the object's pivot.
			freezeTransforms (bool) = Reset the selected transform and all of its children down to the shape level.

		ex. dropToGrid(obj, align='Min') #set the object onto the grid.
		'''
		# pm.undoInfo(openChunk=1)
		for obj in pm.ls(objects, transforms=1):
			osPivot = pm.xform(obj, query=1, rotatePivot=1, objectSpace=1) #save the object space obj pivot.
			wsPivot = pm.xform(obj, query=1, rotatePivot=1, worldSpace=1) #save the world space obj pivot.

			pm.xform(obj, centerPivots=1) #center pivot
			plane = pm.polyPlane(name='temp#')

			if not origin:
				pm.xform(plane, translation=(wsPivot[0], 0, wsPivot[2]), absolute=1, ws=1) #move the object to the pivot location

			pm.align(obj, plane, atl=1, x='Mid', y=align, z='Mid')
			pm.delete(plane)

			if not centerPivot:
				pm.xform(obj, rotatePivot=osPivot, objectSpace=1) #return pivot to orig position.

			if freezeTransforms:
				pm.makeIdentity(obj, apply=True)
		# pm.undoInfo (closeChunk=1)


	@staticmethod
	def setTranslationToPivot(node):
		'''Set an object’s translation value from its pivot location.

		:Parameters:
			node (str)(obj) = An object, or it's name.
		'''
		x, y, z = pivot = pm.xform(node, query=True, worldSpace=True, rotatePivot=True)
		pm.xform(node, relative=True, translation=[-x,-y,-z])
		pm.makeIdentity(node, apply=True, translate=True)
		pm.xform(node, translation=[x, y, z])


	@staticmethod
	@undo
	def alignPivotToSelection(alignFrom=[], alignTo=[], translate=True):
		'''Align one objects pivot point to another using 3 point align.
		:Parameters:
			alignFrom (list) = At minimum; 1 object, 1 Face, 2 Edges, or 3 Vertices.
			alignTo (list) = The object to align with.
			translate (bool) = Move the object with it's pivot.
		'''
		# pm.undoInfo(openChunk=1)
		pos = pm.xform(alignTo, q=1, translation=True, worldSpace=True)
		center_pos = [ #Get center by averaging of all x,y,z points.
			sum(pos[0::3]) / len(pos[0::3]), 
			sum(pos[1::3]) / len(pos[1::3]), 
			sum(pos[2::3]) / len(pos[2::3])]

		vertices = pm.ls(pm.polyListComponentConversion(alignTo, toVertex=True), flatten=True)
		if len(vertices) < 3:
			return

		for obj in pm.ls(alignFrom, flatten=1):

			plane = pm.polyPlane(name="_hptemp#", width=1, height=1, subdivisionsX=1, subdivisionsY=1, axis=[0, 1, 0], createUVs=2, constructionHistory=True)[0] #Create and align helper plane.

			pm.select("%s.vtx[0:2]" % plane, vertices[0:3])
			pm.mel.snap3PointsTo3Points(0)

			pm.xform(obj, rotation=pm.xform(plane, q=True, rotation=True, worldSpace=True), worldSpace=True)

			if translate:
				pm.xform(obj, translation=center_pos, worldSpace=True)
				
			pm.delete(plane)
		# pm.undoInfo(closeChunk=1)


	@staticmethod
	def aimObjectAtPoint(obj, target_pos, aim_vect=(1,0,0), up_vect=(0,1,0)):
		'''Aim the given object at the given world space position.

		Args:
			obj (str)(obj) = Transform node.
			target_pos (tuple) = The (x,y,z) world position to aim at.
			aim_vect (tuple) = Local axis to aim at the target position.
			up_vect (tuple) = Secondary axis aim vector.
		 '''
		target = pm.createNode('transform')

		pm.xform(target, translation=target_pos, absolute=True)
		const = pm.aimConstraint((target, obj), aim=aim_vect, worldUpVector=up_vect, worldUpType="vector")

		pm.delete(const, target)


	@classmethod
	def rotateAxis(cls, obj, target_pos):
		''' Aim the given object at the given world space position.
		All rotations in rotated channel, geometry is transformed so 
		it does not appear to move during this transformation

		:Parameters:
			obj (str)(obj)(list) = A transform node.
			target_pos (tuple) = An (x,y,z) world position.
		'''
		obj, *other = pm.ls(obj)
		cls.aimObjectAtPoint(obj, target_pos)

		try:
			c = obj.v[:]
		except TypeError:
			c = obj.cv[:]

		wim = pm.getAttr(obj.worldInverseMatrix)
		pm.xform(c, matrix=wim)

		pos = pm.xform(obj, q=True, translation=True, absolute=True, worldSpace=True)
		pm.xform(c, translation=pos, relative=True, worldSpace=True)


	@staticmethod
	def getOrientation(obj, returnType='point'):
		'''Get an objects orientation as a point or vector.

		:Parameters:
			obj (str)(obj) = The object to get the orientation of.
			returnType (str) = The desired returned value type. (valid: 'point'(default), 'vector')

		:Return:
			(tuple)
		'''
		obj, *other = pm.ls(obj)

		world_matrix = pm.xform(obj, q=True, matrix=True, worldSpace=True)
		rAxis = pm.getAttr(obj.rotateAxis)
		if any((rAxis[0], rAxis[1], rAxis[2])):
			print('# Warning: {} has a modified .rotateAxis of {} which is included in the result. #'.format(obj, rAxis))

		if returnType=='vector':
			from maya.api.OpenMaya import MVector

			result = (
				MVector(world_matrix[0:3]),
				MVector(world_matrix[4:7]),
				MVector(world_matrix[8:11])
			)

		else:
			result = (
				world_matrix[0:3],
				world_matrix[4:7],
				world_matrix[8:11]
			)

		return result


	@staticmethod
	def getDistanceBetweenTwoObjects(objA, objB):
		'''Get the magnatude of a vector using the center points of two given objects.

		:Parameters:
			objA (obj)(str) = Object, object name, or point (x,y,z).
			objB (obj)(str) = Object, object name, or point (x,y,z).

		:Return:
			(float)

		# xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(startAndEndCurves)
		'''
		x1, y1, z1 = pm.objectCenter(objA)
		x2, y2, z2 = pm.objectCenter(objB)

		from math import sqrt
		distance = sqrt(pow((x1-x2),2) + pow((y1-y2),2) + pow((z1-z2),2))

		return distance


	@staticmethod
	def getCenterPoint(objects):
		'''Get the bounding box center point of any given object(s).
		
		:Parameters:
			objects (str)(obj(list) = The objects or components to get the center of.

		:Return:
			(list) position as [x,y,z].
		'''
		objects = pm.ls(objects, flatten=True)
		pos = [i for sublist in [pm.xform(s, q=1, translation=1, worldSpace=1, absolute=1) for s in objects] for i in sublist]
		center_pos = [ #Get center by averaging of all x,y,z points.
			sum(pos[0::3]) / len(pos[0::3]), 
			sum(pos[1::3]) / len(pos[1::3]), 
			sum(pos[2::3]) / len(pos[2::3])
		]
		return center_pos


	@staticmethod
	def getComponentPoint(component, alignToNormal=False):
		'''Get the center point from the given component.

		:Parameters:
			component (str)(obj) = Object component.
			alignToNormal (bool) = Constain to normal vector.

		:Return: [float list] - x, y, z  coordinate values.
		'''
		if ".vtx" in str(component):
			x = pm.polyNormalPerVertex (component, query=1, x=1)
			y = pm.polyNormalPerVertex (component, query=1, y=1)
			z = pm.polyNormalPerVertex (component, query=1, z=1)
			xyz = [sum(x) / float(len(x)), sum(y) / float(len(y)), sum(z) / float(len(z))] #get average

		elif ".e" in str(component):
			componentName = str(component).split(".")[0]
			vertices = pm.polyInfo (component, edgeToVertex=1)[0]
			vertices = vertices.split()
			vertices = [componentName+".vtx["+vertices[2]+"]",componentName+".vtx["+vertices[3]+"]"]
			x=[];y=[];z=[]
			for vertex in vertices:
				x_ = pm.polyNormalPerVertex (vertex, query=1, x=1)
				x.append(sum(x_) / float(len(x_)))
				y_ = pm.polyNormalPerVertex (vertex, query=1, y=1)
				x.append(sum(y_) / float(len(y_)))
				z_ = pm.polyNormalPerVertex (vertex, query=1, z=1)
				x.append(sum(z_) / float(len(z_)))
			xyz = [sum(x) / float(len(x)), sum(y) / float(len(y)), sum(z) / float(len(z))] #get average

		else:# elif ".f" in str(component):
			xyz = pm.polyInfo (component, faceNormals=1)
			xyz = xyz[0].split()
			xyz = [float(xyz[2]), float(xyz[3]), float(xyz[4])]

		if alignToNormal: #normal constraint
			normal = pm.mel.eval("unit <<"+str(xyz[0])+", "+str(xyz[1])+", "+str(xyz[2])+">>;") #normalize value using MEL
			# normal = [round(i-min(xyz)/(max(xyz)-min(xyz)),6) for i in xyz] #normalize and round value using python

			constraint = pm.normalConstraint(component, object_,aimVector=normal,upVector=[0,1,0],worldUpVector=[0,1,0],worldUpType="vector") # "scene","object","objectrotation","vector","none"
			pm.delete(constraint) #orient object_ then remove constraint.

		vertexPoint = pm.xform (component, query=1, translation=1) #average vertex points on destination to get component center.
		x = vertexPoint[0::3]
		y = vertexPoint[1::3]
		z = vertexPoint[2::3]

		return list(round(sum(x) / float(len(x)),4), round(sum(y) / float(len(y)),4), round(sum(z) / float(len(z)),4))


	@classmethod
	def getBoundingBoxValue(cls, obj, value='sizeX|sizeY|sizeZ'):
		'''Get information of the given object(s) bounding box.

		:Parameters:
			obj (str)(obj)(list) = The object(s) to query.
				Multiple objects will be treated as a combined bounding box.
			value (str) = The type of value to return. Multiple types can be given
				separated by '|'. The order given determines the return order.
				valid (case insensitive): 'xmin', 'xmax', 'ymin', 'ymax', 
				'zmin', 'zmax', 'sizex', 'sizey', 'sizez', 'volume', 'center'

		:Return:
			(float)(list) Dependant on args.

		ex. call: getBoundingBoxValue(sel, 'center|volume') #returns: [[171.9106216430664, 93.622802734375, -1308.4896240234375], 743.2855185396038]
		ex. call: getBoundingBoxValue(sel, 'sizeY') #returns: 144.71902465820312
		'''
		if '|' in value: #use recursion to construct the list using each value.
			return [cls.getBoundingBoxValue(obj, i) for i in value.split('|')]

		v = value.lower()
		for o in pm.ls(obj, objectsOnly=True):
			xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(o)
			if v=='xmin': return xmin
			elif v=='xmax': return xmax
			elif v=='ymin': return ymin
			elif v=='ymax': return ymax
			elif v=='zmin': return zmin
			elif v=='zmax': return zmax
			elif v=='sizex': return xmax-xmin
			elif v=='sizey': return ymax-ymin
			elif v=='sizez': return zmax-zmin
			elif v=='volume': return (xmax-xmin)*(ymax-ymin)*(zmax-zmin)
			elif v=='center': return [(xmin+xmax)/2.0, (ymin+ymax)/2.0, (zmin+zmax)/2.0]


	@classmethod
	def sortByBoundingBoxValue(cls, objects, value='volume', descending=True, returnWithValue=False):
		'''Sort the given objects by their bounding box value.

		:Parameters:
			objects (list) = The objects to sort.
			value (str) = See 'getBoundingBoxInfo' 'value' parameter.
					ex. 'xmin', 'xmax', 'sizex', 'volume', 'center' ..
			descending (bool) = Sort the list from the largest value down.
			returnWithValue (bool) = Instead of just the object; return a 
					list of two element tuples as [(<value>, <obj>)].
		:Return:
			(list)
		'''
		valueAndObjs=[]
		for obj in pm.ls(objects, objectsOnly=True):
			v = cls.getBoundingBoxValue(obj, value)
			valueAndObjs.append((v, obj))

		sorted_ = sorted(valueAndObjs, key=lambda x: int(x[0]), reverse=descending)
		if returnWithValue:
			return sorted_
		return [obj for v, obj in sorted_]


	@staticmethod
	def matchScale(objectsA, objectsB, scale=True, average=False):
		'''Scale each of the given objects to the combined bounding box of a second set of objects.

		:Parameters:
			objectsA (str)(obj)(list) = The object(s) to scale.
			objectsB (str)(obj)(list) = The object(s) to get a bounding box size from.
			scale (bool) = Scale the objects. Else, just return the scale value.
			average (bool) = Average the result across all axes.

		:Return:
			(list) scale values as [x,y,z,x,y,z...]
		'''
		to = pm.ls(objectsA, flatten=True)
		frm = pm.ls(objectsB, flatten=True)

		xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(frm)
		ax, ay, az = aBoundBox = [xmax-xmin, ymax-ymin, zmax-zmin]

		result=[]
		for obj in to:

			xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(obj)
			bx, by, bz = bBoundBox = [xmax-xmin, ymax-ymin, zmax-zmin]

			oldx, oldy, oldz = bScaleOld = pm.xform(obj, q=1, s=1, r=1)

			try:
				diffx, diffy, diffz = boundDifference = [ax/bx, ay/by, az/bz]
			except ZeroDivisionError as error:
				diffx, diffy, diffz = boundDifference = [1, 1, 1]

			bScaleNew = [oldx*diffx, oldy*diffy, oldz*diffz]

			if average:
				bScaleNew = [sum(bScaleNew)/len(bScaleNew) for _ in range(3)]

			if scale:
				pm.xform(obj, scale=bScaleNew)

			[result.append(i) for i in bScaleNew]

		return result


	@staticmethod
	@undo
	def alignVertices(mode, average=False, edgeloop=False):
		'''Align vertices.

		:Parameters:
			mode (int) = possible values are align: 0-YZ, 1-XZ, 2-XY, 3-X, 4-Y, 5-Z, 6-XYZ 
			average (bool) = align to average of all selected vertices. else, align to last selected
			edgeloop (bool) = align vertices in edgeloop from a selected edge

		ex. call: alignVertices(mode=3, average=True, edgeloop=True)
		'''
		# pm.undoInfo (openChunk=True)
		selectTypeEdge = pm.selectType (query=True, edge=True)

		if edgeloop:
			pm.mel.SelectEdgeLoopSp() #select edgeloop

		pm.mel.PolySelectConvert(3) #convert to vertices

		selection = pm.ls(selection=1, flatten=1)
		lastSelected = pm.ls(tail=1, selection=1, flatten=1)
		alignTo = pm.xform(lastSelected, query=1, translation=1, worldSpace=1)
		alignX = alignTo[0]
		alignY = alignTo[1]
		alignZ = alignTo[2]
		
		if average:
			xyz = pm.xform(selection, query=1, translation=1, worldSpace=1)
			x = xyz[0::3]
			y = xyz[1::3]
			z = xyz[2::3]
			alignX = float(sum(x))/(len(xyz)/3)
			alignY = float(sum(y))/(len(xyz)/3)
			alignZ = float(sum(z))/(len(xyz)/3)

		if len(selection)<2:
			if len(selection)==0:
				viewportMessage("No vertices selected")
			viewportMessage("Selection must contain at least two vertices")

		for vertex in selection:
			vertexXYZ = pm.xform(vertex, query=1, translation=1, worldSpace=1)
			vertX = vertexXYZ[0]
			vertY = vertexXYZ[1]
			vertZ = vertexXYZ[2]
			
			modes = {
				0:(vertX, alignY, alignZ), #align YZ
				1:(alignX, vertY, alignZ), #align XZ
				2:(alignX, alignY, vertZ), #align XY
				3:(alignX, vertY, vertZ),
				4:(vertX, alignY, vertZ),
				5:(vertX, vertY, alignZ),
				6:(alignX, alignY, alignZ), #align XYZ
			}

			pm.xform(vertex, translation=modes[mode], worldSpace=1)

		if selectTypeEdge:
			pm.selectType (edge=True)
		# pm.undoInfo (closeChunk=True)


	@staticmethod
	def orderByDistance(objects, point=[0, 0, 0], reverse=False):
		'''Order the given objects by their distance from the given point.

		:Parameters:
			objects (str)(int)(list) = The object(s) to order.
			point (list) = A three value float list x, y, z.
			reverse (bool) = Reverse the naming order. (Farthest object first)

		:Return:
			(list) ordered objects
		'''
		distance={}
		for obj in pm.ls(objects, flatten=1):
			xmin, ymin, zmin, xmax, ymax, zmax = pm.xform(obj, q=1, boundingBox=1)
			bb_pos = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
			bb_dist = mathtk.getDistBetweenTwoPoints(point, bb_pos)

			distance[bb_dist] = obj

		result = [distance[i] for i in sorted(distance)]
		return list(reversed(result)) if reverse else result


	@classmethod
	def matchTransformByVertexOrder(cls, source, target):
		'''Match transform and rotation on like objects by using 3 vertices from each object.
		The vertex order is transferred to the target object(s).

		:Parameters:
			source (str)(obj) = The object to move from.
			target (str)(obj) = The object to move to.
		'''
		pm.polyTransfer(source, alternateObject=target, vertices=2) #vertices positions are copied from the target object.

		source_verts = [pm.ls(source, objectsOnly=1)[0].verts[i] for i in range(3)]
		target_verts = [pm.ls(target, objectsOnly=1)[0].verts[i] for i in range(3)]

		cls.snap3PointsTo3Points(source_verts+target_verts)


	@staticmethod
	def snap3PointsTo3Points(vertices):
		'''Move and align the object defined by the first 3 points to the last 3 points.

		:Parameters:
			vertices (list) = The first 3 points must be on the same object (i.e. it is the 
						object to be transformed). The second set of points define 
						the position and plane to transform to.
		'''
		import math

		vertices = pm.ls(vertices, flatten=True)
		objectToMove = pm.ls(vertices[:3], objectsOnly=True)

		# get the world space position of each selected point object
		p0, p1, p2 = [pm.pointPosition(v) for v in vertices[0:3]]
		p3, p4, p5 = [pm.pointPosition(v) for v in vertices[3:6]]

		dx, dy, dz = distance = [ # calculate the translation amount - the first point on each pair is the point to use for translation.
			p3[0] - p0[0],
			p3[1] - p0[1],
			p3[2] - p0[2]
		]

		pm.move(dx, dy, dz, objectToMove, relative=1) # move the first object by that amount.

		a1x, a1y, a1z = axis1 = [ # define the two vectors for each pair of points.
			p1[0] - p0[0],
			p1[1] - p0[1],
			p1[2] - p0[2]
		]
		a2x, a2y, a2z = axis2 = [
			p4[0] - p3[0],
			p4[1] - p3[1],
			p4[2] - p3[2]
		]

		# get the angle (in radians) between the two vectors and the axis of rotation. This is used to move axis1 to match axis2
		dp = mathtk.dotProduct(axis1, axis2, 1)
		dp = mathtk.clamp(-1.0, 1.0, dp)
		angle = math.acos(dp)
		crossProduct = mathtk.crossProduct(axis1, axis2, 1, 1)

	 	# rotate the first object about the pivot point (the pivot is defined by the first point from the second pair of points. i.e. point 3 from the inputs above)
		rotation = mathtk.xyzRotation(angle, crossProduct)
		pm.rotate(objectToMove, str(rotation[0])+'rad', str(rotation[1])+'rad', str(rotation[2])+'rad', pivot=p3, relative=1)

		# Get these points again since they may have moved
		p2 = pm.pointPosition(vertices[2])
		p5 = pm.pointPosition(vertices[5])

		axis3 = [
			p2[0] - p4[0],
			p2[1] - p4[1],
			p2[2] - p4[2]
		]
		axis4 = [
			p5[0] - p4[0],
			p5[1] - p4[1],
			p5[2] - p4[2]
		]

		axis2 = mathtk.normalize(axis2)

		# Get the dot product of axis3 on axis2
		dp = mathtk.dotProduct(axis3, axis2, 0)
		axis3[0] = p2[0] - p4[0] + dp * axis2[0]
		axis3[1] = p2[1] - p4[1] + dp * axis2[1]
		axis3[2] = p2[2] - p4[2] + dp * axis2[2]

		# Get the dot product of axis4 on axis2
		dp = mathtk.dotProduct(axis4, axis2, 0)
		axis4[0] = p5[0] - p4[0] + dp * axis2[0]
		axis4[1] = p5[1] - p4[1] + dp * axis2[1]
		axis4[2] = p5[2] - p4[2] + dp * axis2[2]

		# rotate the first object again, this time about the 2nd axis so that the 3rd point is in the same plane. ie. match up axis3 with axis4.
		dp = mathtk.dotProduct(axis3, axis4, 1)
		dp = mathtk.clamp(-1.0, 1.0, dp)
		angle = math.acos(dp)

		# reverse the angle if the cross product is in the -ve axis direction
		crossProduct = mathtk.crossProduct(axis3, axis4, 1, 1)
		dp = mathtk.dotProduct(crossProduct, axis2, 0)
		if dp < 0:
			angle = -angle

		rotation = mathtk.xyzRotation(angle, axis2)
		pm.rotate(objectToMove, str(rotation[0])+'rad', str(rotation[1])+'rad', str(rotation[2])+'rad', pivot=p4, relative=1)


	@staticmethod
	def isOverlapping(objA, objB, tolerance=0.001):
		'''Check if the vertices in objA and objB are overlapping within the given tolerance.

		:Parameters:
			objA (str)(obj) = The first object to check. Object can be a component.
			objB (str)(obj) = The second object to check. Object can be a component.
			tolerance (float) = The maximum search distance before a vertex is considered not overlapping.

		:Return:
			(bool)
		'''
		vert_setA = pm.ls(pm.polyListComponentConversion(objA, toVertex=1), flatten=1)
		vert_setB = pm.ls(pm.polyListComponentConversion(objB, toVertex=1), flatten=1)

		closestVerts = comptk.getClosestVerts(vert_setA, vert_setB, tolerance=tolerance)

		return True if vert_setA and len(closestVerts)==len(vert_setA) else False	

# -----------------------------------------------









# -----------------------------------------------

if __name__=='__main__':
	pass


# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)









# print (__name__) #module name
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated: -----------------------------------
