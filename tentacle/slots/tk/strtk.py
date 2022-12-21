# !/usr/bin/python
# coding=utf-8
import sys, os

import itertk


class Strtk():
	'''
	'''

	@staticmethod
	def setCase(strings, case='camelCase'):
		'''Format the given string(s) in the given case.
		
		:Parameters:
			strings (str)(list) = The string(s) to format.
			case (str) = The desired return case. Accepts all python case operators. 
				valid: 'upper', 'lower', 'capitalize' (default), 'swapcase', 'title', 'pascalCase', 'camelCase', None.

		:Return:
			(str)(list) List if 'string' given as list.
		'''
		if not strings or not isinstance(strings, str):
			return strings

		if case=='pascalCase':
			result = [s[:1].capitalize()+s[1:] for s in itertk.makeList(strings)] #capitalize the first letter.

		elif case=='camelCase':
			result = [s[0].lower()+s[1:] for s in itertk.makeList(strings)] #lowercase the first letter.

		else:
			try:
				result = [getattr(s, case)() for s in itertk.makeList(strings)]

			except AttributeError as error: #return the original string(s).
				return strings

		return itertk.formatReturn(result, strings) #if 'strings' is given as a list; return a list.


	@staticmethod
	def splitAtChars(strings, chars='|', occurrence=-1):
		'''Split a string containing the given chars at the given occurrence and return
		a two element tuple containing both halves.

		:Parameters:
			strings (str)(list) = The string(s) to operate on.
			chars (str) = The chars to split at.
			occurrence (int) = The occurrence of the pipe to split at from left.
				ex. -1 would split at the last occurrence. 0 would split at the first.
					If the occurrence is out of range, the full string will be 
					returned as: ('original string', '')
		:Return:
			(tuple)(list) two element tuple, or list of two element tuples if multiple strings given.

		ex. call: splitAtChars(['str|ing', 'string']) returns: [('str', 'ing'), ('string', '')]
		'''
		result = []
		for s in itertk.makeList(strings):
			split = s.split(chars)

			try:
				s2 = ''.join(split[occurrence])
				if chars in s:
					s1 = chars.join(split[:occurrence])
				else:
					s1, s2 = (s2, '')
			except IndexError as error:
				s1, s2 = (s, '')

			result.append((s1, s2))

		return itertk.formatReturn(result, strings) #if 'strings' is given as a list; return a list.


	@classmethod
	def insert(cls, src, ins, at, occurrence=1, before=False):
		'''Insert character(s) into a string at a given location.
		if the character doesn't exist, the original string will be returned.

		:parameters:
			src (str) = The source string.
			ins (str) = The character(s) to insert.
			at (str)(int) = The index or char(s) to insert at.
			occurrence (int) = Specify which occurrence to insert at.
							Valid only when 'at' is given as a string.
							default: The first occurrence.
							(A value of -1 would insert at the last occurrence)
			before (bool) = Specify inserting before or after. default: after
							Valid only when 'at' is given as a string.
		:return:
			(str)
		'''
		try:
			return ''.join((src[:at], str(ins), src[at:]))

		except TypeError:
			if occurrence<0: #if 'occurrance' is a negative value, search from the right.
				i = src.replace(at, ' '*len(at), occurrence-1).rfind(at)
			else:
				i = src.replace(at, ' '*len(at), occurrence-1).find(at)
			return cls.insert(src, str(ins), i if before else i+len(at)) if i!=-1 else src


	@staticmethod
	def rreplace(string, old, new='', count=None):
		'''Replace occurrances in a string from right to left.
		The number of occurrances replaced can be limited by using the 'count' argument.

		:parameters:
			string (str) = 
			old (str) = 
			new (str)(int) = 
			count (int) = 	

		:return:
			(str)
		'''
		if not string or not isinstance(string, str):
			return string

		if count is not None:
			return str(new).join(string.rsplit(old, count))
		else:
			return str(new).join(string.rsplit(old))


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

		ex. call: truncate('12345678', 4) #returns: '..5678'
		'''
		if not string or not isinstance(string, str):
			return string

		if len(string)>length:
			if beginning: #trim starting chars.
				string = insert+string[-length:]
			else: #trim ending chars.
				string = string[:length]+insert
		return string


	@staticmethod
	def getTrailingIntegers(string, inc=0, asString=False):
		'''Returns any integers from the end of the given string.

		:Parameters:
			inc (int) = Increment by a step amount. (default: 0)
					0 does not increment and returns the original number.
			asString (bool) = Return the integers as a string instead of integers.

		"Return:
			(int)

		ex. getTrailingIntegers('p001Cube1', inc=1) #returns: 2
		'''
		import re

		if not string or not isinstance(string, str):
			return string

		m = re.findall(r"\d+\s*$", string)
		result = int(m[0])+inc if m else None

		if asString:
			return str(result)
		return result


	@staticmethod
	def findStr(find, strings, regEx=False, ignoreCase=False):
		'''Filter for elements that containing the given string in a list of strings.

		:Parameters:
			find (str) = The search string. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe chars.
				wildcards:
					*chars* - string contains chars.
					*chars - string endswith chars.
					chars* - string startswith chars.
					chars1|chars2 - string matches any of.  can be used in conjuction with other modifiers.
				regular expressions (if regEx True):
					(.) match any char. ex. re.match('1..', '1111') #returns the regex object <111>
					(^) match start. ex. re.match('^11', '011') #returns None
					($) match end. ex. re.match('11$', '011') #returns the regex object <11>
					(|) or. ex. re.match('1|0', '011') #returns the regex object <0>
					(\A,\Z) beginning of a string and end of a string. ex. re.match(r'\A011\Z', '011') #
					(\b) empty string. (\B matches the empty string anywhere else). ex. re.match(r'\b(011)\b', '011 011 011') #
			strings (list) = The string list to search.
			regEx (bool) = Use regular expressions instead of wildcards.
			ignoreCase (bool) = Search case insensitive.

		:Return:
			(list)

		ex. lst = ['invertVertexWeights', 'keepCreaseEdgeWeight', 'keepBorder', 'keepBorderWeight', 'keepColorBorder', 'keepColorBorderWeight']
			findStr('*Weight*', lst) #find any element that contains the string 'Weight'.
			findStr('Weight$|Weights$', lst, regEx=True) #find any element that endswith 'Weight' or 'Weights'.
		'''
		if regEx: #search using a regular expression.
			import re

			try:
				if ignoreCase:
					result = [i for i in strings if re.search(find, i, re.IGNORECASE)]
				else:
					result = [i for i in strings if re.search(find, i)]
			except Exception as e:
				print ('# Error findStr: in {}: {}. #'.format(find, e))
				result = []

		else: #search using wildcards.
			result=[]
			for w in find.split('|'): #split at pipe chars.
				w_ = w.strip('*').rstrip('*') #remove any modifiers from the left and right end chars.

				#modifiers
				if w.startswith('*') and w.endswith('*'): #contains
					if ignoreCase:				
						result+=[i for i in strings if w_.lower() in i.lower()] #case insensitive.
					else:
						result+=[i for i in strings if w_ in i]

				elif w.startswith('*'): #prefix
					if ignoreCase:
						result+=[i for i in strings if i.lower().endswith(w_.lower())] #case insensitive.
					else:
						result+=[i for i in strings if i.endswith(w_)]

				elif w.endswith('*'): #suffix
					if ignoreCase:
						result+=[i for i in strings if i.lower().startswith(w_.lower())] #case insensitive.
					else:
						result+=[i for i in strings if i.startswith(w_)]

				else: #exact match
					if ignoreCase:
						result+=[i for i in strings if i.lower()==w_.lower()] #case insensitive.
					else:
						result+=[i for i in strings if i==w_]

		return result


	@classmethod
	def findStrAndFormat(cls, strings, to, fltr='', regEx=False, ignoreCase=False, returnOldNames=False):
		'''Expanding on the 'findStr' function: Find matches of a string in a list of strings and re-format them.

		:Parameters:
			strings (list) = A list of string objects to search.
			to (str) = An optional asterisk modifier can be used for formatting. An empty string will attempt to remove the part of the string designated in the from argument.
				"" - (empty string) - strip chars.
				*chars* - replace only.
				*chars - replace suffix.
				**chars - append suffix.
				chars* - replace prefix.
				chars** - append prefix.
			fltr (str) = See the 'findStr' function's 'fltr' parameter for documentation.
			regEx (bool) = Use regular expressions instead of wildcards for the 'find' argument.
			ignoreCase (bool) = Ignore case when searching. Applies only to the 'fltr' parameter's search.
			returnOldNames (bool) = Return the old names as well as the new.

		:Return:
			(list) if returnOldNames: list of two element tuples containing the original and modified string pairs. [('frm','to')]
				else: a list of just the new names.
		'''
		import re

		if fltr: #if 'fltr' is not an empty string; fltr 'strings' for matches using 'fltr'.
			strings = cls.findStr(fltr, strings, regEx=regEx, ignoreCase=ignoreCase)

		frm_ = fltr.strip('*').rstrip('*') #re.sub('[^A-Za-z0-9_:]+', '', fltr) #strip any special chars other than '_'.
		to_ = to.strip('*').rstrip('*') #remove any modifiers from the left and right end chars.

		result=[]
		for orig_str in strings:

			#modifiers
			if to.startswith('*') and to.endswith('*'): #replace chars
				if ignoreCase:
					s = re.sub(frm_, to_, orig_str, flags=re.IGNORECASE) #remove frm_ from the string (case in-sensitive).
				else:
					s = orig_str.replace(frm_, to_)

			elif to.startswith('**'): #append suffix
				s = orig_str+to_

			elif to.startswith('*'): #replace suffix
				if ignoreCase:
					end_index = re.search(frm_, orig_str, flags=re.IGNORECASE).start() #get the starting index of 'frm_'.
					s = orig_str[:index]+to_
				else:
					s = orig_str.split(frm_)[0]+to_

			elif to.endswith('**'): #append prefix
				s = to_+orig_str

			elif to.endswith('*'): #replace prefix
				if ignoreCase:
					end_index = re.search(frm_, orig_str, flags=re.IGNORECASE).end() #get the ending index of 'frm_'.
					s = to_+orig_str[index:]
				else:
					s = to_+frm_+orig_str.split(frm_)[-1]

			elif not to_: #if 'to_' is an empty string:
				if fltr.endswith('*') and not fltr.startswith('*'): #strip only beginning chars.
					if ignoreCase:
						s = re.sub(frm_, '', orig_str, 1, flags=re.IGNORECASE) #remove the first instance of frm_ from the string (case in-sensitive).
					else:
						s = orig_str.replace(frm_, '', 1) #remove first instance of frm_ from the string.

				elif fltr.startswith('*') and not fltr.endswith('*'): #strip only ending chars.
					if ignoreCase:
						s = re.sub(r'(.*)'+frm_, r'\1', orig_str, flags=re.IGNORECASE) #remove the last instance of frm_ from the string (case in-sensitive).
					else:
						s = ''.join(orig_str.rsplit(frm_, 1)) #remove last instance of frm_ from the string.

				else:
					if ignoreCase:
						s = re.sub(frm_, '', orig_str, flags=re.IGNORECASE) #remove frm_ from the string (case in-sensitive).
					else:
						s = orig_str.replace(frm_, '') #remove frm_ from the string.
			else: #else; replace whole string.
				s = to_

			if returnOldNames:
				result.append((orig_str, s))
			else:
				result.append(s)

		return result


	@staticmethod
	def formatSuffix(string, suffix='', strip='', stripTrailingInts=False, stripTrailingAlpha=False):
		'''Re-format the suffix for the given string.

		:parameters:
			string (str) = The string to format.
			suffix (str) = Append a new suffix to the given string.
			strip (str)(list) = Specific string(s) to strip from the end of the given string.
			stripTrailingInts (bool) = Strip all trailing integers.
			stripTrailingAlpha (bool) = Strip all upper-case letters preceeded by a non alphanumeric character.

		:return:
			(str)
		'''
		import re

		try:
			s = string.split('|')[-1]
		except Exception as error:
			s = string.string().split('|')[-1]

		# strip each set of chars in 'strip' from end of string.
		if strip:
			strip = tuple([i for i in itertk.makeList(strip) if not i=='']) #assure 'strip' is a tuple and does not contain any empty strings.
			while s.endswith(strip):
				for chars in strip:
					s = s.rstrip(chars)

		while ((s[-1]=='_' or s[-1].isdigit()) and stripTrailingInts) or ('_' in s and (s=='_' or s[-1].isupper())) and stripTrailingAlpha:

			if (s[-1]=='_' or s[-1].isdigit()) and stripTrailingInts: #trailing underscore and integers.
				s = re.sub(re.escape(s[-1:]) + '$', '', s)

			if ('_' in s and (s=='_' or s[-1].isupper())) and stripTrailingAlpha: #trailing underscore and uppercase alphanumeric char.
				s = re.sub(re.escape(s[-1:]) + '$', '', s)

		return s+suffix

# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)









if __name__=='__main__':
	pass



# -----------------------------------------------
# Notes
# -----------------------------------------------



# Deprecated ------------------------------------