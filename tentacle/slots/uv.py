# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots



class Uv(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.uv.draggableHeader
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='Maya UV Editors')
		dh.ctxMenu.add('QPushButton', setText='Create UV Snapshot', setObjectName='b001', setToolTip='Save an image file of the current UV layout.')

		cmb001 = self.sb.uv.cmb001
		cmb001.popupStyle = 'qmenu'
		cmb001.menu_.add(self.sb.CheckBox, setObjectName='chk014', setText='Checkered', setToolTip='')
		cmb001.menu_.add(self.sb.CheckBox, setObjectName='chk015', setText='Borders', setToolTip='')
		cmb001.menu_.add(self.sb.CheckBox, setObjectName='chk016', setText='Distortion', setToolTip='')

		cmb003 = self.sb.uv.cmb003
		self.getMapSize = lambda: int(self.sb.uv.cmb003.currentText()) #get the map size from the combobox as an int. ie. 2048

		tb001 = self.sb.uv.tb001
		tb001.ctxMenu.add('QRadioButton', setText='Standard', setObjectName='chk000', setChecked=True, setToolTip='Create UV texture coordinates for the selected object or faces by automatically finding the best UV placement using simultanious projections from multiple planes.')
		tb001.ctxMenu.add('QCheckBox', setText='Scale Mode 1', setObjectName='chk001', setTristate=True, setChecked=True, setToolTip='0 - No scale is applied.<br>1 - Uniform scale to fit in unit square.<br>2 - Non proportional scale to fit in unit square.')
		tb001.ctxMenu.add('QRadioButton', setText='Seam Only', setObjectName='chk002', setToolTip='Cut seams only.')
		tb001.ctxMenu.add('QRadioButton', setText='Planar', setObjectName='chk003', setToolTip='Create UV texture coordinates for the current selection by using a planar projection shape.')
		tb001.ctxMenu.add('QRadioButton', setText='Cylindrical', setObjectName='chk004', setToolTip='Create UV texture coordinates for the current selection, using a cylidrical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed cylidrical shapes with no holes or projections on the surface.')
		tb001.ctxMenu.add('QRadioButton', setText='Spherical', setObjectName='chk005', setToolTip='Create UV texture coordinates for the current selection, using a spherical projection that gets wrapped around the mesh.<br>Best suited for completely enclosed spherical shapes with no holes or projections on the surface.')
		tb001.ctxMenu.add('QRadioButton', setText='Normal-Based', setObjectName='chk006', setToolTip='Create UV texture coordinates for the current selection by creating a planar projection based on the average vector of it\'s face normals.')
		# tb001.ctxMenu.chk001.toggled.connect(lambda state: self.sb.toggleWidgets(tb001.ctxMenu, setUnChecked='chk002-3') if state==1 else None)

		tb003 = self.sb.uv.tb003
		tb003.ctxMenu.add('QRadioButton', setText='Back-Facing', setObjectName='chk008', setToolTip='Select all back-facing (using counter-clockwise winding order) components for the current selection.')
		tb003.ctxMenu.add('QRadioButton', setText='Front-Facing', setObjectName='chk009', setToolTip='Select all front-facing (using counter-clockwise winding order) components for the current selection.')
		tb003.ctxMenu.add('QRadioButton', setText='Overlapping', setObjectName='chk010', setToolTip='Select all components that share the same uv space.')
		tb003.ctxMenu.add('QRadioButton', setText='Non-Overlapping', setObjectName='chk011', setToolTip='Select all components that do not share the same uv space.')
		tb003.ctxMenu.add('QRadioButton', setText='Texture Borders', setObjectName='chk012', setToolTip='Select all components on the borders of uv shells.')
		tb003.ctxMenu.add('QRadioButton', setText='Unmapped', setObjectName='chk013', setChecked=True, setToolTip='Select unmapped faces in the current uv set.')

		tb004 = self.sb.uv.tb004
		tb004.ctxMenu.add('QCheckBox', setText='Optimize', setObjectName='chk017', setChecked=True, setToolTip='The Optimize UV Tool evens out the spacing between UVs on a mesh, fixing areas of distortion (overlapping UVs).')
		tb004.ctxMenu.add('QCheckBox', setText='Orient', setObjectName='chk007', setChecked=True, setToolTip='Orient selected UV shells to run parallel with the most adjacent U or V axis.')
		tb004.ctxMenu.add('QCheckBox', setText='Stack Similar', setObjectName='chk022', setChecked=True, setToolTip='Stack only shells that fall within the set tolerance.')
		tb004.ctxMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=1.0, setToolTip='Stack shells with uv\'s within the given range.')

		tb005 = self.sb.uv.tb005
		tb005.ctxMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s001', setMinMax_='0-360 step1', setValue=30, setToolTip='Set the maximum angle used for straightening uv\'s.')
		tb005.ctxMenu.add('QCheckBox', setText='Straighten U', setObjectName='chk018', setChecked=True, setToolTip='Unfold UV\'s along a horizonal contraint.')
		tb005.ctxMenu.add('QCheckBox', setText='Straighten V', setObjectName='chk019', setChecked=True, setToolTip='Unfold UV\'s along a vertical constaint.')
		tb005.ctxMenu.add('QCheckBox', setText='Straighten Shell', setObjectName='chk020', setToolTip='Straighten a UV shell by unfolding UV\'s around a selected UV\'s edgeloop.')

		tb006 = self.sb.uv.tb006
		tb006.ctxMenu.add('QRadioButton', setText='Distribute U', setObjectName='chk023', setChecked=True, setToolTip='Distribute along U.')
		tb006.ctxMenu.add('QRadioButton', setText='Distribute V', setObjectName='chk024', setToolTip='Distribute along V.')

		tb008 = self.sb.uv.tb008
		tb008.ctxMenu.add('QCheckBox', setText='To Similar', setObjectName='chk025', setToolTip='Instead of manually selecting what to transfer to; search the scene for similar objects.')
		tb008.ctxMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s013', setMinMax_='0.0-1000 step.5', setValue=0.00, setToolTip='The maximum attribute value tolerance to use when searching for similar objects.')
		tb008.ctxMenu.add('QCheckBox', setText='Delete History', setObjectName='chk026', setChecked=True, setToolTip='Remove construction history for the objects transferring from.\nOtherwise, the UV\'s will be lost should any of the frm objects be deleted.')


	def draggableHeader(self, state=None):
		'''Context menu
		'''
		dh = self.sb.uv.draggableHeader


	def chk001(self, state):
		'''Auto Unwrap: Scale Mode CheckBox
		'''
		tb = self.sb.uv.tb001
		if state==0:
			tb.ctxMenu.chk001.setText('Scale Mode 0')
		if state==1:
			tb.ctxMenu.chk001.setText('Scale Mode 1')
			self.sb.toggleWidgets(tb.ctxMenu, setUnChecked='chk002-6')
		if state==2:
			tb.ctxMenu.chk001.setText('Scale Mode 2')


	def b021(self):
		'''Unfold and Pack
		'''
		self.tb004() #perform unfold
		self.tb000() #perform pack


	def b022(self):
		'''Cut UV hard edges
		'''
		self.sb.selection.slots.tb003() #perform select edges by angle.
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


	
