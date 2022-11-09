# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtWidgets, QtCore

from tcl import Tcl



class Tcl_blender(Tcl):
	'''Tcl class overridden for use with Blender.

	:Parameters:
		parent = Application top level window instance.
	'''
	def __init__(self, parent=None, slotLoc='blender', *args, **kwargs):
		'''
		'''
		if not parent:
			try:
				parent = self.getMainWindow()

			except Exception as error:
				print(__file__, error)

		super().__init__(parent, slotLoc=slotLoc, *args, **kwargs)
		setattr(QtWidgets.QApplication.instance(), 'mainAppWindow', parent)


	@classmethod
	def getMainWindow(cls):
		'''Get blender's main window object.

		:Return:
			(QWidget)
		'''
		main_window = QApplication.instance().blender_widget

		return main_window


	def keyPressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			modifiers = self.app.keyboardModifiers()

			if event.key()==self.key_undo and modifiers==QtCore.Qt.ControlModifier:
				import bpy
				bpy.ops.ed.undo()

		Tcl.keyPressEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''

		Tcl.showEvent(self, event) #super().showEvent(event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if __name__ == "__main__":
			self.app.instance().quit()
			sys.exit() #assure that the sys processes are terminated.

		Tcl.hideEvent(self, event) #super().hideEvent(event)









if __name__ == "__main__":

	Tcl_blender().show('init') #Tcl_maya(dummyParent).show()

	app = QtWidgets.QApplication.instance()
	sys.exit(app.exec_())



#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

# Example startup macro:

	# def hk_tentacle_show():
	# 	'''Display the tentacle marking menu.
	# 	'''
	# 	if 'tcl' not in globals():
	# 		from tcl_maya import Tcl_maya
	# 		global tcl
	# 		tcl = Tcl_maya(key_show='Key_F12', profile=False)

	# 	tcl.sendKeyPressEvent(tcl.key_show)



# deprecated: -----------------------------------