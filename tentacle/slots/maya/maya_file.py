# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class File(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		#set the text for the open last file button to the last file's name.
		mostRecentFile = File.getRecentFiles(0)
		self.file_submenu_ui.b001.setText(self.getNameFromFullPath(mostRecentFile)) if mostRecentFile else self.file_submenu_ui.b001.setVisible(False)

		ctx = self.file_ui.draggable_header.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
		ctx.add(self.tcl.wgts.PushButton, setObjectName='tb000', setText='Save', setToolTip='Save the current file.')
		ctx.add(self.tcl.wgts.Label, setObjectName='lbl001', setText='Minimize App', setToolTip='Minimize the main application.')
		ctx.add(self.tcl.wgts.Label, setObjectName='lbl002', setText='Maximize App', setToolTip='Restore the main application.')
		ctx.add(self.tcl.wgts.Label, setObjectName='lbl003', setText='Close App', setToolTip='Close the main application.')

		cmb = self.file_ui.draggable_header.contextMenu.cmb000
		items = []
		cmb.addItems_(items, 'Maya File Editors')

		cmb = self.file_ui.cmb002
		ctx = cmb.contextMenu
		autoSaveState = pm.autoSave(q=True, enable=True) #set the initial autosave state.
		autoSaveInterval = pm.autoSave(q=True, int=True)
		autoSaveAmount = pm.autoSave(q=True, maxBackups=True)
		ctx.add('QPushButton', setObjectName='b000', setText='Open Directory', setToolTip='Open the autosave directory.') #open directory
		ctx.add('QPushButton', setObjectName='b002', setText='Delete All', setToolTip='Delete all autosave files.') #delete all
		ctx.add('QCheckBox', setText='Autosave', setObjectName='chk006', setChecked=autoSaveState, setToolTip='Set the autosave state as active or disabled.') #toggle autosave
		ctx.add('QSpinBox', setPrefix='Amount: ', setObjectName='s000', setMinMax_='1-100 step1', setValue=autoSaveAmount, setHeight_=20, setToolTip='The number of autosave files to retain.') #autosave amount
		ctx.add('QSpinBox', setPrefix='Interval: ', setObjectName='s001', setMinMax_='1-60 step1', setValue=autoSaveInterval/60, setHeight_=20, setToolTip='The autosave interval in minutes.') #autosave interval
		ctx.chk006.toggled.connect(lambda s: pm.autoSave(enable=s, limitBackups=True))
		ctx.s000.valueChanged.connect(lambda v: pm.autoSave(maxBackups=v, limitBackups=True))
		ctx.s001.valueChanged.connect(lambda v: pm.autoSave(int=v*60, limitBackups=True))
		cmb.addItems_(File.getRecentAutosave(appendDatetime=True), 'Recent Autosave', clear=True)

		cmb = self.file_ui.cmb003
		cmb.addItems_(['Import file', 'Import Options', 'FBX Import Presets', 'Obj Import Presets'], "Import")

		cmb = self.file_ui.cmb004
		items = ['Export Selection', 'Send to Unreal', 'Send to Unity', 'GoZ', 'Send to 3dsMax: As New Scene', 'Send to 3dsMax: Update Current', 
				'Send to 3dsMax: Add to Current', 'Export to Offline File', 'Export Options', 'FBX Export Presets', 'Obj Export Presets']
		cmb.addItems_(items, 'Export')

		cmb = self.file_ui.cmb005
		ctx = cmb.contextMenu
		cmb.addItems_(File.getRecentFiles(), "Recent Files", clear=True)
		ctx.add('QPushButton', setObjectName='b001', setText='Last', setToolTip='Open the most recent file.')

		ctx = self.file_ui.cmb006.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb001', setToolTip='Current project directory root.')
		ctx.add(self.tcl.wgts.Label, setObjectName='lbl000', setText='Set', setToolTip='Set the project directory.')
		ctx.add(self.tcl.wgts.Label, setObjectName='lbl004', setText='Root', setToolTip='Open the project directory.')

		cmb = self.file_ui.cmb006.contextMenu.cmb001
		cmb.addItems_(File.getRecentProjects(), "Recent Projects", clear=True)

		ctx = self.file_ui.draggable_header.contextMenu.tb000.contextMenu
		ctx.add('QCheckBox', setText='Wireframe', setObjectName='chk000', setToolTip='Set view to wireframe before save.')
		ctx.add('QCheckBox', setText='Increment', setObjectName='chk001', setChecked=True, setToolTip='Append and increment a unique integer value.')
		ctx.add('QCheckBox', setText='Quit', setObjectName='chk002', setToolTip='Quit after save.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.file_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.file_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				mel.eval('') #
			if text=='':
				mel.eval('') #
			if text=='':
				mel.eval('') #
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Recent Projects
		'''
		cmb = self.file_ui.cmb006.contextMenu.cmb001

		if index>0:
			pm.mel.setProject(cmb.items[index]) #mel.eval('setProject "'+items[index]+'"')
			cmb.setCurrentIndex(0)


	@Slots.message
	def cmb002(self, index=-1):
		'''Recent Autosave
		'''
		cmb = self.file_ui.cmb002

		if index>0:
			file = Slots.fileTimeStamp(cmb.items[index], detach=True)
			pm.openFile(file, open=1, force=True)
			cmb.setCurrentIndex(0)


	def cmb003(self, index=-1):
		'''Import
		'''
		cmb = self.file_ui.cmb003

		if index>0: #hide then perform operation
			self.tcl.hide(force=1)
			if index==1: #Import
				mel.eval('Import;')
			elif index==2: #Import options
				mel.eval('ImportOptions;')
			elif index==3: #FBX Import Presets
				mel.eval('FBXUICallBack -1 editImportPresetInNewWindow fbx;') #Fbx Presets
			elif index==4: #Obj Import Presets
				mel.eval('FBXUICallBack -1 editImportPresetInNewWindow obj;') #Obj Presets
			cmb.setCurrentIndex(0)


	def cmb004(self, index=-1):
		'''Export
		'''
		cmb = self.file_ui.cmb004

		if index>0: #hide then perform operation
			self.tcl.hide(force=1)
			if index==1: #Export selection
				mel.eval('ExportSelection;')
			elif index==2: #Unreal
				mel.eval('SendToUnrealSelection;')
			elif index==3: #Unity 
				mel.eval('SendToUnitySelection;')
			elif index==4: #GoZ
				mel.eval('print("GoZ"); source"C:/Users/Public/Pixologic/GoZApps/Maya/GoZBrushFromMaya.mel"; source "C:/Users/Public/Pixologic/GoZApps/Maya/GoZScript.mel";')
			elif index==5: #Send to 3dsMax: As New Scene
				mel.eval('SendAsNewScene3dsMax;') #OneClickMenuExecute ("3ds Max", "SendAsNewScene"); doMaxFlow { "sendNew","perspShape","1" };
			elif index==6: #Send to 3dsMax: Update Current
				mel.eval('UpdateCurrentScene3dsMax;') #OneClickMenuExecute ("3ds Max", "UpdateCurrentScene"); doMaxFlow { "update","perspShape","1" };
			elif index==7: #Send to 3dsMax: Add to Current
				mel.eval('AddToCurrentScene3dsMax;') #OneClickMenuExecute ("3ds Max", "AddToScene"); doMaxFlow { "add","perspShape","1" };
			elif index==8: #Export to Offline File
				mel.eval('ExportOfflineFileOptions;') #ExportOfflineFile
			elif index==9: #Export options
				mel.eval('ExportSelectionOptions;')
			elif index==10: #FBX Export Presets
				mel.eval('FBXUICallBack -1 editExportPresetInNewWindow fbx;') #Fbx Presets
			elif index==11: #Obj Export Presets
				mel.eval('FBXUICallBack -1 editExportPresetInNewWindow obj;') #Obj Presets
			cmb.setCurrentIndex(0)


	def cmb005(self, index=-1):
		'''Recent Files
		'''
		cmb = self.file_ui.cmb005

		if index>0:
			force=True; force if str(pm.mel.file(query=1, sceneName=1, shortName=1)) else not force #if sceneName prompt user to save; else force open
			pm.openFile(cmb.items[index], open=1, force=force)
			cmb.setCurrentIndex(0)


	def cmb006(self, index=-1):
		'''Project Folder
		'''
		cmb = self.file_ui.cmb006

		path = self.formatPath(pm.workspace(query=1, rd=1)) #current project path.
		list_ = [f for f in os.listdir(path)]

		project = self.getNameFromFullPath(path) #add current project path string to label. strip path and trailing '/'

		cmb.addItems_(list_, project, clear=True)

		if index>0:
			os.startfile(path+list_[index-1])
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Save
		'''
		tb = self.file_ui.draggable_header.contextMenu.tb000

		wireframe = tb.contextMenu.chk000.isChecked()
		increment = tb.contextMenu.chk001.isChecked()
		quit = tb.contextMenu.chk002.isChecked()

		if wireframe:
			pm.mel.DisplayWireframe()

		if increment:
			pm.mel.IncrementAndSave()
		else:
			filetype = 'mayaAscii' #type: mayaAscii, mayaBinary, mel, OBJ, directory, plug-in, audio, move, EPS, Adobe(R) Illustrator(R)
			pm.saveFile(force=1, preSaveScript='', postSaveScript='', type=filetype)

		if quit: #quit maya
			import time
			for timer in range(5):
				self.viewPortMessage('Shutting Down:<hl>'+str(timer)+'</hl>')
				time.sleep(timer)
			pm.mel.quit() # pm.Quit()


	def lbl000(self):
		'''Set Project
		'''
		newProject = mel.eval("SetProject;")

		self.cmb006() #refresh cmb006 items to reflect new project folder


	def lbl001(self):
		'''Minimize Main Application
		'''
		mel.eval("minimizeApp;")
		self.tcl.hide(force=1)


	def lbl002(self):
		'''Restore Main Application
		'''
		pass


	def lbl003(self):
		'''Close Main Application
		'''
		# force=false #pymel has no attribute quit error.
		# exitcode=""
		sceneName = str(mel.eval("file -query -sceneName -shortName;")) #if sceneName prompt user to save; else force close
		mel.eval("quit;") if sceneName else mel.eval("quit -f;")
		# pm.quit (force=force, exitcode=exitcode)


	def lbl004(self):
		'''Open current project root
		'''
		dir_ = pm.workspace(query=1, rd=1) #current project path.
		os.startfile(self.formatPath(dir_))


	@Slots.message
	def b000(self):
		'''Autosave: Open Directory
		'''
		# dir1 = str(pm.workspace(query=1, rd=1))+'autosave' #current project path.
		dir2 = os.environ.get('MAYA_AUTOSAVE_FOLDER').split(';')[0] #get autosave dir path from env variable.

		try:
			# os.startfile(self.formatPath(dir1))
			os.startfile(self.formatPath(dir2))
		except FileNotFoundError as error:
			return 'Error: The system cannot find the file specified.'


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


	def b002(self):
		'''Autosave: Delete All
		'''
		files = File.getRecentAutosave()
		for file in files:
			try:
				os.remove(file)
			except Exception as error:
				print (error)


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


	def b015(self):
		'''Remove String From Object Names.
		'''
		from_ = str(self.file_ui.t000.text()) #asterisk denotes startswith*, *endswith, *contains* 
		to = str(self.file_ui.t001.text())
		replace = self.file_ui.chk004.isChecked()
		selected = self.file_ui.chk005.isChecked()

		objects = pm.ls (from_) #Stores a list of all objects starting with 'from_'
		if selected:
			objects = pm.ls (selection=1) #if use selection option; get user selected objects instead
		from_ = from_.strip('*') #strip modifier asterisk from user input

		for obj in objects:
			relatives = pm.listRelatives(obj, parent=1) #Get a list of it's direct parent
			if 'group*' in relatives: #If that parent starts with group, it came in root level and is pasted in a group, so ungroup it
				relatives[0].ungroup()

			newName = to
			if replace:
				newName = obj.replace(from_, to)
			pm.rename(obj, newName) #Rename the object with the new name


	@staticmethod
	def getRecentFiles(index=None):
		'''Get a list of recent files.

		:Parameters:
			index (int) = Return the recent file directory path at the given index. Index 0 would be the most recent file.

		:Return:
			(list)(str)
		'''
		files = pm.optionVar(query='RecentFilesList')
		result = [Slots_maya.formatPath(f) for f in list(reversed(files)) 
					if "Autosave" not in f] if files else []

		try:
			return result[index]
		except (IndexError, TypeError) as error:
			return result


	@staticmethod
	def getRecentProjects():
		'''Get a list of recently set projects.

		:Return:
			(list)
		'''
		files = pm.optionVar(query='RecentProjectsList')
		result = [Slots_maya.formatPath(f) for f in list(reversed(files))]

		return result


	@staticmethod
	def getRecentAutosave(appendDatetime=False):
		'''Get a list of autosave files.

		:Parameters:
			appendDatetime (bool) = Attach a modified timestamp and date to given file path(s).

		:Return:
			(list)
		'''
		dir1 = str(pm.workspace(query=1, rd=1))+'autosave' #current project path.
		dir2 = os.environ.get('MAYA_AUTOSAVE_FOLDER').split(';')[0] #get autosave dir path from env variable.

		files = Slots_maya.getAbsoluteFilePaths(dir1, ['mb', 'ma']) + Slots_maya.getAbsoluteFilePaths(dir2, ['mb', 'ma'])
		result = [Slots_maya.formatPath(f) for f in list(reversed(files))] #format and reverse the list.

		if appendDatetime:  #attach modified timestamp
			result = Slots.fileTimeStamp(result)

		return result









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



# deprecated:


	# def tb000(self, state=None):
	# 	'''
	# 	Save
	# 	'''
	# 	tb = self.file_ui.tb000
	# 	if state=='setMenu':
	# 		tb.contextMenu.add('QCheckBox', setText='ASCII', setObjectName='chk003', setChecked=True, setToolTip='Toggle ASCII or binary file type.')
	# 		tb.contextMenu.add('QCheckBox', setText='Wireframe', setObjectName='chk000', setChecked=True, setToolTip='Set view to wireframe before save.')
	# 		tb.contextMenu.add('QCheckBox', setText='Increment', setObjectName='chk001', setChecked=True, setToolTip='Append and increment a unique integer value.')
	# 		tb.contextMenu.add('QCheckBox', setText='Quit', setObjectName='chk002', setToolTip='Quit after save.')
	# 		return

	# 	increment = tb.contextMenu.chk001.isChecked()
	# 	ASCII = tb.contextMenu.chk003.isChecked()
	# 	wireframe = tb.contextMenu.chk000.isChecked()
	# 	quit = tb.contextMenu.chk002.isChecked()

	# 	preSaveScript = ''
	# 	postSaveScript = ''

	# 	type_ = 'mayaBinary'
	# 	if ASCII: #toggle ascii/ binary
	# 		type_ = 'mayaAscii' #type: mayaAscii, mayaBinary, mel, OBJ, directory, plug-in, audio, move, EPS, Adobe(R) Illustrator(R)

	# 	if wireframe:
	# 		mel.eval('DisplayWireframe;')

	# 	#get scene name and file path
	# 	fullPath = str(mel.eval('file -query -sceneName;')) #ie. O:/Cloud/____Graphics/______project_files/elise.proj/elise.scenes/.maya/elise_mid.009.mb
	# 	index = fullPath.rfind('/')+1
	# 	curFullName = fullPath[index:] #ie. elise_mid.009.mb
	# 	path = fullPath[:index] #ie. O:/Cloud/____Graphics/______project_files/elise.proj/elise.scenes/.maya/

	# 	if increment: #increment filename
	# 		newName = self.incrementFileName(curFullName)
	# 		self.deletePreviousFiles(curFullName, path)
	# 		pm.saveAs (path+newName, force=1, preSaveScript=preSaveScript, postSaveScript=postSaveScript, type=type_)
	# 		print('{0} {1}'.format('Result:', path+newName))
	# 	else:	#save without renaming
	# 		pm.saveFile (force=1, preSaveScript=preSaveScript, postSaveScript=postSaveScript, type=type_)
	# 		print('{0} {1}'.format('Result:', path+currentName,))

	# 	if quit: #quit maya
	# 		import time
	# 		for timer in range(5):
	# 			self.viewPortMessage('Shutting Down:<hl>'+str(timer)+'</hl>')
	# 			time.sleep(timer)
	# 		mel.eval("quit;")
	# 		# pm.Quit()


	# @staticmethod
	# def incrementFileName(fileName):
	# 	'''
	# 	Increment the given file name.

	# 	:Parameters:
	# 		fileName (str) = file name with extension. ie. elise_mid.ma

	# 	:Return:
	# 		(str) incremented name. ie. elise_mid.000.ma
	# 	'''
	# 	import re

	# 	#remove filetype extention
	# 	currentName = fileName[:fileName.rfind('.')] #name without extension ie. elise_mid.009 from elise_mid.009.mb
	# 	#get file number
	# 	numExt = re.search(r'\d+$', currentName) #check if the last chars are numberic
	# 	if numExt is not None:
	# 		name = currentName[:currentName.rfind('.')] #strip off the number ie. elise_mid from elise_mid.009
	# 		num = int(numExt.group())+1 #get file number and add 1 ie. 9 becomes 10
	# 		prefix = '000'[:-len(str(num))]+str(num) #prefix '000' removing zeros according to num length ie. 009 becomes 010
	# 		newName = name+'.'+prefix #ie. elise_mid.010
			
	# 	else:
	# 		newName = currentName+'.001'

	# 	return newName


	# @staticmethod
	# def deletePreviousFiles(fileName, path, numberOfPreviousFiles=5):
	# 	'''
	# 	Delete older files.

	# 	:Parameters:
	# 		fileName (str) = file name with extension. ie. elise_mid.ma
	# 		numberOfPreviousFiles (int) = Number of previous copies to keep.
	# 	'''
	# 	import re, os

	# 	#remove filetype extention
	# 	currentName = fileName[:fileName.rfind('.')] #name without extension ie. elise_mid.009 from elise_mid.009.mb
	# 	#get file number
	# 	numExt = re.search(r'\d+$', currentName) #check if the last chars are numberic
	# 	if numExt is not None:
	# 		name = currentName[:currentName.rfind('.')] #strip off the number ie. elise_mid from elise_mid.009
	# 		num = int(numExt.group())+1 #get file number and add 1 ie. 9 becomes 10

	# 		oldNum = num-numberOfPreviousFiles
	# 		oldPrefix = '000'[:-len(str(oldNum))]+str(oldNum) #prefix the appropriate amount of zeros in front of the old number
	# 		oldName = name+'.'+oldPrefix #ie. elise_mid.007
	# 		try: #search recursively through the project folder and delete any old folders with the old filename
	# 			dir_ =  os.path.abspath(os.path.join(path, "../.."))
	# 			for root, directories, files in os.walk(dir_):
	# 				for filename in files:
	# 					if all([filename==oldName+ext for ext in ('.ma','.ma.swatches','.mb','.mb.swatches')]):
	# 						try:
	# 							import os
	# 							os.remove(filename)
	# 						except:
	# 							pass
	# 		except OSError:
	# 			print('{0} {1}'.format('Error: Could not delete', path+oldName))
	# 			pass