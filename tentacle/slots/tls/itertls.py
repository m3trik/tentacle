# !/usr/bin/python
# coding=utf-8
import sys, os

import inspect


class Itertls():
	'''
	'''

	@staticmethod
	def makeList(x):
		'''Convert the given obj to a list.

		:Parameters:
			x (unknown) = The object to convert to a list if not already a list, set, or tuple.

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


	@staticmethod
	def hasNested(lst):
		'''
		'''
		return any(isinstance(i, (list, tuple, set)) for i in lst)


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
	def rindex(lst, item):
		'''Get the index of the first item to match the given item 
		starting from the back (right side) of the list.

		:Parameters:
			lst (list) = The list to get the index from.
			item () = The item to get the index of.

		:Return:
			(int) -1 if element not found.
		'''
		return next(iter(i for i in range(len(lst)-1,-1,-1) if lst[i]==item), -1)


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

		:Parameters:
			lst (list) = The components(s) to filter.
			include (str)(obj)(list) = The objects(s) to include.
			exclude (str)(obj)(list) = The objects(s) to exclude.
								(exlude take precidence over include)
		:Return:
			(list)

		ex. call: filterList([0, 1, 2, 3, 2], [1, 2, 3], 2) #returns: [1, 3]
		'''
		include = cls.makeList(include)
		exclude = cls.makeList(exclude)
		return [i for i in lst if not i in exclude and (i in include if include else i not in include)]


# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)









if __name__=='__main__':
	pass



# -----------------------------------------------
# Notes
# -----------------------------------------------



# Deprecated ------------------------------------