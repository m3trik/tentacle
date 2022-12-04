#unit testing
import os, sys
import unittest
import inspect

# ---------------------------------------
# this is the missing stuff when running python.exe compared with mayapy.exe

mayaver = 2022
pythonver = 37

mayapath = '%ProgramFiles%/Autodesk/Maya{}'.format(mayaver)

# os.environ['MAYA_LOCATION'] = mayapath
# os.environ['PYTHONHOME'] = mayapath+'/Python{}'.format(mayaver, pythonver)
# os.environ['PATH'] = mayapath+'/bin;'.format(mayaver) + os.environ['PATH']

# for d in Utils.getDirectoryContents(mayapath, 'dirpaths', recursive=True):
# 	sys.path.append(d)

# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/site-packages'.format(mayaver, pythonver))
# # sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/site-packages/pymel-1.0.0-py2.6.egg'.format(mayaver, pythonver))
# # sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/site-packages/ipython-0.10.1-py2.6.egg'.format(mayaver, pythonver))
# # sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/site-packages/ply-3.3-py2.6.egg'.format(mayaver, pythonver))                         
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/bin'.format(mayaver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/bin3'.format(mayaver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/DLLs'.format(mayaver, pythonver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib'.format(mayaver, pythonver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/plat-win'.format(mayaver, pythonver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/lib-tk'.format(mayaver, pythonver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}'.format(mayaver, pythonver))
# sys.path.append('%ProgramFiles%/Autodesk/Maya{}/Python{}/lib/site-packages'.format(mayaver, pythonver))

# import maya.standalone
# maya.standalone.initialize(name='python')

import pymel.core as pm
# # ---------------------------------------

import tentacle
from slots.maya.mayatls import *


sfr = pm.melGlobals['cmdScrollFieldReporter']
pm.cmdScrollFieldReporter(sfr, edit=1, clear=1)


class Test(unittest.TestCase):
	'''
	'''
	def perform_test(self, case):
		'''
		'''
		for expression, expected_result in case.items():
			m = expression.split('(')[0] #ie. 'self.setCase' from "self.setCase('xxx', 'upper')"

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


class Componenttls_test(Test, Componenttls):
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
	node_name = 'cyl'
	if not pm.objExists(node_name):
		n0 = pm.polyCylinder(radius=5, height=10, subdivisionsX=12, subdivisionsY=1, subdivisionsZ=1, name=node_name)

	cyl = pm.ls(node_name)[0]
	verts = pm.ls(cyl.vtx[:], flatten=True)
	edges = pm.ls(cyl.e[:], flatten=True)
	edges_unflattened = pm.ls(edges, flatten=False)
	faces = pm.ls(cyl.f[:], flatten=True)

	node_name = 'cmb'
	if not pm.objExists(node_name): #create two objects and combine them.
		n1 = pm.polyCylinder(radius=5, height=10, subdivisionsX=5, subdivisionsY=1, subdivisionsZ=1)
		pm.move(0, 0, 25)
		n2 = pm.polyCylinder(radius=5, height=6, subdivisionsX=5, subdivisionsY=1, subdivisionsZ=1)
		pm.move(5, 0, 25)
		pm.polyUnite(n1, n2, cp=1, name=node_name)

	node_name = 'pln'
	if not pm.objExists(node_name): #create two objects and combine them.
		n3 = pm.polyPlane(width=20, height=20, subdivisionsX=3, subdivisionsY=3, name=node_name)
		pm.move(0, 0, -25)

	node_name = 'sph'
	if not pm.objExists(node_name):
		n4 = pm.polySphere(radius=8, subdivisionsX=6, subdivisionsY=6, name=node_name)
		pm.move(25, 0, 0)

	def test_getComponentType(self):
		'''
		'''
		self.perform_test({
			"self.getComponentType(self.edges)": 'Polygon Edge',
			"self.getComponentType(self.edges, 'int')": 32,
			"self.getComponentType(self.edges, 'hex')": 0x8000,
		})


	def test_convertComponentName(self):
		'''
		'''
		self.perform_test({
			"self.convertComponentName('vertex', 'hex')": 0x0001,
			"self.convertComponentName(0x0001, 'str')": 'Polygon Vertex',
		})


	def test_convertElementType(self):
		'''
		'''
		self.perform_test({
			"self.convertElementType('cyl.vtx[:2]', 'str')": ['cylShape.vtx[0:2]'],
			"self.convertElementType('cyl.vtx[:2]', 'str', True)": ['cylShape.vtx[0]', 'cylShape.vtx[1]', 'cylShape.vtx[2]'],
			"str(self.convertElementType('cyl.vtx[:2]', 'cyl'))": "[MeshVertex('cylShape.vtx[0:2]')]",
			"str(self.convertElementType('cyl.vtx[:2]', 'cyl', True))": "[MeshVertex('cylShape.vtx[0]'), MeshVertex('cylShape.vtx[1]'), MeshVertex('cylShape.vtx[2]')]",
			"self.convertElementType('cyl.vtx[:2]', 'transform')": ['cyl.vtx[0:2]'],
			"self.convertElementType('cyl.vtx[:2]', 'transform', True)": ['cyl.vtx[0]', 'cyl.vtx[1]', 'cyl.vtx[2]'],
			"str(self.convertElementType('cyl.vtx[:2]', 'int'))": "{nt.Mesh('cylShape'): [(0, 2)]}",
			"str(self.convertElementType('cyl.vtx[:2]', 'int', True))": "{nt.Mesh('cylShape'): [0, 1, 2]}",
			"self.convertElementType('cyl.vtx[:10]', returnType='int', flatten=True, forceList=True)": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
		})


	def test_convertComponentType(self):
		'''
		'''
		self.perform_test({
			"self.convertComponentType('cylShape.vtx[:2]', 'vertex')": ['cylShape.vtx[0:2]'],
			"self.convertComponentType('cylShape.vtx[:2]', 'face')": ['cylShape.f[0:2]', 'cylShape.f[11:14]', 'cylShape.f[23]'],
			"self.convertComponentType('cylShape.vtx[:2]', 'edge')": ['cylShape.e[0:2]', 'cylShape.e[11]', 'cylShape.e[24:26]', 'cylShape.e[36:38]'],
			"self.convertComponentType('cylShape.vtx[:2]', 'uv')": ['cylShape.map[0:2]', 'cylShape.map[12:14]', 'cylShape.map[24]'],
		})


	def test_filterComponents(self):
		'''
		'''
		self.perform_test({
			"self.filterComponents('cyl.vtx[:]', 'cyl.vtx[:2]', 'cyl.vtx[1:23]')": ['cyl.vtx[0]'],
		})


	def test_getComponents(self):
		'''
		'''
		self.perform_test({
			"self.getComponents('cyl', 'vertex', 'str', '', 'cyl.vtx[2:23]')": ['cylShape.vtx[0]', 'cylShape.vtx[1]', 'cylShape.vtx[24]', 'cylShape.vtx[25]'],
			"str(self.getComponents('cyl', 'vertex', 'cyl', '', 'cyl.vtx[:23]'))": "[MeshVertex('cylShape.vtx[24]'), MeshVertex('cylShape.vtx[25]')]",
			"str(self.getComponents('cyl', 'f', 'int'))": "{nt.Mesh('cylShape'): [(0, 35)]}",
			"self.getComponents('cyl', 'edges')": ['cylShape.e[0:59]'],
			"self.getComponents('cyl', 'edges', 'str', 'cyl.e[:2]')": ['cylShape.e[0]', 'cylShape.e[1]', 'cylShape.e[2]'],
		})


	def test_getContigiousEdges(self):
		'''
		'''
		self.perform_test({
			"self.getContigiousEdges(['cyl.e[:2]'])": [{'cylShape.e[1]', 'cylShape.e[0]', 'cylShape.e[2]'}],
			"self.getContigiousEdges(['cyl.f[0]'])": [{'cylShape.e[24]', 'cylShape.e[0]', 'cylShape.e[25]', 'cylShape.e[12]'}],
		})


	def test_getContigiousIslands(self):
		'''
		'''
		self.perform_test({
			"self.getContigiousIslands('cyl.f[21:26]')": [{'cylShape.f[22]', 'cylShape.f[21]', 'cylShape.f[23]'}, {'cylShape.f[26]', 'cylShape.f[24]', 'cylShape.f[25]'}],
		})


	def test_getIslands(self):
		'''
		'''
		self.perform_test({
			"list(self.getIslands('cmb'))": [['cmb.f[0]', 'cmb.f[5]', 'cmb.f[4]', 'cmb.f[9]', 'cmb.f[6]', 'cmb.f[1]', 'cmb.f[10]', 'cmb.f[11]', 'cmb.f[14]', 'cmb.f[8]', 'cmb.f[7]', 'cmb.f[3]', 'cmb.f[13]', 'cmb.f[2]', 'cmb.f[12]'], ['cmb.f[15]', 'cmb.f[20]', 'cmb.f[19]', 'cmb.f[24]', 'cmb.f[21]', 'cmb.f[16]', 'cmb.f[25]', 'cmb.f[26]', 'cmb.f[29]', 'cmb.f[23]', 'cmb.f[22]', 'cmb.f[18]', 'cmb.f[28]', 'cmb.f[17]', 'cmb.f[27]']],
		})


	def test_getBorderComponents(self):
		'''
		'''
		self.perform_test({
			"self.getBorderComponents('pln', 'vtx')": ['plnShape.vtx[0:4]', 'plnShape.vtx[7:8]', 'plnShape.vtx[11:15]'],
			"self.getBorderComponents('pln', 'face')": ['plnShape.f[0:3]', 'plnShape.f[5:8]'],
			"self.getBorderComponents('pln')": ['plnShape.e[0:2]', 'plnShape.e[4]', 'plnShape.e[6]', 'plnShape.e[8]', 'plnShape.e[13]', 'plnShape.e[15]', 'plnShape.e[20:23]'],
			"self.getBorderComponents('pln.e[:]')": ['plnShape.e[0:2]', 'plnShape.e[4]', 'plnShape.e[6]', 'plnShape.e[8]', 'plnShape.e[13]', 'plnShape.e[15]', 'plnShape.e[20:23]'],
			"self.getBorderComponents(['pln.e[9]','pln.e[10]', 'pln.e[12]', 'pln.e[16]'], 'f', componentBorder=True)": ['plnShape.f[1]', 'plnShape.f[3:5]', 'plnShape.f[7]'],
			"self.getBorderComponents('pln.f[3:4]', 'f', componentBorder=True)": ['plnShape.f[0:1]', 'plnShape.f[5:7]'],
			"self.getBorderComponents('pln.f[3:4]', 'vtx', componentBorder=True)": ['plnShape.vtx[4:6]', 'plnShape.vtx[8:10]'],
			"self.getBorderComponents('pln.vtx[6]', 'e', componentBorder=True)": ['plnShape.e[5]', 'plnShape.e[9]', 'plnShape.e[11:12]'],
		})


	def test_getClosestVerts(self):
		'''
		'''
		self.perform_test({
			"self.getClosestVerts('pln.vtx[:10]', 'pln.vtx[11:]', 6.667)": [('plnShape.vtx[7]', 'plnShape.vtx[11]'), ('plnShape.vtx[8]', 'plnShape.vtx[12]'), ('plnShape.vtx[9]', 'plnShape.vtx[13]'), ('plnShape.vtx[10]', 'plnShape.vtx[11]'), ('plnShape.vtx[10]', 'plnShape.vtx[14]')],
		})


	def test_getClosestVertex(self):
		'''
		'''
		self.perform_test({
			"self.getClosestVertex('plnShape.vtx[0]', 'cyl', returnType='int')": {'plnShape.vtx[0]': 3},
			"self.getClosestVertex('plnShape.vtx[0]', 'cyl')": {'plnShape.vtx[0]': 'cylShape.vtx[3]'},
			"self.getClosestVertex('plnShape.vtx[2:3]', 'cyl')": {'plnShape.vtx[2]': 'cylShape.vtx[2]', 'plnShape.vtx[3]': 'cylShape.vtx[1]'},
		})


	def test_getEdgePath(self):
		'''
		'''
		self.perform_test({
			"self.getEdgePath('sph.e[12]', 'edgeLoop')": ['sphShape.e[12]', 'sphShape.e[17]', 'sphShape.e[16]', 'sphShape.e[15]', 'sphShape.e[14]', 'sphShape.e[13]'],
			"self.getEdgePath('sph.e[12]', 'edgeLoop', 'int')": [12, 17, 16, 15, 14, 13],
			"self.getEdgePath('sph.e[12]', 'edgeRing')": ['sphShape.e[0]', 'sphShape.e[6]', 'sphShape.e[12]', 'sphShape.e[18]', 'sphShape.e[24]'],
			"self.getEdgePath(['sph.e[43]', 'sph.e[46]'], 'edgeRingPath')": ['sphShape.e[43]', 'sphShape.e[42]', 'sphShape.e[47]', 'sphShape.e[46]'],
			"self.getEdgePath(['sph.e[54]', 'sph.e[60]'], 'edgeLoopPath')": ['sphShape.e[60]', 'sphShape.e[48]', 'sphShape.e[42]', 'sphShape.e[36]', 'sphShape.e[30]', 'sphShape.e[54]'],
			"self.getEdgePath(['sph.e[11]', 'sph.e[22]'], 'shortestEdgePath')": ['sphShape.e[46]', 'sphShape.e[16]', 'sphShape.e[41]'],
		})


	def test_(self):
		'''
		'''
		self.perform_test({
			# "self.": '',
		})


	def test_(self):
		'''
		'''
		self.perform_test({
			# "self.": '',
		})


	def test_(self):
		'''
		'''
		self.perform_test({
			# "self.": '',
		})


	def test_(self):
		'''
		'''
		self.perform_test({
			# "self.": '',
		})









if __name__=='__main__':
	unittest.main(exit=False)



# --------------------------------
# Notes
# --------------------------------

"""
def test_(self):
	'''
	'''
	self.perform_test({
		# "self.": '',
	})


def test_(self):
	'''
	'''
	self.perform_test({
		# "self.": '',
	})


def test_(self):
	'''
	'''
	self.perform_test({
		# "self.": '',
	})


def test_(self):
	'''
	'''
	self.perform_test({
		# "self.": '',
	})
"""

# Deprecated ---------------------