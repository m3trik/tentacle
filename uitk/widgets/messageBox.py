# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from uitk.widgets.attributes import Attributes


class MessageBox(QtWidgets.QMessageBox, Attributes):
	'''Displays a message box with HTML formatting for a set time before closing.

	Parameters:
		location (str)(point) = move the messagebox to the specified location. Can be given as a qpoint or string value. default is: 'topMiddle'
		timeout (int): time in seconds before the messagebox auto closes.
	'''
	def __init__(self, parent=None, location='topMiddle', timeout=2, **kwargs):
		QtWidgets.QMessageBox.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		self.setWindowFlags(QtCore.Qt.WindowType.WindowDoesNotAcceptFocus|QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint) #QtCore.Qt.CustomizeWindowHint|QtCore.Qt.WindowTitleHint
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.
		self.setStandardButtons(QtWidgets.QMessageBox.NoButton)

		self.menu_timer = QtCore.QTimer()
		self.menu_timer.timeout.connect(self.hide)

		self.setTextFormat(QtCore.Qt.RichText)

		self.location = location

		self.setAttributes(**kwargs)


	def move_(self, location):
		''''''
		p = self.parent()

		if p is None:
			p = self.window()

		rect = p.rect()

		if location=='topMiddle':
			offset = self.sizeHint().width()/2
			point = QtCore.QPoint(rect.right()/2.5-offset, rect.top()+150)

		self.move(point)


	def _setPrefixStyle(self, string):
		'''Set style for specific keywords in the given string.

		Return:
			(str)
		'''
		style = {
		'Error:'	: '<hl style="color:red;">Error:</hl>',
		'Warning:'	: '<hl style="color:yellow;">Warning:</hl>',
		'Note:'		: '<hl style="color:blue;">Note:</hl>',
		'Result:'	: '<hl style="color:green;">Result:</hl>',
		}

		for k,v in style.items():
			string = string.replace(k, v)

		return string


	def _setHTML(self, string):
		'''<p style="font-size:160%;">text</p>
		<p style="text-align:center;">Centered paragraph.</p>
		<p style="font-family:courier;">This is a paragraph.</p>

		Return:
			(str)
		'''
		style = {
		'<p>' 		: '<p style="color:white;">', #paragraph <p>' </p>'
		'<hl>' 		: '<hl style="color:yellow; font-weight: bold;">', #heading <h1>' </h1>'
		'<body>'	: '<body style="color;">', #body <body> </body>
		'<b>'		: '<b style="font-weight: bold;">', #bold <b> </b> 
		'<strong>'	: '<strong style="font-weight: bold;">', #<strong> </strong>
		'<mark>' 	: '<mark style="background-color: grey">', #highlight <mark> </mark>
		}

		for k,v in style.items():
			string = string.replace(k, v)

		return string


	def _setFontColor(self, string, color):
		'''
		Return:
			(str)
		'''
		return '<font color='+color+'>'+string+'</font>'


	def _setBackgroundColor(self, string, color):
		'''
		Return:
			(str)
		'''
		return '<mark style="background-color:'+color+'">'+string+'</mark>'


	def _setFontSize(self, string, size):
		'''
		Return:
			(str)
		'''
		return '<font size='+str(size)+'>'+string+'</font>'


	def setText(self, string, fontColor='white', backgroundColor='rgb(50,50,50)', fontSize=5):
		'''Set the text to be displayed.

		Parameters:
			fontColor (str): text color.
			backgroundColor (str): text background color.
			fontSize (int): text size.
		'''
		s = self._setPrefixStyle(string)
		s = self._setHTML(s)
		s = self._setFontColor(s, fontColor)
		s = self._setBackgroundColor(s, backgroundColor)
		s = self._setFontSize(s, fontSize)

		super().setText(s)


	def showEvent(self, event):
		'''
		Parameters:
			event=<QEvent>
		'''
		self.menu_timer.start(1000)  #5000 milliseconds = 5 seconds
		self.move_(self.location)

		super().showEvent(event)


	def hideEvent(self, event):
		'''
		Parameters:
			event=<QEvent>
		'''
		self.menu_timer.stop()

		super().hideEvent(event)

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.
		
	w = MessageBox()
	w.setText('Warning: Backface Culling is now <hl>Off</hl>')
	w.exec_()

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

# def insertText(self, dict_):
# 	'''
# 	Parameters:
# 		dict_ = {dict} - contents to add.  for each key if there is a value, the key and value pair will be added.
# 	'''
# 	highlight = QtGui.QColor(255, 255, 0)
# 	baseColor = QtGui.QColor(185, 185, 185)

# 	#populate the textedit with any values
# 	for key, value in dict_.items():
# 		if value:
# 			self.setTextColor(baseColor)
# 			self.append(key) #textEdit.append(key+str(value))
# 			self.setTextColor(highlight)
# 			self.insertPlainText(str(value))