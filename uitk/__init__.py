# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect


__package__ = 'uitk'
__version__ = '0.5.3'


def greeting(string, outputToConsole=True):
	'''Format a string using preset variables.

	:Parameters:
		string (str): The greeting to format as a string with placeholders using the below keywords. 
			ex. 'Good {hr}! You are using {modver} with {pyver}.'
			{hr} - Gives the current time of day (morning, afternoon, evening)
			{pyver} - The python interpreter version.
			{modver} - This modules version.
		outputToConsole = Print the greeting.

	:Return:
		(str)

	:Example: greeting('Good {hr}! You are using {modver} with {pyver}.')
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


def import_submodules(package, filetypes=('py', 'pyc', 'pyd'), ignoreStartingWith=('.', '_')):
	'''Import submodules to the given package, expose their classes at the package level
	and their respective class methods at submodule level.

	:Parameters:
		package (str)(obj): A python package.
		filetypes (str)(tuple): Filetype extension(s) to include.
		ignoreStartingWith (str)(tuple): Ignore submodules starting with given chars.

	:Example: import_submodules(__name__)
	'''
	if isinstance(package, str):
		package = sys.modules[package]
	if not package:
		return

	pkg_dir = os.path.dirname(os.path.abspath(package.__file__))
	sys.path.append(pkg_dir) #append this dir to the system path.

	for mod_name in os.listdir(pkg_dir):
		if mod_name.startswith(ignoreStartingWith):
			continue

		elif os.path.isfile(os.path.join(pkg_dir, mod_name)):
			mod_name, *mod_ext = mod_name.rsplit('.', 1)
			if filetypes:
				if not mod_ext or mod_ext[0] not in filetypes:
					continue

		mod = importlib.import_module(mod_name)
		vars(package)[mod_name] = mod

		classes = inspect.getmembers(mod, inspect.isclass)

		for cls_name, clss in classes:
			vars(package)[cls_name] = clss

		# 	methods = inspect.getmembers(clss, inspect.isfunction)

		# 	for method_name, method in methods:
		# 		vars(mod)[method_name] = method

		del mod_name


def addMembers(module, ignoreStartingWith='_'):
	'''Expose class members at module level.

	:Parameters:
		module (str)(obj): A python module.
		ignoreStartingWith (str)(tuple): Ignore class members starting with given chars.

	:Example: addMembers(__name__)
	'''
	if isinstance(module, str):
		module = sys.modules[module]
	if not module:
		return

	classes = inspect.getmembers(module, inspect.isclass)

	for cls_name, clss in classes:
		cls_members = [(o, getattr(clss, o)) for o in dir(clss) if not o.startswith(ignoreStartingWith)]
		for name, mem in cls_members:
			vars(module)[name] = mem


# def pipInstallOnError(module_name):
# 	'''Import a module.
# 	Attempt to pip install the module on ImportError.
# 	:Parameters:
# 		module_name (str): The name of the module.
# 	:Return:
# 		(obj) The imported module.
# 	'''
# 	try:
# 		return __import__(module_name)

# 	except ImportError as error:
# 		from pip._internal import main as pip
# 		pip(['install', '--user', module_name])
# 		return __import__(module_name)


def lazy_import(importer_name, to_import):
	'''Return the importing module and a callable for lazy importing.

	:Parmameters:
		importer_name (str): Represents the module performing the
				import to help facilitate resolving relative imports.
		to_import (list): An iterable of the modules to be potentially imported (absolute
				or relative). The 'as' form of importing is also supported. e.g. 'pkg.mod as spam'
	:Return:
		(tuple) (importer module, the callable to be set to '__getattr__')

	:Example: mod, __getattr__ = lazy_import(__name__, modules_list)
	'''
	module = importlib.import_module(importer_name)
	import_mapping = {}
	for name in to_import:
		importing, _, binding = name.partition(' as ')
		if not binding:
			_, _, binding = importing.rpartition('.')
		import_mapping[binding] = importing

	def __getattr__(name):
		if name not in import_mapping:
			message = f'module {importer_name!r} has no attribute {name!r}'
			raise AttributeError(message)
		importing = import_mapping[name]
		# imortlib.import_module() implicitly sets submodules on this module as appropriate for direct imports.
		imported = importlib.import_module(importing, module.__spec__.parent)
		setattr(module, name, imported)

		return imported

	return module, __getattr__


def appendPaths(rootDir, ignoreStartingWith=('.', '__'), verbose=False):
	'''Append all sub-directories of the given 'rootDir' to the python path.

	:Parameters:
		rootDir (str): Sub-directories of this directory will be appended to the system path.
		ignoreStartingWith (str)(tuple): Ignore directories starting with the given chars.
		verbose (bool): Output the results to the console. (Debug)
	'''
	path = os.path.dirname(os.path.abspath(rootDir))
	sys.path.insert(0, path)
	if verbose:
		print (path)

	# recursively append subdirectories to the system path.
	for root, dirs, files in os.walk(path):
		dirs[:] = [d for d in dirs if not d.startswith(ignoreStartingWith)]
		for dir_name in dirs:
			dir_path = os.path.join(root, dir_name)
			sys.path.insert(0, dir_path)
			if verbose:
				print (dir_path)

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