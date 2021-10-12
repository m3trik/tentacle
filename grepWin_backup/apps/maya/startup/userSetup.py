# !/usr/bin/python
# coding=utf-8
from __future__ import print_function, absolute_import
import os, sys

import pymel.core as pm
import maya.mel as mel
# from pymel import versions


# #globals
# VERSION = versions.current() #get maya version
# USER_SCRIPT_PATH = os.environ['USER_SCRIPT_PATH'].split(';')
# MAYA_SCRIPT_PATH = os.environ['MAYA_SCRIPT_PATH'].split(';')
# PYTHONPATH = os.environ['PYTHONPATH'].split(';')


#maya python path----------------------------------------------------
MAYA_SCRIPT_PATH = os.environ['MAYA_SCRIPT_PATH'].split(';')
file_path = next((s for s in MAYA_SCRIPT_PATH if s.endswith('/apps/maya/startup')), None)
root_dir = file_path.replace('/apps/maya/startup', '', 1)

parent_dir = root_dir.replace('/radial', '', 1)

app_scripts_dir	= os.path.join(root_dir, 'apps', 'maya')
app_slots_dir = os.path.join(app_scripts_dir, 'slots')

#append to system path:
paths = [root_dir, parent_dir, app_scripts_dir, app_slots_dir]
for path in paths:
	sys.path.append(path)
# for p in sys.path: print (p) #debug: list all directories on the system environment path.


#macros--------------------------------------------------------------
from macros import Macros
Macros().setMacros()



#script editor in/output---------------------------------------------
import commandPort #opens ports 7001/7002 for external script editor
import scriptEditorOutputTextHighlighting #syntax highlighting

mel.eval('source "scriptEditorOutput.mel";')
mel.eval('evalDeferred -lowPriority ("initScriptEditorOutputWin");')

pm.evalDeferred("scriptEditorOutputTextHighlighting.wrap()", lowestPriority=1)



#--------------------------------------------------------------------

#Set the initial state of the tool settings.
pm.workspaceControl("ToolSettings", edit=1, minimumWidth=False)
#Set the initial state of the attribute editor.
pm.workspaceControl("AttributeEditor", edit=1, minimumWidth=False)



#--------------------------------------------------------------------

#GoZ
mel.eval("source \"C:/Users/Public/Pixologic/GoZApps/Maya/GoZScript.mel\"");


#MASH tools
import MASH_tools


# ------------------------------------------------
# Get the main Maya window as a QtGui.QMainWindow instance.
# ------------------------------------------------

# import maya.OpenMayaUI as omui
# Main_Window_ptr = omui.MQtUtil.mainWindow()
# if Main_Window_ptr is not None:
# 	mainWindow = wrapInstance (long(Main_Window_ptr), QtWidgets.QWidget)

# ------------------------------------------------





# ------------------------------------------------
# deprecated:

# import inspect
# file_path = inspect.getfile(lambda: None)
# root_dir = file_path.replace('/apps/maya/startup/userSetup.py', '', 1)


# dir_ = os.path.dirname(os.path.abspath(__file__)) #get absolute path from dir of this module. #Error: __file__ is not defined (when python is embedded in another application).



#get %MAYA_SCRIPT_PATH% directories
# MAYA_SCRIPT_PATH = os.environ['MAYA_SCRIPT_PATH'].split(';')
# dir_ = next((s for s in MAYA_SCRIPT_PATH if s.endswith('/apps/maya')), None)
# if dir_:
# 	root_dir = dir_.replace('/apps/maya', '')
# else: #if path not found, print error and current paths set in maya.env
# 	module_name = os.path.splitext(os.path.basename(__file__))[0]
# 	print('Error: {}: dir not found in MAYA_SCRIPT_PATH.'.format(module_name)) #print error and module name.
# 	print('MAYA_SCRIPT_PATH: {}'.format(MAYA_SCRIPT_PATH))
