# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Uv(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		ctx = self.uv_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya UV Editors')
			ctx.add('QPushButton', setText='Create UV Snapshot', setObjectName='b001', setToolTip='Save an image file of the current UV layout.')

		cmb = self.uv_ui.cmb001
		cmb.popupStyle = 'qmenu'
		menu = cmb.menu_
		if not menu.containsMenuItems:
			menu.add(self.tcl.wgts.CheckBox, setObjectName='chk014', setText='Checkered', setToolTip='')
			menu.add(self.tcl.wgts.CheckBox, setObjectName='chk015', setText='Borders', setToolTip='')
			menu.add(self.tcl.wgts.CheckBox, setObjectName='chk016', setText='Distortion', setToolTip='')

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


	
