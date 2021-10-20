# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtGui, QtCore

from attributes import Attributes


'''
Promoting a widget in designer to use a custom class:
>	In Qt Designer, select all the widgets you want to replace, 
		then right-click them and select 'Promote to...'. 

>	In the dialog:
		Base Class:		Class from which you inherit. ie. QWidget
		Promoted Class:	Name of the class. ie. "MyWidget"
		Header File:	Path of the file (changing the extension .py to .h)  ie. myfolder.mymodule.mywidget.h

>	Then click "Add", "Promote", 
		and you will see the class change from "QWidget" to "MyWidget" in the Object Inspector pane.
'''


class WidgetLoadingIndicator(QtWidgets.QWidget, Attributes):
	''''''
	def __init__(self, parent=None, angle=0, timerId=-1, delay=50, displayedWhenStopped=False, color='black', **kwargs):
		'''
		'''
		super().__init__(parent)

		self.angle = angle
		self.timerId = timerId
		self.delay = delay
		self.displayedWhenStopped = displayedWhenStopped
		self.color = getattr(QtCore.Qt, color)

		self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
		self.setFocusPolicy(QtCore.Qt.NoFocus)

		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		# self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		value = QtGui.QCursor.pos()
		self.move(10,0) #fix for widget not moving to correct pos with setPosition_='cursor' attribute. #self.move(value - self.rect().center()) #move and center

		self.setAttributes(**kwargs)


	@property
	def isRunning(self):
		return (self.timerId != -1)


	def start(self, *args):
		self.angle = 0
		
		if self.timerId == -1:
		  self.timerId = self.startTimer(self.delay)
		  self.show()


	def stop(self):
		if self.timerId != -1:
		  self.killTimer(self.timerId)
		  
		self.timerId = -1
		self.update()
		self.hide()


	def setDelay(self, delay):
		if self.timerId != -1:
		  self.killTimer(self.timerId)
		  
		self.delay = delay
		
		if self.timerId != -1:
		  self.timerId = self.startTimer(self.delay)


	def timerEvent(self, event):
		self.angle = (self.angle + 30) % 360
		self.update()


	def sizeHint(self):
		return QtCore.QSize(100, 100)


	def paintEvent(self, event):
		if not self.displayedWhenStopped and not self.isRunning:
		  return

		width = min(self.width(), self.height())
		
		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		
		outerRadius = (width - 1) * 0.5
		innerRadius = (width - 1) * 0.5 * 0.38
		
		capsuleHeight = outerRadius - innerRadius
		capsuleWidth  = capsuleHeight *.23 if (width > 32) else capsuleHeight *.35
		capsuleRadius = capsuleWidth / 2
		
		for i in range(0, 12):
			color = QtGui.QColor(self.color)

		if self.isRunning:
			color.setAlphaF(1.0 - (i / 12.0))
		else:
			color.setAlphaF(0.2)

		painter.setPen(QtCore.Qt.NoPen)
		painter.setBrush(color)
		painter.save()
		painter.translate(self.rect().center())
		painter.rotate(self.angle - (i * 30.0))
		painter.drawRoundedRect(capsuleWidth * -0.5, (innerRadius + capsuleHeight) * -1, capsuleWidth, capsuleHeight, capsuleRadius, capsuleRadius)
		painter.restore()









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	w = WidgetLoadingIndicator(color='blue', start=True, setPosition_='cursor')
	# w.setDelay(70)
	# w.start()
	# w.stop()

	sys.exit(qApp.exec_())