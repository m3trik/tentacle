# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from events import OverlayFactoryFilter


class Overlay(QtWidgets.QWidget, OverlayFactoryFilter):
	'''Handles paint events as an overlay on top of an existing widget.

	:Parameters:
		tcl (obj) = tcl widget instance.
		antialiasing (bool) = Set antialiasing for the tangent paint events.
	'''
	greyPen = QtGui.QPen(QtGui.QColor(115, 115, 115), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
	blackPen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)

	app = QtWidgets.QApplication.instance()

	def __init__(self, parent=None, antialiasing=False):
		super().__init__(parent)

		self.antialiasing = antialiasing
		self.drawEnabled = False

		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
		self.setAttribute(QtCore.Qt.WA_NoSystemBackground) #takes a single arg
		self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

		self.painter = QtGui.QPainter() #Initialize self.painter

		if parent:
			parent.installEventFilter(self)


	@property
	def drawPath(self) -> list:
		'''
		'''
		try:
			return self._drawPath

		except AttributeError as error:
			self._drawPath = []
			return self._drawPath


	@drawPath.setter
	def drawPath(self, lst) -> None:
		'''
		'''
		self._drawPath = lst


	@property
	def returnArea(self) -> object:
		'''
		'''
		try:
			return self._returnArea

		except AttributeError as error:
			#create a return area widget. It's initial location does not matter, as it will later be re-created at cursor pos.
			w = QtWidgets.QPushButton(self)
			w.setObjectName('return_area')
			w.resize(45, 45)
			self._returnArea = w
			return self._returnArea


	def paintEvent(self, event):
		'''
		'''
		if not self.drawEnabled:
			return

		self.painter.begin(self)

		for i, (w, wpos, start_point) in enumerate(self.drawPath): #plot and draw the points in the drawPath list.

			start_point = self.mapFromGlobal(start_point)
			try:
				end_point = self.mapFromGlobal(self.drawPath[i+1][2])
			except IndexError as error:
				end_point = self.mouseMovePos #after the list points are drawn, plot the current end_point, controlled by the mouse move event.

			self.drawTangent(start_point, end_point)

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


	def keyReleaseEvent(self, event):
		'''
		'''
		if event.isAutoRepeat():
			return

		# modifiers = self.app.keyboardModifiers()
		del self.drawPath[:]

		self.update()


	def mousePressEvent(self, event):
		'''
		'''
		del self.drawPath[:]
		curPos = self.mapToGlobal(event.pos())
		self.drawPath.append([self.returnArea, curPos, curPos]) #maintain a list of widgets, their location, and cursor positions, as a path is plotted along the ui hierarchy.

		self.mouseMovePos = event.pos()
		self.drawEnabled = True
		self.update()


	def mouseReleaseEvent(self, event):
		'''
		'''
		self.drawEnabled = False
		self.painter.eraseRect(self.rect())
		self.update()


	def mouseMoveEvent(self, event):
		'''
		'''
		self.mouseMovePos = event.pos()
		self.update()









#module name
print (__name__)

# -----------------------------------------------
# Notes
# -----------------------------------------------