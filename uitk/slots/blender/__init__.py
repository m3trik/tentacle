# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtGui, QtWidgets, QtCore

try: #Blender dependancies
	import bpy

except ImportError as error:
	print(__file__, error)

from uitk.slots import Slots



class Slots_blender(Slots):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		Slots.__init__(self, *args, **kwargs)


	def undo(fn):
		'''A decorator to place a function into Maya's undo chunk.
		Prevents the undo queue from breaking entirely if an exception is raised within the given function.

		:Parameters:
			fn (obj) = The decorated python function that will be placed into the undo que as a single entry.
		'''
		def wrapper(*args, **kwargs):
			# pm.undoInfo(openChunk=True)
			rtn = fn(*args, **kwargs)
			# pm.undoInfo(closeChunk=True)
			return rtn
		return wrapper









#module name
# print (__name__)
# ======================================================================
# Notes
# ======================================================================





#deprecated -------------------------------------

