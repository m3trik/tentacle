# !/usr/bin/python
# coding=utf-8
import sys, os

import strtk, itertk


class Filetk():
	'''
	'''
	@staticmethod
	def formatPath(strings, section='', replace=''):
		'''Format a given filepath(s).
		When a section arg is given, the correlating section of the string will be returned.
		If a replace arg is given, the stated section will be replaced by the given value.

		:Parameters:
			strings (str)(list) = The filepath(s) to be formatted.
			section (str) = The desired subsection of the given path. 
					'path' path - filename, 
					'dir'  directory name, 
					'file' filename + ext, 
					'name', filename - ext,
					'ext', file extension,
					(if '' is given, the fullpath will be returned)
		:Return:
			(str)(list) List if 'strings' given as list.
		'''
		result=[]
		for s in itertk.makeList(strings):
			if not isinstance(s, (str)):
				continue
			s = os.path.expandvars(s) #convert any env variables to their values.
			s = s[:2]+'/'.join(s[2:].split('\\')).rstrip('/') #convert forward slashes to back slashes.

			fullpath = s if '/' in s else ''
			filename_ = s.split('/')[-1]
			filename = filename_ if '.' in filename_ and not filename_.startswith('.') else ''
			path = '/'.join(s.split('/')[:-1]) if filename else s
			directory = s.split('/')[-2] if (filename and path) else s.split('/')[-1]
			name = ''.join(filename.rsplit('.', 1)[:-1]) if filename else '' if fullpath else s
			ext = filename.rsplit('.', 1)[-1]

			orig_str = s #the full original string (formatted with forwardslashes)

			if section=='path':
				s = path

			elif section=='dir':
				s = directory

			elif section=='file':
				s = filename

			elif section=='name':
				s = name

			elif section=='ext':
				s = ext

			if replace:
				s = Str_utils.rreplace(orig_str, s, replace, 1)

			result.append(s)

		return itertk.formatReturn(result, strings) #if 'strings' is given as a list; return a list.


	@classmethod
	def timeStamp(cls, filepaths, detach=False, stamp='%m-%d-%Y  %H:%M', sort=False):
		'''Attach a modified timestamp and date to given file path(s).

		:Parameters:
			filepaths (str)(list) = The full path to a file. ie. 'C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'
			detach (bool) = Remove a previously attached time stamp.
			stamp (str) = The time stamp format.
			sort (bool) = Reorder the list of filepaths by time. (most recent first)

		:Return:
			(list) ie. ['16:46  11-09-2021  C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'] from ['C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb']
		'''
		from datetime import datetime
		import os.path

		files = cls.formatPath(itertk.makeList(filepaths))

		result=[]
		if detach:
			for f in files:
				if len(f)>2 and not any(['/'==f[2], '\\'==f[2], '\\\\'==f[:2]]): #attempt to decipher whether the path has a time stamp.
					strip = ''.join(f.split()[2:])
					result.append(strip)
				else:
					result.append(f)
		else:
			for f in files:
				try:
					result.append('{}  {}'.format(datetime.fromtimestamp(os.path.getmtime(f)).strftime(stamp), f))
				except (FileNotFoundError, OSError) as error:
					continue

			if sort:
				result = list(reversed(sorted(result)))

		return result


	@staticmethod
	def isValidPath(path):
		'''Determine if the given filepath is valid.

		:Parameters:
			path (str) = A filepath.

		:Return:
			(list)
		'''
		path = os.path.expandvars(path) #convert any env variables to their values.

		if os.path.isfile(path):
			return 'file'
		elif os.path.isdir(path):
			return 'dir'
		return None


	@staticmethod
	def createDir(path):
		'''Create a directory if one doesn't already exist.

		:Parameters:
			path (str) = The desired filepath.
		'''
		try:
			if not os.path.exists(path):
				os.makedirs(path)
		except OSError as error:
			print ('{} in createDir\n\t# Error: {}.\n\tConfirm that the following path is correct: #\n\t{}'.format(__file__, error, path))


	@classmethod
	def getDirContents(cls, path, returnType='files', recursive=False, topdown=True, reverse=False, 
								incFiles=[], excFiles=[], incDirs=[], excDirs=[]):
		'''Get the contents of a directory and any of it's children.

		:Parameters:
			path (str) = The path to the directory.
			returnType (str) = Return files and directories. Multiple types can be given using '|' 
					ex. 'files|dirs' (valid: 'files'(default), filenames, 'filepaths', 'dirs', 'dirpaths')
					case insensitive. singular or plural.
			recursive (bool) = return the contents of the root dir only.
			topDown (bool) = Scan directories from the top-down, or bottom-up.
			reverse (bool) = When True, reverse the final result.
			incFiles (str)(list) = Include only specific files.
			excFiles (str)(list) = Excluded specific files.
			incDirs (str)(list) = Include only specific child directories.
			excDirs (str)(list) = Excluded specific child directories.
					supports using the '*' operator: startswith*, *endswith, *contains*
					ex. *.ext will exclude all files with the given extension.
					exclude takes precedence over include.
		:Return:
			(list)

		ex. getDirContents(path, returnType='filepaths')
		ex. getDirContents(path, returnType='files|dirs')
		'''
		path = os.path.expandvars(path) #translate any system variables that might have been used in the path.
		returnTypes = [t.strip().rstrip('s').lower() for t in returnType.split('|')] #strip any whitespace and trailing 's' of the types to allow for singular and plural to be used interchagably. ie. files | dirs becomes [file, dir]

		result=[]
		for root, dirs, files in os.walk(path, topdown=topdown):
			dirs[:] = itertk.filterList(dirs, incDirs, excDirs) #remove any directories in 'exclude'.

			if 'dir' in returnTypes:
				for d in dirs:
					result.append(d) #get the dir contents before filtering for root.
			if 'dirpath' in returnTypes:
				for d in dirs:
					result.append(os.path.join(root, d))
			if not recursive:
				dirs[:] = [d for d in dirs if d is root] #remove all but the root dir.

			files[:] = itertk.filterList(files, incFiles, excFiles) #remove any files in 'exclude'.
			for f in files:
				if 'file' in returnTypes:
					result.append(f)
				if 'filename' in returnTypes:
					n = cls.formatPath(f, 'name')
					result.append(n)
				if 'filepath' in returnTypes:
					result.append(os.path.join(root, f))
		if reverse:
			return result[::-1]
		return result


	@staticmethod
	def getFilepath(obj, incFilename=False):
		'''Get the filepath of a class or module.

		:Parameters:
			obj (obj) = A python module, class, or the built-in __file__ variable.
			incFilename (bool) = Include the filename in the returned result.

		:Return:
			(str)
		'''
		from types import ModuleType

		if isinstance(obj, type(None)):
			return ''
		elif isinstance(obj, str):
			filepath = obj
		elif isinstance(obj, ModuleType):
			filepath = obj.__file__
		else:
			clss = obj if callable(obj) else obj.__class__
			try:
				import inspect
				filepath = inspect.getfile(clss)

			except TypeError as error: #iterate over each filepath in the call frames, until a class with a matching name is found.
				import importlib

				filepath=''
				for frame_record in inspect.stack():
					if filepath:
						break
					frame = frame_record[0]
					_filepath = inspect.getframeinfo(frame).filename
					mod_name = os.path.splitext(os.path.basename(_filepath))[0]
					spec = importlib.util.spec_from_file_location(mod_name, _filepath)
					if not spec:
						continue
					mod = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(mod)

					for cls_name, clss_ in inspect.getmembers(mod, inspect.isclass): #get the module's classes.
						if cls_name==clss.__name__:
							filepath = _filepath
		if incFilename:
			return os.path.abspath(filepath)
		else:
			return os.path.abspath(os.path.dirname(filepath))


	@staticmethod
	def getFile(filepath, mode='a+', contents=False):
		'''Create a file if one doesn't already exist.

		:Parameters:
			filepath (str) = The path to an existing file or the desired location for one to be created.
			mode (str) = 'r' - Read - Default value. Opens a file for reading, error if the file does not exist.
				'a' - Append - Opens a file for appending, creates the file if it does not exist.
				'a+' - Read+Write - Creates a new file or opens an existing file, the file pointer position at the end of the file.
				'w' - Write - Opens a file for writing, creates the file if it does not exist.
				'w+' - Read+Write - Opens a file for reading and writing, creates the file if it does not exist.
				'x' - Create - Creates a new file, returns an error if the file exists.
				't' - Text - Default value. Text mode
				'b' - Binary - Binary mode (e.g. images)
			contents (bool) = Return the contents (of a text based file) instead of the file itself.

		:Return:
			(obj) file or file contents dependant on given parameters.
		'''
		with open(filepath, mode) as f:
			if contents: # note: f has now been truncated to 0 bytes, so you'll only be able to read data that you write after this point.
				f.seek(0)  # important: return to the top of the file before reading, otherwise you'll just read an empty string.
				try:
					data = f.read() # returns: 'somedata\n'
				except OSError as error:
					print ('{} in getFile\n\t# Error: {} #\n\tfilepath:{}\n\tmode: {}'.format(__file__, error, filepath, mode))
				return data
			return f


	@staticmethod
	def writeToFile(filepath, lines, mode='w'):
		'''Write the given list contents to the given file.

		:Parameters:
			filepath (str) = The path to an existing text based file.
			lines (list) = A list of strings to write to the file.
			mode (str) = 'r' - Read - Default value. Opens a file for reading, error if the file does not exist.
				'a' - Append - Opens a file for appending, creates the file if it does not exist.
				'a+' - Read+Write - Creates a new file or opens an existing file, the file pointer position at the end of the file.
				'w' - Write - Opens a file for writing, creates the file if it does not exist.
				'w+' - Read+Write - Opens a file for reading and writing, creates the file if it does not exist.
				'x' - Create - Creates a new file, returns an error if the file exists.
				't' - Text - Default value. Text mode
				'b' - Binary - Binary mode (e.g. images)
		'''
		with open(filepath, mode) as f:
			f.writelines(lines)


	@staticmethod
	def getFileContents(filepath):
		'''Get each line of a text file as indices of a list.

		:Parameters:
			filepath (str) = The path to an existing text based file.

		:Return:
			(list)
		'''
		with open(filepath) as f:
			return f.readlines()


# --------------------------------------------------------------------------------------------
from tentacle import addMembers
addMembers(__name__)









if __name__=='__main__':
	pass



# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# Deprecated ------------------------------------