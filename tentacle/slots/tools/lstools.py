# !/usr/bin/python
# coding=utf-8

import sys, os

import json



class Lstools():
	'''
	'''

	@staticmethod
	def list_(x):
		'''Convert a given obj to a list if it isn't a list, set, or tuple already.

		:Parameters:
			x (unknown) = The object to convert to a list if not already a list, set, or tuple.

		:Return:
			(list)
		'''
		return list(x) if isinstance(x, (list, tuple, set, dict)) else [x]


	@staticmethod
	def flatten(lst):
		'''
		'''
		return [val for sublst in lst for val in sublst]


	@staticmethod
	def rindex(lst, item):
		'''Get the index of the first item to match the given item 
		starting from the back of the list.

		:parameters:
			lst (list) = The list to get the index from.
			item () = The item to get the index of. 
		:return:
			(int)
		'''
		for i in range(len(lst)-1,-1,-1):
			if lst[i]==item:
				return i
		return -1


	@staticmethod
	def removeDuplicates(lst, trailing=True):
		'''Remove all duplicated occurences while keeping the either the first or last.

		:parameters:
			lst (list) = The list to remove duplicate elements of.
			trailing (bool) = Remove all trailing occurances while keeping the first, else keep last.

		:return:
			(list)
		'''
		lst = lst if trailing else lst[::-1] #reverse the list when removing from the start of the list.

		found = set()
		lst = [x for x in lst if x not in found and not found.add(x)]

		return lst if trailing else lst[::-1]


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









if __name__=='__main__':
	pass


# --------------------------------
# Notes
# --------------------------------



# Deprecated -----------------------------------------------