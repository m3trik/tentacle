from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes


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


class ListWidget(QtWidgets.QListWidget, Attributes):
	'''
	'''
	def __init__(self, parent=None, **kwargs):
		QtWidgets.QListWidget.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		# self.setViewMode(QtWidgets.QListView.IconMode)
		self.clear()
		self.setAttributes(**kwargs)


	def add(self, w, **kwargs):
		'''Add items to the menu.

		kw:Parameters:
			show (bool) = show the menu.
			insertSeparator (QAction) = insert separator in front of the given action.
		:Return:
			the added item object.

		ex.call: menu().add(w='QAction', setText='', insertSeparator=True)
		'''
		#get the widget
		try:
			w = getattr(QtWidgets, w)(self) #ex. QtWidgets.QAction(self) object from string.
		except:
			if callable(w):
				w = w() #ex. QtWidgets.QAction(self) object.

		self.setAttributes(w, **kwargs) #set any additional given keyword args for the widget.

		type_ = w.__class__.__name__

		if w=='':
			self.addItem(w)

		elif type_=='QAction': #
			self.addAction(w)

		elif w is not self:
			wItem = QtWidgets.QListWidgetItem(self)
			self.setItemWidget(wItem, w)
			self.addItem(wItem)

		return w









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)

	w = ListWidget()
	w.add('QPushButton', setObjectName='b001', setText='Button1')
	w.add('QPushButton', setObjectName='b002', setText='Button2', setIcon=QtGui.QIcon())
	w.add('QLabel', setObjectName='lbl001', setText='Label1')

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

# deprecated ---------------------


		# self.itemList=[] #list of all current listWidget items.

	


	# @property
	# def items(self):
	# 	'''

	# 	'''
	# 	return self.itemList



	# def clear(self):
	# 	'''

	# 	'''
	# 	self.itemList=[]

	# 	return QtWidgets.QListWidget.clear(self)



# def setAttributes(self, item=None, attributes=None, order=['globalPos'], **kwargs):
	# 	'''
	# 	Works with attributes passed in as a dict or kwargs.
	# 	If attributes are passed in as a dict, kwargs are ignored.
	# 	:Parameters:
	# 		item (obj) = listWidget item.
	# 		attributes (dict) = keyword attributes and their corresponding values.
	# 		order (list) = list of string keywords. ie. ['move', 'show']. attributes in this list will be set last, in order of the list. an example would be setting move positions after setting resize arguments.
	# 	kw:Parameters:
	# 		set any keyword arguments.
	# 	'''
	# 	if not attributes:
	# 		attributes = kwargs

	# 	for k in order: #re-order the attributes (with contents of 'order' list last).
	# 		v = attributes.pop(k, None)
	# 		if v:
	# 			from collections import OrderedDict
	# 			attributes = OrderedDict(attributes)
	# 			attributes[k] = v

	# 	for attr, value in attributes.items():
	# 		try:
	# 			if item:
	# 				getattr(item, attr)(value)
	# 			else:
	# 				getattr(self, attr)(value)

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
	# 		globalPos (QPoint) = move to given global location and center.
	# 	'''
	# 	if attr=='globalPos':
	# 		self.move(self.mapFromGlobal(value - self.rect().center())) #move and center






	# def mouseMoveEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''

	# 	return QtWidgets.QListWidget.mouseMoveEvent(self, event)



	# def showEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''

	# 	return QtWidgets.QListWidget.showEvent(self, event)



	# def enterEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''

	# 	return QtWidgets.QListWidget.enterEvent(self, event)



	# def leaveEvent(self, event):
	# 	'''
	# 	:Parameters:
	# 		event = <QEvent>
	# 	'''

	# 	return QtWidgets.QListWidget.leaveEvent(self, event)