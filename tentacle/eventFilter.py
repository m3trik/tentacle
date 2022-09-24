# !/usr/bin/python
# coding=utf-8
import os, sys

from PySide2 import QtCore, QtWidgets



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









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:

