# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.main import Main



class Main_maya(Main, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)












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
		# 			wgts.= [tree.add(self.MultiWidget, parent, refresh=1, set_by_value=[k, v])
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