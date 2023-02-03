# !/usr/bin/python
# coding=utf-8
from uitk.slots.max import *
from uitk.slots.scripting import Scripting



class Scripting_max(Scripting, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.scripting.draggable_header.ctxMenu.cmb000
		items = ['']
		contents = cmb.addItems_(items, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.scripting.draggable_header.ctxMenu.cmb000

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
		if self.sb.scripting.chk000.isChecked():
			label = ".py"
		# self.sb.scripting.tabWidget.addTab(label)
		self.sb.scripting.tabWidget.insertTab(0, label)


	def b004(self):
		'''Delete Tab
		'''
		index = self.sb.scripting.tabWidget.currentIndex()
		self.sb.scripting.tabWidget.removeTab(index)









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


