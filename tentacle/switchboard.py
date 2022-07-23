# !/usr/bin/python
# coding=utf-8
import os, sys

import importlib
import inspect

from PySide2.QtWidgets import QApplication
from PySide2.QtUiTools import QUiLoader

try: import shiboken2
except: from PySide2 import shiboken2

from ui.styleSheet import StyleSheet



class Switchboard(QUiLoader, StyleSheet):
	'''Load and Manage dynamic ui across modules using convenience methods.
	Dynamically adds and removes slot connections using naming convention.

	Ui files are searched for in the directory of this module.
	Custom widget modules are searched for in a sub directory named 'widgets'. 
	naming convention for custom widgets: <first char lowercase>.py module. <first char uppercase> for the corresponding widget class. ie. calss Label in label.py module.

	The ui name/and it's corresponding slot class name should always be the same. (case insensitive) ie. 'polygons' (ui name) will look to build connections to 'Polygons' (class name). 
	Widget objectName/corresponding class method name need to be the same. ie. 'b000' (widget objectName) will try to connect to <b000> class method.
	A widgets dict is constructed as needed for each class when connectSlots (or any other dependant) is called.

	:QuiLoader Functions:
		workingDirectory() - Returns the working directory of the loader. Return type: QtCore.QDir
		setWorkingDirectory(dir) - Sets the working directory of the loader to dir . The loader will look for other resources, such as icons and resource files, in paths relative to this directory.
		pluginPaths() - Returns a list naming the paths in which the loader will search when locating custom widget plugins.
		addPluginPath(str) - Adds the given path to the list of paths in which the loader will search when locating plugins.
		clearPluginPaths() - Clears the list of paths in which the loader will search when locating plugins.
		availableLayouts() - Returns a list of strings naming all available layouts that can be built using the createLayout() function.
		availableWidgets() - Returns a list of strings naming all available widgets that can be built using the createWidget() function, i.e all the widgets specified within the given plugin paths.
		registerCustomWidget(widget) - Returns a list naming the paths in which the loader will search when locating custom widget plugins.
		load(str, parentWidget=None) - Loads a form from the given device and creates a new widget with the given parentWidget to hold its contents.
		setLanguageChangeEnabled(enabled) - If enabled is true, user interfaces loaded by this loader will automatically retranslate themselves upon receiving a language change event.
		setTranslationEnabled(enabled) - If enabled is true, user interfaces loaded by this loader will be translated. Otherwise, the user interfaces will not be translated.
		isLanguageChangeEnabled() - Returns true if dynamic retranslation on language change is enabled; returns false otherwise.
		isTranslationEnabled() - Returns true if translation is enabled; returns false otherwise.
		errorString() - Returns a human-readable description (str) of the last error occurred in load()

	:QuiLoader Virtual Functions:
		createAction(parent=None, name='') - Creates a new action with the given parent and name.
		createActionGroup(parent=None, name='') - Creates a new action group with the given parent and name.
		createLayout(className, parent=None, name='') - Creates a new layout with the given parent and name using the class specified by className. You can use this function to create any layout returned by availableLayouts().
		createWidget(className, parent=None, name='') - Creates a new widget with the given parent and name using the class specified by className. You can use this function to create any widget returned by availableWidgets().

	:Ui levels: (for stacked layout hierarchy navigation)
		init menu:	0 	The launch menu. Mouse and hotkey combos link to base menus.
		base menu:	1	link to sub and main menus.
		sub menu:	2 	Inherits slots from it's corresponding main menu unless a slot class is created matching the sub menu's name.
		main menu:	3	Top level menu.
	
	:Structure:
		_sbDict = {	
			'<uiName>' : {
						'ui' : <ui object>,
						'uiLevel' : {'base' : <int>},
						'state' : int,
						'class' : <Class>,
						'size' : [int, int],
						'widgets' : {
									'<widget>':{
												'widgetName' : 'objectName',
												'signalInstance' : <widget.signal>,
												'widgetType' : '<widgetClassName>',
												'derivedType' : '<derivedClassName>',
												'method' : <method>,
												'prefix' : 'alphanumeric prefix',
												'docString' : 'method docString',
												'tracked' : <bool>,
									},
						},
			},
		}
	'''
	defaultSignals = { #the default signal to be associated with each widget type.
		'QAction':'triggered',
		'QLabel':'released',
		'QPushButton':'released',
		'QListWidget':'itemClicked',
		'QTreeWidget':'itemClicked',
		'QComboBox':'currentIndexChanged',
		'QSpinBox':'valueChanged',
		'QDoubleSpinBox':'valueChanged',
		'QCheckBox':'clicked',
		'QRadioButton':'released',
		'QLineEdit':'returnPressed',
		'QTextEdit':'textChanged',
		'QProgressBar':'valueChanged',
		}

	trackedWidgets = [ #widget types for mouse tracking.
		'QWidget', 
		'QLabel', 
		'QPushButton', 
		'QCheckBox',
		'QMenu',
	]

	attributesGetSet = {
		'isChecked':'setChecked', 
		'isDisabled':'setDisabled', 
		'isEnabled':'setEnabled', 
		'value':'setValue', 
		'text':'setText', 
		'icon':'setIcon',
	}

	_uiHistory = [] #[str list] - Tracks the order in which the uis are called. A new ui is placed at element[-1]. ie. ['previousName2', 'previousName1', 'currentName']
	_commandHistory = [] #[list of 2 element lists] - Command history. ie. [[<b000>, 'multi-cut tool']]
	_cameraHistory = [] #[list of 2 element lists] - Camera history. ie. [[<v000>, 'camera: persp']]
	_gcProtect = [] #[list] - Items protected from garbage collection
	_classKwargs = {} #{'<property name>':<property value>} - The additional properties of each of the slot classes.
	_registeredWidgets = [] #maintain a list of previously registered custom widgets.

	qApp = QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QApplication(sys.argv)

	defaultDir = os.path.abspath(os.path.dirname(__file__))
	defaultUiDir = defaultDir+'/ui'
	defaultWgtsDir = defaultDir+'/ui/widgets'
	defaultSlotsDir = defaultDir+'/slots'

	def __init__(self, parent=None, uiToLoad=defaultUiDir, widgetsToRegister=defaultWgtsDir, slotsDir=defaultSlotsDir, mainAppWindow=None):
		QUiLoader.__init__(self, parent)
		'''Instantiate switchboard with the directory locations of dynamic ui, custom widgets, slot modules and load the ui with any custom widgets.

		:Parameters:
			parent (obj) = The parent widget instance.
			uiToLoad (str)(list) = The path to a ui file or to a directory containing ui files. Default: '<uiLoader dir>'
			widgetsToRegister (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
						or the widget(s) themselves. Default: '<uiLoader dir>/widgets'
			slotsDir (str) = The path to where the slot modules are located. Default: '../slots'
			mainWindow (obj) = The parent application's top level window instance. ie. the Maya main window.

		ex. call:	qApp = QtWidgets.QApplication.instance()

					sb = Switchboard(uiToLoad=r'path to/ui', widgetsToRegister=r'path to/custom widgets', slotsDir=r'path to/slots')
					ui = sb.edit(setAsCurrent=True) #same as: sb.getUi('edit', setAsCurrent=True)

					widgets = ui.widgets()
					ui.setStyleSheet_(widgets)

					ui.show()
					qApp = QApplication.instance() #get the qApp instance if it exists.
					sys.exit(qApp.exec_())
		'''
		self.uiToLoad = uiToLoad
		self.widgetsToRegister = widgetsToRegister
		self.slotsDir = slotsDir

		for path in self.list_(uiToLoad): #assure uiToLoad is a list.

			self.setWorkingDirectory(self.formatFilepath(path, 'path'))
			# try:
			self.loadUi(path, widgets=widgetsToRegister)

			# except FileNotFoundError as error:
			# 	print ('# FileNotFoundError: {}.__init__(): {} #'.format(__name__, error))

		self.setMainAppWindow(mainAppWindow)


	@property
	def sbDict(self):
		'''Get the full switchboard dict.

		:Return:
			(dict)
		'''
		try:
			return self._sbDict

		except AttributeError as error:
			self._sbDict = {}
			return self._sbDict


	def loadUi(self, path, widgets=None, recursive=True):
		'''Load and add ui files to the uiDict.
		If the ui's directory name is in the form of 'uiLevel_x' then a 'level' key will be added to the uiDict with a value of x.

		:Parameters:
			path (str)(list) = The path to a ui file or to a directory containing ui files.
			widgets (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
						or the widget(s) themselves.
			recursive (bool) = Search the given path(s) recursively.

		:Return:
			{dict} uiDict. ex. {'some_ui':{'ui':<ui obj>, 'level':<int>}} (the ui level is it's hierarchy based on the ui file's dir location)

		ex. call: uiDict = uiLoader.loadUi([list ui filepaths]) #load a list of ui's.
		ex. call: uiDict = uiLoader.loadUi(uiLoader.defaultDir+'/some_ui.ui') #load a single ui using the path of this module.
		ex. call: uiDict = uiLoader.loadUi(__file__+'/some_ui.ui') #load a single ui using the path of the calling module.
		'''
		self.registerWidgets(widgets)

		for path in self.list_(path): #assure path is a list.

			uiName = self.formatFilepath(path, 'name')

			if uiName:
				ui = self.load(path) #load the dynamic ui file.
				uiLevel = self._getUiLevelFromDir(path)

				#set attributes
				setattr(self, uiName, lambda ui=ui, **kwargs: self.getUi(ui, **kwargs)) #set the ui as an attribute of switchboard so that it can be accessed as sb.<some_ui>()
				ui.widgets = lambda ui=ui, **kwargs: self.list_(self.widgets(ui, **kwargs)) #set a 'widgets' attribute to return the ui's widgets. ex. ui.widgets()
				ui.setStyleSheet_ = lambda ui=ui, **kwargs: self.setStyleSheet_(ui, **kwargs) #create a set stylesheet attribute for the ui. ex. ui.setStyleSheet_(style='dark')

				self.sbDict[uiName] = {
					'ui': ui, #the ui object.
					'uiLevel': {'base': uiLevel}, #the ui level as an integer value. (the ui level is it's hierarchy)
					'size': [ui.frameGeometry().width(), ui.frameGeometry().height()], #store the initial size. (useful when trying to properly resize stacked widgets)
					'state': 0, #initialization state.
				}

			else:
				for dirPath, dirNames, filenames in os.walk(path):
					uiFiles = ['{}/{}'.format(dirPath, f) for f in filenames if f.endswith('.ui')]
					self.loadUi(uiFiles)
					if not recursive:
						break

		return self.sbDict


	def setAttributes(self, obj=None, order=['setVisible'], **kwargs):
		'''
		:Parameters:
			obj (obj) = the child obj, or widgetAction to set attributes for. (default=self)
			order (list) = List of string keywords. ie. ['move', 'setVisible']. attributes in this list will be set last, in order of the list. an example would be setting move positions after setting resize arguments.
			**kwargs = The keyword arguments to set.
		'''
		if not kwargs:
			return

		obj = obj if obj else self

		for k in order:
			v = kwargs.pop(k, None)
			if v:
				from collections import OrderedDict
				kwargs = OrderedDict(kwargs)
				kwargs[k] = v

		for attr, value in kwargs.items():
			try:
				getattr(obj, attr)(value)

			except AttributeError:
				pass; # print (__name__+':','setAttributes:', obj, order, kwargs, error)


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
					for attr in dir(obj)
						if not attr in exclude 
							and (attr in include if include else attr not in include)}


	def setSyncAttributesConnections(self, w1, w2, **kwargs):
		'''Set the initial signal connections that will call the _syncAttributes function on state changes.

		:Parameters:
			w1 (obj) = A QWidget that will stay synced with w2.
			w2 (obj) = A QWidget that will stay synced with w1.
		'''
		try:
			s1 = self.defaultSignals[self.getDerivedType(w1)] #get the default signal for the given widget.
			s2 = self.defaultSignals[self.getDerivedType(w2)]

			getattr(w1, s1).connect(lambda: self._syncAttributes(w1, w2, **kwargs))
			getattr(w2, s2).connect(lambda: self._syncAttributes(w2, w1, **kwargs))

		except (KeyError, AttributeError) as error:
			# if w1 and w2: print ('# {}: {}.setSyncAttributesConnections({}, {}): {} is invalid.'.format('KeyError' if error==KeyError else 'AttributeError', __name__, w1, w2, error))
			pass


	def _syncAttributes(self, frm, to, attributes=[]):
		'''Sync the given attributes between the two given widgets.
		If a widget does not have an attribute it will be silently skipped.

		:Parameters:
			frm (obj) = The widget to transfer attribute values from.
			to (obj) = The widget to transfer attribute values to.
			attributes (str)(list)(dict) = The attribute(s) to sync. ie. a setter attribute 'setChecked' or a dict containing getter:setter pairs. ie. {'isChecked':'setChecked'}
		'''
		if not attributes:
			attributes = self.attributesGetSet

		elif not isinstance(attributes, dict):
			attributes = {next((k for k,v in self.attributesGetSet.items() if v==i), None):i #construct a gettr setter pair dict using only the given setter values.
				 for i in self.list_(attributes)
			}

		_attributes = {}
		for gettr, settr in attributes.items():
			try:
				_attributes[settr] = getattr(frm, gettr)()
			except AttributeError as error:
				pass

		[getattr(to, attr)(value) 
			for attr, value in _attributes.items() 
				if hasattr(to, attr)] #set the second widget's attributes from the first.


	def setUniqueObjectName(self, widget, ui=None, _num=None):
		'''Set a unique object name for the given widget based on the pattern name000.

		:Parameters:
			widget (obj) = The child widget to set an object name for.
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
			_num (int) = Integer to append to name. Internal use.

		:Return:
			(str) the widgets object name.
		'''
		if _num: #generate a unique three digit num
			widgetNum = ('00'+str(num))[-3:] #remove prefixed zeros to keep the num three digits. ie. 001, 011, 111

			if widgetType in prefixTypes:
				prefix = prefixTypes[widgetType] #ie. 'b' from 'QPushButton'
			else:
				prefix = widgetType.strip('Q')[:1].lower()+widgetType.strip('Q')[1:] #widgetAction from 'QWidgetAction'

			return '{0}{1}'.format(prefix, widgetNum) #append num. ie. widgetAction000

		uiName = self.getUiName(ui)

		widgetType = widget.__class__.__name__

		num=0
		widgetName = self.setUniqueObjectName(_num=num)
		while self.getWidget(widgetName, uiName): #if a widget of the same name already exists; increment by one and try again.
			num+=1; widgetName = nameGenerator(num)

		widget.setObjectName(widgetName)
		return widget.objectName()


	def getClassKwargs(self, ui):
		'''Get properties as keyword arguments for the given ui.

		:Parameters:
			ui (str)(obj) = The ui, or ui name. ie. <Polygons> or 'polygons'

		:Return:
			(dict) packed keyword arguments. ie. {
				'sb': <switchboard.Switchboard object at 0x000001D97BD7D1C8>, 
				'_currentUi': <function <lambda> at 0x000001D97BCFCAC8>, 
				'_ui': <function <lambda> at 0x000001D97BCFCA58>,
				'polygons': <PySide2.QtWidgets.QMainWindow object at 0x000001D97BCEB0C8>
				'polygons_submenu': <PySide2.QtWidgets.QMainWindow object at 0x000001D978D8A708>, 
				'PushButton': <PySide2.QtWidgets.QPushButton object at 0x000001D978D8A705>,
			}
		'''
		uiName = self.getUiName(ui)

		try: #return kwargs for the given ui, if already stored in '_classKwargs' dict.
			return self._classKwargs[uiName]

		except KeyError as error:

			kwargs = {}
			kwargs['current_ui'] = lambda n=uiName: self.getUi(next((i for i in reversed(self._uiHistory) if i in self.getUiName(n, level=(0,1,2,3,4))), self.getUi()))
			kwargs['sb'] = self

			for uiName in self.getUiName('all'):
				kwargs[uiName] = lambda n=uiName: self.getSlotInstance(n) #assign a function that gets the class instance.
				kwargs['{}_ui'.format(uiName)] = self.getUi(uiName)

			for widget in self._registeredWidgets: #add any registered widgets as properties.
				kwargs[widget.__name__] = widget

			self._classKwargs[uiName] = kwargs

			return self._classKwargs[uiName]


	def getDefaultSignalType(self, widgetType):
		'''Get the default signal type for a given widget type.

		:Parameters:
			widgetType (str) = Widget class name. ie. 'QPushButton'

		:Return:
			(str) signal ie. 'released'
		'''
		try: #if the widget type has a default signal assigned in the signals dict; get the signal.
			signal = self.defaultSignals[widgetType]
		except KeyError:
			signal = ''

		return signal


	def getSignal(self, ui, widget=None):
		'''Get the widget object with attached signal (ie. b001.onPressed) from the given widget name.

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
			objectName (str) = optional widget name. ie. 'b001'

		:Return:
			if objectName: (obj) widget object with attached signal (ie. b001.onPressed) of the given widget name.
			else: (list) all of the signals associated with the given name as a list.
		'''
		uiName = self.getUiName(ui)

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		if widget:
			if not widget in self.widgets(uiName):
				self.addWidget(uiName, widget)
			return self.widgets(uiName)[widget]['signalInstance']
		else:
			return [w['signalInstance'] for w in self.widgets(uiName).values()]


	def setConnections(self, ui):
		'''Replace any signal connections of a previous ui with the set for the ui of the given name.

		:Parameters:
			ui (str)(obj) = The name of ui, or the ui itself. ie. 'polygons' or <polygons>
		'''
		uiName = self.getUiName(ui)
		prevUiName = self.prevUiName(allowDuplicates=True)
		if prevUiName==uiName:
			return

		if prevUiName and self.getUiLevel(prevUiName)<3:
			self.disconnectSlots(prevUiName); #print ('disconnectSlots:', prevUiName) #remove signals from the previous ui.

		level = self.getUiLevel(ui)
		state = self.getUiState(ui)

		if level<3 or state<2:
			self.connectSlots(ui); #print ('connectSlots:', self.getUiName(ui))


	def connectSlots(self, ui, widgets=None):
		'''Connect signals to slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (str)(obj) = The name of ui, or the ui itself. ie. 'polygons' or <polygons>
			widgets (obj)(list) = QWidget(s)
		'''
		uiName = self.getUiName(ui)
		# print ('connectSlots:', uiName)
		if widgets is None:
			widgets = self.widgets(uiName)

		for w in self.list_(widgets): #convert 'widgets' to a list if it is not one already.
			signal = self.getSignal(uiName, w)
			slot = self.getMethod(uiName, w)
			# print ('           >:', w.objectName(), slot)
			if slot and signal:
				try:
					if isinstance(slot, (list, set, tuple)):
						map(signal.connect, slot) #connect to multiple slots from a list.
					else:
						signal.connect(slot) #connect single slot (main and cameras ui)

				except Exception as error:
					print('Error: {0} {1} connectSlots: {2} {3}'.format(uiName, w.objectName(), signal, slot), '\n', error)


	def disconnectSlots(self, ui, widgets=None):
		'''Disconnect signals from slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (str)(obj) = The name of ui, or the ui itself. ie. 'polygons' or <polygons>
			widgets (obj)(list) = QWidget
		'''
		uiName = self.getUiName(ui)
		# print ('disconnectSlots:', uiName)
		if widgets is None:
			widgets = self.widgets(uiName)

		for w in self.list_(widgets):  #convert 'widgets' to a list if it is not one already.
			signal = self.getSignal(uiName, w)
			slot = self.getMethod(uiName, w)
			# print ('           >:', w.objectName(), slot)
			if slot and signal:
				try:
					if isinstance(slot, (list, set, tuple)):
						signal.disconnect() #disconnect all #map(signal.disconnect, slot) #disconnect multiple slots from a list.
					else:
						signal.disconnect(slot) #disconnect single slot (main and cameras ui)

				except Exception as error:
					print('Error: {0} {1} disconnectSlots: {2} {3} #'.format(uiName, w.objectName(), signal, slot), '\n', error)


	def getUi(self, uiName=None, level=None, setAsCurrent=False):
		'''Get a dynamic ui using its string name, or if no argument is given, return the current ui.

		:Property:
			ui

		:Parameters:
			uiName (str)(obj) = The ui object, or ui name. (valid: <ui>, '<uiName>', 'all')
				A value of 'all' will return all ui of the given level(s).
				A value of None will return the current ui.
			level (int)(list) = Integer(s) representing the level to include. ie. 2 for submenu, 3 for main_menu, or [2, 3] for both.
			setAsCurrent (bool) = Setting this flag to True will register the uiName in history as current.

		:Return:
			(str)(list) the corresponding ui(s).
		'''
		if uiName=='all':
			level = level if level!=None else (0,1,2,3,4)
			return [d['ui'] for k, d in self.sbDict.items() if d['uiLevel']['base'] in self.list_(level)]

		uiName = self.getUiName(uiName, case='camelCase', level=level, setAsCurrent=setAsCurrent)

		try:
			if isinstance(uiName, (list, set, tuple)):
				return [self.sbDict[n]['ui'] for n in uiName]
			else:
				return self.sbDict[uiName]['ui']

		except (ValueError, KeyError, TypeError):
			return None


	def getUiFromWidget(self, widget, uiName=False):
		'''Get the ui for the given widget.

		:Parameters:
			widget (obj) = A child widget of the desired ui.
			uiName (bool) = Return the ui's name instead of the ui object.

		:Return:
			 (str)(obj) the corresponding ui, or ui name. ie. <polygons> from <somewidget>
		'''
		result = next((self.getUi(k) for k,v in self.sbDict.items() if 'widgets' in v and widget in v['widgets']), None)
		if uiName: #get ui name from ui
			result = self.getUiName(result)
		return result


	def setUiState(self, ui=None, state=1):
		'''Get the initialization state of the given ui as an int.

		:Parameters:
			ui (str)(obj) = The ui, or ui name to set the state for.
			states (int) = Set the state of the given ui. (valid: 0: uninitialized, 1: initialized, 2: connected)

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
			state (int) = The desired initialization state value.
		'''
		uiName = self.getUiName(ui)

		self.sbDict[uiName]['state'] = state


	def getUiState(self, ui=None):
		'''Get the initialization state of the given ui as an int.

		:Parameters:
			ui (str)(obj) = The ui, or ui name to set the state of.

		states:
			0: uninitialized.
			1: initialized.
			2: connected.

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
		:Return:
			(int)
		'''
		uiName = self.getUiName(ui)

		return self.sbDict[uiName]['state']


	def _setUiName(self, i):
		'''Register the uiName in history as current.
		The '_uiHistory' list is used for various things such as; maintaining a history of ui's that have been called.

		:Property:
			uiName

		:Parameters:
			i (int)(str) = The index of, or name of the ui.

		:Return:
			(str) corresponding ui name.
		'''
		if not isinstance(i, int):
			i = self.getUiIndex(i) #get index using name
			uiName = self.getUiName('all')[i]

		self._uiHistory.append(uiName)

		return self._uiHistory[-1]


	def getUiName(self, ui=None, case=None, level=None, setAsCurrent=False):
		'''Get the ui name as a string.
		If no argument is given, the name for the current ui will be returned.

		:Property:
			uiName

		:Parameters:
			ui (str)(obj) = The ui object, or ui name. (valid: <ui>, '<uiName>', 'all')
				A value of 'all' will return all ui of the given level(s).
				A value of None will return the current ui.
			case (str) = define the returned name's case structure. valid: 'camelCase'=first letter lowercase, 'pascalCase'=first letter capitalized. (default: None)
			level (int)(list) = Integer(s) representing the level to include. ie. 2 for submenu, 3 for main_menu, or [2, 3] for both.
			setAsCurrent (bool) = Setting this flag to True will register the uiName in history as current.

		:Return:
			(str)(list) - ui name, or list of ui names.
		'''
		if level is not None:
			level = self.list_(level)

		if ui is None: #get the ui name:
			try:
				uiName = self._uiHistory[-1]
			except IndexError as error: #if index out of range (no value exists) if uiName==n or (uiName in n and level==4)] if uiName==n or (uiName in n and level==4)]: return None
				if len(self.sbDict)==1:
					return next(iter(self.sbDict)) #if there is only one ui in sbDict return it; else raise error.

				print ('# IndexError: {}.getUiName({}, {}, {}): {} #'.format(__name__, ui, case, level, error))
				raise IndexError('No UI in history. If there are muliple ui loaded, you must set one as the current ui either by using getUi() with setAsCurrent flag, or <switchboard>.<ui name>(setAsCurrent=True).')

		elif isinstance(ui, (str)):
			if ui=='all': #get all ui of the given level(s).
				level = level if level!=None else (0,1,2,3,4)
				return [self.setCase(n, case) for n in self.sbDict if self.getUiLevel(n) in level]
			else:  #get the ui name from ui name.
				uiName = ui

		else: #get the ui name from ui object.
			uiName = next((n for n, d in self.sbDict.items() if d['ui']==ui), None)

		if setAsCurrent:
			self._setUiName(uiName)

		l0=l1=l2=l3=l4 = []
		if uiName is not None:
			if level is not None: #filter by level.

				if 0 in level:
					try:
						l0 = self.sbDict[uiName]['uiLevel'][0]
					except KeyError as error:
						c = uiName.split('_')[0]
						l0 = self.sbDict[uiName]['uiLevel'][0] = [n for n in self.sbDict
																	if all((c==n, self.getUiLevel(n)==0))]
				if 1 in level:
					try:
						l1 = self.sbDict[uiName]['uiLevel'][1]
					except KeyError as error:
						c = uiName.split('_')[0]
						l1 = self.sbDict[uiName]['uiLevel'][1] = [n for n in self.sbDict
																	if all((c==n, self.getUiLevel(n)==1))]
				if 2 in level:
					n, *tags = uiName.replace('_submenu', '').split('#', 1)
					tags = '#'+'#'.join(tags) if tags else ''
					c = uiName = '{}_submenu{}'.format(n, tags) #c = uiName.split('_submenu')[0] + '_submenu'
					try:
						l2 = self.sbDict[uiName]['uiLevel'][2]
					except KeyError as error:
						l2 = self.sbDict[uiName]['uiLevel'][2] = [n for n in self.sbDict
																	if all((c==n, self.getUiLevel(n)==2))]
				if 3 in level:
					try:
						l3 = self.sbDict[uiName]['uiLevel'][3]
					except KeyError as error:
						c = uiName.split('_')[0]
						l3 = self.sbDict[uiName]['uiLevel'][3] = [n for n in self.sbDict
																	if all((c==n, self.getUiLevel(n)==3))]
				if 4 in level:
					try:
						l4 = self.sbDict[uiName]['uiLevel'][4]
					except KeyError as error:
						c = uiName.split('_')[0]
						l4 = self.sbDict[uiName]['uiLevel'][4] = [n for n in self.sbDict
																	if all((c==n.split('_')[0], self.getUiLevel(n)==4))]

				uiName = l0+l1+l2+l3+l4

			uiName = self.setCase(uiName, case)

		if uiName: #return list if more than 1 name, else, single name.
			return uiName[0] if len(uiName)==1 else uiName
		else:
			return None


	def getUiNameFromWidget(self, widget):
		'''Get the ui name from the given widget.

		:Parameters:
			widget (obj) = QWidget

		:Return:
			 (str) ui name. ie. 'polygons' from <somewidget>
		'''
		return next((k for k,v in self.sbDict.items() if type(v) is dict and 'widgets' in v and widget in v['widgets']), None)


	def getUiNameFromMethod(self, method):
		'''Get the ui name from the given method.

		:Parameters:
			widget (obj) = QWidget

		:Return:
			 (str) ui name. ie. 'polygons' from <somewidget>
		'''
		for name, value in self.sbDict.items():
			if type(value)==dict:
				try:
					if next((v for v in value['widgets'].values() if v['method'] is method), None):
						return name
				except KeyError:
					pass; # print (__name__+':','getUiNameFromMethod:', method, error)


	def getUiNameFromKey(self, nestedKey, _uiName=None, _nested_dict=None):
		'''Generator. Get the ui name from a given nested key.

		:Parameters:
			nestedKey (key) = The key of a nested dict to get the ui of.
			_uiName (key) = internal use. The key from the top-level dict. (ie. 'polygons') which is later returned as the uiName if a key match is found in a directly nested dict.
			_nested_dict (dict) = internal use. Recursive call.

		ex. next(self.getUiNameFromKey(<widget>), None) #returns the first ui name with a nested dict containing the given key if found; else None.
		'''
		if _nested_dict is None:
			_nested_dict = self.sbDict

		for k,v in _nested_dict.items():
			if type(v) is dict:
				if nestedKey in v.keys():
					if not self.sbDict.get(k): #if the key is not top level:
						k = _uiName #re-assign and keep passing the top level key so that it can eventually be returned.
					yield _uiName
				else:
					n = next(self.getUiNameFromKey(nestedKey, k, v), None)
					if n:
						yield n


	def getUiNamesFromValue(self, nestedValue):
		'''Get the ui name from a given nested Value.

			:Parameters:
				nestedValue (value) = The value of a nested dict to get the ui of.

			:Return:
				(list) of uiNames that contain the given nestedValue.

			ex. self.getUiNameFromValue('cmb002') #returns the names of all ui with a dict containing value 'cmb002'.
		'''
		_uiNames=[]
		for uiName, value in self.sbDict.items():
			if type(value)==dict: #for each top-level dict in sbDict:
				if self.getParentKeys(nestedValue, value): #if a nested dict contains the nested value: (getParentKeys returns a list containing the hierarchical key path of the nestedValue)
					_uiNames.append(uiName)
		return _uiNames


	def getUiIndex(self, ui=None):
		'''Get the index of the given ui name.

		:Property:
			uiIndex

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.

		:Return:
			if uiName: index of given name from key.
			else: index of current ui
		'''
		uiName = self.getUiName(ui)

		return self.getUiName('all').index(uiName)


	def setUiSize(self, size, ui=None): #store ui size.
		'''Set the size of a ui.
		If no size is given, the minimum ui size needed to frame its
		contents will be used. If no uiName is given, the current ui will be used.

		:Property:
			size

		:Parameters:
			size (list) = The width and height as integers. [width, height]
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
		:Return:
			(list) ui size info as integer values in a list. [width, hight]
		'''
		uiName = self.getUiName(ui)

		self.sbDict[uiName]['size'] = size
		return self.sbDict[uiName]['size']


	def setUiSizeX(self, width, ui=None):
		'''Set the X (width) value for the current ui.

		:Property:
			sizeX

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
			width (int) = X size as an int
		'''
		height = self.getUiSize(ui=ui, height=True) #get the hight value.
		self.setUiSize([width, height], ui)


	def setUiSizeY(self, height, ui=None):
		'''Set the Y (height) value for the current ui.

		:Property:
			sizeY

		:Parameters:
			height (int) = Y size as an int
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
		'''
		width = self.getUiSize(ui=ui, width=True) #get the width value.
		self.setUiSize([width, height], ui)


	def getUiSize(self, ui=None, width=None, percentWidth=None, height=None, percentHeight=None):
		'''Get the stored size info for each ui (allows for resizing a stacked widget where ordinarily resizing is constrained by the largest widget in the stack)

		:Property:
			size

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
			width (int) = Returns the width of current ui.
			height (int) = Returns hight of current ui.
			percentWidth (int) = Returns a percentage of the width.
			percentHeight (int) = returns a percentage of the height.

		:Return:
			(int)(list)
			width: returns width as int
			height: returns height as int
			percentWidth: returns the percentage of the width as an int
			percentHeight: returns the percentage of the height as an int
			else: ui size info as integer values in a list. [width, hight]
		'''
		uiName = self.getUiName(ui)

		if not 'size' in self.sbDict[uiName]:
			self.setUiSize(uiName)

		if width:
			return self.sbDict[uiName]['size'][0]
		elif height:
			return self.sbDict[uiName]['size'][1]
		elif percentWidth:
			return self.sbDict[uiName]['size'][0] *percentWidth /100
		elif percentHeight:
			return self.sbDict[uiName]['size'][1] *percentHeight /100
		else:
			return self.sbDict[uiName]['size']


	def getUiSizeX(self, ui=None):
		'''Get the X (width) value for the current ui.

		:Property:
			sizeX

		:Parameters:
			uiName (str) = ui uiName to get size from.

		:Return:
			returns width as int
		'''
		return self.getUiSize(ui=ui, width=True)


	def getUiSizeY(self, ui=None):
		'''Get the Y (height) value for the current ui.

		:Property:
			sizeY

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.

		:Return:
			returns width as int
		'''
		return self.getUiSize(ui=ui, height=True)


	def setMainAppWindow(self, app):
		'''Set parent application.

		:Property:
			mainAppWindow

		:Parameters:
			app = app object.

		:Return:
			string name of app
		'''
		self._mainAppWindow = app

		return self._mainAppWindow


	def getMainAppWindow(self, objectName=False):
		'''Get parent application if any.

		:Property:
			mainAppWindow

		:Parameters:
			objectName (bool) = get string name of app. (by default getMainAppWindow returns app object)

		:Return:
			app object or string name
		'''
		app = self._mainAppWindow

		if objectName:
			if not app: #if app is None, return an empty string value.
				return ''
			else: #remove 'Window' from objectName ie. 'Maya' from 'MayaWindow' and set lowercase.
				name = app.objectName().rstrip('Window')
				return self.setCase(name, 'camelCase') #lowercase the first letter.
		else:
			return app


	def _setSlotInstance(self, ui):
		'''Stores an instance of a slot class.
		If the ui is a submenu (level 2) and a class is not found, the parent class will be returned. ie. <Polygons> from 'polygons_submenu'

		:Property:
			slotInstance

		:Parameters:
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
		:Return:
			(obj) The class instance.
		'''
		uiName = self.getUiName(ui)

		parentAppName = self.getMainAppWindow(objectName=True)
		mod_name = '{}_{}'.format(self.setCase(uiName, case='camelCase'), parentAppName).rstrip('_') #ie. 'polygons_maya' or 'polygons' if parentAppName is None.

		sys.path.append(self.slotsDir)

		try: #import the module and get the class instance.
			module = importlib.import_module(mod_name) # module = __import__(mod_name)
			# print ('module:', module)
			class_ = getattr(module, self.setCase(mod_name, case='pascalCase')) #ie. <Polygons_maya> from 'Polygons_maya'
			kwargs = self.getClassKwargs(uiName)
			for k, v in kwargs.items():
				setattr(self, k, v)
			try:
				result = self.sbDict[uiName]['class'] = class_(**kwargs)
			except:  #the module has no '**kwargs' keyword arg.
				result = self.sbDict[uiName]['class'] = class_()

		except (ModuleNotFoundError, TypeError) as error: #TypeError: 'NoneType' object is not callable
			if self.getUiLevel(ui) in (0,1,3):
				result = self.sbDict[uiName]['class'] = None #

			else:
				parent_name = self.getUiName(uiName, case='camelCase', level=[0,1,3])
				if uiName==parent_name: #prevent recursion.
					raise error
				result = self.sbDict[uiName]['class'] = self.getSlotInstance(parent_name) #get the parent class.

		# print ('result:', result)
		return result


	def getSlotInstance(self, ui):
		'''Case insensitive. (Class string keys are lowercase and any given string will be converted automatically)
		If class is not in self.sbDict, getSlotInstance will attempt to use _setSlotInstance() to first store the class.

		:Property:
			slotInstance

		:Parameters:
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
							A value of 'all' will return all of the class instances. 
		:Return:
			(obj) The class instance.
		'''
		uiName = self.getUiName(ui)

		if ui=='all':
			return [self.getSlotInstance(n) for n in uiName]

		try:
			return self.sbDict[uiName]['class']

		except KeyError as error:
			return self._setSlotInstance(uiName)


	def _getWidgetsFromUi(self, ui):
		'''Get all widgets of the given ui.

		:Parameters:
			ui (obj)(str) = The ui, or name of the ui you are wanting to get widgets for.

		:Return:
			(list) widget objects
		'''
		ui = ui if not isinstance(ui, str) else self.getUi(ui)

		try:
			return [w for w in ui.__dict__.values() if self.isWidget(w)]

		except AttributeError as error:
			return []


	def isWidget(self, obj):
		'''Returns True if the given obj is a valid widget.

		:Parameters:
			obj (obj) = An object to query.

		:Return:
			(bool)
		'''
		return hasattr(obj, 'objectName') and shiboken2.isValid(obj)


	def _getWidgetsFromDir(self, path):
		'''Get all widget class objects from a given directory.

		:Parameters:
			path (str) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'

		:Return:
			(list) widgets
		'''
		path = self.formatFilepath(path, 'path')
		mod_name = self.formatFilepath(path, 'name')
		mod_ext = self.formatFilepath(path, 'ext')

		self.addPluginPath(path)
		sys.path.append(path)
		modules={}

		if mod_name: #if the path contains a module name, get only that module.
			mod = importlib.import_module(mod_name)

			cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

			for cls_name, cls_mem in cls_members:
				modules[cls_name] = cls_mem


		else: #get all modules in the given path.
			try:
				_path = os.listdir(path)
			except FileNotFoundError as error:
				print ('# FileNotFoundError: {}._getWidgetsFromDir(): {} #'.format(__name__, error))
				return

			for module in _path:

				mod_name = module[:-3]
				mod_ext = module[-3:]

				if module == '__init__.py' or mod_ext != '.py':
					continue

				mod = importlib.import_module(mod_name)

				cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

				for cls_name, cls_mem in cls_members:
					modules[cls_name] = cls_mem

			del module

		widgets = [w for w in modules.values() if type(w).__name__=='ObjectType' and self.isWidget(w)] #get all imported widget classes as a dict.
		return widgets


	def registerWidgets(self, widgets):
		'''Register any custom widgets using the module names.
		Registered widgets can be accessed as properties. ex. sb.PushButton()

		:Parameters:
			widgets (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
						or the widget(s) themselves. 

		ex. call: registerWidgets(<class 'widgets.menu.Menu'>) #register using widget class object.
		ex. call: registerWidgets('O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets/menu.py') #register using path to widget module.
		'''
		if not widgets:
			return

		if isinstance(widgets, (str)):
			widgets = self._getWidgetsFromDir(widgets)

		for w in self.list_(widgets): #assure widgets is a list.

			if w in self._registeredWidgets:
				continue

			try:
				self.registerCustomWidget(w)
				self._registeredWidgets.append(w)
				setattr(self, w.__name__, w)

			except Exception as error:
				print ('# Error: {}.registerWidgets(): {} #'.format(__name__, error))


	def addWidgets(self, uiName, widgets=None, include=[], exclude=[], filterByBaseType=False, **kwargs):
		'''Extends the fuctionality of the 'addWidget' method to support adding multiple widgets.
		If widgets is None; the method will attempt to add all widgets from the ui of the given name.

		:Parameters:
			uiName (str) = The name of the parent ui to construct connections for.
			widgets (list) = widget objects to be added. If none are given all objects from the ui will be added.
			include (list) = Widget types to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Widget types to exclude. ie. ['QWidget', 'QAction', 'QLabel', 'QPushButton', 'QListWidget']
			filterByBaseType (bool) = When using include, or exclude; Filter by base class name, or derived class name. ie. 'QLayout'(base) or 'QGridLayout'(derived)
		'''
		if widgets is None:
			ui = self.getUi(uiName)
			widgets = self._getWidgetsFromUi(ui) #get all widgets of the ui:

		for w in self.list_(widgets): #if 'widgets' isn't a list, convert it to one.
			typ = w.__class__.__base__.__name__ if filterByBaseType else self.getDerivedType(w)
			if not typ in exclude and (typ in include if include else typ not in include):
				self.addWidget(uiName, w, **kwargs)

		# Debug: Print a copy of the sbDict to console for a visual representation.
		#Some objects in the dict will be converted to strings in order to provide a working test example.
		#ie. <PySide2.QtWidgets.QMainWindow(0x1fa56db6310, name="QtUi") at 0x000001FA29138EC8> becomes: '<PySide2.QtWidgets.QMainWindow(0x1fa56db6310, name="QtUi") at 0x000001FA29138EC8>' 
		# print (self.convert(self.sbDict[uiName]))
		# print (self.convert(self.sbDict))


	def addWidget(self, uiName, widget, **kwargs):
		'''Adds a widget to the widgets dict under the given (ui) name.

		:Parameters:
			uiName (str) = The name of the parent ui to construct connections for.
			widget (obj) = The widget to be added.
			objectName (str) = Assign the widget a name. (kwargs)

		:Return:
			(obj) The added widget.

		ex. sb.addWidget('polygons', <widget>, setVisible=False) #example using kwargs to set widget attributes when adding.
		'''
		if widget in self.widgets(uiName): 
			print ('# Error: {0}.addWidget({1}, {2}): Widget was previously added. Widget skipped. #'.format(__name__, uiName, widget))
			return

		try:
			widgetName = widget.objectName()
		except AttributeError as error: #not a valid widget.
			return

		self.setAttributes(widget, **kwargs) #set any passed in keyword args for the widget.

		slotInstance = self.getSlotInstance(uiName) #get the corresponding slot class from the ui name. ie. class <Polygons> from uiName 'polygons'.
		derivedType = self.getDerivedType(widget) #the base class of any custom widgets.  ie. 'QPushButton' from 'PushButton'
		signalType = self.getDefaultSignalType(derivedType) #get the default signal type for the widget as a string. ie. 'released' from 'QPushButton'
		signalInstance = getattr(widget, signalType, None) #add signal to widget. ie. <widget.valueChanged>
		method = getattr(slotInstance, widgetName, None) #use 'widgetName' to get the corresponding method of the same name. ie. method <b006> from widget 'b006' else None
		docString = getattr(method, '__doc__', None)
		prefix = self.prefix(widgetName) #returns an string alphanumberic prefix if widgetName startswith a series of alphanumberic charsinst is followed by three integers. ie. 'cmb' from 'cmb015'
		isTracked = True if derivedType in self.trackedWidgets else False # and self.getUiLevel(uiName)<3

		self.widgets(uiName).update( #add the widget and a dict containing some properties.
					{widget:{
						'widgetName':widgetName, 
						'widgetType':widget.__class__.__name__,
						'derivedType':derivedType,
						'signalInstance':signalInstance,
						'method': method,
						'prefix':prefix,
						'docString':docString,
						'tracked':isTracked,
						}
					})

		if self.getUiLevel(uiName)==2: #sync submenu widgets with their main menu counterparts.
			w2 = self.getWidget(widgetName, self.getUi(uiName, level=3)) #w2 = getattr(self.getUi(uiName, level=3), widgetName) if hasattr(self.getUi(uiName, level=3), widgetName) else None
			self.setSyncAttributesConnections(widget, w2)

		# print(self.widgets(uiName)[widget])
		return self.widgets(uiName)[widget] #return the stored widget.


	def widgets(self, ui=None, query=False):
		'''Get the widgets dict from the main sbDict.

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
			query (bool) = Check if there exists a 'widgets' key for the given class name.

		:Return:
			(dict) widgets of the given ui.

		ex. {'<widget>':{
					'widgetName':'objectName',
					'widgetType':'<widgetClassName>',
					'derivedType':'<derivedClassName>',
					'signalInstance':<widget.signal>,
					'method':<method>,
					'prefix':'alphanumeric prefix',
					'docString':'method docString'
					'tracked':isTracked,
					}
			}
		'''
		uiName = self.getUiName(ui)

		if query:
			return True if 'widgets' in self.sbDict[uiName] else False

		try:
			return self.sbDict[uiName]['widgets']

		except KeyError as error:
			try:
				self.sbDict[uiName]['widgets'] = {}
				self.addWidgets(uiName) #construct the signals and slots for the ui.
			except KeyError as error:
				return

			return self.sbDict[uiName]['widgets']


	def getWidget(self, widgetName=None, ui=None, tracked=False):
		'''Case insensitive. Get the widget object/s from the given ui and widgetName.

		:Property:
			getWidgets

		:Parameters:
			widgetName (str) = The object name of the widget. ie. 'b000'
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
			tracked (bool) = Return only those widgets defined as 'tracked'. 

		:Return:
			(obj) if widgetName:  widget object with the given name from the current ui.
				  if ui and widgetName: widget object with the given name from the given ui name.
			(list) if ui: all widgets for the given ui.
		'''
		uiName = self.getUiName(ui)

		if not 'widgets' in self.sbDict[uiName]:
			self.widgets(uiName) #construct the signals and slots for the ui

		if tracked:
			if widgetName:
				return next((w if self.isWidget(w) else self.removeWidgets(w, uiName) 
							for w, d in self.widgets(uiName).items()
								if d['widgetName']==widgetName and self.isTracked(w, uiName)), None)

			return [w for w in self.widgets(uiName).copy() if (self.isTracked(w, uiName) and self.isWidget(w))]

		else:
			if widgetName:
				return next((w if self.isWidget(w) else self.removeWidgets(w, uiName) 
							for w, d in self.widgets(uiName).items()
								if d['widgetName']==widgetName), None)

			return [w for w in self.widgets(uiName).copy() if self.isWidget(w)] #'copy' is used in place of 'keys' RuntimeError: dictionary changed size during iteration


	def getWidgetsByType(self, types, ui=None, derivedType=False):
		'''Get widgets of the given types.

		:Parameters:
			types (str)(list) = A widget class name, or list of widget class names. ie. 'QPushbutton' or ['QPushbutton', 'QComboBox']
			ui (str)(obj) = Parent ui name, or ui object. ie. 'polygons' or <polygons>
							If no name is given, the current ui will be used.
			derivedType (bool) = Get by using the parent class of custom widgets.

		:Return:
			(list)
		'''
		uiName = self.getUiName(ui)

		key = 'derivedType' if derivedType else 'widgetType'

		return [w for w, d in self.widgets(uiName).items() if d[key] in self.list_(types)]


	def getWidgetsByPrefix(self, prefix, ui=None, widgets=[]):
		'''Get widgets having names using the given prefix.

		:Parameters:
			prefix (str)(list) = A widget prefix, or list of prefixes. ie. 'b' or ['b', 'tb']
			ui (str)(obj) = Parent ui name, or ui object. ie. 'polygons' or <polygons>
							If no name is given, the current ui will be used.
			widgets (list) = If a list of widgets is given the result will be filtered for only those widgets in the given list.

		:Return:
			(list)
		'''	
		uiName = self.getUiName(ui)

		return [w for w, d in self.widgets(uiName).items() if d['prefix'] in self.list_(prefix) and w in widgets if widgets]


	def getWidgetFromMethod(self, method, existing=None):
		'''Get the corresponding widget from a given method.

		:Parameters:
			method (obj) = The method in which to get the widget of.
			existing (str) = Search only for widgets already existing in the dict (faster).

		:Return:
			(obj) widget. ie. <b000 widget> from <b000 method>.
		'''			
		for uiName in self.getUiName('all'):

			if not self.widgets(uiName, query=True):
				if existing:
					continue
				self.widgets(uiName) #construct the signals and slots for the ui

			for widget, v in self.widgets(uiName).items():
				if method==v['method']:
					return widget


	def getWidgetName(self, widget=None, ui=None):
		'''Get the widget's stored string objectName.

		:Property:
			getWidgetNames

		:Parameters:
			widget (obj) = QWidget
			ui (str)(obj) = Parent ui name, or ui object. ie. 'polygons' or <polygons>
					If no name is given, the current ui will be used.

		:Return:
			if widget: (str) the stored objectName for the given widget.
			if not widget: (list) all names.
			if uiName: stored objectNames for the given ui name.
			if not uiName: stored objectName from the current ui.
			else: all stored objectNames.
		'''
		uiName = self.getUiName(ui)

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		if widget:
			if not widget in self.widgets(uiName):
				self.addWidget(uiName, widget)
			return self.widgets(uiName)[widget]['widgetName']

		if uiName and not widget: #return all objectNames from ui name.
			return [w['widgetName'] for w in self.widgets(uiName).values()]
		else: #return all objectNames:
			return [w['widgetName'] for k,w in self.sbDict.items() if k=='widgets']


	def removeWidgets(self, widgets, ui=None):
		'''Remove widget keys from the widgets dict.

		:Parameters:
			widgets (obj)(list) = single or list of QWidgets.
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.
		'''
		uiName = self.getUiName(ui)

		widgets = self.list_(widgets) #if 'widgets' isn't a list, convert it to one.
		for widget in widgets:
			w = self.widgets(uiName).pop(widget, None)
			self.gcProtect(w)

			try: #remove the widget attribute from the ui if it exists.
				delattr(ui, w.objectName())
			except Exception as error:
				pass; # print (__name__+':','removeWidgets:', widgets, uiName, error)


	def isTracked(self, widget, ui=None):
		'''Query if the widget is mouse tracked.

		:Parameters:
			widget (obj) = The widget to query the tracking state of.
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
		:Return:
			(bool)
		'''
		uiName = self.getUiName(ui)

		if not 'widgets' in self.sbDict[uiName]:
			self.widgets(uiName) #construct the signals and slots for the ui

		try:
			return self.sbDict[uiName]['widgets'][widget]['tracked']

		except KeyError as error:
			return False


	def getWidgetType(self, widget, ui=None):
		'''Get widget type class name as a string.
		ie. 'QPushButton' from pushbutton type widget.

		:Parameters:
			widget (str) = name of widget/widget
				*or <object> -widget
			ui (str)(obj) = ui name, or ui object. ie. 'polygons' or <polygons>
					If None is given, the current ui will be used.

		:Return:
			(str) The corresponding widget class name.
		'''
		uiName = self.getUiName(ui)

		if isinstance(widget, (str)):
			objectName = self.widgets(uiName)[widget] #use the stored objectName as a more reliable key.
			widget = self.getWidget(objectName, uiName) #use the objectName to get a string key for 'widget'

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		try:
			if not widget in self.widgets(uiName):
				self.addWidget(uiName, widget)
			return self.widgets(uiName)[widget]['widgetType']

		except KeyError:
			return None


	def getDerivedType(self, widget, ui=None):
		'''Get the base class of a custom widget.
		If the type is a standard widget, the derived type will be that widget's type.

		:Parameters:
			widget (str)(obj) = QWidget or it's objectName.
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.

		:Return:
			(string) base class name. ie. 'QPushButton' from a custom widget with class name: 'PushButton'
		'''
		uiName = self.getUiName(ui)

		if isinstance(widget, str):
			objectName = self.widgets(uiName)[widget] #use the stored objectName as a more reliable key.
			widget = self.getWidget(objectName, uiName) #use the objectName to get a string key for 'widget'

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		try:
			return self.widgets(uiName)[widget]['derivedType']

		except KeyError:
			# print(widget.__class__.__mro__)
			for c in widget.__class__.__mro__:
				if c.__module__=='PySide2.QtWidgets': #check for the first built-in class.
					derivedType = c.__name__ #Then use it as the derived class.
					return derivedType


	def getMethod(self, ui, widget=None):
		'''Get the method(s) associated with the given ui / widget.

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
			widget (str)(obj) = widget, widget's objectName, or method name.

		:Return:
			if widget: corresponding method object to given widget.
			else: all of the methods associated to the given ui name as a list.

		ex. sb.getMethod('polygons', <b022>)() #call method <b022> of the 'polygons' class
		'''
		name = self.getUiName(ui)

		if not self.widgets(name, query=True):
			self.widgets(name) #construct the signals and slots for the ui

		if widget is None: #get all methods for the given ui name.
			return [w['method'] for w in self.sbDict[name]['widgets'].values()]

		try:
			if isinstance(widget, str):
				return next(w['method'][0] for w in self.sbDict[name]['widgets'].values() if w['widgetName']==widget) #if there are event filters attached (as a list), just get the method (at index 0).
			
			elif not widget in self.sbDict[name]['widgets']:
				self.addWidget(name, widget)
			return self.sbDict[name]['widgets'][widget]['method'][0] #if there are event filters attached (as a list), just get the method (at index 0).

		except Exception as error:
			if isinstance(widget, str):
				return next((w['method'] for w in self.sbDict[name]['widgets'].values() if w['widgetName']==widget), None)

			elif not widget in self.sbDict[name]['widgets']:
				self.addWidget(name, widget)
			return self.sbDict[name]['widgets'][widget]['method']


	def getDocString(self, ui, method, first_line_only=True, unformatted=False):
		'''
		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
			method (str)(obj) = method, or name of method. ie. 'b001'
			unformatted = bool return entire unedited docString

		:Return:
			if unformatted: the entire stored docString
			else: edited docString; name of method
		'''
		name = self.getUiName(ui)

		if not self.widgets(name, query=True):
			self.widgets(name) #construct the signals and slots for the ui

		try: #get the doc string:
			docString = method.__doc__
		except:
			docString = next(w['docString'] for w in self.sbDict[name]['widgets'].values() if w['widgetName']==widgetName)
		if not docString:
			return None

		lines = docString.split('\n')
		if first_line_only:
			i=0
			while not docString:
				try:
					docString = lines[i]
					i+=1
				except IndexError:
					break

		if docString and not unformatted:
			return docString.strip('\n\t') #return formatted docString
		else:
			return docString #return entire unformatted docString, or 'None' is docString==None.


	def prevUiName(self, previousIndex=False, allowDuplicates=False, allowCurrent=False, omitLevel=[], as_list=False):
		'''Get the previously called ui name string, or a list of ui name strings ordered by use.
		It does so by pulling from the 'uiNames' list which keeps a list of the ui names as they are called. ie. ['previousName2', 'previousName1', 'currentName']

		:Property:
			prevName

		:Parameters:
			previousIndex (bool) = Return the index of the last valid previously opened ui name.
			allowDuplicates (bool) = Applicable when returning as_list. Allows for duplicate names in the returned list.
			omitLevel (int)(list) = Remove instances of the given ui level(s) from the results. Default is [] which omits nothing.
			allowCurrent (bool) = Allow the currentName. Default is off.
			as_list (bool) = Returns the full list of previously called names. By default duplicates are removed.

		:Return:
			with no arguments given - string name of previously opened ui.
			if previousIndex: int - index of previously opened ui
			if as_list: returns [list of string names]
		'''
		self._uiHistory = self._uiHistory[-200:] #keep original list length restricted to last 200 elements

		list_ = self._uiHistory #work on a copy of the list, keeping the original intact

		if not allowCurrent:
			list_ = list_[:-1] #remove the last index. (currentName)

		omitLevel = self.list_(omitLevel) #if omitLevel is not a list, convert it to one.
		list_ = [i for i in list_ if not self.getUiLevel(i) in omitLevel] #remove any items having a uiLevel of those in the omitLevel list.

		if not allowDuplicates:
			[list_.remove(l) for l in list_[:] if list_.count(l)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if previousIndex:
			validPrevious = [i for i in list_ if all(['cameras' not in i, 'main' not in i])]
			return self.getUiIndex(validPrevious[-2])

		elif as_list:
			return list_ #return entire list after being modified by any flags such as 'allowDuplicates'.

		else:
			try:
				return list_[-1] #return the previous ui name if one exists.
			except:
				return ''


	def prevCommand(self, docString=False, method=False, toolTip=False, as_list=False, add=None):
		'''Get previous commands and relevant information.

		:Parameters:
			docString (bool) = return the docString of last command. Default is off.
			method (bool) = return the method of last command. Default is off.
			toolTip (bool) = return the commands toolTip.
			as_list (bool) = Return the full list.
			add (obj) = Add a command (method) to the list. (if this flag is given, all other flags are invalidated)

		:Return:
			(str) if docString: 'string' description (derived from the last used command method's docString) (as_list: [string list] all docStrings, in order of use)
			(obj) if method: method of last used command. when combined with as_list; [<method object> list} all methods, in order of use)
			(str) if toolTip: the commands toolTip.
			(list) if as_list: list of lists with <method object> as first element and <docString> as second. ie. [[b001, 'multi-cut tool']]
			(obj) else: <method object> of the last used command
		'''
		if add:
			widget = self.getWidgetFromMethod(add, existing=True)
			name = self.getUiFromWidget(widget, uiName=True) #get the ui name.
			docString = self.getDocString(name, add)
			toolTip = widget.toolTip()
			self.prevCommand(as_list=1).append([add, docString, toolTip]) #store the method object and other relevant information about the command.
			return

		self._commandHistory = self._commandHistory[-20:] #keep original list length restricted to last 20 elements

		list_ = self._commandHistory
		[list_.remove(l) for l in list_[:] if list_.count(l)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if as_list:
			if all((method, not docString, not toolTip)): #100
				return [i[0] for i in list_]

			elif all((not method, docString, not toolTip)): #010
				return [i[1] for i in list_]

			elif all((not method, not docString, toolTip)): #001
				return [i[2] for i in list_]

			elif all((method, docString, not toolTip)): #110
				return [i[:2] for i in list_]

			elif all((not method, docString, toolTip)): #011
				return [i[1:] for i in list_]

			elif all((method, not docString, toolTip)): #101
				return [[i[0],i[2]] for i in list_]

			else:
				return list_ #111

		elif docString:
			try:
				return list_[-1][1]
			except:
				return ''

		elif toolTip:
			try:
				return list_[-1][2]
			except:
				return ''

		else:
			try:
				return list_[-1][0]
			except:
				return None


	def prevCamera(self, docString=False, method=False, allowCurrent=False, as_list=False, add=None):
		'''
		:Parameters:
			docString (bool) = return the docString of last camera command. Default is off.
			method (bool) = return the method of last camera command. Default is off.
			allowCurrent (bool) = allow the current camera. Default is off.
			add (str)(obj) = Add a method, or name of method to be used as the command to the current camera.  (if this flag is given, all other flags are invalidated)

		:Return:
			if docString: 'string' description (derived from the last used camera command's docString) (as_list: [string list] all docStrings, in order of use)
			if method: method of last used camera command. (as_list: [<method object> list} all methods, in order of use)
			if as_list: list of lists with <method object> as first element and <docString> as second. ie. [[<v001>, 'camera: persp']]
			else : <method object> of the last used command
		'''
		if add: #set the given method as the current camera.
			if not callable(add):
				add = self.getMethod('cameras', add)
			docString = self.getDocString('cameras', add)
			prevCameraList = self.prevCamera(allowCurrent=True, as_list=1)
			if not prevCameraList or not [add, docString]==prevCameraList[-1]: #ie. do not append perp cam if the prev cam was perp.
				prevCameraList.append([add, docString]) #store the camera view
			return

		self._cameraHistory = self._cameraHistory[-20:] #keep original list length restricted to last 20 elements

		list_ = self._cameraHistory
		[list_.remove(l) for l in list_[:] if list_.count(l)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if not allowCurrent:
			list_ = list_[:-1] #remove the last index. (currentName)

		if as_list:
			if docString and not method:
				try:
					return [i[1] for i in list_]
				except:
					return None
			elif method and not docString:
				try:
					return [i[0] for i in list_]
				except:
					return ['# No commands in history. #']
			else:
				return list_

		elif docString:
			try:
				return list_[-1][1]
			except:
				return ''

		else:
			try:
				return list_[-1][0]
			except:
				return None


	def gcProtect(self, obj=None, clear=False):
		'''Protect given object from garbage collection.

		:Parameters:
			obj (obj) = obj to add to the protected list.

		:Return:
			(list) of protected objects.
		'''
		if clear:
			return self._gcProtect[:]

		if obj and obj not in self._gcProtect:
			self._gcProtect.append(obj)

		return self._gcProtect


	def get(self, obj, type_='value', _nested_dict=None, _nested_list=[]):
		'''Get objects from any nested object in _nested_dict using a given key or value.

		:Parameters:
			obj (key)(value) = Key or Value. The object to get the 'type_' of return value from.
			type_ (str) = Desired return type. valid values are: 'value', 'valuesFromKey', 'keysFromValue', 'namesFromValue'
			_nested_dict (dict) = internal use. default is sbDict
			_nested_list (list) = internal use.

		:Return:
			(list) depending on the specified type.

		ex. call:
		self.get('cmb002', 'nameFromValue') #returns a list of all ui names containing 'cmb002' values.
		'''
		if _nested_dict is None:
			_nested_dict = self.sbDict

		for k,v in _nested_dict.items():
			if type_=='valuesFromKey': 
				if k==obj: #found key
					_nested_list.append(v)

			elif type_=='keysFromValue':
				if v==obj: #found value
					_nested_list.append(k)

			elif type_=='namesFromValue':
				if v==obj: #found value
					_nested_list.append(self.getParentKeys(v)[0])

			if type(v) is dict: #found dict
				p = self.get(obj, type_, v, _nested_list) #recursive call
				if p:
					return p
		return _nested_list


	def getParentKeys(self, value, _nested_dict=None):
		'''Get all parent keys from a nested value.

		:Parameters:
			value (value) = The nested value to get keys for.
			_nested_dict (dict) = internal use.

		:Return:
			(list) parent keys. ex. ['polygons', 'widgets', '<widgets.ComboBox.ComboBox object at 0x0000016B6C078908>', 'widgetName']

		ex. call: getParentKeys('cmb002') returns all parent keys of the given value.
		'''
		if _nested_dict is None:
			_nested_dict = self.sbDict

		for k,v in _nested_dict.items():
			if type(v) is dict:
				p = self.getParentKeys(value, v)
				if p:
					return [k]+p
			elif v==value:
				return [k]


	def _getUiLevelFromDir(self, filePath):
		'''Get the UI level by looking for trailing intergers in it's dir name.
		If none are found a default level of 0 is used.

		:Parameters:
			filePath (str) = The ui's full filepath. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/uiLevel_0/init.ui'

		:Return:
			(int)
		'''
		uiFolder = self.formatFilepath(filePath, 'dir')

		try:
			import re
			uiLevel = int(re.findall(r"\d+\s*$", uiFolder)[0]) #get trailing integers.

		except IndexError as error: #not an int.
			uiLevel = 0

		return uiLevel


	def getUiLevel(self, ui=None):
		'''Get the hierarcical level of a ui.
		If no argument is given, the level of current ui will be returned.

		level 0: init (root)
		level 1: base menus
		level 2: sub menus
		level 3: main menus

		:Property:
			uiLevel

		:Parameters:
			ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
							If None is given, the current ui will be used.

		:Return:
			(int) ui level.
		'''
		try:
			n = self.getUiName(ui)
			uiName = self.setCase(n, 'camelCase') #lowercase the first letter of name.
			return self.sbDict[uiName]['uiLevel']['base']

		except KeyError as error:
			print ('# KeyError: {}.getUiLevel({}): {} #'.format(__name__, ui, error))
			return None


	def prefix(self, widget, prefix=None, ui=None):
		'''Query a widgets prefix.
		A valid prefix is returned when the given widget's objectName startswith an alphanumeric char, followed by at least three integers. ex. i000 (alphanum,int,int,int)
		if the second 'prefix' arg is given, then the method checks if the given objectName has the prefixinst the return value is bool.
		ex. prefix('b023') returns 'b'. #get prefix.
		ex. prefix('b023', prefix='b') returns True. #query prefix match.

		prefix types: 'QPushButton':'b', 'QPushButton':'v', 'QPushButton':'i', 'QPushButton':'tb', 'QComboBox':'cmb', 
			'QCheckBox':'chk', 'QRadioButton':'chk', 'QPushButton(checkable)':'chk', 'QSpinBox':'s', 'QDoubleSpinBox':'s',
			'QLabel':'lbl', 'QWidget':'w', 'QTreeWidget':'tree', 'QListWidget':'list', 'QLineEdit':'line', 'QTextEdit':'text'

		:Parameters:
			widget (str)(obj) = A widget, or it's objectName.
			prefix (str)(list) = Check if the given objectName startwith this prefix.
			ui (str)(obj) = Parent ui name, or ui object. ie. 'polygons' or <polygons>
							If no name is given, the current ui will be used.

		:Return:
			if prefix arg given:
				(bool) True if correct format, else False.
			else:
				(str) alphanumeric 'string'.

		ex call: sb.prefix(widget, ['b', 'chk', '_']) #return True if the given widget's objectName starts with 'b', 'chk', '_' and is followed by 3 or more integers, else False.
		'''
		if prefix is not None: #check the actual prefix against the given prefix and return bool.
			prefix = self.list_(prefix) #if 'widgets' isn't a list, convert it to one.

			uiName = self.getUiName(ui)
			for p in prefix:
				try:
					if isinstance(widget, (str)): #get the prefix using the widget's objectName.
						prefix_ = next(w['prefix'] for w in self.widgets(uiName).values() if w['widgetName']==widget)
					else:
						prefix_ = self.widgets(uiName)[widget]['prefix']
					if prefix_==p:
						return True

				except:
					if not isinstance(widget, (str)):
						widget = widget.objectName()
					if widget.startswith(p):
						i = len(p)
						integers = [c for c in widget[i:i+3] if c.isdigit()]
						if len(integers)>2 or len(widget)==i:
							return True
			return False

		else: #return prefix.
			prefix=''
			if not isinstance(widget, (str)):
				widget = widget.objectName()
			for char in widget:
				if not char.isdigit():
					prefix = prefix+char
				else:
					break

			i = len(prefix)
			integers = [c for c in widget[i:i+3] if c.isdigit()]
			if len(integers)>2 or len(widget)==i:
				return prefix


	def setCase(self, s, case='camelCase'):
		'''Format the given string(s) in the given case.
		
		:Parameters:
			s (str)(list) = The string(s) to format.
			case (str) = The desired return case.

		:Return:
			(str)(list)
		'''
		if case=='pascalCase':
			s = [n[:1].capitalize()+n[1:] for n in self.list_(s)] #capitalize the first letter.

		elif case=='camelCase':
			s = [n[0].lower()+n[1:] for n in self.list_(s)] #lowercase the first letter.

		return s[0] if len(s)==1 else s


	@staticmethod
	def getParentWidgets(widget, objectNames=False):
		'''Get the all parent widgets of the given widget.

		:Parameters:
			widget (obj) = QWidget
			objectNames (bool) = Return as objectNames.

		:Return:
			(list) Object(s) or objectName(s)
		'''
		parentWidgets=[]
		w = widget
		while w:
			parentWidgets.append(w)
			w = w.parentWidget()
		if objectNames:
			return [str(w.objectName()) for w in parentWidgets]
		return parentWidgets


	@staticmethod
	def getTopLevelParent(widget, index=-1):
		'''Get the parent widget at the top of the hierarchy for the given widget.

		:Parameters:
			widget (obj) = QWidget
			index (int) = Last index is top level.

		:Return:
			(QWidget)
		'''
		return self.getParentWidgets[index]


	@staticmethod
	def qApp_getWindow(name=None):
		'''Get Qt window/s

		:Parameters:
			name (str) = optional name of window (widget.objectName)

		:Return:
			if name: corresponding <window object>
			else: return a dictionary of all windows {windowName:window}
		'''
		windows = {w.objectName():w for w in QApplication.allWindows()}
		if name:
			return windows[name]
		else:
			return windows


	@staticmethod
	def qApp_getWidget(name=None):
		'''Get Qt widget/s

		:Parameters:
			name (str) = optional name of widget (widget.objectName)

		:Return:
			if name: corresponding <widget object>
			else: return a dictionary of all widgets {objectName:widget}
		'''
		widgets = {w.objectName():w for w in QApplication.allWidgets()}
		if name:
			return widgets[name]
		else:
			return widgets


	@staticmethod
	def formatFilepath(string, returnType=''):
		'''Format a full path to file string from '\' to '/'.
		When a returnType arg is given, the correlating section of the string will be returned.

		:Parameters:
			string (str) = The file path string to be formatted.
			returnType (str) = valid: 'path' (path without file), 'dir' (dir name), 'file'(name+ext), 'name', 'ext', if '' is given, the fullpath will be returned.

		:Return:
			(str)
		'''
		string = os.path.expandvars(string) #convert any env variables to their values.
		string = '/'.join(string.split('\\')) #convert forward slashes to back slashes.

		# issue: if a directory in fullpath contains '.' then results may not be accurate.
		fullpath = string if '/' in string else ''
		path = '/'.join(string.split('/')[:-1]) if '.' in string else string
		filename = string.split('/')[-1] if '.' in string else ''
		directory = string.split('/')[-2] if filename else string.split('/')[-1]
		name = ''.join(filename.split('.')[:-1]) if '.' in string else '' if '/' in string else string
		ext = filename.split('.')[-1]

		if returnType=='path':
			string = path

		elif returnType=='dir':
			string = directory

		elif returnType=='file':
			string = filename

		elif returnType=='name':
			string = name

		elif returnType=='ext':
			string = ext

		return string #if '' is given, the fullpath will be returned.


	@staticmethod
	def list_(x):
		'''Convert a given obj to a list if it isn't a list, set, or tuple already.

		:Parameters:
			x (unknown) = The object to convert to a list if not already a list, set, or tuple.

		:Return:
			(list)
		'''
		return list(x) if isinstance(x, (list, tuple, set, dict)) else [x]


	@staticmethod
	def convert(obj):
		'''Recursively convert items in sbDict for debugging.

		:Parameters:
			obj (dict) = The dictionary to convert.

		:Return:
			(dict)
		'''
		if isinstance(obj, (list, set, tuple)):
			return [Switchboard.convert(i) for i in obj]
		elif isinstance(obj, dict):
			return {Switchboard.convert(k):Switchboard.convert(v) for k, v in obj.items()}
		elif not isinstance(obj, (float, int, str)):
			return str(obj)
		else:
			return obj


	#assign properties
	# sbDict = property(getSbDict)
	uiName = property(getUiName, _setUiName)
	prevName = property(prevUiName)
	ui = property(getUi)
	uiIndex = property(getUiIndex)
	uiLevel = property(getUiLevel)
	uiState = property(getUiState, setUiState)
	size = property(getUiSize, setUiSize)
	sizeX = property(getUiSizeX, setUiSizeX)
	sizeY = property(getUiSizeY, setUiSizeY)
	slotInstance = property(getSlotInstance, _setSlotInstance)
	mainAppWindow = property(getMainAppWindow, setMainAppWindow)
	getWidgets = property(getWidget)
	getWidgetNames = property(getWidgetName)









if __name__=='__main__':
	import sys, os
	from PySide2.QtWidgets import QApplication

	sb = Switchboard()
	ui = sb.edit(setAsCurrent=True) #same as: sb.getUi('edit', setAsCurrent=True)

	widgets = ui.widgets()
	ui.setStyleSheet_(widgets)

	ui.show()
	qApp = QApplication.instance() #get the qApp instance if it exists.
	sys.exit(qApp.exec_())









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

'''
test example of sbDict:
sbDict = {'init': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbd210, name="QtUi") at 0x000001C20905C248>', 'uiLevel': {'base': 0, 0: ['init'], 1: [], 3: [], 2: [], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbd510, name="staticWindow") at 0x000001C20905C2C8>': {'widgetName': 'staticWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'staticWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QGridLayout(0x1c221556940, name = "gridLayout") at 0x000001C20905C548>': {'widgetName': 'gridLayout', 'widgetType': 'QGridLayout', 'derivedType': 'QGridLayout', 'signalInstance': 'None', 'method': 'None', 'prefix': 'gridLayout', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.textEdit.TextEdit(0x1c220961960, name="hud") at 0x000001C20905C508>': {'widgetName': 'hud', 'widgetType': 'TextEdit', 'derivedType': 'QTextEdit', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927A7B0>', 'method': 'None', 'prefix': 'hud', 'docString': 'None', 'tracked': False}}, 'class': '<maya_init.Init(0x1c22781fab0) at 0x000001C209135A48>', 'size': [600, 400]}, 'cameras': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbde10, name="QtUi") at 0x000001C20905C608>', 'uiLevel': {'base': 1}, 'state': 0}, 'editors': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbe010, name="QtUi") at 0x000001C209061088>', 'uiLevel': {'base': 1}, 'state': 0}, 'main': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbd350, name="QtUi") at 0x000001C2090611C8>', 'uiLevel': {'base': 1, 0: [], 1: ['main'], 3: [], 2: [], 4: ['main_lower']}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbdb10, name="mainWindow") at 0x000001C2090610C8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QGridLayout(0x1c221560de0, name = "gridLayout") at 0x000001C209061588>': {'widgetName': 'gridLayout', 'widgetType': 'QGridLayout', 'derivedType': 'QGridLayout', 'signalInstance': 'None', 'method': 'None', 'prefix': 'gridLayout', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QWidget(0x1c220bc2dd0, name="staticWindow") at 0x000001C209061608>': {'widgetName': 'staticWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'staticWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QWidget(0x1c220bc2e50, name="w002") at 0x000001C209061688>': {'widgetName': 'w002', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'w', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc2e90, name="i000") at 0x000001C209061708>': {'widgetName': 'i000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA56B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QWidget(0x1c220bc3010, name="main") at 0x000001C2090616C8>': {'widgetName': 'main', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'main', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3550, name="i010") at 0x000001C209061788>': {'widgetName': 'i010', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5530>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3a90, name="i012") at 0x000001C209061808>': {'widgetName': 'i012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA54D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3ad0, name="i013") at 0x000001C209061888>': {'widgetName': 'i013', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA54F0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3450, name="i009") at 0x000001C209061908>': {'widgetName': 'i009', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5450>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3b10, name="i008") at 0x000001C209061988>': {'widgetName': 'i008', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5470>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3c90, name="i007") at 0x000001C209061A08>': {'widgetName': 'i007', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5410>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3d10, name="i011") at 0x000001C209061A88>': {'widgetName': 'i011', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA55F0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3d90, name="i014") at 0x000001C209061B48>': {'widgetName': 'i014', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5430>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc3e10, name="i015") at 0x000001C209061BC8>': {'widgetName': 'i015', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA53D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc32d0, name="i003") at 0x000001C209061C48>': {'widgetName': 'i003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5690>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QWidget(0x1c220bc3590, name="w000") at 0x000001C209061C88>': {'widgetName': 'w000', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'w', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QWidget(0x1c220bc45d0, name="w001") at 0x000001C209061CC8>': {'widgetName': 'w001', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'w', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QWidget(0x1c220bc4b50, name="w003") at 0x000001C209061D08>': {'widgetName': 'w003', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'w', 'docString': 'None', 'tracked': True}}, 'class': '<maya_main.Main(0x1c22782be30) at 0x000001C208FA2388>', 'size': [600, 400]}, 'animation_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbdd50, name="QtUi") at 0x000001C2090615C8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['animation'], 2: ['animation_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bc4990, name="mainWindow") at 0x000001C209061E08>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc4dd0, name="i013") at 0x000001C209060048>': {'widgetName': 'i013', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4A30>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc4310, name="i024") at 0x000001C209060108>': {'widgetName': 'i024', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B43B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc4890, name="i020") at 0x000001C209060188>': {'widgetName': 'i020', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4F50>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc4d90, name="i016") at 0x000001C209060208>': {'widgetName': 'i016', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4BD0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc4e90, name="b000") at 0x000001C209060288>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4BB0>', 'method': '<bound method Animation.b000 of <maya_animation.Animation(0x1c22b654e90) at 0x000001C20976FD08>>', 'prefix': 'b', 'docString': '\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c26bef7460, name="tb000") at 0x000001C209061D48>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4A50>', 'method': '<bound method Animation.tb000 of <maya_animation.Animation(0x1c22b654e90) at 0x000001C20976FD08>>', 'prefix': 'tb', 'docString': 'Set Current Frame\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QSpinBox(0x1c2210e8620, name="s000") at 0x000001C209750F48>': {'widgetName': 's000', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478790>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c2210e7ba0, name="chk000") at 0x000001C209750E08>': {'widgetName': 'chk000', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094787B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c2210e92d0, name="chk001") at 0x000001C209750D48>': {'widgetName': 'chk001', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094787F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2210e9ab0, name="return_area") at 0x000001C209750A88>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094788D0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'cameras_lower_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbdb90, name="QtUi") at 0x000001C209061508>', 'uiLevel': {'base': 2}, 'state': 0}, 'convert_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbdb50, name="QtUi") at 0x000001C209060548>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['convert'], 2: ['convert_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbe9d0, name="mainWindow") at 0x000001C209060348>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbea10, name="i002") at 0x000001C2090605C8>': {'widgetName': 'i002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793390>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220ba8c50, name="b000") at 0x000001C209060688>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793410>', 'method': '<bound method Convert.b000 of <maya_convert.Convert(0x1c22d88de30) at 0x000001C2094263C8>>', 'prefix': 'b', 'docString': 'Polygon Edges to Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220ba8210, name="b001") at 0x000001C2090606C8>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793370>', 'method': '<bound method Convert.b001 of <maya_convert.Convert(0x1c22d88de30) at 0x000001C2094263C8>>', 'prefix': 'b', 'docString': 'Instance to Object\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220ba86d0, name="b002") at 0x000001C209060748>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793310>', 'method': '<bound method Convert.b002 of <maya_convert.Convert(0x1c22d88de30) at 0x000001C2094263C8>>', 'prefix': 'b', 'docString': 'NURBS to Polygons\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220ba8510, name="b003") at 0x000001C2090607C8>': {'widgetName': 'b003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097932F0>', 'method': '<bound method Convert.b003 of <maya_convert.Convert(0x1c22d88de30) at 0x000001C2094263C8>>', 'prefix': 'b', 'docString': 'Smooth Mesh Preview to Polygons\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f8ca80, name="return_area") at 0x000001C209436CC8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793450>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f8f410, name="i007") at 0x000001C209453FC8>': {'widgetName': 'i007', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793990>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'crease_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbead0, name="QtUi") at 0x000001C209060848>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['crease'], 2: ['crease_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bb7350, name="mainWindow") at 0x000001C209060988>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb7550, name="i026") at 0x000001C209060A08>': {'widgetName': 'i026', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146310>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb7e10, name="chk011") at 0x000001C209060A88>': {'widgetName': 'chk011', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091461F0>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb75d0, name="chk002") at 0x000001C209060B08>': {'widgetName': 'chk002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146290>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c221544b10, name="tb000") at 0x000001C209060888>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146230>', 'method': '<bound method Crease.tb000 of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'tb', 'docString': 'Crease\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb8b10, name="chk003") at 0x000001C209060B88>': {'widgetName': 'chk003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146210>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QSpinBox(0x1c220e49340, name="s003") at 0x000001C209166FC8>': {'widgetName': 's003', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091466F0>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c220e4bd40, name="chk003") at 0x000001C20915CF08>': {'widgetName': 'chk003', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146610>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c220e4aca0, name="chk002") at 0x000001C20915CEC8>': {'widgetName': 'chk002', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091465D0>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c220e4b4f0, name="chk005") at 0x000001C20915CE08>': {'widgetName': 'chk005', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146590>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QSpinBox(0x1c220e4a300, name="s004") at 0x000001C20915CF48>': {'widgetName': 's004', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146570>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c220e4d710, name="chk004") at 0x000001C20915CD48>': {'widgetName': 'chk004', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146630>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c220e4d390, name="chk011") at 0x000001C20915CBC8>': {'widgetName': 'chk011', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146450>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QSpinBox(0x1c220e4d550, name="s005") at 0x000001C20915CB48>': {'widgetName': 's005', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091464B0>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QSpinBox(0x1c220e4ec80, name="s006") at 0x000001C20915CC08>': {'widgetName': 's006', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091460D0>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e524f0, name="return_area") at 0x000001C209156F08>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146810>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e52250, name="i002") at 0x000001C20915C0C8>': {'widgetName': 'i002', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146A50>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e55dd0, name="i010") at 0x000001C209072F88>': {'widgetName': 'i010', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091467F0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'create_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbea50, name="QtUi") at 0x000001C209060C08>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['create'], 2: ['create_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bc0b50, name="mainWindow") at 0x000001C209060588>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc1010, name="i006") at 0x000001C209060C88>': {'widgetName': 'i006', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793EF0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb6790, name="b001") at 0x000001C209060D48>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793ED0>', 'method': '<bound method Create.b001 of <maya_create.Create(0x1c22d88a5f0) at 0x000001C20944F8C8>>', 'prefix': 'b', 'docString': 'Create poly cube\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb7fd0, name="b002") at 0x000001C209060D88>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793430>', 'method': '<bound method Create.b002 of <maya_create.Create(0x1c22d88a5f0) at 0x000001C20944F8C8>>', 'prefix': 'b', 'docString': 'Create poly sphere\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb7510, name="b003") at 0x000001C209060DC8>': {'widgetName': 'b003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793B70>', 'method': '<bound method Create.b003 of <maya_create.Create(0x1c22d88a5f0) at 0x000001C20944F8C8>>', 'prefix': 'b', 'docString': 'Create poly cylinder\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb8410, name="b004") at 0x000001C209060E08>': {'widgetName': 'b004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793A10>', 'method': '<bound method Create.b004 of <maya_create.Create(0x1c22d88a5f0) at 0x000001C20944F8C8>>', 'prefix': 'b', 'docString': 'Create poly plane\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f88330, name="return_area") at 0x000001C209451BC8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097933D0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f89e50, name="i007") at 0x000001C209441FC8>': {'widgetName': 'i007', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793AD0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'deformation_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bc00d0, name="QtUi") at 0x000001C209060C48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['deformation'], 2: ['deformation_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bc0490, name="mainWindow") at 0x000001C209060BC8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc04d0, name="i020") at 0x000001C209060EC8>': {'widgetName': 'i020', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B41D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2210eda90, name="return_area") at 0x000001C20973C308>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478270>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2210ef770, name="i013") at 0x000001C209784EC8>': {'widgetName': 'i013', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4590>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'display_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bc0c50, name="QtUi") at 0x000001C209060F48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['display'], 2: ['display_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bc0e90, name="mainWindow") at 0x000001C209060E88>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bc0f50, name="i032") at 0x000001C209063048>': {'widgetName': 'i032', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478AD0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb8850, name="b002") at 0x000001C2090630C8>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478AB0>', 'method': '<bound method Display.b002 of <maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>>', 'prefix': 'b', 'docString': 'Hide Selected\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb8210, name="b003") at 0x000001C209063108>': {'widgetName': 'b003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478A50>', 'method': '<bound method Display.b003 of <maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>>', 'prefix': 'b', 'docString': 'Show Selected\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb9b50, name="b005") at 0x000001C209063148>': {'widgetName': 'b005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478A70>', 'method': '<bound method Display.b005 of <maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>>', 'prefix': 'b', 'docString': 'Xray Selected\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb98d0, name="b021") at 0x000001C2090631C8>': {'widgetName': 'b021', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478A10>', 'method': '<bound method Display.b021 of <maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>>', 'prefix': 'b', 'docString': 'Template Selected\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb9110, name="b006") at 0x000001C209063248>': {'widgetName': 'b006', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094789F0>', 'method': '<bound method Display.b006 of <maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>>', 'prefix': 'b', 'docString': 'Un-Xray All\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb9b90, name="b007") at 0x000001C2090632C8>': {'widgetName': 'b007', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094789D0>', 'method': '<bound method Display.b007 of <maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>>', 'prefix': 'b', 'docString': 'Xray Other\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b602100, name="return_area") at 0x000001C209748D88>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478230>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b6033d0, name="i003") at 0x000001C209744448>': {'widgetName': 'i003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478950>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'duplicate_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bc0390, name="QtUi") at 0x000001C209060F88>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['duplicate'], 2: ['duplicate_submenu'], 4: ['duplicate_linear', 'duplicate_radial']}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220ba7890, name="mainWindow") at 0x000001C209063348>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220ba7d90, name="i025") at 0x000001C209063388>': {'widgetName': 'i025', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793470>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb9fd0, name="b004") at 0x000001C209063448>': {'widgetName': 'b004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793BB0>', 'method': '<bound method Duplicate.b004 of <maya_duplicate.Duplicate(0x1c22d88df50) at 0x000001C2094361C8>>', 'prefix': 'b', 'docString': 'Select Instanced Objects\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bba050, name="b005") at 0x000001C209063488>': {'widgetName': 'b005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793BF0>', 'method': '<bound method Duplicate.b005 of <maya_duplicate.Duplicate(0x1c22d88df50) at 0x000001C2094361C8>>', 'prefix': 'b', 'docString': 'Uninstance Selected Objects\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bb9250, name="i019") at 0x000001C2090634C8>': {'widgetName': 'i019', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793490>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f91160, name="return_area") at 0x000001C209428348>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793D70>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f931c0, name="i007") at 0x000001C209424F48>': {'widgetName': 'i007', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793510>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'editors_lower_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220ba8750, name="QtUi") at 0x000001C209060F08>', 'uiLevel': {'base': 2}, 'state': 0}, 'edit_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bb60d0, name="QtUi") at 0x000001C209063688>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['edit'], 2: ['edit_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbcf90, name="mainWindow") at 0x000001C209063C48>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbc650, name="i025") at 0x000001C209063CC8>': {'widgetName': 'i025', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8A10>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbcc90, name="i004") at 0x000001C209063D08>': {'widgetName': 'i004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8A30>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbcfd0, name="i006") at 0x000001C209063D88>': {'widgetName': 'i006', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8990>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbc890, name="i002") at 0x000001C209063DC8>': {'widgetName': 'i002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A89B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbcd10, name="i007") at 0x000001C209063E08>': {'widgetName': 'i007', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8950>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c27cae38b0, name="tb001") at 0x000001C209063708>': {'widgetName': 'tb001', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8930>', 'method': '<bound method Edit.tb001 of <maya_edit.Edit(0x1c22caacbf0) at 0x000001C209783088>>', 'prefix': 'tb', 'docString': 'Delete History\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c27cae5e50, name="tb000") at 0x000001C209063308>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8910>', 'method': '<bound method Edit.tb000 of <maya_edit.Edit(0x1c22caacbf0) at 0x000001C209783088>>', 'prefix': 'tb', 'docString': 'Mesh Cleanup\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c27cae54b0, name="tb002") at 0x000001C209063808>': {'widgetName': 'tb002', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8F90>', 'method': '<bound method Edit.tb002 of <maya_edit.Edit(0x1c22caacbf0) at 0x000001C209783088>>', 'prefix': 'tb', 'docString': 'Delete\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c27cae64e0, name="tb003") at 0x000001C209063908>': {'widgetName': 'tb003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A88F0>', 'method': '<bound method Edit.tb003 of <maya_edit.Edit(0x1c22caacbf0) at 0x000001C209783088>>', 'prefix': 'tb', 'docString': 'Delete Along Axis\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c217fa7520, name="b001") at 0x000001C209063F08>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A88D0>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_edit.Edit(0x1c22caacbf0) at 0x000001C209783088>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd069d0, name="chk018") at 0x000001C209783BC8>': {'widgetName': 'chk018', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A85F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd062d0, name="chk019") at 0x000001C20977DC08>': {'widgetName': 'chk019', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8690>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd07370, name="chk020") at 0x000001C209444F48>': {'widgetName': 'chk020', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A86B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd06d50, name="chk005") at 0x000001C209444CC8>': {'widgetName': 'chk005', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A86D0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd08db0, name="chk004") at 0x000001C209444C88>': {'widgetName': 'chk004', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8730>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd09ad0, name="chk002") at 0x000001C209444B48>': {'widgetName': 'chk002', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8750>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd09d70, name="chk017") at 0x000001C209444A88>': {'widgetName': 'chk017', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8790>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd09440, name="chk021") at 0x000001C209444BC8>': {'widgetName': 'chk021', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A87B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0c000, name="chk010") at 0x000001C209444A48>': {'widgetName': 'chk010', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8710>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0afd0, name="chk011") at 0x000001C209444988>': {'widgetName': 'chk011', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A87D0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0a9b0, name="chk003") at 0x000001C209444748>': {'widgetName': 'chk003', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A87F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0bcf0, name="chk012") at 0x000001C209444688>': {'widgetName': 'chk012', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8830>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0bc10, name="chk018") at 0x000001C2094447C8>': {'widgetName': 'chk018', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8850>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0d0a0, name="chk016") at 0x000001C209444408>': {'widgetName': 'chk016', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8870>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0d420, name="chk013") at 0x000001C209444388>': {'widgetName': 'chk013', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A88B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22bd0c700, name="s006") at 0x000001C209444308>': {'widgetName': 's006', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793050>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0f870, name="chk014") at 0x000001C2094442C8>': {'widgetName': 'chk014', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097930B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22bd0f250, name="s007") at 0x000001C209444248>': {'widgetName': 's007', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097930D0>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd11240, name="chk015") at 0x000001C209444148>': {'widgetName': 'chk015', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793130>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22bd10e50, name="s008") at 0x000001C209444088>': {'widgetName': 's008', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793150>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd0faa0, name="chk022") at 0x000001C209442BC8>': {'widgetName': 'chk022', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097931B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd12dd0, name="chk023") at 0x000001C209442C08>': {'widgetName': 'chk023', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097931D0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd147a0, name="chk001") at 0x000001C209442A88>': {'widgetName': 'chk001', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097931F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd13310, name="chk000") at 0x000001C2097AE508>': {'widgetName': 'chk000', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793230>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22bd15d80, name="chk006") at 0x000001C2097AE408>': {'widgetName': 'chk006', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793250>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QRadioButton(0x1c22bd15920, name="chk007") at 0x000001C2097AE388>': {'widgetName': 'chk007', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793FD0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c22bd15300, name="chk008") at 0x000001C2097AE0C8>': {'widgetName': 'chk008', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793FB0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c22bd17a60, name="chk009") at 0x000001C2097AE188>': {'widgetName': 'chk009', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793F90>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22bd18e10, name="return_area") at 0x000001C2094560C8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793330>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'file_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bb8a50, name="QtUi") at 0x000001C209063F48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['file'], 2: ['file_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbc250, name="mainWindow") at 0x000001C209065248>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbc550, name="i017") at 0x000001C2090652C8>': {'widgetName': 'i017', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4EB0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbcdd0, name="b001") at 0x000001C209065348>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4630>', 'method': '<bound method Slots.hideMain.<locals>.wrapper of <maya_file.File(0x1c22b1ed7f0) at 0x000001C209748548>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbca10, name="b007") at 0x000001C209065388>': {'widgetName': 'b007', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4330>', 'method': '<bound method Slots.hideMain.<locals>.wrapper of <maya_file.File(0x1c22b1ed7f0) at 0x000001C209748548>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbc750, name="b008") at 0x000001C2090653C8>': {'widgetName': 'b008', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4B10>', 'method': '<bound method Slots.hideMain.<locals>.wrapper of <maya_file.File(0x1c22b1ed7f0) at 0x000001C209748548>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c27cae7120, name="tb000") at 0x000001C209063F88>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4E10>', 'method': '<bound method File.tb000 of <maya_file.File(0x1c22b1ed7f0) at 0x000001C209748548>>', 'prefix': 'tb', 'docString': 'Save\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b6092c0, name="return_area") at 0x000001C20973FC88>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4950>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b609bf0, name="i003") at 0x000001C20973CFC8>': {'widgetName': 'i003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4C90>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'lighting_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c220bbb550, name="QtUi") at 0x000001C209063EC8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['lighting'], 2: ['lighting_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbb1d0, name="mainWindow") at 0x000001C209065208>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbb190, name="i014") at 0x000001C209065488>': {'widgetName': 'i014', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B46F0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22af4d270, name="return_area") at 0x000001C2090CB988>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4CD0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'main_lower_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c27ee7ab20, name="QtUi") at 0x000001C209065448>', 'uiLevel': {'base': 2}, 'state': 0}, 'materials_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c26bfc8fc0, name="QtUi") at 0x000001C209065408>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['materials'], 2: ['materials_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c26bfc8900, name="mainWindow") at 0x000001C209065908>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfc81c0, name="i018") at 0x000001C209065988>': {'widgetName': 'i018', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092AB0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfc8400, name="i005") at 0x000001C209065A08>': {'widgetName': 'i005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092A90>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfc91c0, name="i012") at 0x000001C209065A88>': {'widgetName': 'i012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092A70>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfc9500, name="b002") at 0x000001C209065AC8>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092210>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227279d00, name="tb000") at 0x000001C209065688>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092C70>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfda940, name="b001") at 0x000001C209065B08>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092C90>', 'method': '<bound method Materials.b001 of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'b', 'docString': 'Material List: Edit\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfdbcc0, name="b004") at 0x000001C209065B48>': {'widgetName': 'b004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092CB0>', 'method': '<bound method Materials.b004 of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'b', 'docString': 'Assign: Assign Random\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfdbd40, name="b005") at 0x000001C209065B88>': {'widgetName': 'b005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092CD0>', 'method': '<bound method Materials.b005 of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'b', 'docString': 'Assign: Assign New\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfdbe80, name="b003") at 0x000001C209065BC8>': {'widgetName': 'b003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092A30>', 'method': '<bound method Materials.b003 of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'b', 'docString': 'Assign: Assign Current\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfdb280, name="b000") at 0x000001C209065C08>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092A10>', 'method': '<bound method Materials.b000 of <maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>>', 'prefix': 'b', 'docString': 'Material List: Delete\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c228d930e0, name="chk003") at 0x000001C2090B9F08>': {'widgetName': 'chk003', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092BB0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c228d94260, name="chk005") at 0x000001C2090B9D88>': {'widgetName': 'chk005', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092F90>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c228d932a0, name="chk006") at 0x000001C2090B9CC8>': {'widgetName': 'chk006', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092730>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c228d969c0, name="return_area") at 0x000001C2090BDB48>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092F30>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'mirror_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c26bfdb380, name="QtUi") at 0x000001C209065C48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['mirror'], 2: ['mirror_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c26bfdc800, name="mainWindow") at 0x000001C209065F08>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c26bfdd040, name="i019") at 0x000001C209065F88>': {'widgetName': 'i019', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793930>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272728a0, name="tb000") at 0x000001C209065C88>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793910>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_mirror.Mirror(0x1c22d890010) at 0x000001C20942C8C8>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220bbc490, name="chk005") at 0x000001C209065FC8>': {'widgetName': 'chk005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793550>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_mirror.Mirror(0x1c22d890010) at 0x000001C20942C8C8>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c232f966b0, name="chk000") at 0x000001C209428848>': {'widgetName': 'chk000', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793890>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QRadioButton(0x1c232f98390, name="chk001") at 0x000001C209434EC8>': {'widgetName': 'chk001', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793750>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c232f989b0, name="chk002") at 0x000001C209434D48>': {'widgetName': 'chk002', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793570>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c232f982b0, name="chk003") at 0x000001C209434E08>': {'widgetName': 'chk003', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793770>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c232f98550, name="chk004") at 0x000001C209434CC8>': {'widgetName': 'chk004', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097938B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c232f99f90, name="chk005") at 0x000001C209434C08>': {'widgetName': 'chk005', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793CF0>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_mirror.Mirror(0x1c22d890010) at 0x000001C20942C8C8>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c232f9a230, name="s000") at 0x000001C209434A48>': {'widgetName': 's000', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793730>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c232f9a0e0, name="chk006") at 0x000001C209434AC8>': {'widgetName': 'chk006', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793C70>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f7c7f0, name="return_area") at 0x000001C209434388>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097937F0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c232f7c860, name="i025") at 0x000001C209434188>': {'widgetName': 'i025', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793C30>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22dece900, name="i007") at 0x000001C209450F08>': {'widgetName': 'i007', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793690>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'normals_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c21c57f270, name="QtUi") at 0x000001C209065EC8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['normals'], 2: ['normals_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c220bbcf50, name="mainWindow") at 0x000001C2090695C8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c220ba9090, name="i005") at 0x000001C209069648>': {'widgetName': 'i005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092D30>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22729f8c0, name="tb001") at 0x000001C2090690C8>': {'widgetName': 'tb001', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092D50>', 'method': '<bound method Normals.tb001 of <maya_normals.Normals(0x1c22873efb0) at 0x000001C2090BBF48>>', 'prefix': 'tb', 'docString': 'Harden Edge Normals\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272af700, name="b010") at 0x000001C209069688>': {'widgetName': 'b010', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092DB0>', 'method': '<bound method Normals.b010 of <maya_normals.Normals(0x1c22873efb0) at 0x000001C2090BBF48>>', 'prefix': 'b', 'docString': 'Reverse Normals\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272afe80, name="b006") at 0x000001C209069708>': {'widgetName': 'b006', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092D90>', 'method': '<bound method Normals.b006 of <maya_normals.Normals(0x1c22873efb0) at 0x000001C2090BBF48>>', 'prefix': 'b', 'docString': 'Set To Face\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22729e7b0, name="tb004") at 0x000001C209069308>': {'widgetName': 'tb004', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090929D0>', 'method': '<bound method Normals.tb004 of <maya_normals.Normals(0x1c22873efb0) at 0x000001C2090BBF48>>', 'prefix': 'tb', 'docString': 'Average Normals\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272af500, name="b001") at 0x000001C209069788>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092DD0>', 'method': '<bound method Normals.b001 of <maya_normals.Normals(0x1c22873efb0) at 0x000001C2090BBF48>>', 'prefix': 'b', 'docString': 'Soften Edge Normals\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QSpinBox(0x1c228d9c8b0, name="s002") at 0x000001C2090A3188>': {'widgetName': 's002', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092B10>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c228d9d870, name="chk001") at 0x000001C2090C9E88>': {'widgetName': 'chk001', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092EF0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c228d9d560, name="chk002") at 0x000001C2090C9D08>': {'widgetName': 'chk002', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092ED0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c228d9dbf0, name="chk000") at 0x000001C2090C9D88>': {'widgetName': 'chk000', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090927B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c228da09e0, name="chk003") at 0x000001C2090C9948>': {'widgetName': 'chk003', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092BD0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c228da3450, name="return_area") at 0x000001C2090C9108>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092E30>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22740fc80, name="i012") at 0x000001C2090BCF08>': {'widgetName': 'i012', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092E10>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'nurbs_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b1000, name="QtUi") at 0x000001C2090697C8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['nurbs'], 2: ['nurbs_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b07c0, name="mainWindow") at 0x000001C209069588>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b0e80, name="i011") at 0x000001C209069848>': {'widgetName': 'i011', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478EB0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b13c0, name="b042") at 0x000001C2090698C8>': {'widgetName': 'b042', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478DB0>', 'method': '<bound method Nurbs.b042 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Detach Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b18c0, name="b028") at 0x000001C209069948>': {'widgetName': 'b028', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478E90>', 'method': '<bound method Nurbs.b028 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Straighten Curve\n\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b15c0, name="b041") at 0x000001C2090699C8>': {'widgetName': 'b041', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478E70>', 'method': '<bound method Nurbs.b041 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Attach Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1b80, name="b032") at 0x000001C209069A48>': {'widgetName': 'b032', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478E50>', 'method': 'None', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b14c0, name="b014") at 0x000001C209069AC8>': {'widgetName': 'b014', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478E10>', 'method': '<bound method Nurbs.b014 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Duplicate Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b2140, name="b045") at 0x000001C209069B48>': {'widgetName': 'b045', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478EF0>', 'method': '<bound method Nurbs.b045 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Cut Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1c80, name="b012") at 0x000001C209069BC8>': {'widgetName': 'b012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478D90>', 'method': '<bound method Nurbs.b012 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Project Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1300, name="b016") at 0x000001C209069C48>': {'widgetName': 'b016', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478D70>', 'method': '<bound method Nurbs.b016 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Extract Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1380, name="b026") at 0x000001C209069CC8>': {'widgetName': 'b026', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478D50>', 'method': '<bound method Nurbs.b026 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Smooth Curve\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1500, name="b051") at 0x000001C209069D48>': {'widgetName': 'b051', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478D30>', 'method': '<bound method Nurbs.b051 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Reverse Curve\n\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1dc0, name="b034") at 0x000001C209069DC8>': {'widgetName': 'b034', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478D10>', 'method': 'None', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b1f00, name="b030") at 0x000001C209069E48>': {'widgetName': 'b030', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478CF0>', 'method': '<bound method Nurbs.b030 of <maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>>', 'prefix': 'b', 'docString': 'Extrude\n\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22af54900, name="return_area") at 0x000001C2097305C8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094784B0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'pivot_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b1080, name="QtUi") at 0x000001C209069EC8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['pivot'], 2: ['pivot_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b2dc0, name="mainWindow") at 0x000001C20906B1C8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b2600, name="i029") at 0x000001C20906B248>': {'widgetName': 'i029', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A84D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b2640, name="b000") at 0x000001C20906B2C8>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A84F0>', 'method': '<bound method Pivot.b000 of <maya_pivot.Pivot(0x1c22caaa5b0) at 0x000001C20977DA48>>', 'prefix': 'b', 'docString': 'Center Pivot: Object\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b2cc0, name="b004") at 0x000001C20906B308>': {'widgetName': 'b004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8550>', 'method': '<bound method Pivot.b004 of <maya_pivot.Pivot(0x1c22caaa5b0) at 0x000001C20977DA48>>', 'prefix': 'b', 'docString': 'Bake Pivot\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b25c0, name="b002") at 0x000001C20906B348>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8530>', 'method': '<bound method Pivot.b002 of <maya_pivot.Pivot(0x1c22caaa5b0) at 0x000001C20977DA48>>', 'prefix': 'b', 'docString': 'Center Pivot: World\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b2bc0, name="b001") at 0x000001C20906B388>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8590>', 'method': '<bound method Pivot.b001 of <maya_pivot.Pivot(0x1c22caaa5b0) at 0x000001C20977DA48>>', 'prefix': 'b', 'docString': 'Center Pivot: Component\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a2410, name="tb000") at 0x000001C209069F08>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A85B0>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_pivot.Pivot(0x1c22caaa5b0) at 0x000001C20977DA48>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a03d500, name="chk000") at 0x000001C209783F88>': {'widgetName': 'chk000', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8B30>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a03cd20, name="chk001") at 0x000001C209783D48>': {'widgetName': 'chk001', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8AD0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22a03efb0, name="return_area") at 0x000001C2097838C8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A89F0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22a0412b0, name="i008") at 0x000001C209442EC8>': {'widgetName': 'i008', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8650>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'polygons_component_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b1140, name="QtUi") at 0x000001C209069E88>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['polygons'], 2: ['polygons_component_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b5100, name="mainWindow") at 0x000001C20906BDC8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b49c0, name="b009") at 0x000001C20906BE48>': {'widgetName': 'b009', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146D10>', 'method': '<bound method Polygons.b009 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Collapse Component\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b47c0, name="b012") at 0x000001C20906BEC8>': {'widgetName': 'b012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146CF0>', 'method': '<bound method Polygons.b012 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Multi-Cut Tool\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a3910, name="tb003") at 0x000001C20906B3C8>': {'widgetName': 'tb003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091468F0>', 'method': '<bound method Init.attr.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b5d80, name="b032") at 0x000001C20906BF08>': {'widgetName': 'b032', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091468D0>', 'method': '<bound method Polygons.b032 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Poke\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b5e00, name="b046") at 0x000001C20906BF48>': {'widgetName': 'b046', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146930>', 'method': '<bound method Polygons.b046 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Split\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a44e0, name="tb005") at 0x000001C20906B608>': {'widgetName': 'tb005', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146950>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b52c0, name="b000") at 0x000001C20906C048>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146970>', 'method': '<bound method Init.attr.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b5340, name="b022") at 0x000001C20906C088>': {'widgetName': 'b022', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146990>', 'method': '<bound method Polygons.b022 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Attach\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b5500, name="i011") at 0x000001C20906C108>': {'widgetName': 'i011', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091469B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a6700, name="tb004") at 0x000001C20906B888>': {'widgetName': 'tb004', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091469D0>', 'method': '<bound method Init.attr.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b6c80, name="b003") at 0x000001C20906C148>': {'widgetName': 'b003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091469F0>', 'method': '<bound method Polygons.b003 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Symmetrize\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a5f90, name="tb001") at 0x000001C20906BB08>': {'widgetName': 'tb001', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146A10>', 'method': '<bound method Init.attr.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c227c22080, name="chk002") at 0x000001C20907A208>': {'widgetName': 'chk002', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146EF0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QSpinBox(0x1c227c23740, name="s004") at 0x000001C20907A908>': {'widgetName': 's004', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146E10>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c227c25500, name="chk014") at 0x000001C20907A9C8>': {'widgetName': 'chk014', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146D90>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c227c255e0, name="chk015") at 0x000001C20907AA88>': {'widgetName': 'chk015', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146D50>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c227c29be0, name="s000") at 0x000001C20907AC88>': {'widgetName': 's000', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146C50>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QSpinBox(0x1c227c2ba10, name="s003") at 0x000001C20907AD48>': {'widgetName': 's003', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146BF0>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2273f17c0, name="return_area") at 0x000001C209073A08>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146F10>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2273f35f0, name="i010") at 0x000001C20907FFC8>': {'widgetName': 'i010', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146F70>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'polygons_edge_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b1100, name="QtUi") at 0x000001C20906BD88>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['polygons'], 2: ['polygons_edge_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b0640, name="mainWindow") at 0x000001C20906C188>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b0200, name="b047") at 0x000001C20906C1C8>': {'widgetName': 'b047', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146350>', 'method': '<bound method Polygons.b047 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Insert Edgeloop\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b3dc0, name="i002") at 0x000001C20906C288>': {'widgetName': 'i002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146390>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b3f40, name="i026") at 0x000001C20906C2C8>': {'widgetName': 'i026', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146370>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e41a80, name="return_area") at 0x000001C209156F48>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091462D0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e44b10, name="i010") at 0x000001C20916AF48>': {'widgetName': 'i010', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146470>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'polygons_face_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b0400, name="QtUi") at 0x000001C20906B288>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['polygons'], 2: ['polygons_face_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b3c80, name="mainWindow") at 0x000001C20906C588>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b3f80, name="b034") at 0x000001C20906C608>': {'widgetName': 'b034', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927AA30>', 'method': '<bound method Polygons.b034 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Wedge\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b3500, name="i003") at 0x000001C20906C648>': {'widgetName': 'i003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927AA10>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a7650, name="tb006") at 0x000001C20906C308>': {'widgetName': 'tb006', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927A9F0>', 'method': '<bound method Init.attr.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c227273da0, name="s001") at 0x000001C208FA7F08>': {'widgetName': 's001', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927AB10>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c26bef70e0, name="return_area") at 0x000001C20914F0C8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927AA70>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e3fa90, name="i010") at 0x000001C209149FC8>': {'widgetName': 'i010', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091462F0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'polygons_mesh_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b10c0, name="QtUi") at 0x000001C20906C548>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['polygons'], 2: ['polygons_mesh_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b8380, name="mainWindow") at 0x000001C20906C948>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b8d80, name="b001") at 0x000001C20906C9C8>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146E70>', 'method': '<bound method Polygons.b001 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Fill Holes\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272a99c0, name="tb002") at 0x000001C20906C6C8>': {'widgetName': 'tb002', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146E90>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b83c0, name="b002") at 0x000001C20906CA08>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146EB0>', 'method': '<bound method Polygons.b002 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Separate\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b8cc0, name="i004") at 0x000001C20906CA48>': {'widgetName': 'i004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146ED0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c2273f9b00, name="chk000") at 0x000001C209087EC8>': {'widgetName': 'chk000', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146F50>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2273fb5b0, name="return_area") at 0x000001C209087D88>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092070>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2273fce30, name="i010") at 0x000001C209086F48>': {'widgetName': 'i010', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092430>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'polygons_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b0b40, name="QtUi") at 0x000001C20906C908>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['polygons'], 2: ['polygons_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b0d40, name="mainWindow") at 0x000001C20906C688>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b0f80, name="i010") at 0x000001C20906CAC8>': {'widgetName': 'i010', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5190>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b9cc0, name="i004") at 0x000001C20906CB48>': {'widgetName': 'i004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA51B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b99c0, name="i000") at 0x000001C20906CB88>': {'widgetName': 'i000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5290>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b9c40, name="i002") at 0x000001C20906CBC8>': {'widgetName': 'i002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA5270>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b9d80, name="i003") at 0x000001C20906CC08>': {'widgetName': 'i003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C208FA52D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b9f80, name="i011") at 0x000001C20906CC48>': {'widgetName': 'i011', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927A810>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227635580, name="return_area") at 0x000001C208FF8148>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C20927A910>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'polygons_vertex_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b0380, name="QtUi") at 0x000001C20906CA88>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['polygons'], 2: ['polygons_vertex_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b9c00, name="mainWindow") at 0x000001C20906CF08>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272aaf30, name="tb000") at 0x000001C20906CC88>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091466D0>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272ba440, name="i000") at 0x000001C20906CF88>': {'widgetName': 'i000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091466B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272ba1c0, name="b043") at 0x000001C20906CFC8>': {'widgetName': 'b043', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146690>', 'method': '<bound method Polygons.b043 of <maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>>', 'prefix': 'b', 'docString': 'Target Weld\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c220e5a7c0, name="s002") at 0x000001C209072D88>': {'widgetName': 's002', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2091467D0>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c220e5dd20, name="return_area") at 0x000001C209072388>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146910>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227c1d8c0, name="i010") at 0x000001C20907AE88>': {'widgetName': 'i010', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146C70>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'preferences_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b0500, name="QtUi") at 0x000001C20906CEC8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['preferences'], 2: ['preferences_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b3280, name="mainWindow") at 0x000001C20906F088>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272b3300, name="i022") at 0x000001C20906F0C8>': {'widgetName': 'i022', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478FD0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b5fad80, name="return_area") at 0x000001C209741708>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478B10>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b5fc130, name="i003") at 0x000001C20973B208>': {'widgetName': 'i003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478070>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'rendering_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b3380, name="QtUi") at 0x000001C20906CB08>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['rendering'], 2: ['rendering_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b3940, name="mainWindow") at 0x000001C20906F048>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bb300, name="i015") at 0x000001C20906F1C8>': {'widgetName': 'i015', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4D30>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bb780, name="b002") at 0x000001C20906F248>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4EF0>', 'method': '<bound method Rendering.b002 of <maya_rendering.Rendering(0x1c22b6546b0) at 0x000001C2097349C8>>', 'prefix': 'b', 'docString': 'Redo Previous Render\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bbac0, name="b000") at 0x000001C20906F288>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4450>', 'method': '<bound method Rendering.b000 of <maya_rendering.Rendering(0x1c22b6546b0) at 0x000001C2097349C8>>', 'prefix': 'b', 'docString': 'Render Current Frame\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b613eb0, name="return_area") at 0x000001C209734888>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478770>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'rigging_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b3900, name="QtUi") at 0x000001C20906F2C8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['rigging'], 2: ['rigging_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272bb400, name="mainWindow") at 0x000001C20906FD08>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bb240, name="i016") at 0x000001C20906FD88>': {'widgetName': 'i016', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4250>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bb440, name="b001") at 0x000001C20906FDC8>': {'widgetName': 'b001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4410>', 'method': '<bound method Rigging.b001 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'b', 'docString': 'Connect Joints\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bb740, name="b004") at 0x000001C20906FE08>': {'widgetName': 'b004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4290>', 'method': '<bound method Rigging.b004 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'b', 'docString': 'Reroot\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2272ac200, name="tb002") at 0x000001C20906F308>': {'widgetName': 'tb002', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4650>', 'method': '<bound method Rigging.tb002 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'tb', 'docString': 'Constraint: Parent\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227323230, name="tb001") at 0x000001C20906F548>': {'widgetName': 'tb001', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B45D0>', 'method': '<bound method Rigging.tb001 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'tb', 'docString': 'Orient Joints\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bd280, name="b002") at 0x000001C20906FE48>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4A10>', 'method': '<bound method Rigging.b002 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'b', 'docString': 'Insert Joint Tool\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bdd40, name="b008") at 0x000001C20906FE88>': {'widgetName': 'b008', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4A70>', 'method': '<bound method Rigging.b008 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'b', 'docString': 'Constraint: Orient\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bd700, name="b009") at 0x000001C20906FEC8>': {'widgetName': 'b009', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4270>', 'method': '<bound method Rigging.b009 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'b', 'docString': 'Constraint: Aim\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227323c40, name="tb003") at 0x000001C20906F7C8>': {'widgetName': 'tb003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4510>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227324570, name="tb004") at 0x000001C20906FA48>': {'widgetName': 'tb004', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4DB0>', 'method': '<bound method Rigging.tb004 of <maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>>', 'prefix': 'tb', 'docString': 'Lock/Unlock Attributes\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c2210f9e20, name="chk004") at 0x000001C20977E448>': {'widgetName': 'chk004', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094786F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c2210fbb70, name="chk003") at 0x000001C209791108>': {'widgetName': 'chk003', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094786B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QLineEdit(0x1c2210fdee0, name="t000") at 0x000001C2097911C8>': {'widgetName': 't000', 'widgetType': 'QLineEdit', 'derivedType': 'QLineEdit', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478550>', 'method': 'None', 'prefix': 't', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c2210ff060, name="chk005") at 0x000001C209791388>': {'widgetName': 'chk005', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478910>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QLineEdit(0x1c2210ff1b0, name="t001") at 0x000001C209791448>': {'widgetName': 't001', 'widgetType': 'QLineEdit', 'derivedType': 'QLineEdit', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4430>', 'method': 'None', 'prefix': 't', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c2210ffc30, name="s001") at 0x000001C209791688>': {'widgetName': 's001', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8030>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c2211003a0, name="chk006") at 0x000001C209791408>': {'widgetName': 'chk006', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8090>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221101980, name="chk010") at 0x000001C2097915C8>': {'widgetName': 'chk010', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094789B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c2211004f0, name="chk011") at 0x000001C2097917C8>': {'widgetName': 'chk011', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A80B0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221102550, name="chk007") at 0x000001C209791908>': {'widgetName': 'chk007', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A80D0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221102fd0, name="chk008") at 0x000001C209791888>': {'widgetName': 'chk008', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A80F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221102f60, name="chk009") at 0x000001C2097916C8>': {'widgetName': 'chk009', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8110>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221102940, name="chk015") at 0x000001C209791988>': {'widgetName': 'chk015', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8130>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221104310, name="chk012") at 0x000001C209787608>': {'widgetName': 'chk012', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8190>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c221105e30, name="chk013") at 0x000001C209787308>': {'widgetName': 'chk013', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8210>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22b6140e0, name="chk014") at 0x000001C209787248>': {'widgetName': 'chk014', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8230>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22945cfd0, name="return_area") at 0x000001C209750788>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A82F0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22945ed90, name="i013") at 0x000001C209787A08>': {'widgetName': 'i013', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8F70>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'scene_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b34c0, name="QtUi") at 0x000001C20906FF08>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['scene'], 2: ['scene_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272b9b40, name="mainWindow") at 0x000001C20906FCC8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bf480, name="i017") at 0x000001C20906FF88>': {'widgetName': 'i017', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478390>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bfec0, name="i032") at 0x000001C20906E048>': {'widgetName': 'i032', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094783B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bfe40, name="i003") at 0x000001C20906E088>': {'widgetName': 'i003', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478CB0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bfac0, name="i022") at 0x000001C20906E0C8>': {'widgetName': 'i022', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478CD0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bfb00, name="i023") at 0x000001C20906E108>': {'widgetName': 'i023', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478C70>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bf6c0, name="i020") at 0x000001C20906E188>': {'widgetName': 'i020', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478C50>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22af59d00, name="return_area") at 0x000001C20973BEC8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094781F0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'scripting_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272b9b80, name="QtUi") at 0x000001C20906FF48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['scripting'], 2: ['scripting_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272ba780, name="mainWindow") at 0x000001C20906E1C8>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bac80, name="i023") at 0x000001C20906E208>': {'widgetName': 'i023', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4970>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b60db60, name="return_area") at 0x000001C209734E88>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4D50>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b60fca0, name="i003") at 0x000001C20973D208>': {'widgetName': 'i003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2094784F0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'selection_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272baa80, name="QtUi") at 0x000001C20906FD48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['selection'], 2: ['selection_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272c01c0, name="mainWindow") at 0x000001C20906EA08>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c0c80, name="i009") at 0x000001C20906EA88>': {'widgetName': 'i009', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090924D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c0340, name="i021") at 0x000001C20906EAC8>': {'widgetName': 'i021', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209146A90>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c0880, name="chk006") at 0x000001C20906EB48>': {'widgetName': 'chk006', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090924B0>', 'method': '<bound method Selection.chk006 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'Select Style: Lasso\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227326f00, name="tb000") at 0x000001C20906E288>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092090>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227325b50, name="tb001") at 0x000001C20906E4C8>': {'widgetName': 'tb001', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092030>', 'method': '<bound method Selection.tb001 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'tb', 'docString': 'Select Similar\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c227328160, name="tb002") at 0x000001C20906E748>': {'widgetName': 'tb002', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090920D0>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c2440, name="chk005") at 0x000001C20906EBC8>': {'widgetName': 'chk005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090920F0>', 'method': '<bound method Selection.chk005 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'Select Style: Marquee\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c2640, name="chk007") at 0x000001C20906EC08>': {'widgetName': 'chk007', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092110>', 'method': '<bound method Selection.chk007 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'Select Style: Paint\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c2b80, name="chk004") at 0x000001C20906EC88>': {'widgetName': 'chk004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092130>', 'method': '<bound method Slots.hideMain.<locals>.wrapper of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QLabel(0x1c2272c25c0, name="lbl003") at 0x000001C20906ED08>': {'widgetName': 'lbl003', 'widgetType': 'QLabel', 'derivedType': 'QLabel', 'signalInstance': 'None', 'method': '<bound method Selection.lbl003 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'lbl', 'docString': 'Grow Selection\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QLabel(0x1c2272c2940, name="lbl004") at 0x000001C20906ED88>': {'widgetName': 'lbl004', 'widgetType': 'QLabel', 'derivedType': 'QLabel', 'signalInstance': 'None', 'method': '<bound method Selection.lbl004 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'lbl', 'docString': 'Shrink Selection\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c3040, name="chk008") at 0x000001C20906EE08>': {'widgetName': 'chk008', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092150>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QRadioButton(0x1c2274040d0, name="chk000") at 0x000001C209070A08>': {'widgetName': 'chk000', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092890>', 'method': '<bound method Selection.chk000 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'Select Nth: uncheck other checkboxes\n\t\t', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c227405090, name="chk001") at 0x000001C209070108>': {'widgetName': 'chk001', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092870>', 'method': '<bound method Selection.chk001 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'Select Nth: uncheck other checkboxes\n\t\t', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c227403c00, name="chk009") at 0x000001C20909F5C8>': {'widgetName': 'chk009', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092850>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c227404990, name="chk002") at 0x000001C20909F488>': {'widgetName': 'chk002', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092830>', 'method': '<bound method Selection.chk002 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 'chk', 'docString': 'Select Nth: uncheck other checkboxes\n\t\t', 'tracked': False}, '<PySide2.QtWidgets.QRadioButton(0x1c2274055d0, name="chk010") at 0x000001C20909F388>': {'widgetName': 'chk010', 'widgetType': 'QRadioButton', 'derivedType': 'QRadioButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092810>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QSpinBox(0x1c227406910, name="s003") at 0x000001C20909F248>': {'widgetName': 's003', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092610>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c227408040, name="s000") at 0x000001C20907C0C8>': {'widgetName': 's000', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092930>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c22740ba00, name="chk003") at 0x000001C2090A2048>': {'widgetName': 'chk003', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090924F0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22740b5a0, name="s002") at 0x000001C2090A2188>': {'widgetName': 's002', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090923F0>', 'method': '<bound method Selection.s002 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 's', 'docString': 'Select Island: tolerance x\n\t\t', 'tracked': False}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22740a5e0, name="s004") at 0x000001C2090A22C8>': {'widgetName': 's004', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092370>', 'method': '<bound method Selection.s004 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 's', 'docString': 'Select Island: tolerance y\n\t\t', 'tracked': False}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22740cfe0, name="s005") at 0x000001C2090A2308>': {'widgetName': 's005', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090922F0>', 'method': '<bound method Selection.s005 of <maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>>', 'prefix': 's', 'docString': 'Select Island: tolerance z\n\t\t', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22784aaa0, name="return_area") at 0x000001C20909A948>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090921D0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'subdivision_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272ba8c0, name="QtUi") at 0x000001C20906E9C8>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['subdivision'], 2: ['subdivision_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272bc0c0, name="mainWindow") at 0x000001C20906E248>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bbc40, name="i004") at 0x000001C20906EEC8>': {'widgetName': 'i004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097934D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c0ac0, name="b004") at 0x000001C20906EF48>': {'widgetName': 'b004', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097938F0>', 'method': 'None', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c05c0, name="b009") at 0x000001C20906EF88>': {'widgetName': 'b009', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097935B0>', 'method': '<bound method Subdivision.b009 of <maya_subdivision.Subdivision(0x1c22d8922d0) at 0x000001C209439708>>', 'prefix': 'b', 'docString': 'Smooth\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c0bc0, name="b008") at 0x000001C20906EFC8>': {'widgetName': 'b008', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097934F0>', 'method': '<bound method Subdivision.b008 of <maya_subdivision.Subdivision(0x1c22d8922d0) at 0x000001C209439708>>', 'prefix': 'b', 'docString': 'Add Divisions - Subdivide Mesh\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c36c0, name="b005") at 0x000001C209270048>': {'widgetName': 'b005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793610>', 'method': '<bound method Subdivision.b005 of <maya_subdivision.Subdivision(0x1c22d8922d0) at 0x000001C209439708>>', 'prefix': 'b', 'docString': 'Reduce\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22ded6f50, name="return_area") at 0x000001C209489D88>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793CD0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22ded9db0, name="i007") at 0x000001C209439608>': {'widgetName': 'i007', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097936B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22dedad00, name="i007") at 0x000001C209481FC8>': {'widgetName': 'i007', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209793630>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'symmetry_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bbec0, name="QtUi") at 0x000001C20906EE88>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['symmetry'], 2: ['symmetry_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272bc000, name="mainWindow") at 0x000001C209270088>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272bc040, name="i021") at 0x000001C2092700C8>': {'widgetName': 'i021', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092690>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c3ac0, name="chk000") at 0x000001C209270148>': {'widgetName': 'chk000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092C10>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_symmetry.Symmetry(0x1c228738ad0) at 0x000001C20907CD88>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c3fc0, name="chk001") at 0x000001C2092701C8>': {'widgetName': 'chk001', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092EB0>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_symmetry.Symmetry(0x1c228738ad0) at 0x000001C20907CD88>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c3600, name="chk002") at 0x000001C209270248>': {'widgetName': 'chk002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092790>', 'method': '<bound method Slots.sync.<locals>.wrapper of <maya_symmetry.Symmetry(0x1c228738ad0) at 0x000001C20907CD88>>', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c228d8c9a0, name="return_area") at 0x000001C20908BB08>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092A50>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c228d8e5a0, name="i009") at 0x000001C2090A3F08>': {'widgetName': 'i009', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092750>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'transform_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bb1c0, name="QtUi") at 0x000001C20906EE48>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['transform'], 2: ['transform_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272c5040, name="mainWindow") at 0x000001C209270788>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c43c0, name="i029") at 0x000001C209270808>': {'widgetName': 'i029', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A82D0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c4540, name="i008") at 0x000001C209270848>': {'widgetName': 'i008', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A82B0>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22732bb90, name="tb000") at 0x000001C20906EF08>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8350>', 'method': '<bound method Transform.tb000 of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'tb', 'docString': 'Drop To Grid\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c5900, name="chk012") at 0x000001C209270888>': {'widgetName': 'chk012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8330>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c5c00, name="b012") at 0x000001C209270908>': {'widgetName': 'b012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8390>', 'method': '<bound method Transform.b012 of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'b', 'docString': 'Make Live (Toggle)\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c5780, name="b002") at 0x000001C209270948>': {'widgetName': 'b002', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A83B0>', 'method': '<bound method Transform.b002 of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'b', 'docString': 'Freeze Transformations\n\t\t', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22732bf10, name="tb001") at 0x000001C2092704C8>': {'widgetName': 'tb001', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A83F0>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'tb', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6b80, name="chk013") at 0x000001C209270988>': {'widgetName': 'chk013', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8410>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6ac0, name="chk014") at 0x000001C209270A08>': {'widgetName': 'chk014', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8430>', 'method': '<bound method Transform.chk014 of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'chk', 'docString': 'Snap: Toggle Rotation\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6b00, name="b000") at 0x000001C209270A88>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8450>', 'method': '<bound method Slots.message.<locals>.wrapper of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QComboBox(0x1c22a024a60, name="cmb004") at 0x000001C20977E888>': {'widgetName': 'cmb004', 'widgetType': 'QComboBox', 'derivedType': 'QComboBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8F30>', 'method': 'None', 'prefix': 'cmb', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QCheckBox(0x1c22a0279a0, name="chk014") at 0x000001C20979CF08>': {'widgetName': 'chk014', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8F50>', 'method': '<bound method Transform.chk014 of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'chk', 'docString': 'Snap: Toggle Rotation\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a0281f0, name="chk016") at 0x000001C20979CDC8>': {'widgetName': 'chk016', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8DD0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a0288f0, name="chk017") at 0x000001C20979CCC8>': {'widgetName': 'chk017', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8D90>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02c010, name="chk029") at 0x000001C20979CA48>': {'widgetName': 'chk029', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8D70>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02a9c0, name="chk030") at 0x000001C20979CA08>': {'widgetName': 'chk030', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8D10>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02bf30, name="chk031") at 0x000001C20979C908>': {'widgetName': 'chk031', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8CD0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02b9f0, name="chk013") at 0x000001C20979C808>': {'widgetName': 'chk013', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8C90>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02ca90, name="chk007") at 0x000001C20979C788>': {'widgetName': 'chk007', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8C70>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02d3c0, name="chk006") at 0x000001C20979C848>': {'widgetName': 'chk006', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8D30>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02cb00, name="chk010") at 0x000001C20979C648>': {'widgetName': 'chk010', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8C30>', 'method': '<bound method Transform.chk010 of <maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>>', 'prefix': 'chk', 'docString': 'Align Vertices: Auto Align\n\t\t', 'tracked': True}, '<PySide2.QtWidgets.QCheckBox(0x1c22a02e0e0, name="chk011") at 0x000001C20979C5C8>': {'widgetName': 'chk011', 'widgetType': 'QCheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8BF0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22a0305a0, name="return_area") at 0x000001C209796108>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2097A8B10>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'utilities_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bc080, name="QtUi") at 0x000001C209270748>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['utilities'], 2: ['utilities_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272bfd40, name="mainWindow") at 0x000001C209270208>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c3380, name="i020") at 0x000001C209270B08>': {'widgetName': 'i020', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478C30>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b5f5130, name="return_area") at 0x000001C209741EC8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478F90>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22b5f6710, name="i003") at 0x000001C209740208>': {'widgetName': 'i003', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478B70>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'uv_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272c00c0, name="QtUi") at 0x000001C209270B88>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['uv'], 2: ['uv_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272c6dc0, name="mainWindow") at 0x000001C209270E48>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6880, name="i018") at 0x000001C209270EC8>': {'widgetName': 'i018', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092970>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6c40, name="b018") at 0x000001C209270F08>': {'widgetName': 'b018', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4090>', 'method': 'None', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6e00, name="b005") at 0x000001C209270F88>': {'widgetName': 'b005', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4110>', 'method': '<bound method Uv.b005 of <maya_uv.Uv(0x1c22b1e2450) at 0x000001C2090C74C8>>', 'prefix': 'b', 'docString': "Cut Uv'S\n\t\t", 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6e80, name="b000") at 0x000001C209270FC8>': {'widgetName': 'b000', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4150>', 'method': 'None', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6400, name="b012") at 0x000001C209273048>': {'widgetName': 'b012', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4170>', 'method': 'None', 'prefix': 'b', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c6600, name="b011") at 0x000001C209273088>': {'widgetName': 'b011', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4190>', 'method': '<bound method Uv.b011 of <maya_uv.Uv(0x1c22b1e2450) at 0x000001C2090C74C8>>', 'prefix': 'b', 'docString': "Sew Uv'S\n\t\t", 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22732cb50, name="tb000") at 0x000001C209270BC8>': {'widgetName': 'tb000', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B41B0>', 'method': '<bound method Uv.tb000 of <maya_uv.Uv(0x1c22b1e2450) at 0x000001C2090C74C8>>', 'prefix': 'tb', 'docString': "Pack UV's\n\n\t\tpm.u3dLayout:\n\t\t\tlayoutScaleMode (int),\n\t\t\tmultiObject (bool),\n\t\t\tmutations (int),\n\t\t\tpackBox (float, float, float, float),\n\t\t\tpreRotateMode (int),\n\t\t\tpreScaleMode (int),\n\t\t\tresolution (int),\n\t\t\trotateMax (float),\n\t\t\trotateMin (float),\n\t\t\trotateStep (float),\n\t\t\tshellSpacing (float),\n\t\t\ttileAssignMode (int),\n\t\t\ttileMargin (float),\n\t\t\ttileU (int),\n\t\t\ttileV (int),\n\t\t\ttranslate (bool)\n\t\t", 'tracked': True}, '<tentacle.ui.widgets.checkBox.CheckBox(0x1c22af3eb00, name="chk025") at 0x000001C2090D6EC8>': {'widgetName': 'chk025', 'widgetType': 'CheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4AF0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.checkBox.CheckBox(0x1c22af40e00, name="chk007") at 0x000001C2090D6CC8>': {'widgetName': 'chk007', 'widgetType': 'CheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4AD0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22af40a80, name="s007") at 0x000001C2090D6C48>': {'widgetName': 's007', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B48F0>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.checkBox.CheckBox(0x1c22af421b0, name="chk026") at 0x000001C2090D6A88>': {'widgetName': 'chk026', 'widgetType': 'CheckBox', 'derivedType': 'QCheckBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4AB0>', 'method': 'None', 'prefix': 'chk', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QDoubleSpinBox(0x1c22af43250, name="s006") at 0x000001C2090D69C8>': {'widgetName': 's006', 'widgetType': 'QDoubleSpinBox', 'derivedType': 'QDoubleSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4830>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QSpinBox(0x1c22af42ae0, name="s004") at 0x000001C2090D6888>': {'widgetName': 's004', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209092990>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<PySide2.QtWidgets.QSpinBox(0x1c22af444b0, name="s005") at 0x000001C2090D6808>': {'widgetName': 's005', 'widgetType': 'QSpinBox', 'derivedType': 'QSpinBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4790>', 'method': 'None', 'prefix': 's', 'docString': 'None', 'tracked': False}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22af45a90, name="return_area") at 0x000001C2090D56C8>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B46D0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c22af47930, name="i012") at 0x000001C2090DF188>': {'widgetName': 'i012', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B4B90>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'vfx_submenu': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bfa00, name="QtUi") at 0x000001C209270E08>', 'uiLevel': {'base': 2, 0: [], 1: [], 3: ['vfx'], 2: ['vfx_submenu'], 4: []}, 'state': 1, 'widgets': {'<PySide2.QtWidgets.QWidget(0x1c2272bf280, name="mainWindow") at 0x000001C209273108>': {'widgetName': 'mainWindow', 'widgetType': 'QWidget', 'derivedType': 'QWidget', 'signalInstance': 'None', 'method': 'None', 'prefix': 'mainWindow', 'docString': 'None', 'tracked': True}, '<PySide2.QtWidgets.QPushButton(0x1c2272c4900, name="i024") at 0x000001C209273188>': {'widgetName': 'i024', 'widgetType': 'QPushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478930>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2210f2b10, name="return_area") at 0x000001C20977EF08>': {'widgetName': 'return_area', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C2090B41F0>', 'method': 'None', 'prefix': 'return_area', 'docString': 'None', 'tracked': True}, '<tentacle.ui.widgets.pushButton.PushButton(0x1c2210f4f60, name="i013") at 0x000001C209769AC8>': {'widgetName': 'i013', 'widgetType': 'PushButton', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x000001C209478710>', 'method': 'None', 'prefix': 'i', 'docString': 'None', 'tracked': True}}, 'size': [600, 400]}, 'animation': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bf540, name="QtUi") at 0x000001C209273848>', 'uiLevel': {'base': 3, 2: ['animation_submenu'], 0: [], 1: [], 3: ['animation']}, 'state': 0, 'class': '<maya_animation.Animation(0x1c22b654e90) at 0x000001C20976FD08>'}, 'convert': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bf3c0, name="QtUi") at 0x000001C209274208>', 'uiLevel': {'base': 3, 2: ['convert_submenu'], 0: [], 1: [], 3: ['convert']}, 'state': 0, 'class': '<maya_convert.Convert(0x1c22d88de30) at 0x000001C2094263C8>'}, 'crease': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272c3c40, name="QtUi") at 0x000001C2092746C8>', 'uiLevel': {'base': 3, 2: ['crease_submenu'], 0: [], 1: [], 3: ['crease']}, 'state': 0, 'class': '<maya_crease.Crease(0x1c2277349f0) at 0x000001C209166048>'}, 'create': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272c3f40, name="QtUi") at 0x000001C209274D48>', 'uiLevel': {'base': 3, 2: ['create_submenu'], 0: [], 1: [], 3: ['create']}, 'state': 0, 'class': '<maya_create.Create(0x1c22d88a5f0) at 0x000001C20944F8C8>'}, 'deformation': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2272bf340, name="QtUi") at 0x000001C209276408>', 'uiLevel': {'base': 3, 2: ['deformation_submenu'], 0: [], 1: [], 3: ['deformation']}, 'state': 0}, 'display': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6a80, name="QtUi") at 0x000001C2092767C8>', 'uiLevel': {'base': 3, 2: ['display_submenu'], 0: [], 1: [], 3: ['display']}, 'state': 0, 'class': '<maya_display.Display(0x1c22b1ec330) at 0x000001C209737748>'}, 'duplicate': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6b00, name="QtUi") at 0x000001C209276F88>', 'uiLevel': {'base': 3, 2: ['duplicate_submenu'], 0: [], 1: [], 3: ['duplicate']}, 'state': 0, 'class': '<maya_duplicate.Duplicate(0x1c22d88df50) at 0x000001C2094361C8>'}, 'dynLayout': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6f80, name="QtUi") at 0x000001C20927C788>', 'uiLevel': {'base': 3}, 'state': 0}, 'edit': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6580, name="QtUi") at 0x000001C20927CB48>', 'uiLevel': {'base': 3, 2: ['edit_submenu'], 0: [], 1: [], 3: ['edit']}, 'state': 0, 'class': '<maya_edit.Edit(0x1c22caacbf0) at 0x000001C209783088>'}, 'file': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6cc0, name="QtUi") at 0x000001C209277D48>', 'uiLevel': {'base': 3, 2: ['file_submenu'], 0: [], 1: [], 3: ['file']}, 'state': 0, 'class': '<maya_file.File(0x1c22b1ed7f0) at 0x000001C209748548>'}, 'lighting': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6600, name="QtUi") at 0x000001C209279688>', 'uiLevel': {'base': 3, 2: ['lighting_submenu'], 0: [], 1: [], 3: ['lighting']}, 'state': 0, 'class': '<maya_lighting.Lighting(0x1c22b1e25b0) at 0x000001C2090CB708>'}, 'main_lower': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2278bbd40, name="QtUi") at 0x000001C209297E08>', 'uiLevel': {'base': 4}, 'state': 0}, 'materials': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6d80, name="QtUi") at 0x000001C209279B88>', 'uiLevel': {'base': 3, 2: ['materials_submenu'], 0: [], 1: [], 3: ['materials']}, 'state': 0, 'class': '<maya_materials.Materials(0x1c22873a010) at 0x000001C2090B38C8>'}, 'mirror': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6780, name="QtUi") at 0x000001C20927E508>', 'uiLevel': {'base': 3, 2: ['mirror_submenu'], 0: [], 1: [], 3: ['mirror']}, 'state': 0, 'class': '<maya_mirror.Mirror(0x1c22d890010) at 0x000001C20942C8C8>'}, 'normals': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c6fc0, name="QtUi") at 0x000001C20927EA48>', 'uiLevel': {'base': 3, 2: ['normals_submenu'], 0: [], 1: [], 3: ['normals']}, 'state': 0, 'class': '<maya_normals.Normals(0x1c22873efb0) at 0x000001C2090BBF48>'}, 'nurbs': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273c7980, name="QtUi") at 0x000001C20927DF08>', 'uiLevel': {'base': 3, 2: ['nurbs_submenu'], 0: [], 1: [], 3: ['nurbs']}, 'state': 0, 'class': '<maya_nurbs.Nurbs(0x1c22b1e4c70) at 0x000001C2090E08C8>'}, 'pivot': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2273d6c40, name="QtUi") at 0x000001C209281688>', 'uiLevel': {'base': 3, 2: ['pivot_submenu'], 0: [], 1: [], 3: ['pivot']}, 'state': 0, 'class': '<maya_pivot.Pivot(0x1c22caaa5b0) at 0x000001C20977DA48>'}, 'polygons': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275ca2a0, name="QtUi") at 0x000001C209282C08>', 'uiLevel': {'base': 3, 2: ['polygons_submenu'], 0: [], 1: [], 3: ['polygons']}, 'state': 0, 'class': '<maya_polygons.Polygons(0x1c22782d5f0) at 0x000001C208FF8108>'}, 'polygons_component': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275ca460, name="QtUi") at 0x000001C209285848>', 'uiLevel': {'base': 3, 2: ['polygons_component_submenu']}, 'state': 0}, 'polygons_edge': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275ca260, name="QtUi") at 0x000001C209286FC8>', 'uiLevel': {'base': 3, 2: ['polygons_edge_submenu']}, 'state': 0}, 'polygons_face': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275caa60, name="QtUi") at 0x000001C209284548>', 'uiLevel': {'base': 3, 2: ['polygons_face_submenu']}, 'state': 0}, 'polygons_mesh': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275ca7a0, name="QtUi") at 0x000001C209284F48>', 'uiLevel': {'base': 3, 2: ['polygons_mesh_submenu']}, 'state': 0}, 'polygons_vertex': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275cac60, name="QtUi") at 0x000001C20928A888>', 'uiLevel': {'base': 3, 2: ['polygons_vertex_submenu']}, 'state': 0}, 'preferences': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275cace0, name="QtUi") at 0x000001C20928B248>', 'uiLevel': {'base': 3, 2: ['preferences_submenu'], 0: [], 1: [], 3: ['preferences']}, 'state': 0, 'class': '<maya_preferences.Preferences(0x1c22b1ea9f0) at 0x000001C209741648>'}, 'rendering': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275caaa0, name="QtUi") at 0x000001C20928BB08>', 'uiLevel': {'base': 3, 2: ['rendering_submenu'], 0: [], 1: [], 3: ['rendering']}, 'state': 0, 'class': '<maya_rendering.Rendering(0x1c22b6546b0) at 0x000001C2097349C8>'}, 'rigging': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275cab60, name="QtUi") at 0x000001C20928BD48>', 'uiLevel': {'base': 3, 2: ['rigging_submenu'], 0: [], 1: [], 3: ['rigging']}, 'state': 0, 'class': '<maya_rigging.Rigging(0x1c22b65a370) at 0x000001C2090CCAC8>'}, 'scene': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227706db0, name="QtUi") at 0x000001C20928D988>', 'uiLevel': {'base': 3, 2: ['scene_submenu'], 0: [], 1: [], 3: ['scene']}, 'state': 0, 'class': '<maya_scene.Scene(0x1c22b1e7090) at 0x000001C2090DEC08>'}, 'scripting': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227706d30, name="QtUi") at 0x000001C20928DDC8>', 'uiLevel': {'base': 3, 2: ['scripting_submenu'], 0: [], 1: [], 3: ['scripting']}, 'state': 0, 'class': '<maya_scripting.Scripting(0x1c22b6546d0) at 0x000001C20973DCC8>'}, 'selection': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227706770, name="QtUi") at 0x000001C20928F848>', 'uiLevel': {'base': 3, 2: ['selection_submenu'], 0: [], 1: [], 3: ['selection']}, 'state': 0, 'class': '<maya_selection.Selection(0x1c2287384f0) at 0x000001C209087048>'}, 'subdivision': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227706c30, name="QtUi") at 0x000001C2092906C8>', 'uiLevel': {'base': 3, 2: ['subdivision_submenu'], 0: [], 1: [], 3: ['subdivision']}, 'state': 0, 'class': '<maya_subdivision.Subdivision(0x1c22d8922d0) at 0x000001C209439708>'}, 'symmetry': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227706730, name="QtUi") at 0x000001C209290B88>', 'uiLevel': {'base': 3, 2: ['symmetry_submenu'], 0: [], 1: [], 3: ['symmetry']}, 'state': 0, 'class': '<maya_symmetry.Symmetry(0x1c228738ad0) at 0x000001C20907CD88>'}, 'transform': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227707770, name="QtUi") at 0x000001C209292348>', 'uiLevel': {'base': 3, 2: ['transform_submenu'], 0: [], 1: [], 3: ['transform']}, 'state': 0, 'class': '<maya_transform.Transform(0x1c22caaa010) at 0x000001C209740488>'}, 'utilities': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2277073b0, name="QtUi") at 0x000001C209292D88>', 'uiLevel': {'base': 3, 2: ['utilities_submenu'], 0: [], 1: [], 3: ['utilities']}, 'state': 0, 'class': '<maya_utilities.Utilities(0x1c22b1e9550) at 0x000001C209740AC8>'}, 'uv': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227707230, name="QtUi") at 0x000001C209294848>', 'uiLevel': {'base': 3, 2: ['uv_submenu'], 0: [], 1: [], 3: ['uv']}, 'state': 0, 'class': '<maya_uv.Uv(0x1c22b1e2450) at 0x000001C2090C74C8>'}, 'vfx': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c227707a30, name="QtUi") at 0x000001C209296F08>', 'uiLevel': {'base': 3, 2: ['vfx_submenu'], 0: [], 1: [], 3: ['vfx']}, 'state': 0, 'class': '<maya_vfx.Vfx(0x1c22b659310) at 0x000001C209769EC8>'}, 'duplicate_linear': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2275e00e0, name="QtUi") at 0x000001C2093266C8>', 'uiLevel': {'base': 4}, 'state': 0}, 'duplicate_radial': {'ui': '<PySide2.QtWidgets.QMainWindow(0x1c2278bbb00, name="QtUi") at 0x000001C2092732C8>', 'uiLevel': {'base': 4}, 'state': 0}}


older version:
sbDict={
	'polygons':{'class': '<Polygons>',
				'ui': '<polygons ui object>',
				'uiLevel': 3,
				'size': [210, 480],
				'widgets': {'<widgets.ComboBox.ComboBox object at 0x0000016B6C078908>': {
									'widgetName': 'cmb002', 
									'widgetType': 'ComboBox', 
									'derivedType': 'QComboBox', 
									'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000016B62BC5780>',
									'prefix':'cmb', 
									'docString': '\n\t\tSelect All Of Type\n\t\t',
									'method': '<bound method Polygons.cmb002 of <slots_max_polygons.Polygons object at 0x0000016B6BC26470>>'}, }},
	'mainAppWindow': None,
	'uiNames': ['polygons'],
	'prevCommand': [['b000', 'multi-cut tool']],
	'prevCamera:': [['v000', 'Viewport: Persp']],
	'gcProtect': ['<protected object>']}


#real world example:
sbDict = {
'materials': {
	'widgets': {
		'<PySide2.QtWidgets.QVBoxLayout object at 0x0000000003D07208>': {'widgetType': 'QVBoxLayout', 'widgetName': 'verticalLayout_2', 'derivedType': 'QVBoxLayout', 'signalInstance': None, 'docString': None, 'prefix': None, 'method': None}, 
		'<widgets.pushButton.PushButton object at 0x0000000003D04E08>': {'widgetType': 'PushButton', 'widgetName': 'tb002', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A463D8>', 'docString': None, 'prefix': 'tb', 'method': '<bound method Materials.wrapper of <slots_max_materials.Materials object at 0x0000000003D547C8>>'}, 
		'<PySide2.QtWidgets.QGroupBox object at 0x0000000003D07248>': {'widgetType': 'QGroupBox', 'widgetName': 'group000', 'derivedType': 'QGroupBox', 'signalInstance': None, 'docString': None, 'prefix': 'group', 'method': None}, 
		'<PySide2.QtWidgets.QPushButton object at 0x0000000003D07288>': {'widgetType': 'QPushButton', 'widgetName': 'b002', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A46390>', 'docString': None, 'prefix': 'b', 'method': '<bound method Materials.wrapper of <slots_max_materials.Materials object at 0x0000000003D547C8>>'}, 
		'<widgets.pushButton.PushButton object at 0x0000000003D04FC8>': {'widgetType': 'PushButton', 'widgetName': 'tb001', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A46408>', 'docString': '\n\t\tStored Material Options\n\t\t', 'prefix': 'tb', 'method': '<bound method Materials.tb001 of <slots_max_materials.Materials object at 0x0000000003D547C8>>'}, 
		'<PySide2.QtWidgets.QWidget object at 0x0000000003D070C8>': {'widgetType': 'QWidget', 'widgetName': 'mainWindow', 'derivedType': 'QWidget', 'signalInstance': None, 'docString': None, 'prefix': 'mainWindow', 'method': None}, 
		'<widgets.progressBar.ProgressBar object at 0x0000000003D07088>': {'widgetType': 'ProgressBar', 'widgetName': 'progressBar', 'derivedType': 'QProgressBar', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A463F0>', 'docString': None, 'prefix': 'progressBar', 'method': None}, 
		'<widgets.comboBox.ComboBox object at 0x0000000003D04F08>': {'widgetType': 'ComboBox', 'widgetName': 'cmb002', 'derivedType': 'QComboBox', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A46378>', 'docString': '\n\t\tMaterial list\n\n\t\t:Parameters:\n\t\t\tindex (int) = parameter on activated, currentIndexChanged, and highlighted signals.\n\t\t', 'prefix': 'cmb', 'method': '<bound method Materials.cmb002 of <slots_max_materials.Materials object at 0x0000000003D547C8>>'}, 
		'<widgets.pushButtonDraggable.PushButtonDraggable object at 0x0000000003D04D88>': {'widgetType': 'PushButtonDraggable', 'widgetName': 'draggable_header', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A463A8>', 'docString': '\n\t\tContext menu\n\t\t', 'prefix': 'draggable_header', 'method': '<bound method Materials.draggable_header of <slots_max_materials.Materials object at 0x0000000003D547C8>>'}, 
		'<PySide2.QtWidgets.QGridLayout object at 0x0000000003D07148>': {'widgetType': 'QGridLayout', 'widgetName': 'gridLayout_2', 'derivedType': 'QGridLayout', 'signalInstance': None, 'docString': None, 'prefix': None, 'method': None}, 
		'<PySide2.QtWidgets.QHBoxLayout object at 0x0000000003D07188>': {'widgetType': 'QHBoxLayout', 'widgetName': 'horizontalLayout', 'derivedType': 'QHBoxLayout', 'signalInstance': None, 'docString': None, 'prefix': 'horizontalLayout', 'method': None}, 
		'<PySide2.QtWidgets.QVBoxLayout object at 0x0000000003D071C8>': {'widgetType': 'QVBoxLayout', 'widgetName': 'verticalLayout', 'derivedType': 'QVBoxLayout', 'signalInstance': None, 'docString': None, 'prefix': 'verticalLayout', 'method': None}, 
		'<widgets.pushButton.PushButton object at 0x0000000003D04E88>': {'widgetType': 'PushButton', 'widgetName': 'tb000', 'derivedType': 'QPushButton', 'signalInstance': '<PySide2.QtCore.SignalInstance object at 0x0000000002A46420>', 'docString': None, 'prefix': 'tb', 'method': '<bound method Materials.wrapper of <slots_max_materials.Materials object at 0x0000000003D547C8>>'}, 
		'<PySide2.QtWidgets.QWidget object at 0x0000000003D07108>': {'widgetType': 'QWidget', 'widgetName': 'layoutWidget_2', 'derivedType': 'QWidget', 'signalInstance': None, 'docString': None, 'prefix': None, 'method': None}
		}, 
	'size': [256, 182], 
	'ui': '<PySide2.QtWidgets.QMainWindow object at 0x0000000003D04D48>', 
	'class': '<slots_max_materials.Materials object at 0x0000000003D547C8>', 
	'uiLevel': 3
	}
}
'''




# deprecated: -----------------------------------



			# ln_name = self.getUiName(ui, level=[0, 1, 3]) #main menu
			# attr = '{}_ui'.format(ln_name)
			# value = self.getUi(ln_name) #ie. 'polygons_ui': <PySide2.QtWidgets.QMainWindow object at 0x000001D97BCEB0C8>
			# kwargs[attr] = value

			# l2_name = self.getUiName(ui, level=2) #submenu
			# if l2_name:
			# 	attr = '{}_ui'.format(l2_name)
			# 	value = self.getUi(l2_name) #ie. 'polygons_submenu_ui': <PySide2.QtWidgets.QMainWindow object at 0x000001D978D8A708>
			# 	kwargs[attr] = value

			# try: #if there is a list of level 4 ui's add them.
			# 	l4_names = self.getUiName(ui, level=4)
			# 	for n in l4_names:
			# 		attr = '{}_ui'.format(n)
			# 		value = self.getUi(n)
			# 		kwargs[attr] = value
			# except TypeError as error:
			# 	pass


# def getUiDict(self, uiName=None):
# 	'''Get the ui dict from the main sbDict.

# 	:Parameters:
# 		ui (str)(obj) = The ui name, or ui object. ie. 'polygons' or <polygons>
# 						If None is given, the current ui will be used.
# 	:Return:
# 		(dict)
# 	'''
# 	uiName = self.getUiName(ui)

# 	try:
# 		return self.sbDict[uiName]

# 	except KeyError as error:
# 		print ('# Error: {}.ui({}) {} #'.format(__name__, uiName, error))
# 		return {}


		# #add the widget as an attribute of the ui if it is not already.
		# ui = self.getUi(name)
		# if not hasattr(ui, objectName):
		# 	setattr(ui, objectName, widget) #this will add child items as attributes to the main menu so they can be accessed directly.
	



# def hasKey(self, *args): #check if key exists in switchboard dict.
# 	'''
# 	Check if a nested key exists .

# 	:Parameters:
# 		(str) dict keys in order of hierarchy.  ie. 'polygons', 'widgets', 'b001', 'method'

# 	:Return:
# 		(bool)
# 	'''
# 	if len(args)==1:
# 		if args[0] in self.sbDict:
# 			return True

# 	elif len(args)==2:
# 		if args[1] in self.sbDict[args[0]]:
# 			return True

# 	elif len(args)==3:
# 		if args[2] in self.sbDict[args[0]][args[1]]:
# 			return True

# 	elif len(args)==4:
# 		if args[3] in self.sbDict[args[0]][args[1]][args[2]]:
# 			return True
# 	else:
# 		return False




	# def getWidgets(self, name=None):
	# 	'''
	# 	Get all widgets for a ui.

	# 	:Parameters:
	# 		name (str) = name of ui. ie. 'polygons'. If no name is given, the current ui will be used.
	# 	:Return:
	# 		all widgets for the given ui.
	# 	'''
	# 	return self.getWidget(name=name)


	
	# def getPrevNameList_wDuplicates(self):
	# 	'''
	# 	Get previous names as a list (containing duplicates).

	# 	:Return:
	# 		list
	# 	'''
	# 	return self.prevUiName(as_list=True, allowDuplicates=True)



	# def getPrevNameList_woDuplicates(self):
	# 	'''
	# 	Get previous names as a list (duplicates removed).

	# 	:Return:
	# 		list
	# 	'''
	# 	return self.prevUiName(allowLevel0=1, as_list=1)

# def getNameFrom(obj):
# 	'''
# 	Get the ui name from any object existing in 'widgets'.

# 	:Parameters:
# 		obj = <object> - 
# 	:Return:
# 		 'string' - the corresponding method name from the given object.
# 		 ex. 'polygons' from <widget>
# 	'''
# 	for name, v in self.sbDict.items():
# 		if type(v)==dict:
# 			for k, v in v.items():
# 				if type(v)==dict:
# 					for k, v in v.items():
# 						if type(v)==dict:
# 							for k, v in v.items():
# 								if v==obj:
# 									return name