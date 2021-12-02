# !/usr/bin/python
# coding=utf-8
import sys, os.path

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
	'''
	qApp = QtWidgets.QApplication

	def __init__(self, parent=None, preventHide=False, key_show='Key_F12'):
		QtWidgets.QStackedWidget.__init__(self, parent)

		self.preventHide = preventHide
		self.key_show = getattr(QtCore.Qt, key_show)
		self.key_undo = QtCore.Qt.Key_Z
		self.key_close = QtCore.Qt.Key_Escape
		# self.qApp.setDoubleClickInterval(400)
		# self.qApp.setKeyboardInputInterval(400)

		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		self.sb = Switchboard(self)
		self.sb.setMainAppWindow(self.parent())
		self.sb.setClassInstance(self)

		self.childEvents = EventFactoryFilter(self)
		self.overlay = OverlayFactoryFilter(self) #Paint events are handled by the overlay module.

		self.wgts = wgts

		self.qApp.instance().focusChanged.connect(self.focusChanged)

		self.centerPos = lambda: QtGui.QCursor.pos() - self.rect().center() #the center point of the widget at any given time.


	def initUi(self, name, level=None):
		'''Adds the given ui to the stacked widget (if it has not been set before), and constructs any additional dependancies.

		:Parameters:
			name (str) = The name of the ui. ie. 'polygons_component_submenu'
			level (int) = The desired returned ui level. If None, then the level will be derived from the name.

		:Return:
			(obj) ui.
		'''
		ui = self.sb.getUi(name, level=level) #get the parent ui.
		name = self.sb.getUiName(name, level=level) #get the parent ui's name.

		if self.indexOf(ui)==-1: #if the given widget is not a child of the QStackedWidget.
			self.addWidget(ui) #add the ui to the stackedLayout.
			self.childEvents.initWidgets(name)

		return ui


	def setUi(self, name):
		'''Set the stacked Widget's index to the ui of the given name.

		:Parameters:
			name (str) = The name of the ui to set the stacked widget index to.
		'''
		ui = self.sb.getUi(name, setAsCurrent=True) #Get the ui of the given name, and set it as the current ui in the switchboard module, which amoung other things, sets connections.

		self.initUi(name) #add the ui to the stackedLayout (if it hasn't already been added).

		self.resize(self.sb.sizeX, self.sb.sizeY) #The ui sizes for individual ui's are stored in sizeX and sizeY properties. Otherwise size would be constrained to the largest widget in the stack)

		if self.sb.uiLevel>2:
			self.move(self.centerPos().x(), self.centerPos().y()+(self.sb.sizeY/2.15)) #self.move(self.centerPos() - ui.draggable_header.mapToGlobal(ui.draggable_header.rect().center()))
		# else:
		# 	self.showFullScreen()
		# print('keyboardGrabber:', self.keyboardGrabber())

		self.setCurrentWidget(ui) #set the stacked widget to the given ui.

		return ui


	def setPrevUi(self):
		'''Return the stacked widget to it's starting index.
		'''
		# self.setWindowOpacity(0.0)
		previous = self.sb.previousName(omitLevel=[2,3])
		self.setUi(previous) #return the stacked widget to it's previous ui.

		self.move(self.drawPath[0] - self.rect().center())

		#Reset the lists that make up the draw and widget paths.
		del self.drawPath[1:] #clear the draw path, while leaving the starting point.
		del self.widgetPath[:] #clear the list of previous widgets.
		# self.setWindowOpacity(1.0)


	def setSubUi(self, widget, name):
		'''Set the stacked widget's index to the submenu associated with the given widget.
		Positions the new ui to line up with the previous ui's button that called the new ui.

		:Parameters:
			widget (QWidget) = The widget that called this method.
			name (str) = The name of the ui to set.
		'''
		# self.setWindowOpacity(0.0)
		p1 = widget.mapToGlobal(widget.rect().center()) #widget position before submenu change.

		try: #set the ui to the submenu (if it exists).
			self.initUi(name, level=3) #initialize the parent ui if not done so already.
			self.setUi(name) #switch the stacked widget to the given submenu.
		except ValueError: #if no submenu exists: ignore and return.
			return None

		w = getattr(self.currentWidget(), widget.objectName()) #get the widget of the same name in the new ui.

		#remove entrys from widget and draw paths when moving back down levels in the ui.
		if len(self.sb.previousName(as_list=1))>2:
			if name in self.sb.previousName(as_list=1): #if name is that of a previous ui:
				self.removeFromPath(name)

		self.widgetPath.append([widget, p1, name]) #add the widget (<widget>, position, 'ui name') from the old ui to the widgetPath list so that it can be re-created in the new ui (in the same position).
		self.drawPath.append(QtGui.QCursor.pos()) #add the global cursor position to the drawPath list so that paint events can draw the path tangents.

		p2 = w.mapToGlobal(w.rect().center()) #widget position after submenu change.
		currentPos = self.mapToGlobal(self.pos())
		self.resize(1, 1)
		self.move(self.mapFromGlobal(currentPos +(p1 - p2))) #currentPos + difference

		if name not in self.sb.previousName(as_list=1): #if the submenu ui called for the first time:
			self.cloneWidgetsAlongPath(name) #re-construct any widgets from the previous ui that fall along the plotted path.

		self.resize(self.sb.sizeX, self.sb.sizeY)
		# self.setWindowOpacity(1.0)


	def removeFromPath(self, name):
		'''Remove the last entry from the widget and draw paths for the given ui name.

		:Parameters:
			name (str) = The name of the ui to remove entry of.
		'''
		names = [i[2] for i in self.widgetPath] #get the ui names in widgetPath. ie. 'edit_submenu'

		if name in names:
			i = names[::-1].index(name) #reverse the list and get the index of the last occurrence of name.
			del self.drawPath[-i-1:]
			del self.widgetPath[-2:]


	def cloneWidgetsAlongPath(self, name):
		'''Re-constructs the relevant buttons from the previous ui for the new ui, and positions them.
		Initializes the new buttons by adding them to the switchboard dict, setting connections, event filters, and stylesheets.
		The previous widget information is derived from the widget and draw paths.

		:Parameters:
			name (str) = The name of ui to duplicate the widgets to.
		'''
		w0 = self.wgts.PushButton(parent=self.sb.getUi(name), setObjectName='return_area', setSize_=(45, 45), setPosition_=self.drawPath[0]) #create an invisible return button at the start point.
		self.childEvents.addWidgets(name, w0) #initialize the widget to set things like the event filter and styleSheet.

		if self.sb.getUiLevel(self.sb.previousName(omitLevel=3))==2: #if submenu: recreate widget/s from the previous ui that are in the current path.
			for i in range(2, len(self.widgetPath)+1): #for index in widgetPath starting at 2:
				prevWidget = self.widgetPath[-i][0] #assign the index a neg value to count from the back of the list (starting at -2).
				w1 = self.wgts.PushButton(parent=self.sb.getUi(name), copy_=prevWidget, setPosition_=self.widgetPath[-i][1], setVisible=True)
				self.childEvents.addWidgets(name, w1) #initialize the widget to set things like the event filter and styleSheet.
				self.childEvents._mouseOver.append(w1)
				w1.grabMouse() #set widget to receive mouse events.
				self.childEvents._mouseGrabber = w1



	# ------------------------------------------------
	# 	Tcl widget events
	# ------------------------------------------------
	def keyPressEvent(self, event):
		'''A widget must call setFocusPolicy() to accept focus initially, and have focus, in order to receive a key press event.

		:Parameters:
			event = <QEvent>
		'''
		if not event.isAutoRepeat():
			# print ('keyPressEvent:', event.key()==self.key_show)
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
			# print ('keyReleaseEvent:', event.key()==self.key_show)
			if event.key()==self.key_show and not modifiers==QtCore.Qt.ControlModifier:
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
		if self.sb.uiLevel<3:
			self.childEvents.mouseTracking(self.sb.uiName)

		return QtWidgets.QStackedWidget.mouseMoveEvent(self, event)


	def mouseReleaseEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		if self.sb.uiLevel>0 and self.sb.uiLevel<3:
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
			old (obj) = The previously focused widget.
			new (obj) = The current widget with focus.
		'''
		if not self.isActiveWindow():
			self.hide()


	def show(self, name=None, active=True):
		'''Sets the widget as visible.

		:Parameters:
			name (str) = Show the ui of the given name.
			active (bool) = Set as the active window.
		'''
		if name:
			self.setUi(name)

		QtWidgets.QStackedWidget.show(self)
		if active:
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
		previousName = self.sb.previousName(omitLevel=[0,1,2])
		if previousName:
			self.setUi(previousName)
			self.move(self.drawPath[0] - self.rect().center())
		else:
			print('# Warning: No recent menus in history. #')









if __name__ == '__main__':
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	Tcl().show('init')
	sys.exit(qApp.exec_())



#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------





# Deprecated ----------------------------------------------------------------



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


# self.sb.setUiSize(name) #Set the size info for each ui (allows for resizing a stacked widget where otherwise resizing is constrained by the largest widget in the stack)
	# if self.sb.getUiLevel(name)==2: #initialize the parent ui
	# 	parentUi = self.sb.getUi(name, level=3) #get the parent ui.
	# 	parentUiName = self.sb.getUiName(parentUi, level=3) #get the parent ui name.
		# if not parentUiName in self.sb.previousName(as_list=1):
			# self.addWidget(parentUi) #add the ui to the stackedLayout.
			# self.childEvents.initWidgets(parentUiName)

# if any([self.sb.uiName=='main', self.sb.uiName=='cameras', self.sb.uiName=='editors']):
# 	drag = QtGui.QDrag(self)
# 	drag.setMimeData(QtCore.QMimeData())

# 	# drag.setHotSpot(event.pos())
# 	# drag.setDragCursor(QtGui.QCursor(QtCore.Qt.CrossCursor).pixmap(), QtCore.Qt.MoveAction) #QtCore.Qt.CursorShape(2) #QtCore.Qt.DropAction
# 	drag.start(QtCore.Qt.MoveAction) #drag.exec_(QtCore.Qt.MoveAction)
# 	print(drag.target() #the widget where the drag object was dropped.)

# @property
# 	def sb(self):
# 		if not hasattr(self, '_sb'):
# 			self._sb = Switchboard()
# 			self._sb.setMainAppWindow(self.parent)
# 			self._sb.setClassInstance(self, 'main')
# 		return self._sb

# 	@property
# 	def childEvents(self):
# 		if not hasattr(self, '_childEvents'):
# 			self._childEvents = EventFactoryFilter(self)
# 		return self._childEvents

# 	@property
# 	def overlay(self):
# 		if not hasattr(self, '_overlay'):
# 			self._overlay = OverlayFactoryFilter(self) #Paint events are handled by the overlay module.
# 		return self._overlay