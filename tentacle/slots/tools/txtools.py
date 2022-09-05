# !/usr/bin/python
# coding=utf-8

import sys, os

import json



class Txtools():
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

		# known issue: if the path does not include a filename and a directory name contains '.' the results may not be accurate.
		'''
		string = os.path.expandvars(string) #convert any env variables to their values.
		string = '/'.join(string.split('\\')) #convert forward slashes to back slashes.

		fullpath = string if '/' in string else ''
		path = '/'.join(string.split('/')[:-1]) if '.' in string else string
		filename = string.split('/')[-1] if '.' in string else ''
		directory = string.split('/')[-2] if filename else string.split('/')[-1]
		name = ''.join(filename.rsplit('.', 1)[:-1]) if '.' in string else '' if '/' in string else string
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

		return string #if '' is given, the fullpath will be returned.


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
	def setJson(key, value, file='txtools.json'):
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
	def getJson(key, file='txtools.json'):
		'''
		'''
		try:
			with open(file, 'r') as f:

				return json.loads(f.read())[key]

		except (FileNotFoundError, KeyError, json.decoder.JSONDecodeError) as error:
			return None


	@staticmethod
	def setCase(string, case='camelCase'):
		'''Format the given string(s) in the given case.
		
		:Parameters:
			string (str)(list) = The string(s) to format.
			case (str) = The desired return case. Accepts all python case operators. 
				valid: 'upper', 'lower', 'caplitalize' (default), 'swapcase', 'title', 'pascalCase', 'camelCase', None.

		:Return:
			(str)(list) returns a list if more than one string is given.
		'''
		if not string or not isinstance(string, str):
			return string

		list_ = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure that the arg is a list.

		if case=='pascalCase':
			result = [s[:1].capitalize()+s[1:] for s in list_(string)] #capitalize the first letter.

		elif case=='camelCase':
			result = [s[0].lower()+s[1:] for s in list_(string)] #lowercase the first letter.

		elif isinstance(case, str) and hasattr(string, case):
			result = [getattr(s, case)() for s in list_(string)]

		else: #return the original string(s).
			return string

		return result[0] if len(result)==1 else result


	@classmethod
	def insert(cls, src, ins, at, occurrence=1, before=False):
		'''Insert character(s) into a string at a given location.
		if the character doesn't exist, the original string will be returned.

		:parameters:
			src (str) = The source string.
			ins (str) = The character(s) to insert.
			at (str)(int) = The index or char(s) to insert at.
			occurrence (int) = Valid only when 'at' is given as a string.
						Specify which occurrence to insert at. default: first
			before (bool) = Valid only when 'at' is given as a string.
						Specify inserting before or after. default: after
		:return:
			(str)
		'''
		try:
			return ''.join((src[:at], str(ins), src[at:]))

		except TypeError:
			i = src.replace(at, ' '*len(at), occurrence-1).find(at)
			return cls.insert(src, str(ins), i if before else i+len(at)) if i!=-1 else src









if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated -----------------------------------------------