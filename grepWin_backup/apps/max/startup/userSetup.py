# !/usr/bin/python
from __future__ import print_function, absolute_import
import os.path, sys



#max python path----------------------------------------------------
from pymxs import runtime as rt
file_name = rt.getSourceFileName() #ie. "C:\__portable\_scripts\apps\max\startup\startup.ms"
file_path = rt.getFilenamePath(file_name) #ie. "C:\__portable\_scripts\apps\max\startup"

root_dir = file_path.replace('\\apps\\max\\startup\\', '', 1)
parent_dir = root_dir.replace('\\radial', '', 1)

app_scripts_dir	= os.path.join(root_dir, 'apps', 'max')
app_slots_dir = os.path.join(app_scripts_dir, 'slots')

#append to system path:
paths = [root_dir, parent_dir, app_scripts_dir, app_slots_dir]
for path in paths:
	sys.path.append(path)
# for p in sys.path: print (p) #debug: list all directories on the system environment path.






# ------------------------------------------------
# Notes:
# ------------------------------------------------



# ------------------------------------------------
# deprecated:

# import inspect
# file_path = inspect.getfile(lambda: None)