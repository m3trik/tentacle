# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes
from text import RichText
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


class PushButtonDraggable(QtWidgets.QPushButton, MenuInstance, Attributes, RichText):
	'''Draggable/Checkable pushbutton.
	'''
	__mousePressPos = QtCore.QPoint()

	def __init__(self, parent=None, **kwargs):
		QtWidgets.QPushButton.__init__(self, parent)

		self.setCheckable(True)

		self.setStyleSheet('''
			QPushButton {
				border: 1px solid transparent;
				background-color: rgba(127,127,127,2);
			}

			QPushButton::hover {
				background-color: rgba(127,127,127,2);
			}

			QPushButton:checked::hover {
				background-color: rgba(127,127,127,2);
			}''')

		self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

		#override built-ins
		self.text = self.richText
		self.setText = self.setRichText
		self.sizeHint = self.richTextSizeHint

		self.setAttributes(**kwargs)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		if event.button()==QtCore.Qt.LeftButton:
			self.__mousePressPos = event.globalPos() #mouse positon at press.
			self.__mouseMovePos = event.globalPos() #mouse move position from last press. (updated on move event) 

			self.setChecked(True) #setChecked to prevent window from closing.
			self.window().preventHide = True

		if event.button()==QtCore.Qt.RightButton:
			self.contextMenu.show()

		return QtWidgets.QPushButton.mousePressEvent(self, event)


	def mouseMoveEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))

		#move window:
		curPos = self.window().mapToGlobal(self.window().pos())
		globalPos = event.globalPos()

		try: #if hasattr(self, '__mouseMovePos'):
			diff = globalPos - self.__mouseMovePos

			self.window().move(self.window().mapFromGlobal(curPos + diff))
			self.__mouseMovePos = globalPos
		except AttributeError as error:
			pass

		return QtWidgets.QPushButton.mouseMoveEvent(self, event)


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

		moveAmount = event.globalPos() -self.__mousePressPos

		if moveAmount.manhattanLength() >5: #if widget moved:
			self.setChecked(True) #setChecked to prevent window from closing.
			self.window().preventHide = True
		else:
			self.setChecked(not self.isChecked()) #toggle check state

		self.window().preventHide = self.isChecked()
		if not self.window().preventHide: #prevent the parent window from hiding if checked.
			self.window().hide()

		return QtWidgets.QPushButton.mouseReleaseEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		text = self.text().rstrip('*')
		if self.menu_.containsMenuItems:
			self.menu_.setTitle(text)

		if self.contextMenu.containsMenuItems:
			self.contextMenu.setTitle(text)
			self.setText(text+'*')

		return QtWidgets.QPushButton.showEvent(self, event)









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)
		
	PushButtonDraggable().show()
	sys.exit(qApp.exec_())



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


# Deprecated ---------------------------------------------------------------


	# def showEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event=<QEvent>
	# 	'''

	# 	return QtWidgets.QPushButton.showEvent(self, event)


	# def add(self, w, **kwargs):
	# 	'''
	# 	Add items to the toolbutton's menu.

	# 	:Parameters:
	# 		widget (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel
	# 	kw:Parameters:
	# 		show (bool) = show the menu.
	# 		insertSeparator (QAction) = insert separator in front of the given action.
	# 	:Return:
 # 			the added widget.

	# 	ex.call:
	# 	tb.menu_.add('QCheckBox', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
	# 	'''
	# 	try:
	# 		w = getattr(QtWidgets, w)() #ex. QtWidgets.QAction(self) object from string.
	# 	except:
	# 		if callable(w):
	# 			w = w() #ex. QtWidgets.QAction(self) object.

	# 	w.setMinimumHeight(self.minimumSizeHint().height()+1) #set child widget height to that of the toolbutton

	# 	w = self.contextMenu.add(w, **kwargs)
	# 	setattr(self, w.objectName(), w)
	# 	return w


	# def children_(self, index=None):
	# 	'''
	# 	Get the widget at the given index.
	# 	If no arg is given all widgets will be returned.

	# 	:Parameters:
	# 		index (int) = widget location.
	# 	:Return:
	# 		(QWidget) or (list)
	# 	'''
	# 	return self.contextMenu.children_(index)


	# @property
	# def containsContextMenuItems(self):
	# 	'''
	# 	Query whether a menu has been constructed.
	# 	'''
	# 	if not self.children_():
	# 		return False
	# 	return True





		# if not __name__=='__main__' and not hasattr(self, 'parentUiName'):
		# 	p = self.parent()
		# 	while not hasattr(p.window(), 'sb'):
		# 		p = p.parent()

		# 	self.sb = p.window().sb
		# 	self.parentUiName = self.sb.getUiName()
		# 	self.childEvents = self.sb.getClassInstance('EventFactoryFilter')

		# 	self.classMethod = self.sb.getMethod(self.parentUiName, self)
		# 	if callable(self.classMethod):
		# 		if self.contextMenu:
		# 			self.classMethod('setMenu')