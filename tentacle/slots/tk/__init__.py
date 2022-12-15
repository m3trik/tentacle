# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect

from tentacle.slots.tk import itertk


class Tk():
	'''
	'''
	@staticmethod
	def setAttributes(obj, **attributes):
		'''Set attributes for a given object.

		:Parameters:
			obj (obj) = The object to set attributes for.
			attributes (kwargs) = Attributes and their correponding values as keyword args.
		'''
		[setattr(obj, attr, value) for attr, value in attributes.items() 
			if attr and value]


	@staticmethod
	def getAttributes(obj, include=[], exclude=[]):
		'''Get attributes for a given object.

		:Parameters:
			obj (obj) = The object to get the attributes of.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']
	
		:Return:
			(dict) {'string attribute': current value}
		'''
		filtered = itertk.filterList(obj.__dict__, include, exclude)
		return {attr:getattr(obj, attr) for attr in filtered}


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


	@classmethod
	def areSimilar(cls, a, b, tol=0.0):
		'''Check if the two numberical values are within a given tolerance.
		Supports nested lists.

		:parameters:
			a (obj)(tuple) = The first object(s) to compare.
			b (obj)(tuple) = The second object(s) to compare.
			tol (float) = The maximum allowed variation between the values.

		:return:
			(bool)

		ex. call: areSimilar(1, 10, 9)" #returns: True
		ex. call: areSimilar(1, 10, 8)" #returns: False
		'''
		func = lambda a, b: abs(a-b)<=tol if isinstance(a, (int, float)) else True if isinstance(a, (list, set, tuple)) and cls.areSimilar(a, b, tol) else a==b
		return all(map(func, itertk.makeList(a), itertk.makeList(b)))


	@staticmethod
	def randomize(lst, ratio=1.0):
		'''Random elements from the given list will be returned with a quantity determined by the given ratio.
		A value of 0.5 will return 50% of the original elements in random order.

		:Parameters:
			lst (tuple) = A list to randomize.
			ratio (float) = A value of 0.0-1. (default: 100%) With 0 representing 0% and 
					1 representing 100% of the given elements returned in random order.
		:Return:
			(list)

		ex. call: randomize(range(10), 1.0) #returns: [8, 4, 7, 6, 0, 5, 9, 1, 3, 2]
		ex. call: randomize(range(10), 0.5) #returns: [7, 6, 4, 2, 8]
		'''
		import random

		lower, upper = 0.0, ratio if ratio<=1 else 1.0 #end result range.
		normalized = lower + (upper - lower) * len(lst) #returns a float value.
		randomized = random.sample(lst, int(normalized))

		return randomized

# -----------------------------------------------
from tentacle import import_submodules, addMembers
addMembers(__name__)
import_submodules(__name__)






# print (__package__, __file__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------
