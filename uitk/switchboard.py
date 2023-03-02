# !/usr/bin/python
# coding=utf-8
import os, sys
import re
import glob
import importlib
import inspect
from functools import partial

from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtUiTools import QUiLoader

from pythontk import File, Str, Iter, hasAttribute, setAttributes
from uitk.styleSheet import StyleSheet


class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, switchboard_instance, file):
		'''Represents a main window in a GUI application.
		Inherits from QtWidgets.QMainWindow class, providing additional functionality for 
		managing user interface (UI) elements.

		Parameters:
			switchboard_instance (obj): An instance of the switchboard class
			file_path (str): The full path to the UI file

		Attributes:
			switchboard_instance (obj): The instance of the switchboard class
			path (str): The path of the UI file
			level (int): The level of the UI in the hierarchy (0: init (root), 1: base menus, 2: sub menus, 3: parent menus, 4: popup menus)
			isSubmenu (bool): Whether the UI is a submenu
			isInitialized (bool): Whether the UI has been initialized (True after the UI is first shown)
			isConnected (bool): Whether the UI is connected
			preventHide (bool): Whether hiding the UI should be prevented
			connectOnShow (bool): Whether the UI should be connected on show
			base (str): The base of the UI name
			tags (list): The tags of the UI name (trailing strings in the UI name preceded by a hashtag used to define special behaviors)
			sizeX (int): The width of the UI
			sizeY (int): The height of the UI
			widgets (list): The list of widgets in the UI

		Properties:
			name (str): The name of the UI
			ui (obj): The current UI
			<UI>.name (str): The UI filename
			<UI>.alias (str): Get or set an alternate attribute name that can be used to access the UI
			<UI>.base (str): The base UI name
			<UI>.path (str): The directory path containing the UI file
			<UI>.tags (list): Any UI tags as a list
			<UI>.level (int): The UI level
			<UI>.sizeX (int): The original width of the UI
			<UI>.sizeY (int): The original height of the UI
			<UI>.isCurrentUi (bool): True if the UI is set as current
			<UI>.isSubmenu (bool): True if the UI is a submenu
			<UI>.isInitialized (bool): True after the UI is first shown
			<UI>.connected (bool): True if the UI is connected. If set to True, the UI will be set as current and connections established
			<UI>.isConnected (bool): True if the UI is connected to its slots
			<UI>.connectOnShow (bool): While True, the UI will be set as current on show
			<UI>.show: An override of the built-in hide method
			<UI>.preventHide (bool): While True, the hide method is disabled
			<UI>.hide: An override of the built-in hide method
			<UI>.initWidgets (function): Initialize widgets.
			<UI>.widgets (list): All the widgets of the UI
			<UI>.slots (obj): The slots class instance
		'''
		super().__init__()

		self.sb = switchboard_instance
		self.name = File.formatPath(file, 'name')
		self.path = File.formatPath(file, 'path')
		self.level = self.sb._getUiLevelFromDir(file)
		self.isSubmenu = self.level==2
		self.isInitialized = False
		self.isConnected = False
		self.preventHide = False
		self.connectOnShow = True
		self.base = next(iter(self.name.split('_')))
		self.tags = self.name.split('#')[1:]
		self.sizeX = self.frameGeometry().width()
		self.sizeY = self.frameGeometry().height()
		self._widgets = set()
		self._deferred = {}

		ui = self.sb.load(file)
		self.setWindowFlags(ui.windowFlags())
		self.setCentralWidget(ui.centralWidget())

	def __getattr__(self, attr_name):
		"""Looks for the widget in the parent class.
		If found, the widget is initialized and returned, else an AttributeError is raised.

		Parameters:
			attr_name (str): the name of the attribute being accessed.

		Return:
			() The value of the widget attribute if it exists, or raises an AttributeError
			if the attribute cannot be found.
  
		Raises:
			AttributeError: if the attribute does not exist in the current instance
			or the parent class.
		"""
		found_widget = self.sb._getWidgetFromUi(self, attr_name)
		if found_widget:
			self.sb.initWidgets(self, found_widget)
			return found_widget
		raise AttributeError(f'{self.__class__.__name__} has no attribute `{attr_name}`')

	def event(self, event):
		if event.type() == QtCore.QEvent.ChildPolished:
			child = event.child()
			self.on_child_polished(child)
		return super().event(event)

	def defer(self, func, *args, priority=0):
		"""Defer execution of a function until later. The function is added to a dictionary of deferred 
		methods, with a specified priority. Lower priority values will be executed before higher ones.
		
		Parameters:
			func (function): The function to defer.
			*args: Any arguments to be passed to the function.
			priority (int, optional): The priority of the deferred method. Lower values will be executed 
					first. Defaults to 0.
		"""
		method = partial(func, *args)
		if priority in self._deferred:
			self._deferred[priority] += (method,)
		else:
			self._deferred[priority] = (method,)

	def trigger_deferred(self):
		"""Executes all deferred methods, in priority order. Any arguments passed to the deferred functions
		will be applied at this point. Once all deferred methods have executed, the dictionary is cleared.
		"""
		for priority in sorted(self._deferred):
			for method in self._deferred[priority]:
				method()
		self._deferred.clear()

	@property
	def name(self):
		return self.objectName()

	@name.setter
	def name(self, new_name):
		try:
			delattr(self.sb, self.objectName())
		except AttributeError:
			pass
		self.setObjectName(new_name)
		setattr(self.sb, new_name, self)

	@property
	def widgets(self):
		return list(self._widgets) or self.sb.initWidgets(self, self.findChildren(QtWidgets.QWidget), returnAllWidgets=True)

	@property
	def slots(self):
		return self.sb.getSlots(self)

	@property
	def isCurrentUi(self):
		return self==self.sb.getCurrentUi()

	def setAsCurrent(self):
		self.sb.setCurrentUi(self)

	def connect(self):
		self.sb.setConnections(self)

	def on_child_polished(self, w): #called after child polished event.
		if w not in self._widgets:
			self.sb.initWidgets(self, w)
			# print ('on_child_polished:', w.ui.name.ljust(30), w.name.ljust(15), id(w)) #debug
			self.trigger_deferred()
			if self.isConnected:
				self.sb.connectSlots(self, w)

	def setVisible(self, state): #called every time the after widget is shown or hidden on screen.
		if state: #visible
			if self.connectOnShow and not self.isConnected:
				self.sb.setConnections(self)
			self.activateWindow()
			self.isInitialized = True
		elif self.preventHide: #invisible
			return
		super().setVisible(state)



class Switchboard(QUiLoader, StyleSheet):
	'''Load dynamic UI, assign convenience properties, and handle slot connections.

	Properties:
		sb: The instance of this class holding all properties.
		sb.ui: Returns the current UI.
		sb.<uiFileName>: Accesses the UI loaded from uiFileName.
		sb.<customWidgetClassName>: Accesses the custom widget with the specified class name.

	Parameters:
		parent (obj): A QtObject derived class.
		dynui (str/obj): Set the directory of the dynamic UI, or give the dynamic UI objects.
		widgets (str/obj): Set the directory of any custom widgets, or give the widget objects.
		slots (str/obj): Set the directory of where the slot classes will be imported, or give the slot class itself.
		preloadUi (bool): Load all UI immediately. Otherwise UI will be loaded as required.
		style (str): Stylesheet color mode. ie. 'standard', 'dark', None
		submenuStyle (str): The stylesheet color mode for submenus.

	Methods:
		loadUi(uiPath): Load the UI file located at uiPath.
		loadAllUi(): Load all UI files in the UI directory.
		registerWidget(widget): Register the specified widget.
		connectSlots(slotClass, ui=None): Connect the slots in the specified slot class to the specified UI.

	Attributes:
		defaultDir: The default directory.
		defaultSignals: A dictionary of the default signals to be connected per widget type.

	Default Directories:
		The default directory is the calling module's directory.
		If any of the given file paths are not a full path, they will be treated as relative to the currently set path.

	Example:
		1. Create a subclass of Switchboard and define the slots for the UI events.
			class MySwitchboard(Switchboard):
				def __init__(self, parent=None, **kwargs):
					super().__init__(parent)
					...
				def my_slot(self):
					...
		2. Instantiate the subclass and show the UI.
			sb = MySwitchboard()
			sb.ui.show()
		3. Run the app, show the window, wait for input, then terminate program with the status code returned from app.
			exit_code = sb.app.exec_()
			if exit_code != -1:
				sys.exit(exit_code)
	'''
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	def __init__(self, parent=None, dynui=None, widgets=None, slots=None, preloadUi=False, style='standard', submenuStyle='dark'):
		super().__init__(parent)
		'''
		'''
		calling_frame = inspect.currentframe().f_back
		calling_file = calling_frame.f_code.co_filename
		self.defaultDir = os.path.abspath(os.path.dirname(calling_file))
		self.moduleDir = File.getFilepath(__file__)

		self.dynui = dynui or f'{self.moduleDir}/ui' #use the relative filepath of this module if None is given.
		self.widgets = widgets or f'{self.moduleDir}/widgets'
		self.slots = slots or f'{self.moduleDir}/slots'

		self.style = style
		self.submenuStyle = submenuStyle

		self._uiHistory = [] #A list of previously loaded ui.
		self._wgtHistory = [] #A list of previously used widgets.
		self._registeredWidgets = {} #A dict of all registered custom widgets.
		self._loadedUi = set() #A set of all loaded ui.
		self._synced_pairs = set() #A set of hashed values representing widgets that have synced values.
		self._gcProtect = set() #A set of widgets to be protected from garbage collection.

		self.defaultSignals = { #the signals to be connected per widget type. Values can be a list or a single item string.
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

		if preloadUi:
			self.loadAllUi()

	def __getattr__(self, attr_name):
		'''If an unknown attribute matches the name of a ui in the current ui directory; load and return it.
		Else, if an unknown attribute matches the name of a custom widget in the widgets directory; register and return it.
		If no match is found raise an attribute error.

		Return:
			(obj) ui or widget.
		'''
		# Check if the attribute matches a ui file
		ui_path = File.formatPath(self.dynui, 'path')
		found_ui = next((f for f in glob.iglob(f'{ui_path}/**/{attr_name}.ui', recursive=True)), None)
		if found_ui:
			ui = self.loadUi(found_ui)
			return ui

		# Check if the attribute matches a widget file
		widget_path = File.formatPath(self.widgets, 'path')
		widget_name = Str.setCase(attr_name, 'camel')
		found_widget = next((f for f in glob.iglob(f'{widget_path}/**/{widget_name}.py', recursive=True)), None)
		if found_widget:
			widget = self.registerWidgets(found_widget)
			if isinstance(widget, list):
				widget = next(iter(w for w in widget if w.__name__.lower()==attr_name.lower()), None) #check if any of the widgets in the list has a name that matches the attribute name in a case-insensitive manner.
			if widget and widget.__name__.lower()==attr_name.lower(): #If the widget's name matches the attribute name, the widget is returned.
				return widget

		raise AttributeError(f'{self.__class__.__name__} has no attribute `{attr_name}`')


	@property
	def dynui(self) -> str:
		'''Get the directory where the dynamic ui are stored.

		Return:
			(str) directory path.
		'''
		
		if not hasAttribute(self, '_uiLoc'): #does not invoke __getattr__.
			self._uiLoc = self.defaultDir
			return self._uiLoc
		return self._uiLoc


	@dynui.setter
	def dynui(self, d) -> None:
		'''Set the directory where the dynamic ui are located.

		Parameters:
			d (str): The directory path where the dynamic ui are located.
				If the given dir is not a full path, it will be treated as relative to the default path.
		'''
		if isinstance(d, str):
			isAbsPath = os.path.isabs(d)
			self._uiLoc = d if isAbsPath else os.path.join(self.defaultDir, d) #if the given dir is not a full path, treat it as relative to the default path.
		else: #store object.
			self.setWorkingDirectory(d) #set QUiLoader working path.
			self._uiLoc = d


	@property
	def widgets(self) -> str:
		'''Get the directory where any custom widgets are stored.

		Return:
			(str) directory path.
		'''
		if not hasAttribute(self, '_widgetLoc'): #does not invoke __getattr__.
			self._widgetLoc = self.defaultDir
			return self._widgetLoc
		return self._widgetLoc


	@widgets.setter
	def widgets(self, d) -> None:
		'''Set the directory where any custom widgets are stored.

		Parameters:
			d (str): The directory path where any custom widgets are located.
				If the given dir is not a full path, it will be treated as relative to the default path.
		'''
		if isinstance(d, str):
			isAbsPath = os.path.isabs(d)
			self._widgetLoc = d if isAbsPath else os.path.join(self.defaultDir, d) #if the given dir is not a full path, treat it as relative to the default path.
		else: #store object.
			self.addPluginPath(d) #set QUiLoader working path.
			self._widgetLoc = d


	@property
	def slots(self) -> str:
		'''Get the directory where the slot classes will be imported from.

		Return:
			(str)(obj) slots class directory path or slots class object.
		'''
		try:
			return self._slotLoc

		except AttributeError as error:
			self._slotLoc = self.defaultDir
			return self._slotLoc


	@slots.setter
	def slots(self, d) -> None:
		'''Set the directory where the slot classes will be imported from.

		Parameters:
			d (str): The directory path where the slot classes are located.
				If the given dir is not a full path, it will be treated as relative to the default path.
		'''
		if isinstance(d, str):
			isAbsPath = os.path.isabs(d)
			self._slotLoc = d if isAbsPath else os.path.join(self.defaultDir, d) #if the given dir is not a full path, treat it as relative to the default path.
		else: #store object.
			self._slotLoc = d


	@property
	def ui(self) -> QtWidgets.QWidget:
		'''Get the current ui.

		Return:
			(obj) ui
		'''
		return self.getCurrentUi()


	@ui.setter
	def ui(self, ui) -> None:
		'''Register the uiName in history as current and set slot connections.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
		'''
		self.setCurrentUi(ui)


	@property
	def prevUi(self) -> QtWidgets.QWidget:
		'''Get the previous ui from history.

		Return:
			(obj)
		'''
		return self.getPrevUi()


	@property
	def prevCommand(self) -> object:
		'''Get the last called slot method.

		Return:
			(obj) method.
		'''
		try:
			return self.prevCommands[-1]

		except IndexError as error:
			return None


	@property
	def prevCommands(self) -> tuple:
		'''Get a list of previously called slot methods.

		Return:
			(tuple) list of methods.
		'''
		cmds = [w.getSlot() for w in self._wgtHistory[-10:]] #limit to last 10 elements and get methods from widget history.
		hist = tuple(dict.fromkeys(cmds[::-1]))[::-1] #remove any duplicates (keeping the last element). [hist.remove(l) for l in hist[:] if hist.count(l)>1] #

		return hist


	def initWidgets(self, ui, widgets, recursive=True, returnAllWidgets=False, **kwargs):
		"""Add widgets as attributes of the ui while giving additional attributes to the widgets themselves.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			widgets (obj)(list): A widget or list of widgets to be added.
			recursive (bool): Whether to recursively add child widgets (default=True).
			kwargs (): Keyword arguments to set additional widget attributes.

		Return:
			(set) The added widgets.
		"""
		added_widgets = set()
		for w in Iter.makeList(widgets):
			if w in ui._widgets or w in added_widgets or not self.isWidget(w):
				continue

			w.ui = ui
			w.name = w.objectName()
			w.type = w.__class__.__name__
			w.derivedType = self.getDerivedType(w, name=True)
			w.signals = self.getDefaultSignals(w) #default widget signals as list. ie. [<widget.valueChanged>]
			w.prefix = self.getprefix(w.name) #returns an string alphanumberic prefix if name startswith a series of alphanumberic charsinst is followed by three integers. ie. 'cmb' from 'cmb015'
			w.getSlot = lambda w=w, u=ui: getattr(self.getSlots(u), w.name, None)

			if ui.isSubmenu and not w.prefix=='i':
				self.setStyle(w, style=self.submenuStyle, alpha=0)
			else:
				self.setStyle(w, style=self.style, alpha=0.01)

			setAttributes(w, **kwargs)
			setattr(ui, w.name, w)
			added_widgets.add(w)
			# print (0, 'initWidgts:', w.ui.name.ljust(26), w.prefix.ljust(25), (w.name or type(w).__name__).ljust(25), w.type.ljust(15), w.derivedType.ljust(15), id(w)) #debug

			if recursive:
				child_widgets = w.findChildren(QtWidgets.QWidget)
				self.initWidgets(ui, child_widgets, **kwargs)

		ui._widgets.update(added_widgets)
		return added_widgets if not returnAllWidgets else ui._widgets


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

		Parameters:
			file (str): The full file path to the ui file.
			prop (str): the property text without its opening and closing brackets. 
								ie. 'customwidget' for the property <customwidget>.
		Return:
			(list) list of tuples (typically one or two element).

		Example: getPropertyFromUiFile(file, 'customwidget')
		'''
		f = open(file); # print (f.read()) #debug
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

		manu types:
			level 0: stackedwidget: start (root)
			level 1: stackedwidget: base menus
			level 2: stackedwidget: sub menus
			level 3: main menus
			level 4: popup menus

		Parameters:
			filePath (str): The directory containing the ui file. ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/uiLevel_0/init.ui'

		Return:
			(int) If no level is found, a level of 3 (main menu) will be returned.
		'''
		uiFolder = File.formatPath(filePath, 'dir')
		try:
			return int(re.findall(r"\d+\s*$", uiFolder)[0]) #get trailing integers.
		except IndexError: #not an int.
			return 3


	@staticmethod
	def getprefix(widget):
		'''Return the prefix of a widget's object name.
		A valid prefix is an alphanumeric character sequence at the beginning of the widget's object name,
		ending at the first digit.

		Parameters:
			widget (str)(obj): The widget or its object name as a string.

		Return:
			(str) The prefix of the widget's object name as a string.

		Example:
			getprefix('someName00') #returns: 'someName'
			getprefix('someName') #returns: 'someName'
			getprefix('some0Name') #returns: 'some'
		'''
		import re

		if not isinstance(widget, str):
			widget = widget.objectName()

		match = re.search(r'^\D*', widget)
		return widget[:match.end()]


	@staticmethod
	def _getWidgetsFromUi(ui: QtWidgets.QWidget, inc=[], exc='_*', objectNamesOnly=False) -> dict:
		'''Find widgets in a PySide2 UI object.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			inc (str)(tuple): Widget names to include.
			exc (str)(tuple): Widget names to exclude.
			objectNamesOnly (bool): Only include widgets with object names.

		Return:
			(dict) {<widget>:'objectName'}
		'''
		dct = {c:c.objectName() for c in ui.findChildren(QtWidgets.QWidget, None) 
			if (not objectNamesOnly or c.objectName())}

		return Iter.filterDict(dct, inc, exc, keys=True, values=True)


	@staticmethod
	def _getWidgetFromUi(ui: QtWidgets.QWidget, object_name: str) -> QtWidgets.QWidget:
		'''Find a widget in a PySide2 UI object by its object name.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			object_name (str): The object name of the widget to find.

		Return:
			(obj)(None) The widget object if it's found, or None if it's not found.
		'''
		return ui.findChild(QtWidgets.QWidget, object_name)


	def _getWidgetsFromDir(self, path):
		'''Get all widget class objects from a given directory, module filepath or module name.

		Parameters:
			path (str): A directory, fullpath to a widget module, or the name of a module residing in the 'widgets' directory.
						For example: - 'path_to/uitk/widgets'
									 - 'path_to/uitk/widgets/comboBox.py'
									 - 'comboBox'
		Return:
			(dict) keys are widget names and the values are the widget class objects.
			Returns an empty dictionary if no widgets were found or an error occurred.
		'''
		mod_name = File.formatPath(path, 'name')
		if mod_name:
			wgt_name = Str.setCase(mod_name, 'pascal')
			if wgt_name in self._registeredWidgets:
				return {}

			if not File.isValidPath(path):
				path = os.path.join(self.widgets, f'{mod_name}.py')

			try:
				spec = importlib.util.spec_from_file_location(mod_name, path)
				mod = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(mod)
			except ModuleNotFoundError as error:
				print(f"# Error: {__file__} in _getWidgetsFromDir\n#\t{error}")
				return {}

			cls_members = inspect.getmembers(mod, lambda m: inspect.isclass(m) 
				and m.__module__==mod.__name__ and issubclass(m, QtWidgets.QWidget)) #get only the widget classes that are defined in the module and not any imported classes.
			return dict(cls_members)

		else: #get all widgets in the given path by recursively calling this fuction.
			try:
				files = os.listdir(path)
			except FileNotFoundError as error:
				print(f"# Error: {__file__} in _getWidgetsFromDir\n#\t{error}")
				return {}

			widgets={}
			for file in files:
				if file.endswith('.py') and not file.startswith('_'):
					mod_path = os.path.join(path, file)
					widgets.update(self._getWidgetsFromDir(mod_path))
			return widgets


	def setSlots(self, ui, clss):
		'''Explicitly set the slot class for a given ui.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			clss (obj): A class or class instance to set as the slots location for the given ui. 

		Return:
			(obj) class instance.
		'''
		if inspect.isclass(clss):
			setattr(clss, 'sb', self)
			ui._slots = clss() if callable(clss) else clss
			self.initWidgets(ui, ui.findChildren(QtWidgets.QWidget))
			return ui._slots
		return None


	def getSlots(self, ui, persist=False):
		'''Get the class instance of the ui's slots module if it exists.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			persist (bool): Do not assign the ui's slots attribute a None value when a class is not found.

		Return:
			(obj) class instance.
		'''
		if hasAttribute(ui, '_slots'):
			# print ('getSlots:', ui.name, ui._slots, self.slots, inspect.isclass(ui._slots)) #debug
			return ui._slots

		else:
			if isinstance(self.slots, str):
				clss = self._importSlots(ui)
			else: #if slots is a class object:
				clss = self.slots
			# print ('getSlots:2', ui.name, clss, inspect.isclass(clss), self.slots) #debug
			if not clss:
				if ui.isSubmenu:
					mainmenu = self.getUi(ui, 3)
					basemenu = self.getUi(ui, 1)
					if mainmenu: #is a submenu that has a parent menu.
						return self.getSlots(mainmenu)
					elif basemenu:
						return self.getSlots(basemenu)
		if clss:
			return self.setSlots(ui, clss)
		elif not persist:
			ui._slots = None
		return None


	def _importSlots(self, ui, path=None, recursive=True):
		'''Import the slot class associated with the given ui.
		ie. get <Polygons> class using ui name 'polygons'

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			path (str): The directory location of the module.
					If None is given, the slots property will be used.
			recursive (bool): Search subfolders of the given path.

		Return:
			(obj) class
		'''
		assert isinstance(ui, QtWidgets.QMainWindow), 'Incorrect datatype: {}: {}'.format(type(ui), ui)

		d = File.formatPath(self.slots, 'dir')
		suffix = '' if d=='slots' else d

		mod_name = '{}_{}'.format(
							Str.setCase(ui.name, case='camel'), 
							Str.setCase(suffix, case='camel'),
							).rstrip('_') #ie. 'polygons_maya' or 'polygons' if suffix is None.
		if not path:
			if isinstance(self.slots, str):
				path = self.slots
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

		Parameters:
			widgets (str)(obj)(list): A filepath to a dir containing widgets or to the widget itself. 
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets' or the widget(s) themselves. 

		Return:
			(obj)(list) list if widgets given as a list.

		Example: registerWidgets(<class 'widgets.menu.Menu'>) #register using widget class object.
		Example: registerWidgets('O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets/menu.py') #register using path to widget module.
		'''
		result=[]
		for w in Iter.makeList(widgets): #assure widgets is a list.

			if isinstance(w, str):
				widgets_ = self._getWidgetsFromDir(w)
				for w_ in widgets_.values():
					rw = self.registerWidgets(w_)
					result.append(rw)
				continue

			elif w.__name__ in self._registeredWidgets:
				continue

			try:
				self.registerCustomWidget(w)
				self._registeredWidgets[w.__name__] = w
				setattr(self, w.__name__, w)
				result.append(w)

			except Exception as error:
				print (f'# Error: {__file__} in registerWidgets\n#\t{error}.')

		return Iter.formatReturn(result, widgets) #if 'widgets' is given as a list; return a list.


	def loadAllUi(self, path=None, widgets=None):
		'''Extends the 'loadUi' method to load all ui from a given path.

		Parameters:
			path (str): The path to the directory containing the ui files to load.
				If no path is given all ui from the default 'dynui' will be loaded.
			widgets (str)(obj)(list): A filepath to a dir containing widgets or to the widget itself.
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets' or the widget(s) themselves.

		Return:
			(list) QMainWindow object(s).
		'''
		files = glob.iglob('{}/**/*.ui'.format(path or self.dynui), recursive=True)
		return [self.loadUi(f, widgets) for f in files]


	def loadUi(self, file, widgets=None):
		'''Loads a ui from the given path to the ui file.

		Parameters:
			file (str): The full file path to the ui file.
			widgets (str)(obj)(list): A filepath to a dir containing widgets or the widget(s) itself.
						ie. 'O:/Cloud/Code/_scripts/uitk/uitk/ui/widgets' or the widget(s) themselves.
		Return:
			(obj) QMainWindow object.
		'''
		name = File.formatPath(file, 'name')
		path = File.formatPath(file, 'path')
		level = self._getUiLevelFromDir(file)

		#register custom widgets
		if widgets is None and not isinstance(self.widgets, str): #widget objects defined in widgets.
			widgets = self.widgets
		if widgets is not None: #widgets given explicitly or defined in widgets.
			self.registerWidgets(widgets)
		else: #search for and attempt to load any widget dependancies using the path defined in widgets.
			lst = self.getPropertyFromUiFile(file, 'customwidget')
			for l in lst: #get any custom widgets from the ui file.
				try:
					className = l[0][1] #ie. 'PushButtonDraggable' from ('class', 'PushButtonDraggable')
					derivedType = l[1][1] #ie. 'QPushButton' from ('extends', 'QPushButton')
				except IndexError as error:
					continue

				mod_name = Str.setCase(className, 'camel')
				fullpath = os.path.join(self.widgets, mod_name+'.py')
				self.registerWidgets(fullpath)

		ui = MainWindow(self, file)
		self._loadedUi.add(ui)
		return ui


	def getUi(self, ui=None, level=None):
		'''Get a dynamic ui using its string name, or if no argument is given, return the current ui.

		Parameters:
			ui (str)(obj)(list): The ui or name(s) of the ui.
			level (int)(list): Integer(s) representing the level to include.
						ex. 2 for submenu, 3 for main menu, or [2, 3] for both.
		Return:
			(str)(list) list if 'level' given as a list.
		'''
		error_msg = lambda ui: f'# Error: {__file__} in getUi\n#\tUI not found: {ui}({type(ui).__name__})\n#\tConfirm the following UI path is correct: {self.dynui}'

		if not ui:
			ui = self.ui

		if level:
			if isinstance(ui, str):
				ui, *tags = ui.split('#')

				ui1 = self.getUi(ui)
				if not ui1 or level==2:
					submenu_name = '{}_{}#{}'.format(ui, 'submenu', '#'.join(tags)).rstrip('#') #reformat as submenu w/tags. ie. 'polygons_submenu#edge' from 'polygons'
					ui1 = self.getUi(submenu_name) #in the case where a submenu exist without a parent menu.
					if not ui1:
						print (error_msg(ui))
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
				print (error_msg(ui))
				return None

		elif isinstance(ui, (list, set, tuple)):
			return [self.getUi(u) for u in ui]

		else:
			return ui


	def showAndConnect(self, ui, connectOnShow=True):
		'''Register the uiName in history as current, 
		set slot connections, and show the given ui.
		An override for the built-in show method.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			connectOnShow (bool): The the ui as connected.
		'''
		if connectOnShow:
			ui.connected = True
		ui.__class__.show(ui)


	def getCurrentUi(self) -> object:
		'''Get the current ui.

		Return:
			(obj) ui
		'''
		try:
			return self._currentUi

		except AttributeError as error:
			if len(self._loadedUi)==1: #if only one ui is loaded set that ui as current.
				ui = self._loadedUi.pop()
				self.setCurrentUi(ui)
				return ui
			elif self.dynui.endswith('.ui'): #if the ui location is set to a single ui, then load and set that ui as current.
				ui = self.loadUi(self.dynui)
				self.setCurrentUi(ui)
				return ui

			return None


	def setCurrentUi(self, ui) -> None:
		'''Register the specified dynamic UI as the current one in the application's history.
		Once registered, the `ui` object can be accessed through the `ui` property while it remains as the current UI.
		If the specified `ui` is already the current UI, the method simply returns without making any changes. 

		Parameters:
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


	def getPrevUi(self, allowDuplicates=False, allowCurrent=False, omitLevel=None, asList=False):
		'''Get ui from history.
		ex. _uiHistory list: ['previousName2', 'previousName1', 'currentName']

		Parameters:
			allowDuplicates (bool): Applicable when returning asList. Allows for duplicate names in the returned list.
			omitLevel (int)(list): Remove instances of the given ui level(s) from the results. Default is [] which omits nothing.
			allowCurrent (bool): Allow the currentName. Default is off.
			asList (bool): Returns the full list of previously called names. By default duplicates are removed.

		Return:
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


	@staticmethod
	def getDerivedType(widget, name=False, module='QtWidgets', inc=[], exc=[], filterByBaseType=False):
		'''Get the base class of a custom widget.
		If the type is a standard widget, the derived type will be that widget's type.

		Parameters:
			widget (str)(obj): QWidget or it's objectName.
			name (bool): Return the class or the class name.
			module (str): The name of the base class module to check for.
			inc (list): Widget types to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exc (list): Widget types to exclude. ie. ['QWidget', 'QAction', 'QLabel', 'QPushButton', 'QListWidget']
			filterByBaseType (bool): When using `inc`, or `exc`; Filter by base class name, or derived class name. ie. 'QLayout'(base) or 'QGridLayout'(derived)

		Return:
			(obj)(string)(None) class or class name if `name`. ie. 'QPushButton' from a custom widget with class name: 'PushButton'
		'''
		# print(widget.__class__.__mro__) #debug
		for c in widget.__class__.__mro__:
			if c.__module__==module or c.__module__.split('.')[-1]==module: #check for the first built-in class. ie. 'PySide2.QtWidgets' or 'QtWidgets'
				typ = c.__class__.__base__.__name__ if filterByBaseType else c
				if not (typ in exc and (typ in inc if inc else typ not in inc)):
					return typ.__name__ if name else typ


	def getWidget(self, name, ui=None):
		'''Case insensitive. Get the widget object/s from the given ui and name.

		Parameters:
			name (str): The object name of the widget. ie. 'b000'
			ui (str)(obj): ui, or name of ui. ie. 'polygons'. If no nothing is given, the current ui will be used.
							A ui object can be passed into this parameter, which will be used to get it's corresponding name.
		Return:
			(obj) if name:  widget object with the given name from the current ui.
				  if ui and name: widget object with the given name from the given ui name.
			(list) if ui: all widgets for the given ui.
		'''
		if ui is None or isinstance(ui, str):
			ui = self.getUi(ui)

		return next((w for w in ui.widgets if w.name==name), None)


	def getWidgetsByType(self, types, ui=None, derivedType=False):
		'''Get widgets of the given types.

		Parameters:
			types (str)(list): A widget class name, or list of widget class names. ie. 'QPushbutton' or ['QPushbutton', 'QComboBox']
			ui (str)(obj): Parent ui name, or ui object. ie. 'polygons' or <polygons>
							If no name is given, the current ui will be used.
			derivedType (bool): Get by using the parent class of custom widgets.

		Return:
			(list)
		'''
		if ui is None or isinstance(ui, str):
			ui = self.getUi(ui)

		typ = 'derivedType' if derivedType else 'type'
		return [w for w in ui.widgets if getattr(w, typ) in Iter.makeList(types)]


	def getWidgetName(self, widget=None, ui=None):
		'''Get the widget's stored string objectName.

		Parameters:
			widget (obj): The widget to get the object name of.
					If no widget is given, names of all widgets will be returned.
			ui (str)(obj): The parent ui, or ui name. ie. <polygons> or 'polygons'
					If no name is given, the current ui will be used.
		Return:
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

		Parameters:
			method (obj): The method in which to get the widget of.

		Return:
			(obj) widget. ie. <b000 widget> from <b000 method>.
		'''
		if not method:
			return None

		return next(iter(w for u in self._loadedUi for w in u.widgets if w.getSlot()==method), None)


	def getMethod(self, ui, widget=None):
		'''Get the method(s) associated with the given ui / widget.

		Parameters:
			ui (str)(obj): The ui name, or ui object. ie. 'polygons' or <polygons>
			widget (str)(obj): widget, widget's objectName, or method name.

		Return:
			if widget: corresponding method object to given widget.
			else: all of the methods associated to the given ui name as a list.

		Example:
			sb.getSlot('polygons', <b022>)() #call method <b022> of the 'polygons' class
		'''
		if not isinstance(ui, QtWidgets.QMainWindow):
			ui = self.getUi(ui)

		if widget is None: #get all methods for the given ui name.
			return [w.getSlot() for w in ui.widgets]

		elif isinstance(widget, str):
			return next(iter(w.getSlot() for w in ui.widgets if w.getSlot().__name__==widget), None)

		elif not widget in ui._widgets:
			self.initWidgets(ui, widget)

		return next(iter(w.getSlot() for w in ui.widgets if w.getSlot()==widget.getSlot()), None)


	def getSignals(self, w, d=True, exc=[]):
		'''Get all signals for a given widget.

		Parameters:
			w (str)(obj): The widget to get signals for.
			d (bool): Return signals from all derived classes instead of just the given widget class.
				ex. get: QObject, QWidget, QAbstractButton, QPushButton signals from 'QPushButton'
			exc (list): Exclude any classes in this list. ex. exc=[QtCore.QObject, 'QWidget']

		Return:
			(list)

		Example: getSignals(QtWidgets.QPushButton)
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

		Parameters:
			widgetType (str): Widget class name. ie. 'QPushButton'

		Return:
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

		Parameters:
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

		submenus = self.getUi(ui, [2]) #give level arg as a list to assure that a list is returned.
		for submenu in submenus:
			mainmenu = self.getUi(ui, 3)
			self.syncAllWidgets(submenu, mainmenu) #sync any submenu widgets with their main menu counterparts.


	def connectSlots(self, ui, widgets=None):
		'''Connect signals to slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			widgets (obj)(list): QWidget(s)
		'''
		if widgets is None:
			if ui.isConnected:
				return
			widgets = ui.widgets
		# print ('connectSlots:', ui.name, [w.objectName() for w in Iter.makeList(widgets)]) #debug

		for w in Iter.makeList(widgets): #convert 'widgets' to a list if it is not one already.
			# print ('           >:', w.name, w.getSlot()) #debug
			if w.getSlot() and w.signals:
				for s in w.signals:
					if not s:
						continue
					try:
						if isinstance(w.getSlot(), (list, set, tuple)):
							map(s.connect, w.getSlot()) #connect to multiple slots from a list.
						else:
							s.connect(w.getSlot()) #connect single slot (ex. main and cameras ui)

						s.connect(lambda *args, w=w: self._wgtHistory.append(w)) #add the widget to the widget history set on connect. (*args prevents 'w' from being overwritten by the parameter emitted by the signal.)

					except Exception as error:
						print(f'# Error: {__file__} in connectSlots\n#\t{ui.name} {w.name} {s} {w.getSlot()}\n#\t{error}.')

		ui.isConnected = True #set ui state as slots connected.


	def disconnectSlots(self, ui, widgets=None):
		'''Disconnect signals from slots for the widgets of the given ui.
		Works with both single slots or multiple slots given as a list.

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			widgets (obj)(list): QWidget
		'''
		# print ('disconnectSlots:', ui.name) #debug
		if widgets is None:
			if not ui.isConnected:
				return
			widgets = ui.widgets

		for w in Iter.makeList(widgets):  #convert 'widgets' to a list if it is not one already.
			# print ('           >:', w.name, w.getSlot()) #debug
			if w.getSlot() and w.signals:
				for s in w.signals:
					if not s:
						continue
					try:
						if isinstance(w.getSlot(), (list, set, tuple)):
							s.disconnect() #disconnect all #map(signal.disconnect, slot) #disconnect multiple slots from a list.
						else:
							s.disconnect(w.getSlot()) #disconnect single slot (main and cameras ui)

					except Exception as error:
						print(f'# Error: {__file__} in disconnectSlots\n#\t{ui.name} {w.name} {s} {w.getSlot()}\n#\t{error}.')

		ui.isConnected = False #set ui state as slots disconnected.


	def connect(self, widgets, signals, slots, clss=None):
		'''Connect multiple signals to multiple slots at once.

		Parameters:
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
				widgets = self.getWidgetsFromStr(self.getCurrentUi(), widgets, showError=True)

		#if the variables are not of a list type; convert them.
		widgets = Iter.makeList(widgets)
		signals = Iter.makeList(signals)
		slots = Iter.makeList(slots)

		for widget in widgets:
			for signal in signals:
				signal = getattr(widget, signal)
				for slot in slots:
					signal.connect(slot)


	def syncAllWidgets(self, frm, to, **kwargs):
		'''Extends setSynConnections method to set sync connections 
		for all widgets of the given pair of ui objects.

		Parameters:
			frm (obj): A previously loaded dynamic ui object to sync widgets from.
			to (obj): A previously loaded dynamic ui object to sync widgets to.
		'''
		for w1 in frm.widgets:
			try:
				w2 = self.getWidget(w1.name, to)
			except AttributeError as error:
				continue

			pair_id = hash((w1, w2))
			if pair_id in self._synced_pairs:
				continue

			self.syncWidgets(w1, w2, **kwargs)


	def syncWidgets(self, w1, w2, **kwargs):
		'''Set the initial signal connections that will call the _syncAttributes function on state changes.

		Parameters:
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

			pair_id = hash((w1, w2))
			self._synced_pairs.add(pair_id)

		except (AttributeError, KeyError) as error:
			# if w1 and w2: print ('# {}: {}.syncWidgets({}, {}): {}. args: {}, {} #'.format('KeyError' if type(error)==KeyError else 'AttributeError', __name__, w1.objectName(), w2.objectName(), error, w1, w2)) #debug
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

		Parameters:
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

		Parameters:
			*args = arg [0] (str) String of objectNames. - objectNames separated by ',' ie. 'b000-12,b022'
					arg [1:] dynamic ui object/s.  If no ui's are given, then the parent and child uis will be used.
			*kwargs = keyword: - the property to modify. ex. setText, setValue, setEnabled, setDisabled, setVisible, setHidden
					value: - intended value.

		Example:
			setWidgetAttrs('chk003', <ui1>, <ui2>, setText='Un-Crease')
		'''
		if not args[1:]:
			mainmenu = self.getUi(self.getCurrentUi(), 3)
			submenu = self.getUi(self.getCurrentUi(), 2)
			args = args+(mainmenu, submenu)

		for ui in args[1:]:
			widgets = self.getWidgetsFromStr(ui, args[0]) #getWidgetsFromStr returns a widget list from a string of objectNames.
			for property_, value in kwargs.items():
				[getattr(w, property_)(value) for w in widgets] #set the property state for each widget in the list.


	@staticmethod
	def unpackNames(nameString):
		'''Get a list of individual names from a single name string.
		If you are looking to get multiple objects from a name string, call 'getWidgetsFromStr' directly instead.

		Parameters:
			nameString = string consisting of widget names separated by commas. ie. 'v000, b004-6'

		Return:
			unpacked names. ie. ['v000','b004','b005','b006']

		Example: unpackNames('chk021-23, 25, tb001')
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

		Parameters:
			ui (obj): A previously loaded dynamic ui object.
			nameString (str): Widget object names separated by ','. ie. 's000,b004-7'. b004-7 specifies buttons b004-b007.
			showError (bool): Print an error message to the console if a widget is not found.

		Return:
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

		Parameters:
			w (obj): The widget to query.

		Return:
			(obj) QPoint
		'''
		return QtGui.QCursor.pos() - w.rect().center()


	@staticmethod
	def resizeAndCenterWidget(widget, paddingX=30, paddingY=6):
		'''Adjust the given widget's size to fit contents and re-center.

		Parameters:
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

		Parameters:
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

		Parameters:
			*args = dynamic ui object/s. If no ui's are given, then the current UI will be used.
			*kwargs = keyword: - the property to modify. ex. setChecked, setUnChecked, setEnabled, setDisabled, setVisible, setHidden
						value: string of objectNames - objectNames separated by ',' ie. 'b000-12,b022'
		Example:
			toggleWidgets(<ui1>, <ui2>, setDisabled='b000', setUnChecked='chk009-12', setVisible='b015,b017')
		'''
		if not args:
			mainmenu = self.getUi(self.getCurrentUi(), 3)
			submenu = self.getUi(self.getCurrentUi(), 2)
			args = [submenu, mainmenu]

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

		Parameters:
			checkboxes (str)(list): 3 or 4 (or six with explicit negative values) checkboxes.
			axis (str): Axis to set. Valid text: '-','X','Y','Z','-X','-Y','-Z' ('-' indicates a negative axis in a four checkbox setup)

		ex call: setAxisForCheckBoxes('chk000-3', '-X') #optional ui arg for the checkboxes
		'''
		if isinstance(checkboxes, (str)):
			if ui is None:
				ui = self.getCurrentUi()
			checkboxes = self.getWidgetsFromStr(ui, checkboxes)

		prefix = '-' if '-' in axis else '' #separate the prefix and axis
		coord = axis.strip('-')

		for chk in checkboxes:
			if any([chk.text()==prefix, chk.text()==coord, chk.text()==prefix+coord]):
				chk.setChecked(True)


	def getAxisFromCheckBoxes(self, checkboxes, ui=None):
		'''Get the intended axis value as a string by reading the multiple checkbox's check states.

		Parameters:
			checkboxes (str)(list): 3 or 4 (or six with explicit negative values) checkboxes. Valid text: '-','X','Y','Z','-X','-Y','-Z' ('-' indicates a negative axis in a four checkbox setup)

		Return:
			(str) axis value. ie. '-X'		

		ex call: getAxisFromCheckBoxes('chk000-3')
		'''
		if isinstance(checkboxes, (str)):
			if ui is None:
				ui = self.getCurrentUi()
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

		Parameters:
			obj (obj)(list): The obj(s) to add to the protected list.
			clear (bool): Clear the set before adding any given object(s).

		Return:
			(list) protected objects.
		'''
		if clear:
			self._gcProtect.clear()

		for o in Iter.makeList(obj):
			self._gcProtect.add(o)

		return self._gcProtect


	def isWidget(self, obj):
		'''Returns True if the given obj is a valid widget.

		Parameters:
			obj (obj): An object to query.

		Return:
			(bool)
		'''
		try:
			return issubclass(obj, QtWidgets.QWidget)
		except TypeError:
			return issubclass(obj.__class__, QtWidgets.QWidget)


	@staticmethod
	def getWidgetAt(pos, topWidgetOnly=True):
		'''Get visible and enabled widget(s) located at the given position.
		As written, this will disable `TransparentForMouseEvents` on each widget queried.

		Parameters:
			pos (QPoint) = The global position at which to query.
			topWidgetOnly (bool): Return only the top-most widget, 
				otherwise widgets are returned in the order in which they overlap.
				Disabling this option will cause overlapping windows to flash as 
				their attribute is changed and restored.
		Return:
			(obj)(list) list if not topWidgetOnly.

		Example: getWidgetAt(QtGui.QCursor.pos())
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

		Parameters:
			widget (obj): QWidget
			objectNames (bool): Return as objectNames.

		Return:
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

		Parameters:
			widget (obj): QWidget
			index (int): Last index is top level.

		Return:
			(QWidget)
		'''
		return self.getParentWidgets()[index]


	@staticmethod
	def getAllWindows(name=None):
		'''Get Qt windows.

		Parameters:
			name (str): Return only windows having the given object name.

		Return:
			(list) windows.
		'''
		return [w for w in QtWidgets.QApplication.allWindows() if (name is None) or (w.objectName()==name)]


	@staticmethod
	def getAllWidgets(name=None):
		'''Get Qt widgets.

		Parameters:
			name (str): Return only widgets having the given object name.

		Return:
			(list) widgets.
		'''
		return [w for w in QtWidgets.QApplication.allWidgets() if (name is None) or (w.objectName()==name)]


	def messageBox(self, string, messageType='', location='topMiddle', timeout=1):
		'''Spawns a message box with the given text.
		Supports HTML formatting.
		Prints a formatted version of the given string to console, stripped of html tags, to the console.

		Parameters:
			messageType (str): The message context type. ex. 'Error', 'Warning', 'Note', 'Result'
			location (str)(point) = move the messagebox to the specified location. Can be given as a qpoint or string value. default is: 'topMiddle'
			timeout (int): time in seconds before the messagebox auto closes.
		'''
		if messageType:
			string = f'{messageType.capitalize()}: {string}'

		try:
			self._messageBox.location = location
		except AttributeError:
			self._messageBox = self.MessageBox(self.parent())
			self._messageBox.location = location
		self._messageBox.timeout = timeout

		from re import sub
		print(f"# {sub('<.*?>', '', string)}") #strip everything between '<' and '>' (html tags)

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
			self._progressBar = ProgressBar(self.parent())

			try:
				self.ui.progressBar.step1
			except AttributeError:
				pass

			return self._progressBar


	@staticmethod
	def invertOnModifier(value):
		'''Invert a numerical or boolean value if the alt key is pressed.

		Parameters:
			value (int, float, bool) = The value to invert.
		
		Return:
			(int, float, bool)
		'''
		modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
		if not modifiers in (QtCore.Qt.AltModifier, QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
			return value

		if type(value) in (int, float):
			result = abs(value) if value<0 else -value
		elif type(value)==bool:
			result = True if value else False

		return result

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

if __name__=='__main__':

	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	from uitk.slots.polygons import Polygons
	sb = Switchboard(slots='slots/maya') #set relative paths, and explicity set the slots class instead of providing a path like: slots='slots/maya', which in this case would produce the same result with just a little more overhead.
	ui = sb.polygons #get the ui by it's name.
	ui.show()

	print ('current ui:', sb.ui)
	print ('current ui name:', sb.ui.name)
	print ('connected state:', ui.isConnected)
	print ('slots:', ui.slots)
	print ('method tb000:', ui.tb000.getSlot())
	print ('widget from method tb000:', sb.getWidgetFromMethod(ui.tb000.getSlot()))
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

	# def __getattr__(self, attr_name):
	# 	found_widget = self.sb._getWidgetFromUi(self, attr_name)
	# 	if found_widget:
	# 		self.sb.initWidgets(self, found_widget)
	# 		return found_widget
	# 	raise AttributeError(f'{self.__class__.__name__} has no attribute `{attr_name}`')

# def getprefix(widget):
# 		'''Query a widgets prefix.
# 		A valid prefix is returned when the given widget's objectName startswith an alphanumeric char, 
# 		followed by at least three integers. ex. i000 (alphanum,int,int,int)

# 		Parameters:
# 			widget (str)(obj): A widget or it's object name.

# 		Return:
# 			(str)
# 		'''
# 		prefix=''
# 		if not isinstance(widget, (str)):
# 			widget = widget.objectName()
# 		for char in widget:
# 			if not char.isdigit():
# 				prefix = prefix+char
# 			else:
# 				break

# 		i = len(prefix)
# 		integers = [c for c in widget[i:i+3] if c.isdigit()]
# 		if len(integers)>2 or len(widget)==i:
# 			return prefix

	# def setAttributes(self, obj=None, order=['setVisible'], **kwargs):
	# 	'''Set attributes for a given object.

	# 	Parameters:
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