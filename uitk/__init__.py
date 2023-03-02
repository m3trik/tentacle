# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect


__package__ = 'uitk'
__version__ = '0.5.9'


def greeting(string, outputToConsole=True):
	'''Format a string using preset variables.

	Parameters:
		string (str): The greeting to format as a string with placeholders using the below keywords. 
			ex. 'Good {hr}! You are using {modver} with {pyver}.'
			{hr} - Gives the current time of day (morning, afternoon, evening)
			{pyver} - The python interpreter version.
			{modver} - This modules version.
		outputToConsole = Print the greeting.

	Return:
		(str)

	Example: greeting('Good {hr}! You are using {modver} with {pyver}.')
	'''
	import datetime
	h = datetime.datetime.now().hour
	hr = 'morning' if 5<=h<12 else 'afternoon' if h<18 else 'evening'

	pyver = 'interpreter v{}.{}.{}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2])

	modver = 'uitk v{}'.format(__version__)

	result = string.format(hr=hr, pyver=pyver, modver=modver)

	if outputToConsole:
		print (result)
	return result

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

greeting('Good {hr}! You are using {modver} with {pyver}.')

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------


# def greeting(hello=False, mod_version=False, py_version=False):
# 	'''
	# print(greeting(hello=1, mod_version=1, py_version=1))
# 	'''
# 	string=''

# 	if hello: #print greeting
# 		import datetime
# 		hour = datetime.datetime.now().hour
# 		greeting = 'morning' if 5<=hour<12 else 'afternoon' if hour<18 else 'evening'
# 		string+='\nGood {}!'.format(greeting)

# 	if py_version: #print python version
# 		string+='\ninterpreter v{}.{}.{}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2])

# 	if mod_version:
# 		string+='\ntentacle v{}'.format(__version__)

# 	return string