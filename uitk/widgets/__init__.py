# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect


def __getattr__(attr_name):
	"""This function dynamically imports a module and returns an attribute from the module. 

	Parameters:
		attr_name (str): The name of the attribute to be imported. The name should be in the format 
					'module_name.attribute_name' or just 'attribute_name'.
	Return:
		(obj) The attribute specified by the `attr_name` argument.

	:Raises:
		AttributeError: If the specified attribute is not found in the original module.

	Example:
		<package>.__getattr__('module1.attribute1') #returns: <attribute1 value>
		<package>.__getattr__('attribute1') #returns: <attribute1 value>
	"""
	try:
		module = __import__(f"{__package__}.{attr_name}", fromlist=[f"{attr_name}"])
		setattr(sys.modules[__name__], attr_name, getattr(module, attr_name))
		return getattr(module, attr_name)

	except ModuleNotFoundError as error:
		raise AttributeError(f"Module '{__package__}' has no attribute '{attr_name}'") from error

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

'''
EXAMPLE USE CASE:
import ui.widgets as wgts

wgts.PushButton #get a specific widget.
wgts.widgets #get a list of all widgets.
'''

# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------
