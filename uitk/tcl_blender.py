# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtCore

from tentacle.tcl import Tcl


class Tcl_blender(Tcl):
	'''Tcl class overridden for use with Blender.

	:Parameters:
		parent = Application top level window instance.
	'''
	def __init__(self, parent=None, slotLoc='slots/blender', *args, **kwargs):
		'''
		'''
		if not parent:
			try:
				parent = self.getMainWindow()

			except Exception as error:
				print(__file__, error)

		super().__init__(parent, slotLoc=slotLoc, *args, **kwargs)


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
			modifiers = self.sb.app.keyboardModifiers()

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
			self.sb.app.quit()
			sys.exit() #assure that the sys processes are terminated.

		Tcl.hideEvent(self, event) #super().hideEvent(event)

# --------------------------------------------------------------------------------------------

_instances = {}
def getInstance(instanceID=None, *args, **kwargs):
	'''Get an instance of this class using a given instanceID.
	The instanceID is either the object or the object's id.

	:Parameters:
		instanceID () = The instanceID can be any immutable type.
		args/kwargs () = The args to be passed to the class instance when it is created.

	:Return:
		(obj) An instance of this class.

	ex. call: tcl = Tcl_maya.getInstance(id(0), key_show='Key_F12') #returns the class instance with an instance ID of the value of `id(0)`.
	'''
	import inspect

	if instanceID is None:
		instanceID = inspect.stack()[1][3]
	try:
		return _instances[instanceID]

	except KeyError as error:
		_instances[instanceID] = Tcl_blender(*args, **kwargs)
		return _instances[instanceID]

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__ == "__main__":

	tcl = Tcl_blender()
	tcl.show('init')

	sys.exit(tcl.sb.app.exec_()) # run app, show window, wait for input, then terminate program with a status code returned from app.

#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

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