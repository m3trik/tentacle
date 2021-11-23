# !/usr/bin/python
# coding=utf-8
import os.path

from PySide2 import QtCore, QtGui, QtWidgets



class EventFactoryFilter(QtCore.QObject):
	'''Event filter for dynamic ui objects.

	:Parameters:
		tcl (obj) = tcl widget instance.
	'''
	_mouseOver=[] #list of widgets currently under the mouse cursor.
	_mouseGrabber=None
	_mouseHover = QtCore.Signal(bool)
	_mousePressPos = QtCore.QPoint()

	enterEvent_ = QtCore.QEvent(QtCore.QEvent.Enter)
	leaveEvent_ = QtCore.QEvent(QtCore.QEvent.Leave)


	def __init__(self, tcl):
		super(EventFactoryFilter, self).__init__(tcl)

		self.tcl = tcl
		self.tcl.sb.setClassInstance(self)

		self.widgetTypes = [ #install an event filter for the given widget types.
				'QWidget', 
				'QAction', 
				'QLabel', 
				'QPushButton', 
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
				'QMenu',
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


	def addWidgets(self, uiName, widgets):
		'''Convenience method for adding additional widgets to the switchboard dict,
		and initializing them by setting connections, event filters, and stylesheets.

		:Parameters:
			uiName (str) = name of the parent ui.
			widgets (obj)(list) = widget or list of widgets.
		'''
		widgets = self.tcl.sb.list_(widgets) #if 'widgets' isn't a list, convert it to one.

		self.tcl.sb.addWidgets(uiName, widgets) #add the widgets to the switchboard dict.
		self.tcl.sb.connectSlots(uiName, widgets)
		self.initWidgets(uiName, widgets) #initialize the widget to set things like the event filter and styleSheet.


	def initWidgets(self, uiName, widgets=None):
		'''Set Initial widget states.

		:Parameters:
			uiName (str) = ui name.
			widgets (str)(list) = <QWidgets> if no arg is given, the operation will be performed on all widgets of the given ui name.
		'''
		if uiName is None:
			uiName = self.tcl.sb.getUiName()
		if widgets is None:
			widgets = self.tcl.sb.getWidget(ui=uiName) #get all widgets for the given ui name.
		widgets = self.tcl.sb.list_(widgets) #if 'widgets' isn't a list, convert it to one.

		for widget in widgets: #get all widgets for the given ui name.
			widgetName = self.tcl.sb.getWidgetName(widget, uiName)
			widgetType = self.tcl.sb.getWidgetType(widget, uiName) #get the class type as string.
			derivedType = self.tcl.sb.getDerivedType(widget, uiName) #get the derived class type as string.
			ui = self.tcl.sb.getUi(uiName)
			uiLevel = self.tcl.sb.getUiLevel(uiName)
			method = self.tcl.sb.getMethod(uiName, widgetName)

			self.tcl.setStyleSheet_(widget, uiName)

			if derivedType in self.widgetTypes:
				widget.installEventFilter(self)
				# print (widgetName if widgetName else widget)

				if widgetType in ('PushButton', 'PushButtonDraggable', 'ComboBox', 'TreeWidgetExpandableList', 'LineEdit'): #widget types to initialize menus for.
					try: #if callable(method): #attempt to clear any current menu items.
						method.clear()
					except AttributeError as error:
						pass # print (__name__, error)

					try: #attempt to construct the widget's contextMenu.
						method('setMenu')
					except Exception as error:
						pass # print (__name__, widgetName, error)

					try: #add the child widgets of popup menus.
						self.addWidgets(uiName, widget.menu_.childWidgets)
						self.addWidgets(uiName, widget.contextMenu.childWidgets)
					except AttributeError as error:
						pass # print (__name__, error)

				if derivedType in ('QPushButton', 'QLabel'): #widget types to resize and center.
					if uiLevel<3:
						EventFactoryFilter.resizeAndCenterWidget(widget)

				elif derivedType=='QWidget': #widget types to set an initial state as hidden.
					if self.tcl.sb.prefix(widget, 'w') and uiLevel==1: #prefix returns True if widgetName startswith the given prefix, and is followed by three integers.
						widget.setVisible(False)


	def mouseTracking(self, uiName):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Used to trigger widget evemts while in the mouse button down state.

		:Parameters:
			uiName (str) = ui name.
		'''
		# print([i.objectName() for i in self.tcl.sb.getWidget(ui=uiName) if uiName=='cameras']), '---'
		ui = self.tcl.sb.getUi(uiName)
		widgetsUnderMouse=[] #list of widgets currently under the mouse cursor and their parents. in hierarchical order. ie. [[<widgets.pushButton.PushButton object at 0x00000000045F6948>, <PySide2.QtWidgets.QMainWindow object at 0x00000000045AA8C8>, <__main__.Main_max object at 0x000000000361F508>, <PySide2.QtWidgets.QWidget object at 0x00000000036317C8>]]
		for widget in self.tcl.sb.getWidget(ui=uiName): #get all widgets from the current ui.
			# if hasattr(widget, 'rect'): #ignore any widgets not having the 'rect' attribute.
				try:
					widgetName = self.tcl.sb.getWidgetName(widget, uiName)
				except KeyError:
					self.addWidgets(uiName, widget) #initialize the widget to set things like the event filter and styleSheet.
					widgetName = self.tcl.sb.getWidgetName(widget, uiName)

				try:
					if widget.rect().contains(widget.mapFromGlobal(QtGui.QCursor.pos())): #if mouse over widget:
						# print (widget.objectName(), 'mouseTracking')
						if not widget in self._mouseOver: #if widget is already in the mouseOver list, no need to re-process the events.
							QtWidgets.QApplication.sendEvent(widget, self.enterEvent_)
							self._mouseOver.append(widget)

							if not widgetName=='mainWindow':
								if widget.underMouse() and widget.isEnabled():
									parentWidgets = self.tcl.sb.getParentWidgets(widget)
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
			self.uiName = self.tcl.sb.getUiNameFromWidget(self.widget) #get the name of the ui containing the given widget.
			# if not self.uiName: print('Error: childEvents.eventFilter: getNameFrom(widget): {0} Failed on Event: {1} #'.format(self.widget.objectName(), str(event.type()).split('.')[-1]))
			self.widgetName = self.tcl.sb.getWidgetName(self.widget, self.uiName) #get the stored objectName string (pyside objectName() returns unicode).
			self.widgetType = self.tcl.sb.getWidgetType(self.widget, self.uiName)
			self.derivedType = self.tcl.sb.getDerivedType(self.widget, self.uiName)
			self.ui = self.tcl.sb.getUi(self.uiName)
			self.uiLevel = self.tcl.sb.getUiLevel(self.uiName)
			self.method = self.tcl.sb.getMethod(self.uiName, self.widgetName)

			# print(self.uiName, self.widgetType, self.widgetName, event.__class__.__name__, eventName)

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
					self.tcl.sb.addWidget(self.uiName, self.widget)
					self.tcl.sb.getMethod(self.uiName, self.widgetName)()
				except (AttributeError, NameError, TypeError) as error:
					print(self.__class__.__name__, 'Call to {}.{} failed:'.format(self.uiName, self.widgetName), error)

			if self.widgetType=='TreeWidgetExpandableList':
				self.addWidgets(self.uiName, self.widget.newWidgets) #removeWidgets=self.widget._gcWidgets.keys()


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
			if self.tcl.sb.prefix(self.widget, 'w'):
				self.widget.setVisible(True) #set visibility

		elif self.derivedType=='QPushButton':
			if self.tcl.sb.prefix(self.widget, 'i'): #set the stacked widget.
				submenu = self.tcl.sb.getUiName(self.widget.whatsThis(), level=2)
				if submenu and not self.uiName==submenu: #do not reopen the submenu if it is already open.
					self.uiName = self.tcl.setSubUi(self.widget, submenu)

			elif self.widgetName=='return_area':
				self.tcl.setPrevUi()

		if self.tcl.sb.prefix(self.widget, 'chk'):
			if self.tcl.sb.getUiLevel(self.uiName)==2: #if submenu:
				self.widget.click()


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mouseHover.emit(False)

		if self.widgetType=='QWidget':
			if self.tcl.sb.prefix(self.widget, 'w'):
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
			if self.derivedType=='QPushButton':
				if self.tcl.sb.prefix(self.widget, 'i'): #ie. 'i012'
					ui = self.tcl.setUi(self.widget.whatsThis()) #switch the stacked layout to the given ui.

				elif self.tcl.sb.prefix(self.widget, 'v'):
					if self.uiName=='cameras':
						self.tcl.sb.prevCamera(add=self.method)
					#send click signal on mouseRelease.
					self.widget.click()

				elif self.tcl.sb.prefix(self.widget, ['b','tb']):
					if self.tcl.sb.getUiLevel(self.uiName)==2: #if submenu:
						self.widget.click()
					#add the buttons command info to the prevCommand list.
					self.tcl.sb.prevCommand(add=self.method)








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:

# self.widgetClasses = [getattr(QtWidgets, t) for t in self.widgetTypes]

			#finally, add any of the widget's children.
			# exclude = ['TreeWidgetExpandableList'] #'QObject', 'QBoxLayout', 'QFrame', 'QAbstractItemView', 'QHeaderView', 'QItemSelectionModel', 'QItemDelegate', 'QScrollBar', 'QScrollArea', 'QValidator', 'QStyledItemDelegate', 'QPropertyAnimation'] #, 'QAction', 'QWidgetAction'
			# for c in widget.children(): #from itertools import chain; list(chain(*[widget.findChildren(t) for t in self.widgetClasses])) #get children and flatten list with itertools chain. # children = [i for sublist in [widget.findChildren(t) for t in self.widgetClasses] for i in sublist]
			# 	typ = self.tcl.sb._getDerivedType(c) #get the derived type without adding.
			# 	if typ in self.widgetTypes and not typ in exclude:
			# 		if c not in widgets:
			# 			self.addWidgets(uiName, c) 
			# print(uiName, [w.objectName() for w in widget.children() if w not in widgets and not widgetType in exclude])


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
