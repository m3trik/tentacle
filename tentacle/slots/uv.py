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
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui object of <name>. ie. self.polygons_ui
					<widget> (registered widget) = Any widget previously registered in the switchboard module. ie. self.PushButton
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
		'''
		dh = self.uv_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='Maya UV Editors')
		dh.contextMenu.add('QPushButton', setText='Create UV Snapshot', setObjectName='b001', setToolTip='Save an image file of the current UV layout.')

		cmb001 = self.uv_ui.cmb001
		cmb001.popupStyle = 'qmenu'
		cmb001.menu_.add(self.CheckBox, setObjectName='chk014', setText='Checkered', setToolTip='')
		cmb001.menu_.add(self.CheckBox, setObjectName='chk015', setText='Borders', setToolTip='')
		cmb001.menu_.add(self.CheckBox, setObjectName='chk016', setText='Distortion', setToolTip='')

		cmb003 = self.uv_ui.cmb003
		self.getMapSize = lambda: int(self.uv_ui.cmb003.currentText()) #get the map size from the combobox as an int. ie. 2048

		tb001 = self.uv_ui.tb001
		tb001.contextMenu.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
		tb001.contextMenu.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
		tb001.contextMenu.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
		tb001.contextMenu.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
		tb001.contextMenu.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
		tb001.contextMenu.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
		tb001.contextMenu.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')
		# tb001.contextMenu.chk001.toggled.connect(lambda state: self.toggleWidgets(tb001.contextMenu, setUnChecked='chk002-3') if state==1 else None)

		tb003 = self.uv_ui.tb003
		tb003.contextMenu.add('QRadioButton', setText='Back-Facing', setObjectName='chk008', setToolTip='Select all back-facing (using counter-clockwise winding order) components for the current selection.')
		tb003.contextMenu.add('QRadioButton', setText='Front-Facing', setObjectName='chk009', setToolTip='Select all front-facing (using counter-clockwise winding order) components for the current selection.')
		tb003.contextMenu.add('QRadioButton', setText='Overlapping', setObjectName='chk010', setToolTip='Select all components that share the same uv space.')
		tb003.contextMenu.add('QRadioButton', setText='Non-Overlapping', setObjectName='chk011', setToolTip='Select all components that do not share the same uv space.')
		tb003.contextMenu.add('QRadioButton', setText='Texture Borders', setObjectName='chk012', setToolTip='Select all components on the borders of uv shells.')
		tb003.contextMenu.add('QRadioButton', setText='Unmapped', setObjectName='chk013', setChecked=True, setToolTip='Select unmapped faces in the current uv set.')

		tb004 = self.uv_ui.tb004
		tb004.contextMenu.add('QCheckBox', setText='Optimize', setObjectName='chk017', setChecked=True, setToolTip='The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).')
		tb004.contextMenu.add('QCheckBox', setText='Orient', setObjectName='chk007', setChecked=True, setToolTip='Orient selected UV shells to run parallel with the most adjacent U or V axis.')
		tb004.contextMenu.add('QCheckBox', setText='Stack Similar', setObjectName='chk022', setChecked=True, setToolTip='Stack only shells that fall within the set tolerance.')
		tb004.contextMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')

		tb005 = self.uv_ui.tb005
		tb005.contextMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s001', setMinMax_='0-360 step1', setValue=30, setToolTip='Set the maximum angle used for straightening uv\'s.')
		tb005.contextMenu.add('QCheckBox', setText='Straighten U', setObjectName='chk018', setChecked=True, setToolTip='Unfold UV\'s along a horizonal contraint.')
		tb005.contextMenu.add('QCheckBox', setText='Straighten V', setObjectName='chk019', setChecked=True, setToolTip='Unfold UV\'s along a vertical constaint.')
		tb005.contextMenu.add('QCheckBox', setText='Straighten Shell', setObjectName='chk020', setToolTip='Straighten a UV shell by unfolding UV\'s around a selected UV\'s edgeloop.')

		tb006 = self.uv_ui.tb006
		tb006.contextMenu.add('QRadioButton', setText='Distribute U', setObjectName='chk023', setChecked=True, setToolTip='Distribute along U.')
		tb006.contextMenu.add('QRadioButton', setText='Distribute V', setObjectName='chk024', setToolTip='Distribute along V.')

		tb007 = self.uv_ui.tb007
		tb007.contextMenu.add('QPushButton', setText='Get Texel Density', setObjectName='b099', setChecked=True, setToolTip='Get the average texel density of any selected faces.')
		tb007.contextMenu.add('QDoubleSpinBox', setPrefix='Texel Density: ', setObjectName='s003', setMinMax_='0.00-128 step8', setValue=32, setToolTip='Set the desired texel density.')


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


	def b000(self):
		'''Unfold and Pack
		'''
		self.tb004() #perform unfold
		self.tb000() #perform pack


	def b003(self):
		'''Cut UV hard edges
		'''
		self.selection().tb003() #perform select edges by angle.
		self.b005() #perform cut.


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


	
