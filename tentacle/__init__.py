# !/usr/bin/python
# coding=utf-8
import sys, os.path


name = 'tcl-toolkit'
__version__ = '0.510'


def greeting(hello=False, mod_version=False, py_version=False):
	'''
	'''
	string=''

	if hello: #print greeting
		import datetime
		hour = datetime.datetime.now().hour
		greeting = 'morning' if 5<=hour<12 else 'afternoon' if hour<18 else 'evening'
		string+='\nGood {}!'.format(greeting)

	if py_version: #print python version
		string+='\npython interpreter v{}.{}.{}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2])

	if mod_version:
		string+='\ntentacle v{}'.format(__version__)

	return string


def appendPaths(verbose=False, exclude=[]):
	'''Append all sub-directories to the python path.

	:Parameters:
		exclude (list) = Exclude directories by name.
		verbose (bool) = Output the results to the console. (Debug)
	'''
	path = (__file__.rstrip(__file__.split('\\')[-1])) #get the path to this module, and format it to get the path root.

	sys.path.insert(0, path)
	if verbose:
		print (path)

	# recursively append subdirectories to the system path.
	for root, dirs, files in os.walk(path):
		for dir_name in dirs:
			if not any([(e in root or e==dir_name) for e in exclude]):
				dir_path = os.path.join(root, dir_name)
				sys.path.insert(0, dir_path)
				if verbose:
					print (dir_path)



print(greeting(hello=1, mod_version=1, py_version=1))
appendPaths(verbose=0)









# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------