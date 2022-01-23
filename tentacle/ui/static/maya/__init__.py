# !/usr/bin/python
# coding=utf-8
import sys, os.path

sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

if __name__=='__main__':
	import tentacle.ui
	globals()['__package__'] = 'tentacle.ui'


# print ('tentacle.ui:', __name__, __package__, __file__)






# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------


# import sys, os
# this_module_dir = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(this_module_dir)
# import sys; for p in sys.path: print (p)