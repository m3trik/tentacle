# !/usr/bin/python
# coding=utf-8



class Mathutils():
	'''
	'''

	@staticmethod
	def areSimilar(a, b, tol=0.0):
		'''Check if the two numberical values are within a given tolerance.
		Supports nested lists.

		:parameters:
			a (obj)(list) = The first object(s) to compare.
			b (obj)(list) = The second object(s) to compare.
			tol (float) = The maximum allowed variation between the values.

		:return:
			(bool)
		'''
		lst = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure the arg is a list.

		func = lambda a, b: abs(a-b)<=tol if isinstance(a, (int, float)) else True if isinstance(a, (list, set, tuple)) and areSimilar(a, b, tol) else a==b
		return all(map(func, lst(a), lst(b)))


	@staticmethod
	def randomize(lst, ratio=1.0):
		'''Random elements from the given list will be returned with a quantity determined by the given ratio.
		A value of 0.5 will return 50% of the original elements in random order.

		:Parameters:
			lst (list) = A list to randomize.
			ratio (float) = A value of 0.0-1. With 0 representing 0% and 1 representing 100% of the given elements returned in random order. (default: 100%)

		:Return:
			(list)
		'''
		import random

		lower, upper = 0.0, ratio if ratio<=1 else 1.0 #end result range.
		normalized = lower + (upper - lower) * len(lst) #returns a float value.
		randomized = random.sample(lst, int(normalized))

		return randomized


	@staticmethod
	def getVectorFromTwoPoints(startPoint, endPoint):
		'''Get a directional vector from a given start and end point.

		:Parameters:
			startPoint (tuple) = The vectors start point as x, y, z values.
			endPoint (tuple) = The vectors end point as x, y, z values.

		:Return:
			(tuple) vector.
		'''
		x1, y1, z1 = startPoint
		x2, y2, z2 = endPoint

		result = (
			x1 - x2,
			y1 - y2,
			z1 - z2,
		)

		return result


	@staticmethod
	def clamp(x=0.0, minimum=0.0, maximum=1.0):
		'''Clamps the value x between min and max.

		:Parameters:
			x (float) = 
			minimum (float) = 
			maximum (float) = 

		:Return:
			(float)
		'''
		if minimum < maximum:
			realmin = minimum
			realmax = maximum
		else:
			realmin = maximum
			realmax = minimum

		if x < realmin:
			result = realmin
		elif x > realmax:
			result = realmax
		else:
			result = x

		return result


	@classmethod
	def normalize(cls, vector, amount=1):
		'''Normalize a vector

		:Parameters:
			vector (vector) = The vector to normalize.
			amount (float) = (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.
		
		:Return:
			(tuple)
		'''
		length = cls.getMagnitude(vector)
		x, y, z = vector

		result = (
			x /length *amount,
			y /length *amount,
			z /length *amount
		)

		return result


	@staticmethod
	def normalized(vector3):
		'''Normalize a 3 dimensional vector using numpy.

		:Parameters:
			vector3 (vector) = A three point vector. ie. [-0.03484325110912323, 0.0, -0.5519591569900513]

		:Return:
			(vector)
		'''
		import numpy

		length = numpy.sqrt(sum(vector3[i] * vector3[i] for i in range(3)))
		result = [vector3[i] / length for i in range(3)]

		return result


	@staticmethod
	def getMagnitude(vector):
		'''Get the magnatude (length) of a given vector.

		:Parameters:
			vector (tuple) = Vector xyz values.

		:Return:
			(float)
		'''
		from math import sqrt

		x, y, z = vector
		length = sqrt(x**2 + y**2 + z**2)

		return length


	@classmethod
	def dotProduct(cls, v1, v2, normalizeInputs=False):
		'''Returns the dot product of two 3D float arrays.  If $normalizeInputs
		is set then the vectors are normalized before the dot product is calculated.

		:Parameters:
			v1 (list) = The first 3 point vector. 
			v2 (list) = The second 3 point vector.
			normalizeInputs (int) = Normalize v1, v2 before calculating the point float list.

		:Return:
			(float) Dot product of the two vectors.
		'''
		if normalizeInputs: #normalize the input vectors
			v1 = cls.normalize(v1)
			v2 = cls.normalize(v2)

		return sum((a*b) for a, b in zip(v1, v2)) #the dot product


	@classmethod
	def crossProduct(cls, v1, v2, normalizeInputs=False, normalizeResult=False):
		'''Given two float arrays of 3 values each, this procedure returns
		the cross product of the two arrays as a float array of size 3.

		:Parmeters:
			v1 (list) = The first 3 point vector. 
			v2 (list) = The second 3 point vector.
			normalizeInputs (bool) = Normalize v1, v2 before calculating the point float list.
			normalizeResult (bool) = Normalize the return value.

		:Return:
			(list) The cross product of the two vectors.
		'''
		if normalizeInputs: #normalize the input vectors
			v1 = cls.normalize(v1)
			v2 = cls.normalize(v2)

		cross = [ #the cross product
			v1[1]*v2[2] - v1[2]*v2[1],
			v1[2]*v2[0] - v1[0]*v2[2],
			v1[0]*v2[1] - v1[1]*v2[0]
		]

		if normalizeResult: #normalize the cross product result
			cross = cls.normalize(cross)

		return cross


	@classmethod
	def getCrossProduct(cls, p1, p2, p3=None, normalize=0):
		'''Get the cross product of two vectors, using 2 vectors, or 3 points.

		:Parameters:
			p1 (vector)(point) = xyz point value as a tuple.
			p2 (vector)(point) = xyz point value as a tuple.
			p3 (point) = xyz point value as a tuple (used when working with point values instead of vectors).
			normalize (float) = (0) Do not normalize. (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.

		:Return:
			(tuple)
		'''
		if p3 is not None: #convert points to vectors and unpack.
			v1x, v1y, v1z = (
				p2[0] - p1[0],
				p2[1] - p1[1], 
				p2[2] - p1[2]
			)

			v2x, v2y, v2z = (
				p3[0] - p1[0], 
				p3[1] - p1[1], 
				p3[2] - p1[2]
			)
		else: #unpack vector.
			v1x, v1y, v1z = p1
			v2x, v2y, v2z = p2

		result = (
			(v1y*v2z) - (v1z*v2y), 
			(v1z*v2x) - (v1x*v2z), 
			(v1x*v2y) - (v1y*v2x)
		)

		if normalize:
			result = cls.normalize(result, normalize)

		return result


	@classmethod
	def movePointRelative(cls, p, d, v=None):
		'''Move a point relative to it's current position.

		:Parameters:
			p (tuple) = A points x, y, z values.
			d (tuple)(float) = The distance to move. (use a float value when moving along a vector)
			v (tuple) = Optional: A vectors x, y, z values can be given to move the point along that vector.
		'''
		x, y, z = p

		if v is not None: #move along a vector if one is given.
			if not isinstance(d, (float, int)):
				print('# Warning: The distance parameter requires an integer or float value when moving along a vector. {} given. #'.format(type(d)))
			dx, dy, dz = cls.normalize(v, d)
		else:
			dx, dy, dz = d

		result = (
			x + dx,
			y + dy,
			z + dz
		)

		return result


	@classmethod
	def movePointAlongVectorTowardPoint(cls, point, toward, vect, dist):
		'''Move a point along a given vector in the direction of another point.

		:Parameters:
			point (tuple) = The point to move given as (x,y,z).
			toward (tuple) = The point to move toward.
			vect (tuple) = A vector to move the point along.
			dist (float) = The linear amount to move the point.
		
		:Return:
			(tuple) point.
		'''
		for i in [dist, -dist]: #move in pos and neg direction, and determine which is moving closer to the reference point.
			p = cls.movePointRelative(point, i, vect)
			d = cls.getDistanceBetweenTwoPoints(p, toward)
			if d<=d:
				result = p

		return result


	@classmethod
	def getDistanceBetweenTwoPoints(cls, p1, p2):
		'''Get the vector between two points, and return it's magnitude.

		:Parameters:
			p1 (tuple) = Point 1.
			p2 (tuple) = Point 2.

		:Return:
			(float)
		'''
		from math import sqrt
		
		p1x, p1y, p1z = p1
		p2x, p2y, p2z = p2

		vX = p1x - p2x
		vY = p1y - p2y
		vZ = p1z - p2z

		vector = (vX, vY, vZ)
		length = cls.getMagnitude(vector)

		return length


	@staticmethod
	def getCenterPointBetweenTwoPoints(p1, p2):
		'''Get the point in the middle of two given points.

		:Parameters:
			p1 (tuple) = Point as x,y,z values.
			p2 (tuple) = Point as x,y,z values.

		:Return:
			(tuple)
		'''
		Ax, Ay, Az = p1
		Bx, By, Bz = p2

		result = (
			(Ax+Bx) /2,
			(Ay+By) /2,
			(Az+Bz) /2
		)

		return result


	@classmethod
	def getAngleFrom2Vectors(cls, v1, v2, degree=False):
		'''Get an angle from two given vectors.

		:Parameters:
			v1 (point) = A vectors xyz values as a tuple.
			v2 (point) = A vectors xyz values as a tuple.
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(float)
		'''
		from math import acos, degrees

		def length(v):
			return (cls.dotProduct(v, v))**0.5

		result = acos(cls.dotProduct(v1, v2) / (length(v1) * length(v2)))

		if degree:
			result = round(degrees(result), 2)
		return result


	@staticmethod
	def getAngleFrom3Points(a, b, c, degree=False):
		'''Get the opposing angle from 3 given points.

		:Parameters:
			a (point) = A points xyz values as a tuple.
			b (point) = A points xyz values as a tuple.
			c (point) = A points xyz values as a tuple.
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(float)
		'''
		from math import sqrt, acos, degrees

		ba = [aa-bb for aa,bb in zip(a,b)] #create vectors from points
		bc = [cc-bb for cc,bb in zip(c,b)]

		nba = sqrt(sum((x**2.0 for x in ba))) #normalize vector
		ba = [x/nba for x in ba]

		nbc = sqrt(sum((x**2.0 for x in bc)))
		bc = [x/nbc for x in bc]

		scalar = sum((aa*bb for aa,bb in zip(ba,bc))) #get scalar from normalized vectors

		angle = acos(scalar)#get the angle in radian

		if degree:
			angle = round(degrees(angle), 2)
		return angle


	@staticmethod
	def getTwoSidesOfASATriangle(a1, a2, s, unit='degrees'):
		'''Get the length of two sides of a triangle, given two angles, and the length of the side in-between.

		:Parameters:
			a1 (float) = Angle in radians or degrees. (unit flag must be set if value given in radians)
			a2 (float) = Angle in radians or degrees. (unit flag must be set if value given in radians)
			s (float) = The distance of the side between the two given angles.
			unit (str) = Specify whether the angle values are given in degrees or radians. (valid: 'radians', 'degrees')(default: degrees)

		:Return:
			(tuple)
		'''
		from math import sin, radians

		if unit=='degrees':
			a1, a2 = radians(a1), radians(a2)

		a3 = 3.14159 - a1 - a2

		result = (
			(s/sin(a3)) * sin(a1),
			(s/sin(a3)) * sin(a2)
		)

		return result


	@classmethod
	def xyzRotation(cls, theta, axis, rotation=[]):
		'''Get the rotation about the X,Y,Z axes (in rotation) given 
		an angle for rotation (in radians) and an axis about which to 
		do the rotation.

		:Parameters:
			theta (float) = 
			axis (list) = X, Y, Z float values.
			rotation (list) = 

		:Return:
			(list) 3 point rotation.
		'''
		import math

		#set up the xyzw quaternion values
		theta *= 0.5
		w = math.cos(theta)
		factor = math.sin(theta)
		axisLen2 = cls.dotProduct(axis, axis, 0)

		if (axisLen2 != 1.0 and axisLen2 != 0.0):
			factor /= math.sqrt(axisLen2)
		x, y, z = factor * axis[0], factor * axis[1], factor * axis[2]

		#setup rotation in a matrix
		ww, xx, yy, zz = w*w, x*x, y*y, z*z
		s = 2.0 / (ww + xx + yy + zz)
		xy, xz, yz, wx, wy, wz = x*y, x*z, y*z, w*x, w*y, w*z
		matrix = [
			1.0 - s * (yy + zz),
			s * (xy + wz),
			s * (xz - wy),
			None, None,
			1.0 - s * (xx + zz),
			s * (yz + wx),
			None, None,
			s * (yz - wx),
			1.0 - s * (xx + yy)
		]

		#get x,y,z values for rotation
		cosB = math.sqrt(matrix[0]*matrix[0] + matrix[1]*matrix[1])
		if (cosB > 1.0e-10):
			pi = 3.14159265
	 
			a, b, c = solution1 = [
				math.atan2(matrix[6], matrix[10]),
				math.atan2(-matrix[2], cosB),
				math.atan2(matrix[1], matrix[0])
			]

			solution2 = [
				a + (pi if a < pi else -pi),
				(pi if b > -pi else -pi) - b,
				c + (pi if c < pi else -pi)
			]

			if sum([abs(solution2[0]), abs(solution2[1]), abs(solution2[2])]) < sum([abs(solution1[0]), abs(solution1[1]), abs(solution1[2])]):

				rotation = solution2
			else:
				rotation = solution1

		else:
			rotation = [
				math.atan2(-matrix[9], matrix[5]),
				math.atan2(-matrix[2], cosB),
				0.0
			]

		return rotation