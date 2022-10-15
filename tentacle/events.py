# !/usr/bin/python
# coding=utf-8
import os, sys

from PySide2 import QtCore, QtGui, QtWidgets



class EventFactoryFilter(QtCore.QObject):
	'''Event filter for dynamic ui objects.

	:Parameters:
		tcl (obj) = tcl widget instance.
	'''
	events=['showEvent', #the types of events to be handled here.
			'hideEvent',
			'enterEvent',
			'leaveEvent',
			'mousePressEvent',
			'mouseMoveEvent',
			'mouseReleaseEvent',
			'keyPressEvent',
			'keyReleaseEvent',
	]

	eventNamePrefix = ''
	forwardEventsTo = None

	def __init__(self, parent=None, eventNamePrefix=eventNamePrefix, forwardEventsTo=forwardEventsTo, events=events):
		super().__init__(parent)

		self.eventNamePrefix = eventNamePrefix
		self.forwardEventsTo = forwardEventsTo


	def createEventName(self, event):
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
		if self.forwardEventsTo is None:
			self.forwardEventsTo = self

		eventName = self.createEventName(event) #get 'mousePressEvent' from <QEvent>

		if eventName in self.events: #handle only events listed in 'eventTypes'
			try:
				getattr(self.forwardEventsTo, self.eventNamePrefix+eventName)(widget, event) #handle the event (in subclass. #ie. self.enterEvent(<widget>, <event>)
				return True

			except AttributeError as error:
				pass #print (__file__, error)

		return False #event not handled



class OverlayFactoryFilter(QtCore.QObject):
	'''Handles paint events as an overlay on top of an existing widget.
	'''
	def __init__(self, parent=None):
		super().__init__(parent)


	def eventFilter(self, widget, event):
		'''Relay events from the parent widget to the overlay.
		'''
		if not widget.isWidgetType():
			return False

		if event.type()==QtCore.QEvent.MouseButtonPress:
			self.mousePressEvent(event)

		elif event.type()==QtCore.QEvent.MouseButtonRelease:
			self.mouseReleaseEvent(event)

		elif event.type()==QtCore.QEvent.MouseMove:
			self.mouseMoveEvent(event)

		elif event.type()==QtCore.QEvent.MouseButtonDblClick:
			self.mouseDoubleClickEvent(event)

		elif event.type()==QtCore.QEvent.KeyPress:
			self.keyPressEvent(event)

		elif event.type()==QtCore.QEvent.KeyRelease:
			self.keyReleaseEvent(event)

		elif event.type()==QtCore.QEvent.Resize:
			if widget==self.parentWidget():
				self.resize(widget.size())

		elif event.type()==QtCore.QEvent.Show:
			self.raise_()

		return super().eventFilter(widget, event)



class MouseTracking(QtCore.QObject):
	'''
	'''
	_prevMouseOver=[] #list of widgets currently under the mouse cursor. (Limited to those widgets set as mouse tracked)

	enterEvent_ = QtCore.QEvent(QtCore.QEvent.Enter)
	leaveEvent_ = QtCore.QEvent(QtCore.QEvent.Leave)

	app = QtWidgets.QApplication.instance()
	if not app:
		app = QtWidgets.QApplication(sys.argv)


	def __init__(self, parent=None,):
		'''
		:Parameters:
			parent (obj) = The parent application's top level window instance. ie. the Maya main window.
			profile (bool) = Prints the total running time, times each function separately, and tells you how many times each function was called.
		'''
		super().__init__(parent)


	def mouseOverFilter(self, widgets):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Primarily used to trigger widget events while moving the cursor in the mouse button down state.

		:Parameters:
			widgets (list) = The widgets to filter for those currently under the mouse cursor.

		:Return:
			(list) widgets currently under mouse.
		'''
		mouseOver=[]
		for w in widgets: #get all widgets currently under mouse cursor and send enter|leave events accordingly.
			try:
				if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos())):
					mouseOver.append(w)

			except AttributeError as error:
				pass

		return mouseOver


	def track(self, widgets):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Primarily used to trigger widget events while moving the cursor in the mouse button down state.

		:Parameters:
			widgets (list) = The widgets to track.
		'''
		mouseOver = self.mouseOverFilter(widgets)

		#send enter / leave events.
		[self.app.sendEvent(w, self.leaveEvent_) and w.releaseMouse() for w in self._prevMouseOver if not w in mouseOver] #send leave events for widgets no longer in mouseOver.
		[self.app.sendEvent(w, self.enterEvent_) for w in mouseOver if not w in self._prevMouseOver] #send enter events for any new widgets in mouseOver. 

		try:
			topWidget = self.app.widgetAt(QtGui.QCursor.pos())
			topWidget.grabMouse() #set widget to receive mouse events.
			print (topWidget)

		except AttributeError as error:
			self.app.activeWindow().grabMouse()

		self._prevMouseOver = mouseOver









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:

# w = self.app.widgetAt(QtGui.QCursor.pos())

# 		if not w==self._prevMouseOver:
# 			try:
# 				self._prevMouseOver.releaseMouse()
# 				self.app.sendEvent(self._prevMouseOver, self.leaveEvent_)
# 			except (TypeError, AttributeError) as error:
# 				pass

# 			w.grabMouse() #set widget to receive mouse events.
# 			print ('grab:', w.objectName())
# 			self.app.sendEvent(w, self.enterEvent_)
# 			self._prevMouseOver = w