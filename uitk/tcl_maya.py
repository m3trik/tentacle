# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtCore

from uitk.tcl import Tcl
from mayatk import getMainWindow


class Tcl_maya(Tcl):
	'''Tcl class overridden for use with Autodesk Maya.

	Parameters:
		parent = Application top level window instance.
	'''
	def __init__(self, parent=None, slots_location='slots/maya', *args, **kwargs):
		'''
		'''
		if not parent:
			try:
				parent = getMainWindow()

			except Exception as error:
				print(__file__, error)

		super().__init__(parent, slots_location=slots_location, *args, **kwargs)


	def keyPressEvent(self, event):
		'''
		Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			modifiers = self.app.keyboardModifiers()

			if event.key()==self.key_undo and modifiers==QtCore.Qt.ControlModifier:
				import Pymel.Core as pm
				pm.undo()

		Tcl.keyPressEvent(self, event)


	def showEvent(self, event):
		'''
		Parameters:
			event = <QEvent>
		'''

		Tcl.showEvent(self, event) #super().showEvent(event)


	def hideEvent(self, event):
		'''
		Parameters:
			event = <QEvent>
		'''
		if __name__ == "__main__":
			self.app.quit()
			sys.exit() #assure that the sys processes are terminated.

		Tcl.hideEvent(self, event) #super().hideEvent(event)

# --------------------------------------------------------------------------------------------

_instances = {}
def getInstance(instanceID=None, *args, **kwargs):
	'''Get an instance of this class using a given instanceID.
	The instanceID is either the object or the object's id.

	Parameters:
		instanceID () = The instanceID can be any immutable type.
		args/kwargs () = The args to be passed to the class instance when it is created.

	Return:
		(obj) An instance of this class.

	Example: tcl = Tcl_maya.getInstance(id(0), key_show='Key_F12') #returns the class instance with an instance ID of the value of `id(0)`.
	'''
	import inspect

	if instanceID is None:
		instanceID = inspect.stack()[1][3]
	try:
		return _instances[instanceID]

	except KeyError as error:
		_instances[instanceID] = Tcl_maya(*args, **kwargs)
		return _instances[instanceID]


def show(instanceID=None, *args, **kwargs):
	'''Expands `getInstance` to get and then show an instance in a single command.
	'''
	inst = getInstance(instanceID=instanceID, *args, **kwargs)
	inst.show()

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__ == "__main__":

	main = Tcl_maya()
	main.show('init')

	exit_code = main.app.exec_()
	if exit_code != -1:
		sys.exit(exit_code) # run app, show window, wait for input, then terminate program with a status code returned from app.

#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# Example startup macro:

	# def hk_tentacle_show():
	# 	'''Display the uitk marking menu.
	# 	'''
	# 	if 'tcl' not in globals():
	# 		from tcl_maya import Tcl_maya
	# 		global tcl
	# 		tcl = Tcl_maya(key_show='Key_F12', profile=False)

	# 	tcl.sendKeyPressEvent(tcl.key_show)



# deprecated: -----------------------------------


	# _instances = {}

	# def __init__(self, parent=None, id=None, slots='slots/maya', *args, **kwargs):
	# 	'''
	# 	'''
	# 	if not parent:
	# 		try:
	# 			parent = getMainWindow()

	# 		except Exception as error:
	# 			print(__file__, error)

	# 	super().__init__(parent, slots=slots, *args, **kwargs)

	# 	if id is not None:
	# 		Tcl_maya._instances[id] = self


	# @classmethod
	# def get_instance(cls, id, profile=False):
	# 	if id not in cls._instances:
	# 		cls._instances[id] = Tcl_maya(key_show='Key_F12', profile=profile, id=id)
	# 	return cls._instances[id]


	# def show_instance(self):
	# 	self.sendKeyPressEvent(self.key_show)

	# #call
	# from uitk.tcl_maya import Tcl_maya
	# 	tcl = Tcl_maya.get_instance(id, profile=profile)
	# 	tcl.show_instance()



# class Instance(Instance):
# 	'''Manage multiple instances of Tcl_maya.
# 	'''
# 	def __init__(self, *args, **kwargs):
# 		'''
# 		'''
# 		super().__init__(*args, **kwargs)
# 		self.Class = Tcl_maya





# if not pm.runTimeCommand('Hk_main', exists=1):
# 	pm.runTimeCommand(
# 		'Hk_main'
# 		annotation='',
# 		catagory='',
# 		commandLanguage='python',
# 		command=if 'uitk' not in {**locals(), **globals()}: main = Tcl_maya.createInstance(); main.hide(); main.show(),
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