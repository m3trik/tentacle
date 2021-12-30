# !/usr/bin/python
# coding=utf-8
from maya_init import *



class Scripting(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		dh = self.scripting_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.scripting_ui.draggable_header.contextMenu.cmb000
		files = ['']
		contents = cmb.addItems_(files, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.scripting_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.scripting_ui.draggable_header.contextMenu.cmb000

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	def chk000(self, state=None):
		'''Toggle Mel/Python
		'''
		if self.scripting_ui.chk000.isChecked():
			self.scripting_ui.chk000.setText("python")
		else:
			self.scripting_ui.chk000.setText("MEL")


	def b000(self):
		'''Toggle Script Output Window
		'''
		state = pm.workspaceControl ("scriptEditorOutputWorkspace", query=1, visible=1)
		pm.workspaceControl ("scriptEditorOutputWorkspace", edit=1, visible=not state)


	def b001(self):
		'''Command Line Window
		'''
		mel.eval('commandLineWindow;')


	def b002(self):
		'''Script Editor
		'''
		mel.eval('ScriptEditor;')


	def b003(self):
		'''New Tab
		'''
		label = "MEL"
		if self.scripting_ui.chk000.isChecked():
			label = ".py"
		# self.scripting_ui.tabWidget.addTab(label)
		self.scripting_ui.tabWidget.insertTab(0, label)


	def b004(self):
		'''Delete Tab
		'''
		index = self.scripting_ui.tabWidget.currentIndex()
		self.scripting_ui.tabWidget.removeTab(index)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------