# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.uv import Uv



class Uv_max(Uv, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Uv.__init__(self, *args, **kwargs)

		cmb000 = self.sb.uv.draggable_header.contextMenu.cmb000
		items = ['UV Editor','UV Set Editor','UV Tool Kit','UV Linking: Texture-Centric','UV Linking: UV-Centric','UV Linking: Paint Effects/UV','UV Linking: Hair/UV']
		cmb000.addItems_(items, '3dsMax UV Editors')

		cmb002 = self.sb.uv.cmb002
		items = ['Flip U', 'Flip V', 'Align U Left', 'Align U Middle', 'Align U Right', 'Align V Top', 'Align V Middle', 'Align V Bottom', 'Linear Align']
		cmb002.addItems_(items, 'Transform:')

		tb000 = self.sb.uv.tb000
		tb000.contextMenu.add('QSpinBox', setPrefix='Pre-Scale Mode: ', setObjectName='s009', setMinMax_='0-1 step1', setValue=1, setToolTip='Allow shell scaling during packing.')
		tb000.contextMenu.add('QSpinBox', setPrefix='Pre-Rotate Mode: ', setObjectName='s010', setMinMax_='0-1 step1', setValue=1, setToolTip='Allow shell rotation during packing.')

		tb001 = self.sb.uv.tb001
		tb001.contextMenu.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
		tb001.contextMenu.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
		tb001.contextMenu.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
		tb001.contextMenu.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
		tb001.contextMenu.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
		tb001.contextMenu.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
		tb001.contextMenu.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')
		# tb001.contextMenu.chk001.toggled.connect(lambda state: self.toggleWidgets(tb001.contextMenu, setUnChecked='chk002-3') if state==1 else None)

		# tb007 = self.sb.uv.tb007
		# tb007.contextMenu.b099.released.connect(lambda: tb007.contextMenu.s003.setValue(float(pm.mel.texGetTexelDensity(tb007.contextMenu.s002.value())))) #get and set texel density value.


	@property
	def uvModifier(self):
		'''Get the UV modifier for the current object.
		If one doesn't exist, a UV modifier will be added to the selected object.

		:Return:
			(obj) uv modifier.
		'''
		selection = rt.selection
		if not selection:
			self.messageBox('Nothing selected.')

		mod = self.getModifier(selection[0], 'Unwrap_UVW', -1) #get/set the uv xform modifier.
		return mod


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.uv.draggable_header.contextMenu.cmb000

		if index>0: #hide hotbox then perform operation
			self.sb.parent().hide()
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
		cmb = self.sb.uv.cmb001


	def cmb002(self, index=-1):
		'''Transform
		'''
		cmb = self.sb.uv.cmb002

		if index>0:
			text = cmb.items[index]
			self.sb.parent().hide() #hide hotbox then perform operation
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


	def chk014(self):
		'''Display: Checkered Pattern
		'''
		cmb = self.sb.uv.cmb001
		state = cmb.menu_.chk014.isChecked()

		self.toggleMaterialOverride(checker=state)


	def chk015(self):
		'''Display: Borders
		'''
		cmb = self.sb.uv.cmb001
		state = cmb.menu_.chk015.isChecked()

		borderWidth = pm.optionVar(query='displayPolyBorderEdgeSize')[1]
		borders = pm.polyOptions(displayMapBorder=state, sizeBorder=borderWidth)


	def chk016(self):
		'''Display: Distortion
		'''
		cmb = self.sb.uv.cmb001
		state = cmb.menu_.chk016.isChecked()

		# actionMan.executeAction 2077580866 "40177"  -- Unwrap UVW: Show Edge Distortion
		mod = self.uv_uiModifier #get/set the uv modifier.

		mod.localDistortion = state
		self.messageBox('{0}{1}'.format('localDistortion:', state))


	def tb000(self, state=None):
		'''Pack UV's

		#pack command: Lets you pack the texture vertex elements so that they fit within a square space.
		# --method - 0 is a linear packing algorithm fast but not that efficient, 1 is a recursive algorithm slower but more efficient.
		# --spacing - the gap between cluster in percentage of the edge distance of the square
		# --normalize - determines whether the clusters will be fit to 0 to 1 space.
		# --rotate - determines whether a cluster will be rotated so it takes up less space.
		# --fillholes - determines whether smaller clusters will be put in the holes of the larger cluster.
		'''
		tb = self.sb.uv.tb000

		scale = tb.contextMenu.s009.value()
		rotate = tb.contextMenu.s010.value()

		obj = rt.selection[0]

		self.uv_uiModifier.pack(1, 0.01, scale, rotate, True) #(method, spacing, normalize, rotate, fillholes)


	@Slots_max.attr
	def tb001(self, state=None):
		'''Auto Unwrap
		'''
		tb = self.sb.uv.tb001

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
		tb = self.sb.uv.tb002

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
		tb = self.sb.uv.tb003

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
		tb = self.sb.uv.tb004

		optimize = self.tb.contextMenu.chk017.isChecked()

		# if optimize:
		# 	# self.uv_uiModifier.
		# else:
		self.uv_uiModifier.relax(1, 0.01, True, True)


	def tb005(self, state=None):
		'''Straighten Uv
		'''
		tb = self.sb.uv.tb005

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
		tb = self.sb.uv.tb006

		u = tb.contextMenu.chk023.isChecked()
		v = tb.contextMenu.chk024.isChecked()
		
		if u:
			pm.mel.texDistributeShells(0, 0, "right", []) #'left', 'right'
		if v:
			pm.mel.texDistributeShells(0, 0, "down", []) #'up', 'down'


	def tb007(self, state=None):
		'''Set Texel Density
		'''
		tb = self.sb.uv.tb007

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
			self.messageBox('The operation requires the selection of two polygon objects.')

		from_ = sel[0]
		to = sel[-1]
		pm.transferAttributes(from_, to, transferUVs=2) # 0:no UV sets, 1:single UV set (specified by sourceUVSet and targetUVSet args), and 2:all UV sets are transferred.
		self.messageBox('UV sets transferred from: {} to: {}.'.format(from_.name(), to.name()), messageType='Result')


	def b005(self):
		'''Cut Uv'S
		'''
		self.uv_uiModifier.breakSelected()


	def b011(self):
		'''Sew Uv'S
		'''
		self.uv_uiModifier.stitchVerts(True, 1.0) #(align, bias) --Bias of 0.0 the vertices will move to the source and 1.0 they will move to the target. 


	def moveSelectedToUvSpace(self, u, v, relative=True):
		'''Move sny selected objects to the given u and v coordinates.

		:Parameters:
			u (int) = u coordinate.
			v (int) = v coordinate.
			relative (bool) = Move relative or absolute.
		'''
		mod = self.uv_uiModifier

		pm.polyEditUV(sel, u=u, v=v, relative=relative)


	def flipUV(self, objects=None):
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