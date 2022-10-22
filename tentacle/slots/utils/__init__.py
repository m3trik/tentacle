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