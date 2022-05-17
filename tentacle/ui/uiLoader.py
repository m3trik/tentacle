# !/usr/bin/python
# coding=utf-8
import sys, os.path

from PySide2 import QtCore, QtUiTools, QtWidgets



# ------------------------------------------------
#	Load Dynamic Ui files
# ------------------------------------------------
class UiLoader(QtUiTools.QUiLoader):
	'''Load and maintain a dict of loaded dynamic ui files and related info.

	Ui files are searched for in the directory of this module.
	Custom widget modules are searched for in a sub directory named 'widgets'. 
	naming convention for custom widgets: <first char lowercase>.py module. <first char uppercase> for the corresponding widget class. ie. calss Label in label.py module.

	structure:
		uiDict = {
			'<uiName>':{'ui':<ui obj>, 'level':<int>}
		}
	'''
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	def __init__(self, uiPath=os.path.dirname(os.path.abspath(__file__)), uiFolder='ui'):
		QtUiTools.QUiLoader.__init__(self)
		'''Load the ui files and any custom widgets.
		'''
		self.uiFolder = uiFolder
		self.uiPath = uiPath

		# register any custom widgets.
		import tentacle.ui.widgets
		widgets = [w for w in tentacle.ui.widgets.__dict__.values() if type(w).__name__=='ObjectType']
		self.registerWidgets(widgets)

		# initialize uiDict by setting keys for the ui files.
		for dirPath, dirNames, filenames in os.walk(self.uiPath):
			uiFiles = [f for f in filenames if f.endswith('.ui')]
			self.addUi(dirPath, uiFiles)


	@property
	def uiDict(self):
		'''Get the full ui dict.
		'''
		try:
			return self._uiDict

		except AttributeError as error:
			self._uiDict = {}
			return self._uiDict


	def registerWidgets(self, widgets):
		'''Register any custom widgets using the module names.
		'''
		for w in widgets:
			try:
				self.registerCustomWidget(w)

			except Exception as error:
				print ('{}.registerWidgets(): {}'.format(__name__, error))


	def addUi(self, dirPath, uiFiles):
		'''Load ui files and add them to the uiDict.

		:Parameters:
			dirPath (str) = The absolute directory path to the uiFiles.
			uiFiles (str)(list) = Dynamic ui filename(s).

		ie. {'polygons':{'ui':<ui obj>, 'level':<int>}} (the ui level is it's hierarchy based on the ui file's dir location)
		'''
		uiFiles = [uiFiles] if isinstance(uiFiles, str) else uiFiles

		for filename in uiFiles:
			uiName = filename.replace('.ui','') #get the name from fileName by removing the '.ui' extension.

			#load the dynamic ui file.
			path = os.path.join(dirPath, filename)
			ui = self.load(path)

			#get the ui level from it's directory location.
			d = dirPath.split('\\'+self.uiFolder+'\\')[-1] #ie. base_menus from fullpath\ui\base_menus
			try:
				uiLevel = int(d.strip('uiLevel_'))
				self.uiDict[uiName] = {'ui':ui, 'level':uiLevel}

			except KeyError as error: #not a valid ui dir.
				pass; #print ('{}.addUi(): {}'.format(__name__, error))









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated:

# def __init__(self, parent=None):
# 		super().__init__(parent)
# 		'''Load the ui files and any custom widgets.
# 		'''
# 		uiPath = os.path.dirname(os.path.abspath(__file__)) #get absolute path from dir of this module

# 		# register any custom widgets.
# 		widgetPath = os.path.join(os.path.dirname(uiPath), uiFolder+'\\'+WIDGET_DIR) #get the path to the widget directory.
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