# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtGui, QtWidgets, QtCore

try: #Blender dependancies
	import bpy

except ImportError as error:
	print(__file__, error)

from slots import Slots



class Slots_blender(Slots):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		Slots.__init__(self, *args, **kwargs)









#module name
print (__name__)
# ======================================================================
# Notes
# ======================================================================





#deprecated -------------------------------------

