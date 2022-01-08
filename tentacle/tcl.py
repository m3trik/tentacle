
# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtCore, QtGui, QtWidgets

from tentacle import Switchboard, EventFactoryFilter, OverlayFactoryFilter
from tentacle.ui import StyleSheet
import tentacle.ui.widgets as wgts



# ------------------------------------------------
# 	Construct the Widget Stack
# ------------------------------------------------
class Tcl(QtWidgets.QStackedWidget, StyleSheet):
	'''Tcl is a marking menu based on a QStackedWidget.
	Gets and sets signal connections (through the switchboard module).
	Initializes events for child widgets using the childEvents module.
	Plots points for paint events in the overlay module.

	The various ui's are set by calling 'setUi' with the intended ui name string. ex. Tcl().setUi('polygons')

	:Parameters:
		parent (obj) = The parent application's top level window.
		profile (bool) = Prints the total running time, times each function separately, and tells you how many times each function was called.
	'''
	_key_show_release = QtCore.Signal()

	def __init__(self, parent=None, key_show='Key_F12', preventHide=False, profile=False):
		QtWidgets.QStackedWidget.__init__(self, parent)

		self.key_show = getattr(QtCore.Qt, key_show)
		self.key_undo = QtCore.Qt.Key_Z
		self.key_close = QtCore.Qt.Key_Escape
		self.profile = profile
		self.preventHide = preventHide
		# self.qApp.setDoubleClickInterval(400)
		# self.qApp.setKeyboardInputInterval(400)

		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		self.sb = Switchboard(self)

		self.childEvents = EventFactoryFilter(self)
		self.overlay = OverlayFactoryFilter(self, antialiasing=True) #Paint events are handled by the overlay module.

		self.wgts = wgts

		self.qApp = QtWidgets.QApplication.instance()
		self.qApp.focusChanged.connect(self.focusChanged)

		self.centerPos = lambda: QtGui.QCursor.pos() - self.rect().center() #get the center point of this widget.
		self.centerWidget = lambda w, p: w.move(QtCore.QPoint(p.x()-(w.width()/2), p.y()-(w.height()/4))) #center a given widget on a given position.


	def initUi(self, uiName):
		'''
		'''
		ui = self.sb.getUi(uiName)
		ui.preventHide = False
		self.childEvents.initWidgets(uiName)

		if self.sb.getUiLevel(uiName)<3: #stacked ui.
			self.addWidget(ui) #add the ui to the stackedLayout.

		else: #popup ui.
			ui.setParent(self.parent())

			ui.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
			ui.setAttribute(QtCore.Qt.WA_TranslucentBackground)
			ui.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

			ui.hide = lambda w=ui: True if ui.preventHide else w.__class__.hide(w) #ui.setVisible(0)
			self._key_show_release.connect(ui.hide)

		self.sb.setUiState(uiName, 1)


	def setUi(self, uiName):
		'''Set the stacked Widget's index to the ui of the given name.

		:Parameters:
			uiName (str) = The name of the ui to set the stacked widget index to.

		:Return:
			(obj)
		'''
		ui = self.sb.getUi(uiName, setAsCurrent=True) #Get the ui of the given name, and set it as the current ui in the switchboard module.

		if self.sb.uiState<1: #self.indexOf(ui)==-1:
			self.initUi(uiName)

		if self.sb.uiLevel<3: #stacked ui.
			self.setCurrentWidget(ui) #set the stacked widget to the given ui.

		else: #popup ui.
			self.hide()
			ui.show()
			ui.activateWindow()

			self.childEvents.sendKeyPressEvent(self.key_show)

			self.centerWidget(ui, QtGui.QCursor.pos()) #move to cursor position and offset slightly.
		self.resize(self.sb.sizeX, self.sb.sizeY) #The ui sizes for individual ui's are stored in sizeX and sizeY properties. Otherwise size would be constrained to the largest widget in the stack)

		self.sb.setConnections(ui) #connect signal/slot connections for the current ui, while disconnecting the previous.
		self.sb.setUiState(uiName, 2)

		return ui


	def setPrevUi(self):
		'''Return the stacked widget to it's starting index.
		'''
		previous = self.sb.prevUiName(omitLevel=2)
		ui = self.setUi(previous) #return the stacked widget to it's previous ui.

		self.move(self.drawPath[0] - self.rect().center())

		#Reset the lists that make up the draw and widget paths.
		del self.drawPath[1:] #clear the draw path, while leaving the starting point.
		del self.widgetPath[:] #clear the list of previous widgets.


	def setSubUi(self, widget, uiName):
		'''Set the stacked widget's index to the submenu associated with the given widget.
		Positions the new ui to line up with the previous ui's button that called the new ui.

		:Parameters:
			widget (QWidget) = The widget that called this method.
			uiName (str) = The name of the ui to set.
		'''
		p1 = widget.mapToGlobal(widget.rect().center()) #widget position before submenu change.

		try: #set the ui to the submenu (if it exists).
			ui = self.setUi(uiName) #switch the stacked widget to the given submenu.
		except ValueError as error: #if no submenu exists: ignore and return.
			return None

		w = getattr(self.currentWidget(), widget.objectName()) #get the widget of the same name in the new ui.

		#remove entrys from widget and draw paths when moving back down levels in the ui.
		if len(self.sb.prevUiName(as_list=1))>2:
			if uiName in self.sb.prevUiName(as_list=1): #if uiName is that of a previous ui:
				self.removeFromPath(uiName)

		self.widgetPath.append([widget, p1, uiName]) #add the widget (<widget>, position, 'ui name') from the old ui to the widgetPath list so that it can be re-created in the new ui (in the same position).
		self.drawPath.append(QtGui.QCursor.pos()) #add the global cursor position to the drawPath list so that paint events can draw the path tangents.

		p2 = w.mapToGlobal(w.rect().center()) #widget position after submenu change.
		currentPos = self.mapToGlobal(self.pos())
		self.resize(1, 1)
		self.move(self.mapFromGlobal(currentPos +(p1 - p2))) #currentPos + difference

		if uiName not in self.sb.prevUiName(as_list=1): #if the submenu ui called for the first time:
			self.cloneWidgetsAlongPath(uiName) #re-construct any widgets from the previous ui that fall along the plotted path.

		self.resize(self.sb.sizeX, self.sb.sizeY)


	def removeFromPath(self, uiName):
		'''Remove the last entry from the widget and draw paths for the given ui name.

		:Parameters:
			uiName (str) = The name of the ui to remove entry of.
		'''
		uiNames = [i[2] for i in self.widgetPath] #get the ui names in widgetPath. ie. 'edit_submenu'

		if uiName in uiNames:
			i = uiNames[::-1].index(uiName) #reverse the list and get the index of the last occurrence of uiName.
			del self.drawPath[-i-1:]
			del self.widgetPath[-2:]


	def cloneWidgetsAlongPath(self, uiName):
		'''Re-constructs the relevant buttons from the previous ui for the new ui, and positions them.
		Initializes the new buttons by adding them to the switchboard dict, setting connections, event filters, and stylesheets.
		The previous widget information is derived from the widget and draw paths.

		:Parameters:
			uiName (str) = The name of ui to duplicate the widgets to.
		'''
		w0 = self.wgts.PushButton(parent=self.sb.getUi(uiName), setObjectName='return_area', setSize_=(45, 45), setPosition_=self.drawPath[0]) #create an invisible return button at the start point.
		self.childEvents.initWidgets(uiName, w0) #initialize the widget to set things like the event filter and styleSheet.
		self.sb.connectSlots(uiName, w0)

		if self.sb.getUiLevel(self.sb.prevUiName(omitLevel=3))==2: #if submenu: recreate widget/s from the previous ui that are in the current path.
			for i in range(2, len(self.widgetPath)+1): #for index in widgetPath starting at 2:
				prevWidget = self.widgetPath[-i][0] #assign the index a neg value to count from the back of the list (starting at -2).
				w1 = self.wgts.PushButton(parent=self.sb.getUi(uiName), copy_=prevWidget, setPosition_=self.widgetPath[-i][1], setVisible=True)
				self.childEvents.initWidgets(uiName, w1) #initialize the widget to set things like the event filter and styleSheet.
				self.sb.connectSlots(uiName, w1)
				self.childEvents._mouseOver.append(w1)
				w1.grabMouse() #set widget to receive mouse events.
				self.childEvents._mouseGrabber = w1



	# ------------------------------------------------
	# 	Tcl widget events
	# ------------------------------------------------
	def sendKeyPressEvent(self, key, modifier=QtCore.Qt.NoModifier):
		'''
		:Parameters:
			widget (obj) = 
			key (obj) = 
			modifier (obj = 
		'''
		self.grabKeyboard()
		event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, modifier)
		self.keyPressEvent(event)


	def keyPressEvent(self, event):
		'''A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event.

		:Parameters:
			event = <QEvent>
		'''
		# self._key_show_press.emit(True)

		if not event.isAutoRepeat():
			modifiers = self.qApp.keyboardModifiers()

			if event.key()==self.key_show:
				self.show()

			elif event.key()==self.key_close:
				self.close()

		return QtWidgets.QStackedWidget.keyPressEvent(self, event)


	def keyReleaseEvent(self, event):
		'''A widget must accept focus initially, and have focus, in order to receive a key release event.

		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			modifiers = self.qApp.keyboardModifiers()

			if event.key()==self.key_show and not modifiers==QtCore.Qt.ControlModifier:
				self._key_show_release.emit()
				self.releaseKeyboard()
				self.hide()

		return QtWidgets.QStackedWidget.keyReleaseEvent(self, event)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		modifiers = self.qApp.keyboardModifiers()

		if self.sb.uiLevel<3:
			self.move(self.centerPos())

			self.widgetPath=[] #maintain a list of widgets and their location, as a path is plotted along the ui hierarchy. ie. [[<QPushButton object1>, QPoint(665, 396)], [<QPushButton object2>, QPoint(585, 356)]]
			self.drawPath=[] #initiate the drawPath list that will contain points as the user moves along a hierarchical path.
			self.drawPath.append(self.mapToGlobal(self.rect().center()))

			if not modifiers:
				if event.button()==QtCore.Qt.LeftButton:
					self.setUi('cameras')

				elif event.button()==QtCore.Qt.MiddleButton:
					self.setUi('editors')

				elif event.button()==QtCore.Qt.RightButton:
					self.setUi('main')

		return QtWidgets.QStackedWidget.mousePressEvent(self, event)


	def mouseMoveEvent(self, event):
		'''If mouse tracking is switched off, mouse move events only occur if 
		a mouse button is pressed while the mouse is being moved. If mouse tracking 
		is switched on, mouse move events occur even if no mouse button is pressed.

		:Parameters:
			event = <QEvent>
		'''
		self.childEvents.mouseTracking(self.sb.uiName)

		return QtWidgets.QStackedWidget.mouseMoveEvent(self, event)


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self.setUi('init')

		return QtWidgets.QStackedWidget.mouseReleaseEvent(self, event)


	def mouseDoubleClickEvent(self, event):
		'''The widget will also receive mouse press and mouse release events 
		in addition to the double click event. If another widget that overlaps 
		this widget disappears in response to press or release events, 
		then this widget will only receive the double click event.

		:Parameters:
			event = <QEvent>
		'''
		modifiers = self.qApp.keyboardModifiers()

		if self.sb.uiLevel<3:
			if event.button()==QtCore.Qt.LeftButton:

				if modifiers in (QtCore.Qt.ControlModifier, QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
					self.repeatLastCommand()
				else:
					self.repeatLastCameraView()

			elif event.button()==QtCore.Qt.MiddleButton:
				pass

			elif event.button()==QtCore.Qt.RightButton:
				self.repeatLastUi()

		return QtWidgets.QStackedWidget.mouseDoubleClickEvent(self, event)


	def focusChanged(self, old, new):
		'''Called on focus events.

		:Parameters:
			old (obj) = The widget with previous focus.
			new (obj) = The widget with current focus.
		'''
		if not self.isActiveWindow():
			self.hide()

		# try:
		# 	self._key_show_release.disconnect(old.grabKeyboard)
		# except Exception as error:
		# 	pass
		# try:
		# 	self._key_show_release.connect(new.grabKeyboard)
		# except Exception as error:
		# 	pass

		try:
			new.grabKeyboard()
		except:
			pass


	def show(self, uiName='init'):
		'''Sets the widget as visible.

		:Parameters:
			uiName (str) = Show the ui of the given name.
			activate (bool) = Set as the active window.
		'''
		if self.profile:
			import cProfile
			cProfile.run("self.setUi(uiName)")
		else:
			self.setUi(uiName)

		QtWidgets.QStackedWidget.show(self)

		self.activateWindow()


	def showEvent(self, event):
		'''Non-spontaneous show events are sent to widgets immediately before they are shown.

		:Parameters:
			event = <QEvent>
		'''
		if self.sb.uiLevel==0:
			self.move(self.centerPos())

		return QtWidgets.QStackedWidget.showEvent(self, event)


	def hide(self, force=False):
		'''Sets the widget as invisible.
		Prevents hide event under certain circumstances.

		:Parameters:
			force (bool) = override preventHide.
		'''
		if force or not self.preventHide:
			# self.grabMouse()
			# self.releaseMouse() #Releases the mouse grab.
			# print ('mouseGrabber:', self.mouseGrabber()) #Returns the widget that is currently grabbing the mouse input. else: None 

			QtWidgets.QStackedWidget.hide(self)


	def hideEvent(self, event):
		'''Hide events are sent to widgets immediately after they have been hidden.

		:Parameters:
			event = <QEvent>
		'''
		# self.sb.gcProtect(clear=True) #clear any garbage protected items.

		# if __name__ == "__main__":
		# 	sys.exit() #assure that the sys processes are terminated during testing.

		return QtWidgets.QStackedWidget.hideEvent(self, event)



	# ------------------------------------------------
	# 	
	# ------------------------------------------------
	def repeatLastCommand(self):
		'''Repeat the last stored command.
		'''
		method = self.sb.prevCommand()
		if callable(method):
			method()
		else:
			print('# Warning: No recent commands in history. #')


	def repeatLastCameraView(self):
		'''Show the previous camera view.
		'''
		method = self.sb.prevCamera()
		if method:
			method()
			method_ = self.sb.prevCamera(allowCurrent=True, as_list=1)[-2][0]
		else:
			method_ = self.sb.getMethod('cameras', 'v004') #get the persp camera.
			method_()
		self.sb.prevCamera(add=method_) #store the camera view


	def repeatLastUi(self):
		'''Open the last used level 3 menu.
		'''
		prevUiName = self.sb.prevUiName(omitLevel=[0,1,2])
		if prevUiName:
			self.setUi(prevUiName)
			# self.move(self.drawPath[0] - self.rect().center())
		else:
			print('# Warning: No recent menus in history. #')









if __name__ == '__main__':
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	Tcl().show('init')
	sys.exit(qApp.exec_())



#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------





# Deprecated ----------------------------------------------------------------

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

# 		:Parameters:
# 			uiName (str) = Show the ui of the given name.
# 			active (bool) = Set as the active window.
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

# # self.loadingIndicator = self.wgts.LoadingIndicator(color='white', start=True, setPosition_='cursor')
# self.loadingIndicator = self.wgts.GifPlayer(setPosition_='cursor')
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

	# 	:Parameters:
	# 		ui (obj) = The ui widget to be added to the layout stack.
	# 		query (bool) = Check whether the ui widget has been added.

	# 	:Return:
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
	# 				self.childEvents.initWidgets(name)