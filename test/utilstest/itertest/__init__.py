import sys, os
import importlib
import inspect


this_mod = sys.modules[__name__]
mod = importlib.import_module('iter_test')

cls_members = inspect.getmembers(mod, inspect.isclass)

for cls_name, cls_mem in cls_members:
	methods = [getattr(cls_mem, mn) for mn in dir(cls_mem) if callable(getattr(cls_mem, mn)) and not mn.startswith('_')]

	for m in methods:
		setattr(this_mod, m.__name__, m)


print (globals())