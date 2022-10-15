# !/usr/bin/python
# coding=utf-8

import sys, os

import json



class File_utils():
	'''
	'''

	@staticmethod
	def formatFilepath(string, returnType=''):
		'''Format a full path to file string from '\' to '/'.
		When a returnType arg is given, the correlating section of the string will be returned.

		:Parameters:
			string (str) = The file path string to be formatted.
			returnType (str) = The desired subsection of the given path. 
				'path' path - filename, 
				'dir'  directory name, 
				'file' filename + ext, 
				'name', filename - ext,
				'ext', file extension,
				(if '' is given, the fullpath will be returned)

		:Return:
			(str)
		'''
		assert isinstance(string, str), 'Incorrect datatype for string argument: {}: {}'.format(string, type(string))
		isfile = os.path.isfile(string)
		# isDir = os.path.isdir(string)

		string = os.path.expandvars(string) #convert any env variables to their values.
		string = '/'.join(string.split('\\')) #convert forward slashes to back slashes.

		fullpath = string if '/' in string else ''
		path = '/'.join(string.split('/')[:-1]) if isfile else string
		filename = string.split('/')[-1] if isfile else ''
		directory = string.split('/')[-2] if filename else string.split('/')[-1]
		name = ''.join(filename.rsplit('.', 1)[:-1]) if isfile else '' if '/' in string else string
		ext = filename.rsplit('.', 1)[-1]

		if returnType=='path':
			string = path

		elif returnType=='dir':
			string = directory

		elif returnType=='file':
			string = filename

		elif returnType=='name':
			string = name

		elif returnType=='ext':
			string = ext

		return string #if no arg is given, the fullpath will be returned.


	@staticmethod
	def getFileContents(file):
		'''Get each line of a file as indices of a list.

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
	def getDirectoryContents(path, returnType='files', exclude=[], rootOnly=False, topdown=True):
		'''Get the contents of a directory and any of it's children.

		:Parameters:
			path (str) = The path to the directory.
			returnType (str) = Return files, directories, files with full path, dirs with full path. 
				multiple types can be given, separated by '|' ex. 'files | dirs'
				(valid: 'files'(default), 'filePaths', 'dirs', 'dirPaths')
			rootOnly (bool) = return the contents of the root dir only.
			exclude (list) = Excluded child directories or files.
			topDown (bool) = Scan directories from the top-down, or bottom-up.

		:Return:
			(list)

		ex. getDirectoryContents(path, returnType='filePaths')
		ex. getDirectoryContents(path, returnType='files|dirs')
		'''
		path = os.path.expandvars(path) #translate any system variables that might have been used in the path.
		returnTypes = [t.strip().rstrip('s') for t in returnType.split('|')] #strip any whitespace and trailing 's' of the types to allow for singular and plural to be used interchagably. ie. files | dirs becomes [file, dir]

		result=[]
		for root, dirs, files in os.walk(path, topdown=topdown):

			if rootOnly:
				if 'dir' in returnTypes:
					[result.append(d) for d in dirs] #get the dir contents before filtering for root.
				elif 'dirPath' in returnTypes:
					[os.path.join(root, d) for d in dirs]
				dirs[:] = [d for d in dirs if d is root] #remove all but the root dir.
			else:
				dirs[:] = [d for d in dirs if not d in exclude] #remove any directories in 'exclude'.
				if 'dir' in returnTypes:
					[result.append(d) for d in dirs]
				elif 'dirPath' in returnTypes:
					[os.path.join(root, d) for d in dirs]

			files[:] = [f for f in files if f not in exclude] #remove any files in 'exclude'.
			if 'file' in returnTypes:
				[result.append(f) for f in files]
			elif 'filePath' in returnTypes:
				[result.append(os.path.join(root, f)) for f in files]

		return result


	@staticmethod
	def setJson(key, value, file='file_utils.json'):
		'''
		'''
		try:
			with open(file, 'r') as f:
				dict_ = json.loads(f.read())
				dict_[key] = value
		except json.decoder.JSONDecodeError as error:
			dict_={}
			dict_[key] = value

		with open(file, 'w') as f:

			f.write(json.dumps(dict_))


	@staticmethod
	def getJson(key, file='file_utils.json'):
		'''
		'''
		try:
			with open(file, 'r') as f:

				return json.loads(f.read())[key]

		except (FileNotFoundError, KeyError, json.decoder.JSONDecodeError) as error:
			return None









if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated -----------------------------------------------