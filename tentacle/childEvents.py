# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets



class EventFactoryFilter(QtCore.QObject):
	'''Event filter for dynamic ui objects.

	:Parameters:
		tcl (obj) = tcl widget instance.
	'''
	_mouseOver=[] #list of widgets currently under the mouse cursor. (Limited to those widgets set as mouse tracked)
	_mouseGrabber=None
	_mouseHover = QtCore.Signal(bool)
	_mousePressPos = QtCore.QPoint()

	enterEvent_ = QtCore.QEvent(QtCore.QEvent.Enter)
	leaveEvent_ = QtCore.QEvent(QtCore.QEvent.Leave)


	def __init__(self, tcl):
		super(EventFactoryFilter, self).__init__(tcl)

		self.tcl = tcl
		self.sb = self.tcl.sb

		self.widgetTypes = [ #install an event filter for the given widget types.
				'QMainWindow',
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
			ui (obj) = The ui to init widgets of.
			widgets (str)(list) = <QWidgets> if no arg is given, the operation will be performed on all widgets of the given ui name.
		'''
		if widgets is None:
			widgets = ui.widgets #get all widgets for the given ui.

		for w in self.sb.list_(widgets): #if 'widgets' isn't a list, convert it to one.

			if w not in ui.widgets:
				ui.addWidgets(w)

			#set stylesheet
			if ui.isSubmenu and not w.prefix=='i': #if submenu and objectName doesn't start with 'i':
				self.sb.setStyle(w, style='dark', hideMenuButton=True, backgroundOpacity=0)

			elif ui.level>2: #main menus
				self.sb.setStyle(w, style='dark', backgroundOpacity=0)

			else:
				self.sb.setStyle(w, backgroundOpacity=0)


			if w.derivedType in self.widgetTypes:
				# print (widgetName if widgetName else widget)
				if ui.level<3 or w.type=='QMainWindow':
					w.installEventFilter(self)

				try: #add the child widgets of popup menus.
					self.initWidgets(ui, w.menu_.childWidgets) #initialize the widget to set things like the event filter and styleSheet.
					self.sb.connectSlots(ui, w.menu_.childWidgets)

					self.initWidgets(ui, w.contextMenu.childWidgets)
					self.sb.connectSlots(ui, w.contextMenu.childWidgets)
				except AttributeError as error:
					pass; #print ("# Error: {}.EventFactoryFilter.initWidgets({}, {}): {}. #".format(__name__, ui, widgetName, error))

				if w.derivedType in ('QPushButton', 'QLabel'): #widget types to resize and center.
					if ui.level<=2:
						EventFactoryFilter.resizeAndCenterWidget(w)

				elif w.derivedType=='QWidget': #widget types to set an initial state as hidden.
					if w.prefix=='w' and ui.level==1: #prefix returns True if widgetName startswith the given prefix, and is followed by three integers.
						w.setVisible(False)


	def mouseTracking(self, ui):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Primarily used to trigger widget events while moving the cursor in the mouse button down state.

		:Parameters:
			ui (obj) = The ui to track widgets of.
		'''
		mouseOver = [w for w in ui.trackedWidgets if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos()))] #get all widgets currently under mouse cursor.
		#[print ('mouseOver:', w.objectName()) for w in ui.trackedWidgets if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos()))] #debug

		#send enter / leave events.
		[QtWidgets.QApplication.sendEvent(w, self.leaveEvent_) for w in self._mouseOver if not w in mouseOver] #send leave events for widgets no longer in mouseOver.
		[QtWidgets.QApplication.sendEvent(w, self.enterEvent_) for w in mouseOver if not w in self._mouseOver] #send enter events for any new widgets in mouseOver. 

		try:
			index = -1
			self._mouseGrabber = mouseOver[index]
			self._mouseGrabber.grabMouse() #set widget to receive mouse events.
			while not self._mouseGrabber.underMouse():
				index-=1
				self._mouseGrabber = mouseOver[index]
				self._mouseGrabber.grabMouse() #set widget to receive mouse events.
			# print ('\n_mouseGrabber:', self.tcl.mouseGrabber().name); [print(w) for w in self._mouseOver] #debug

		except IndexError as error:
			self._mouseGrabber = ui.mainWindow
			self._mouseGrabber.grabMouse()

		self._mouseOver = mouseOver


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
		eventName = EventFactoryFilter.createEventName(event) #get 'mousePressEvent' from <QEvent>

		result = False #default to False (event not handled)
		if eventName in self.eventTypes: #handle only events listed in 'eventTypes'
			self.w = widget
			# print (self.uiName, self.widgetType, self.widgetName, event.__class__.__name__, eventName)

			getattr(self, eventName)(event) #handle the event locally. #ie. self.enterEvent(event)
			result = True

		return result


	# ------------------------------------------------
	# Events
	# ------------------------------------------------
	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.w.name=='info':
			EventFactoryFilter.resizeAndCenterWidget(self.w)

		if self.w.type in ('ComboBox', 'TreeWidgetExpandableList'):
			try: #call the class method associated with the current widget.
				self.method()
			except:
				try: #if call fails (ie. NoneType error); try adding the widget, and call again.
					self.sb.addWidgets(self.w.ui, self.w)
					self.w.method()
				except (AttributeError, NameError, TypeError) as error:
					pass; #print ('# Error: {}.EventFactoryFilter.ShowEvent: Call to {}.{} failed: {}. #'.format(__name__, self.uiName, self.widgetName, error))

			if self.w.type=='TreeWidgetExpandableList':
				self.initWidgets(self.w.ui, self.w.newWidgets) #initialize the widget to set things like the event filter and styleSheet.
				self.sb.connectSlots(self.w.ui, self.w.newWidgets)

		self.w.__class__.showEvent(self.w, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.w.name=='mainWindow':#self.w.type=='QMainWindow':
			if self._mouseGrabber:
				self._mouseGrabber.releaseMouse()
				self._mouseGrabber = None

		self.w.__class__.hideEvent(self.w, event)


	def enterEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mouseHover.emit(True)

		if self.w.type=='QWidget':
			if self.w.prefix=='w':
				self.w.setVisible(True) #set visibility

		elif self.w.derivedType=='QPushButton':
			if self.w.prefix=='i': #set the stacked widget.
				subUi = self.sb.getUi(self.w.whatsThis(), level=2)
				self.tcl.setSubUi(subUi, self.w)

			elif self.w.name=='return_area':
				self.tcl.returnToStart()

		if self.w.prefix=='chk':
			if self.w.ui.isSubmenu:
				self.w.click()

		self.w.__class__.enterEvent(self.w, event)


	def leaveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mouseHover.emit(False)

		if self.w.type=='QWidget':
			if self.w.prefix=='w':
				self.w.setVisible(False) #set visibility

		self.w.__class__.leaveEvent(self.w, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self._mousePressPos = event.globalPos() #mouse positon at press
		self.__mouseMovePos = event.globalPos() #mouse move position from last press

		self.w.__class__.mousePressEvent(self.w, event)


	def mouseMoveEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		try:# if hasattr(self, '__mouseMovePos'):
			globalPos = event.globalPos()
			diff = globalPos - self.__mouseMovePos
			self.__mouseMovePos = globalPos
		except AttributeError as error:
			pass

		self.w.__class__.mouseMoveEvent(self.w, event)


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.w.underMouse(): #if self.widget.rect().contains(event.pos()): #if mouse over widget:
			if self.w.derivedType=='QPushButton':
				if self.w.prefix=='i': #ie. 'i012'
					#hide/show ui groupboxes according to the buttons whatsThis formatting.
					name, *gbNames = self.w.whatsThis().split('#') #get any groupbox names that were prefixed by '#'.
					groupBoxes = self.sb.getWidgetsByType('QGroupBox', name)
					[gb.hide() if gbNames and not gb.name in gbNames else gb.show() for gb in groupBoxes] #show only groupboxes with those names if any were given, else show all.
					# self.sb.qApp.processEvents() #the minimum size is not computed until some events are processed in the event loop.
					self.tcl.setUi(name)

				elif self.w.prefix=='v':
					if self.w.ui.name=='cameras':
						self.tcl.prevCamera(add=self.w.method)
					#send click signal on mouseRelease.
					self.w.click()

				elif self.w.prefix in ('b','tb'):
					if self.w.ui.isSubmenu:
						self.w.click()
					#add the buttons command info to the prevCommand list.
					self.sb.prevCommand(self.w.method, add=True)

		self.w.__class__.mouseReleaseEvent(self.w, event)


	def sendKeyPressEvent(self, key, modifier=QtCore.Qt.NoModifier):
		'''
		:Parameters:
			key (obj) = 
			modifier (obj = 
		'''
		self.w.grabKeyboard()
		event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
		self.keyPressEvent(event)


	def keyPressEvent(self, event):
		'''A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event.

		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			# print ('keyPressEvent (childEvents): 0')
			modifiers = self.sb.qApp.keyboardModifiers()

			if event.key()==self.tcl.key_close:
				self.close()

		self.w.__class__.keyPressEvent(self.w, event)


	def keyReleaseEvent(self, event):
		'''A widget must accept focus initially, and have focus, in order to receive a key release event.

		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			# print ('keyReleaseEvent (childEvents): 0')
			modifiers = self.sb.qApp.keyboardModifiers()

			if event.key()==self.tcl.key_show and not modifiers==QtCore.Qt.ControlModifier:
				if self.w.name=='mainWindow':#self.w.type=='QMainWindow':
					if self.w.ui.level>2:
						self.tcl._key_show_release.emit()
						self.w.releaseKeyboard()

		self.w.__class__.keyReleaseEvent(self.w, event)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:


		# for w in trackedWidgets: #get all tracked widgets of the current ui.

		# 	# try:
		# 	if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos())): #if mouse cursor is over widget:
		# 		# print ('mouseTracking: {}.{}'.format(self.sb.getUiName(ui), self.sb.getWidgetName(widget, ui))) #debug
		# 		if not w in self._mouseOver: #if widget already in mouseOver list, do not re-process the events.
		# 			self._mouseOver.append(w)
		# 			QtWidgets.QApplication.sendEvent(w, self.enterEvent_)

		# 	else:
		# 		try:
		# 			self._mouseOver.remove(w)
		# 			QtWidgets.QApplication.sendEvent(w, self.leaveEvent_)
		# 		except ValueError as error:
		# 			pass

			# except (AttributeError, TypeError) as error:
			# 	pass; #print ('# Error: {}.EventFactoryFilter.mouseTracking: {}. #'.format(__name__, error)) #debug


# if widget.underMouse() and widget.isEnabled():
# 	parentWidgets = self.sb.getParentWidgets(widget)
# 	widgetsUnderMouse.append(parentWidgets)


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
			# 	typ = self.sb._getDerivedType(c) #get the derived type without adding.
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
