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


class Rigtk_test(Main, Rigtk):
	'''
	'''
	#Tear down the any previous test by creating a new scene:
	pm.mel.file(new=True, force=True)

	#assemble the test scene:
	if not pm.objExists('loc'):
		loc = pm.spaceLocator(name='loc')

	if not pm.objExists('cyl'):
		cyl = pm.polyCylinder(radius=5, height=10, subdivisionsX=6, subdivisionsY=1, subdivisionsZ=1, name='cyl')

	def test_createLocator(self):
		'''
		'''
		self.perform_test({
			"self.createLocator('_loc')": '_loc',
		})

	def test_removeLocator(self):
		'''
		'''
		self.perform_test({
			"self.removeLocator('loc')": None,
		})

	def test_resetPivotTransforms(self):
		'''
		'''
		self.perform_test({
			"self.resetPivotTransforms('cyl')": None,
		})

	def test_bakeCustomPivot(self):
		'''
		'''
		self.perform_test({
			"self.bakeCustomPivot('cyl')": None,
			"self.bakeCustomPivot('cyl', position=True)": None,
			"self.bakeCustomPivot('cyl', orientation=True)": None,
		})

	def test_setAttrLockState(self):
		'''
		'''
		self.perform_test({
			"self.setAttrLockState('cyl')": None,
		})

	def test_createGroup(self):
		'''
		'''
		self.perform_test({
			"self.createGroup(name='emptyGrp').name()": 'emptyGrp',
		})

	def test_createGroupLRA(self):
		'''
		'''
		self.perform_test({
			"self.createGroupLRA('cyl', 'LRAgrp').name()": 'LRAgrp',
		})

	def test_createLocatorAtObject(self):
		'''
		'''
		self.perform_test({
			"self.createLocatorAtObject('cyl')": None,
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