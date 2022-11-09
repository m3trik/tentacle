# !/usr/bin/python
# coding=utf-8
import sys, os



class Str_utils():
	'''
	'''

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

		lst = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure that the arg is a list.

		if case=='pascalCase':
			result = [s[:1].capitalize()+s[1:] for s in lst(string)] #capitalize the first letter.

		elif case=='camelCase':
			result = [s[0].lower()+s[1:] for s in lst(string)] #lowercase the first letter.

		elif isinstance(case, str) and hasattr(string, case):
			result = [getattr(s, case)() for s in lst(string)]

		else: #return the original string(s).
			return string

		return result[0] if len(result)==1 else result


	@staticmethod
	def formatName(name, stripTrailingInts=False, stripTrailingAlpha=False, strip='', suffix=''):
		'''
		:parameters:
			name (str)(obj) = The name string to format or the object itself (from which the name will be pulled).
			stripTrailingInts (bool) = Strip all trailing integers.
			stripTrailingAlpha (bool) = Strip all upper-case letters preceeded by a non alphanumeric character.
			strip (str)(list) = Specific string(s) to strip. All occurances will be removed.
			suffix (str) = A suffix to apply to the end result.

		:return:
			(str)
		'''
		import re

		try:
			n = name.split('|')[-1]
		except Exception as error:
			n = name.name().split('|')[-1]

		for s in strip:
			n = n.replace(s, '')

		while ((n[-1]=='_' or n[-1].isdigit()) and stripTrailingInts) or ('_' in n and (n=='_' or n[-1].isupper())) and stripTrailingAlpha:

			if (n[-1]=='_' or n[-1].isdigit()) and stripTrailingInts: #trailing underscore and integers.
				n = re.sub(re.escape(n[-1:]) + '$', '', n)

			if ('_' in n and (n=='_' or n[-1].isupper())) and stripTrailingAlpha: #trailing underscore and uppercase alphanumeric char.
				n = re.sub(re.escape(n[-1:]) + '$', '', n)

		return n+suffix


	@staticmethod
	def splitAtChars(strings, chars='|', occurance=-1):
		'''Split a string containing the given chars at the given occurance and return
		a two element tuple containing both halves.

		:Parameters:
			strings (str)(list) = The string(s) to operate on.
			occurance (int) = The occurance of the pipe to split at from left.
				ex. -1 would split at the last occurance. 0 would split at the first.
					If the occurance is out of range, the full string will be 
					returned as: ('original string', '')
		:Return:
			(list)

		ex. call: splitAtChars(['str|ing', 'string']) returns: [('str', 'ing'), ('string', '')]
		'''
		from iter_utils import Iter_utils

		result = []
		for s in Iter_utils.makeList(strings):
			try:
				s2 = ''.join(s.split(chars)[occurance])
				if chars in s:
					s1 = chars.join(s.split(chars)[:occurance])
				else:
					s1, s2 = (s2, '')
			except IndexError as error:
				s1, s2 = (s, '')

			result.append((s1, s2))
		return result


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


	@staticmethod
	def rreplace(string, old, new, count=None):
		'''Return a copy of 'string' with all occurrences of substring 'old' replaced by 'new'.
		If the optional argument count is given, only the first count occurrences are replaced.

		:parameters:
			string (str) = 
			old (str) = 
			new (str) = 
			count (int) = 	

		:return:
			(str)
		'''
		return new.join(string.rsplit(old, count))


	@staticmethod
	def truncate(string, length=75, beginning=True, insert='..'):
		'''Shorten the given string to the given length.
		An ellipsis will be added to the section trimmed.

		:Parameters:
			length (int) = The maximum allowed length before trunicating.
			beginning (bool) = Trim starting chars, else; ending.
			insert (str) = Chars to add at the trimmed area. (default: ellipsis)

		:Return:
			(str)

		ex. call: truncate('12345678', 4)
			returns: '..5678'
		'''
		if len(string)>length:
			if beginning: #trim starting chars.
				string = insert+string[-length:]
			else: #trim ending chars.
				string = string[:length]+insert
		return string








if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated ---------------------