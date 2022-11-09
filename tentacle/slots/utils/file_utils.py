# !/usr/bin/python
# coding=utf-8

import sys, os

import json



class File_utils():
	'''
	'''
	@staticmethod
	def formatFilepath(string, section='', replace=''):
		'''Format a full path to file string from '\' to '/'.
		When a section arg is given, the correlating section of the string will be returned.
		If a replace arg is given, the stated section will be replaced by the given value.

		:Parameters:
			string (str) = The file path string to be formatted.
			section (str) = The desired subsection of the given path. 
				'path' path - filename, 
				'dir'  directory name, 
				'file' filename + ext, 
				'name', filename - ext,
				'ext', file extension,
				(if '' is given, the fullpath will be returned)

		:Return:
			(str)
		'''
		from str_utils import Str_utils
		assert isinstance(string, str), '{}: Incorrect datatype: {}'.format(__file__, type(string).__name__)

		string = os.path.expandvars(string) #convert any env variables to their values.
		string = '/'.join(string.split('\\')).rstrip('/') #convert forward slashes to back slashes.

		fullpath = string if '/' in string else ''
		filename_ = string.split('/')[-1]
		filename = filename_ if '.' in filename_ else ''
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

		return string #if no arg is given, the fullpath will be returned.


	@staticmethod
	def isValidPath(path):
		'''Determine if the given filepath is valid.

		:Parameters:
			path (str) = A filepath.

		:Return:
			(list)
		'''
		if os.path.isfile(path):
			return 'file'
		if os.path.isdir(path):
			return 'dir'
		return None


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
	def createBackupDirectory(dest):
		'''Create a backup directory if one doesn't already exist.

		:Parameters:
			dest (str) = The file path to the desired backup folder destination.
		'''
		try:
			if not os.path.exists(dest):
				os.makedirs(dest)
		except OSError:
			print ('Error: Creating backup directory: '+dest)


	@staticmethod
	def getDirectoryContents(path, returnType='files', exclude=[], include=[], recursive=False, topdown=True, stripExtension=False):
		'''Get the contents of a directory and any of it's children.

		:Parameters:
			path (str) = The path to the directory.
			returnType (str) = Return files and directories. Multiple types can be given using '|' 
						ex. 'files|dirs' (valid: 'files'(default), 'filepaths', 'dirs', 'dirpaths')
						case insensitive. Can be singular or plural.
			recursive (bool) = return the contents of the root dir only.
			exclude (str)(list) = Excluded specific child directories or files.
						*.ext will exclude all files with the given extension.
						exclude takes precedence over include.
			include (str)(list) = Include specific child directories or files.
						*.ext will include all files with the given extension.
						exclude takes precedence over include.
			stripExtension (bool) = Return filenames without their extension.
			topDown (bool) = Scan directories from the top-down, or bottom-up.

		:Return:
			(list)

		ex. getDirectoryContents(path, returnType='filePaths')
		ex. getDirectoryContents(path, returnType='files|dirs')
		'''
		from file_utils import File_utils
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
				if stripExtension:
					f.rstrip('.'+File_utils.formatFilepath(f, 'ext'))

				ext = File_utils.formatFilepath(f, 'ext')
				if f in exclude or '*.'+ext in exclude:
					continue

				if any(include): #filter include for None values so not to get a false positive.
					if not f in include and not '*.'+ext in include:
						continue

				if 'file' in types:
					result.append(f)
				if 'filepath' in types:
					result.append(os.path.join(root, f))

		return result


	@classmethod
	def getJsonFile(cls, returnType=''):
		'''Get the current json file path.

		:Return:
			(str)
		'''
		try:
			return cls.formatFilepath(cls._json_file, returnType)
		except AttributeError as error:
			cls._json_file = '/'.join([os.path.dirname(__file__), 'file_utils.json'])
			return cls._json_file


	@classmethod
	def setJsonFile(cls, string, subsection=''):
		'''Set the json file path in full or modify any of it's subsections.

		:Parameters:
			string (str) = The desired replacement string.
			subsection (str) = Modify only part of the file path.
				(Any of the 'returnType' args in 'formatFilepath')
				ex. 'path' path - filename,
					'dir'  directory name, 
					'file' filename + ext, 
					'name', filename - ext,
					'ext', file extension,
		'''
		cls._json_file = cls.formatFilepath(cls.getJsonFile(), subsection, string)


	@classmethod
	def setJson(cls, key, value):
		'''
		'''
		file = cls.getJsonFile()
		if not os.path.exists(file): #if the file doesn't exist, create it.
			open(file, 'w').close()

		try:
			with open(file, 'r') as f:
				dct = json.loads(f.read())
				dct[key] = value
		except json.decoder.JSONDecodeError as error:
			dct={}
			dct[key] = value

		with open(file, 'w') as f:
			f.write(json.dumps(dct))


	@classmethod
	def getJson(cls, key):
		'''
		'''
		file = cls.getJsonFile()

		try:
			with open(file, 'r') as f:
				return json.loads(f.read())[key]

		except KeyError as error:
			# print ('# Error: {}: getJson: KeyError: {}'.format(__file__, error))
			pass
		except FileNotFoundError as error:
			# print ('# Error: {}: getJson: FileNotFoundError: {}'.format(__file__, error))
			pass
		except json.decoder.JSONDecodeError as error:
			print ('# Error: {}: getJson: JSONDecodeError: {}'.format(__file__, error))

		return None









if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated ---------------------