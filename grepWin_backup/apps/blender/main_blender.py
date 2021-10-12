# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import sys

from PySide2 import QtWidgets, QtCore

try: import shiboken2
except: from PySide2 import shiboken2

from radial import Main



class Main_maya(Main):
	'''Main class overridden for use with Blender.

	:Parameters:
		parent = Application top level window instance.
	'''
	qapp = QtWidgets.QApplication

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

		return Main.showEvent(self, event) #super(Main_blender, self).showEvent(event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if __name__ == "__main__":
			self.qapp.instance().quit()
			sys.exit() #assure that the sys processes are terminated.

		return Main.hideEvent(self, event) #super(Main_blender, self).hideEvent(event)


class Instance():
	'''Manage multiple instances of Main_blender.
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
			setattr(self, name, Main_maya(self.parent, self.preventHide, self.key_show))
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
	app = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not app:
		app = QtWidgets.QApplication(sys.argv)

	#create a generic parent object to run the code outside of blender.
	dummyParent = QtWidgets.QWidget()
	# dummyParent.setObjectName('BlenderWindow')

	import cProfile
	cProfile.run("Instance(dummyParent).show('init')")
	# Instance(dummyParent).show_() #Main_maya(dummyParent).show()
	sys.exit(app.exec_())



# -----------------------------------------------
# Notes
# -----------------------------------------------


# run = if 'main' not in locals() or 'main' not in globals(): main = Main_blender.createInstance(); main.hide(); main.show(),
