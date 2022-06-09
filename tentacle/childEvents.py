# !/usr/bin/python
# coding=utf-8
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
				'keyPressEvent',
				'keyReleaseEvent',
		]


	def initWidgets(self, ui, widgets=None):
		'''Set Initial widget states.

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
			widgets (str)(list) = <QWidgets> if no arg is given, the operation will be performed on all widgets of the given ui name.
		'''
		uiName = self.tcl.sb.getUiName(ui)

		if widgets is None:
			widgets = self.tcl.sb.widgets(uiName) #get all widgets for the given ui.

		for widget in self.tcl.sb.list_(widgets): #if 'widgets' isn't a list, convert it to one.
			widgetName = self.tcl.sb.getWidgetName(widget, uiName)
			widgetType = self.tcl.sb.getWidgetType(widget, uiName) #get the class type as string.
			derivedType = self.tcl.sb.getDerivedType(widget, uiName) #get the derived class type as string.
			ui = self.tcl.sb.getUi(uiName)
			uiLevel = self.tcl.sb.getUiLevel(uiName)
			method = self.tcl.sb.getMethod(uiName, widgetName)

			#set stylesheet
			if uiLevel==2 and not self.tcl.sb.prefix(widget, 'i'): #if submenu and objectName doesn't start with 'i':
				self.tcl.sb.setStyleSheet_(widget, style='dark', hideMenuButton=True, backgroundOpacity=0)

			elif uiLevel>2: #main menus
				self.tcl.sb.setStyleSheet_(widget, style='dark', backgroundOpacity=0)

			else:
				self.tcl.sb.setStyleSheet_(widget, backgroundOpacity=0)


			if derivedType in self.widgetTypes:
				# print (widgetName if widgetName else widget)
				if uiLevel<3 or widgetName=='mainWindow':
					widget.installEventFilter(self)

				try: #add the child widgets of popup menus.
					self.initWidgets(uiName, widget.menu_.childWidgets) #initialize the widget to set things like the event filter and styleSheet.
					self.tcl.sb.connectSlots(uiName, widget.menu_.childWidgets)

					self.initWidgets(uiName, widget.contextMenu.childWidgets)
					self.tcl.sb.connectSlots(uiName, widget.contextMenu.childWidgets)
				except AttributeError as error:
					pass; #print ("# Error: {}.EventFactoryFilter.initWidgets({}, {}): {}. #".format(__name__, uiName, widgetName, error))

				if derivedType in ('QPushButton', 'QLabel'): #widget types to resize and center.
					if uiLevel<3:
						EventFactoryFilter.resizeAndCenterWidget(widget)

				elif derivedType=='QWidget': #widget types to set an initial state as hidden.
					if self.tcl.sb.prefix(widget, 'w') and uiLevel==1: #prefix returns True if widgetName startswith the given prefix, and is followed by three integers.
						widget.setVisible(False)


	def mouseTracking(self, ui):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Used to trigger widget evemts while in the mouse button down state.

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
		'''
		uiName = self.tcl.sb.getUiName(ui)
		widgetsUnderMouse = [] #list of widgets currently under the mouse cursor and their parents. in hierarchical order. ie. [[<widgets.pushButton.PushButton object at 0x00000000045F6948>, <PySide2.QtWidgets.QMainWindow object at 0x00000000045AA8C8>, <__main__.Main_max object at 0x000000000361F508>, <PySide2.QtWidgets.QWidget object at 0x00000000036317C8>]]
		trackedWidgets = self.tcl.sb.getWidget(ui=uiName, tracked=True)

		for widget in trackedWidgets: #get all widgets from the current ui.

			try: # if hasattr(widget, 'rect'):
				widgetName = self.tcl.sb.getWidgetName(widget, uiName)
			except KeyError as error: #ignore any widgets not having the 'rect' attribute.
				self.initWidgets(uiName, widget) #initialize the widget to set things like the event filter and styleSheet.
				self.tcl.sb.connectSlots(uiName, widget)
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
						ui = self.tcl.sb.getUi(ui)
						if ui.mainWindow.isVisible():
							ui.mainWindow.grabMouse()
							self._mouseGrabber = ui.mainWindow

			except (AttributeError, TypeError) as error:
				pass; #print ('# Error: {}.EventFactoryFilter.mouseTracking: {}. #'.format(__name__, error))


		widgetsUnderMouse.sort(key=len) #sort 'widgetsUnderMouse' by ascending length so that lowest level child widgets get grabMouse last.
		for widgetList in widgetsUnderMouse:
			widget = widgetList[0]
			widget.grabMouse() #set widget to receive mouse events.
			self._mouseGrabber = widget
			break; #print (widget.objectName()); # print('grab:', widget.mouseGrabber().objectName(), '(childEvents)')


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
		s1 = str(event.type()).split('.')[-1] #get the event name ie. 'Enter' from QtCore.QEvent.Type.Enter
		s2 = s1[0].lower() + s1[1:] #lowercase the first letter.
		s3 = s2.replace('Button', '') #remove 'Button' if it exists.
		return s3 + 'Event' #add trailing 'Event'


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
			self.widgetName = self.tcl.sb.getWidgetName(self.widget, self.uiName) #get the stored objectName string (pyside objectName() returns unicode).
			self.widgetType = self.tcl.sb.getWidgetType(self.widget, self.uiName)
			self.derivedType = self.tcl.sb.getDerivedType(self.widget, self.uiName)
			self.ui = self.tcl.sb.getUi(self.uiName)
			self.uiLevel = self.tcl.sb.getUiLevel(self.uiName)
			self.method = self.tcl.sb.getMethod(self.uiName, self.widgetName)
			# print (self.uiName, self.widgetType, self.widgetName, event.__class__.__name__, eventName)

			# try: # if hasattr(self, eventName):
			getattr(self, eventName)(event) #handle the event locally. #ie. self.enterEvent(event)
			result = True
			# except AttributeError as error:
				# pass; print ('# Error: {}.eventFilter({}, {}): {} ui: {}. #'.format(__name__, widget, event.__class__.__name__, self.uiName, error))

		return result


	# ------------------------------------------------
	# Events
	# ------------------------------------------------
	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.widgetName=='info':
			EventFactoryFilter.resizeAndCenterWidget(self.widget)

		if self.widgetType in ('ComboBox', 'TreeWidgetExpandableList'):
			try: #call the class method associated with the current widget.
				self.method()
			except:
				try: #if call fails (ie. NoneType error); try adding the widget, and call again.
					self.tcl.sb.addWidget(self.uiName, self.widget)
					self.tcl.sb.getMethod(self.uiName, self.widgetName)()
				except (AttributeError, NameError, TypeError) as error:
					pass; #print ('# Error: {}.EventFactoryFilter.ShowEvent: Call to {}.{} failed: {}. #'.format(__name__, self.uiName, self.widgetName, error))

			if self.widgetType=='TreeWidgetExpandableList':
				self.initWidgets(self.uiName, self.widget.newWidgets) #initialize the widget to set things like the event filter and styleSheet.
				self.tcl.sb.connectSlots(self.uiName, self.widget.newWidgets)

		self.widget.__class__.showEvent(self.widget, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.widgetName=='mainWindow':
			if self._mouseGrabber:
				self._mouseGrabber.releaseMouse()
				self._mouseGrabber = None

		self.widget.__class__.hideEvent(self.widget, event)


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

		self.widget.__class__.enterEvent(self.widget, event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mouseHover.emit(False)

		if self.widgetType=='QWidget':
			if self.tcl.sb.prefix(self.widget, 'w'):
				self.widget.setVisible(False) #set visibility

		self.widget.__class__.leaveEvent(self.widget, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mousePressPos = event.globalPos() #mouse positon at press
		self.__mouseMovePos = event.globalPos() #mouse move position from last press

		self.widget.__class__.mousePressEvent(self.widget, event)


	def mouseMoveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if hasattr(self, '__mouseMovePos'):
			globalPos = event.globalPos()
			diff = globalPos -self.__mouseMovePos
			self.__mouseMovePos = globalPos

		self.widget.__class__.mouseMoveEvent(self.widget, event)


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.widget.underMouse(): #if self.widget.rect().contains(event.pos()): #if mouse over widget:
			if self.derivedType=='QPushButton':
				if self.tcl.sb.prefix(self.widget, 'i'): #ie. 'i012'
					self.tcl.setUi(self.widget.whatsThis())

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

		self.widget.__class__.mouseReleaseEvent(self.widget, event)


	def sendKeyPressEvent(self, key, modifier=QtCore.Qt.NoModifier):
		'''
		:Parameters:
			widget (obj) = 
			key (obj) = 
			modifier (obj = 
		'''
		self.widget.grabKeyboard()
		event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
		self.keyPressEvent(event)


	def keyPressEvent(self, event):
		'''A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event.

		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			# print ('keyPressEvent (childEvents): 0')
			modifiers = self.tcl.qApp.keyboardModifiers()

			if event.key()==self.tcl.key_close:
				self.close()

		self.widget.__class__.keyPressEvent(self.widget, event)


	def keyReleaseEvent(self, event):
		'''A widget must accept focus initially, and have focus, in order to receive a key release event.

		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			# print ('keyReleaseEvent (childEvents): 0')
			modifiers = self.tcl.qApp.keyboardModifiers()

			if event.key()==self.tcl.key_show and not modifiers==QtCore.Qt.ControlModifier:
				if self.widgetName=='mainWindow':
					if self.uiLevel>2:
						self.tcl._key_show_release.emit()
						self.widget.releaseKeyboard()

		self.widget.__class__.keyReleaseEvent(self.widget, event)








#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:


# try: #if callable(method): #attempt to clear any current menu items.
	# 	method.clear()
	# except AttributeError as error:
	# 	pass; #print ("# Error: {}.EventFactoryFilter.initWidgets: Call: {}.clear() failed: {}. #".format(__name__, method, error))

	# try: #attempt to construct the widget's contextMenu.
	# 	print ('METHOD:', widgetName, method)
	# 	method('setMenu')
	# except Exception as error:
	# 	pass; #print ("# Error: {}.EventFactoryFilter.initWidgets: Call: {}('setMenu') failed: {}. #".format(__name__, widgetName, error))


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
