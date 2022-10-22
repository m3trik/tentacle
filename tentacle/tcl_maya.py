# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtWidgets, QtCore

try: import shiboken2
except: from PySide2 import shiboken2

from tcl import Tcl
from utils_maya import Utils_maya



class Tcl_maya(Tcl):
	'''Tcl class overridden for use with Autodesk Maya.

	:Parameters:
		parent = Application top level window instance.
	'''
	def __init__(self, parent=None, slotLoc='maya', *args, **kwargs):
		'''
		'''
		if not parent:
			try:
				parent = Utils_maya.getMainWindow()

			except Exception as error:
				print(__file__, error)

		super().__init__(parent, slotLoc=slotLoc, *args, **kwargs)
		setattr(QtWidgets.QApplication.instance(), 'mainAppWindow', parent)


	def keyPressEvent(self, event):
		'''
		:Parameters:
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
			self.app.quit()
			sys.exit() #assure that the sys processes are terminated.

		Tcl.hideEvent(self, event) #super().hideEvent(event)









if __name__ == "__main__":

	tcl = Tcl_maya()
	tcl.show('init') #Tcl_maya(dummyParent).show()

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