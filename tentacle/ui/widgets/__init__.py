# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect



sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.
globals()['__package__'] = 'widgets'


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


rwidgets = [w for w in globals().values() if type(w).__name__=='ObjectType'] #get all imported widget classes as a list.









# -----------------------------------------------
# Notes
# -----------------------------------------------

'''
EXAMPLE USE CASE:
import ui.widgets as wgts

wgts.PushButton #get a specific widget.
wgts.widgets #get a list of all widgets.
'''

# -----------------------------------------------
# deprecated:
# -----------------------------------------------
