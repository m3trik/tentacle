# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.scripting import Scripting



class Scripting_max(Scripting, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Scripting.__init__(self, *args, **kwargs)

		cmb = self.scripting_ui.draggable_header.contextMenu.cmb000
		items = ['']
		contents = cmb.addItems_(items, '')


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.scripting_ui.draggable_header.contextMenu.cmb000

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''Toggle Script Output Window
		'''
		state = pm.workspaceControl ("scriptEditorOutputWorkspace", query=1, visible=1)
		pm.workspaceControl ("scriptEditorOutputWorkspace", edit=1, visible=not state)


	def b001(self):
		'''Command Line Window
		'''
		maxEval('commandLineWindow_;')


	def b002(self):
		'''Script Editor
		'''
		maxEval('ScriptEditor;')


	def b003(self):
		'''New Tab
		'''
		label = "Maxscript"
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


