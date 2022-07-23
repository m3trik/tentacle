# !/usr/bin/python
# coding=utf-8
import sys, os.path

from PySide2 import QtCore



class Slots(QtCore.QObject):
	'''Provides methods that can be triggered by widgets in the ui.
	Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

	If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
	@Slot(result=int, float)
	def getFloatReturnInt(self, f):
		return int(f)
	'''
	def __init__(self, parent=None, *args, **kwargs):
		QtCore.QObject.__init__(self, parent)
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
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
	def getObjects(class_, objectNames, showError_=False):
		'''Get a list of corresponding objects from a shorthand string.
		ie. 's000,b002,cmb011-15' would return object list: [<s000>, <b002>, <cmb011>, <cmb012>, <cmb013>, <cmb014>, <cmb015>]

		:Parameters:
			class_ (obj) = Class object
			objectNames (str) = Names separated by ','. ie. 's000,b004-7'. b004-7 specifies buttons b004-b007.  
			showError (bool) = Show attribute error if item doesnt exist

		:Return:
			(list) of corresponding objects

		#ex call: getObjects(self.ui, 's000,b002,cmb011-15')
		'''
		objects=[]
		for name in Slots.unpackNames(objectNames):
			try:
				objects.append(getattr(class_, name)) #equivilent to:(self.current_ui().m000)

			except AttributeError as error:
				if showError_:
					print("slots: '{}.getObjects:' objects.append(getattr({}, {})) {}".format(__name__, class_, name, error))

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

		self.sb.setStyleSheet_(menu.childWidgets) # self.sb.parent().childEvents.addWidgets(self.sb.getUiName(), menu.childWidgets)
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
				[lambda state: self.rigging_ui.tb004.setText('Unlock Transforms' if state else 'Lock Transforms'), 
				lambda state: self.rigging_submenu_ui.tb004.setText('Unlock Transforms' if state else 'Lock Transforms')])
		'''
		if isinstance(widgets, (str)):
			try:
				widgets = Slots.getObjects(class_, widgets, showError_=True) #getObjects returns a widget list from a string of objectNames.
			except:
				widgets = Slots.getObjects(self.sb.getUi(), widgets, showError_=True)

		#if the variables are not of a list type; convert them.
		widgets = self.sb.list_(widgets)
		signals = self.sb.list_(signals)
		slots = self.sb.list_(slots)

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
			parentUi = self.sb.getUi(self.current_ui(), level=3)
			childUi = self.sb.getUi(self.current_ui(), level=2)
			args = [childUi, parentUi]

		for ui in args:
			for k in kwargs: #property_ ie. setUnChecked
				widgets = Slots.getObjects(ui, kwargs[k]) #getObjects returns a widget list from a string of objectNames.

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
			parentUi = self.sb.getUi(self.current_ui(), level=3)
			childUi = self.sb.getUi(self.current_ui(), level=2)
			args = args+(parentUi, childUi)

		for ui in args[1:]:
			widgets = Slots.getObjects(ui, args[0]) #getObjects returns a widget list from a string of objectNames.
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
				ui = self.current_ui()
			checkboxes = Slots.getObjects(ui, checkboxes)

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
				ui = self.current_ui()
			checkboxes = Slots.getObjects(ui, checkboxes, showError_=1)

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
		If you are looking to get multiple objects from a name string, call 'getObjects' directly instead.

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
				self.current_ui().progressBar.step1
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


	@staticmethod
	def areSimilar(a, b, tol=0.0):
		'''Check if the two numberical values are within a given tolerance.
		Supports nested lists.

		:parameters:
			a (obj)(list) = The first object(s) to compare.
			b (obj)(list) = The second object(s) to compare.
			tol (float) = The maximum allowed variation between the values.

		:return:
			(bool)
		'''
		list_ = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure that the arg is a list.

		func = lambda a, b: abs(a-b)<=tol if isinstance(a, (int, float)) else True if isinstance(a, (list, set, tuple)) and areSimilar(a, b, tol) else a==b
		return all(map(func, list_(a), list_(b)))



	# ----------------------------------------------------------------------------------------------------------
	' MATH '
	# ----------------------------------------------------------------------------------------------------------

	@staticmethod
	def getVectorFromTwoPoints(startPoint, endPoint):
		'''Get a directional vector from a given start and end point.

		:Parameters:
			startPoint (tuple) = The vectors start point as x, y, z values.
			endPoint (tuple) = The vectors end point as x, y, z values.

		:Return:
			(tuple) vector.
		'''
		x1, y1, z1 = startPoint
		x2, y2, z2 = endPoint

		result = (
			x1 - x2,
			y1 - y2,
			z1 - z2,
		)

		return result


	@staticmethod
	def clamp(x=0.0, minimum=0.0, maximum=1.0):
		'''Clamps the value x between min and max.

		:Parameters:
			x (float) = 
			minimum (float) = 
			maximum (float) = 

		:Return:
			(float)
		'''
		if minimum < maximum:
			realmin = minimum
			realmax = maximum
		else:
			realmin = maximum
			realmax = minimum

		if x < realmin:
			result = realmin
		elif x > realmax:
			result = realmax
		else:
			result = x

		return result


	@staticmethod
	def normalize(vector, amount=1):
		'''Normalize a vector

		:Parameters:
			vector (vector) = The vector to normalize.
			amount (float) = (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.
		
		:Return:
			(tuple)
		'''
		length = Slots.getMagnitude(vector)
		x, y, z = vector

		result = (
			x /length *amount,
			y /length *amount,
			z /length *amount
		)

		return result


	@staticmethod
	def normalized(vector3):
		'''Normalize a 3 dimensional vector using numpy.

		:Parameters:
			vector3 (vector) = A three point vector. ie. [-0.03484325110912323, 0.0, -0.5519591569900513]

		:Return:
			(vector)
		'''
		import numpy

		length = numpy.sqrt(sum(vector3[i] * vector3[i] for i in range(3)))
		result = [vector3[i] / length for i in range(3)]

		return result


	@staticmethod
	def getMagnitude(vector):
		'''Get the magnatude (length) of a given vector.

		:Parameters:
			vector (tuple) = Vector xyz values.

		:Return:
			(float)
		'''
		from math import sqrt

		x, y, z = vector
		length = sqrt(x**2 + y**2 + z**2)

		return length


	@staticmethod
	def dotProduct(v1, v2, normalizeInputs=False):
		'''Returns the dot product of two 3D float arrays.  If $normalizeInputs
		is set then the vectors are normalized before the dot product is calculated.

		:Parameters:
			v1 (list) = The first 3 point vector. 
			v2 (list) = The second 3 point vector.
			normalizeInputs (int) = Normalize v1, v2 before calculating the point float list.

		:Return:
			(float) Dot product of the two vectors.
		'''
		if normalizeInputs: #normalize the input vectors
			v1 = Slots.normalize(v1)
			v2 = Slots.normalize(v2)

		return sum((a*b) for a, b in zip(v1, v2)) #the dot product


	@staticmethod
	def crossProduct(v1, v2, normalizeInputs=False, normalizeResult=False):
		'''Given two float arrays of 3 values each, this procedure returns
		the cross product of the two arrays as a float array of size 3.

		:Parmeters:
			v1 (list) = The first 3 point vector. 
			v2 (list) = The second 3 point vector.
			normalizeInputs (bool) = Normalize v1, v2 before calculating the point float list.
			normalizeResult (bool) = Normalize the return value.

		:Return:
			(list) The cross product of the two vectors.
		'''
		if normalizeInputs: #normalize the input vectors
			v1 = Slots.normalize(v1)
			v2 = Slots.normalize(v2)

		cross = [ #the cross product
			v1[1]*v2[2] - v1[2]*v2[1],
			v1[2]*v2[0] - v1[0]*v2[2],
			v1[0]*v2[1] - v1[1]*v2[0]
		]

		if normalizeResult: #normalize the cross product result
			cross = Slots.normalize(cross)

		return cross


	@staticmethod
	def getCrossProduct(p1, p2, p3=None, normalize=0):
		'''Get the cross product of two vectors, using 2 vectors, or 3 points.

		:Parameters:
			p1 (vector)(point) = xyz point value as a tuple.
			p2 (vector)(point) = xyz point value as a tuple.
			p3 (point) = xyz point value as a tuple (used when working with point values instead of vectors).
			normalize (float) = (0) Do not normalize. (1) Normalize standard. (value other than 0 or 1) Normalize using the given float value as desired length.

		:Return:
			(tuple)
		'''
		if p3 is not None: #convert points to vectors and unpack.
			v1x, v1y, v1z = (
				p2[0] - p1[0],
				p2[1] - p1[1], 
				p2[2] - p1[2]
			)

			v2x, v2y, v2z = (
				p3[0] - p1[0], 
				p3[1] - p1[1], 
				p3[2] - p1[2]
			)
		else: #unpack vector.
			v1x, v1y, v1z = p1
			v2x, v2y, v2z = p2

		result = (
			(v1y*v2z) - (v1z*v2y), 
			(v1z*v2x) - (v1x*v2z), 
			(v1x*v2y) - (v1y*v2x)
		)

		if normalize:
			result = Slots.normalize(result, normalize)

		return result


	@staticmethod
	def movePointRelative(p, d, v=None):
		'''Move a point relative to it's current position.

		:Parameters:
			p (tuple) = A points x, y, z values.
			d (tuple)(float) = The distance to move. (use a float value when moving along a vector)
			v (tuple) = Optional: A vectors x, y, z values can be given to move the point along that vector.
		'''
		x, y, z = p

		if v is not None: #move along a vector if one is given.
			if not isinstance(d, (float, int)):
				print('# Warning: The distance parameter requires an integer or float value when moving along a vector. {} given. #'.format(type(d)))
			dx, dy, dz = Slots.normalize(v, d)
		else:
			dx, dy, dz = d

		result = (
			x + dx,
			y + dy,
			z + dz
		)

		return result


	@staticmethod
	def movePointAlongVectorTowardPoint(point, toward, vect, dist):
		'''Move a point along a given vector in the direction of another point.

		:Parameters:
			point (tuple) = The point to move given as (x,y,z).
			toward (tuple) = The point to move toward.
			vect (tuple) = A vector to move the point along.
			dist (float) = The linear amount to move the point.
		
		:Return:
			(tuple) point.
		'''
		for i in [dist, -dist]: #move in pos and neg direction, and determine which is moving closer to the reference point.
			p = Slots.movePointRelative(point, i, vect)
			d = Slots.getDistanceBetweenTwoPoints(p, toward)
			if d<=d:
				result = p

		return result


	@staticmethod
	def getDistanceBetweenTwoPoints(p1, p2):
		'''Get the vector between two points, and return it's magnitude.

		:Parameters:
			p1 (tuple) = Point 1.
			p2 (tuple) = Point 2.

		:Return:
			(float)
		'''
		from math import sqrt
		
		p1x, p1y, p1z = p1
		p2x, p2y, p2z = p2

		vX = p1x - p2x
		vY = p1y - p2y
		vZ = p1z - p2z

		vector = (vX, vY, vZ)
		length = Slots.getMagnitude(vector)

		return length


	@staticmethod
	def getCenterPointBetweenTwoPoints(p1, p2):
		'''Get the point in the middle of two given points.

		:Parameters:
			p1 (tuple) = Point as x,y,z values.
			p2 (tuple) = Point as x,y,z values.

		:Return:
			(tuple)
		'''
		Ax, Ay, Az = p1
		Bx, By, Bz = p2

		result = (
			(Ax+Bx) /2,
			(Ay+By) /2,
			(Az+Bz) /2
		)

		return result


	@staticmethod
	def getAngleFrom2Vectors(v1, v2, degree=False):
		'''Get an angle from two given vectors.

		:Parameters:
			v1 (point) = A vectors xyz values as a tuple.
			v2 (point) = A vectors xyz values as a tuple.
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(float)
		'''
		from math import acos, degrees

		def length(v):
			return (Slots.dotProduct(v, v))**0.5

		result = acos(Slots.dotProduct(v1, v2) / (length(v1) * length(v2)))

		if degree:
			result = round(degrees(result), 2)
		return result


	@staticmethod
	def getAngleFrom3Points(a, b, c, degree=False):
		'''Get the opposing angle from 3 given points.

		:Parameters:
			a (point) = A points xyz values as a tuple.
			b (point) = A points xyz values as a tuple.
			c (point) = A points xyz values as a tuple.
			degree (bool) = Convert the radian result to degrees.

		:Return:
			(float)
		'''
		from math import sqrt, acos, degrees

		ba = [aa-bb for aa,bb in zip(a,b)] #create vectors from points
		bc = [cc-bb for cc,bb in zip(c,b)]

		nba = sqrt(sum((x**2.0 for x in ba))) #normalize vector
		ba = [x/nba for x in ba]

		nbc = sqrt(sum((x**2.0 for x in bc)))
		bc = [x/nbc for x in bc]

		scalar = sum((aa*bb for aa,bb in zip(ba,bc))) #get scalar from normalized vectors

		angle = acos(scalar)#get the angle in radian

		if degree:
			angle = round(degrees(angle), 2)
		return angle


	@staticmethod
	def getTwoSidesOfASATriangle(a1, a2, s, unit='degrees'):
		'''Get the length of two sides of a triangle, given two angles, and the length of the side in-between.

		:Parameters:
			a1 (float) = Angle in radians or degrees. (unit flag must be set if value given in radians)
			a2 (float) = Angle in radians or degrees. (unit flag must be set if value given in radians)
			s (float) = The distance of the side between the two given angles.
			unit (str) = Specify whether the angle values are given in degrees or radians. (valid: 'radians', 'degrees')(default: degrees)

		:Return:
			(tuple)
		'''
		from math import sin, radians

		if unit=='degrees':
			a1, a2 = radians(a1), radians(a2)

		a3 = 3.14159 - a1 - a2

		result = (
			(s/sin(a3)) * sin(a1),
			(s/sin(a3)) * sin(a2)
		)

		return result


	@staticmethod
	def xyzRotation(theta, axis, rotation=[]):
		'''Get the rotation about the X,Y,Z axes (in rotation) given 
		an angle for rotation (in radians) and an axis about which to 
		do the rotation.

		:Parameters:
			theta (float) = 
			axis (list) = X, Y, Z float values.
			rotation (list) = 

		:Return:
			(list) 3 point rotation.
		'''
		import math

		#set up the xyzw quaternion values
		theta *= 0.5
		w = math.cos(theta)
		factor = math.sin(theta)
		axisLen2 = Slots.dotProduct(axis, axis, 0)

		if (axisLen2 != 1.0 and axisLen2 != 0.0):
			factor /= math.sqrt(axisLen2)
		x, y, z = factor * axis[0], factor * axis[1], factor * axis[2]

		#setup rotation in a matrix
		ww, xx, yy, zz = w*w, x*x, y*y, z*z
		s = 2.0 / (ww + xx + yy + zz)
		xy, xz, yz, wx, wy, wz = x*y, x*z, y*z, w*x, w*y, w*z
		matrix = [
			1.0 - s * (yy + zz),
			s * (xy + wz),
			s * (xz - wy),
			None, None,
			1.0 - s * (xx + zz),
			s * (yz + wx),
			None, None,
			s * (yz - wx),
			1.0 - s * (xx + yy)
		]

		#get x,y,z values for rotation
		cosB = math.sqrt(matrix[0]*matrix[0] + matrix[1]*matrix[1])
		if (cosB > 1.0e-10):
			pi = 3.14159265
	 
			a, b, c = solution1 = [
				math.atan2(matrix[6], matrix[10]),
				math.atan2(-matrix[2], cosB),
				math.atan2(matrix[1], matrix[0])
			]

			solution2 = [
				a + (pi if a < pi else -pi),
				(pi if b > -pi else -pi) - b,
				c + (pi if c < pi else -pi)
			]

			if sum([abs(solution2[0]), abs(solution2[1]), abs(solution2[2])]) < sum([abs(solution1[0]), abs(solution1[1]), abs(solution1[2])]):

				rotation = solution2
			else:
				rotation = solution1

		else:
			rotation = [
				math.atan2(-matrix[9], matrix[5]),
				math.atan2(-matrix[2], cosB),
				0.0
			]

		return rotation









#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


#depricated:

	# @classmethod
	# def message(cls, fn):
	# 	'''A decorator for messageBox.
	# 	Does not work with staticmethods.
	# 	'''
	# 	def wrapper(self, *args, **kwargs):
	# 		self.messageBox(fn(self, *args, **kwargs))
	# 	return wrapper


# @classmethod
# def sync(cls, fn):
# 	'''A decorator using the syncWidgets method.
# 	Does not work with staticmethods.
# 	'''
# 	def wrapper(self, *args, **kwargs):
# 		fn(self, *args, **kwargs) #execute the method normally.
# 		self.syncWidgets(fn.__name__) #Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.
# 	return wrapper





# def syncWidgets(self, widgets, from_ui=None, op=2, attributeTypes = {
# 	'isChecked':'setChecked', 'isDisabled':'setDisabled', 'isEnabled':'setEnabled', 
# 	'value':'setValue', 'text':'setText', 'icon':'setIcon',}):
# 	'''Keep widgets (having the same objectName) in sync across parent and child UIs.
# 	If the second widget does not have an attribute it will be silently skipped.
# 	Attributes starting with '__' are ignored.

# 	:Parameters:
# 		widgets (str)(list) = Widget objectNames as string or list of widget objects. string shorthand style: ie. 'b000-12,b022'
# 		from_ui (obj) = The ui to sync to. default is the current ui.
# 		op (int) = Which widgets to sync. 1) the given widgets, 2) the given widgets, and their parents, 3) all widgets.
# 		attributeTypes (dict) = Which attributes to sync. the dict contains gettr:settr pairs. ie. {'isChecked':'setChecked'}

# 	self.syncWidgets('chk002-6')
# 	'''
# 	if not from_ui:
# 		from_ui = self.sb.getUi()

# 	to_ui = self.sb.getUi(from_ui, level=2) if self.sb.getUiLevel(from_ui)==3 else self.sb.getUi(from_ui, level=3)#get either it's parent or submenu, depending on the given ui.

# 	if op in (0, 1): #
# 		if isinstance(widgets, (str)):
# 			from_widgets = Slots.getObjects(from_ui, widgets) #returns a list of widget objects from a string of objectNames.  ie. [<b000>, <b001>, ..] from 'b000-12,b022'
# 			to_widgets = Slots.getObjects(to_ui, widgets)
# 		else: #if list of widget objects:
# 			from_widgets = widgets
# 			to_widgets = [self.sb.getWidget(w.objectName(), ui=to_ui) for w in widgets]

# 	if op==1: #get parents of the given widgets
# 		from_widgets += [w.parent() for w in from_widgets]
# 		to_widgets += [w.parent() for w in to_widgets]

# 	else: #get all widgets
# 		if not op in (0, 1):
# 			from_widgets = self.sb.getWidget(ui=from_ui)
# 			to_widgets = self.sb.getWidget(ui=to_ui)

# 	from_widgets = {w.objectName():w for w in from_widgets}; #print ('from_widgets:', [i for i in from_widgets.values() if 'QRadioButton' in str(i)])
# 	to_widgets = {w.objectName():w for w in to_widgets}; #print ('to_widgets:  ', [i for i in to_widgets.values() if 'QRadioButton' in str(i)])

# 	_widgets = {from_widgets[i]:to_widgets[i] for i in from_widgets if i in to_widgets} #{<from_widget>:<to_widget>}
# 	for from_widget, to_widget in _widgets.items():

# 		attributes = {settr:getattr(from_widget, gettr)() 
# 						for gettr, settr in attributeTypes.items() 
# 							if hasattr(from_widget, gettr)} #get the from_widget's {attribute:value} ie. {'setChecked':True}
		
# 		[getattr(to_widget, attr)(value) 
# 			for attr, value in attributes.items() 
# 				if hasattr(to_widget, attr)] #set the second widget's attributes from the first.




	# def callMethod(self, name, method, *args, **kwargs):
	# 	'''
	# 	Call a method from a class outside of the current ui.
	# 	Momentarily switches to the ui of the given method for the call, before returning to the previous ui.

	# 	:Parameters:
	# 		name (str) = ui name.
	# 		method (str) = method name.
	# 	'''
	# 	ui = self.sb.getUi()
	# 	temp = self.sb.parent().setUi(name)
	# 	method = self.sb.getMethod(name, method)

	# 	try:
	# 		method(*args, **kwargs)
	# 	except Exception as error:
	# 		print(error)

	# 	self.sb.parent().setUi(ui)


	# def setSpinboxes(self, ui, spinboxes, attributes={}):
	# 	'''
	# 	Set multiple spinbox values and adjust for the data type.

	# 	:Parameters:
	# 		ui = <dynamic ui>
	# 		spinboxes (str)(list) = Packed spinbox names or object list. ie. 's001-4, s007' or [<s001>, <s002>, <s003>, <s004>, <s007>]
	# 		attributes = {'string key':value}

	# 	ex. self.setSpinboxes (self.ui, spinboxNames='s000-15', attributes={'width':1, 'length ratio':1, 'patches U':1, 'patches V':1})
	# 	ex. self.setSpinboxes (self.ui, spinboxNames='s000', attributes={'size':5} #explicit;  set single s000 with a label 'size' and value of 5
	# 	'''
	# 	if isinstance(spinboxes, (str)):
	# 		spinboxes = Slots.getObjects(ui, spinboxes) #get spinbox objects

	# 	#set values
	# 	for index, (key, value) in enumerate(attributes.items()):
	# 		spinboxes[index].blockSignals(True)
	# 		if isinstance(value, float):
	# 			if value<0:
	# 				spinboxes[index].setMinimum(-100)
	# 			decimals = str(value)[::-1].find('.') #get decimal places
	# 			spinboxes[index].setDecimals(decimals)
	# 			spinboxes[index].setPrefix(key+': ')
	# 			spinboxes[index].setValue(value)
	# 			spinboxes[index].setSuffix('')

	# 		elif isinstance(value, int):
	# 			if value<0:
	# 				spinboxes[index].setMinimum(-100)
	# 			spinboxes[index].setDecimals(0)
	# 			spinboxes[index].setPrefix(key+': ')
	# 			spinboxes[index].setValue(value)
	# 			spinboxes[index].setSuffix('')

	# 		elif isinstance(value, bool):
	# 			value = int(value)
	# 			spinboxes[index].setMinimum(0)
	# 			spinboxes[index].setMaximum(1)
	# 			spinboxes[index].setSuffix('<bool>')

	# 		# spinboxes[index].setEnabled(True)
	# 		spinboxes[index].blockSignals(False)


	# def setComboBox(self, comboBox, text):
	# 	'''
	# 	Set the given comboBox's index using a text string.
	# 	:Parameters:
	# 		comboBox (str) = comboBox name (will also be used as the methods name).
	# 		text (str) = text of the index to switch to.
	# 	'''
	# 	cmb = getattr(ui, comboBox)
	# 	method = getattr(self, comboBox)
	# 	cmb.currentIndexChanged.connect(method)
	# 	cmb.setCurrentIndex(cmb.findText(text))


	# @staticmethod
	# def msg(string, prefix='', inView=False):
	# 	'''
	# 	:Parameters:
	# 		string (str) = message string.
	# 	:Return:
	# 		(str) formatted string.
	# 	'''
	# 	if prefix:
	# 		prefix = prefix+':'
	# 	return '{}{}{}{}'.format('',prefix, string, '')


	# def getUiObject(self, widgets):
	# 	'''
	# 	Get ui objects from name strings.
	# 	:Parameters:
	# 		widgets (str) = ui object names
	# 	:Return:
	# 		list of corresponding ui objects	
	# 	'''
	# 	objects=[]
	# 	for name in self.unpackNames(widgets):
	# 		try:
	# 			w = getattr(self.ui, name)
	# 			objects.append(w)
	# 		except: pass
	# 	return objects





	# def setButtons(self, ui, checked=None, unchecked=None, enable=None, disable=None, visible=None, invisible=None):
	# 	'''
	# 	Set various states for multiple buttons at once.
	# 	:Parameters:
	# 		setButtons = dynamic ui object
	# 		checked/unchecked/enable/disable/visible/invisible (str) = the names of buttons to modify separated by ','. ie. 'b000,b001,b022'

	# 	ex.	setButtons(self.ui, disable='b000', unchecked='chk009-12', invisible='b015')
	# 	'''
	# 	if checked:
	# 		checked = Slots.getObjects(ui, checked)
	# 		[button.setChecked(True) for button in checked]
			
	# 	if unchecked:
	# 		unchecked = Slots.getObjects(ui, unchecked)
	# 		[button.setChecked(False) for button in unchecked]
			
	# 	if enable:
	# 		enable = Slots.getObjects(ui, enable)
	# 		[button.setEnabled(True) for button in enable]
			
	# 	if disable:
	# 		disable = Slots.getObjects(ui, disable)
	# 		[button.setDisabled(True) for button in disable]
			
	# 	if visible:
	# 		visible = Slots.getObjects(ui, visible)
	# 		[button.setVisible(True) for button in visible]
			
	# 	if invisible:
	# 		invisible = Slots.getObjects(ui, invisible)
	# 		[button.setVisible(False) for button in invisible]




# def setSpinboxes(ui, spinboxNames='s000-15', values=[]):
# 	'''
# 	:Parameters:	 ui=<dynamic ui>
# 			 spinboxNames (str) = spinbox string object names (used in place of the range argument). ie. 's001-4, s007'.  
# 						  default value will try to add values to spinboxes starting at s000 and add values in order skipping any spinboxes not found in the ui.
# 			 values=int or [(tuple) list] - tuple representing a string prefix label and value, and/or just a value. [(string prefix,int value)] ie. [("size",5), 20, ("width",8)]
	
# 	:Return: list of values without prefix
# 	ex. self.setSpinboxes (self.ui, values=[("width",1),("length ratio",1),("patches U",1),("patches V",1)]) #range. dict 'value's will be added to corresponding spinbox starting at s000 through s003.
# 	ex. self.setSpinboxes (self.ui, spinboxNames='s000', values=[('size',5)]) #explicit;  set single s000 with a label 'size' and value of 5. multiple spinboxes can be set this way. specify a range of spinboxes using 's010-18'.
# 	'''
# 	spinboxes = Slots.getObjects(ui, spinboxNames) #get spinbox objects

# 	#clear previous values
# 	for spinbox in spinboxes:
# 		spinbox.blockSignals(True) #block signals to keep from calling method on valueChanged
# 		spinbox.setPrefix('')
# 		spinbox.setValue(0)
# 		spinbox.setDisabled(True)
# 		spinbox.setVisible(False)

# 	values_=[] #list of values to return.
# 	#set new values
# 	for i, value in enumerate(values):
# 		spinboxes[i].setVisible(True)
# 		spinboxes[i].setEnabled(True)
# 		if type(value) == tuple:
# 			spinboxes[i].setPrefix(value[0]+': ')
# 			spinboxes[i].setValue(value[1])
# 			values_.append(value[1])
# 		else:
# 			spinboxes[i].setValue(value)
# 			values_.append(value)
# 		spinboxes[i].blockSignals(False)

# 	return values_


# packed_names = [n.strip() for n in objectNames.split(',') if '-' in n] #build list of all objectNames passed in containing '-'

# 		unpacked_names=[]
# 		for name in packed_names:
# 			name=name.split('-') #ex. split 'b000-8'
# 			prefix = name[0].strip('0123456789') #ex. split 'b' from 'b000'
# 			start = int(name[0].strip('abcdefghijklmnopqrstuvwxyz') or 0) #start range. #ex. '000' #converting int('000') returns None, if case; assign 0.
# 			stop = int(name[1])+1 #end range. #ex. '9' from 'b000-8' for range up to 9 but not including 9.
# 			unpacked_names.extend([str(prefix)+'000'[:-len(str(num))]+str(num) for num in range(start,stop)]) #build list of name strings within given range

# 		names = [n.strip() for n in objectNames.split(',') if '-' not in n] #all objectNames passed in not containing '-'
# 		if print_: print names+unpacked_names #used for debugging





	# @staticmethod
	# def comboBox(comboBox, items, title=None):
	# 	'''
	# 	Set comboBox items.
	# 	:Parameters:
	# 		comboBox = QComboBox object - list of items to fill the comboBox with
	# 		title (str) = optional value for the first index of the comboBox's list

	# 	:Return:
	# 		comboBox's current item list minus any title.
	# 	ex. comboBox (self.current_ui().cmb003, ["Import file", "Import Options"], "Import")
	# 	'''
	# 	comboBox.blockSignals(True) #to keep clear from triggering currentIndexChanged
	# 	index = comboBox.currentIndex() #get current index before refreshing list
	# 	comboBox.clear()
		
	# 	items_ = [str(i) for i in [title]+items if i]
	# 	comboBox.addItems(items_) 

	# 	comboBox.setCurrentIndex(index)
	# 	comboBox.blockSignals(False)

	# 	return items_