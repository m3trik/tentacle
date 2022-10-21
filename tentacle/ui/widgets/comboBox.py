# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes
from text import RichText, TextOverlay
from menu import MenuInstance



class ComboBox(QtWidgets.QComboBox, MenuInstance, Attributes, RichText, TextOverlay):
	'''
	'''
	returnPressed = QtCore.Signal()
	beforePopupShown = QtCore.Signal()
	beforePopupHidden = QtCore.Signal()

	def __init__(self, parent=None, popupStyle='modelView', **kwargs):
		super().__init__(parent)
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
		ex call: comboBox.addItems_({'Import file':<obj>, "Import Options":<obj>}, "Import") #example of adding items with data.
		'''
		assert isinstance(items, (str, list, set, tuple, dict)), '{}: addItems_: Incorrect datatype: {}'.format(__file__, type(items).__name__) 

		index = self.currentIndex() if self.currentIndex()>0 else 0 #get the current index before refreshing list. avoid negative values.

		if clear:
			self.clear()

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

		if header:
			self.insertItem(-1, header)

		self.setCurrentIndex(index)

		return items


	@blockSignals_
	def currentData(self):
		'''Get the data at the current index.

		:Return:
			() data
		'''
		index = self.currentIndex()
		return self.itemData(index)


	@blockSignals_
	def setCurrentData(self, value):
		'''Sets the data for the current index.

		:Parameters:
			value () = The current item's data value.
		'''
		index = self.currentIndex()
		self.setItemData(index, value)


	@blockSignals_
	def currentText(self):
		'''Get the text at the current index.

		:Return:
			(str)
		'''
		index = self.currentIndex()
		return self.richText(index)


	@blockSignals_
	def setCurrentText(self, text):
		'''Sets the text for the current index.

		:Parameters:
			item (str) = The current item's text value.
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
			try:
				self.setCurrentText(i)
			except Exception as error:
				if i:
					print ('{}: setCurrentItem: {}'.format(__file__, error))


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

		super().showPopup()


	def hidePopup(self):
		''''''
		self.beforePopupHidden.emit()

		if not self.popupStyle=='modelView':
			self.menu_.hide()
			# self.menu_.visible=False
		else:
			super().hidePopup()


	def clear(self):
		''''''
		if not self.popupStyle=='modelView':
			self.menu_.clear()
		else:
			super().clear()


	def enterEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''

		super().enterEvent(event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		# self.hidePopup()

		super().leaveEvent(event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		if event.button()==QtCore.Qt.RightButton:
			self.ctxMenu.show()

		super().mousePressEvent(event)


	def keyPressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if event.key()==QtCore.Qt.Key_Return and not event.isAutoRepeat():
			self.returnPressed.emit()
			self.setEditable(False)

		super().keyPressEvent(event)


	def showEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		if self.ctxMenu.containsMenuItems:
			# self.ctxMenu.setTitle(self.itemText(0))
			self.setTextOverlay('⧉', alignment='AlignRight')
			self.setItemText(0, self.itemText(0)) #set text: comboBox

		super().showEvent(event)


	def eventFilter(self, widget, event):
		'''Event filter for the standard view.

		QtCore.QEvent.Show, Hide, FocusIn, FocusOut, FocusAboutToChange
		'''
		# if not (str(event.type()).split('.')[-1]) in ['QPaintEvent', 'UpdateLater', 'PolishRequest', 'Paint']: print(str(event.type())) #debugging
		if event.type()==QtCore.QEvent.Hide:
			if self.parent().__class__.__name__=='Menu':
				self.parent().hide()

		return super().eventFilter(widget, event)









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)

	w = ComboBox(popupStyle='qmenu')
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

# deprecated:

