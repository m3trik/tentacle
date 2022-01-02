# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class Main(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		self.main_lower_ui = self.tcl.sb.getUi('main_lower_submenu')

		tree = self.main_lower_ui.tree000
		tree.expandOnHover = True
		tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.


	def tree000(self, wItem=None, column=None):
		'''
		'''
		tree = self.main_lower_ui.tree000

		if not any([wItem, column]): # code here will run before each show event. generally used to refresh tree contents. -----------------------------
			#command history
			recentCommandInfo = self.tcl.sb.prevCommand(docString=1, toolTip=1, as_list=1) #Get a list of any recent command names and their toolTips
			[tree.add('QLabel', 'Recent Commands', refresh=1, setText=s[0], setToolTip=s[1]) for s in recentCommandInfo]
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

		# # if header=='':
		# # 	if text=='':
		# # 		pass
		# # 	if text=='':
		# # 		pass


	def v013(self):
		'''Minimize Main Application
		'''
		self.tcl.sb.getMethod('file', 'b005')()









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated: -----------------------------------

		# 	node history
		# 	selection = pm.ls(sl=1, objectsOnly=1, flatten=1)
		# 	if selection:
		# 		history = selection[0].history()[1:]
		# 		for node in history:
		# 			parent = tree.add('QLabel', 'History', childHeader=node.name(), refresh=1, setText=node.name())
		# 			# print(parent, node.name())
		# 			attributes = Slots_maya.getAttributesMEL(node) #get dict containing attributes:values of the history node.
		# 			spinboxes = [tree.add('QDoubleSpinBox', parent, refresh=1, setSpinBoxByValue_=[k, v])
		# 				for k, v in attributes.items() 
		# 					if isinstance(v, (float, int, bool))]

		# 			set signal/slot connections:
		# 			wgts.= [tree.add(self.tcl.wgts.MultiWidget, parent, refresh=1, set_by_value=[k, v])
		# 				for k, v in attributes.items() 
		# 					if isinstance(v, (float, int, bool))]

		# 			for multiWidget in wgts.
		# 				attr = multiWidget.children_(index=0).text()
		# 				w = multiWidget.children_(index=1)
		# 				type_ = w.__class__.__name__

		# 				if type_ in ['QSpinBox', 'QDoubleSpinBox']:
		# 					w.valueChanged.connect(
		# 						lambda value, widget=w, node=node: self.setAttributesMEL(node, {attr:w.value()}))

		# 			[w.valueChanged.connect(
		# 				lambda value, widget=w, node=node: self.setAttributesMEL(node, {widget.prefix().rstrip(': '):value})) 
		# 					for w in spinboxes] #set signal/slot connections