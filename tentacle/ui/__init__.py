# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect



sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.
# globals()['__package__'] = 'ui'


for module in os.listdir(os.path.dirname(__file__)):

	mod_name = module[:-3]
	mod_ext = module[-3:]

	if module == '__init__.py' or mod_ext != '.py':
		continue

	mod = importlib.import_module(mod_name)

	cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

	for cls_name, cls_mem in cls_members:
		globals()[cls_name] = cls_mem

del module









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