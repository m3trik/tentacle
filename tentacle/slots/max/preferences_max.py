# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.preferences import Preferences
from ui.static.max.preferences_ui_max import Preferences_ui_max



class Preferences(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Preferences_ui_max.__init__(self, *args, **kwargs)
		Preferences.__init__(self, *args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.preferences_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.preferences_ui.draggable_header.contextMenu.cmb000

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Preferences:App - Set Working Units: Linear
		'''
		cmb = self.preferences_ui.cmb001

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

		if index is not None:
			pm.currentUnit(time=cmb.items[index]) #game | film | pal | ntsc | show | palf | ntscf


	def cmb003(self, index=-1):
		'''Ui Style: Set main ui style using QStyleFactory
		'''
		cmb = self.preferences_ui.cmb003

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
print (__name__)
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

