# !/usr/bin/python
# coding=utf-8
import os.path

from maya_init import *



class Selection(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.selection_ui.draggable_header

		if state=='setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb006', setToolTip='A list of currently selected objects.')
			dh.contextMenu.add('QCheckBox', setText='Ignore Backfacing', setObjectName='chk004', setToolTip='Ignore backfacing components during selection.')
			dh.contextMenu.add('QCheckBox', setText='Soft Selection', setObjectName='chk008', setToolTip='Toggle soft selection mode.')
			dh.contextMenu.add(self.tcl.wgts.Label, setText='Grow Selection', setObjectName='lbl003', setToolTip='Grow the current selection.')
			dh.contextMenu.add(self.tcl.wgts.Label, setText='Shrink Selection', setObjectName='lbl004', setToolTip='Shrink the current selection.')
			return


	def txt001(self):
		'''Select By Name
		'''
		searchStr = str(self.selection_ui.txt001.text()) #asterisk denotes startswith*, *endswith, *contains* 
		if searchStr:
			selection = pm.select(pm.ls (searchStr))


	def lbl000(self):
		'''Selection Sets: Create New
		'''
		cmb = self.selection_ui.cmb001
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
		cmb = self.selection_ui.cmb001
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
		cmb = self.selection_ui.cmb001
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
		cmb = self.selection_ui.cmb001
		name = cmb.currentText()

		if cmb.currentIndex()>0:
			pm.select(name) # pm.select(name, noExpand=1) #Select The Selection Set Itself (Not Members Of) (noExpand=select set)


	def s002(self, value=None):
		'''Select Island: tolerance x
		'''
		tb = self.current_ui.tb002
		if tb.contextMenu.chk003.isChecked():
			text = tb.contextMenu.s002.value()
			tb.contextMenu.s004.setValue(text)
			tb.contextMenu.s005.setValue(text)


	def s004(self, value=None):
		'''Select Island: tolerance y
		'''
		tb = self.current_ui.tb002
		if tb.contextMenu.chk003.isChecked():
			text = tb.contextMenu.s004.value()
			tb.contextMenu.s002.setValue(text)
			tb.contextMenu.s005.setValue(text)


	def s005(self, value=None):
		'''Select Island: tolerance z
		'''
		tb = self.current_ui.tb002
		if tb.contextMenu.chk003.isChecked():
			text = tb.contextMenu.s005.value()
			tb.contextMenu.s002.setValue(text)
			tb.contextMenu.s004.setValue(text)


	def chk000(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk001-2')


	def chk001(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk000,chk002')


	def chk002(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk000-1')


	@Slots.hideMain
	@Slots.message
	def chk004(self, state=None):
		'''Ignore Backfacing (Camera Based Selection)
		'''
		if self.selection_submenu_ui.chk004.isChecked():
			pm.selectPref(useDepth=True)
			return 'Camera-based selection <hl>On</hl>.'
		else:
			pm.selectPref(useDepth=False)
			return 'Camera-based selection <hl>Off</hl>.'


	@Slots.message
	def chk008(self, state=None):
		'''Toggle Soft Selection
		'''
		if self.selection_submenu_ui.chk008.isChecked():
			pm.softSelect(edit=1, softSelectEnabled=True)
			return 'Soft Select <hl>On</hl>.'
		else:
			pm.softSelect(edit=1, softSelectEnabled=False)
			return 'Soft Select <hl>Off</hl>.'


	# @Slots.message
	def chk005(self, state=None):
		'''Select Style: Marquee
		'''
		self.toggleWidgets(setChecked='chk005', setUnChecked='chk006-7')
		Selection.setSelectionStyle('marquee')
		return 'Select Style: <hl>Marquee</hl>'


	# @Slots.message
	def chk006(self, state=None):
		'''Select Style: Lasso
		'''
		self.toggleWidgets(setChecked='chk006', setUnChecked='chk005,chk007')
		Selection.setSelectionStyle('lasso')
		return 'Select Style: <hl>Lasso</hl>'


	# @Slots.message
	def chk007(self, state=None):
		'''Select Style: Paint
		'''
		self.toggleWidgets(setChecked='chk007', setUnChecked='chk005-6')
		Selection.setSelectionStyle('paint')
		return 'Select Style: <hl>Paint</hl>'


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
		cmb = self.selection_ui.draggable_header.contextMenu.cmb000
		
		if index=='setMenu':
			items = ['Polygon Selection Constraints']
			cmb.addItems_(items, 'Selection Editors:')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Polygon Selection Constraints':
				mel.eval('PolygonSelectionConstraints;')
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Selection Sets
		'''
		cmb = self.selection_ui.cmb001

		if index=='setMenu':
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Select', setObjectName='lbl005', setToolTip='Select the current set elements.')
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='New', setObjectName='lbl000', setToolTip='Create a new selection set.')
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Modify', setObjectName='lbl001', setToolTip='Modify the current set by renaming and/or changing the selection.')
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current set.')
			cmb.returnPressed.connect(lambda m=cmb.contextMenu.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
			cmb.currentIndexChanged.connect(self.lbl005) #select current set on index change.
			cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.
			return

		items = [str(s) for s in pm.ls(et='objectSet', flatten=1)]
		cmb.addItems_(items, clear=True)


	def cmb002(self, index=-1):
		'''Select by Type
		'''
		cmb = self.selection_ui.cmb002	

		if index=='setMenu':
			items = ['IK Handles','Joints','Clusters','Lattices','Sculpt Objects','Wires','Transforms','Geometry','NURBS Curves','NURBS Surfaces','Polygon Geometry','Cameras','Lights','Image Planes','Assets','Fluids','Particles','Rigid Bodies','Rigid Constraints','Brushes','Strokes','Dynamic Constraints','Follicles','nCloths','nParticles','nRigids']
			cmb.addItems_(items, 'By Type:')
			return

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
		cmb = self.selection_ui.cmb003

		if index=='setMenu':
			items = ['Verts', 'Vertex Faces', 'Vertex Perimeter', 'Edges', 'Edge Loop', 'Edge Ring', 'Contained Edges', 'Edge Perimeter', 'Border Edges', 'Faces', 'Face Path', 'Contained Faces', 'Face Perimeter', 'UV\'s', 'UV Shell', 'UV Shell Border', 'UV Perimeter', 'UV Edge Loop', 'Shell', 'Shell Border'] 
			cmb.addItems_(items, 'Convert To:')
			return

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
		cmb = self.selection_ui.cmb005

		if index=='setMenu':
			items = ['Angle', 'Border', 'Edge Loop', 'Edge Ring', 'Shell', 'UV Edge Loop']
			items = cmb.addItems_(items, 'Off')
			return

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
		cmb = self.selection_ui.draggable_header.contextMenu.cmb006

		if index=='setMenu':
			cmb.setCurrentText('Current Selection') # cmb.insertItem(cmb.currentIndex(), 'Current Selection') #insert item at current index.
			cmb.popupStyle = 'qmenu'
			cmb.beforePopupShown.connect(self.cmb006) #refresh the comboBox contents before showing it's popup.
			return

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
		tb = self.current_ui.tb000
		if state=='setMenu':
			tb.contextMenu.add('QRadioButton', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
			tb.contextMenu.add('QRadioButton', setText='Component Loop', setObjectName='chk001', setChecked=True, setToolTip='Select all contiguous components that form a loop with the current selection.')
			tb.contextMenu.add('QRadioButton', setText='Path Along Loop', setObjectName='chk009', setToolTip='The path along loop between two selected edges, vertices or UV\'s.')
			tb.contextMenu.add('QRadioButton', setText='Shortest Path', setObjectName='chk002', setToolTip='The shortest component path between two selected edges, vertices or UV\'s.')
			tb.contextMenu.add('QRadioButton', setText='Border Edges', setObjectName='chk010', setToolTip='Select the object(s) border edges.')
			tb.contextMenu.add('QSpinBox', setPrefix='Step: ', setObjectName='s003', setMinMax_='1-100 step1', setValue=1, setToolTip='Step Amount.')
			return

		edgeRing = tb.contextMenu.chk000.isChecked()
		edgeLoop = tb.contextMenu.chk001.isChecked()
		pathAlongLoop = tb.contextMenu.chk009.isChecked()
		shortestPath = tb.contextMenu.chk002.isChecked()
		borderEdges = tb.contextMenu.chk010.isChecked()
		step = tb.contextMenu.s003.value()

		selection = pm.ls(sl=1)

		result=[]
		if edgeRing:
			result = self.getEdgeRing(selection, step=step)

		elif edgeLoop:
			result = self.getEdgeLoop(selection, step=step)

		elif pathAlongLoop:
			result = self.getPathAlongLoop(selection, step=step)

		elif shortestPath:
			result = self.getShortestPath(selection, step=step)

		elif borderEdges:
			result = self.getBorderComponents(selection, returnType='edges')

		pm.select(result)


	def tb001(self, state=None):
		'''Select Similar
		'''
		tb = self.current_ui.tb001
		if state=='setMenu':
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=0.3, setToolTip='Select similar objects or components, depending on selection mode.')
			return

		tolerance = str(tb.contextMenu.s000.value()) #string value because mel.eval is sending a command string

		mel.eval("doSelectSimilar 1 {\""+ tolerance +"\"}")


	@Slots.message
	def tb002(self, state=None):
		'''Select Island: Select Polygon Face Island
		'''
		tb = self.current_ui.tb002
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Lock Values', setObjectName='chk003', setChecked=True, setToolTip='Keep values in sync.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='x: ', setObjectName='s002', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal X range.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='y: ', setObjectName='s004', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Y range.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='z: ', setObjectName='s005', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Z range.')
			return

		rangeX = float(tb.contextMenu.s002.value())
		rangeY = float(tb.contextMenu.s004.value())
		rangeZ = float(tb.contextMenu.s005.value())

		selectedFaces = pm.filterExpand(sm=34)
		if selectedFaces:
			similarFaces = self.getFacesWithSimilarNormals(selectedFaces, rangeX=rangeX, rangeY=rangeY, rangeZ=rangeZ)
			islands = self.getContigiousIslands(similarFaces)
			pm.select((islands))

		else:
			return 'Warning: No faces were selected.'


	def tb003(self, state=None):
		'''Select Edges By Angle
		'''
		tb = self.selection_ui.tb003
		if state=='setMenu':
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Angle Low:  ', setObjectName='s006', setMinMax_='0.0-180 step1', setValue=50, setToolTip='Normal angle low range.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Angle High: ', setObjectName='s007', setMinMax_='0.0-180 step1', setValue=130, setToolTip='Normal angle high range.')
			return

		angleLow = tb.contextMenu.s006.value()
		angleHigh = tb.contextMenu.s007.value()

		objects = pm.ls(sl=1, objectsOnly=1)
		edges = Init.getEdgesByNormalAngle(objects, lowAngle=angleLow, highAngle=angleHigh)
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
		num = self.cycle(list(range(99)), 'selectionSetNum')
		name = '{0}_Set{1}'.format(pm.ls(obj, objectsOnly=1, flatten=1)[0].name, num) #ie. pCube1_Set0

		return name


	@Slots.message
	def creatNewSelectionSet(self, name=None):
		'''Selection Sets: Create a new selection set.
		'''
		if pm.objExists(name):
			return 'Error: Set with name <hl>{}</hl> already exists.'.format(name)

		else: #create set
			if not name: #name=='set#Set': #generate a generic name based on obj.name
				name = self.generateUniqueSetName()

			pm.sets(name=name, text="gCharacterSet")


	@Slots.message
	def modifySet(self, name):
		'''Selection Sets: Modify Current by renaming or changing the set members.
		'''
		newName = self.selection_ui.cmb001.currentText()
		if not newName:
			newName = self.generateUniqueSetName()
		name = pm.rename(name, newName)

		if pm.objExists(name):
			pm.sets(name, clear=1)
			pm.sets(name, add=1) #if set exists; clear set and add current selection









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------