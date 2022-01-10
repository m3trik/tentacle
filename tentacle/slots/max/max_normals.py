# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Normals(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		self.normals_ui.b003.setText('Hard Edge Display')

		ctx = self.normals_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.normals_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		ctx = self.normals_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Display Size: ', setObjectName='s001', setMinMax_='1-100 step1', setValue=1, setToolTip='Normal display size.')

		ctx = self.normals_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Angle: ', setObjectName='s002', setMinMax_='0-180 step1', setValue=0, setToolTip='The normal angle in degrees.')
			ctx.add('QCheckBox', setText='Harden Creased Edges', setObjectName='chk001', setToolTip='Soften all non-creased edges.')
			ctx.add('QCheckBox', setText='Harden UV Borders', setObjectName='chk002', setToolTip='Harden UV shell border edges.')
			ctx.add('QCheckBox', setText='Soften All Other', setObjectName='chk000', setChecked=True, setToolTip='Soften all non-hard edges.')

		ctx = self.normals_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Angle: ', setObjectName='s000', setMinMax_='0-180 step1', setValue=60, setToolTip='Angle degree.')

		ctx = self.normals_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Lock', setObjectName='chk002', setChecked=True, setToolTip='Toggle Lock/Unlock.')
			ctx.add('QCheckBox', setText='All', setObjectName='chk001', setChecked=True, setToolTip='Lock/Unlock All.')
			ctx.chk002.toggled.connect(lambda state, w=ctx.chk002: w.setText('Lock') if state else w.setText('Unlock')) 

		ctx = self.normals_ui.tb004.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='By UV Shell', setObjectName='chk003', setToolTip='Average the normals of each object\'s faces per UV shell.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.normals_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.normals_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots.message
	def tb000(self, state=None):
		'''Display Face Normals
		'''
		tb = self.normals_ui.tb000

		size = float(tb.contextMenu.s001.value())

		'No 3ds Version.'
		tb.setDisabled(True)
		# # state = pm.polyOptions (query=True, displayNormal=True)
		# state = self.cycle([1,2,3,0], 'displayNormals')
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
		tb = self.normals_ui.tb001

		maxEval('$.EditablePoly.makeHardEdges 1')

		# hardAngle = tb.contextMenu.s002.value()
		# hardenCreased = tb.contextMenu.chk001.isChecked()
		# hardenUvBorders = tb.contextMenu.chk002.isChecked()
		# softenOther = tb.contextMenu.chk000.isChecked()

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
		tb = self.normals_ui.tb002

		normalAngle = str(tb.contextMenu.s000.value())
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
		tb = self.normals_ui.tb003

		print ('# Error: No 3ds Version of this command yet. #')
		tb.setDisabled(True)
		# all_ = tb.contextMenu.chk001.isChecked()
		# state = tb.contextMenu.chk002.isChecked() #pm.polyNormalPerVertex(vertex, query=1, freezeNormal=1)
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
		# 				self.viewPortMessage("Normals <hl>UnLocked</hl>.")
		# 			else:
		# 				self.viewPortMessage("Normals <hl>Locked</hl>.")
		# 	elif maskVertex and not maskObject:
		# 		if not state:
		# 			pm.polyNormalPerVertex(unFreezeNormal=1)
		# 			self.viewPortMessage("Normals <hl>UnLocked</hl>.")
		# 		else:
		# 			pm.polyNormalPerVertex(freezeNormal=1)
		# 			self.viewPortMessage("Normals <hl>Locked</hl>.")
		# 	else:
		# 		return 'Warning: Selection must be object or vertex.'
		# else:
		# 	return 'Warning: No object selected.'


	def tb004(self, state=None):
		'''Average Normals
		'''
		tb = self.normals_ui.tb004

		byUvShell = tb.contextMenu.chk003.isChecked()

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
# -----------------------------------------------
# Notes
# -----------------------------------------------
