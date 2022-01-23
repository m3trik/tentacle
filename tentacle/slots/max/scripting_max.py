# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.scripting import Scripting
from ui.static.max.scripting_ui_max import Scripting_ui_max



class Scripting(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Scripting_ui_max.__init__(self, *args, **kwargs)
		Scripting.__init__(self, *args, **kwargs)


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


	def b005(self):
		''''''
		pass


	def b006(self):
		''''''
		pass


	def b007(self):
		''''''
		pass

	def b008(self):
		''''''
		pass

	def b009(self):
		''''''
		pass









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# cmdScrollFieldReporter_ = pm.cmdScrollFieldReporter (
		# 														height=35,
		# 														backgroundColor=[0,0,0],
		# 														highlightColor=[0,0,0],
		# 														echoAllCommands=False,
		# 														filterSourceType="")

		# self.scripting_ui.plainTextEdit.appendPlainText(cmdScrollFieldReporter_)