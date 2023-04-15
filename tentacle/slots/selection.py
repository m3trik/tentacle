# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots



class Selection(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.selection.draggableHeader
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb006', setToolTip='A list of currently selected objects.')
		dh.ctxMenu.add('QCheckBox', setText='Ignore Backfacing', setObjectName='chk004', setToolTip='Ignore backfacing components during selection.')
		dh.ctxMenu.add('QCheckBox', setText='Soft Selection', setObjectName='chk008', setToolTip='Toggle soft selection mode.')
		dh.ctxMenu.add(self.sb.Label, setText='Grow Selection', setObjectName='lbl003', setToolTip='Grow the current selection.')
		dh.ctxMenu.add(self.sb.Label, setText='Shrink Selection', setObjectName='lbl004', setToolTip='Shrink the current selection.')
		dh.ctxMenu.cmb006.setCurrentText('Current Selection') # cmb.insertItem(cmb.currentIndex(), 'Current Selection') #insert item at current index.
		dh.ctxMenu.cmb006.popupStyle = 'qmenu'
		dh.ctxMenu.cmb006.beforePopupShown.connect(self.cmb006) #refresh the comboBox contents before showing it's popup.

		cmb001 = self.sb.selection.cmb001
		cmb001.ctxMenu.add(self.sb.Label, setText='Select', setObjectName='lbl005', setToolTip='Select the current set elements.')
		cmb001.ctxMenu.add(self.sb.Label, setText='New', setObjectName='lbl000', setToolTip='Create a new selection set.')
		cmb001.ctxMenu.add(self.sb.Label, setText='Modify', setObjectName='lbl001', setToolTip='Modify the current set by renaming and/or changing the selection.')
		cmb001.ctxMenu.add(self.sb.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current set.')
		cmb001.returnPressed.connect(lambda m=cmb001.ctxMenu.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb001.lbl000 was clicked last.
		cmb001.currentIndexChanged.connect(self.lbl005) #select current set on index change.
		cmb001.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		tb000 = self.sb.selection.tb000
		tb000.ctxMenu.add('QRadioButton', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
		tb000.ctxMenu.add('QRadioButton', setText='Component Loop', setObjectName='chk001', setChecked=True, setToolTip='Select all contiguous components that form a loop with the current selection.')
		tb000.ctxMenu.add('QRadioButton', setText='Path Along Loop', setObjectName='chk009', setToolTip='The path along loop between two selected edges, vertices or UV\'s.')
		tb000.ctxMenu.add('QRadioButton', setText='Shortest Path', setObjectName='chk002', setToolTip='The shortest component path between two selected edges, vertices or UV\'s.')
		tb000.ctxMenu.add('QRadioButton', setText='Border Edges', setObjectName='chk010', setToolTip='Select the object(s) border edges.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Step: ', setObjectName='s003', setMinMax_='1-100 step1', setValue=1, setToolTip='Step Amount.')

		tb001 = self.sb.selection.tb001
		tb001.ctxMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.000-9999 step1.0', setValue=0.0, setToolTip='The allowed difference in any of the compared results.\nie. A tolerance of 4 allows for a difference of 4 components.\nie. A tolerance of 0.05 allows for that amount of variance between any of the bounding box values.')
		tb001.ctxMenu.add('QCheckBox', setText='Vertex', setObjectName='chk011', setChecked=True, setToolTip='The number of vertices.')
		tb001.ctxMenu.add('QCheckBox', setText='Edge', setObjectName='chk012', setChecked=True, setToolTip='The number of edges.')
		tb001.ctxMenu.add('QCheckBox', setText='Face', setObjectName='chk013', setChecked=True, setToolTip='The number of faces.')
		tb001.ctxMenu.add('QCheckBox', setText='Triangle', setObjectName='chk014', setToolTip='The number of triangles.')
		tb001.ctxMenu.add('QCheckBox', setText='Shell', setObjectName='chk015', setToolTip='The number of shells shells (disconnected pieces).')
		tb001.ctxMenu.add('QCheckBox', setText='Uv Coord', setObjectName='chk016', setToolTip='The number of uv coordinates (for the current map).')
		tb001.ctxMenu.add('QCheckBox', setText='Area', setObjectName='chk017', setToolTip='The surface area of the object\'s faces in local space.')
		tb001.ctxMenu.add('QCheckBox', setText='World Area', setObjectName='chk018', setChecked=True, setToolTip='The surface area of the object\'s faces in world space.')
		tb001.ctxMenu.add('QCheckBox', setText='Bounding Box', setObjectName='chk019', setToolTip='The object\'s bounding box in 3d space.\nCannot be used with the topological flags.')
		tb001.ctxMenu.add('QCheckBox', setText='Include Original', setObjectName='chk020', setToolTip='Include the original selected object(s) in the final selection.')
		tb001.ctxMenu.chk018.stateChanged.connect(lambda state: self.sb.toggleWidgets(tb001.ctxMenu, setDisabled='chk011-18') if state 
															else self.sb.toggleWidgets(tb001.ctxMenu, setEnabled='chk011-18')) #disable non-relevant options.
		tb002 = self.sb.selection.tb002
		tb002.ctxMenu.add('QCheckBox', setText='Lock Values', setObjectName='chk003', setChecked=True, setToolTip='Keep values in sync.')
		tb002.ctxMenu.add('QDoubleSpinBox', setPrefix='x: ', setObjectName='s002', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal X range.')
		tb002.ctxMenu.add('QDoubleSpinBox', setPrefix='y: ', setObjectName='s004', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Y range.')
		tb002.ctxMenu.add('QDoubleSpinBox', setPrefix='z: ', setObjectName='s005', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Z range.')

		tb003 = self.sb.selection.tb003
		tb003.ctxMenu.add('QDoubleSpinBox', setPrefix='Angle Low:  ', setObjectName='s006', setMinMax_='0.0-180 step1', setValue=70, setToolTip='Normal angle low range.')
		tb003.ctxMenu.add('QDoubleSpinBox', setPrefix='Angle High: ', setObjectName='s007', setMinMax_='0.0-180 step1', setValue=160, setToolTip='Normal angle high range.')


	def draggableHeader(self, state=None):
		'''Context menu
		'''
		dh = self.sb.selection.draggableHeader


	def s002(self, value=None):
		'''Select Island: tolerance x
		'''
		tb = self.sb.selection.tb002
		if tb.ctxMenu.chk003.isChecked():
			text = tb.ctxMenu.s002.value()
			tb.ctxMenu.s004.setValue(text)
			tb.ctxMenu.s005.setValue(text)


	def s004(self, value=None):
		'''Select Island: tolerance y
		'''
		tb = self.sb.selection.tb002
		if tb.ctxMenu.chk003.isChecked():
			text = tb.ctxMenu.s004.value()
			tb.ctxMenu.s002.setValue(text)
			tb.ctxMenu.s005.setValue(text)


	def s005(self, value=None):
		'''Select Island: tolerance z
		'''
		tb = self.sb.selection.tb002
		if tb.ctxMenu.chk003.isChecked():
			text = tb.ctxMenu.s005.value()
			tb.ctxMenu.s002.setValue(text)
			tb.ctxMenu.s004.setValue(text)


	def chk000(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.sb.toggleWidgets(setUnChecked='chk001-2')


	def chk001(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.sb.toggleWidgets(setUnChecked='chk000,chk002')


	def chk002(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.sb.toggleWidgets(setUnChecked='chk000-1')


	def chk005(self, state=None):
		'''Select Style: Marquee
		'''
		self.sb.toggleWidgets(setChecked='chk005', setUnChecked='chk006-7')
		Selection.setSelectionStyle('marquee')
		self.sb.messageBox('Select Style: <hl>Marquee</hl>')


	def chk006(self, state=None):
		'''Select Style: Lasso
		'''
		self.sb.toggleWidgets(setChecked='chk006', setUnChecked='chk005,chk007')
		Selection.setSelectionStyle('lasso')
		self.sb.messageBox('Select Style: <hl>Lasso</hl>')


	def chk007(self, state=None):
		'''Select Style: Paint
		'''
		self.sb.toggleWidgets(setChecked='chk007', setUnChecked='chk005-6')
		Selection.setSelectionStyle('paint')
		self.sb.messageBox('Select Style: <hl>Paint</hl>')


	