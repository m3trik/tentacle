# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Edit_ui



class Edit_ui_max(Edit_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (passed in via the switchboard module's 'getClassInstanceFromUiName' method.)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		Edit_ui.__init__(self, *args, **kwargs)

		ctx = self.edit_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Editors')

		cmb = self.edit_ui.draggable_header.contextMenu.cmb000
		items = ['Cleanup', 'Transfer: Attribute Values', 'Transfer: Shading Sets']
		cmb.addItems_(items, 'Maya Editors')

		cmb = self.edit_ui.cmb001
		cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		ctx = self.edit_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='All Geometry', setObjectName='chk005', setToolTip='Clean All scene geometry.')
			ctx.add('QCheckBox', setText='Repair', setObjectName='chk004', setToolTip='Repair matching geometry. Else, select only.') #add(self.tcl.wgts.CheckBox, setText='Select Only', setObjectName='chk004', setTristate=True, setCheckState_=2, setToolTip='Select and/or Repair matching geometry. <br>0: Repair Only<br>1: Repair and Select<br>2: Select Only')
			ctx.add('QCheckBox', setText='N-Gons', setObjectName='chk002', setChecked=True, setToolTip='Find N-gons.')
			ctx.add('QCheckBox', setText='Non-Manifold Geometry', setObjectName='chk017', setChecked=True, setToolTip='Check for nonmanifold polys.')
			ctx.add('QCheckBox', setText='Non-Manifold Vertex', setObjectName='chk021', setToolTip='A connected vertex of non-manifold geometry where the faces share a single vertex.')
			ctx.add('QCheckBox', setText='Quads', setObjectName='chk010', setToolTip='Check for quad sided polys.')
			ctx.add('QCheckBox', setText='Concave', setObjectName='chk011', setToolTip='Check for concave polys.')
			ctx.add('QCheckBox', setText='Non-Planar', setObjectName='chk003', setToolTip='Check for non-planar polys.')
			ctx.add('QCheckBox', setText='Holed', setObjectName='chk012', setToolTip='Check for holed polys.')
			ctx.add('QCheckBox', setText='Lamina', setObjectName='chk018', setToolTip='Check for lamina polys.')
			ctx.add('QCheckBox', setText='Shared UV\'s', setObjectName='chk016', setToolTip='Unshare uvs that are shared across vertices.')
			# ctx.add('QCheckBox', setText='Invalid Components', setObjectName='chk019', setToolTip='Check for invalid components.')
			ctx.add('QCheckBox', setText='Zero Face Area', setObjectName='chk013', setToolTip='Check for 0 area faces.')
			ctx.add('QDoubleSpinBox', setPrefix='Face Area Tolerance:   ', setObjectName='s006', setDisabled=True, setMinMax_='0.0-10 step.001', setValue=0.001, setToolTip='Tolerance for face areas.')
			ctx.add('QCheckBox', setText='Zero Length Edges', setObjectName='chk014', setToolTip='Check for 0 length edges.')
			ctx.add('QDoubleSpinBox', setPrefix='Edge Length Tolerance: ', setObjectName='s007', setDisabled=True, setMinMax_='0.0-10 step.001', setValue=0.001, setToolTip='Tolerance for edge length.')
			ctx.add('QCheckBox', setText='Zero UV Face Area', setObjectName='chk015', setToolTip='Check for 0 uv face area.')
			ctx.add('QDoubleSpinBox', setPrefix='UV Face Area Tolerance:', setObjectName='s008', setDisabled=True, setMinMax_='0.0-10 step.001', setValue=0.001, setToolTip='Tolerance for uv face areas.')
			ctx.add('QCheckBox', setText='Overlapping Duplicate Objects', setObjectName='chk022', setToolTip='Find any duplicate overlapping geometry at the object level.')
			ctx.add('QCheckBox', setText='Omit Selected Objects', setObjectName='chk023', setDisabled=True, setToolTip='Overlapping Duplicate Objects: Search for duplicates of any selected objects while omitting the initially selected objects.')
			ctx.chk013.toggled.connect(lambda state: ctx.s006.setEnabled(True if state else False))
			ctx.chk014.toggled.connect(lambda state: ctx.s007.setEnabled(True if state else False))
			ctx.chk015.toggled.connect(lambda state: ctx.s008.setEnabled(True if state else False))
			ctx.chk022.stateChanged.connect(lambda state: self.toggleWidgets(ctx, setDisabled='chk002-3,chk005,chk010-21,s006-8', setEnabled='chk023') if state 
															else self.toggleWidgets(ctx, setEnabled='chk002-3,chk005,chk010-21,s006-8', setDisabled='chk023')) #disable non-relevant options.
		ctx = self.edit_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='For All Objects', setObjectName='chk018', setChecked=True, setToolTip='Delete history on All objects or just those selected.')
			ctx.add('QCheckBox', setText='Delete Unused Nodes', setObjectName='chk019', setChecked=True, setToolTip='Delete unused nodes.')
			ctx.add('QCheckBox', setText='Delete Deformers', setObjectName='chk020', setToolTip='Delete deformers.')

		ctx = self.edit_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Delete Edge Loop', setObjectName='chk001', setToolTip='Delete the edge loops of any edges selected.')
			ctx.add('QCheckBox', setText='Delete Edge Ring', setObjectName='chk000', setToolTip='Delete the edge rings of any edges selected.')

		ctx = self.edit_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='-', setObjectName='chk006', setChecked=True, setToolTip='Perform delete along negative axis.')
			ctx.add('QRadioButton', setText='X', setObjectName='chk007', setChecked=True, setToolTip='Perform delete along X axis.')
			ctx.add('QRadioButton', setText='Y', setObjectName='chk008', setToolTip='Perform delete along Y axis.')
			ctx.add('QRadioButton', setText='Z', setObjectName='chk009', setToolTip='Perform delete along Z axis.')
			self.connect_('chk006-9', 'toggled', self.chk006_9, ctx)
