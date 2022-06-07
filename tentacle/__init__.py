# !/usr/bin/python
# coding=utf-8
import sys, os.path

import datetime

import importlib
import inspect



#print greeting
hour = datetime.datetime.now().hour
greeting = "morning" if 5<=hour<12 else "afternoon" if hour<18 else "evening"
print("Good {}!".format(greeting))

#print python version
print ('You are using python interpreter version {}.{}.{}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2]))


sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.
globals()['__package__'] = 'tentacle'


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