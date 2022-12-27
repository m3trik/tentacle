# !/usr/bin/python
# coding=utf-8
import os, sys
import unittest
import inspect

import pymel.core as pm

from tentacle.slots.maya.mayatk import *
import test


sfr = pm.melGlobals['cmdScrollFieldReporter']
pm.cmdScrollFieldReporter(sfr, edit=1, clear=1)


class Main(unittest.TestCase):
	'''
	'''
	def perform_test(self, case):
		'''
		'''
		for expression, expected_result in case.items():
			m = str(expression).split('(')[0] #ie. 'self.setCase' from "self.setCase('xxx', 'upper')"

			try:
				path = os.path.abspath(inspect.getfile(eval(m)))
			except TypeError as error:
				path = ''

			result = eval(expression)
			self.assertEqual(
				result, 
				expected_result, 
				"\n\nError: {}\n  Call:     {}\n  Expected: {} {}\n  Returned: {} {}".format(path, expression.replace('self.', '', 1), type(expected_result), expected_result, type(result), result)
			)


class Xformtk_test(Main, Xformtk):
	'''
	'''
	# Tear down the any previous test by creating a new scene:
	pm.mel.file(new=True, force=True)

	# assemble the test scene:
	if not pm.objExists('cube1'):
		cube1 = pm.polyCube(width=5, height=5, depth=5, subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1, name='cube1')

	if not pm.objExists('cube2'):
		cube2 = pm.polyCube(width=2, height=4, depth=8, subdivisionsX=3, subdivisionsY=3, subdivisionsZ=3, name='cube2')

	if not pm.objExists('sph'):
		sph = pm.polySphere(radius=5, subdivisionsX=12, subdivisionsY=12, name='sph')

	def test_moveTo(self):
		'''
		'''
		self.perform_test({
			"self.moveTo('cube1', 'cube2')": None,
		})

	def test_dropToGrid(self):
		'''
		'''
		self.perform_test({
			"self.dropToGrid('cube1', align='Min', origin=True, centerPivot=True, freezeTransforms=True)": None,
		})

	def test_resetTranslation(self):
		'''
		'''
		self.perform_test({
			"self.resetTranslation('cube1')": None,
		})

	def test_setTranslationToPivot(self):
		'''
		'''
		self.perform_test({
			"self.setTranslationToPivot('cube1')": None,
		})

	def test_alignPivotToSelection(self):
		'''
		'''
		self.perform_test({
			"self.alignPivotToSelection('cube1', 'cube2')": None,
		})

	def test_aimObjectAtPoint(self):
		'''
		'''
		self.perform_test({
			"self.aimObjectAtPoint(['cube1', 'cube2'], (0, 15, 15))": None,
		})

	def test_rotateAxis(self):
		'''
		'''
		self.perform_test({
			"self.rotateAxis(['cube1', 'cube2'], (0, 15, 15))": None,
		})

	def test_getOrientation(self):
		'''
		'''
		self.perform_test({
			"self.getOrientation('cube1')": ([1, 0, 0], [0, 1, 0], [0, 0, 1]),
		})

	def test_getDistanceBetweenTwoObjects(self):
		'''
		'''
		self.dropToGrid(['cube1', 'cube2'], origin=True, centerPivot=True)
		pm.move('cube2', 0, 0, 15)

		self.perform_test({
			"self.getDistanceBetweenTwoObjects('cube1', 'cube2')": 15,
		})

	def test_getCenterPoint(self):
		'''
		'''
		self.perform_test({
			"self.getCenterPoint('sph')": (0, 0, 0),
			"self.getCenterPoint('sph.vtx[*]')": (0, 0, 0),
		})


	def test_getBoundingBoxValue(self):
		'''
		'''
		self.perform_test({
			"self.getBoundingBoxValue('sph')": (10, 10, 10),
		})

	def test_sortByBoundingBoxValue(self):
		'''
		'''
		self.perform_test({
			"str(self.sortByBoundingBoxValue(['sph.vtx[0]', 'sph.f[0]']))": "[MeshFace('sphShape.f[0]'), MeshVertex('sphShape.vtx[0]')]",
		})

	def test_matchScale(self):
		'''
		'''
		self.perform_test({
			"self.matchScale('cube1', 'cube2', scale=False)": [1.3063946090989371, 0.539387725343009, 0.539387708993454],
		})

	def test_snap3PointsTo3Points(self):
		'''
		'''
		self.perform_test({
			# "self.snap3PointsTo3Points()": None,
		})

	def test_isOverlapping(self):
		'''
		'''
		self.perform_test({
			# "self.isOverlapping()": None,
		})

	def test_alignVertices(self):
		'''
		'''
		self.perform_test({
			# "self.alignVertices()": None,
		})

# --------------------------------

if __name__=='__main__':

	unittest.main(exit=False)






# --------------------------------
# Notes
# --------------------------------

# """
# def test_(self):
# 	'''
# 	'''
# 	self.perform_test({
# 		# "self.": '',
# 	})


# def test_(self):
# 	'''
# 	'''
# 	self.perform_test({
# 		# "self.": '',
# 	})


# def test_(self):
# 	'''
# 	'''
# 	self.perform_test({
# 		# "self.": '',
# 	})


# def test_(self):
# 	'''
# 	'''
# 	self.perform_test({
# 		# "self.": '',
# 	})
# """

# # Deprecated ---------------------