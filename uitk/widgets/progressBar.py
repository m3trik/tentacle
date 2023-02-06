# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes



class ProgressBar(QtWidgets.QProgressBar, Attributes):
	'''ex. for n, i in enumerate(lst):
			if not self.sb.currentUi.progressBar.step(n, len(lst)): #register progress while checking for cancellation:
				break
	'''
	def __init__(self, parent=None, **kwargs):
		QtWidgets.QProgressBar.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		self.setVisible(False)

		self.isCanceled = False
		# self.connect(QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), self), self.cancel())

		self.setAttributes(**kwargs)


	def cancel(self):
		'''cancel the procedure.
		'''
		self.isCanceled = True


	def step(self, progress, length=100):
		'''
		:Parameters:
			progress (int): current value
			length (int): total value

		:Return:
			current percentage
		ie.
		self.progressBar(init=1) #initialize the progress bar
		for obj in selection:
			self.progressBar(len(selection)) #register progress
		'''
		if self.isCanceled:
			return False

		if not self.isVisible():
			self.setVisible(True)

		value = 100*progress/length
		self.setValue(value)
		# QtWidgets.QApplication.instance().processEvents() #ensure that any pending events are processed sufficiently often for the GUI to remain responsive
		if value>=100:
			self.setVisible(False)

		print(value)
		return True


	def showEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.isCanceled = False
		self.setValue(0)

		QtWidgets.QProgressBar.showEvent(self, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''

		QtWidgets.QProgressBar.hideEvent(self, event)






if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	w = ProgressBar()
	w.show()
	sys.exit(app.exec_())



# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

'''
Promoting a widget in designer to use a custom class:
>	In Qt Designer, select all the widgets you want to replace, 
		then right-click them and select 'Promote to...'. 

>	In the dialog:
		Base Class:		Class from which you inherit. ie. QWidget
		Promoted Class:	Name of the class. ie. "MyWidget"
		Header File:	Path of the file (changing the extension .py to .h)  ie. myfolder.mymodule.mywidget.h

>	Then click "Add", "Promote", 
		and you will see the class change from "QWidget" to "MyWidget" in the Object Inspector pane.
'''

# deprecated: -----------------------------------

# if pm.progressBar ("progressBar_", query=1, isCancelled=1):
	# break
