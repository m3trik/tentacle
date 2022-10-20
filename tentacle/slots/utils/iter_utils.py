# !/usr/bin/python
# coding=utf-8

import sys, os



class Iter_utils():
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
		return list(x) if isinstance(x, (list, tuple, set, dict)) else [x]


	@staticmethod
	def formatReturn(lst):
		'''Return a single object if the given list only contains one element.
		If the list is empty return None. If the list contains multiple elements,
		return the full list.

		:Parameters:
			lst (list) = An iterable.

		:Return:
			(obj)(list)(None)
		'''
		return lst[0] if len(lst)==1 else lst if lst else None


	@classmethod
	def flatten(lst):
		'''Flatten arbitrarily nested lists.

		:Parameters:
			lst (list) = A list with potentially nested lists.

		:Return:
			(list)
		'''
		for i in lst:
			if isinstance(i, (list,tuple,set)):
				for ii in cls.flatten(i):
					yield ii
			else:
				yield i


	@staticmethod
	def collapseList(lst, limit=None, compress=True, returnAsString=True):
		'''Convert a list of integers to a collapsed sequential string format.
		ie. [19,22,23,24,25,26] to ['19', '22..26']

		:Parameters:
			lst (list) = A list of integers
			compress (bool) = Trim redundant chars from the second half of a compressed set. ie. ['19', '22-32', '1225-6'] from ['19', '22..32', '1225..1226']
			returnAsString (bool) = Return a single string value instead of a list.

		:Return:
			(list) or (str) if 'returnAsString'.
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
		
		if returnAsString:
			collapsedList = ', '.join(collapsedList)

		return collapsedList


	@staticmethod
	def bitArrayToList(bitArray):
		'''Convert a binary bitArray to a python list.

		:Parameters:
			bitArray=bit array
				*or list of bit arrays

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
		starting from the back of the list.

		:parameters:
			lst (list) = The list to get the index from.
			item () = The item to get the index of. 
		:return:
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

		# #alternate method:
		# lst = lst if trailing else lst[::-1] #reverse the list when removing from the start of the list.

		# found = set()
		# lst = [x for x in lst if x not in found and not found.add(x)]

		# return lst if trailing else lst[::-1]


	@classmethod
	def convertForDebugging(cls, obj):
		'''Recursively convert items in sbDict for debugging.

		:Parameters:
			obj (dict) = The dictionary to convert.

		:Return:
			(dict)
		'''
		if isinstance(obj, (list, set, tuple)):
			return [cls.convert(i) for i in obj]
		elif isinstance(obj, dict):
			return {cls.convert(k):cls.convert(v) for k, v in obj.items()}
		elif not isinstance(obj, (float, int, str)):
			return str(obj)
		else:
			return obj


	global cycleDict
	cycleDict={}
	@staticmethod
	def cycle(sequence, name=None, query=False):
		'''Toggle between numbers in a given sequence.
		Used for maintaining toggling sequences for multiple objects simultaniously.
		Each time this function is called, it returns the next number in the sequence
		using the name string as an identifier key.
		
		:Parameters:
			sequence (list) = sequence to cycle through. ie. [1,2,3].
			name (str) = identifier. used as a key to get the sequence value from the dict.
			
		ex. cycle([0,1,2,3,4], 'componentID')
		'''
		try:
			if query: #return the value without changing it.
				return cycleDict[name][-1] #get the current value ie. 0

			value = cycleDict[name] #check if key exists. if so return the value. ie. value = [1,2,3]
		
		except KeyError: #else create sequence list for the given key
			cycleDict[name] = [i for i in sequence] #ie. {name:[1,2,3]}

		value = cycleDict[name][0] #get the current value. ie. 1
		cycleDict[name] = cycleDict[name][1:]+[value] #move the current value to the end of the list. ie. [2,3,1]
		return value #return current value. ie. 1









if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated -----------------------------------------------