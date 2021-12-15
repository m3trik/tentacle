# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtWidgets, QtCore

try: import shiboken2
except: from PySide2 import shiboken2

from tentacle import Tcl, Instance



class Tcl_maya(Tcl):
	'''Tcl class overridden for use with Autodesk Maya.

	:Parameters:
		parent = Application top level window instance.
	'''
	qApp = QtWidgets.QApplication

	def __init__(self, parent=None, *args, **kwargs):
		'''
		'''
		if not parent:
			try:
				parent = self.getMainWindow()

			except Exception as error:
				print(self.__class__.__name__, error)

		super().__init__(parent, *args, **kwargs)


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



class Instance(Instance):
	'''Manage multiple instances of Tcl_maya.
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		super().__init__(*args, **kwargs)
		self.Class = Tcl_maya









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