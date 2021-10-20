# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Preferences(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.preferences_ui.b010.setText('3dsMax Preferences')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.preferences_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.preferences_ui.draggable_header.contextMenu.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Preferences:App - Set Working Units: Linear
		'''
		cmb = self.preferences_ui.cmb001

		if index is 'setMenu':
			list_ = ['millimeter','centimeter','meter','kilometer','inch','foot','mile']
			cmb.addItems_(list_)
			try:
				index = cmb.items.index(pm.currentUnit(query=1, fullName=1, linear=1)) #get/set current linear value
				cmb.setCurrentIndex(index)
			except:
				pass
			return

		if index is not None:
			if index is 'millimeter':
				maxEval('units.SystemType = #Millimeters')
			if index is 'centimeter':
				maxEval('units.SystemType = #Centimeters')
			if index is 'meter':
				maxEval('units.SystemType = #Meters')
			if index is 'kilometer':
				maxEval('units.SystemType = #Kilometers')
			if index is 'inch':
				maxEval('units.SystemType = #Inches')
			if index is 'foot':
				maxEval('units.SystemType = #Feet')
			if index is 'mile':
				maxEval('units.SystemType = #Miles')


	def cmb002(self, index=-1):
		'''Preferences:App - Set Working Units: Time
		'''
		cmb = self.preferences_ui.cmb002

		if index is 'setMenu':
			#store a corresponding value for each item in the comboBox list_.
			l = [('15 fps: ','game'),('24 fps: ','film'),('25 fps: ','pal'),('30 fps: ','ntsc'),('48 fps: ','show'),('50 fps: ','palf'),('60 fps: ','ntscf')]
			list_ = [i[0]+i[1] for i in l] #ie. ['15 fps: game','24 fps: film', ..etc]
			values = [i[1] for i in l] #ie. ['game','film', ..etc]
			cmb.addItems_(list_)
			try:
				index = cmb.items.index(pm.currentUnit(query=1, fullName=1, time=1)) #get/set current time value
				cmb.setCurrentIndex(index)
			except:
				pass
			return

		if index is not None:
			pm.currentUnit(time=cmb.items[index]) #game | film | pal | ntsc | show | palf | ntscf


	def cmb003(self, index=-1):
		'''Ui Style: Set main ui style using QStyleFactory
		'''
		cmb = self.preferences_ui.cmb003

		if index is 'setMenu':
			from PySide2 import QtWidgets, QtCore
			list_ = QtWidgets.QStyleFactory.keys() #get styles from QStyleFactory
			cmb.addItems_(list_)
			try:
				index = self.styleComboBox.findText(QtGui.qApp.style().objectName(), QtCore.Qt.MatchFixedString)
				cmb.setCurrentIndex(index)
			except:
				pass
			return

		if index is not None:
			QtGui.qApp.setStyle(cmb.items[index])


	def b001(self):
		'''Color Settings
		'''
		maxEval('colorPrefWnd;')


	def b008(self):
		'''Hotkeys
		'''
		maxEval('actionMan.executeAction 0 "59245"') #Customize User Interface: Hotkey Editor


	def b009(self):
		'''Plug-In Manager
		'''
		maxEval('Plug_in_Manager.PluginMgrAction.show()')


	def b010(self):
		'''Settings/Preferences
		'''
		maxEval('actionMan.executeAction 0 "40108"')









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------


	# def cmb000(self, index=-1):
	# 	'''
	# 	Custom Menu Set
	# 	'''
	# 	cmb = self.preferences_ui.draggable_header.contextMenu.cmb000
		
	# 	list_ = ['Modeling', 'Normals', 'Materials', 'UV'] #combobox list menu corresponding to the button text sets.
	# 	contents = cmb.addItems_(list_, 'Menu Sets')

	# 	if not index:
			# index = cmb.currentIndex()
	# 	buttons = self.getObjects(self.tcl.sb.getUi('main'), 'v000-11') #the ui in which the changes are to be made.
	# 	for i, button in enumerate(buttons):
	# 		if index==1: #set the text for each button.
	# 			button.setText(['','','','','','','','','','','',''][i])

	# 		if index==2:
	# 			button.setText(['','','','','','','','','','','',''][i])

