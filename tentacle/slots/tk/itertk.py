# !/usr/bin/python
# coding=utf-8
import sys, os

import inspect


class Itertk():
	'''
	'''

	@staticmethod
	def makeList(x):
		'''Convert the given obj to a list.

		:Parameters:
			x () = The object to convert to a list if not already a list, set, or tuple.

		:Return:
			(list)
		'''
		return list(x) if isinstance(x, (list, tuple, set, dict, range)) else [x]


	@classmethod
	def formatReturn(cls, rtn, orig=None):
		'''Return the list element if the given iterable only contains a single element.
		If the list contains multiple elements, always return the full list.
		If the 'orig' arg is a multi-element type then the original format will always be returned.

		:Parameters:
			rtn (list) = An iterable.
			orig (obj) = Optionally; derive the return type form the original value.
					ie. if it was a multi-value type; do not modify the return value.
		:Return:
			(obj)(list) dependant on flags.
		'''
		orig = isinstance(orig, (list, tuple, set, dict, range))

		try:
			if len(rtn)==1 and not orig and not isinstance(rtn, str):
				return rtn[0]

		except Exception as e:
			pass
		return rtn


	@classmethod
	def nestedDepth(cls, lst, typ=(list, set, tuple)):
		'''Get the maximum nested depth of any sub-lists of the given list.
		If there is nothing nested, 0 will be returned.

		:Parameters:
			lst (list) = The list to check.
			typ (type)(tuple) = The type(s) to include in the query.

		:Return:
			(int) 0 if none, else the max nested depth.
		'''
		d=-1
		for i in lst:
			if isinstance(i, typ):
				d = max(cls.nestedDepth(i), d)
		return d+1


	@classmethod
	def flatten(cls, lst):
		'''Flatten arbitrarily nested lists.

		:Parameters:
			lst (list) = A list with potentially nested lists.

		:Return:
			(generator)
		'''
		for i in lst:
			if isinstance(i, (list, tuple, set)):
				for ii in cls.flatten(i):
					yield ii
			else:
				yield i


	@staticmethod
	def collapseList(lst, limit=None, compress=True, toString=True):
		'''Convert a list of integers to a collapsed sequential string format.
		ie. [19,22,23,24,25,26] to ['19', '22..26']

		:Parameters:
			lst (list) = A list of integers.
			limit (int) = limit the maximum length of the returned elements.
			compress (bool) = Trim redundant chars from the second half of a compressed set. ie. ['19', '22-32', '1225-6'] from ['19', '22..32', '1225..1226']
			toString (bool) = Return a single string value instead of a list.

		:Return:
			(list)(str) string if 'toString'.
		'''
		ranges=[]
		for x in map(str, lst): #make sure the list is made up of strings.
			if not ranges:
				ranges.append([x])
			elif int(x)-prev_x==1:
				ranges[-1].append(x)
			else:
				ranges.append([x])
			prev_x = int(x)

		if compress: #style: ['19', '22-32', '1225-6']
			collapsedList = ['-'.join([r[0], r[-1][len(str(r[-1]))-len(str((int(r[-1])-int(r[0])))):]] #find the difference and use that value to further trim redundant chars from the string
								if len(r) > 1 else r) 
									for r in ranges]

		else: #style: ['19', '22..32', '1225..1226']
			collapsedList = ['..'.join([r[0], r[-1]] 
								if len(r) > 1 else r) 
									for r in ranges]

		if limit and len(collapsedList)>limit:
			l = collapsedList[:limit]
			l.append('...')
			collapsedList = l
		
		if toString:
			collapsedList = ', '.join(collapsedList)

		return collapsedList


	@staticmethod
	def bitArrayToList(bitArray):
		'''Convert a binary bitArray to a python list.

		:Parameters:
			bitArray () = A bit array or list of bit arrays.

		:Return:
			(list) containing values of the indices of the on (True) bits.
		'''
		if len(bitArray):
			if type(bitArray[0])!=bool: #if list of bitArrays: flatten
				lst=[]
				for array in bitArray:
					lst.append([i+1 for i, bit in enumerate(array) if bit==1])
				return [bit for array in lst for bit in array]

			return [i+1 for i, bit in enumerate(bitArray) if bit==1]


	@staticmethod
	def rindex(itr, item):
		'''Get the index of the first item to match the given item 
		starting from the back (right side) of the list.

		:Parameters:
			itr (iter) = An iterable.
			item () = The item to get the index of.

		:Return:
			(int) -1 if element not found.
		'''
		return next(iter(i for i in range(len(itr)-1,-1,-1) if itr[i]==item), -1)


	@staticmethod
	def indices(itr, value):
		'''Get the index of each element of a list matching the given value.

		:Parameters:
			itr (iter) = An iterable.
			value () = The search value.

		:Return:
			(generator)
		'''
		return (i for i, v in enumerate(itr) if v==value)


	@staticmethod
	def removeDuplicates(lst, trailing=True):
		'''Remove all duplicated occurences while keeping the either the first or last.

		:parameters:
			lst (list) = The list to remove duplicate elements of.
			trailing (bool) = Remove all trailing occurances while keeping the first, else keep last.

		:return:
			(list)
		'''
		if trailing:
			return list(dict.fromkeys(lst))
		else:
			return list(dict.fromkeys(lst[::-1]))[::-1] #reverse the list when removing from the start of the list.


	@classmethod
	def filterList(cls, lst, include=[], exclude=[]):
		'''Filter the given list.
		An 'operator' value of 'None' filters without wildcards.

		:Parameters:
			lst (list) = The components(s) to filter.
			include (str)(obj)(list) = The objects(s) to include.
					supports using the '*' operator: startswith*, *endswith, *contains*
					Will include all items that satisfy ANY of the given search terms.
					meaning: '*.png' and '*Normal*' returns all strings ending in '.png' AND all 
					strings containing 'Normal'. NOT strings satisfying both terms.
			exclude (str)(obj)(list) = The objects(s) to exclude. Similar to include.
					exlude take precidence over include.
		:Return:
			(list)

		ex. call:
		filterList([0, 1, 2, 3, 2], [1, 2, 3], 2) #returns: [1, 3]
		'''
		exclude = cls.makeList(exclude)
		include = cls.makeList(include)

		if not any((i for i in include+exclude if isinstance(i, str) and '*' in i)): #if no wildcards used:
			return [i for i in lst if not i in exclude and (i in include if include else i not in include)]

		#else: split include and exclude lists into separate tuples according to wildcard positions. 
		if exclude:
			exc, excContains, excStartsWith, excEndsWith = [],[],[],[]
			for i in exclude:
				if isinstance(i, str) and '*' in i:
					if i.startswith('*'):
						if i.endswith('*'):
							excContains.append(i[1:-1])
						excEndsWith.append(i[1:])
					elif i.endswith('*'):
						excStartsWith.append(i[:-1])
				else:
					exc.append(i)
		if include:
			inc, incContains, incStartsWith, incEndsWith = [],[],[],[]
			for i in include:
				if isinstance(i, str) and '*' in i:
					if i.startswith('*'):
						if i.endswith('*'):
							incContains.append(i[1:-1])
						incEndsWith.append(i[1:])
					elif i.endswith('*'):
						incStartsWith.append(i[:-1])
				else:
					inc.append(i)

		result=[]
		for i in lst:

			if exclude:
				if i in exc or isinstance(i, str) and any((
					i.startswith(tuple(excStartsWith)),
					i.endswith(tuple(excEndsWith)),
					next(iter(chars in i for chars in excContains), False))):
					continue

			if include:
				if i not in inc and not (isinstance(i, str) and any(( 
					i.startswith(tuple(incStartsWith)), 
					i.endswith(tuple(incEndsWith)), 
					next(iter(chars in i for chars in incContains), False)))):
					continue

			result.append(i)
		return result


	@staticmethod
	def splitList(lst, into):
		'''Split a list into parts.

		:Parameters:
			into (str) = Split the list into parts defined by the following:
				'<n>parts' - Split the list into n parts.
					ex. 2 returns:  [[1, 2, 3, 5], [7, 8, 9]] from [1,2,3,5,7,8,9]
				'<n>parts+' - Split the list into n equal parts with any trailing remainder.
					ex. 2 returns:  [[1, 2, 3], [5, 7, 8], [9]] from [1,2,3,5,7,8,9]
				'<n>chunks' - Split into sublists of n size.
					ex. 2 returns: [[1,2], [3,5], [7,8], [9]] from [1,2,3,5,7,8,9]
				'contiguous' - The list will be split by contiguous numerical values.
					ex. 'contiguous' returns: [[1,2,3], [5], [7,8,9]] from [1,2,3,5,7,8,9]
				'range' - The values of 'contiguous' will be limited to the high and low end of each range.
					ex. 'range' returns: [[1,3], [5], [7,9]] from [1,2,3,5,7,8,9]
		:Return:
			(list)
		'''
		from string import digits, ascii_letters, punctuation
		mode = into.lower().lstrip(digits)
		digit = into.strip(ascii_letters+punctuation)
		n = int(digit) if digit else None

		if n:
			if mode=='parts':
				n = len(lst)*-1 // n*-1 #ceil
			elif mode=='parts+':
				n = len(lst) // n
			return [lst[i:i+n] for i in range(0, len(lst), n)]

		elif mode=='contiguous' or mode=='range':
			from itertools import groupby
			from operator import itemgetter

			try:
				contiguous = [list(map(itemgetter(1), g)) for k, g in groupby(enumerate(lst), lambda x: int(x[0])-int(x[1]))]
			except ValueError as error:
				print ('{} in splitList\n	# Error: {} #\n	{}'.format(__file__, error, lst))
				return lst
			if mode=='range':
				return [[i[0], i[-1]] if len(i)>1 else (i) for i in contiguous]
			return contiguous

# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)









if __name__=='__main__':
	pass



# -----------------------------------------------
# Notes
# -----------------------------------------------



# Deprecated ------------------------------------