# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes
from text import RichText, TextOverlay
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


class ComboBox(QtWidgets.QComboBox, MenuInstance, Attributes, RichText, TextOverlay):
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

		self.setStyleSheet(parent.styleSheet()) if parent else None

		# self.menu_.visible = False #built-in method isVisible() not working.
		self.view().installEventFilter(self)

		self.setAttributes(**kwargs)


	@property
	def items(self):
		'''Get a list of each items's text or it's data if it exists from the standard model/view.
		:Return:
			(list)
		'''
		return [self.itemData(i) if self.itemData(i) else self.itemText(i) for i in range(self.count())]


	def blockSignals_(fn):
		'''A decorator that blocks signals before executing a function, and unblocks them after.

		:Parameters:
			fn (obj) = The function to be decorated.
		'''
		def wrapper(self, *args, **kwargs):
			self.blockSignals(True) #prevent triggering currentIndexChanged
			rtn = fn(self, *args, **kwargs)
			self.blockSignals(False)
			return rtn
		return wrapper


	@blockSignals_
	def addItems_(self, items, header=None, clear=True, ascending=False):
		'''Add items to the combobox's standard modelView without triggering any signals.

		:Parameters:
			items (str)(list)(dict) = A string, list of strings, or dict with 'string':data pairs to fill the comboBox with.
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

		if header:
			self.insertItem(-1, header)

		if isinstance(items, str):
			items = [items]
		if isinstance(items, (list, tuple, set)):
			items = {i:None for i in items}

		for item, data in items.items():
			if item is not None:
				if ascending:
					self.insertItem(0, item, data)
				else:
					self.addItem(item, data)

		self.setCurrentIndex(index)

		return items


	@blockSignals_
	def currentText(self):
		'''Get the text at the current index.

		:Parameters:
			item (str) = item text.
		'''
		index = self.currentIndex()
		return self.richText(index)


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
			self.setCurrentIndex(self.items.index(i))

		except Exception as error: #set by item text:
			print ('{}.setCurrentItem({}): {}'.format(__name__, i, error))
			self.setCurrentText(i)


	def showPopup(self):
		'''Show the popup menu.
		'''
		self.beforePopupShown.emit()

		if not self.popupStyle=='modelView':
			self.menu_.show() if not self.menu_.isVisible() else self.menu_.hide()
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
		if self.contextMenu.containsMenuItems:
			# self.contextMenu.setTitle(self.itemText(0))
			self.setTextOverlay('⧉', alignment='AlignRight')
			self.setItemText(0, self.itemText(0)) #set text: comboBox

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

# deprecated:

