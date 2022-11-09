# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Crease(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.crease.draggable_header
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='Crease Editors')

		tb000 = self.sb.crease.tb000
		tb000.ctxMenu.add('QSpinBox', setPrefix='Crease Amount: ', setObjectName='s003', setMinMax_='0-10 step1', setValue=10, setToolTip='Crease amount 0-10. Overriden if "max" checked.')
		tb000.ctxMenu.add('QCheckBox', setText='Toggle Max', setObjectName='chk003', setToolTip='Toggle crease amount from it\'s current value to the maximum amount.')
		tb000.ctxMenu.add('QCheckBox', setText='Un-Crease', setObjectName='chk002', setToolTip='Un-crease selected components or If in object mode, uncrease all.')
		tb000.ctxMenu.add('QCheckBox', setText='Perform Normal Edge Hardness', setObjectName='chk005', setChecked=True, setToolTip='Toggle perform normal edge hardness.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Hardness Angle: ', setObjectName='s004', setMinMax_='0-180 step1', setValue=30, setToolTip='Normal edge hardness 0-180.')
		tb000.ctxMenu.add('QCheckBox', setText='Crease Vertex Points', setObjectName='chk004', setChecked=True, setToolTip='Crease vertex points.')
		tb000.ctxMenu.add('QCheckBox', setText='Auto Crease', setObjectName='chk011', setToolTip='Auto crease selected object(s) within the set angle tolerance.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Auto Crease: Low: ', setObjectName='s005', setMinMax_='0-180 step1', setValue=85, setToolTip='Auto crease: low angle constraint.')
		tb000.ctxMenu.add('QSpinBox', setPrefix='Auto Crease: high: ', setObjectName='s006', setMinMax_='0-180 step1', setValue=95, setToolTip='Auto crease: max angle constraint.')
		self.sb.toggleWidgets(tb000.ctxMenu, setDisabled='s005,s006')


	def s003(self, value=None):
		'''Crease Amount
		Tracks the standard crease amount while toggles such as un-crease, and crease max temporarily change the spinbox value. 
		'''
		if not self.sb.crease.tb000.ctxMenu.chk002.isChecked(): #un-crease
			if not self.sb.crease.tb000.ctxMenu.chk003.isChecked(): #toggle max
				self.creaseValue = self.sb.crease.tb000.ctxMenu.s003.value()
				text = self.sb.crease.tb000.text().split()[0]
				self.sb.crease.tb000.setText('{} {}'.format(text, self.creaseValue))


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.crease.draggable_header


	def chk002(self, state=None):
		'''Un-Crease
		'''
		if self.sb.crease.tb000.ctxMenu.chk002.isChecked():
			self.sb.crease.tb000.ctxMenu.s003.setValue(0) #crease value
			self.sb.crease.tb000.ctxMenu.s004.setValue(180) #normal angle
			self.sb.toggleWidgets(self.sb.crease.tb000.ctxMenu, self.crease_submenu.tb000.ctxMenu, setChecked='chk002', setUnChecked='chk003')
			self.sb.crease.tb000.ctxMenu.s003.setDisabled(True)
			text = 'Un-Crease 0'
		else:
			self.sb.crease.tb000.ctxMenu.s003.setValue(self.creaseValue) #crease value
			self.sb.crease.tb000.ctxMenu.s004.setValue(30) #normal angle
			self.sb.crease.tb000.ctxMenu.s003.setEnabled(True)
			text = '{} {}'.format('Crease', self.creaseValue)

		self.sb.crease.tb000.setText(text)


	def chk003(self, state=None):
		'''Crease: Max
		'''
		if self.sb.crease.tb000.ctxMenu.chk003.isChecked():
			self.sb.crease.tb000.ctxMenu.s003.setValue(10) #crease value
			self.sb.crease.tb000.ctxMenu.s004.setValue(30) #normal angle
			self.sb.toggleWidgets(self.sb.crease.tb000.ctxMenu, self.crease_submenu.tb000.ctxMenu, setChecked='chk003', setUnChecked='chk002')
			self.sb.crease.tb000.ctxMenu.s003.setDisabled(True)
			text = 'Un-Crease 0'
		else:
			self.sb.crease.tb000.ctxMenu.s003.setValue(self.creaseValue) #crease value
			self.sb.crease.tb000.ctxMenu.s004.setValue(60) #normal angle
			self.sb.crease.tb000.ctxMenu.s003.setEnabled(True)
			text = '{} {}'.format('Crease', self.creaseValue)

		self.sb.crease.tb000.setText(text)


	def chk011(self, state=None):
		'''Crease: Auto
		'''
		if self.sb.crease.tb000.ctxMenu.chk011.isChecked():
			self.sb.toggleWidgets(self.sb.crease.tb000.ctxMenu, setEnabled='s005,s006')
		else:
			self.sb.toggleWidgets(self.sb.crease.tb000.ctxMenu, setDisabled='s005,s006')


	def b000(self):
		'''Crease Set Transfer: Transform Node
		'''
		if self.sb.crease.b001.isChecked():
			newObject = str(pm.ls(selection=1)) #ex. [nt.Transform(u'pSphere1')]

			index1 = newObject.find("u")
			index2 = newObject.find(")")
			newObject = newObject[index1+1:index2].strip("'") #ex. pSphere1

			if newObject != "[":
				self.sb.crease.b001.setText(newObject)
			else:
				self.sb.crease.b001.setText("must select obj first")
				self.sb.toggleWidgets(setUnChecked='b001')
			if self.sb.crease.b000.isChecked():
				self.sb.toggleWidgets(setEnabled='b052')
		else:
			self.sb.crease.b001.setText("Object")


	def b001(self):
		'''Crease Set Transfer: Crease Set
		'''
		if self.sb.crease.b000.isChecked():
			creaseSet = str(pm.ls(selection=1)) #ex. [nt.CreaseSet(u'creaseSet1')]

			index1 = creaseSet.find("u")
			index2 = creaseSet.find(")")
			creaseSet = creaseSet[index1+1:index2].strip("'") #ex. creaseSet1

			if creaseSet != "[":
				self.sb.crease.b000.setText(creaseSet)
			else:
				self.sb.crease.b000.setText("must select set first")
				self.sb.toggleWidgets(setUnChecked='b000')
			if self.sb.crease.b001.isChecked():
				self.sb.toggleWidgets(setEnabled='b052')
		else:
			self.sb.crease.b000.setText("Crease Set")
	