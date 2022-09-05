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
# globals()['__package__'] = 'ui'









# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------


# sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

# if __name__=='__main__':
# 	# import tentacle.ui
# 	globals()['__package__'] = 'tentacle.ui'


# from . import uiLevel_0, uiLevel_1, uiLevel_2, uiLevel_3
# from .uiLoader import UiLoader
# from .styleSheet import StyleSheet

# print ('tentacle.ui:', __name__, __package__, __file__)


# import sys, os
# this_module_dir = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(this_module_dir)
# import sys; for p in sys.path: print (p)