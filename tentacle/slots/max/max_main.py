# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Main(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def tree000(self, wItem=None, column=None):
		''''''
		tree = self.current_ui.tree000

		if wItem=='setMenu':
			tree.expandOnHover = True
			tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.
			return

		if not any([wItem, column]): #refresh list items -----------------------------
			recentCommandInfo = self.tcl.sb.prevCommand(docString=1, toolTip=1, as_list=1) #Get a list of any recent command names and their toolTips
			[tree.add('QLabel', 'Recent Commands', refresh=True, setText=s[0], setToolTip=s[1]) for s in recentCommandInfo]
			return

		# widget = tree.getWidget(wItem, column)
		header = tree.getHeaderFromColumn(column)
		text = tree.getWidgetText(wItem, column)
		index = tree.getIndexFromWItem(wItem, column)

		if header=='Recent Commands':
			recentCommands = self.tcl.sb.prevCommand(method=1, as_list=1) #Get a list of any recent commands
			method = recentCommands[index]
			if callable(method):
				method()

		# if header=='':
		# 	if text=='':
		# 		mel.eval('')
		# 	if text=='':
		# 		mel.eval('')


	def v013(self):
		'''Minimize Main Application

		'''
		self.tcl.sb.getMethod('file', 'b005')()


	def v024(self):
		'''Recent Command: 1
		'''
		self.tcl.sb.prevCommand(method=1, as_list=1)[-1]() #execute command at index


	def v025(self):
		'''Recent Command: 2
		'''
		self.tcl.sb.prevCommand(method=1, as_list=1)[-2]() #execute command at index
			

	def v026(self):
		'''Recent Command: 3
		'''
		self.tcl.sb.prevCommand(method=1, as_list=1)[-3]() #execute command at index


	def v027(self):
		'''Recent Command: 4
		'''
		self.tcl.sb.prevCommand(method=1, as_list=1)[-4]() #execute command at index


	def v028(self):
		'''Recent Command: 5
		'''
		self.tcl.sb.prevCommand(method=1, as_list=1)[-5]() #execute command at index


	def v029(self):
		'''Recent Command: 6
		'''
		self.tcl.sb.prevCommand(method=1, as_list=1)[-6]() #execute command at index







#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------