# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from tentacle.events import OverlayFactoryFilter


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
	def drawPathStartPos(self):
		'''The starting widget ('returnArea') position stored in the drawPath.
		'''
		try:
			return self.drawPath[0][2]
		except IndexError as error:
			return None


	@property
	def drawPathEndPos(self):
		'''The ending widget position stored in the drawPath.
		Returns None if not found.
		'''
		try:
			return self.drawPath[-1][1]
		except IndexError as error:
			return None


	def getWidgetPos(self, widget):
		'''
		'''
		return next((wpos for w, wpos, cpos in self.drawPath if w==widget), None)


	def clearDrawPath(self):
		'''Reset the list of draw paths, while keeping the return point.
		'''
		del self.drawPath[1:]


	def addToDrawPath(self, w):
		'''Add a widget to the drawPath.
		It's current position, as well as the current cursor position, will be logged at the time of adding.
		'''
		w_pos = w.mapToGlobal(w.rect().center()) #the widget position before submenu change.
		self.drawPath.append((w, w_pos, QtGui.QCursor.pos())) #add the (<widget>, position) from the old ui to the path so that it can be re-created in the new ui (in the same position).
		self.removeFromPath(w)


	def removeFromPath(self, ui):
		'''Remove the last entry from the widget and draw paths for the given ui.

		:Parameters:
			ui (obj) = The ui to remove.
		'''
		uis = [w.ui for w, wpos, cpos in self.drawPath[1:]]
		# print ([w.name for w, wpos, cpos in self.drawPath[1:]])
		if ui in uis:
			i = uis[::-1].index(ui) #reverse the list and get the index of the last occurrence of name.
			# print (i, -i-1, ui.name, [(w.ui.name, cpos) for w, wpos, cpos in self.drawPath]) #debug
			del self.drawPath[-i-1:]


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
			w.move(QtCore.QPoint(self.pos().x()-w.width(), self.pos().y()-w.height())) #center the widget.
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


	def drawTangent(self, start_point, end_point, color=(115, 115, 115), background=(127, 127, 127, 0), ellipseSize=7):
		'''Draw a segment between two points.
		'''
		path = QtGui.QPainterPath()

		#create QColors from the given arguments.
		color = QtGui.QColor(*color)
		bgColor = QtGui.QColor(*background)
		#add ellipse if size is above 0.
		if ellipseSize:
			path.addEllipse(QtCore.QPointF(start_point), ellipseSize, ellipseSize)

		self.painter.fillRect(self.rect(), bgColor) #transparent overlay background.
		self.painter.setRenderHint(QtGui.QPainter.Antialiasing, self.antialiasing)
		self.painter.setBrush(color)
		self.painter.fillPath(path, color)
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

		self.mouseMovePos = curPos
		self.update()


	def mouseReleaseEvent(self, event):
		'''
		'''
		self.drawEnabled = False
		self.update()


	def mouseMoveEvent(self, event):
		'''
		'''
		self.drawEnabled = True
		self.mouseMovePos = event.pos()
		self.update()


	def showEvent(self, event):
		'''
		'''








if __name__ == '__main__':
	import sys
	overlay = Overlay()

	app = QtWidgets.QApplication.instance()
	sys.exit(app.exec_())






#module name
print (__name__)

# -----------------------------------------------
# Notes
# -----------------------------------------------


# Deprecated: -----------------------------------

	# def getDrawPathWidget(self, index):
	# 	'''
	# 	'''
	# 	try:
	# 		return self.drawPath[index][0]
	# 	except IndexError as error:
	# 		return None


	# def getDrawPathWidgetPos(self, index):
	# 	'''
	# 	'''
	# 	try:
	# 		return self.drawPath[index][1]
	# 	except IndexError as error:
	# 		return None


	# def getDrawPathCursorPos(self, index):
	# 	'''
	# 	'''
	# 	try:
	# 		return self.drawPath[index][2]
	# 	except IndexError as error:
	# 		return None