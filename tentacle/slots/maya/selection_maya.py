# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.selection import Selection


class Selection_maya(Selection, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Selection.__init__(self, *args, **kwargs)

		dh = self.sb.selection.draggable_header
		items = ['Polygon Selection Constraints']
		dh.contextMenu.cmb000.addItems_(items, 'Selection Editors:')

		cmb002 = self.sb.selection.cmb002
		items = ['IK Handles','Joints','Clusters','Lattices','Sculpt Objects','Wires','Transforms','Geometry','NURBS Curves','NURBS Surfaces','Polygon Geometry','Cameras','Lights','Image Planes','Assets','Fluids','Particles','Rigid Bodies','Rigid Constraints','Brushes','Strokes','Dynamic Constraints','Follicles','nCloths','nParticles','nRigids']
		cmb002.addItems_(items, 'By Type:')

		cmb003 = self.sb.selection.cmb003
		items = ['Verts', 'Vertex Faces', 'Vertex Perimeter', 'Edges', 'Edge Loop', 'Edge Ring', 'Contained Edges', 'Edge Perimeter', 'Border Edges', 'Faces', 'Face Path', 'Contained Faces', 'Face Perimeter', 'UV\'s', 'UV Shell', 'UV Shell Border', 'UV Perimeter', 'UV Edge Loop', 'Shell', 'Shell Border'] 
		cmb003.addItems_(items, 'Convert To:')

		cmb005 = self.sb.selection.cmb005
		items = ['Angle', 'Border', 'Edge Loop', 'Edge Ring', 'Shell', 'UV Edge Loop']
		cmb005.addItems_(items, 'Off')


	def txt001(self):
		'''Select By Name
		'''
		searchStr = str(self.sb.selection.txt001.text()) #asterisk denotes startswith*, *endswith, *contains* 
		if searchStr:
			selection = pm.select(pm.ls (searchStr))


	def lbl000(self):
		'''Selection Sets: Create New
		'''
		cmb = self.sb.selection.cmb001
		if not cmb.isEditable():
			cmb.addItems_('', ascending=True)
			cmb.setEditable(True)
			cmb.lineEdit().setPlaceholderText('New Set:')
		else:
			name = cmb.currentText()
			self.creatNewSelectionSet(name)
			self.cmb001() #refresh the sets comboBox
			cmb.setCurrentIndex(0)


	def lbl001(self):
		'''Selection Sets: Modify Current
		'''
		cmb = self.sb.selection.cmb001
		if not cmb.isEditable():
			name = cmb.currentText()
			self._oldSetName = name
			cmb.setEditable(True)
			cmb.lineEdit().setPlaceholderText(name)
		else:
			name = cmb.currentText()
			self.modifySet(self._oldSetName)
			cmb.setItemText(cmb.currentIndex(), name)
			# self.cmb001() #refresh the sets comboBox


	def lbl002(self):
		'''Selection Sets: Delete Current
		'''
		cmb = self.sb.selection.cmb001
		name = cmb.currentText()

		pm.delete(name)

		self.cmb001() #refresh the sets comboBox


	def lbl003(self):
		'''Grow Selection
		'''
		pm.mel.GrowPolygonSelectionRegion()


	def lbl004(self):
		'''Shrink Selection
		'''
		pm.mel.ShrinkPolygonSelectionRegion()


	def lbl005(self):
		'''Selection Sets: Select Current
		'''
		cmb = self.sb.selection.cmb001
		name = cmb.currentText()

		if cmb.currentIndex()>0:
			pm.select(name) # pm.select(name, noExpand=1) #Select The Selection Set Itself (Not Members Of) (noExpand=select set)


	@Slots.hideMain
	def chk004(self, state=None):
		'''Ignore Backfacing (Camera Based Selection)
		'''
		if self.selection_submenu_ui.chk004.isChecked():
			pm.selectPref(useDepth=True)
			self.messageBox('Camera-based selection <hl>On</hl>.', messageType='Result')
		else:
			pm.selectPref(useDepth=False)
			self.messageBox('Camera-based selection <hl>Off</hl>.', messageType='Result')


	def chk008(self, state=None):
		'''Toggle Soft Selection
		'''
		if self.selection_submenu_ui.chk008.isChecked():
			pm.softSelect(edit=1, softSelectEnabled=True)
			self.messageBox('Soft Select <hl>On</hl>.', messageType='Result')
		else:
			pm.softSelect(edit=1, softSelectEnabled=False)
			self.messageBox('Soft Select <hl>Off</hl>.', messageType='Result')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.selection.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Polygon Selection Constraints':
				pm.mel.PolygonSelectionConstraints()
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Selection Sets
		'''
		cmb = self.sb.selection.cmb001

		items = [str(s) for s in pm.ls(et='objectSet', flatten=1)]
		cmb.addItems_(items, clear=True)


	def cmb002(self, index=-1):
		'''Select by Type
		'''
		cmb = self.sb.selection.cmb002

		if index>0:
			text = cmb.items[index]
			if text=='IK Handles': #
				type_ = pm.ls(type=['ikHandle', 'hikEffector'])
			elif text=='Joints': #
				type_ = pm.ls(type='joint')
			elif text=='Clusters': #
				type_ = pm.listTransforms(type='clusterHandle')
			elif text=='Lattices': #
				type_ = pm.listTransforms(type='lattice')
			elif text=='Sculpt Objects': #
				type_ = pm.listTransforms(type=['implicitSphere', 'sculpt'])
			elif text=='Wires': #
				type_ = pm.ls(type='wire')
			elif text=='Transforms': #
				type_ = pm.ls(type='transform')
			elif text=='Geometry': #Select all Geometry
				geometry = pm.ls(geometry=True)
				type_ = pm.listRelatives(geometry, p=True, path=True) #pm.listTransforms(type='nRigid')
			elif text=='NURBS Curves': #
				type_ = pm.listTransforms(type='nurbsCurve')
			elif text=='NURBS Surfaces': #
				type_ = pm.ls(type='nurbsSurface')
			elif text=='Polygon Geometry': #
				type_ = pm.listTransforms(type='mesh')
			elif text=='Cameras': #
				type_ = pm.listTransforms(cameras=1)
			elif text=='Lights': #
				type_ = pm.listTransforms(lights=1)
			elif text=='Image Planes': #
				type_ = pm.ls(type='imagePlane')
			elif text=='Assets': #
				type_ = pm.ls(type=['container', 'dagContainer'])
			elif text=='Fluids': #
				type_ = pm.listTransforms(type='fluidShape')
			elif text=='Particles': #
				type_ = pm.listTransforms(type='particle')
			elif text=='Rigid Bodies': #
				type_ = pm.listTransforms(type='rigidBody')
			elif text=='Rigid Constraints': #
				type_ = pm.ls(type='rigidConstraint')
			elif text=='Brushes': #
				type_ = pm.ls(type='brush')
			elif text=='Strokes': #
				type_ = pm.listTransforms(type='stroke')
			elif text=='Dynamic Constraints': #
				type_ = pm.listTransforms(type='dynamicConstraint')
			elif text=='Follicles': #
				type_ = pm.listTransforms(type='follicle')
			elif text=='nCloths': #
				type_ = pm.listTransforms(type='nCloth')
			elif text=='nParticles': #
				type_ = pm.listTransforms(type='nParticle')
			elif text=='nRigids': #
				type_ = pm.listTransforms(type='nRigid')

			pm.select(type_)
			cmb.setCurrentIndex(0)


	def cmb003(self, index=-1):
		'''Convert To
		'''
		cmb = self.sb.selection.cmb003

		if index>0:
			text = cmb.items[index]
			if text=='Verts': #Convert Selection To Vertices
				pm.mel.PolySelectConvert(3)
			elif text=='Vertex Faces': #
				pm.mel.PolySelectConvert(5)
			elif text=='Vertex Perimeter': #
				pm.mel.ConvertSelectionToVertexPerimeter()
			elif text=='Edges': #Convert Selection To Edges
				pm.mel.PolySelectConvert(2)
			elif text=='Edge Loop': #
				pm.mel.polySelectSp(loop=1)
			elif text=='Edge Ring': #Convert Selection To Edge Ring
				pm.mel.SelectEdgeRingSp()
			elif text=='Contained Edges': #
				pm.mel.PolySelectConvert(20)
			elif text=='Edge Perimeter': #
				pm.mel.ConvertSelectionToEdgePerimeter()
			elif text=='Border Edges': #
				pm.select(self.getBorderEdgeFromFace())
			elif text=='Faces': #Convert Selection To Faces
				pm.mel.PolySelectConvert(1)
			elif text=='Face Path': #
				pm.mel.polySelectEdges('edgeRing')
			elif text=='Contained Faces': #
				pm.mel.PolySelectConvert(10)
			elif text=='Face Perimeter': #
				pm.mel.polySelectFacePerimeter()
			elif text=='UV\'s': #
				pm.mel.PolySelectConvert(4)
			elif text=='UV Shell': #
				pm.mel.polySelectBorderShell(0)
			elif text=='UV Shell Border': #
				pm.mel.polySelectBorderShell(1)
			elif text=='UV Perimeter': #
				pm.mel.ConvertSelectionToUVPerimeter()
			elif text=='UV Edge Loop': #
				pm.mel.polySelectEdges('edgeUVLoopOrBorder')
			elif text=='Shell': #
				pm.mel.polyConvertToShell()
			elif text=='Shell Border': #
				pm.mel.polyConvertToShellBorder()
			cmb.setCurrentIndex(0)


	def cmb005(self, index=-1):
		'''Selection Contraints
		'''
		cmb = self.sb.selection.cmb005

		if index>0:
			text = cmb.items[index]
			if text=='Angle':
				pm.mel.dR_selConstraintAngle() #dR_DoCmd("selConstraintAngle");
			elif text=='Border':
				pm.mel.dR_selConstraintBorder() #dR_DoCmd("selConstraintBorder");
			elif text=='Edge Loop':
				pm.mel.dR_selConstraintEdgeLoop() #dR_DoCmd("selConstraintEdgeLoop");
			elif text=='Edge Ring':
				pm.mel.dR_selConstraintEdgeRing() #dR_DoCmd("selConstraintEdgeRing");
			elif text=='Shell':
				pm.mel.dR_selConstraintElement() #dR_DoCmd("selConstraintElement");
			elif text=='UV Edge Loop':
				pm.mel.dR_selConstraintUVEdgeLoop() #dR_DoCmd("selConstraintUVEdgeLoop");
		else:
			pm.mel.dR_selConstraintOff() #dR_DoCmd("selConstraintOff");


	def cmb006(self, index=-1):
		'''Currently Selected Objects
		'''
		cmb = self.sb.selection.draggable_header.contextMenu.cmb006

		cmb.clear()
		items = [str(i) for i in pm.ls(sl=1, flatten=1)]
		widgets = [cmb.menu_.add('QCheckBox', setText=t, setChecked=1) for t in items[:50]] #selection list is capped with a slice at 50 elements.

		for w in widgets:
			try:
				w.disconnect() #disconnect all previous connections.

			except TypeError:
				pass #if no connections are present; pass
			w.toggled.connect(lambda state, widget=w: self.chkxxx(state=state, widget=widget))


	def chkxxx(self, **kwargs):
		'''Transform Constraints: Constraint CheckBoxes
		'''
		try:
			pm.select(kwargs['widget'].text(), deselect=(not kwargs['state']))
		except KeyError:
			pass


	def tb000(self, state=None):
		'''Select Nth
		'''
		tb = self.sb.selection.tb000

		edgeRing = tb.contextMenu.chk000.isChecked()
		edgeLoop = tb.contextMenu.chk001.isChecked()
		pathAlongLoop = tb.contextMenu.chk009.isChecked()
		shortestPath = tb.contextMenu.chk002.isChecked()
		borderEdges = tb.contextMenu.chk010.isChecked()
		step = tb.contextMenu.s003.value()

		selection = pm.ls(sl=1)
		if not selection:
			self.messageBox('Operation requires a valid selection.')
			return

		result=[]
		if edgeRing:
			result = self.getEdgePath(selection, 'edgeRing')

		elif edgeLoop:
			result = self.getEdgePath(selection, 'edgeLoop')

		elif pathAlongLoop:
			result = self.getPathAlongLoop(selection)

		elif shortestPath:
			result = self.getShortestPath(selection)

		elif borderEdges:
			result = self.getBorderComponents(selection, returnCompType='edges')

		pm.select(result[::step])


	def tb001(self, state=None):
		'''Select Similar
		'''
		tb = self.sb.selection.tb001

		tol = tb.contextMenu.s000.value() #tolerance
		v = tb.contextMenu.chk011.isChecked() #vertex
		e = tb.contextMenu.chk012.isChecked() #edge
		f = tb.contextMenu.chk013.isChecked() #face
		t = tb.contextMenu.chk014.isChecked() #triangle
		s = tb.contextMenu.chk015.isChecked() #shell
		uv = tb.contextMenu.chk016.isChecked() #uvcoord
		a = tb.contextMenu.chk017.isChecked() #area
		wa = tb.contextMenu.chk018.isChecked() #world area
		b = tb.contextMenu.chk019.isChecked() #bounding box
		inc = tb.contextMenu.chk020.isChecked() #select the original objects

		objMode = pm.selectMode(query=1, object=1)
		if objMode:
			selection = pm.ls(sl=1, objectsOnly=1)
			pm.select(clear=1)
			for obj in selection:
				similar = self.sb.edit.slots.getSimilarMesh(obj, tol=tol, includeOrig=inc, vertex=v, edge=e, face=f, uvcoord=uv, triangle=t, shell=s, boundingBox=b, area=a, worldArea=wa)
				pm.select(similar, add=True)
		else:
			pm.mel.doSelectSimilar(1, {tol})


	def tb002(self, state=None):
		'''Select Island: Select Polygon Face Island
		'''
		tb = self.sb.selection.tb002

		rangeX = float(tb.contextMenu.s002.value())
		rangeY = float(tb.contextMenu.s004.value())
		rangeZ = float(tb.contextMenu.s005.value())

		selectedFaces = self.getComponents(componentType='faces')
		if not selectedFaces:
			self.messageBox('The operation requires a face selection.')
			return

		similarFaces = self.sb.normals.slots.getFacesWithSimilarNormals(selectedFaces, rangeX=rangeX, rangeY=rangeY, rangeZ=rangeZ)
		islands = self.getContigiousIslands(similarFaces)
		island = [i for i in islands if bool(set(i) & set(selectedFaces))]
		pm.select(island)


	def tb003(self, state=None):
		'''Select Edges By Angle
		'''
		tb = self.sb.selection.tb003

		angleLow = tb.contextMenu.s006.value()
		angleHigh = tb.contextMenu.s007.value()

		objects = pm.ls(sl=1, objectsOnly=1)
		edges = Slots_maya.getEdgesByNormalAngle(objects, lowAngle=angleLow, highAngle=angleHigh)
		pm.select(edges)

		pm.selectMode(component=1)
		pm.selectType(edge=1)


	def b016(self):
		'''Convert Selection To Vertices
		'''
		pm.mel.PolySelectConvert(3)


	def b017(self):
		'''Convert Selection To Edges
		'''
		pm.mel.PolySelectConvert(2)


	def b018(self):
		'''Convert Selection To Faces
		'''
		pm.mel.PolySelectConvert(1)


	def b019(self):
		'''Convert Selection To Edge Ring
		'''
		pm.mel.SelectEdgeRingSp()


	@staticmethod
	def setSelectionStyle(ctx):
		'''Set the selection style context.

		:Parameters:
			ctx (str) = Selection style context. Possible values include: 'marquee', 'lasso', 'paint'.
		'''
		ctx = ctx+'Context'
		if pm.contextInfo(ctx, exists=True):
			pm.deleteUI(ctx)

		if ctx=='marqueeContext':
			ctx = pm.selectContext(ctx)
		elif ctx=='lassoContext':
			ctx = pm.lassoContext(ctx)
		elif ctx=='paintContext':
			ctx = pm.artSelectCtx(ctx)

		pm.setToolTo(ctx)


	def generateUniqueSetName(self, obj=None):
		'''Generate a generic name based on the object's name.

		:Parameters:
			obj (str)(obj)(list) = The maya scene object to derive a unique name from.

		<objectName>_Set<int>
		'''
		if obj is None:
			obj = pm.ls(sl=1)
		num = self.cycle(list(range(99)), 'selectionSetNum')
		name = '{0}_Set{1}'.format(pm.ls(obj, objectsOnly=1, flatten=1)[0].name, num) #ie. pCube1_Set0

		return name


	def creatNewSelectionSet(self, name=None):
		'''Selection Sets: Create a new selection set.
		'''
		if pm.objExists(name):
			self.messageBox('Set with name <hl>{}</hl> already exists.'.format(name))
			return

		else: #create set
			if not name: #name=='set#Set': #generate a generic name based on obj.name
				name = self.generateUniqueSetName()

			pm.sets(name=name, text="gCharacterSet")


	def modifySet(self, name):
		'''Selection Sets: Modify Current by renaming or changing the set members.
		'''
		newName = self.sb.selection.cmb001.currentText()
		if not newName:
			newName = self.generateUniqueSetName()
		name = pm.rename(name, newName)

		if pm.objExists(name):
			pm.sets(name, clear=1)
			pm.sets(name, add=1) #if set exists; clear set and add current selection









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------