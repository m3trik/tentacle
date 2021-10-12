# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtCore, QtGui

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


class WidgetMultiWidget(QtWidgets.QWidget, Attributes):
	'''
	:Parameters:
		layoutType (str) = valid values are: 'QBoxLayout', 'QHBoxLayout', 'QVBoxLayout' default is: 'QHBoxLayout'
	'''
	enterEvent_	= QtCore.QEvent(QtCore.QEvent.Enter)
	leaveEvent_	= QtCore.QEvent(QtCore.QEvent.Leave)
	hoverEnter_ = QtCore.QEvent(QtCore.QEvent.HoverEnter)
	hoverMove_ = QtCore.QEvent(QtCore.QEvent.HoverMove)
	hoverLeave_ = QtCore.QEvent(QtCore.QEvent.HoverLeave)

	def __init__(self, parent=None, layoutType='QHBoxLayout', **kwargs):
		super().__init__(parent)

		self.layoutType = layoutType
		self._mouseGrabber=None
		# self.setMouseTracking(True)
		self.setAttributes(kwargs) #set any additional given keyword args for the widget.


	@property
	def row(self):
		'''Get the row from the layout.
		'''
		if not hasattr(self, '_row'):
			self._row = getattr(QtWidgets, self.layoutType)(self)
			self._row.setSpacing(0)
			# self.row.addStretch(0)
			self._row.setContentsMargins(0,0,0,0) #self.row.setMargin(0)

		return self._row


	def add(self, w, **kwargs):
		'''Add items to the Layout.

		:Parameters:
			widget (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel

		kw:Parameters:
			insertSeparator_ (bool) = insert a separator before the widget.
			setLayoutDirection_ (str) = ie. 'LeftToRight'
			setAlignment_ (str) = ie. 'AlignVCenter'
			setButtonSymbols_ (str) = ie. 'PlusMinus'
			setMinMax_ (str) = Set the min, max, and step values with a string. ie. '1-100 step.1'

		:Return:
 			the added widget.

		ex.call:
		w.add('QCheckBox', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
		'''
		#get the widget
		try:
			w = getattr(QtWidgets, w)(self) #ie. QtWidgets.QAction(self) object from string.
		except:
			if callable(w):
				w = w(self) #ie. QtWidgets.QAction(self) object.

		self.setAttributes(kwargs, w) #set any additional given keyword args for the widget.

		# type_ = w.__class__.__name__

		self.row.addWidget(w)

		w.installEventFilter(self)

		w.setMinimumSize(w.sizeHint().width(), 20) #self.parent().minimumSizeHint().height()+1) #set child widget height to that of the toolbutton]

		setattr(self, w.objectName(), w) #add the widget's objectName as a QMenu attribute.

		return w


	def eventFilter(self, widget, event):
		'''
		'''
		# if not (str(event.type()).split('.')[-1]) in ['QPaintEvent', 'UpdateLater', 'PolishRequest', 'Paint']: print(str(event.type())) #debugging
		# if event.type()==QtCore.QEvent.HoverEnter:
		# 	print ('hoverEnter_')

		if event.type()==QtCore.QEvent.HoverMove:
			try:
				w = next(w for w in self.children_() if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos())) and w.isVisible())
			except StopIteration:
				return QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.hoverLeave_)

			if not w is self._mouseGrabber:
				if self._mouseGrabber is not None:
					QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.hoverLeave_)
					QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.leaveEvent_)
				if not w is self.mouseGrabber():
					w.grabMouse()
				self._mouseGrabber = w
				QtWidgets.QApplication.sendEvent(w, self.hoverEnter_)
				QtWidgets.QApplication.sendEvent(w, self.enterEvent_)

		if event.type()==QtCore.QEvent.HoverLeave:
			if not __name__=='__main__':
				if self.window().isVisible():
					self.window().grabMouse()

		if event.type()==QtCore.QEvent.MouseButtonRelease:
			if widget.rect().contains(widget.mapFromGlobal(QtGui.QCursor.pos())):
				next(w.hide() for w in QtWidgets.QApplication.topLevelWindows() if w.isVisible() and not 'QMenu' in w.objectName()) #hide all windowshttps://www.commondreams.org/news/2020/04/21/warnings-suspension-democracy-new-york-state-officials-weigh-removing-sanders

		return super(WidgetMultiWidget, self).eventFilter(widget, event)


	def enterEvent(self, event):
		'''
		'''
		self._mouseGrabber = self.mouseGrabber()
		
		return QtWidgets.QWidget.enterEvent(self, event)


	def mouseMoveEvent(self, event):
		'''
		'''
		for w in self.children_():
			if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos())) and w.isVisible():
				w.grabMouse()

		return QtWidgets.QWidget.mouseMoveEvent(self, event)


	def leaveEvent(self, event):
		'''
		'''
		QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.hoverLeave_)
		if self._mouseGrabber is not self:
			QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.leaveEvent_)
		
		return QtWidgets.QWidget.leaveEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self.resize(self.sizeHint().width(), self.sizeHint().height())

		return QtWidgets.QWidget.showEvent(self, event)


	def children_(self, index=None, include=[], exclude=['QBoxLayout', 'QHBoxLayout', 'QVBoxLayout']):
		'''Get a list of the menu's child objects, excluding those types listed in 'exclude'.

		:Parameters:
			index (int) = return the child widget at the given index.
			exclude (list) = Widget types to exclude from the returned results.
			include (list) = Widget types to include in the returned results. All others will be omitted. Exclude takes dominance over include. Meaning, if a widget is both in the exclude and include lists, it will be excluded.

		:Return:
			(obj)(list) child widgets or child widget at given index.
		'''
		children = [i for i in self.children() 
				if i.__class__.__name__ not in exclude 
				and (i.__class__.__name__ in include if include else i.__class__.__name__ not in include)]

		if index is not None:
			try:
				children = children[index]
			except IndexError:
				children = None
		return children


	def setAsOptionBox(self, w):
		'''Set a pushbutton type widget to an option box style.

		:Parameters:
			w (obj) = QWidget

		:Return:
			(bool) True if the widget was set; else False.
		'''
		if not hasattr(w, 'setText'):
			return False

		w.setFixedWidth(w.sizeHint().height()*1.5)
		w.setFixedHeight(w.sizeHint().height()*1.6)
		w.setText('□')
		font = w.font()
		font.setPointSize(font.pointSize()*1.5)
		w.setFont(font)
		w.setContentsMargins(0,0,0,0) # widget.setStyleSheet('margin: 0px 0px 5px 0px;')
		w.setStyleSheet('QLabel {padding: 0px 0px 5px 0px;}')

		return True


	def set_by_value(self, values):
		''''''
		for v in values:
			if isinstance(v, (str)):
				self.add(QtWidgets.QLabel(v))

			elif isinstance(v, bool):
				self.add(QtWidgets.QCheckBox(), setChecked=v)

			elif isinstance(v, int):
				print (type(v))
				self.add(QtWidgets.QSpinBox(), setSpinBoxByValue=v)

			elif isinstance(v, float):
				self.add(QtWidgets.QDoubleSpinBox(v), setSpinBoxByValue=v)









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	w = WidgetMultiWidget(set_by_value=['Height', 0])
	# w.add(QtWidgets.QLabel('Height'))
	# w.add('QDoubleSpinBox')

	# w.setAsOptionBox(w.children_(index=1))
	# print(w.children_(index=0).text())

	w.show()
	sys.exit(qApp.exec_())



# --------------------------------
# Notes
# --------------------------------

# adding a Multi-Widget row to a custom tree widget:
# m = MultiWidget(['QPushButton', 'QPushButton'])
# m.children_(0).setText('ButtonText')
# m.setAsOptionBox(m.children_(1)) #set button 2 to be an option box style
# tree.add(m, 'Cameras') #add the widgets to the tree under the parent header 'Cameras'


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


# deprecated ------------------------------------------------




	# def setAttributes(self, attributes=None, w=None, order=[], **kwargs):
	# 	'''
	# 	Works with attributes passed in as a dict or kwargs.
	# 	If attributes are passed in as a dict, kwargs are ignored.

	# 	:Parameters:
	# 		attributes (dict) = keyword attributes and their corresponding values.
	# 		w (obj) = the child widget to set attributes for. (default=None)
	# 		#order (list) = list of string keywords. ie. ['move', 'show']. attributes in this list will be set last, by list order. an example would be setting move positions after setting resize arguments, or showing the widget only after other attributes have been set.
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
	# 			getattr(w, attr)(value)

	# 		except Exception as error:
	# 			if type(error)==AttributeError:
	# 				self.setCustomAttribute(w, attr, value)
	# 			else:
	# 				raise error


	# def setCustomAttribute(self, w, attr, value):
	# 	'''
	# 	Custom attributes can be set using a trailing underscore convention to differentiate them from standard attributes. ie. insertSeparator_=True

	# 	:Parameters:
	# 		w (obj) = the child widget to set attributes for.
	# 		attr (str) = custom keyword attribute.
	# 		value (str) = the value corresponding to the given attr.
	# 	'''
	# 	if attr=='':
	# 		if value=='':
	# 			pass
	# 	else:
	# 		print('Error: {} has no attribute {}'.format(action, attr))





# if not __name__=='__main__' and not hasattr(self, 'parentUiName'):
# 	p = self.parent()
# 	while not hasattr(p.window(), 'sb'):
# 		p = p.parent()

# 	self.sb = p.window().sb
# 	self.parentUiName = self.sb.getUiName()
# 	self.childEvents = self.sb.getClassInstance('EventFactoryFilter')

# 	self.childEvents.addWidgets(self.parentUiName, self.children_())

# self.resize(self.sizeHint().width(), self.sizeHint().height())