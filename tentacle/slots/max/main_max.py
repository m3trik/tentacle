# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.main import Main



class Main_max(Main, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Main.__init__(self, *args, **kwargs)

		










#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------