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

		ctx = self.file_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			ctx.add(self.tcl.wgts.PushButton, setObjectName='tb000', setText='Save', setToolTip='Save the current file.')
			ctx.add(self.tcl.wgts.Label, setObjectName='lbl001', setText='Minimize App', setToolTip='Minimize the main application.')
			ctx.add(self.tcl.wgts.Label, setObjectName='lbl002', setText='Maximize App', setToolTip='Restore the main application.')
			ctx.add(self.tcl.wgts.Label, setObjectName='lbl003', setText='Close App', setToolTip='Close the main application.')

		cmb = self.file_ui.cmb005
		ctx = cmb.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QPushButton', setObjectName='b001', setText='Last', setToolTip='Open the most recent file.')
			cmb.addItems_(self.getRecentFiles(), "Recent Files", clear=True)

		ctx = self.file_ui.cmb006.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb001', setToolTip='Current project directory root.')
			ctx.add(self.tcl.wgts.Label, setObjectName='lbl000', setText='Set', setToolTip='Set the project directory.')
			ctx.add(self.tcl.wgts.Label, setObjectName='lbl004', setText='Root', setToolTip='Open the project directory.')

		cmb = self.file_ui.cmb006.contextMenu.cmb001
		cmb.addItems_(self.getRecentProjects(), "Recent Projects", clear=True)

		ctx = self.file_ui.draggable_header.contextMenu.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Wireframe', setObjectName='chk000', setToolTip='Set view to wireframe before save.')
			ctx.add('QCheckBox', setText='Increment', setObjectName='chk001', setChecked=True, setToolTip='Append and increment a unique integer value.')
			ctx.add('QCheckBox', setText='Quit', setObjectName='chk002', setToolTip='Quit after save.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.file_ui.draggable_header


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
