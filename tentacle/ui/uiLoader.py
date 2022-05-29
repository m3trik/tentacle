# !/usr/bin/python
# coding=utf-8
import sys, os.path

from PySide2 import QtCore, QtUiTools, QtWidgets
# from PySide2.QtUiTools import QUiLoader



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

	def __init__(self, uiDir=os.path.abspath(os.path.dirname(__file__))):
		QtUiTools.QUiLoader.__init__(self)
		'''Load the ui files and any custom widgets.

		:Parameters:
			uiDir (str) = The path to the directory containing ui files.

		ex. call: widgets = [w for w in widgets_mod.__dict__.values() if type(w).__name__=='ObjectType'] #get any custom widgets to register.
				  uiDict = uiLoader.loadUI(uiLoader.uiDir, widgets=widgets) #add all ui from the directory and subdirectories of this file.
		'''
		self.uiDir = uiDir


	@property
	def uiDict(self):
		'''Get the full ui dict.
		'''
		try:
			return self._uiDict

		except AttributeError as error:
			self._uiDict = {}
			return self._uiDict


	def formatFilepath(self, string, returnType=''):
		'''Format a full path to file string from '\' to '/'.
		When a returnType arg is given, the correlating section of the string will be returned.

		:Parameters:
			string (str) = The file path string to be formatted.
			returnType (str) = valid: 'path' (path without file), 'dir' (dir name), 'file'(name+ext), 'name', 'ext', if '' is given, the fullpath will be returned.

		:Return:
			(str)
		'''
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

		return string


	def getUiLevelFromPath(self, filePath):
		'''Get the UI level using it's directory's naming convention.
		The default level is 0.

		:Parameters:
			filePath (str) = The ui's full filepath. ie. 'O:/Cloud/Code/_scripts/tentacle/tentacle/ui/uiLevel_0/init.ui'

		:Return:
			(int)
		'''
		uiFolder = self.formatFilepath(filePath, 'dir')

		try:
			uiLevel = int(uiFolder.strip('uiLevel_'))

		except KeyError as error: #not a valid ui dir.
			uiLevel = 0

		return uiLevel


	def registerWidgets(self, widgets):
		'''Register any custom widgets using the module names.
		'''
		for w in widgets:
			try:
				self.registerCustomWidget(w)

			except Exception as error:
				print ('# Error: {}.registerWidgets(): {} #'.format(__name__, error))


	def loadUI(self, uiDir='', widgets=[]):
		'''Extends the fuctionality of the 'addUi' method to support adding all ui recursively from a given directory.

		:Parameters:
			uiDir (str) = The absolute directory path to the uiFiles. Default is the directory of this module.

		ex. call: uiLoader.addAllUI(uiLoader.uiDir)
		'''
		uiDir = uiDir if uiDir else self.uiDir

		self.registerWidgets(widgets)

		for dirPath, dirNames, filenames in os.walk(uiDir):
			uiFiles = ['{}/{}'.format(dirPath, f) for f in filenames if f.endswith('.ui')]
			self.addUi(uiFiles)

		return self.uiDict


	def addUi(self, ui, widgets=[]):
		'''Load and add ui files to the uiDict.
		If the ui's directory name is in the form of 'uiLevel_x' then a 'level' key will be added to the uiDict with a value of x.

		:Parameters:
			ui (str)(list) = The full path to a dynamic ui.

		ie. {'polygons':{'ui':<ui obj>, 'level':<int>}} (the ui level is it's hierarchy based on the ui file's dir location)
		ex. call: self.ui = uiLoader.loadUi(uiLoader.uiPath, 'imtools.ui')['imtools'] #load a single ui.
		'''
		uiFiles = [ui] if isinstance(ui, str) else ui  #assure uiFiles in a list.

		self.registerWidgets(widgets)

		for filePath in uiFiles:
			uiName = self.formatFilepath(filePath, 'name')

			#load the dynamic ui file.
			ui = self.load(filePath)

			uiLevel = self.getUiLevelFromPath(filePath)

			self.uiDict[uiName] = {
				'ui': ui, #the ui object.
				'uiLevel': {'base': uiLevel}, #the ui level as an integer value. (the ui level is it's hierarchy)
				'size': [ui.frameGeometry().width(), ui.frameGeometry().height()],
				'state': 0, #initialization state.
			}

		return self.uiDict









if __name__ == "__main__":

	sys.exit(qApp.exec_())

else:
	uiLoader = UiLoader()

#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated:


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