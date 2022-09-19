# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtCore

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


class Label(QtWidgets.QLabel, MenuInstance, Attributes):
	'''
	'''
	clicked = QtCore.Signal()
	released = QtCore.Signal()

	def __init__(self, parent=None, **kwargs):
		QtWidgets.QLabel.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		self.setTextFormat(QtCore.Qt.RichText)
		self.setAttributes(**kwargs)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event (QEvent) = 
		'''
		if event.button()==QtCore.Qt.LeftButton:
			self.clicked.emit()
			self.menu_.show()

		if event.button()==QtCore.Qt.RightButton:
			self.contextMenu.show()

		return QtWidgets.QLabel.mousePressEvent(self, event)


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event (QEvent) = 
		'''
		if event.button()==QtCore.Qt.LeftButton:
			self.released.emit()

		return QtWidgets.QLabel.mouseReleaseEvent(self, event)









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)

	w = Label(setText='QLabel', setVisible=True)
	w.resize(w.sizeHint().width(), 19)
	menuItem = w.menu_.add(Label, setText='menu item')
	contextMenuItem = w.contextMenu.add(Label, setText='context menu item')
	print (menuItem, contextMenuItem)
	# w.show()
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

# deprecated:

