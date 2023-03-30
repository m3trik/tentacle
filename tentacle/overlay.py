# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtCore, QtGui, QtWidgets


class OverlayFactoryFilter(QtCore.QObject):
	"""Handles paint events as an overlay on top of an existing widget.
	This class provides an event filter to relay events from the parent widget to the overlay.
	"""
	def eventFilter(self, widget, event):
		"""Relay events from the parent widget to the overlay.
		Captures various event types and forwards them to the respective methods.

		Parameters:
			widget (QWidget): The parent widget that the event filter is applied to.
			event (QEvent): The event that needs to be processed.
		
		Returns:
			bool: False if the widget is not a QWidget, True otherwise.
		"""
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



class Overlay(QtWidgets.QWidget, OverlayFactoryFilter):
	"""Handles paint events as an overlay on top of an existing widget.
	Inherits from OverlayFactoryFilter to relay events from the parent widget to the overlay.
	Maintains a list of draw paths to track the user's interactions.

	Parameters:
		parent (QWidget, optional): The parent widget for the overlay. Defaults to None.
		antialiasing (bool, optional): Set antialiasing for the tangent paint events. Defaults to False.
	"""
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	def __init__(self, parent=None, antialiasing=False):
		super().__init__(parent)

		self.antialiasing = antialiasing
		self.drawEnabled = False
		self.clearPainting = False

		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
		self.setAttribute(QtCore.Qt.WA_NoSystemBackground) #takes a single arg
		self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		self.setFocusPolicy(QtCore.Qt.NoFocus)

		self.fgcolor = QtGui.QColor(115, 115, 115)
		self.bgColor = QtGui.QColor(127, 127, 127, 0)
		self.penColor = QtGui.QPen(self.fgcolor, 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
		self.penStroke = QtGui.QPen(QtGui.QColor(0, 0, 0), 2, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)

		self.painter = QtGui.QPainter()

		self.app.focusChanged.connect(self.on_focus_changed)

		if parent:
			parent.installEventFilter(self)


	@property
	def path(self) -> list:
		"""Getter for the path attribute.
		If the attribute doesn't exist, it initializes an empty list.

		Returns:
			list: The list representing the draw path.
		"""
		try:
			return self._path

		except AttributeError:
			self._path = []
			return self._path


	@path.setter
	def path(self, new_path) -> None:
		"""Setter for the path attribute.

		Parameters:
			new_path (list): A list to be used as the new draw path.
		"""
		self._path = new_path


	@property
	def pathStartPos(self) -> QtCore.QPoint:
		"""Getter for the starting widget ('returnArea') position stored in the path.

		Returns:
			QPoint: The starting position of the draw path. Returns None if not found.
		"""
		try:
			return self.path[0][2]
		except IndexError:
			return None


	def getWidgetPos(self, target_widget):
		"""Get the position of the given widget within the path.

		Parameters:
			target_widget (QWidget): The widget whose position is to be retrieved.

		Returns:
			QPoint or None: The position of the target widget if it exists in the path, otherwise None.
		"""
		return next((widget_pos for widget, widget_pos, _ in self.path if widget == target_widget), None)


	def addToPath(self, ui, w):
		"""Add a widget to the path.
		It's current position, as well as the current cursor position, will be logged at the time of adding.

		Paramters:
			ui (QMainWindow): The UI to add.
			w (QWidget): The widget that called the given UI.
		"""
		w_pos = w.mapToGlobal(w.rect().center()) #the widget position before submenu change.
		self.path.append((w, w_pos, QtGui.QCursor.pos())) #add the (<widget>, position) from the old ui to the path so that it can be re-created in the new ui (in the same position).
		self.removeFromPath(ui) #remove entrys from widget and draw paths when moving back down levels in the ui.


	def removeFromPath(self, target_ui):
		"""Remove the last occurrence of the given UI from the widget path and update the path.

		Parameters:
			target_ui (QMainWindow): The UI to remove.
		"""
		last_occurrence_index = next( # Find the index of the last occurrence of the target UI in the path.
			(index + 1 for index, (widget, _, _) in reversed(list(enumerate(self.path[1:]))) if widget.ui == target_ui),
			None,
		)

		if last_occurrence_index is not None: # If the target UI is found, remove it and all elements after it.
			self.path = self.path[:last_occurrence_index]
		else:
			self.path = self.path[:]


	def clearPath(self, clear_all=False):
		"""Clear the widget path and paint events. By default, it keeps the return point.

		Parameters:
			clear_all (bool, optional): If True, clears the entire path including the return point. Default is False.
		"""
		if clear_all:
			self.path.clear()
			self.clearPaintEvents()
		else:
			self.path = self.path[:1]
			self.clearPaintEvents()


	def cloneWidgetsAlongPath(self, ui, return_func):
		"""Re-constructs the relevant widgets from the previous ui for the new ui, and positions them.
		Initializes the new widgets by adding them to the switchboard.
		The previous widget information is derived from the widget and draw paths.
		Sets up the onEnter signal of the Region widget to be connected to the returnToStart method.

		Parameters:
			ui (QMainWindow): The ui in which to copy the widgets to.
			return_func (func): A function to be called when the cursor enters the return area.
		"""
		#initialize the return area region for the UI.
		region_widget = self.initRegion(ui, self.pathStartPos)
		region_widget.onEnter.connect(return_func)
		region_widget.onEnter.connect(self.clearPath)

		def clone_widget(ui, prev_widget, position):
			new_widget = type(prev_widget)(ui)

			try:
				new_widget.setObjectName(prev_widget.objectName())
				new_widget.resize(prev_widget.size())
				new_widget.setWhatsThis(prev_widget.whatsThis())
				new_widget.setText(prev_widget.text())
				new_widget.move(new_widget.mapFromGlobal(position - new_widget.rect().center())) # set the position of the new widget in the new UI.
				new_widget.setVisible(True)
			except AttributeError:
				pass

			return new_widget


		new_widgets = tuple(map(
				lambda i: clone_widget(ui, i[0], i[1]),
				self.path[1:]
		))

		return new_widgets


	def clearPaintEvents(self):
		"""Clear paint events by disabling drawing and updating the overlay."""
		self.clearPainting = True
		self.update()


	def paintEvent(self, event):
		"""Handles the paint event for the overlay, drawing the tangent paths as needed.
		"""
		self.painter.begin(self)

		if self.clearPainting:
			self.painter.fillRect(self.rect(), self.bgColor)
			self.clearPainting = False
		elif self.drawEnabled:
			for i, (_, _, start_point) in enumerate(self.path):  # plot and draw the points in the path list.
				start_point = self.mapFromGlobal(start_point)
				try:
					end_point = self.mapFromGlobal(self.path[i+1][2])
				except IndexError:
					end_point = self.mouseMovePos  # after the list points are drawn, plot the current end_point, controlled by the mouse move event.

				self.drawTangent(start_point, end_point)

		self.painter.end()


	def drawTangent(self, start_point, end_point, ellipseSize=7):
		"""Draws a tangent line between two points with an ellipse at the start point.

		Parameters:
			start_point (QtCore.QPointF): The starting point of the line.
			end_point (QtCore.QPointF): The ending point of the line.
			ellipseSize (int, optional): The size of the ellipse at the starting point. Defaults to 7.
		"""
		if end_point.isNull():
			return

		linePath = QtGui.QPainterPath()
		ellipsePath = QtGui.QPainterPath()

		if ellipseSize:
			ellipsePath.addEllipse(start_point, ellipseSize, ellipseSize)

		self.painter.fillRect(self.rect(), self.bgColor)
		self.painter.setRenderHint(QtGui.QPainter.Antialiasing, self.antialiasing)

		# Draw the line
		linePath.moveTo(start_point)
		linePath.lineTo(end_point)

		# Combine the paths
		combinedPath = QtGui.QPainterPath()
		combinedPath.addPath(ellipsePath)
		combinedPath.addPath(linePath)

		# Create a stroker with the penStroke and stroke the combined path
		stroker = QtGui.QPainterPathStroker(self.penStroke)
		strokedPath = stroker.createStroke(combinedPath)

		# Draw the stroked path (outline)
		self.painter.setPen(self.penStroke)
		self.painter.setBrush(QtCore.Qt.NoBrush)
		self.painter.drawPath(strokedPath)

		# Draw the combined shape with the fill color
		self.painter.setPen(self.penColor)
		self.painter.setBrush(self.fgcolor)
		self.painter.drawPath(combinedPath)


	def initRegion(self, ui, *args, **kwargs):
		"""Initializes a Region widget with the specified properties and adds it to the given ui's central widget.

		Parameters:
			ui (QWidget): The parent QWidget in which the Region widget will be added.

		Return:
			Region: The initialized Region widget.
		"""
		from uitk.widgets.region import Region
		region_widget = Region(ui, *args, **kwargs)

		return region_widget


	def mousePressEvent(self, event):
		'''
		'''
		self.clearPath(clear_all=True)

		curPos = self.mapToGlobal(event.pos())
		self.path.append((None, None, curPos))  # maintain a list of widgets, their location, and cursor positions, as a path is plotted along the ui hierarchy.

		QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor)) # Change the cursor shape to a drag move cursor.

		self.mouseMovePos = curPos

		super().mousePressEvent(event)


	def mouseReleaseEvent(self, event):
		'''
		'''
		self.clearPath(clear_all=True)
		QtWidgets.QApplication.restoreOverrideCursor() # Restore the cursor to its default shape.

		super().mouseReleaseEvent(event)


	def mouseMoveEvent(self, event):
		'''
		'''
		self.drawEnabled = True
		self.mouseMovePos = event.pos()
		self.update()

		super().mouseMoveEvent(event)


	def on_focus_changed(self, old_widget, new_widget):
		'''
		'''
		if new_widget!=self:
			self.clearPath(clear_all=True)
			QtWidgets.QApplication.restoreOverrideCursor() # Restore the cursor to its default shape.

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__ == '__main__':
	import sys
	overlay = Overlay()

	sys.exit(overlay.app.exec_())

#module name
print (__name__)

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# Deprecated: -----------------------------------

	# def getPathWidget(self, index):
	# 	'''
	# 	'''
	# 	try:
	# 		return self.path[index][0]
	# 	except IndexError as error:
	# 		return None


	# def getPathWidgetPos(self, index):
	# 	'''
	# 	'''
	# 	try:
	# 		return self.path[index][1]
	# 	except IndexError as error:
	# 		return None


	# def getPathCursorPos(self, index):
	# 	'''
	# 	'''
	# 	try:
	# 		return self.path[index][2]
	# 	except IndexError as error:
	# 		return None