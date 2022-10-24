# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect



def import_modules(importAll=False):
	'''
	'''
	sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

	for module in os.listdir(os.path.dirname(__file__)):

		mod_name = module[:-3]
		mod_ext = module[-3:]

		if module == '__init__.py' or mod_ext != '.py':
			continue

		mod = importlib.import_module(mod_name)

		if importAll:
			if '__all__' in mod.__dict__: #is there an __all__?  if so respect it.
				names = mod.__dict__['__all__']

			else: #otherwise we import all names that don't begin with _.
				names = [x for x in mod.__dict__ if not x.startswith('_')]

			# now drag them in
			globals().update({k: getattr(mod, k) for k in names})

		else:
			cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

			for cls_name, cls_mem in cls_members:
				globals()[cls_name] = cls_mem

		del module


import_modules(importAll=0)



class Utils(File_utils, Img_utils, Iter_utils, Math_utils, Str_utils):
	'''
	'''
	@staticmethod
	def getAttributes(obj, include=[], exclude=[]):
		'''Get attributes for a given object.

		:Parameters:
			obj (obj) = The object to get the attributes of.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']

		:Return:
			(dict) {'string attribute': current value}
		'''
		return {attr:getattr(obj, attr) 
					for attr in obj.__dict__ 
						if not attr in exclude 
						and (attr in include if include else attr not in include)}


	@staticmethod
	def setAttributes(obj, attributes):
		'''Set attributes for a given object.

		:Parameters:
			obj (obj) = The object to set attributes for.
			attributes = dictionary {'string attribute': value} - attributes and their correponding value to set
		'''
		[setattr(obj, attr, value) 
			for attr, value in attributes.items() 
				if attr and value]


	@staticmethod
	def pipInstallOnError(module_name):
		'''Import a module.
		Attempt to pip install the module on ImportError.

		:Parameters:
			module_name (str) = The name of the module.

		:Return:
			(obj) The imported module.
		'''
		try:
			return __import__(module_name)
		except ImportError as error:
			from pip._internal import main as pip
			pip(['install', '--user', module_name])
			return __import__(module_name)


	@classmethod
	def convertForDebugging(cls, obj):
		'''Recursively convert items in sbDict for debugging.

		:Parameters:
			obj (dict) = The dictionary to convert.

		:Return:
			(dict)
		'''
		if isinstance(obj, (list, set, tuple)):
			return [cls.convert(i) for i in obj]
		elif isinstance(obj, dict):
			return {cls.convert(k):cls.convert(v) for k, v in obj.items()}
		elif not isinstance(obj, (float, int, str)):
			return str(obj)
		else:
			return obj


	global cycleDict
	cycleDict={}
	@staticmethod
	def cycle(sequence, name=None, query=False):
		'''Toggle between numbers in a given sequence.
		Used for maintaining toggling sequences for multiple objects simultaniously.
		Each time this function is called, it returns the next number in the sequence
		using the name string as an identifier key.
		
		:Parameters:
			sequence (list) = sequence to cycle through. ie. [1,2,3].
			name (str) = identifier. used as a key to get the sequence value from the dict.
			
		ex. cycle([0,1,2,3,4], 'componentID')
		'''
		try:
			if query: #return the value without changing it.
				return cycleDict[name][-1] #get the current value ie. 0

			value = cycleDict[name] #check if key exists. if so return the value. ie. value = [1,2,3]
		
		except KeyError: #else create sequence list for the given key
			cycleDict[name] = [i for i in sequence] #ie. {name:[1,2,3]}

		value = cycleDict[name][0] #get the current value. ie. 1
		cycleDict[name] = cycleDict[name][1:]+[value] #move the current value to the end of the list. ie. [2,3,1]
		return value #return current value. ie. 1









# print (__package__, __file__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------


# sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

# if __name__=='__main__':
# 	import tentacle
# 	globals()['__package__'] = 'tentacle'


# from .switchboard import Switchboard
# from .childEvents import EventFactoryFilter
# from .overlay import OverlayFactoryFilter
# from .tcl import Tcl

# print ('tentacle:', __name__, __package__, __file__)




# import sys, os
# this_module_dir = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(this_module_dir)
# import sys; for p in sys.path: print (p)


# import os
# for module in os.listdir(os.path.dirname(__file__)):
# 	if module == '__init__.py' or module[-3:] != '.py':
# 		continue
# 	__import__(module[:-3], locals(), globals())
# del module