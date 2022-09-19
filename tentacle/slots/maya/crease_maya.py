# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.crease import Crease



class Crease_maya(Crease, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.creaseValue = 10

		cmb = self.sb.crease.draggable_header.contextMenu.cmb000
		items = ['Crease Set Editor']
		cmb.addItems_(items, 'Crease Editors:')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.crease.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Crease Set Editor':
				from maya.app.general import creaseSetEditor
				creaseSetEditor.showCreaseSetEditor()

			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Crease
		'''
		tb = self.sb.crease.tb000

		creaseAmount = float(tb.contextMenu.s003.value())
		normalAngle = int(tb.contextMenu.s004.value()) 

		if tb.contextMenu.chk011.isChecked(): #crease: Auto
			angleLow = int(tb.contextMenu.s005.value()) 
			angleHigh = int(tb.contextMenu.s006.value()) 

			mel.eval("PolySelectConvert 2;") #convert selection to edges
			contraint = pm.polySelectConstraint( mode=3, type=0x8000, angle=True, anglebound=(angleLow, angleHigh) ) # to get edges with angle between two degrees. mode=3 (All and Next) type=0x8000 (edge). 

		operation = 0 #Crease selected components
		pm.polySoftEdge (angle=0, constructionHistory=0) #Harden edge normal
		if tb.contextMenu.chk002.isChecked():
			objectMode = pm.selectMode (query=True, object=True)
			if objectMode: #if in object mode,
				operation = 2 #2-Remove all crease values from mesh
			else:
				operation = 1 #1-Remove crease from sel components
				pm.polySoftEdge (angle=180, constructionHistory=0) #soften edge normal

		if tb.contextMenu.chk004.isChecked(): #crease vertex point
			pm.polyCrease (value=creaseAmount, vertexValue=creaseAmount, createHistory=True, operation=operation)
		else:
			pm.polyCrease (value=creaseAmount, createHistory=True, operation=operation) #PolyCreaseTool;

		if tb.contextMenu.chk005.isChecked(): #adjust normal angle
			pm.polySoftEdge (angle=normalAngle)

		if tb.contextMenu.chk011.isChecked(): #crease: Auto
			pm.polySelectConstraint( angle=False ) # turn off angle constraint


	@Slots_maya.undo
	def b002(self):
		'''Transfer Crease Edges
		'''
		# an updated version of this is in the maya python projects folder. transferCreaseSets.py
		# the use of separate buttons for donor and target mesh are deprecated.
		# add pm.polySoftEdge (angle=0, constructionHistory=0); #harden edge, when applying crease.
		
		creaseSet = str(self.sb.crease.b000.text())
		newObject = str(self.sb.crease.b001.text())

		sets = pm.sets (creaseSet, query=1)

		setArray = []
		for set_ in sets:
			name = str(set_)
			setArray.append(name)
		print(setArray)

		# pm.undoInfo (openChunk=1)
		for set_ in setArray:
			oldObject = ''.join(set_.partition('.')[:1]) #ex. pSphereShape1 from pSphereShape1.e[260:299]
			pm.select (set_, replace=1)
			value = pm.polyCrease (query=1, value=1)[0]
			name = set_.replace(oldObject, newObject)
			pm.select (name, replace=1)
			pm.polyCrease (value=value, vertexValue=value, createHistory=True)
			# print("crease:", name)
		# pm.undoInfo (closeChunk=1)

		self.sb.toggleWidgets(setDisabled='b052', setUnChecked='b000')#,self.sb.crease.b001])
		self.sb.crease.b000.setText("Crease Set")
		# self.sb.crease.b001.setText("Object")


	def getCreasedEdges(self, edges):
		'''Return any creased edges from a list of edges.

		:Parameters:
			edges (str)(obj)(list) = The edges to check crease state on.

		:Return:
			(list) edges.
		'''
		creased_edges = [e for e in pm.ls(edges, flatten=1) if pm.polyCrease(e, q=1, value=1)[0] > 0]

		return creased_edges









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------
#b008, b010, b011, b019, b024-27, b058, b059, b060