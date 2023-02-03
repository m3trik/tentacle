# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtCore

try:
	from pymxs import runtime as rt
except ImportError as error:
	print(error)

from tentacle.tcl import Tcl


class Tcl_max(Tcl):
	'''Tcl class overridden for use with Autodesk 3ds max.

	:Parameters:
		parent = main application top level window object.
	'''
	def __init__(self, parent=None, slotLoc='slots/max', *args, **kwargs):
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
		'''Get the 3DS MAX main window.

		Returns:
			PySide2.QtWidgets.QMainWindow: 'QMainWindow' 3DS MAX main window.
		'''
		# import qtmax
		# main_window = qtmax.GetQMaxMainWindow()

		main_window = next((w.window() for w in cls.app.topLevelWidgets()
			if w.inherits('QMainWindow') and w.metaObject().className()=='QmaxApplicationWindow'), 
				lambda: (_ for _ in ()).throw(RuntimeError('Count not find QmaxApplicationWindow instance.'))
			)

		if not main_window.objectName():
			main_window.setObjectName('MaxWindow')

		return main_window


	def keyPressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			modifiers = self.sb.app.keyboardModifiers()

			if event.key()==self.key_undo and modifiers==QtCore.Qt.ControlModifier:
				import pymxs
				pymxs.undo(True)

		Tcl.keyPressEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		try:
			rt.enableAccelerators = False

		except Exception as error:
			print(error)

		Tcl.showEvent(self, event) #super().showEvent(event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		try:
			rt.enableAccelerators = True

		except Exception as error:
			print(error)

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
		_instances[instanceID] = Tcl_max(*args, **kwargs)
		return _instances[instanceID]

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__ == "__main__":

	tcl = Tcl_max()
	tcl.show('init')

	sys.exit(tcl.sb.app.exec_()) # run app, show window, wait for input, then terminate program with a status code returned from app.

#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# Example startup macro:

	# macroScript main_max
	# category: "_macros.ui"
	# silentErrors: false
	# autoUndoEnabled: false
	# (
	# 	python.Execute "if 'tentacle' not in globals(): from tcl_max import Tcl_max; global tcl; tcl = Tcl_max(key_show='Key_F12', profile=False)" --create an instance
	# 	python.Execute "tcl.sendKeyPressEvent(tcl.key_show);"
	# )




# deprecated: -----------------------------------

# class Instance(Instance):
# 	'''Manage multiple instances of Tcl_max.
# 	'''
# 	def __init__(self, *args, **kwargs):
# 		'''
# 		'''
# 		super().__init__(*args, **kwargs)
# 		self.Class = Tcl_max




# import contextlib
# @contextlib.contextmanager
# def performAppUndo(self, enabled=True, message=''):
# 	'''
# 	Uses pymxs's undo mechanism, but doesn't silence exceptions raised
# 	in it.

# 	:Parameter:
# 		enabled (bool) = Turns undo functionality on.
# 		message (str) = Label for the undo item in the undo menu.
# 	'''
# 	print('undo')
# 	import pymxs
# 	import traceback
# 	e = None
# 	with pymxs.undo(enabled, message):
# 		try:
# 			yield
# 		except Exception as e:
# 			# print error, raise error then run undo 
# 			print(traceback.print_exc())
# 			raise(e)
# 			pymxs.run_undo()