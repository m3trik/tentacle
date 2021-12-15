# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtWidgets, QtCore

try: import shiboken2
except: from PySide2 import shiboken2

from tentacle import Tcl, Instance



class Tcl_blender(Tcl):
	'''Tcl class overridden for use with Blender.

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

		# progressIndicator = self.tcl.wgts.WidgetProgressIndicator()
		# progressIndicator.start()

		super().__init__(parent, *args, **kwargs)

		# progressIndicator.stop()


	def getMainWindow(self):
		'''Get blender's main window object.

		:Return:
			(QWidget)
		'''
		main_window = QApplication.instance().blender_widget

		return main_window


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''

		return Tcl.showEvent(self, event) #super(Tcl, self).showEvent(event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if __name__ == "__main__":
			self.qApp.instance().quit()
			sys.exit() #assure that the sys processes are terminated.

		return Tcl.hideEvent(self, event) #super(Tcl, self).hideEvent(event)



class Instance(Instance):
	'''Manage multiple instances of Tcl_blender.
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		super().__init__(*args, **kwargs)
		self.Class = Tcl_blender









if __name__ == "__main__":
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	#create a generic parent object to run the code outside of blender.
	dummyParent = QtWidgets.QWidget()
	dummyParent.setObjectName('BlenderWindow')

	import cProfile
	cProfile.run("Instance(dummyParent).show('init')")
	# Instance(dummyParent).show_() #Tcl_blender(dummyParent).show()
	sys.exit(qApp.exec_())



# -----------------------------------------------
# Notes
# -----------------------------------------------


# run = if 'tentacle' not in {**locals(), **globals()}: tentacle = Tcl_blender.createInstance(); tentacle.hide(); tentacle.show(),
