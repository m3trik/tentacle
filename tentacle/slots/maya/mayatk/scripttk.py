# !/usr/bin/python
# coding=utf-8
import sys, os

import importlib
import inspect

try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)


class Scriptingtls():
	'''
	'''
	@staticmethod
	def getMelGlobals(keyword=None, caseSensitive=False):
		'''Get global MEL variables.

		:Parameters:
			keyword (str) = search string.

		:Return:
			(list)
		'''
		variables = [
			v for v in sorted(pm.mel.eval('env')) 
				if not keyword 
					or (v.count(keyword) if caseSensitive else v.lower().count(keyword.lower()))
		]

		return variables


	@staticmethod
	def convertMelToPy(mel, excludeFromInput=[], excludeFromOutput=['from pymel.all import *','s pm']):
		'''Convert a string representing mel code into a string representing python code.

		:Parameters:
			mel (str) = string containing mel code.
			excludeFromInput (list) (list) = of strings specifying series of chars to strip from the Input.
			excludeFromOutput (list) (list) = of strings specifying series of chars to strip from the Output.
		
		mel2PyStr Parameters:
			currentModule (str) = The name of the module that the hypothetical code is executing in. In most cases you will leave it at its default, the __main__ namespace.
			pymelNamespace (str) = The namespace into which pymel will be imported. the default is '', which means from pymel.all import *
			forceCompatibility (bool) = If True, the translator will attempt to use non-standard python types in order to produce python code which more exactly reproduces the behavior of the original mel file, but which will produce 'uglier' code. Use this option if you wish to produce the most reliable code without any manual cleanup.
			verbosity (int) = Set to non-zero for a lot of feedback.
		'''
		from pymel.tools import mel2py
		import re

		l = filter(None, re.split('[\n][;]', mel))

		python=[]
		for e in l:
			if not e in excludeFromInput:
				try:
					py = mel2py.mel2pyStr(e, pymelNamespace='pm')
					for i in excludeFromOutput:
						py = py.strip(i)
				except:
					py = e
				python.append(py)

		return ''.join(python)


	@staticmethod
	def commandHelp(command): #mel command help
		#:Parameters: command (str) = mel command
		command = ('help ' + command)
		modtext = (pm.mel.eval(command))
		outputscrollField (modtext, "command help", 1.0, 1.0) #text, window_title, width, height


	@staticmethod
	def keywordSearch (keyword): #keyword command search
		#:Parameters: keyword (str) = 
		keyword = ('help -list' + '"*' + keyword + '*"')
		array = sorted(pm.mel.eval(keyword))
		outputTextField(array, "keyword search")


	@staticmethod
	def queryRuntime (command): #query runtime command info
		type       = ('whatIs '                           + command + ';')
		catagory   = ('runTimeCommand -query -category '  + command + ';')
		command	   = ('runTimeCommand -query -command '   + command + ';')
		annotation = ('runTimeCommand -query -annotation '+ command + ';')
		type = (pm.mel.eval(type))
		catagory = (pm.mel.eval(catagory))
		command = (pm.mel.eval(command))
		annotation = (pm.mel.eval(annotation))
		output_text = '{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}'.format(command, "Type:", type, "Annotation:", annotation, "Catagory:", catagory, "Command:", command)
		outputscrollField(output_text, "runTimeCommand", 1.0, 1.0) #text, window_title, width, height


	@staticmethod
	def searchMEL (keyword): #search autodest MEL documentation
		url = '{}{}{}'.format("http://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/Commands/",keyword,".html")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def searchPython (keyword): #Search autodesk Python documentation
		url = '{}{}{}'.format("http://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/CommandsPython/",keyword,".html")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def searchPymel (keyword): #search online pymel documentation
		url = '{}{}{}'.format("http://download.autodesk.com/global/docs/maya2014/zh_cn/PyMel/search.html?q=",keyword,"&check_keywords=yes&area=default")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def currentCtx(): #get current tool context
		output_text = pm.mel.eval('currentCtx;')
		outputscrollField(output_text, "currentCtx", 1.0, 1.0)


	@staticmethod
	def sourceScript(): #Source External Script file
		import os.path

		mel_checkBox = checkBox('mel_checkBox', query=1, value=1)
		python_checkBox = checkBox('python_checkBox', query=1, value=1)

		if mel_checkBox == 1:
			path = os.path.expandvars("%\CLOUD%/____graphics/Maya/scripts/*.mel")
			
		else:
			path = os.path.expandvars("%\CLOUD%/____graphics/Maya/scripts/*.py")

		file = pm.system.fileDialog (directoryMask=path)
		pm.openFile(file)


	@staticmethod
	def commandRef(): #open maya MEL commands list 
		pm.showHelp ('http://download.autodesk.com/us/maya/2011help/Commands/index.html', absolute=True)


	@staticmethod
	def globalVars(): #$g List all global mel variables in current scene
		pm.mel.eval('scriptEditorInfo -clearHistory')
		array = sorted(pm.mel.eval("env"))
		outputTextField(array, "Global Variables")


	@staticmethod
	def listUiObjects(): #lsUI returns the names of UI objects
		windows			= '{}\n{}\n{}\n'.format("Windows", "Windows created using ELF UI commands:", pm.lsUI (windows=True))
		panels			= '{}\n{}\n{}\n'.format("Panels", "All currently existing panels:", pm.lsUI (panels=True))
		editors			= '{}\n{}\n{}\n'.format("Editors", "All currently existing editors:", pm.lsUI (editors=True))
		controls		= '{}\n{}\n{}\n'.format("Controls", "Controls created using ELF UI commands: [e.g. buttons, checkboxes, etc]", pm.lsUI (controls=True))
		control_layouts = '{}\n{}\n{}\n'.format("Control Layouts", "Control layouts created using ELF UI commands: [e.g. formLayouts, paneLayouts, etc.]", pm.lsUI (controlLayouts=True))
		menus			= '{}\n{}\n{}\n'.format("Menus", "Menus created using ELF UI commands:", pm.lsUI (menus=True))
		menu_items	= '{}\n{}\n{}\n'.format("Menu Items", "Menu items created using ELF UI commands:", pm.lsUI (menuItems=True))
		contexts		= '{}\n{}\n{}\n'.format("Tool Contexts", "Tool contexts created using ELF UI commands:", pm.lsUI (contexts=True))
		output_text	= '{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}'.format(windows, panels, editors, menus, menu_items, controls, control_layouts, contexts)
		outputscrollField(output_text, "Ui Elements", 6.4, 0.85)

# --------------------------------------------------------------------------------------------
from tentacle import import_submodules, addMembers
addMembers(__name__)
import_submodules(__name__)





# print (__package__, __file__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------
