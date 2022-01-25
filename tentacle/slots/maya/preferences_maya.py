# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.preferences import Preferences



class Preferences_maya(Preferences, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Preferences.__init__(self, *args, **kwargs)

		self.preferences_ui.b010.setText('Maya Preferences')

		cmb = self.preferences_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		cmb = self.preferences_ui.cmb001
		items = ['millimeter','centimeter','meter','kilometer','inch','foot','yard','mile']
		cmb.addItems_(items)
		index = cmb.items.index(pm.currentUnit(query=1, fullName=1, linear=1)) #get/set current linear value.
		cmb.setCurrentIndex(index)

		# cmb = self.preferences_ui.cmb002
		# #store a corresponding value for each item in the comboBox list_.
		# l = {'15 fps: ':'game','24 fps: ':'film','25 fps: ':'pal','30 fps: ':'ntsc','48 fps: ':'show','50 fps: ':'palf','60 fps: ':'ntscf'}
		# items = [k+v for k,v in l.items()] #ie. ['15 fps: game','24 fps: film', ..etc]
		# values = [i[1] for i in l] #ie. ['game','film', ..etc]
		# cmb.addItems_(items)
		# index = cmb.items.index(pm.currentUnit(query=1, fullName=1, time=1)) #get/set current time value.
		# cmb.setCurrentIndex(index)

		# cmb = self.preferences_ui.cmb003
		# from PySide2 import QtWidgets, QtCore
		# items = QtWidgets.QStyleFactory.keys() #get styles from QStyleFactory
		# cmb.addItems_(items)
		# index = self.styleComboBox.findText(QtGui.qApp.style().objectName(), QtCore.Qt.MatchFixedString) #get/set current value
		# cmb.setCurrentIndex(index)


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.preferences_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Set Working Units: Linear
		'''
		cmb = self.preferences_ui.cmb001

		if index>0:
			pm.currentUnit(linear=cmb.items[index]) #millimeter | centimeter | meter | kilometer | inch | foot | yard | mile


	def cmb002(self, index=-1):
		'''Set Working Units: Time
		'''
		cmb = self.preferences_ui.cmb002

		if index>0:
			pm.currentUnit(time=cmb.items[index].split()[-1]) #game | film | pal | ntsc | show | palf | ntscf


	def b001(self):
		'''Color Settings

		'''
		mel.eval('colorPrefWnd;')


	def b008(self):
		'''Hotkeys

		'''
		mel.eval("HotkeyPreferencesWindow;")


	def b009(self):
		'''Plug-In Manager

		'''
		mel.eval('PluginManager;')


	def b010(self):
		'''Settings/Preferences

		'''
		mel.eval("PreferencesWindow;")









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated

# def cmb000(self):
# 	'''
# 	Custom Menu Set
# 	'''
# 	cmb = self.preferences_ui.draggable_header.contextMenu.cmb000
	
# 	list_ = ['Modeling', 'Normals', 'Materials', 'UV'] #combobox list menu corresponding to the button text sets.
# 	contents = cmb.addItems_(list_, 'Menu Sets')

# 	if not index:
		# index = cmb.currentIndex()
# 	buttons = self.getObjects(sb.getUi('main'), 'v000-11') #the ui in which the changes are to be made.
# 	for i, button in enumerate(buttons):
# 		if index==1: #set the text for each button.
# 			button.setText(['','','','','','','','','','','',''][i])

# 		if index==2:
# 			button.setText(['','','','','','','','','','','',''][i])