# !/usr/bin/python
# coding=utf-8
import os, sys

from PySide2 import QtCore, QtGui, QtWidgets


class EventFactoryFilter(QtCore.QObject):
	'''Event filter for dynamic ui objects.

	:Parameters:
		tcl (obj): tcl widget instance.
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



class MouseTracking(QtCore.QObject):
	'''
	'''
	_prevMouseOver=[] #list of widgets currently under the mouse cursor. (Limited to those widgets set as mouse tracked)

	enterEvent_ = QtCore.QEvent(QtCore.QEvent.Enter)
	leaveEvent_ = QtCore.QEvent(QtCore.QEvent.Leave)

	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	def mouseOverFilter(self, widgets):
		'''Get the widget(s) currently under the mouse cursor, and manage mouse grab and event handling for those widgets.
		Primarily used to trigger widget events while moving the cursor in the mouse button down state.

		:Parameters:
			widgets (list): The widgets to filter for those currently under the mouse cursor.

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
			widgets (list): The widgets to track.
		'''
		mouseOver = self.mouseOverFilter(widgets)

		#send leave events for widgets no longer in mouseOver.
		for w in self._prevMouseOver:
			if not w in mouseOver:
				self.app.sendEvent(w, self.leaveEvent_)
				w.releaseMouse()
				# print ('releaseMouse:', w) #debug

		#send enter events for any new widgets in mouseOver.
		for w in mouseOver:
			if not w in self._prevMouseOver:
				self.app.sendEvent(w, self.enterEvent_)

		try:
			topWidget = self.app.widgetAt(QtGui.QCursor.pos())
			topWidget.grabMouse() #set widget to receive mouse events.
			# print ('grabMouse:', topWidget) #debug
			# print ('focusWidget:', self.app.focusWidget())

		except AttributeError as error:
			self.app.activeWindow().grabMouse()

		self._prevMouseOver = mouseOver

# --------------------------------------------------------------------------------------------







#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


#deprecated: ------------------------------

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