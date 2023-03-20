# !/usr/bin/python
# coding=utf-8
import sys, os

from PySide2 import QtCore, QtGui, QtWidgets

from pythontk.Iter import makeList
from uitk.switchboard import Switchboard
from uitk.events import EventFactoryFilter, MouseTracking
from tentacle.overlay import Overlay


class Tcl(QtWidgets.QStackedWidget):
	'''Tcl is a marking menu based on a QStackedWidget.
	The various ui's are set by calling 'setUi' with the intended ui name string. ex. Tcl().setUi('polygons')
	'''
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	_key_show_release = QtCore.Signal()

	def __init__(self, parent=None, key_show='Key_F12', preventHide=False, ui_location='ui', slots_location=''):
		'''
		Parameters:
			parent (obj): The parent application's top level window instance. ie. the Maya main window.
		'''
		super().__init__(parent)

		self.key_show = getattr(QtCore.Qt, key_show)
		self.key_undo = QtCore.Qt.Key_Z
		self.key_close = QtCore.Qt.Key_Escape
		self.preventHide = preventHide
		self._mousePressPos = QtCore.QPoint()

		# self.app.setDoubleClickInterval(400)
		# self.app.setKeyboardInputInterval(400)
		self.setFocusPolicy(QtCore.Qt.StrongFocus)

		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint) #|QtCore.Qt.WindowStaysOnTopHint
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_NoMousePropagation, False)
		self.resize(1000, 1000)

		self.sb = Switchboard(self, ui_location=ui_location, slots_location=slots_location)
		self.overlay = Overlay(self, antialiasing=True) #Paint events are handled by the overlay module.
		self.eventFilter = EventFactoryFilter(self, eventNamePrefix='ef_', forwardEventsTo=self)
		self.mouseTracking = MouseTracking(self)


	def initUi(self, ui):
		'''Initialize the given ui.

		Parameters:
			ui (obj): The ui to initialize.
		'''
		self.initWidgets(ui.widgets)

		if ui.level<3: #stacked ui.
			ui.setParent(self)
			self.addWidget(ui) #add the ui to the stackedLayout.

		else: #popup ui.
			ui.setParent(self.parent())
			ui.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
			ui.setAttribute(QtCore.Qt.WA_TranslucentBackground)

			self._key_show_release.connect(ui.hide)


	def setUi(self, ui):
		'''Set the stacked Widget's index to the given ui.

		Parameters:
			ui (str)(obj): The ui or name of the ui to set the stacked widget index to.
		'''
		assert isinstance(ui, (str, QtWidgets.QWidget)), f'# Error: {__file__} in setUi\n#\tIncorrect datatype: {type(ui).__name__}'

		ui = self.sb.getUi(ui) #Get the ui of the given name, and set it as the current ui in the switchboard module.
		ui.setAsCurrent()
		if not ui.isInitialized:
			self.initUi(ui)

		if ui.level<3: #stacked ui top level window.
			self.setCurrentWidget(ui) #set the stacked widget to the given ui.

		else: #popup ui.
			ui.resize(ui.minimumSizeHint())
			self.sb.moveAndCenterWidget(ui, QtGui.QCursor.pos(), offsetY=4) #move to cursor position.
			ui.show(); self.hide() #activate the popup ui before hiding the stacked layout.


	def setSubUi(self, ui, w):
		'''Set the stacked widget's index to the submenu associated with the given widget.
		Positions the new ui to line up with the previous ui's button that called the new ui.

		Parameters:
			ui (obj): The submenu ui to set as current.
			w (obj): The widget that called this method.
		'''
		if not ui or ui==self.sb.ui:
			return

		p1 = w.mapToGlobal(w.rect().center()) #the widget position before submenu change.
		self.overlay.addToPath(ui, w)

		self.setUi(ui) #switch the stacked widget to the given submenu.

		w2 = getattr(self.currentWidget(), w.name) #get the widget of the same name in the new ui.
		p2 = w2.mapToGlobal(w2.rect().center()) #widget position after submenu change.
		currentPos = self.mapToGlobal(self.pos())
		self.move(self.mapFromGlobal(currentPos +(p1 - p2))) #currentPos + difference

		if ui not in self.sb.getPrevUi(asList=True): #if the submenu ui called for the first time:
			cloned_widgets = self.overlay.cloneWidgetsAlongPath(ui, self.returnToStart) #re-construct any widgets from the previous ui that fall along the plotted path.
			self.initWidgets(cloned_widgets)  # Initialize the widgets to set things like the event filter.


	def returnToStart(self):
		'''Return the stacked widget to it's starting index.
		'''
		starting_ui = self.sb.getPrevUi(omitLevel=2)
		self.setUi(starting_ui)
		self.move(self.overlay.pathStartPos - self.rect().center())



	# ---------------------------------------------------------------------------------------------
	# 	Stacked Widget Event handling:
	# ---------------------------------------------------------------------------------------------
	def sendKeyPressEvent(self, key, modifier=QtCore.Qt.NoModifier):
		'''
		'''
		self.grabKeyboard()
		event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
		self.keyPressEvent(event) # self.app.postEvent(self, event)


	def keyPressEvent(self, event):
		'''A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event.
		'''
		if event.isAutoRepeat():
			return

		# modifiers = self.app.keyboardModifiers()

		# if event.key()==self.key_show:
		# 	self.show()

		elif event.key()==self.key_close:
			self.close()

		super().keyPressEvent(event)


	def keyReleaseEvent(self, event):
		'''A widget must accept focus initially, and have focus, in order to receive a key release event.
		'''
		if event.isAutoRepeat():
			return

		modifiers = self.app.keyboardModifiers()

		if event.key()==self.key_show and not modifiers==QtCore.Qt.ControlModifier:
			self._key_show_release.emit()
			self.releaseKeyboard()
			self.hide()

		super().keyReleaseEvent(event)


	def mousePressEvent(self, event):
		'''
		'''
		modifiers = self.app.keyboardModifiers()

		if self.sb.ui.level<3:
			self.move(self.sb.getCenter(self))

			if not modifiers:
				if event.button()==QtCore.Qt.LeftButton:
					self.setUi('cameras')

				elif event.button()==QtCore.Qt.MiddleButton:
					self.setUi('editors')

				elif event.button()==QtCore.Qt.RightButton:
					self.setUi('main')

		super().mousePressEvent(event)


	def mouseMoveEvent(self, event):
		'''If mouse tracking is switched off, mouse move events only occur if 
		a mouse button is pressed while the mouse is being moved. If mouse tracking 
		is switched on, mouse move events occur even if no mouse button is pressed.
		'''

		super().mouseMoveEvent(event)


	def mouseReleaseEvent(self, event):
		'''
		'''
		self.setUi('init')

		super().mouseReleaseEvent(event)


	def mouseDoubleClickEvent(self, event):
		'''The widget will also receive mouse press and mouse release events 
		in addition to the double click event. If another widget that overlaps 
		this widget disappears in response to press or release events, 
		then this widget will only receive the double click event.
		'''
		modifiers = self.app.keyboardModifiers()

		if self.sb.ui.level<3:
			if event.button()==QtCore.Qt.LeftButton:

				if modifiers in (QtCore.Qt.ControlModifier, QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
					self.repeatLastCommand()
				else:
					self.repeatLastCameraView()

			elif event.button()==QtCore.Qt.MiddleButton:
				pass

			elif event.button()==QtCore.Qt.RightButton:
				self.repeatLastUi()

		super().mouseDoubleClickEvent(event)


	def show(self, ui='init', profile=False):
		'''Sets the widget as visible.

		Parameters:
			ui (str)(obj): Show the given ui.
			profile (bool): Prints the total running time, times each function separately, 
				and tells you how many times each function was called.
		'''
		self.sendKeyPressEvent(self.key_show)

		if profile:
			import cProfile
			cProfile.run(f'self.setUi({self.sb.getUi(ui).name})')
		else:
			self.setUi(ui)

		if self.sb.ui.level==0:
			self.move(self.sb.getCenter(self))

		super().show()
		self.activateWindow() #the window cannot be activated for keyboard events until after it is shown.


	def hide(self, force=False):
		'''Sets the widget as invisible.
		Prevents hide event under certain circumstances.

		Parameters:
			force (bool): override preventHide.
		'''
		if force or not self.preventHide:
			# print ('mouseGrabber:', self.mouseGrabber()) #Returns the widget that is currently grabbing the mouse input. else: None 
			super().hide()


	def hideEvent(self, event):
		'''Hide events are sent to widgets immediately after they have been hidden.
		'''
		try:
			self.mouseGrabber().releaseMouse()
		except AttributeError as error: #'NoneType' object has no attribute 'releaseMouse'
			pass

		super().hideEvent(event)



	# ---------------------------------------------------------------------------------------------
	# child widget event handling:
	# ---------------------------------------------------------------------------------------------
	ef_widgetTypes = [ #install an event filter for the given widget types.
		'QMainWindow',
		'QWidget',
		'QAction',
		'QLabel',
		'QPushButton',
		'QCheckBox',
		'QRadioButton',
		# 'QLineEdit',
		# 'QTextEdit',
		# 'QProgressBar',
		# 'QMenu',
		# 'QListWidget', 
		# 'QTreeWidget', 
		# 'QComboBox', 
		# 'QSpinBox',
		# 'QDoubleSpinBox',
	]
	def initWidgets(self, widgets):
		'''Set Initial widget states.

		Parameters:
			widgets (str)(list): The widget(s) to initialize.
		'''
		for w in makeList(widgets): #if 'widgets' isn't a list, convert it to one.
			# print (1, 'initWidgets:', w.ui.name.ljust(26), w.prefix.ljust(25), (w.name or type(w).__name__).ljust(25), w.type.ljust(15), w.derivedType.ljust(15), id(w)) #debug
			if w.derivedType in self.ef_widgetTypes:
				if w.ui.level<3:# or w.type=='QMainWindow':
					w.installEventFilter(self.eventFilter)

				if w.derivedType in ('QPushButton', 'QLabel'): #widget types to resize and center.
					if w.ui.level<3:
						self.sb.resizeAndCenterWidget(w)

				elif w.derivedType=='QWidget':
					if w.prefix=='hidden_area': #widget types to set an initial state as hidden.
						w.setVisible(False)


	def ef_showEvent(self, w, event):
		'''
		'''
		if w.name=='info':
			self.sb.resizeAndCenterWidget(w)

		if w.type in ('ComboBox', 'ListWidget'):
			try: #call the class method associated with the current widget.
				w.getSlot()()
			except (AttributeError, TypeError) as error:
				print (f'# Error: {__file__} in ef_showEvent\n#\t{error}.')
				pass

		w.showEvent(event)


	def ef_hideEvent(self, w, event):
		'''
		'''

		w.hideEvent(event)


	def ef_enterEvent(self, w, event):
		'''
		'''
		if w.type=='QWidget':
			if w.prefix=='hidden_area':
				w.setVisible(True) #set visibility

		elif w.derivedType=='QPushButton':
			if w.prefix=='i': #set the stacked widget.
				subUi = self.sb.getUi(w.whatsThis(), level=2)
				self.setSubUi(subUi, w)

		if w.prefix=='chk':
			if w.ui.isSubmenu:
				w.click()

		w.enterEvent(event)


	def ef_leaveEvent(self, w, event):
		'''
		'''
		if w.type=='QWidget':
			if w.prefix=='hidden_area':
				w.setVisible(False) #set visibility

		w.leaveEvent(event)


	def ef_mousePressEvent(self, w, event):
		'''
		'''
		self._mousePressPos = event.globalPos() #mouse positon at press
		self.__mouseMovePos = event.globalPos() #mouse move position from last press

		w.mousePressEvent(event)


	def ef_mouseMoveEvent(self, w, event):
		'''
		'''
		try:# if hasattr(self, '__mouseMovePos'):
			globalPos = event.globalPos()
			diff = globalPos - self.__mouseMovePos
			self.__mouseMovePos = globalPos
		except AttributeError as error:
			pass

		w.mouseMoveEvent(event)


	def ef_mouseReleaseEvent(self, w, event):
		'''
		'''
		if w.underMouse(): #if self.widget.rect().contains(event.pos()): #if mouse over widget:
			if w.derivedType=='QPushButton':
				if w.prefix=='i': #ie. 'i012'
					#hide/show ui groupboxes according to the buttons whatsThis formatting.
					name, *gbNames = w.whatsThis().split('#') #get any groupbox names that were prefixed by '#'.
					groupBoxes = self.sb.getWidgetsByType('QGroupBox', name)
					[gb.hide() if gbNames and not gb.name in gbNames else gb.show() for gb in groupBoxes] #show only groupboxes with those names if any were given, else show all.
					# self.app.processEvents() #the minimum size is not computed until some events are processed in the event loop.
					self.setUi(name)

				elif w.prefix=='v':
					if w.ui.name=='cameras':
						self.prevCamera(add=w.getSlot())
					#send click signal on mouseRelease.
					w.click()

				elif w.prefix in ('b','tb'):
					if w.ui.isSubmenu:
						w.click()
						self.hide()

		w.mouseReleaseEvent(event)


	def ef_sendKeyPressEvent(self, w, key, modifier=QtCore.Qt.NoModifier):
		'''
		'''
		w.grabKeyboard()
		event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
		self.ef_keyPressEvent(w, event)


	def ef_keyPressEvent(self, w, event):
		'''A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event.
		'''
		if not event.isAutoRepeat():
			# print (f'ef_keyPressEvent: {w}: {event}')
			modifiers = self.app.keyboardModifiers()

			if event.key()==self.key_close:
				self.close()

		w.keyPressEvent(event)


	def ef_keyReleaseEvent(self, w, event):
		'''A widget must accept focus initially, and have focus, in order to receive a key release event.
		'''
		if not event.isAutoRepeat():
			# print (f'ef_keyReleaseEvent: {e}: {event}')
			modifiers = self.app.keyboardModifiers()

			if event.key()==self.key_show and not modifiers==QtCore.Qt.ControlModifier:
				if w.type=='QMainWindow':
					if w.ui.level>2:
						self._key_show_release.emit()
						w.releaseKeyboard()

		w.keyReleaseEvent(event)


	# ---------------------------------------------------------------------------------------------
	# 	
	# ---------------------------------------------------------------------------------------------
	def repeatLastCommand(self):
		'''Repeat the last stored command.
		'''
		method = self.sb.prevCommand

		if callable(method):
			method()
		else:
			print('# Result: No recent commands in history. #')


	def repeatLastCameraView(self):
		'''Show the previous camera view.
		'''
		method = self.prevCamera()
		if method:
			method()
			method_ = self.prevCamera(allowCurrent=True, asList=1)[-2][0]
		else:
			method_ = self.sb.cameras.slots.v004 #get the persp camera.
			method_()
		self.prevCamera(add=method_) #store the camera view


	def repeatLastUi(self):
		'''Open the last used level 3 menu.
		'''
		prevUi = self.sb.getPrevUi(omitLevel=[0,1,2])
		if prevUi:
			self.setUi(prevUi)
		else:
			print('# Result: No recent menus in history. #')


	_cameraHistory = []
	def prevCamera(self, docString=False, method=False, allowCurrent=False, asList=False, add=None):
		'''
		Parameters:
			docString (bool): return the docString of last camera command. Default is off.
			method (bool): return the method of last camera command. Default is off.
			allowCurrent (bool): allow the current camera. Default is off.
			add (str)(obj): Add a method, or name of method to be used as the command to the current camera.  (if this flag is given, all other flags are invalidated)

		Return:
			if docString: 'string' description (derived from the last used camera command's docString) (asList: [string list] all docStrings, in order of use)
			if method: method of last used camera command. (asList: [<method object> list} all methods, in order of use)
			if asList: list of lists with <method object> as first element and <docString> as second. ie. [[<v001>, 'camera: persp']]
			else : <method object> of the last used command
		'''
		if add: #set the given method as the current camera.
			if not callable(add):
				add = self.sb.getSlot('cameras', add)
			docString = add.__doc__
			prevCameraList = self.prevCamera(allowCurrent=True, asList=1)
			if not prevCameraList or not [add, docString]==prevCameraList[-1]: #ie. do not append perp cam if the prev cam was perp.
				prevCameraList.append([add, docString]) #store the camera view
			return

		self._cameraHistory = self._cameraHistory[-20:] #keep original list length restricted to last 20 elements

		hist = self._cameraHistory
		[hist.remove(l) for l in hist[:] if hist.count(l)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if not allowCurrent:
			hist = hist[:-1] #remove the last index. (currentName)

		if asList:
			if docString and not method:
				try:
					return [i[1] for i in hist]
				except:
					return None
			elif method and not docString:
				try:
					return [i[0] for i in hist]
				except:
					return ['# No commands in history. #']
			else:
				return hist

		elif docString:
			try:
				return hist[-1][1]
			except:
				return ''

		else:
			try:
				return hist[-1][0]
			except:
				return None

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__ == '__main__':

	main = Tcl()
	main.show('init')

	exit_code = main.app.exec_()
	if exit_code != -1:
		sys.exit(exit_code) # run app, show window, wait for input, then terminate program with a status code returned from app.

#module name
# print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------





# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------

# self.app.focusChanged.connect(self.focusChanged)

		# def focusChanged(self, old, new):
		# 	'''Called on focus events.

		# 	Parameters:
		# 		old (obj): The widget with previous focus.
		# 		new (obj): The widget with current focus.
		# 	'''
		# 	try:
		# 		new.grabKeyboard()
		# 	except AttributeError as error:
		# 		self.setFocus()

		# 	if not self.isActiveWindow():
		# 		self.hide()

# class Instance():
# 	'''Manage multiple instances of the Tcl ui.
# 	'''
# 	instances={}

# 	def __init__(self, parent=None, preventHide=False, key_show='Key_F12'):
# 		'''
# 		'''
# 		self.Class = Tcl

# 		self.parent = parent
# 		self.preventHide = preventHide
# 		self.key_show = key_show

# 		self.activeWindow_ = None


# 	@property
# 	def instances_(self):
# 		'''Get all instances as a dictionary with the names as keys, and the window objects as values.
# 		'''
# 		return {k:v for k,v in self.instances.items() if not any([v.isVisible(), v==self.activeWindow_])}


# 	def _getInstance(self):
# 		'''Internal use. Returns a new instance if one is running and currently visible.
# 		Removes any old non-visible instances outside of the current 'activeWindow_'.
# 		'''
# 		if self.activeWindow_ is None or self.activeWindow_.isVisible():
# 			name = 'tentacle'+str(len(self.instances_))
# 			setattr(self, name, self.Class(self.parent, self.preventHide, self.key_show)) #set the instance as a property using it's name.
# 			self.activeWindow_ = getattr(self, name)
# 			self.instances_[name] = self.activeWindow_

# 		return self.activeWindow_


# 	def show(self, uiName=None, active=True):
# 		'''Sets the widget as visible.

# 		Parameters:
# 			uiName (str): Show the ui of the given name.
# 			active (bool): Set as the active window.
# 		'''
# 		inst = self._getInstance()
# 		inst.show(uiName=uiName, active=active)






# class Worker(QtCore.QObject):
# 	'''Send and receive signals from the GUI allowing for events to be 
# 	triggered from a separate thread.

# 	ex. self.worker = Worker()
# 		self.thread = QtCore.QThread()
# 		self.worker.moveToThread(self.thread)
# 		self.worker.finished.connect(self.thread.quit)
# 		self.thread.started.connect(self.worker.start)
# 		self.thread.start()
# 		self.worker.stop()
# 	'''
# 	started = QtCore.Signal()
# 	updateProgress = QtCore.Signal(int)
# 	finished = QtCore.Signal()

# 	def __init__(self, parent=None):
# 		super().__init__(parent)

# 	def start(self):
# 		self.started.emit()

# 	def stop(self):
# 		self.finished.emit()


# self.worker = Worker()
# self.thread = QtCore.QThread()
# self.worker.moveToThread(self.thread)

# self.worker.finished.connect(self.thread.quit)
# self.thread.started.connect(self.worker.start)

# # self.loadingIndicator = self.sb.LoadingIndicator(color='white', start=True, setPosition_='cursor')
# self.loadingIndicator = self.sb.GifPlayer(setPosition_='cursor')
# self.worker.started.connect(self.loadingIndicator.start)
# self.worker.finished.connect(self.loadingIndicator.stop)
# self.thread.start()

# import time #threading test
# for _ in range(11):
# 	time.sleep(.25)

#code
# self.worker.stop()


		# if self.addUi(ui, query=True): #if the ui has not yet been added to the widget stack.
		# 	self.addUi(ui) #initialize the parent ui if not done so already.

	# def addUi(self, ui, query=False):
	# 	'''Initializes the ui of the given name and it's dependancies.

	# 	Parameters:
	# 		ui (obj): The ui widget to be added to the layout stack.
	# 		query (bool): Check whether the ui widget has been added.

	# 	Return:
	# 		(bool) When queried.
	# 	'''
	# 	if query:
	# 		return self.indexOf(ui)<0

	# 	for i in reversed(range(4)): #in order of uiLevel heirarchy (top-level parent down).
	# 		ui_ = self.sb.getUi(ui, level=i)
	# 		if ui_:
	# 			name = self.sb.getUiName(ui_)

	# 			if self.addUi(ui_, query=True): #if the ui has not yet been added to the widget stack.
	# 				self.addWidget(ui_) #add the ui to the stackedLayout.
	# 				self.initWidgets(name)