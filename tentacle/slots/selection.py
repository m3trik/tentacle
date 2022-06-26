# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Selection(Slots):
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
		dh = self.selection_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='')
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb006', setToolTip='A list of currently selected objects.')
		dh.contextMenu.add('QCheckBox', setText='Ignore Backfacing', setObjectName='chk004', setToolTip='Ignore backfacing components during selection.')
		dh.contextMenu.add('QCheckBox', setText='Soft Selection', setObjectName='chk008', setToolTip='Toggle soft selection mode.')
		dh.contextMenu.add(self.Label, setText='Grow Selection', setObjectName='lbl003', setToolTip='Grow the current selection.')
		dh.contextMenu.add(self.Label, setText='Shrink Selection', setObjectName='lbl004', setToolTip='Shrink the current selection.')

		cmb001 = self.selection_ui.cmb001
		cmb001.contextMenu.add(self.Label, setText='Select', setObjectName='lbl005', setToolTip='Select the current set elements.')
		cmb001.contextMenu.add(self.Label, setText='New', setObjectName='lbl000', setToolTip='Create a new selection set.')
		cmb001.contextMenu.add(self.Label, setText='Modify', setObjectName='lbl001', setToolTip='Modify the current set by renaming and/or changing the selection.')
		cmb001.contextMenu.add(self.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current set.')
		cmb001.returnPressed.connect(lambda m=cmb001.contextMenu.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb001.lbl000 was clicked last.
		cmb001.currentIndexChanged.connect(self.lbl005) #select current set on index change.
		cmb001.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.

		dh = self.selection_ui.draggable_header
		dh.contextMenu.cmb006.setCurrentText('Current Selection') # cmb.insertItem(cmb.currentIndex(), 'Current Selection') #insert item at current index.
		dh.contextMenu.cmb006.popupStyle = 'qmenu'
		dh.contextMenu.cmb006.beforePopupShown.connect(self.cmb006) #refresh the comboBox contents before showing it's popup.

		tb000 = self.selection_ui.tb000
		tb000.contextMenu.add('QRadioButton', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
		tb000.contextMenu.add('QRadioButton', setText='Component Loop', setObjectName='chk001', setChecked=True, setToolTip='Select all contiguous components that form a loop with the current selection.')
		tb000.contextMenu.add('QRadioButton', setText='Path Along Loop', setObjectName='chk009', setToolTip='The path along loop between two selected edges, vertices or UV\'s.')
		tb000.contextMenu.add('QRadioButton', setText='Shortest Path', setObjectName='chk002', setToolTip='The shortest component path between two selected edges, vertices or UV\'s.')
		tb000.contextMenu.add('QRadioButton', setText='Border Edges', setObjectName='chk010', setToolTip='Select the object(s) border edges.')
		tb000.contextMenu.add('QSpinBox', setPrefix='Step: ', setObjectName='s003', setMinMax_='1-100 step1', setValue=1, setToolTip='Step Amount.')

		tb001 = self.selection_ui.tb001
		tb001.contextMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=0.3, setToolTip='Select similar objects or components, depending on selection mode.')

		tb002 = self.selection_ui.tb002
		tb002.contextMenu.add('QCheckBox', setText='Lock Values', setObjectName='chk003', setChecked=True, setToolTip='Keep values in sync.')
		tb002.contextMenu.add('QDoubleSpinBox', setPrefix='x: ', setObjectName='s002', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal X range.')
		tb002.contextMenu.add('QDoubleSpinBox', setPrefix='y: ', setObjectName='s004', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Y range.')
		tb002.contextMenu.add('QDoubleSpinBox', setPrefix='z: ', setObjectName='s005', setMinMax_='0.00-1 step.01', setValue=0.05, setToolTip='Normal Z range.')

		tb003 = self.selection_ui.tb003
		tb003.contextMenu.add('QDoubleSpinBox', setPrefix='Angle Low:  ', setObjectName='s006', setMinMax_='0.0-180 step1', setValue=70, setToolTip='Normal angle low range.')
		tb003.contextMenu.add('QDoubleSpinBox', setPrefix='Angle High: ', setObjectName='s007', setMinMax_='0.0-180 step1', setValue=160, setToolTip='Normal angle high range.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.selection_ui.draggable_header


	def s002(self, value=None):
		'''Select Island: tolerance x
		'''
		tb = self.selection_ui.tb002
		if tb.contextMenu.chk003.isChecked():
			text = tb.contextMenu.s002.value()
			tb.contextMenu.s004.setValue(text)
			tb.contextMenu.s005.setValue(text)


	def s004(self, value=None):
		'''Select Island: tolerance y
		'''
		tb = self.selection_ui.tb002
		if tb.contextMenu.chk003.isChecked():
			text = tb.contextMenu.s004.value()
			tb.contextMenu.s002.setValue(text)
			tb.contextMenu.s005.setValue(text)


	def s005(self, value=None):
		'''Select Island: tolerance z
		'''
		tb = self.selection_ui.tb002
		if tb.contextMenu.chk003.isChecked():
			text = tb.contextMenu.s005.value()
			tb.contextMenu.s002.setValue(text)
			tb.contextMenu.s004.setValue(text)


	def chk000(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk001-2')


	def chk001(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk000,chk002')


	def chk002(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk000-1')


	def chk005(self, state=None):
		'''Select Style: Marquee
		'''
		self.toggleWidgets(setChecked='chk005', setUnChecked='chk006-7')
		Selection.setSelectionStyle('marquee')
		self.messageBox('Select Style: <hl>Marquee</hl>')


	def chk006(self, state=None):
		'''Select Style: Lasso
		'''
		self.toggleWidgets(setChecked='chk006', setUnChecked='chk005,chk007')
		Selection.setSelectionStyle('lasso')
		self.messageBox('Select Style: <hl>Lasso</hl>')


	def chk007(self, state=None):
		'''Select Style: Paint
		'''
		self.toggleWidgets(setChecked='chk007', setUnChecked='chk005-6')
		Selection.setSelectionStyle('paint')
		self.messageBox('Select Style: <hl>Paint</hl>')


	