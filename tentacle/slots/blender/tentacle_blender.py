# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtWidgets, QtCore

try: import shiboken2
except: from PySide2 import shiboken2

from tentacle import Tentacle_main



class Tentacle_blender(Tentacle_main):
	'''Tentacle class overridden for use with Blender.

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

		# progressIndicator = wgts.WidgetProgressIndicator()
		# progressIndicator.start()

		super().__init__(parent)

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

		return Tentacle_main.showEvent(self, event) #super(Tentacle_main, self).showEvent(event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if __name__ == "__main__":
			self.qApp.instance().quit()
			sys.exit() #assure that the sys processes are terminated.

		return Tentacle_main.hideEvent(self, event) #super(Tentacle_main, self).hideEvent(event)


class Instance():
	'''Manage multiple instances of Tentacle_blender.
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
			name = 'tentacle'+str(len(self.instances))
			setattr(self, name, Tentacle_blender(self.parent, self.preventHide, self.key_show))
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

	#create a generic parent object to run the code outside of blender.
	dummyParent = QtWidgets.QWidget()
	dummyParent.setObjectName('BlenderWindow')

	import cProfile
	cProfile.run("Instance(dummyParent).show('init')")
	# Instance(dummyParent).show_() #Tentacle_blender(dummyParent).show()
	sys.exit(qApp.exec_())



# -----------------------------------------------
# Notes
# -----------------------------------------------


# run = if 'tentacle' not in {**locals(), **globals()}: tentacle = Tentacle_blender.createInstance(); tentacle.hide(); tentacle.show(),
