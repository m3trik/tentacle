# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtWidgets, QtCore

try: import shiboken2
except: from PySide2 import shiboken2

from tentacle import Tcl



class Tcl_maya(Tcl):
	'''Tcl class overridden for use with Autodesk Maya.

	:Parameters:
		parent = Application top level window instance.
	'''
	qApp = QtWidgets.QApplication

	def __init__(self, parent=None, preventHide=False, key_show='Key_F12'):
		'''
		'''
		if not parent:
			try:
				parent = self.getMainWindow()

			except Exception as error:
				print(self.__class__.__name__, error)

		super().__init__(parent)


	def getMainWindow(self):
		'''Get maya's main window object.

		:Return:
			(QWidget)
		'''
		# ptr = OpenMayaUI.MQtUtil.mainWindow()
		# main_window = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)

		main_window = next(w for w in self.qApp.instance().topLevelWidgets() if w.objectName()=='MayaWindow')

		return main_window


	def keyPressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			modifiers = self.qApp.keyboardModifiers()

			if event.key()==self.key_undo and modifiers==QtCore.Qt.ControlModifier:
				import Pymel.Core as pm
				pm.undo()

		return Tcl.keyPressEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''

		return Tcl.showEvent(self, event) #super().showEvent(event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if __name__ == "__main__":
			self.qApp.instance().quit()
			sys.exit() #assure that the sys processes are terminated.

		return Tcl.hideEvent(self, event) #super().hideEvent(event)



class Instance():
	'''Manage multiple instances of Tcl_maya.
	'''
	instances={}

	def __init__(self, parent=None, preventHide=False, key_show=QtCore.Qt.Key_F12):
		'''
		'''
		self.parent = parent
		self.activeWindow_ = None
		self.preventHide = preventHide
		self.key_show = key_show


	def _getInstance(self):
		'''Internal use. Returns a new instance if one is running and currently visible.
		Removes any old non-visible instances outside of the current 'activeWindow_'.
		'''
		self.instances = {k:v for k,v in self.instances.items() if not any([v.isVisible(), v==self.activeWindow_])}

		if self.activeWindow_ is None or self.activeWindow_.isVisible():
			name = 'main'+str(len(self.instances))
			setattr(self, name, Tcl_maya(self.parent, self.preventHide, self.key_show))
			self.activeWindow_ = getattr(self, name)
			self.instances[name] = self.activeWindow_

		return self.activeWindow_


	def show(self, name=None, active=True):
		'''Sets the widget as visible.

		:Parameters:
			name (str) = Show the ui of the given name.
			active (bool) = Set as the active window.
		'''
		inst = self._getInstance()
		inst.show(name=name, active=active)









if __name__ == "__main__":
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	# import os, sys
	# VERSION = '2022'

	# os.environ["MAYA_LOCATION"] = "C:\\Program Files\\Autodesk\\Maya{}".format(VERSION)
	# os.environ["PYTHONHOME"]    = "C:\\Program Files\\Autodesk\\Maya{}\\Python37".format(VERSION)
	# os.environ["PATH"] = "C:\\Program Files\\Autodesk\\Maya{}\\bin;{}".format(VERSION, os.environ["PATH"])

	# path = "C:\\Program Files\\Autodesk\\Maya{}\\Python37".format(VERSION)

	# for root, subdirs, files in os.walk(path):
	# 	for subdir in subdirs:
	# 		path_ = os.path.join(root, subdir)
	# 		sys.path.append(path_)
	# 		# print (path_)

	# import maya.standalone as standalone
	# standalone.initialize(name="python")

	#create a generic parent object to run the code outside of maya.
	dummyParent = QtWidgets.QWidget()
	dummyParent.setObjectName('MayaWindow')

	# import cProfile
	# cProfile.run('Instance(dummyParent).show_()')
	Instance(dummyParent).show('init') #Tcl_maya(dummyParent).show()
	sys.exit(qApp.exec_())



# -----------------------------------------------
# Notes
# -----------------------------------------------


# if not pm.runTimeCommand('Hk_main', exists=1):
# 	pm.runTimeCommand(
# 		'Hk_main'
# 		annotation='',
# 		catagory='',
# 		commandLanguage='python',
# 		command=if 'tentacle' not in {**locals(), **globals()}: main = Tcl_maya.createInstance(); main.hide(); main.show(),
# 		hotkeyCtx='',
# 	)


	# def hk_main_show():
	# 	'''hk_main_show
	# 	Display main marking menu.

	# 	profile: Prints the total running time, times each function separately, and tells you how many times each function was called.
	# 	'''
	# 	if 'main' not in locals() and 'main' not in globals():
	# 		from main_maya import Instance
	# 		main = Instance()

	# 	main.show_()
	# 	# import cProfile
	# 	# cProfile.run('main.show_()')