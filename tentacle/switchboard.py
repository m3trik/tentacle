# !/usr/bin/python
# coding=utf-8
from pydoc import locate

from PySide2 import QtCore
try: import shiboken2
except: from PySide2 import shiboken2

from tentacle.ui import UiLoader



# ------------------------------------------------
#	Manage Ui element information.
# ------------------------------------------------
class Switchboard(QtCore.QObject):
	'''Get/set elements across modules using convenience methods.
	
	Ui name/and it's corresponding slot class name should always be the same. (case insensitive) ie. 'polygons' (ui name) will look to build connections to 'Polygons' (class name). 
	Widget objectName/corresponding class method name need to be the same. ie. 'b000' (widget objectName) will try to connect to <b000> class method.
	A widgets dict is constructed as needed for each class when connectSlots (or any other dependant) is called.

	_sbDict = {	
		'<uiName>' : {
					'ui' : <ui object>,
					'uiLevel' : {'base' : <int>}
					'class' : <Class>,
					'size' : [int, int]
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
								}
					}
		}
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
		'QCheckBox':'stateChanged',
		'QRadioButton':'toggled',
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

	_uiHistory = [] #[str list] - Tracks the order in which the uis are called. A new ui is placed at element[-1]. ie. ['previousName2', 'previousName1', 'currentName']
	_commandHistory = [] #[list of 2 element lists] - Command history. ie. [[<b000>, 'multi-cut tool']]
	_cameraHistory = [] #[list of 2 element lists] - Camera history. ie. [[<v000>, 'camera: persp']]
	_gcProtect = [] #[list] - Items protected from garbage collection
	_classProperties = {} #{'<property name>':<property value>} - The additional properties of each of the slot classes.


	def __init__(self, parent=None):
		super().__init__(parent)
		'''
		'''
		for uiName, v in UiLoader().uiDict.items(): #Initialize the sbDict with ui name, ui object, and ui base level.
			self.sbDict[uiName] = { #ie. {'polygons':{'ui':<ui obj>, uiLevel:<int>}}
				'ui': v['ui'], #the ui object.
				'uiLevel': {'base' : v['level']}, #the ui level as an integer value. (the ui level is it's hierarchy)
				'state': 0, #initialization state.
			}

		self.setMainAppWindow(parent.parent())


	@property
	def sbDict(self, debug=0):
		'''Property:sbDict. Get the full switchboard dict.

		:Parameters:
			debug (bool) = Print a copy of the sbDict to console for a visual representation.
						Some objects in the dict will be converted to strings in order to provide a working test example.
						ie. <PySide2.QtWidgets.QMainWindow(0x1fa56db6310, name="QtUi") at 0x000001FA29138EC8> becomes: '<PySide2.QtWidgets.QMainWindow(0x1fa56db6310, name="QtUi") at 0x000001FA29138EC8>' 

		:Return:
			(dict)
		'''
		def convert(obj): #recursively convert items in sbDict for debugging.
			if isinstance(obj, (list, set, tuple)):
				return [convert(i) for i in obj]
			elif isinstance(obj, dict):
				return {convert(k):convert(v) for k, v in obj.items()}
			elif not isinstance(obj, (float, int, str)):
				return str(obj)
			else:
				return obj

		if debug:
			print (convert(self.sbDict, debug=False))

		try:
			return self._sbDict

		except AttributeError as error:
			self._sbDict = {}
			return self._sbDict


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
			widgets = ui.__dict__.values() #each object in the ui:

		for w in widgets:
			typ = w.__class__.__base__.__name__ if filterByBaseType else self._getDerivedType(w)
			if not typ in exclude and (typ in include if include else typ not in include):
				self.addWidget(uiName, w, **kwargs)


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

		self.setAttributes(widget, **kwargs) #set any passed in keyword args for the widget.

		objectName = str(widget.objectName())
		classInst = self.getClassInstance(uiName, **self.getClassProperties(uiName)) #get the corresponding slot class from the ui name. ie. class <Polygons> from uiName 'polygons'.
		derivedType = self._getDerivedType(widget) #the base class of any custom widgets.  ie. 'QPushButton' from 'PushButton'
		signalType = self.getDefaultSignalType(derivedType) #get the default signal type for the widget as a string. ie. 'released' from 'QPushButton'
		signalInstance = getattr(widget, signalType, None) #add signal to widget. ie. <widget.valueChanged>
		method = getattr(classInst, objectName, None) #use 'objectName' to get the corresponding method of the same name. ie. method <b006> from widget 'b006' else None
		docString = getattr(method, '__doc__', None)
		prefix = self.prefix(objectName) #returns an string alphanumberic prefix if objectName startswith a series of alphanumberic chars, and is followed by three integers. ie. 'cmb' from 'cmb015'
		isTracked = True if derivedType in self.trackedWidgets else False

		self.widgets(uiName).update( #add the widget and it's values.
					{widget:{
						'widgetName':objectName, 
						'widgetType':widget.__class__.__name__,
						'derivedType':derivedType,
						'signalInstance':signalInstance,
						'method': method,
						'prefix':prefix,
						'docString':docString,
						'tracked':isTracked,
						}
					})
		# print(self.sbDict[uiName]['widgets'][widget])
		return self.sbDict[uiName]['widgets'][widget] #return the stored widget.


	def removeWidgets(self, widgets, uiName=None):
		'''Remove widget keys from the widgets dict.

		:Parameters:
			widgets (obj)(list) = single or list of QWidgets.
			uiName (str) = ui name.
		'''
		if not uiName:
			uiName = self.getUiName()

		widgets = self.list_(widgets) #if 'widgets' isn't a list, convert it to one.
		for widget in widgets:
			w = self.sbDict[uiName]['widgets'].pop(widget, None)
			self.gcProtect(w)

			try: #remove the widget attribute from the ui if it exists.
				delattr(ui, w.objectName())
			except Exception as error:
				pass; # print (__name__+':','removeWidgets:', widgets, uiName, error)


	def widgets(self, uiName, query=False):
		'''A dictionary holding widget information.

		:Parameters:
			uiName (str) = The name of parent ui/class. ie. 'polygons'
			query (bool) = Check if there exists a 'widgets' key for the given class name.

		:Return:
			connection dict of given name with widget name string as key.

		ex. {'widgets' : {
						'<widget>':{
									'widgetName':'objectName',
									'signalInstance':<widget.signal>,
									'widgetType':'<widgetClassName>',
									'derivedType':'<derivedClassName>',

									'method':<method>,
									'prefix':'alphanumeric prefix',
									'docString':'method docString'
						}
			}
		'''
		if query:
			return True if 'widgets' in self.sbDict[uiName] else False

		try:
			return self.sbDict[uiName]['widgets']

		except KeyError as error:
			self.sbDict[uiName]['widgets'] = {}
			self.addWidgets(uiName) #, exclude=['QLayout', 'QBoxLayout'], filterByBaseType=True) #construct the signals and slots for the ui

			return self.sbDict[uiName]['widgets']


	def setAttributes(self, obj=None, order=['setVisible'], **kwargs):
		'''
		:Parameters:
			obj (obj) = the child obj or widgetAction to set attributes for. (default=self)
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


	def setUniqueObjectName(self, widget, uiName=None, _num=None):
		'''Set a unique object name for the given widget based on the pattern name000.

		:Parameters:
			widget (obj) = The child widget to set an object name for.
			uiName (str) = Ui name.
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

		if not uiName:
			uiName = self.getUiName()

		widgetType = widget.__class__.__name__

		num=0
		widgetName = self.setUniqueObjectName(_num=num)
		while self.getWidget(widgetName, uiName): #if a widget of the same name already exists; increment by one and try again.
			num+=1; widgetName = nameGenerator(num)

		widget.setObjectName(widgetName)
		return widget.objectName()


	def getClassProperties(self, ui):
		'''Get properties as keyword arguments for the given ui.

		:Parameters:
			ui (str)(obj) = The ui, or ui name. ie. <Polygons> or 'polygons'

		:Return:
			(dict) packed keyword arguments. ie. {'_currentUi': <function <lambda> at 0x000001D97BCFCAC8>, '_ui': <function <lambda> at 0x000001D97BCFCA58>, 'tcl': <PySide2.QtWidgets.QWidget object at 0x000001D94E1E9D88>, 'polygons_submenu': <PySide2.QtWidgets.QMainWindow object at 0x000001D978D8A708>, 'sb': <switchboard.Switchboard object at 0x000001D97BD7D1C8>, 'polygons': <PySide2.QtWidgets.QMainWindow object at 0x000001D97BCEB0C8>}
		'''
		try: #return kwargs for the given ui, if already stored in '_classProperties' dict.
			return self._classProperties[ui]

		except KeyError as error:

			kwargs = {}

			ln_name = self.getUiName(ui, level=[0, 1, 3]) #main menu
			kwargs['{}_ui'.format(ln_name)] = self.getUi(ln_name) #ie. 'polygons_ui': <PySide2.QtWidgets.QMainWindow object at 0x000001D97BCEB0C8>
	
			l2_name = self.getUiName(ui, level=2) #submenu
			if l2_name:
				kwargs['{}_ui'.format(l2_name)] = self.getUi(l2_name) #ie. 'polygons_submenu_ui': <PySide2.QtWidgets.QMainWindow object at 0x000001D978D8A708>

			kwargs['_current_ui'] = lambda: self.getUi() if self.getUi() in (d['ui'] for n, d in self.sbDict.items() if ln_name in n) else ln #if the current ui is not one of the parent ui's children or the parent ui itself, default to the parent ui.

			kwargs['tcl'] = self.parent() #tcl instance


			try: #if there is a list of level 4 ui's add them.
				l4_names = self.getUiName(ui, level=4)
				for n in l4_names:
					kwargs['{}_ui'.format(n)] = self.getUi(n)
			except TypeError as error:
				pass

			self._classProperties[ui] = kwargs

			return self._classProperties[ui]


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


	def getSignal(self, uiName, widget=None):
		'''Get the widget object with attached signal (ie. b001.onPressed) from the given widget name.

		:Parameters:
			uiName (str) = THe name of ui. ie. 'polygons'
			objectName (str) = optional widget name. ie. 'b001'

		:Return:
			if objectName: (obj) widget object with attached signal (ie. b001.onPressed) of the given widget name.
			else: (list) all of the signals associated with the given name as a list.
		'''
		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		if widget:
			if not widget in self.sbDict[uiName]['widgets']:
				self.addWidget(uiName, widget)
			return self.sbDict[uiName]['widgets'][widget]['signalInstance']
		else:
			return [w['signalInstance'] for w in self.sbDict[uiName]['widgets'].values()]


	def setConnections(self, ui):
		'''Replace any signal connections of a previous ui with the set for the ui of the given name.

		:Parameters:
			ui (str) = The name of ui, or the ui itself. ie. 'polygons' or <polygons>
		'''
		prevUiName = self.prevUiName(allowDuplicates=True)
		if prevUiName:
			self.disconnectSlots(prevUiName) #remove signals from the previous ui.
		self.connectSlots(ui)


	def connectSlots(self, ui, widgets=None):
		'''Connects signals/slots from the widgets for the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (str) = The name of ui, or the ui itself. ie. 'polygons' or <polygons>
			widgets (obj)(list) = QWidget(s)
		'''
		uiName = self.getUiName(ui)

		if widgets is None:
			widgets = self.widgets(uiName)
		else:
			widgets = self.list_(widgets) #convert 'widgets' to a list if it is not one already.

		for widget in widgets:
			signal = self.getSignal(uiName, widget)
			slot = self.getMethod(uiName, widget)
			# print('connectSlots: ', uiName, widget.objectName(), signal, slot)
			if slot and signal:
				try:
					if isinstance(slot, (list, set, tuple)):
						map(signal.connect, slot) #connect to multiple slots from a list.
					else:
						signal.connect(slot) #connect single slot (main and cameras ui)

				except Exception as error:
					print('Error: {0} {1} connectSlots: {2} {3}'.format(uiName, widget.objectName(), signal, slot), '\n', error)


	def disconnectSlots(self, ui, widgets=None):
		'''Disconnects signals/slots from the widgets for the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (str) = The name of ui, or the ui itself. ie. 'polygons' or <polygons>
			widgets (obj)(list) = QWidget
		'''
		uiName = self.getUiName(ui)

		if widgets is None:
			widgets = self.widgets(uiName)
		else:
			widgets = self.list_(widgets) #convert 'widgets' to a list if it is not one already.

		for widget in widgets:
			signal = self.getSignal(uiName, widget)
			slot = self.getMethod(uiName, widget)
			# print('disconnectSlots: ', uiName, widget.objectName(), signal, slot)
			if slot and signal:
				try:
					if isinstance(slot, (list, set, tuple)):
						signal.disconnect() #disconnect all #map(signal.disconnect, slot) #disconnect multiple slots from a list.
					else:
						signal.disconnect(slot) #disconnect single slot (main and cameras ui)

				except Exception as error:
					print('Error: {0} {1} disconnectSlots: {2} {3} #'.format(uiName, widget.objectName(), signal, slot), '\n', error)


	def getUi(self, uiName=None, level=None, setAsCurrent=False):
		'''Property:ui. Get a dynamic ui using its string name, or if no argument is given, return the current ui.

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
			if level is None:
				level = [0,1,2,3,4]
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


	def setUiState(self, state=1, ui=None):
		'''Get the initialization state of the given ui as an int.

		:Parameters:
			ui (str)(obj) = The ui object, or ui name.
		'''
		uiName = self.getUiName(ui)

		self.sbDict[uiName]['state'] = state


	def getUiState(self, ui=None):
		'''Get the initialization state of the given ui as an int.

		:Parameters:
			ui (str)(obj) = The ui object, or ui name.

		:Return:
			(int)
		'''
		uiName = self.getUiName(ui)

		return self.sbDict[uiName]['state']


	def setUiName(self, i):
		'''Property:uiName. Register the uiName in history as current.
		The '_uiHistory' list is used for various things such as; maintaining a history of ui's that have been called.

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
		'''Property:uiName. Get the ui name as a string.
		If no argument is given, the name for the current ui will be returned.

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
				return None; print ('{}.getUiName({}, {}, {}): {}'.format(__name__, ui, case, level, error))

		elif isinstance(ui, (str)):
			if ui=='all': #get all ui of the given level(s).
				if level is None:
					level = [0,1,2,3,4]
				return [self.setCase(n, case) for n in self.sbDict if self.getUiLevel(n) in level]
			else:  #get the ui name from ui name.
				uiName = ui

		else: #get the ui name from ui object.
			uiName = next((n for n, d in self.sbDict.items() if d['ui']==ui), None)

		if setAsCurrent:
			self.setUiName(uiName)

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
					try:
						l2 = self.sbDict[uiName]['uiLevel'][2]
					except KeyError as error:
						c = uiName.split('_submenu')[0] + '_submenu'
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


	def getUiIndex(self, uiName=False):
		'''Property:uiIndex. Get the index of the given ui name.

		:Parameters:
			uiName (str) = The name of ui/class. ie. 'polygons'

		:Return:
			if uiName: index of given name from key.
			else: index of current ui
		'''
		if uiName:
			return self.getUiName('all').index(uiName)
		else:
			return self.getUiName('all').index(self.getUiName())


	def setUiSize(self, uiName=None, size=None): #store ui size.
		'''Property:size. Set the size of a ui.
		If no size is given, the minimum ui size needed to frame its
		contents will be used. If no uiName is given, the current ui will be used.

		:Parameters:
			uiName (str) = optional ui name
			size = [int, int] - optional width and height as an integer list. [width, height]

		:Return:
			ui size info as integer values in a list. [width, hight]
		'''
		if not uiName:
			uiName = self.getUiName()

		if not size:
			ui = self.getUi(uiName)
			size = [ui.frameGeometry().width(), ui.frameGeometry().height()]

		self.sbDict[uiName]['size'] = size
		return self.sbDict[uiName]['size']


	def setUiSizeX(self, width, uiName=None):
		'''Property:sizeX. Set the X (width) value for the current ui.

		:Parameters:
			uiName (str) = The name of the ui to set the width for.
			width (int) = X size as an int
		'''
		height = self.getUiSize(uiName=uiName, height=True) #get the hight value.
		self.setUiSize(uiName=uiName, width=width, height=height)


	def setUiSizeY(self, height, uiName=None):
		'''Property:sizeY. Set the Y (height) value for the current ui.

		:Parameters:
			uiName (str) = The name of the ui to set the height for.
			height (int) = Y size as an int
		'''
		width = self.getUiSize(uiName=uiName, width=True) #get the width value.
		self.setUiSize(uiName=uiName, height=height, width=width)


	def getUiSize(self, uiName=None, width=None, percentWidth=None, height=None, percentHeight=None): #get current ui size info.
		'''Property:size. Get the size info for each ui (allows for resizing a stacked widget where ordinarily resizing is constrained by the largest widget in the stack)

		:Parameters:
			uiName (str) = The ui name to get size from.
			width (int) = Returns the width of current ui.
			height (int) = Returns hight of current ui.
			percentWidth (int) = Returns a percentage of the width.
			percentHeight (int) = returns a percentage of the height.

		:Return:
			(int)(list)
			if width: returns width as int
			elif height: returns height as int
			elif percentWidth: returns the percentage of the width as an int
			elif percentHeight: returns the percentage of the height as an int
			else: ui size info as integer values in a list. [width, hight]
		'''
		if not uiName:
			uiName = self.getUiName()

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


	def getUiSizeX(self, uiName=None):
		'''Property:sizeX. Get the X (width) value for the current ui.

		:Parameters:
			uiName (str) = ui uiName to get size from.

		:Return:
			returns width as int
		'''
		return self.getUiSize(uiName=uiName, width=True)


	def getUiSizeY(self, uiName=None):
		'''Property:sizeY. Get the Y (height) value for the current ui.

		:Parameters:
			uiName (str) = ui name to get size from.

		:Return:
			returns width as int
		'''
		return self.getUiSize(uiName=uiName, height=True)


	def setMainAppWindow(self, app):
		'''Property:mainAppWindow. Set parent application.

		:Parameters:
			app = app object.

		:Return:
			string name of app
		'''
		self._mainAppWindow = app

		return self._mainAppWindow


	def getMainAppWindow(self, objectName=False):
		'''Property:mainAppWindow. Get parent application if any.

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


	def _setClassInstance(self, class_, **kwargs):
		'''Property:classInst. Stores an instance of a class.
		If the name is a submenu, the parent class will be returned. ie. <Polygons> from 'polygons_submenu'

		:Parameters:
			class_ (str)(obj) = The class or class name to import, create an instance of, and store. 
					ie. 'polygons', 'slots_max_polygons.Polygons', or <slots_max_polygons.Polygons>

		:Return:
			(obj) The class instance.
		'''
		if isinstance(class_, (str)): #if arg given as string or unicode:
			mainAppWindowName = self.getMainAppWindow(objectName=True)
			name = self.getUiName(class_, case='camelCase', level=[0,1,3])
			className = self.getUiName(class_, case='pascalCase', level=[0,1,3])
			path = '{0}_{1}.{2}'.format(mainAppWindowName, name, className) #ie. 'maya_init.Init'
			class_ = locate(path)
			if class_==None:
				print ('# Error: {}._setClassInstance({}): import {} failed. #'.format(__name__, class_, path))
				return None

		if not name:
			name = class_.__class__.__name__ #if arg as <object>:

		name = self.setCase(name, 'camelCase') #lowercase the first letter.

		if not name in self.sbDict:
			self.sbDict[name] = {}

		try:
			self.sbDict[name]['class'] = class_(**kwargs)
		except Exception as error:
			self.sbDict[name]['class'] = class_

		return self.sbDict[name]['class']


	def getClassInstance(self, class_, **kwargs):
		'''Property:classInst. Case insensitive. (Class string keys are lowercase and any given string will be converted automatically)
		If class is not in self.sbDict, getClassInstance will attempt to use _setClassInstance() to first store the class.

		:Parameters:
			class_ (str)(obj) = module name.class to import and store class.
				ie. 'polygons', 'slots_max_polygons.Polygons', or <slots_max_polygons.Polygons>

		:Return:
			class object.
		'''
		if isinstance(class_, (str)): #if arg given as string.
			name = self.getUiName(class_, case='camelCase', level=[0,1,3])

		else: #if arg as <object>:
			try:
				name = class_.__class__.__name__
			except Exception as error:
				return None

		try:
			return self.sbDict[name]['class']
		except KeyError as error:
			return self._setClassInstance(name, **kwargs) #set the class instance while passing in any keyword arguments into **kwargs.


	def getWidget(self, objectName=None, ui=None, tracked=False):
		'''Property:getWidgets. Case insensitive. Get the widget object/s from the given ui and objectName.

		:Parameters:
			objectName (str) = optional name of widget. ie. 'b000'
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
			tracked (bool) = Return only those widgets defined as 'tracked'. 

		:Return:
			(obj) if objectName:  widget object with the given name from the current ui.
				  if ui and objectName: widget object with the given name from the given ui name.
			(list) if ui: all widgets for the given ui.
		'''
		if not ui:
			ui = self.getUiName()
		if not isinstance(ui, str):
			ui = self.getUiName(ui)

		if not 'widgets' in self.sbDict[ui]:
			self.widgets(ui) #construct the signals and slots for the ui

		if objectName:
			return next((w if shiboken2.isValid(w) 
				else self.removeWidgets(w, ui) for w in self.sbDict[ui]['widgets'].values() 
					if w['widgetName']==objectName and self.isTracked(w, ui) if tracked), None)
		elif tracked:
			return [w for w in self.sbDict[ui]['widgets'].copy() if (self.isTracked(w, ui) and shiboken2.isValid(w))]
		else:
			return [w for w in self.sbDict[ui]['widgets'].copy() if shiboken2.isValid(w)] #'copy' is used in place of 'keys' RuntimeError: dictionary changed size during iteration


	def isTracked(self, widget, ui=None):
		'''Query if the widget is mouse tracked.

		:Parameters:
			widget (obj) = The widget to query the tracking state of.
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
		:Return:
			(bool)
		'''
		if not ui:
			ui = self.getUiName()
		if not isinstance(ui, str):
			ui = self.getUiName(ui)

		if not 'widgets' in self.sbDict[ui]:
			self.widgets(ui) #construct the signals and slots for the ui

		try:
			return self.sbDict[ui]['widgets'][widget]['tracked']

		except KeyError as error:
			return False


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

			for widget, v in self.sbDict[uiName]['widgets'].items():
				if method==v['method']:
					return widget


	def getWidgetName(self, widget=None, uiName=None):
		'''Property:getWidgetNames. Get the widget's stored string objectName.

		:Parameters:
			widget (obj) = QWidget
			uiName (str) = The name of parent ui. ie. 'polygons'. If no name is given, the current ui will be used.

		:Return:
			if widget: (str) the stored objectName for the given widget.
			if not widget: (list) all names.
			if uiName: stored objectNames for the given ui name.
			if not uiName: stored objectName from the current ui.
			else: all stored objectNames.
		'''
		if not uiName:
			uiName = self.getUiName()

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		if widget:
			if not widget in self.sbDict[uiName]['widgets']:
				self.addWidget(uiName, widget)
			return self.sbDict[uiName]['widgets'][widget]['widgetName']

		if uiName and not widget: #return all objectNames from ui name.
			return [w['widgetName'] for w in self.sbDict[uiName]['widgets'].values()]
		else: #return all objectNames:
			return [w['widgetName'] for k,w in self.sbDict.items() if k=='widgets']


	def getWidgetType(self, widget, uiName=None):
		'''Get widget type class name as a string.
		ie. 'QPushButton' from pushbutton type widget.

		:Parameters:
			widget (str) = name of widget/widget
				*or <object> -widget
			uiName (str) = The name of parent ui. (else use current ui)

		:Return:
			(str) The corresponding widget class name.
		'''
		if isinstance(widget, (str)):
			objectName = self.sbDict[uiName]['widgets'][widget] #use the stored objectName as a more reliable key.
			widget = self.getWidget(objectName, uiName) #use the objectName to get a string key for 'widget'

		if not uiName:
			uiName = self.getUiName()

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		try:
			if not widget in self.sbDict[uiName]['widgets']:
				self.addWidget(uiName, widget)
			return self.sbDict[uiName]['widgets'][widget]['widgetType']

		except KeyError:
			return None


	def _getDerivedType(self, widget):
		'''Internal use. Get the base class of a custom widget.
		If the type is a standard widget, the derived type will be that widget's type.

		:Parameters:
			widget (obj) = QWidget. ie. widget with class name: 'PushButton'

		:Return:
			(string) base class name. ie. 'QPushButton'
		'''
		# print(widget.__class__.__mro__)
		for c in widget.__class__.__mro__:
			if c.__module__=='PySide2.QtWidgets': #check for the first built-in class.
				derivedType = c.__name__ #Then use it as the derived class.
				return derivedType


	def getDerivedType(self, widget, uiName=None):
		'''Get the base class of a custom widget.
		If the type is a standard widget, the derived type will be that widget's type.

		:Parameters:
			widget (str)(obj) = QWidget or it's objectName.
			uiName (str) = ui name.

		:Return:
			(string) base class name. ie. 'QPushButton' from a custom widget with class name: 'PushButton'
		'''
		if isinstance(widget, (str)):
			objectName = self.sbDict[uiName]['widgets'][widget] #use the stored objectName as a more reliable key.
			widget = self.getWidget(objectName, uiName) #use the objectName to get a string key for 'widget'

		if not uiName:
			uiName = self.getUiName()

		if not self.widgets(uiName, query=True):
			self.widgets(uiName) #construct the signals and slots for the ui

		try:
			if not widget in self.sbDict[uiName]['widgets']:
				self.addWidget(uiName, widget)
			return self.sbDict[uiName]['widgets'][widget]['derivedType']

		except KeyError:
			return None


	def getMethod(self, name, widget=None):
		'''Get the method(s) associated with the given ui / widget.

		:Parameters:
			name (str) = name of class. ie. 'polygons'
			widget (str)(obj) = widget, widget's objectName, or method name.

		:Return:
			if widget: corresponding method object to given widget.
			else: all of the methods associated to the given ui name as a list.

		ex. sb.getMethod('polygons', <b022>)() #call method <b022> of the 'polygons' class
		'''
		if not self.widgets(name, query=True):
			self.widgets(name) #construct the signals and slots for the ui

		if widget is None: #get all methods for the given ui name.
			return [w['method'] for w in self.sbDict[name]['widgets'].values()]

		try:
			if type(widget) is str:
				return next(w['method'][0] for w in self.sbDict[name]['widgets'].values() if w['widgetName']==widget) #if there are event filters attached (as a list), just get the method (at index 0).
			
			elif not widget in self.sbDict[name]['widgets']:
				self.addWidget(name, widget)
			return self.sbDict[name]['widgets'][widget]['method'][0] #if there are event filters attached (as a list), just get the method (at index 0).

		except:
			if type(widget) is str:
				return next((w['method'] for w in self.sbDict[name]['widgets'].values() if w['widgetName']==widget), None)
			
			elif not widget in self.sbDict[name]['widgets']:
				self.addWidget(name, widget)
			return self.sbDict[name]['widgets'][widget]['method']


	def getDocString(self, name, method, first_line_only=True, unformatted=False):
		'''
		:Parameters:
			name (str) = optional name of class. ie. 'polygons'. else, use current name.
			method (str)(obj) = method, or name of method. ie. 'b001'
			unformatted = bool return entire unedited docString

		:Return:
			if unformatted: the entire stored docString
			else: edited docString; name of method
		'''
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
		'''Property:prevName. Get the previously called ui name string, or a list of ui name strings ordered by use.
		It does so by pulling from the 'uiNames' list which keeps a list of the ui names as they are called. ie. ['previousName2', 'previousName1', 'currentName']

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


	def getUiLevel(self, uiName=None):
		'''Property:uiLevel. Get the hierarcical level of a ui.
		If no argument is given, the level of current ui will be returned.

		level 0: init (root) (parent class)
		level 1: base_menus
		level 2: sub_menus
		level 3: main_menus
		level 4: popup_menus

		:Parameters:
			uiName (str)(obj) = The ui name or ui object to get level of. ie. 'polygons' or <polygons>

		:Return:
			(int) ui level.
		'''
		if not uiName:
			uiName = self.getUiName() #get the current ui name.

		try:
			n = self.getUiName(uiName)
			uiName = self.setCase(n, 'camelCase') #lowercase the first letter of name.
			return self.sbDict[uiName]['uiLevel']['base']

		except (TypeError, ValueError) as error:
			print ('{}.getUiLevel({}): {}'.format(__name__, uiName, error))
			return None


	def prefix(self, widget, prefix=None):
		'''Get or Query the widgets prefix.
		A valid prefix is returned when the given widget's objectName startswith an alphanumeric char, followed by at least three integers. ex. i000 (alphanum,int,int,int)
		if the second 'prefix' arg is given, then the method checks if the given objectName has the prefix, and the return value is bool.

		prefixTypes = {'QPushButton':'b', 'QPushButton':'v', 'QPushButton':'i', 'QPushButton':'tb', 'QComboBox':'cmb', 
			'QCheckBox':'chk', 'QRadioButton':'chk', 'QPushButton(checkable)':'chk', 'QSpinBox':'s', 'QDoubleSpinBox':'s',
			'QLabel':'lbl', 'QWidget':'w', 'QTreeWidget':'tree', 'QListWidget':'list', 'QLineEdit':'line', 'QTextEdit':'text'}

		ex. prefix('b023') returns 'b'

		:Parameters:
			widget (str)(obj) = widget or it's objectName.
			prefix (str)(list) = optional; check if the given objectName startwith this prefix.

		:Return:
			if prefix arg given:
				(bool) - True if correct format else; False.
			else:
				(str) alphanumeric 'string' 

		ex call: sb.prefix(widget, ['b', 'chk', '_']) #return True if the given widget's objectName starts with 'b', 'chk', '_' and is followed by 3 or more integers, else False.
		'''
		if prefix is not None: #check the actual prefix against the given prefix and return bool.
			prefix = self.list_(prefix) #if 'widgets' isn't a list, convert it to one.

			uiName = self.getUiName()
			for p in prefix:
				try:
					if isinstance(widget, (str)): #get the prefix using the widget's objectName.
						prefix_ = next(w['prefix'] for w in self.sbDict[uiName]['widgets'].values() if w['widgetName']==widget)
					else:
						prefix_ = self.sbDict[uiName]['widgets'][widget]['prefix']
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


	@staticmethod
	def list_(x):
		'''Convert a given obj to a list if it isn't a list, set, or tuple already.

		:Parameters:
			x (unknown) = The object to convert to a list if not already a list, set, or tuple.

		:Return:
			(list)
		'''
		return x if isinstance(x, (list, tuple, set)) else [x]


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


	#assign properties
	uiName = property(getUiName, setUiName)
	prevName = property(prevUiName)
	ui = property(getUi)
	uiIndex = property(getUiIndex)
	uiLevel = property(getUiLevel)
	uiState = property(getUiState, setUiState)
	size = property(getUiSize, setUiSize)
	sizeX = property(getUiSizeX, setUiSizeX)
	sizeY = property(getUiSizeY, setUiSizeY)
	classInst = property(getClassInstance, _setClassInstance)
	mainAppWindow = property(getMainAppWindow, setMainAppWindow)
	getWidgets = property(getWidget)
	getWidgetNames = property(getWidgetName)









if __name__=='__main__':
	#initialize and create a Switchboard instance
	from PySide2.QtWidgets import QApplication
	qApp = QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QApplication(sys.argv)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

'''
test example:
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