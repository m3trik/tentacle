# !/usr/bin/python
# coding=utf-8

import sys, os



class Txtools():
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