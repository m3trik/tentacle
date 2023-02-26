# !/usr/bin/python
# coding=utf-8
from uitk.slots.maya import *
from uitk.slots.preferences import Preferences



class Preferences_maya(Preferences, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.sb.preferences.b010.setText('Maya Preferences')

		cmb000 = self.sb.preferences.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb000.addItems_(items, '')

		cmb001 = self.sb.preferences.cmb001
		items = ['millimeter','centimeter','meter','kilometer','inch','foot','yard','mile']
		cmb001.addItems_(items)
		index = cmb001.items.index(pm.currentUnit(query=1, fullName=1, linear=1)) #get/set current linear value.
		cmb001.setCurrentIndex(index)

		cmb002 = self.sb.preferences.cmb002
		items = {'15 fps (game)':'game','24 fps (film)':'film','25 fps (pal)':'pal','30 fps (ntsc)':'ntsc','48 fps (show)':'show','50 fps (palf)':'palf','60 fps (ntscf)':'ntscf'}
		cmb002.addItems_(items)
		index = cmb002.items.index(pm.currentUnit(query=1, fullName=1, time=1)) #get/set current time value.
		cmb002.setCurrentIndex(index)

		cmb003 = self.sb.preferences.cmb003
		from PySide2 import QtWidgets, QtGui, QtCore
		items = QtWidgets.QStyleFactory.keys() #get styles from QStyleFactory
		cmb003.addItems_(items)
		index = cmb003.findText(QtWidgets.QApplication.style().objectName(), QtCore.Qt.MatchFixedString) #get/set current value
		cmb003.setCurrentIndex(index)


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.preferences.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Set Working Units: Linear
		'''
		cmb = self.sb.preferences.cmb001

		if index>0:
			pm.currentUnit(linear=cmb.items[index]) #millimeter | centimeter | meter | kilometer | inch | foot | yard | mile


	def cmb002(self, index=-1):
		'''Set Working Units: Time
		'''
		cmb = self.sb.preferences.cmb002

		if index>0:
			pm.currentUnit(time=cmb.items[index].split()[-1]) #game | film | pal | ntsc | show | palf | ntscf


	def b001(self):
		'''Color Settings

		'''
		pm.mel.colorPrefWnd()


	def b008(self):
		'''Hotkeys

		'''
		pm.mel.HotkeyPreferencesWindow()


	def b009(self):
		'''Plug-In Manager

		'''
		pm.mel.PluginManager()


	def b010(self):
		'''Settings/Preferences

		'''
		pm.mel.PreferencesWindow()


	@staticmethod
	def loadPlugin(plugin):
		'''Loads A Plugin.
		
		Parameters:
			plugin (str): The desired plugin to load.

		ex. loadPlugin('nearestPointOnMesh')
		'''
		not pm.pluginInfo(plugin, query=True, loaded=True) and pm.loadPlugin(plugin)









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



#deprecated

# def cmb000(self):
# 	'''
# 	Custom Menu Set
# 	'''
# 	cmb = self.sb.preferences.draggable_header.ctxMenu.cmb000
	
# 	items = ['Modeling', 'Normals', 'Materials', 'UV'] #combobox list menu corresponding to the button text sets.
# 	contents = cmb.addItems_(items, 'Menu Sets')

# 	if not index:
		# index = cmb.currentIndex()
# 	buttons = self.getObjects(sb.getUi('main'), 'v000-11') #the ui in which the changes are to be made.
# 	for i, button in enumerate(buttons):
# 		if index==1: #set the text for each button.
# 			button.setText(['','','','','','','','','','','',''][i])

# 		if index==2:
# 			button.setText(['','','','','','','','','','','',''][i])