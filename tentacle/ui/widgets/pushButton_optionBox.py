# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtCore

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


class PushButton_optionBox(QtWidgets.QPushButton, MenuInstance, Attributes, RichText):
	'''
	'''
	def __init__(self, parent, showMenuOnMouseOver=False, **kwargs):
		QtWidgets.QPushButton.__init__(self, parent)

		#override built-ins
		self.text = self.richText
		self.setText = self.setRichText
		self.sizeHint = self.richTextSizeHint

		self.menu_.position = 'topRight'
		self.showMenuOnMouseOver = showMenuOnMouseOver

		self.setText('<hl style="color:black;">⧉</hl>')
		self.setObjectName('{}_optionBox'.format(parent.objectName()))
		self.resize(self.parent().size().height(), self.parent().size().height())

		self.setMaximumWidth(self.size().width())
		self.parent().setMaximumWidth(20)#self.parent().size().width() - self.size().width())

		print ('parent:  ', parent)
		print ('g_parent:', self.parent().parent())
		print ('\n')

		# container = QtWidgets.QWidget(self.parent().parent())

		layout = QtWidgets.QHBoxLayout()
		layout.setContentsMargins(1,0,0,0)
		layout.setSpacing(0)
		layout.addWidget(self.parent())
		layout.addWidget(self)

		self.parent().parent().setLayout(layout)

		self.parent().setText('opt')

		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.
		self.setAttributes(**kwargs)


	def enterEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.showMenuOnMouseOver:
			self.menu_.show()

		return QtWidgets.QPushButton.enterEvent(self, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if event.button()==QtCore.Qt.LeftButton:
			self.menu_.show()

		return QtWidgets.QPushButton.mousePressEvent(self, event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.showMenuOnMouseOver:
			self.menu_.hide()

		return QtWidgets.QPushButton.leaveEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.menu_.containsMenuItems:
			self.menu_.setTitle(self.text())
			self.menu_.applyButton.show()

		return QtWidgets.QPushButton.showEvent(self, event)









if __name__ == "__main__":
	import sys
	from PySide2.QtCore import QSize

	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	window = QtWidgets.QWidget()
	parent = QtWidgets.QPushButton(window)

	layout = QtWidgets.QHBoxLayout(window)

	w = PushButton_optionBox(
		parent=parent,
		setText='<hl style="color:black;">⧉</hl>',
		setWhatsThis='',
	)

	window.show()
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

# Deprecated ------------------------------------------------------




	# @property
	# def containsContextMenuItems(self):
	# 	'''
	# 	Query whether a menu has been constructed.
	# 	'''
	# 	if not self.children_():
	# 		return False
	# 	return True


	# def setAttributes(self, attributes=None, order=['globalPos', 'setVisible'], **kwargs):
	# 	'''
	# 	Works with attributes passed in as a dict or kwargs.
	# 	If attributes are passed in as a dict, kwargs are ignored.
	# 	:Parameters:
	# 		attributes (dict) = keyword attributes and their corresponding values.
	# 		#order (list) = list of string keywords. ie. ['move', 'show']. attributes in this list will be set last, in order of the list. an example would be setting move positions after setting resize arguments.
	# 	kw:Parameters:
	# 		set any keyword arguments.
	# 	'''
	# 	if not attributes:
	# 		attributes = kwargs

	# 	for k in order:
	# 		v = attributes.pop(k, None)
	# 		if v:
	# 			from collections import OrderedDict
	# 			attributes = OrderedDict(attributes)
	# 			attributes[k] = v

	# 	for attr, value in attributes.items():
	# 		try:
	# 			getattr(self, attr)(value)

	# 		except Exception as error:
	# 			if type(error)==AttributeError:
	# 				self.setCustomAttribute(attr, value)
	# 			else:
	# 				raise error


	# def setCustomAttribute(self, attr, value):
	# 	'''
	# 	Handle custom keyword arguments.
	# 	:Parameters:
	# 		attr (str) = custom keyword attribute.
	# 		value (str) = the value corresponding to the given attr.
	# 	kw:Parameters:
	# 		copy (obj) = widget to copy certain attributes from.
	# 		globalPos (QPoint) = move to given global location and center.
	# 	'''
	# 	if attr=='copy':
	# 		self.setObjectName(value.objectName())
	# 		self.resize(value.size())
	# 		self.setText(value.text())
	# 		self.setWhatsThis(value.whatsThis())

	# 	if attr=='globalPos':
	# 		self.move(self.mapFromGlobal(value - self.rect().center())) #move and center


	# @property
	# def contextMenu(self):
	# 	'''
	# 	Get the context menu.
	# 	'''
	# 	if not hasattr(self, '_menu'):
	# 		self._menu = Menu(self, position='cursorPos')
	# 	return self._menu


	# def addToContext(self, w, **kwargs):
	# 	'''
	# 	Add items to the pushbutton's context menu.

	# 	:Parameters:
	# 		w (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel
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

	# 	w.setMinimumHeight(self.minimumSizeHint().height()+1) #set child widget height to that of the button

	# 	w = self.contextMenu.add(w, **kwargs)
	# 	setattr(self, w.objectName(), w)
	# 	return w






# if not __name__=='__main__' and not hasattr(self, 'parentUiName'):
# 	p = self.parent()
# 	while not hasattr(p.window(), 'sb'):
# 		p = p.parent()

# 	self.sb = p.window().sb
# 	self.parentUiName = self.sb.getUiName()
# 	self.classMethod = self.sb.getMethod(self.parentUiName, self)

# 	if callable(self.classMethod):
# 		if self.contextMenu:
# 			self.classMethod('setMenu')