# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.uv import Uv



class Uv_max(Uv, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb000 = self.sb.uv.draggable_header.ctxMenu.cmb000
		items = ['UV Editor','UV Set Editor','UV Tool Kit','UV Linking: Texture-Centric','UV Linking: UV-Centric','UV Linking: Paint Effects/UV','UV Linking: Hair/UV']
		cmb000.addItems_(items, '3dsMax UV Editors')

		cmb002 = self.sb.uv.cmb002
		items = ['Flip U', 'Flip V', 'Align U Left', 'Align U Middle', 'Align U Right', 'Align V Top', 'Align V Middle', 'Align V Bottom', 'Linear Align']
		cmb002.addItems_(items, 'Transform:')

		tb000 = self.sb.uv.tb000
		tb000.ctxMenu.add('QSpinBox', setPrefix='Pre-Scale Mode: ', setObjectName='s009', setMinMax_='0-1 step1', setValue=1, setToolTip='Allow shell scaling during packing.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Pre-Rotate Mode: ', setObjectName='s010', setMinMax_='0-1 step1', setValue=1, setToolTip='Allow shell rotation during packing.')

		tb001 = self.sb.uv.tb001
		tb001.ctxMenu.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
		tb001.ctxMenu.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
		tb001.ctxMenu.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
		tb001.ctxMenu.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
		tb001.ctxMenu.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
		tb001.ctxMenu.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
		tb001.ctxMenu.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')
		# tb001.ctxMenu.chk001.toggled.connect(lambda state: self.sb.toggleWidgets(tb001.ctxMenu, setUnChecked='chk002-3') if state==1 else None)


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
		cmb = self.sb.uv.draggable_header.ctxMenu.cmb000

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

		scale = tb.ctxMenu.s009.value()
		rotate = tb.ctxMenu.s010.value()

		obj = rt.selection[0]

		self.uv_uiModifier.pack(1, 0.01, scale, rotate, True) #(method, spacing, normalize, rotate, fillholes)


	@Slots_max.attr
	def tb001(self, state=None):
		'''Auto Unwrap
		'''
		tb = self.sb.uv.tb001

		standardUnwrap = tb.ctxMenu.chk000.isChecked()
		scaleMode = tb.ctxMenu.chk001.isChecked()
		seamOnly = tb.ctxMenu.chk002.isChecked()
		planarUnwrap = tb.ctxMenu.chk003.isChecked()
		cylindricalUnwrap = tb.ctxMenu.chk004.isChecked()
		sphericalUnwrap = tb.ctxMenu.chk005.isChecked()
		normalBasedUnwrap = tb.ctxMenu.chk006.isChecked()

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

		orient = tb.ctxMenu.chk021.isChecked()
		stackSimilar = tb.ctxMenu.chk022.isChecked()
		tolerance = tb.ctxMenu.s000.value()
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

		back_facing = tb.ctxMenu.chk008.isChecked()
		front_facing = tb.ctxMenu.chk009.isChecked()
		overlapping = tb.ctxMenu.chk010.isChecked()
		nonOverlapping = tb.ctxMenu.chk011.isChecked()
		textureBorders = tb.ctxMenu.chk012.isChecked()
		unmapped = tb.ctxMenu.chk013.isChecked()

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

		optimize = self.tb.ctxMenu.chk017.isChecked()

		# if optimize:
		# 	# self.uv_uiModifier.
		# else:
		self.uv_uiModifier.relax(1, 0.01, True, True)


	def tb005(self, state=None):
		'''Straighten Uv
		'''
		tb = self.sb.uv.tb005

		u = tb.ctxMenu.chk018.isChecked()
		v = tb.ctxMenu.chk019.isChecked()
		angle = tb.ctxMenu.s001.value()
		straightenShell = tb.ctxMenu.chk020.isChecked()

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

		u = tb.ctxMenu.chk023.isChecked()
		v = tb.ctxMenu.chk024.isChecked()
		
		if u:
			pm.mel.texDistributeShells(0, 0, "right", []) #'left', 'right'
		if v:
			pm.mel.texDistributeShells(0, 0, "down", []) #'up', 'down'


	def tb008(self, state=None):
		'''Transfer UV's
		'''
		tb = self.sb.uv.tb008

		toSimilar = tb.ctxMenu.chk025.isChecked()
		similarTol = tb.ctxMenu.s013.value()
		deleteConstHist = tb.ctxMenu.chk026.isChecked()

		frm, *to = pm.ls(orderedSelection=1, flatten=1)
		if toSimilar:
			to = 'similar'
		elif not to:
			return self.messageBox('<b>Nothing selected.</b><br>The operation requires the selection of two polygon objects.')

		self.transferUVs(frm, to, tol=similarTol, deleteConstHist=deleteConstHist)


	def b001(self):
		'''Create UV Snapshot
		'''
		pass


	def b002(self):
		'''Stack Shells
		'''
		pm.mel.texStackShells()
		# pm.mel.texOrientShells()


	def b003(self):
		'''Get texel density.
		'''
		density = pm.mel.texGetTexelDensity(self.getMapSize())
		self.sb.uv.s003.setValue(density)


	def b004(self):
		'''Set Texel Density
		'''	
		density = self.sb.uv.s003.value()
		mapSize = self.getMapSize()
		pm.mel.texSetTexelDensity(density, mapSize)


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