# !/usr/bin/python
# coding=utf-8
import os, sys
import re
import glob
import importlib
import inspect

from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtUiTools import QUiLoader

from pythontk import File, Str, Iter, setAttributes
from uitk.styleSheet import StyleSheet


class Switchboard(QUiLoader, StyleSheet):
	'''Load dynamic ui and assign properties.

	:Properties:
		sb = The property 'sb' is automatically passed to all slot class instances, sb is the instance of this class holding all of the properties below. ex. sb.ui.widgets
		sb.<uiFileName> = Any ui located in the switchboard's ui directory can be accessed using it's filename.
		sb.<customWidgetClassName> = Any of the custom widgets in the widget directory.

		ui = sb.<the_ui's_filename> #ie `myfile` from `myfile.ui` or sb.currentUi
		ui.name = The ui's filename.
		ui.base = The base ui name. The base name is any characters before an underscore in the ui's name.
		ui.path = The directory path containing the ui file.
		ui.tags = Any ui tags as a list. Tags are trailing strings in the ui name preceeded by a hashtag used to define special behaviors.
		ui.level = The ui level. 0: init (root), 1: base menus, 2: sub menus, 3: parent menus, 4: popup menus
		ui.sizeX = The original width of the ui.
		ui.sizeY = The original hight of the ui.
		ui.level2 = The submenu for the ui (level 2).
		ui.level3 = The parent menu of the ui (level 3).
		ui.isCurrentUi = True if the ui is set as current.
		ui.isSubmenu = True if the ui is a submenu (level 2).
		ui.isInitialized = A convenience property not handled by this module. Can be used to mark the ui as initialized in the main app.
		ui.connected = True if the ui is connected. If set to True, the ui will be set as current and connections established.
		ui.isConnected = True if the ui is connected to it's slots.
		ui.isSynced = True if the ui is synced. When set to True any submenu widgets will be synced with their parent menu's counterparts.
		ui.connectOnShow = While True the ui will be set as current on show.
		ui.show = An override of the built-in hide method.
		ui.preventHide = While True the hide method is disabled.
		ui.hide = An override of the built-in hide method.
		ui.addWidgets = (function) add widgets to the ui.
		ui.widgets = All the widgets of the ui.
		ui.slots = The slots class instance.

		w = ui.<theWidgetsObjectName> #ie. widgetname from 
		w.ui = Access the widget's parent ui (QMainWindow).
		w.name = The widget's object name.
		w.type = The widget's class name.
		w.derivedType = A custom widget's derived class name.
		w.signals = The signal. ie. <widget.valueChanged>. Used when establishing connections.
		w.method = The corresponding method of the slot's class of the same name as the widget's object name. ie. method <b006> from widget 'b006' else None
		w.prefix = The alphanumberic string prefix determining widget type. If the widget name starts with a series of alphanumberic chars and is followed by three integers. ie. 'cmb' from 'cmb015'
		w.isSynced = True if the widget is being synced between submenu and it's parent menu.

	Example:
		sb.ui.w.isSynced #written as: sb.<theUisFileName>.<theWidgetsObjectName>.isSynced

	Example of a single ui with the slots pointing to a subclass (named `SomeClass_slots`) in the same module as the main app ('.

		class SomeClass_main(QtWidgets.QObject):
			"""SomeClass is subclassed from a QObject so that it can be properly parented to `Switchboard`.
			"""
			def __init__(self, parent=None):
				super().__init__(parent)

				sb = Switchboard(self, widgetLoc='location/of/your/custom/widgets', slotLoc=Map_compositor_slots) #see directory descriptions in the __init__ docstring below.
				ui = sb.some_ui #will load and return the ui with filename 'some_ui'
				sb.setStyle(ui.widgets) #set the stylesheet for the ui's widgets.
				ui.show()

				sys.exit(sb.app.exec_())
	'''
	defaultSignals = { #the signals to be connected per widget type. Values can be a list or a single item string.
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
		'QLineEdit':['editingFinished'],
		'QTextEdit':'textChanged',
		'QSlider':'sliderMoved',
		'QProgressBar':'valueChanged',
	}

	def __init__(self, parent=None, uiLoc='', widgetLoc='', slotLoc='', preloadUi=False):
		super().__init__(parent)
		'''
		:Parameters:
			parent (obj): A QtObject derived class.
			uiLoc (str)(obj): Set the directory of the dynamic ui, or give the dynamic ui objects.
			widgetLoc (str)(obj): Set the directory of any custom widgets, or give the widget objects.
			slotLoc (str)(obj): Set the directory of where the slot classes will be imported, or give the slot class itself.
			preloadUi (bool): Load all ui immediately. Otherwise ui will be loaded as required.

			When a parent is given; the 'defaultDir' attribute is the parent module's directory. 
			When no parent is given; the directory of this module will be used.
			If any of the given filepaths are not a full path, it will be treated as relative to the currently set path.
			#in following example; since no paths have been set, the default directory is used, and an 
			argument given as: slotLoc='maya' is treated as a relative path: '<sb.defaultDir>/maya'
		'''
		self.defaultDir = File.getFilepath(parent) or File.getFilepath(__file__) #use the filepath from the parent class if a parent is given.

		self.uiLoc = uiLoc
		self.widgetLoc = widgetLoc
		self.slotLoc = slotLoc

		self._loadedUi = []
		self._registeredWidgets = []
		self._uiHistory = []
		self._wgtHistory = []
		self._gcProtect = set()

		if preloadUi:
			self.loadAllUi()


	def __getattr__(self, attr):
		'''If an unknown attribute matches the name of a ui in the current ui directory; load and return it.
		Else, if an unknown attribute matches the name of a custom widget in the widgets directory; register and return it.
		If no match is found raise an attribute error.

		:Return:
			(obj) ui or widget else raise attribute error.
		'''
		#when an unknown attribute is encountered, first look for a ui of that name:
		uiPath = File.formatPath(self.uiLoc, 'path') #will return an empty list on incorrect datatype.
		foundUi = next((f for f in glob.iglob(f'{uiPath}/**/{attr}.ui', recursive=True)), None)
		if foundUi:
			ui = self.loadUi(foundUi) #load the dynamic ui file.
			if not ui:
				print (f'# Error: {__file__} in __getattr__ (loadUi)\n#\tUnable to load {attr}({type(attr).__name__})')
			return ui

		#if no ui is found, check if a widget exists with the given attribute name:
		wgtPath = File.formatPath(self.widgetLoc, 'path') #will return an empty list on incorrect datatype.
		wgtName = Str.setCase(attr, 'camel')
		foundWgt = next((f for f in glob.iglob(f'{wgtPath}/**/{wgtName}.py', recursive=True)), None)
		if foundWgt:
			wgt = self.registerWidgets(attr)
			if not wgt:
				print (f'# Error: {__file__} in __getattr__ (registerWidgets)\n#\tUnable to register {attr}({type(attr).__name__})')
			return wgt

		raise AttributeError(f'# Error: {__file__} in __getattr__\n#\t{self.__class__.__name__} has no attribute {attr}({type(attr).__name__})')


	def hasattr_static(self, attr):
		'''Check if this class has an attribute, without calling '__getattr__'.
		
		:Parameters:
			attr (str): The name of the attribute in which to query.

		:Return:
			(bool)
		'''
		try:
			inspect.getattr_static(self, attr)
			return True
		except AttributeError as error:
			return False


	@property
	def uiLoc(self) -> str:
		'''Get the directory where the dynamic ui are stored.

		:Return:
			(str) directory path.
		'''
		
		if not self.hasattr_static('_uiLoc'):
			self._uiLoc = self.defaultDir
			return self._uiLoc
		return self._uiLoc


	@uiLoc.setter
	def uiLoc(self, d) -> None:
		'''Set the directory where the dynamic ui are located.

		:Parameters:
			d (str): The directory path where the dynamic ui are located.
				If the given dir is not a full path, it will be treated as relative to the default path.
		'''
		if isinstance(d, str):
			isAbsPath = os.path.isabs(d)
			self._uiLoc = d if isAbsPath else os.path.join(self.defaultDir, d) #if the given dir is not a full path, treat it as relative to the default path.
		else: #store object.
			self._uiLoc = d


	@property
	def widgetLoc(self) -> str:
		'''Get the directory where any custom widgets are stored.

		:Return:
			(str) directory path.
		'''
		if not self.hasattr_static('_widgetLoc'):
			self._widgetLoc = self.defaultDir
			return self._widgetLoc
		return self._widgetLoc


	@widgetLoc.setter
	def widgetLoc(self, d) -> None:
		'''Set the directory where any custom widgets are stored.

		:Parameters:
			d (str): The directory path where any custom widgets are located.
				If the given dir is not a full path, it will be treated as relative to the default path.
		'''
		if isinstance(d, str):
			isAbsPath = os.path.isabs(d)
			self._widgetLoc = d if isAbsPath else os.path.join(self.defaultDir, d) #if the given dir is not a full path, treat it as relative to the default path.
		else: #store object.
			self._widgetLoc = d


	@property
	def slotLoc(self) -> str:
		'''Get the directory where the slot classes will be imported from.

		:Return:
			(str)(obj) slots class directory path or slots class object.
		'''
		try:
			return self._slotLoc

		except AttributeError as error:
			self._slotLoc = self.defaultDir
			return self._slotLoc


	@slotLoc.setter
	def slotLoc(self, d) -> None:
		'''Set the directory where the slot classes will be imported from.

		:Parameters:
			d (str): The directory path where the slot classes are located.
				If the given dir is not a full path, it will be treated as relative to the default path.
		'''
		if isinstance(d, str):
			isAbsPath = os.path.isabs(d)
			self._slotLoc = d if isAbsPath else os.path.join(self.defaultDir, d) #if the given dir is not a full path, treat it as relative to the default path.
		else: #store object.
			self._slotLoc = d


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

		:Parameters:
			file (str): The full file path to the ui file.
			prop (str): the property text without its opening and closing brackets. 
								ie. 'customwidget' for the property <customwidget>.
		:Return:
			(list) list of tuples (typically one or two element).

		:Example: getPropertyFromUiFile(file, 'customwidget')
		'''
		f = open(file)
		# print (f.read()) #debug
		content = list(f.readlines())

		result = []
		actual_prop_text=''
		for i, l in enumerate(content):

			if l.strip() == '<{}>'.format(prop):
				actual_prop_text = l
				start = i+1
			elif l == Str.insert(actual_prop_text, '/', '<'):
				end = i

				delimiters = '</', '<', '>', '\n', ' ',
				regex_pattern = '|'.join(map(re.escape, delimiters))

				lst = [tuple(dict.fromkeys([i for i in re.split(regex_pattern, s) if i])) 
							for s in content[start:end]] #use dict to remove any duplicates.
				result.append(lst)

		f.close()
		return result


	@staticmethod
	def _getUiLevelFromDir(filePath):
		'''Get the UI level by looking for trailing intergers in it's dir name.
		If none are found a default level of 3 (main menu) is used.

		level 0: stackedwidget: init (root)
		level 1: stackedwidget: base menus
		level 2: stackedwidget: sub menus
		level 3: main menus
		level 4: popup menus

		:Parameters:
			filePath (str): The directory containing the ui file. ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/uiLevel_0/init.ui'

		:Return:
			(int)
		'''
		uiFolder = File.formatPath(filePath, 'dir')

		try:
			return int(re.findall(r"\d+\s*$", uiFolder)[0]) #get trailing integers.

		except IndexError as error: #not an int.
			return 3


	@staticmethod
	def _getPrefix(widget):
		'''Query a widgets prefix.
		A valid prefix is returned when the given widget's objectName startswith an alphanumeric char, 
		followed by at least three integers. ex. i000 (alphanum,int,int,int)

		:Parameters:
			widget (str)(obj): A widget or it's object name.

		:Return:
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


	@staticmethod
	def _getWidgetsFromUi(ui, inc=[], exc='_*', objectNamesOnly=True):
		'''Get all widgets of the given ui.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			inc (str)(tuple): Widget names to include.
			exc (str)(tuple): Widget names to exclude.
			objectNamesOnly (bool): Only include widgets with object names.

		:Return:
			(dict) {<widget>:'objectName'}
		'''
		dct = {c:c.objectName() for c in ui.findChildren(QtCore.QObject, None) 
			if (not objectNamesOnly or c.objectName())}
		return Iter.filterDict(dct, inc, exc, values=True)


	def _getWidgetsFromDir(self, path):
		'''Get all widget class objects from a given directory.

		:Parameters:
			path (str): A filepath to a dir containing widgets or to the widget itself, 
					or the name of a widget residing in the 'widgetLoc'. 
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets'
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets/comboBox.py'
						ie. 'ComboBox'
		:Return:
			(list) widgets
		'''
		mod_name = File.formatPath(path, 'name')

		if not File.isValidPath(path):
			mod_name = Str.setCase(mod_name, 'camel')
			path = os.path.join(self.widgetLoc, f'{mod_name}.py')

		path_ = File.formatPath(path, 'path')

		self.setWorkingDirectory(path_) #set QUiLoader working paths.
		self.addPluginPath(path_)
		sys.path.append(path_)

		modules={}
		if mod_name: #if the path contains a module name, get only that module.
			try:
				mod = importlib.import_module(mod_name)
			except ModuleNotFoundError as error:
				print (f"# Error: {__file__} in _getWidgetsFromDir: #\n\t{mod_name} not found.\n\tConfirm that the following \'widgetLoc\' path is correct:\n\t{path_}")
				return []
			cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

			for cls_name, cls_mem in cls_members:
				modules[cls_name] = cls_mem

		else: #get all modules in the given path.
			try:
				_path = os.listdir(path_)
			except FileNotFoundError as error:
				print (f"# Error: {__file__} in _getWidgetsFromDir: #\n\t{mod_name} not found.\n\tConfirm that the following \'widgetLoc\' path is correct:\n\t{path_}")
				return []

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

		widgets = [w for w in modules.values() if type(w).__name__=='ObjectType' and self.isWidget(w)] #get all imported widget classes as a list.
		return widgets


	def setSlots(self, ui, clss):
		'''Explicitly set the slot class for a given ui.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			clss (obj): A class or class instance to set as the slots location for the given ui. 

		:Return:
			(obj) class instance.
		'''
		if inspect.isclass(clss):
			setattr(clss, 'sb', self)
			ui._slots = clss() if callable(clss) else clss

			return ui._slots
		return None


	def getSlots(self, ui, persist=False):
		'''Get the class instance of the ui's slots module if it exists.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			persist (bool): Do not assign the ui's slots attribute a None value when a class is not found.

		:Return:
			(obj) class instance.
		'''
		try:
			# print ('getSlots:1', ui.name, ui._slots, inspect.isclass(ui._slots), self.slotLoc) #debug
			return ui._slots

		except AttributeError as error:
			if isinstance(self.slotLoc, str):
				clss = self._importSlots(ui)
			else: #if slotLoc is a class object:
				clss = self.slotLoc
			# print ('getSlots:2', ui.name, clss, inspect.isclass(clss), self.slotLoc) #debug
			if not clss:
				if ui.isSubmenu:
					if ui.level3: #is a submenu that has a parent menu.
						return self.getSlots(ui.level3)
					elif ui.level1:
						return self.getSlots(ui.level1)
		if clss and inspect.isclass(clss):
			return self.setSlots(ui, clss)
		elif not persist:
			ui._slots = None
		return None


	def _importSlots(self, ui, path=None, recursive=True):
		'''Import the slot class associated with the given ui.
		ie. get <Polygons> class using ui name 'polygons'

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			path (str): The directory location of the module.
					If None is given, the slotLoc property will be used.
			recursive (bool): Search subfolders of the given path.

		:Return:
			(obj) class
		'''
		assert isinstance(ui, QtWidgets.QMainWindow), 'Incorrect datatype: {}: {}'.format(type(ui), ui)

		d = File.formatPath(self.slotLoc, 'dir')
		suffix = '' if d=='slots' else d

		mod_name = '{}_{}'.format(
							Str.setCase(ui.name, case='camel'), 
							Str.setCase(suffix, case='camel'),
							).rstrip('_') #ie. 'polygons_maya' or 'polygons' if suffix is None.
		if not path:
			if isinstance(self.slotLoc, str):
				path = self.slotLoc
			else:
				path = self.defaultDir
		path = next((f for f in glob.iglob('{}/**/{}.py'.format(path, mod_name), recursive=recursive)), None)
		if path:
			try: #import the module and return the slots class object.
				spec = importlib.util.spec_from_file_location(mod_name, path) #mod_name: ie. 'polygons_maya'. path: ie. 'full\path\to\maya/polygons_maya.py'
				mod = importlib.util.module_from_spec(spec)
				sys.modules[spec.name] = mod
				spec.loader.exec_module(mod)

				cls_name = Str.setCase(mod_name, case='pascal')
				try:
					clss = getattr(mod, cls_name)
				except AttributeError as error: #if a class by the same name as the module doesn't exist: (ex. <Polygons_maya> from module 'polygons_maya')
					clsmembers = inspect.getmembers(mod, inspect.isclass)
					clss = clsmembers[0][1] #just get the first class.
					print (f'# Warning: {__file__} in _importSlots\n#\t{error}.\n#\tUsing {clss} instead.')
				return clss

			except (FileNotFoundError, ModuleNotFoundError) as error:
				print (f'# Error: {__file__} in _importSlots\n#\t{error}.')
		return None


	def registerWidgets(self, widgets):
		'''Register any custom widgets using the module names.
		Registered widgets can be accessed as properties. ex. sb.PushButton()

		:Parameters:
			widgets (str)(obj)(list): A filepath to a dir containing widgets or to the widget itself. 
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets' or the widget(s) themselves. 

		:Return:
			(obj)(list) list if widgets given as a list.

		:Example: registerWidgets(<class 'widgets.menu.Menu'>) #register using widget class object.
		:Example: registerWidgets('O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets/menu.py') #register using path to widget module.
		'''
		result=[]
		for w in Iter.makeList(widgets): #assure widgets is a list.

			if isinstance(w, str):
				widgets_ = self._getWidgetsFromDir(w)
				for i in widgets_:
					w_ = self.registerWidgets(i)
					result.append(w_)
				continue

			if w in self._registeredWidgets:
				continue

			try:
				self.registerCustomWidget(w)
				self._registeredWidgets.append(w)
				setattr(self, w.__name__, w)
				result.append(w)

			except Exception as error:
				print (f'# Error: {__file__} in registerWidgets\n#\t{error}.')

		return Iter.formatReturn(result, widgets) #if 'widgets' is given as a list; return a list.


	def loadAllUi(self, path=None, widgets=None, parent=None):
		'''Extends the 'loadUi' method to load all ui from a given path.

		:Parameters:
			path (str): The path to the directory containing the ui files to load.
				If no path is given all ui from the default 'uiLoc' will be loaded.
			widgets (str)(obj)(list): A filepath to a dir containing widgets or to the widget itself. 
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets' or the widget(s) themselves.
			parent (obj): An optional parent widget.

		:Return:
			(list) QMainWindow object(s).
		'''
		if path is None:
			path = self.uiLoc

		files = glob.iglob('{}/**/*.ui'.format(path), recursive=True)
		return [self.loadUi(f, widgets, parent) for f in files]


	def loadUi(self, file, widgets=None, parent=None):
		'''Loads a ui from the given path to the ui file.

		:Parameters:
			file (str): The full file path to the ui file.
			widgets (str)(obj)(list): A filepath to a dir containing widgets or the widget(s) itself.
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets' or the widget(s) themselves.
			parent (obj): An optional parent widget.

		:Return:
			(obj) QMainWindow object.
		'''
		name = File.formatPath(file, 'name')
		path = File.formatPath(file, 'path')
		level = self._getUiLevelFromDir(file)

		#register custom widgets
		if widgets is None and not isinstance(self.widgetLoc, str): #widget objects defined in widgetLoc.
			widgets = self.widgetLoc
		if widgets is not None: #widgets given explicitly or defined in widgetLoc.
			self.registerWidgets(widgets)
		else: #search for and attempt to load any widget dependancies using the path defined in widgetLoc.
			lst = self.getPropertyFromUiFile(file, 'customwidget')
			for l in lst: #get any custom widgets from the ui file.
				try:
					className = l[0][1] #ie. 'PushButtonDraggable' from ('class', 'PushButtonDraggable')
					derivedType = l[1][1] #ie. 'QPushButton' from ('extends', 'QPushButton')
				except IndexError as error:
					continue

				mod_name = Str.setCase(className, 'camel')
				fullpath = os.path.join(self.widgetLoc, mod_name+'.py')
				self.registerWidgets(fullpath)
		#load ui
		ui = self.load(file)
		if parent:
			ui.setParent(parent, ui.windowFlags())

		#set attributes
		ui.__slots__ = [
			'name', 'base', 'path', 'tags', 'level', 'connected', 'isConnected', 'isInitialized',
			'isCurrentUi', 'isSubmenu', 'sync', 'isSynced', 'hide', 'preventHide', 'show', 'connectOnShow',
			'addWidgets', 'widgets', '_widgets', 'slots', '_slots', 'sizeX', 'sizeY',
			'level0', 'level1', 'level2', 'level3', 'level4',
		]
		ui.name = name
		ui.base = next(iter(name.split('_')))
		ui.path = path
		ui.tags = name.split('#')[1:]
		ui.level = level
		ui.sizeX = ui.frameGeometry().width()
		ui.sizeY = ui.frameGeometry().height()
		ui._widgets = []
		ui.isInitialized = False #a convenience property not handled by this module.
		ui.isConnected = False
		ui.isSynced = False
		ui.isSubmenu = ui.level==2
		ui.preventHide = False
		ui.connectOnShow = True

		ui.show = lambda u=ui: self.showAndConnect(u, u.connectOnShow)
		ui.hide = lambda u=ui: None if u.preventHide else u.__class__.hide(u)
		ui.sync = lambda u=ui: self._syncUi(u)

		#set properties
		ui.__class__.addWidgets = lambda u, *args, **kwargs: self.addWidgets(u, *args, **kwargs)

		ui.__class__.widgets = property(
			lambda u: u._widgets or u.addWidgets()
		)
		ui.__class__.slots = property(
			lambda u: self.getSlots(u)
		)
		ui.__class__.connected = property(
			lambda u: u.isConnected, 
			lambda u, state: setattr(self, 'currentUi', u) if state else self.disconnect(u)
		)
		ui.__class__.isCurrentUi = property(
			lambda u: u==self.currentUi
		)
		ui.__class__.level0 = property(
			lambda u: self.getUi(u, 0)
		)
		ui.__class__.level1 = property(
			lambda u: self.getUi(u, 1)
		)
		ui.__class__.level2 = property(
			lambda u: self.getUi(u, 2)
		)
		ui.__class__.level3 = property(
			lambda u: self.getUi(u, 3)
		)
		ui.__class__.level4 = property(
			lambda u: self.getUi(u, 4)
		)

		setattr(self, name, ui) #set ui name as attribute so that the ui can be accessed as: self.<ui_name> which returns the <ui> object.
		self._loadedUi.append(ui)
		return ui


	def addWidgets(self, ui, widgets='all', inc=[], exc=[], filterByBaseType=False, **kwargs):
		'''If widgets is None; the method will attempt to add all widgets from the ui of the given name.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			widgets (list): A list of widgets to be added. Default: 'all' widgets of the given ui.
			inc (list): Widget types to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exc (list): Widget types to exclude. ie. ['QWidget', 'QAction', 'QLabel', 'QPushButton', 'QListWidget']
			filterByBaseType (bool): When using `inc`, or `exc`; Filter by base class name, or derived class name. ie. 'QLayout'(base) or 'QGridLayout'(derived)
		'''
		if widgets=='all':
			widgets = self._getWidgetsFromUi(ui) #get all widgets of the ui:

		for w in Iter.makeList(widgets): #assure 'widgets' is a list.

			derivedType = self.getDerivedType(w, name=True) #the base class of any custom widgets.  ie. 'QPushButton' from a custom pushbutton widget.
			typ = w.__class__.__base__.__name__ if filterByBaseType else derivedType
			if typ in exc and (typ in inc if inc else typ not in inc):
				continue

			setAttributes(w, **kwargs) #set any passed in keyword args for the widget.

			try:
				name = w.objectName()
			except AttributeError as error: #not a valid widget.
				return

			#set attributes
			w.__slots__ = [
				'ui', 'name', 'type', 'derivedType', 'signals', 
				'method', 'prefix', 'isSynced',
			]
			w.ui = ui
			w.name = name
			w.type = w.__class__.__name__
			w.derivedType = derivedType
			w.signals = self.getDefaultSignals(w) #default widget signals as list. ie. [<widget.valueChanged>]
			w.prefix = self._getPrefix(name) #returns an string alphanumberic prefix if name startswith a series of alphanumberic charsinst is followed by three integers. ie. 'cmb' from 'cmb015'
			w.isSynced = False
			w.__class__.method = property(lambda w=w: getattr(w.ui.slots, w.name, None))
			ui._widgets.append(w)
		return ui.widgets


	def getUi(self, ui=None, level=None):
		'''Get a dynamic ui using its string name, or if no argument is given, return the current ui.

		:Parameters:
			ui (str)(obj)(list): The ui or name(s) of the ui.
			level (int)(list): Integer(s) representing the level to include. ex. 2 for submenu, 3 for parent menu, or [2, 3] for both.

		:Return:
			(str)(list) list if 'levels' given as a list.
		'''
		if not ui:
			ui = self.currentUi

		if level:
			if isinstance(ui, str):
				ui, *tags = ui.split('#')

				ui1 = self.getUi(ui)
				if not ui1 or level==2:
					submenu_name = '{}_{}#{}'.format(ui, 'submenu', '#'.join(tags)).rstrip('#') #reformat as submenu w/tags. ie. 'polygons_submenu#edge' from 'polygons'
					ui1 = self.getUi(submenu_name) #in the case where a submenu exist without a parent menu.
					if not ui1:
						print (f'# Error: {__file__} in getUi\n#\tUI not found: {ui}({type(ui).__name__})\n#\tConfirm the following ui path is correct\n#\t{self.uiLoc}')
						return None

				ui = [u for u in self._loadedUi 
						if all([
							u.base==ui1.base, 
							u.tags==Iter.makeList(tags), 
							u.level in Iter.makeList(level),
						])
				]

			else:
				ui = [u for u in self._loadedUi 
						if all([
							u.base==ui.base, 
							u.level in Iter.makeList(level),
						])
				]

			return Iter.formatReturn(ui, level) #if 'level' is given as a list; return a list.

		elif isinstance(ui, str):
			try:
				if not '_submenu' in ui:
					ui, *tags = ui.split('#')

				return getattr(self, ui)

			except AttributeError as error:
				print (f'# Error: {__file__} in getUi\n#\tUI not found: {ui}({type(ui).__name__})\n#\tConfirm the following ui path is correct\n#\t{self.uiLoc}')
				return None

		elif isinstance(ui, (list, set, tuple)):
			return [self.getUi(u) for u in ui]

		else:
			return ui


	def showAndConnect(self, ui, connectOnShow=True):
		'''Register the uiName in history as current, 
		set slot connections, and show the given ui.
		An override for the built-in show method.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			connectOnShow (bool): The the ui as connected.
		'''
		if connectOnShow:
			ui.connected = True
		ui.__class__.show(ui)


	@property
	def currentUi(self) -> object:
		'''Get the current ui.

		:Return:
			(obj) ui
		'''
		try:
			return self._currentUi

		except AttributeError as error:
			if len(self._loadedUi)==1: #in the case where there is only one ui loaded, and current ui is queried, set the ui as current.
				ui = self._loadedUi[0]
				self.currentUi = ui
				return self._currentUi
			return None


	@currentUi.setter
	def currentUi(self, ui) -> None:
		'''Register the uiName in history as current and set slot connections.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
		'''
		try:
			if self._currentUi==ui:
				return
		except AttributeError as error:
			pass

		# print ('set current ui:', ui.name, id(self), locals()) #debug
		self._currentUi = ui
		self._uiHistory.append(ui)
		# print ('_uiHistory:', [u.name for u in self._uiHistory]) #debug

		self.setConnections(ui)
		ui.sync() #sync submenu widgets with their parent menu counterparts.


	@property
	def prevUi(self) -> object:
		'''Get the previous ui from history.

		:Return:
			(obj)
		'''
		return self.getPrevUi()


	def getPrevUi(self, allowDuplicates=False, allowCurrent=False, omitLevel=None, asList=False):
		'''Get ui from history.
		ex. _uiHistory list: ['previousName2', 'previousName1', 'currentName']

		:Parameters:
			allowDuplicates (bool): Applicable when returning asList. Allows for duplicate names in the returned list.
			omitLevel (int)(list): Remove instances of the given ui level(s) from the results. Default is [] which omits nothing.
			allowCurrent (bool): Allow the currentName. Default is off.
			asList (bool): Returns the full list of previously called names. By default duplicates are removed.

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
			hist = [u for u in hist if not u.level in Iter.makeList(omitLevel)] #remove any items having a ui level of those in the omitLevel list.

		if asList:
			return hist #return entire list after being modified by any flags such as 'allowDuplicates'.
		else:
			try:
				return hist[-1] #return the previous ui name if one exists.
			except:
				return None


	@property
	def prevCommand(self) -> object:
		'''Get the last called slot method.

		:Return:
			(obj) method.
		'''
		try:
			return self.prevCommands[-1]

		except IndexError as error:
			return None


	@property
	def prevCommands(self) -> list:
		'''Get a list of previously called slot methods.

		:Return:
			(list) list of methods.
		'''
		cmds = [w.method for w in self._wgtHistory[-10:]] #limit to last 10 elements and get methods from widget history.
		hist = list(dict.fromkeys(cmds[::-1]))[::-1] #remove any duplicates (keeping the last element). [hist.remove(l) for l in hist[:] if hist.count(l)>1] #

		return hist


	@staticmethod
	def getDerivedType(widget, name=False, module='PySide2.QtWidgets'):
		'''Get the base class of a custom widget.
		If the type is a standard widget, the derived type will be that widget's type.

		:Parameters:
			widget (str)(obj): QWidget or it's objectName.
			name (bool): Return the class or the class name.
			module (str): The base class module to check for.

		:Return:
			(obj)(string) class or class name if `name`. ie. 'QPushButton' from a custom widget with class name: 'PushButton'
		'''
		# print(widget.__class__.__mro__) #debug
		for c in widget.__class__.__mro__:
			if c.__module__==module: #check for the first built-in class.
				return c.__name__ if name else c


	def getWidget(self, name, ui=None):
		'''Case insensitive. Get the widget object/s from the given ui and name.

		:Parameters:
			name (str): The object name of the widget. ie. 'b000'
			ui (str)(obj): ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
		:Return:
			(obj) if name:  widget object with the given name from the current ui.
				  if ui and name: widget object with the given name from the given ui name.
			(list) if ui: all widgets for the given ui.
		'''
		if ui is None or isinstance(ui, str):
			ui = self.getUi(ui)

		return next((w for w in ui.widgets if w.name==name), None)


	def getWidgetsByType(self, types, ui=None, derivedType=False):
		'''Get widgets of the given types.

		:Parameters:
			types (str)(list): A widget class name, or list of widget class names. ie. 'QPushbutton' or ['QPushbutton', 'QComboBox']
			ui (str)(obj): Parent ui name, or ui object. ie. 'polygons' or <polygons>
							If no name is given, the current ui will be used.
			derivedType (bool): Get by using the parent class of custom widgets.

		:Return:
			(list)
		'''
		if ui is None or isinstance(ui, str):
			ui = self.getUi(ui)

		typ = 'derivedType' if derivedType else 'type'
		return [w for w in ui.widgets if getattr(w, typ) in Iter.makeList(types)]


	def getWidgetName(self, widget=None, ui=None):
		'''Get the widget's stored string objectName.

		:Parameters:
			widget (obj): The widget to get the object name of.
					If no widget is given, names of all widgets will be returned.
			ui (str)(obj): The parent ui, or ui name. ie. <polygons> or 'polygons'
					If no name is given, the current ui will be used.
		:Return:
			(str)(list)
			if widget: (str) the widget objectName for the given widget.
			if ui: the widget objectNames for widgets of the given ui name.
			if not ui: the widget objectNames for widgets of the current ui.
		'''
		if not isinstance(ui, QtWidgets.QMainWindow):
			ui = self.getUi(ui)

		if widget:
			return widget.name

		else: #return all objectNames from ui name.
			return [w.name for w in ui.widgets]


	def getWidgetFromMethod(self, method):
		'''Get the corresponding widget from a given method.

		:Parameters:
			method (obj): The method in which to get the widget of.

		:Return:
			(obj) widget. ie. <b000 widget> from <b000 method>.
		'''
		if not method:
			return None

		return next(iter(w for u in self._loadedUi for w in u.widgets if w.method==method), None)


	def getMethod(self, ui, widget=None):
		'''Get the method(s) associated with the given ui / widget.

		:Parameters:
			ui (str)(obj): The ui name, or ui object. ie. 'polygons' or <polygons>
			widget (str)(obj): widget, widget's objectName, or method name.

		:Return:
			if widget: corresponding method object to given widget.
			else: all of the methods associated to the given ui name as a list.

		ex. sb.getMethod('polygons', <b022>)() #call method <b022> of the 'polygons' class
		'''
		if not isinstance(ui, QtWidgets.QMainWindow):
			ui = self.getUi(ui)

		if widget is None: #get all methods for the given ui name.
			return [w.method for w in ui.widgets]

		elif isinstance(widget, str):
			return next(iter(w.method for w in ui.widgets if w.method.__name__==widget), None)

		elif not widget in ui.widgets:
			self.addWidgets(ui, widget)

		return next(iter(w.method for w in ui.widgets if w.method==widget.method), None)


	def getSignals(self, w, d=True, exc=[]):
		'''Get all signals for a given widget.

		:Parameters:
			w (str)(obj): The widget to get signals for.
			d (bool): Return signals from all derived classes instead of just the given widget class.
				ex. get: QObject, QWidget, QAbstractButton, QPushButton signals from 'QPushButton'
			exc (list): Exclude any classes in this list. ex. exc=[QtCore.QObject, 'QWidget']

		:Return:
			(list)

		:Example: getSignals(QtWidgets.QPushButton)
			would return:
				clicked (QAbstractButton)
				pressed (QAbstractButton)
				released (QAbstractButton)
				toggled (QAbstractButton)
				customContextMenuRequested (QWidget)
				windowIconChanged (QWidget)
				windowIconTextChanged (QWidget)
				windowTitleChanged (QWidget)
				destroyed (QObject)
				objectNameChanged (QObject)
		'''
		signals=[]
		clss = source if isinstance(source, type) else type(source)
		signal = type(QtCore.Signal())
		for subcls in clss.mro():
			clsname = f'{subcls.__module__}.{subcls.__name__}'
			for k, v in sorted(vars(subcls).items()):
				if isinstance(v, signal):
					if (not d and clsname!=clss.__name__) or (exc and (clss in exc or clss.__name__ in exc)): #if signal is from parent class QAbstractButton and given widget is QPushButton:
						continue
					signals.append(k)
		return signals


	def getDefaultSignals(self, w):
		'''Get the default signals for a given widget type.

		:Parameters:
			widgetType (str): Widget class name. ie. 'QPushButton'

		:Return:
			(str) signal ie. 'released'
		'''
		signals=[]
		try: #if the widget type has a default signal assigned in the signals dict; get the signal.
			signalTypes = self.defaultSignals[w.derivedType]
			for s in Iter.makeList(signalTypes): #assure 'signalTypes' is a list.
				signal = getattr(w, s, None)
				signals.append(signal)

		except KeyError:
			pass
		return signals


	def setConnections(self, ui):
		'''Replace any signal connections of a previous ui with the set for the ui of the given name.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
		'''
		assert isinstance(ui, QtWidgets.QMainWindow), 'Incorrect datatype: {}: {}'.format(type(ui), ui)

		prevUi = self.getPrevUi(allowDuplicates=True)
		if prevUi==ui:
			return

		if prevUi and prevUi.isConnected and prevUi.level<3:
			self.disconnectSlots(prevUi)

		if ui.level<3 or not ui.isConnected:
			self.connectSlots(ui)


	def connectSlots(self, ui, widgets=None):
		'''Connect signals to slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			widgets (obj)(list): QWidget(s)
		'''
		if widgets is None:
			widgets = ui.widgets
		# print ('connectSlots:', ui.name, [w.objectName() for w in Iter.makeList(widgets)])

		for w in Iter.makeList(widgets): #convert 'widgets' to a list if it is not one already.
			# print ('           >:', w.name, w.method)
			if w.method and w.signals:
				for s in w.signals:
					if not s:
						continue
					try:
						if isinstance(w.method, (list, set, tuple)):
							map(s.connect, w.method) #connect to multiple slots from a list.
						else:
							s.connect(w.method) #connect single slot (ex. main and cameras ui)

						s.connect(lambda *args, w=w: self._wgtHistory.append(w)) #add the widget to the widget history list on connect. (*args prevents 'w' from being overwritten by the parameter emitted by the signal.)

					except Exception as error:
						print(f'# Error: {__file__} in connectSlots\n#\t{ui.name} {w.name} {s} {w.method}\n#\t{error}.')

		ui.isConnected = True #set ui state as slots connected.


	def disconnectSlots(self, ui, widgets=None):
		'''Disconnect signals from uitk.slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			widgets (obj)(list): QWidget
		'''
		# print ('disconnectSlots:', ui.name)
		if widgets is None:
			widgets = ui.widgets

		for w in Iter.makeList(widgets):  #convert 'widgets' to a list if it is not one already.
			# print ('           >:', w.name, w.method)
			if w.method and w.signals:
				for s in w.signals:
					if not s:
						continue
					try:
						if isinstance(w.method, (list, set, tuple)):
							s.disconnect() #disconnect all #map(signal.disconnect, slot) #disconnect multiple slots from a list.
						else:
							s.disconnect(w.method) #disconnect single slot (main and cameras ui)

					except Exception as error:
						print(f'# Error: {__file__} in disconnectSlots\n#\t{ui.name} {w.name} {s} {w.method}\n#\t{error}.')

		ui.isConnected = False #set ui state as slots disconnected.


	def connect(self, widgets, signals, slots, clss=None):
		'''Connect multiple signals to multiple slots at once.

		:Parameters:
			widgets (str)(obj)(list): ie. 'chk000-2' or [tb.ctxMenu.chk000, tb.ctxMenu.chk001]
			signals (str)(list): ie. 'toggled' or ['toggled']
			slots (obj)(list): ie. self.cmb002 or [self.cmb002]
			clss (obj)(list): if the widgets arg is given as a string, then the class it belongs to can be explicitly given. else, the current ui will be used.

		ex call: connect_('chk000-2', 'toggled', self.cmb002, tb.ctxMenu)
		*or connect_([tb.ctxMenu.chk000, tb.ctxMenu.chk001], 'toggled', self.cmb002)
		*or connect_(tb.ctxMenu.chk015, 'toggled', 
				[lambda state: self.rigging.tb004.setText('Unlock Transforms' if state else 'Lock Transforms'), 
				lambda state: self.rigging_submenu.tb004.setText('Unlock Transforms' if state else 'Lock Transforms')])
		'''
		if isinstance(widgets, (str)):
			try:
				widgets = self.getWidgetsFromStr(clss, widgets, showError=True) #getWidgetsFromStr returns a widget list from a string of objectNames.
			except Exception as error:
				widgets = self.getWidgetsFromStr(self.currentUi, widgets, showError=True)

		#if the variables are not of a list type; convert them.
		widgets = Iter.makeList(widgets)
		signals = Iter.makeList(signals)
		slots = Iter.makeList(slots)

		for widget in widgets:
			for signal in signals:
				signal = getattr(widget, signal)
				for slot in slots:
					signal.connect(slot)


	def _syncUi(self, submenu, **kwargs):
		'''Extends setSynConnections method to set sync connections 
		for all widgets of the given ui.

		:Parameters:
			submenu (obj): A submenu (level 2) with a corresponding parent menu (level 3).
		'''
		if any((not submenu.isSubmenu, submenu.isSynced, not submenu.level3)):
			return #assure the ui is a unsynced submenu with a parent menu to sync with.

		for w1 in submenu.widgets:
			try:
				w2 = self.getWidget(w1.name, submenu.level3)
			except AttributeError as error:
				continue

			self.setSyncConnections(w1, w2, **kwargs)

		submenu.isSynced = True
		submenu.level3.isSynced = True


	def setSyncConnections(self, w1, w2, **kwargs):
		'''Set the initial signal connections that will call the _syncAttributes function on state changes.

		:Parameters:
			w1 (obj): The first widget to sync.
			w2 (obj): The second widget to sync.
			kwargs = The attribute(s) to sync as keyword arguments.
		'''
		try:
			signals1 = self.getDefaultSignals(w1) #get the default signal for the given widget.
			signals2 = self.getDefaultSignals(w2)

			for s1, s2 in zip(signals1, signals2): #set sync connections for each of the widgets signals.
				s1.connect(lambda: self._syncAttributes(w1, w2, **kwargs))
				s2.connect(lambda: self._syncAttributes(w2, w1, **kwargs))

			w1.isSynced = True
			w2.isSynced = True

		except (AttributeError, KeyError) as error:
			# if w1 and w2: print ('# {}: {}.setSyncConnections({}, {}): {}. args: {}, {} #'.format('KeyError' if type(error)==KeyError else 'AttributeError', __name__, w1.objectName(), w2.objectName(), error, w1, w2))
			return


	attributesGetSet = {
		'value':'setValue', 
		'text':'setText', 
		'icon':'setIcon', 
		'checkState':'setCheckState', 
		'isChecked':'setChecked', 
		'isDisabled':'setDisabled', 
	}
	def _syncAttributes(self, frm, to, attributes=[]):
		'''Sync the given attributes between the two given widgets.
		If a widget does not have an attribute it will be silently skipped.

		:Parameters:
			frm (obj): The widget to transfer attribute values from.
			to (obj): The widget to transfer attribute values to.
			attributes (str)(list)(dict): The attribute(s) to sync. ie. a setter attribute 'setChecked' or a dict containing getter:setter pairs. ie. {'isChecked':'setChecked'}
		'''
		if not attributes:
			attributes = self.attributesGetSet

		elif not isinstance(attributes, dict):
			attributes = {next((k for k,v in self.attributesGetSet.items() if v==i), None):i #construct a gettr setter pair dict using only the given setter values.
				 for i in Iter.makeList(attributes)
			}

		_attributes = {}
		for gettr, settr in attributes.items():
			try:
				_attributes[settr] = getattr(frm, gettr)()
			except AttributeError as error:
				pass

		for attr, value in _attributes.items(): #set the second widget's attributes from the first.
			try:
				getattr(to, attr)(value)
			except AttributeError as error:
				pass


	def setWidgetAttrs(self, *args, **kwargs):
		'''Set multiple properties, for multiple widgets, on multiple ui's at once.

		:Parameters:
			*args = arg [0] (str) String of objectNames. - objectNames separated by ',' ie. 'b000-12,b022'
					arg [1:] dynamic ui object/s.  If no ui's are given, then the parent and child uis will be used.
			*kwargs = keyword: - the property to modify. ex. setText, setValue, setEnabled, setDisabled, setVisible, setHidden
					value: - intended value.

		ex.	setWidgetAttrs('chk003', <ui1>, <ui2>, setText='Un-Crease')
		'''
		if not args[1:]:
			parentUi = self.currentUi.level3
			childUi = self.currentUi.level2
			args = args+(parentUi, childUi)

		for ui in args[1:]:
			widgets = self.getWidgetsFromStr(ui, args[0]) #getWidgetsFromStr returns a widget list from a string of objectNames.
			for property_, value in kwargs.items():
				[getattr(w, property_)(value) for w in widgets] #set the property state for each widget in the list.


	@staticmethod
	def unpackNames(nameString):
		'''Get a list of individual names from a single name string.
		If you are looking to get multiple objects from a name string, call 'getWidgetsFromStr' directly instead.

		:Parameters:
			nameString = string consisting of widget names separated by commas. ie. 'v000, b004-6'

		:Return:
			unpacked names. ie. ['v000','b004','b005','b006']

		:Example: unpackNames('chk021-23, 25, tb001')
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


	@classmethod
	def getWidgetsFromStr(cls, ui, nameString, showError=False):
		'''Get a list of corresponding widgets from a single shorthand formatted string.
		ie. 's000,b002,cmb011-15' would return object list: [<s000>, <b002>, <cmb011>, <cmb012>, <cmb013>, <cmb014>, <cmb015>]

		:Parameters:
			ui (obj): A previously loaded dynamic ui object.
			nameString (str): Widget object names separated by ','. ie. 's000,b004-7'. b004-7 specifies buttons b004-b007.
			showError (bool): Print an error message to the console if a widget is not found.

		:Return:
			(list)

		#ex call: getWidgetsFromStr(<ui>, 's000,b002,cmb011-15')
		'''
		widgets=[]
		for n in cls.unpackNames(nameString):
			try:
				w = getattr(ui, n)
				widgets.append(w)
			except AttributeError as error:
				if showError:
					print (f'# Error: {__file__} in getWidgetsFromStr\n#\t{error}.')
				pass

		return widgets


	@staticmethod
	def getCenter(w):
		'''Get the center point of a given widget.

		:Parameters:
			w (obj): The widget to query.

		:Return:
			(obj) QPoint
		'''
		return QtGui.QCursor.pos() - w.rect().center()


	@staticmethod
	def resizeAndCenterWidget(widget, paddingX=30, paddingY=6):
		'''Adjust the given widget's size to fit contents and re-center.

		:Parameters:
			widget (obj): The widget to resize.
			paddingX (int): Any additional width to be applied.
			paddingY (int): Any additional height to be applied.
		'''
		p1 = widget.rect().center()
		widget.resize(widget.sizeHint().width()+paddingX, widget.sizeHint().height()+paddingY)
		p2 = widget.rect().center()
		diff = p1-p2
		widget.move(widget.pos()+diff)


	@staticmethod
	def moveAndCenterWidget(w, p, offsetX=2, offsetY=2):
		'''Move and center the given widget on the given point.

		:Parameters:
			w (obj): The widget to resize.
			p (obj): A point to move to.
			offsetX (int): The desired offset on the x axis. 2 is center. 
			offsetY (int): The desired offset on the y axis.
		'''
		width = p.x()-(w.width()/offsetX)
		height = p.y()-(w.height()/offsetY)

		w.move(QtCore.QPoint(width, height)) #center a given widget at a given position.


	@staticmethod
	def centerWidgetOnScreen(w):
		'''
		'''
		centerPoint = QtGui.QScreen.availableGeometry(QtWidgets.QApplication.primaryScreen()).center()
		w.move(centerPoint - w.frameGeometry().center())


	def toggleWidgets(self, *args, **kwargs):
		'''Set multiple boolean properties, for multiple widgets, on multiple ui's at once.

		:Parameters:
			*args = dynamic ui object/s. If no ui's are given, then the current UI will be used.
			*kwargs = keyword: - the property to modify. ex. setChecked, setUnChecked, setEnabled, setDisabled, setVisible, setHidden
					value: string of objectNames - objectNames separated by ',' ie. 'b000-12,b022'

		ex.	toggleWidgets(<ui1>, <ui2>, setDisabled='b000', setUnChecked='chk009-12', setVisible='b015,b017')
		'''
		if not args:
			parentUi = self.currentUi.level3
			childUi = self.currentUi.level2
			args = [childUi, parentUi]

		for ui in args:
			for k in kwargs: #property_ ie. setUnChecked
				widgets = self.getWidgetsFromStr(ui, kwargs[k]) #getWidgetsFromStr returns a widget list from a string of objectNames.

				state = True
				if 'Un' in k: #strips 'Un' and sets the state from True to False. ie. 'setUnChecked' becomes 'setChecked' (False)
					k = k.replace('Un', '')
					state = False

				[getattr(w, k)(state) for w in widgets] #set the property state for each widget in the list.


	def setAxisForCheckBoxes(self, checkboxes, axis, ui=None):
		'''Set the given checkbox's check states to reflect the specified axis.

		:Parameters:
			checkboxes (str)(list): 3 or 4 (or six with explicit negative values) checkboxes.
			axis (str): Axis to set. Valid text: '-','X','Y','Z','-X','-Y','-Z' ('-' indicates a negative axis in a four checkbox setup)

		ex call: setAxisForCheckBoxes('chk000-3', '-X') #optional ui arg for the checkboxes
		'''
		if isinstance(checkboxes, (str)):
			if ui is None:
				ui = self.currentUi
			checkboxes = self.getWidgetsFromStr(ui, checkboxes)

		prefix = '-' if '-' in axis else '' #separate the prefix and axis
		coord = axis.strip('-')

		for chk in checkboxes:
			if any([chk.text()==prefix, chk.text()==coord, chk.text()==prefix+coord]):
				chk.setChecked(True)


	def getAxisFromCheckBoxes(self, checkboxes, ui=None):
		'''Get the intended axis value as a string by reading the multiple checkbox's check states.

		:Parameters:
			checkboxes (str)(list): 3 or 4 (or six with explicit negative values) checkboxes. Valid text: '-','X','Y','Z','-X','-Y','-Z' ('-' indicates a negative axis in a four checkbox setup)

		:Return:
			(str) axis value. ie. '-X'		

		ex call: getAxisFromCheckBoxes('chk000-3')
		'''
		if isinstance(checkboxes, (str)):
			if ui is None:
				ui = self.currentUi
			checkboxes = self.getWidgetsFromStr(ui, checkboxes, showError=True)

		prefix=axis=''
		for chk in checkboxes:
			if chk.isChecked():
				if chk.text()=='-':
					prefix = '-'
				else:
					axis = chk.text()
		# print ('prefix:', prefix, 'axis:', axis) #debug
		return prefix+axis #ie. '-X'


	def gcProtect(self, obj=None, clear=False):
		'''Protect the given object from garbage collection.

		:Parameters:
			obj (obj)(list): The obj(s) to add to the protected list.
			clear (bool): Clear the set before adding any given object(s).

		:Return:
			(list) protected objects.
		'''
		if clear:
			self._gcProtect.clear()

		for o in Iter.makeList(obj):
			self._gcProtect.add(o)

		return self._gcProtect


	@staticmethod
	def isWidget(obj):
		'''Returns True if the given obj is a valid widget.

		:Parameters:
			obj (obj): An object to query.

		:Return:
			(bool)
		'''
		import shiboken2
		return hasattr(obj, 'objectName') and shiboken2.isValid(obj)


	@staticmethod
	def getWidgetAt(pos, topWidgetOnly=True):
		'''Get visible and enabled widget(s) located at the given position.
		As written, this will disable `TransparentForMouseEvents` on each widget queried.

		:Parameters:
			pos (QPoint) = The global position at which to query.
			topWidgetOnly (bool): Return only the top-most widget, 
				otherwise widgets are returned in the order in which they overlap.
				Disabling this option will cause overlapping windows to flash as 
				their attribute is changed and restored.
		:Return:
			(obj)(list) list if not topWidgetOnly.

		:Example: getWidgetAt(QtGui.QCursor.pos())
		'''
		w = QtWidgets.QApplication.widgetAt(pos)
		if topWidgetOnly:
			return w

		widgets=[]
		while w:
			widgets.append(w)

			w.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents) #make widget invisible to further enquiries.
			w = QtWidgets.QApplication.widgetAt(pos)

		for w in widgets: #restore attribute.
			w.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

		return widgets


	@staticmethod
	def getParentWidgets(widget, objectNames=False):
		'''Get the all parent widgets of the given widget.

		:Parameters:
			widget (obj): QWidget
			objectNames (bool): Return as objectNames.

		:Return:
			(list) Object(s) or objectName(s)
		'''
		parentWidgets=[]
		w = widget
		while w:
			parentWidgets.append(w)
			w = w.parentWidget()
		if objectNames:
			return [w.objectName() for w in parentWidgets]
		return parentWidgets


	@staticmethod
	def getTopLevelParent(widget, index=-1):
		'''Get the parent widget at the top of the hierarchy for the given widget.

		:Parameters:
			widget (obj): QWidget
			index (int): Last index is top level.

		:Return:
			(QWidget)
		'''
		return self.getParentWidgets()[index]


	@staticmethod
	def qApp_getWindow(name=None):
		'''Get Qt window/s

		:Parameters:
			name (str): optional name of window (widget.objectName)

		:Return:
			if name: corresponding <window object>
			else: return a dictionary of all windows {windowName:window}
		'''
		windows = {w.objectName():w for w in QtWidgets.QApplication.allWindows()}
		if name:
			return windows[name]
		else:
			return windows


	@staticmethod
	def qApp_getWidget(name=None):
		'''Get Qt widget/s

		:Parameters:
			name (str): optional name of widget (widget.objectName)

		:Return:
			if name: corresponding <widget object>
			else: return a dictionary of all widgets {objectName:widget}
		'''
		widgets = {w.objectName():w for w in QtWidgets.QApplication.allWidgets()}
		if name:
			return widgets[name]
		else:
			return widgets

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__=='__main__':

	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	from uitk.slots.polygons import Polygons
	sb = Switchboard(uiLoc='ui', widgetLoc='widgets', slotLoc='slots/maya') #set relative paths, and explicity set the slots class instead of providing a path like: slotLoc='slots/maya', which in this case would produce the same result with just a little more overhead.
	ui = sb.polygons #get the ui by it's name.

	ui.show()

	print ('current ui name:', sb.currentUi.name)
	print ('current ui:', sb.currentUi)
	print ('connected state:', ui.isConnected)
	print ('slots:', ui.slots)
	print ('method tb000:', ui.tb000.method) #None because tb000 defined in subclass. ie. Polygons_maya
	print ('widget from method tb000:', sb.getWidgetFromMethod(ui.tb000.method))
	# print ('widgets:', ui.widgets)

	exit_code = app.exec_()
	if exit_code != -1:
		sys.exit(exit_code) # run app, show window, wait for input, then terminate program with a status code returned from app.

print (__name__) #module name
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------

	# def setAttributes(self, obj=None, order=['setVisible'], **kwargs):
	# 	'''Set attributes for a given object.

	# 	:Parameters:
	# 		obj (obj): the child obj, or widgetAction to set attributes for. (default=self)
	# 		order (list): List of string keywords. ie. ['move', 'setVisible']. attributes in this list will be set last, in order of the list. an example would be setting move positions after setting resize arguments.
	# 		**kwargs = The keyword arguments to set.
	# 	'''
	# 	if not kwargs:
	# 		return

	# 	obj = obj if obj else self

	# 	for k in order:
	# 		v = kwargs.pop(k, None)
	# 		if v:
	# 			from collections import OrderedDict
	# 			kwargs = OrderedDict(kwargs)
	# 			kwargs[k] = v

	# 	for attr, value in kwargs.items():
	# 		try:
	# 			getattr(obj, attr)(value)

	# 		except AttributeError as error:
	# 			pass; # print (__name__+':','setAttributes:', obj, order, kwargs, error)