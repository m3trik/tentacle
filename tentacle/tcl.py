# !/usr/bin/python
# coding=utf-8
import sys, os

from PySide2 import QtCore, QtGui, QtWidgets

from switchboard import Switchboard
from childEvents import EventFactoryFilter
from overlay import OverlayFactoryFilter

from ui.widgets import rwidgets



class Tcl(QtWidgets.QStackedWidget):
	'''Tcl is a marking menu based on a QStackedWidget.
	Gets and sets signal connections (through the switchboard module).
	Initializes events for child widgets using the childEvents module.
	Plots points for paint events in the overlay module.

	The various ui's are set by calling 'setUi' with the intended ui name string. ex. Tcl().setUi('polygons')

	:Parameters:
		parent (obj) = The parent application's top level window instance. ie. the Maya main window.
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
		# self.sb.qApp.setDoubleClickInterval(400)
		# self.sb.qApp.setKeyboardInputInterval(400)

		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		appName = self.parent().objectName().lower().rstrip('Window')
		self.sb = Switchboard(self, appName)
		self.sb.slotDir = os.path.join(self.sb.slotDir, appName)
		self.sb.loadAllUi(widgets=rwidgets)

		self.childEvents = EventFactoryFilter(self)
		self.overlay = OverlayFactoryFilter(self, antialiasing=True) #Paint events are handled by the overlay module.

		self.sb.qApp.focusChanged.connect(self.focusChanged)

		self.centerPos = lambda: QtGui.QCursor.pos() - self.rect().center() #get the center point of this widget.
		self.moveToAndCenter = lambda w, p: w.move(QtCore.QPoint(p.x()-(w.width()/2), p.y()-(w.height()/4))) #center a given widget on a given position.


	def initUi(self, ui):
		'''Initialize the given ui.

		:Parameters:
			ui (obj) = The ui to initialize.
		'''
		self.childEvents.initWidgets(ui)

		if ui.level<3: #stacked ui.
			self.addWidget(ui) #add the ui to the stackedLayout.

		else: #popup ui.
			ui.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
			ui.setAttribute(QtCore.Qt.WA_TranslucentBackground)
			# ui.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

			self._key_show_release.connect(ui.hide)

		ui.isInitialized = True


	def setUi(self, ui):
		'''Set the stacked Widget's index to the given ui.

		:Parameters:
			ui (str)(obj) = The ui or name of the ui to set the stacked widget index to.
		'''
		ui = self.sb.getUi(ui) #Get the ui of the given name, and set it as the current ui in the switchboard module.
		ui.connected = True #connect the ui to it's slots.

		if not ui.isInitialized:
			self.initUi(ui)

		if ui.level<3: #stacked ui top level window.
			self.setCurrentWidget(ui) #set the stacked widget to the given ui.
			self.resize(ui.sizeX, ui.sizeY) #The ui sizes for individual ui's are stored in sizeX and sizeY properties. Otherwise size would be constrained to the largest widget in the stack)

		else: #popup ui.
			ui.show()
			ui.resize(ui.minimumSizeHint()) #ui.adjustSize()
			self.moveToAndCenter(ui, QtGui.QCursor.pos()) #move to cursor position and offset slightly.
			self.childEvents.sendKeyPressEvent(self.key_show) #forward the keypress event.
			ui.activateWindow() #activate the popup ui before hiding the stacked layout.
			self.hide()


	def setSubUi(self, ui, w):
		'''Set the stacked widget's index to the submenu associated with the given widget.
		Positions the new ui to line up with the previous ui's button that called the new ui.

		:Parameters:
			ui (obj) = The submenu ui to set as current.
			w (obj) = The widget that called this method.
		'''
		if not ui or ui==self.sb.currentUi:
			return

		p1 = w.mapToGlobal(w.rect().center()) #the widget position before submenu change.

		self.setUi(ui) #switch the stacked widget to the given submenu.

		w2 = getattr(self.currentWidget(), w.name) #get the widget of the same name in the new ui.
		p2 = w2.mapToGlobal(w2.rect().center()) #widget position after submenu change.
		currentPos = self.mapToGlobal(self.pos())
		self.move(self.mapFromGlobal(currentPos +(p1 - p2))) #currentPos + difference

		if ui not in self.sb.getPrevUi(asList=1): #if the submenu ui called for the first time:
			self.cloneWidgetsAlongPath(ui) #re-construct any widgets from the previous ui that fall along the plotted path.
		self.drawPath.append((w, p1, QtGui.QCursor.pos())) #add the (<widget>, position) from the old ui to the path so that it can be re-created in the new ui (in the same position).
		self.removeFromPath(ui) #remove entrys from widget and draw paths when moving back down levels in the ui.

		self.resize(ui.sizeX, ui.sizeY)


	def returnToStart(self):
		'''Return the stacked widget to it's starting index.
		'''
		prevUi = self.sb.getPrevUi(omitLevel=2)
		self.setUi(prevUi) #return the stacked widget to it's previous ui.

		self.move(self.drawPath[0][2] - self.rect().center())

		del self.drawPath[1:] #Reset the list of previous widget and draw paths, while keeping the return point.


	def cloneWidgetsAlongPath(self, ui):
		'''Re-constructs the relevant buttons from the previous ui for the new ui, and positions them.
		Initializes the new buttons by adding them to the switchboard dict, setting connections, event filters, and stylesheets.
		The previous widget information is derived from the widget and draw paths.

		:Parameters:
			ui (obj) = The ui in which to copy the widgets to.
		'''
		w0 = self.sb.PushButton(ui, setObjectName='return_area', setSize_=(45, 45), setPosition_=self.drawPath[0][2]) #create an invisible return button at the start point.
		self.childEvents.initWidgets(ui, w0) #initialize the widget to set things like the event filter and styleSheet.
		self.sb.connectSlots(ui, w0)

		for prevWgt, prevPos, drawPos in self.drawPath[1:]:
			w1 = self.sb.PushButton(ui, copy_=prevWgt, setPosition_=prevPos, setVisible=True)
			self.childEvents.initWidgets(ui, w1) #initialize the widget to set things like the event filter and styleSheet.
			self.sb.connectSlots(ui, w1)


	def removeFromPath(self, ui):
		'''Remove the last entry from the widget and draw paths for the given ui.

		:Parameters:
			ui (obj) = The ui to remove.
		'''
		uis = [w.ui for w, wpos, cpos in self.drawPath]

		if ui in uis:
			i = uis[::-1].index(ui) #reverse the list and get the index of the last occurrence of name.
			# print (ui.name, [(w.ui.name, cpos) for w, wpos, cpos in self.drawPath]) #debug
			del self.drawPath[-i-1:]



	# ------------------------------------------------
	# 	Event handling:
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
			modifiers = self.sb.qApp.keyboardModifiers()

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
			modifiers = self.sb.qApp.keyboardModifiers()

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
		modifiers = self.sb.qApp.keyboardModifiers()

		if self.sb.currentUi.level<3:
			self.move(self.centerPos())

			w = self.sb.currentUi.mainWindow
			self.drawPath = [(w, w.mapToGlobal(w.rect().center()), w.mapToGlobal(w.rect().center()))] #maintain a list of widgets, their location, and cursor positions, as a path is plotted along the ui hierarchy.

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
		self.childEvents.mouseTracking(self.sb.currentUi)

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
		modifiers = self.sb.qApp.keyboardModifiers()

		if self.sb.currentUi.level<3:
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


	def show(self, ui='init'):
		'''Sets the widget as visible.

		:Parameters:
			ui (str)(obj) = Show the given ui.
		'''
		if self.profile:
			import cProfile
			cProfile.run('self.setUi({})'.format(ui.name))
		else:
			self.setUi(ui)

		QtWidgets.QStackedWidget.show(self)

		self.activateWindow()


	def showEvent(self, event):
		'''Non-spontaneous show events are sent to widgets immediately before they are shown.

		:Parameters:
			event = <QEvent>
		'''
		if self.sb.currentUi.level==0:
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
		if __name__ == "__main__":
			self.sb.qApp.quit()
			sys.exit() #assure that the sys processes are terminated during testing.

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
			print('# Warning: No recent menus in history. #')


	_cameraHistory = []
	def prevCamera(self, docString=False, method=False, allowCurrent=False, asList=False, add=None):
		'''
		:Parameters:
			docString (bool) = return the docString of last camera command. Default is off.
			method (bool) = return the method of last camera command. Default is off.
			allowCurrent (bool) = allow the current camera. Default is off.
			add (str)(obj) = Add a method, or name of method to be used as the command to the current camera.  (if this flag is given, all other flags are invalidated)

		:Return:
			if docString: 'string' description (derived from the last used camera command's docString) (asList: [string list] all docStrings, in order of use)
			if method: method of last used camera command. (asList: [<method object> list} all methods, in order of use)
			if asList: list of lists with <method object> as first element and <docString> as second. ie. [[<v001>, 'camera: persp']]
			else : <method object> of the last used command
		'''
		if add: #set the given method as the current camera.
			if not callable(add):
				add = self.sb.getMethod('cameras', add)
			docString = add.__doc__
			prevCameraList = self.prevCamera(allowCurrent=True, asList=1)
			if not prevCameraList or not [add, docString]==prevCameraList[-1]: #ie. do not append perp cam if the prev cam was perp.
				prevCameraList.append([add, docString]) #store the camera view
			return

		self._cameraHistory = self._cameraHistory[-20:] #keep original list length restricted to last 20 elements

		list_ = self._cameraHistory
		[list_.remove(l) for l in list_[:] if list_.count(l)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if not allowCurrent:
			list_ = list_[:-1] #remove the last index. (currentName)

		if asList:
			if docString and not method:
				try:
					return [i[1] for i in list_]
				except:
					return None
			elif method and not docString:
				try:
					return [i[0] for i in list_]
				except:
					return ['# No commands in history. #']
			else:
				return list_

		elif docString:
			try:
				return list_[-1][1]
			except:
				return ''

		else:
			try:
				return list_[-1][0]
			except:
				return None









if __name__ == '__main__':
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	#create a generic parent object to run the code using the Maya slots.
	dummyParent = QtWidgets.QWidget()
	dummyParent.setObjectName('MayaWindow')

	tcl = Tcl(dummyParent)
	tcl.sendKeyPressEvent(tcl.key_show) # Tcl().show('init')

	sys.exit(qApp.exec_())









#module name
# print (__name__)
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