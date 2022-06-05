# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect

from PySide2.QtWidgets import QApplication
from PySide2 import QtUiTools

try: import shiboken2
except: from PySide2 import shiboken2



# ------------------------------------------------
#	Load Dynamic Ui files
# ------------------------------------------------
class UiLoader(QtUiTools.QUiLoader):
	'''Load and maintain a dict of loaded dynamic ui files and related info.

	Ui files are searched for in the directory of this module.
	Custom widget modules are searched for in a sub directory named 'widgets'. 
	naming convention for custom widgets: <first char lowercase>.py module. <first char uppercase> for the corresponding widget class. ie. calss Label in label.py module.

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

	:uiDict Structure:
		uiDict = {
			'<uiName>':{
				'ui':<ui obj>,
				'uiLevel': {'base': <int>}, #the ui level as an integer. (the ui level is it's hierarchy)
				'size': [<int>, <int>],
				'state': <int>, #initialization state. (default:0)
		}
	'''
	qApp = QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QApplication(sys.argv)

	def __init__(self, parent=None, uiToLoad=None, widgetsToRegister=None):
		QtUiTools.QUiLoader.__init__(self, parent)
		'''Load dynamic ui files and any custom widgets.

		:Parameters:
			uiToLoad (str)(list) = The path to a directory containing ui files.
			widgetsToRegister (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
						or the widget(s) themselves.

		ex. call:	from uiLoader import UiLoader

					path = os.path.abspath(os.path.dirname(__file__))
					uiLoader = UiLoader(uiToLoad=path, widgetsToRegister=path+'/widgets')

					transform_ui = uiLoader.transform
					widgets = transform_ui.widgets()

					qApp = QApplication.instance()
					transform_ui.show()
					sys.exit(qApp.exec_())
		'''
		self.defaultDir = os.path.abspath(os.path.dirname(__file__))
		self.uiToLoad = uiToLoad if uiToLoad else self.defaultDir
		self.widgetsToRegister = widgetsToRegister if widgetsToRegister else self.defaultDir
		self.registeredWidgets=[] #maintain a list of previously registered widgets.

		for path in self.list_(self.uiToLoad): #assure uiToLoad is a list.
			self.setWorkingDirectory(path)
			self.loadUi(path)


	@property
	def uiDict(self):
		'''Get the full ui dict.
		'''
		try:
			return self._uiDict

		except AttributeError as error:
			self._uiDict = {}
			return self._uiDict


	def loadUi(self, path, widgets=None, recursive=True):
		'''Load and add ui files to the uiDict.
		If the ui's directory name is in the form of 'uiLevel_x' then a 'level' key will be added to the uiDict with a value of x.

		:Parameters:
			path (str)(list) = The full path(s) to a dynamic ui.
			widgets (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
						or the widget(s) themselves.
			recursive (bool) = Search the given path(s) recursively.

		:Return:
			{dict} uiDict. ex. {'some_ui':{'ui':<ui obj>, 'level':<int>}} (the ui level is it's hierarchy based on the ui file's dir location)

		ex. call: uiDict = uiLoader.loadUi([list ui filepaths]) #load a list of ui's.
		ex. call: uiDict = uiLoader.loadUi(uiLoader.defaultDir+'/some_ui.ui') #load a single ui using the path of this module.
		ex. call: uiDict = uiLoader.loadUi(__file__+'/some_ui.ui') #load a single ui using the path of the calling module.
		'''
		widgets = widgets if widgets else self.widgetsToRegister

		self.registerWidgets(widgets)

		for path in self.list_(path): #assure path is a list.

			uiName = self.formatFilepath(path, 'name')

			if uiName:
				ui = self.load(path) #load the dynamic ui file.
				uiLevel = self.getUiLevelFromDir(path)

				#set attributes
				setattr(self, uiName, ui) #set the ui as an attribute of the uiLoader so that it can be accessed as uiLoader.<some_ui>
				ui.widgets = lambda ui=ui: self.getWidgetsFromUi(ui) #set a 'widgets' attribute to return the ui's widgets. ex. ui.widgets()

				self.uiDict[uiName] = {
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

		return self.uiDict


	def getUi(self, uiName):
		'''Get a previously loaded ui object using it's name.

		:Parameters:
			uiName (str) = The name of the ui you are wanting to return.

		:Return:
			(obj) ui

		ex. call: some_ui = uiLoader.getUi('some_ui')
		'''
		try:
			return self.uiDict[uiName]['ui']

		except KeyError as error:
			return None


	def getUiLevelFromDir(self, filePath):
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


	def getWidgetsFromUi(self, ui):
		'''Get all widgets of the given ui.
		Used by the ui.widgets attribute and can be accessed using: some_ui.widgets()

		:Property:
			ui.widgets

		:Parameters:
			ui (obj)(str) = The ui, or name of the ui you are wanting to get widgets for.

		:Return:
			(list) widget objects
		'''
		ui = ui if not isinstance(ui, str) else self.getUi(ui)

		try:
			return [w for w in ui.__dict__.values() if shiboken2.isValid(w)]

		except AttributeError as error:
			return []


	def getWidgetsFromDir(self, path):
		'''Get all widget class objects from a given directory.

		:Parameters:
			path (str) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'

		:Return:
			(list) widgets
		'''
		path = self.formatFilepath(path, 'path')
		mod_name = self.formatFilepath(path, 'name')
		mod_ext = self.formatFilepath(path, 'ext')

		self.addPluginPath(path) #sys.path.append(path)
		modules={}

		if mod_name: #if the path contains a module name, get only that module.
			mod = importlib.import_module(mod_name)

			cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

			for cls_name, cls_mem in cls_members:
				modules[cls_name] = cls_mem


		else: #get all modules in the given path.
			for module in os.listdir(path):

				mod_name = module[:-3]
				mod_ext = module[-3:]

				if module == '__init__.py' or mod_ext != '.py':
					continue

				mod = importlib.import_module(mod_name)

				cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

				for cls_name, cls_mem in cls_members:
					modules[cls_name] = cls_mem

			del module

		widgets = [w for w in modules.values() if type(w).__name__=='ObjectType' and shiboken2.isValid(w)] #get all imported widget classes as a dict.
		return widgets


	def registerWidgets(self, widgets):
		'''Register any custom widgets using the module names.

		:Parameters:
			widgets (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
						or the widget(s) themselves. 

		ex. call: registerWidgets(<class 'widgets.menu.Menu'>) #register using widget class object.
		ex. call: registerWidgets('O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets/menu.py') #register using path to widget module.
		'''
		if isinstance(widgets, (str)):
			widgets = self.getWidgetsFromDir(widgets)

		for w in self.list_(widgets): #assure widgets is a list.

			if w in self.registeredWidgets:
				continue

			try:
				self.registerCustomWidget(w)
				self.registeredWidgets.append(w)

			except Exception as error:
				print ('# Error: {}.registerWidgets(): {} #'.format(__name__, error))


	def formatFilepath(self, string, returnType=''):
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
		if isinstance(x, (list, tuple, set)):
			return x
		elif isinstance(x, dict):
			return list(x)
		else:
			return [x]









if __name__ == "__main__":

	path = os.path.abspath(os.path.dirname(__file__))
	uiLoader = UiLoader(uiToLoad=path, widgetsToRegister=path+'/widgets')

	transform_ui = uiLoader.transform
	widgets = transform_ui.widgets()

	transform_ui.show()
	qApp = QApplication.instance()
	sys.exit(qApp.exec_())









#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated:


	# def loadUiFromDir(self, path='', widgets=None, recursive=False):
	# 	'''Extends the fuctionality of the 'addUi' method to support adding all ui from a given directory.

	# 	:Parameters:
	# 		path (str)(list) = The absolute directory path to the uiFiles. Default is the directory of this module.
	# 		widgets (str)(obj)(list) = A full filepath to a dir containing widgets or to the widget itself. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/widgets'
	# 					or the widget(s) themselves. 

	# 	:Return:
	# 		{dict} uiDict. ex. {'some_ui':{'ui':<ui obj>, 'level':<int>}} (the ui level is it's hierarchy based on the ui file's dir location)

	# 	ex. call: uiDict = uiLoader.loadUiFromDir(uiLoader.defaultDir)
	# 	'''
	# 	path = path if path else self.uiToLoad
	# 	paths = path if not isinstance(path, str) else [path]  #assure path is a list.

	# 	widgets = widgets if widgets else self.widgetsToRegister
	# 	self.registerWidgets(widgets)

	# 	for path in paths:
	# 		path = self.formatFilepath(path, 'path')
	# 		for dirPath, dirNames, filenames in os.walk(path):
	# 			uiFiles = ['{}/{}'.format(dirPath, f) for f in filenames if f.endswith('.ui')]
	# 			self.loadUi(uiFiles)
	# 			if not recursive:
	# 				break

	# 	return self.uiDict


		# register any custom widgets.
		# import tentacle.ui.widgets
		# widgets = [w for w in tentacle.ui.widgets.__dict__.values() if type(w).__name__=='ObjectType']
		# self.registerWidgets(widgets)

		# initialize uiDict by setting keys for the ui files.
		# uiPath = os.path.dirname(os.path.abspath(__file__)) #get absolute path from dir of this module
		# for dirPath, dirNames, filenames in os.walk(uiPath):
		# 	uiFiles = [f for f in filenames if f.endswith('.ui')]
		# 	self.addUi(dirPath, uiFiles)

	# def loadUi(name):
	# 	#arg: string
	# 	#returns: dynamic ui object
	# 	uiPath = "ui/"+name+".ui"
	# 	uiFile = os.path.expandvars(uiPath)
	# 	qtui = QUiLoader().load(uiFile)
	# 	return qtui

# def __init__(self, parent=None):
# 		super().__init__(parent)
# 		'''Load the ui files and any custom widgets.
# 		'''
# 		uiPath = os.path.dirname(os.path.abspath(__file__)) #get absolute path from dir of this module

# 		# register any custom widgets.
# 		widgetPath = os.path.join(os.path.dirname(uiPath), uiDir+'\\'+WIDGET_DIR) #get the path to the widget directory.
# 		moduleNames = [file_.replace('.py','',-1) for file_ in os.listdir(widgetPath) if file_.startswith(WIDGET_MODULE_PREFIX) and file_.endswith('.py')] #format names using the files in path.
# 		self.registerWidgets(moduleNames)

# 		# initialize _sbDict by setting keys for the ui files.
# 		for dirPath, dirNames, filenames in os.walk(uiPath):
# 			uiFiles = [f for f in filenames if f.endswith('.ui')]
# 			self.addUi(dirPath, uiFiles)



# def registerWidgets(self, moduleNames):
# 		'''Register any custom widgets using the module names.
# 		'''
# 		for m in moduleNames:
# 			className = m[:1].capitalize()+m[1:] #capitalize first letter of module name to convert to class name
# 			path = '{}.{}.{}'.format(WIDGET_DIR, m, className)
# 			class_ = locate(path)

# 			if class_:
# 				self.registerCustomWidget(class_)
# 			else:
# 				raise ImportError, path