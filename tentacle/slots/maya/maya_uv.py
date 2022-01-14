# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class Uv(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		Slots_maya.loadPlugin('Unfold3D.mll')

		ctx = self.uv_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya UV Editors')
			ctx.add('QPushButton', setText='Create UV Snapshot', setObjectName='b001', setToolTip='Save an image file of the current UV layout.')

		cmb = self.uv_ui.draggable_header.contextMenu.cmb000
		items = ['UV Editor','UV Set Editor','UV Tool Kit','UV Linking: Texture-Centric','UV Linking: UV-Centric','UV Linking: Paint Effects/UV','UV Linking: Hair/UV','Flip UV']
		cmb.addItems_(items, 'Maya UV Editors')

		cmb = self.uv_ui.cmb001
		cmb.popupStyle = 'qmenu'
		panel = pm.getPanel(scriptType='polyTexturePlacementPanel')
		checkered = pm.textureWindow(panel, displayCheckered=1, query=1)
		borders = True if pm.polyOptions(query=1, displayMapBorder=1) else False
		distortion = pm.textureWindow(panel, query=1, displayDistortion=1)
		cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName='chk014', setText='Checkered', setChecked=checkered, setToolTip='')
		cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName='chk015', setText='Borders', setChecked=borders, setToolTip='')
		cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName='chk016', setText='Distortion', setChecked=distortion, setToolTip='')

		cmb = self.uv_ui.cmb002
		items = ['Flip U', 'Flip V', 'Align U Left', 'Align U Middle', 'Align U Right', 'Align V Top', 'Align V Middle', 'Align V Bottom', 'Linear Align']
		cmb.addItems_(items, 'Transform:')

		ctx = self.uv_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Pre-Scale Mode: ', setObjectName='s009', setMinMax_='0-2 step1', setValue=1, setToolTip='Allow shell scaling during packing.')
			ctx.add('QSpinBox', setPrefix='Pre-Rotate Mode: ', setObjectName='s010', setMinMax_='0-2 step1', setValue=1, setToolTip='Allow shell rotation during packing.')
			ctx.add('QDoubleSpinBox', setPrefix='Rotate Step: ', setObjectName='s007', setMinMax_='0.0-360 step22.5', setValue=22.5, setToolTip='Set the allowed rotation increment contraint.')
			ctx.add('QSpinBox', setPrefix='Stack Similar: ', setObjectName='s011', setMinMax_='0-2 step1', setValue=0, setToolTip='Find Similar shells. <br>state 1: Find similar shells, and pack one of each, ommiting the rest.<br>state 2: Find similar shells, and stack during packing.')
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s006', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack Similar: Stack shells with uv\'s within the given range.')
			ctx.add('QSpinBox', setPrefix='UDIM: ', setObjectName='s004', setMinMax_='1001-1200 step1', setValue=1001, setToolTip='Set the desired UDIM tile space.')
			ctx.add('QSpinBox', setPrefix='Map Size: ', setObjectName='s005', setMinMax_='512-8192 step512', setValue=2048, setToolTip='UV map resolution.')

		ctx = self.uv_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
			ctx.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
			ctx.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
			ctx.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
			ctx.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
			ctx.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
			ctx.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')
			# ctx.chk001.toggled.connect(lambda state: self.toggleWidgets(ctx, setUnChecked='chk002-3') if state==1 else None)

		ctx = self.uv_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Orient', setObjectName='chk021', setChecked=True, setToolTip='Orient UV shells to run parallel with the most adjacent U or V axis.')
			ctx.add('QCheckBox', setText='Stack Similar', setObjectName='chk022', setChecked=True, setToolTip='Stack only shells that fall within the set tolerance.')
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')

		ctx = self.uv_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Back-Facing', setObjectName='chk008', setToolTip='Select all back-facing (using counter-clockwise winding order) components for the current selection.')
			ctx.add('QRadioButton', setText='Front-Facing', setObjectName='chk009', setToolTip='Select all front-facing (using counter-clockwise winding order) components for the current selection.')
			ctx.add('QRadioButton', setText='Overlapping', setObjectName='chk010', setToolTip='Select all components that share the same uv space.')
			ctx.add('QRadioButton', setText='Non-Overlapping', setObjectName='chk011', setToolTip='Select all components that do not share the same uv space.')
			ctx.add('QRadioButton', setText='Texture Borders', setObjectName='chk012', setToolTip='Select all components on the borders of uv shells.')
			ctx.add('QRadioButton', setText='Unmapped', setObjectName='chk013', setChecked=True, setToolTip='Select unmapped faces in the current uv set.')

		ctx = self.uv_ui.tb004.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Optimize', setObjectName='chk017', setToolTip='The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).')
			# ctx.add('QSpinBox', setPrefix='Optimize Amount: ', setObjectName='s008', setMinMax_='0-100 step1', setValue=25, setToolTip='The number of times to run optimize on the unfolded mesh.')

		ctx = self.uv_ui.tb005.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Angle: ', setObjectName='s001', setMinMax_='0-360 step1', setValue=30, setToolTip='Set the maximum angle used for straightening uv\'s.')
			ctx.add('QCheckBox', setText='Straighten U', setObjectName='chk018', setChecked=True, setToolTip='Unfold UV\'s along a horizonal contraint.')
			ctx.add('QCheckBox', setText='Straighten V', setObjectName='chk019', setChecked=True, setToolTip='Unfold UV\'s along a vertical constaint.')
			ctx.add('QCheckBox', setText='Straighten Shell', setObjectName='chk020', setToolTip='Straighten a UV shell by unfolding UV\'s around a selected UV\'s edgeloop.')

		ctx = self.uv_ui.tb006.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Distribute U', setObjectName='chk023', setChecked=True, setToolTip='Distribute along U.')
			ctx.add('QRadioButton', setText='Distribute V', setObjectName='chk024', setToolTip='Distribute along V.')

		ctx = self.uv_ui.tb007.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Map Size: ', setObjectName='s002', setMinMax_='512-8192 step512', setValue=2048, setToolTip='Set the map used as reference when getting texel density.')
			ctx.add('QDoubleSpinBox', setPrefix='Texel Density: ', setObjectName='s003', setMinMax_='0.00-128 step8', setValue=32, setToolTip='Set the desired texel density.')
			ctx.add('QPushButton', setText='Get Texel Density', setObjectName='b099', setChecked=True, setToolTip='Get the average texel density of any selected faces.')
			ctx.b099.released.connect(lambda: ctx.s003.setValue(float(pm.mel.texGetTexelDensity(ctx.s002.value())))) #get and set texel density value.


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.uv_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.uv_ui.draggable_header.contextMenu.cmb000

		if index>0: #hide tentacle then perform operation
			text = cmb.items[index]
			self.tcl.hide()
			if text=='UV Editor':
				mel.eval('TextureViewWindow;') 
			elif text=='UV Set Editor':
				mel.eval('uvSetEditor;')
			elif text=='UV Tool Kit':
				mel.eval('toggleUVToolkit;')
			elif text=='UV Linking: Texture-Centric':
				mel.eval('textureCentricUvLinkingEditor;')
			elif text=='UV Linking: UV-Centric':
				mel.eval('uvCentricUvLinkingEditor;')
			elif text=='UV Linking: Paint Effects/UV':
				mel.eval('pfxUVLinkingEditor;')
			elif text=='UV Linking: Hair/UV':
				mel.eval('hairUVLinkingEditor;')
			elif text=='Flip UV':
				mel.eval("performPolyForceUV flip 1;")
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Display
		'''
		cmb = self.uv_ui.cmb001


	def cmb002(self, index=-1):
		'''Transform
		'''
		cmb = self.uv_ui.cmb002

		if index>0:
			text = cmb.items[index]
			self.tcl.hide() #hide hotbox then perform operation
			if text=='Flip U':
				pm.polyFlipUV(flipType=0, local=1, usePivot=1, pivotU=0, pivotV=0)
			elif text=='Flip V':
				pm.polyFlipUV(flipType=1, local=1, usePivot=1, pivotU=0, pivotV=0)
			elif text=='Align U Left':
				pm.mel.performAlignUV('minU')
			elif text=='Align U Middle':
				pm.mel.performAlignUV('avgU')
			elif text=='Align U Right':
				pm.mel.performAlignUV('maxU')
			elif text=='Align U Top':
				pm.mel.performAlignUV('maxV')
			elif text=='Align U Middle':
				pm.mel.performAlignUV('avgV')
			elif text=='Align U Bottom':
				pm.mel.performAlignUV('minV')
			elif text=='Linear Align':
				pm.mel.performLinearAlignUV()
			cmb.setCurrentIndex(0)


	def chk001(self, state):
		'''Auto Unwrap: Scale Mode CheckBox
		'''
		tb = self.uv_ui.tb001
		if state==0:
			tb.contextMenu.chk001.setText('Scale Mode 0')
		if state==1:
			tb.contextMenu.chk001.setText('Scale Mode 1')
			self.toggleWidgets(tb.contextMenu, setUnChecked='chk002-6')
		if state==2:
			tb.contextMenu.chk001.setText('Scale Mode 2')


	def chk014(self):
		'''Display: Checkered Pattern
		'''
		cmb = self.uv_ui.cmb001
		state = cmb.menu_.chk014.isChecked()

		panel = pm.getPanel(scriptType='polyTexturePlacementPanel')
		pm.textureWindow(panel, edit=1, displayCheckered=state)


	def chk015(self):
		'''Display: Borders
		'''
		cmb = self.uv_ui.cmb001
		state = cmb.menu_.chk015.isChecked()

		borderWidth = pm.optionVar(query='displayPolyBorderEdgeSize')[1]
		borders = pm.polyOptions(displayMapBorder=state, sizeBorder=borderWidth)


	def chk016(self):
		'''Display: Distortion
		'''
		cmb = self.uv_ui.cmb001
		state = cmb.menu_.chk016.isChecked()

		panel = pm.getPanel(scriptType='polyTexturePlacementPanel')
		pm.textureWindow(panel, edit=1, displayDistortion=state)


	def tb000(self, state=None):
		'''Pack UV's

		pm.u3dLayout:
			layoutScaleMode (int),
			multiObject (bool),
			mutations (int),
			packBox (float, float, float, float),
			preRotateMode (int),
			preScaleMode (int),
			resolution (int),
			rotateMax (float),
			rotateMin (float),
			rotateStep (float),
			shellSpacing (float),
			tileAssignMode (int),
			tileMargin (float),
			tileU (int),
			tileV (int),
			translate (bool)
		'''
		tb = self.uv_ui.tb000

		scale = tb.contextMenu.s009.value()
		rotate = tb.contextMenu.s010.value()
		rotateStep = tb.contextMenu.s007.value()
		UDIM = tb.contextMenu.s004.value()
		mapSize = tb.contextMenu.s005.value()
		similar = tb.contextMenu.s011.value()
		tolerance = tb.contextMenu.s006.value()

		U,D,I,M = [int(i) for i in str(UDIM)]

		sel = self.UvShellSelection() #assure the correct selection mask.
		if similar>0:
			dissimilar = pm.polyUVStackSimilarShells(sel, tolerance=tolerance, onlyMatch=True)
			dissimilarUVs = [s.split() for s in dissimilar] if dissimilar else []
			dissimilarFaces = pm.polyListComponentConversion(dissimilarUVs, fromUV=1, toFace=1)
			pm.u3dLayout(dissimilarFaces, resolution=mapSize, preScaleMode=scale, preRotateMode=rotate, rotateStep=rotateStep, shellSpacing=.005, tileMargin=.005, packBox=[M-1, D, I, U]) #layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)

		elif similar==2:
			pm.select(dissimilarFaces, toggle=1)
			similarFaces = pm.ls(sl=1)
			pm.polyUVStackSimilarShells(similarFaces, dissimilarFaces, tolerance=tolerance)

		else:
			pm.u3dLayout(sel, resolution=mapSize, preScaleMode=scale, preRotateMode=rotate, rotateStep=rotateStep, shellSpacing=.005, tileMargin=.005, packBox=[M-1, D, I, U]) #layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)


	@Slots_maya.attr
	def tb001(self, state=None):
		'''Auto Unwrap
		'''
		tb = self.uv_ui.tb001

		standardUnwrap = tb.contextMenu.chk000.isChecked()
		scaleMode = tb.contextMenu.chk001.isChecked()
		seamOnly = tb.contextMenu.chk002.isChecked()
		planarUnwrap = tb.contextMenu.chk003.isChecked()
		cylindricalUnwrap = tb.contextMenu.chk004.isChecked()
		sphericalUnwrap = tb.contextMenu.chk005.isChecked()
		normalBasedUnwrap = tb.contextMenu.chk006.isChecked()

		selection = pm.ls(selection=1, flatten=1)
		for obj in selection:
			try:
				if seamOnly:
					autoSeam = pm.u3dAutoSeam(obj, s=0, p=1)
					return autoSeam if len(selection)==1 else autoSeam

				elif any((cylindricalUnwrap, sphericalUnwrap, planarUnwrap)):
					unwrapType = 'Planar'
					if cylindricalUnwrap:
						unwrapType = 'Cylindrical'
					elif sphericalUnwrap:
						unwrapType = 'Spherical'
					objFaces = Slots_maya.getComponents('f', obj, selection=1)
					if not objFaces:
						objFaces = Slots_maya.getComponents('f', obj)
					pm.polyProjection(objFaces, type=unwrapType, insertBeforeDeformers=1, smartFit=1)

				elif normalBasedUnwrap:
					pm.mel.texNormalProjection(1, 1, obj) #Normal-Based unwrap

				elif standardUnwrap:
					polyAutoProjection = pm.polyAutoProjection (obj, layoutMethod=0, optimize=1, insertBeforeDeformers=1, scaleMode=scaleMode, createNewMap=False, #Create a new UV set, as opposed to editing the current one, or the one given by the -uvSetName flag.
						projectBothDirections=0, #If "on" : projections are mirrored on directly opposite faces. If "off" : projections are not mirrored on opposite faces. 
						layout=2, #0 UV pieces are set to no layout. 1 UV pieces are aligned along the U axis. 2 UV pieces are moved in a square shape.
						planes=6, #intermediate projections used. Valid numbers are 4, 5, 6, 8, and 12
						percentageSpace=0.2, #percentage of the texture area which is added around each UV piece.
						worldSpace=0) #1=world reference. 0=object reference.

					return polyAutoProjection if len(selection)==1 else polyAutoProjection

			except Exception as error:
				print(error)


	def tb002(self, state=None):
		'''Stack
		'''
		tb = self.uv_ui.tb002

		orient = tb.contextMenu.chk021.isChecked()
		stackSimilar = tb.contextMenu.chk022.isChecked()
		tolerance = tb.contextMenu.s000.value()
		sel = self.UvShellSelection() #assure the correct selection mask.

		if stackSimilar:
			pm.polyUVStackSimilarShells(sel, tolerance=tolerance)
		else:
			pm.mel.texStackShells([])
		if orient:
			pm.mel.texOrientShells()


	def tb003(self, state=None):
		'''Select By Type
		'''
		tb = self.uv_ui.tb003

		back_facing = tb.contextMenu.chk008.isChecked()
		front_facing = tb.contextMenu.chk009.isChecked()
		overlapping = tb.contextMenu.chk010.isChecked()
		nonOverlapping = tb.contextMenu.chk011.isChecked()
		textureBorders = tb.contextMenu.chk012.isChecked()
		unmapped = tb.contextMenu.chk013.isChecked()

		if back_facing:
			pm.mel.selectUVFaceOrientationComponents({}, 0, 2, 1)
		elif front_facing:
			pm.mel.selectUVFaceOrientationComponents({}, 0, 1, 1)
		elif overlapping:
			pm.mel.selectUVOverlappingComponents(1, 0)
		elif nonOverlapping:
			pm.mel.selectUVOverlappingComponents(0, 0)
		elif textureBorders:
			pm.mel.selectUVBorderComponents({}, "", 1)
		elif unmapped:
			pm.mel.selectUnmappedFaces()


	def tb004(self, state=None):
		'''Unfold

		Synopsis: u3dUnfold [flags] [String...]
		Flags:
		  -bi -borderintersection  on|off
		 -ite -iterations          Int
		  -ms -mapsize             Int
		   -p -pack                on|off
		  -rs -roomspace           Int
		  -tf -triangleflip        on|off

		Synopsis: u3dOptimize [flags] [String...]
		Flags:
		  -bi -borderintersection  on|off
		 -ite -iterations          Int
		  -ms -mapsize             Int
		 -pow -power               Int
		  -rs -roomspace           Int
		  -sa -surfangle           Float
		  -tf -triangleflip        on|off
		'''
		tb = self.uv_ui.tb004

		optimize = tb.contextMenu.chk017.isChecked()
		amount = 1#tb.contextMenu.s008.value()

		pm.u3dUnfold(iterations=1, pack=0, borderintersection=1, triangleflip=1, mapsize=2048, roomspace=0) #pm.mel.performUnfold(0)

		if optimize:
			pm.u3dOptimize(iterations=amount, power=1, surfangle=1, borderintersection=0, triangleflip=1, mapsize=2048, roomspace=0) #pm.mel.performPolyOptimizeUV(0)


	def tb005(self, state=None):
		'''Straighten Uv
		'''
		tb = self.uv_ui.tb005

		u = tb.contextMenu.chk018.isChecked()
		v = tb.contextMenu.chk019.isChecked()
		angle = tb.contextMenu.s001.value()
		straightenShell = tb.contextMenu.chk020.isChecked()

		if u and v:
			pm.mel.texStraightenUVs('UV', angle)
		elif u:
			pm.mel.texStraightenUVs('U', angle)
		elif v:
			pm.mel.texStraightenUVs('V', angle)

		if straightenShell:
			pm.mel.texStraightenShell()


	def tb006(self, state=None):
		'''Distribute
		'''
		tb = self.uv_ui.tb006

		u = tb.contextMenu.chk023.isChecked()
		v = tb.contextMenu.chk024.isChecked()
		
		if u:
			pm.mel.texDistributeShells(0, 0, "right", []) #'left', 'right'
		if v:
			pm.mel.texDistributeShells(0, 0, "down", []) #'up', 'down'


	def tb007(self, state=None):
		'''Set Texel Density
		'''
		tb = self.uv_ui.tb007

		mapSize = tb.contextMenu.s002.value()
		density = tb.contextMenu.s003.value()

		pm.mel.texSetTexelDensity(density, mapSize)


	def b001(self):
		'''Create UV Snapshot
		'''
		pm.mel.UVCreateSnapshot()


	@Slots_maya.undoChunk
	@Slots.message
	def b002(self):
		'''Transfer Uv's
		'''
		selection = pm.ls(orderedSelection=1, flatten=1)
		if len(selection)<2:
			return 'Error: <b>Nothing selected.</b><br>The operation requires the selection of two polygon objects.'

		# pm.undoInfo(openChunk=1)
		set1 = pm.listRelatives(selection[0], children=1)
		set2 = pm.listRelatives(selection[1:], children=1)

		for frm in set1:
			for to in set2:
				if pm.polyEvaluate(frm)==pm.polyEvaluate(to):
					pm.transferAttributes(frm, to, transferUVs=2, sampleSpace=4) #-transferNormals 0 -transferUVs 2 -transferColors 2 -sourceUvSpace "map1" -targetUvSpace "map1" -searchMethod 3-flipUVs 0 -colorBorders 1 ;
					print('Result: UV sets transferred from: {} to: {}.'.format(frm.name(), to.name()))
					pm.bakePartialHistory(frm, prePostDeformers=1)
		# pm.undoInfo(closeChunk=1)


	def b005(self):
		'''Cut Uv'S
		'''
		objects = pm.ls(selection=1, objectsOnly=1, shapes=1, flatten=1)

		for obj in objects:
			sel = pm.ls(obj, sl=1)
			pm.polyMapCut(sel)


	def b011(self):
		'''Sew Uv'S
		'''
		objects = pm.ls(selection=1, objectsOnly=1, shapes=1, flatten=1)

		for obj in objects:
			sel = pm.ls(obj, sl=1)

			pm.polyMapSew(sel) if len(objects)==1 else pm.polyMapSew(sel)
 

	def b023(self):
		'''Move To Uv Space: Left
		'''
		self.moveSelectedToUvSpace(-1, 0) #move left


	def b024(self):
		'''Move To Uv Space: Down
		'''
		self.moveSelectedToUvSpace(0, -1) #move down


	def b025(self):
		'''Move To Uv Space: Up
		'''
		self.moveSelectedToUvSpace(0, 1) #move up


	def b026(self):
		'''Move To Uv Space: Right
		'''
		self.moveSelectedToUvSpace(1, 0) #move right


	def moveSelectedToUvSpace(self, u, v, relative=True):
		'''Move sny selected objects to the given u and v coordinates.

		:Parameters:
			u (int) = u coordinate.
			v (int) = v coordinate.
			relative (bool) = Move relative or absolute.
		'''
		sel = self.UvShellSelection() #assure the correct selection mask.

		pm.polyEditUV(sel, u=u, v=v, relative=relative)


	@Slots.message
	def UvShellSelection(self):
		'''Select all faces of any selected geometry, and switch the component mode to uv shell,
		if the current selection is not maskFacet, maskUv, or maskUvShell.

		:Return:
			(list) the selected faces.
		'''
		selection = pm.ls(sl=1)
		if not selection:
			return 'Error: <b>Nothing selected.<b><br>The operation requires at lease one selected object.'

		objects = pm.ls(selection, objectsOnly=1)
		objectMode = pm.selectMode(query=1, object=1)

		maskFacet = pm.selectType(query=1, facet=1)
		maskUv = pm.selectType(query=1, polymeshUV=1)
		maskUvShell = pm.selectType(query=1, meshUVShell=1)

		if all((objects, objectMode)) or not any((objectMode, maskFacet, maskUv, maskUvShell)):

			for obj in objects:
				pm.selectMode(component=1)
				pm.selectType(meshUVShell=1)
				selection = Slots_maya.getComponents('f', obj, flatten=False)
				pm.select(selection, add=True)

		return selection


	def getUvShellSets(self, objects=None, returnType='shells'):
		'''Get All UV shells and their corresponding sets of faces.

		:Parameters:
			objects (obj)(list) = Polygon object(s) or Polygon face(s).
			returnType (str) = The desired returned type. valid values are: 'shells', 'shellIDs'. If None is given, the full dict will be returned.

		:Return:
			(list)(dict) dependant on the given returnType arg. ex. {0L:[[MeshFace(u'pShape.f[0]'), MeshFace(u'pShape.f[1]')], 1L:[[MeshFace(u'pShape.f[2]'), MeshFace(u'pShape.f[3]')]}
		'''
		if not objects:
			objects = pm.ls(selection=1, objectsOnly=1, transforms=1, flatten=1)

		if not isinstance(objects, (list, set, tuple)):
			objects=[objects]

		objectType = Slots_maya.getObjectType(objects[0])
		if objectType=='Polygon Face':
			faces = objects
		else:
			faces = Slots_maya.getComponents(objects, 'faces')

		shells={}
		for face in faces:
			shell_Id = pm.polyEvaluate(face, uvShellIds=True)

			try:
				shells[shell_Id[0]].append(face)
			except KeyError:
				try:
					shells[shell_Id[0]]=[face]
				except IndexError:
					pass

		if returnType=='shells':
			shells = list(shells.values())
		elif returnType=='shellIDs':
			shells = shells.keys()

		return shells


	def getUvShellBorderEdges(self, objects):
		'''Get the edges that make up any UV islands of the given objects.

		:Parameters:
			objects (str)(obj)(list) = Polygon mesh objects.

		:Return:
			(list) uv border edges.
		'''
		mesh_edges=[]
		for obj in pm.ls(objects, objectsOnly=1):
			try: # Try to get edges from provided objects.
				mesh_edges.extend(pm.ls(pm.polyListComponentConversion(obj, te=True), fl=True, l=True))
			except Exception as error:
				pass

		if len(mesh_edges)<=0: # Error if no valid objects were found
			raise RuntimeError('No valid mesh objects or components were provided.')

		pm.progressWindow(t='Find UV Border Edges', pr=0, max=len(mesh_edges), ii=True) # Start progressWindow
		
		uv_border_edges = list() # Find and return uv border edges
		for edge in mesh_edges:  # Filter through the mesh(s) edges.

			if pm.progressWindow(q=True, ic=True): # Kill if progress window is cancelled
				pm.progressWindow(ep=True)  # End progressWindow
				raise RuntimeError('Cancelled by user.')

			pm.progressWindow(e=True, s=1, st=edge) # Update the progress window status
			
			edge_uvs = pm.ls(pm.polyListComponentConversion(edge, tuv=True), fl=True)
			edge_faces = pm.ls(pm.polyListComponentConversion(edge, tf=True), fl=True)
			if len(edge_uvs) > 2:  # If an edge has more than two uvs, it is a uv border edge.
				uv_border_edges.append(edge)
			elif len(edge_faces) < 2:  # If an edge has less than 2 faces, it is a border edge.
				uv_border_edges.append(edge)

		pm.progressWindow(ep=True) # End progressWindow

		return uv_border_edges









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------