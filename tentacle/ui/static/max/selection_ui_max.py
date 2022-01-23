# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Selection_ui



class Selection_ui_max(Selection_ui):
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
		Selection_ui.__init__(self, *args, **kwargs)

		ctx = self.selection_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb006', setToolTip='A list of currently selected objects.')
			ctx.add('QCheckBox', setText='Ignore Backfacing', setObjectName='chk004', setToolTip='Ignore backfacing components during selection.')
			ctx.add('QCheckBox', setText='Soft Selection', setObjectName='chk008', setToolTip='Toggle soft selection mode.')
			ctx.add(self.tcl.wgts.Label, setText='Grow Selection', setObjectName='lbl003', setToolTip='Grow the current selection.')
			ctx.add(self.tcl.wgts.Label, setText='Shrink Selection', setObjectName='lbl004', setToolTip='Shrink the current selection.')

		cmb = self.selection_ui.draggable_header.contextMenu.cmb000
		items = ['Polygon Selection Constraints']
		cmb.addItems_(items, 'Selection Editors:')

		cmb = self.selection_ui.cmb001
		ctx = cmb.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.Label, setText='Select', setObjectName='lbl005', setToolTip='Select the current set elements.')
			ctx.add(self.tcl.wgts.Label, setText='New', setObjectName='lbl000', setToolTip='Create a new selection set.')
			ctx.add(self.tcl.wgts.Label, setText='Modify', setObjectName='lbl001', setToolTip='Modify the current set by renaming and/or changing the selection.')
			ctx.add(self.tcl.wgts.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current set.')
			cmb.returnPressed.connect(lambda m=ctx.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
			cmb.currentIndexChanged.connect(self.lbl005) #select current set on index change.
			cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		cmb = self.selection_ui.cmb002
		items = ['IK Handles','Joints','Clusters','Lattices','Sculpt Objects','Wires','Transforms','Geometry','NURBS Curves','NURBS Surfaces','Polygon Geometry','Cameras','Lights','Image Planes','Assets','Fluids','Particles','Rigid Bodies','Rigid Constraints','Brushes','Strokes','Dynamic Constraints','Follicles','nCloths','nParticles','nRigids']
		cmb.addItems_(items, 'By Type:')

		cmb = self.selection_ui.cmb003
		items = ['Verts', 'Vertex Faces', 'Vertex Perimeter', 'Edges', 'Edge Loop', 'Edge Ring', 'Contained Edges', 'Edge Perimeter', 'Border Edges', 'Faces', 'Face Path', 'Contained Faces', 'Face Perimeter', 'UV\'s', 'UV Shell', 'UV Shell Border', 'UV Perimeter', 'UV Edge Loop', 'Shell', 'Shell Border'] 
		cmb.addItems_(items, 'Convert To:')

		cmb = self.selection_ui.cmb005
		items = ['Angle', 'Border', 'Edge Loop', 'Edge Ring', 'Shell', 'UV Edge Loop']
		items = cmb.addItems_(items, 'Off')

		cmb = self.selection_ui.draggable_header.contextMenu.cmb006
		cmb.setCurrentText('Current Selection') # cmb.insertItem(cmb.currentIndex(), 'Current Selection') #insert item at current index.
		cmb.popupStyle = 'qmenu'
		cmb.beforePopupShown.connect(self.cmb006) #refresh the comboBox contents before showing it's popup.

		ctx= self.selection_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
			ctx.add('QRadioButton', setText='Component Loop', setObjectName='chk001', setChecked=True, setToolTip='Select all contiguous components that form a loop with the current selection.')
			ctx.add('QRadioButton', setText='Path Along Loop', setObjectName='chk009', setToolTip='The path along loop between two selected edges, vertices or UV\'s.')
			ctx.add('QRadioButton', setText='Shortest Path', setObjectName='chk002', setToolTip='The shortest component path between two selected edges, vertices or UV\'s.')
			ctx.add('QRadioButton', setText='Border Edges', setObjectName='chk010', setToolTip='Select the object(s) border edges.')
			ctx.add('QSpinBox', setPrefix='Step: ', setObjectName='s003', setMinMax_='1-100 step1', setValue=1, setToolTip='Step Amount.')

		ctx = self.selection_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=0.3, setToolTip='Select similar objects or components, depending on selection mode.')

		ctx = self.selection_ui.tb002.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Lock Values', setObjectName='chk003', setChecked=True, setToolTip='Keep values in sync.')
			ctx.add('QDoubleSpinBox', setPrefix='x: ', setObjectName='s002', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal X range.')
			ctx.add('QDoubleSpinBox', setPrefix='y: ', setObjectName='s004', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Y range.')
			ctx.add('QDoubleSpinBox', setPrefix='z: ', setObjectName='s005', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Z range.')

		ctx = self.selection_ui.tb003.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QDoubleSpinBox', setPrefix='Angle Low:  ', setObjectName='s006', setMinMax_='0.0-180 step1', setValue=50, setToolTip='Normal angle low range.')
			ctx.add('QDoubleSpinBox', setPrefix='Angle High: ', setObjectName='s007', setMinMax_='0.0-180 step1', setValue=130, setToolTip='Normal angle high range.')


		