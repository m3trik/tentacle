# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Normals(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.normals_ui.b003.setText('Hard Edge Display')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.normals_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.normals_ui.draggable_header.contextMenu.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots.message
	def tb000(self, state=None):
		'''Display Face Normals
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QSpinBox', setPrefix='Display Size: ', setObjectName='s001', setMinMax_='1-100 step1', setValue=1, setToolTip='Normal display size.')
			return

		size = float(tb.menu_.s001.value())
		# state = pm.polyOptions (query=True, displayNormal=True)
		state = self.cycle([1,2,3,0], 'displayNormals')
		if state ==0: #off
			pm.polyOptions (displayNormal=0, sizeNormal=0)
			pm.polyOptions (displayTangent=False)
			return 'Normals Display <hl>Off</hl>.'

		elif state ==1: #facet
			pm.polyOptions (displayNormal=1, facet=True, sizeNormal=size)
			pm.polyOptions (displayTangent=False)
			return '<hl>Facet</hl> Normals Display <hl>On</hl>.'

		elif state ==2: #Vertex
			pm.polyOptions (displayNormal=1, point=True, sizeNormal=size)
			pm.polyOptions (displayTangent=False)
			return '<hl>Vertex</hl> Normals Display <hl>On</hl>.'

		elif state ==3: #tangent
			pm.polyOptions (displayTangent=True)
			pm.polyOptions (displayNormal=0)
			return '<hl>Tangent</hl> Display <hl>On</hl>.'


	def tb001(self, state=None):
		'''Harden Creased Edges
		'''
		tb = self.current_ui.tb001
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Soften non-creased', setObjectName='chk000', setToolTip='Soften all non-creased edges.')
			return

		mel.eval("PolySelectConvert 2")
		edges = pm.polyListComponentConversion (toEdge=1)
		edges = pm.ls(edges, flatten=1)

		pm.undoInfo(openChunk=1)
		self.mainProgressBar(len(edges))

		soften = tb.menu_.chk000.isChecked()

		for edge in edges:
			pm.progressBar("progressBar_", edit=1, step=1)
			if pm.progressBar("progressBar_", query=1, isCancelled=1):
				break
			crease = pm.polyCrease(edge, query=1, value=1)
			# print(edge, crease[0])
			if crease[0]>0:
				pm.polySoftEdge(edge, angle=30)
			elif soften:
				pm.polySoftEdge(edge, angle=180)
		pm.progressBar("progressBar_", edit=1, endProgress=1)
		pm.undoInfo(closeChunk=1)


	def tb002(self, state=None):
		'''Set Normal By Angle
		'''
		tb = self.current_ui.tb002
		if state is 'setMenu':
			tb.menu_.add('QSpinBox', setPrefix='Angle: ', setObjectName='s000', setMinMax_='1-180 step1', setValue=60, setToolTip='Angle degree.')
			return

		normalAngle = str(tb.menu_.s000.value())
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

		self.tcl.hide()


	def tb003(self, state=None):
		'''Lock/Unlock Vertex Normals
		'''
		tb = tb = self.normals_ui.tb003
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='All', setObjectName='chk001', setChecked=True, setToolTip='Lock/Unlock: all.')
			return

		print('Error: No 3ds Version.')
		tb.setDisabled(True)
		# all_ = tb.menu_.chk001.isChecked()
		# state = self.normals_ui.chk002.isChecked()#pm.polyNormalPerVertex(vertex, query=1, freezeNormal=1)
		# selection = pm.ls (selection=1, objectsOnly=1)
		# maskObject = pm.selectMode (query=1, object=1)
		# maskVertex = pm.selectType (query=1, vertex=1)

		# if len(selection)>0:
		# 	if (all_ and maskVertex) or maskObject:
		# 		for obj in selection:
		# 			count = pm.polyEvaluate(obj, vertex=1) #get number of vertices
		# 			vertices = [vertices.append(str(obj) + ".vtx ["+str(num)+"]") for num in range(count)] #geometry.vtx[0]
		# 			for vertex in vertices:
		# 				if state:
		# 					pm.polyNormalPerVertex(vertex, unFreezeNormal=1)
		# 				else:
		# 					pm.polyNormalPerVertex(vertex, freezeNormal=1)
		# 			if state:
		# 				return 'Normals <hl>UnLocked</hl>.'
		# 			else:
		# 				return 'Normals <hl>Locked</hl>.'
		# 	elif maskVertex and not maskObject:
		# 		if state:
		# 			pm.polyNormalPerVertex(unFreezeNormal=1)
		# 			return 'Normals <hl>UnLocked</hl>.'
		# 		else:
		# 			pm.polyNormalPerVertex(freezeNormal=1)
		# 			return 'Normals <hl>Locked</hl>.'
		# 	else:
		# 		return 'Error: Selection must be object or vertex.'
		# else:
		# 	return Error: No object selected.'


	def tb004(self, state=None):
		'''Average Normals
		'''
		tb = self.current_ui.tb004
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='By UV Shell', setObjectName='chk003', setToolTip='Average the normals of each object\'s faces per UV shell.')
			return

		byUvShell = tb.menu_.chk003.isChecked()

		if byUvShell:
			sets_ = Init.getUvShellSets(obj)
			for set_ in sets_:
				pm.polySetToFaceNormal(set_)
				pm.polyAverageNormal(set_)
		else:
			maxEval('macros.run "PolyTools" "SmoothSelection"')


	def b001(self):
		'''Soften Edge Normal
		'''
		self.tcl.hide()
		maxEval('$.EditablePoly.makeSmoothEdges 1')


	def b002(self):
		'''Harden Edge Normal
		'''
		self.tcl.hide()
		maxEval('$.EditablePoly.makeHardEdges 1')


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


	def b009(self):
		'''Harden Uv Edges
		'''
		def createArrayFromSelection (): #(string sel[])	/* returns a string array of the selected transform nodes
			pm.select (hierarchy=1)
			nodes = pm.ls (selection=1, transforms=1)
			groupedNodes = pm.listRelatives (type="transform") #if the nodes are grouped then just get the children

			if groupedNodes[0] != "":	#check to see if the nodes are grouped
				size = len(groupedNodes)
				clear (nodes)
				appendStringArray(nodes, groupedNodes, size)
			return nodes

		uvBorder=edgeUVs=finalBorder=[]
		nodes = createArrayFromSelection()

		for node in nodes:
			pm.select (node, replace=1)
			pm.polyNormalPerVertex (unFreezeNormal=True)
			pm.polySoftEdge (node, angle=180, constructionHistory=1)
			maxEval('select -replace '+node+'.map["*"];')

			mel.eval("polySelectBorderShell 1;")

			uvBorder = pm.polyListComponentConversion (toEdge=1, internal=1)
			uvBorder = pm.ls (uvBorder, flatten=1)

			pm.clear(finalBorder)

			for curEdge in uvBorder:
				edgeUVs = pm.polyListComponentConversion (curEdge, toUv=1)
				edgeUVs = pm.ls (edgeUVs, flatten=1)

				if len(edgeUVs) >2:
					finalBorder[len(finalBorder)] = curEdge
				pm.polySoftEdge (finalBorder, angle=0, constructionHistory=1)

			pm.select (nodes, replace=1)


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
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------
