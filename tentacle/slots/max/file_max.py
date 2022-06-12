# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.file import File



class File_max(File, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		File.__init__(self, *args, **kwargs)

		cmb = self.file_ui.draggable_header.contextMenu.cmb000
		items = ['Schematic View']
		cmb.addItems_(items, 'File Editors')

		cmb = self.file_ui.cmb002
		ctx = cmb.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QPushButton', setObjectName='b000', setText='Open Directory', setToolTip='Open the autosave directory.') #open directory
			ctx.add('QPushButton', setObjectName='b002', setText='Delete All', setToolTip='Delete all autosave files.') #delete all
			ctx.add('QCheckBox', setText='Autosave', setObjectName='chk006', setChecked=rt.autosave.Enable, setToolTip='Set the autosave state as active or disabled.') #toggle autosave
			ctx.add('QSpinBox', setPrefix='Amount: ', setObjectName='s000', setMinMax_='1-100 step1', setValue=rt.autosave.NumberOfFiles, setHeight_=20, setToolTip='The number of autosave files to retain.') #autosave amount
			ctx.add('QSpinBox', setPrefix='Interval: ', setObjectName='s001', setMinMax_='1-60 step1', setValue=rt.autosave.Interval, setHeight_=20, setToolTip='The autosave interval in minutes.') #autosave interval
			ctx.chk006.toggled.connect(lambda s: rt.autosave.setmxsprop('Enable', s))
			ctx.s000.valueChanged.connect(lambda v: rt.autosave.setmxsprop('NumberOfFiles', v))
			ctx.s001.valueChanged.connect(lambda v: rt.autosave.setmxsprop('Interval', v))
			cmb.addItems_(self.getRecentAutosave(appendDatetime=True), 'Recent Autosave', clear=True)

		cmb = self.file_ui.cmb003
		cmb.addItems_(['Import file', 'Import Options', 'Merge', 'Replace', 'Link Revit', 'Link FBX', 'Link AutoCAD'], 'Import')

		cmb = self.file_ui.cmb004
		items = ["Export Selection", "Export Options", "Unreal", "Unity", "GoZ", "Send to Maya: New Scene", "Send to Maya: Update Scene", "Send to Maya: Add to Scene"]
		cmb.addItems_(items, "Export")


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.file_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Schematic View':
				maxEval('schematicView.Open "Schematic View 1"')
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Recent Projects
		'''
		cmb = self.file_ui.cmb006.contextMenu.cmb001

		items = cmb.addItems_(self.getRecentProjects(), "Recent Projects", clear=True)

		if index>0:
			maxEval('setProject "'+items[index]+'"')
			cmb.setCurrentIndex(0)


	def cmb002(self, index=-1):
		'''Recent Autosave
		'''
		cmb = self.file_ui.cmb002

		items = cmb.addItems_(self.getRecentAutosave(appendDatetime=True), "Recent Autosave", clear=True)

		if index>0:
			file = Slots.fileNameTimeStamp(cmb.items[index], detach=True)[0] #cmb.items[index].split('\\')[-1]
			rt.loadMaxFile(file)
			cmb.setCurrentIndex(0)


	def cmb003(self, index=-1):
		'''Import
		'''
		cmb = self.file_ui.cmb003

		if index>0: #hide then perform operation
			self.sb.parent().hide(force=1)
			if index == 1: #Import
				maxEval('max file import')
			elif index == 2: #Import options
				maxEval('')
			elif index == 3: #Merge
				maxEval('max file merge')
			elif index == 4: #Replace
				maxEval('max file replace')
			elif index == 5: #Manage Links: Link Revit File
				maxEval('actionMan.executeAction 769996349 "108"')
			elif index == 6: #Manage Links: Link FBX File
				maxEval('actionMan.executeAction 769996349 "109"')
			elif index == 7: #Manage Links: Link AutoCAD File
				maxEval('actionMan.executeAction 769996349 "110"')
			cmb.setCurrentIndex(0)


	def cmb004(self, index=-1):
		'''Export
		'''
		cmb = self.file_ui.cmb004

		if index>0: #hide then perform operation
			self.sb.parent().hide(force=1)
			if index==1: #Export selection
				maxEval('actionMan.executeAction 0 "40373"') #max file export
			elif index==2: #Export options
				maxEval('')
			elif index==3: #Unreal: File: Game Exporter
				maxEval('actionMan.executeAction 0 "40488"')
			elif index==4: #Unity: File: Game Exporter
				maxEval('actionMan.executeAction 0 "40488"')
			elif index==5: #GoZ
				print('GoZ')
				maxEval(''' 
					try (
						if (s_verbose) then print "\n === 3DS -> ZBrush === "
						local result = s_gozServer.GoToZBrush()
						) catch ();
					''')
			elif index==6: #One Click Maya: Send as New Scene to Maya
				maxEval('actionMan.executeAction 924213374 "0"')
			elif index==7: #One Click Maya: Update Current Scene in Maya
				maxEval('actionMan.executeAction 924213374 "1"')
			elif index==8: #One Click Maya: Add to Current Scene in Maya
				maxEval('actionMan.executeAction 924213374 "2"')

			cmb.setCurrentIndex(0)


	def cmb005(self, index=-1):
		'''Recent Files
		'''
		cmb = self.file_ui.cmb005

		items = cmb.addItems_(self.getRecentFiles(), 'Recent Files:', clear=True)

		if index>0:
			rt.loadMaxFile(str(items[index-1]))
			cmb.setCurrentIndex(0)


	def cmb006(self, index=-1):
		'''Project Folder
		'''
		cmb = self.file_ui.cmb006

		path = self.formatPath(rt.pathconfig.getCurrentProjectFolderPath(), strip='file') #current project path.
		list_ = [f for f in os.listdir(path)]

		project = self.getNameFromFullPath(path) #add current project path string to label. strip path and trailing '/'

		cmb.addItems_(list_, project, clear=True)

		if index>0:
			dir_ = path+list_[index-1] #reformat for network address
			os.startfile(dir_)
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
			rt.saveMaxFile(quiet=True)

		if quit: #quit maya
			import time
			for timer in range(5):
				self.viewPortMessage('Shutting Down:<hl>'+str(timer)+'</hl>')
				time.sleep(timer)
			pm.mel.quit() # pm.Quit()


	def lbl000(self):
		'''Set Project
		'''
		maxEval('macros.run "Tools" "SetProjectFolder"') #rt.pathconfig.setCurrentProjectFolderPath(path) --Sets the current project folder to the given path. The Project Folder is displayed in the title bar of 3ds Max and will be updated instantly.

		self.cmb006() #refresh cmb006 items to reflect new project folder


	def lbl001(self):
		'''Minimize Main Application
		'''
		app = rt.createOLEObject('Shell.Application')
		maxEval('minimizeAll app')
		maxEval('undoMinimizeAll app')
		rt.releaseOLEObject(app)
		self.sb.parent().hide(force=1)


	def lbl002(self):
		'''Restore Main Application
		'''
		maxEval('actionMan.executeAction 0 "50026"') #Tools: Maximize Viewport Toggle


	def lbl003(self):
		'''Close Main Application
		'''
		maxEval("quitmax #noprompt") # maxEval("quitmax")


	def lbl004(self):
		'''Open current project root
		'''
		recentFiles = self.getRecentFiles() #current project path.
		dir_ = self.formatPath(recentFiles) #reformat for network address
		os.startfile(dir_)


	def b000(self):
		'''Autosave: Open Directory
		'''
		dir_ = rt.GetDir(rt.name('autoback'))
			
		try:
			os.startfile(self.formatPath(dir_))
		except FileNotFoundError as error:
			self.messageBox('The system cannot find the file specified.')


	def b002(self):
		'''Autosave: Delete All
		'''
		files = self.getRecentAutosave()
		for file in files:
			try:
				os.remove(file)
			except Exception as error:
				print (error)


	def b015(self):
		'''Remove String From Object Names.
		'''
		from_ = str(self.file_ui.t000.text()) #asterisk denotes startswith*, *endswith, *contains* 
		to = str(self.file_ui.t001.text())
		replace = self.file_ui.chk004.isChecked()
		selected = self.file_ui.chk005.isChecked()

		# objects = pm.ls (from_) #Stores a list of all objects starting with 'from_'
		# if selected:
		# 	objects = pm.ls (selection=1) #if use selection option; get user selected objects instead
		# from_ = from_.strip('*') #strip modifier asterisk from user input

		# for obj in objects:
		# 	relatives = pm.listRelatives(obj, parent=1) #Get a list of it's direct parent
		# 	if 'group*' in relatives: #If that parent starts with group, it came in root level and is pasted in a group, so ungroup it
		# 		relatives[0].ungroup()

		# 	newName = to
		# 	if replace:
		# 		newName = obj.replace(from_, to)
		# 	pm.rename(obj, newName) #Rename the object with the new name


	def getRecentFiles(self, index=None):
		'''Get a list of recent files from "RecentDocuments.xml" in the maxData directory.

		:Parameters:
			index (int) = Return the recent file directory path at the given index. Index 0 would be the most recent file.

		:Return:
			(list)(str)
		'''
		maxEval('''
		fn _getRecentFiles = (
			local recentfiles = (getdir #maxData) + "RecentDocuments.xml"
			if doesfileexist recentfiles then (
				XMLArray = #()
				xDoc = dotnetobject "system.xml.xmldocument"
				xDoc.Load recentfiles
				Rootelement = xDoc.documentelement

				XMLArray = for i = 0 to rootelement.childnodes.item[4].childnodes.itemof[0].childnodes.count-1 collect (
					rootelement.childnodes.item[4].childnodes.itemof[0].childnodes.itemof[i].childnodes.itemof[3].innertext
				)

				Return XMLArray
				LRXML = Undefined
				XDoc = Undefined
				XDoc = nothing
			)
		)
		''')
		files = rt._getRecentFiles()
		result = [Slots_max.formatPath(f) for f in files]

		try:
			return result[index]
		except (IndexError, TypeError) as error:
			return result


	def getRecentProjects(self):
		'''Get a list of recently set projects.

		:Return:
			(list)
		'''
		files = ['No 3ds max function']
		result = [Slots_max.formatPath(f) for f in list(reversed(files))]

		return result


	def getRecentAutosave(self, appendDatetime=False):
		'''Get a list of autosave files.

		:Parameters:
			appendDatetime (bool) = Attach a modified timestamp and date to given file path(s).

		:Return:
			(list)
		'''
		from datetime import datetime

		path = rt.GetDir(rt.name('autoback'))
		files = [r'{}\{}'.format(path, f) for f in os.listdir(path) if f.endswith('.max') or f.endswith('.bak')] #get list of max autosave files
		result = [Slots_max.formatPath(f) for f in list(reversed(files))] #format and reverse the list.

		if appendDatetime:  #attach modified timestamp
			result = Slots.fileNameTimeStamp(result)

		return result


	def incrementFileName(self, fileName):
		'''Increment the given file name.

		:Parameters:
			fileName (str) = file name with extension. ie. elise_mid.ma

		:Return:
			(str) incremented name. ie. elise_mid.000.ma
		'''
		import re

		#remove filetype extention
		currentName = fileName[:fileName.rfind('.')] #name without extension ie. elise_mid.009 from elise_mid.009.mb
		#get file number
		numExt = re.search(r'\d+$', currentName) #check if the last chars are numberic
		if numExt is not None:
			name = currentName[:currentName.rfind('.')] #strip off the number ie. elise_mid from elise_mid.009
			num = int(numExt.group())+1 #get file number and add 1 ie. 9 becomes 10
			prefix = '000'[:-len(str(num))]+str(num) #prefix '000' removing zeros according to num length ie. 009 becomes 010
			newName = name+'.'+prefix #ie. elise_mid.010
			
		else:
			newName = currentName+'.001'

		return newName


	def deletePreviousFiles(self, fileName, path, numberOfPreviousFiles=5):
		'''Delete older files.

		:Parameters:
			fileName (str) = file name with extension. ie. elise_mid.ma
			numberOfPreviousFiles (int) = Number of previous copies to keep.
		'''
		import re, os

		#remove filetype extention
		currentName = fileName[:fileName.rfind('.')] #name without extension ie. elise_mid.009 from elise_mid.009.mb
		#get file number
		numExt = re.search(r'\d+$', currentName) #check if the last chars are numberic
		if numExt is not None:
			name = currentName[:currentName.rfind('.')] #strip off the number ie. elise_mid from elise_mid.009
			num = int(numExt.group())+1 #get file number and add 1 ie. 9 becomes 10

			oldNum = num-numberOfPreviousFiles
			oldPrefix = '000'[:-len(str(oldNum))]+str(oldNum) #prefix the appropriate amount of zeros in front of the old number
			oldName = name+'.'+oldPrefix #ie. elise_mid.007
			try: #search recursively through the project folder and delete any old folders with the old filename
				dir_ =  os.path.abspath(os.path.join(path, "../.."))
				for root, directories, files in os.walk(dir_):
					for filename in files:
						if all([filename==oldName+ext for ext in ('.ma','.ma.swatches','.mb','.mb.swatches')]):
							try:
								import os
								os.remove(filename)
							except:
								pass
			except OSError:
				print('{0} {1}'.format('Error: Could not delete', path+oldName))









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------