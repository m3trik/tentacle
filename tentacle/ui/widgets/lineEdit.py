# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes
from menu import MenuInstance


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


class LineEdit(QtWidgets.QLineEdit, MenuInstance, Attributes):
	'''
	'''
	shown = QtCore.Signal()
	hidden = QtCore.Signal()

	def __init__(self, parent=None, **kwargs):
		super().__init__(parent)

		# self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
		self.setAttributes(kwargs)


	def contextMenuEvent(self, event):
		'''Override the standard context menu if there is a custom one.

		:Parameters:
			event=<QEvent>
		'''
		if self.contextMenu:
			self.contextMenu.show()
		else:
			return QtWidgets.QLineEdit.contextMenuEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.shown.emit()

		return QtWidgets.QLineEdit.showEvent(self, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.hidden.emit()

		return QtWidgets.QLineEdit.hideEvent(self, event)









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	w = LineEdit()

	w.insertText('Selected: <font style="color: Yellow;">8 <font style="color: LightGray;">/1486 faces')
	w.insertText('Previous Camera: <font style="color: Yellow;">Perspective')

	w.show()
	sys.exit(qApp.exec_())



# -----------------------------------------------
# Notes
# -----------------------------------------------

# deprecated:

# if pm.progressBar ("progressBar_", query=1, isCancelled=1):
	# break


	# def insertText(self, dict_):
	# 	'''
	# 	:Parameters:
	# 		dict_ = {dict} - contents to add.  for each key if there is a value, the key and value pair will be added.
	# 	'''
	# 	highlight = QtGui.QColor(255, 255, 0)
	# 	baseColor = QtGui.QColor(185, 185, 185)

	# 	#populate the textedit with any values
	# 	for key, value in dict_.items():
	# 		if value:
	# 			self.setTextColor(baseColor)
	# 			self.append(key) #Appends a new paragraph with text to the end of the text edit.
	# 			self.setTextColor(highlight)
	# 			self.insertPlainText(str(value)) #inserts text at the current cursor position.