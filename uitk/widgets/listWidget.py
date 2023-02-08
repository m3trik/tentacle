# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes


class ListWidget(QtWidgets.QListWidget, Attributes):
	'''
	'''

	def __init__(self, parent=None, **kwargs):
		'''
		'''
		super().__init__(parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		# self.setViewMode(QtWidgets.QListView.IconMode)
		self.clear()
		self.setAttributes(**kwargs)


	def getItems(self):
		'''
		'''
		return [self.item(i) for i in range(self.count())]


	def getItemsByText(self, text):
		'''
		'''
		return [i for i in self.getItems() if i.text()==text]


	def getItemWidgets(self):
		'''
		'''
		return [self.itemWidget(self.item(i)) for i in range(self.count())]


	def getItemWidgetsByText(self, text):
		'''
		'''
		return [i for i in self.getItemWidgets() if hasattr(i, 'text') and i.text()==text]


	def addItem(self, i):
		'''
		'''
		self.add(i)


	def add(self, w, **kwargs):
		'''Add items to the menu.

		:Parameters:
			w () = 
			kwargs:
				show (bool): show the menu.
				insertSeparator (QAction) = insert separator in front of the given action.
		:Return:
			the added item object.

		ex.call: menu().add(w='QAction', setText='', insertSeparator=True)
		'''
		try: #get the widget from string class name.
			w = getattr(QtWidgets, w)(self) #ex. QtWidgets.QAction(self) object from string.
		except: #if w is a widget object instead of string.
			if callable(w):
				w = w() #ex. QtWidgets.QAction(self) object.

		typ = w.__class__.__name__

		# if typ=='QListWidgetItem':
			# super().addItem(w)

		if w is not self:
			if typ=='str': #if 'w' is still a string; create a label and use the str value as the label's text.
				lbl = QtWidgets.QLabel(self)
				lbl.setText(w)
				w = lbl
			wItem = QtWidgets.QListWidgetItem(self)
			self.setItemWidget(wItem, w)
			super().addItem(wItem)

		w.__class__.list = property( #add an expandable list to the widget.
			lambda w: w._list if hasattr(w, '_list') else self._addList(w)
		)

		self.setAttributes(w, **kwargs) #set any additional given keyword args for the widget.
		self.resize(self.sizeHint().width(), self.minimumSizeHint().height())
		self.raise_()

		return w


	def _addList(self, w):
		'''Add an expanding list to the given widget.
		:Parameters:
			w (obj): 
		'''
		lw = ListWidget(self.parent(), setVisible=False, setObjectName='list')
		w._list = lw
		w._list.prevlist = self #w.parent().parent()
		w.leaveEvent = lambda event, w=w: w._list.leaveEvent(event)
		lw.leaveEvent = lambda event, lw=lw: (self._hideLists(lw)) if not lw.rect().contains(lw.mapFromGlobal(QtGui.QCursor.pos())) else None
		lw.show = lambda lw=lw: lw.__class__.show(lw) if lw.getItemWidgets() else None
		w.installEventFilter(self)
		return w._list


	def _hideLists(self, lw):
		'''Hide the given list and all previous lists in it's hierarchy.
		'''
		while hasattr(lw, 'prevlist'):
			lw.hide()
			lw = lw.prevlist


	def convert(self, items, to='QLabel', **kwargs):
		'''
		:Example: self.convert(self.getItems(), 'QPushButton') #construct the list using the existing contents.
		'''
		lst = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure 'x' is a list.

		for item in lst(items):
			i = self.indexFromItem(item).row() #get the row as an int from the items QModelIndex.
			item = self.takeItem(i)
			self.add(to, setText=item.text(), **kwargs)


	def eventFilter(self, w, event):
		'''
		'''
		if event.type()==QtCore.QEvent.Enter:
			print(event.type(), w)
			try:
				pos = w.parent().parent().parent().mapFromGlobal(w.mapToGlobal(w.rect().topRight()))
				w.list.move(pos)
				w.list.show()

			except AttributeError as error:
				pass

		if event.type()==QtCore.QEvent.MouseButtonRelease:
			if QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())==w:
			# if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos())):
				try:
					self.itemClicked.emit(w)
				except AttributeError as error:
					pass

		if event.type()==QtCore.QEvent.Leave:
			print ('ef_leaveEvent')
			self.releaseMouse()

		return super().eventFilter(w, event)


	def showEvent(self, event):
		'''
		'''
		# for i in self.getItems():
		# 	self.add(i)


	def leaveEvent(self, event):
		'''
		'''
		print ('leaveEvent')
		self.releaseMouse()

# -----------------------------------------------------------------------------









# -----------------------------------------------------------------------------

if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	window = QtWidgets.QWidget()
	lw = ListWidget(window)
	w1 = lw.add('QPushButton', setObjectName='b001', setText='Button 1')
	w1.list.add('list A')
	w2 = lw.add('QPushButton', setObjectName='b002', setText='Button 2')
	w3 = w2.list.add('List B')
	w3.list.add('QPushButton', setObjectName='b004', setText='Button 4')
	lw.add('QPushButton', setObjectName='b003', setText='Button 3')

	print (lw.getItems())
	print (lw.getItemWidgets())

	window.resize(765, 255)
	window.show()
	sys.exit(app.exec_())


# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------

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

# deprecated ---------------------


