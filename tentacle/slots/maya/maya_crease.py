# !/usr/bin/python
# coding=utf-8
import os.path

from maya_init import *



class Crease(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.creaseValue = 10


	@Slots.sync
	def s003(self, value=None):
		'''Crease Amount
		Tracks the standard crease amount while toggles such as un-crease, and crease max temporarily change the spinbox value. 
		'''
		if not self.crease_ui.tb000.contextMenu.chk002.isChecked(): #un-crease
			if not self.crease_ui.tb000.contextMenu.chk003.isChecked(): #toggle max
				self.creaseValue = self.crease_ui.tb000.contextMenu.s003.value()
				text = self.current_ui.tb000.text().split()[0]
				self.current_ui.tb000.setText('{} {}'.format(text, self.creaseValue))


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.crease_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Crease Editors')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.crease_ui.draggable_header.contextMenu.cmb000

		if index is 'setMenu':
			list_ = ['Crease Set Editor']
			cmb.addItems_(list_, 'Crease Editors:')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Crease Set Editor':
				from maya.app.general import creaseSetEditor
				creaseSetEditor.showCreaseSetEditor()

			cmb.setCurrentIndex(0)


	@Slots.sync
	def chk002(self, state=None):
		'''Un-Crease
		'''
		if self.current_ui.tb000.contextMenu.chk002.isChecked():
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

		self.current_ui.tb000.setText(text)


	@Slots.sync
	def chk003(self, state=None):
		'''Crease: Max
		'''
		if self.current_ui.tb000.contextMenu.chk003.isChecked():
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

		self.current_ui.tb000.setText(text)


	@Slots.sync
	def chk011(self, state=None):
		'''Crease: Auto
		'''
		if self.current_ui.tb000.contextMenu.chk011.isChecked():
			self.toggleWidgets(self.crease_ui.tb000.contextMenu, setEnabled='s005,s006')
		else:
			self.toggleWidgets(self.crease_ui.tb000.contextMenu, setDisabled='s005,s006')


	def tb000(self, state=None):
		'''Crease
		'''
		tb = self.current_ui.tb000

		if state is 'setMenu':
			tb.contextMenu.add('QSpinBox', setPrefix='Crease Amount: ', setObjectName='s003', setMinMax_='0-10 step1', setValue=10, setToolTip='Crease amount 0-10. Overriden if "max" checked.')
			tb.contextMenu.add('QCheckBox', setText='Toggle Max', setObjectName='chk003', setToolTip='Toggle crease amount from it\'s current value to the maximum amount.')
			tb.contextMenu.add('QCheckBox', setText='Un-Crease', setObjectName='chk002', setToolTip='Un-crease selected components or If in object mode, uncrease all.')
			tb.contextMenu.add('QCheckBox', setText='Perform Normal Edge Hardness', setObjectName='chk005', setChecked=True, setToolTip='Toggle perform normal edge hardness.')
			tb.contextMenu.add('QSpinBox', setPrefix='Hardness Angle: ', setObjectName='s004', setMinMax_='0-180 step1', setValue=30, setToolTip='Normal edge hardness 0-180.')
			tb.contextMenu.add('QCheckBox', setText='Crease Vertex Points', setObjectName='chk004', setChecked=True, setToolTip='Crease vertex points.')
			tb.contextMenu.add('QCheckBox', setText='Auto Crease', setObjectName='chk011', setToolTip='Auto crease selected object(s) within the set angle tolerance.')
			tb.contextMenu.add('QSpinBox', setPrefix='Auto Crease: Low: ', setObjectName='s005', setMinMax_='0-180 step1', setValue=85, setToolTip='Auto crease: low angle constraint.')
			tb.contextMenu.add('QSpinBox', setPrefix='Auto Crease: high: ', setObjectName='s006', setMinMax_='0-180 step1', setValue=95, setToolTip='Auto crease: max angle constraint.')
			
			self.toggleWidgets(tb.contextMenu, setDisabled='s005,s006')
			return

		creaseAmount = float(tb.contextMenu.s003.value())
		normalAngle = int(tb.contextMenu.s004.value()) 

		if tb.contextMenu.chk011.isChecked(): #crease: Auto
			angleLow = int(tb.contextMenu.s005.value()) 
			angleHigh = int(tb.contextMenu.s006.value()) 

			mel.eval("PolySelectConvert 2;") #convert selection to edges
			contraint = pm.polySelectConstraint( mode=3, type=0x8000, angle=True, anglebound=(angleLow, angleHigh) ) # to get edges with angle between two degrees. mode=3 (All and Next) type=0x8000 (edge). 

		operation = 0 #Crease selected components
		pm.polySoftEdge (angle=0, constructionHistory=0) #Harden edge normal
		if tb.contextMenu.chk002.isChecked():
			objectMode = pm.selectMode (query=True, object=True)
			if objectMode: #if in object mode,
				operation = 2 #2-Remove all crease values from mesh
			else:
				operation = 1 #1-Remove crease from sel components
				pm.polySoftEdge (angle=180, constructionHistory=0) #soften edge normal

		if tb.contextMenu.chk004.isChecked(): #crease vertex point
			pm.polyCrease (value=creaseAmount, vertexValue=creaseAmount, createHistory=True, operation=operation)
		else:
			pm.polyCrease (value=creaseAmount, createHistory=True, operation=operation) #PolyCreaseTool;

		if tb.contextMenu.chk005.isChecked(): #adjust normal angle
			pm.polySoftEdge (angle=normalAngle)

		if tb.contextMenu.chk011.isChecked(): #crease: Auto
			pm.polySelectConstraint( angle=False ) # turn off angle constraint


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


	@Init.undoChunk
	def b002(self):
		'''Transfer Crease Edges
		'''
		# an updated version of this is in the maya python projects folder. transferCreaseSets.py
		# the use of separate buttons for donor and target mesh are deprecated.
		# add pm.polySoftEdge (angle=0, constructionHistory=0); #harden edge, when applying crease.
		
		creaseSet = str(self.crease_ui.b000.text())
		newObject = str(self.crease_ui.b001.text())

		sets = pm.sets (creaseSet, query=1)

		setArray = []
		for set_ in sets:
			name = str(set_)
			setArray.append(name)
		print(setArray)

		# pm.undoInfo (openChunk=1)
		for set_ in setArray:
			oldObject = ''.join(set_.partition('.')[:1]) #ex. pSphereShape1 from pSphereShape1.e[260:299]
			pm.select (set_, replace=1)
			value = pm.polyCrease (query=1, value=1)[0]
			name = set_.replace(oldObject, newObject)
			pm.select (name, replace=1)
			pm.polyCrease (value=value, vertexValue=value, createHistory=True)
			# print("crease:", name)
		# pm.undoInfo (closeChunk=1)

		self.toggleWidgets(setDisabled='b052', setUnChecked='b000')#,self.crease_ui.b001])
		self.crease_ui.b000.setText("Crease Set")
		# self.crease_ui.b001.setText("Object")









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------
#b008, b010, b011, b019, b024-27, b058, b059, b060