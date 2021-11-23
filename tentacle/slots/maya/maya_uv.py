# !/usr/bin/python
# coding=utf-8
import os.path

from maya_init import *



class Uv(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.uv_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya UV Editors')
			dh.contextMenu.add('QPushButton', setText='Create UV Snapshot', setObjectName='b001', setToolTip='Save an image file of the current UV layout.')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.uv_ui.draggable_header.contextMenu.cmb000

		if index is 'setMenu':
			list_ = ['UV Editor','UV Set Editor','UV Tool Kit','UV Linking: Texture-Centric','UV Linking: UV-Centric','UV Linking: Paint Effects/UV','UV Linking: Hair/UV','Flip UV']
			cmb.addItems_(list_, 'Maya UV Editors')
			return

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

		if index is 'setMenu':
			cmb.popupStyle = 'qmenu'

			try:
				panel = pm.getPanel(scriptType='polyTexturePlacementPanel')
				checkered = pm.textureWindow(panel, displayCheckered=1, query=1)
				borders = True if pm.polyOptions(query=1, displayMapBorder=1) else False
				distortion = pm.textureWindow(panel, query=1, displayDistortion=1)

				cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName='chk014', setText='Checkered', setChecked=checkered, setToolTip='')
				cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName='chk015', setText='Borders', setChecked=borders, setToolTip='')
				cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName='chk016', setText='Distortion', setChecked=distortion, setToolTip='')

			except NameError as error:
				print(error)
			return


	def cmb002(self, index=-1):
		'''Transform
		'''
		cmb = self.uv_ui.cmb002

		if index is 'setMenu':
			list_ = ['Flip U', 'Flip V', 'Align U Left', 'Align U Middle', 'Align U Right', 'Align V Top', 'Align V Middle', 'Align V Bottom', 'Linear Align']
			cmb.addItems_(list_, 'Transform:')
			return

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
		tb = self.current_ui.tb001
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
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.contextMenu.add(self.tcl.wgts.CheckBox, setText='Pre-Scale Mode: 1', setObjectName='chk025', setTristate=True, setCheckState_=1, setToolTip='Allow shell scaling during packing.')
			tb.contextMenu.add(self.tcl.wgts.CheckBox, setText='Pre-Rotate Mode: 1', setObjectName='chk007', setTristate=True, setCheckState_=1, setToolTip='Allow shell rotation during packing.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Rotate Step: ', setObjectName='s007', setMinMax_='0.0-360 step22.5', setValue=22.5, setToolTip='Set the allowed rotation increment contraint.')
			tb.contextMenu.add(self.tcl.wgts.CheckBox, setText='Stack Similar: 2', setObjectName='chk026', setTristate=True, setCheckState_=2, setToolTip='Find Similar shells. <br>state 1: Find similar shells, and pack one of each, ommiting the rest.<br>state 2: Find similar shells, and stack during packing.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Stack Similar Tolerance: ', setObjectName='s006', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')
			tb.contextMenu.add('QSpinBox', setPrefix='UDIM: ', setObjectName='s004', setMinMax_='1001-1200 step1', setValue=1001, setToolTip='Set the desired UDIM tile space.')
			tb.contextMenu.add('QSpinBox', setPrefix='Map Size: ', setObjectName='s005', setMinMax_='512-8192 step512', setValue=2048, setToolTip='UV map resolution.')

			tb.contextMenu.chk025.stateChanged.connect(lambda state: tb.contextMenu.chk025.setText('Pre-Scale Mode: '+str(state)))
			tb.contextMenu.chk007.stateChanged.connect(lambda state: tb.contextMenu.chk007.setText('Pre-Rotate Mode: '+str(state)))
			tb.contextMenu.chk026.stateChanged.connect(lambda state: tb.contextMenu.chk026.setText('Stack Similar: '+str(state)))
			return

		scale = tb.contextMenu.chk025.isChecked()
		rotate = tb.contextMenu.chk007.isChecked()
		rotateStep = tb.contextMenu.s007.value()
		UDIM = tb.contextMenu.s004.value()
		mapSize = tb.contextMenu.s005.value()
		similar = tb.contextMenu.chk026.checkState_()
		tolerance = tb.contextMenu.s006.value()

		U,D,I,M = [int(i) for i in str(UDIM)]

		sel = Uv.UvShellSelection() #assure the correct selection mask.
		if similar > 0:
			dissimilar = pm.polyUVStackSimilarShells(sel, tolerance=tolerance, onlyMatch=True)
			dissimilarUVs = [s.split() for s in dissimilar] if dissimilar else []
			dissimilarFaces = pm.polyListComponentConversion(dissimilarUVs, fromUV=1, toFace=1)
			pm.u3dLayout(dissimilarFaces, resolution=mapSize, preScaleMode=scale, preRotateMode=rotate, rotateStep=rotateStep, shellSpacing=.005, tileMargin=.005, packBox=[M-1, D, I, U]) #layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)
		if similar is 2:
			pm.select(dissimilarFaces, toggle=1)
			similarFaces = pm.ls(sl=1)
			pm.polyUVStackSimilarShells(similarFaces, dissimilarFaces, tolerance=tolerance)

		else:
			pm.u3dLayout(sel, resolution=mapSize, preScaleMode=scale, preRotateMode=rotate, rotateStep=rotateStep, shellSpacing=.005, tileMargin=.005, packBox=[M-1, D, I, U]) #layoutScaleMode (int), multiObject (bool), mutations (int), packBox (float, float, float, float), preRotateMode (int), preScaleMode (int), resolution (int), rotateMax (float), rotateMin (float), rotateStep (float), shellSpacing (float), tileAssignMode (int), tileMargin (float), tileU (int), tileV (int), translate (bool)


	@Init.attr
	def tb001(self, state=None):
		'''Auto Unwrap
		'''
		tb = self.current_ui.tb001
		if state is 'setMenu':
			tb.contextMenu.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
			tb.contextMenu.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
			tb.contextMenu.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
			tb.contextMenu.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
			tb.contextMenu.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
			tb.contextMenu.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
			tb.contextMenu.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')

			# tb.contextMenu.chk001.toggled.connect(lambda state: self.toggleWidgets(tb.contextMenu, setUnChecked='chk002-3') if state==1 else None)
			return

		standardUnwrap = self.uv_ui.chk000.isChecked()
		scaleMode = self.uv_ui.chk001.isChecked()
		seamOnly = self.uv_ui.chk002.isChecked()
		planarUnwrap = self.uv_ui.chk003.isChecked()
		cylindricalUnwrap = self.uv_ui.chk004.isChecked()
		sphericalUnwrap = self.uv_ui.chk005.isChecked()
		normalBasedUnwrap = self.uv_ui.chk006.isChecked()

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
					objFaces = Init.getComponents('f', obj, selection=1)
					if not objFaces:
						objFaces = Init.getComponents('f', obj)
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
		tb = tb = self.uv_ui.tb002
		if state is 'setMenu':
			tb.contextMenu.add('QCheckBox', setText='Orient', setObjectName='chk021', setChecked=True, setToolTip='Orient UV shells to run parallel with the most adjacent U or V axis.')
			tb.contextMenu.add('QCheckBox', setText='Stack Similar', setObjectName='chk022', setChecked=True, setToolTip='Stack only shells that fall within the set tolerance.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')
			return

		orient = tb.contextMenu.chk021.isChecked()
		stackSimilar = tb.contextMenu.chk022.isChecked()
		tolerance = tb.contextMenu.s000.value()
		sel = Uv.UvShellSelection() #assure the correct selection mask.

		if stackSimilar:
			pm.polyUVStackSimilarShells(sel, tolerance=tolerance)
		else:
			pm.mel.texStackShells([])
		if orient:
			pm.mel.texOrientShells()


	def tb003(self, state=None):
		'''Select By Type
		'''
		tb = tb = self.uv_ui.tb003
		if state is 'setMenu':
			tb.contextMenu.add('QRadioButton', setText='Back-Facing', setObjectName='chk008', setToolTip='Select all back-facing (using counter-clockwise winding order) components for the current selection.')
			tb.contextMenu.add('QRadioButton', setText='Front-Facing', setObjectName='chk009', setToolTip='Select all front-facing (using counter-clockwise winding order) components for the current selection.')
			tb.contextMenu.add('QRadioButton', setText='Overlapping', setObjectName='chk010', setToolTip='Select all components that share the same uv space.')
			tb.contextMenu.add('QRadioButton', setText='Non-Overlapping', setObjectName='chk011', setToolTip='Select all components that do not share the same uv space.')
			tb.contextMenu.add('QRadioButton', setText='Texture Borders', setObjectName='chk012', setToolTip='Select all components on the borders of uv shells.')
			tb.contextMenu.add('QRadioButton', setText='Unmapped', setObjectName='chk013', setChecked=True, setToolTip='Select unmapped faces in the current uv set.')
			return

		back_facing = self.uv_ui.chk008.isChecked()
		front_facing = self.uv_ui.chk009.isChecked()
		overlapping = self.uv_ui.chk010.isChecked()
		nonOverlapping = self.uv_ui.chk011.isChecked()
		textureBorders = self.uv_ui.chk012.isChecked()
		unmapped = self.uv_ui.chk013.isChecked()

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
		tb = self.current_ui.tb004
		if state is 'setMenu':
			tb.contextMenu.add('QCheckBox', setText='Optimize', setObjectName='chk017', setToolTip='The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).')
			# tb.contextMenu.add('QSpinBox', setPrefix='Optimize Amount: ', setObjectName='s008', setMinMax_='0-100 step1', setValue=25, setToolTip='The number of times to run optimize on the unfolded mesh.')
			return

		optimize = tb.contextMenu.chk017.isChecked()
		amount = 1#tb.contextMenu.s008.value()

		pm.u3dUnfold(iterations=1, pack=0, borderintersection=1, triangleflip=1, mapsize=2048, roomspace=0) #pm.mel.performUnfold(0)

		if optimize:
			pm.u3dOptimize(iterations=amount, power=1, surfangle=1, borderintersection=0, triangleflip=1, mapsize=2048, roomspace=0) #pm.mel.performPolyOptimizeUV(0)


	def tb005(self, state=None):
		'''Straighten Uv
		'''
		tb = tb = self.uv_ui.tb005
		if state is 'setMenu':
			tb.contextMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s001', setMinMax_='0-360 step1', setValue=30, setToolTip='Set the maximum angle used for straightening uv\'s.')
			tb.contextMenu.add('QCheckBox', setText='Straighten U', setObjectName='chk018', setChecked=True, setToolTip='Unfold UV\'s along a horizonal contraint.')
			tb.contextMenu.add('QCheckBox', setText='Straighten V', setObjectName='chk019', setChecked=True, setToolTip='Unfold UV\'s along a vertical constaint.')
			tb.contextMenu.add('QCheckBox', setText='Straighten Shell', setObjectName='chk020', setToolTip='Straighten a UV shell by unfolding UV\'s around a selected UV\'s edgeloop.')
			return

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
		tb = tb = self.uv_ui.tb006
		if state is 'setMenu':
			tb.contextMenu.add('QRadioButton', setText='Distribute U', setObjectName='chk023', setChecked=True, setToolTip='Distribute along U.')
			tb.contextMenu.add('QRadioButton', setText='Distribute V', setObjectName='chk024', setToolTip='Distribute along V.')
			return

		u = tb.contextMenu.chk023.isChecked()
		v = tb.contextMenu.chk024.isChecked()
		
		if u:
			pm.mel.texDistributeShells(0, 0, "right", []) #'left', 'right'
		if v:
			pm.mel.texDistributeShells(0, 0, "down", []) #'up', 'down'


	def tb007(self, state=None):
		'''Set Texel Density
		'''
		tb = tb = self.uv_ui.tb007
		if state is 'setMenu':
			tb.contextMenu.add('QSpinBox', setPrefix='Map Size: ', setObjectName='s002', setMinMax_='512-8192 step512', setValue=2048, setToolTip='Set the map used as reference when getting texel density.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Texel Density: ', setObjectName='s003', setMinMax_='0.00-128 step8', setValue=32, setToolTip='Set the desired texel density.')
			tb.contextMenu.add('QPushButton', setText='Get Texel Density', setObjectName='b099', setChecked=True, setToolTip='Get the average texel density of any selected faces.')

			tb.contextMenu.b099.released.connect(lambda: tb.contextMenu.s003.setValue(float(pm.mel.texGetTexelDensity(tb.contextMenu.s002.value())))) #get and set texel density value.
			return

		mapSize = tb.contextMenu.s002.value()
		density = tb.contextMenu.s003.value()

		pm.mel.texSetTexelDensity(density, mapSize)


	def b000(self):
		'''Cut Uv Hard Edges
		'''
		pm.mel.cutUvHardEdge()


	def b001(self):
		'''Create UV Snapshot
		'''
		pm.mel.UVCreateSnapshot()


	@Init.undoChunk
	def b002(self):
		'''Transfer Uv's
		'''
		sel = pm.ls(orderedSelection=1, flatten=1)
		if len(sel)<2:
			Slots.messageBox('Error: The operation requires the selection of two polygon objects.')

		# pm.undoInfo(openChunk=1)
		from_ = sel[0]
		to = sel[1:]

		for i in to: # 0:no UV sets, 1:single UV set (specified by sourceUVSet and targetUVSet args), and 2:all UV sets are transferred.
			pm.transferAttributes(from_, i, transferUVs=2)
			print('Result: UV sets transferred from: {} to: {}.'.format(from_.name(), i.name()))
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
		Uv.moveSelectedToUvSpace(-1, 0) #move left


	def b024(self):
		'''Move To Uv Space: Down
		'''
		Uv.moveSelectedToUvSpace(0, -1) #move down


	def b025(self):
		'''Move To Uv Space: Up
		'''
		Uv.moveSelectedToUvSpace(0, 1) #move up


	def b026(self):
		'''Move To Uv Space: Right
		'''
		Uv.moveSelectedToUvSpace(1, 0) #move right


	@staticmethod
	def moveSelectedToUvSpace(u, v, relative=True):
		'''Move sny selected objects to the given u and v coordinates.

		:Parameters:
			u (int) = u coordinate.
			v (int) = v coordinate.
			relative (bool) = Move relative or absolute.
		'''
		sel = Uv.UvShellSelection() #assure the correct selection mask.

		pm.polyEditUV(sel, u=u, v=v, relative=relative)


	@staticmethod
	def UvShellSelection():
		'''Select all faces of any selected geometry, and switch the component mode to uv shell,
		if the current selection is not maskFacet, maskUv, or maskUvShell.

		:Return:
			(list) the selected faces.
		'''
		selection = pm.ls(sl=1)
		if not selection:
			Slots.messageBox('Error: Nothing selected.')

		objects = pm.ls(selection, objectsOnly=1)
		objectMode = pm.selectMode(query=1, object=1)

		maskFacet = pm.selectType(query=1, facet=1)
		maskUv = pm.selectType(query=1, polymeshUV=1)
		maskUvShell = pm.selectType(query=1, meshUVShell=1)

		if all((objects, objectMode)) or not any((objectMode, maskFacet, maskUv, maskUvShell)):

			for obj in objects:
				pm.selectMode(component=1)
				pm.selectType(meshUVShell=1)
				selection = Init.getComponents('f', obj, flatten=False)
				pm.select(selection, add=True)

		return selection








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------