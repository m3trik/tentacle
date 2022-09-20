# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtCore

from attributes import Attributes
from text import RichText, TextOverlay
from menu import MenuInstance

from pushButton_optionBox import PushButton_optionBox



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


class PushButton(QtWidgets.QPushButton, MenuInstance, Attributes, RichText, TextOverlay):
	'''
	'''
	def __init__(self, parent=None, showMenuOnMouseOver=False, **kwargs):
		QtWidgets.QPushButton.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		self.menu_.position = 'topRight'
		self.showMenuOnMouseOver = showMenuOnMouseOver

		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		#override built-ins
		self.text = self.richText
		self.setText = self.setRichText
		self.sizeHint = self.richTextSizeHint

		self.optionBox = None

		self.setAttributes(**kwargs)


	def enterEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.showMenuOnMouseOver:
			self.menu_.show()

		QtWidgets.QPushButton.enterEvent(self, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if event.button()==QtCore.Qt.RightButton:
			self.ctxMenu.show()

		QtWidgets.QPushButton.mousePressEvent(self, event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.showMenuOnMouseOver:
			self.menu_.hide()

		QtWidgets.QPushButton.leaveEvent(self, event)


	def createOptionBox(self):
		'''
		'''
		self.optionBox = PushButton_optionBox(self) #create an option box


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.ctxMenu.containsMenuItems:
			if not self.optionBox:
				self.createOptionBox()

		QtWidgets.QPushButton.showEvent(self, event)









if __name__ == "__main__":
	import sys
	from PySide2.QtCore import QSize
	app = QtWidgets.QApplication(sys.argv)

	w = PushButton(
		parent=None,
		setObjectName='b000',
		setText='<hl style="color:black;">A QPushButton <hl style="color:violet;"><b>with Rich Text</b></hl>',
		resize=QSize(125, 45),
		setWhatsThis='',
		# setVisible=True,
	)

	w.show()
	sys.exit(app.exec_())



# --------------------------------
# Notes
# --------------------------------

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

# Deprecated:

