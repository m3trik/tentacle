# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Uv(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.uv_ui.draggable_header.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya UV Editors')
		ctx.add('QPushButton', setText='Create UV Snapshot', setObjectName='b001', setToolTip='Save an image file of the current UV layout.')

		cmb = self.uv_ui.draggable_header.contextMenu.cmb000
		items = ['UV Editor','UV Set Editor','UV Tool Kit','UV Linking: Texture-Centric','UV Linking: UV-Centric','UV Linking: Paint Effects/UV','UV Linking: Hair/UV']
		cmb.addItems_(items, '3dsMax UV Editors')

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
		ctx.add(self.tcl.wgts.CheckBox, setText='Pre-Scale Mode: 1', setObjectName='chk025', setTristate=True, setCheckState_=1, setToolTip='Allow shell scaling during packing.')
		ctx.add(self.tcl.wgts.CheckBox, setText='Pre-Rotate Mode: 1', setObjectName='chk007', setTristate=True, setCheckState_=1, setToolTip='Allow shell rotation during packing.')
		ctx.add('QDoubleSpinBox', setPrefix='Rotate Step: ', setObjectName='s007', setMinMax_='0.0-360 step22.5', setValue=22.5, setToolTip='Set the allowed rotation increment contraint.')
		ctx.add(self.tcl.wgts.CheckBox, setText='Stack Similar: 2', setObjectName='chk026', setTristate=True, setCheckState_=2, setToolTip='Find Similar shells. <br>state 1: Find similar shells, and pack one of each, ommiting the rest.<br>state 2: Find similar shells, and stack during packing.')
		ctx.add('QDoubleSpinBox', setPrefix='Stack Similar Tolerance: ', setObjectName='s006', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')
		ctx.add('QSpinBox', setPrefix='UDIM: ', setObjectName='s004', setMinMax_='1001-1200 step1', setValue=1001, setToolTip='Set the desired UDIM tile space.')
		ctx.add('QSpinBox', setPrefix='Map Size: ', setObjectName='s005', setMinMax_='512-8192 step512', setValue=2048, setToolTip='UV map resolution.')
		ctx.chk025.stateChanged.connect(lambda state: ctx.chk025.setText('Pre-Scale Mode: '+str(state)))
		ctx.chk007.stateChanged.connect(lambda state: ctx.chk007.setText('Pre-Rotate Mode: '+str(state)))
		ctx.chk026.stateChanged.connect(lambda state: ctx.chk026.setText('Stack Similar: '+str(state)))

		ctx = self.uv_ui.tb001.contextMenu
		ctx.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
		ctx.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
		ctx.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
		ctx.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
		ctx.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
		ctx.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
		ctx.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')
		# ctx.chk001.toggled.connect(lambda state: self.toggleWidgets(ctx, setUnChecked='chk002-3') if state==1 else None)

		ctx = self.uv_ui.tb002.contextMenu
		ctx.add('QCheckBox', setText='Orient', setObjectName='chk021', setChecked=True, setToolTip='Orient UV shells to run parallel with the most adjacent U or V axis.')
		ctx.add('QCheckBox', setText='Stack Similar', setObjectName='chk022', setChecked=True, setToolTip='Stack only shells that fall within the set tolerance.')
		ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')

		ctx = self.uv_ui.tb003.contextMenu
		ctx.add('QRadioButton', setText='Back-Facing', setObjectName='chk008', setToolTip='Select all back-facing (using counter-clockwise winding order) components for the current selection.')
		ctx.add('QRadioButton', setText='Front-Facing', setObjectName='chk009', setToolTip='Select all front-facing (using counter-clockwise winding order) components for the current selection.')
		ctx.add('QRadioButton', setText='Overlapping', setObjectName='chk010', setToolTip='Select all components that share the same uv space.')
		ctx.add('QRadioButton', setText='Non-Overlapping', setObjectName='chk011', setToolTip='Select all components that do not share the same uv space.')
		ctx.add('QRadioButton', setText='Texture Borders', setObjectName='chk012', setToolTip='Select all components on the borders of uv shells.')
		ctx.add('QRadioButton', setText='Unmapped', setObjectName='chk013', setChecked=True, setToolTip='Select unmapped faces in the current uv set.')

		ctx = self.uv_ui.tb004.contextMenu
		ctx.add('QCheckBox', setText='Optimize', setObjectName='chk017', setToolTip='The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).')
		# ctx.add('QSpinBox', setPrefix='Optimize Amount: ', setObjectName='s008', setMinMax_='0-100 step1', setValue=25, setToolTip='The number of times to run optimize on the unfolded mesh.')

		ctx = self.uv_ui.tb005.contextMenu
		ctx.add('QSpinBox', setPrefix='Angle: ', setObjectName='s001', setMinMax_='0-360 step1', setValue=30, setToolTip='Set the maximum angle used for straightening uv\'s.')
		ctx.add('QCheckBox', setText='Straighten U', setObjectName='chk018', setChecked=True, setToolTip='Unfold UV\'s along a horizonal contraint.')
		ctx.add('QCheckBox', setText='Straighten V', setObjectName='chk019', setChecked=True, setToolTip='Unfold UV\'s along a vertical constaint.')
		ctx.add('QCheckBox', setText='Straighten Shell', setObjectName='chk020', setToolTip='Straighten a UV shell by unfolding UV\'s around a selected UV\'s edgeloop.')

		ctx = self.uv_ui.tb006.contextMenu
		ctx.add('QRadioButton', setText='Distribute U', setObjectName='chk023', setChecked=True, setToolTip='Distribute along U.')
		ctx.add('QRadioButton', setText='Distribute V', setObjectName='chk024', setToolTip='Distribute along V.')

		ctx = self.uv_ui.tb007.contextMenu
		ctx.add('QSpinBox', setPrefix='Map Size: ', setObjectName='s002', setMinMax_='512-8192 step512', setValue=2048, setToolTip='Set the map used as reference when getting texel density.')
		ctx.add('QDoubleSpinBox', setPrefix='Texel Density: ', setObjectName='s003', setMinMax_='0.00-128 step8', setValue=32, setToolTip='Set the desired texel density.')
		ctx.add('QPushButton', setText='Get Texel Density', setObjectName='b099', setChecked=True, setToolTip='Get the average texel density of any selected faces.')
		ctx.b099.released.connect(lambda: ctx.s003.setValue(float(pm.mel.texGetTexelDensity(ctx.s002.value())))) #get and set texel density value.


	@property
	def uvModifier():
		'''Get the UV modifier for the current object.
		If one doesn't exist, a UV modifier will be added to the selected object.

		:Return:
			(obj) uv modifier.
		'''
		selection = rt.selection
		if not selection:
			Slots.messageBox('Error: Nothing selected.')

		mod = self.getModifier(selection[0], 'Unwrap_UVW', -1) #get/set the uv xform modifier.
		return mod


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.uv_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.uv_ui.draggable_header.contextMenu.cmb000

		if index>0: #hide hotbox then perform operation
			self.tcl.hide()
			if index==1: #UV Editor
				maxEval('TextureViewWindow;') 
			elif index==2: #UV Set Editor
				maxEval('uvSetEditor;')
			elif index==3: #UV Tool Kit
				maxEval('toggleUVToolkit;')
			elif index==4: #UV Linking: Texture-Centric
				maxEval('textureCentricUvLinkingEditor;')
			elif index==5: #UV Linking: UV-Centric
				maxEval('uvCentricUvLinkingEditor;')
			elif index==6: #UV Linking: Paint Effects/UV
				maxEval('pfxUVLinkingEditor;')
			elif index==7: #UV Linking: Hair/UV
				maxEval('hairUVLinkingEditor;')
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
		pass


	def chk014(self):
		'''Display: Checkered Pattern
		'''
		cmb = self.uv_ui.cmb001
		state = cmb.menu_.chk014.isChecked()

		self.toggleMaterialOverride(checker=state)


	def chk015(self):
		'''Display: Borders
		'''
		cmb = self.uv_ui.cmb001
		state = cmb.menu_.chk015.isChecked()

		borderWidth = pm.optionVar(query='displayPolyBorderEdgeSize')[1]
		borders = pm.polyOptions(displayMapBorder=state, sizeBorder=borderWidth)


	@Slots.message
	def chk016(self):
		'''Display: Distortion
		'''
		cmb = self.uv_ui.cmb001
		state = cmb.menu_.chk016.isChecked()

		# actionMan.executeAction 2077580866 "40177"  -- Unwrap UVW: Show Edge Distortion
		mod = self.uv_uiModifier #get/set the uv modifier.

		mod.localDistortion = state
		return '{0}{1}'.format('localDistortion:', state)


	def tb000(self, state=None):
		'''Pack UV's

		#pack command: Lets you pack the texture vertex elements so that they fit within a square space.
		# --method - 0 is a linear packing algorithm fast but not that efficient, 1 is a recursive algorithm slower but more efficient.
		# --spacing - the gap between cluster in percentage of the edge distance of the square
		# --normalize - determines whether the clusters will be fit to 0 to 1 space.
		# --rotate - determines whether a cluster will be rotated so it takes up less space.
		# --fillholes - determines whether smaller clusters will be put in the holes of the larger cluster.
		'''
		tb = self.current_ui.tb000
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Scale', setObjectName='chk025', setChecked=True, setToolTip='Allow shell scaling during packing.')
			tb.contextMenu.add('QCheckBox', setText='Rotate', setObjectName='chk007', setChecked=True, setToolTip='Allow shell rotation during packing.')
			return

		scale = tb.contextMenu.chk025.isChecked()
		rotate = tb.contextMenu.chk007.isChecked()

		obj = rt.selection[0]

		self.uv_uiModifier.pack(1, 0.01, scale, rotate, True) #(method, spacing, normalize, rotate, fillholes)


	@Slots_max.attr
	def tb001(self, state=None):
		'''Auto Unwrap
		'''
		tb = self.current_ui.tb001

		standardUnwrap = tb.contextMenu.chk000.isChecked()
		scaleMode = tb.contextMenu.chk001.isChecked()
		seamOnly = tb.contextMenu.chk002.isChecked()
		planarUnwrap = tb.contextMenu.chk003.isChecked()
		cylindricalUnwrap = tb.contextMenu.chk004.isChecked()
		sphericalUnwrap = tb.contextMenu.chk005.isChecked()
		normalBasedUnwrap = tb.contextMenu.chk006.isChecked()

		objects = rt.selection

		for obj in objects:
			if standardUnwrap:
				try:
					self.uv_uiModifier.FlattenBySmoothingGroup(scaleMode, False, 0.2)

				except Exception as error:
					print(error)


	def tb002(self, state=None):
		'''Stack
		'''
		tb = self.uv_ui.tb002

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
		'''
		tb = self.current_ui.tb004

		optimize = self.tb.contextMenu.chk017.isChecked()

		# if optimize:
		# 	# self.uv_uiModifier.
		# else:
		self.uv_uiModifier.relax(1, 0.01, True, True)


	def tb005(self, state=None):
		'''Straighten Uv
		'''
		tb = self.uv_ui.tb005

		u = tb.contextMenu.chk018.isChecked()
		v = tb.contextMenu.chk019.isChecked()
		angle = tb.contextMenu.s001.value()
		straightenShell = tb.contextMenu.chk020.isChecked()

		# if u:
		# 	contraint = 'U'
		# if v:
		# 	constaint = 'V' if not u else 'UV'

		self.uv_uiModifier.Straighten()

		# if straightenShell:
		# 	pm.mel.texStraightenShell()


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
		tb = self.current_ui.tb007

		mapSize = tb.contextMenu.s002.value()
		density = tb.contextMenu.s003.value()

		pm.mel.texSetTexelDensity(density, mapSize)


	def b001(self):
		'''Create UV Snapshot
		'''
		pass


	def b002(self):
		'''Transfer Uv's
		'''
		sel = pm.ls(orderedSelection=1, flatten=1)
		if len(sel)<2:
			Slots.messageBox('Error: The operation requires the selection of two polygon objects.')

		from_ = sel[0]
		to = sel[-1]
		pm.transferAttributes(from_, to, transferUVs=2) # 0:no UV sets, 1:single UV set (specified by sourceUVSet and targetUVSet args), and 2:all UV sets are transferred.
		Slots.messageBox('Result: UV sets transferred from: {} to: {}.'.format(from_.name(), to.name()))


	def b005(self):
		'''Cut Uv'S
		'''
		self.uv_uiModifier.breakSelected()


	def b011(self):
		'''Sew Uv'S
		'''
		self.uv_uiModifier.stitchVerts(True, 1.0) #(align, bias) --Bias of 0.0 the vertices will move to the source and 1.0 they will move to the target. 


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
		mod = self.uv_uiModifier

		pm.polyEditUV(sel, u=u, v=v, relative=relative)


	@staticmethod
	def flipUV(objects=None):
		''''''
		u = 1
		v = 0
		w = 0

		if not objects:
			objects = rt.selection

		for obj in objects:
			try:
				uv = self.uv_uiModifier #get/set the uv xform modifier.
				uv.U_Flip = u
				uv.V_Flip = v
				uv.W_Flip = w

			except Exception as error:
				print(error)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

#apply uv map
# maxEval('modPanel.addModToSelection (Uvwmap ()) ui:on')