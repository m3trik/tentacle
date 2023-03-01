# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets


class Attributes(object):
	'''Methods for setting widget Attributes.
	'''

	def setAttributes(self, obj=None, **kwargs):
		'''Works with attributes passed in as a dict or kwargs.
		If attributes are passed in as a dict, kwargs are ignored.

		Parameters:
			obj (obj): the child obj or widgetAction to set attributes for. (default=self)
			**kwargs = The keyword arguments to set.
		'''
		if not kwargs: #if no attributes given.
			return

		if not obj:
			obj = self

		for attr, value in kwargs.items():
			try:
				getattr(obj, attr)(value)

			except:
				#print ('setAttributes:', attr, value)
				self.setCustomAttribute(obj, attr, value)


	def setCustomAttribute(self, w, attr, value):
		'''Attributes that throw an AttributeError in 'setAttributes' are sent here, where they can be assigned a value.
		Custom attributes can be set using a trailing underscore convention to aid readability, and differentiate them from standard attributes.

		Parameters:
			w (obj): The child widget or widgetAction to set attributes for.
			attr (str): Custom keyword attribute.
			value (str): The value corresponding to the given attr.

		attributes:
			copy_ (obj): The widget to copy attributes from.
			setSize_ (list): The size as an x and y value. ie. (40, 80)
			setWidth_ (int): The desired width.
			setHeight_ (int): The desired height.
			setPosition_ (QPoint)(str): Move to the given global position and center. valid: <QPoint>, 'cursor', 
			addMenu_ (QMenu) = Used for adding additional menus to a parent menu. ex. parentMenu = Menu(); childMenu = Menu('Create', addMenu_=parentMenu)
			insertSeparator_ (bool): Insert a line separater before the new widget.
			setLayoutDirection_ (str): Set the layout direction using a string value. ie. 'LeftToRight'
			setAlignment_ (str): Set the alignment using a string value. ie. 'AlignVCenter'
			setButtonSymbols_ (str): Set button symbols using a string value. ex. ie. 'PlusMinus'
			setMinMax_ (str): Set the min, max, and step value using a string value. ex. '.01-10 step.1'
			setCheckState_ (int): Set a tri-state checkbox state using an integer value. 0(unchecked), 1(partially checked), 2(checked).
		'''
		if attr=='copy_':
			w.setObjectName(value.objectName())
			w.resize(value.size())
			w.setText(value.text())
			w.setWhatsThis(value.whatsThis())

		elif attr=='setSize_':
			x, y = value
			w.resize(QtCore.QSize(x, y))

		elif attr=='setWidth_':
			w.setFixedWidth(value)
			# w.resize(value, w.size().height())

		elif attr=='setHeight_':
			w.setFixedHeight(value)
			# w.resize(w.size().width(), value)

		elif attr=='setPosition_':
			if value=='cursor':
				value = QtGui.QCursor.pos()
			w.move(w.mapFromGlobal(value - w.rect().center())) #move and center

		elif attr=='addMenu_':
			value.addMenu(w)

		elif attr=='insertSeparator_':
			if w.__class__.__name__=='QAction':
				self.insertSeparator(w)

		elif attr=='setLayoutDirection_':
			self.setAttributes(w, setLayoutDirection=getattr(QtCore.Qt, value))

		elif attr=='setAlignment_':
			self.setAttributes(w, setAlignment=getattr(QtCore.Qt, value))

		elif attr=='setButtonSymbols_':
			self.setAttributes(w, setButtonSymbols=getattr(QtWidgets.QAbstractSpinBox, value))

		#presets
		elif attr=='setMinMax_':
			self.setMinMax(w, value)

		elif attr=='setSpinBoxByValue_':
			self.setSpinBoxByValue(w, value)

		elif attr=='setCheckState_':
			state = {0:QtCore.Qt.CheckState.Unchecked, 1:QtCore.Qt.CheckState.PartiallyChecked, 2:QtCore.Qt.CheckState.Checked}
			w.setCheckState(state[value])

		else:
			print('Error: {} has no attribute {}'.format(w, attr))


	def setMinMax(self, spinbox, value):
		'''Set the minimum, maximum, and step values for a spinbox using a shorthand string value.

		Parameters:
			spinbox (obj): spinbox widget.
			value (str): value as shorthand string. ie. '0.00-100 step1'
		'''
		stepStr = value.split()[1].strip('step')
		step = float(stepStr)
		decimals = len(stepStr.split('.')[-1])

		spanStr = value.split('-')
		minimum = float(spanStr[0])
		maximum = float(spanStr[1].split()[0])

		if hasattr(spinbox, 'setDecimals'):
			self.setAttributes(spinbox, setDecimals=decimals)

		self.setAttributes(spinbox, setMinimum=minimum, setMaximum=maximum, setSingleStep=step, setButtonSymbols_='NoButtons')


	def setSpinBoxByValue(self, spinbox, value):
		'''Set a spinbox's attributes according to a given value.

		Parameters:
			spinbox (obj): spinbox widget.
			value (multi) = attribute value.
		'''
		maximum = spinbox.maximum()
		minimum = -maximum

		if isinstance(value, (int, bool)):
			step = spinbox.singleStep()

			if isinstance(value, bool):
				value = int(value)
				minimum = 0
				maximum = 1

			self.setAttributes(spinbox, setValue=value, setMinimum=minimum, setMaximum=maximum, 
				setSingleStep=step, setButtonSymbols_='NoButtons',)

		elif isinstance(value, float):
			decimals = str(value)[::-1].find('.') #get decimal places
			step = Attributes.moveDecimalPoint(1, -decimals)

			self.setAttributes(spinbox, setValue=value, setMinimum=minimum, setMaximum=maximum, 
				setSingleStep=step, setDecimals=decimals, setButtonSymbols_='NoButtons',)


	@staticmethod
	def moveDecimalPoint(num, decimal_places):
		'''Move the decimal place in a given number.

		Parameters:
			decimal_places (int): decimal places to move. (works only with values 0 and below.)
		
		Return:
			(float) the given number with it's decimal place moved by the desired amount.
		
		ex. moveDecimalPoint(11.05, -2) Return: 0.1105
		'''
		for _ in range(abs(decimal_places)):

			if decimal_places>0:
				num *= 10; #shifts decimal place right
			else:
				num /= 10.; #shifts decimal place left

		return float(num)









if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	sys.exit(app.exec_())



# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------

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

# depricated ------------------------------------------------------------------------







# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------