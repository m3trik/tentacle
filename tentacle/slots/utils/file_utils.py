# !/usr/bin/python
# coding=utf-8
import sys, os


class File_utils():
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
		from str_utils import Str_utils
		from iter_utils import Iter_utils

		assert isinstance(strings, (str, list, tuple, set, dict)), 'Error: {}:\n  Incorrect datatype: {}'.format(__file__, type(strings).__name__)

		result=[]
		for string in Iter_utils.makeList(strings):
			string = os.path.expandvars(string) #convert any env variables to their values.
			string = string[:2]+'/'.join(string[2:].split('\\')).rstrip('/') #convert forward slashes to back slashes.

			fullpath = string if '/' in string else ''
			filename_ = string.split('/')[-1]
			filename = filename_ if '.' in filename_ and not filename_.startswith('.') else ''
			path = '/'.join(string.split('/')[:-1]) if filename else string
			directory = string.split('/')[-2] if (filename and path) else string.split('/')[-1]
			name = ''.join(filename.rsplit('.', 1)[:-1]) if filename else '' if fullpath else string
			ext = filename.rsplit('.', 1)[-1]

			orig_str = string #the full original string (formatted with forwardslashes)

			if section=='path':
				string = path

			elif section=='dir':
				string = directory

			elif section=='file':
				string = filename

			elif section=='name':
				string = name

			elif section=='ext':
				string = ext

			if replace:
				string = Str_utils.rreplace(orig_str, string, replace, 1)

			result.append(string)

		return Iter_utils.formatReturn(result, strings) #if 'strings' is given as a list; return a list.


	@classmethod
	def timeStamp(cls, files, detach=False, stamp='%m-%d-%Y  %H:%M', sort=False):
		'''Attach a modified timestamp and date to given file path(s).

		:Parameters:
			files (str)(list) = The full path to a file. ie. 'C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'
			detach (bool) = Remove a previously attached time stamp.
			stamp (str) = The time stamp format.
			sort (bool) = Reorder the list of files by time. (most recent first)

		:Return:
			(list) ie. ['16:46  11-09-2021  C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb'] from ['C:/Windows/Temp/__AUTO-SAVE__untitled.0001.mb']
		'''
		from datetime import datetime
		import os.path

		files = [files] if not isinstance(files, (list, tuple, set)) else files
		files = cls.formatPath(files)

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
	def createDirectory(path):
		'''Create a directory if one doesn't already exist.

		:Parameters:
			path (str) = The desired filepath.
		'''
		try:
			if not os.path.exists(path):
				os.makedirs(path)
		except OSError as error:
			print ('Error: {}: {}: {}'.format(__file__, error, path))


	@classmethod
	def getDirectoryContents(cls, path, returnType='files', include=[], exclude=[], recursive=False, topdown=True, stripExtension=False, reverse=False):
		'''Get the contents of a directory and any of it's children.

		:Parameters:
			path (str) = The path to the directory.
			returnType (str) = Return files and directories. Multiple types can be given using '|' 
						ex. 'files|dirs' (valid: 'files'(default), 'filepaths', 'dirs', 'dirpaths')
						case insensitive. Can be singular or plural.
			recursive (bool) = return the contents of the root dir only.
			include (str)(list) = Include only specific child directories or files.
						*.ext will isolate all files with the given extension.
						exclude takes precedence over include.
			exclude (str)(list) = Excluded specific child directories or files.
						*.ext will exclude all files with the given extension.
						exclude takes precedence over include.
			stripExtension (bool) = Return filenames without their extension.
			topDown (bool) = Scan directories from the top-down, or bottom-up.
			reverse (bool) = When True, reverse the final result.

		:Return:
			(list)

		ex. getDirectoryContents(path, returnType='filepaths')
		ex. getDirectoryContents(path, returnType='files|dirs')
		'''
		from iter_utils import Iter_utils

		exclude = Iter_utils.makeList(exclude)
		include = Iter_utils.makeList(include)

		path = os.path.expandvars(path) #translate any system variables that might have been used in the path.
		types = [t.strip().rstrip('s').lower() for t in returnType.split('|')] #strip any whitespace and trailing 's' of the types to allow for singular and plural to be used interchagably. ie. files | dirs becomes [file, dir]

		result=[]
		for root, dirs, files in os.walk(path, topdown=topdown):

			dirs[:] = [d for d in dirs if not d in exclude] #remove any directories in 'exclude'.
			if 'dir' in types:
				for d in dirs:
					result.append(d) #get the dir contents before filtering for root.
			if 'dirpath' in types:
				for d in dirs:
					result.append(os.path.join(root, d))
			if not recursive:
				dirs[:] = [d for d in dirs if d is root] #remove all but the root dir.

			for f in files:
				ext = cls.formatPath(f, 'ext')
				if f in exclude or '*.'+ext in exclude:
					continue

				if any(include): #filter include for None values so not to get a false positive.
					if not f in include and not '*.'+ext in include:
						continue

				if stripExtension:
					f = f.rstrip('.'+cls.formatPath(f, 'ext'))

				if 'file' in types:
					result.append(f)
				if 'filepath' in types:
					result.append(os.path.join(root, f))
		if reverse:
			return result[::-1]
		return result


	@staticmethod
	def getFilepath(obj, includeFilename=False):
		'''Get the filepath from a class or module.

		:Parameters:
			obj (obj) = A python module, class, or the built-in __file__ variable.
			includeFilename (bool) = Include the filename in the returned result.

		:Return:
			(str)
		'''
		from types import ModuleType

		if isinstance(obj, str):
			filepath = obj
		elif isinstance(obj, ModuleType):
			filepath = obj.__file__
		else:
			filepath = os.path.abspath(sys.modules[obj.__module__].__file__)

		if includeFilename:
			return filepath
		else:
			return os.path.abspath(os.path.dirname(filepath))


	@staticmethod
	def createFile(path, mode='w', close=True):
		'''Create a file if one doesn't already exist.

		:Parameters:
			path (str) = The desired filepath.
			mode (str) = "r" - Read - Default value. Opens a file for reading, error if the file does not exist.
				"a" - Append - Opens a file for appending, creates the file if it does not exist.
				"w" - Write - Opens a file for writing, creates the file if it does not exist.
				"x" - Create - Creates the specified file, returns an error if the file exists.
				"t" - Text - Default value. Text mode
				"b" - Binary - Binary mode (e.g. images)
			close (bool) = Do not leave the file open for writing.

		:Return:
			(obj) file
		'''
		try:
			f = open(path, mode)
			if close:
				f.close()
			return f
		except OSError as error:
			print ('Error: {}: {}: {}'.format(__file__, error, path))


	@staticmethod
	def writeToFile(file, lines, mode='w'):
		'''Write the given list contents to the given file.

		:Parameters:
			file (str) = A path to a text based file.
			lines (list) = A list of strings to write to the file.
			mode (str) = "r" - Read - Default value. Opens a file for reading, error if the file does not exist
						"a" - Append - Opens a file for appending, creates the file if it does not exist
						"w" - Write - Opens a file for writing, creates the file if it does not exist
						"x" - Create - Creates the specified file, returns an error if the file exist
						"t" - Text - Default value. Text mode
						"b" - Binary - Binary mode (e.g. images)
		'''
		with open(file, mode) as f:
			f.writelines(lines)


	@staticmethod
	def getFileContents(file):
		'''Get each line of a text file as indices of a list.

		:Parameters:
			file (str) = A path to a text based file.

		:Return:
			(list)
		'''
		with open(file) as f:
			return f.readlines()









if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated ---------------------