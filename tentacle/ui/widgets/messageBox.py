# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes


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


class MessageBox(QtWidgets.QMessageBox, Attributes):
	'''Displays a message box with HTML formatting for a set time before closing.

	:Parameters:
		location (str)(point) = move the messagebox to the specified location. Can be given as a qpoint or string value. default is: 'topMiddle'
		timeout (int) = time in seconds before the messagebox auto closes.
	'''
	def __init__(self, parent=None, location='topMiddle', timeout=2, **kwargs):
		QtWidgets.QMessageBox.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint|QtCore.Qt.WindowStaysOnTopHint) #QtCore.Qt.CustomizeWindowHint|QtCore.Qt.WindowTitleHint
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.
		self.setStandardButtons(QtWidgets.QMessageBox.NoButton)

		self.timer = QtCore.QTimer()
		self.timeout = timeout
		self.timer.timeout.connect(self._tick)
		self.timer.setInterval(1000)

		self.setTextFormat(QtCore.Qt.RichText)

		self.location = location

		self.setAttributes(**kwargs)


	def _tick(self):
		self.timeout -= 1
		if self.timeout >= 0:
			pass
		else:
			self.timer.stop()
			self.hide()


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

		:Return:
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

		:Return:
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
		:Return:
			(str)
		'''
		return '<font color='+color+'>'+string+'</font>'


	def _setBackgroundColor(self, string, color):
		'''
		:Return:
			(str)
		'''
		return '<mark style="background-color:'+color+'">'+string+'</mark>'


	def _setFontSize(self, string, size):
		'''
		:Return:
			(str)
		'''
		return '<font size='+str(size)+'>'+string+'</font>'


	def setText(self, string, fontColor='white', backgroundColor='rgb(50,50,50)', fontSize=5):
		'''Set the text to be displayed.

		:Parameters:
			fontColor (str) = text color.
			backgroundColor (str) = text background color.
			fontSize (int) = text size.
		'''
		string = self._setPrefixStyle(string)
		string = self._setHTML(string)
		string = self._setFontColor(string, fontColor)
		string = self._setBackgroundColor(string, backgroundColor)
		string = self._setFontSize(string, fontSize)

		return super(MessageBox, self).setText(string)


	def exec_(self):
		''''''
		if self.isVisible():
			self.hide()

		self._tick()
		self.timer.start()

		return super(MessageBox, self).exec_()


	def showEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.move_(self.location)

		return QtWidgets.QMessageBox.showEvent(self, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''

		return QtWidgets.QMessageBox.hideEvent(self, event)









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)
		
	w = MessageBox()
	w.setText('Warning: Backface Culling is now <hl>Off</hl>')
	w.exec_()

	sys.exit(qApp.exec_())



# -----------------------------------------------
# Notes
# -----------------------------------------------

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
# 			self.append(key) #textEdit.append(key+str(value))
# 			self.setTextColor(highlight)
# 			self.insertPlainText(str(value))