# !/usr/bin/python
# coding=utf-8
import itertk


class Mathtls():
	'''
	'''
	@staticmethod
	def getVectorFromTwoPoints(startPoint, endPoint):
		'''Get a directional vector from a given start and end point.

		:Parameters:
			startPoint (tuple) = A start point given as (x,y,z).
			endPoint (tuple) = An end point given as (x,y,z).

		:Return:
			(tuple) vector.

		ex. call: getVectorFromTwoPoints((1, 2, 3), (1, 1, -1)) #returns: (0, -1, -4)
		'''
		ax, ay, az = startPoint
		bx, by, bz = endPoint

		return (bx - ax, by - ay, bz - az)


	@staticmethod
	def clamp(n=0.0, minimum=0.0, maximum=1.0):
		'''Clamps the value x between min and max.

		:Parameters:
			n (float)(tuple) = The numeric value to clamp.
			minimum (float) = Clamp min value.
			maximum (float) = Clamp max value.

		:Return:
			(float)

		ex. call: clamp(range(10), 3, 7) #returns: [3, 3, 3, 3, 4, 5, 6, 7, 7, 7]
		'''
		result=[]
		for n_ in itertk.makeList(n):
			result.append(max(minimum, min(n_, maximum)))

		return itertk.formatReturn(result, n)


	@classmethod
	def normalize(cls, vector, amount=1):
		'''Normalize a 2 or 3 dimensional vector.

		:Parameters:
			vector (tuple) = A two or three point vector. ie. (-0.03484, 0.0, -0.55195)
			amount (float) = (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.

		:Return:
			(tuple)

		ex. call: normalize((2, 3, 4)) #returns: (0.3713906763541037, 0.5570860145311556, 0.7427813527082074)
		ex. call: normalize((2, 3)) #returns: (0.5547001962252291, 0.8320502943378437)
		ex. call: normalize((2, 3, 4), 2) #returns: (0.7427813527082074, 1.1141720290623112, 1.4855627054164149)
		'''
		n = len(vector) #determine 2 or 3d vector.
		length = cls.getMagnitude(vector)
		return tuple(vector[i] / length * amount for i in range(n))


	@staticmethod
	def getMagnitude(vector):
		'''Get the magnatude (length) of a given vector.

		:Parameters:
			vector (tuple) = A two or three point vector. ie. (-0.03484, 0.0, -0.55195)

		:Return:
			(float)

		ex. call: getMagnitude((2, 3, 4)) #returns: 5.385164807134504
		ex. call: getMagnitude((2, 3)) #returns: 3.605551275463989
		'''
		from math import sqrt

		n = len(vector) #determine 2 or 3d vector.
		return sqrt(sum(vector[i] * vector[i] for i in range(n)))


	@classmethod
	def dotProduct(cls, v1, v2, normalizeInputs=False):
		'''Returns the dot product of two 3D float arrays.  If $normalizeInputs
		is set then the vectors are normalized before the dot product is calculated.

		:Parameters:
			v1 (tuple) = The first 3 point vector. 
			v2 (tuple) = The second 3 point vector.
			normalizeInputs (int) = Normalize v1, v2 before calculating the point float list.

		:Return:
			(float) Dot product of the two vectors.

		ex. call: dotProduct((1, 2, 3), (1, 1, -1)) #returns: 0
		ex. call: dotProduct((1, 2), (1, 1)) #returns: 3
		'''
		if normalizeInputs: #normalize the input vectors
			v1 = cls.normalize(v1)
			v2 = cls.normalize(v2)

		return sum((a*b) for a, b in zip(v1, v2)) #the dot product


	@classmethod
	def crossProduct(cls, a, b, c=None, normalize=0):
		'''Get the cross product of two vectors, using two 3d vectors, or 3 points.

		:Parameters:
			a (tuple) = A point represented as x,y,z or a 3 point vector.
			b (tuple) = A point represented as x,y,z or a 3 point vector.
			c (tuple) = A point represented as x,y,z (used only when working with 3 point values instead of 2 vectors).
			normalize (float) = (0) Do not normalize. (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.

		:Return:
			(tuple)

		ex. call: crossProduct((1, 2, 3), (1, 1, -1)) #returns: (-5, 4, -1),
		ex. call: crossProduct((3, 1, 1), (1, 4, 2), (1, 3, 4)) #returns: (7, 4, 2),
		ex. call: crossProduct((1, 2, 3), (1, 1, -1), None, 1) #returns: (-0.7715167498104595, 0.6172133998483676, -0.1543033499620919)
		'''
		if c is not None: #convert points to vectors and unpack.
			a = cls.getVectorFromTwoPoints(a, b)
			b = cls.getVectorFromTwoPoints(b, c)

		ax, ay, az = a
		bx, by, bz = b

		result = (
			(ay*bz) - (az*by), 
			(az*bx) - (ax*bz), 
			(ax*by) - (ay*bx)
		)

		if normalize:
			result = cls.normalize(result, normalize)

		return result


	@classmethod
	def movePointRelative(cls, p, d, v=None):
		'''Move a point relative to it's current position.

		:Parameters:
			p (tuple) = A points x, y, z values.
			d (tuple)(float) = The distance to move. Use a float value when moving along a vector, 
						and a point value to move in a given distance.
			v (tuple) = Optional: A vectors x, y, z values can be given to move the point along that vector.

		:Return:
			(tuple) point.

		ex. call: movePointRelative((0, 5, 0), (0, 5, 0)) #returns: (0, 10, 0)
		ex. call: movePointRelative((0, 5, 0), 5, (0, 1, 0)) #returns: (0, 10, 0)
		'''
		x, y, z = p

		if v is not None: #move along a vector if one is given.
			assert isinstance(d, (float, int)), '# Error: {}\n  The distance parameter requires an integer or float value when moving along a vector.\n  {} {} given. #'.format(__file__, type(d), d)
			dx, dy, dz = cls.normalize(v, d)
		else:
			assert isinstance(d, (list, tuple, set)), '# Error: {}\n  The distance parameter requires an list, tuple, set value when not moving along a vector.\n  {} {} given. #'.format(__file__, type(d), d)
			dx, dy, dz = d

		result = (
			x + dx,
			y + dy,
			z + dz
		)

		return result


	@classmethod
	def movePointAlongVectorRelativeToPoint(cls, p1, p2, vect, dist, toward=True):
		'''Move a point (p1) along a given vector toward or away from a given point (p2).

		:Parameters:
			p1 (tuple) = The point to move given as (x,y,z).
			p2 (tuple) = The point to move toward.
			vect (tuple) = A vector to move the point along.
			dist (float) = The linear amount to move the point.
			toward (bool) = Move the point toward or away from.
		
		:Return:
			(tuple) point.

		ex. call: movePointAlongVectorRelativeToPoint((0, 0, 0), (0, 10, 0), (0, 1, 0), 5) #returns: (0.0, 5.0, 0.0)
		ex. call: movePointAlongVectorRelativeToPoint((0, 0, 0), (0, 10, 0), (0, 1, 0), 5, False) #returns: (0.0, -15.0, 0.0)
		'''
		lowest=None
		for i in [dist, -dist]: #move in pos and neg direction, and determine which is moving closer to the reference point.
			p = cls.movePointRelative(p1, i, vect)
			d = cls.getDistBetweenTwoPoints(p, p2)
			if lowest is None or (d<lowest if toward else d>lowest):
				result, lowest = (p, d)

		return result


	@classmethod
	def getDistBetweenTwoPoints(cls, p1, p2):
		'''Get the vector between two points, and return it's magnitude.

		:Parameters:
			p1 (tuple) = A point given as (x,y,z).
			p2 (tuple) = A point given as (x,y,z).

		:Return:
			(float)

		ex. call: getDistBetweenTwoPoints((0, 10, 0), (0, 5, 0)) #returns: 5.0
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
			p1 (tuple) = A point given as (x,y,z).
			p2 (tuple) = A point given as (x,y,z).

		:Return:
			(tuple)

		ex. call: getCenterPointBetweenTwoPoints((0, 10, 0), (0, 5, 0)) #returns: (0.0, 7.5, 0.0)
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
			v1 (tuple) = A vectors xyz values as a tuple.
			v2 (tuple) = A vectors xyz values as a tuple.
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(float)

		ex. call: getAngleFrom2Vectors((1, 2, 3), (1, 1, -1)) #returns: 1.5707963267948966,
		ex. call: getAngleFrom2Vectors((1, 2, 3), (1, 1, -1), True) #returns: 90
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
			a (tuple) = A point given as (x,y,z).
			b (tuple) = A point given as (x,y,z).
			c (tuple) = A point given as (x,y,z).
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(float)

		ex. call: getAngleFrom3Points((1, 1, 1), (-1, 2, 3), (1, 4, -3)) #returns: 0.7904487543360762,
		ex. call: getAngleFrom3Points((1, 1, 1), (-1, 2, 3), (1, 4, -3), True) #returns: 45.29
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

		ex. call: getTwoSidesOfASATriangle(60, 60, 100) #returns: (100.00015320566493, 100.00015320566493)
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
	def xyzRotation(cls, theta, axis, rotation=[], degree=False):
		'''Get the rotation about the X,Y,Z axes (in rotation) given 
		an angle for rotation (in radians) and an axis about which to 
		do the rotation.

		:Parameters:
			theta (float) = The angular position of a vector in radians.
			axis (tuple) = The rotation axis given as float values (x,y,z).
			rotation (list) = 
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(tuple) 3 point rotation.

		ex. call: xyzRotation(2, (0, 1, 0)) #returns: [3.589792907376932e-09, 1.9999999964102069, 3.589792907376932e-09]
		ex. call: xyzRotation(2, (0, 1, 0), [], True) #returns: [0.0, 114.59, 0.0]
		'''
		from math import cos, sin, sqrt, atan2, degrees

		#set up the xyzw quaternion values
		theta *= 0.5
		w = cos(theta)
		factor = sin(theta)
		axisLen2 = cls.dotProduct(axis, axis, 0)

		if (axisLen2 != 1.0 and axisLen2 != 0.0):
			factor /= sqrt(axisLen2)
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
		cosB = sqrt(matrix[0]*matrix[0] + matrix[1]*matrix[1])
		if (cosB > 1.0e-10):
			pi = 3.14159265
	 
			a, b, c = solution1 = [
				atan2(matrix[6], matrix[10]),
				atan2(-matrix[2], cosB),
				atan2(matrix[1], matrix[0])
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
				atan2(-matrix[9], matrix[5]),
				atan2(-matrix[2], cosB),
				0.0
			]

		if degree:
			rotation = [round(degrees(r), 2) for r in rotation]
		return tuple(rotation)

# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)









if __name__=='__main__':
	pass



# -----------------------------------------------
# Notes
# -----------------------------------------------



# Deprecated ------------------------------------

# @classmethod
# def normalize(cls, vector, amount=1):
# 	'''Normalize a vector

# 	:Parameters:
# 		vector (vector) = The vector to normalize.
# 		amount (float) = (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.
	
# 	:Return:
# 		(tuple)
# 	'''
# 	length = cls.getMagnitude(vector)
# 	x, y, z = vector

# 	result = (
# 		x /length *amount,
# 		y /length *amount,
# 		z /length *amount
# 	)

# 	return result

	# @classmethod
	# def crossProduct(cls, v1, v2, normalizeInputs=False, normalizeResult=False):
	# 	'''Given two float arrays of 3 values each, this procedure returns
	# 	the cross product of the two arrays as a float array of size 3.

	# 	:Parmeters:
	# 		v1 (list) = The first 3 point vector. 
	# 		v2 (list) = The second 3 point vector.
	# 		normalizeInputs (bool) = Normalize v1, v2 before calculating the point float list.
	# 		normalizeResult (bool) = Normalize the return value.

	# 	:Return:
	# 		(tuple) The cross product of the two vectors.

	# 	ex. call: crossProduct((1, 2, 3), (1, 1, -1)) #returns: (-5, 4, -1)
	# 	ex. call: crossProduct((1, 2, 3), (1, 1, -1), True) #returns: (-0.7715167498104597, 0.6172133998483678, -0.15430334996209194)
	# 	ex. call: crossProduct((1, 2, 3), (1, 1, -1), False, True) #returns: (-0.7715167498104595, 0.6172133998483676, -0.1543033499620919)
	# 	'''
	# 	if normalizeInputs: #normalize the input vectors
	# 		v1 = cls.normalize(v1)
	# 		v2 = cls.normalize(v2)

	# 	cross = [ #the cross product
	# 		v1[1]*v2[2] - v1[2]*v2[1],
	# 		v1[2]*v2[0] - v1[0]*v2[2],
	# 		v1[0]*v2[1] - v1[1]*v2[0]
	# 	]

	# 	if normalizeResult: #normalize the cross product result
	# 		cross = cls.normalize(cross)

	# 	return tuple(cross)