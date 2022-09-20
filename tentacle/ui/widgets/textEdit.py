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


class TextEdit(QtWidgets.QTextEdit, Attributes, MenuInstance):
	'''
	'''
	shown = QtCore.Signal()
	hidden = QtCore.Signal()

	def __init__(self, parent=None, **kwargs):
		QtWidgets.QTextEdit.__init__(self, parent)

		self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

		self.viewport().setAutoFillBackground(False)
		# self.setTextBackgroundColor(QtGui.QColor(50, 50, 50))

		self.setAttributes(**kwargs)


	def insertText(self, text):
		'''Append a new paragraph to the textEdit.

		:Parameters:
			text (str) = A value to append to the lineEdit as a new paragraph. The value is converted to a string if it isn't already.
		'''
		baseStyle = '<font style="color: LightGray; background-color: rgb(50, 50, 50);">'
		self.append(baseStyle+str(text)) #Appends a new paragraph with the given text to the end of the textEdit.


	def showEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.shown.emit()

		# self.resize(self.sizeHint())

		QtWidgets.QTextEdit.showEvent(self, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.hidden.emit()

		self.clear()

		QtWidgets.QTextEdit.hideEvent(self, event)









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)
		
	w = TextEdit()

	w.insertText('Selected: <font style="color: Yellow;">8 <font style="color: LightGray;">/1486 faces')
	w.insertText('Previous Camera: <font style="color: Yellow;">Perspective')

	w.show()
	sys.exit(app.exec_())



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