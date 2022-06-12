# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Main(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui object of <name>. ie. self.polygons_ui
					<widget> (registered widget) = Any widget previously registered in the switchboard module. ie. self.PushButton
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
		'''
		tree = self.main_lower_submenu_ui.tree000
		tree.expandOnHover = True
		tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.


	def tree000(self, wItem=None, column=None):
		'''
		'''
		tree = self.main_lower_submenu_ui.tree000

		if not any([wItem, column]): # code here will run before each show event. generally used to refresh tree contents. -----------------------------
			#command history
			recentCommandInfo = self.sb.prevCommand(docString=1, toolTip=1, as_list=1) #Get a list of any recent command names and their toolTips
			[tree.add('QLabel', 'Recent Commands', refresh=1, setText=s[0], setToolTip=s[1]) for s in recentCommandInfo]
			return

		# widget = tree.getWidget(wItem, column)
		header = tree.getHeaderFromColumn(column)
		text = tree.getWidgetText(wItem, column)
		index = tree.getIndexFromWItem(wItem, column)

		if header=='Recent Commands':
			recentCommands = self.sb.prevCommand(method=1, as_list=1) #Get a list of any recent commands
			method = recentCommands[index]
			if callable(method):
				method()

		# # if header=='':
		# # 	if text=='':
		# # 		pass
		# # 	if text=='':
		# # 		pass
