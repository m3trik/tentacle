# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import Preferences_ui



class Preferences_ui_max(Preferences_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		Preferences_ui.__init__(self, *args, **kwargs)

		ctx = self.preferences_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

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
