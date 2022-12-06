# !/usr/bin/python
# coding=utf-8
from slots.blender import *
from slots.selection import Selection


class Selection_blender(Selection, Slots_blender):
	def __init__(self, *args, **kwargs):
		Slots_blender.__init__(self, *args, **kwargs)
		Selection.__init__(self, *args, **kwargs)

		cmb = self.sb.selection.draggable_header.ctxMenu.cmb000
		items = []
		cmb.addItems_(items, 'Selection Editors:')

		cmb = self.sb.selection.cmb002
		items = []
		cmb.addItems_(items, 'By Type:')

		cmb = self.sb.selection.cmb003
		items = [] 
		cmb.addItems_(items, 'Convert To:')

		cmb = self.sb.selection.cmb005
		items = []
		items = cmb.addItems_(items, 'Off')


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
		mel.eval('GrowPolygonSelectionRegion;')


	def lbl004(self):
		'''Shrink Selection
		'''
		mel.eval('ShrinkPolygonSelectionRegion;')


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
			return 'Camera-based selection <hl>On</hl>.'
		else:
			pm.selectPref(useDepth=False)
			return 'Camera-based selection <hl>Off</hl>.'


	def chk008(self, state=None):
		'''Toggle Soft Selection
		'''
		if self.selection_submenu_ui.chk008.isChecked():
			pm.softSelect(edit=1, softSelectEnabled=True)
			return 'Soft Select <hl>On</hl>.'
		else:
			pm.softSelect(edit=1, softSelectEnabled=False)
			return 'Soft Select <hl>Off</hl>.'


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


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.selection.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Polygon Selection Constraints':
				mel.eval('PolygonSelectionConstraints;')
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
				mel.eval('PolySelectConvert 3;')
			elif text=='Vertex Faces': #
				mel.eval('PolySelectConvert 5;')
			elif text=='Vertex Perimeter': #
				mel.eval('ConvertSelectionToVertexPerimeter;')
			elif text=='Edges': #Convert Selection To Edges
				mel.eval('PolySelectConvert 2;')
			elif text=='Edge Loop': #
				mel.eval('polySelectSp -loop;')
			elif text=='Edge Ring': #Convert Selection To Edge Ring
				mel.eval('SelectEdgeRingSp;')
			elif text=='Contained Edges': #
				mel.eval('PolySelectConvert 20;')
			elif text=='Edge Perimeter': #
				mel.eval('ConvertSelectionToEdgePerimeter;')
			elif text=='Border Edges': #
				pm.select(self.getBorderEdgeFromFace())
			elif text=='Faces': #Convert Selection To Faces
				mel.eval('PolySelectConvert 1;')
			elif text=='Face Path': #
				mel.eval('polySelectEdges edgeRing;')
			elif text=='Contained Faces': #
				mel.eval('PolySelectConvert 10;')
			elif text=='Face Perimeter': #
				mel.eval('polySelectFacePerimeter;')
			elif text=='UV\'s': #
				mel.eval('PolySelectConvert 4;')
			elif text=='UV Shell': #
				mel.eval('polySelectBorderShell 0;')
			elif text=='UV Shell Border': #
				mel.eval('polySelectBorderShell 1;')
			elif text=='UV Perimeter': #
				mel.eval('ConvertSelectionToUVPerimeter;')
			elif text=='UV Edge Loop': #
				mel.eval('polySelectEdges edgeUVLoopOrBorder;')
			elif text=='Shell': #
				mel.eval('polyConvertToShell;')
			elif text=='Shell Border': #
				mel.eval('polyConvertToShellBorder;')
			cmb.setCurrentIndex(0)


	def cmb005(self, index=-1):
		'''Selection Contraints
		'''
		cmb = self.sb.selection.cmb005

		if index>0:
			text = cmb.items[index]
			if text=='Angle':
				mel.eval('dR_selConstraintAngle;') #dR_DoCmd("selConstraintAngle");
			elif text=='Border':
				mel.eval('dR_selConstraintBorder;') #dR_DoCmd("selConstraintBorder");
			elif text=='Edge Loop':
				mel.eval('dR_selConstraintEdgeLoop;') #dR_DoCmd("selConstraintEdgeLoop");
			elif text=='Edge Ring':
				mel.eval('dR_selConstraintEdgeRing;') #dR_DoCmd("selConstraintEdgeRing");
			elif text=='Shell':
				mel.eval('dR_selConstraintElement;') #dR_DoCmd("selConstraintElement");
			elif text=='UV Edge Loop':
				mel.eval('dR_selConstraintUVEdgeLoop;') #dR_DoCmd("selConstraintUVEdgeLoop");
		else:
			mel.eval('dR_selConstraintOff;') #dR_DoCmd("selConstraintOff");


	def cmb006(self, index=-1):
		'''Currently Selected Objects
		'''
		cmb = self.sb.selection.draggable_header.ctxMenu.cmb006

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

		edgeRing = tb.ctxMenu.chk000.isChecked()
		edgeLoop = tb.ctxMenu.chk001.isChecked()
		pathAlongLoop = tb.ctxMenu.chk009.isChecked()
		shortestPath = tb.ctxMenu.chk002.isChecked()
		borderEdges = tb.ctxMenu.chk010.isChecked()
		step = tb.ctxMenu.s003.value()

		selection = pm.ls(sl=1)
		if not selection:
			return 'Error: Operation requires a valid selection.'

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

		tolerance = str(tb.ctxMenu.s000.value()) #string value because mel.eval is sending a command string

		mel.eval("doSelectSimilar 1 {\""+ tolerance +"\"}")


	def tb002(self, state=None):
		'''Select Island: Select Polygon Face Island
		'''
		tb = self.sb.selection.tb002

		rangeX = float(tb.ctxMenu.s002.value())
		rangeY = float(tb.ctxMenu.s004.value())
		rangeZ = float(tb.ctxMenu.s005.value())

		selectedFaces = pm.filterExpand(sm=34)
		if selectedFaces:
			similarFaces = self.sb.normals.slots.getFacesWithSimilarNormals(selectedFaces, rangeX=rangeX, rangeY=rangeY, rangeZ=rangeZ)
			islands = self.getContigiousIslands(similarFaces)
			island = [i for i in islands if bool(set(i) & set(selectedFaces))]
			pm.select(island)

		else:
			return 'Warning: No faces were selected.'


	def tb003(self, state=None):
		'''Select Edges By Angle
		'''
		tb = self.sb.selection.tb003

		angleLow = tb.ctxMenu.s006.value()
		angleHigh = tb.ctxMenu.s007.value()

		objects = pm.ls(sl=1, objectsOnly=1)
		edges = Slots_blender.getEdgesByNormalAngle(objects, lowAngle=angleLow, highAngle=angleHigh)
		pm.select(edges)


	def b016(self):
		'''Convert Selection To Vertices
		'''
		mel.eval('PolySelectConvert 3;')


	def b017(self):
		'''Convert Selection To Edges
		'''
		mel.eval('PolySelectConvert 2;')


	def b018(self):
		'''Convert Selection To Faces
		'''
		mel.eval('PolySelectConvert 1;')


	def b019(self):
		'''Convert Selection To Edge Ring
		'''
		mel.eval('SelectEdgeRingSp;')


	def generateUniqueSetName(self, obj=None):
		'''Generate a generic name based on the object's name.

		:Parameters:
			obj (str)(obj)(list) = The maya scene object to derive a unique name from.

		<objectName>_Set<int>
		'''
		if obj is None:
			obj = pm.ls(sl=1)
		num = tls.cycle(list(range(99)), 'selectionSetNum')
		name = '{0}_Set{1}'.format(pm.ls(obj, objectsOnly=1, flatten=1)[0].name, num) #ie. pCube1_Set0

		return name


	def creatNewSelectionSet(self, name=None):
		'''Selection Sets: Create a new selection set.
		'''
		if pm.objExists(name):
			return 'Error: Set with name <hl>{}</hl> already exists.'.format(name)

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