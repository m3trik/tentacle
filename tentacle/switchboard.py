# !/usr/bin/python
# coding=utf-8
import os, sys

import re
import glob
import importlib
import inspect

from PySide2 import QtCore, QtWidgets
from PySide2.QtUiTools import QUiLoader

from ui.styleSheet import StyleSheet
import tools



class Switchboard(QUiLoader):
	'''
	:properties:
		sb.<ui name> = Any ui located in the switchboard's ui directory.
		sb.<custom widget name> = Any of the custom widgets in the widget directory.

		ui.name = The ui's file name.
		ui.base = The base ui name. The base name is any characters before an underscore in the ui's name.
		ui.path = The directory path containing the ui file.
		ui.tags = Any ui tags as a list. Tags are trailing strings in the ui name preceeded by a hashtag used to define special behaviors.
		ui.level = The ui level. 0: init (root), 1: base menus, 2: sub menus, 3: parent menus, 4: popup menus
		ui.sizeX = The original width of the ui.
		ui.sizeY = The original hight of the ui.

		ui.isInitialized = A convienience property not handled by this module. Can be used to mark the ui as initialized in the main app.
		ui.isConnected = True if the ui is connected to it's slots.
		ui.isSynced = True if the ui is synced. Synced means that the submenu widget values change if the parent menu's are changed and vice versa.
		ui.isSubmenu = True if the ui is a submenu (level 2).
		ui.preventHide = While True the hide method is disabled.
		ui.hide = An override of the built-in hide method.

		ui.addWidgets = (function) add widgets to the ui.
		ui.widgets = All the widgets of the ui.
		ui.trackedWidgets = A list of widgets that are being mousetracked.
		ui.slots = The slots class instance.
		ui.connected = True if the ui is connected. If set to True, the ui will be set as current and connections established.
		ui.synced = True if the ui is synced. When set to True any submenu widgets will be synced with their parent menu's counterparts.
		ui.isCurrent = True if the ui is set as current.
		ui.level3 = The parent menu of the ui (level 3).
		ui.level2 = The submenu for the ui (level 2).

		w.ui = Access the widget's parent ui (QMainWindow).
		w.name = The widget's object name.
		w.type = The widget's class name.
		w.derivedType = A custom widget's derived class name.
		w.signalType = The default signal type for the widget as a string. ie. 'released' from 'QPushButton'
		w.signal = The signal. ie. <widget.valueChanged>. Used when establishing connections.
		w.method = The corresponding method of the slot's class of the same name as the widget's object name. ie. method <b006> from widget 'b006' else None
		w.prefix = The alphanumberic string prefix determining widget type. If the widget name starts with a series of alphanumberic chars and is followed by three integers. ie. 'cmb' from 'cmb015'
		w.isTracked = True if the widget type is of those in the switchboard's trackedWidgets list.
		w.isSynced = True if the widget is being synced between submenu and it's parent menu.
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
		'QMainWindow', 
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

	_loadedUi = []
	_registeredWidgets = []
	_uiHistory = []
	_cmdHistory = []

	defaultDir = os.path.abspath(os.path.dirname(__file__))
	defaultUiDir = defaultDir+'/ui'
	defaultWgtDir = defaultDir+'/ui/widgets'
	defaultSlotDir = defaultDir+'/slots'

	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	def __init__(self, parent=None, appName='', uiDir=defaultUiDir, widgetDir=defaultWgtDir, slotDir=defaultSlotDir):
		QUiLoader.__init__(self, parent)
		'''
		'''
		self.uiDir = uiDir
		self.widgetDir = widgetDir
		self.slotDir = slotDir
		self.appName = appName

		self.setStyle = StyleSheet.setStyleSheet_
		self._getDerivedType = StyleSheet.getDerivedType
		self.setCase = tools.Txtools.setCase
		self.formatFilepath = tools.Txtools.formatFilepath
		self.list_ = tools.Lstools.list_
		self.convertForDebugging = tools.Lstools.convertForDebugging


	def __getattr__(self, attr):
		'''If an unknown attribute matches the name of a ui in the current ui directory; load it.
		'''
		path = self.uiDir

		uiFullPath = next((f for f in glob.iglob('{}/**/{}.ui'.format(path, attr), recursive=True)), None)
		if not uiFullPath:
			raise AttributeError(__file__, attr)

		ui = self.loadUi(uiFullPath, self.parent()) #load the dynamic ui file.
		return ui


	@staticmethod
	def getPropertyFromUiFile(file, prop):
		'''Get sub-properties and their values from a given property name.
		Returns all items between the opening and closing statements of the given property.

		So 'customwidget' would return:
			[('class', 'PushButtonDraggable'), ('extends', 'QPushButton'), ('header', 'widgets.pushbuttondraggable.h')]
		from:
			<customwidget>
				<class>PushButtonDraggable</class>
				<extends>QPushButton</extends>
				<header>widgets.pushbuttondraggable.h</header>
			</customwidget>

		:parameters:
			file (str) = The full file path to the ui file.
			prop (str) = the property text without its opening and closing brackets. 
								ie. 'customwidget' for the property <customwidget>.
		:return:
			(list) list of tuples (typically one or two element).

		ex. call: getPropertyFromUiFile(file, 'customwidget')
		'''
		f = open(file)
		# print (f.read()) #debugging.
		content = list(f.readlines())

		result = []
		actual_prop_text=''
		for i, l in enumerate(content):

			if l.strip() == '<{}>'.format(prop):
				actual_prop_text = l
				start = i+1
			elif l == tools.Txtools.insert(actual_prop_text, '/', '<'):
				end = i

				delimiters = '</', '<', '>', '\n', ' ',
				regex_pattern = '|'.join(map(re.escape, delimiters))

				lst = [tuple(dict.fromkeys([i for i in re.split(regex_pattern, s) if i])) 
							for s in content[start:end]] #use dict to remove any duplicates.
				result.append(lst)

		f.close()
		return result


	def _getUiLevelFromDir(self, filePath):
		'''Get the UI level by looking for trailing intergers in it's dir name.
		If none are found a default level of 4 (standalone menu) is used.

		level 0: stackedwidget: init (root)
		level 1: stackedwidget: base menus
		level 2: stackedwidget: sub menus
		level 3: main menus
		level 4: popup menus

		:parameters:
			filePath (str) = The directory containing the ui file. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/uiLevel_0/init.ui'

		:return:
			(int)
		'''
		uiFolder = self.formatFilepath(filePath, 'dir')

		try:
			return int(re.findall(r"\d+\s*$", uiFolder)[0]) #get trailing integers.

		except IndexError as error: #not an int.
			return 3


	def _getPrefix(self, widget):
		'''Query a widgets prefix.
		A valid prefix is returned when the given widget's objectName startswith an alphanumeric char, followed by at least three integers. ex. i000 (alphanum,int,int,int)
		
		:parameters:
			widget (str)(obj) = A widget or it's object name.

		:return:
			(str)
		'''
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


	def isWidget(self, obj):
		'''Returns True if the given obj is a valid widget.

		:Parameters:
			obj (obj) = An object to query.

		:Return:
			(bool)
		'''
		try: import shiboken2
		except: from PySide2 import shiboken2

		return hasattr(obj, 'objectName') and shiboken2.isValid(obj)


	def _getWidgetsFromUi(self, ui):
		'''Get all widgets of the given ui.

		:Parameters:
			ui (obj) = A previously loaded dynamic ui object.

		:Return:
			(dict) {<widget>:'objectName'}
		'''
		return [c for c in ui.findChildren(QtCore.QObject, None) 
			if c.objectName() and not c.objectName().startswith('_')]


	def _getWidgetsFromDir(self, path):
		'''Get all widget class objects from a given directory.

		:Parameters:
			path (str) = A filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'

		:Return:
			(list) widgets
		'''
		mod_name = self.formatFilepath(path, 'name')
		path_ = self.formatFilepath(path, 'path')

		self.setWorkingDirectory(path_)
		self.addPluginPath(path_)
		sys.path.append(path_)

		modules={}
		if mod_name: #if the path contains a module name, get only that module.
			mod = importlib.import_module(mod_name)
			cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

			for cls_name, cls_mem in cls_members:
				modules[cls_name] = cls_mem


		else: #get all modules in the given path.
			try:
				_path = os.listdir(path_)
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
			widgets (str)(obj)(list) = A filepath to a dir containing widgets or to the widget itself. 
						ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets' or the widget(s) themselves. 

		ex. call: registerWidgets(<class 'widgets.menu.Menu'>) #register using widget class object.
		ex. call: registerWidgets('O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets/menu.py') #register using path to widget module.
		'''
		for w in self.list_(widgets): #assure widgets is a list.

			if isinstance(w, str):
				[self.registerWidgets(i) for i in self._getWidgetsFromDir(w)]
				continue

			if w in self._registeredWidgets:
				continue

			try:
				self.registerCustomWidget(w)
				self._registeredWidgets.append(w)
				setattr(self, w.__name__, w)

			except Exception as error:
				print ('# Error: {}.registerWidgets(): {} #'.format(__file__, error))


	def getSlotsInstance(self, ui):
		'''Get the class instance of the ui's slots module if it exists.
		'''
		try:
			return ui._slots

		except AttributeError as error:
			class_ = self._importSlots(ui)
			if not class_:
				if ui.isSubmenu:
					return self.getSlotsInstance(ui.level3)

			ui._slots = class_() if class_ else None
			return ui._slots


	def _importSlots(self, ui, slotDir=None):
		'''Import the slot class associated with the given ui.
		ie. <Polygons> class from ui 'polygons',

		:parameters:
			ui (obj) = A previously loaded dynamic ui object.
			slotDir (str) = Specify a parent directory.
					If None is given, the slotDir property will be used.
		:return:
			(obj) class
		'''
		mod_name = '{}_{}'.format(
							self.setCase(ui.name, case='camelCase'), 
							self.setCase(self.appName, case='camelCase'),
							).rstrip('_') #ie. 'polygons_maya' or 'polygons' if appName is None.
		if not slotDir:
			slotDir = self.slotDir
		sys.path.append(slotDir)

		try: #import the module and get the class instance.
			module = importlib.import_module(mod_name)
			class_ = getattr(module, self.setCase(mod_name, case='pascalCase')) #ie. <Polygons_maya> from 'Polygons_maya'
			setattr(class_, 'sb', self)

			return class_ #get the corresponding slot class from the ui name. 

		except ModuleNotFoundError as error:
			return None


	def loadAllUi(self, path=None, widgets=None, parent=None):
		'''Extends the 'loadUi' method to load all ui from a given path.

		:parameters:
			path (str) = The path to the directory containing the ui files to load.
				If no path is given all ui from the default 'uiDir' will be loaded.
			widgets (str)(obj)(list) = A filepath to a dir containing widgets or to the widget itself. 
						ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets' or the widget(s) themselves. 
			parent (obj) = An optional parent widget.

		:return:
			(list) The loaded ui.
		'''
		if path is None:
			path = self.uiDir

		return [self.loadUi(f, widgets, parent) for f in glob.iglob('{}/**/*.ui'.format(path), recursive=True)]


	def loadUi(self, file, widgets=None, parent=None):
		'''Loads a ui from the given path to the ui file.

		:parameters:
			file (str) = The full file path to the ui file.
			widgets (str)(obj)(list) = A filepath to a dir containing widgets or to the widget itself. 
						ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets' or the widget(s) themselves. 
			parent (obj) = An optional parent widget.

		:return:
			(obj) The loaded ui.
		'''
		name = self.formatFilepath(file, 'name')
		path = self.formatFilepath(file, 'path')
		level = self._getUiLevelFromDir(file)

		#register custom widgets
		if widgets is not None:
			self.registerWidgets(widgets)
		else:
			lst = self.getPropertyFromUiFile(file, 'customwidget')
			for l in lst: #get any custom widgets from the ui file.
				try:
					className = l[0][1] #ie. 'PushButtonDraggable' from ('class', 'PushButtonDraggable')
					derivedType = l[1][1] #ie. 'QPushButton' from ('extends', 'QPushButton')
				except IndexError as error:
					continue

				mod_name = self.setCase(className, 'camelCase')
				fullpath = os.path.join(self.widgetDir, mod_name+'.py')
				self.registerWidgets(fullpath)

		#load ui
		ui = self.load(file)
		ui.setParent(parent, ui.windowFlags())

		#set attributes
		setattr(self, name, ui)
		ui.__class__.__slots__ = [
			'name', 'base', 'path', 'tags', 'level', 'sizeX', 'sizeY', 'isConnected', 
			'isSynced', 'isSubmenu', 'preventHide', 'hide', 'addWidgets', 'widgets', 
			'trackedWidgets', 'slots', 'connected', 'sync', 'isCurrent', 'level2', 'level3',
		]
		ui.name = name
		ui.base = next(iter(name.split('_')))
		ui.path = path
		ui.tags = name.split('#')[1:]
		ui.level = level
		ui.sizeX = ui.frameGeometry().width()
		ui.sizeY = ui.frameGeometry().height()
		ui._widgets = []
		ui.isInitialized = False #not handled by this module.
		ui.isConnected = False
		ui.isSynced = False
		ui.isSubmenu = ui.level==2
		ui.preventHide = False
		ui.hide = lambda: None if ui.preventHide else ui.__class__.hide(ui) #ui.setVisible(0) #ui.setVisible(0)
		ui.sync = lambda: self._syncUi(ui)

		#set properties
		ui.__class__.addWidgets = lambda ui, *args, **kwargs: self.addWidgets(ui, *args, **kwargs)

		ui.__class__.widgets = property(
			lambda ui: ui._widgets if ui._widgets else ui.addWidgets()
		)
		ui.__class__.trackedWidgets = property(
			lambda ui: [w for w in ui.widgets if w.isTracked]
		)
		ui.__class__.slots = property(
			lambda ui: self.getSlotsInstance(ui)
		)
		ui.__class__.connected = property(
			lambda ui: True if ui.isConnected else False, 
			lambda ui, state: setattr(self, 'currentUi', ui) if state else self.disconnect(ui)
		)
		ui.__class__.isCurrent = property(
			lambda ui: True if ui==self.currentUi else False
		)
		ui.__class__.level2 = property(
			lambda ui: self.getUi(ui, 2)
		)
		ui.__class__.level3 = property(
			lambda ui: self.getUi(ui, 3)
		)

		self._loadedUi.append(ui)
		return ui


	def addWidgets(self, ui, widgets='all', include=[], exclude=[], filterByBaseType=False, **kwargs):
		'''If widgets is None; the method will attempt to add all widgets from the ui of the given name.

		:parameters:
			ui (obj) = A previously loaded dynamic ui object.
			widgets (list) = A list of widgets to be added. Default: 'all' widgets of the given ui.
			include (list) = Widget types to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Widget types to exclude. ie. ['QWidget', 'QAction', 'QLabel', 'QPushButton', 'QListWidget']
			filterByBaseType (bool) = When using include, or exclude; Filter by base class name, or derived class name. ie. 'QLayout'(base) or 'QGridLayout'(derived)
		'''
		if widgets=='all':
			widgets = self._getWidgetsFromUi(ui) #get all widgets of the ui:

		for w in self.list_(widgets): #assure 'widgets' is a list.

			derivedType = self._getDerivedType(w) #the base class of any custom widgets.  ie. 'QPushButton' from a custom pushbutton widget.
			typ = w.__class__.__base__.__name__ if filterByBaseType else derivedType
			if typ in exclude and (typ in include if include else typ not in include):
				continue

			self.setAttributes(w, **kwargs) #set any passed in keyword args for the widget.

			try:
				name = w.objectName()
			except AttributeError as error: #not a valid widget.
				return

			#set attributes
			ui._widgets.append(w)
			w.__class__.__slots__ = [
				'ui', 'name', 'type', 'derivedType', 'signalType', 'signal', 
				'method', 'prefix', 'isTracked', 'isSynced',
			]
			w.ui = ui
			w.name = name
			w.type = w.__class__.__name__
			w.derivedType = derivedType
			w.signalType = self.getDefaultSignalType(w.derivedType) #get the default signal type for the widget as a string. ie. 'released' from 'QPushButton'
			w.signal = getattr(w, w.signalType, None) #add signal to widget. ie. <widget.valueChanged>
			w.method = getattr(ui.slots, name, None) #use 'name' to get the corresponding method of the same name. ie. method <b006> from widget 'b006' else None
			w.prefix = self._getPrefix(name) #returns an string alphanumberic prefix if name startswith a series of alphanumberic charsinst is followed by three integers. ie. 'cmb' from 'cmb015'
			w.isTracked = True if derivedType in self.trackedWidgets else False
			w.isSynced = False

			# Debug: Print a copy of the _sbdict to console for a visual representation.
			#Some objects in the dict will be converted to strings in order to provide a working test example.
			#ie. <PySide2.QtWidgets.QMainWindow(0x1fa56db6310, name="QtUi") at 0x000001FA29138EC8> becomes: '<PySide2.QtWidgets.QMainWindow(0x1fa56db6310, name="QtUi") at 0x000001FA29138EC8>' 
			# print (self.convertForDebugging(self._sbdict[name]))
			# print (self.convertForDebugging(self._sbdict))

		return ui.widgets	


	def setAttributes(self, obj=None, order=['setVisible'], **kwargs):
		'''Set attributes for a given object.

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

			except AttributeError as error:
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


	def _syncUi(self, submenu, **kwargs):
		'''Extends setSynConnections method to set sync connections 
		for all widgets of the given ui.

		:Parameters:
			ui1 (obj) = 
		'''
		if not submenu.isSubmenu or submenu.isSynced:
			return

		for w1 in submenu.widgets:
			try:
				w2 = getattr(submenu.level3, w1.name)
			except AttributeError as error:
				continue

			self.setSyncConnections(w1, w2, **kwargs)

		submenu.isSynced = True
		submenu.level3.isSynced = True


	def setSyncConnections(self, w1, w2, **kwargs):
		'''Set the initial signal connections that will call the _syncAttributes function on state changes.

		:Parameters:
			w1 (obj) = The first widget to sync.
			w2 (obj) = The second widget to sync.
			kwargs = The attribute(s) to sync as keyword arguments.
		'''
		try:
			s1 = self.defaultSignals[self.getDerivedType(w1)] #get the default signal for the given widget.
			s2 = self.defaultSignals[self.getDerivedType(w2)]

			getattr(w1, s1).connect(lambda: self._syncAttributes(w1, w2, **kwargs))
			getattr(w2, s2).connect(lambda: self._syncAttributes(w2, w1, **kwargs))

			w1.isSynced = True
			w2.isSynced = True

		except AttributeError as error:
			# if w1 and w2: print ('# {}: {}.setSyncConnections({}, {}): {} is invalid.'.format('KeyError' if error==KeyError else 'AttributeError', __name__, w1, w2, error))
			return


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


	def getUi(self, ui=None, level=None):
		'''Get a dynamic ui using its string name, or if no argument is given, return the current ui.

		:Parameters:
			ui (str)(obj)(list) = The ui or name(s) of the ui.
			level (int)(list) = Integer(s) representing the level to include. ex. 2 for submenu, 3 for parent menu, or [2, 3] for both.

		:Return:
			(str)(list) list if multiple levels are given.
		'''
		if not ui:
			ui = self.currentUi

		if level:
			if isinstance(ui, str):
				ui, *tags = ui.split('#')
				ui = self.getUi(ui)
				ui = [u for u in self._loadedUi 
						if all([
							u.base==ui.base, 
							u.tags==self.list_(tags), 
							u.level in self.list_(level),
					])
				]

			else:
				ui = [u for u in self._loadedUi 
						if all([
							u.base==ui.base, 
							u.level in self.list_(level),
					])
				]

			return ui[0] if len(ui)==1 else ui

		elif isinstance(ui, str):
			try:
				if not '_submenu' in ui:
					ui, *tags = ui.split('#')

				return getattr(self, ui)

			except AttributeError as error:
				return None

		elif isinstance(ui, (list, set, tuple)):
			return [self.getUi(u) for u in ui]

		else:
			return ui


	@property
	def currentUi(self) -> object:
		'''Get the current ui.

		:return:
			(obj) ui
		'''
		try:
			return self._currentUi

		except AttributeError as error:
			return None


	@currentUi.setter
	def currentUi(self, ui) -> None:
		'''Register the uiName in history as current and set slot connections.

		:parameters:
			ui (obj) = A previously loaded dynamic ui object.
		'''
		self._currentUi = ui
		self._uiHistory.append(ui)

		self.setConnections(ui)
		ui.sync() #sync submenu widgets with their parent menu counterparts.


	@property
	def prevUi(self):
		'''Get the previous ui from history.
		'''
		return self.getPrevUi()


	def getPrevUi(self, allowDuplicates=False, allowCurrent=False, omitLevel=None, asList=False):
		'''Get ui from history.
		ex. _uiHistory list: ['previousName2', 'previousName1', 'currentName']

		:Parameters:
			allowDuplicates (bool) = Applicable when returning asList. Allows for duplicate names in the returned list.
			omitLevel (int)(list) = Remove instances of the given ui level(s) from the results. Default is [] which omits nothing.
			allowCurrent (bool) = Allow the currentName. Default is off.
			asList (bool) = Returns the full list of previously called names. By default duplicates are removed.

		:Return:
			(str)(list) if 'asList': returns [list of string names]
		'''
		self._uiHistory = self._uiHistory[-200:] #keep original list length restricted to last 200 elements
		hist = self._uiHistory.copy() #work on a copy of the list, keeping the original intact

		if not allowCurrent:
			hist = hist[:-1] #remove the last index. (currentName)

		if not allowDuplicates:
			[hist.remove(u) for u in hist[:] if hist.count(u)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if omitLevel is not None:
			hist = [u for u in hist if not u.level in self.list_(omitLevel)] #remove any items having a ui level of those in the omitLevel list.

		if asList:
			return hist #return entire list after being modified by any flags such as 'allowDuplicates'.
		else:
			try:
				return hist[-1] #return the previous ui name if one exists.
			except:
				return None


	def getWidget(self, name=None, ui=None, tracked=False):
		'''Case insensitive. Get the widget object/s from the given ui and name.

		:Parameters:
			name (str) = The object name of the widget. ie. 'b000'
			ui (str)(obj) = ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
			tracked (bool) = Return only those widgets whose 'isTracked' property is True. 

		:Return:
			(obj) if name:  widget object with the given name from the current ui.
				  if ui and name: widget object with the given name from the given ui name.
			(list) if ui: all widgets for the given ui.
		'''
		if ui is None or isinstance(ui, str):
			ui = self.getUi(ui)

		if name:
			return next((w for w in ui.widgets if (w.isTracked if tracked else True) and w.name==name), None)
		else:
			return [w for w in ui.widgets if (w.isTracked if tracked else True)]


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
		if ui is None or isinstance(ui, str):
			ui = self.getUi(ui)

		typ = 'derivedType' if derivedType else 'type'
		return [w for w in ui.widgets if getattr(w, typ) in self.list_(types)]


	def getWidgetName(self, widget=None, ui=None):
		'''Get the widget's stored string objectName.

		:Parameters:
			widget (obj) = The widget to get the object name of.
					If no widget is given, names of all widgets will be returned.
			ui (str)(obj) = The parent ui, or ui name. ie. <polygons> or 'polygons'
					If no name is given, the current ui will be used.
		:Return:
			(str)(list)
			if widget: (str) the widget objectName for the given widget.
			if ui: the widget objectNames for widgets of the given ui name.
			if not ui: the widget objectNames for widgets of the current ui.
		'''
		if isinstance(ui, (None, str)):
			ui = self.getUi(ui)

		if widget:
			return widget.name

		else: #return all objectNames from ui name.
			return [w.name for w in ui.widgets]


	def getWidgetFromMethod(self, method, existing=None):
		'''Get the corresponding widget from a given method.

		:Parameters:
			method (obj) = The method in which to get the widget of.
			existing (str) = Search only for widgets already existing in the dict (faster).

		:Return:
			(obj) widget. ie. <b000 widget> from <b000 method>.
		'''			
		for u in self._loadedUi:
			for w in u.widgets:
				for m in u.slots:
					if m==method:
						return widget


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
		if isinstance(ui, (None, str)):
			ui = self.getUi(ui)

		if widget is None: #get all methods for the given ui name.
			return [w.method for w in ui.widgets]

		elif isinstance(widget, str):
			return next(iter(w.method for w in ui.widgets if w.method.__name__==widget), None) #if there are event filters attached (as a list), just get the method (at index 0).

		elif not widget in ui.widgets:
			self.addWidgets(ui, widget)

		return next(iter(w.method for w in ui.widgets if w.method==widget.method), None) #if there are event filters attached (as a list), just get the method (at index 0).


	def setConnections(self, ui):
		'''Replace any signal connections of a previous ui with the set for the ui of the given name.

		:Parameters:
			ui (obj) = A previously loaded dynamic ui object.
		'''
		# assert type(ui)!='PySide2.QtWidgets.QMainWindow', '{}: setConnections: incorrect arg type {}'.format(__file__, type(ui))

		prevUi = self.getPrevUi(allowDuplicates=True)
		if prevUi==ui:
			return

		if prevUi and prevUi.connected and prevUi.level<3:
			self.disconnectSlots(prevUi)

		if ui.level<3 or not ui.connected:
			self.connectSlots(ui)


	def connectSlots(self, ui, widgets=None):
		'''Connect signals to slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (obj) = A previously loaded dynamic ui object.
			widgets (obj)(list) = QWidget(s)
		'''
		# print ('connectSlots:', ui.name)
		if widgets is None:
			widgets = ui.widgets

		for w in self.list_(widgets): #convert 'widgets' to a list if it is not one already.
			# print ('           >:', w.name, w.method)
			if w.method and w.signal:
				try:
					if isinstance(w.method, (list, set, tuple)):
						map(w.signal.connect, w.method) #connect to multiple slots from a list.
					else:
						w.signal.connect(w.method) #connect single slot (main and cameras ui)

				except Exception as error:
					print('Error: {0} {1} connectSlots: {2} {3}'.format(ui.name, w.name, w.signal, w.method), '\n', error)

		ui.isConnected = True #set ui state as slots connected.


	def disconnectSlots(self, ui, widgets=None):
		'''Disconnect signals from slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (obj) = A previously loaded dynamic ui object.
			widgets (obj)(list) = QWidget
		'''
		# print ('disconnectSlots:', ui.name)
		if widgets is None:
			widgets = ui.widgets

		for w in self.list_(widgets):  #convert 'widgets' to a list if it is not one already.
			# print ('           >:', w.name, w.method)
			if w.method and w.signal:
				try:
					if isinstance(w.method, (list, set, tuple)):
						w.signal.disconnect() #disconnect all #map(signal.disconnect, slot) #disconnect multiple slots from a list.
					else:
						w.signal.disconnect(w.method) #disconnect single slot (main and cameras ui)

				except Exception as error:
					print('Error: {0} {1} disconnectSlots: {2} {3} #'.format(ui.name, w.name, w.signal, w.method), '\n', error)

		ui.isConnected = False #set ui state as slots disconnected.


	def prevCommand(self, method=False, add=False, asList=False):
		'''Get previous commands and relevant information.

		:Parameters:
			method (bool) = return the method of last command. Default is off.
			add (bool) = Add a command (method) to the list.
			asList (bool) = Return the full list. Not valid with 'asList' flag.

		:Return:
			(obj)(list) method or list ob methods.
		'''
		if add:
			w = self.getWidgetFromMethod(method)
			self.prevCommand(asList=1).append(w) #store the method object and other relevant information about the command.
			return

		self._cmdHistory = self._cmdHistory[-20:] #keep original list length restricted to last 20 elements

		hist = self._cmdHistory
		[hist.remove(l) for l in hist[:] if hist.count(l)>1] #remove any previous duplicates if they exist; keeping the last added element.

		if asList:
			return hist
		try:
			return hist[-1]
		except IndexError as error:
			return None


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









if __name__=='__main__':

	sb = Switchboard()
	sb.loadAllUi()
	ui = sb.polygons #or sb.getUi('polygons')
	sb.setStyle(ui.widgets)

	ui.connected = True
	print ('current ui:', sb.currentUi.name)
	print ('connected state:', ui.connected) #or ui.isConnected
	# print ('widgets:', ui.widgets)
	print ('slot:', ui.tb000.method)
	print ('mainWindow:', ui.mainWindow)

	ui.show()

	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	sys.exit(qApp.exec_())









print (__name__) #module name
# -----------------------------------------------
# Notes
# -----------------------------------------------

# deprecated:


	# def _formatName(self, name, level=None):
	# 	'''
	# 	'''
	# 	assert isinstance(name, str), '{}: _formatName: name argument given as: {} {}'.format(__file__, name, type(name))

	# 	if level==2:
	# 		n, *tags = name.replace('_submenu', '').split('#', 1)
	# 		tags = '#'+'#'.join(tags) if tags else ''
	# 		name = '{}_submenu{}'.format(n, tags)

	# 	elif level==3 and '#' in name:
	# 		name = name.split('#', 1)[0]

	# 	elif level==0 or level==1:
	# 		name = name.split('_')[0].split('#', 1)[0]

	# 	return name


	# def _getUiName(self, ui, level):
	# 	'''Get the ui name at the given level(s).

	# 	:Parameters:
	# 		ui (obj) = A previously loaded dynamic ui object.
	# 		level (int)(list) = Integer(s) representing the level to include.
	# 					ie. 2 for submenu, 3 for main_menu, or [2, 3] for both.
	# 	:Return:
	# 		(str)(list) list if multiple levels are given.
	# 	'''
	# 	assert ui!=None, '{}: _getUiName: ui argument given as: {} {}'.format(__file__, ui, type(ui))

	# 	return_asList = isinstance(level, (list, tuple, set))

	# 	result = []
	# 	for lvl in self.list_(level):
	# 		attr = '_level{}'.format(lvl)
	# 		try:
	# 			name = getattr(ui, attr)

	# 		except AttributeError as error:

	# 			f = self._formatName(ui.name, lvl)
	# 			if lvl==4:
	# 				name = [u.name for u in self._loadedUi if all([f.split('_')[0]==u.name.split('_')[0], u.level==lvl])]
	# 			else:
	# 				n = [u.name for u in self._loadedUi if all([f==u.name, u.level==lvl])]

	# 			name = n[0] if isinstance(n, list) and len(n)==1 else n
	# 			setattr(ui, attr, name)

	# 		result.append(name)

	# 	if return_asList:
	# 		return self.list_(result)
	# 	else:
	# 		return result[0] if result else None