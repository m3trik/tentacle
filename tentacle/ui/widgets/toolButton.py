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


class ToolButton(QtWidgets.QToolButton, MenuInstance, Attributes, RichText):
	'''
	'''
	def __init__(self, parent=None, showMenuOnMouseOver=False, **kwargs):
		super().__init__(parent)
		RichText.__init__(self, alignment='AlignCenter')

		self.showMenuOnMouseOver=showMenuOnMouseOver

		self.menu_.position = 'topRight'
		self.setMenu(self.menu_)

		self.setArrowType(QtCore.Qt.RightArrow) #DownArrow,LeftArrow,NoArrow,RightArrow,UpArrow
		self.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly) #ToolButtonIconOnly,ToolButtonTextBesideIcon,ToolButtonTextOnly,ToolButtonTextUnderIcon
		self.setPopupMode(self.MenuButtonPopup) #DelayedPopup (default), MenuButtonPopup, InstantPopup

		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		self.setAttributes(kwargs)


	def enterEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.showMenuOnMouseOver:
			self.menu().show()

		return QtWidgets.QToolButton.enterEvent(self, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		if event.button()==QtCore.Qt.RightButton:
			self.contextMenu.show()

		return QtWidgets.QToolButton.mousePressEvent(self, event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.showMenuOnMouseOver:
			self.menu().hide()

		return QtWidgets.QToolButton.leaveEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if not self.menu_.containsMenuItems: #if no menu items present, disable the menu button.
			self.setPopupMode(self.DelayedPopup) #DelayedPopup (default), MenuButtonPopup, InstantPopup

		return QtWidgets.QToolButton.showEvent(self, event)









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)
	
	tb = ToolButton()
	tb.menu().add('QAction', setText='Action', insertSeparator_=True, setVisible=True)
	tb.menu().add('QPushButton', setText='Button')
	tb.menu().add('QLabel', setText='Label')
	# tb.show()
	# tb.showMenu()
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

# deprecated ---------------------------------------------------


	# def add(self, w, _menu=None, **kwargs):
	# 	'''
	# 	Add items to the toolbutton's menu.

	# 	:Parameters:
	# 		w (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel
	# 		_menu (obj) = menu to add to. typically internal use only.
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

	# 	if _menu is None:
	# 		_menu = self.menu()
	# 	w = _menu.add(w, **kwargs)

	# 	setattr(self, w.objectName(), w)

	# 	return w



# def children_(self, of_type=[], contextMenu=False, _exclude=['QAction', 'QWidgetAction']):
	# 	'''
	# 	Get a list of the menu's child objects, excluding those types listed in '_exclude'.

	# 	:Parameters:
	# 		contextMenu (bool) = Get the child widgets for the context menu.
	# 		of_type (list) = Widget types as strings. Types of widgets to return. Any types listed in _exclude will still be excluded.
	# 		_exclude (list) = Widget types as strings. Can be modified to set types to exclude from the returned results.
	# 	:Return:
	# 		(list)
	# 	'''
	# 	if contextMenu:
	# 		menu = self.contextMenu
	# 	else:
	# 		menu = self.menu

	# 	if of_type:
	# 		children = [i for i in menu.children() if i.__class__.__name__ in of_type and i.__class__.__name__ not in _exclude]
	# 	else:
	# 		children = [i for i in menu.children() if i.__class__.__name__ not in _exclude]
	# 	return children





	# @property
	# def containsMenuItems(self):
	# 	'''
	# 	Query whether a menu has been constructed.
	# 	'''
	# 	if not self.children_():
	# 		return False
	# 	return True


	# @property
	# def containsContextMenuItems(self):
	# 	'''
	# 	Query whether a menu has been constructed.
	# 	'''
	# 	if not self.children_(contextMenu=True):
	# 		return False
	# 	return True


	# @property
	# def contextMenu(self):
	# 	'''
	# 	Get the context menu.
	# 	'''
	# 	if not hasattr(self, '_menu'):
	# 		self._menu = Menu(self, position='cursorPos')
	# 	return self._menu


	# def addToContext(self, w, title=None, **kwargs):
	# 	'''
	# 	Same as 'add', but instead adds items to the context menu.
	# 	'''
	# 	_menu=self.contextMenu
	# 	return self.add(w, title, _menu, **kwargs)






# 	if not __name__=='__main__' and not hasattr(self, 'parentUiName'):
# 		p = self.parent()
# 		while not hasattr(p.window(), 'sb'):
# 			p = p.parent()

# 		self.sb = p.window().sb
# 		self.parentUiName = self.sb.getUiName()
# 		self.classMethod = self.sb.getMethod(self.parentUiName, self)

# 		if callable(self.classMethod):
# 			self.classMethod('setMenu')



	# def mouseMoveEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''

	# 	return QtWidgets.QToolButton.mouseMoveEvent(self, event)


	# def mouseClickEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''
	# 	if event.button()==QtCore.Qt.LeftButton:
	# 		pass
	# 	elif event.button()==QtCore.Qt.MiddleButton:
	# 		pass
	# 	elif event.button()==QtCore.Qt.RightButton:
	# 		self.menu().show()

	# 	return QtWidgets.QToolButton.mouseClickEvent(self, event)