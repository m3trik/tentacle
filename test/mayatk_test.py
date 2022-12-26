# !/usr/bin/python
# coding=utf-8
import os, sys
import unittest
import inspect


# ---------------------------------------
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
# 	for dd in filetk.getDirContents(d, 'dirpaths', excludeDirs='Python27',  recursive=True):
# 		print (dd)
# 		sys.path.append(dd)

# import maya.standalone
# maya.standalone.initialize(name='python')

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


class Mayatk_test(Main, Mayatk):
	'''
	set object mode:
		pm.selectMode(object=1)

	set component mode:
		pm.selectMode(component=1)

	set component mode type:
		pm.selectType(allObjects=1)
		pm.selectType(mc=1)
		pm.selectType(vertex=1)
		pm.selectType(edge=1)
		pm.selectType(facet=1)
		pm.selectType(polymeshUV=1)
		pm.selectType(meshUVShell=1)
	'''
	#Tear down the any previous test by creating a new scene:
	pm.mel.file(new=True, force=True)

	#assemble the test scene:
	if not pm.objExists('cyl'):
		cyl = pm.polyCylinder(radius=5, height=10, subdivisionsX=12, subdivisionsY=1, subdivisionsZ=1, name='cyl')

	def test_getArrayType(self):
		'''
		'''
		self.perform_test({
			"self.getArrayType('cyl.vtx[0]')": 'transform',
			"self.getArrayType('cylShape.vtx[:]')": 'str',
			"self.getArrayType(pm.ls('cylShape.vtx[:]'))": 'obj',
		})

	def test_convertElemType(self):
		'''
		'''
		self.perform_test({
			"self.convertArrayType('cyl.vtx[:2]', 'str')": ['cylShape.vtx[0:2]'],
			"self.convertArrayType('cyl.vtx[:2]', 'str', flatten=True)": ['cylShape.vtx[0]', 'cylShape.vtx[1]', 'cylShape.vtx[2]'],
			"str(self.convertArrayType('cyl.vtx[:2]', obj'))": "[MeshVertex('cylShape.vtx[0:2]')]",
			"str(self.convertArrayType('cyl.vtx[:2]', obj', flatten=True))": "[MeshVertex('cylShape.vtx[0]'), MeshVertex('cylShape.vtx[1]'), MeshVertex('cylShape.vtx[2]')]",
			"self.convertArrayType('cyl.vtx[:2]', 'int')": [0, 2],
			"self.convertArrayType('cyl.vtx[:2]', 'int', flatten=True)": [0, 1, 2],
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

# Deprecated ---------------------