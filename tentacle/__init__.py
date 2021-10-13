# !/usr/bin/python
# coding=utf-8
import sys, os.path

import datetime

hour = datetime.datetime.now().hour
greeting = "morning" if 5<=hour<12 else "afternoon" if hour<18 else "evening"
print("Good {}!".format(greeting))

sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

if __name__=='__main__':
	import tentacle
	globals()['__package__'] = 'tentacle'


from .switchboard import Switchboard
from .childEvents import EventFactoryFilter
from .overlay import OverlayFactoryFilter
from .styleSheet import StyleSheet
from .tcl_main import Tcl_main

# print ('tentacle:', __name__, __package__, __file__)






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


# import os
# for module in os.listdir(os.path.dirname(__file__)):
# 	if module == '__init__.py' or module[-3:] != '.py':
# 		continue
# 	__import__(module[:-3], locals(), globals())
# del module