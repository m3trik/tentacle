# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots



class Main(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		lw = self.sb.main_lower_submenu.lw000
		# print (lw.getItems())
		# print (lw.getItemWidgets())


	def lw000(self, w=None):
		'''
		'''
		lw = self.sb.main_lower_submenu.lw000

		if not w: # code here will run before each show event. generally used to refresh list contents. ------------------
			#command history
			recentCommandInfo = [m.__name__ for m in self.sb.prevCommands] #Get a list of any recently called method names.
			# w1 = lw.getItemWidgetsByText('Recent Commands')[0]
			w1 = lw.getItemsByText('Recent Commands')[0]
			# print (0, w1)
			lw._addList(w1)
			# print (1, w1.list)
			w2 = w1.list.add('QPushButton', setObjectName='b004', setText='Button 4')
			# [w1.list.add('QLabel', setText=m.__doc__) for m in recentCommandInfo]
			return

		# print (w.text(), w, w.list)
		if w.text=='Recent Commands':
			recentCommands = self.sb.prevCommands #Get a list of any previously called slot methods.
			method = recentCommands[index]
			if callable(method):
				method()

