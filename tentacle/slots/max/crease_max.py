# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.crease import Crease



class Crease_max(Crease, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Crease.__init__(self, *args, **kwargs)

		self.creaseValue = 10

		cmb = self.crease_ui.draggable_header.contextMenu.cmb000
		items = ['Crease Modifier']
		cmb.addItems_(items, 'Crease Modifiers:')


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.crease_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Crease Modifier':
				#check if modifier exists
				for obj in rt.selection:
					mod = obj.modifiers[rt.Crease]
					if mod==None: #if not create
						mod = rt.crease()
						rt.addModifier (obj, mod)
						#set modifier attributes
						# mod.enabled = state

			rt.redrawViews()
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Crease
		'''
		tb = self.crease_ui.tb000

		creaseAmount = int(tb.contextMenu.s003.value())
		normalAngle = int(tb.contextMenu.s004.value())

		# if tb.contextMenu.chk011.isChecked(): #crease: Auto
		# 	angleLow = int(tb.contextMenu.s005.value()) 
		# 	angleHigh = int(tb.contextMenu.s006.value()) 

		# 	mel.eval("PolySelectConvert 2;") #convert selection to edges
		# 	contraint = pm.polySelectConstraint( mode=3, type=0x8000, angle=True, anglebound=(angleLow, angleHigh) ) # to get edges with angle between two degrees. mode=3 (All and Next) type=0x8000 (edge). 

		creaseAmount = creaseAmount*0.1 #convert to max 0-1 range

		for obj in rt.selection:
			if rt.classOf(obj)=='Editable_Poly':

				if tb.contextMenu.chk011.isChecked(): #crease: Auto
					minAngle = int(tb.contextMenu.s005.value()) 
					maxAngle = int(tb.contextMenu.s006.value()) 

					edgelist = self.getEdgesByAngle(minAngle, maxAngle)
					rt.polyOp.setEdgeSelection(obj, edgelist)

				if tb.contextMenu.chk004.isChecked(): #crease vertex point
					obj.EditablePoly.setVertexData(1, creaseAmount)
				else: #crease edge
					obj.EditablePoly.setEdgeData(1, creaseAmount)

				if tb.contextMenu.chk005.isChecked(): #adjust normal angle
					edges = rt.polyop.getEdgeSelection(obj)
					for edge in edges:
						edgeVerts = rt.polyop.getEdgeVerts(obj, edge)
						normal = rt.averageSelVertNormal(obj)
						for vertex in edgeVerts:
							rt.setNormal(obj, vertex, normal)
			else:
				print('Error: object type '+rt.classOf(obj)+' is not supported.')


	def b002(self):
		'''Transfer Crease Edges
		'''
		# an updated version of this is in the maya python projects folder
		# the use of separate buttons for donor and target mesh are obsolete
		# add pm.polySoftEdge (angle=0, constructionHistory=0); #harden edge, when applying crease 

		creaseSet = str(self.crease_ui.b000.text())
		newObject = str(self.crease_ui.b001.text())

		sets = pm.sets (creaseSet, query=1)

		setArray = []
		for set_ in sets:
			name = str(set_)
			setArray.append(name)
		print(setArray)

		pm.undoInfo (openChunk=1)
		for set_ in setArray:
			oldObject = ''.join(set_.partition('.')[:1]) #ex. pSphereShape1 from pSphereShape1.e[260:299]
			pm.select (set_, replace=1)
			value = pm.polyCrease (query=1, value=1)[0]
			name = set_.replace(oldObject, newObject)
			pm.select (name, replace=1)
			pm.polyCrease (value=value, vertexValue=value, createHistory=True)
			# print("crease:", name)
		pm.undoInfo (closeChunk=1)

		self.toggleWidgets(setDisabled='b052', setUnChecked='b000')#,self.crease_ui.b001])
		self.crease_ui.b000.setText("Crease Set")
		# self.crease_ui.b001.setText("Object")









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------