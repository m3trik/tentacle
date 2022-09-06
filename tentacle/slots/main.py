# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Main(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		# tree = self.sb.main_lower_submenu.tree000
		tree = self.sb.main_lower_submenu.tree000
		tree.expandOnHover = True
		tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.


	def tree000(self, wItem=None, column=None):
		'''
		'''
		tree = self.sb.main_lower_submenu.tree000

		if not any([wItem, column]): # code here will run before each show event. generally used to refresh tree contents. -----------------------------
			#command history
			recentCommandInfo = self.sb.prevCommand(asList=1) #Get a list of any recent command names and their toolTips
			[tree.add('QLabel', 'Recent Commands', refresh=1, setText=w.name, setToolTip=w.toolTip()) for w in recentCommandInfo]
			return

		# widget = tree.getWidget(wItem, column)
		header = tree.getHeaderFromColumn(column)
		text = tree.getWidgetText(wItem, column)
		index = tree.getIndexFromWItem(wItem, column)

		if header=='Recent Commands':
			recentCommands = self.sb.prevCommand(method=1, asList=1) #Get a list of any recent commands
			method = recentCommands[index]
			if callable(method):
				method()

		# # if header=='':
		# # 	if text=='':
		# # 		pass
		# # 	if text=='':
		# # 		pass
