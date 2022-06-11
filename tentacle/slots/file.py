# !/usr/bin/python
# coding=utf-8
from slots import Slots



class File(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		#set the text for the open last file button to the last file's name.
		mostRecentFile = self.getRecentFiles(0)
		self.file_submenu_ui.b001.setText(self.getNameFromFullPath(mostRecentFile)) if mostRecentFile else self.file_submenu_ui.b001.setVisible(False)

		dh = self.file_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
		dh.contextMenu.add(self.tcl.wgts.PushButton, setObjectName='tb000', setText='Save', setToolTip='Save the current file.')
		dh.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl001', setText='Minimize App', setToolTip='Minimize the main application.')
		dh.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl002', setText='Maximize App', setToolTip='Restore the main application.')
		dh.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl003', setText='Close App', setToolTip='Close the main application.')

		cmb005 = self.file_ui.cmb005
		cmb005.contextMenu.add('QPushButton', setObjectName='b001', setText='Last', setToolTip='Open the most recent file.')
		cmb005.addItems_(dict(zip(self.getRecentFiles(timestamp=True), self.getRecentFiles(timestamp=False))), "Recent Files", clear=True)

		cmb006 = self.file_ui.cmb006
		cmb006.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb001', setToolTip='Current project directory root.')
		cmb006.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl000', setText='Set', setToolTip='Set the project directory.')
		cmb006.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl004', setText='Root', setToolTip='Open the project directory.')
		cmb006.contextMenu.cmb001.addItems_(self.getRecentProjects(), "Recent Projects", clear=True)

		tb000 = self.file_ui.draggable_header.contextMenu.tb000
		tb000.contextMenu.add('QCheckBox', setText='Wireframe', setObjectName='chk000', setToolTip='Set view to wireframe before save.')
		tb000.contextMenu.add('QCheckBox', setText='Increment', setObjectName='chk001', setChecked=True, setToolTip='Append and increment a unique integer value.')
		tb000.contextMenu.add('QCheckBox', setText='Quit', setObjectName='chk002', setToolTip='Quit after save.')


	def referenceSceneMenu(self, clear=False):
		'''
		'''
		try:
			if clear:
				del self._referenceSceneMenu
			return self._referenceSceneMenu

		except AttributeError as error:
			menu = self.tcl.wgts.Menu(self.file_ui.lbl005)
			for i in self.getWorkspaceScenes(fullPath=True): #zip(self.getWorkspaceScenes(fullPath=False), self.getWorkspaceScenes(fullPath=True)):
				chk = menu.add(self.tcl.wgts.CheckBox, setText=i)
				chk.toggled.connect(lambda state, scene=i: self.referenceScene(scene, not state))

				# if chk.sizeHint().width() > menu.sizeHint().width():
				# 	chk.setMinimumSize(chk.sizeHint().width(), chk.sizeHint().height())

			self.sb.setStyleSheet_(menu.childWidgets, style='dark') # self.tcl.childEvents.addWidgets(self.tcl.sb.getUiName(), menu.childWidgets)

			self._referenceSceneMenu = menu
			return self._referenceSceneMenu


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.file_ui.draggable_header


	def lbl005(self):
		'''Reference
		'''
		self.referenceSceneMenu().show()


	@Slots.hideMain
	def b001(self):
		'''Recent Files: Open Last
		'''
		# files = [file_ for file_ in (list(reversed(pm.optionVar(query='RecentFilesList')))) if "Autosave" not in file_]

		# force=True
		# if str(mel.eval("file -query -sceneName -shortName;")):
		# 	force=False #if sceneName, prompt user to save; else force open
		# pm.openFile(files[0], open=1, force=force)

		self.cmb005(index=1)


	@Slots.hideMain
	def b007(self):
		'''Import file
		'''
		self.cmb003(index=1)


	@Slots.hideMain
	def b008(self):
		'''Export Selection
		'''
		self.cmb004(index=1)


	@staticmethod
	def getAbsoluteFilePaths(directory, endingWith=[]):
		'''Get the absolute paths of all the files in a directory and it's sub-folders.

		directory (str) = Root directory path.
		endingWith (list) = Extension types (as strings) to include. ex. ['mb', 'ma']
		
		:Return:
			(list) absolute file paths
		'''
		import os

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
	def fileNameTimeStamp(files, detach=False, stamp='%m-%d-%Y  %H:%M'):
		'''Attach a modified timestamp and date to given file path(s) and sort accordingly.

		:Parameters:
			files (str)(list) = The full path to a file. ie. 'C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'
			detach (bool) = Remove a previously attached time stamp.
			stamp (str) = The time stamp format.

		:Return:
			(list) ie. ['16:46  11-09-2021  C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'] from ['C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb']
		'''
		from datetime import datetime
		import os.path

		files = [files] if not isinstance(files, (list, tuple, set)) else files

		if detach:
			result = [''.join(f.split()[2:]) for f in files]

		else:
			result=[]
			for f in files:
				try:
					result.append('{}  {}'.format(datetime.fromtimestamp(os.path.getmtime(f)).strftime(stamp), f))
				except (FileNotFoundError, OSError) as error:
					continue
			result = list(reversed(sorted(result)))

		return result









# -----------------------------------------------
# Notes
# -----------------------------------------------



# deprecated: