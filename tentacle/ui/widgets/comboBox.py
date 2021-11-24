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


class ComboBox(QtWidgets.QComboBox, MenuInstance, Attributes, RichText):
	'''
	'''
	returnPressed = QtCore.Signal()
	beforePopupShown = QtCore.Signal()
	beforePopupHidden = QtCore.Signal()

	def __init__(self, parent=None, popupStyle='modelView', **kwargs):
		QtWidgets.QComboBox.__init__(self, parent)
		'''
		:Parameters:
			popupStyle (str) = specify the type of popup menu. default is the standard 'modelView'.
		'''
		self.popupStyle = popupStyle

		# self.menu_.visible = False #built-in method isVisible() not working.
		self.view().installEventFilter(self)

		self.setAttributes(**kwargs)


	@property
	def items(self):
		'''Get a list of each items's text from the standard model/view.
		:Return:
			(list)
		'''
		return [self.itemText(i) for i in range(self.count())]


	def blockSignals_(fn):
		'''A decorator that blocks signals before executing a function, and unblocks them after.

		:Parameters:
			fn (obj) = The function to be decorated.
		'''
		def wrapper(self, *args, **kwargs):
			self.blockSignals(True) #to keep clear from triggering currentIndexChanged
			rtn = fn(self, *args, **kwargs)
			self.blockSignals(False)
			return rtn
		return wrapper


	@blockSignals_
	def addItems_(self, items, header=None, clear=True, ascending=False):
		'''Add items to the combobox's standard modelView without triggering any signals.

		:Parameters:
			items (str)(list) = A string or list of strings to fill the comboBox with.
			header (str) = An optional value for the first index of the comboBox's list.
			clear (bool) = Clear any previous items before adding new.
			ascending (bool) = Insert in ascending order. New item(s) will be added to the top of the list.

		:Return:
			(list) comboBox's current item list minus any header.

		ex call: comboBox.addItems_(["Import file", "Import Options"], "Import")
		'''
		index = self.currentIndex() if self.currentIndex()>0 else 0 #get the current index before refreshing list. avoid negative values.

		if clear:
			self.clear()

		if not isinstance(items, (list, tuple, set)):
			items = [items]

		for item in [header]+items:
			if item is not None:
				if ascending:
					self.insertItem(0, item)
				else:
					self.addItem(item)

		self.setCurrentIndex(index)

		return items


	@blockSignals_
	def currentText(self):
		'''Get the text at the current index.

		:Parameters:
			item (str) = item text.
		'''
		return self.richText()


	@blockSignals_
	def setCurrentText(self, text):
		'''Sets the text for the current index.

		:Parameters:
			item (str) = item text.
		'''
		index = self.currentIndex()
		self.setRichText(text, index)


	@blockSignals_
	def setItemText(self, index, text):
		'''Set the text at the given index.
		Override for setItemText built-in method.

		:Parameters:
			item (str) = Item text.
			index (int) = Item index
		'''
		self.setRichText(text, index)


	@blockSignals_
	def setCurrentItem(self, i):
		'''Sets the current item from the given item text, or index without triggering any signals.

		:Parameters:
			i (str)(int) = item text or item index
		'''
		try: #set by item index:
			self.setCurrentIndex(i)

		except Exception as error: #set by item text:
			print (__name__, 'setCurrentItem:', error)
			self.setCurrentText(i)


	def showPopup(self):
		'''Show the popup menu.
		'''
		self.beforePopupShown.emit()

		if not self.popupStyle=='modelView':
			if not self.menu_.isVisible():
				self.menu_.show()
				# self.menu_.visible = True
			else:
				self.menu_.hide()
				# self.menu_.visible = False
			return	

		else:
			width = self.sizeHint().width()
			self.view().setMinimumWidth(width)

		QtWidgets.QComboBox.showPopup(self)


	def hidePopup(self):
		''''''
		self.beforePopupHidden.emit()

		if not self.popupStyle=='modelView':
			self.menu_.hide()
			# self.menu_.visible=False
		else:
			QtWidgets.QComboBox.hidePopup(self)


	def clear(self):
		''''''
		if not self.popupStyle=='modelView':
			self.menu_.clear()
		else:
			QtWidgets.QComboBox.clear(self)


	def enterEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''

		return QtWidgets.QComboBox.enterEvent(self, event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		# self.hidePopup()

		return QtWidgets.QComboBox.leaveEvent(self, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		if event.button()==QtCore.Qt.RightButton:
			self.contextMenu.show()

		return QtWidgets.QComboBox.mousePressEvent(self, event)


	def keyPressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if event.key()==QtCore.Qt.Key_Return and not event.isAutoRepeat():
			self.returnPressed.emit()
			self.setEditable(False)

		return QtWidgets.QComboBox.keyPressEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		text = self.itemText(0).rstrip('*')
		if self.contextMenu.containsMenuItems:
			self.contextMenu.setTitle(text)
			self.setItemText(0, text+'*') #set text: comboBox

		return QtWidgets.QComboBox.showEvent(self, event)


	def eventFilter(self, widget, event):
		'''Event filter for the standard view.

		QtCore.QEvent.Show, Hide, FocusIn, FocusOut, FocusAboutToChange
		'''
		# if not (str(event.type()).split('.')[-1]) in ['QPaintEvent', 'UpdateLater', 'PolishRequest', 'Paint']: print(str(event.type())) #debugging
		if event.type()==QtCore.QEvent.Hide:
			if self.parent().__class__.__name__=='Menu':
				self.parent().hide()

		return QtWidgets.QComboBox.eventFilter(self, widget, event)









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	w = ComboBox(popupStyle='qmenu')
	w.show()
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

# Deprecated -----------------------------------------------


	# def addToContext(self, w, header=None, **kwargs):
	# 	'''
	# 	Same as 'add', but instead adds items to the context menu.
	# 	'''
	# 	_menu=self.contextMenu
	# 	return self.add(w, header, _menu, **kwargs)


	# def add(self, w, header=None, _menu=None, **kwargs):
	# 	'''
	# 	Add an item to the comboboxes's menu. (custom or the standard modelView).

	# 	:Parameters:
	# 		w (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel
	# 		header (str) = optional - header string at top when using standard model/view.
	# 		_menu (obj) = menu to add to. typically internal use only.

	# 	kw:Parameters:
	# 		show (bool) = show the menu.
	# 		insertSeparator (QAction) = insert separator in front of the given action.

	# 	:Return:
	# 		the added widget.

	# 	ex.call:
	# 	tb.menu_.add('QCheckBox', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
	# 	'''
	# 	if self.popupStyle=='modelView' and _menu is None:
	# 		item = self.addItems_(w, header)
	# 		return item

	# 	try:
	# 		w = getattr(QtWidgets, w)() #ex. QtWidgets.QAction(self) object from string.
	# 	except:
	# 		if callable(w):
	# 			w = w() #ex. QtWidgets.QAction(self) object.

	# 	if _menu is None:
	# 		_menu = self.menu_
	# 	_menu.add(w, **kwargs)

	# 	setattr(self, w.objectName(), w)

	# 	#connect to 'setLastActiveChild' when signal activated.
	# 	if hasattr(w, 'released'):
	# 		w.released.connect(lambda widget=w: self.setLastActiveChild(widget))
	# 	elif hasattr(w, 'valueChanged'):
	# 		w.valueChanged.connect(lambda value, widget=w: self.setLastActiveChild(value, widget))

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




	# def setAttributes(self, attributes=None, order=[Shared, 'setVisible'], **kwargs):
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

	# 	if attr==Shared:
	# 		self.move(self.mapFromGlobal(value - self.rect().center())) #move and center


	# @property
	# def contextMenu(self):
	# 	'''
	# 	Get the context menu.
	# 	'''
	# 	if not hasattr(self, '_menu'):
	# 		self._menu = Menu(self, position='cursorPos')
	# 	return self._menu



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







# shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Return), self, activated=self.onActivated)
# def onActivated(self):
# 	print("enter pressed")


# try:
# 	if not __name__=='__main__':
# 		if callable(self.classMethod):
# 			self.classMethod()
# except:
# 	p = self.parent()
# 	while not hasattr(p.window(), 'sb'):
# 		p = p.parent()

# 	self.sb = p.window().sb
# 	self.parentUiName = self.sb.getUiName()
# 	self.classMethod = self.sb.getMethod(self.parentUiName, self)
# 	if callable(self.classMethod):
# 		self.classMethod()
# 		self.setCurrentItem(0)

# 	self.addContextMenuItemsToToolTip()



	# def childWidgets(self, index=None, contextMenu=False):
	# 	'''
	# 	Get the widget at the given index from a custom menu. If no arg is given all widgets will be returned.

	# 	:Parameters:
	# 		index (int) = widget location.
	# 		contextMenu (bool) = get the child widgets for the context menu.
	# 	:Return:
	# 		(QWidget) or (list)
	# 	'''
	# 	menuWidgets = self.menu.children_(index)
	# 	contextMenuWidgets = self.contextMenu.children_(index)

	# 	if contextMenu:
	# 		return contextMenuWidgets
	# 	if index is None:
	# 		return menuWidgets + contextMenuWidgets
	# 	else:
	# 		return menuWidgets


	# def mouseDoubleClickEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event=<QEvent>
	# 	'''
	# 	if self.isEditable():
	# 		self.setEditable(False)
	# 	else:
	# 		self.setEditable(True)
	# 		print('mouseDoubleClickEvent')
	# 		self.lineEdit().installEventFilter(self)

	# 	return QtWidgets.QComboBox.mouseDoubleClickEvent(self, event)


	# def eventFilter(self, widget, event):
	# 	'''
	# 	Event filter for the lineEdit.
	# 	'''
	# 	if event.type()==QtCore.QEvent.MouseButtonDblClick:
	# 		pass
	# 	# print (event.type)
	# 	if event.type()==QtCore.QEvent.KeyPress:
	# 		print (widget, event, event.key())
	# 		if event.key()==QtCore.Qt.Key_Enter:
	# 			self.setEditable(False)

	# 	return QtWidgets.QComboBox.eventFilter(widget, event)



	# def mouseMoveEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event=<QEvent>
	# 	'''
	# 	# print '__mouseMoveEvent_1'
	# 	if not self.rect().contains(self.mapFromGlobal(QtGui.QCursor.pos())): #if mouse over widget:
	# 		self.hidePopup()

	# 	return QtWidgets.QComboBox.mouseMoveEvent(self, event)




