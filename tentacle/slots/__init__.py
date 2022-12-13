# !/usr/bin/python
# coding=utf-8
import sys, os.path

from PySide2 import QtCore


class Slots(QtCore.QObject):
	'''Provides methods that can be triggered by widgets in the ui.
	Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

	If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
	@Slot(result=int, float)
	ex. def getFloatReturnInt(self, f):
			return int(f)
	'''
	def __init__(self, parent=None, *args, **kwargs):
		QtCore.QObject.__init__(self, parent)
		'''
		'''
		for a, v in kwargs.items():
			setattr(self, a, v)


	def hideMain(fn):
		'''A decorator that hides the stacked widget main window.
		'''
		def wrapper(self, *args, **kwargs):
			fn(self, *args, **kwargs) #execute the method normally.
			self.sb.parent().hide() #Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.
		return wrapper


	def objAttrWindow(self, obj, checkableLabel=False, fn=None, fn_args=[], **attributes):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (obj) = The object to get the attributes of.
			checkableLabel (bool) = Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. setParameterValuesMEL
					The first parameter of fn is always the given object. ex. fn(obj, {'attr':<value>})
			fn_args (list) = Any additonal args to pass to fn.
			attributes (kwargs) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from mtk.getAttributesMEL for the given obj.

		:Return:
			(obj) the menu widget. (use menu.childWidgets to get the menu's child widgets.)

		ex. call: self.objAttrWindow(node, attrs, fn=mtk.setParameterValuesMEL, fn_args='transformLimits')
		ex. call: self.objAttrWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)
		'''
		import ast
		from tentacle.slots import tk

		fn = fn if fn else tk.setAttributes
		fn_args = tk.itertk.makeList(fn_args) #assure that fn_args is a list.

		try: #get the objects name to as the window title:
			title = obj.name()
		except:
			try:
				title = obj.name
			except:
				title = str(obj)

		menu = self.sb.Menu(self.sb.parent(), menu_type='form', padding=2, title=title, position='cursorPos')

		for a, v in attributes.items():

			if isinstance(v, (float, int, bool)):
				if type(v)==int or type(v)==bool:
					s = menu.add('QSpinBox', label=a, checkableLabel=checkableLabel, setSpinBoxByValue_=v)

				elif type(v)==float:
					v = float(f'{v:g}') ##remove any trailing zeros from the float value.
					s = menu.add('QDoubleSpinBox', label=a, checkableLabel=checkableLabel, setSpinBoxByValue_=v, setDecimals=3)

				s.valueChanged.connect(lambda v, a=a: fn(obj, *fn_args, **{a:v}))

			else: #isinstance(v, (list, set, tuple)):
				w = menu.add('QLineEdit', label=a, checkableLabel=checkableLabel, setText=str(v))
				w.returnPressed.connect(lambda w=w, a=a: fn(obj, *fn_args, **{a:ast.literal_eval(w.text())}))

		self.sb.setStyle(menu.childWidgets)
		menu.show()

		return menu


	def messageBox(self, string, messageType='', location='topMiddle', timeout=1):
		'''Spawns a message box with the given text.
		Supports HTML formatting.
		Prints a formatted version of the given string to console, stripped of html tags, to the console.

		:Parameters:
			messageType (str) = The message context type. ex. 'Error', 'Warning', 'Note', 'Result'
			location (str)(point) = move the messagebox to the specified location. Can be given as a qpoint or string value. default is: 'topMiddle'
			timeout (int) = time in seconds before the messagebox auto closes.
		'''
		if messageType:
			string = '{}: {}'.format(messageType.capitalize(), string)

		if not hasattr(self, '_messageBox'):
			from tentacle.ui.widgets.messageBox import MessageBox
			self._messageBox = MessageBox(self.sb.parent().parent())

		self._messageBox.location = location
		self._messageBox.timeout = timeout

		from re import sub
		print(''+sub('<.*?>', '', string)+'') #strip everything between '<' and '>' (html tags)

		self._messageBox.setText(string)
		self._messageBox.exec_()


	# @classmethod
	# def progress(cls, fn):
	# 	'''A decorator for progressBar.
	#	Does not work with staticmethods.
	# 	'''
	# 	def wrapper(self, *args, **kwargs):
	# 		self.progressBar(fn(self, *args, **kwargs))
	# 	return wrapper

	def progressBar(self):
		'''
		'''
		try:
			return self._progressBar

		except AttributeError as error:
			from widgets.progressBar import ProgressBar
			self._progressBar = ProgressBar(self.sb.parent())

			try:
				self.sb.currentUi.progressBar.step1
			except AttributeError:
				pass

			return self._progressBar


	def invertOnModifier(self, value):
		'''Invert a numerical or boolean value if the alt key is pressed.

		:Parameters:
			value (int, float, bool) = The value to invert.
		
		:Return:
			(int, float, bool)
		'''
		modifiers = self.sb.parent().app.keyboardModifiers()
		if not modifiers in (QtCore.Qt.AltModifier, QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
			return value

		if type(value) in (int, float):
			result = abs(value) if value<0 else -value
		elif type(value)==bool:
			result = True if value else False

		return result

# -----------------------------------------------









#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# depricated: -----------------------------------
