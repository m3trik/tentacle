# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super

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


class WidgetGifPlayer(QtWidgets.QWidget, Attributes):
	def __init__(self, parent=None, gif='loading_indicator.gif', **kwargs): 
		super().__init__(parent)
		'''
		'''
		self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
		self.setFocusPolicy(QtCore.Qt.NoFocus)

		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_SetStyle) #Indicates that the widget has a style of its own.

		self.label = QtWidgets.QLabel() #set up the player on a label.
		# expand and center the label
		self.label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
		self.label.setAlignment(QtCore.Qt.AlignCenter)     

		# positin the widgets
		main_layout = QtWidgets.QVBoxLayout() 
		main_layout.addWidget(self.label)
		self.setLayout(main_layout)

		self.movie = QtGui.QMovie(gif, QtCore.QByteArray(), self) 
		self.movie.setCacheMode(QtGui.QMovie.CacheAll) 
		self.movie.setSpeed(100) 
		self.label.setMovie(self.movie)

		# self.movie.start(); self.movie.stop() # display first frame
		self.label.resize(50, 50)
		self.move(QtGui.QCursor.pos() - self.rect().center())

		self.setAttributes(kwargs)


	def start(self):
		'''start animnation
		'''
		self.show()
		self.movie.start()

		
	def stop(self):
		'''stop the animation
		'''
		self.hide()
		self.movie.stop()


if __name__=='__main__':
	import sys
	app = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not app:
		app = QtWidgets.QApplication(sys.argv)

	player = WidgetGifPlayer() 

	player.start()
	app.exec_()