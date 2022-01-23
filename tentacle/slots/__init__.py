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
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		for k, v in kwargs.items():
			setattr(self, k, v)


	def hideMain(fn):
		'''A decorator that hides the stacked widget main window.
		'''
		def wrapper(self, *args, **kwargs):
			fn(self, *args, **kwargs) #execute the method normally.
			self.tcl.hide() #Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.
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
				print("slots: 'getObjects:' objects.append(getattr({0}, {1})) {2}".format(class_, name, error)) if showError_ else None

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
			for attr, value in attributes.iteritems() 
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

		menu = self.tcl.wgts.Menu(self.tcl, menu_type='form', padding=2, title=title, position='cursorPos')

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

		self.tcl.setStyleSheet_(menu.childWidgets) # self.tcl.childEvents.addWidgets(self.tcl.sb.getUiName(), menu.childWidgets)
		menu.show()

		return menu


	def connect_(self, widgets, signals, slots, class_=None):
		'''Connect multiple signals to multiple slots at once.

		:Parameters:
			widgets (str)(obj)(list) = ie. 'chk000-2' or [tb.contextMenu.chk000, tb.contextMenu.chk001]
			signals (str)(list) = ie. 'toggled' or ['toggled']
			slots (obj)(list) = ie. self.cmb002 or [self.cmb002]
			class_ (obj)(list) = if the widgets arg is given as a string, then the class_ it belongs to can be explicitly given. else, the current ui will be used.

		ex call: self.connect_('chk000-2', 'toggled', self.cmb002, tb.contextMenu.
		*or self.connect_([tb.contextMenu.chk000, tb.contextMenu.chk001], 'toggled', self.cmb002)
		*or self.connect_(tb.contextMenu.chk015, 'toggled', 
				[lambda state: self.rigging_ui.tb004.setText('Unlock Transforms' if state else 'Lock Transforms'), 
				lambda state: self.rigging_submenu_ui.tb004.setText('Unlock Transforms' if state else 'Lock Transforms')])
		'''
		if isinstance(widgets, (str)):
			try:
				widgets = Slots.getObjects(class_, widgets, showError_=True) #getObjects returns a widget list from a string of objectNames.
			except:
				widgets = Slots.getObjects(self.tcl.sb.getUi(), widgets, showError_=True)

		#if the variables are not of a list type; convert them.
		widgets = self.tcl.sb.list_(widgets)
		signals = self.tcl.sb.list_(signals)
		slots = self.tcl.sb.list_(slots)

		for widget in widgets:
			for signal in signals:
				signal = getattr(widget, signal)
				for slot in slots:
					signal.connect(slot)


	@classmethod
	def sync(cls, fn):
		'''A decorator using the syncWidgets method.
		Does not work with staticmethods.
		'''
		def wrapper(self, *args, **kwargs):
			fn(self, *args, **kwargs) #execute the method normally.
			self.syncWidgets(fn.__name__) #Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.
		return wrapper

	def syncWidgets(self, widgets, from_ui=None, op=2, attributeTypes = {
		'isChecked':'setChecked', 'isDisabled':'setDisabled', 'isEnabled':'setEnabled', 
		'value':'setValue', 'text':'setText', 'icon':'setIcon',}):
		'''
		Keep widgets (having the same objectName) in sync across parent and child UIs.
		If the second widget does not have an attribute it will be silently skipped.
		Attributes starting with '__' are ignored.

		:Parameters:
			widgets (str)(list) = Widget objectNames as string or list of widget objects. string shorthand style: ie. 'b000-12,b022'
			from_ui (obj) = The ui to sync to. default is the current ui.
			op (int) = Which widgets to sync. 1) the given widgets, 2) the given widgets and their parents, 3) all widgets.
			attributeTypes (dict) = Which attributes to sync. the dict contains gettr:settr pairs. ie. {'isChecked':'setChecked'}

		self.syncWidgets('chk002-6')
		'''
		if not from_ui:
			from_ui = self.tcl.sb.getUi()

		to_ui = self.tcl.sb.getUi(from_ui, level=2) if self.tcl.sb.getUiLevel(from_ui)==3 else self.tcl.sb.getUi(from_ui, level=3)#get either it's parent or submenu, depending on the given ui.

		if op in (0, 1): #
			if isinstance(widgets, (str)):
				from_widgets = Slots.getObjects(from_ui, widgets) #returns a list of widget objects from a string of objectNames.  ie. [<b000>, <b001>, ..] from 'b000-12,b022'
				to_widgets = Slots.getObjects(to_ui, widgets)
			else: #if list of widget objects:
				from_widgets = widgets
				to_widgets = [self.tcl.sb.getWidget(w.objectName(), ui=to_ui) for w in widgets]

		if op==1: #get parents of the given widgets
			from_widgets += [w.parent() for w in from_widgets]
			to_widgets += [w.parent() for w in to_widgets]

		else: #get all widgets
			if not op in (0, 1):
				from_widgets = self.tcl.sb.getWidget(ui=from_ui)
				to_widgets = self.tcl.sb.getWidget(ui=to_ui)

		from_widgets = {w.objectName():w for w in from_widgets}; #print ('from_widgets:', [i for i in from_widgets.values() if 'QRadioButton' in str(i)])
		to_widgets = {w.objectName():w for w in to_widgets}; #print ('to_widgets:  ', [i for i in to_widgets.values() if 'QRadioButton' in str(i)])

		_widgets = {from_widgets[i]:to_widgets[i] for i in from_widgets if i in to_widgets} #{<from_widget>:<to_widget>}
		for from_widget, to_widget in _widgets.items():

			attributes = {settr:getattr(from_widget, gettr)() 
							for gettr, settr in attributeTypes.items() 
								if hasattr(from_widget, gettr)} #get the from_widget's {attribute:value} ie. {'setChecked':True}
			
			[getattr(to_widget, attr)(value) 
				for attr, value in attributes.items() 
					if hasattr(to_widget, attr)] #set the second widget's attributes from the first.


	def toggleWidgets(self, *args, **kwargs):
		'''Set multiple boolean properties, for multiple widgets, on multiple ui's at once.

		:Parameters:
			*args = dynamic ui object/s. If no ui's are given, then the parent and child uis will be used.
			*kwargs = keyword: - the property to modify. ex. setChecked, setUnChecked, setEnabled, setDisabled, setVisible, setHidden
					value: string of objectNames - objectNames separated by ',' ie. 'b000-12,b022'

		ex.	self.toggleWidgets(<ui1>, <ui2>, setDisabled='b000', setUnChecked='chk009-12', setVisible='b015,b017')
		'''
		if not args:
			childUi = self.tcl.sb.getUi(level=2)
			parentUi = self.tcl.sb.getUi(level=3)
			args = [parentUi, childUi]

		for ui in args:
			for property_ in kwargs: #property_ ie. setUnChecked
				widgets = Slots.getObjects(ui, kwargs[property_]) #getObjects returns a widget list from a string of objectNames.

				state = True
				if 'Un' in property_: #strips 'Un' and sets the state from True to False. ie. 'setUnChecked' becomes 'setChecked' (False)
					property_ = property_.replace('Un', '')
					state = False

				[getattr(w, property_)(state) for w in widgets] #set the property state for each widget in the list.


	def setWidgetKwargs(self, *args, **kwargs):
		'''Set multiple properties, for multiple widgets, on multiple ui's at once.

		:Parameters:
			*args = arg [0] (str) String of objectNames. - objectNames separated by ',' ie. 'b000-12,b022'
					arg [1:] dynamic ui object/s.  If no ui's are given, then the parent and child uis will be used.
			*kwargs = keyword: - the property to modify. ex. setText, setValue, setEnabled, setDisabled, setVisible, setHidden
					value: - intended value.

		ex.	self.setWidgetAttr('chk003', <ui1>, <ui2>, setText='Un-Crease')
		'''
		if not args[1:]:
			args = args+[self.parentUi, self.childUi]

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
				ui = self.currentUi
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
				ui = self.currentUi
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
		'''
		packed_names = [n.strip() for n in nameString.split(',') if '-' in n] #build list of all widgets passed in containing '-'
		otherNames = [n.strip() for n in nameString.split(',') if '-' not in n] #all widgets passed in not containing '-'

		unpacked_names=[] #unpack the packed names:
		for name in packed_names:
			name = name.split('-') #ex. split 'b000-8'
			prefix = name[0].strip('0123456789') #ex. split 'b' from 'b000'
			start = int(name[0].strip('abcdefghijklmnopqrstuvwxyz') or 0) #start range. #ex. '000' #converting int('000') returns None, if case; assign 0.
			stop = int(name[1])+1 #end range. #ex. '8' from 'b000-8' becomes 9, for range up to 9 but not including 9.
			unpacked_names.extend([str(prefix)+'000'[:-len(str(num))]+str(num) for num in range(start,stop)]) #build list of name strings within given range

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
		list_ = [str(x) for x in list_] #make sure the list is made up of strings.

		ranges=[]
		for x in list_:
			if not ranges:
				ranges.append([x])
			elif int(x)-prev_x == 1:
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


	def invertOnModifier(self, value):
		'''Invert a numerical or boolean value if the alt key is pressed.

		:Parameters:
			value (int, float, bool) = The value to invert.
		
		:Return:
			(int, float, bool)
		'''
		modifiers = self.tcl.qApp.keyboardModifiers()
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
			self._progressBar = ProgressBar(self.tcl)

			try:
				self.currentUi.progressBar.step1
			except AttributeError:
				pass

			return self._progressBar


	@classmethod
	def message(cls, fn):
		'''A decorator for messageBox.
		Does not work with staticmethods.
		'''
		def wrapper(self, *args, **kwargs):
			self.messageBox(fn(self, *args, **kwargs))
		return wrapper


	def messageBox(self, string, location='topMiddle', timeout=1):
		'''Spawns a message box with the given text.
		Prints a formatted version of the given string, stripped of html tags, to the console.
		Supports HTML formatting.

		:Parameters:
			location (str)(point) = move the messagebox to the specified location. Can be given as a qpoint or string value. default is: 'topMiddle'
			timeout (int) = time in seconds before the messagebox auto closes.
		'''
		if not hasattr(self, '_messageBox'):
			from widgets.messageBox import MessageBox
			self._messageBox = MessageBox(self.tcl.parent())

		self._messageBox.location = location
		self._messageBox.timeout = timeout

		if isinstance(string, (str)):
			from re import sub
			print(''+sub('<.*?>', '', string)+'') #strip everything between '<' and '>' (html tags)

			self._messageBox.setText(string)
			self._messageBox.exec_()


	@staticmethod
	def getTrailingIntegers(string, inc=0):
		'''Returns any integers from the end of the given string.

		:Parameters:
			inc (int) = Increment by a step amount. 0 does not increment and returns the original number. (default: 0)

		"Return:
			(int)

		ex. n = getTrailingIntegers('p001Cube1', inc=1) #returns: 2
		'''
		import re

		m = re.findall(r"\d+\s*$", string)
		result = int(m[0])+inc if m else None

		return result


	@staticmethod
	def findStr(what, where, regEx=False, ignoreCase=False):
		'''Find matches of a string in a list.

		:Parameters:
			what (str) = The search string. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe chars.
				wildcards:
					*what* - search contains chars.
					*what - search endswith chars.
					what* - search startswith chars.
					what|what - search any of.  can be used in conjuction with other modifiers.
				regular expressions (if regEx True):
					(.) match any char. ex. re.match('1..', '1111') #returns the regex object <111>
					(^) match start. ex. re.match('^11', '011') #returns None
					($) match end. ex. re.match('11$', '011') #returns the regex object <11>
					(|) or. ex. re.match('1|0', '011') #returns the regex object <0>
					(\A,\Z) beginning of a string and end of a string. ex. re.match(r'\A011\Z', '011') #
					(\b) empty string. (\B matches the empty string anywhere else). ex. re.match(r'\b(011)\b', '011 011 011') #
			where (list) = The string list to search in.
			ignoreCase (bool) = Search case insensitive.

		:Return:
			(list)

		ex. list_ = ['invertVertexWeights', 'keepCreaseEdgeWeight', 'keepBorder', 'keepBorderWeight', 'keepColorBorder', 'keepColorBorderWeight']
			findStr('*Weight*', list_) #find any element that contains the string 'Weight'.
			findStr('Weight$|Weights$', list_, regEx=True) #find any element that endswith 'Weight' or 'Weights'.
		'''
		if regEx: #search using a regular expression.
			import re

			try:
				if ignoreCase:
					result = [i for i in where if re.search(what, i, re.IGNORECASE)]
				else:
					result = [i for i in where if re.search(what, i)]
			except Exception as e:
				print ('# Error findStr: in {}: {}. #'.format(what, e))
				result = []

		else: #search using wildcards.
			for w in what.split('|'): #split at pipe chars.
				w_ = w.strip('*').rstrip('*') #remove any modifiers from the left and right end chars.

				#modifiers
				if w.startswith('*') and w.endswith('*'): #contains
					if ignoreCase:				
						result = [i for i in where if w_.lower() in i.lower()] #case insensitive.
					else:
						result = [i for i in where if w_ in i]

				elif w.startswith('*'): #prefix
					if ignoreCase:
						result = [i for i in where if i.lower().endswith(w_.lower())] #case insensitive.
					else:
						result = [i for i in where if i.endswith(w_)]

				elif w.endswith('*'): #suffix
					if ignoreCase:
						result = [i for i in where if i.lower().startswith(w_.lower())] #case insensitive.
					else:
						result = [i for i in where if i.startswith(w_)]

				else: #exact match
					if ignoreCase:
						result = [i for i in where if i.lower()==w_.lower()] #case insensitive.
					else:
						result = [i for i in where if i==w_]

		return result


	@staticmethod
	def findStrAndFormat(frm, to, where, regEx=False, ignoreCase=False):
		'''Search a list for matching strings and re-format them.
		Useful for things such as finding and renaming objects.

		:Parameters:
			frm (str) = Current name. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe ('|') chars.
				*frm* - Search contains chars.
				*frm - Search endswith chars.
				frm* - Search startswith chars.
				frm|frm - Search any of.  can be used in conjuction with other modifiers.
			to (str) = Desired name: An optional asterisk modifier can be used for formatting. An empty to string will attempt to remove the part of the string designated in the from argument.
				"" - (empty string) - strip chars.
				*to* - replace only.
				*to - replace suffix.
				**to - append suffix.
				to* - replace prefix.
				to** - append prefix.
			where (list) = A list of string objects to search.
			regEx (bool) = If True, regex syntax is used instead of '*' and '|'.
			ignoreCase (bool) = Ignore case when searching. Applies only to the 'frm' parameter's search.

		:Return:
			(list) list of two element tuples containing the original and modified string pairs. [('frm','to')]

		ex. findStrAndFormat(r'Cube', '*001', regEx=True) #replace chars after frm on any object with a name that contains 'Cube'. ie. 'polyCube001' from 'polyCube'
		ex. findStrAndFormat(r'Cube', '*001', regEx=True) #append chars on any object with a name that contains 'Cube'. ie. 'polyCube1001' from 'polyCube1'
		'''
		import re

		if frm: #filter for matching strings if a frm argument is given. else; use all.
			where = Slots.findStr(frm, where, regEx=regEx, ignoreCase=ignoreCase)

		frm_ = re.sub('[^A-Za-z0-9_:]+', '', frm) #strip any special chars other than '_'.
		to_ = to.strip('*').rstrip('*') #remove any modifiers from the left and right end chars.

		result=[]
		for name in where:

			#modifiers
			if to.startswith('*') and to.endswith('*'): #replace chars
				if ignoreCase:
					n = re.sub(frm_, to_, name, flags=re.IGNORECASE) #remove frm_ from the string (case in-sensitive).
				else:
					n = name.replace(frm_, to_)

			elif to.startswith('**'): #append suffix
				n = name+to_

			elif to.startswith('*'): #replace suffix
				if ignoreCase:
					end_index = re.search(frm_, name, flags=re.IGNORECASE).start() #get the starting index of 'frm_'.
					n = name[:index]+to_
				else:
					n = name.split(frm_)[0]+to_

			elif to.endswith('**'): #append prefix
				n = to_+name

			elif to.endswith('*'): #replace prefix
				if ignoreCase:
					end_index = re.search(frm_, name, flags=re.IGNORECASE).end() #get the ending index of 'frm_'.
					n = to_+name[index:]
				else:
					n = to_+frm_+name.split(frm_)[-1]

			else:
				if not to_: #if 'to_' is an empty string:
					if ignoreCase:
						n = re.sub(frm_, '', name, flags=re.IGNORECASE) #remove frm_ from the string (case in-sensitive).
					else:
						n = name.replace(frm_, '') #remove frm_ from the string.
				else: #else; replace whole name
					n = to_

			result.append((name, n))

		return result


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

		def dotproduct(v1, v2):
			return sum((a*b) for a, b in zip(v1, v2))

		def length(v):
			return (dotproduct(v, v))**0.5

		result = acos(dotproduct(v1, v2) / (length(v1) * length(v2)))

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






	# ------------------------------------------------
	'FILE'
	# ------------------------------------------------

	@staticmethod
	def getAbsoluteFilePaths(directory, endingWith=[]):
		'''Get the absolute paths of all the files in a directory and it's sub-folders.

		directory (str) = Root directory path.
		endingWith (list) = Extension types (as strings) to include. ex. ['mb', 'ma']
		
		:Return:
			(list) absolute file paths
		'''
		paths=[]
		for dirpath, _, filenames in os.walk(directory):
			for f in filenames:
				if f.split('.')[-1] in endingWith:
					paths.append(os.path.abspath(os.path.join(dirpath, f)))

		return paths


	@staticmethod
	def formatPath(dir_, strip=''):
		'''Assure a given directory path string is formatted correctly.
		Replace any backslashes with forward slashes.

		:Parameters:
			dir_ (str) = A directory path. ie. 'C:/Users/m3/Documents/3ds Max 2022/3ds Max 2022.mxp'
			strip (str) = Strip from the path string. (valid: 'file', 'path')

		:Return:
			(str)
		'''
		formatted_dir = dir_.replace('/', '\\') #assure any single slash is forward.

		split = formatted_dir.split('\\')
		file = split[-1]

		if strip=='file':
			formatted_dir = '\\'.join(split[:-1]) if '.' in file else formatted_dir

		elif strip=='path':
			formatted_dir = file if '.' in file else formatted_dir

		return formatted_dir


	@staticmethod
	def getNameFromFullPath(fullPath):
		'''Extract the file or dir name from a path string.

		:Parameters:
			fullPath (str) = A full path including file name.

		:Return:
			(str) the dir or file name including extension.
		'''
		name = fullPath.split('/')[-1]
		if len(fullPath)==len(name):
			name = fullPath.split('\\')[-1]
			if not name:
				name = fullPath.split('\\')[-2]

		return name


	@staticmethod
	def fileTimeStamp(files, detach=False):
		'''Attach a modified timestamp and date to given file path(s).

		:Parameters:
			files (str)(list) = The full path to a file. ie. 'C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'
			detach (bool) = Return the full path to it's previous state.

		:Return:
			(list) ie. ['C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb  16:46  11-09-2021'] from ['C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb']
		'''
		from datetime import datetime

		if not isinstance(files, (list, tuple, set)):
			files = [files]

		if detach:
			result = [''.join(f.split()[:-2]) for f in files]
		else:
			result = [f+datetime.fromtimestamp(os.path.getmtime(f)).strftime('  %m-%d-%Y  %H:%M') for f in files] #attach modified timestamp

		return result









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


#depricated:


	# def callMethod(self, name, method, *args, **kwargs):
	# 	'''
	# 	Call a method from a class outside of the current ui.
	# 	Momentarily switches to the ui of the given method for the call, before returning to the previous ui.

	# 	:Parameters:
	# 		name (str) = ui name.
	# 		method (str) = method name.
	# 	'''
	# 	ui = self.tcl.sb.getUi()
	# 	temp = self.tcl.setUi(name)
	# 	method = self.tcl.sb.getMethod(name, method)

	# 	try:
	# 		method(*args, **kwargs)
	# 	except Exception as error:
	# 		print(error)

	# 	self.tcl.setUi(ui)


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