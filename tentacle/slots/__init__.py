# !/usr/bin/python
# coding=utf-8
import sys, os.path

from PySide2 import QtCore

from tools.math_tools import Math_tools



class Slots(QtCore.QObject, Math_tools):
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
		for k, v in kwargs.items():
			setattr(self, k, v)


	def hideMain(fn):
		'''A decorator that hides the stacked widget main window.
		'''
		def wrapper(self, *args, **kwargs):
			fn(self, *args, **kwargs) #execute the method normally.
			self.sb.parent().hide() #Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.
		return wrapper


	@staticmethod
	def getWidgets(class_, objectNames, showError_=False):
		'''Get a list of corresponding objects from a shorthand string.
		ie. 's000,b002,cmb011-15' would return object list: [<s000>, <b002>, <cmb011>, <cmb012>, <cmb013>, <cmb014>, <cmb015>]

		:Parameters:
			class_ (obj) = Class object
			objectNames (str) = Names separated by ','. ie. 's000,b004-7'. b004-7 specifies buttons b004-b007.  
			showError (bool) = Show attribute error if item doesnt exist

		:Return:
			(list) of corresponding objects

		#ex call: getWidgets(self.ui, 's000,b002,cmb011-15')
		'''
		objects=[]
		for name in Slots.unpackNames(objectNames):
			try:
				objects.append(getattr(class_, name)) #equivilent to:(self.sb.currentUi.m000)

			except AttributeError as error:
				if showError_:
					print("slots: '{}.getWidgets:' objects.append(getattr({}, {})) {}".format(__name__, class_, name, error))

		return objects


	@staticmethod
	def getAttributes(obj, include=[], exclude=[]):
		'''Get attributes for a given object.

		:Parameters:
			obj (obj) = The object to get the attributes of.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']

		:Return:
			(dict) {'string attribute': current value}
		'''
		return {attr:getattr(obj, attr) 
					for attr in obj.__dict__ 
						if not attr in exclude 
						and (attr in include if include else attr not in include)}


	@staticmethod
	def setAttributes(obj, attributes):
		'''Set attributes for a given object.

		:Parameters:
			obj (obj) = The object to set attributes for.
			attributes = dictionary {'string attribute': value} - attributes and their correponding value to set
		'''
		[setattr(obj, attr, value) 
			for attr, value in attributes.items() 
				if attr and value]


	def objAttrWindow(self, obj, attributes, checkableLabel=False, fn=None, fn_args=[]):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (obj) = The object to get the attributes of.
			attributes (dict) = {'attribute':<value>}
			checkableLabel (bool) = Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. Init.setParameterValuesMEL
			fn_args (list) = Any additonal args to pass to fn.
				The first parameter of fn is always the given object, and the last parameter is the attribute:value pairs as a dict.

		:Return:
			(obj) the menu widget. (use menu.childWidgets to get the menu's child widgets.)

		ex. call: self.objAttrWindow(node, attrs, fn=Init.setParameterValuesMEL, fn_args='transformLimits')
		ex. call: self.objAttrWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)
		'''
		import ast

		fn = fn if fn else self.setAttributes
		fn_args = fn_args if isinstance(fn_args, (list, tuple, set)) else [fn_args]

		try: #get the objects name to as the window title:
			title = obj.name()
		except:
			try:
				title = obj.name
			except:
				title = str(obj)

		menu = self.sb.Menu(self.sb.parent(), menu_type='form', padding=2, title=title, position='cursorPos')

		for k, v in attributes.items():

			if isinstance(v, (float, int, bool)):
				if type(v)==int or type(v)==bool:
					s = menu.add('QSpinBox', label=k, checkableLabel=checkableLabel, setSpinBoxByValue_=v)

				elif type(v)==float:
					v = float(f'{v:g}') ##remove any trailing zeros from the float value.
					s = menu.add('QDoubleSpinBox', label=k, checkableLabel=checkableLabel, setSpinBoxByValue_=v, setDecimals=3)

				s.valueChanged.connect(lambda value, attr=k: fn(obj, *fn_args, {attr:value}))

			else: #isinstance(v, (list, set, tuple)):
				w = menu.add('QLineEdit', label=k, checkableLabel=checkableLabel, setText=str(v))
				w.returnPressed.connect(lambda w=w, attr=k: fn(obj, *fn_args, {attr:ast.literal_eval(w.text())}))

		self.sb.setStyleSheet_(menu.childWidgets)
		menu.show()

		return menu


	def connect_(self, widgets, signals, slots, class_=None):
		'''Connect multiple signals to multiple slots at once.

		:Parameters:
			widgets (str)(obj)(list) = ie. 'chk000-2' or [tb.contextMenu.chk000, tb.contextMenu.chk001]
			signals (str)(list) = ie. 'toggled' or ['toggled']
			slots (obj)(list) = ie. self.cmb002 or [self.cmb002]
			class_ (obj)(list) = if the widgets arg is given as a string, then the class_ it belongs to can be explicitly given. else, the current ui will be used.

		ex call: self.connect_('chk000-2', 'toggled', self.cmb002, tb.contextMenu)
		*or self.connect_([tb.contextMenu.chk000, tb.contextMenu.chk001], 'toggled', self.cmb002)
		*or self.connect_(tb.contextMenu.chk015, 'toggled', 
				[lambda state: self.sb.rigging.tb004.setText('Unlock Transforms' if state else 'Lock Transforms'), 
				lambda state: self.sb.rigging_submenu.tb004.setText('Unlock Transforms' if state else 'Lock Transforms')])
		'''
		list_ = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure the arg is a list.

		if isinstance(widgets, (str)):
			try:
				widgets = Slots.getWidgets(class_, widgets, showError_=True) #getWidgets returns a widget list from a string of objectNames.
			except Exception as error:
				widgets = Slots.getWidgets(self.sb.currentUi, widgets, showError_=True)

		#if the variables are not of a list type; convert them.
		widgets = list_(widgets)
		signals = list_(signals)
		slots = list_(slots)

		for widget in widgets:
			for signal in signals:
				signal = getattr(widget, signal)
				for slot in slots:
					signal.connect(slot)


	def toggleWidgets(self, *args, **kwargs):
		'''Set multiple boolean properties, for multiple widgets, on multiple ui's at once.

		:Parameters:
			*args = dynamic ui object/s. If no ui's are given, then the current UI will be used.
			*kwargs = keyword: - the property to modify. ex. setChecked, setUnChecked, setEnabled, setDisabled, setVisible, setHidden
					value: string of objectNames - objectNames separated by ',' ie. 'b000-12,b022'

		ex.	self.toggleWidgets(<ui1>, <ui2>, setDisabled='b000', setUnChecked='chk009-12', setVisible='b015,b017')
		'''
		if not args:
			parentUi = self.sb.currentUi.level3
			childUi = self.sb.currentUi.level2
			args = [childUi, parentUi]

		for ui in args:
			for k in kwargs: #property_ ie. setUnChecked
				widgets = Slots.getWidgets(ui, kwargs[k]) #getWidgets returns a widget list from a string of objectNames.

				state = True
				if 'Un' in k: #strips 'Un' and sets the state from True to False. ie. 'setUnChecked' becomes 'setChecked' (False)
					k = k.replace('Un', '')
					state = False

				[getattr(w, k)(state) for w in widgets] #set the property state for each widget in the list.


	def setWidgetKwargs(self, *args, **kwargs):
		'''Set multiple properties, for multiple widgets, on multiple ui's at once.

		:Parameters:
			*args = arg [0] (str) String of objectNames. - objectNames separated by ',' ie. 'b000-12,b022'
					arg [1:] dynamic ui object/s.  If no ui's are given, then the parent and child uis will be used.
			*kwargs = keyword: - the property to modify. ex. setText, setValue, setEnabled, setDisabled, setVisible, setHidden
					value: - intended value.

		ex.	self.setWidgetKwargs('chk003', <ui1>, <ui2>, setText='Un-Crease')
		'''
		if not args[1:]:
			parentUi = self.sb.currentUi.level3
			childUi = self.sb.currentUi.level2
			args = args+(parentUi, childUi)

		for ui in args[1:]:
			widgets = Slots.getWidgets(ui, args[0]) #getWidgets returns a widget list from a string of objectNames.
			for property_, value in kwargs.items():
				[getattr(w, property_)(value) for w in widgets] #set the property state for each widget in the list.


	def setAxisForCheckBoxes(self, checkboxes, axis, ui=None):
		'''Set the given checkbox's check states to reflect the specified axis.

		:Parameters:
			checkboxes (str)(list) = 3 or 4 (or six with explicit negative values) checkboxes.
			axis (str) = Axis to set. Valid text: '-','X','Y','Z','-X','-Y','-Z' ('-' indicates a negative axis in a four checkbox setup)

		ex call: self.setAxisForCheckBoxes('chk000-3', '-X') #optional ui arg for the checkboxes
		'''
		if isinstance(checkboxes, (str)):
			if ui is None:
				ui = self.sb.currentUi
			checkboxes = Slots.getWidgets(ui, checkboxes)

		prefix = '-' if '-' in axis else '' #separate the prefix and axis
		coord = axis.strip('-')

		for chk in checkboxes:
			if any([chk.text()==prefix, chk.text()==coord, chk.text()==prefix+coord]):
				chk.setChecked(True)


	def getAxisFromCheckBoxes(self, checkboxes, ui=None):
		'''Get the intended axis value as a string by reading the multiple checkbox's check states.

		:Parameters:
			checkboxes (str)(list) = 3 or 4 (or six with explicit negative values) checkboxes. Valid text: '-','X','Y','Z','-X','-Y','-Z' ('-' indicates a negative axis in a four checkbox setup)

		:Return:
			(str) axis value. ie. '-X'		

		ex call: self.getAxisFromCheckBoxes('chk000-3')
		'''
		if isinstance(checkboxes, (str)):
			if ui is None:
				ui = self.sb.currentUi
			checkboxes = Slots.getWidgets(ui, checkboxes, showError_=1)

		prefix=axis=''
		for chk in checkboxes:
			if chk.isChecked():
				if chk.text()=='-':
					prefix = '-'
				else:
					axis = chk.text()
		# print ('prefix:', prefix, 'axis:', axis) #debug
		return prefix+axis #ie. '-X'


	global cycleDict
	cycleDict={}
	@staticmethod
	def cycle(sequence, name=None, query=False):
		'''Toggle between numbers in a given sequence.
		Used for maintaining toggling sequences for multiple objects simultaniously.
		Each time this function is called, it returns the next number in the sequence
		using the name string as an identifier key.
		
		:Parameters:
			sequence (list) = sequence to cycle through. ie. [1,2,3].
			name (str) = identifier. used as a key to get the sequence value from the dict.
			
		ex. cycle([0,1,2,3,4], 'componentID')
		'''
		try:
			if query: #return the value without changing it.
				return cycleDict[name][-1] #get the current value ie. 0

			value = cycleDict[name] #check if key exists. if so return the value. ie. value = [1,2,3]
		
		except KeyError: #else create sequence list for the given key
			cycleDict[name] = [i for i in sequence] #ie. {name:[1,2,3]}

		value = cycleDict[name][0] #get the current value. ie. 1
		cycleDict[name] = cycleDict[name][1:]+[value] #move the current value to the end of the list. ie. [2,3,1]
		return value #return current value. ie. 1


	@staticmethod
	def unpackNames(nameString):
		'''Get a list of individual names from a single name string.
		If you are looking to get multiple objects from a name string, call 'getWidgets' directly instead.

		:Parameters:
			nameString = string consisting of widget names separated by commas. ie. 'v000, b004-6'

		:Return:
			unpacked names. ie. ['v000','b004','b005','b006']

		ex. call: unpackNames('chk021-23, 25, tb001')
		'''
		packed_names = [n.strip() for n in nameString.split(',') #build list of all widgets passed in containing '-' 
							if '-' in n or n.strip().isdigit()]

		otherNames = [n.strip() for n in nameString.split(',') #all widgets passed in not containing '-'
							if '-' not in n and not n.strip().isdigit()]

		unpacked_names=[] #unpack the packed names:
		for name in packed_names:
			if '-' in name:
				name = name.split('-') #ex. split 'b000-8'
				prefix = name[0].strip('0123456789') #ex. split 'b' from 'b000'
				start = int(name[0].strip('abcdefghijklmnopqrstuvwxyz') or 0) #start range. #ex. '000' #converting int('000') returns None, if case; assign 0.
				stop = int(name[1])+1 #end range. #ex. '8' from 'b000-8' becomes 9, for range up to 9 but not including 9.
				unpacked_names.extend([str(prefix)+'000'[:-len(str(num))]+str(num) for num in range(start,stop)]) #build list of name strings within given range
				last_name = name
				last_prefix = prefix
			else:
				num = name
				unpacked_names.extend([str(last_prefix)+'000'[:-len(str(num))]+str(num)])

		return otherNames+unpacked_names


	@staticmethod
	def collapseList(list_, limit=None, compress=True, returnAsString=True):
		'''Convert a list of integers to a collapsed sequential string format.
		ie. [19,22,23,24,25,26] to ['19', '22..26']

		:Parameters:
			list_ (list) = A list of integers
			compress (bool) = Trim redundant chars from the second half of a compressed set. ie. ['19', '22-32', '1225-6'] from ['19', '22..32', '1225..1226']
			returnAsString (bool) = Return a single string value instead of a list.

		:Return:
			(list) or (str) if 'returnAsString'.
		'''
		ranges=[]
		for x in map(str, list_): #make sure the list is made up of strings.
			if not ranges:
				ranges.append([x])
			elif int(x)-prev_x==1:
				ranges[-1].append(x)
			else:
				ranges.append([x])
			prev_x = int(x)

		if compress: #style: ['19', '22-32', '1225-6']
			collapsedList = ['-'.join([r[0], r[-1][len(str(r[-1]))-len(str((int(r[-1])-int(r[0])))):]] #find the difference and use that value to further trim redundant chars from the string
								if len(r) > 1 else r) 
									for r in ranges]

		else: #style: ['19', '22..32', '1225..1226']
			collapsedList = ['..'.join([r[0], r[-1]] 
								if len(r) > 1 else r) 
									for r in ranges]

		if limit and len(collapsedList)>limit:
			l = collapsedList[:limit]
			l.append('...')
			collapsedList = l
		
		if returnAsString:
			collapsedList = ', '.join(collapsedList)

		return collapsedList


	@staticmethod
	def bitArrayToList(bitArray):
		'''Convert a binary bitArray to a python list.

		:Parameters:
			bitArray=bit array
				*or list of bit arrays

		:Return:
			(list) containing values of the indices of the on (True) bits.
		'''
		if len(bitArray):
			if type(bitArray[0])!=bool: #if list of bitArrays: flatten
				list_=[]
				for array in bitArray:
					list_.append([i+1 for i, bit in enumerate(array) if bit==1])
				return [bit for array in list_ for bit in array]

			return [i+1 for i, bit in enumerate(bitArray) if bit==1]


	def invertOnModifier(self, value):
		'''Invert a numerical or boolean value if the alt key is pressed.

		:Parameters:
			value (int, float, bool) = The value to invert.
		
		:Return:
			(int, float, bool)
		'''
		modifiers = self.sb.parent().qApp.keyboardModifiers()
		if not modifiers in (QtCore.Qt.AltModifier, QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
			return value

		if type(value) in (int, float):
			result = abs(value) if value<0 else -value
		elif type(value)==bool:
			result = True if value else False

		return result


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
			from widgets.messageBox import MessageBox
			self._messageBox = MessageBox(self.sb.parent().parent())

		self._messageBox.location = location
		self._messageBox.timeout = timeout

		from re import sub
		print(''+sub('<.*?>', '', string)+'') #strip everything between '<' and '>' (html tags)

		self._messageBox.setText(string)
		self._messageBox.exec_()









#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# depricated:
