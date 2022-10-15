# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtCore

from attributes import Attributes
from text import RichText
from menu import MenuInstance



class PushButton_optionBox(QtWidgets.QPushButton, Attributes, RichText):
	'''
	'''
	def __init__(self, parent, showMenuOnMouseOver=False, **kwargs):
		super().__init__(parent)

		#override built-ins
		self.text = self.richText
		self.setText = self.setRichText
		self.sizeHint = self.richTextSizeHint

		self.setStyleSheet(parent.styleSheet())

		# font = self.font()
		# font.setPointSize(font.pointSize()+3)
		# self.setFont(font)

		self.setText('⧉') #default option box text.
		self.setObjectName('{}_optionBox'.format(parent.objectName()))

		self.setMaximumSize(parent.size().height(), parent.size().height())
		parent.setMinimumSize(parent.size().width()-parent.size().height(), parent.size().height())

		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.
		self.setAttributes(**kwargs)


	def create(self):
		'''
		'''
		self.orig_parent = self.parent() #the parent will change after adding a container and a layout, but we will need the original parent widget later.
		g_parent = self.parent().parent()
		container = QtWidgets.QWidget(g_parent)
		container.setMaximumHeight(self.parent().size().height())
		try:
			removed_wItem = g_parent.layout().replaceWidget(self.parent(), container)
			g_parent.layout().update()
		except AttributeError as error:
			pass

		layout = QtWidgets.QHBoxLayout(container)
		layout.setContentsMargins(0,0,0,0)
		layout.setSpacing(0)
		layout.addWidget(self.orig_parent, 0)
		layout.addWidget(self, 1)

		# self.setStyleSheet('''
		# 	QPushButton {border: 0px solid transparent;}
		# 	''')
		# self.orig_parent.setStyleSheet('''
		# 	QPushButton {border: 0px solid transparent;}
		# 	''')
		# container.setStyleSheet('''
		# 	QWidget {border: 1px solid rgb(50,50,50);}
		# 	''')


	# def enterEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''
	# 	# if self.showMenuOnMouseOver:
	# 	# 	self.menu_.show()

	# 	return QtWidgets.QPushButton.enterEvent(self, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if event.button()==QtCore.Qt.LeftButton:
			self.orig_parent.ctxMenu.show()

		QtWidgets.QPushButton.mousePressEvent(self, event)


	# def leaveEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''
	# 	if self.showMenuOnMouseOver:
	# 		self.menu_.hide()

	# 	QtWidgets.QPushButton.leaveEvent(self, event)


	# def showEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''
	# 	if self.menu_.containsMenuItems:
	# 		self.menu_.setTitle(self.text())
	# 		self.menu_.applyButton.show()

	# 	QtWidgets.QPushButton.showEvent(self, event)









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)

	window = QtWidgets.QWidget()
	parent = QtWidgets.QPushButton(window)
	parent.setText('Parent')
	parent.resize(120, 20)


	w = PushButton_optionBox(parent,
		setText='<hl style="color:black;">⧉</hl>'
	)

	window.show()
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

# Deprecated: --------------------

