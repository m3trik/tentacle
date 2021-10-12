# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

import os.path



class EventFactoryFilter(QtCore.QObject):
	'''Event filter for dynamic ui objects.

	:Parameters:
		parent (obj) = parent widget.
	'''
	_mouseOver=[] #list of widgets currently under the mouse cursor.
	_mouseGrabber=None
	_mouseHover = QtCore.Signal(bool)
	_mousePressPos = QtCore.QPoint()

	enterEvent_ = QtCore.QEvent(QtCore.QEvent.Enter)
	leaveEvent_ = QtCore.QEvent(QtCore.QEvent.Leave)


	def __init__(self, parent):
		super(EventFactoryFilter, self).__init__(parent)

		self.parent = parent
		self.sb = self.parent.sb
		self.sb.setClassInstance(self)

		self.widgetTypes = [ #install an event filter on the given widget types.
				'QWidget', 
				'QAction', 
				'QLabel', 
				'QPushButton', 
				'QToolButton', 
				'QListWidget', 
				'QTreeWidget', 
				'QComboBox', 
				'QSpinBox',
				'QDoubleSpinBox',
				'QCheckBox',
				'QRadioButton',
				'QLineEdit',
				'QTextEdit',
				'QProgressBar',
		]

		self.eventTypes = [ #the types of events to be handled here.
				'showEvent',
				'hideEvent',
				'enterEvent',
				'leaveEvent',
				'mousePressEvent',
				'mouseMoveEvent',
				'mouseReleaseEvent',
		]


	def initWidgets(self, name, widgets=None):
		'''Set Initial widget states.

		:Parameters:
			name (str) = ui name.
			widgets (str)(list) = <QWidgets> if no arg is given, the operation will be performed on all widgets of the given ui name.
		'''
		if widgets is None:
			widgets = self.sb.getWidget(ui=name) #get all widgets for the given ui name.
		widgets = self.sb.list(widgets) #if 'widgets' isn't a list, convert it to one.

		for widget in widgets: #get all widgets for the given ui name.
			widgetName = self.sb.getWidgetName(widget, name)
			widgetType = self.sb.getWidgetType(widget, name) #get the class type as string.
			derivedType = self.sb.getDerivedType(widget, name) #get the derived class type as string.
			ui = self.sb.getUi(name)
			uiLevel = self.sb.getUiLevel(name)
			method = self.sb.getMethod(name, widgetName)

			self.parent.style.setStyleSheet(name, widget)

			if derivedType in self.widgetTypes:
				widget.installEventFilter(self)
				# print (widgetName if widgetName else widget)

				if widgetType in ('ToolButton', 'PushButtonDraggable', 'ComboBox', 'TreeWidgetExpandableList', 'LineEdit'): #widget types to initialize menus|contextMenu's for.
					if callable(method):
						try: #attempt to clear any current menu items.
							method.clear()
						except (AttributeError):
							pass
						method('setMenu')

				if derivedType in ('QPushButton', 'QToolButton', 'QLabel'): #widget types to resize and center.
					if uiLevel<3:
						EventFactoryFilter.resizeAndCenterWidget(widget)

				elif derivedType=='QWidget': #widget types to set an initial state as hidden.
					if self.sb.prefix(widget, 'w') and uiLevel==1: #prefix returns True if widgetName startswith the given prefix, and is followed by three integers.
						widget.setVisible(False)

			#finally, add any of the widget's children.
			exclude = ['TreeWidgetExpandableList'] #'QObject', 'QBoxLayout', 'QFrame', 'QAbstractItemView', 'QHeaderView', 'QItemSelectionModel', 'QItemDelegate', 'QScrollBar', 'QScrollArea', 'QValidator', 'QStyledItemDelegate', 'QPropertyAnimation'] #, 'QAction', 'QWidgetAction'
			[self.addWidgets(name, w) for w in widget.children() if w not in widgets and not widgetType in exclude]
			# print(name, [w.objectName() for w in widget.children() if w not in widgets and not widgetType in exclude])


	def addWidgets(self, name, widgets):
		'''Convenience method for adding additional widgets to the switchboard dict,
		and initializing them by setting connections, event filters, and stylesheets.

		:Parameters:
			name (str) = name of the parent ui.
			widgets (obj)(list) = widget or list of widgets.
		'''
		widgets = self.sb.list(widgets) #if 'widgets' isn't a list, convert it to one.

		self.sb.addWidgets(name, widgets) #add the widgets to the switchboard dict.
		self.sb.connectSlots(name, widgets)
		self.initWidgets(name, widgets) #initialize the widget to set things like the event filter and styleSheet.


	def mouseTracking(self, name):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Used to trigger widget evemts while in the mouse button down state.

		:Parameters:
			name (str) = ui name.
		'''
		# print([i.objectName() for i in self.sb.getWidget(ui=name) if name=='cameras']), '---'
		ui = self.sb.getUi(name)
		widgetsUnderMouse=[] #list of widgets currently under the mouse cursor and their parents. in hierarchical order. ie. [[<widgets.pushButton.PushButton object at 0x00000000045F6948>, <PySide2.QtWidgets.QMainWindow object at 0x00000000045AA8C8>, <__main__.Main_max object at 0x000000000361F508>, <PySide2.QtWidgets.QWidget object at 0x00000000036317C8>]]
		for widget in self.sb.getWidget(ui=name): #get all widgets from the current ui.
			# if hasattr(widget, 'rect'): #ignore any widgets not having the 'rect' attribute.
				try:
					widgetName = self.sb.getWidgetName(widget, name)
				except KeyError:
					self.addWidgets(name, widget) #initialize the widget to set things like the event filter and styleSheet.
					widgetName = self.sb.getWidgetName(widget, name)

				try:
					if widget.rect().contains(widget.mapFromGlobal(QtGui.QCursor.pos())): #if mouse over widget:
						# print (widget.objectName(), 'mouseTracking')
						if not widget in self._mouseOver: #if widget is already in the mouseOver list, no need to re-process the events.
							QtWidgets.QApplication.sendEvent(widget, self.enterEvent_)
							self._mouseOver.append(widget)

							if not widgetName=='mainWindow':
								if widget.underMouse() and widget.isEnabled():
									parentWidgets = self.sb.getParentWidgets(widget)
									widgetsUnderMouse.append(parentWidgets)
					else:
						if widget in self._mouseOver: #if widget is in the mouseOver list, but the mouse is no longer over the widget:
							QtWidgets.QApplication.sendEvent(widget, self.leaveEvent_)
							self._mouseOver.remove(widget)
							if ui.mainWindow.isVisible():
								ui.mainWindow.grabMouse()
								self._mouseGrabber = ui.mainWindow
				except (AttributeError, TypeError) as e:
					pass #print('# Error: {}: mouseTracking: {} #'.format(os.path.splitext(os.path.basename(__file__))[0], e))


		widgetsUnderMouse.sort(key=len) #sort 'widgetsUnderMouse' by ascending length so that lowest level child widgets get grabMouse last.
		for widgetList in widgetsUnderMouse:
			widget = widgetList[0]
			widget.grabMouse() #set widget to receive mouse events.
			self._mouseGrabber = widget
			break
			# print (widget.objectName())
			# print('grab:', widget.mouseGrabber().objectName(), '(childEvents)')


	@staticmethod
	def resizeAndCenterWidget(widget, paddingX=30, paddingY=6):
		'''Adjust the given widget's size to fit contents and re-center.

		:Parameters:
			widget = <widget object> - widget to resize.
			paddingX (int) = additional width to be applied.
			paddingY (int) = additional height to be applied.
		'''
		p1 = widget.rect().center()
		widget.resize(widget.sizeHint().width()+paddingX, widget.sizeHint().height()+paddingY)
		p2 = widget.rect().center()
		diff = p1-p2
		widget.move(widget.pos()+diff)


	@staticmethod
	def createEventName(event):
		'''Get an event method name string from a given event.
		ie. 'enterEvent' from QtCore.QEvent.Type.Enter,
		ie. 'mousePressEvent' from QtCore.QEvent.Type.MouseButtonPress

		:Parameters:
			event = <QEvent>
		:Return:
			'string' - formatted method name
		'''
		e = str(event.type()).split('.')[-1] #get the event name ie. 'Enter' from QtCore.QEvent.Type.Enter
		e = e[0].lower() + e[1:] #lowercase the first letter.
		e = e.replace('Button', '') #remove 'Button' if it exists.
		return e + 'Event' #add trailing 'Event'


	def eventFilter(self, widget, event):
		'''Forward widget events to event handlers.
		For any event type, the eventfilter will try to connect to a corresponding method derived
		from the event type string.  ie. self.enterEvent(event) from 'QtCore.QEvent.Type.Enter'
		This allows for forwarding of all events without each having to be explicity stated.

		:Parameters:
			widget = <QWidget>
			event = <QEvent>
		'''
		result = False #default to False (event not handled)

		eventName = EventFactoryFilter.createEventName(event) #get 'mousePressEvent' from <QEvent>
		if eventName in self.eventTypes: #handle only events listed in 'eventTypes'

			self.widget = widget
			self.name = self.sb.getUiNameFromWidget(self.widget) #get the name of the ui containing the given widget.
			# if not self.name: print('Error: childEvents.eventFilter: getNameFrom(widget): {0} Failed on Event: {1} #'.format(self.widget.objectName(), str(event.type()).split('.')[-1]))
			self.widgetName = self.sb.getWidgetName(self.widget, self.name) #get the stored objectName string (pyside objectName() returns unicode).
			self.widgetType = self.sb.getWidgetType(self.widget, self.name)
			self.derivedType = self.sb.getDerivedType(self.widget, self.name)
			self.ui = self.sb.getUi(self.name)
			self.uiLevel = self.sb.getUiLevel(self.name)
			self.method = self.sb.getMethod(self.name, self.widgetName)

			# print(self.name, self.widgetType, self.widgetName, event.__class__.__name__, eventName)

			if hasattr(self, eventName):
				getattr(self, eventName)(event) #handle the event locally. #ie. self.enterEvent(event)
				result = super(EventFactoryFilter, self).eventFilter(widget, event)

		return result


	# ------------------------------------------------
	# Events
	# ------------------------------------------------
	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.widgetName=='mainWindow':
			self.widget.activateWindow()

		elif self.widgetName=='info':
			EventFactoryFilter.resizeAndCenterWidget(self.widget)

		if self.widgetType in ('ComboBox', 'TreeWidgetExpandableList'):
			try: #call the class method associated with the current widget.
				self.method()
			except:
				try: #if call fails (ie. NoneType error); try adding the widget, and call again.
					self.sb.addWidget(self.name, self.widget)
					self.sb.getMethod(self.name, self.widgetName)()
				except (AttributeError, NameError, TypeError) as error:
					print(self.__class__.__name__, 'Call to {}.{} failed:'.format(self.name, self.widgetName), error)

			if self.widgetType=='TreeWidgetExpandableList':
				self.addWidgets(self.name, self.widget.newWidgets) #removeWidgets=self.widget._gcWidgets.keys()


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.widgetName=='mainWindow':
			if self._mouseGrabber:
				self._mouseGrabber.releaseMouse()
				self._mouseGrabber = None


	def enterEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mouseHover.emit(True)

		if self.widgetType=='QWidget':
			if self.sb.prefix(self.widget, 'w'):
				self.widget.setVisible(True) #set visibility

		elif self.derivedType=='QPushButton':
			if self.sb.prefix(self.widget, 'i'): #set the stacked widget.
				submenu = self.sb.getUiName(self.widget.whatsThis(), level=2)
				if submenu and not self.name==submenu: #do not reopen the submenu if it is already open.
					self.name = self.parent.setSubUi(self.widget, submenu)

			elif self.widgetName=='return_area':
				self.parent.setPrevUi()

		if self.sb.prefix(self.widget, 'chk'):
			if self.sb.getUiLevel(self.name)==2: #if submenu:
				self.widget.click()


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mouseHover.emit(False)

		if self.widgetType=='QWidget':
			if self.sb.prefix(self.widget, 'w'):
				self.widget.setVisible(False) #set visibility


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mousePressPos = event.globalPos() #mouse positon at press
		self.__mouseMovePos = event.globalPos() #mouse move position from last press


	def mouseMoveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if hasattr(self, '__mouseMovePos'):
			globalPos = event.globalPos()
			diff = globalPos -self.__mouseMovePos
			self.__mouseMovePos = globalPos


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.widget.underMouse(): #if self.widget.rect().contains(event.pos()): #if mouse over widget:
			if self.derivedType=='QPushButton' or self.derivedType=='QToolButton':
				if self.sb.prefix(self.widget, 'i'): #ie. 'i012'
					ui = self.parent.setUi(self.widget.whatsThis()) #switch the stacked layout to the given ui.

				elif self.sb.prefix(self.widget, 'v'):
					if self.name=='cameras':
						self.sb.prevCamera(add=self.method)
					#send click signal on mouseRelease.
					self.widget.click()

				elif self.sb.prefix(self.widget, ['b','tb']):
					if self.sb.getUiLevel(self.name)==2: #if submenu:
						self.widget.click()
					#add the buttons command info to the prevCommand list.
					self.sb.prevCommand(add=self.method)








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:

# if event.type()==QtCore.QEvent.Destroy: return result

# self.eventTypes = [ #the types of events to be handled here.
# 				'QEvent',
# 				'QChildEvent',
# 				'QResizeEvent',
# 				'QShowEvent',
# 				'QHideEvent',
# 				'QEnterEvent',
# 				'QLeaveEvent',
# 				'QKeyEvent',
# 				'QMouseEvent',
# 				'QMoveEvent',
# 				'QHoverEvent',
# 				'QContextMenuEvent',
# 				'QDragEvent',
# 				'QDropEvent',
# 		]
