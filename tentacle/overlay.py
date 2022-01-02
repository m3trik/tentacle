# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from tentacle import EventFactoryFilter



# ------------------------------------------------
# PaintEvent Overlay
# ------------------------------------------------
class Overlay(QtWidgets.QWidget):
	'''Handles paint events as an overlay on top of an existing widget.

	:Parameters:
		tcl (obj) = tcl widget instance.
		antialiasing (bool) = Set antialiasing for the tangent paint events.
	'''
	greyPen = QtGui.QPen(QtGui.QColor(115, 115, 115), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
	blackPen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)


	def __init__(self, tcl=None, antialiasing=False):
		super(Overlay, self).__init__(tcl)

		if tcl:
			self.tcl = tcl
			self.antialiasing = antialiasing

			self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
			self.setAttribute(QtCore.Qt.WA_NoSystemBackground) #takes a single arg
			self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

			self.painter = QtGui.QPainter() #Initialize self.painter


	def paintEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		if self.tcl.sb.uiLevel>0 and self.tcl.sb.uiLevel<3:

			self.painter.begin(self)

			for i, start_point in enumerate(self.tcl.drawPath): #plot and draw the points in the drawPath list.
				try:
					end_point = self.mapFromGlobal(self.tcl.drawPath[i+1])
				except:
					end_point = self.mouseEventPos #after the list points are drawn, plot the current end_point, controlled by the mouse move event.

				self.drawTangent(self.mapFromGlobal(start_point), end_point)

			self.painter.end()


	def drawTangent(self, start_point, end_point):
		'''draw a segment between two points with the given self.painter.
		'''
		path = QtGui.QPainterPath()
		path.addEllipse(QtCore.QPointF(start_point), 7, 7)

		self.painter.fillRect(self.rect(), QtGui.QColor(127, 127, 127, 0)) #transparent overlay background.
		self.painter.setRenderHint(QtGui.QPainter.Antialiasing, self.antialiasing)
		self.painter.setBrush(QtGui.QColor(115, 115, 115))
		self.painter.fillPath(path, QtGui.QColor(115, 115, 115))
		self.painter.setPen(self.blackPen)
		self.painter.drawPath(path) #stroke
		if not end_point.isNull():
			self.painter.setPen(self.greyPen)
			self.painter.drawLine(start_point, end_point)
			# self.painter.drawEllipse(end_point, 5, 5)


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		# self.painter.eraseRect(self.rect())
		self.mouseEventPos = event.pos()
		self.update()


	def mouseMoveEvent(self, event):
		'''
		:Parameters:
			event=<QEvent>
		'''
		self.mouseEventPos = event.pos()
		self.update()






class OverlayFactoryFilter(QtCore.QObject):
	'''Relay events from the parent widget to the overlay.
	'''
	def __init__(self, parent=None, antialiasing=False):
		super(OverlayFactoryFilter, self).__init__(parent)

		self.overlay = Overlay(parent, antialiasing)

		if parent:
			parent.installEventFilter(self)


	def eventFilter(self, widget, event):
		'''
		:Parameters:
			widget=<QWidget>
			event=<QEvent>
		'''
		if not widget.isWidgetType():
			return False

		if event.type()==QtCore.QEvent.MouseButtonPress:
			self.overlay.mousePressEvent(event)

		elif event.type()==QtCore.QEvent.MouseButtonRelease:
			self.overlay.mouseReleaseEvent(event)

		elif event.type()==QtCore.QEvent.MouseMove:
			self.overlay.mouseMoveEvent(event)

		elif event.type()==QtCore.QEvent.MouseButtonDblClick:
			self.overlay.mouseDoubleClickEvent(event)

		elif event.type()==QtCore.QEvent.Resize:
			if widget==self.overlay.parentWidget():
				self.overlay.resize(widget.size())

		elif event.type()==QtCore.QEvent.Show:
			self.overlay.raise_()

		return super(OverlayFactoryFilter, self).eventFilter(widget, event)









#module name
print (__name__)


# -----------------------------------------------
# Notes
# -----------------------------------------------