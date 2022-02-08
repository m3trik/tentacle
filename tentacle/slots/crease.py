# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Crease(Slots):
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
		dh = self.crease_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Crease Editors')

		tb000 = self.crease_ui.tb000
		tb000.contextMenu.add('QSpinBox', setPrefix='Crease Amount: ', setObjectName='s003', setMinMax_='0-10 step1', setValue=10, setToolTip='Crease amount 0-10. Overriden if "max" checked.')
		tb000.contextMenu.add('QCheckBox', setText='Toggle Max', setObjectName='chk003', setToolTip='Toggle crease amount from it\'s current value to the maximum amount.')
		tb000.contextMenu.add('QCheckBox', setText='Un-Crease', setObjectName='chk002', setToolTip='Un-crease selected components or If in object mode, uncrease all.')
		tb000.contextMenu.add('QCheckBox', setText='Perform Normal Edge Hardness', setObjectName='chk005', setChecked=True, setToolTip='Toggle perform normal edge hardness.')
		tb000.contextMenu.add('QSpinBox', setPrefix='Hardness Angle: ', setObjectName='s004', setMinMax_='0-180 step1', setValue=30, setToolTip='Normal edge hardness 0-180.')
		tb000.contextMenu.add('QCheckBox', setText='Crease Vertex Points', setObjectName='chk004', setChecked=True, setToolTip='Crease vertex points.')
		tb000.contextMenu.add('QCheckBox', setText='Auto Crease', setObjectName='chk011', setToolTip='Auto crease selected object(s) within the set angle tolerance.')
		tb000.contextMenu.add('QSpinBox', setPrefix='Auto Crease: Low: ', setObjectName='s005', setMinMax_='0-180 step1', setValue=85, setToolTip='Auto crease: low angle constraint.')
		tb000.contextMenu.add('QSpinBox', setPrefix='Auto Crease: high: ', setObjectName='s006', setMinMax_='0-180 step1', setValue=95, setToolTip='Auto crease: max angle constraint.')
		self.toggleWidgets(tb000.contextMenu, setDisabled='s005,s006')


	def s003(self, value=None):
		'''Crease Amount
		Tracks the standard crease amount while toggles such as un-crease, and crease max temporarily change the spinbox value. 
		'''
		if not self.crease_ui.tb000.contextMenu.chk002.isChecked(): #un-crease
			if not self.crease_ui.tb000.contextMenu.chk003.isChecked(): #toggle max
				self.creaseValue = self.crease_ui.tb000.contextMenu.s003.value()
				text = self.crease_ui.tb000.text().split()[0]
				self.crease_ui.tb000.setText('{} {}'.format(text, self.creaseValue))


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.crease_ui.draggable_header


	def chk002(self, state=None):
		'''Un-Crease
		'''
		if self.crease_ui.tb000.contextMenu.chk002.isChecked():
			self.crease_ui.tb000.contextMenu.s003.setValue(0) #crease value
			self.crease_ui.tb000.contextMenu.s004.setValue(180) #normal angle
			self.toggleWidgets(self.crease_ui.tb000.contextMenu, self.crease_submenu_ui.tb000.contextMenu, setChecked='chk002', setUnChecked='chk003')
			self.crease_ui.tb000.contextMenu.s003.setDisabled(True)
			text = 'Un-Crease 0'
		else:
			self.crease_ui.tb000.contextMenu.s003.setValue(self.creaseValue) #crease value
			self.crease_ui.tb000.contextMenu.s004.setValue(30) #normal angle
			self.crease_ui.tb000.contextMenu.s003.setEnabled(True)
			text = '{} {}'.format('Crease', self.creaseValue)

		self.crease_ui.tb000.setText(text)


	def chk003(self, state=None):
		'''Crease: Max
		'''
		if self.crease_ui.tb000.contextMenu.chk003.isChecked():
			self.crease_ui.tb000.contextMenu.s003.setValue(10) #crease value
			self.crease_ui.tb000.contextMenu.s004.setValue(30) #normal angle
			self.toggleWidgets(self.crease_ui.tb000.contextMenu, self.crease_submenu_ui.tb000.contextMenu, setChecked='chk003', setUnChecked='chk002')
			self.crease_ui.tb000.contextMenu.s003.setDisabled(True)
			text = 'Un-Crease 0'
		else:
			self.crease_ui.tb000.contextMenu.s003.setValue(self.creaseValue) #crease value
			self.crease_ui.tb000.contextMenu.s004.setValue(60) #normal angle
			self.crease_ui.tb000.contextMenu.s003.setEnabled(True)
			text = '{} {}'.format('Crease', self.creaseValue)

		self.crease_ui.tb000.setText(text)


	def chk011(self, state=None):
		'''Crease: Auto
		'''
		if self.crease_ui.tb000.contextMenu.chk011.isChecked():
			self.toggleWidgets(self.crease_ui.tb000.contextMenu, setEnabled='s005,s006')
		else:
			self.toggleWidgets(self.crease_ui.tb000.contextMenu, setDisabled='s005,s006')


	def b000(self):
		'''Crease Set Transfer: Transform Node
		'''
		if self.crease_ui.b001.isChecked():
			newObject = str(pm.ls(selection=1)) #ex. [nt.Transform(u'pSphere1')]

			index1 = newObject.find("u")
			index2 = newObject.find(")")
			newObject = newObject[index1+1:index2].strip("'") #ex. pSphere1

			if newObject != "[":
				self.crease_ui.b001.setText(newObject)
			else:
				self.crease_ui.b001.setText("must select obj first")
				self.toggleWidgets(setUnChecked='b001')
			if self.crease_ui.b000.isChecked():
				self.toggleWidgets(setEnabled='b052')
		else:
			self.crease_ui.b001.setText("Object")


	def b001(self):
		'''Crease Set Transfer: Crease Set
		'''
		if self.crease_ui.b000.isChecked():
			creaseSet = str(pm.ls(selection=1)) #ex. [nt.CreaseSet(u'creaseSet1')]

			index1 = creaseSet.find("u")
			index2 = creaseSet.find(")")
			creaseSet = creaseSet[index1+1:index2].strip("'") #ex. creaseSet1

			if creaseSet != "[":
				self.crease_ui.b000.setText(creaseSet)
			else:
				self.crease_ui.b000.setText("must select set first")
				self.toggleWidgets(setUnChecked='b000')
			if self.crease_ui.b001.isChecked():
				self.toggleWidgets(setEnabled='b052')
		else:
			self.crease_ui.b000.setText("Crease Set")
	