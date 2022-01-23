# !/usr/bin/python
# coding=utf-8
try: #Maya dependancies
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui

	import shiboken2

except ImportError as error:
	print(__file__, error)

from ui.static import File_ui



class File_ui_maya(File_ui):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		File_ui.__init__(self, *args, **kwargs)

		ctx = self.file_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
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
		if not ctx.containsMenuItems:
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
			cmb.addItems_(self.getRecentAutosave(appendDatetime=True), 'Recent Autosave', clear=True)

		cmb = self.file_ui.cmb003
		cmb.addItems_(['Import file', 'Import Options', 'FBX Import Presets', 'Obj Import Presets'], "Import")

		cmb = self.file_ui.cmb004
		items = ['Export Selection', 'Send to Unreal', 'Send to Unity', 'GoZ', 'Send to 3dsMax: As New Scene', 'Send to 3dsMax: Update Current', 
				'Send to 3dsMax: Add to Current', 'Export to Offline File', 'Export Options', 'FBX Export Presets', 'Obj Export Presets']
		cmb.addItems_(items, 'Export')

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
