# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.normals import Normals



class Normals_max(Normals, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.sb.normals.b003.setText('Hard Edge Display')

		cmb = self.sb.normals.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.normals.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Display Face Normals
		'''
		tb = self.sb.normals.tb000

		size = float(tb.ctxMenu.s001.value())

		self.sb.messageBox('No 3ds Version.')
		tb.setDisabled(True)
		# # state = pm.polyOptions (query=True, displayNormal=True)
		# state = ptk.cycle([1,2,3,0], 'displayNormals')
		# if state ==0: #off
		# 	pm.polyOptions (displayNormal=0, sizeNormal=0)
		# 	pm.polyOptions (displayTangent=False)
		# 	return 'Normals Display <hl>Off</hl>.'

		# elif state ==1: #facet
		# 	pm.polyOptions (displayNormal=1, facet=True, sizeNormal=size)
		# 	pm.polyOptions (displayTangent=False)
		# 	return '<hl>Facet</hl> Normals Display <hl>On</hl>.'

		# elif state ==2: #Vertex
		# 	pm.polyOptions (displayNormal=1, point=True, sizeNormal=size)
		# 	pm.polyOptions (displayTangent=False)
		# 	return '<hl>Vertex</hl> Normals Display <hl>On</hl>.'

		# elif state ==3: #tangent
		# 	pm.polyOptions (displayTangent=True)
		# 	pm.polyOptions (displayNormal=0)
		# 	return '<hl>Tangent</hl> Display <hl>On</hl>.'


	def tb001(self, state=None):
		'''Harden Edge Normals
		'''
		tb = self.sb.normals.tb001

		maxEval('$.EditablePoly.makeHardEdges 1')

		# hardAngle = tb.ctxMenu.s002.value()
		# hardenCreased = tb.ctxMenu.chk001.isChecked()
		# hardenUvBorders = tb.ctxMenu.chk002.isChecked()
		# softenOther = tb.ctxMenu.chk000.isChecked()

		# objects = rt.selection

		# for obj in objects:
			# selection = pm.ls(obj, sl=True, l=True)
			# selEdges = pm.ls(pm.polyListComponentConversion(selection, toEdge=1), flatten=1)
			# allEdges = edges = pm.ls(pm.polyListComponentConversion(obj, toEdge=1), flatten=1)

			# if hardenCreased:
			# 	creasedEdges = Normals.getCreasedEdges(allEdges)
			# 	selEdges = selEdges + creasedEdges if not selEdges==allEdges else creasedEdges

			# if hardenUvBorders:
			# 	uv_border_edges = Slots_max.getUvShellBorderEdges(selection)
			# 	selEdges = selEdges + uv_border_edges if not selEdges==allEdges else uv_border_edges

			# obj.EditablePoly.makeHardEdges(1) #set hard edges.

			# if softenOther:
			# 	invEdges = [e for e in allEdges if e not in selEdges]
			# 	pm.polySoftEdge(invEdges, angle=180, constructionHistory=0) #set soft edges.

			# rt.select(selEdges)


	@Slots.hideMain
	def tb002(self, state=None):
		'''Set Normal By Angle
		'''
		tb = self.sb.normals.tb002

		normalAngle = str(tb.ctxMenu.s000.value())
		subObjectLevel = rt.subObjectLevel


		if subObjectLevel==4: #smooth selected faces
			for obj in rt.selection:
				obj.autoSmoothThreshold = normalAngle
				# faceSelection = rt.polyop.getFaceSelection(obj)
				rt.polyop.autoSmooth(obj)
				rt.update(obj)

		else: #smooth entire mesh
			mod = rt.Smooth()
			mod.autoSmooth = True
			mod.threshold = normalAngle

			for obj in rt.selection:
				rt.modPanel.setCurrentObject(obj.baseObject)
				rt.modPanel.addModToSelection (mod)
				index = [mod for mod in obj.modifiers].index(mod)+1 #add one to convert index from python to maxscript
				rt.maxOps.CollapseNodeTo(obj, index, False)


	def tb003(self, state=None):
		'''Lock/Unlock Vertex Normals
		'''
		tb = self.sb.normals.tb003

		print ('# Error: No 3ds Version of this command yet. #')
		tb.setDisabled(True)
		# all_ = tb.ctxMenu.chk001.isChecked()
		# state = tb.ctxMenu.chk002.isChecked() #pm.polyNormalPerVertex(vertex, query=1, freezeNormal=1)
		# selection = pm.ls (selection=1, objectsOnly=1)
		# maskObject = pm.selectMode (query=1, object=1)
		# maskVertex = pm.selectType (query=1, vertex=1)

		# if len(selection)>0:
		# 	if (all_ and maskVertex) or maskObject:
		# 		for obj in selection:
		# 			count = pm.polyEvaluate(obj, vertex=1) #get number of vertices
		# 			vertices = [vertices.append(str(obj) + ".vtx ["+str(num)+"]") for num in range(count)] #geometry.vtx[0]
		# 			for vertex in vertices:
		# 				if not state:
		# 					pm.polyNormalPerVertex(vertex, unFreezeNormal=1)
		# 				else:
		# 					pm.polyNormalPerVertex(vertex, freezeNormal=1)
		# 			if not state:
		# 				self.mtk.viewportMessage("Normals <hl>UnLocked</hl>.")
		# 			else:
		# 				self.mtk.viewportMessage("Normals <hl>Locked</hl>.")
		# 	elif maskVertex and not maskObject:
		# 		if not state:
		# 			pm.polyNormalPerVertex(unFreezeNormal=1)
		# 			self.mtk.viewportMessage("Normals <hl>UnLocked</hl>.")
		# 		else:
		# 			pm.polyNormalPerVertex(freezeNormal=1)
		# 			self.mtk.viewportMessage("Normals <hl>Locked</hl>.")
		# 	else:
		# 		return 'Warning: Selection must be object or vertex.'
		# else:
		# 	return 'Warning: No object selected.'


	def tb004(self, state=None):
		'''Average Normals
		'''
		tb = self.sb.normals.tb004

		byUvShell = tb.ctxMenu.chk003.isChecked()

		if byUvShell:
			print ('# Error: No 3ds Version of this flag yet. #')
			sets_ = Slots_max.getUvShellSets(obj)
			for set_ in sets_:
				pm.polySetToFaceNormal(set_)
				pm.polyAverageNormal(set_)
		else:
			maxEval('macros.run "PolyTools" "SmoothSelection"')


	@Slots.hideMain
	def b001(self):
		'''Soften Edge Normal
		'''
		maxEval('$.EditablePoly.makeSmoothEdges 1')


	def b003(self):
		'''Soft Edge Display
		'''
		for obj in rt.selection:
			state = obj.hardedgedisplay
			obj.hardedgedisplay = not state


	def b005(self):
		'''Adjust Vertex Normals
		'''
		maxEval('bgAdjustVertexNormalsWin;')


	def b006(self):
		'''Set To Face
		'''
		maxEval('macros.run "PolyTools" "HardSelection"')


	def b010(self):
		'''Reverse Normals
		'''
		for obj in rt.selection:		
			rt.modPanel.setCurrentObject(obj.baseObject)
			
			mod = rt.Normalmodifier()
			mod.flip = True
			
			rt.modpanel.addModToSelection(mod)
			
			index = rt.modPanel.getModifierIndex(obj, mod)
			rt.maxOps.CollapseNodeTo(obj, index, False)

		







#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
