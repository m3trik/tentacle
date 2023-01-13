# !/usr/bin/python
# coding=utf-8
import os, sys
import unittest
import inspect


# ------------------------------------------------------------------------------------
# this is the missing stuff when running python.exe compared with mayapy.exe

# mayaver = 2022
# pythonver = 37

# mayapath = '%ProgramFiles%/Autodesk/Maya{}'.format(mayaver)

# os.environ['MAYA_LOCATION'] = mayapath
# os.environ['PYTHONHOME'] = mayapath+'/Python{}'.format(mayaver, pythonver)
# os.environ['PATH'] = mayapath+'/bin;'.format(mayaver) + os.environ['PATH']

# from tentacle.slots.tk import filetk
# for d in [
# 	'{}/bin'.format(mayapath), 
# 	'{}/bin3'.format(mayapath), 
# 	'{}/Python{}'.format(mayapath, pythonver)
# 	]:
# 	for dd in filetk.getDirContents(d, 'dirpaths', excDirs='Python27',  recursive=True):
# 		print (dd)
# 		sys.path.append(dd)

# import maya.standalone
# maya.standalone.initialize(name='python')

import pymel.core as pm
# # ------------------------------------------------------------------------------------

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



class Edittk_test(Main, Edittk):
	'''
	'''
	#Tear down the any previous test by creating a new scene:
	pm.mel.file(new=True, force=True)

	#assemble the test scene:
	if not pm.objExists('cube1'):
		cube1 = pm.polyCube(width=5, height=5, depth=5, subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1, name='cube1')

	if not pm.objExists('cube2'):
		cube2 = pm.polyCube(width=2, height=4, depth=8, subdivisionsX=3, subdivisionsY=3, subdivisionsZ=3, name='cube2')

	if not pm.objExists('cyl'):
		cyl = pm.polyCylinder(radius=5, height=10, subdivisionsX=12, subdivisionsY=1, subdivisionsZ=1, name='cyl')

	def test_rename(self):
		'''
		'''
		self.perform_test({
			"self.rename('cube1', 'newName')": None,
			"self.rename('newName', 'cube1')": None,
		})

	def test_setCase(self):
		'''
		'''
		self.perform_test({
			"self.setCase('cube1', 'lower')": None,
		})

	def test_setSuffixByObjLocation(self):
		'''
		'''
		if not pm.objExists('c1'):
			c1 = pm.polyCube(width=2, height=2, depth=8, subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1, name='c1')

		if not pm.objExists('c2'):
			c2 = pm.polyCube(width=8, height=2, depth=2, subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1, name='c2')
			pm.move(0, 0, 5, c2)

		self.perform_test({
			"self.setSuffixByObjLocation(['c1', 'c2'])": None,
		})

	def test_snapClosestVerts(self):
		'''
		'''
		self.perform_test({
			"self.snapClosestVerts('cube1', 'cube2')": None,
		})

	def test_mergeVertices(self):
		'''
		'''
		self.perform_test({
			"self.mergeVertices('cube1')": None,
		})

	def test_deleteAlongAxis(self):
		'''
		'''
		self.perform_test({
			"self.deleteAlongAxis('cube1')": None,
		})

	def test_getAllFacesOnAxis(self):
		'''
		'''
		self.perform_test({
			"self.getAllFacesOnAxis('cube1')": [], #faces should have been deleted by the previous test 'deleteAlongAxis'.
		})

	def test_cleanGeometry(self):
		'''
		'''
		self.perform_test({
			"self.cleanGeometry('cyl')": None,
		})

	def test_getOverlappingDupObjects(self):
		'''
		'''
		self.perform_test({
			"self.getOverlappingDupObjects(['cyl', 'cube1', 'cube2'])": set(),
		})

	def test_findNonManifoldVertex(self):
		'''
		'''
		self.perform_test({
			"self.findNonManifoldVertex('cyl')": set(),
		})

	def test_splitNonManifoldVertex(self):
		'''
		'''
		self.perform_test({
			"self.splitNonManifoldVertex('cyl')": None,
		})

	def test_getNGons(self):
		'''
		'''
		self.perform_test({
			"self.getNGons('cyl')": [],
		})

	def test_getOverlappingVertices(self):
		'''
		'''
		self.perform_test({
			"self.getOverlappingVertices('cyl')": [],
		})

	def test_getOverlappingFaces(self):
		'''
		'''
		self.perform_test({
			"self.getOverlappingFaces('cyl')": [],
			"self.getOverlappingFaces('cyl.f[:]')": [],
		})

	def test_getSimilarMesh(self):
		'''
		'''
		self.perform_test({
			"self.getSimilarMesh('cyl')": [],
		})

	def test_getSimilarTopo(self):
		'''
		'''
		self.perform_test({
			"self.getSimilarTopo('cyl')": [],
		})

# -----------------------------------------------------------------------------

if __name__=='__main__':

	unittest.main(exit=False)






# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------

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